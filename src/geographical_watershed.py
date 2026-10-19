"""Constrained, progressively committed *river topology* at regional scale.

This is a deliberately bounded experiment, separate from GeographicalDesign's
already-established river. Coordinates are kilometres in a local continuous
frame; heights are metres above sea level. A downhill directed graph and its
continuous piecewise-linear edges are authoritative after commitment. The
illustrative relief is *not* a hydrodynamic or geomorphological solution.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import random


def _number(name, value):
    if isinstance(value, bool):
        raise ValueError(f'{name} must be finite')
    try:
        result = float(value)
    except (ValueError, TypeError) as exc:
        raise ValueError(f'{name} must be finite') from exc
    if not math.isfinite(result):
        raise ValueError(f'{name} must be finite')
    return result


def _rng(*parts):
    key = json.dumps(parts, separators=(',', ':'), sort_keys=True).encode('utf-8')
    return random.Random(int.from_bytes(hashlib.sha256(key).digest()[:16], 'big'))


@dataclass(frozen=True)
class ChannelProposal:
    branch: str
    candidate_index: int
    revision: int
    points: tuple[tuple[float, float, float], ...]  # x km, y km, bed m

    def as_dict(self):
        return {'branch': self.branch, 'candidate_index': self.candidate_index,
                'revision': self.revision, 'points': [list(p) for p in self.points]}


class WatershedDesign:
    """Generate a single-outlet branching drainage graph without preset courses.

    Immutable anchors: a river runs beside village (4,0), empties into the bay
    at (8,-0.6), and begins in a mountain *source region* at western edge.
    The source's specific position and the river route are unresolved initially.

    The main-stem course must be committed before tributary courses can be
    realized. Tributaries can subsequently be realized in either order.
    """

    VERSION = 1
    XMAX = 8.0
    YMIN = -2.0
    YMAX = 2.0
    STEP = 0.5
    VILLAGE = (4.0, 0.0, 500.0)
    BAY = (8.0, -0.6, 0.0)
    SIDES = ('north', 'south')
    BRANCHES = ('main', 'north', 'south')

    def __init__(self, seed=845, conditions=None):
        if isinstance(seed, bool):
            raise ValueError('seed must be an integer')
        self.seed = int(seed)
        self.conditions = []
        self._channels = {}
        self._events = []
        self.revision = 0
        for c in conditions or []:
            self.add_condition(c)

    @staticmethod
    def _round(v):
        return round(v, 8)

    @classmethod
    def _segment_height(cls, x):
        if x <= cls.VILLAGE[0]:
            return 1400.0 + (cls.VILLAGE[2] - 1400.0) * x / cls.VILLAGE[0]
        return cls.VILLAGE[2] * (cls.BAY[0] - x) / (cls.BAY[0] - cls.VILLAGE[0])

    @classmethod
    def _grid_x(cls, x):
        return abs(x / cls.STEP - round(x / cls.STEP)) < 1e-8

    def _check_condition(self, raw):
        if not isinstance(raw, dict):
            raise ValueError('A geographic condition must be a mapping')
        x = _number('x_km', raw['x_km'])
        y = _number('y_km', raw['y_km'])
        tol = _number('tolerance_km', raw['tolerance_km'])
        if not (0 < x < self.XMAX and self._grid_x(x)):
            raise ValueError('Condition x must be an interior 0.5 km station')
        if not self.YMIN <= y <= self.YMAX or not 0 <= tol <= 1.0:
            raise ValueError('Condition coordinate or tolerance outside bounds')
        if x == self.VILLAGE[0] and abs(y - self.VILLAGE[1]) > tol + 1e-8:
            raise ValueError('Condition contradicts the established village crossing')
        return {'x_km': x, 'y_km': y, 'tolerance_km': tol}

    def add_condition(self, raw):
        """Add a known main-stem crossing, without realizing a river route."""
        condition = self._check_condition(raw)
        new_conditions = self.conditions + [condition]
        for x in sorted({c['x_km'] for c in new_conditions}):
            candidates = [c for c in new_conditions if c['x_km'] == x]
            lo = max(c['y_km'] - c['tolerance_km'] for c in candidates)
            hi = min(c['y_km'] + c['tolerance_km'] for c in candidates)
            if lo > hi + 1e-8:
                raise ValueError('Contradictory observations of the river position')
            if 'main' in self._channels:
                current = self._at_x(self._channels['main'], x)
                if not lo - 1e-8 <= current[1] <= hi + 1e-8:
                    raise ValueError('Condition contradicts committed river course')
        # Necessary reachability bound between known crossings: a continuous
        # river cannot jump arbitrarily far across the region between adjacent
        # 0.5 km stations. This checks feasibility of imposed constraints even
        # *before* a main-stem course is realized.
        bands = {0.0: (0.35, 0.95), 4.0: (0.0, 0.0), 8.0: (-0.6, -0.6)}
        for x in sorted({c['x_km'] for c in new_conditions}):
            group = [c for c in new_conditions if c['x_km'] == x]
            lo = max(c['y_km'] - c['tolerance_km'] for c in group)
            hi = min(c['y_km'] + c['tolerance_km'] for c in group)
            if x in bands:
                low0, high0 = bands[x]
                lo, hi = max(lo, low0), min(hi, high0)
            if lo > hi + 1e-8:
                raise ValueError('Condition contradicts established geographic anchor')
            bands[x] = (lo, hi)
        max_lateral_km = math.sqrt(1.0 - self.STEP*self.STEP)
        stations = sorted(bands)
        for left, right in zip(stations, stations[1:]):
            (a, b), (c, d) = bands[left], bands[right]
            gap = max(0.0, c-b, a-d)
            if gap > max_lateral_km*(right-left)/self.STEP + 1e-8:
                raise ValueError('Crossing condition cannot connect continuously to established river anchors')
        self.conditions.append(condition)
        self._events.append({'type': 'condition', 'value': dict(condition)})
        self.revision += 1
        return dict(condition)

    @staticmethod
    def _at_x(points, x):
        for a, b in zip(points, points[1:]):
            if a[0] - 1e-9 <= x <= b[0] + 1e-9:
                t = (x - a[0]) / (b[0] - a[0])
                return (x, a[1]*(1-t)+b[1]*t, a[2]*(1-t)+b[2]*t)
        if abs(x - points[-1][0]) < 1e-8:
            return points[-1]
        raise ValueError('Station is outside a channel')

    def _sample_main(self, index):
        gen = _rng(self.seed, 'main', index, self.conditions)
        # Independently proposed source, not a predetermined source point.
        source_y = self._round(gen.uniform(0.35, 0.95))
        stations = [i * self.STEP for i in range(17)]
        knots = {0.0: source_y, 4.0: self.VILLAGE[1], 8.0: self.BAY[1]}
        for x in sorted({c['x_km'] for c in self.conditions}):
            candidates = [c for c in self.conditions if c['x_km'] == x]
            lo = max(c['y_km'] - c['tolerance_km'] for c in candidates)
            hi = min(c['y_km'] + c['tolerance_km'] for c in candidates)
            if x in knots:
                # An established anchor is immutable, even with a permissive tolerance.
                if not lo - 1e-8 <= knots[x] <= hi + 1e-8:
                    raise ValueError('Condition contradicts fixed geographic anchor')
            else:
                knots[x] = self._round(gen.uniform(lo, hi))
        points = []
        for x in stations:
            if x in knots:
                y = knots[x]
            else:
                left = max(k for k in knots if k < x)
                right = min(k for k in knots if k > x)
                fraction = (x-left)/(right-left)
                y = (1-fraction)*knots[left] + fraction*knots[right]
                # Narrow meanders between commitments; no need to interpolate
                # millions of intervening time or spatial points.
                y += gen.uniform(-0.14, 0.14) * math.sin(math.pi*fraction)
            points.append((self._round(x), self._round(y),
                           self._round(self._segment_height(x))))
        return tuple(points)

    def _sample_branch(self, side, index):
        main = self._channels['main']
        gen = _rng(self.seed, side, index, main)
        side_sign = 1 if side == 'north' else -1
        start = gen.choice([1.0, 1.5, 2.0])
        end = gen.choice([5.0, 5.5, 6.0] if side == 'north' else [6.0, 6.5, 7.0])
        source_y = side_sign * gen.uniform(1.4, 1.85)
        start_main = self._at_x(main, start)
        # Source remains on its assigned side of the main stem.
        separation = source_y - start_main[1]
        if separation * side_sign <= 0.25:
            raise ValueError('No admissible tributary source')
        nodes = []
        for i in range(round(start/self.STEP), round(end/self.STEP)+1):
            x = self._round(i*self.STEP)
            fraction = (x-start)/(end-start)
            trunk = self._at_x(main, x)
            offset = separation * (1-fraction)
            bend = gen.uniform(-0.075, 0.075) * math.sin(math.pi*fraction)
            y = trunk[1] + offset + bend
            # Elevated headwaters merge at precisely the trunk's bed and
            # location, with monotonically descending elevations downstream.
            z = trunk[2] + 320*(1-fraction)
            nodes.append((x, self._round(y), self._round(z)))
        return tuple(nodes)

    def _validate_course(self, branch, points):
        if len(points) < 2:
            raise ValueError('A channel requires at least two vertices')
        for index, (x, y, z) in enumerate(points):
            if not (0 <= x <= self.XMAX and self.YMIN <= y <= self.YMAX and z >= -1e-9):
                raise ValueError('Channel leaves geographic bounds')
            if index:
                old = points[index-1]
                if abs(x-old[0]-self.STEP) > 1e-7:
                    raise ValueError('Channel stations must progress by 0.5 km')
                if not old[2] > z + 1e-8:
                    raise ValueError('Channel would flow uphill or remain level')
                if math.hypot(x-old[0], y-old[1]) > 1.0:
                    raise ValueError('Unreasonably discontinuous channel course')
        if branch == 'main':
            if points[-1] != self.BAY or self.VILLAGE not in points:
                raise ValueError('Main stem must pass through village to bay')
            if abs(points[0][0]) > 1e-8 or not 0.35 <= points[0][1] <= 0.95:
                raise ValueError('Main source must lie in mountain source region')
            if points[0][2] != 1400.0:
                raise ValueError('Main stem source elevation is established')
            for c in self.conditions:
                point = self._at_x(points, c['x_km'])
                if abs(point[1] - c['y_km']) > c['tolerance_km'] + 1e-7:
                    raise ValueError('River conflicts with an imposed crossing')
        else:
            if 'main' not in self._channels:
                raise ValueError('Main stem must be committed before tributaries')
            trunk = self._channels['main']
            if any((p[1]-self._at_x(trunk, p[0])[1]) * (1 if branch=='north' else -1) <= 0
                   for p in points[:-1]):
                raise ValueError('Tributary crosses the main river before confluence')
            if any(p[2] <= self._at_x(trunk, p[0])[2] for p in points[:-1]):
                raise ValueError('Tributary bed must descend toward main stem')
            if any(abs(a-b) > 1e-7 for a,b in zip(points[-1], self._at_x(trunk, points[-1][0]))):
                raise ValueError('Tributary must join an exact main-stem vertex')

    def preview(self, branch='main', candidate_index=0):
        if branch not in self.BRANCHES:
            raise ValueError('Unknown river branch')
        if branch in self._channels:
            raise ValueError('Channel already committed')
        if branch != 'main' and 'main' not in self._channels:
            raise ValueError('First realize the main stem from village to bay')
        if isinstance(candidate_index, bool) or not isinstance(candidate_index, int) or candidate_index < 0:
            raise ValueError('Candidate index must be a nonnegative integer')
        points = self._sample_main(candidate_index) if branch=='main' else self._sample_branch(branch, candidate_index)
        self._validate_course(branch, points)
        return ChannelProposal(branch, candidate_index, self.revision, points)

    def commit(self, proposal):
        if not isinstance(proposal, ChannelProposal):
            raise ValueError('Expected a channel proposal')
        if proposal.revision != self.revision:
            raise ValueError('Stale preview; generate a fresh proposal')
        expected = self.preview(proposal.branch, proposal.candidate_index)
        if expected != proposal:
            raise ValueError('Proposal does not match the current world')
        self._channels[proposal.branch] = proposal.points
        self._events.append({'type': 'commit', 'branch': proposal.branch,
                             'candidate_index': proposal.candidate_index,
                             'points': [list(p) for p in proposal.points]})
        self.revision += 1
        return proposal.as_dict()

    def inspect(self, question='river_to_bay'):
        if question not in ('river_to_bay', 'north_tributary', 'south_tributary', 'whole_network'):
            raise ValueError('Unknown geographical inquiry')
        needed = {'river_to_bay': ('main',), 'north_tributary': ('main','north'),
                  'south_tributary': ('main','south'),
                  'whole_network': self.BRANCHES}[question]
        missing = [key for key in needed if key not in self._channels]
        known = [key for key in needed if key in self._channels]
        return {'question': question, 'answered': not missing,
                'missing': missing, 'established': known,
                'answer': self._channel_answer(known) if not missing else None,
                'revision': self.revision}

    def _channel_answer(self, names):
        return {key: [list(p) for p in self._channels[key]] for key in names}

    @classmethod
    def _topology(cls, channels):
        """Expose a shared, directed graph (not disconnected line drawings).

        Tributary mouths reuse the identical main-stem node. Downstream edges
        strictly increase in x, guaranteeing an acyclic network.
        """
        nodes, edges = {}, []
        for branch, points in channels.items():
            previous = None
            for index, point in enumerate(points):
                if branch != 'main' and index == len(points) - 1:
                    node_id = f'main:{round(point[0] / cls.STEP)}'
                    if node_id not in nodes or nodes[node_id] != point:
                        raise ValueError('Tributary does not join a shared trunk vertex')
                else:
                    node_id = f'{branch}:{index}'
                    nodes[node_id] = point
                if previous is not None:
                    edges.append({'from': previous, 'to': node_id, 'course': branch})
                previous = node_id
        return {'nodes': [{'id': key, 'position': value} for key, value in nodes.items()],
                'edges': edges, 'outlet_id': 'main:16' if 'main' in channels else None}

    def network(self, proposal=None):
        channels = {k: [list(p) for p in v] for k,v in self._channels.items()}
        if proposal:
            if not isinstance(proposal, ChannelProposal):
                raise ValueError('Invalid preview')
            channels[proposal.branch] = [list(p) for p in proposal.points]
        return {'channels': channels, 'graph': self._topology(channels),
                'preview_branch': proposal.branch if proposal else None,
                'village': list(self.VILLAGE), 'bay': list(self.BAY),
                'conditions': [dict(c) for c in self.conditions],
                'bounds': {'x': [0,self.XMAX], 'y': [self.YMIN,self.YMAX]},
                'revision': self.revision}

    def state(self):
        return {'version': self.VERSION, 'seed': self.seed,
                'conditions': [dict(c) for c in self.conditions],
                'events': json.loads(json.dumps(self._events)),
                'channels': self._channel_answer(self._channels),
                'revision': self.revision}

    def dumps(self):
        return json.dumps(self.state(), sort_keys=True, indent=2, allow_nan=False)

    @classmethod
    def restore(cls, payload):
        if not isinstance(payload, dict) or payload.get('version') != cls.VERSION:
            raise ValueError('Unsupported watershed world version')
        world = cls(seed=payload['seed'])
        for event in payload['events']:
            if event['type'] == 'condition':
                world.add_condition(event['value'])
            elif event['type'] == 'commit':
                proposal = world.preview(event['branch'], event['candidate_index'])
                if [list(p) for p in proposal.points] != event['points']:
                    raise ValueError('Saved river course contradicts generation rules')
                world.commit(proposal)
            else:
                raise ValueError('Unknown watershed event')
        if world.state() != payload:
            raise ValueError('Saved watershed state contradicts its journal')
        return world

    @classmethod
    def loads(cls, text):
        return cls.restore(json.loads(text))
