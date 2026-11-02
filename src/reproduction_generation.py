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
    if parents in {parent_set for parent_set, _ in snapshot.progressive_parent_set_scopes}:
        raise ReproductionGroupValidationError("exact parent set already has progressive test-profile history")
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


# Progressive profile-based V2. This intentionally has a separate versioned
# input contract from V1's one-shot whole-horizon count distribution.
INTERVAL_PROFILE_SCHEMA = "test-only-interval-count-profile/1"
PROGRESSIVE_ALGORITHM = "python-mt19937-hash-derived-period-stream/1"


@dataclass(frozen=True)
class TestOnlyIntervalReproductionProfile:
    """Explicit per-period test profile; it is not an adopted biology rule."""

    profile_id: str
    version: str
    weighted_counts_per_period: tuple[tuple[int, int], ...]

    def __post_init__(self):
        _text(self.profile_id, "profile_id")
        _text(self.version, "profile version")
        if type(self.weighted_counts_per_period) not in (tuple, list):
            raise ReproductionGroupValidationError("period count weights must be a tuple or list")
        rows = tuple(tuple(row) if type(row) in (tuple, list) else row
                     for row in self.weighted_counts_per_period)
        if not rows or any(type(row) is not tuple or len(row) != 2 for row in rows):
            raise ReproductionGroupValidationError("profile requires weighted (count, weight) rows")
        if any(type(count) is not int or count < 0 or type(weight) is not int or weight <= 0
               for count, weight in rows):
            raise ReproductionGroupValidationError("period counts must be nonnegative; weights positive")
        counts = tuple(count for count, _ in rows)
        if counts != tuple(sorted(set(counts))):
            raise ReproductionGroupValidationError("period count support must be unique and ascending")
        object.__setattr__(self, "weighted_counts_per_period", rows)


@dataclass(frozen=True)
class ProgressiveReproductionRequest:
    """Request to resolve through an inclusive abstract period index."""

    parent_ids: tuple[str, ...]
    world_seed: int
    target_period: int
    profile: TestOnlyIntervalReproductionProfile

    def __post_init__(self):
        if type(self.parent_ids) not in (tuple, list):
            raise ReproductionGroupValidationError("parent_ids must be a tuple or list")
        parents = tuple(self.parent_ids)
        if not parents or any(type(parent) is not str or not parent.strip() for parent in parents):
            raise ReproductionGroupValidationError("progressive request needs a nonempty exact parent set")
        if len(set(parents)) != len(parents):
            raise ReproductionGroupValidationError("progressive parent IDs must be unique")
        if type(self.world_seed) is not int or self.world_seed < 0:
            raise ReproductionGroupValidationError("world_seed must be a nonnegative integer")
        if type(self.target_period) is not int or self.target_period < 0:
            raise ReproductionGroupValidationError("target_period must be a nonnegative integer")
        if type(self.profile) is not TestOnlyIntervalReproductionProfile:
            raise ReproductionGroupValidationError("an explicit test-only interval profile is required")
        object.__setattr__(self, "parent_ids", tuple(sorted(parents)))


@dataclass(frozen=True)
class ProgressivePeriodCandidate:
    period: int
    count: int
    offspring_ids: tuple[str, ...]

    def __post_init__(self):
        if type(self.period) is not int or self.period < 0:
            raise ReproductionGroupValidationError("period must be a nonnegative abstract tick")
        if type(self.count) is not int or self.count < 0:
            raise ReproductionGroupValidationError("period count must be nonnegative")
        if type(self.offspring_ids) not in (tuple, list):
            raise ReproductionGroupValidationError("period offspring IDs must be a tuple or list")
        ids = tuple(self.offspring_ids)
        if (len(ids) != self.count or any(type(value) is not str or not value.strip() for value in ids)
                or len(set(ids)) != len(ids)):
            raise ReproductionGroupValidationError("period offspring identities do not match its count")
        object.__setattr__(self, "offspring_ids", ids)


