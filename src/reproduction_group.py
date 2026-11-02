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
_STATISTICAL_PUBLICATION_PHASES = (
    "group", "parent_set_index", "offspring_indexes", "origin_ticks",
    "person_reservations", "group_reservation", "generation_outcome",
    "generation_scope", "idempotency", "revision", "consistency",
)
_PROGRESSIVE_PUBLICATION_PHASES = (
    "progressive_group", "progressive_parent_set_index", "progressive_offspring_indexes",
    "progressive_origin_ticks", "progressive_person_reservations",
    "progressive_group_reservation", "progressive_history", "progressive_scope",
    "progressive_idempotency", "progressive_revision", "progressive_consistency",
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
    offspring_origin_ticks: tuple[tuple[str, int], ...]
    generation_outcomes: tuple[object, ...]
    generation_parent_set_scopes: tuple[tuple[tuple[str, ...], str], ...]
    progressive_histories: tuple[object, ...]
    progressive_parent_set_scopes: tuple[tuple[tuple[str, ...], str], ...]
    progressive_request_keys: tuple[str, ...]

    def known_parents(self, person_id: str) -> tuple[str, ...] | None:
        """Exact known parent set for this published child, or ``None`` if unknown."""
        return dict(self.parent_set_by_offspring).get(person_id)

    def known_full_siblings(self, person_id: str) -> tuple[str, ...]:
        """Known other offspring in the child's exact ReproductionGroup only."""
        group_id = dict(self.group_id_by_offspring).get(person_id)
        if group_id is None:
            return ()
        groups = {group.group_id: group for group in self.groups}
        group = groups.get(group_id)
        if group is None:
            raise RuntimeError("offspring index references an unavailable group")
        return tuple(child for child in group.offspring_ids if child != person_id)

    def known_shared_parent_relatives(self, person_id: str) -> tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...]:
        """Return ``(other child, shared parents, other exact parent set)`` facts.

        This deliberately uses relationship-neutral wording. For parent sets
        larger than two it does not assign a sibling category.
        """
        parents = self.known_parents(person_id)
        if parents is None:
            return ()
        rows = []
        for group in self.groups:
            if group.parent_ids == parents:
                continue
            shared = tuple(sorted(set(parents) & set(group.parent_ids)))
            if not shared:
                continue
            for other in group.offspring_ids:
                if other != person_id:
                    rows.append((other, shared, group.parent_ids))
        return tuple(sorted(set(rows)))

    def known_half_siblings(self, person_id: str) -> tuple[str, ...]:
        """Known one-parent overlaps between two-parent groups only."""
        parents = self.known_parents(person_id)
        if parents is None:
            return ()
        if len(parents) != 2:
            raise UnsupportedReproductionKinshipQuery(
                "half-sibling labels are supported only for two-parent groups"
            )
        return tuple(sorted({other for other, shared, other_parents
                             in self.known_shared_parent_relatives(person_id)
                             if len(other_parents) == 2 and len(shared) == 1}))

    def known_grandparent_paths(self, person_id: str) -> tuple[tuple[str, tuple[str, ...]], ...]:
        """Known two-step parentage paths, without completeness claims."""
        parents = self.known_parents(person_id)
        if parents is None:
            return ()
        paths = []
        for parent in parents:
            grandparents = self.known_parents(parent)
            if grandparents is not None:
                if person_id in grandparents or parent in grandparents:
                    raise ValueError("cyclic parentage cannot be presented as a grandparent path")
                paths.append((parent, grandparents))
        return tuple(paths)


