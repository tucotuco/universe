"""Bounded statistical reproduction demo contract (explicitly test-only).

This module is an engineering demonstration, not an adopted species or
historical distribution. It samples from caller-supplied weighted counts and
abstract eligible ticks using a private deterministic Python RNG.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import random

from reproduction_group import ReproductionGroupValidationError


TEST_DISTRIBUTION_SCHEMA = "test-only-offspring-counts/1"
SAMPLING_ALGORITHM = "python-random-mt19937-randrange-sample-no-replacement-sorted/1"


def _text(value, name):
    if type(value) is not str or not value.strip():
        raise ReproductionGroupValidationError(f"{name} must be nonempty text")
    return value


@dataclass(frozen=True)
class TestOnlyOffspringCountDistribution:
    """An explicit finite weighted distribution; never a production default."""

    distribution_id: str
    version: str
    weighted_counts: tuple[tuple[int, int], ...]

    def __post_init__(self):
        _text(self.distribution_id, "distribution_id")
        _text(self.version, "distribution version")
        if type(self.weighted_counts) not in (tuple, list):
            raise ReproductionGroupValidationError("weighted_counts must be a tuple or list")
        rows = tuple(tuple(row) if type(row) in (tuple, list) else row
                     for row in self.weighted_counts)
        if not rows or any(type(row) is not tuple or len(row) != 2 for row in rows):
            raise ReproductionGroupValidationError("distribution requires weighted (count, weight) rows")
        if any(type(count) is not int or count < 0 or type(weight) is not int or weight <= 0
               for count, weight in rows):
            raise ReproductionGroupValidationError("counts must be nonnegative and integer weights positive")
        counts = tuple(count for count, _ in rows)
        if counts != tuple(sorted(set(counts))):
            raise ReproductionGroupValidationError("distribution counts must be unique and ascending")
        object.__setattr__(self, "weighted_counts", rows)


@dataclass(frozen=True)
class StatisticalReproductionRequest:
    """Bounded no-Encounter request using abstract integer origin-time ticks."""

    parent_ids: tuple[str, ...]
    seed: int
    horizon_tick: int
    eligible_origin_ticks: tuple[int, ...]
    distribution: TestOnlyOffspringCountDistribution

    def __post_init__(self):
        if type(self.parent_ids) not in (tuple, list):
            raise ReproductionGroupValidationError("parent_ids must be a tuple or list")
        parents = tuple(self.parent_ids)
        if not parents or any(type(p) is not str or not p.strip() for p in parents):
            raise ReproductionGroupValidationError("request requires nonempty parent identities")
        if len(set(parents)) != len(parents):
            raise ReproductionGroupValidationError("request parent identities must be unique")
        if type(self.seed) is not int or self.seed < 0:
            raise ReproductionGroupValidationError("seed must be a nonnegative integer")
        if type(self.horizon_tick) is not int or self.horizon_tick < 0:
            raise ReproductionGroupValidationError("horizon_tick must be a nonnegative integer")
        if type(self.eligible_origin_ticks) not in (tuple, list):
            raise ReproductionGroupValidationError("eligible_origin_ticks must be a tuple or list")
        ticks = tuple(self.eligible_origin_ticks)
        if (any(type(t) is not int or t < 0 or t > self.horizon_tick for t in ticks)
                or ticks != tuple(sorted(set(ticks)))):
            raise ReproductionGroupValidationError(
                "eligible ticks must be unique, ascending integers within the inclusive horizon"
            )
        if type(self.distribution) is not TestOnlyOffspringCountDistribution:
            raise ReproductionGroupValidationError("request requires an explicit test-only distribution")
        if max(count for count, _ in self.distribution.weighted_counts) > len(ticks):
            raise ReproductionGroupValidationError("count support exceeds eligible distinct origin ticks")
        object.__setattr__(self, "parent_ids", tuple(sorted(parents)))
        object.__setattr__(self, "eligible_origin_ticks", ticks)


@dataclass(frozen=True)
class PreparedStatisticalReproduction:
    """Immutable sampled facts and the registry revision they read."""

    parent_ids: tuple[str, ...]
    horizon_tick: int
    eligible_origin_ticks: tuple[int, ...]
    seed: int
    distribution_id: str
    distribution_version: str
    distribution_schema: str
    weighted_counts: tuple[tuple[int, int], ...]
    algorithm: str
    scope_digest: str
    world_identity: int
    base_revision: int
    offspring_count: int
    group_id: str | None
    offspring_ids: tuple[str, ...]
    origin_ticks: tuple[int, ...]
    source_reference: str

    def __post_init__(self):
        if not self.parent_ids or self.parent_ids != tuple(sorted(set(self.parent_ids))):
            raise ReproductionGroupValidationError("prepared parent set must be canonical and nonempty")
        if type(self.base_revision) is not int or self.base_revision < 0:
            raise ReproductionGroupValidationError("prepared registry revision is invalid")
        if type(self.world_identity) is not int or self.world_identity <= 0:
            raise ReproductionGroupValidationError("prepared world identity is invalid")
        if type(self.offspring_count) is not int or self.offspring_count < 0:
            raise ReproductionGroupValidationError("prepared offspring count is invalid")
        if len(self.offspring_ids) != self.offspring_count or len(self.origin_ticks) != self.offspring_count:
            raise ReproductionGroupValidationError("prepared offspring and origin records disagree")
        if (self.offspring_count == 0) != (self.group_id is None):
            raise ReproductionGroupValidationError("zero outcomes have no group; positive outcomes require one")
        if self.group_id is not None and (not self.offspring_ids or len(set(self.offspring_ids)) != self.offspring_count):
            raise ReproductionGroupValidationError("positive outcome requires unique offspring identities")
        if self.origin_ticks != tuple(sorted(self.origin_ticks)):
            raise ReproductionGroupValidationError("origin ticks must be ordered")


@dataclass(frozen=True)
class StatisticalReproductionOutcome:
    """Request-scoped published result; completeness is never global."""

    world_identity: int
    request_key: str
    scope_digest: str
    parent_ids: tuple[str, ...]
    horizon_tick: int
    eligible_origin_ticks: tuple[int, ...]
    count: int
    group_id: str | None
    offspring_ids: tuple[str, ...]
    origin_ticks: tuple[int, ...]
    seed: int
    distribution_id: str
    distribution_version: str
    distribution_schema: str
    weighted_counts: tuple[tuple[int, int], ...]
    algorithm: str
    source_reference: str
    revision: int
    coverage_scope: str = "this-parent-set-request-through-inclusive-horizon"
    parent_offspring_enumeration_complete: bool = False


@dataclass(frozen=True)
class _GenerationIdempotencyRecord:
    normalized_request: tuple
    normalized_inputs: tuple
    outcome: StatisticalReproductionOutcome


def _normalized_request(request: StatisticalReproductionRequest) -> tuple:
    distribution = request.distribution
    return (request.parent_ids, request.seed, request.horizon_tick,
            request.eligible_origin_ticks, distribution.distribution_id,
            distribution.version, distribution.weighted_counts,
            TEST_DISTRIBUTION_SCHEMA, SAMPLING_ALGORITHM)


def _sample(request: StatisticalReproductionRequest, base_revision: int,
            world_identity: int) -> PreparedStatisticalReproduction:
    normalized = _normalized_request(request)
    canonical = json.dumps(normalized, ensure_ascii=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("ascii")).hexdigest()
    rng = random.Random(request.seed)
    total = sum(weight for _, weight in request.distribution.weighted_counts)
    draw = rng.randrange(total)
    count = 0
    for value, weight in request.distribution.weighted_counts:
        if draw < weight:
            count = value
            break
        draw -= weight
    origin_ticks = tuple(sorted(rng.sample(request.eligible_origin_ticks, count))) if count else ()
    group_id = f"RG-STAT-{digest[:24]}" if count else None
    offspring_ids = tuple(f"PERSON-STAT-{digest[:24]}-{index + 1:04d}" for index in range(count))
    source = (f"{TEST_DISTRIBUTION_SCHEMA}:{request.distribution.distribution_id}@"
              f"{request.distribution.version}:{digest}")
    return PreparedStatisticalReproduction(
        request.parent_ids, request.horizon_tick, request.eligible_origin_ticks, request.seed,
        request.distribution.distribution_id, request.distribution.version,
        TEST_DISTRIBUTION_SCHEMA, request.distribution.weighted_counts, SAMPLING_ALGORITHM, digest,
        world_identity, base_revision, count, group_id, offspring_ids, origin_ticks, source,
    )


def prepare_statistical_reproduction(world, request: StatisticalReproductionRequest) -> PreparedStatisticalReproduction:
    """Sample a detached outcome without touching authoritative/global RNG.

    This first proof accepts only an unrepresented exact parent set. The
    registry revision is captured as a dependency and must still match at
    publication. Ticks are abstract, inclusive-horizon ordering values only.
    """
    if type(request) is not StatisticalReproductionRequest:
        raise ReproductionGroupValidationError("request must be a StatisticalReproductionRequest")
    snapshot = world.reproduction_group_snapshot()
    parents = request.parent_ids
    prepared = _sample(request, snapshot.revision, snapshot.world_identity)
    prior_scope = dict(snapshot.generation_parent_set_scopes).get(parents)
    if prior_scope is not None:
        if prior_scope != prepared.scope_digest:
            raise ReproductionGroupValidationError("exact parent set already has a different bounded generation outcome")
        return prepared
    if parents in {record.parent_ids for record in snapshot.groups}:
        raise ReproductionGroupValidationError("exact parent set already has an established ReproductionGroup")
    return prepared


def normalized_prepared_request(candidate: PreparedStatisticalReproduction) -> tuple:
    """Closed, canonical content used by the world publisher's idempotency check."""
    return (candidate.parent_ids, candidate.horizon_tick, candidate.eligible_origin_ticks, candidate.seed,
            candidate.distribution_id, candidate.distribution_version,
            candidate.distribution_schema, candidate.weighted_counts,
            candidate.algorithm, candidate.scope_digest, candidate.world_identity,
            candidate.offspring_count, candidate.group_id, candidate.offspring_ids,
            candidate.origin_ticks, candidate.source_reference)