@dataclass(frozen=True)
class PreparedProgressiveReproduction:
    world_identity: int
    base_revision: int
    parent_ids: tuple[str, ...]
    world_seed: int
    profile_id: str
    profile_version: str
    profile_schema: str
    weighted_counts_per_period: tuple[tuple[int, int], ...]
    algorithm: str
    scope_digest: str
    proposed_group_id: str
    previous_through_period: int
    previous_history_digest: str | None
    target_period: int
    new_periods: tuple[ProgressivePeriodCandidate, ...]
    source_reference: str

    def __post_init__(self):
        if type(self.world_identity) is not int or self.world_identity <= 0:
            raise ReproductionGroupValidationError("prepared world identity is invalid")
        if type(self.base_revision) is not int or self.base_revision < 0:
            raise ReproductionGroupValidationError("prepared revision is invalid")
        if type(self.parent_ids) not in (tuple, list):
            raise ReproductionGroupValidationError("prepared parent IDs must be a tuple or list")
        parents = tuple(self.parent_ids)
        if (not parents or any(type(value) is not str or not value.strip() for value in parents)
                or parents != tuple(sorted(set(parents)))):
            raise ReproductionGroupValidationError("prepared parent IDs must be canonical, unique and nonempty")
        for value, label in ((self.profile_id, "profile ID"), (self.profile_version, "profile version"),
                             (self.profile_schema, "profile schema"), (self.algorithm, "algorithm"),
                             (self.scope_digest, "scope digest"),
                             (self.proposed_group_id, "proposed group ID"),
                             (self.source_reference, "source reference")):
            _text(value, label)
        if type(self.world_seed) is not int or self.world_seed < 0:
            raise ReproductionGroupValidationError("prepared world seed is invalid")
        if type(self.previous_through_period) is not int or self.previous_through_period < -1:
            raise ReproductionGroupValidationError("previous period is invalid")
        if (self.previous_history_digest is not None
                and (type(self.previous_history_digest) is not str or not self.previous_history_digest)):
            raise ReproductionGroupValidationError("previous history digest is invalid")
        if type(self.target_period) is not int or self.target_period <= self.previous_through_period:
            raise ReproductionGroupValidationError("target must extend beyond the previous period")
        profile = TestOnlyIntervalReproductionProfile(
            self.profile_id, self.profile_version, self.weighted_counts_per_period
        )
        if type(self.new_periods) not in (tuple, list):
            raise ReproductionGroupValidationError("new periods must be a tuple or list")
        periods = tuple(self.new_periods)
        if (any(type(row) is not ProgressivePeriodCandidate for row in periods)
                or tuple(row.period for row in periods)
                != tuple(range(self.previous_through_period + 1, self.target_period + 1))):
            raise ReproductionGroupValidationError("candidate must cover its exact contiguous period suffix")
        object.__setattr__(self, "parent_ids", parents)
        object.__setattr__(self, "weighted_counts_per_period", profile.weighted_counts_per_period)
        object.__setattr__(self, "new_periods", periods)


@dataclass(frozen=True)
class ProgressiveReproductionHistory:
    """Only this test profile's explicitly resolved period prefix is covered."""

    world_identity: int
    parent_ids: tuple[str, ...]
    world_seed: int
    profile_id: str
    profile_version: str
    profile_schema: str
    weighted_counts_per_period: tuple[tuple[int, int], ...]
    algorithm: str
    scope_digest: str
    through_period: int
    group_id: str | None
    periods: tuple[ProgressivePeriodCandidate, ...]
    revision: int
    parent_global_history_complete: bool = False

    def __post_init__(self):
        if type(self.world_identity) is not int or self.world_identity <= 0:
            raise ReproductionGroupValidationError("history world identity is invalid")
        if type(self.parent_ids) not in (tuple, list):
            raise ReproductionGroupValidationError("history parent IDs must be a tuple or list")
        parents = tuple(self.parent_ids)
        if not parents or parents != tuple(sorted(set(parents))):
            raise ReproductionGroupValidationError("history parent set must be canonical and nonempty")
        profile = TestOnlyIntervalReproductionProfile(
            self.profile_id, self.profile_version, self.weighted_counts_per_period
        )
        if (self.profile_schema != INTERVAL_PROFILE_SCHEMA
                or self.algorithm != PROGRESSIVE_ALGORITHM
                or type(self.world_seed) is not int or self.world_seed < 0
                or type(self.through_period) is not int or self.through_period < 0
                or type(self.revision) is not int or self.revision <= 0
                or self.parent_global_history_complete is not False):
            raise ReproductionGroupValidationError("progressive history metadata is invalid")
        if type(self.periods) not in (tuple, list):
            raise ReproductionGroupValidationError("history periods must be a tuple or list")
        periods = tuple(self.periods)
        if (any(type(row) is not ProgressivePeriodCandidate for row in periods)
                or tuple(row.period for row in periods) != tuple(range(self.through_period + 1))):
            raise ReproductionGroupValidationError("history must contain the complete resolved period prefix")
        _text(self.scope_digest, "scope digest")
        expected_group = f"RG-PROG-{self.scope_digest[:24]}" if any(row.count for row in periods) else None
        if self.group_id != expected_group:
            raise ReproductionGroupValidationError("history group identity does not match its realized offspring")
        object.__setattr__(self, "parent_ids", parents)
        object.__setattr__(self, "weighted_counts_per_period", profile.weighted_counts_per_period)
        object.__setattr__(self, "periods", periods)


