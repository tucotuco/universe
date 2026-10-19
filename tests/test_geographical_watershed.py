"""River-network topology, selective realization, and browser API tests."""
from copy import deepcopy
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import json
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT/'examples'))
from geographical_watershed import WatershedDesign, ChannelProposal
from watershed_designer import WatershedApp, make_handler


class WatershedTests(unittest.TestCase):
    def setUp(self):
        self.world=WatershedDesign(**json.loads((ROOT/'examples/watershed_region.json').read_text()))

    def test_initial_anchors_without_automatic_channel_realization(self):
        before=self.world.dumps()
        response=self.world.inspect()
        self.assertEqual(response['missing'], ['main'])
        self.assertIsNone(response['answer'])
        self.assertEqual(self.world.network()['village'], [4,0,500])
        self.assertEqual(self.world.network()['bay'], [8,-.6,0])
        self.assertEqual(self.world.dumps(),before)

    def test_preview_does_not_commit_anything(self):
        before=self.world.dumps()
        proposal=self.world.preview('main',3)
        self.assertEqual(len(proposal.points),17)
        self.assertEqual(self.world.dumps(),before)
        self.assertIn('main',self.world.network(proposal)['channels'])
        self.assertNotIn('main',self.world.network()['channels'])

    def test_main_stem_source_village_outlet(self):
        proposal=self.world.preview('main',5)
        self.world.commit(proposal)
        main=self.world.network()['channels']['main']
        self.assertTrue(.35<=main[0][1]<=.95)
        self.assertEqual(main[0][2],1400)
        self.assertIn([4,0,500],main)
        self.assertEqual(main[-1],[8,-.6,0])
        self.assertTrue(self.world.inspect()['answered'])
        self.assertEqual(self.world.inspect('whole_network')['missing'], ['north','south'])

    def test_different_candidates_and_repeatability(self):
        a=self.world.preview('main',0)
        self.assertEqual(a,self.world.preview('main',0))
        self.assertNotEqual(a.points,self.world.preview('main',1).points)

    def test_main_bed_declines_at_all_stations(self):
        for i in range(6):
            p=self.world.preview('main',i)
            self.assertTrue(all(a[2]>b[2] for a,b in zip(p.points,p.points[1:])))
            self.assertTrue(all(b[0]>a[0] for a,b in zip(p.points,p.points[1:])))

    def test_crossing_condition_respects_exact_coordinate(self):
        c={'x_km':2.5,'y_km':.4,'tolerance_km':0}
        self.world.add_condition(c)
        p=self.world.preview('main',2)
        self.assertEqual(self.world._at_x(p.points,2.5)[1],.4)
        self.world.commit(p)
        self.assertEqual(self.world._at_x(self.world._channels['main'],2.5)[1],.4)

    def test_conditions_do_not_resolve_river(self):
        self.world.add_condition({'x_km':2,'y_km':.4,'tolerance_km':.1})
        self.assertFalse(self.world.inspect()['answered'])
        self.assertEqual(len(self.world.state()['channels']),0)

    def test_contradictory_crossings_rejected_atomically(self):
        self.world.add_condition({'x_km':2,'y_km':.4,'tolerance_km':.1})
        before=self.world.dumps()
        with self.assertRaisesRegex(ValueError,'Contradictory'):
            self.world.add_condition({'x_km':2,'y_km':-.4,'tolerance_km':.1})
        self.assertEqual(self.world.dumps(),before)

    def test_village_constraint_with_tolerance_cannot_displace_village(self):
        self.world.add_condition({'x_km':4,'y_km':0,'tolerance_km':.25})
        p=self.world.preview('main')
        self.assertEqual(self.world._at_x(p.points,4),self.world.VILLAGE)

    def test_invalid_crossings_do_not_change_world(self):
        before=self.world.dumps()
        for c in [{'x_km':9,'y_km':0,'tolerance_km':0},
                  {'x_km':2.1,'y_km':0,'tolerance_km':0},
                  {'x_km':4,'y_km':1,'tolerance_km':.1},
                  {'x_km':3,'y_km':float('nan'),'tolerance_km':0}]:
            with self.subTest(c=c),self.assertRaises(ValueError):
                self.world.add_condition(c)
        self.assertEqual(self.world.dumps(),before)

    def test_crossing_far_from_source_is_impossible_without_generating(self):
        before=self.world.dumps()
        with self.assertRaisesRegex(ValueError,'cannot connect'):
            self.world.add_condition({'x_km':.5,'y_km':-2,'tolerance_km':0})
        self.assertEqual(self.world.dumps(),before)

    def test_new_condition_cannot_rewrite_committed_route(self):
        self.world.commit(self.world.preview('main'))
        y=self.world._at_x(self.world._channels['main'],2)[1]
        before=self.world.dumps()
        with self.assertRaisesRegex(ValueError,'committed'):
            self.world.add_condition({'x_km':2,'y_km':y+1,'tolerance_km':0})
        self.assertEqual(self.world.dumps(),before)

    def test_old_preview_is_invalid_after_conditions_change(self):
        p=self.world.preview('main')
        self.world.add_condition({'x_km':2,'y_km':.4,'tolerance_km':.2})
        before=self.world.dumps()
        with self.assertRaisesRegex(ValueError,'Stale'):
            self.world.commit(p)
        self.assertEqual(self.world.dumps(),before)

    def test_cannot_realize_tributary_without_main_stem(self):
        for side in ('north','south'):
            with self.assertRaisesRegex(ValueError,'First realize'):
                self.world.preview(side)

    def test_tributaries_connect_only_at_confluences_and_flow_downhill(self):
        self.world.commit(self.world.preview('main'))
        for side in ('north','south'):
            p=self.world.preview(side)
            trunk=self.world._channels['main']
            confluence=self.world._at_x(trunk,p.points[-1][0])
            self.assertEqual(p.points[-1],confluence)
            self.assertTrue(all(a[2]>b[2] for a,b in zip(p.points,p.points[1:])))
            sign=1 if side=='north' else -1
            for x,y,z in p.points[:-1]:
                trunk_point=self.world._at_x(trunk,x)
                self.assertGreater((y-trunk_point[1])*sign,0)
                self.assertGreater(z,trunk_point[2])
            self.world.commit(p)
        self.assertTrue(self.world.inspect('whole_network')['answered'])

    def test_topology_has_shared_confluences_and_paths_to_bay(self):
        self.world.commit(self.world.preview('main'))
        self.world.commit(self.world.preview('north'))
        self.world.commit(self.world.preview('south'))
        graph=self.world.network()['graph']
        edges=graph['edges']
        nodes={n['id']:n['position'] for n in graph['nodes']}
        downstream={e['from']:e['to'] for e in edges}
        self.assertEqual(graph['outlet_id'],'main:16')
        self.assertEqual(len(nodes), len(set(nodes)))
        self.assertTrue(any(e['course']=='north' and e['to'].startswith('main:') for e in edges))
        self.assertTrue(any(e['course']=='south' and e['to'].startswith('main:') for e in edges))
        for start in ('main:0','north:0','south:0'):
            visited=set()
            current=start
            while current != graph['outlet_id']:
                self.assertNotIn(current, visited, 'A river loop would violate drainage')
                visited.add(current)
                next_node=downstream[current]
                self.assertGreater(nodes[next_node][0],nodes[current][0])
                self.assertGreater(nodes[current][2],nodes[next_node][2])
                current=next_node

    def test_tributary_order_preserves_existing_commitments(self):
        self.world.commit(self.world.preview('main',7))
        main=deepcopy(self.world._channels['main'])
        north=self.world.preview('north',2)
        self.world.commit(self.world.preview('south',3))
        # Old preview itself has a stale revision; a fresh preview must be
        # geometrically identical despite prior south-side realization.
        self.assertNotEqual(north.revision,self.world.revision)
        self.assertEqual(north.points,self.world.preview('north',2).points)
        self.world.commit(self.world.preview('north',2))
        self.assertEqual(self.world._channels['main'],main)
        self.assertTrue(self.world.inspect('whole_network')['answered'])

    def test_main_course_is_immutable_after_tributary_discovery(self):
        self.world.commit(self.world.preview('main'))
        before=self.world.inspect()['answer']
        self.world.commit(self.world.preview('north'))
        self.assertEqual(before,self.world.inspect()['answer'])
        with self.assertRaisesRegex(ValueError,'already committed'):
            self.world.preview('main')

    def test_bad_proposal_rejected_without_mutation(self):
        p=self.world.preview('main')
        wrong=ChannelProposal('main',p.candidate_index,p.revision,tuple(
            (v[0],v[1]+.2,v[2]) if index==5 else v for index,v in enumerate(p.points)))
        before=self.world.dumps()
        with self.assertRaisesRegex(ValueError,'does not match'):
            self.world.commit(wrong)
        self.assertEqual(before,self.world.dumps())

    def test_export_reload_preserves_commitment_order(self):
        self.world.add_condition({'x_km':2,'y_km':.3,'tolerance_km':.1})
        self.world.commit(self.world.preview('main',4))
        self.world.add_condition({'x_km':3,'y_km':self.world._at_x(self.world._channels['main'],3)[1],'tolerance_km':0})
        self.world.commit(self.world.preview('south',8))
        self.world.commit(self.world.preview('north',6))
        saved=self.world.dumps()
        self.assertEqual(WatershedDesign.loads(saved).dumps(),saved)

    def test_tampered_route_is_rejected(self):
        self.world.commit(self.world.preview('main',3))
        corrupted=self.world.state()
        corrupted['events'][0]['points'][4][1]+=.5
        with self.assertRaisesRegex(ValueError,'generation rules'):
            WatershedDesign.restore(corrupted)

    def test_tampered_summary_rejected(self):
        self.world.commit(self.world.preview('main'))
        corrupted=self.world.state()
        corrupted['channels']['main'][4][1]+=.5
        with self.assertRaisesRegex(ValueError,'journal'):
            WatershedDesign.restore(corrupted)


class WatershedHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=WatershedApp(WatershedDesign())
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(cls.app))
        cls.thread=Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()
        cls.base=f'http://127.0.0.1:{cls.server.server_address[1]}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join(2)

    def post(self,path,value):
        req=Request(self.base+path,data=json.dumps(value).encode('utf-8'),headers={'Content-Type':'application/json'})
        with urlopen(req,timeout=3) as response:
            return json.load(response)

    def test_preview_does_not_mutate_commit_changes_world(self):
        before=json.load(urlopen(self.base+'/api/state',timeout=3))
        res=self.post('/api/preview',{'branch':'main','candidate_index':2})
        self.assertEqual(json.load(urlopen(self.base+'/api/state',timeout=3)),before)
        self.assertEqual(res['network']['preview_branch'],'main')
        self.post('/api/commit',{})
        self.assertIn('main',json.load(urlopen(self.base+'/api/state',timeout=3))['channels'])

    def test_cross_origin_commands_rejected(self):
        req=Request(self.base+'/api/preview',data=b'{"branch":"north"}',headers={
            'Origin':'https://untrusted.example','Content-Type':'application/json'})
        with self.assertRaises(HTTPError) as error:
            urlopen(req,timeout=3)
        self.assertEqual(error.exception.code,403)

    def test_browser_template_contains_expected_controls(self):
        html=urlopen(self.base+'/',timeout=3).read().decode('utf-8')
        for token in ['id="map"','id="profile"','id="inspect"','id="preview"',
                      'id="commit"','id="condition"','id="export"']:
            self.assertIn(token,html)

if __name__=='__main__':unittest.main()
