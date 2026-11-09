"""Closed portable representation for revision-65 Arena perception evidence.

This adapter captures observer-owned facts only. It does not perform an
observation, draw RNG, advance time, or authorize restoration of an Encounter.
"""
from __future__ import annotations

import math

from arena_perception import (
    BASIS, ENVIRONMENT, ArenaPerceptionEvidence, ArenaPerceptionLedger,
)


LEDGER_SCHEMA = "universe.arena-perception-ledger/1"
EVIDENCE_SCHEMA = "universe.arena-perception-evidence/1"
POSITION_SCHEMA = "universe.cartesian-position-binary64/1"
MAX_LEDGER_ENTITIES = 3002  # Two Beings plus the adopted 3,000-object Arena ceiling.
MAX_HISTORY_ROWS = 16_384
MAX_TEXT_CHARS = 4096
_LEDGER_FIELDS = frozenset(("_current", "_history", "environment", "observer_id"))
_EVIDENCE_FIELDS = frozenset((
    "basis", "boundary", "category", "entity_id", "name", "observer_id",
    "position", "present_state", "time", "type_key",
))


class ArenaPerceptionCheckpointRejected(ValueError):
    """Arena observer evidence is outside the reviewed versioned subset."""


def _need(value, message):
    if not value:
        raise ArenaPerceptionCheckpointRejected(message)


def _position_data(position):
    if position is None:
        return None
    from spatial.state import CartesianPosition
    _need(type(position) is CartesianPosition, "perception position must be native CartesianPosition")
    coordinates = tuple(position.as_tuple())
    _need(len(coordinates) == 3 and all(type(value) is float and math.isfinite(value)
                                        for value in coordinates),
          "perception position must contain three finite binary64 coordinates")
    return (POSITION_SCHEMA, *(value.hex() for value in coordinates))


def _decode_position(data):
    if data is None:
        return None
    _need(type(data) is tuple and len(data) == 4
          and type(data[0]) is str and data[0] == POSITION_SCHEMA,
          "malformed Arena perception position")
    coordinates = []
    for text in data[1:]:
        _need(type(text) is str, "position coordinate must be canonical hexadecimal text")
        try:
            value = float.fromhex(text)
        except ValueError as exc:
            raise ArenaPerceptionCheckpointRejected("position coordinate is not hexadecimal") from exc
        _need(math.isfinite(value) and value.hex() == text,
              "position coordinate is not canonical finite binary64")
        coordinates.append(value)
    from spatial.state import CartesianPosition
    return CartesianPosition(*coordinates)


def _time_data(value):
    if type(value) is int:
        return ("integer", str(value))
    _need(type(value) is float and math.isfinite(value), "evidence time must be finite int or float")
    return ("binary64", value.hex())


def _decode_time(data):
    _need(type(data) is tuple and len(data) == 2, "malformed Arena evidence time")
    _need(type(data[0]) is str, "unsupported Arena evidence time representation")
    if data[0] == "integer":
        _need(type(data[1]) is str, "integer evidence time must be text")
        try:
            value = int(data[1], 10)
        except ValueError as exc:
            raise ArenaPerceptionCheckpointRejected("evidence time is not integer text") from exc
        _need(str(value) == data[1], "evidence time integer is not canonical")
        return value
    _need(data[0] == "binary64" and type(data[1]) is str,
          "unsupported Arena evidence time representation")
    try:
        value = float.fromhex(data[1])
    except ValueError as exc:
        raise ArenaPerceptionCheckpointRejected("evidence time is not hexadecimal") from exc
    _need(math.isfinite(value) and value.hex() == data[1],
          "evidence time is not canonical finite binary64")
    return value


