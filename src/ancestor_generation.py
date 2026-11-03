"""Bounded, world-only reverse-direction ancestry generation experiment.

This module attaches newly generated logical parent identities to one existing
logical Person through the existing ReproductionGroup publisher. Parent counts
and optional sibling counts are test inputs, not adopted biological rules.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import random

from reproduction_generation import TestOnlyOffspringCountDistribution
from reproduction_group import (
    PreparedReproductionGroupCandidate,
    ReproductionGroupProposal,
    ReproductionGroupPublicationError,
    StaleReproductionGroupRevision,
    prepare_reproduction_group,
)


ANCESTOR_GENERATION_SCHEMA = "test-only-reverse-ancestor-generation/1"


class AncestorGenerationError(ValueError):
    """A request or read snapshot cannot safely support the bounded operation."""


@dataclass(frozen=True)
class ResolveParentsRequest:
    """World-authored request for an existing logical Person's parentage."""

    person_id: str
    parent_count: int
    seed: int
    additional_sibling_distribution: TestOnlyOffspringCountDistribution

    def __post_init__(self):
        if type(self.person_id) is not str or not self.person_id.strip():
            raise AncestorGenerationError("person_id must be nonempty text")
        if type(self.parent_count) is not int or self.parent_count < 1:
            raise AncestorGenerationError("parent_count must be an explicit positive integer")
        if type(self.seed) is not int or self.seed < 0:
            raise AncestorGenerationError("seed must be a nonnegative integer")
        if type(self.additional_sibling_distribution) is not TestOnlyOffspringCountDistribution:
            raise AncestorGenerationError("an explicit test-only additional-sibling distribution is required")


@dataclass(frozen=True)
class PreparedAncestorGeneration:
    """Detached plan for one existing Person plus optional new siblings."""

    request: ResolveParentsRequest
    world_identity: int
    base_revision: int
    parent_ids: tuple[str, ...]
    additional_sibling_count: int
    sibling_ids: tuple[str, ...]
    scope_digest: str
    candidate: PreparedReproductionGroupCandidate

    def __post_init__(self):
        if type(self.request) is not ResolveParentsRequest:
            raise AncestorGenerationError("prepared plan has an unsupported request")
        if type(self.world_identity) is not int or self.world_identity <= 0:
            raise AncestorGenerationError("prepared plan has an invalid world owner")
        if type(self.base_revision) is not int or self.base_revision < 0:
            raise AncestorGenerationError("prepared plan has an invalid registry revision")
        if type(self.candidate) is not PreparedReproductionGroupCandidate:
            raise AncestorGenerationError("prepared plan requires the native group candidate")
        expected = _plan_fields(self.request)
        parent_ids, count, sibling_ids, digest, group_id, source = expected
        if (self.parent_ids != parent_ids or self.additional_sibling_count != count
                or self.sibling_ids != sibling_ids or self.scope_digest != digest
                or self.candidate.group_id != group_id
                or self.candidate.parent_ids != parent_ids
                or self.candidate.offspring_ids != (self.request.person_id, *sibling_ids)
                or self.candidate.source_reference != source):
            raise AncestorGenerationError("prepared plan does not match its deterministic request")

    @property
    def offspring_enumeration_complete(self) -> bool:
        return False


def _plan_fields(request):
    """Deterministically derive test-only IDs and one optional-sibling draw."""
    distribution = request.additional_sibling_distribution
    weights = distribution.weighted_counts
    total = sum(weight for _count, weight in weights)
    point = random.Random(request.seed).randrange(total)
    sibling_count = 0
    for count, weight in weights:
        if point < weight:
            sibling_count = count
            break
        point -= weight
    normalized = (
        ANCESTOR_GENERATION_SCHEMA,
        request.person_id,
        request.parent_count,
        request.seed,
        distribution.distribution_id,
        distribution.version,
        distribution.weighted_counts,
    )
    encoded = json.dumps(normalized, ensure_ascii=True, separators=(",", ":"))
    digest = hashlib.sha256(encoded.encode("ascii")).hexdigest()
    parent_ids = tuple(
        f"PERSON-V9-ANCESTOR-{digest[:24]}-{index + 1:03d}"
        for index in range(request.parent_count)
    )
    sibling_ids = tuple(
        f"PERSON-V9-SIBLING-{digest[:24]}-{index + 1:04d}"
        for index in range(sibling_count)
    )
    group_id = f"RG-V9-ANCESTOR-{digest[:24]}"
    source = (f"{ANCESTOR_GENERATION_SCHEMA}:{distribution.distribution_id}@"
             f"{distribution.version}:{digest}")
    return parent_ids, sibling_count, sibling_ids, digest, group_id, source


