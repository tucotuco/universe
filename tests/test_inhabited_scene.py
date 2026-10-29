"""Integration invariants for the inhabited scene, not an optics or society model."""
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'examples')]
from inhabited_scene import InhabitedScene
# The application example has the same module stem; import it by explicit source file.
import importlib.util
spec = importlib.util.spec_from_file_location('inhabited_scene_http', ROOT / 'examples' / 'inhabited_scene.py')
app_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app_module)


class InhabitedSceneTests(unittest.TestCase):
    def setUp(self):
        self.scene = InhabitedScene()

    def test_initial_scenario_has_unresolved_composition_and_geography(self):
        state = self.scene.state()
        self.assertIsNone(state['caravan']['objective_counts'])
        self.assertFalse(state['caravan']['noticed'])
        self.assertEqual(state['caravan']['individuals_realized'], 0)
        self.assertEqual(state['terrain']['unresolved_tiles'], 8)
        self.assertEqual(state['beliefs']['estimates']['humans'], None)
        self.assertEqual(len(state['history']), 0)

    def test_inspection_and_rendering_do_not_mutate_reality_or_agent(self):
        before = self.scene.export()
        for _ in range(3):
            self.scene.inspect()
            self.scene.map_data()
        self.assertEqual(self.scene.export(), before)
        self.assertIsNone(self.scene.group._counts)

    def test_scan_changes_awareness_but_not_population_or_terrain(self):
        event = self.scene.act('scan')
        self.assertEqual(event['result']['perceived'], ['caravan', 'companion'])
        self.assertTrue(self.scene.state()['caravan']['noticed'])
        self.assertIsNone(self.scene.group._counts)
        self.assertEqual(self.scene.state()['terrain']['committed_tiles'], [])
        self.assertIsNone(self.scene.state()['beliefs']['estimates']['dogs'])

    def test_targeted_survey_commits_terrain_without_revealing_counts(self):
        event = self.scene.act('survey', x_km=4.1, y_km=-.4)
        self.assertEqual(event['result']['objective_realized'], ['terrain_tile:2,0'])
        self.assertEqual(self.scene.state()['terrain']['committed_tiles'], [[2, 0]])
        again = self.scene.act('survey', x_km=4.1, y_km=-.4)
        self.assertEqual(again['result']['objective_realized'], [])
        self.assertIsNone(self.scene.group._counts)
        self.assertEqual(self.scene.state()['caravan']['individuals_realized'], 0)

    def test_out_of_range_survey_rejected_without_any_mutation(self):
        before = self.scene.export()
        with self.assertRaisesRegex(ValueError, 'within 300 m'):
            self.scene.act('survey', x_km=1, y_km=1)
        self.assertEqual(self.scene.export(), before)

    def test_sky_refuses_missing_ephemeris_instead_of_inventing_sunset(self):
        answer = self.scene.act('sky')['result']
        self.assertEqual(answer['known_daypart'], 'dusk')
        self.assertIsNone(answer['sunset_prediction'])
        self.assertGreater(len(answer['missing']), 0)
        self.assertEqual(self.scene.environment.revision, 1)

    def test_successful_observation_realizes_aggregate_but_not_members(self):
        self.scene.act('scan')
        for _ in range(10):
            event = self.scene.act('observe')
            if event['result']['evidence_created']:
                break
        else:
            self.fail('No successful observation across ten attempts')
        s = self.scene.state()
        self.assertTrue(s['caravan']['aggregate_composition_realized'])
        self.assertTrue(s['evidence'])
        self.assertIsNotNone(s['beliefs']['estimates']['dogs'])
        self.assertEqual(s['caravan']['individuals_realized'], 0)
        self.assertEqual(s['terrain']['committed_tiles'], [])
        # Evidence is the sampled instrument reading, not copied truth.
        self.assertEqual(s['evidence'][0]['source'], 'traveler')
        self.assertIn('proxy', s['evidence'][0]['mode'])

    def test_observation_rejected_before_scan(self):
        before = self.scene.export()
        with self.assertRaisesRegex(ValueError, 'Scan'):
            self.scene.act('observe')
        self.assertEqual(self.scene.export(), before)

    def test_companion_communicates_evidence_not_objective_truth(self):
        communication = self.scene.act('talk')['result']
        self.assertEqual(communication['reports_shared'], 1)
        self.assertTrue(self.scene.state()['caravan']['aggregate_composition_realized'])
        evidence = self.scene.state()['evidence'][0]
        self.assertEqual(evidence['source'], 'companion')
        self.assertEqual(evidence['acquired_as'], 'communicated')
        self.assertEqual(self.scene.state()['caravan']['individuals_realized'], 0)
        again = self.scene.act('talk')['result']
        self.assertEqual(again['reports_shared'], 0)

    def test_approach_and_companion_range_constraint(self):
        old = self.scene.state()['traveler']['position_m']
        self.scene.act('approach')
        new = self.scene.state()['traveler']['position_m']
        self.assertEqual(new[0]-old[0], 240)
        self.assertEqual(self.scene.state()['time_s'], 120)
        self.assertFalse(self.scene.state()['companion']['nearby'])
        before = self.scene.export()
        with self.assertRaisesRegex(ValueError, 'too far'):
            self.scene.act('talk')
        self.assertEqual(self.scene.export(), before)

    def test_saved_history_round_trip_including_communication_and_terrain(self):
        for op, args in [('scan', {}), ('survey', {'x_km':4.1, 'y_km':-.4}),
                         ('sky', {}), ('talk', {}), ('observe', {}),
                         ('approach', {}), ('observe', {})]:
            self.scene.act(op, **args)
        saved = json.loads(json.dumps(self.scene.export()))
        restored = InhabitedScene.restore(saved)
        self.assertEqual(restored.state(), self.scene.state())
        self.assertEqual(restored.map_data(), self.scene.map_data())
        self.assertEqual(restored.export(), saved)

    def test_forged_history_rejected(self):
        self.scene.act('scan')
        payload = self.scene.export()
        payload['expected_state']['caravan']['objective_counts'] = {'dogs': 1000}
        with self.assertRaisesRegex(ValueError, 'contradicts'):
            InhabitedScene.restore(payload)
        payload = self.scene.export()
        payload['events'].append({'operation':'overwrite_truth','args':{}})
        with self.assertRaisesRegex(ValueError, 'Unsupported'):
            InhabitedScene.restore(payload)

    def test_bad_requests_are_rejected_without_mutating_world(self):
        for operation, arguments in [('survey', {'x_km':True,'y_km':-.4}),
                                     ('scan', {'unexpected':1}),
                                     ('approach', {'x_km':1}),
                                     ('survey', {'x_km':4.1,'y_km':float('nan')})]:
            before = self.scene.export()
            with self.assertRaises(ValueError):
                self.scene.act(operation, **arguments)
            self.assertEqual(self.scene.export(), before)


class InhabitedSceneHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = app_module.SceneApp()
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), app_module.handler_for(cls.app))
        cls.thread = Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)

    def setUp(self):
        self.app.scene = InhabitedScene()

    def get(self, path):
        return json.loads(urlopen(self.base + path, timeout=10).read())

    def post(self, operation, args=None, headers=None):
        request = Request(self.base + '/api/act', json.dumps({'operation': operation, 'args': args or {}}).encode(),
                          headers={'Content-Type': 'application/json', **(headers or {})})
        return json.loads(urlopen(request, timeout=10).read())

    def test_read_only_endpoints(self):
        before = self.get('/api/export')
        self.get('/api/state')
        self.assertEqual(before, self.get('/api/export'))

    def test_valid_action_and_replay(self):
        event = self.post('scan')['event']
        self.assertEqual(event['operation'], 'scan')
        self.assertTrue(self.get('/api/state')['state']['caravan']['noticed'])
        payload = self.get('/api/export')
        self.assertEqual(InhabitedScene.restore(payload).state(), payload['expected_state'])

    def test_rejects_foreign_origin_without_mutation(self):
        before = self.get('/api/export')
        with self.assertRaises(HTTPError) as caught:
            self.post('scan', headers={'Origin': 'https://hostile.example'})
        self.assertEqual(caught.exception.code, 403)
        self.assertEqual(before, self.get('/api/export'))

    def test_bad_json_rejected_without_mutation(self):
        before = self.get('/api/export')
        request = Request(self.base+'/api/act', b'{broken',
                          headers={'Content-Type':'application/json'})
        with self.assertRaises(HTTPError) as caught:
            urlopen(request, timeout=10)
        self.assertEqual(caught.exception.code, 400)
        self.assertEqual(self.get('/api/export'), before)


if __name__ == '__main__':
    unittest.main()
