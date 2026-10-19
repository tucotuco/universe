"""Bounded question-driven realization for a local planetary solar cycle.

This is a deliberately reduced, circular-orbit/flat-horizon model. It does not
assert a complete planetary ephemeris or replace ``planetary_system``. Known
parameters and world-imposed conditions constrain previews; only a deliberate
commit changes objective state. Inspection and previews are non-mutating.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import random
from typing import Mapping

# Declared physical/design priors, not silently assumed objective world facts.
PRIORS = {
    'solar_day_hours': (12.0, 40.0),
    'axial_tilt_deg': (0.0, 50.0),
    'season_phase_deg': (0.0, 360.0),  # 0 = northern winter solstice
    'hour_angle_deg': (-180.0, 180.0),  # 0 = local apparent noon
    'orbital_year_days': (180.0, 800.0),
    'sidereal_rotation_hours': (6.0, 60.0),
}
QUERIES = ('daylight_hours', 'time_to_sunset_hours')
CONDITIONS = ('solar_day_hours', 'daylight_hours', 'time_to_sunset_hours')


def _number(label, value):
    if isinstance(value, bool):
        raise ValueError(f'{label} must be a finite number')
    try:
        value = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f'{label} must be a finite number') from exc
    if not math.isfinite(value):
        raise ValueError(f'{label} must be a finite number')
    return value


def _check_value(key, value):
    if key not in PRIORS:
        raise ValueError(f'Unknown solar design parameter: {key}')
    v = _number(key, value)
    if key in ('solar_day_hours', 'sidereal_rotation_hours', 'orbital_year_days') and v <= 0:
        raise ValueError(f'{key} must be positive')
    if key == 'axial_tilt_deg' and not 0 <= v <= 90:
        raise ValueError('axial_tilt_deg must be between 0 and 90')
    return v


def _latitude(value):
    value = _number('latitude_deg', value)
    if not -90 <= value <= 90:
        raise ValueError('latitude_deg must be between -90 and 90')
    return value


def _angle(value):
    return (value + 180.0) % 360.0 - 180.0


def _derived_solar_day(values):
    solar = values.get('solar_day_hours')
    sidereal, year = values.get('sidereal_rotation_hours'), values.get('orbital_year_days')
    if sidereal is not None and year is not None:
        rate = 1.0 / sidereal - 1.0 / (year * 24.0)
        if rate <= 0:
            raise ValueError('Solar model requires prograde spin faster than orbital motion')
        derived = 1.0 / rate
        if solar is not None and not math.isclose(solar, derived, rel_tol=1e-8, abs_tol=1e-8):
            raise ValueError('Declared solar day contradicts sidereal rotation and orbital year')
        return derived
    return solar


def _requirements(query, time_s, values):
    if query not in QUERIES:
        raise ValueError(f'Unknown planetary demand: {query}')
    required = ['axial_tilt_deg', 'season_phase_deg']
    if values.get('solar_day_hours') is None and (
            values.get('sidereal_rotation_hours') is not None
            and values.get('orbital_year_days') is not None):
        required[:0] = ['sidereal_rotation_hours', 'orbital_year_days']
    else:
        required.insert(0, 'solar_day_hours')
    if query == 'time_to_sunset_hours':
        required.append('hour_angle_deg')
    if time_s != 0:
        required.append('orbital_year_days')
    return tuple(dict.fromkeys(required))


def _calculate(query, values, latitude_deg, time_s):
    """Approximate circular orbit and fixed-season-day local sky.

    This is a mean-solar-rate approximation: terrain, atmosphere, refraction,
    elliptical orbital speed and seasonal drift within a single day are absent.
    """
    day = _derived_solar_day(values)
    if day is None:
        raise ValueError('Solar day not resolved')
    if 'axial_tilt_deg' not in values or 'season_phase_deg' not in values:
        raise ValueError('Solar declination not resolved')
    year = values.get('orbital_year_days')
    if time_s != 0 and year is None:
        raise ValueError('Orbital year required to advance the seasonal phase')
    phase = math.radians(values['season_phase_deg'] + (360.0 * time_s / (year * 86400.0) if year else 0))
    tilt = math.radians(values['axial_tilt_deg'])
    decl = math.asin(-math.sin(tilt) * math.cos(phase))
    lat = math.radians(latitude_deg)
    sin_alt_noon = math.sin(lat)*math.sin(decl) + math.cos(lat)*math.cos(decl)
    a = math.sin(lat)*math.sin(decl)
    b = math.cos(lat)*math.cos(decl)
    if abs(b) < 1e-12:
        fraction = 1.0 if a > 1e-12 else 0.0 if a < -1e-12 else 0.5
    else:
        x = -a/b
        fraction = 1.0 if x <= -1 else 0.0 if x >= 1 else math.acos(x)/math.pi
    daylight = day * fraction
    result = {'solar_day_hours': day, 'daylight_hours': daylight,
              'sun_declination_deg': math.degrees(decl), 'solar_noon_altitude_deg': math.degrees(math.asin(min(1.0, sin_alt_noon))),
              'sun_altitude_deg': None, 'time_to_sunset_hours': None, 'sunset_status': 'not_requested'}
    if query == 'time_to_sunset_hours':
        if 'hour_angle_deg' not in values:
            raise ValueError('Local solar hour angle not resolved')
        hour = _angle(values['hour_angle_deg'] + time_s / (day * 3600.0) * 360.0)
        sun_sin = a + b * math.cos(math.radians(hour))
        result['sun_altitude_deg'] = math.degrees(math.asin(max(-1.0, min(1.0, sun_sin))))
        if fraction == 1.0:
            result['sunset_status'] = 'polar_day_no_sunset_under_fixed_season_approximation'
        elif fraction == 0.0:
            result['sunset_status'] = 'polar_night_no_sunset_under_fixed_season_approximation'
        else:
            sunset_angle = 180.0 * fraction
            elapsed = (sunset_angle - hour) % 360.0
            result['time_to_sunset_hours'] = day * elapsed / 360.0
            result['sunset_status'] = 'approximate'
    return result


@dataclass(frozen=True)
class Proposal:
    query: str
    latitude_deg: float
    time_s: float
    revision: int
    candidate_index: int
    parameters: tuple
    answer: dict
    newly_realized: tuple

    def as_dict(self):
        return {'query': self.query, 'latitude_deg': self.latitude_deg, 'time_s': self.time_s,
                'revision': self.revision, 'candidate_index': self.candidate_index,
                'parameters': dict(self.parameters), 'answer': dict(self.answer),
                'newly_realized': list(self.newly_realized)}


class PlanetaryDesign:
    """A small, explicit query/preview/commit boundary for planetary daylight.

    It solves no general inverse problem. Bounded sampling enforces directly
    evaluable world conditions; an unsatisfied request fails without commitment.
    """

    def __init__(self, known=None, conditions=None, seed=801, priors=None):
        self.seed = int(seed)
        self.known = {k: _check_value(k, v) for k, v in (known or {}).items()}
        self.priors = dict(PRIORS)
        for k, bounds in (priors or {}).items():
            if k not in PRIORS or len(bounds) != 2:
                raise ValueError('Unknown or invalid prior')
            low, high = _check_value(k, bounds[0]), _check_value(k, bounds[1])
            if low > high:
                raise ValueError('Invalid prior bounds')
            self.priors[k] = (low, high)
        _derived_solar_day(self.known)
        self.conditions = []
        self.commits = []
        self.revision = 0
        for condition in conditions or []:
            self.add_condition(condition)

    def _condition(self, raw):
        metric = raw.get('metric')
        if metric not in CONDITIONS:
            raise ValueError(f'Unsupported world condition: {metric}')
        condition = {'metric': metric,
                     'target': _number('target', raw['target']),
                     'tolerance': _number('tolerance', raw['tolerance']),
                     'latitude_deg': _latitude(raw.get('latitude_deg', 40)),
                     'time_s': _number('time_s', raw.get('time_s', 0))}
        if condition['tolerance'] < 0:
            raise ValueError('Tolerance cannot be negative')
        return condition

    def _check_conditions(self, values):
        _derived_solar_day(values)
        for cond in self.conditions:
            metric = cond['metric']
            if metric == 'solar_day_hours':
                number = _derived_solar_day(values)
            else:
                needed = _requirements(metric, cond['time_s'], values)
                if any(k not in values for k in needed):
                    continue
                number = _calculate(metric, values, cond['latitude_deg'], cond['time_s'])[metric]
            if number is not None and abs(number-cond['target']) > cond['tolerance'] + 1e-9:
                raise ValueError(f"Contradicts imposed condition: {metric}={cond['target']}±{cond['tolerance']}")

    def add_condition(self, raw):
        condition = self._condition(raw)
        self.conditions.append(condition)
        try:
            self._check_conditions(self.known)
        except (ValueError, ArithmeticError):
            self.conditions.pop()
            raise
        self.revision += 1
        return dict(condition)

    def inspect(self, query, latitude_deg=40, time_s=0):
        lat = _latitude(latitude_deg)
        time = _number('time_s', time_s)
        required = _requirements(query, time, self.known)
        missing = [k for k in required if k not in self.known]
        value = _calculate(query, self.known, lat, time) if not missing else None
        return {'query': query, 'latitude_deg': lat, 'time_s': time,
                'required': list(required), 'missing': missing, 'answer': value,
                'known': dict(self.known), 'conditions': list(self.conditions), 'revision': self.revision}

    def _rng(self, index, attempt, key):
        data = f'{self.seed}|{index}|{attempt}|{key}'.encode('utf-8')
        return random.Random(int.from_bytes(hashlib.sha256(data).digest(), 'big'))

    def _draw(self, key, index, attempt):
        low, high = self.priors[key]
        if key == 'solar_day_hours':
            # Inverse propagation of direct measured/required day-length bands.
            for cond in self.conditions:
                if cond['metric'] == key:
                    low = max(low, cond['target']-cond['tolerance'])
                    high = min(high, cond['target']+cond['tolerance'])
        if low > high:
            raise ValueError(f'No admissible {key} under the known constraints and priors')
        return self._rng(index, attempt, key).uniform(low, high)

    def preview(self, query='time_to_sunset_hours', latitude_deg=40, time_s=0, trial=None,
                candidate_index=0, max_attempts=1500):
        lat = _latitude(latitude_deg)
        time = _number('time_s', time_s)
        trial = {k: _check_value(k, v) for k, v in (trial or {}).items()}
        for k, v in trial.items():
            if k in self.known and not math.isclose(self.known[k], v, rel_tol=1e-12, abs_tol=1e-12):
                raise ValueError(f'{k} is already committed and cannot be changed in preview')
        required = _requirements(query, time, dict(self.known, **trial))
        for attempt in range(max_attempts):
            candidate = dict(self.known, **trial)
            for k in required:
                if k not in candidate:
                    candidate[k] = self._draw(k, candidate_index, attempt)
            try:
                self._check_conditions(candidate)
                answer = _calculate(query, candidate, lat, time)
            except (ValueError, ArithmeticError):
                continue
            additions = tuple(k for k in required if k not in self.known)
            return Proposal(query, lat, time, self.revision, int(candidate_index),
                            tuple(sorted(candidate.items())), answer, additions)
        raise ValueError('No admissible candidate found within the sampling budget; relax conditions or refine priors')

    def commit(self, proposal):
        if proposal.revision != self.revision:
            raise ValueError('Stale proposal: world conditions or commitments changed')
        values = dict(proposal.parameters)
        for k, v in self.known.items():
            if not math.isclose(values.get(k, float('nan')), v, rel_tol=1e-12, abs_tol=1e-12):
                raise ValueError('Proposal conflicts with committed reality')
        additions = {k: values[k] for k in proposal.newly_realized}
        if any(k in self.known for k in additions):
            raise ValueError('Proposal attempts to re-commit an established parameter')
        updated = dict(self.known, **additions)
        self._check_conditions(updated)
        verified = _calculate(proposal.query, updated, proposal.latitude_deg, proposal.time_s)
        if verified != proposal.answer:
            raise ValueError('Proposal answer is inconsistent with the committed parameters')
        if additions:
            self.known = updated
            self.commits.append({'revision': self.revision+1, 'query': proposal.query,
                                 'latitude_deg': proposal.latitude_deg, 'time_s': proposal.time_s,
                                 'parameters': dict(additions)})
            self.revision += 1
        return dict(additions)

    def export(self):
        return {'format': 'universe.planetary-solar-design', 'version': 1, 'seed': self.seed,
                'known': dict(self.known), 'conditions': list(self.conditions),
                'priors': {k: list(v) for k, v in self.priors.items()},
                'commits': list(self.commits), 'revision': self.revision}

    @classmethod
    def restore(cls, data):
        if data.get('format') != 'universe.planetary-solar-design' or data.get('version') != 1:
            raise ValueError('Unsupported planetary design format')
        obj = cls(known=data['known'], conditions=data['conditions'],
                  seed=data['seed'], priors=data['priors'])
        # Preserve provenance, but reject malformed claimed revision histories.
        commits = data.get('commits', [])
        if not isinstance(commits, list) or any(not isinstance(x, dict) for x in commits):
            raise ValueError('Invalid design commitments')
        if not isinstance(data.get('revision'), int) or data['revision'] < len(commits)+len(obj.conditions):
            raise ValueError('Invalid design revision')
        obj.commits = commits
        obj.revision = data['revision']
        return obj
