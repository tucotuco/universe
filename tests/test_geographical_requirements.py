"""Continuous terrain, staged geographical realization and local designer API."""
from copy import deepcopy
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import json
import math
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'examples'))
from geographical_requirements import GeographicalDesign, TerrainProposal
from geographical_designer import GeographyApp, make_handler


class GeographyTests(unittest.TestCase):
    def setUp(self):
        self.design = GeographicalDesign(**json.loads(
            (ROOT/'examples/geographical_region.json').read_text()))

    def test_coarse_estimate_unresolved_until_refined(self):
        before = self.design.dumps()
        result = self.design.inspect(3, -1)
        self.assertFalse(result['resolved'])
        self.assertIsNone(result['elevation_m'])
        self.assertEqual(result['missing'], ['terrain_tile:1,0'])
        self.assertEqual(before, self.design.dumps())

    def test_boundary_and_river_are_already_established(self):
        for x, y in [(0, 0), (8, 0), (2, -1), (3, 0), (4, 2), (5, self.design.river_y(5))]:
            self.assertTrue(self.design.inspect(x, y)['resolved'])

    def test_river_source_and_outlet(self):
        self.assertEqual(self.design.river_bed(0), 1400)
        self.assertEqual(self.design.river_bed(8), 0)
        for x in [0, 1, 3, 4, 5.5, 8]:
            self.assertAlmostEqual(self.design.elevation(x, self.design.river_y(x)),
                                   self.design.river_bed(x), places=9)

    def test_river_stays_strictly_downhill_for_either_refinement(self):
        self.design.commit(self.design.preview((1, 0), 0))
        self.design.commit(self.design.preview((2, 1), 4))
        beds = [p['bed_m'] for p in self.design.river_profile(129)]
        self.assertTrue(all(a > b for a, b in zip(beds, beds[1:])))
        self.assertAlmostEqual(self.design.elevation(3, self.design.river_y(3)),
                               self.design.river_bed(3))

    def test_preview_does_not_commit_or_change_state(self):
        before = self.design.dumps()
        p = self.design.preview((1, 0), 7)
        self.assertNotEqual(self.design.elevation(3, -1), self.design.elevation(3, -1, p))
        self.assertEqual(self.design.dumps(), before)

    def test_deterministic_previews_with_distinct_candidates(self):
        self.assertEqual(self.design.preview((1, 0), 5), self.design.preview((1, 0), 5))
        self.assertNotEqual(self.design.preview((1, 0), 5).amplitude_m,
                            self.design.preview((1, 0), 6).amplitude_m)

    def test_commit_fixes_one_tile_without_materializing_neighbours(self):
        p = self.design.preview((1, 0), 3)
        self.design.commit(p)
        self.assertEqual(self.design.inspect(3, -1)['elevation_m'],
                         self.design.elevation(3, -1, p))
        self.assertFalse(self.design.inspect(5, -1)['resolved'])
        self.assertEqual(len(self.design.state()['committed_tiles']), 1)

    def test_out_of_order_discoveries_do_not_change_prior_tile(self):
        self.design.commit(self.design.preview((1, 0), 2))
        known = self.design.elevation(3, -1)
        self.design.commit(self.design.preview((2, 0), 5))
        self.assertEqual(self.design.elevation(3, -1), known)
        self.assertFalse(self.design.inspect(1, 1)['resolved'])

    def test_continuity_at_all_shared_tile_edges(self):
        for tile in [(0, 0), (1, 0), (1, 1), (2, 0), (3, 1)]:
            self.design.commit(self.design.preview(tile))
        for x in (2, 4, 6):
            for y in (-1.7, -0.6, 0.7, 1.6):
                exact = self.design.elevation(x, y)
                self.assertAlmostEqual(self.design.elevation(x-1e-7, y), exact, delta=1e-4)
                self.assertAlmostEqual(self.design.elevation(x+1e-7, y), exact, delta=1e-4)
        for x in (0.3, 2.7, 4.3, 7.2):
            exact = self.design.elevation(x, 0)
            self.assertAlmostEqual(self.design.elevation(x, -1e-7), exact, delta=1e-4)
            self.assertAlmostEqual(self.design.elevation(x, 1e-7), exact, delta=1e-4)

    def test_conditions_limit_feasible_amplitudes(self):
        x, y = 3, -1
        target = self.design.baseline(x, y) + 10 * self.design._shape(x, y, (1,0))
        self.design.add_condition({'x_km':x,'y_km':y,'target_m':target,'tolerance_m':0.01})
        p = self.design.preview((1,0),3)
        self.assertAlmostEqual(self.design.elevation(x,y,p), target, delta=.01)
        self.design.commit(p)
        self.assertAlmostEqual(self.design.elevation(x,y), target, delta=.01)

    def test_impossible_condition_rejected_atomically(self):
        before = self.design.dumps()
        with self.assertRaisesRegex(ValueError, 'fixed geographic geometry'):
            self.design.add_condition({'x_km':8,'y_km':0,'target_m':20,'tolerance_m':0})
        self.assertEqual(before, self.design.dumps())

    def test_conflicting_conditions_rejected(self):
        z = self.design.baseline(3,-1)
        self.design.add_condition({'x_km':3,'y_km':-1,'target_m':z+2,'tolerance_m':.01})
        before = self.design.dumps()
        with self.assertRaisesRegex(ValueError, 'no admissible refinement'):
            self.design.add_condition({'x_km':3,'y_km':-1,'target_m':z-2,'tolerance_m':.01})
        self.assertEqual(before, self.design.dumps())

    def test_impossible_amplitude_rejected(self):
        with self.assertRaisesRegex(ValueError, 'contradicts geographic conditions'):
            self.design.preview((1,0),amplitude_m=1000)

    def test_stale_proposal_rejected_without_mutation(self):
        p = self.design.preview((1,0))
        z=self.design.baseline(1,-1)
        self.design.add_condition({'x_km':1,'y_km':-1,'target_m':z,'tolerance_m':0})
        before = self.design.dumps()
        with self.assertRaisesRegex(ValueError, 'Stale'):
            self.design.commit(p)
        self.assertEqual(self.design.dumps(),before)

    def test_unknown_tile_invalid_and_no_mutation(self):
        before = self.design.dumps()
        with self.assertRaisesRegex(ValueError, 'outside'):
            self.design.preview((9,0))
        with self.assertRaisesRegex(ValueError, 'outside'):
            self.design.inspect(-1,0)
        self.assertEqual(before,self.design.dumps())

    def test_committed_tile_does_not_change_when_condition_added(self):
        self.design.commit(self.design.preview((1,0)))
        before = self.design.dumps()
        with self.assertRaisesRegex(ValueError,'committed'):
            self.design.add_condition({'x_km':3,'y_km':-1,'target_m':-999,'tolerance_m':0})
        self.assertEqual(self.design.dumps(),before)

    def test_export_restore_preserves_history_and_rejects_tampering(self):
        self.design.commit(self.design.preview((1,0),2))
        z=self.design.elevation(3,-1)
        self.design.add_condition({'x_km':3,'y_km':-1,'target_m':z,'tolerance_m':.001})
        self.design.commit(self.design.preview((2,1),4))
        blob=self.design.dumps()
        restored=GeographicalDesign.loads(blob)
        self.assertEqual(restored.dumps(), blob)
        altered=json.loads(blob)
        altered['commits'][0]['amplitude_m'] += 5
        with self.assertRaisesRegex(ValueError,'journal'):
            GeographicalDesign.restore(altered)

    def test_map_preview_does_not_change_existing_tile(self):
        self.design.commit(self.design.preview((1,0)))
        before=self.design.elevation(3,-1)
        p=self.design.preview((2,0))
        mapview=self.design.map_data(p)
        self.assertEqual(mapview['preview_tile'],[2,0])
        self.assertEqual(len(mapview['heights_m']),33)
        self.assertEqual(self.design.elevation(3,-1),before)

    def test_demand_is_local_rather_than_full_world(self):
        x,y=3,-1
        req=self.design.inspect(x,y)
        self.assertEqual(req['missing'],['terrain_tile:1,0'])
        self.design.commit(self.design.preview(req['tile']))
        self.assertEqual(self.design.inspect(x,y)['missing'],[])
        self.assertEqual(len(self.design.state()['committed_tiles']),1)


class GeographyHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=GeographyApp(GeographicalDesign())
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(cls.app))
        cls.thread=Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()
        cls.base=f'http://127.0.0.1:{cls.server.server_address[1]}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(2)

    def post(self, path, value, origin=None):
        headers={'Content-Type':'application/json'}
        if origin:
            headers['Origin']=origin
        req=Request(self.base+path, data=json.dumps(value).encode(), headers=headers)
        with urlopen(req,timeout=3) as response:
            return json.load(response)

    def test_preview_commit_and_stale_boundary(self):
        initial=json.load(urlopen(self.base+'/api/state',timeout=3))
        p=self.post('/api/preview',{'tile':[1,0]})
        self.assertEqual(json.load(urlopen(self.base+'/api/state',timeout=3)),initial)
        self.assertEqual(p['map']['preview_tile'],[1,0])
        c=self.post('/api/commit',{})
        self.assertIn([1,0],c['world']['committed_tiles'])

    def test_cross_origin_write_rejected(self):
        req=Request(self.base+'/api/preview',data=b'{"tile":[0,0]}',headers={
            'Origin':'https://untrusted.example','Content-Type':'application/json'})
        with self.assertRaises(HTTPError) as context:
            urlopen(req,timeout=3)
        self.assertEqual(context.exception.code,403)

    def test_html_contains_map_and_preview_controls(self):
        html=urlopen(self.base+'/',timeout=3).read().decode()
        for word in ['id="terrain"','id="profile"','id="preview"','id="commit"',
                     'id="conditions"','id="export"']:
            self.assertIn(word,html)


if __name__=='__main__':
    unittest.main()
