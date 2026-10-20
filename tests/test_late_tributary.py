"""Late topological refinement against already partially committed terrain."""
from dataclasses import replace
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
from geographical_late_tributary import LateTributaryDesign
from late_tributary_designer import TributaryApp, make_handler, sample_world


class LateTributaryTests(unittest.TestCase):
    def setUp(self):
        self.world = sample_world()

    def test_initial_state_has_partly_realized_terrain_but_no_late_river(self):
        state = self.world.state()
        self.assertEqual(len(state['terrain']['committed']), 2)
        self.assertIsNone(state['late_tributary'])
        self.assertNotIn('late', self.world.mesh()['channels'])

    def test_preview_is_read_only_reproducible_and_supports_alternatives(self):
        before = self.world.dumps()
        a = self.world.preview(1, -1, 2)
        self.assertEqual(a, self.world.preview(1, -1, 2))
        b = self.world.preview(1, -1, 8)
        self.assertNotEqual(a, b)
        self.assertEqual(self.world.dumps(), before)
        self.assertNotIn('late', self.world.mesh()['channels'])
        self.assertIn('late', self.world.mesh(proposal=a)['channels'])
        self.assertEqual(before, self.world.dumps())

    def test_exact_line_tile_coverage_does_not_skip_narrow_crossings(self):
        # Two grid crossings only 0.0000001 in parameter apart, midway
        # between adjacent old 1/128 sampling positions.
        a = (1.0, -1.0)
        b = (1.0+1.0/.501, -1.0+1.0/.5010001)
        tiles = LateTributaryDesign._line_tiles(self.world.terrain, a, b)
        self.assertEqual(tiles, {(0,0), (1,0), (1,1)})

    def test_commits_only_needed_tile_with_branch_atomically(self):
        old = self.world.terrain
        old_realized = {tuple(record['tile']) for record in old.state()['committed']}
        old_heights = {(x, y): old.elevation(x, y) for x, y in
                       ((3, -1), (3, -0.7), (5, 1), (4, 0), (6, 1), (7, 1))}
        old_channels = old.watershed.network()['channels']
        proposal = self.world.preview(1, -1, 2)
        self.assertEqual(proposal.resolved_tiles, ((0, 0),))
        result = self.world.commit(proposal)
        self.assertEqual(result['target_branch'], proposal.target_branch)
        new_realized = {tuple(record['tile']) for record in self.world.terrain.state()['committed']}
        self.assertEqual(new_realized-old_realized, {(0, 0)})
        self.assertEqual(self.world.terrain.watershed.network()['channels'], old_channels)
        for (x, y), height in old_heights.items():
            self.assertAlmostEqual(self.world.terrain.elevation(x, y), height, places=8)
        for x, y, z in proposal.points:
            self.assertAlmostEqual(self.world.terrain.elevation(x, y), z, places=7)
        self.assertEqual(self.world.revision, 1)

    def test_already_committed_tile_adds_only_river(self):
        proposal = self.world.preview(3, -1, 0)
        self.assertEqual(proposal.resolved_tiles, ())
        before = self.world.terrain.dumps()
        self.world.commit(proposal)
        self.assertEqual(self.world.terrain.dumps(), before)

    def test_proposed_course_descends_to_shared_graph_confluence(self):
        proposal = self.world.preview(3, -1, 0)
        self.assertTrue(all(a[2] >= b[2]-1e-6 for a, b in zip(proposal.points, proposal.points[1:])))
        graph = self.world.graph(proposal)
        node = {e['id']: e['position'] for e in graph['nodes']}
        self.assertEqual(len(node), len(graph['nodes']))
        junction = [key for key, location in node.items() if location == list(proposal.points[-1])]
        self.assertTrue(junction)
        edges = graph['edges']
        self.assertEqual(len(edges), len(graph['nodes']) - 1)
        next_hop = {}
        for e in edges:
            self.assertNotIn(e['from'], next_hop)
            next_hop[e['from']] = e['to']
        cursor = 'late:0'
        visited = set()
        while cursor != graph['outlet_id']:
            self.assertNotIn(cursor, visited)
            visited.add(cursor)
            cursor = next_hop[cursor]
        self.assertGreater(len(visited), len(proposal.points))

    def test_future_refinement_of_other_tiles_does_not_change_late_channel(self):
        p = self.world.preview(3, -1, 0)
        self.world.commit(p)
        before = [self.world.terrain.elevation(x, y) for x, y, _ in p.points]
        self.world.terrain.commit(self.world.terrain.preview((0, 1), 12))
        # Out-of-band modifications must be rejected by the wrapper, rather
        # than silently accepted as a change to its committed history.
        with self.assertRaisesRegex(ValueError, 'outside'):
            self.world.state()
        # The geometry itself remains unchanged, even before reconciliation.
        self.assertEqual(before, [self.world.terrain.elevation(x, y) for x, y, _ in p.points])

    def test_continuous_channel_bed_agrees_with_terrain_between_samples(self):
        proposal = self.world.preview(1, -1, 2)
        samples = [self.world.channel_at(f, proposal) for f in (0.003, 0.1723, 0.651, 0.997)]
        self.world.commit(proposal)
        for expected, fraction in zip(samples, (0.003, 0.1723, 0.651, 0.997)):
            self.assertEqual(expected, self.world.channel_at(fraction))
            self.assertAlmostEqual(expected[2], self.world.terrain.elevation(*expected[:2]), places=7)
        with self.assertRaises(ValueError):
            self.world.channel_at(1.1)

    def test_invalid_or_impossible_source_does_not_change_world(self):
        before = self.world.dumps()
        for x, y in [(-1, 0), (9, 0), (3, 8), (4, 0)]:
            with self.assertRaises(ValueError):
                self.world.preview(x, y, 0)
        with self.assertRaises(ValueError):
            self.world.preview(3, -1, -1)
        self.assertEqual(before, self.world.dumps())

    def test_tampered_proposal_rejected_without_mutation(self):
        p = self.world.preview(3, -1, 0)
        before = self.world.dumps()
        forged = replace(p, target_branch='main')
        with self.assertRaisesRegex(ValueError, 'disagrees'):
            self.world.commit(forged)
        self.assertEqual(before, self.world.dumps())

    def test_add_two_late_tributaries_preserving_old_elevations(self):
        baseline = self.world.terrain.dumps()
        original_channels = self.world.terrain.watershed.network()['channels']
        old_sample = self.world.terrain.elevation(3, -1)
        first = self.world.preview(1, -1, 2)
        self.world.commit(first)
        first_heights = [self.world.channel_at(f) for f in (0.01, .43, .95)]
        old_tile_values = dict(self.world.terrain._committed)
        second = self.world.preview(3, -1, 0)
        self.assertEqual(self.world.revision, 1)
        self.world.commit(second)
        self.assertEqual(self.world.revision, 2)
        self.assertEqual(len(self.world.state()['late_tributaries']), 2)
        self.assertEqual(len(self.world.state()['events']), 2)
        self.assertEqual(self.world.terrain.watershed.network()['channels'], original_channels)
        self.assertEqual(self.world.terrain.elevation(3, -1), old_sample)
        for tile, strength in old_tile_values.items():
            self.assertEqual(self.world.terrain._committed[tile], strength)
        self.assertEqual(first_heights, [self.world.channel_at(f) for f in (.01, .43, .95)])
        for x, y, z in second.points:
            self.assertAlmostEqual(self.world.terrain.elevation(x, y), z, places=7)
        self.assertIn('late', self.world.mesh()['channels'])
        self.assertIn('late2', self.world.mesh()['channels'])
        self.assertNotEqual(baseline, self.world.terrain.dumps())

    def test_order_independence_of_disjoint_late_discoveries(self):
        choices = ((1, -1, 2), (3, -1, 0))
        def build(order):
            world = sample_world()
            courses = {}
            for source in order:
                proposal = world.preview(*source)
                courses[source] = proposal.points
                world.commit(proposal)
            return world, courses
        left, a = build(choices)
        right, b = build(tuple(reversed(choices)))
        self.assertEqual(a, b)
        # The journal and channel labels encode discovery order, not physical difference.
        self.assertNotEqual(left.state()['events'], right.state()['events'])
        for x, y in ((.5, -1), (1, -1), (3, -1), (5, 1), (7, -1)):
            self.assertAlmostEqual(left.terrain.elevation(x,y), right.terrain.elevation(x,y))
        self.assertEqual(left.terrain.state()['committed'], right.terrain.state()['committed'])
        for graph in (left.graph(), right.graph()):
            self.assertEqual(len(graph['edges']), len(graph['nodes'])-1)
            downstream = {edge['from']: edge['to'] for edge in graph['edges']}
            self.assertEqual(len(downstream), len(graph['edges']))
            for root in ('late:0', 'late2:0'):
                seen, cursor = set(), root
                while cursor != graph['outlet_id']:
                    self.assertNotIn(cursor, seen)
                    seen.add(cursor)
                    cursor = downstream[cursor]

    def test_disallowed_crossing_and_duplicate_source_are_atomic(self):
        first = self.world.preview(3, -1, 0)
        self.world.commit(first)
        before = self.world.dumps()
        with self.assertRaisesRegex(ValueError, 'crosses or approaches'):
            self.world.preview(3, -1, 0)
        # A source almost on the previously established channel must also be
        # rejected; coordinate rounding must not mask the contact.
        midpoint = first.points[len(first.points)//2]
        with self.assertRaisesRegex(ValueError, 'crosses or approaches'):
            self.world.preview(midpoint[0], midpoint[1], 0)
        self.assertEqual(before, self.world.dumps())

    def test_two_mouths_on_the_same_original_edge_in_either_order(self):
        sources = ((3, -.8, 0), (3.5, -1.65, 0))
        for sequence in (sources, tuple(reversed(sources))):
            world = sample_world()
            proposals = []
            for source in sequence:
                proposal = world.preview(*source)
                self.assertEqual(proposal.target_branch, 'south')
                world.commit(proposal)
                proposals.append(proposal)
            self.assertNotEqual(proposals[0].points[-1], proposals[1].points[-1])
            graph = world.graph()
            self.assertEqual(len(graph['edges']), len(graph['nodes'])-1)
            mouths = [node['position'] for node in graph['nodes'] if node['id'].endswith(':confluence')]
            self.assertEqual(len(mouths), 2)
            for branch in proposals:
                self.assertIn(list(branch.points[-1]), mouths)

    def test_stale_second_proposal_rejected(self):
        stale = self.world.preview(3, -1, 0)
        self.world.commit(self.world.preview(1, -1, 2))
        before = self.world.dumps()
        with self.assertRaisesRegex(ValueError, 'Stale'):
            self.world.commit(stale)
        self.assertEqual(before, self.world.dumps())

    def test_restore_legacy_version_one_export(self):
        self.world.commit(self.world.preview(3, -1, 0))
        old_state = self.world.state()
        old_state['version'] = 1
        del old_state['late_tributaries']
        upgraded = LateTributaryDesign.restore(old_state)
        self.assertEqual(upgraded.dumps(), self.world.dumps())
        upgraded.commit(upgraded.preview(1, -1, 2))
        self.assertEqual(len(upgraded.state()['late_tributaries']), 2)

    def test_export_restore_exact_and_revalidate(self):
        self.world.commit(self.world.preview(1, -1, 8))
        text = self.world.dumps()
        restored = LateTributaryDesign.loads(text)
        self.assertEqual(text, restored.dumps())
        self.assertEqual(self.world.graph(), restored.graph())
        tampered = json.loads(text)
        tampered['events'][0]['points'][0][2] += 1.0
        with self.assertRaises(ValueError):
            LateTributaryDesign.restore(tampered)
        tampered = json.loads(text)
        tampered['terrain']['committed'][0]['strength'] += 0.03
        with self.assertRaises(ValueError):
            LateTributaryDesign.restore(tampered)

    def test_existing_committed_terrain_is_not_mutated_at_all_by_preview(self):
        before = self.world.terrain.dumps()
        proposal = self.world.preview(5.4, 1.2, 2)
        self.assertTrue(proposal.resolved_tiles)
        self.world.graph(proposal)
        self.world.mesh(proposal=proposal)
        self.assertEqual(self.world.terrain.dumps(), before)


class LateTributaryServerTests(unittest.TestCase):
    def setUp(self):
        self.app.world = sample_world()
        self.app.pending = None

    @classmethod
    def setUpClass(cls):
        cls.app = TributaryApp(sample_world())
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), make_handler(cls.app))
        cls.thread = Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f'http://127.0.0.1:{cls.server.server_address[1]}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)

    def post(self, path, data, headers=None):
        request = Request(self.base + path, json.dumps(data).encode(),
                          headers={'Content-Type': 'application/json', **(headers or {})})
        return json.loads(urlopen(request, timeout=5).read())

    def test_server_preview_and_inspect_are_noncommitting(self):
        before = json.loads(urlopen(self.base+'/api/state', timeout=5).read())
        self.post('/api/inspect', {'x_km': 1, 'y_km': -1})
        candidate = self.post('/api/preview', {'x_km': 1, 'y_km': -1, 'candidate_index': 2})
        self.assertTrue(candidate['proposal']['resolved_tiles'])
        self.assertIn('late', candidate['mesh']['channels'])
        self.assertEqual(before, json.loads(urlopen(self.base+'/api/state', timeout=5).read()))

    def test_server_commit_updates_state(self):
        self.post('/api/preview', {'x_km': 1, 'y_km': -1, 'candidate_index': 2})
        outcome = self.post('/api/commit', {})
        self.assertEqual(outcome['committed']['source'], [1.0, -1.0])
        self.assertIn('late', outcome['mesh']['channels'])
        self.assertTrue(json.loads(urlopen(self.base+'/api/state',timeout=5).read())['late_tributary'])

    def test_http_accepts_a_second_late_tributary(self):
        self.post('/api/preview', {'x_km': 1, 'y_km': -1, 'candidate_index': 2})
        self.post('/api/commit', {})
        self.post('/api/preview', {'x_km': 3, 'y_km': -1, 'candidate_index': 0})
        completed = self.post('/api/commit', {})
        self.assertIn('late2', completed['mesh']['channels'])
        self.assertEqual(len(completed['state']['late_tributaries']), 2)

    def test_cross_origin_mutation_forbidden(self):
        before = json.loads(urlopen(self.base+'/api/state', timeout=5).read())
        with self.assertRaises(HTTPError) as caught:
            self.post('/api/reset', {}, {'Origin': 'https://foreign.example'})
        self.assertEqual(caught.exception.code, 403)
        self.assertEqual(before, json.loads(urlopen(self.base+'/api/state', timeout=5).read()))


if __name__ == '__main__':
    unittest.main()
