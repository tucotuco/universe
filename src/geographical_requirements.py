"""Bounded demand-driven geographical realization on a continuous regional surface.

A committed regional model fixes a coastline, a downhill river corridor and
shared tile-edge elevations. Optional, compactly supported relief is realized
one tile at a time. A preview never changes the world; committed local detail
cannot affect other tiles, river beds, or pre-existing boundary elevations.

This is NOT a geomorphology or erosion model. Grid cells index refinement;
they do not define the geometry of the continuous topographic surface.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import random


def finite(name, value):
    if isinstance(value, bool):
        raise ValueError(f'{name} must be a finite number')
    try:
        value = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f'{name} must be a finite number') from exc
    if not math.isfinite(value):
        raise ValueError(f'{name} must be a finite number')
    return value


@dataclass(frozen=True)
class TerrainProposal:
    tile: tuple[int, int]
    amplitude_m: float
    candidate_index: int
    revision: int
    requested_amplitude_m: float | None = None

    def as_dict(self):
        return {'tile': list(self.tile), 'amplitude_m': self.amplitude_m,
                'candidate_index': self.candidate_index, 'revision': self.revision,
                'requested_amplitude_m': self.requested_amplitude_m}


class GeographicalDesign:
    """A small immutable-boundary terrain realization experiment.

    x and y are regional east/north distances in km; z is height above sea
    level in m. Tiles are 2 km squares. The x=8 km coastline is sea level.
    The river source is at (0,0), the outlet at (8,0), and its bed descends.
    """

    VERSION = 1
    XMAX = 8.0
    YMIN = -2.0
    YMAX = 2.0
    TILE_KM = 2.0
    NX = 4
    NY = 2
    MAX_AMPLITUDE_M = 45.0

    def __init__(self, seed=712, source_elevation_m=1400.0,
                 meander_amplitude_km=0.35, conditions=None):
        self.seed = int(seed)
        self.source_elevation_m = finite('source_elevation_m', source_elevation_m)
        self.meander_amplitude_km = finite('meander_amplitude_km', meander_amplitude_km)
        if not 100 <= self.source_elevation_m <= 5000:
            raise ValueError('Source elevation must be between 100 and 5000 m')
        if not 0 <= self.meander_amplitude_km <= 0.7:
            raise ValueError('River meander amplitude must be between 0 and 0.7 km')
        self.conditions = []
        self._committed = {}  # (tile_x,tile_y) -> signed local relief amplitude (m)
        self._history = []
        self._events = []
        self.revision = 0
        for condition in conditions or []:
            self.add_condition(condition)

    def _xy(self, x, y):
        x, y = finite('x_km', x), finite('y_km', y)
        if not 0 <= x <= self.XMAX or not self.YMIN <= y <= self.YMAX:
            raise ValueError('Location outside the modeled region')
        return x, y

    def tile_at(self, x, y):
        x, y = self._xy(x, y)
        return (min(int(x / self.TILE_KM), self.NX - 1),
                min(int((y - self.YMIN) / self.TILE_KM), self.NY - 1))

    def _tile(self, tile):
        if (not isinstance(tile, (tuple, list)) or len(tile) != 2 or
                any(isinstance(v, bool) or not isinstance(v, int) for v in tile)):
            raise ValueError('Tile must be two integer indices')
        key = tuple(tile)
        if not (0 <= key[0] < self.NX and 0 <= key[1] < self.NY):
            raise ValueError('Tile outside the modeled region')
        return key

    def river_y(self, x):
        x = finite('x_km', x)
        if not 0 <= x <= self.XMAX:
            raise ValueError('River point outside region')
        return self.meander_amplitude_km * math.sin(math.pi * x / self.XMAX)

    def river_bed(self, x):
        x = finite('x_km', x)
        if not 0 <= x <= self.XMAX:
            raise ValueError('River point outside region')
        return self.source_elevation_m * (1 - x / self.XMAX) ** 1.5

    def baseline(self, x, y):
        x, y = self._xy(x, y)
        # A continuous nonnegative valley, bounded below by a downhill river.
        return self.river_bed(x) + 75.0 * (y - self.river_y(x)) ** 2 * (1 - x / self.XMAX)

    def _shape(self, x, y, tile):
        """Local relief vanishes at tile edges, river centerline and coast.

        Neighboring tiles can therefore be refined independently without
        introducing height discontinuities, including at shared corners.
        """
        ix, iy = tile
        u = (x - ix * self.TILE_KM) / self.TILE_KM
        v = (y - (self.YMIN + iy * self.TILE_KM)) / self.TILE_KM
        if not 0 <= u <= 1 or not 0 <= v <= 1:
            return 0.0
        d = y - self.river_y(x)
        return (math.sin(math.pi * u) * math.sin(math.pi * v)
                * d*d / (0.10 + d*d) * (1 - x / self.XMAX))

    def elevation(self, x, y, proposal=None):
        x, y = self._xy(x, y)
        tile = self.tile_at(x, y)
        amplitude = self._committed.get(tile, 0.0)
        if proposal is not None:
            if not isinstance(proposal, TerrainProposal):
                raise ValueError('Expected TerrainProposal')
            if tile == proposal.tile and tile not in self._committed:
                amplitude = proposal.amplitude_m
        return self.baseline(x, y) + amplitude * self._shape(x, y, tile)

    def _stable(self, x, y):
        x, y = self._xy(x, y)
        return abs(self._shape(x, y, self.tile_at(x, y))) < 1e-11

    def inspect(self, x, y):
        x, y = self._xy(x, y)
        tile = self.tile_at(x, y)
        resolved = tile in self._committed or self._stable(x, y)
        return {'x_km': x, 'y_km': y, 'tile': list(tile), 'resolved': resolved,
                'elevation_m': self.elevation(x, y) if resolved else None,
                'coarse_estimate_m': self.baseline(x, y),
                'missing': [] if resolved else [f'terrain_tile:{tile[0]},{tile[1]}'],
                'revision': self.revision}

    def elevation_bounds(self, x, y):
        """Nonmutating range of admissible terrain heights at a location.

        This is the public cross-domain dependency contract for approximate
        visibility/inquiry. It uses the same constrained amplitude interval as
        preview(), and collapses to an exact height at fixed points.
        """
        point = self.inspect(x, y)
        if point['resolved']:
            lo = hi = point['elevation_m']
        else:
            tile = tuple(point['tile'])
            a, b = self._allowed_interval(tile)
            factor = self._shape(point['x_km'], point['y_km'], tile)
            baseline = point['coarse_estimate_m']
            lo, hi = sorted((baseline+a*factor, baseline+b*factor))
        return {'x_km': point['x_km'], 'y_km': point['y_km'],
                'tile': point['tile'], 'min_m': lo, 'max_m': hi,
                'resolved': point['resolved'], 'revision': self.revision}

    def _condition(self, raw):
        if not isinstance(raw, dict):
            raise ValueError('Condition must be a mapping')
        x, y = self._xy(raw['x_km'], raw['y_km'])
        condition = {'x_km': x, 'y_km': y,
                     'target_m': finite('target_m', raw['target_m']),
                     'tolerance_m': finite('tolerance_m', raw['tolerance_m'])}
        if condition['tolerance_m'] < 0:
            raise ValueError('Condition tolerance cannot be negative')
        return condition

    def _allowed_interval(self, tile):
        lo, hi = -self.MAX_AMPLITUDE_M, self.MAX_AMPLITUDE_M
        for c in self.conditions:
            x, y = c['x_km'], c['y_km']
            if self.tile_at(x, y) != tile:
                continue
            factor = self._shape(x, y, tile)
            delta = c['target_m'] - self.baseline(x, y)
            if abs(factor) < 1e-11:
                if abs(delta) > c['tolerance_m'] + 1e-8:
                    raise ValueError('Condition contradicts fixed geographic geometry')
                continue
            a = (delta - c['tolerance_m']) / factor
            b = (delta + c['tolerance_m']) / factor
            lo, hi = max(lo, min(a, b)), min(hi, max(a, b))
            if lo > hi + 1e-9:
                raise ValueError('Geographic conditions have no admissible refinement')
        return lo, hi

    def _check_amplitude(self, tile, amplitude):
        amp = finite('amplitude_m', amplitude)
        lo, hi = self._allowed_interval(tile)
        if amp < lo - 1e-8 or amp > hi + 1e-8:
            raise ValueError('Proposed relief contradicts geographic conditions')
        # Bounded local relief is not allowed to create below-sea-level land.
        for i in range(11):
            for j in range(11):
                x = (tile[0] + i/10) * self.TILE_KM
                y = self.YMIN + (tile[1] + j/10) * self.TILE_KM
                if self.baseline(x, y) + amp * self._shape(x, y, tile) < -1e-8:
                    raise ValueError('Proposed relief falls below established sea level')
        return amp

    def add_condition(self, raw):
        c = self._condition(raw)
        tile = self.tile_at(c['x_km'], c['y_km'])
        if tile in self._committed:
            if abs(self.elevation(c['x_km'], c['y_km']) - c['target_m']) > c['tolerance_m'] + 1e-8:
                raise ValueError('Condition contradicts committed terrain')
        self.conditions.append(c)
        try:
            self._allowed_interval(tile)
            # The same point on a tile boundary may be stable for neighboring
            # tiles; validate directly rather than trusting one ownership.
            if self._stable(c['x_km'], c['y_km']):
                if abs(self.baseline(c['x_km'], c['y_km']) - c['target_m']) > c['tolerance_m'] + 1e-8:
                    raise ValueError('Condition contradicts fixed boundary')
        except ValueError:
            self.conditions.pop()
            raise
        self.revision += 1
        self._events.append({'type': 'condition', 'condition': dict(c)})
        return dict(c)

    def preview(self, tile, candidate_index=0, amplitude_m=None):
        tile = self._tile(tile)
        if tile in self._committed:
            raise ValueError('This tile is already committed')
        if isinstance(candidate_index, bool) or not isinstance(candidate_index, int) or candidate_index < 0:
            raise ValueError('Candidate index must be a nonnegative integer')
        lo, hi = self._allowed_interval(tile)
        if amplitude_m is None:
            key = f'{self.seed}:{tile}:{candidate_index}'.encode('ascii')
            seed = int.from_bytes(hashlib.sha256(key).digest()[:8], 'big')
            amplitude = random.Random(seed).uniform(lo, hi)
        else:
            amplitude = finite('amplitude_m', amplitude_m)
        amplitude = self._check_amplitude(tile, amplitude)
        return TerrainProposal(tile, amplitude, candidate_index, self.revision,
                               None if amplitude_m is None else amplitude)

    def commit(self, proposal):
        if not isinstance(proposal, TerrainProposal):
            raise ValueError('Only a TerrainProposal can be committed')
        if proposal.revision != self.revision:
            raise ValueError('Stale geographical proposal; preview again')
        if proposal.tile in self._committed:
            raise ValueError('Tile already committed')
        # Reconstruct the proposal; do not trust manually modified payloads.
        expected = self.preview(proposal.tile, proposal.candidate_index,
                                proposal.requested_amplitude_m)
        if expected != proposal:
            raise ValueError('Proposal does not match current geographic conditions')
        self._committed[proposal.tile] = proposal.amplitude_m
        record = {'tile': list(proposal.tile), 'amplitude_m': proposal.amplitude_m,
                  'candidate_index': proposal.candidate_index,
                  'requested_amplitude_m': proposal.requested_amplitude_m}
        self._history.append(record)
        self._events.append({'type': 'commit', 'record': dict(record)})
        self.revision += 1
        return dict(record)

    def river_profile(self, samples=33):
        if not 2 <= samples <= 1001:
            raise ValueError('Invalid river sampling density')
        return [{'x_km': self.XMAX*i/(samples-1),
                 'y_km': self.river_y(self.XMAX*i/(samples-1)),
                 'bed_m': self.river_bed(self.XMAX*i/(samples-1))}
                for i in range(samples)]

    def map_data(self, proposal=None, nx=65, ny=33):
        if not 9 <= nx <= 129 or not 9 <= ny <= 129:
            raise ValueError('Invalid preview sampling density')
        return {'width': nx, 'height': ny,
                'heights_m': [[round(self.elevation(self.XMAX*i/(nx-1),
                                                  self.YMIN+(self.YMAX-self.YMIN)*j/(ny-1), proposal), 3)
                               for i in range(nx)] for j in range(ny)],
                'river': self.river_profile(65),
                'preview_tile': list(proposal.tile) if proposal else None,
                'tile_extent_km': self.TILE_KM,
                'committed_tiles': [list(t) for t in sorted(self._committed)]}

    def state(self):
        return {'version': self.VERSION, 'seed': self.seed,
                'source_elevation_m': self.source_elevation_m,
                'meander_amplitude_km': self.meander_amplitude_km,
                'region': {'x_km': [0, self.XMAX], 'y_km': [self.YMIN, self.YMAX],
                           'tile_km': self.TILE_KM, 'sea_level_m': 0},
                'conditions': [dict(c) for c in self.conditions],
                'events': [dict(e) for e in self._events],
                'commits': [dict(r) for r in self._history],
                'committed_tiles': [list(t) for t in sorted(self._committed)],
                'revision': self.revision}

    @classmethod
    def restore(cls, payload):
        if payload.get('version') != cls.VERSION:
            raise ValueError('Unsupported geographical save version')
        design = cls(seed=payload['seed'],
                     source_elevation_m=payload['source_elevation_m'],
                     meander_amplitude_km=payload['meander_amplitude_km'])
        # Replay in original chronological commitment order; a later
        # condition must not retrospectively change the candidate RNG range
        # used for an earlier terrain refinement.
        for event in payload.get('events', []):
            if event.get('type') == 'condition':
                design.add_condition(event['condition'])
            elif event.get('type') == 'commit':
                record = event['record']
                proposal = design.preview(record['tile'], record['candidate_index'],
                                          record.get('requested_amplitude_m'))
                if abs(proposal.amplitude_m - finite('amplitude_m', record['amplitude_m'])) > 1e-9:
                    raise ValueError('Saved terrain commitment does not match generation rules')
                design.commit(proposal)
            else:
                raise ValueError('Unknown geographical event type')
        if design.state() != payload:
            raise ValueError('Saved geographical state contradicts its event journal')
        return design

    @classmethod
    def loads(cls, text):
        return cls.restore(json.loads(text))

    def dumps(self):
        return json.dumps(self.state(), indent=2, sort_keys=True)
