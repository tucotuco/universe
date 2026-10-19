"""Small experimental contract for committing partially realized objective reality.

This module is deliberately *not* an observer, belief system, or simulation
engine. An inquiry can trigger realization, but its returned objective fact
must still pass through a separate perception/communication model before an
Agent may know it.

Domain constraints are supplied as pure validators of a proposed whole state.
Their job is to reject invalid proposals, not silently repair prior facts.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
import math
from typing import Callable, Iterable


class ImpossibleRealization(ValueError):
    """A proposed addition contradicts a committed fact or domain constraint."""


@dataclass(frozen=True)
class FactKey:
    entity_id: str
    attribute: str
    time: float | None = None
    detail: str = ""

    def __post_init__(self):
        if not isinstance(self.entity_id, str) or not self.entity_id.strip():
            raise ValueError("entity_id must be a nonempty string")
        if not isinstance(self.attribute, str) or not self.attribute.strip():
            raise ValueError("attribute must be a nonempty string")
        if not isinstance(self.detail, str):
            raise ValueError("detail must be a string")
        if self.time is not None:
            if (isinstance(self.time, bool) or not isinstance(self.time, (int, float))
                    or not math.isfinite(self.time)):
                raise ValueError("time must be finite when specified")
            object.__setattr__(self, "time", float(self.time))


@dataclass(frozen=True)
class Fact:
    """One proposed objective claim. Values must be JSON-compatible."""
    key: FactKey
    value: object
    origin: str = "generated"


@dataclass(frozen=True)
class CommittedFact:
    key: FactKey
    value: object
    origin: str
    revision: int  # commitment order, not the in-world time of the fact


@dataclass(frozen=True)
class InquiryResult:
    record: CommittedFact
    newly_realized: bool


class RealityView:
    """Defensive, read-only-style snapshot visible to generators/validators."""

    def __init__(self, records):
        self._records = deepcopy(records)

    def contains(self, key: FactKey) -> bool:
        return key in self._records

    def get(self, key: FactKey):
        """Return a committed value, or None if absent (use contains for null)."""
        record = self._records.get(key)
        return deepcopy(record.value) if record is not None else None

    def fact(self, key: FactKey) -> CommittedFact | None:
        record = self._records.get(key)
        return deepcopy(record) if record is not None else None

    def facts_at(self, entity_id: str, time: float | None):
        """Facts explicitly committed at a time; does NOT interpolate."""
        return tuple(deepcopy(rec) for rec in self._records.values()
                     if rec.key.entity_id == entity_id and rec.key.time == time)

    def all_facts(self):
        return tuple(deepcopy(record) for record in self._records.values())


class RealityLedger:
    """Atomic, constraint-checked commitment of objective facts.

    The ledger is an experiment in realization semantics, not a replacement for
    the existing Universe state/Group registries. A future integration must
    establish a single authoritative store rather than copying live state.
    """

    def __init__(self, validators: Iterable[Callable[[RealityView], None]] = ()):
        self._records: dict[FactKey, CommittedFact] = {}
        self._revision = 0
        self._validators = tuple(validators)

    @property
    def revision(self) -> int:
        return self._revision

    def view(self) -> RealityView:
        return RealityView(self._records)

    def inspect(self, key: FactKey) -> CommittedFact | None:
        """Read a fact without causing any realization."""
        return self.view().fact(key)

    def commit(self, proposed: Iterable[Fact]) -> tuple[CommittedFact, ...]:
        """Validate all additions and commit all, or commit none.

        Identical repeated claims are idempotent. Conflicting claims are not
        overwritten. Domain validators inspect the full candidate snapshot.
        """
        items = tuple(proposed)
        if not items:
            return ()
        staged = dict(self._records)
        new_keys = []
        for item in items:
            if not isinstance(item, Fact) or not isinstance(item.key, FactKey):
                raise TypeError("commit expects Fact instances")
            if not isinstance(item.origin, str) or not item.origin.strip():
                raise ValueError("origin must be a nonempty string")
            try:
                value = json.loads(json.dumps(item.value, allow_nan=False))
            except (TypeError, ValueError) as exc:
                raise ValueError("fact values must be finite JSON values") from exc
            existing = staged.get(item.key)
            if existing is not None:
                if existing.value != value or type(existing.value) != type(value):
                    raise ImpossibleRealization(f"conflicting claim for {item.key!r}")
                continue
            staged[item.key] = CommittedFact(item.key, value, item.origin,
                                             self._revision + 1)
            new_keys.append(item.key)
        if not new_keys:
            return ()
        view = RealityView(staged)
        try:
            for validate in self._validators:
                validate(view)
        except ImpossibleRealization:
            raise
        except ValueError as exc:
            raise ImpossibleRealization(str(exc)) from exc
        self._records = staged
        self._revision += 1
        return tuple(deepcopy(self._records[key]) for key in new_keys)

    def ask(self, key: FactKey, generate: Callable[[RealityView], Iterable[Fact]]) -> InquiryResult:
        """Interrogate reality; call the generator only if detail is unresolved.

        Generator may propose supporting facts atomically along with requested
        fact. A failed proposal does not change committed reality. No perception
        or Agent belief is created by this operation.
        """
        known = self.inspect(key)
        if known is not None:
            return InquiryResult(known, False)
        proposal = tuple(generate(self.view()))
        if not any(item.key == key for item in proposal):
            raise ValueError("generator did not propose the requested fact")
        self.commit(proposal)
        return InquiryResult(self.inspect(key), True)

    def to_jsonable(self):
        """Export committed facts (validators/rules must be supplied on reload)."""
        return [dict(entity_id=r.key.entity_id, attribute=r.key.attribute,
                     time=r.key.time, detail=r.key.detail, value=deepcopy(r.value),
                     origin=r.origin, revision=r.revision)
                for r in self.view().all_facts()]

    @classmethod
    def from_jsonable(cls, data, validators=()):
        """Restore committed objective facts, rechecking the supplied rules.

        The exported source/order of commitments is preserved. Domain rules are
        code/configuration and must be supplied again by the caller. This does
        not reconstruct World/Being registries, Events, or Agent beliefs.
        """
        ledger = cls(validators)
        group = []
        current_revision = 0
        for item in data:
            if not isinstance(item, dict):
                raise ValueError("malformed realization record")
            revision = item.get("revision")
            if (type(revision) is not int or revision < 1
                    or revision < current_revision
                    or revision > current_revision + 1):
                raise ValueError("realization revisions must be consecutive")
            if revision != current_revision:
                if group:
                    ledger.commit(group)
                current_revision = revision
                group = []
            try:
                key = FactKey(item["entity_id"], item["attribute"],
                              item["time"], item["detail"])
                group.append(Fact(key, item["value"], item["origin"]))
            except (KeyError, TypeError) as exc:
                raise ValueError("malformed realization record") from exc
        if group:
            ledger.commit(group)
        return ledger
