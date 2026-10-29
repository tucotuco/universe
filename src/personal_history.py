"""Opt-in, constraint-checked retrospective realization of a Being's life.

The Being's mutable current state and recorded skill uses remain authoritative.
This ledger commits only requested historical detail; it does not simulate the
intervals between facts, infer memories, or produce Agent perceptions.
"""
from __future__ import annotations

import math

from realization import Fact, FactKey, ImpossibleRealization, RealityLedger


class PersonalHistory:
    """Partial objective history tied to one existing BeingInstance.

    Only skills explicitly in ``nondeclining_skills`` use a monotonic rank rule.
    The model does not claim that all skills are permanent; skill decay and
    retraining require a different domain constraint.
    """

    def __init__(self, being, *, earliest, known_through, nondeclining_skills=()):
        self.being = being
        self.earliest = self._finite(earliest)
        self.known_through = self._finite(known_through)
        if self.earliest > self.known_through:
            raise ValueError("earliest exceeds known_through")
        skills = tuple(nondeclining_skills)
        if any(not isinstance(skill, str) or not skill.strip() for skill in skills):
            raise ValueError("skill names must be nonempty strings")
        self.nondeclining_skills = frozenset(skills)
        self.reality = RealityLedger((self._validate,))

    @staticmethod
    def _finite(value):
        if (isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(value)):
            raise ValueError("time must be a finite number")
        return float(value)

    def _at(self, time):
        time = self._finite(time)
        if not self.earliest <= time <= self.known_through:
            raise ValueError("time outside established historical inquiry window")
        return time

    def episode_key(self, time, topic):
        if not isinstance(topic, str) or not topic.strip():
            raise ValueError("episode topic must be a nonempty string")
        return FactKey(self.being.id, "episode", self._at(time), topic)

    def skill_key(self, time, skill):
        if skill not in self.nondeclining_skills:
            raise ValueError("this skill has no historical non-decline model")
        return FactKey(self.being.id, "skill_rank", self._at(time), skill)

    def inspect_episode(self, time, topic):
        """Inspect committed history without resolving an episode."""
        return self.reality.inspect(self.episode_key(time, topic))

    def facts_at(self, time):
        """Committed facts at a particular time; no interpolation or sampling."""
        return self.reality.view().facts_at(self.being.id, self._at(time))

    def realize_episode(self, time, topic, propose):
        """Ask for an episode; validate the complete proposal before commitment.

        The callback receives a defensive RealityView and returns Fact objects.
        For a training episode, commit a matching skill_rank fact atomically.
        The recorded result describes objective history, NOT anyone's memory.
        """
        return self.reality.ask(self.episode_key(time, topic), propose)

    def commit_skill_rank(self, time, skill, rank, *, origin="historical_evidence"):
        """Commit explicitly supported historical rank, not a guessed present rank."""
        return self.reality.commit((Fact(self.skill_key(time, skill), rank, origin),))

    def _validate(self, view, additional_skill_use=()):
        from frozen_practice import validate_history_constraints
        validate_history_constraints(self.being.id, self.earliest, self.known_through,
            self.nondeclining_skills, view.all_facts(),
            (*self.being.skill_use_history, *additional_skill_use))

    def validate_future_skill_use(self, proposed_use):
        """Reject a newly recorded skill use that would invalidate committed past.

        Runs before BeingInstance mutates current capability or skill history.
        Undated skill uses do not claim a time-specific historical relationship.
        """
        if self.reality.revision and proposed_use.skill_name in self.nondeclining_skills:
            self._validate(self.reality.view(), (proposed_use,))

    def to_jsonable(self):
        return {
            "being_id": self.being.id,
            "earliest": self.earliest,
            "known_through": self.known_through,
            "nondeclining_skills": sorted(self.nondeclining_skills),
            "facts": self.reality.to_jsonable(),
        }

    @classmethod
    def from_jsonable(cls, being, data):
        if not isinstance(data, dict) or data.get("being_id") != being.id:
            raise ValueError("personal history belongs to a different Being")
        history = cls(being, earliest=data["earliest"],
                      known_through=data["known_through"],
                      nondeclining_skills=data["nondeclining_skills"])
        history.reality = RealityLedger.from_jsonable(data["facts"], (history._validate,))
        return history
