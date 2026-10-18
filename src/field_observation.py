"""Experimental Agent-relative observation and belief; never authoritative reality.

Count reports are deliberately noisy and intentionally *not* Bayesian truth.
They demonstrate incorrect, repeated, and communicated evidence. Future
perception and inference policies can replace this provisional instrument.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
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
    dubious_candidates: dict[str, int] = field(default_factory=dict)
    # Raw, potentially misclassified candidate counts. These cues suggest
    # suspect candidates; they do not reveal objective species identity.


class FieldObserver:
    """Instrument-scaffold: range gates plus controlled errors (not optical vision)."""

    def __init__(self, coarse_range_m, detailed_range_m):
        if not 0 < detailed_range_m <= coarse_range_m:
            raise ValueError("range limits must be positive and ordered")
        self.coarse_range_m = float(coarse_range_m)
        self.detailed_range_m = float(detailed_range_m)

    def observe(self, encounter, observer_id, group, observation_id, *,
                count_bias=None, position_error=(0, 0, 0),
                dubious_candidates=None):
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
        dubious_candidates = {} if dubious_candidates is None else dict(dubious_candidates)
        for category, count in dubious_candidates.items():
            if category not in reports or isinstance(count, bool) or not isinstance(count, int) \
                    or count < 0 or count > reports[category].estimate:
                raise ValueError("dubious candidate count must fit a reported category")
        error = tuple(float(v) for v in position_error)
        if len(error) != 3 or not all(math.isfinite(v) for v in error):
            raise ValueError("position_error must be a finite three-vector")
        location = CartesianPosition(*(value + delta for value, delta in zip(
            group.get_position().as_tuple(), error)))
        return FieldObservation(observation_id, observer_id, group.id,
                                encounter.time, location, 15.0 if detailed else 80.0,
                                reports, "detailed_range_proxy" if detailed else "coarse_range_proxy",
                                dubious_candidates)


@dataclass(frozen=True)
class BeliefRevision:
    """A dated snapshot of one Agent's estimate, not a claim about reality.

    ``time=None`` means the acquisition time was not supplied. Revision order
    always follows the ledger append order; it is not an inferred world time.
    """
    group_id: str
    category: str
    estimate: float
    evidence_ids: tuple[str, ...]
    trigger: str  # observation, communication, or reinterpretation
    time: float | None
    disputed: bool
    trigger_observation_id: str


@dataclass(frozen=True)
class EvidenceReassessment:
    """A later reading of one's own evidence; original interpretation survives."""
    observation_id: str
    time: float | None
    interpretation: object  # FieldInterpretation; avoid module import cycle


def _valid_history_time(time):
    if time is None:
        return None
    if isinstance(time, bool) or not isinstance(time, (int, float)) or not math.isfinite(time):
        raise ValueError("history time must be finite or None")
    return float(time)