def prepare_resolve_parents(world, request: ResolveParentsRequest, *, request_key: str) -> PreparedAncestorGeneration:
    """Prepare without writes or global RNG use, reading only a detached snapshot."""
    if type(request) is not ResolveParentsRequest:
        raise AncestorGenerationError("request must be a ResolveParentsRequest")
    if type(request_key) is not str or not request_key.strip():
        raise AncestorGenerationError("request_key must be nonempty text")
    snapshot = world.reproduction_group_snapshot()
    if request.person_id not in snapshot.person_id_reservations:
        raise AncestorGenerationError("the focal Person must already exist in logical reproductive Reality")
    if not any(request.person_id in group.parent_ids for group in snapshot.groups):
        raise AncestorGenerationError("the focal Person must already be established as a logical parent")
    idempotent_retry = request_key in snapshot.request_keys
    if snapshot.known_parents(request.person_id) is not None and not idempotent_retry:
        raise ReproductionGroupPublicationError("the focal Person already has an established exact parent set")

    parent_ids, sibling_count, sibling_ids, digest, group_id, source = _plan_fields(request)
    if request.person_id in parent_ids or request.person_id in sibling_ids:
        raise AncestorGenerationError("deterministic identity collision with the focal Person")
    if len(set(parent_ids)) != request.parent_count or set(parent_ids) & set(sibling_ids):
        raise AncestorGenerationError("deterministic Person identities are not unique")
    if not idempotent_retry:
        reserved_people = set(snapshot.person_id_reservations)
        # Zero-only V1/V2 scopes do not reserve People in the group indexes,
        # but their immutable requests still contain authoritative logical
        # Person references. Do not mint one of those names as a new ancestor.
        referenced_people = set(reserved_people)
        for outcome in snapshot.generation_outcomes:
            referenced_people.update(outcome.parent_ids)
        for history in snapshot.progressive_histories:
            referenced_people.update(history.parent_ids)
        reserved_groups = set(snapshot.group_id_reservations)
        object_ids = set(world.object_registry.object_instances)
        generated_people = set(parent_ids) | set(sibling_ids)
        if generated_people & (referenced_people | reserved_groups | object_ids):
            raise ReproductionGroupPublicationError("generated logical Person identity collides with existing state")
        if group_id in reserved_people | reserved_groups | object_ids:
            raise ReproductionGroupPublicationError("generated ReproductionGroup identity collides with existing state")
        if parent_ids in {tuple(row[0]) for row in snapshot.group_id_by_parent_set}:
            raise ReproductionGroupPublicationError("generated exact parent set already has a ReproductionGroup")

    candidate = prepare_reproduction_group(ReproductionGroupProposal(
        group_id, parent_ids, (request.person_id, *sibling_ids), source,
    ))
    return PreparedAncestorGeneration(
        request, snapshot.world_identity, snapshot.revision, parent_ids,
        sibling_count, sibling_ids, digest, candidate,
    )


def resolve_parents(world, request: ResolveParentsRequest, *, request_key: str,
                    expected_revision: int | None = None, _fail_after: str | None = None):
    """Publish one prepared plan through Universe's existing atomic publisher."""
    prepared = prepare_resolve_parents(world, request, request_key=request_key)
    if prepared.world_identity != id(world):
        raise ReproductionGroupPublicationError("prepared ancestor plan belongs to another Universe")
    if expected_revision is not None and type(expected_revision) is not int:
        raise AncestorGenerationError("expected_revision must be an integer or None")
    if (expected_revision is not None and expected_revision != prepared.base_revision
            and request_key not in world.reproduction_group_snapshot().request_keys):
        raise StaleReproductionGroupRevision(
            f"expected revision {expected_revision}, current is {prepared.base_revision}"
        )
    return world.publish_reproduction_group(
        prepared.candidate,
        request_key=request_key,
        expected_revision=prepared.base_revision,
        _fail_after=_fail_after,
    )
