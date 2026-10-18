"""Experimental Agent-relative observation and belief; never authoritative reality.

Count reports are deliberately noisy and intentionally *not* Bayesian truth.
They demonstrate incorrect, repeated, and communicated evidence. Future
perception and inference policies can replace this provisional instrument.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

from perception import RangePerception
from spatial.state import CartesianPosition


@dataclass(frozen=True)
class CountReport:
    estimate: int
    uncertainty: int  # inclusive half-width: estimate +/- uncertainty

    def __post_init__(self):
        if not isinstance(self.estimate, int) or not isinstance(self.uncertainty, int):
            raise TypeError("count report requires integers")
        if self.uncertainty < 0:
            raise ValueError("uncertainty must be nonnegative")

    @property
    def interval(self):
        return (max(0, self.estimate - self.uncertainty),
                self.estimate + self.uncertainty)


@dataclass(frozen=True)
class FieldObservation:
    id: str
    observer_id: str
    group_id: str
    time: float
    reported_position: CartesianPosition
    position_uncertainty_m: float
    reports: dict[str, CountReport]
    mode: str


class FieldObserver:
    """Instrument-scaffold: range gates plus controlled errors (not optical vision)."""

    def __init__(self, coarse_range_m, detailed_range_m):
        if not 0 < detailed_range_m <= coarse_range_m:
            raise ValueError("range limits must be positive and ordered")
        self.coarse_range_m = float(coarse_range_m)
        self.detailed_range_m = float(detailed_range_m)

    def observe(self, encounter, observer_id, group, observation_id, *,
                count_bias=None, position_error=(0, 0, 0)):
        """Generate imperfect evidence; sampling objective counts cannot copy guesses.

        The observer must be a placed Being close enough to notice the group.
        Count biases are controlled experimental inputs, not truths about the
        group. They may remain correlated across repeated observations.
        """
        perceived = encounter.perceive(observer_id, RangePerception(self.coarse_range_m))
        if not any(item.target_id == group.id for item in perceived):
            return None
        distance = encounter.distance_between_entities(observer_id, group.id)
        detailed = distance <= self.detailed_range_m
        uncertainty = 1 if detailed else 3
        count_bias = count_bias or {}
        truth = group.counts()
        reports = {
            key: CountReport(max(0, truth[key] + int(count_bias.get(key, 0))), uncertainty)
            for key in ("humans", "livestock", "dogs")
        }
        error = tuple(float(v) for v in position_error)
        if len(error) != 3 or not all(math.isfinite(v) for v in error):
            raise ValueError("position_error must be a finite three-vector")
        location = CartesianPosition(*(value + delta for value, delta in zip(
            group.get_position().as_tuple(), error)))
        return FieldObservation(observation_id, observer_id, group.id,
                                encounter.time, location, 15.0 if detailed else 80.0,
                                reports, "detailed_range_proxy" if detailed else "coarse_range_proxy")


class BeliefLedger:
    """An Agent's evidence with provenance; never edits the observed Entity.

    Inferred count estimates are illustrative summaries only. Contradictions
    are retained as investigation targets instead of silently reconciled.
    """
    def __init__(self, observer_id):
        self.observer_id = observer_id
        self._evidence = {}
        self.communication_log = []

    @property
    def evidence(self):
        return tuple(self._evidence.values())

    def learn(self, observation, *, communicated_by=None):
        if not isinstance(observation, FieldObservation):
            raise TypeError("evidence must be a FieldObservation")
        if observation.id in self._evidence:
            if self._evidence[observation.id] != observation:
                raise ValueError("observation ID conflicts with existing evidence")
            return False
        self._evidence[observation.id] = observation
        if communicated_by is not None:
            self.communication_log.append((observation.id, communicated_by))
        return True

    def share_from(self, other):
        """Exchange original evidence, not an assertion that the other's belief is fact."""
        return sum(self.learn(e, communicated_by=other.observer_id)
                   for e in other.evidence)

    def count_estimate(self, group_id, category):
        """Uncalibrated weighted evidence summary; *not* a posterior distribution."""
        reports = [e.reports[category] for e in self.evidence
                   if e.group_id == group_id and category in e.reports]
        if not reports:
            return None
        weights = [1 / (1 + report.uncertainty)**2 for report in reports]
        return sum(r.estimate * w for r, w in zip(reports, weights)) / sum(weights)

    def discrepancies(self, group_id):
        """Return count disagreements with nonoverlapping reported intervals."""
        group_evidence = [e for e in self.evidence if e.group_id == group_id]
        conflicts = []
        for i, first in enumerate(group_evidence):
            for other in group_evidence[i + 1:]:
                for key in sorted(first.reports.keys() & other.reports.keys()):
                    lo1, hi1 = first.reports[key].interval
                    lo2, hi2 = other.reports[key].interval
                    if hi1 < lo2 or hi2 < lo1:
                        conflicts.append((key, first.id, other.id))
        return conflicts

    def estimated_velocity(self, group_id, observer_id=None):
        """Two sightings of the *same observer* provide crude average velocity."""
        observer_id = self.observer_id if observer_id is None else observer_id
        entries = sorted((e for e in self.evidence if e.group_id == group_id
                          and e.observer_id == observer_id), key=lambda e: e.time)
        if len(entries) < 2 or entries[-1].time == entries[0].time:
            return None
        dt = entries[-1].time - entries[0].time
        return tuple((b - a) / dt for a, b in zip(
            entries[0].reported_position.as_tuple(),
            entries[-1].reported_position.as_tuple()))

    def predict_position(self, group_id, future_time):
        """Uncertain straight-line extrapolation from this Scout's own sightings.

        Does not consult the true group motion. Deliberately omits uncertainty
        growth and acceleration; it is a *belief*, not a physically assured path.
        """
        entries = sorted((e for e in self.evidence if e.group_id == group_id
                          and e.observer_id == self.observer_id), key=lambda e: e.time)
        velocity = self.estimated_velocity(group_id)
        if not entries or velocity is None:
            return None
        latest = entries[-1]
        future_time = float(future_time)
        if not math.isfinite(future_time) or future_time < latest.time:
            raise ValueError("predicted time must be finite and not precede last sighting")
        dt = future_time - latest.time
        return CartesianPosition(*(p + v * dt for p, v in zip(
            latest.reported_position.as_tuple(), velocity)))
