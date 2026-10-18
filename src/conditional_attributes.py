"""Keyed, lazy conditional CDFs for partially realized Entity attributes.

Intentionally narrow experiment: each attribute has at most one parent, while
chains allow several correlated attributes. This is private objective generator
state, NOT an observation, belief, or learned/current capability.
"""
from copy import deepcopy
import math


def _outcome_key(value):
    if isinstance(value, bool):
        return 'true' if value else 'false'
    return str(value)


def _validate_cdf(points):
    if not isinstance(points, list) or not points:
        raise ValueError('CDF must be a nonempty list')
    prior = 0.0
    seen = set()
    for item in points:
        if not isinstance(item, (tuple, list)) or len(item) != 2:
            raise ValueError('CDF entries must be [value, cumulative_probability]')
        value, probability = item
        if (value is None or not isinstance(value, (str, int, float, bool))
                or isinstance(value, float) and not math.isfinite(value)):
            raise ValueError('CDF values must be finite JSON scalar values')
        typed_value = (type(value), value)
        if typed_value in seen:
            raise ValueError('CDF outcomes must be distinct')
        seen.add(typed_value)
        if (isinstance(probability, bool)
                or not isinstance(probability, (float, int))
                or not math.isfinite(probability)
                or not prior < probability <= 1):
            raise ValueError('CDF probabilities must strictly increase to 1')
        prior = probability
    if not math.isclose(prior, 1, abs_tol=1e-12):
        raise ValueError('CDF must terminate at 1')


def _draw(points, rng):
    u = rng.random()
    for value, probability in points:
        if u < probability:
            return value
    return points[-1][0]


class ConditionalAttributes:
    """Partially commit attributes of identities without creating Entity objects.

    ``rng_for(identity, attribute)`` returns a fresh, keyed random generator.
    ``external_names`` are already-committed facts supplied on each request,
    for example whether an adult held a fixed formation-time skill quota.
    """

    def __init__(self, specifications, rng_for, external_names=()):
        self.specifications = deepcopy(specifications)
        self._rng_for = rng_for
        self._external = set(external_names)
        self._committed = {}
        if not isinstance(self.specifications, dict):
            raise ValueError('conditional attributes must be a mapping')
        if self._external.intersection(self.specifications):
            raise ValueError('an external attribute cannot also be sampled')
        for name, spec in self.specifications.items():
            if not isinstance(name, str) or not name or not isinstance(spec, dict):
                raise ValueError('attribute names and specifications must be valid')
            parent = spec.get('given')
            if parent is None:
                if set(spec) != {'cdf'}:
                    raise ValueError('unconditional attributes require only cdf')
                _validate_cdf(spec['cdf'])
            else:
                if (not isinstance(parent, str) or parent == name
                        or set(spec) != {'given', 'conditional_cdfs'}
                        or parent not in self._external | self.specifications.keys()):
                    raise ValueError('invalid conditional attribute parent')
                branches = spec['conditional_cdfs']
                if not isinstance(branches, dict) or not branches:
                    raise ValueError('conditional_cdfs must be a nonempty mapping')
                for branch, cdf in branches.items():
                    if not isinstance(branch, str):
                        raise ValueError('conditional branch names must be strings')
                    _validate_cdf(cdf)
        # Detect dependency cycles and absent cases before any individual is sampled.
        visiting, visited = set(), set()

        def visit(name):
            if name in visiting:
                raise ValueError('cyclic conditional attribute dependencies')
            if name in visited or name in self._external:
                return
            visiting.add(name)
            parent = self.specifications[name].get('given')
            if parent is not None:
                visit(parent)
                if parent in self.specifications:
                    parent_spec = self.specifications[parent]
                    parent_cdfs = (parent_spec['conditional_cdfs'].values()
                                   if 'conditional_cdfs' in parent_spec
                                   else [parent_spec['cdf']])
                    keys = {_outcome_key(value) for cdf in parent_cdfs for value, _ in cdf}
                    missing = keys - self.specifications[name]['conditional_cdfs'].keys()
                    if missing:
                        raise ValueError(f'{name}: missing branches for {sorted(missing)}')
                # External values are supplied at runtime; branch validation
                # against their actual values happens before sampling.
            visiting.remove(name)
            visited.add(name)

        for name in self.specifications:
            visit(name)

    def committed(self, identity):
        """Inspect only already-realized attributes; never sample new values."""
        return dict(self._committed.get(identity, {}))

    def resolve(self, identity, name, external=None):
        """Commit one attribute and its dependencies, in any request order."""
        if name not in self.specifications:
            raise ValueError(f'unknown conditional attribute: {name}')
        external = external or {}
        if set(external) - self._external:
            raise ValueError('unexpected external attributes')
        committed = self._committed.setdefault(identity, {})

        def sample(attribute):
            if attribute in external:
                return external[attribute]
            if attribute in committed:
                return committed[attribute]
            if attribute in self._external:
                raise ValueError(f'missing committed external attribute: {attribute}')
            spec = self.specifications[attribute]
            parent = spec.get('given')
            if parent is None:
                points = spec['cdf']
            else:
                key = _outcome_key(sample(parent))
                if key not in spec['conditional_cdfs']:
                    raise ValueError(f'{attribute}: no distribution for parent value {key}')
                points = spec['conditional_cdfs'][key]
            value = _draw(points, self._rng_for(identity, attribute))
            committed[attribute] = value
            return value

        return sample(name)
