"""Native persistent Q/B state, separate from legacy Exertion during migration.

There are exactly two physical-fatigue reserves. This module contains no
combat adjudication, work accounting or new physiological equations.
"""
from dataclasses import dataclass
import math


PHYSICAL_FATIGUE_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class PhysicalFatigueState:
    q: float = 1.0
    b: float = 1.0

    def __post_init__(self):
        for key in ('q', 'b'):
            value = getattr(self, key)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f'{key} must be a real number')
            if not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError(f'{key} must be finite and in [0, 1]')
            object.__setattr__(self, key, float(value))

    def to_dict(self, physiology_id=None):
        return {'version': PHYSICAL_FATIGUE_SCHEMA_VERSION,
                'q': self.q, 'b': self.b,
                'physiology_id': physiology_id}


def read_physical_fatigue(record, *, missing='reject'):
    """Explicit migration boundary for a historical or modern Being record.

    Missing Q/B is not inferred from legacy discrete fatigue_level. Passing
    missing='fresh' is an *opt-in migration decision* for old saved Beings.
    Returns state and an unresolved/versioned physiology reference.
    """
    if not isinstance(record, dict):
        raise TypeError('saved Being must be a mapping')
    if 'physical_fatigue' not in record:
        if missing == 'fresh':
            return PhysicalFatigueState(), None
        if missing == 'reject':
            raise ValueError('old save has no physical_fatigue; opt in to fresh migration')
        raise ValueError('missing must be reject or fresh')
    payload = record['physical_fatigue']
    if not isinstance(payload, dict) or set(payload) != {
            'version', 'q', 'b', 'physiology_id'}:
        raise ValueError('invalid physical_fatigue record')
    if type(payload['version']) is not int or payload['version'] != PHYSICAL_FATIGUE_SCHEMA_VERSION:
        raise ValueError('unsupported physical_fatigue schema version')
    physiology_id = payload['physiology_id']
    if physiology_id is not None and (not isinstance(physiology_id, str) or not physiology_id.strip()):
        raise ValueError('physiology_id must be a nonempty reference or None')
    return PhysicalFatigueState(payload['q'], payload['b']), physiology_id
