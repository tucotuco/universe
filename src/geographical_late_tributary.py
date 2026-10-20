"""Conditionally add surface-flow tributaries to partly realized drainage terrain.

The existing continuous terrain equation and the original channel geometry are
immutable. A candidate tributary follows an actual downhill trace to an
established channel. Unresolved tiles crossed by that trace are realized *in
one transaction* so the new bed cannot change under later terrain refinement.

This is an intentionally bounded topological refinement, not stream incision,
hydraulic modeling, or dynamic geomorphology.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import math

from geographical_drainage_terrain import DrainageTerrainDesign


@dataclass(frozen=True)
class TributaryProposal:
    source: tuple[float, float]
    target_branch: str
    points: tuple[tuple[float, float, float], ...]
    resolved_tiles: tuple[tuple[int, int], ...]
    candidate_index: int
    revision: int

    def as_dict(self):
        return {'source': list(self.source), 'target_branch': self.target_branch,
                'points': [list(p) for p in self.points],
                'resolved_tiles': [list(t) for t in self.resolved_tiles],
                'candidate_index': self.candidate_index, 'revision': self.revision}


class LateTributaryDesign:
    """Bounded additive tributaries against a frozen terrain world.

    Each late tributary joins an original channel; joins between late branches
    and crossings between them require a later network-extension experiment.
    The original watershed and all committed terrain remain authoritative.
    """
    VERSION = 2
    SAMPLES = 32
    LATE_CLEARANCE_KM = 0.01  # Do not silently merge nearly touching late courses.

    def __init__(self, terrain: DrainageTerrainDesign):
        if not isinstance(terrain, DrainageTerrainDesign):
            raise ValueError('A drainage terrain world is required')
        self.terrain = DrainageTerrainDesign.loads(terrain.dumps())
        self._base = self.terrain.state()
        self._terrain_snapshot = self.terrain.dumps()
        self._branches = []
        self._events = []
        self.revision = 0

    def _verify(self):
        if self.terrain.dumps() != self._terrain_snapshot:
            raise ValueError('Terrain changed outside tributary commitment')

    @staticmethod
    def _line_tiles(terrain, source, foot):
        """Exact tile coverage of a straight corridor, even for tiny slivers.

        Check the midpoint of every interval separated by a tile boundary;
        fixed-grid sampling could miss a narrowly crossed tile.
        """
        split = {0.0, 1.0}
        for axis, boundaries in ((0, (2, 4, 6)), (1, (0,))):
            distance = foot[axis] - source[axis]
            if abs(distance) < 1e-12:
                continue
            for boundary in boundaries:
                t = (boundary-source[axis])/distance
                if 0 < t < 1:
                    split.add(t)
        cuts = sorted(split)
        checked = cuts + [(a+b)/2 for a,b in zip(cuts, cuts[1:])]
        return {terrain._tile(source[0]+t*(foot[0]-source[0]),
                              source[1]+t*(foot[1]-source[1])) for t in checked}

    def _trial(self, source, index):
        """Resolve only necessary tiles in a scratch world; no live mutations."""
        required = {self.terrain._tile(*source)}
        for _ in range(10):
            trial = DrainageTerrainDesign.loads(self.terrain.dumps())
            newly_committed = []
            for tile in sorted(required):
                if tile not in trial._committed:
                    candidate = trial.preview(tile, index)
                    trial.commit(candidate)
                    newly_committed.append(tile)
            _, branch, foot, distance = trial._surface(*source)
            if distance < 0.10:
                raise ValueError('Tributary source must be at least 0.1 km from an existing channel')
            needed = required | self._line_tiles(trial, source, foot)
            if needed == required:
                return trial, branch, foot, tuple(newly_committed)
            required = needed
        raise ValueError('Tributary corridor could not be resolved consistently')

    def preview(self, x_km, y_km, candidate_index=0):
        self._verify()
        if type(candidate_index) is not int or candidate_index < 0:
            raise ValueError('Candidate index must be a nonnegative integer')
        x, y = self.terrain._coords(x_km, y_km)
        source = (round(x, 6), round(y, 6))
        trial, branch, foot, tiles = self._trial(source, candidate_index)
        points = []
        for i in range(self.SAMPLES + 1):
            f = i / self.SAMPLES
            a = source[0]*(1-f)+foot[0]*f
            b = source[1]*(1-f)+foot[1]*f
            points.append((a, b, trial.elevation(a, b)))
        points[-1] = tuple(foot)
        if points[0][2] < points[-1][2] + 0.1:
            raise ValueError('Tributary source must lie above its confluence')
        if any(a[2] + 1e-6 < b[2] for a, b in zip(points, points[1:])):
            raise ValueError('No continuously descending path from that source to a channel')
        if any(trial._tile(a, b) not in trial._committed for a, b, _ in points):
            raise ValueError('Tributary depends on unresolved terrain')
        if abs(trial.elevation(*foot[:2]) - foot[2]) > 1e-5:
            raise ValueError('Confluence does not match the established channel bed')
        for earlier in self._branches:
            if self._segments_intersect(source, foot, earlier.source, earlier.points[-1]):
                raise ValueError('New tributary crosses or approaches an established late tributary; '
                                 'confluences between late branches are not supported')
        proposed = TributaryProposal(source, branch, tuple(points), tiles,
                                     candidate_index, self.revision)
        # Validate an unambiguous, connected graph *before* exposing an
        # apparently commit-ready candidate.
        self._graph_from(self._branches + [proposed])
        return proposed

    @classmethod
    def _segments_intersect(cls, a, b, c, d):
        """Reject crossings and near contacts (within 10 m) of late courses."""
        def cross(p, q, r):
            return ((q[0]-p[0])*(r[1]-p[1])
                    -(q[1]-p[1])*(r[0]-p[0]))

        def distance_to_segment(p, q, r):
            u,v = r[0]-q[0],r[1]-q[1]
            t = max(0.0,min(1.0, ((p[0]-q[0])*u+(p[1]-q[1])*v)/(u*u+v*v)))
            return math.hypot(p[0]-(q[0]+t*u),p[1]-(q[1]+t*v))

        if min(distance_to_segment(p,q,r) for p,q,r in
               ((a,c,d),(b,c,d),(c,a,b),(d,a,b))) <= cls.LATE_CLEARANCE_KM:
            return True
        # Proper interior crossing even when no endpoint lies near an edge.
        return cross(a,b,c)*cross(a,b,d) < 0 and cross(c,d,a)*cross(c,d,b) < 0

    @staticmethod
    def _channel_id(index):
        return 'late' if index == 0 else f'late{index+1}'

    def commit(self, proposal):
        self._verify()
        if not isinstance(proposal, TributaryProposal):
            raise ValueError('Expected a tributary proposal')
        if proposal.revision != self.revision:
            raise ValueError('Stale tributary preview')
        expected = self.preview(*proposal.source, proposal.candidate_index)
        if expected != proposal:
            raise ValueError('Tributary proposal disagrees with current world')
        # The trial only changes previously unresolved tiles and passes every
        # check *before* making any of its results authoritative.
        trial, branch, foot, tiles = self._trial(proposal.source, proposal.candidate_index)
        if branch != proposal.target_branch or tiles != proposal.resolved_tiles:
            raise ValueError('Tributary trial differs from preview')
        self.terrain = trial
        self._terrain_snapshot = trial.dumps()
        self._branches.append(proposal)
        self._events.append({'type': 'tributary', 'source': list(proposal.source),
                             'candidate_index': proposal.candidate_index,
                             'target_branch': branch,
                             'points': [list(p) for p in proposal.points],
                             'resolved_tiles': [list(t) for t in tiles]})
        self.revision += 1
        return proposal.as_dict()

    def inspect(self, x_km, y_km):
        self._verify()
        item = self.terrain.inspect(x_km, y_km)
        item['late_tributary_committed'] = bool(self._branches)
        item['late_tributaries_committed'] = len(self._branches)
        return item

    def channel_at(self, fraction, proposal=None, *, branch_index=0):
        """Evaluate the exact surface-attached branch at any parameter position.

        Graph polyline heights are samples of this curve, not a new elevation
        field that could contradict the committed continuous terrain.
        """
        self._verify()
        f = float(fraction)
        if not math.isfinite(f) or not 0 <= f <= 1:
            raise ValueError('Channel fraction must lie between zero and one')
        if proposal is None:
            if type(branch_index) is not int or not 0 <= branch_index < len(self._branches):
                raise ValueError('No tributary exists at that branch index')
            branch = self._branches[branch_index]
        else:
            branch = proposal
        if proposal is not None and proposal != self.preview(*proposal.source, proposal.candidate_index):
            raise ValueError('Stale or invalid preview')
        terrain = self._trial(proposal.source, proposal.candidate_index)[0] if proposal else self.terrain
        q = branch.points[-1]
        x = branch.source[0]*(1-f)+q[0]*f
        y = branch.source[1]*(1-f)+q[1]*f
        return (x, y, terrain.elevation(x,y))

    def _graph_from(self, branches):
        """Add all late branches to one acyclic graph with shared junctions.

        Split the *currently surviving* original-course edge, not necessarily
        the original watershed edge: several late mouths can join different
        positions on that same former edge in either commitment order.
        """
        base = self.terrain.watershed.network()['graph']
        nodes = [dict(n) for n in base['nodes']]
        edges = [dict(e) for e in base['edges']]
        positions = {n['id']: n['position'] for n in nodes}
        for index, branch in enumerate(branches):
            prefix = self._channel_id(index)
            q = branch.points[-1]
            # Reuse authoritative nodes, including existing confluences.
            matches = [key for key, pos in positions.items() if math.dist(pos, q) < 1e-6]
            if matches:
                junction_id = matches[0]
            else:
                candidates = []
                for edge_index, edge in enumerate(edges):
                    if edge['course'] != branch.target_branch:
                        continue
                    a, b = positions[edge['from']], positions[edge['to']]
                    d, foot, t = self.terrain._foot(q[0], q[1], a, b)
                    if d < 1e-6 and math.dist(foot, q) < 1e-5 and 1e-8 < t < 1-1e-8:
                        candidates.append(edge_index)
                if len(candidates) != 1:
                    raise ValueError('Confluence does not uniquely split an established channel edge')
                junction_id = f'{prefix}:confluence'
                positions[junction_id] = list(q)
                nodes.append({'id': junction_id, 'position': list(q)})
                existing_edge = edges.pop(candidates[0])
                edges.extend([
                    {'from': existing_edge['from'], 'to': junction_id,
                     'course': existing_edge['course']},
                    {'from': junction_id, 'to': existing_edge['to'],
                     'course': existing_edge['course']}])
            for i, point in enumerate(branch.points[:-1]):
                node_id = f'{prefix}:{i}'
                positions[node_id] = list(point)
                nodes.append({'id': node_id, 'position': list(point)})
                edges.append({'from': node_id,
                              'to': f'{prefix}:{i+1}' if i+1<len(branch.points)-1 else junction_id,
                              'course': prefix})
        # One downstream route per node, ending at the original bay.
        targets = {}
        for edge in edges:
            if edge['from'] in targets:
                raise ValueError('Drainage graph has multiple downstream links')
            targets[edge['from']] = edge['to']
        for node_id in positions:
            seen = set()
            cursor = node_id
            while cursor != base['outlet_id']:
                if cursor in seen or cursor not in targets:
                    raise ValueError('Drainage graph has a cycle or disconnected channel')
                seen.add(cursor)
                cursor = targets[cursor]
        return {'nodes': nodes, 'edges': edges, 'outlet_id': base['outlet_id']}

    def graph(self, proposal=None):
        self._verify()
        if proposal is not None and proposal != self.preview(*proposal.source, proposal.candidate_index):
            raise ValueError('Stale or invalid preview')
        return self._graph_from(self._branches + ([proposal] if proposal is not None else []))

    def mesh(self, step_km=0.2, proposal=None):
        self._verify()
        if proposal is not None and proposal != self.preview(*proposal.source, proposal.candidate_index):
            raise ValueError('Stale or invalid preview')
        if proposal is not None:
            trial, _, _, _ = self._trial(proposal.source, proposal.candidate_index)
        else:
            trial = self.terrain
        mesh = trial.mesh(step_km)
        for index, branch in enumerate(self._branches + ([proposal] if proposal is not None else [])):
            mesh['channels'][self._channel_id(index)] = [list(p) for p in branch.points]
        mesh['proposed_channel_id'] = self._channel_id(len(self._branches)) if proposal else None
        mesh['proposed_tiles'] = [list(t) for t in proposal.resolved_tiles] if proposal else []
        mesh['late_provisional'] = proposal is not None
        return mesh

    def state(self):
        self._verify()
        return {'version': self.VERSION, 'base_terrain': self._base,
                'terrain': self.terrain.state(), 'events': json.loads(json.dumps(self._events)),
                'revision': self.revision,
                'late_tributary': self._branches[0].as_dict() if self._branches else None,
                'late_tributaries': [branch.as_dict() for branch in self._branches]}

    def dumps(self):
        return json.dumps(self.state(), sort_keys=True, indent=2, allow_nan=False)

    @classmethod
    def restore(cls, state):
        if not isinstance(state, dict) or state.get('version') not in (1, cls.VERSION):
            raise ValueError('Unsupported late tributary world')
        # Earlier single-tributary exports remain loadable. Once restored,
        # they export the current multibranch format.
        if state['version'] == 1:
            state = json.loads(json.dumps(state))
            state['version'] = cls.VERSION
            state['late_tributaries'] = ([state['late_tributary']]
                                          if state['late_tributary'] else [])
        design = cls(DrainageTerrainDesign.restore(state['base_terrain']))
        for event in state['events']:
            if event['type'] != 'tributary':
                raise ValueError('Unexpected tributary event')
            proposal = design.preview(*event['source'], event['candidate_index'])
            if any(proposal.as_dict()[key] != event[key] for key in
                   ('target_branch', 'points', 'resolved_tiles')):
                raise ValueError('Saved tributary does not match admissible generation')
            design.commit(proposal)
        if design.state() != state:
            raise ValueError('Late tributary state contradicts its history')
        return design

    @classmethod
    def loads(cls, source):
        return cls.restore(json.loads(source))