def _evidence_data(row):
    _need(type(row) is ArenaPerceptionEvidence, "unsupported Arena perception evidence type")
    fields = object.__getattribute__(row, "__dict__")
    _need(type(fields) is dict and set(fields) == _EVIDENCE_FIELDS,
          "Arena perception evidence has unknown or missing fields")
    _need(all(type(fields[key]) is str and fields[key] for key in
              ("observer_id", "entity_id", "category", "name", "type_key",
               "present_state", "basis")),
          "Arena perception identity and label fields must be nonempty text")
    _need(all(len(fields[key]) <= MAX_TEXT_CHARS for key in
              ("observer_id", "entity_id", "category", "name", "type_key",
               "present_state", "basis")),
          "Arena perception identity or label exceeds the bounded text size")
    _need(fields["category"] in ("being", "object"), "unsupported evidence category")
    _need(fields["basis"] == BASIS, "unsupported Arena perception evidence basis")
    _need(type(fields["boundary"]) is int and fields["boundary"] >= 0,
          "evidence boundary must be a nonnegative integer")
    _need(type(fields["time"]) in (int, float) and math.isfinite(fields["time"])
          and fields["time"] >= 0, "evidence time must be finite and nonnegative")
    state = fields["present_state"]
    _need(state in ("present", "ground", "carried", "unplaced"),
          "unsupported Arena evidence state")
    position = _position_data(fields["position"])
    _need(state != "ground" or position is not None,
          "ground Object evidence requires a position")
    _need(state != "carried" or position is None,
          "carried Object evidence cannot expose a ground position")
    _need(fields["category"] != "being" or state == "present",
          "Being evidence must use the present state")
    _need(fields["category"] != "object" or state != "present",
          "Object evidence cannot use the Being present state")
    return (EVIDENCE_SCHEMA, fields["observer_id"], fields["entity_id"],
            fields["category"], fields["name"], fields["type_key"], position,
            state, fields["boundary"], _time_data(fields["time"]), fields["basis"])


def _evidence_from_data(data):
    _need(type(data) is tuple and len(data) == 11
          and type(data[0]) is str and data[0] == EVIDENCE_SCHEMA,
          "malformed Arena perception evidence record")
    _, observer_id, entity_id, category, name, type_key, position, state, boundary, time_data, basis = data
    values = (observer_id, entity_id, category, name, type_key, state, basis)
    _need(all(type(value) is str and value for value in values),
          "Arena evidence identity and label values must be nonempty text")
    _need(all(len(value) <= MAX_TEXT_CHARS for value in values),
          "Arena evidence identity or label exceeds the bounded text size")
    _need(type(boundary) is int and boundary >= 0, "invalid evidence boundary")
    try:
        return ArenaPerceptionEvidence(observer_id, entity_id, category, name, type_key,
            _decode_position(position), state, boundary, _decode_time(time_data), basis)
    except (TypeError, ValueError) as exc:
        raise ArenaPerceptionCheckpointRejected(
            f"malformed Arena perception evidence value: {exc}") from exc


def _registry_category(entity):
    from being import BeingInstance
    from object import ObjectInstance
    from weapon import WeaponInstance
    from armor import ArmorInstance
    if type(entity) is BeingInstance:
        return "being", "Being"
    if type(entity) in (ObjectInstance, WeaponInstance, ArmorInstance):
        return "object", entity.current.obj_type
    raise ArenaPerceptionCheckpointRejected("evidence references an unsupported native Entity type")


