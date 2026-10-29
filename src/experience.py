"""Minimal evidence-based skill practice and progression for Universe.

An action determines which skills were actually exercised, how much experience
to award, and optional direct observations. Recording practice does not infer
use from an Action's *required* skill, which is merely a prerequisite.
"""
from dataclasses import dataclass

from perception import Perception


@dataclass(frozen=True)
class SkillExercise:
    """One explicitly exercised skill and its resolver-assigned XP award."""

    skill_name: str
    experience: int = 0

    def __post_init__(self):
        if not isinstance(self.skill_name, str) or not self.skill_name.strip():
            raise ValueError("skill_name must be a nonempty string")
        if isinstance(self.experience, bool) or not isinstance(self.experience, int) or self.experience < 0:
            raise ValueError("experience must be a nonnegative integer")

    def to_dict(self):
        return {"skill_name": self.skill_name, "experience": self.experience}


@dataclass(frozen=True)
class ActionResolution:
    """An Action resolver's outcome, actual skill use, and observations.

    An Action's required_skill is a prerequisite, not practice evidence.
    Observations are declarative; Encounter validates and applies awareness.
    """

    outcome: str
    skill_exercises: tuple = ()
    observations: tuple = ()

    def __post_init__(self):
        if not isinstance(self.outcome, str) or not self.outcome.strip():
            raise ValueError("outcome must be a nonempty string")
        try:
            exercises = tuple(self.skill_exercises)
        except TypeError as exc:
            raise TypeError("skill_exercises must be iterable") from exc
        if any(not isinstance(item, SkillExercise) for item in exercises):
            raise TypeError("skill_exercises must contain SkillExercise objects")
        names = [item.skill_name for item in exercises]
        if len(names) != len(set(names)):
            raise ValueError("a skill may be recorded only once per Action")
        object.__setattr__(self, "skill_exercises", exercises)
        try:
            observations = tuple(self.observations)
        except TypeError as exc:
            raise TypeError("observations must be iterable") from exc
        if any(not isinstance(observation, Perception) for observation in observations):
            raise TypeError("observations must contain Perception records")
        object.__setattr__(self, "observations", observations)

    def to_dict(self):
        data = {"outcome": self.outcome,
                "skill_exercises": [item.to_dict() for item in self.skill_exercises]}
        if self.observations:
            data["observations"] = [vars(item).copy() for item in self.observations]
        return data




@dataclass(frozen=True)
class SkillUse:
    """An Agent-relative history entry linked to a completed Action where possible."""

    skill_name: str
    experience: int
    level_before: int
    level_after: int
    action_id: str = None
    time: float = None
    outcome: str = None

    def to_dict(self):
        return {
            'skill_name': self.skill_name,
            'experience': self.experience,
            'level_before': self.level_before,
            'level_after': self.level_after,
            'action_id': self.action_id,
            'time': self.time,
            'outcome': self.outcome,
        }


def level_from_practice(baseline_level, experience, cost_per_rank=250):
    """Progressive rank after earned practice, using the draft's XP curve.

    Rank n costs ``n * cost_per_rank`` experience.  Experience here is
    practice earned *since the Being's baseline level*, not historical
    experience already represented by its definition.
    """
    level = baseline_level
    remaining = experience
    while remaining >= (level + 1) * cost_per_rank:
        remaining -= (level + 1) * cost_per_rank
        level += 1
    return level


@dataclass(frozen=True)
class BatchSkillUse:
    """One Target-owned simultaneous transition; exercises retain all causes.

    Deliberately no per-Action before/after ranks. Legacy history readers can
    use the shared transition fields; persistence requires separate 5C3 work.
    """
    being_id: str
    skill_name: str
    experience: int
    level_before: int
    level_after: int
    time: int
    exercises: tuple
    action_id: None = None
    outcome: str = 'simultaneous'

    def to_dict(self):
        raise ValueError('Batch skill history requires a separately authorized checkpoint migration')


def practice_action_ids(use):
    """Source IDs without fabricating sequential per-Action rank transitions."""
    return tuple(x.action_id for x in use.exercises) if type(use) is BatchSkillUse else (() if use.action_id is None else (use.action_id,))