class BeliefLedger:
    """An Agent's evidence with provenance; never edits the observed Entity.

    Inferred count estimates are illustrative summaries only. Contradictions
    are retained as investigation targets instead of silently reconciled.
    """
    def __init__(self, observer_id):
        self.observer_id = observer_id
        self._evidence = {}
        self._interpretations = {}
        self._reassessments = []
        self._current_reassessments = {}
        self._belief_history = []
        self.communication_log = []

    @property
    def evidence(self):
        return tuple(self._evidence.values())

    @property
    def belief_history(self):
        """Chronological acquisition/reassessment snapshots (append-only)."""
        return tuple(self._belief_history)

    @property
    def reassessments(self):
        return tuple(self._reassessments)

    def interpretation_for(self, observation_id):
        """Original interpretation at the time of observation; never revised."""
        return self._interpretations.get(observation_id)

    def current_interpretation_for(self, observation_id):
        """Owner's most recent re-reading, else source's original reading."""
        return self._current_reassessments.get(observation_id,
                                                self.interpretation_for(observation_id))

    def _reports_for(self, observation):
        interpretation = self.current_interpretation_for(observation.id)
        return interpretation.reports if interpretation is not None else observation.reports

    def learn(self, observation, *, communicated_by=None, interpretation=None,
              at_time=None):
        if not isinstance(observation, FieldObservation):
            raise TypeError("evidence must be a FieldObservation")
        at_time = _valid_history_time(at_time)
        if at_time is not None and at_time < observation.time:
            raise ValueError("cannot acquire evidence before it was observed")
        if interpretation is not None:
            from field_interpretation import FieldInterpretation
            if not isinstance(interpretation, FieldInterpretation) or \
                    interpretation.observation_id != observation.id or \
                    interpretation.observer_id != observation.observer_id:
                raise ValueError("interpretation must belong to the original observer and evidence")
        if observation.id in self._evidence:
            if (self._evidence[observation.id] != observation or
                    (interpretation is not None and
                     self._interpretations.get(observation.id) != interpretation)):
                raise ValueError("observation ID conflicts with existing evidence")
            return False
        self._evidence[observation.id] = observation
        if interpretation is not None:
            self._interpretations[observation.id] = interpretation
        if communicated_by is not None:
            self.communication_log.append((observation.id, communicated_by))
        self._record_belief(observation.group_id,
                            "communication" if communicated_by is not None else "observation",
                            observation.time if at_time is None and communicated_by is None else at_time,
                            observation.id)
        return True

    def share_from(self, other, *, at_time=None):
        """Exchange source evidence/interpretations, preserving source provenance."""
        if not isinstance(other, BeliefLedger):
            raise TypeError("can share only another BeliefLedger")
        at_time = _valid_history_time(at_time)
        return sum(self.learn(e, communicated_by=other.observer_id,
                              interpretation=other.interpretation_for(e.id),
                              at_time=at_time)
                   for e in other.evidence)

    def _record_belief(self, group_id, trigger, time, observation_id):
        relevant = [e for e in self.evidence if e.group_id == group_id]
        categories = sorted(set().union(*(self._reports_for(e).keys() for e in relevant)))
        conflicts = {category for category, _, _ in self.discrepancies(group_id)}
        for category in categories:
            sources = tuple(e.id for e in relevant if category in self._reports_for(e))
            self._belief_history.append(BeliefRevision(
                group_id, category, self.count_estimate(group_id, category),
                sources, trigger, time, category in conflicts, observation_id))

    def reconsider(self, observation_id, observer, interpreter, *, at_time=None):
        """Reinterpret an original personal observation using present skill.

        Neither raw evidence nor historical/source interpretation changes.
        Shared evidence cannot be presented as one's own sighting. No XP is
        awarded merely for reading evidence again.
        """
        at_time = _valid_history_time(at_time)
        observation = self._evidence.get(observation_id)
        if observation is None:
            raise KeyError(observation_id)
        if observer.id != self.observer_id or observation.observer_id != observer.id:
            raise ValueError("only the original observer may reconsider own evidence")
        if at_time is not None and at_time < observation.time:
            raise ValueError("reassessment cannot precede observation")
        from field_interpretation import FieldInterpreter
        if not isinstance(interpreter, FieldInterpreter):
            raise TypeError("interpreter must be a FieldInterpreter")
        new = interpreter.interpret(observation, observer)
        if new == self.current_interpretation_for(observation_id):
            return False
        self._current_reassessments[observation_id] = new
        self._reassessments.append(EvidenceReassessment(observation_id, at_time, new))
        self._record_belief(observation.group_id, "reinterpretation", at_time,
                            observation_id)
        return True

    def to_dict(self):
        """Portable representation of evidence and all belief change provenance.

        The source observation and initial interpretation are retained even if
        the present assessment has changed. This is an export, not a loader.
        """
        return {
            "observer_id": self.observer_id,
            "evidence": [asdict(e) for e in self.evidence],
            "original_interpretations": {
                key: asdict(value) for key, value in self._interpretations.items()},
            "reassessments": [asdict(entry) for entry in self.reassessments],
            "belief_history": [asdict(entry) for entry in self.belief_history],
            "communication_log": list(self.communication_log),
        }

    def count_estimate(self, group_id, category):
        """Uncalibrated weighted evidence summary; *not* a posterior distribution."""
        reports = [self._reports_for(e)[category] for e in self.evidence
                   if e.group_id == group_id and category in self._reports_for(e)]
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
                a, b = self._reports_for(first), self._reports_for(other)
                for key in sorted(a.keys() & b.keys()):
                    lo1, hi1 = a[key].interval
                    lo2, hi2 = b[key].interval
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
