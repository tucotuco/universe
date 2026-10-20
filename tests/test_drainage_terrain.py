"""Consistency of continuous terrain conditioned on committed river topology."""
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

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'examples')]
from geographical_watershed import WatershedDesign
from geographical_drainage_terrain import DrainageTerrainDesign,ReliefProposal
from terrain_from_watershed import sample_world,DrainageTerrainApp,make_handler


class TerrainFromDrainageTests(unittest.TestCase):
    def setUp(self):
        self.world=sample_world()

    def test_main_river_required(self):
        with self.assertRaisesRegex(ValueError,'main river'):
            DrainageTerrainDesign(WatershedDesign())

    def test_existing_watershed_unchanged_and_all_channels_present(self):
        network=self.world.watershed.network()
        self.assertEqual(set(network['channels']),{'main','north','south'})
        self.assertEqual(self.world.watershed.inspect('whole_network')['missing'],[])

    def test_terrain_exactly_meets_every_channel_and_junction(self):
        for branch,points in self.world.watershed._channels.items():
            for a,b in zip(points,points[1:]):
                for t in (0,.125,.5,.75,1):
                    x,y,z=[a[j]+t*(b[j]-a[j]) for j in range(3)]
                    self.assertAlmostEqual(self.world.elevation(x,y),z,places=5,msg=(branch,x,y))
        for tile in [(i,j) for i in range(4) for j in range(2)]:
            self.world.commit(self.world.preview(tile,4))
        for points in self.world.watershed._channels.values():
            for x,y,z in points:
                self.assertAlmostEqual(self.world.elevation(x,y),z,places=5)

    def test_unrealized_elevation_is_range_not_false_committed_fact(self):
        before=self.world.dumps()
        answer=self.world.inspect(1,1)
        self.assertFalse(answer['realized'])
        self.assertIn('possible_elevation_m',answer)
        self.assertLess(answer['possible_elevation_m'][0],answer['possible_elevation_m'][1])
        self.assertNotIn('elevation_m',answer)
        self.assertEqual(before,self.world.dumps())

    def test_preview_no_effect_repeatable_and_multiple_candidates(self):
        before=self.world.dumps()
        a=self.world.preview((0,0),0)
        b=self.world.preview((0,0),1)
        self.assertEqual(a,self.world.preview((0,0),0))
        self.assertNotEqual(a,b)
        self.assertEqual(before,self.world.dumps())
        x,y=.8,-.7
        self.assertNotAlmostEqual(self.world.elevation(x,y,a),self.world.elevation(x,y,b),places=7)

    def test_committed_tile_preserves_neighbor_and_shared_edges(self):
        samples=[(2.0,y) for y in (-1.95,-1.5,-.1,.3,1.5)]
        baseline=[self.world.elevation(x,y) for x,y in samples]
        distant=self.world.elevation(3,-1)
        p=self.world.preview((0,0),1)
        interior=self.world.elevation(1,-1,p)
        self.world.commit(p)
        self.assertAlmostEqual(interior,self.world.elevation(1,-1),places=9)
        self.assertEqual([self.world.elevation(x,y) for x,y in samples],baseline)
        self.assertEqual(self.world.elevation(3,-1),distant)
        for x,y in ((2,-1),(1,0),(1,-2),(0,-1)):
            self.assertAlmostEqual(self.world.elevation(x,y),self.world._height_at_strength(x,y,.08))

    def test_refinement_order_independent_with_fixed_per_tile_candidates(self):
        a,b=sample_world(),sample_world()
        for tile in ((0,0),(3,1),(1,0)):
            a.commit(a.preview(tile,7))
        for tile in ((1,0),(0,0),(3,1)):
            b.commit(b.preview(tile,7))
        for x,y in ((1,-1),(3,-1),(7,1),(4,0),(3,0)):
            self.assertAlmostEqual(a.elevation(x,y),b.elevation(x,y))
        self.assertNotEqual(a.state()['events'],b.state()['events'])

    def test_downhill_witness_reaches_bay_monotonically(self):
        for x,y in ((1,1.25),(1,-1.5),(3,.8),(3,-.8),(6,1.25),(7,-1.2)):
            result=self.world.downhill_witness(x,y)
            points=result['points']
            self.assertEqual(tuple(points[-1]),self.world.watershed.BAY)
            self.assertGreater(len(points),10)
            self.assertTrue(all(a[2]>=b[2]-1e-6 for a,b in zip(points,points[1:])),(x,y))

    def test_downhill_path_remains_monotonic_after_tile_commit(self):
        for tile in ((i,j) for i in range(4) for j in range(2)):
            self.world.commit(self.world.preview(tile,5))
        for x,y in ((1,1),(1,-1),(3,1),(5,-1),(7,1)):
            route=self.world.downhill_witness(x,y)
            self.assertFalse(route['provisional'])
            self.assertTrue(all(a[2]>=b[2]-1e-6 for a,b in zip(route['points'],route['points'][1:])))

    def test_conditions_restrict_preview_without_realizing_tile(self):
        x,y=1,-1
        example=self.world.preview((0,0),8)
        target=self.world.elevation(x,y,example)
        self.world.add_condition({'x_km':x,'y_km':y,'elevation_m':target,'tolerance_m':.05})
        before=self.world.dumps()
        self.assertFalse(self.world.inspect(x,y)['realized'])
        candidate=self.world.preview((0,0),3)
        self.assertLessEqual(abs(self.world.elevation(x,y,candidate)-target),.0500001)
        self.assertEqual(before,self.world.dumps())

    def test_impossible_condition_rejected_atomically(self):
        before=self.world.dumps()
        lo=self.world.inspect(1,-1)['possible_elevation_m'][0]
        with self.assertRaisesRegex(ValueError,'incompatible'):
            self.world.add_condition({'x_km':1,'y_km':-1,'elevation_m':lo-400,'tolerance_m':0})
        self.assertEqual(before,self.world.dumps())

    def test_conflicting_conditions_rejected_atomically(self):
        x,y=1,-1
        low,high=self.world.inspect(x,y)['possible_elevation_m']
        self.world.add_condition({'x_km':x,'y_km':y,'elevation_m':low,'tolerance_m':.01})
        before=self.world.dumps()
        with self.assertRaisesRegex(ValueError,'Contradictory'):
            self.world.add_condition({'x_km':x,'y_km':y,'elevation_m':high,'tolerance_m':.01})
        self.assertEqual(before,self.world.dumps())

    def test_existing_tile_cannot_be_rewritten_by_condition(self):
        self.world.commit(self.world.preview((0,0),1))
        before=self.world.dumps()
        z=self.world.elevation(1,-1)
        with self.assertRaises(ValueError):
            self.world.add_condition({'x_km':1,'y_km':-1,'elevation_m':z+100,'tolerance_m':0})
        self.assertEqual(before,self.world.dumps())

    def test_stale_and_tampered_preview_rejected(self):
        p=self.world.preview((0,0),1)
        self.world.add_condition({'x_km':1,'y_km':-1,'elevation_m':self.world.elevation(1,-1,p),'tolerance_m':1})
        before=self.world.dumps()
        with self.assertRaisesRegex(ValueError,'Stale'):
            self.world.commit(p)
        p2=self.world.preview((0,0),1)
        with self.assertRaisesRegex(ValueError,'does not match'):
            self.world.commit(ReliefProposal(p2.tile,.8,p2.candidate_index,p2.revision))
        self.assertEqual(before,self.world.dumps())

    def test_existing_network_snapshot_cannot_change(self):
        before=self.world.dumps()
        self.world.watershed.add_condition({'x_km':2,'y_km':self.world.watershed._at_x(
            self.world.watershed._channels['main'],2)[1],'tolerance_km':.05})
        with self.assertRaisesRegex(ValueError,'changed'):
            self.world.inspect(1,-1)
        with self.assertRaisesRegex(ValueError,'changed'):
            self.world.preview((0,0))
        # Source watershed did not change; this mutation was inside frozen copy.
        self.assertNotIn('tolerance_km',before)

    def test_save_replay_journal_integrity_and_order(self):
        for tile in ((3,0),(1,1)):
            self.world.commit(self.world.preview(tile,2))
        x,y=.6,.6
        self.world.add_condition({'x_km':x,'y_km':y,'elevation_m':self.world.inspect(x,y)['possible_elevation_m'][0]+5,'tolerance_m':10})
        saved=self.world.dumps()
        self.assertEqual(DrainageTerrainDesign.loads(saved).dumps(),saved)
        tampered=json.loads(saved)
        tampered['events'][0]['strength']+=.01
        with self.assertRaises(ValueError):
            DrainageTerrainDesign.restore(tampered)
        tampered=json.loads(saved)
        tampered['committed'][0]['strength']+=.01
        with self.assertRaises(ValueError):
            DrainageTerrainDesign.restore(tampered)

    def test_bad_coordinates_and_tile_rejected(self):
        for x,y in ((-1,0),(9,0),(0,9),(float('nan'),0)):
            with self.assertRaises(ValueError):
                self.world.inspect(x,y)
        for tile in ((-1,0),(4,0),(0,2),('1',0)):
            with self.assertRaises(ValueError):
                self.world.preview(tile)

    def test_mesh_dimensions_and_river_overlay(self):
        mesh=self.world.mesh(0.5)
        self.assertEqual(len(mesh['heights_m']),9)
        self.assertEqual(len(mesh['heights_m'][0]),17)
        self.assertEqual(set(mesh['channels']),{'main','north','south'})


class TerrainServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=DrainageTerrainApp(sample_world())
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(cls.app))
        cls.thread=Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()
        cls.base=f'http://127.0.0.1:{cls.server.server_address[1]}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)

    def post(self,path,payload,headers=None):
        request=Request(self.base+path,json.dumps(payload).encode(),headers={'Content-Type':'application/json',**(headers or {})})
        return json.loads(urlopen(request,timeout=5).read())

    def test_server_inspect_does_not_realize_terrain(self):
        before=json.loads(urlopen(self.base+'/api/state',timeout=5).read())
        answer=self.post('/api/inspect',{'x_km':1,'y_km':1})
        self.assertFalse(answer['realized'])
        after=json.loads(urlopen(self.base+'/api/state',timeout=5).read())
        self.assertEqual(before,after)

    def test_http_preview_and_commit(self):
        preview=self.post('/api/preview',{'tile':[2,0],'candidate_index':2})
        self.assertEqual(preview['proposal']['tile'],[2,0])
        answer=self.post('/api/commit',{})
        self.assertEqual(answer['committed']['tile'],[2,0])
        self.assertEqual(len(answer['mesh']['realized_tiles']),1)

    def test_cross_origin_rejected_without_mutation(self):
        before=json.loads(urlopen(self.base+'/api/state',timeout=5).read())
        request=Request(self.base+'/api/commit',b'{}',headers={'Origin':'https://another-site.invalid','Content-Type':'application/json'})
        with self.assertRaises(HTTPError) as caught:
            urlopen(request,timeout=5)
        self.assertEqual(caught.exception.code,403)
        self.assertEqual(before,json.loads(urlopen(self.base+'/api/state',timeout=5).read()))


if __name__=='__main__':unittest.main()
