"""Skill-dependent, fallible interpretation of observational evidence.

The observer has access only to FieldObservation evidence, never to the
StatisticalGroup or its objective counts. Dubious candidate cues are merely
reported features: skilled skepticism can help or hurt, depending on whether
the cues are reliable. This is an explicit experimental policy, not vision AI.
"""
from dataclasses import dataclass

from field_observation import CountReport, FieldObservation


@dataclass(frozen=True)
class FieldInterpretation:
    observation_id: str
    observer_id: str
    skill_name: str
    skill_level: int
    reports: dict[str, CountReport]
    rejected_candidates: dict[str, int]


class FieldInterpreter:
    """Discount suspiciously classified candidates according to `spot` rank.

    Full discount at `expert_level`; novice ranks discount proportionally.
    No check against true Entity composition is permitted. The cue heuristic
    can be wrong, which is why the source observations must be retained.
    """

    def __init__(self, skill_name="spot", expert_level=5):
        if not isinstance(expert_level, int) or isinstance(expert_level, bool) or expert_level < 1:
            raise ValueError("expert_level must be a positive integer")
        self.skill_name = skill_name
        self.expert_level = expert_level

    def interpret(self, observation, observer):
        if not isinstance(observation, FieldObservation):
            raise TypeError("expected FieldObservation")
        if observation.observer_id != observer.id:
            raise ValueError("only the original observer may directly interpret its own sighting")
        level = observer.get_skill_level(self.skill_name)
        if isinstance(level, bool) or not isinstance(level, int) or level < 0:
            raise ValueError("invalid observer skill level")
        fraction = min(level / self.expert_level, 1.0)
        reports, rejected = {}, {}
        for category, report in observation.reports.items():
            dubious = observation.dubious_candidates.get(category, 0)
            reduction = round(dubious * fraction)
            rejected[category] = reduction
            reports[category] = CountReport(report.estimate - reduction,
                                            report.uncertainty)
        return FieldInterpretation(observation.id, observation.observer_id,
                                   self.skill_name, level, reports, rejected)
