"""Cross-domain lantern inquiry: terrain -> sampled geometry -> light -> evidence."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from http.server import ThreadingHTTPServer
from threading import Thread
from urllib.request import urlopen, Request
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'examples')]
from geographical_requirements import GeographicalDesign
from inhabited_scene import InhabitedScene
from lantern_inquiry import LanternInquiry

spec = importlib.util.spec_from_file_location('inhabited_scene_lantern_http', ROOT / 'examples' / 'inhabited_scene.py')
app_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app_module)


class LanternTests(unittest.TestCase):
    def test_geography_bounds_do_not_commit_and_collapse_after_realization(self):
        geo = GeographicalDesign()
        point = geo.elevation_bounds(5.1, -1.3)
        self.assertFalse(point['resolved'])
        self.assertLess(point['min_m'], point['max_m'])
        self.assertEqual(geo.state()['committed_tiles'], [])
        geo.commit(geo.preview((2, 0), 11))
        fixed = geo.elevation_bounds(5.1, -1.3)
        self.assertTrue(fixed['resolved'])
        self.assertEqual(fixed['min_m'], fixed['max_m'])
        self.assertAlmostEqual(fixed['min_m'], geo.elevation(5.1, -1.3))

    def test_terrain_bounds_narrow_with_conditions_and_stable_boundary(self):
        geo = GeographicalDesign()
        self.assertTrue(geo.elevation_bounds(4, -.5)['resolved'])
        before = geo.elevation_bounds(5.1, -1.3)
        geo.add_condition({'x_km':5.1,'y_km':-1.3,
                           'target_m':geo.baseline(5.1,-1.3), 'tolerance_m':1})
        after = geo.elevation_bounds(5.1, -1.3)
        self.assertLess(after['max_m']-after['min_m'],before['max_m']-before['min_m'])
        self.assertEqual(geo.state()['committed_tiles'], [])

    def test_read_only_assessment_keeps_all_authorities_unmodified(self):
        scene = InhabitedScene()
        before = scene.export()
        for _ in range(4):
            answer = scene.lantern_inquiry.assess(scene._map_xy(scene.actors['traveler']))
            self.assertEqual(answer['geometry'],'unresolved')
            self.assertEqual(answer['missing_terrain_tiles'],[[2,0]])
            scene.inspect()
        self.assertEqual(scene.export(), before)
        self.assertFalse(scene.group._counts)

    def test_default_world_reveals_only_one_needed_tile_and_may_be_seen(self):
        scene = InhabitedScene(terrain_candidate_index=2)
        result = scene.act('look_lantern')['result']
        self.assertEqual(result['objective_realized'],['terrain_tile:2,0'])
        self.assertEqual(result['physical_visibility'],'detectable_candidate')
        self.assertEqual(result['assessment']['geometry'],'clear')
        self.assertEqual(scene.state()['terrain']['committed_tiles'], [[2, 0]])
        self.assertIsNone(scene.group._counts)
        self.assertEqual(scene.group.materialized_count,0)
        self.assertEqual(len(scene.state()['beliefs']['lantern']['evidence_ids']),1)
        again = scene.act('look_lantern')['result']
        self.assertEqual(again['objective_realized'],[])
        self.assertEqual(len(scene.state()['beliefs']['lantern']['evidence_ids']),2)

    def test_another_admissible_world_blocks_light_without_changing_any_other_truth(self):
        clear = InhabitedScene(terrain_candidate_index=2)
        blocked = InhabitedScene(terrain_candidate_index=11)
        answer_clear = clear.act('look_lantern')['result']
        answer_blocked = blocked.act('look_lantern')['result']
        self.assertEqual(answer_clear['physical_visibility'],'detectable_candidate')
        self.assertEqual(answer_blocked['physical_visibility'],'occluded')
        self.assertEqual(answer_blocked['assessment']['geometry'],'blocked')
        self.assertIsNotNone(answer_blocked['assessment']['blocking_sample_km'])
        self.assertEqual(clear.state()['terrain']['committed_tiles'], blocked.state()['terrain']['committed_tiles'])
        self.assertEqual(clear.state()['caravan'], blocked.state()['caravan'])
        self.assertEqual(clear.state()['lantern']['location_km'],blocked.state()['lantern']['location_km'])
        self.assertTrue(clear.state()['lantern']['lit'])
        self.assertTrue(blocked.state()['lantern']['lit'])

    def test_unlit_lantern_requires_no_terrain_realization(self):
        scene = InhabitedScene(lantern_lit=False)
        result = scene.act('look_lantern')['result']
        self.assertEqual(result['physical_visibility'],'undetectable_light')
        self.assertEqual(result['objective_realized'],[])
        self.assertEqual(scene.state()['terrain']['committed_tiles'],[])
        self.assertIsNone(scene.group._counts)

    def test_lantern_testimony_is_separate_from_true_visibility(self):
        scene = InhabitedScene(terrain_candidate_index=11)
        result = scene.act('look_lantern')['result']
        belief = scene.state()['beliefs']['lantern']
        self.assertNotIn('physical_visibility',belief)
        self.assertEqual(len(belief['evidence_ids']),1)
        self.assertEqual(belief['belief'], 'possible_glow' if result['perceived'] else 'not_detected')
        self.assertEqual(scene.state()['perceptions'][-1]['source'],'lantern_proxy')

    def test_existing_survey_prevents_duplicate_realization(self):
        scene = InhabitedScene()
        scene.act('survey',x_km=4.1,y_km=-.4)
        result = scene.act('look_lantern')['result']
        self.assertEqual(result['objective_realized'],[])
        self.assertEqual(scene.state()['terrain']['committed_tiles'],[[2,0]])

    def test_replay_and_config_tamper_detection(self):
        for index, lit in [(2,True),(11,True),(2,False)]:
            scene = InhabitedScene(index,lit)
            scene.act('look_lantern')
            scene.act('scan')
            scene.act('approach')
            scene.act('look_lantern')
            saved = json.loads(json.dumps(scene.export()))
            restored = InhabitedScene.restore(saved)
            self.assertEqual(restored.state(), scene.state())
            self.assertEqual(restored.export(), saved)
            forged = deepcopy(saved)
            forged['configuration']['terrain_candidate_index'] = (11 if index != 11 else 2)
            with self.assertRaisesRegex(ValueError,'contradicts'):
                InhabitedScene.restore(forged)

    def test_prior_version_one_save_still_restores(self):
        scene = InhabitedScene()
        scene.act('scan')
        scene.act('survey',x_km=4.1,y_km=-.4)
        old = deepcopy(scene.export())
        old['version'] = 1
        old.pop('configuration')
        expected = old['expected_state']
        expected['version'] = 1
        expected.pop('lantern')
        expected['beliefs'].pop('lantern')
        expected['authorities'].pop('lamp_and_visibility')
        self.assertEqual(InhabitedScene.restore(old).state(),scene.state())

    def test_invalid_configuration_does_not_construct_world(self):
        for candidate in (-1, 1.2, True, 100001):
            with self.assertRaises(ValueError):
                InhabitedScene(terrain_candidate_index=candidate)
        with self.assertRaises(ValueError):
            InhabitedScene(lantern_lit=1)


class LanternHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = app_module.SceneApp(InhabitedScene())
        cls.server = ThreadingHTTPServer(('127.0.0.1',0),app_module.handler_for(cls.app))
        cls.thread = Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()
        cls.base = f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join(3)

    def setUp(self):
        self.app.scene = InhabitedScene()

    def get(self,path):
        return json.loads(urlopen(self.base+path,timeout=10).read())

    def test_readonly_endpoint(self):
        before = self.get('/api/export')
        self.assertEqual(self.get('/api/lantern')['geometry'],'unresolved')
        self.assertEqual(before,self.get('/api/export'))

    def test_look_endpoint_and_history(self):
        data = json.dumps({'operation':'look_lantern','args':{}}).encode()
        req = Request(self.base+'/api/act',data,headers={'Content-Type':'application/json'})
        response = json.loads(urlopen(req,timeout=10).read())
        self.assertEqual(response['event']['operation'],'look_lantern')
        self.assertEqual(response['event']['result']['objective_realized'],['terrain_tile:2,0'])
        self.assertEqual(InhabitedScene.restore(self.get('/api/export')).state(),response['state'])

    def test_http_foreign_origin_rejected_without_mutation(self):
        before = self.get('/api/export')
        data = json.dumps({'operation':'look_lantern','args':{}}).encode()
        req = Request(self.base+'/api/act',data,headers={
            'Content-Type':'application/json','Origin':'https://outside.example'})
        with self.assertRaises(HTTPError) as caught:
            urlopen(req,timeout=10)
        self.assertEqual(caught.exception.code,403)
        self.assertEqual(before,self.get('/api/export'))


if __name__ == '__main__':
    unittest.main()