def _validate_wire(data, *, observer_id, entity_ids, visible_entity_ids, boundary, time):
    _need(type(data) is tuple and len(data) == 5
          and type(data[0]) is str and data[0] == LEDGER_SCHEMA,
          "unsupported Arena perception ledger schema")
    _, encoded_observer, environment, current, history = data
    _need(type(observer_id) is str and observer_id and type(encoded_observer) is str
          and encoded_observer == observer_id,
          "Arena perception ledger belongs to another observer")
    _need(type(environment) is str and environment == ENVIRONMENT,
          "unsupported Arena perception environment")
    _need(type(entity_ids) is tuple and all(type(key) is str and key for key in entity_ids)
          and len(entity_ids) <= MAX_LEDGER_ENTITIES
          and all(len(key) <= MAX_TEXT_CHARS for key in entity_ids)
          and len(set(entity_ids)) == len(entity_ids)
          and entity_ids == tuple(sorted(entity_ids)),
          "invalid durable Entity binding set")
    _need(observer_id in entity_ids, "observer identity is absent from the bound Entity set")
    allowed = set(entity_ids) - {observer_id}
    _need(type(visible_entity_ids) is tuple
          and all(type(key) is str and key for key in visible_entity_ids)
          and len(set(visible_entity_ids)) == len(visible_entity_ids)
          and visible_entity_ids == tuple(sorted(visible_entity_ids))
          and set(visible_entity_ids) <= allowed,
          "invalid observer-owned visible Entity binding set")
    _need(type(current) is tuple and type(history) is tuple,
          "Arena ledger current/history must be immutable ordered tuples")
    _need(len(current) <= MAX_LEDGER_ENTITIES - 1 and len(history) <= MAX_HISTORY_ROWS,
          "Arena perception ledger exceeds its bounded Entity/history size")
    current_by_id = {}
    for entry in current:
        _need(type(entry) is tuple and len(entry) == 2,
              "malformed current Arena evidence entry")
        key, row_data = entry
        _need(type(key) is str and key in allowed,
              "current evidence references an absent or self Entity")
        _need(key not in current_by_id, "duplicate current Arena evidence Entity")
        row = _evidence_from_data(row_data)
        _need(row.entity_id == key and row.observer_id == observer_id,
              "current evidence key or observer identity mismatch")
        current_by_id[key] = row
    _need(tuple(key for key, _ in current) == tuple(sorted(current_by_id)),
          "current Arena evidence is not in canonical Entity order")
    _need(set(current_by_id) == set(visible_entity_ids),
          "current Arena evidence differs from the observer-owned visible Entity set")
    _need(type(boundary) is int and boundary >= 0 and type(time) in (int, float)
          and math.isfinite(time) and time >= 0, "invalid committed Arena evidence boundary")
    for row in current_by_id.values():
        _need(row.boundary == boundary and row.time == time,
              "current Arena evidence is stale relative to the committed boundary")

    last_boundary = -1
    last_time = -1.0
    seen_entity_boundaries = set()
    per_entity = {}
    rows = []
    for row_data in history:
        row = _evidence_from_data(row_data)
        _need(row.observer_id == observer_id and row.entity_id in allowed,
              "history evidence has a foreign observer or dangling Entity")
        _need(row.boundary <= boundary and row.time <= time,
              "history evidence lies beyond the committed boundary")
        _need(row.boundary >= last_boundary and row.time >= last_time,
              "Arena evidence history chronology regressed")
        marker = (row.entity_id, row.boundary)
        _need(marker not in seen_entity_boundaries,
              "duplicate Entity evidence at one committed boundary")
        seen_entity_boundaries.add(marker)
        prior = per_entity.get(row.entity_id)
        _need(prior is None or (row.boundary > prior.boundary and row.time > prior.time),
              "per-Entity Arena evidence history is not strictly chronological")
        per_entity[row.entity_id] = row
        last_boundary, last_time = row.boundary, row.time
        rows.append(row)
    _need(set(per_entity) == set(visible_entity_ids),
          "Arena evidence history differs from the observer-owned visible Entity set")
    return current_by_id, tuple(rows)


def encode_detached_arena_perception_ledger(ledger, *, observer_id, entity_ids,
                                            visible_entity_ids, boundary, time):
    """Encode a reconstructed ledger after checking its explicit stable bindings."""
    _need(type(ledger) is ArenaPerceptionLedger,
          "unsupported detached Arena perception ledger type")
    fields = object.__getattribute__(ledger, "__dict__")
    _need(type(fields) is dict and set(fields) == _LEDGER_FIELDS,
          "Arena perception ledger has unknown or missing fields")
    _need(ledger.observer_id == observer_id and ledger.environment == ENVIRONMENT,
          "detached Arena ledger observer/environment mismatch")
    _need(type(ledger._current) is dict and type(ledger._history) is list,
          "Arena perception ledger storage has unsupported shape")
    _need(len(ledger._current) <= MAX_LEDGER_ENTITIES - 1
          and len(ledger._history) <= MAX_HISTORY_ROWS,
          "Arena perception ledger exceeds its bounded Entity/history size")
    current = tuple((key, _evidence_data(ledger._current[key]))
                    for key in sorted(ledger._current))
    history = tuple(_evidence_data(row) for row in ledger._history)
    result = (LEDGER_SCHEMA, observer_id, ENVIRONMENT, current, history)
    _validate_wire(result, observer_id=observer_id, entity_ids=entity_ids,
        visible_entity_ids=visible_entity_ids, boundary=boundary, time=time)
    return result


