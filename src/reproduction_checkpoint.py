"""Versioned, reproduction-domain-only save/restore and continuation.

This format contains logical reproductive records only. It is not a general
Universe checkpoint, and its SHA-256 digest detects accidental corruption;
it does not authenticate a file or its author.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, replace
import hashlib
import json
from threading import RLock
from types import SimpleNamespace

from reproduction_generation import (
    INTERVAL_PROFILE_SCHEMA, PROGRESSIVE_ALGORITHM, SAMPLING_ALGORITHM,
    TEST_DISTRIBUTION_SCHEMA, ProgressivePeriodCandidate,
    ProgressiveReproductionHistory, ProgressiveReproductionResult,
    ProgressiveReproductionRequest, StatisticalReproductionOutcome,
    StatisticalReproductionRequest, _GenerationIdempotencyRecord,
    _ProgressiveIdempotencyRecord,
    TestOnlyIntervalReproductionProfile, TestOnlyOffspringCountDistribution,
    _normalized_request, _progressive_history_digest, _progressive_inputs,
    _progressive_prefix_digest, normalized_prepared_request,
)
from reproduction_group import (
    InjectedReproductionGroupFailure, ReproductionGroupRecord,
    ReproductionGroupPublicationResult, ReproductionGroupRegistry,
    _IdempotencyRecord,
)


CHECKPOINT_SCHEMA = "universe-reproduction-domain-checkpoint"
CHECKPOINT_VERSION = 3
LEGACY_CHECKPOINT_VERSION = 1
PREVIOUS_CHECKPOINT_VERSION = 2
REGISTRY_CONTRACT = "logical-reproduction-registry/3"
LEGACY_REGISTRY_CONTRACT = "logical-reproduction-registry/1"
PREVIOUS_REGISTRY_CONTRACT = "logical-reproduction-registry/2"
RESTORE_FAILURE_PHASES = (
    "groups", "indexes", "aliases", "authored_requests", "v1_records", "v2_records",
    "revision", "consistency",
)


class ReproductionCheckpointError(ValueError):
    """Base error for the bounded reproduction checkpoint contract."""


class ReproductionCheckpointValidationError(ReproductionCheckpointError):
    """A checkpoint is malformed, incompatible, or internally inconsistent."""


class ReproductionCheckpointRestoreError(ReproductionCheckpointError):
    """A valid checkpoint cannot be restored into the selected Universe."""


class InjectedReproductionCheckpointFailure(RuntimeError):
    """Private deterministic fault injection for restore rollback tests."""


@dataclass(frozen=True)
class DetachedReproductionCheckpoint:
    source_world_identity: int
    revision: int
    groups: tuple[ReproductionGroupRecord, ...]
    group_id_by_parent_set: tuple
    group_id_by_offspring: tuple
    parent_set_by_offspring: tuple
    person_id_reservations: tuple[str, ...]
    group_id_reservations: tuple[str, ...]
    offspring_origin_ticks: tuple
    authored_requests: tuple
    generation_parent_set_scopes: tuple
    generation_requests: tuple
    progressive_histories: tuple[ProgressiveReproductionHistory, ...]
    progressive_parent_set_scopes: tuple
    progressive_requests: tuple
    wire_version: int = CHECKPOINT_VERSION
    group_id_aliases: tuple = ()


def _fail(message):
    raise ReproductionCheckpointValidationError(message)


def _strict_object(value, keys, label):
    if type(value) is not dict or set(value) != set(keys):
        _fail(f"{label} has missing or unknown fields")
    return value


def _int(value, label, minimum=None):
    if type(value) is not int or (minimum is not None and value < minimum):
        _fail(f"{label} must be an integer" + (f" >= {minimum}" if minimum is not None else ""))
    return value


def _str(value, label):
    if type(value) is not str or not value.strip():
        _fail(f"{label} must be nonempty text")
    return value


def _array(value, label):
    if type(value) is not list:
        _fail(f"{label} must be a JSON array")
    return value


def _pairs(value, label, left, right):
    rows = []
    for index, row in enumerate(_array(value, label)):
        if type(row) is not list or len(row) != 2:
            _fail(f"{label}[{index}] must contain two values")
        rows.append((left(row[0], f"{label}[{index}][0]"), right(row[1], f"{label}[{index}][1]")))
    if len({key for key, _ in rows}) != len(rows):
        _fail(f"{label} contains duplicate keys")
    return tuple(rows)


def _tuple_strings(value, label, nonempty=False):
    result = tuple(_str(item, f"{label} entry") for item in _array(value, label))
    if nonempty and not result:
        _fail(f"{label} must not be empty")
    if len(set(result)) != len(result):
        _fail(f"{label} contains duplicate identities")
    return result


def _tuple_of_pairs(value, label, first, second):
    return _pairs(value, label, first, second)


def _normalization_to_data(value):
    if type(value) is tuple:
        return [_normalization_to_data(item) for item in value]
    if type(value) is list:
        return [_normalization_to_data(item) for item in value]
    if type(value) is ProgressivePeriodCandidate:
        return {"$period": {"period": value.period, "count": value.count,
                            "offspring_ids": list(value.offspring_ids)}}
    if value is None or type(value) in (str, int, bool):
        return value
    _fail(f"unsupported idempotency normalization value: {type(value).__name__}")


def _normalization_from_data(value):
    if type(value) is list:
        return tuple(_normalization_from_data(item) for item in value)
    if type(value) is dict:
        if set(value) != {"$period"}:
            _fail("unsupported object in idempotency normalization")
        row = _strict_object(value["$period"], {"period", "count", "offspring_ids"}, "period normalization")
        return ProgressivePeriodCandidate(
            _int(row["period"], "period", 0), _int(row["count"], "count", 0),
            _tuple_strings(row["offspring_ids"], "period offspring IDs"),
        )
    if value is None or type(value) in (str, int, bool):
        return value
    _fail("unsupported JSON value in idempotency normalization")


def _data_fields(instance):
    return {field.name: _normalization_to_data(getattr(instance, field.name)) for field in fields(instance)}


def _group_from_data(value, *, version):
    keys = {"world_identity", "group_id", "parent_ids", "offspring_ids", "source_reference", "revision"}
    if version >= 2:
        keys.add("parents_complete")
    row = _strict_object(value, keys, "group record")
    complete = True if version == 1 else row["parents_complete"]
    if type(complete) is not bool:
        _fail("group parents_complete must be explicitly boolean in checkpoint V2")
    return ReproductionGroupRecord(
        _int(row["world_identity"], "group world identity", 1), _str(row["group_id"], "group ID"),
        _tuple_strings(row["parent_ids"], "group parents", True),
        _tuple_strings(row["offspring_ids"], "group offspring", True),
        _str(row["source_reference"], "group source"), _int(row["revision"], "group revision", 1),
        complete,
    )


def _authored_result_from_data(value, *, version):
    keys = {"world_identity", "group_id", "parent_ids", "offspring_ids",
            "source_reference", "request_key", "revision"}
    if version >= 2:
        keys.add("parents_complete")
    row = _strict_object(value, keys, "authored result")
    complete = True if version == 1 else row["parents_complete"]
    if type(complete) is not bool:
        _fail("authored result parents_complete must be explicitly boolean in checkpoint V2")
    return ReproductionGroupPublicationResult(
        _int(row["world_identity"], "result world identity", 1), _str(row["group_id"], "result group ID"),
        _tuple_strings(row["parent_ids"], "result parents", True),
        _tuple_strings(row["offspring_ids"], "result offspring", True),
        _str(row["source_reference"], "result source"), _str(row["request_key"], "result request key"),
        _int(row["revision"], "result revision", 1), complete,
    )


def _group_to_data(group):
    """V2 wire representation, explicit about parent-membership completeness."""
    return {
        "world_identity": group.world_identity,
        "group_id": group.group_id,
        "parent_ids": list(group.parent_ids),
        "offspring_ids": list(group.offspring_ids),
        "source_reference": group.source_reference,
        "revision": group.revision,
        "parents_complete": group.parents_complete,
    }


def _authored_result_to_data(result):
    return {
        "world_identity": result.world_identity,
        "group_id": result.group_id,
        "parent_ids": list(result.parent_ids),
        "offspring_ids": list(result.offspring_ids),
        "source_reference": result.source_reference,
        "request_key": result.request_key,
        "revision": result.revision,
        "parents_complete": result.parents_complete,
    }


def _period_from_data(value):
    if type(value) is dict and set(value) == {"$period"}:
        value = value["$period"]
    row = _strict_object(value, {"period", "count", "offspring_ids"}, "period record")
    return ProgressivePeriodCandidate(
        _int(row["period"], "period", 0), _int(row["count"], "period count", 0),
        _tuple_strings(row["offspring_ids"], "period offspring"),
    )


def _outcome_from_data(value):
    keys = {field.name for field in fields(StatisticalReproductionOutcome)}
    row = _strict_object(value, keys, "V1 outcome")
    parsed = dict(row)
    parsed["world_identity"] = _int(row["world_identity"], "V1 world identity", 1)
    parsed["request_key"] = _str(row["request_key"], "V1 request key")
    parsed["scope_digest"] = _str(row["scope_digest"], "V1 scope digest")
    parsed["parent_ids"] = _tuple_strings(row["parent_ids"], "V1 parents", True)
    parsed["horizon_tick"] = _int(row["horizon_tick"], "V1 horizon", 0)
    parsed["eligible_origin_ticks"] = tuple(_int(x, "V1 eligible tick", 0)
                                            for x in _array(row["eligible_origin_ticks"], "V1 eligible ticks"))
    parsed["count"] = _int(row["count"], "V1 count", 0)
    parsed["group_id"] = None if row["group_id"] is None else _str(row["group_id"], "V1 group ID")
    parsed["offspring_ids"] = _tuple_strings(row["offspring_ids"], "V1 offspring")
    parsed["origin_ticks"] = tuple(_int(x, "V1 origin tick", 0) for x in _array(row["origin_ticks"], "V1 origin ticks"))
    parsed["seed"] = _int(row["seed"], "V1 seed", 0)
    parsed["distribution_id"] = _str(row["distribution_id"], "V1 distribution ID")
    parsed["distribution_version"] = _str(row["distribution_version"], "V1 distribution version")
    parsed["distribution_schema"] = _str(row["distribution_schema"], "V1 distribution schema")
    parsed["weighted_counts"] = _pairs(row["weighted_counts"], "V1 weighted counts",
                                       lambda v, n: _int(v, n, 0), lambda v, n: _int(v, n, 1))
    parsed["algorithm"] = _str(row["algorithm"], "V1 algorithm")
    parsed["source_reference"] = _str(row["source_reference"], "V1 source reference")
    parsed["revision"] = _int(row["revision"], "V1 revision", 1)
    if type(row["coverage_scope"]) is not str or type(row["parent_offspring_enumeration_complete"]) is not bool:
        _fail("V1 completeness metadata has invalid types")
    return StatisticalReproductionOutcome(**parsed)


def _progressive_history_from_data(value):
    keys = {field.name for field in fields(ProgressiveReproductionHistory)}
    row = _strict_object(value, keys, "progressive history")
    return ProgressiveReproductionHistory(
        _int(row["world_identity"], "V2 history world identity", 1),
        _tuple_strings(row["parent_ids"], "V2 history parents", True),
        _int(row["world_seed"], "V2 world seed", 0), _str(row["profile_id"], "V2 profile ID"),
        _str(row["profile_version"], "V2 profile version"), _str(row["profile_schema"], "V2 profile schema"),
        _pairs(row["weighted_counts_per_period"], "V2 profile weights",
               lambda v, n: _int(v, n, 0), lambda v, n: _int(v, n, 1)),
        _str(row["algorithm"], "V2 algorithm"), _str(row["scope_digest"], "V2 scope digest"),
        _int(row["through_period"], "V2 horizon", 0),
        None if row["group_id"] is None else _str(row["group_id"], "V2 group ID"),
        tuple(_period_from_data(item) for item in _array(row["periods"], "V2 periods")),
        _int(row["revision"], "V2 revision", 1), row["parent_global_history_complete"],
    )


def _progressive_result_from_data(value):
    keys = {field.name for field in fields(ProgressiveReproductionResult)}
    row = _strict_object(value, keys, "progressive result")
    return ProgressiveReproductionResult(
        _int(row["world_identity"], "V2 result world identity", 1),
        _str(row["request_key"], "V2 request key"), _str(row["scope_digest"], "V2 result scope"),
        _tuple_strings(row["parent_ids"], "V2 result parents", True),
        _int(row["from_period"], "V2 first period", 0), _int(row["through_period"], "V2 result horizon", 0),
        tuple(_period_from_data(item) for item in _array(row["added_periods"], "V2 added periods")),
        None if row["group_id"] is None else _str(row["group_id"], "V2 result group ID"),
        _tuple_strings(row["all_offspring_ids"], "V2 cumulative offspring"),
        _int(row["revision"], "V2 result revision", 1), row["parent_global_history_complete"],
    )


def _canonical(value):
    try:
        return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ReproductionCheckpointValidationError(f"checkpoint is not canonical JSON data: {exc}") from exc


def _reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _fail(f"duplicate JSON field: {key}")
        result[key] = value
    return result


def _compatible_context(world, *, require_empty=False):
    from encounter import Encounter
    from transactional_progression import is_quarantined
    if is_quarantined(world):
        raise ReproductionCheckpointRestoreError("quarantined Universes cannot use reproduction checkpoints")
    if any(isinstance(event, Encounter) for event in world.event_history.values()) or world._choice_books:
        raise ReproductionCheckpointRestoreError("reproduction checkpoint is no-Encounter only")
    registry = world._reproduction_group_registry
    if registry._world is not world or world._reproduction_group_registry is not registry:
        raise ReproductionCheckpointRestoreError("reproduction registry ownership is inconsistent")
    if require_empty:
        if (registry.revision != 0 or world.object_registry.object_instances
                or set(world.event_history) != {"0"}):
            raise ReproductionCheckpointRestoreError(
                "restore requires a fresh compatible Universe with no Objects or reproduction state"
            )
        origin = world.event_history.get("0")
        if origin is None or getattr(origin, "id", None) != "0":
            raise ReproductionCheckpointRestoreError("fresh Universe origin event is incompatible")
    else:
        ids = set(registry._person_id_reservations) | set(registry._group_id_reservations)
        object_ids = set(world.object_registry.object_instances)
        if ids & object_ids:
            raise ReproductionCheckpointValidationError("logical reproduction IDs collide with native Objects")
    return registry


def _registry_data(registry):
    return {
        "revision": registry._revision,
        "groups": [_group_to_data(registry._groups_by_id[key]) for key in sorted(registry._groups_by_id)],
        "indexes": {
            "group_id_by_parent_set": [[list(key), value] for key, value in sorted(registry._group_id_by_parent_set.items())],
            "group_id_by_offspring": [list(item) for item in sorted(registry._group_id_by_offspring.items())],
            "parent_set_by_offspring": [[key, list(value)] for key, value in sorted(registry._parent_set_by_offspring.items())],
            "person_id_reservations": sorted(registry._person_id_reservations),
            "group_id_reservations": sorted(registry._group_id_reservations),
            "group_id_aliases": [list(item) for item in sorted(registry._group_id_aliases.items())],
            "offspring_origin_ticks": [list(item) for item in sorted(registry._offspring_origin_ticks.items())],
            "generation_parent_set_scopes": [[list(key), value] for key, value in sorted(registry._generation_parent_set_scopes.items())],
            "progressive_parent_set_scopes": [[list(key), value] for key, value in sorted(registry._progressive_parent_set_scopes.items())],
        },
        "authored_requests": [
            {"request_key": key, "normalized_request": _normalization_to_data(record.normalized_request),
             "result": _authored_result_to_data(record.result)}
            for key, record in sorted(registry._requests.items())
        ],
        "generation_requests": [
            {"request_key": key, "normalized_request": _normalization_to_data(record.normalized_request),
             "normalized_inputs": _normalization_to_data(record.normalized_inputs),
             "outcome": _data_fields(record.outcome)}
            for key, record in sorted(registry._generation_requests.items())
        ],
        "progressive_histories": [
            _data_fields(registry._progressive_histories[key])
            for key in sorted(registry._progressive_histories)
        ],
        "progressive_requests": [
            {"request_key": key, "normalized_request": _normalization_to_data(record.normalized_request),
             "normalized_inputs": _normalization_to_data(record.normalized_inputs),
             "result": _data_fields(record.result)}
            for key, record in sorted(registry._progressive_requests.items())
        ],
    }


def encode_reproduction_checkpoint(world) -> str:
    """Return a human-readable, versioned snapshot without mutating the world."""
    with world._schedule_lock:
        registry = _compatible_context(world)
        if registry._revision:
            registry._assert_consistent()
        elif any((registry._groups_by_id, registry._group_id_by_parent_set,
                  registry._group_id_by_offspring, registry._parent_set_by_offspring,
                  registry._person_id_reservations, registry._group_id_reservations,
                  registry._group_id_aliases,
                  registry._requests, registry._offspring_origin_ticks,
                  registry._generation_requests, registry._generation_parent_set_scopes,
                  registry._progressive_histories, registry._progressive_parent_set_scopes,
                  registry._progressive_requests)):
            raise ReproductionCheckpointValidationError(
                "revision-zero registry contains unpublished records"
            )
        payload = _registry_data(registry)
        source_identity = registry.world_identity
        envelope = {
            "schema": CHECKPOINT_SCHEMA,
            "version": CHECKPOINT_VERSION,
            "registry_contract": REGISTRY_CONTRACT,
            "source_world_identity": source_identity,
            "payload": payload,
        }
        envelope["sha256"] = hashlib.sha256(_canonical(envelope).encode("ascii")).hexdigest()
        encoded = json.dumps(envelope, sort_keys=True, ensure_ascii=True, indent=2, allow_nan=False) + "\n"
        _parse_checkpoint(encoded)
        return encoded


def _parse_checkpoint(text) -> DetachedReproductionCheckpoint:
    if type(text) is not str:
        _fail("checkpoint input must be text")
    try:
        envelope = json.loads(text, object_pairs_hook=_reject_duplicate_keys)
    except ReproductionCheckpointValidationError:
        raise
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise ReproductionCheckpointValidationError(f"checkpoint JSON is invalid: {exc}") from exc
    keys = {"schema", "version", "registry_contract", "source_world_identity", "payload", "sha256"}
    envelope = _strict_object(envelope, keys, "checkpoint envelope")
    if (type(envelope["schema"]) is not str or envelope["schema"] != CHECKPOINT_SCHEMA
            or type(envelope["version"]) is not int):
        _fail("unsupported checkpoint schema or version")
    version = envelope["version"]
    expected_contract = (LEGACY_REGISTRY_CONTRACT if version == LEGACY_CHECKPOINT_VERSION
                         else PREVIOUS_REGISTRY_CONTRACT if version == PREVIOUS_CHECKPOINT_VERSION
                         else REGISTRY_CONTRACT if version == CHECKPOINT_VERSION else None)
    if type(envelope["registry_contract"]) is not str or envelope["registry_contract"] != expected_contract:
        _fail("unsupported reproduction registry contract")
    source_identity = _int(envelope["source_world_identity"], "source world identity", 1)
    if type(envelope["sha256"]) is not str or len(envelope["sha256"]) != 64:
        _fail("checkpoint digest is malformed")
    unsigned = {key: envelope[key] for key in keys if key != "sha256"}
    expected_digest = hashlib.sha256(_canonical(unsigned).encode("ascii")).hexdigest()
    if envelope["sha256"] != expected_digest:
        _fail("checkpoint digest mismatch; file may be corrupted")

    payload = _strict_object(envelope["payload"], {"revision", "groups", "indexes", "authored_requests",
        "generation_requests", "progressive_histories", "progressive_requests"}, "checkpoint payload")
    revision = _int(payload["revision"], "registry revision", 0)
    groups = tuple(_group_from_data(item, version=version)
                   for item in _array(payload["groups"], "group records"))
    index_keys = {
        "group_id_by_parent_set", "group_id_by_offspring", "parent_set_by_offspring",
        "person_id_reservations", "group_id_reservations", "offspring_origin_ticks",
        "generation_parent_set_scopes", "progressive_parent_set_scopes",
    }
    if version >= 3:
        index_keys.add("group_id_aliases")
    indexes = _strict_object(payload["indexes"], index_keys, "registry indexes")
    parent_group = _pairs(indexes["group_id_by_parent_set"], "parent index",
                          lambda value, label: _tuple_strings(value, label, True), _str)
    child_group = _pairs(indexes["group_id_by_offspring"], "offspring index", _str, _str)
    child_parents = tuple((row[0], tuple(row[1])) for row in _pairs(
        indexes["parent_set_by_offspring"], "offspring parent index", _str,
        lambda value, label: _tuple_strings(value, label, True)))
    person_reservations = _tuple_strings(indexes["person_id_reservations"], "person reservations")
    group_reservations = _tuple_strings(indexes["group_id_reservations"], "group reservations")
    group_aliases = (_pairs(indexes["group_id_aliases"], "group aliases", _str, _str)
                     if version >= 3 else ())
    origin_ticks = _pairs(indexes["offspring_origin_ticks"], "origin ticks", _str,
                           lambda value, label: _int(value, label, 0))
    generation_scopes = _pairs(indexes["generation_parent_set_scopes"], "V1 scopes",
                               lambda value, label: _tuple_strings(value, label, True), _str)
    progressive_scopes = _pairs(indexes["progressive_parent_set_scopes"], "V2 scopes",
                                 lambda value, label: _tuple_strings(value, label, True), _str)

    authored = []
    for item in _array(payload["authored_requests"], "authored requests"):
        row = _strict_object(item, {"request_key", "normalized_request", "result"}, "authored request")
        authored.append((_str(row["request_key"], "authored key"),
                         _normalization_from_data(row["normalized_request"]),
                         _authored_result_from_data(row["result"], version=version)))

    generation = []
    for item in _array(payload["generation_requests"], "V1 request records"):
        row = _strict_object(item, {"request_key", "normalized_request", "normalized_inputs", "outcome"}, "V1 request")
        generation.append((_str(row["request_key"], "V1 key"),
                           _normalization_from_data(row["normalized_request"]),
                           _normalization_from_data(row["normalized_inputs"]),
                           _outcome_from_data(row["outcome"])))

    histories = tuple(_progressive_history_from_data(item)
                      for item in _array(payload["progressive_histories"], "V2 histories"))
    progressive = []
    for item in _array(payload["progressive_requests"], "V2 request records"):
        row = _strict_object(item, {"request_key", "normalized_request", "normalized_inputs", "result"}, "V2 request")
        progressive.append((_str(row["request_key"], "V2 key"),
                            _normalization_from_data(row["normalized_request"]),
                            _normalization_from_data(row["normalized_inputs"]),
                            _progressive_result_from_data(row["result"])))

    candidate = DetachedReproductionCheckpoint(
        source_identity, revision, groups, parent_group, child_group, child_parents,
        person_reservations, group_reservations, origin_ticks, tuple(authored), generation_scopes,
        tuple(generation), histories, progressive_scopes, tuple(progressive), version, group_aliases,
    )
    groups_by_id = [row.group_id for row in groups]
    history_keys = [row.parent_ids for row in histories]
    authored_keys = [row[0] for row in authored]
    generation_keys = [row[0] for row in generation]
    progressive_keys = [row[0] for row in progressive]
    for label, values in (("group IDs", groups_by_id), ("V2 history parent sets", history_keys),
                          ("authored request keys", authored_keys), ("V1 request keys", generation_keys),
                          ("V2 request keys", progressive_keys)):
        if len(set(values)) != len(values):
            _fail(f"{label} contain duplicates")
    _validate_detached(candidate)
    return candidate


def decode_reproduction_checkpoint(text) -> DetachedReproductionCheckpoint:
    """Parse and fully validate detached checkpoint state without publication."""
    return _parse_checkpoint(text)


class _ValidationOwner:
    def __init__(self):
        self._schedule_lock = RLock()
        self.object_registry = SimpleNamespace(object_instances={})
        self.event_history = {"0": SimpleNamespace(id="0")}
        self._choice_books = []
        self._reproduction_group_registry = None


def _populate_registry(registry, candidate):
    registry._groups_by_id.update((row.group_id, row) for row in candidate.groups)
    registry._group_id_aliases.update(candidate.group_id_aliases)
    registry._group_id_by_parent_set.update(candidate.group_id_by_parent_set)
    registry._group_id_by_offspring.update(candidate.group_id_by_offspring)
    registry._parent_set_by_offspring.update(candidate.parent_set_by_offspring)
    registry._person_id_reservations.update(candidate.person_id_reservations)
    registry._group_id_reservations.update(candidate.group_id_reservations)
    registry._offspring_origin_ticks.update(candidate.offspring_origin_ticks)
    registry._generation_parent_set_scopes.update(candidate.generation_parent_set_scopes)
    registry._progressive_parent_set_scopes.update(candidate.progressive_parent_set_scopes)
    registry._requests.update((key, _IdempotencyRecord(norm, result)) for key, norm, result in candidate.authored_requests)
    registry._generation_requests.update(
        (key, _GenerationIdempotencyRecord(norm, inputs, outcome))
        for key, norm, inputs, outcome in candidate.generation_requests
    )
    registry._progressive_histories.update((row.parent_ids, row) for row in candidate.progressive_histories)
    registry._progressive_requests.update(
        (key, _ProgressiveIdempotencyRecord(norm, inputs, result))
        for key, norm, inputs, result in candidate.progressive_requests
    )
    registry._revision = candidate.revision


def _validate_detached(candidate):
    owner = _ValidationOwner()
    registry = ReproductionGroupRegistry(owner)
    owner._reproduction_group_registry = registry
    registry.world_identity = candidate.source_world_identity
    _populate_registry(registry, candidate)
    if candidate.revision == 0:
        if any((registry._groups_by_id, registry._group_id_by_parent_set, registry._group_id_by_offspring,
                registry._parent_set_by_offspring, registry._requests, registry._generation_requests,
                registry._generation_parent_set_scopes, registry._progressive_histories,
                registry._progressive_parent_set_scopes, registry._progressive_requests,
                registry._person_id_reservations, registry._group_id_reservations,
                registry._group_id_aliases,
                registry._offspring_origin_ticks)):
            _fail("revision-zero checkpoint contains published records")
        return
    try:
        registry._assert_consistent()
    except (ValueError, RuntimeError, TypeError, KeyError) as exc:
        raise ReproductionCheckpointValidationError(f"registry indexes or records are inconsistent: {exc}") from exc
    keys = set(registry._requests) | set(registry._generation_requests) | set(registry._progressive_requests)
    if (len(keys) != len(registry._requests) + len(registry._generation_requests) + len(registry._progressive_requests)
            or set(registry._generation_parent_set_scopes) & set(registry._progressive_parent_set_scopes)):
        _fail("request keys or exact parent-set scopes conflict")
    person_ids = set(registry._person_id_reservations)
    group_ids = set(registry._group_id_reservations)
    if person_ids & group_ids:
        _fail("Person and ReproductionGroup identity reservations overlap")
    if any(group.revision > candidate.revision for group in registry._groups_by_id.values()):
        _fail("a ReproductionGroup revision is newer than the registry checkpoint")
    generated_v1 = {outcome.parent_ids for outcome in
                    (record.outcome for record in registry._generation_requests.values()) if outcome.count > 0}
    generated_v2 = {parents for parents, history in registry._progressive_histories.items() if history.group_id}
    # A retired authored group can have a completion receipt for the same
    # exact set as the statistical/progressive group it was merged into.
    # That alias is the V3 merge fact, not a competing reproduction scope.
    authored_sets = {result.parent_ids for result in
                     (record.result for record in registry._requests.values())
                     if result.parents_complete and result.group_id not in registry._group_id_aliases}
    if (authored_sets & (set(registry._generation_parent_set_scopes) | set(registry._progressive_parent_set_scopes))
            or generated_v1 & generated_v2):
        _fail("authored, V1 and V2 parent-set scopes overlap incompatibly")
    group_origins = {}
    authored_by_group = {}
    for key, record in registry._requests.items():
        normalized, result = record.normalized_request, record.result
        if result.world_identity != candidate.source_world_identity or result.request_key != key:
            _fail("authored request result owner or key is inconsistent")
        if type(normalized) is not tuple or not normalized:
            _fail("authored idempotency normalization is malformed")
        if len(normalized) == 8 and normalized[0] == "elaborate-membership":
            if candidate.wire_version < 2 or len(normalized) != 8:
                _fail("membership-elaboration history requires reproduction checkpoint V2 or later")
            (_operation, group_id, prior, added, resulting, offspring, source, complete) = normalized
            if (type(group_id) is not str or type(prior) is not tuple or not prior
                    or type(added) is not tuple or type(resulting) is not tuple
                    or type(offspring) is not tuple or type(source) is not str
                    or type(complete) is not bool
                    or prior != tuple(sorted(set(prior)))
                    or added != tuple(sorted(set(added)))
                    or set(prior) & set(added)
                    or resulting != tuple(sorted((*prior, *added)))
                    or resulting != result.parent_ids or offspring != result.offspring_ids
                    or group_id != result.group_id or source != result.source_reference
                    or complete is not result.parents_complete):
                _fail("membership-elaboration request and result disagree")
            authored_by_group.setdefault(group_id, []).append((result.revision, normalized, result))
        else:
            expected = (result.group_id, result.parent_ids, result.offspring_ids, result.source_reference)
            if not result.parents_complete:
                expected += (False,)
            if normalized != expected:
                _fail("authored idempotency request data is inconsistent")
            authored_by_group.setdefault(result.group_id, []).append((result.revision, normalized, result))

    # Validate authored membership evolution and reconstruct each canonical
    # survivor's deterministic offspring union from the immutable request
    # receipts. Retired IDs remain aliases, never live group records.
    for group_id, history in authored_by_group.items():
        history.sort(key=lambda item: item[0])
        creators = [item for item in history
                    if not (len(item[1]) == 8 and item[1][0] == "elaborate-membership")]
        if len(creators) != 1:
            _fail("each authored ReproductionGroup must have exactly one creation request")
        creation_revision, creation_norm, creation_result = creators[0]
        if len(creation_norm) not in (4, 5):
            _fail("authored group-creation request has unsupported normalized data")
        current_parents = creation_result.parent_ids
        current_complete = creation_result.parents_complete
        latest_revision = creation_revision
        for revision, normalized, result in history:
            if revision < creation_revision:
                _fail("membership request predates its ReproductionGroup")
            if len(normalized) != 8 or normalized[0] != "elaborate-membership":
                continue
            if revision <= latest_revision or current_complete:
                _fail("membership request order or completion history is inconsistent")
            if normalized[2] != current_parents:
                _fail("membership request does not extend the preceding known parent members")
            current_parents = normalized[4]
            current_complete = normalized[7]
            latest_revision = revision
        canonical_id = registry._canonical_group_id_unlocked(group_id)
        group = registry._groups_by_id.get(canonical_id)
        if group is None:
            _fail("authored request history does not resolve to a live ReproductionGroup")
        if group_id in registry._group_id_aliases:
            if (not current_complete or not group.parents_complete
                    or current_parents != group.parent_ids
                    or not set(creation_result.offspring_ids).issubset(group.offspring_ids)
                    or latest_revision > group.revision):
                _fail("retired group history does not match its canonical survivor")
            continue
        incoming = []
        for retired_id, survivor_id in registry._group_id_aliases.items():
            if survivor_id != group_id:
                continue
            retired_history = authored_by_group.get(retired_id, ())
            retired_completion = [row for row in retired_history
                                  if len(row[1]) == 8 and row[1][0] == "elaborate-membership"
                                  and row[2].parents_complete]
            if not retired_completion:
                _fail("group alias has no completed membership receipt")
            receipt = max(retired_completion, key=lambda row: row[0])
            retired_creator = next((row[2] for row in retired_history
                                    if not (len(row[1]) == 8 and row[1][0] == "elaborate-membership")), None)
            if retired_creator is None:
                _fail("group alias has no authored source history")
            incoming.append((receipt[0], retired_id, retired_creator.offspring_ids))
        expected_children = list(creation_result.offspring_ids)
        for _revision, _retired, children in sorted(incoming):
            for child in children:
                if child in expected_children:
                    _fail("merge history duplicates an offspring identity")
                expected_children.append(child)
        expected_revision = max([latest_revision, *(row[0] for row in incoming)])
        if (group.parent_ids != current_parents or group.parents_complete is not current_complete
                or group.offspring_ids != tuple(expected_children)
                or group.source_reference != creation_result.source_reference
                or group.revision != expected_revision):
            _fail("current ReproductionGroup state does not match its authored/merge history")
        group_origins[group_id] = expected_revision
    for key, record in registry._generation_requests.items():
        outcome = record.outcome
        if outcome.world_identity != candidate.source_world_identity or outcome.request_key != key:
            _fail("V1 outcome owner or request key is inconsistent")
        expected_norm = (outcome.parent_ids, outcome.horizon_tick, outcome.eligible_origin_ticks,
                         outcome.seed, outcome.distribution_id, outcome.distribution_version,
                         outcome.distribution_schema, outcome.weighted_counts, outcome.algorithm,
                         outcome.scope_digest, outcome.world_identity, outcome.count, outcome.group_id,
                         outcome.offspring_ids, outcome.origin_ticks, outcome.source_reference)
        if record.normalized_request != expected_norm:
            _fail("V1 idempotency candidate data is inconsistent")
        request = StatisticalReproductionRequest(
            outcome.parent_ids, outcome.seed, outcome.horizon_tick, outcome.eligible_origin_ticks,
            TestOnlyOffspringCountDistribution(outcome.distribution_id,
                outcome.distribution_version, outcome.weighted_counts),
        )
        if record.normalized_inputs != _normalized_request(request):
            _fail("V1 idempotency inputs are inconsistent")
        if outcome.group_id is not None:
            canonical_id = registry._canonical_group_id_unlocked(outcome.group_id)
            generated_group = registry._groups_by_id.get(canonical_id)
            if (generated_group is None or not generated_group.parents_complete
                    or generated_group.parent_ids != outcome.parent_ids
                    or generated_group.offspring_ids[:len(outcome.offspring_ids)] != outcome.offspring_ids):
                _fail("V1 generated groups must have complete parent membership")
            group_origins[canonical_id] = max(group_origins.get(canonical_id, 0), outcome.revision)
    history_by_parent = registry._progressive_histories
    intervals = {}
    for key, record in registry._progressive_requests.items():
        result = record.result
        history = history_by_parent.get(result.parent_ids)
        if result.world_identity != candidate.source_world_identity or result.request_key != key or history is None:
            _fail("V2 idempotency result owner, key, or history reference is inconsistent")
        request = ProgressiveReproductionRequest(
            result.parent_ids, history.world_seed, result.through_period,
            TestOnlyIntervalReproductionProfile(history.profile_id, history.profile_version,
                                                history.weighted_counts_per_period),
        )
        if record.normalized_inputs != _progressive_inputs(request) + (result.through_period,):
            _fail("V2 idempotency inputs are inconsistent")
        prefix = result.from_period - 1
        expected_norm = (
            candidate.source_world_identity, result.parent_ids, history.world_seed,
            history.profile_id, history.profile_version, history.profile_schema,
            history.weighted_counts_per_period, history.algorithm, history.scope_digest,
            f"RG-PROG-{history.scope_digest[:24]}", prefix,
            _progressive_prefix_digest(history, prefix), result.through_period,
            history.periods[result.from_period:result.through_period + 1],
            f"{INTERVAL_PROFILE_SCHEMA}:{history.profile_id}@{history.profile_version}:{history.scope_digest}",
        )
        if record.normalized_request != expected_norm:
            _fail("V2 idempotency candidate data is inconsistent")
        intervals.setdefault(result.parent_ids, []).append((result.from_period, result.through_period, result.revision))
    for parents, history in history_by_parent.items():
        ordered = sorted(intervals.get(parents, ()), key=lambda row: row[2])
        expected_start = 0
        for start, end, _revision in ordered:
            if start != expected_start or end < start:
                _fail("V2 request periods overlap or leave a gap")
            expected_start = end + 1
        if expected_start != history.through_period + 1:
            _fail("V2 request records do not cover the stored period history")
        if not ordered or ordered[-1][2] != history.revision:
            _fail("V2 history revision is not bound to its final published extension")
        if history.group_id is not None:
            canonical_id = registry._canonical_group_id_unlocked(history.group_id)
            generated_group = registry._groups_by_id.get(canonical_id)
            generated_children = tuple(child for period in history.periods for child in period.offspring_ids)
            if (generated_group is None or not generated_group.parents_complete
                    or generated_group.parent_ids != parents
                    or generated_group.offspring_ids[:len(generated_children)] != generated_children):
                _fail("V2 generated groups must have complete parent membership")
            group_origins[canonical_id] = max(group_origins.get(canonical_id, 0), history.revision)
    for survivor_id in set(registry._group_id_aliases.values()):
        survivor = registry._groups_by_id[survivor_id]
        origin_rows = []
        authored_creator = next((row[2] for row in authored_by_group.get(survivor_id, ())
                                 if not (len(row[1]) == 8 and row[1][0] == "elaborate-membership")), None)
        if authored_creator is not None:
            origin_rows.append((authored_creator.revision, authored_creator.offspring_ids))
        origin_rows.extend((record.outcome.revision, record.outcome.offspring_ids)
                           for record in registry._generation_requests.values()
                           if record.outcome.count and record.outcome.group_id == survivor_id)
        origin_rows.extend((history.revision,
                            tuple(child for period in history.periods for child in period.offspring_ids))
                           for history in registry._progressive_histories.values()
                           if history.group_id == survivor_id)
        if len(origin_rows) != 1:
            _fail("merge survivor has an ambiguous authored/statistical origin")
        expected_children = list(origin_rows[0][1])
        expected_revision = origin_rows[0][0]
        expected_revision = max(
            (expected_revision, *(row[0] for row in authored_by_group.get(survivor_id, ())))
        )
        for retired_id, canonical_id in registry._group_id_aliases.items():
            if canonical_id != survivor_id:
                continue
            retired_history = authored_by_group.get(retired_id, ())
            creators = [row[2] for row in retired_history
                        if not (len(row[1]) == 8 and row[1][0] == "elaborate-membership")]
            completions = [row for row in retired_history
                           if len(row[1]) == 8 and row[1][0] == "elaborate-membership"
                           and row[2].parents_complete]
            if len(creators) != 1 or not completions:
                _fail("retired group lacks creation or completion request history")
            completion = max(completions, key=lambda row: row[0])
            expected_revision = max(expected_revision, completion[0])
            for child in creators[0].offspring_ids:
                if child in expected_children:
                    _fail("merge history duplicates an offspring identity")
                expected_children.append(child)
        if survivor.offspring_ids != tuple(expected_children):
            _fail("canonical offspring union disagrees with persisted merge references")
        group_origins[survivor_id] = expected_revision
    if (set(group_origins) != set(registry._groups_by_id)
            or any(registry._groups_by_id[group_id].revision != revision
                   for group_id, revision in group_origins.items())):
        _fail("ReproductionGroup records lack one consistent authored/statistical history source")
    # The only ancestry invariant needed by this slice is acyclicity of known
    # parentage; no age, maturity, or calendar constraints are inferred.
    ancestry = registry._parent_set_by_offspring
    for child in ancestry:
        pending, seen = list(ancestry[child]), set()
        while pending:
            person = pending.pop()
            if person == child:
                _fail("checkpoint contains cyclic parentage")
            if person in seen:
                continue
            seen.add(person)
            pending.extend(ancestry.get(person, ()))


def _rebind(candidate, world_identity):
    groups = tuple(replace(row, world_identity=world_identity) for row in candidate.groups)
    authored = tuple((key, normalized, replace(result, world_identity=world_identity))
                     for key, normalized, result in candidate.authored_requests)
    generation = []
    for key, normalized, inputs, outcome in candidate.generation_requests:
        normalized = list(normalized)
        normalized[10] = world_identity
        generation.append((key, tuple(normalized), inputs, replace(outcome, world_identity=world_identity)))
    histories = tuple(replace(row, world_identity=world_identity) for row in candidate.progressive_histories)
    progressive = []
    for key, normalized, inputs, result in candidate.progressive_requests:
        normalized = list(normalized)
        normalized[0] = world_identity
        progressive.append((key, tuple(normalized), inputs, replace(result, world_identity=world_identity)))
    return replace(candidate, source_world_identity=world_identity, groups=groups, authored_requests=authored,
                   generation_requests=tuple(generation), progressive_histories=histories,
                   progressive_requests=tuple(progressive))


def restore_reproduction_checkpoint(world, checkpoint, *, _fail_after=None):
    """Validate detached data, then atomically restore into a fresh Universe."""
    candidate = decode_reproduction_checkpoint(checkpoint) if type(checkpoint) is str else checkpoint
    if type(candidate) is not DetachedReproductionCheckpoint:
        raise ReproductionCheckpointValidationError("restore requires decoded reproduction checkpoint data")
    if _fail_after is not None and _fail_after not in RESTORE_FAILURE_PHASES:
        raise ReproductionCheckpointRestoreError("unknown restore fault phase")
    with world._schedule_lock:
        registry = _compatible_context(world, require_empty=True)
        rebound = _rebind(candidate, registry.world_identity)
        _validate_detached(rebound)
        scratch_owner = _ValidationOwner()
        scratch = ReproductionGroupRegistry(scratch_owner)
        scratch_owner._reproduction_group_registry = scratch
        scratch.world_identity = registry.world_identity
        _populate_registry(scratch, rebound)
        undo = registry._capture_undo()
        try:
            registry._groups_by_id.update(scratch._groups_by_id)
            registry._group_id_reservations.update(scratch._group_id_reservations)
            registry._maybe_fail(_fail_after, "groups")
            registry._group_id_by_parent_set.update(scratch._group_id_by_parent_set)
            registry._group_id_by_offspring.update(scratch._group_id_by_offspring)
            registry._parent_set_by_offspring.update(scratch._parent_set_by_offspring)
            registry._person_id_reservations.update(scratch._person_id_reservations)
            registry._offspring_origin_ticks.update(scratch._offspring_origin_ticks)
            registry._maybe_fail(_fail_after, "indexes")
            registry._group_id_aliases.update(scratch._group_id_aliases)
            registry._maybe_fail(_fail_after, "aliases")
            registry._requests.update(scratch._requests)
            registry._maybe_fail(_fail_after, "authored_requests")
            registry._generation_requests.update(scratch._generation_requests)
            registry._generation_parent_set_scopes.update(scratch._generation_parent_set_scopes)
            registry._maybe_fail(_fail_after, "v1_records")
            registry._progressive_histories.update(scratch._progressive_histories)
            registry._progressive_parent_set_scopes.update(scratch._progressive_parent_set_scopes)
            registry._progressive_requests.update(scratch._progressive_requests)
            registry._maybe_fail(_fail_after, "v2_records")
            registry._revision = scratch._revision
            registry._maybe_fail(_fail_after, "revision")
            if registry._revision:
                registry._assert_consistent()
            registry._maybe_fail(_fail_after, "consistency")
        except BaseException as exc:
            registry._restore_undo(undo)
            if isinstance(exc, InjectedReproductionCheckpointFailure):
                raise
            raise ReproductionCheckpointRestoreError(f"checkpoint restoration rolled back: {exc}") from exc
    return world.reproduction_group_snapshot()


def logical_reproduction_checkpoint_digest(checkpoint_text: str) -> str:
    """Hash logical domain contents while excluding process-local owner bindings.

    This comparison helper is for same-seed test demonstrations. It is not an
    authenticity check and does not make a checkpoint a trusted artifact.
    """
    _parse_checkpoint(checkpoint_text)
    envelope = json.loads(checkpoint_text, object_pairs_hook=_reject_duplicate_keys)
    envelope.pop("sha256")
    envelope["source_world_identity"] = 0

    def clear_owner_bindings(value):
        if type(value) is list:
            return [clear_owner_bindings(item) for item in value]
        if type(value) is not dict:
            return value
        output = {}
        for key, item in value.items():
            if key == "world_identity":
                output[key] = 0
            elif key == "normalized_request" and type(item) is list:
                normalized = list(item)
                if normalized and type(normalized[0]) is int:
                    normalized[0] = 0  # V2 candidate starts with its process owner.
                elif len(normalized) > 10 and type(normalized[10]) is int:
                    normalized[10] = 0  # V1 candidate stores owner at field 10.
                output[key] = clear_owner_bindings(normalized)
            else:
                output[key] = clear_owner_bindings(item)
        return output

    logical = clear_owner_bindings(envelope)
    return hashlib.sha256(_canonical(logical).encode("ascii")).hexdigest()


def _maybe_fail(fail_after, phase):
    if fail_after == phase:
        raise InjectedReproductionCheckpointFailure(f"injected restore failure after {phase}")
