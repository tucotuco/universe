"""Minimal evidence-based skill practice and progression for Universe.

An action determines which skills were actually exercised and how much
experience to award.  Recording an exercise does not infer use from an
Action's *required* skill, which is merely a prerequisite.
"""
from dataclasses import dataclass


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
