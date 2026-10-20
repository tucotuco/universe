"""Realize continuous terrain conditioned on an immutable watershed graph.

Continuous x/y coordinates are kilometres; channel beds and terrain are metres.
A lower-envelope construction provides a downhill route to a committed channel
without running a hydraulic solver. Optional tile-local relief modifies slopes
but never changes channel elevations or adjacent tile boundaries.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import random

from geographical_watershed import WatershedDesign


def _finite(name, value):
    if isinstance(value, bool):
        raise ValueError(f'{name} must be finite')
    try:
        result = float(value)
    except (ValueError, TypeError) as exc:
        raise ValueError(f'{name} must be finite') from exc
    if not math.isfinite(result):
        raise ValueError(f'{name} must be finite')
    return result


@dataclass(frozen=True)
class ReliefProposal:
    tile: tuple[int, int]
    strength: float
    candidate_index: int
    revision: int

    def as_dict(self):
        return {'tile': list(self.tile), 'strength': self.strength,
                'candidate_index': self.candidate_index, 'revision': self.revision}


class DrainageTerrainDesign:
    """Terrain constrained by a previously committed, frozen river network.

    Exact bed geometry is immutable. A continuous distance-to-channel potential
    defines an admissible surface and constructive downhill paths to channels.
    Per-tile resolution is optional; uncommitted tiles have an elevation RANGE,
    not a secretly fixed terrain. This is a bounded regional demonstration.
    """
    VERSION = 1
    TILE_KM = 2.0
    MAX_STRENGTH = 0.08
    BASE_SLOPE_M_PER_KM = 1500.0

    def __init__(self, watershed: WatershedDesign, seed=1102):
        if not isinstance(watershed, WatershedDesign):
            raise ValueError('A WatershedDesign is required')
        if 'main' not in watershed._channels:
            raise ValueError('Commit the main river before constructing drainage terrain')
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise ValueError('Terrain seed must be an integer')
        # Take a read-only snapshot: later river-network edits cannot silently
        # invalidate terrain commitments. Reload uses the exact same journal.
        self.watershed = WatershedDesign.loads(watershed.dumps())
        self._watershed_snapshot = self.watershed.dumps()
        self.seed = seed
        self._segments = []
        for branch, points in self.watershed._channels.items():
            for a, b in zip(points, points[1:]):
                self._segments.append((branch, a, b))
        self._committed = {}
        self.conditions = []
        self._events = []
        self.revision = 0

    def _check_frozen(self):
        if self.watershed.dumps() != self._watershed_snapshot:
            raise ValueError('Watershed changed after terrain construction; no implicit revision')

    @staticmethod
    def _tile(x, y):
        return min(3, int(x // 2)), min(1, int((y + 2) // 2))

    @staticmethod
    def _tile_valid(tile):
        return (isinstance(tile, (tuple, list)) and len(tile) == 2
                and all(type(n) is int for n in tile) and 0 <= tile[0] < 4
                and 0 <= tile[1] < 2)

    @classmethod
    def _coords(cls, x, y):
        x, y = _finite('x_km', x), _finite('y_km', y)
        if not (0 <= x <= 8 and -2 <= y <= 2):
            raise ValueError('Coordinates outside region')
        return x, y

    @staticmethod
    def _weight(x, y, tile):
        x0, y0 = 2 * tile[0], -2 + 2 * tile[1]
        u, v = (x - x0) / 2, (y - y0) / 2
        if not (0 <= u <= 1 and 0 <= v <= 1):
            return 0.0
        return math.sin(math.pi*u)**2 * math.sin(math.pi*v)**2

    @staticmethod
    def _foot(x, y, a, b):
        vx, vy = b[0]-a[0], b[1]-a[1]
        t = max(0.0, min(1.0, ((x-a[0])*vx + (y-a[1])*vy) / (vx*vx+vy*vy)))
        qx, qy = a[0]+t*vx, a[1]+t*vy
        z = a[2]+t*(b[2]-a[2])
        return math.hypot(x-qx, y-qy), (qx, qy, z), t

    def _effective_strength(self, x, y, proposal=None, *, tile_override=None, strength_override=None):
        tile = self._tile(x, y)
        strength = self._committed.get(tile, 0.0)
        if proposal is not None and proposal.tile == tile:
            strength = proposal.strength
        if tile_override == tile:
            strength = strength_override
        return strength * self._weight(x, y, tile)

    def _surface(self, x, y, proposal=None, *, tile_override=None, strength_override=None):
        # Lower envelope of continuous cones centered on channel segments.
        # At every committed channel, the exact known bed is recovered when
        # BASE_SLOPE dominates inter-channel/longitudinal bed gradients.
        k = self.BASE_SLOPE_M_PER_KM * (1.0 + self._effective_strength(
            x, y, proposal, tile_override=tile_override, strength_override=strength_override))
        best = None
        for branch, a, b in self._segments:
            d, q, t = self._foot(x, y, a, b)
            elevation = q[2] + k*d
            if best is None or elevation < best[0]:
                best = elevation, branch, q, d
        return best

    def _check_proposal(self, proposal):
        if proposal is not None:
            if not isinstance(proposal, ReliefProposal) or proposal.revision != self.revision:
                raise ValueError('Invalid or stale terrain preview')
            if proposal != self.preview(proposal.tile, proposal.candidate_index):
                raise ValueError('Terrain preview does not match committed constraints')

    def elevation(self, x, y, proposal=None):
        self._check_frozen()
        self._check_proposal(proposal)
        x, y = self._coords(x, y)
        return self._surface(x, y, proposal)[0]

    def _height_at_strength(self, x, y, strength):
        return self._surface(x, y, tile_override=self._tile(x,y), strength_override=strength)[0]

    def _feasible(self, tile, conditions=None):
        lo, hi = 0.0, self.MAX_STRENGTH
        for c in self.conditions if conditions is None else conditions:
            if tuple(c['tile']) != tile:
                continue
            x, y = c['x_km'], c['y_km']
            target_lo = c['elevation_m']-c['tolerance_m']
            target_hi = c['elevation_m']+c['tolerance_m']
            h0 = self._height_at_strength(x, y, 0.0)
            hmax = self._height_at_strength(x, y, self.MAX_STRENGTH)
            if target_hi < h0-1e-7 or target_lo > hmax+1e-7:
                raise ValueError('Elevation condition incompatible with committed drainage terrain')
            # Height is monotonic in relief strength because every segment
            # contributes z + K(strength)*distance, and we take their minimum.
            if target_lo > h0:
                a, b = 0.0, self.MAX_STRENGTH
                for _ in range(48):
                    m = (a+b)/2
                    if self._height_at_strength(x,y,m) < target_lo:
                        a = m
                    else:
                        b = m
                lo = max(lo,b)
            if target_hi < hmax:
                a, b = 0.0, self.MAX_STRENGTH
                for _ in range(48):
                    m = (a+b)/2
                    if self._height_at_strength(x,y,m) > target_hi:
                        b = m
                    else:
                        a = m
                hi = min(hi,a)
        if lo > hi + 1e-12:
            raise ValueError('Contradictory elevation conditions in one tile')
        return min(lo, hi), hi

    def add_condition(self, data):
        """Impose one known elevation without forcing the entire tile to exist."""
        self._check_frozen()
        if not isinstance(data, dict):
            raise ValueError('Elevation condition must be a mapping')
        x,y = self._coords(data['x_km'],data['y_km'])
        z = _finite('elevation_m',data['elevation_m'])
        tol = _finite('tolerance_m',data.get('tolerance_m',0))
        if tol < 0:
            raise ValueError('Tolerance must be nonnegative')
        tile = self._tile(x,y)
        condition = {'x_km':x, 'y_km':y, 'elevation_m':z,
                     'tolerance_m':tol, 'tile':list(tile)}
        proposed = self.conditions+[condition]
        self._feasible(tile, proposed)
        if tile in self._committed and abs(self.elevation(x,y)-z) > tol+1e-7:
            raise ValueError('Condition contradicts committed terrain')
        self.conditions.append(condition)
        self._events.append({'type':'condition','value':dict(condition)})
        self.revision += 1
        return condition

    def inspect(self, x, y):
        """Inspection does not commit unestablished terrain."""
        self._check_frozen()
        x,y=self._coords(x,y)
        tile=self._tile(x,y)
        low,high=self._feasible(tile)
        result={'tile':list(tile),'realized':tile in self._committed,
                'revision':self.revision,'active_conditions':sum(tuple(c['tile'])==tile for c in self.conditions)}
        if result['realized']:
            result['elevation_m']=self.elevation(x,y)
        else:
            result['possible_elevation_m']=[self._height_at_strength(x,y,low),
                                            self._height_at_strength(x,y,high)]
        return result

    def preview(self, tile, candidate_index=0):
        self._check_frozen()
        if not self._tile_valid(tile):
            raise ValueError('Invalid terrain tile')
        tile=tuple(tile)
        if tile in self._committed:
            raise ValueError('Terrain tile already realized')
        if type(candidate_index) is not int or candidate_index < 0:
            raise ValueError('Candidate index must be a nonnegative integer')
        lo,hi=self._feasible(tile)
        key=json.dumps([self.seed,tile,candidate_index,self.conditions,
                        self._watershed_snapshot],sort_keys=True).encode('utf-8')
        rng=random.Random(int.from_bytes(hashlib.sha256(key).digest()[:16],'big'))
        strength=lo+(hi-lo)*rng.random()
        return ReliefProposal(tile,strength,candidate_index,self.revision)

    def commit(self, proposal):
        self._check_frozen()
        if not isinstance(proposal, ReliefProposal):
            raise ValueError('Expected a relief proposal')
        if proposal.revision != self.revision:
            raise ValueError('Stale preview; retry')
        if proposal != self.preview(proposal.tile,proposal.candidate_index):
            raise ValueError('Relief proposal does not match the current world')
        self._committed[proposal.tile]=proposal.strength
        self._events.append({'type':'commit','tile':list(proposal.tile),
                             'candidate_index':proposal.candidate_index,
                             'strength':proposal.strength})
        self.revision+=1
        return proposal.as_dict()

    def downhill_witness(self, x, y, proposal=None, steps=12):
        """Show a strictly descending line to a channel, then follow it to bay.

        Only valid for a fully specified *candidate surface*. Coordinates in
        uncommitted tiles along the witness are explicitly provisional.
        """
        self._check_frozen()
        self._check_proposal(proposal)
        x,y=self._coords(x,y)
        _, branch, foot, dist=self._surface(x,y,proposal)
        locations=[]
        if dist>1e-8:
            for i in range(steps+1):
                t=i/steps
                xx=x+t*(foot[0]-x)
                yy=y+t*(foot[1]-y)
                locations.append((xx,yy,self.elevation(xx,yy,proposal)))
        else:
            locations.append((x,y,self.elevation(x,y,proposal)))
        # Downstream polyline interpolation uses the exact channel vertices.
        channel=self.watershed._channels[branch]
        q=foot
        if not locations or math.hypot(locations[-1][0]-q[0],locations[-1][1]-q[1])>1e-7:
            locations.append(q)
        for point in channel:
            if point[0] > q[0]+1e-8:
                locations.append(point)
        if branch!='main':
            junction=channel[-1]
            for point in self.watershed._channels['main']:
                if point[0] > junction[0]+1e-8:
                    locations.append(point)
        return {'branch':branch,'points':[list(p) for p in locations],
                'provisional':any(self._tile(a,b) not in self._committed for a,b,_ in locations)}

    def mesh(self, step_km=0.2, proposal=None):
        self._check_frozen()
        self._check_proposal(proposal)
        step=_finite('step_km',step_km)
        if not 0.1 <= step <= 1 or abs(8/step-round(8/step))>1e-8 or abs(4/step-round(4/step))>1e-8:
            raise ValueError('Map sampling interval must divide 4 and 8 km')
        nx,ny=round(8/step),round(4/step)
        heights=[]
        for j in range(ny+1):
            y=-2+j*step
            heights.append([round(self._surface(i*step,y,proposal)[0],2) for i in range(nx+1)])
        return {'step_km':step,'heights_m':heights,
                'realized_tiles':[list(t) for t in sorted(self._committed)],
                'proposed_tile':list(proposal.tile) if proposal else None,
                'channels':self.watershed.network()['channels']}

    def state(self):
        self._check_frozen()
        return {'version':self.VERSION,'watershed':self.watershed.state(),
                'seed':self.seed,'events':json.loads(json.dumps(self._events)),
                'conditions':[dict(c) for c in self.conditions],
                'committed':[{'tile':list(t),'strength':s} for t,s in sorted(self._committed.items())],
                'revision':self.revision}

    def dumps(self):
        return json.dumps(self.state(),sort_keys=True,indent=2,allow_nan=False)

    @classmethod
    def restore(cls,payload):
        if not isinstance(payload,dict) or payload.get('version')!=cls.VERSION:
            raise ValueError('Unsupported drainage terrain version')
        world=cls(WatershedDesign.restore(payload['watershed']),seed=payload['seed'])
        for event in payload['events']:
            if event['type']=='condition':
                result=world.add_condition(event['value'])
                if result!=event['value']:
                    raise ValueError('Saved condition disagrees with replay')
            elif event['type']=='commit':
                proposal=world.preview(event['tile'],event['candidate_index'])
                if proposal.strength!=event['strength']:
                    raise ValueError('Saved relief differs from reproducible proposal')
                world.commit(proposal)
            else:
                raise ValueError('Unknown drainage terrain event')
        if world.state()!=payload:
            raise ValueError('Saved drainage terrain disagrees with its journal')
        return world

    @classmethod
    def loads(cls,text):
        return cls.restore(json.loads(text))
