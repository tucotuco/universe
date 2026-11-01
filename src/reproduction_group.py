"""Pure authored proposals for nonempty reproductive groups.

This module does not register or publish authoritative world state. It defines
logical identity only: parent and offspring IDs are strings, never Being,
StatisticalGroup, Encounter, Observation, or Belief objects.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


class ReproductionGroupValidationError(ValueError):
    """An authored proposal cannot describe one unambiguous nonempty group."""


def _identifier(value: object, label: str) -> str:
    if type(value) is not str or not value.strip():
        raise ReproductionGroupValidationError(
            f"{label} must be a nonempty logical identifier string"
        )
    return value


def _identifier_tuple(values: object, label: str) -> tuple[str, ...]:
    # Restrict accepted containers to ordinary data values. Do not execute an
    # arbitrary iterable while freezing an authored proposal.
    if type(values) not in (tuple, list):
        raise ReproductionGroupValidationError(
            f"{label} must be supplied as a tuple or list of logical identifiers"
        )
    return tuple(_identifier(value, f"{label} entry") for value in values)


@dataclass(frozen=True)
class ReproductionGroupProposal:
    """Caller-authored, immutable description of a proposed nonempty group.

    ``group_id`` is a proposed stable group identity, not a reservation in any
    authoritative registry. Input lists are defensively copied to tuples.
    Duplicate identities and empty parent/offspring sets are rejected during
    pure preparation so callers receive one explicit validation boundary.
    """

    group_id: str
    parent_ids: tuple[str, ...]
    offspring_ids: tuple[str, ...]
    source_reference: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "group_id", _identifier(self.group_id, "group_id"))
        object.__setattr__(self, "parent_ids", _identifier_tuple(self.parent_ids, "parent_ids"))
        object.__setattr__(self, "offspring_ids", _identifier_tuple(self.offspring_ids, "offspring_ids"))
        object.__setattr__(
            self, "source_reference", _identifier(self.source_reference, "source_reference")
        )


@dataclass(frozen=True)
class PreparedReproductionGroupCandidate:
    """Detached, immutable candidate; not an authoritative group or commit."""

    group_id: str
    parent_ids: tuple[str, ...]  # canonical exact unordered parent-set key
    offspring_ids: tuple[str, ...]  # authored order retained; enumeration is partial
    source_reference: str

    def __post_init__(self) -> None:
        group_id = _identifier(self.group_id, "group_id")
        parents = _identifier_tuple(self.parent_ids, "parent_ids")
        offspring = _identifier_tuple(self.offspring_ids, "offspring_ids")
        source = _identifier(self.source_reference, "source_reference")
        if not parents or len(set(parents)) != len(parents):
            raise ReproductionGroupValidationError(
                "a prepared candidate requires a nonempty, unique parent set"
            )
        if parents != tuple(sorted(parents)):
            raise ReproductionGroupValidationError("prepared parent_ids must be canonical")
        if not offspring or len(set(offspring)) != len(offspring):
            raise ReproductionGroupValidationError(
                "a prepared candidate requires at least one unique offspring identity"
            )
        if group_id in set(parents) | set(offspring):
            raise ReproductionGroupValidationError(
                "group_id must be distinct from the proposed Person identities"
            )
        object.__setattr__(self, "group_id", group_id)
        object.__setattr__(self, "parent_ids", parents)
        object.__setattr__(self, "offspring_ids", offspring)
        object.__setattr__(self, "source_reference", source)

    @property
    def offspring_enumeration_complete(self) -> Literal[False]:
        """This candidate never asserts that the authored list is exhaustive."""
        return False

    @property
    def parent_set_key(self) -> tuple[str, ...]:
        """Canonical complete parent identity set for equality comparisons."""
        return self.parent_ids


def prepare_reproduction_group(
    proposal: ReproductionGroupProposal,
) -> PreparedReproductionGroupCandidate:
    """Validate and detach one authored nonempty-group candidate.

    Preparation is deterministic and side-effect-free. Repeated parent IDs
    refuse as ambiguous input rather than being silently deduplicated. The
    function performs no global uniqueness/reservation checks; those require a
    later world-owned publisher. It makes no chronology, gender, reproductive
    role, species, or offspring-completeness claim.
    """
    if type(proposal) is not ReproductionGroupProposal:
        raise ReproductionGroupValidationError(
            "proposal must be a ReproductionGroupProposal data record"
        )
    if not proposal.parent_ids:
        raise ReproductionGroupValidationError("at least one exact parent identity is required")
    if len(set(proposal.parent_ids)) != len(proposal.parent_ids):
        raise ReproductionGroupValidationError(
            "repeated parent identity is ambiguous; parent IDs are not silently deduplicated"
        )
    if not proposal.offspring_ids:
        raise ReproductionGroupValidationError(
            "an instantiated ReproductionGroup proposal requires at least one offspring identity"
        )
    if len(set(proposal.offspring_ids)) != len(proposal.offspring_ids):
        raise ReproductionGroupValidationError(
            "duplicate offspring identity would count one logical person more than once"
        )
    if proposal.group_id in set(proposal.parent_ids) | set(proposal.offspring_ids):
        raise ReproductionGroupValidationError(
            "group_id must be distinct from the proposed Person identities"
        )

    return PreparedReproductionGroupCandidate(
        group_id=proposal.group_id,
        parent_ids=tuple(sorted(proposal.parent_ids)),
        offspring_ids=proposal.offspring_ids,
        source_reference=proposal.source_reference,
    )