@dataclass(frozen=True)
class ProgressiveReproductionResult:
    world_identity: int
    request_key: str
    scope_digest: str
    parent_ids: tuple[str, ...]
    from_period: int
    through_period: int
    added_periods: tuple[ProgressivePeriodCandidate, ...]
    group_id: str | None
    all_offspring_ids: tuple[str, ...]
    revision: int
    parent_global_history_complete: bool = False

    def __post_init__(self):
        if type(self.world_identity) is not int or self.world_identity <= 0:
            raise ReproductionGroupValidationError("result world identity is invalid")
        _text(self.request_key, "request key")
        _text(self.scope_digest, "scope digest")
        if (type(self.parent_ids) not in (tuple, list) or not self.parent_ids
                or tuple(self.parent_ids) != tuple(sorted(set(self.parent_ids)))):
            raise ReproductionGroupValidationError("result parent IDs must be canonical and nonempty")
        if (type(self.from_period) is not int or self.from_period < 0
                or type(self.through_period) is not int or self.through_period < self.from_period
                or type(self.revision) is not int or self.revision <= 0
                or self.parent_global_history_complete is not False):
            raise ReproductionGroupValidationError("progressive result metadata is invalid")
        if type(self.added_periods) not in (tuple, list):
            raise ReproductionGroupValidationError("result periods must be a tuple or list")
        periods = tuple(self.added_periods)
        if (any(type(row) is not ProgressivePeriodCandidate for row in periods)
                or tuple(row.period for row in periods) != tuple(range(self.from_period, self.through_period + 1))):
            raise ReproductionGroupValidationError("result periods do not match its declared suffix")
        children = tuple(child for row in periods for child in row.offspring_ids)
        all_children = tuple(self.all_offspring_ids)
        if len(set(all_children)) != len(all_children) or not set(children).issubset(all_children):
            raise ReproductionGroupValidationError("result cumulative offspring identities are inconsistent")
        if bool(all_children) != bool(self.group_id):
            raise ReproductionGroupValidationError("zero cumulative outcome must not name a group")
        if self.group_id is not None:
            _text(self.group_id, "group ID")
        object.__setattr__(self, "parent_ids", tuple(self.parent_ids))
        object.__setattr__(self, "added_periods", periods)
        object.__setattr__(self, "all_offspring_ids", all_children)


@dataclass(frozen=True)
class _ProgressiveIdempotencyRecord:
    normalized_request: tuple
    normalized_inputs: tuple
    result: ProgressiveReproductionResult


def _progressive_inputs(request: ProgressiveReproductionRequest) -> tuple:
    profile = request.profile
    return (request.parent_ids, request.world_seed, profile.profile_id, profile.version,
            INTERVAL_PROFILE_SCHEMA, profile.weighted_counts_per_period, PROGRESSIVE_ALGORITHM)


def _period_draw(scope_digest: str, period: int, rows: tuple[tuple[int, int], ...]) -> int:
    stream_material = f"{scope_digest}:period:{period}:{PROGRESSIVE_ALGORITHM}".encode("ascii")
    stream_seed = int.from_bytes(hashlib.sha256(stream_material).digest(), "big")
    rng = random.Random(stream_seed)
    draw = rng.randrange(sum(weight for _, weight in rows))
    for count, weight in rows:
        if draw < weight:
            return count
        draw -= weight
    raise AssertionError("positive count weights did not select a period outcome")


def _progressive_digest(inputs: tuple) -> str:
    encoded = json.dumps(inputs, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("ascii")).hexdigest()


