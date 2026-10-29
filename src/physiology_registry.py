"""Versioned R4 physiology configuration, resolved explicitly for a native Being.

No implicit human fallback: each Being must select a registered identifier.
A definition may inherit from an explicit parent (body plan -> species ->
population -> individual), but only the root selects the physiological model.
This is a data/reference resolver, not an independent fatigue simulator.
"""
from dataclasses import dataclass, fields, replace
from hashlib import sha256
import json
import math
from types import MappingProxyType

from universe_physical_fatigue_r4 import Profile, human_profile


_FIELDS = frozenset(field.name for field in fields(Profile))


def _numeric(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f'{name} must be a number')
    if not math.isfinite(value):
        raise ValueError(f'{name} must be finite')
    return float(value)


def _validate_profile(p):
    for name in _FIELDS:
        value = _numeric(name, getattr(p, name))
        if name in {'critical_fresh', 'critical_floor', 'peak_floor', 'slow_baseline'}:
            if not 0 < value < 1:
                raise ValueError(f'{name} must lie strictly between 0 and 1')
        elif value <= 0:
            raise ValueError(f'{name} must be positive')
    if p.peak_floor < p.critical_fresh * p.critical_floor:
        raise ValueError('depleted peak output must not be below depleted critical output')
    if p.critical_fresh > 1:
        raise ValueError('critical output cannot exceed fresh maximal output')
    return p


@dataclass(frozen=True)
class PhysiologyDefinition:
    identifier: str
    parent_id: str | None = None
    model: str | None = None  # root: human-r4 or parameterized-r4
    parameters: tuple = ()  # name/value pairs; immutable and reproducible

    def __post_init__(self):
        if not isinstance(self.identifier, str) or not self.identifier.strip() or '@' not in self.identifier:
            raise ValueError('physiology identifier must be nonempty and version-qualified (@...)')
        if self.parent_id is not None and (not isinstance(self.parent_id, str) or not self.parent_id.strip()):
            raise ValueError('invalid parent physiology identifier')
        if self.parent_id == self.identifier:
            raise ValueError('physiology cannot inherit from itself')
        if (self.parent_id is None) != (self.model is not None):
            raise ValueError('only root physiology definitions may choose the model')
        if self.model not in (None, 'human-r4', 'parameterized-r4'):
            raise ValueError('unknown physiology model')
        pairs = tuple(self.parameters.items()) if isinstance(self.parameters, dict) else tuple(self.parameters)
        if len(pairs) != len({key for key, _ in pairs}):
            raise ValueError('duplicate physiology field')
        converted = []
        for key, value in pairs:
            if key not in _FIELDS:
                raise ValueError(f'unknown R4 physiological parameter: {key}')
            converted.append((key, _numeric(key, value)))
        if self.model == 'parameterized-r4' and {key for key, _ in converted} != _FIELDS:
            raise ValueError('nonhuman root requires all R4 profile fields, not human defaults')
        object.__setattr__(self, 'parameters', tuple(sorted(converted)))


@dataclass(frozen=True)
class ResolvedPhysiology:
    profile: Profile
    identifier: str
    lineage: tuple
    version_hash: str
    mode: str


class PhysiologyRegistry:
    def __init__(self, definitions=()):
        self._definitions = {}
        for definition in definitions:
            self.register(definition)

    def register(self, definition):
        if not isinstance(definition, PhysiologyDefinition):
            raise TypeError('expected PhysiologyDefinition')
        if definition.identifier in self._definitions:
            raise ValueError('physiology definition already registered; published versions are immutable')
        self._definitions[definition.identifier] = definition

    def resolve(self, being, *, mode='ordinary'):
        """Resolve a native Being's inherited R4 profile and content fingerprint.

        'running' is the sole skill-specialized mode at present. Future mode
        changes require their own physiological calibration, not guesswork.
        """
        if mode not in ('ordinary', 'running'):
            raise ValueError('unsupported physiological mode')
        identifier = being.physiology_id
        if identifier is None or identifier not in self._definitions:
            raise KeyError(f'physiology not registered: {identifier!r}')
        lineage = []
        visited = set()
        cursor = identifier
        while cursor is not None:
            if cursor in visited:
                raise ValueError('cyclic physiology inheritance')
            visited.add(cursor)
            try:
                definition = self._definitions[cursor]
            except KeyError as exc:
                raise KeyError(f'missing inherited physiology: {cursor}') from exc
            lineage.append(definition)
            cursor = definition.parent_id
        lineage.reverse()
        root = lineage[0]
        if root.model == 'human-r4':
            fitness = _numeric('Fitness', being.FIT())
            if fitness <= 0:
                raise ValueError('Fitness must be positive')
            run_level = being.get_skill_level('run') or 0
            if isinstance(run_level, bool) or int(run_level) != run_level:
                raise ValueError('Run level must be an integer')
            profile = human_profile(fitness, run_level=int(run_level),
                                    running=mode == 'running')
        elif root.model == 'parameterized-r4':
            profile = Profile(**dict(root.parameters))
        else:
            raise ValueError('unsupported physiology root')
        for definition in lineage:
            profile = replace(profile, **dict(definition.parameters))
        _validate_profile(profile)
        canonical = {'definitions': [
            {'id': d.identifier, 'parent': d.parent_id, 'model': d.model,
             'parameters': d.parameters} for d in lineage],
            'mode': mode, 'resolved_profile': [getattr(profile, key) for key in sorted(_FIELDS)]}
        digest = sha256(json.dumps(canonical, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        return ResolvedPhysiology(profile, identifier,
                                 tuple(d.identifier for d in lineage), digest, mode)