class UnsupportedReproductionKinshipQuery(ValueError):
    """A requested family label cannot be derived from the supported facts."""


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
        self._offspring_origin_ticks: dict[str, int] = {}
        self._generation_requests: dict[str, object] = {}
        self._generation_parent_set_scopes: dict[tuple[str, ...], str] = {}
        self._progressive_histories: dict[tuple[str, ...], object] = {}
        self._progressive_parent_set_scopes: dict[tuple[str, ...], str] = {}
        self._progressive_requests: dict[str, object] = {}
        # Exact-ID native Being bindings are a separate, explicit bridge. They
        # do not change reproductive facts and are excluded from V4 checkpoint
        # payloads; the checkpoint API refuses worlds containing them.
        self._native_beings_by_person_id: dict[str, object] = {}
        self._native_being_requests: dict[str, object] = {}
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
                offspring_origin_ticks=tuple(sorted(self._offspring_origin_ticks.items())),
                generation_outcomes=tuple(
                    self._generation_requests[key].outcome
                    for key in sorted(self._generation_requests)
                ),
                generation_parent_set_scopes=tuple(sorted(self._generation_parent_set_scopes.items())),
                progressive_histories=tuple(
                    self._progressive_histories[key] for key in sorted(self._progressive_histories)
                ),
                progressive_parent_set_scopes=tuple(sorted(self._progressive_parent_set_scopes.items())),
                progressive_request_keys=tuple(sorted(self._progressive_requests)),
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
            if request_key in self._generation_requests:
                raise ReproductionGroupPublicationError("request key is reserved by a statistical outcome")
            if request_key in self._progressive_requests:
                raise ReproductionGroupPublicationError("request key is reserved by a progressive outcome")
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

    def publish_statistical_reproduction(self, candidate, *, request_key: str,
                                         expected_revision: int,
                                         _fail_after: str | None = None):
        """Atomically publish one bounded seeded outcome (positive or zero).

        This API consumes only the explicitly test-only candidate type. Zero
        outcomes publish a request/horizon record and no group or Person IDs.
        Positive outcomes publish their group, child parentage and ordered tick
        facts in the same critical section. Existing Encounter publication is
        deliberately outside this registry's supported scope.
        """
        from reproduction_generation import (
            PreparedStatisticalReproduction, StatisticalReproductionOutcome,
            _GenerationIdempotencyRecord,
            _normalized_request, normalized_prepared_request,
        )
        if type(candidate) is not PreparedStatisticalReproduction:
            raise ReproductionGroupPublicationError(
                "statistical publication requires a prepared bounded demo outcome"
            )
        if type(request_key) is not str or not request_key.strip():
            raise ReproductionGroupPublicationError("request_key must be nonempty text")
        if type(expected_revision) is not int or expected_revision < 0:
            raise ReproductionGroupPublicationError("expected_revision must be nonnegative")
        if _fail_after is not None and _fail_after not in _STATISTICAL_PUBLICATION_PHASES:
            raise ReproductionGroupPublicationError("unknown statistical publication fault phase")
        normalized = normalized_prepared_request(candidate)
        try:
            # Independently verify deterministic IDs, count, times and digest;
            # a frozen instance can still be tampered with via object.__setattr__.
            from reproduction_generation import (
                StatisticalReproductionRequest, TestOnlyOffspringCountDistribution,
                _normalized_request, _sample,
            )
            request = StatisticalReproductionRequest(
                candidate.parent_ids, candidate.seed, candidate.horizon_tick,
                candidate.eligible_origin_ticks,
                TestOnlyOffspringCountDistribution(candidate.distribution_id,
                    candidate.distribution_version, candidate.weighted_counts),
            )
            # Recompute from the immutable request and its captured revision;
            # this does not query current authority or advance global RNG.
            expected = _sample(request, candidate.base_revision, self.world_identity)
        except (TypeError, ValueError) as exc:
            raise ReproductionGroupPublicationError(f"invalid statistical candidate: {exc}") from exc
        if normalized_prepared_request(expected) != normalized:
            raise ReproductionGroupPublicationError("statistical candidate does not match its deterministic request")
        if expected.scope_digest != candidate.scope_digest:
            raise ReproductionGroupPublicationError("statistical request digest mismatch")

        with self._world._schedule_lock:
            if self._world._reproduction_group_registry is not self:
                raise ReproductionGroupPublicationError("registry is not owned by this Universe")
            previous = self._generation_requests.get(request_key)
            if previous is not None:
                self._assert_consistent()
                if previous.normalized_request != normalized:
                    raise ReproductionGroupPublicationError(
                        "request key was reused with different statistical inputs"
                    )
                return previous.outcome
            if request_key in self._requests:
                raise ReproductionGroupPublicationError("request key is already used by authored publication")
            if request_key in self._progressive_requests:
                raise ReproductionGroupPublicationError("request key is already used by progressive publication")
            if expected_revision != candidate.base_revision or expected_revision != self._revision:
                raise StaleReproductionGroupRevision(
                    f"statistical candidate read revision {candidate.base_revision}; current is {self._revision}"
                )
            self._validate_no_encounter_context()
            if candidate.parent_ids in self._progressive_parent_set_scopes:
                raise ReproductionGroupPublicationError("exact parent set already has progressive test-profile history")
            if candidate.parent_ids in self._generation_parent_set_scopes:
                raise ReproductionGroupPublicationError(
                    "this exact parent set already has a bounded generation outcome"
                )
            self._validate_generated_parent_ids(candidate)
            self._validate_parentage_addition(candidate.parent_ids, candidate.offspring_ids)
            if candidate.parent_ids in self._group_id_by_parent_set:
                raise ReproductionGroupPublicationError(
                    "exact parent set already has an established ReproductionGroup"
                )
            if candidate.offspring_count:
                self._validate_generated_identities(candidate)
            revision = self._revision + 1
            outcome = StatisticalReproductionOutcome(
                world_identity=self.world_identity,
                request_key=request_key,
                scope_digest=candidate.scope_digest,
                parent_ids=candidate.parent_ids,
                horizon_tick=candidate.horizon_tick,
                eligible_origin_ticks=candidate.eligible_origin_ticks,
                count=candidate.offspring_count,
                group_id=candidate.group_id,
                offspring_ids=candidate.offspring_ids,
                origin_ticks=candidate.origin_ticks,
                seed=candidate.seed,
                distribution_id=candidate.distribution_id,
                distribution_version=candidate.distribution_version,
                distribution_schema=candidate.distribution_schema,
                weighted_counts=candidate.weighted_counts,
                algorithm=candidate.algorithm,
                source_reference=candidate.source_reference,
                revision=revision,
            )
            undo = self._capture_undo()
            try:
                if candidate.offspring_count:
                    record = ReproductionGroupRecord(
                        self.world_identity, candidate.group_id, candidate.parent_ids,
                        candidate.offspring_ids, candidate.source_reference, revision,
                    )
                    self._groups_by_id[candidate.group_id] = record
                    self._maybe_fail(_fail_after, "group")
                    self._group_id_by_parent_set[candidate.parent_ids] = candidate.group_id
                    self._maybe_fail(_fail_after, "parent_set_index")
                    for person_id in candidate.offspring_ids:
                        self._group_id_by_offspring[person_id] = candidate.group_id
                        self._parent_set_by_offspring[person_id] = candidate.parent_ids
                    self._maybe_fail(_fail_after, "offspring_indexes")
                    self._offspring_origin_ticks.update(zip(candidate.offspring_ids, candidate.origin_ticks))
                    self._maybe_fail(_fail_after, "origin_ticks")
                    self._person_id_reservations.update(candidate.parent_ids)
                    self._person_id_reservations.update(candidate.offspring_ids)
                    self._maybe_fail(_fail_after, "person_reservations")
                    self._group_id_reservations.add(candidate.group_id)
                    self._maybe_fail(_fail_after, "group_reservation")
                self._generation_requests[request_key] = _GenerationIdempotencyRecord(
                    normalized, _normalized_request(request), outcome
                )
                self._maybe_fail(_fail_after, "generation_outcome")
                self._generation_parent_set_scopes[candidate.parent_ids] = candidate.scope_digest
                self._maybe_fail(_fail_after, "generation_scope")
                self._maybe_fail(_fail_after, "idempotency")
                self._revision = revision
                self._maybe_fail(_fail_after, "revision")
                self._assert_consistent()
                self._maybe_fail(_fail_after, "consistency")
                return outcome
            except BaseException:
                self._restore_undo(undo)
                raise

    def resolve_statistical_reproduction(self, request, *, request_key: str,
                                         expected_revision: int,
                                         _fail_after: str | None = None):
        """Resolve and publish one request, replaying without another draw.

        This narrow orchestration keeps the pure candidate preparer separate
        while providing a retry surface that can recognize an already
        committed normalized request before constructing a local RNG.
        """
        from reproduction_generation import (
            StatisticalReproductionRequest, _normalized_request,
            prepare_statistical_reproduction,
        )
        if type(request) is not StatisticalReproductionRequest:
            raise ReproductionGroupPublicationError("request must be a statistical reproduction request")
        if type(request_key) is not str or not request_key.strip():
            raise ReproductionGroupPublicationError("request_key must be nonempty text")
        if type(expected_revision) is not int or expected_revision < 0:
            raise ReproductionGroupPublicationError("expected_revision must be nonnegative")
        normalized_inputs = _normalized_request(request)
        with self._world._schedule_lock:
            prior = self._generation_requests.get(request_key)
            if prior is not None:
                self._assert_consistent()
                if prior.normalized_inputs != normalized_inputs:
                    raise ReproductionGroupPublicationError(
                        "request key was reused with different statistical inputs"
                    )
                return prior.outcome
            if request_key in self._requests:
                raise ReproductionGroupPublicationError("request key is already used by authored publication")
            if expected_revision != self._revision:
                raise StaleReproductionGroupRevision(
                    f"expected reproduction revision {expected_revision}, current revision is {self._revision}"
                )
            candidate = prepare_statistical_reproduction(self._world, request)
            return self.publish_statistical_reproduction(
                candidate, request_key=request_key, expected_revision=expected_revision,
                _fail_after=_fail_after,
            )

    def publish_progressive_reproduction(self, candidate, *, request_key: str,
                                         expected_revision: int,
                                         _fail_after: str | None = None):
        """Atomically append the uncommitted suffix of one test-profile history."""
        from reproduction_generation import (
            ProgressiveReproductionRequest, TestOnlyIntervalReproductionProfile,
            ProgressiveReproductionHistory, ProgressiveReproductionResult,
            _ProgressiveIdempotencyRecord, _progressive_inputs,
            _progressive_history_digest, _progressive_periods,
            _progressive_scope_digest, normalized_progressive_candidate,
        )
        from reproduction_generation import PreparedProgressiveReproduction
        if type(candidate) is not PreparedProgressiveReproduction:
            raise ReproductionGroupPublicationError("progressive publication requires a prepared candidate")
        if type(request_key) is not str or not request_key.strip():
            raise ReproductionGroupPublicationError("request_key must be nonempty text")
        if type(expected_revision) is not int or expected_revision < 0:
            raise ReproductionGroupPublicationError("expected_revision must be nonnegative")
        if _fail_after is not None and _fail_after not in _PROGRESSIVE_PUBLICATION_PHASES:
            raise ReproductionGroupPublicationError("unknown progressive publication fault phase")
        try:
            profile = TestOnlyIntervalReproductionProfile(
                candidate.profile_id, candidate.profile_version,
                candidate.weighted_counts_per_period,
            )
            request = ProgressiveReproductionRequest(
                candidate.parent_ids, candidate.world_seed, candidate.target_period, profile,
            )
            scope = _progressive_scope_digest(request)
            expected = _progressive_periods(
                scope, candidate.previous_through_period + 1, candidate.target_period,
                profile.weighted_counts_per_period,
            )
        except (TypeError, ValueError) as exc:
            raise ReproductionGroupPublicationError(f"invalid progressive candidate: {exc}") from exc
        expected_group = f"RG-PROG-{scope[:24]}"
        expected_source = f"test-only-interval-count-profile/1:{profile.profile_id}@{profile.version}:{scope}"
        if (candidate.world_identity != self.world_identity
                or candidate.scope_digest != scope
                or candidate.algorithm != "python-mt19937-hash-derived-period-stream/1"
                or candidate.profile_schema != "test-only-interval-count-profile/1"
                or candidate.proposed_group_id != expected_group
                or candidate.source_reference != expected_source
                or candidate.target_period <= candidate.previous_through_period
                or candidate.new_periods != expected):
            raise ReproductionGroupPublicationError("progressive candidate does not match its deterministic request")
        normalized = normalized_progressive_candidate(candidate)
        normalized_inputs = _progressive_inputs(request) + (request.target_period,)

        with self._world._schedule_lock:
            if self._world._reproduction_group_registry is not self:
                raise ReproductionGroupPublicationError("registry is not owned by this Universe")
            previous_request = self._progressive_requests.get(request_key)
            if previous_request is not None:
                self._assert_consistent()
                if previous_request.normalized_request != normalized:
                    raise ReproductionGroupPublicationError("progressive request key reused with different inputs")
                return previous_request.result
            if request_key in self._requests or request_key in self._generation_requests:
                raise ReproductionGroupPublicationError("request key is already used by another publication path")
            if expected_revision != candidate.base_revision or expected_revision != self._revision:
                raise StaleReproductionGroupRevision(
                    f"progressive candidate read revision {candidate.base_revision}; current is {self._revision}"
                )
            self._validate_no_encounter_context()
            history = self._progressive_histories.get(candidate.parent_ids)
            if history is None:
                if candidate.previous_through_period != -1 or candidate.previous_history_digest is not None:
                    raise StaleReproductionGroupRevision("progressive initial-history dependency changed")
                if (candidate.parent_ids in self._group_id_by_parent_set
                        or candidate.parent_ids in self._generation_parent_set_scopes):
                    raise ReproductionGroupPublicationError(
                        "exact parent set already has an authored or V1 reproductive history"
                    )
                prior_periods = ()
                prior_group_id = None
            else:
                if history.scope_digest != candidate.scope_digest:
                    raise ReproductionGroupPublicationError("parent set has a different progressive seed/profile")
                if (candidate.previous_through_period != history.through_period
                        or candidate.previous_history_digest != _progressive_history_digest(history)):
                    raise StaleReproductionGroupRevision("progressive history prefix changed after preparation")
                if candidate.target_period <= history.through_period:
                    raise ReproductionGroupPublicationError("overlapping progressive horizons are unsupported")
                prior_periods = history.periods
                prior_group_id = history.group_id

            if self._progressive_parent_set_scopes.get(candidate.parent_ids, candidate.scope_digest) != candidate.scope_digest:
                raise ReproductionGroupPublicationError("parent set has a conflicting progressive scope")
            new_children = tuple(child for row in candidate.new_periods for child in row.offspring_ids)
            if len(set(new_children)) != len(new_children) or any(child in self._group_id_by_offspring for child in new_children):
                raise ReproductionGroupPublicationError("progressive offspring identity conflicts with established Reality")
            if set(new_children) & self._person_id_reservations:
                raise ReproductionGroupPublicationError("progressive offspring identity is already reserved as a Person")
            if set(candidate.parent_ids) & set(self._group_id_reservations):
                raise ReproductionGroupPublicationError("progressive parent ID collides with a group ID")
            if set(candidate.parent_ids) & set(self._world.object_registry.object_instances):
                raise ReproductionGroupPublicationError("progressive parent ID collides with a native Object ID")
            if set(new_children) & set(candidate.parent_ids):
                raise ReproductionGroupPublicationError("progressive child identity collides with a parent identity")
            self._validate_parentage_addition(candidate.parent_ids, new_children)

            all_periods = prior_periods + candidate.new_periods
            all_children = tuple(child for row in all_periods for child in row.offspring_ids)
            has_children = bool(all_children)
            group_id = prior_group_id or (candidate.proposed_group_id if has_children else None)
            if has_children:
                if group_id != candidate.proposed_group_id:
                    raise ReproductionGroupPublicationError("progressive group identity changed across horizons")
                if prior_group_id is None:
                    if group_id in self._groups_by_id or group_id in self._group_id_reservations:
                        raise ReproductionGroupPublicationError("progressive group ID is already reserved")
                    if group_id in self._person_id_reservations or group_id in self._world.object_registry.object_instances:
                        raise ReproductionGroupPublicationError("progressive group ID collides with another identity")
                elif group_id in self._world.object_registry.object_instances:
                    raise ReproductionGroupPublicationError("progressive group ID collides with a native Object ID")
                if set(all_children) & self._group_id_reservations:
                    raise ReproductionGroupPublicationError("progressive offspring ID collides with a group ID")
                # Previously materialized logical offspring are legitimate
                # identity bindings. Only newly proposed children can collide
                # with an existing native Object during a progressive append.
                if set(new_children) & set(self._world.object_registry.object_instances):
                    raise ReproductionGroupPublicationError("progressive offspring ID collides with a native Object ID")

            revision = self._revision + 1
            history_after = ProgressiveReproductionHistory(
                self.world_identity, candidate.parent_ids, candidate.world_seed,
                candidate.profile_id, candidate.profile_version, candidate.profile_schema,
                candidate.weighted_counts_per_period, candidate.algorithm, candidate.scope_digest,
                candidate.target_period, group_id, all_periods, revision,
            )
            result = ProgressiveReproductionResult(
                self.world_identity, request_key, candidate.scope_digest, candidate.parent_ids,
                candidate.previous_through_period + 1, candidate.target_period,
                candidate.new_periods, group_id, all_children, revision,
            )
            undo = self._capture_undo()
            try:
                if has_children:
                    group = ReproductionGroupRecord(
                        self.world_identity, group_id, candidate.parent_ids, all_children,
                        candidate.source_reference, revision,
                    )
                    self._groups_by_id[group_id] = group
                    self._maybe_fail(_fail_after, "progressive_group")
                    if prior_group_id is None:
                        self._group_id_by_parent_set[candidate.parent_ids] = group_id
                        self._maybe_fail(_fail_after, "progressive_parent_set_index")
                    for child in new_children:
                        self._group_id_by_offspring[child] = group_id
                        self._parent_set_by_offspring[child] = candidate.parent_ids
                    self._maybe_fail(_fail_after, "progressive_offspring_indexes")
                    for row in candidate.new_periods:
                        for child in row.offspring_ids:
                            self._offspring_origin_ticks[child] = row.period
                    self._maybe_fail(_fail_after, "progressive_origin_ticks")
                    self._person_id_reservations.update(candidate.parent_ids)
                    self._person_id_reservations.update(new_children)
                    self._maybe_fail(_fail_after, "progressive_person_reservations")
                    if prior_group_id is None:
                        self._group_id_reservations.add(group_id)
                        self._maybe_fail(_fail_after, "progressive_group_reservation")
                self._progressive_histories[candidate.parent_ids] = history_after
                self._maybe_fail(_fail_after, "progressive_history")
                self._progressive_parent_set_scopes[candidate.parent_ids] = candidate.scope_digest
                self._maybe_fail(_fail_after, "progressive_scope")
                self._progressive_requests[request_key] = _ProgressiveIdempotencyRecord(
                    normalized, normalized_inputs, result
                )
                self._maybe_fail(_fail_after, "progressive_idempotency")
                self._revision = revision
                self._maybe_fail(_fail_after, "progressive_revision")
                self._assert_consistent()
                self._maybe_fail(_fail_after, "progressive_consistency")
                return result
            except BaseException:
                self._restore_undo(undo)
                raise

    def resolve_progressive_reproduction(self, request, *, request_key: str,
                                         expected_revision: int,
                                         _fail_after: str | None = None):
        """Prepare/publish a period suffix; cached retries return before any draw."""
        from reproduction_generation import (
            ProgressiveReproductionRequest, _progressive_inputs,
            prepare_progressive_reproduction,
        )
        if type(request) is not ProgressiveReproductionRequest:
            raise ReproductionGroupPublicationError("request must be ProgressiveReproductionRequest")
        if type(request_key) is not str or not request_key.strip():
            raise ReproductionGroupPublicationError("request_key must be nonempty text")
        if type(expected_revision) is not int or expected_revision < 0:
            raise ReproductionGroupPublicationError("expected_revision must be nonnegative")
        normalized_inputs = _progressive_inputs(request) + (request.target_period,)
        with self._world._schedule_lock:
            previous = self._progressive_requests.get(request_key)
            if previous is not None:
                self._assert_consistent()
                if previous.normalized_inputs != normalized_inputs:
                    raise ReproductionGroupPublicationError("progressive request key reused with different inputs")
                return previous.result
            if request_key in self._requests or request_key in self._generation_requests:
                raise ReproductionGroupPublicationError("request key is already used by another publication path")
            if expected_revision != self._revision:
                raise StaleReproductionGroupRevision(
                    f"expected reproduction revision {expected_revision}, current revision is {self._revision}"
                )
            candidate = prepare_progressive_reproduction(self._world, request)
            return self.publish_progressive_reproduction(
                candidate, request_key=request_key, expected_revision=expected_revision,
                _fail_after=_fail_after,
            )

    def _validate_no_encounter_context(self) -> None:
        from encounter import Encounter
        if (any(isinstance(event, Encounter) for event in self._world.event_history.values())
                or self._world._choice_books):
            raise ReproductionGroupPublicationError(
                "world-level reproduction is supported only in a Universe with no Encounter/ChoiceBook context"
            )

    def _validate_generated_identities(self, candidate) -> None:
        if candidate.group_id is None:
            raise ReproductionGroupPublicationError("positive outcome has no ReproductionGroup identity")
        if candidate.group_id in self._groups_by_id or candidate.group_id in self._group_id_reservations:
            raise ReproductionGroupPublicationError("generated group identity is already reserved")
        if candidate.group_id in self._person_id_reservations:
            raise ReproductionGroupPublicationError("generated group ID collides with a Person identity")
        person_ids = set(candidate.parent_ids) | set(candidate.offspring_ids)
        if person_ids & self._group_id_reservations:
            raise ReproductionGroupPublicationError("generated Person identity collides with a group ID")
        object_ids = set(self._world.object_registry.object_instances)
        if (candidate.group_id in object_ids or person_ids & object_ids):
            raise ReproductionGroupPublicationError("generated logical identity collides with a native Object ID")
        if any(person_id in self._group_id_by_offspring for person_id in candidate.offspring_ids):
            raise ReproductionGroupPublicationError("generated offspring already has an established parent set")

    def _validate_generated_parent_ids(self, candidate) -> None:
        if set(candidate.parent_ids) & self._group_id_reservations:
            raise ReproductionGroupPublicationError("reproductive parent ID collides with a group ID")
        if set(candidate.parent_ids) & set(self._world.object_registry.object_instances):
            raise ReproductionGroupPublicationError("reproductive parent ID collides with a native Object ID")

    def _validate_current_state(self, candidate) -> None:
        self._validate_no_encounter_context()
        if candidate.group_id in self._groups_by_id or candidate.group_id in self._group_id_reservations:
            raise ReproductionGroupPublicationError("group ID is already reserved in this Universe")
        if candidate.parent_ids in self._group_id_by_parent_set:
            raise ReproductionGroupPublicationError(
                "this exact parent set already has an authoritative ReproductionGroup"
            )
        if candidate.parent_ids in self._generation_parent_set_scopes:
            raise ReproductionGroupPublicationError(
                "this exact parent set already has a bounded generation outcome"
            )
        if candidate.parent_ids in self._progressive_parent_set_scopes:
            raise ReproductionGroupPublicationError(
                "this exact parent set already has progressive test-profile history"
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
        self._validate_parentage_addition(candidate.parent_ids, candidate.offspring_ids)

    def _validate_parentage_addition(self, parent_ids, offspring_ids) -> None:
        """Refuse only a parentage edge that closes a known directed cycle."""
        for child in offspring_ids:
            pending = list(parent_ids)
            seen = set()
            while pending:
                ancestor = pending.pop()
                if ancestor == child:
                    raise ReproductionGroupPublicationError(
                        "parentage assignment would create a known ancestry cycle"
                    )
                if ancestor in seen:
                    continue
                seen.add(ancestor)
                pending.extend(self._parent_set_by_offspring.get(ancestor, ()))

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
        if set(self._generation_requests) != {
                record.outcome.request_key for record in self._generation_requests.values()}:
            raise RuntimeError("statistical idempotency request index is inconsistent")
        expected_scopes = {}
        expected_origin_ticks = {}
        from reproduction_generation import SAMPLING_ALGORITHM
        for request_key, record in self._generation_requests.items():
            outcome = record.outcome
            expected_inputs = (
                outcome.parent_ids, outcome.seed, outcome.horizon_tick,
                outcome.eligible_origin_ticks, outcome.distribution_id,
                outcome.distribution_version, outcome.weighted_counts,
                outcome.distribution_schema,
                SAMPLING_ALGORITHM,
            )
            if (outcome.world_identity != self.world_identity or outcome.request_key != request_key
                    or request_key in self._requests
                    or record.normalized_inputs != expected_inputs
                    or type(outcome.revision) is not int or not 1 <= outcome.revision <= self._revision
                    or type(outcome.horizon_tick) is not int or outcome.horizon_tick < 0
                    or type(outcome.count) is not int or outcome.count < 0
                    or len(outcome.offspring_ids) != outcome.count
                    or len(outcome.origin_ticks) != outcome.count
                    or outcome.origin_ticks != tuple(sorted(outcome.origin_ticks))
                    or any(type(tick) is not int or tick < 0 or tick > outcome.horizon_tick
                           for tick in outcome.origin_ticks)
                    or outcome.parent_ids in expected_scopes
                    or outcome.parent_ids not in self._generation_parent_set_scopes
                    or self._generation_parent_set_scopes[outcome.parent_ids] != outcome.scope_digest
                    or outcome.coverage_scope != "this-parent-set-request-through-inclusive-horizon"
                    or outcome.parent_offspring_enumeration_complete is not False):
                raise RuntimeError("statistical generation scope or ownership is inconsistent")
            expected_scopes[outcome.parent_ids] = outcome.scope_digest
            if outcome.count == 0:
                if (outcome.group_id is not None or outcome.offspring_ids or outcome.origin_ticks
                        or outcome.parent_ids in self._group_id_by_parent_set):
                    raise RuntimeError("zero outcome incorrectly publishes a group or offspring")
            else:
                group = self._groups_by_id.get(outcome.group_id)
                if (group is None or group.parent_ids != outcome.parent_ids
                        or group.offspring_ids != outcome.offspring_ids
                        or tuple(self._offspring_origin_ticks.get(child) for child in outcome.offspring_ids)
                        != outcome.origin_ticks):
                    raise RuntimeError("positive statistical outcome lacks matching published facts")
                expected_origin_ticks.update(zip(outcome.offspring_ids, outcome.origin_ticks))
        if expected_scopes != self._generation_parent_set_scopes:
            raise RuntimeError("statistical parent-set scope index is inconsistent")
        from reproduction_generation import (
            INTERVAL_PROFILE_SCHEMA, PROGRESSIVE_ALGORITHM,
            ProgressiveReproductionHistory, ProgressiveReproductionRequest,
            TestOnlyIntervalReproductionProfile, _progressive_inputs,
        )
        expected_progressive_scopes = {}
        for parent_ids, history in self._progressive_histories.items():
            if (type(history) is not ProgressiveReproductionHistory
                    or history.world_identity != self.world_identity
                    or history.parent_ids != parent_ids
                    or history.profile_schema != INTERVAL_PROFILE_SCHEMA
                    or history.algorithm != PROGRESSIVE_ALGORITHM
                    or parent_ids in expected_scopes
                    or history.scope_digest != self._progressive_parent_set_scopes.get(parent_ids)
                    or type(history.revision) is not int or not 1 <= history.revision <= self._revision):
                raise RuntimeError("progressive history ownership or scope is inconsistent")
            expected_progressive_scopes[parent_ids] = history.scope_digest
            children = tuple(child for row in history.periods for child in row.offspring_ids)
            if len(set(children)) != len(children):
                raise RuntimeError("progressive history repeats an offspring identity")
            if children:
                group = self._groups_by_id.get(history.group_id)
                expected_group_id = f"RG-PROG-{history.scope_digest[:24]}"
                expected_source = (f"{INTERVAL_PROFILE_SCHEMA}:{history.profile_id}@"
                                   f"{history.profile_version}:{history.scope_digest}")
                if (history.group_id != expected_group_id or group is None
                        or group.parent_ids != parent_ids or group.offspring_ids != children
                        or group.source_reference != expected_source):
                    raise RuntimeError("progressive history does not match its authoritative group")
                expected_origin_ticks.update(
                    (child, row.period) for row in history.periods for child in row.offspring_ids
                )
            elif history.group_id is not None or parent_ids in self._group_id_by_parent_set:
                raise RuntimeError("zero-only progressive history created an empty group")
        if expected_progressive_scopes != self._progressive_parent_set_scopes:
            raise RuntimeError("progressive parent-set scope index is inconsistent")
        all_request_keys = set(self._requests) | set(self._generation_requests)
        if all_request_keys & set(self._progressive_requests):
            raise RuntimeError("publication request-key spaces overlap")
        if set(self._progressive_requests) != {
                record.result.request_key for record in self._progressive_requests.values()}:
            raise RuntimeError("progressive idempotency request index is inconsistent")
        for request_key, record in self._progressive_requests.items():
            result = record.result
            history = self._progressive_histories.get(result.parent_ids)
            if (result.world_identity != self.world_identity or result.request_key != request_key
                    or history is None or result.scope_digest != history.scope_digest
                    or result.through_period > history.through_period
                    or result.all_offspring_ids != tuple(
                        child for row in history.periods for child in row.offspring_ids
                    )[:len(result.all_offspring_ids)]):
                raise RuntimeError("progressive idempotency result is inconsistent with its history")
            request = ProgressiveReproductionRequest(
                result.parent_ids, history.world_seed, result.through_period,
                TestOnlyIntervalReproductionProfile(
                    history.profile_id, history.profile_version, history.weighted_counts_per_period
                ),
            )
            if record.normalized_inputs != _progressive_inputs(request) + (result.through_period,):
                raise RuntimeError("progressive idempotency request inputs are inconsistent")
        if expected_origin_ticks != self._offspring_origin_ticks:
            raise RuntimeError("offspring origin-time index is inconsistent")
        from being import BeingInstance
        native_bindings = self._native_beings_by_person_id
        if set(native_bindings) - set(self._group_id_by_offspring):
            raise RuntimeError("native Being binding does not refer to an established offspring")
        if len({id(being) for being in native_bindings.values()}) != len(native_bindings):
            raise RuntimeError("one native Being is bound to multiple logical offspring identities")
        for person_id, being in native_bindings.items():
            if (not isinstance(being, BeingInstance) or being.id != person_id
                    or self._world.object_registry.get_object_by_id(person_id) is not being):
                raise RuntimeError("native Being identity binding is inconsistent with ObjectRegistry")
        native_reproduction_ids = set(self._person_id_reservations) & set(self._world.object_registry.object_instances)
        if native_reproduction_ids != set(native_bindings):
            raise RuntimeError("logical Person/Object identity collision lacks an explicit native binding")
        if set(self._native_being_requests) & all_request_keys:
            raise RuntimeError("native Being materialization request keys overlap reproduction publication keys")
        if set(self._native_being_requests) != {
                record.request_key for record in self._native_being_requests.values()}:
            raise RuntimeError("native Being materialization request index is inconsistent")
        for request_key, record in self._native_being_requests.items():
            if (record.request_key != request_key
                    or self._native_beings_by_person_id.get(record.person_id) is not record.being
                    or record.being.id != record.person_id):
                raise RuntimeError("native Being materialization record is inconsistent")

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
            dict(self._offspring_origin_ticks),
            dict(self._generation_requests),
            dict(self._generation_parent_set_scopes),
            dict(self._progressive_histories),
            dict(self._progressive_parent_set_scopes),
            dict(self._progressive_requests),
            dict(self._native_beings_by_person_id),
            dict(self._native_being_requests),
        )

    def _restore_undo(self, undo) -> None:
        maps = (
            (self._groups_by_id, undo[0]),
            (self._group_id_by_parent_set, undo[1]),
            (self._group_id_by_offspring, undo[2]),
            (self._parent_set_by_offspring, undo[3]),
            (self._requests, undo[6]),
            (self._offspring_origin_ticks, undo[8]),
            (self._generation_requests, undo[9]),
            (self._generation_parent_set_scopes, undo[10]),
            (self._progressive_histories, undo[11]),
            (self._progressive_parent_set_scopes, undo[12]),
            (self._progressive_requests, undo[13]),
            (self._native_beings_by_person_id, undo[14]),
            (self._native_being_requests, undo[15]),
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