def _progressive_periods(scope_digest: str, start: int, target: int,
                         rows: tuple[tuple[int, int], ...]) -> tuple[ProgressivePeriodCandidate, ...]:
    periods = []
    for period in range(start, target + 1):
        count = _period_draw(scope_digest, period, rows)
        ids = tuple(
            f"PERSON-PROG-{scope_digest[:24]}-T{period:06d}-{index + 1:03d}"
            for index in range(count)
        )
        periods.append(ProgressivePeriodCandidate(period, count, ids))
    return tuple(periods)


def _progressive_scope_digest(request: ProgressiveReproductionRequest) -> str:
    return _progressive_digest(_progressive_inputs(request))


def _progressive_history_digest(history: ProgressiveReproductionHistory | None) -> str | None:
    if history is None:
        return None
    data = (history.parent_ids, history.world_seed, history.profile_id, history.profile_version,
            history.profile_schema, history.weighted_counts_per_period, history.algorithm,
            history.scope_digest, history.through_period, history.group_id,
            tuple((row.period, row.count, row.offspring_ids) for row in history.periods))
    return _progressive_digest(data)


def _progressive_prefix_digest(history: ProgressiveReproductionHistory, through_period: int) -> str | None:
    if through_period < 0:
        return None
    periods = history.periods[:through_period + 1]
    if len(periods) != through_period + 1:
        raise ReproductionGroupValidationError("requested history prefix is unavailable")
    group_id = f"RG-PROG-{history.scope_digest[:24]}" if any(row.count for row in periods) else None
    data = (history.parent_ids, history.world_seed, history.profile_id, history.profile_version,
            history.profile_schema, history.weighted_counts_per_period, history.algorithm,
            history.scope_digest, through_period, group_id,
            tuple((row.period, row.count, row.offspring_ids) for row in periods))
    return _progressive_digest(data)


def prepare_progressive_reproduction(world, request: ProgressiveReproductionRequest) -> PreparedProgressiveReproduction:
    """Prepare only the uncommitted period suffix; earlier periods are immutable."""
    if type(request) is not ProgressiveReproductionRequest:
        raise ReproductionGroupValidationError("request must be ProgressiveReproductionRequest")
    snapshot = world.reproduction_group_snapshot()
    by_parent = {history.parent_ids: history for history in snapshot.progressive_histories}
    history = by_parent.get(request.parent_ids)
    scope_digest = _progressive_scope_digest(request)
    if history is None:
        if request.parent_ids in {parent_set for parent_set, _ in snapshot.generation_parent_set_scopes}:
            raise ReproductionGroupValidationError("exact parent set already has a V1 generation scope")
        if request.parent_ids in {group.parent_ids for group in snapshot.groups}:
            raise ReproductionGroupValidationError("exact parent set already has an established ReproductionGroup")
        previous = -1
        prior_digest = None
    else:
        if history.scope_digest != scope_digest:
            raise ReproductionGroupValidationError("parent set already has a different progressive profile/seed")
        if request.target_period <= history.through_period:
            raise ReproductionGroupValidationError(
                "progressive request must extend beyond the resolved horizon; overlapping scopes are refused"
            )
        previous = history.through_period
        prior_digest = _progressive_history_digest(history)
    profile = request.profile
    group_id = f"RG-PROG-{scope_digest[:24]}"
    source = f"{INTERVAL_PROFILE_SCHEMA}:{profile.profile_id}@{profile.version}:{scope_digest}"
    return PreparedProgressiveReproduction(
        snapshot.world_identity, snapshot.revision, request.parent_ids, request.world_seed,
        profile.profile_id, profile.version, INTERVAL_PROFILE_SCHEMA,
        profile.weighted_counts_per_period, PROGRESSIVE_ALGORITHM, scope_digest,
        group_id, previous, prior_digest,
        request.target_period,
        _progressive_periods(scope_digest, previous + 1, request.target_period,
                             profile.weighted_counts_per_period),
        source,
    )


def normalized_progressive_candidate(candidate: PreparedProgressiveReproduction) -> tuple:
    return (candidate.world_identity, candidate.parent_ids, candidate.world_seed,
            candidate.profile_id, candidate.profile_version, candidate.profile_schema,
            candidate.weighted_counts_per_period, candidate.algorithm, candidate.scope_digest,
            candidate.proposed_group_id, candidate.previous_through_period,
            candidate.previous_history_digest, candidate.target_period, candidate.new_periods,
            candidate.source_reference)
