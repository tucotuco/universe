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


class ReproductionGroupPublicationError(ValueError):
    """A world-owned publication request conflicts with current state."""


class StaleReproductionGroupRevision(ReproductionGroupPublicationError):
    """The caller's reproduction-registry read revision is no longer current."""


class InjectedReproductionGroupFailure(RuntimeError):
    """Private deterministic fault-injection point for rollback tests."""


_PUBLICATION_PHASES = (
    "group",
    "parent_set_index",
    "offspring_indexes",
    "person_reservations",
    "group_reservation",
    "idempotency",
    "revision",
    "consistency",
)


@dataclass(frozen=True)
class ReproductionGroupRecord:
    """Published objective reproductive data, owned by one Universe in memory."""

    world_identity: int
    group_id: str
    parent_ids: tuple[str, ...]
    offspring_ids: tuple[str, ...]
    source_reference: str
    revision: int

    def __post_init__(self) -> None:
        if type(self.world_identity) is not int or self.world_identity <= 0:
            raise ReproductionGroupValidationError("world_identity must be a positive live owner token")
        _identifier(self.group_id, "group_id")
        parents = _identifier_tuple(self.parent_ids, "parent_ids")
        offspring = _identifier_tuple(self.offspring_ids, "offspring_ids")
        _identifier(self.source_reference, "source_reference")
        if not parents or parents != tuple(sorted(set(parents))):
            raise ReproductionGroupValidationError("published parent set must be nonempty, unique and canonical")
        if not offspring or len(set(offspring)) != len(offspring):
            raise ReproductionGroupValidationError("published group requires unique offspring identities")
        if self.group_id in set(parents) | set(offspring):
            raise ReproductionGroupValidationError("group ID must be distinct from Person IDs")
        if type(self.revision) is not int or self.revision <= 0:
            raise ReproductionGroupValidationError("published group revision must be positive")
        object.__setattr__(self, "parent_ids", parents)
        object.__setattr__(self, "offspring_ids", offspring)

    @property
    def offspring_enumeration_complete(self) -> Literal[False]:
        return False


@dataclass(frozen=True)
class ReproductionGroupPublicationResult:
    """Data-only publication receipt; not an Encounter Action receipt/evidence."""

    world_identity: int
    group_id: str
    parent_ids: tuple[str, ...]
    offspring_ids: tuple[str, ...]
    source_reference: str
    request_key: str
    revision: int


@dataclass(frozen=True)
class ReproductionGroupRegistrySnapshot:
    """Detached inspection of the bounded world-owned registry."""

    world_identity: int
    revision: int
    groups: tuple[ReproductionGroupRecord, ...]
    group_id_by_parent_set: tuple[tuple[tuple[str, ...], str], ...]
    group_id_by_offspring: tuple[tuple[str, str], ...]
    parent_set_by_offspring: tuple[tuple[str, tuple[str, ...]], ...]
    person_id_reservations: tuple[str, ...]
    group_id_reservations: tuple[str, ...]
    request_keys: tuple[str, ...]


@dataclass(frozen=True)
class _IdempotencyRecord:
    normalized_request: tuple
    result: ReproductionGroupPublicationResult