def encode_arena_perception_ledger(ledger, *, observer, encounter, registry):
    """Validate live native evidence and return a versioned pointer-free tuple."""
    from being import BeingInstance
    _need(type(observer) is BeingInstance and observer.id in encounter.being_list,
          "Arena ledger owner must be an Encounter Being")
    _need(type(ledger) is ArenaPerceptionLedger,
          "Arena Being has no supported observer-owned perception ledger")
    fields = object.__getattribute__(ledger, "__dict__")
    _need(type(fields) is dict and set(fields) == _LEDGER_FIELDS,
          "Arena perception ledger has unknown or missing fields")
    _need(ledger.observer_id == observer.id, "Arena perception ledger owner mismatch")
    _need(ledger.environment == ENVIRONMENT, "unsupported Arena perception environment")
    _need(type(ledger._current) is dict and type(ledger._history) is list,
          "Arena perception ledger storage has unsupported shape")
    _need(len(ledger._current) <= MAX_LEDGER_ENTITIES - 1
          and len(ledger._history) <= MAX_HISTORY_ROWS,
          "Arena perception ledger exceeds its bounded Entity/history size")
    entity_ids = tuple(sorted(encounter.entity_ids()))
    _need(len(entity_ids) <= MAX_LEDGER_ENTITIES
          and len(entity_ids) == len(set(entity_ids)) and observer.id in entity_ids
          and type(registry) is dict and all(registry.get(key) is encounter.universe.get_object_by_id(key)
                                            for key in entity_ids),
          "Encounter Entity registry is not closed over native Universe identities")
    boundary = encounter.last_processed_boundary
    _need(observer.id in encounter.awareness,
          "Arena observer has no native Awareness binding")
    visible_entity_ids = tuple(sorted(encounter.awareness[observer.id]))
    expected_current = set(visible_entity_ids)
    _need(set(ledger._current) == expected_current,
          "Arena current evidence differs from native observer Awareness")

    for entity_id in sorted(expected_current):
        row = ledger._current[entity_id]
        _evidence_data(row)
        entity = registry[entity_id]
        category, type_key = _registry_category(entity)
        _need((row.observer_id, row.entity_id, row.category, row.type_key)
              == (observer.id, entity_id, category, type_key),
              "current Arena evidence disagrees with its bound Entity identity/type")
        expected_name = entity.name or type_key
        parent = entity.parent_container_id
        position = entity.get_position()
        expected_state = ("present" if category == "being" else
                          "carried" if parent is not None else
                          "ground" if position is not None else "unplaced")
        expected_position = None if expected_state == "carried" else position
        _need(row.name == expected_name and row.present_state == expected_state
              and row.position == expected_position,
              "current Arena evidence disagrees with committed Entity name, custody, or position")
    for row in ledger._history:
        _evidence_data(row)
        entity = registry.get(row.entity_id)
        _need(entity is not None, "Arena history evidence references a dangling Entity")
        category, type_key = _registry_category(entity)
        _need((row.observer_id, row.category, row.type_key)
              == (observer.id, category, type_key),
              "Arena history evidence disagrees with its durable observer/Entity binding")
    return encode_detached_arena_perception_ledger(ledger,
        observer_id=observer.id, entity_ids=entity_ids,
        visible_entity_ids=visible_entity_ids, boundary=boundary,
        time=encounter.time)


def decode_arena_perception_ledger(data, *, observer_id, entity_ids,
                                   visible_entity_ids, boundary, time):
    """Rebuild a detached native ledger using explicit stable Entity bindings."""
    current, history = _validate_wire(data, observer_id=observer_id,
        entity_ids=entity_ids, visible_entity_ids=visible_entity_ids,
        boundary=boundary, time=time)
    ledger = ArenaPerceptionLedger(observer_id)
    ledger._current = dict(current)
    ledger._history = list(history)
    return ledger
