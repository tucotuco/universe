"""Native time-bounded physical work contract, before combat calibration.

A WorkSegment describes ONE already-consolidated realized muscular effort, not
an action-derived guess. Multiple actions sharing that effort are recorded in
'sources'. Overlapping, independent normalized workloads are rejected rather
than added, averaged or arbitrarily maximized. The provider must calculate
one combined profile or subdivide time before submitting a work timeline.
"""
from dataclasses import dataclass
import math
from types import MappingProxyType


def _real(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f'{name} must be numeric')
    if not math.isfinite(value):
        raise ValueError(f'{name} must be finite')
    return float(value)


@dataclass(frozen=True)
class WorkSegment:
    start: float
    end: float
    requested_u: float
    wear: float = 1.0
    mode: str = 'required'  # required, all_out, actual, rest, sleep
    physiology_mode: str = 'ordinary'  # or running
    sources: tuple = ()
    outcome: str = 'performed'  # attempted failure still costs realized work

    def __post_init__(self):
        for key in ('start', 'end', 'requested_u', 'wear'):
            object.__setattr__(self, key, _real(key, getattr(self, key)))
        if self.end <= self.start:
            raise ValueError('work segment duration must be positive')
        if not 0 <= self.requested_u <= 1 or self.wear < 0:
            raise ValueError('work intensity must be in [0,1]; wear nonnegative')
        if self.mode not in ('required', 'all_out', 'actual', 'rest', 'sleep'):
            raise ValueError('unsupported work mode')
        if self.physiology_mode not in ('ordinary', 'running'):
            raise ValueError('unsupported physiological mode')
        if self.mode in ('rest', 'sleep') and self.requested_u != 0:
            raise ValueError('rest and sleep have zero muscular work')
        if self.mode in ('rest', 'sleep') and self.physiology_mode != 'ordinary':
            raise ValueError('rest and sleep do not select running specialization')
        if self.mode == 'actual' and self.outcome not in ('performed', 'failed'):
            raise ValueError('actual work outcome must be performed or failed')
        if not isinstance(self.sources, (tuple, list)) or not self.sources or any(
                not isinstance(s, str) or not s.strip() for s in self.sources):
            raise ValueError('work requires explicit provenance sources (rest included)')
        if len(set(self.sources)) != len(self.sources):
            raise ValueError('duplicate source in consolidated work segment')
        object.__setattr__(self, 'sources', tuple(self.sources))

    def to_dict(self):
        return {'start': self.start, 'end': self.end, 'requested_u': self.requested_u,
                'wear': self.wear, 'mode': self.mode,
                'physiology_mode': self.physiology_mode,
                'sources': list(self.sources), 'outcome': self.outcome}


class WorkTimeline:
    """Exact gap-free, nonoverlapping realized work for *each* required Being.

    Half-open segments [start,end) cover the interval; the same source can
    appear in subsequent nonoverlapping segments. No omission means 'idle'.
    """
    def __init__(self, start, end, segments_by_being, *, participants):
        self.start = _real('start', start)
        self.end = _real('end', end)
        if self.end <= self.start:
            raise ValueError('work timeline requires positive duration')
        if not isinstance(segments_by_being, dict):
            raise TypeError('segments_by_being must be a mapping')
        participants = tuple(participants)
        if len(set(participants)) != len(participants) or set(segments_by_being) != set(participants):
            raise ValueError('work must explicitly cover each participating Being once')
        rows = {}
        for being_id in sorted(participants):
            segments = tuple(sorted(segments_by_being[being_id], key=lambda item: (item.start, item.end)))
            if not segments:
                raise ValueError(f'missing work/recovery for Being {being_id}')
            cursor = self.start
            for segment in segments:
                if not isinstance(segment, WorkSegment):
                    raise TypeError('expected WorkSegment')
                if not math.isclose(segment.start, cursor, rel_tol=0, abs_tol=1e-9):
                    raise ValueError(f'gap or overlapping work for Being {being_id}')
                if segment.end > self.end + 1e-9:
                    raise ValueError('segment exceeds frame')
                cursor = segment.end
            if not math.isclose(cursor, self.end, rel_tol=0, abs_tol=1e-9):
                raise ValueError('work does not cover the entire interval')
            rows[being_id] = segments
        self._rows = MappingProxyType(rows)

    @property
    def participant_ids(self):
        return frozenset(self._rows)

    def segments(self, being_id):
        return self._rows[being_id]

    def to_dict(self):
        return {'start': self.start, 'end': self.end,
                'beings': {key: [s.to_dict() for s in row] for key, row in self._rows.items()}}