class ReproductionGroupRegistry:
    """Per-Universe in-memory authority for authored ReproductionGroups.

    The instance is created and retained by ``Universe``. Callers publish via
    ``Universe.publish_reproduction_group`` and inspect via its snapshot method.
    All public reads/writes use the owning Universe's schedule lock. This is a
    process-local, nonpersistent registry; raw mutation of Universe internals
    is outside its coordination contract.
    """

    def __init__(self, world):
        if not hasattr(world, "_schedule_lock") or not hasattr(world, "object_registry"):
            raise TypeError("ReproductionGroupRegistry requires a native Universe owner")
        self._world = world
        # Universe.id is currently the constant '0'; the live owner identity
        # distinguishes worlds without claiming cross-process durability.
        self.world_identity = id(world)
        self._groups_by_id: dict[str, ReproductionGroupRecord] = {}
        self._group_id_by_parent_set: dict[tuple[str, ...], str] = {}
        self._group_id_by_offspring: dict[str, str] = {}
        self._parent_set_by_offspring: dict[str, tuple[str, ...]] = {}
        self._person_id_reservations: set[str] = set()
        self._group_id_reservations: set[str] = set()
        self._requests: dict[str, _IdempotencyRecord] = {}
        self._revision = 0

    @property
    def revision(self) -> int:
        with self._world._schedule_lock:
            return self._revision

    def snapshot(self) -> ReproductionGroupRegistrySnapshot:
        """Return immutable copies, never live dictionaries or sets."""
        with self._world._schedule_lock:
            return ReproductionGroupRegistrySnapshot(
                world_identity=self.world_identity,
                revision=self._revision,
                groups=tuple(self._groups_by_id[key] for key in sorted(self._groups_by_id)),
                group_id_by_parent_set=tuple(sorted(self._group_id_by_parent_set.items())),
                group_id_by_offspring=tuple(sorted(self._group_id_by_offspring.items())),
                parent_set_by_offspring=tuple(sorted(self._parent_set_by_offspring.items())),
                person_id_reservations=tuple(sorted(self._person_id_reservations)),
                group_id_reservations=tuple(sorted(self._group_id_reservations)),
                request_keys=tuple(sorted(self._requests)),
            )

    def get_group(self, group_id: str) -> ReproductionGroupRecord | None:
        with self._world._schedule_lock:
            return self._groups_by_id.get(group_id)

    @staticmethod
    def _validate_request(candidate, request_key, expected_revision, fail_after):
        if type(candidate) is not PreparedReproductionGroupCandidate:
            raise ReproductionGroupPublicationError(
                "publication requires a prepared ReproductionGroup candidate"
            )
        # Reconstructing through the public immutable validator also guards
        # against object.__setattr__ tampering with a frozen record.
        try:
            validated = prepare_reproduction_group(ReproductionGroupProposal(
                candidate.group_id, candidate.parent_ids,
                candidate.offspring_ids, candidate.source_reference,
            ))
        except (TypeError, ValueError) as exc:
            raise ReproductionGroupPublicationError(f"invalid candidate: {exc}") from exc
        if validated != candidate:
            raise ReproductionGroupPublicationError("candidate is not canonical or detached data")
        if type(request_key) is not str or not request_key.strip():
            raise ReproductionGroupPublicationError("request_key must be a nonempty string")
        if type(expected_revision) is not int or expected_revision < 0:
            raise ReproductionGroupPublicationError("expected_revision must be a nonnegative integer")
        if fail_after is not None and fail_after not in _PUBLICATION_PHASES:
            raise ReproductionGroupPublicationError("unknown fault-injection phase")
        normalized = (
            candidate.group_id,
            candidate.parent_ids,
            candidate.offspring_ids,
            candidate.source_reference,
        )
        return normalized

    def publish(self, candidate, *, request_key: str, expected_revision: int,
                _fail_after: str | None = None) -> ReproductionGroupPublicationResult:
        """Atomically publish one group and its first offspring fact.

        Expected validation failures occur before writes. Injected/unexpected
        failures restore all authoritative maps, sets, aliases, and revision in
        place. This operation does not consult Encounter, Observation, Belief,
        RNG, dates, statistical populations, or Being instances.
        """
        normalized = self._validate_request(candidate, request_key, expected_revision, _fail_after)
        with self._world._schedule_lock:
            if self._world._reproduction_group_registry is not self:
                raise ReproductionGroupPublicationError("registry is not owned by this Universe")
            prior = self._requests.get(request_key)
            if prior is not None:
                self._assert_consistent()
                if prior.normalized_request != normalized:
                    raise ReproductionGroupPublicationError(
                        "request key was already used for different normalized content"
                    )
                return prior.result
            if expected_revision != self._revision:
                raise StaleReproductionGroupRevision(
                    f"expected reproduction revision {expected_revision}, current revision is {self._revision}"
                )
            self._validate_current_state(candidate)

            new_revision = self._revision + 1
            record = ReproductionGroupRecord(
                world_identity=self.world_identity,
                group_id=candidate.group_id,
                parent_ids=candidate.parent_ids,
                offspring_ids=candidate.offspring_ids,
                source_reference=candidate.source_reference,
                revision=new_revision,
            )
            result = ReproductionGroupPublicationResult(
                world_identity=self.world_identity,
                group_id=record.group_id,
                parent_ids=record.parent_ids,
                offspring_ids=record.offspring_ids,
                source_reference=record.source_reference,
                request_key=request_key,
                revision=new_revision,
            )
            undo = self._capture_undo()
            try:
                self._groups_by_id[candidate.group_id] = record
                self._maybe_fail(_fail_after, "group")

                self._group_id_by_parent_set[candidate.parent_ids] = candidate.group_id
                self._maybe_fail(_fail_after, "parent_set_index")

                for person_id in candidate.offspring_ids:
                    self._group_id_by_offspring[person_id] = candidate.group_id
                    self._parent_set_by_offspring[person_id] = candidate.parent_ids
                self._maybe_fail(_fail_after, "offspring_indexes")

                self._person_id_reservations.update(candidate.parent_ids)
                self._person_id_reservations.update(candidate.offspring_ids)
                self._maybe_fail(_fail_after, "person_reservations")

                self._group_id_reservations.add(candidate.group_id)
                self._maybe_fail(_fail_after, "group_reservation")

                self._requests[request_key] = _IdempotencyRecord(normalized, result)
                self._maybe_fail(_fail_after, "idempotency")

                self._revision = new_revision
                self._maybe_fail(_fail_after, "revision")

                self._assert_consistent()
                self._maybe_fail(_fail_after, "consistency")
                return result
            except BaseException:
                self._restore_undo(undo)
                raise

    def _validate_current_state(self, candidate) -> None:
        from encounter import Encounter
        if (any(isinstance(event, Encounter) for event in self._world.event_history.values())
                or self._world._choice_books):
            raise ReproductionGroupPublicationError(
                "D4B publication is supported only in a Universe with no Encounter/ChoiceBook context"
            )
        if candidate.group_id in self._groups_by_id or candidate.group_id in self._group_id_reservations:
            raise ReproductionGroupPublicationError("group ID is already reserved in this Universe")
        if candidate.parent_ids in self._group_id_by_parent_set:
            raise ReproductionGroupPublicationError(
                "this exact parent set already has an authoritative ReproductionGroup"
            )
        if candidate.group_id in self._person_id_reservations:
            raise ReproductionGroupPublicationError("group ID collides with a reserved Person ID")
        person_ids = set(candidate.parent_ids) | set(candidate.offspring_ids)
        if person_ids & self._group_id_reservations:
            raise ReproductionGroupPublicationError("Person ID collides with a reserved group ID")
        if person_ids & set(self._world.object_registry.object_instances):
            raise ReproductionGroupPublicationError(
                "logical Person ID collides with a native Object ID; identity binding is not integrated"
            )
        if candidate.group_id in self._world.object_registry.object_instances:
            raise ReproductionGroupPublicationError("group ID collides with a native Object ID")
        for person_id in candidate.offspring_ids:
            if person_id in self._group_id_by_offspring:
                raise ReproductionGroupPublicationError(
                    "offspring already has a parent-set assignment in this world"
                )

    def _assert_consistent(self) -> None:
        if self._revision < 1:
            raise RuntimeError("published state has no committed revision")
        if set(self._groups_by_id) != self._group_id_reservations:
            raise RuntimeError("group identity reservation index is inconsistent")
        if len(self._groups_by_id) != len(self._group_id_by_parent_set):
            raise RuntimeError("group and exact-parent-set indexes differ in size")
        expected_people = set()
        expected_offspring = {}
        for group_id, group in self._groups_by_id.items():
            if group.group_id != group_id or group.world_identity != self.world_identity:
                raise RuntimeError("group owner or identity mismatch")
            if not group.parent_ids or group.parent_ids != tuple(sorted(set(group.parent_ids))):
                raise RuntimeError("group parent set is empty, duplicated or noncanonical")
            if not group.offspring_ids:
                raise RuntimeError("published group is empty")
            if self._group_id_by_parent_set.get(group.parent_ids) != group_id:
                raise RuntimeError("exact-parent-set index is inconsistent")
            expected_people.update(group.parent_ids)
            expected_people.update(group.offspring_ids)
            for person_id in group.offspring_ids:
                if person_id in expected_offspring:
                    raise RuntimeError("offspring identity is assigned more than once")
                expected_offspring[person_id] = (group_id, group.parent_ids)
        if expected_people != self._person_id_reservations:
            raise RuntimeError("Person identity reservations are inconsistent")
        expected_group_by_child = {person: value[0] for person, value in expected_offspring.items()}
        expected_parent_sets = {person: value[1] for person, value in expected_offspring.items()}
        if self._group_id_by_offspring != expected_group_by_child:
            raise RuntimeError("offspring-to-group index is inconsistent")
        if self._parent_set_by_offspring != expected_parent_sets:
            raise RuntimeError("offspring parentage index is inconsistent")
        if set(self._requests) != {record.result.request_key for record in self._requests.values()}:
            raise RuntimeError("idempotency request index is inconsistent")
        for request_key, record in self._requests.items():
            result = record.result
            group = self._groups_by_id.get(result.group_id)
            if (result.world_identity != self.world_identity or result.request_key != request_key
                    or group is None or group.parent_ids != result.parent_ids
                    or group.offspring_ids != result.offspring_ids
                    or group.source_reference != result.source_reference):
                raise RuntimeError("idempotency record is inconsistent with published world state")

    def _capture_undo(self):
        return (
            dict(self._groups_by_id),
            dict(self._group_id_by_parent_set),
            dict(self._group_id_by_offspring),
            dict(self._parent_set_by_offspring),
            set(self._person_id_reservations),
            set(self._group_id_reservations),
            dict(self._requests),
            self._revision,
        )

    def _restore_undo(self, undo) -> None:
        maps = (
            (self._groups_by_id, undo[0]),
            (self._group_id_by_parent_set, undo[1]),
            (self._group_id_by_offspring, undo[2]),
            (self._parent_set_by_offspring, undo[3]),
            (self._requests, undo[6]),
        )
        for target, original in maps:
            target.clear()
            target.update(original)
        self._person_id_reservations.clear()
        self._person_id_reservations.update(undo[4])
        self._group_id_reservations.clear()
        self._group_id_reservations.update(undo[5])
        self._revision = undo[7]

    @staticmethod
    def _maybe_fail(fail_after, phase):
        if fail_after == phase:
            raise InjectedReproductionGroupFailure(f"injected failure after {phase}")
