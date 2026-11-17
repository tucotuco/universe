"""Arena-session-independent, fact-only native Encounter history records.

The history wire stores an initial committed-boundary projection, atomic
state changes, sparse EntityInspection and Arena observer-knowledge context
changes, and native Action/Effect/observation/receipt facts for each commit.
``NativeHistoryQuery``
provides validated repeated historical reads without re-expanding quiet spans
or evaluating Actions. This module does not yet replace production Save/Load.
"""
from __future__ import annotations

from dataclasses import fields, is_dataclass, replace
from bisect import bisect_right
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
from threading import RLock
from types import MappingProxyType
from weakref import WeakKeyDictionary, ref as weakref

from checkpoint_fields import FIELD_ADAPTERS


LEGACY_SCHEMA = "universe.native-encounter-history/1"
PREVIOUS_SCHEMA = "universe.native-encounter-history/2"
QUIET_SPAN_SCHEMA = "universe.native-encounter-history/3"
ENTITY_CONTEXT_SCHEMA = "universe.native-encounter-history/4"
FATIGUE_CONTEXT_SCHEMA = "universe.native-encounter-history/5"
INITIAL_RNG_SCHEMA = "universe.native-encounter-history/6"
RECEIPT_FACT_SCHEMA = "universe.native-encounter-history/7"
OBSERVER_KNOWLEDGE_SCHEMA = "universe.native-encounter-history/8"
RECIPIENT_HISTORY_SCHEMA = "universe.native-encounter-history/9"
PUBLICATION_FACT_SCHEMA = "universe.native-encounter-history/10"
SCHEMA = "universe.native-encounter-history/11"
LEGACY_SCHEMAS = (LEGACY_SCHEMA, PREVIOUS_SCHEMA, QUIET_SPAN_SCHEMA,
                  ENTITY_CONTEXT_SCHEMA, FATIGUE_CONTEXT_SCHEMA,
                  INITIAL_RNG_SCHEMA, RECEIPT_FACT_SCHEMA,
                  OBSERVER_KNOWLEDGE_SCHEMA, RECIPIENT_HISTORY_SCHEMA,
                  PUBLICATION_FACT_SCHEMA)
RNG_HISTORY_SCHEMAS = (INITIAL_RNG_SCHEMA, RECEIPT_FACT_SCHEMA,
                       OBSERVER_KNOWLEDGE_SCHEMA, RECIPIENT_HISTORY_SCHEMA,
                       PUBLICATION_FACT_SCHEMA, SCHEMA)
RECEIPT_FACT_SCHEMAS = (RECEIPT_FACT_SCHEMA, OBSERVER_KNOWLEDGE_SCHEMA,
                        RECIPIENT_HISTORY_SCHEMA, PUBLICATION_FACT_SCHEMA, SCHEMA)
OBSERVER_KNOWLEDGE_SCHEMAS = (OBSERVER_KNOWLEDGE_SCHEMA,
                              RECIPIENT_HISTORY_SCHEMA, PUBLICATION_FACT_SCHEMA,
                              SCHEMA)
INITIAL_SCHEDULE_SCHEMAS = (RECIPIENT_HISTORY_SCHEMA,
                            PUBLICATION_FACT_SCHEMA, SCHEMA)
ENTITY_CONTEXT_SCHEMAS = (ENTITY_CONTEXT_SCHEMA, FATIGUE_CONTEXT_SCHEMA, INITIAL_RNG_SCHEMA,
                          RECEIPT_FACT_SCHEMA, OBSERVER_KNOWLEDGE_SCHEMA,
                          RECIPIENT_HISTORY_SCHEMA, PUBLICATION_FACT_SCHEMA,
                          SCHEMA)
CURRENT_ENTITY_CONTEXT_SCHEMAS = tuple(
    value for value in ENTITY_CONTEXT_SCHEMAS
    if value != ENTITY_CONTEXT_SCHEMA)
SAME_RNG = {"$same_as_previous": True}
_EMPTY_EVENTS = {"action_ids": [], "effect_ids": [], "actions": {},
                 "effects": {}, "starts": [], "participants": []}
MAX_BYTES = 64 * 1024 * 1024
MAX_NODES = 10_000_000
MAX_BOUNDARIES = 10_000_000
MAX_DEPTH = 128


class NativeHistoryRejected(ValueError):
    """Native history is malformed, unsupported, or inconsistent."""


_RECORDERS = WeakKeyDictionary()
_INITIAL_SCHEDULES = WeakKeyDictionary()
_INITIAL_ENTITIES = WeakKeyDictionary()
_RECORDER_LOCK = RLock()


def _canonical(value):
    try:
        return json.dumps(value, sort_keys=True, ensure_ascii=True,
                          separators=(",", ":"), allow_nan=False).encode("ascii")
    except (TypeError, ValueError, RecursionError, UnicodeError) as exc:
        raise NativeHistoryRejected("native history is not canonical finite JSON data") from exc


def _number_value(value):
    if type(value) in (int, float) and type(value) is not bool:
        return value
    if (type(value) is dict and set(value) == {"$number"}
            and type(value["$number"]) is str):
        try:
            result = float.fromhex(value["$number"])
        except ValueError as exc:
            raise NativeHistoryRejected("native history timeline number is malformed") from exc
        if math.isfinite(result) and result.hex() == value["$number"]:
            return result
    raise NativeHistoryRejected("native history timeline number is malformed")


def _native_types():
    import importlib
    result = {}
    for tag in FIELD_ADAPTERS:
        module, name = tag.rsplit(".", 1)
        cls = getattr(importlib.import_module(module), name)
        if not isinstance(cls, type) or cls.__module__ != module or cls.__name__ != name:
            raise NativeHistoryRejected("native history type registry changed")
        result[tag] = cls
    return result


def _plain(value, depth=0, active=None):
    """Encode closed native inspection data without addresses or callbacks."""
    if depth > MAX_DEPTH:
        raise NativeHistoryRejected("native history nesting limit exceeded")
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise NativeHistoryRejected("native history contains a non-finite number")
        return {"$number": value.hex()}
    active = set() if active is None else active
    if type(value) in (dict, MappingProxyType):
        identity = id(value)
        if identity in active:
            raise NativeHistoryRejected("cyclic native history mapping")
        active.add(identity)
        try:
            if all(type(key) is str for key in value):
                return {key: _plain(item, depth + 1, active)
                        for key, item in sorted(value.items())}
            rows = [[_plain(key, depth + 1, active), _plain(item, depth + 1, active)]
                    for key, item in value.items()]
            rows.sort(key=lambda row: _canonical(row[0]))
            return {"$map": rows}
        finally:
            active.remove(identity)
    if type(value) in (tuple, list):
        identity = id(value)
        if identity in active:
            raise NativeHistoryRejected("cyclic native history sequence")
        active.add(identity)
        try:
            return {"$tuple" if type(value) is tuple else "$list":
                    [_plain(item, depth + 1, active) for item in value]}
        finally:
            active.remove(identity)
    if type(value) in (set, frozenset):
        rows = [_plain(item, depth + 1, active) for item in value]
        rows.sort(key=_canonical)
        return {"$frozenset" if type(value) is frozenset else "$set": rows}
    if is_dataclass(value) and not isinstance(value, type):
        tag = type(value).__module__ + "." + type(value).__name__
        adapter = FIELD_ADAPTERS.get(tag)
        if adapter is None:
            # Inspection-only projections are closed frozen records too; the
            # allowlist is populated by the native inspector's data classes.
            from encounter_inspection import (
                ActionInspection, BoundaryInspection, DisarmLandingReceipt,
                EncounterInspection, EntityInspection, ObjectiveFactInspection,
                ObjectiveInspection, TargetInspection,
            )
            inspection_types = {cls.__module__ + "." + cls.__name__: cls for cls in (
                ActionInspection, BoundaryInspection, DisarmLandingReceipt,
                EncounterInspection, EntityInspection, ObjectiveFactInspection,
                ObjectiveInspection, TargetInspection,
            )}
            if inspection_types.get(tag) is not type(value):
                raise NativeHistoryRejected("unreviewed native history record type")
            allowed = {field.name for field in fields(type(value))}
            required = allowed
        else:
            allowed = set(adapter["allowed"])
            required = set(adapter["required"])
        data = object.__getattribute__(value, "__dict__")
        if (type(data) is not dict or set(data) - allowed
                or required - set(data)):
            raise NativeHistoryRejected("native history record fields differ from the closed schema")
        if tag == "observer_proposals.RecipientIdentity":
            # object_identity is id(handle), not a logical identity. The
            # originating Effect carries the stable observer/recipient ID.
            data = {"role": data["role"]}
        elif tag == "interval_staging.AuthorityReference":
            # Rebuild anchors bind through the stable role/key pair.
            data = {"key": data["key"], "role": data["role"]}
        elif tag == "encounter_inspection.ObjectiveInspection":
            # ledger_identity is id(ledger); the subject ID is its portable
            # owner reference and the live validator is rebound by authority.
            data = {name: value for name, value in data.items()
                    if name != "ledger_identity"}
        elif tag == "objective_reality.SubjectRealityCandidate":
            # The candidate's stable subject ID identifies the owning native
            # Group. ledger_identity is a process address and is rebound on
            # restoration from that owner.
            data = {name: value for name, value in data.items()
                    if name != "ledger_identity"}
        return {"$record": tag,
                "fields": {name: _plain(data[name], depth + 1, active)
                           for name in sorted(data)}}
    raise NativeHistoryRejected("native history contains an unsupported value")


def _measure(value):
    count = 0
    stack = [(value, 0)]
    while stack:
        item, depth = stack.pop()
        count += 1
        if count > MAX_NODES or depth > MAX_DEPTH:
            raise NativeHistoryRejected("native history exceeds structural bounds")
        if type(item) is dict:
            stack.extend((child, depth + 1) for child in item.values())
        elif type(item) is list:
            stack.extend((child, depth + 1) for child in item)
        elif item is None or type(item) in (str, bool, int):
            if type(item) is str and len(item) > 1_000_000:
                raise NativeHistoryRejected("native history string exceeds field limit")
        else:
            raise NativeHistoryRejected("native history contains an invalid JSON value")
    return count


def _materialize_plain(value, depth=0):
    """Rehydrate one validated tagged native fact using exact closed types."""
    if depth > MAX_DEPTH:
        raise NativeHistoryRejected("native history fact nesting limit exceeded")
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is list:
        return [_materialize_plain(item, depth + 1) for item in value]
    if type(value) is not dict:
        raise NativeHistoryRejected("native history fact has an unsupported value")
    if "$number" in value:
        if set(value) != {"$number"} or type(value["$number"]) is not str:
            raise NativeHistoryRejected("native history fact number is malformed")
        try:
            number = float.fromhex(value["$number"])
        except ValueError as exc:
            raise NativeHistoryRejected("native history fact number is malformed") from exc
        if not math.isfinite(number) or number.hex() != value["$number"]:
            raise NativeHistoryRejected("native history fact number is noncanonical")
        return number
    if "$tuple" in value or "$list" in value or "$set" in value or "$frozenset" in value:
        if len(value) != 1:
            raise NativeHistoryRejected("native history fact sequence tag is ambiguous")
        tag, rows = next(iter(value.items()))
        if type(rows) is not list:
            raise NativeHistoryRejected("native history fact sequence is malformed")
        materialized = [_materialize_plain(item, depth + 1) for item in rows]
        if tag == "$tuple":
            return tuple(materialized)
        if tag == "$list":
            return materialized
        try:
            result = set(materialized)
        except TypeError as exc:
            raise NativeHistoryRejected("native history fact set is not hashable") from exc
        if len(result) != len(materialized):
            raise NativeHistoryRejected("native history fact set has duplicate members")
        return result if tag == "$set" else frozenset(result)
    if "$map" in value:
        if set(value) != {"$map"} or type(value["$map"]) is not list:
            raise NativeHistoryRejected("native history fact map is malformed")
        result = {}
        for pair in value["$map"]:
            if type(pair) is not list or len(pair) != 2:
                raise NativeHistoryRejected("native history fact map entry is malformed")
            key = _materialize_plain(pair[0], depth + 1)
            item = _materialize_plain(pair[1], depth + 1)
            try:
                if key in result:
                    raise NativeHistoryRejected("native history fact map repeats a key")
                result[key] = item
            except TypeError as exc:
                raise NativeHistoryRejected("native history fact map key is not hashable") from exc
        return result
    if "$record" in value:
        if set(value) != {"$record", "fields"} or type(value["$record"]) is not str:
            raise NativeHistoryRejected("native history fact record tag is malformed")
        tag = value["$record"]
        from encounter_inspection import (
            ActionInspection, BoundaryInspection, DisarmLandingReceipt,
            EncounterInspection, EntityInspection, ObjectiveFactInspection,
            ObjectiveInspection, TargetInspection,
        )
        inspection_types = {cls.__module__ + "." + cls.__name__: cls for cls in (
            ActionInspection, BoundaryInspection, DisarmLandingReceipt,
            EncounterInspection, EntityInspection, ObjectiveFactInspection,
            ObjectiveInspection, TargetInspection,
        )}
        cls = inspection_types.get(tag)
        if cls is None:
            cls = _native_types().get(tag)
        if (cls is None or not is_dataclass(cls)
                or getattr(cls, "__dataclass_params__", None) is None
                or cls.__dataclass_params__.frozen is not True
                or type(value["fields"]) is not dict):
            raise NativeHistoryRejected("native history fact record type is not admitted")
        expected = {field.name for field in fields(cls)}
        encoded_fields = value["fields"]
        if (tag == "observer_proposals.RecipientIdentity"
                and set(encoded_fields) == {"role"}
                and expected == {"role", "object_identity"}):
            # `_plain` deliberately omits id(handle). Historical Target facts
            # retain this type only as a role marker; 0 is a fail-closed
            # process-local sentinel and is never rebound or dereferenced.
            encoded_fields = {**encoded_fields, "object_identity": 0}
        if (tag == "interval_staging.AuthorityReference"
                and set(encoded_fields) == {"key", "role"}
                and expected == {"key", "role", "identity"}):
            # Stable role/key pairs are portable; the identity is rebuilt by
            # the native restore adapter after resolving the registered owner.
            encoded_fields = {**encoded_fields, "identity": 0}
        if (tag == "encounter_inspection.ObjectiveInspection"
                and set(encoded_fields) == expected - {"ledger_identity"}
                and "ledger_identity" in expected):
            # The ledger is rebound from the native subject registry below.
            encoded_fields = {**encoded_fields, "ledger_identity": 0}
        if (tag == "objective_reality.SubjectRealityCandidate"
                and set(encoded_fields) == expected - {"ledger_identity"}
                and "ledger_identity" in expected):
            # This address is rebound from the same stable objective subject.
            encoded_fields = {**encoded_fields, "ledger_identity": 0}
        if set(encoded_fields) != expected:
            raise NativeHistoryRejected("native history fact record fields differ")
        record = object.__new__(cls)
        for name in expected:
            object.__setattr__(record, name,
                               _materialize_plain(encoded_fields[name], depth + 1))
        return record
    if all(type(key) is str for key in value):
        return {key: _materialize_plain(item, depth + 1)
                for key, item in value.items()}
    raise NativeHistoryRejected("native history fact mapping is unsupported")


def _diff(before, after, path=()):
    if type(before) is dict and type(after) is dict:
        output = []
        for key in sorted(set(before) | set(after)):
            if key not in before:
                output.append({"path": list(path + (key,)), "before": False,
                               "after": True, "value": after[key]})
            elif key not in after:
                output.append({"path": list(path + (key,)), "before": True,
                               "before_value": before[key], "after": False})
            else:
                output.extend(_diff(before[key], after[key], path + (key,)))
        return output
    if type(before) is not type(after) or before != after:
        return [{"path": list(path), "before": True, "before_value": before,
                 "after": True, "value": after}]
    return []


def _apply(state, changes):
    result = json.loads(_canonical(state).decode("ascii"))
    seen = set()
    for row in changes:
        if type(row) is not dict or set(row) not in (
                {"path", "before", "after", "value"},
                {"path", "before", "before_value", "after"},
                {"path", "before", "before_value", "after", "value"}):
            raise NativeHistoryRejected("native history change schema is invalid")
        path = row["path"]
        if type(path) is not list or not path or any(type(part) is not str for part in path):
            raise NativeHistoryRejected("native history property path is invalid")
        key = tuple(path)
        if key in seen:
            raise NativeHistoryRejected("native history repeats an atomic property path")
        seen.add(key)
        if type(row["before"]) is not bool or type(row["after"]) is not bool:
            raise NativeHistoryRejected("native history property presence flags are not Boolean")
        parent = result
        for part in path[:-1]:
            if type(parent) is not dict or part not in parent:
                raise NativeHistoryRejected("native history property parent is absent")
            parent = parent[part]
        leaf = path[-1]
        if type(parent) is not dict:
            raise NativeHistoryRejected("native history property owner is not a mapping")
        present = leaf in parent
        if present is not row["before"]:
            raise NativeHistoryRejected("native history property preimage presence differs")
        if present and parent[leaf] != row.get("before_value"):
            raise NativeHistoryRejected("native history property preimage value differs")
        if row["after"]:
            parent[leaf] = row["value"]
        else:
            parent.pop(leaf)
    return result


def _boundary_payload(encounter, receipt, latest_view, targets_by_boundary):
    meta = receipt.inspection
    timeline = next((row for row in latest_view.timeline if row.boundary == receipt.boundary), None)
    if timeline is None:
        raise NativeHistoryRejected("native boundary receipt is missing from inspection timeline")
    actions = {action_id: latest_view.actions[action_id]
               for action_id in timeline.action_ids}
    effects = {effect_id: latest_view.effects[effect_id]
               for effect_id in timeline.effect_ids}
    targets = targets_by_boundary.get(receipt.boundary, {})
    landing_rows = tuple(row for row in encounter.__dict__.get(
        "_disarm_landing_receipts", ()) if row.boundary == receipt.boundary)
    return {
        "boundary": receipt.boundary,
        "start": _plain(meta.start),
        "end": _plain(meta.end),
        "action_ids": list(receipt.action_ids),
        "effect_ids": [_plain(value) for value in receipt.effect_ids],
        "notification_intents": _plain(receipt.notification_intents),
        "disarm_landings": _plain(landing_rows),
        "actions": _plain(actions),
        "effects": _plain(effects),
        "target_states": _plain(targets),
        "entity_context": _plain(meta.entities),
        "objective": _plain(meta.objective),
        "objective_use": _plain(meta.objective_use),
        "recipients": _stable_recipients(meta.recipients),
        "schedule": _plain(meta.schedule),
        "starts": _plain(meta.starts),
        "participants": _plain(meta.participants),
        "projectile_states": _plain(meta.projectile_states),
        "rng_after": _plain(receipt.rng_state),
    }


def initial_entities_from_snapshot(encounter, snapshot):
    """Detach the exact pre-movement Entity projection for boundary zero.

    The first receipt is already post-movement.  Native progression supplies
    its validated pre-action snapshot before applying that movement; this
    adapter captures its represented Entities without running a resolver.
    Time-derived status fields are evaluated at the actual Encounter start.
    """
    from action_evaluation import EvaluationSnapshot, native_data
    from encounter_inspection import EntityInspection
    from being import BeingInstance, BeingDefinition
    from states import States
    if (type(snapshot) is not EvaluationSnapshot
            or snapshot.encounter_id != encounter.id
            or encounter.last_processed_boundary != math.floor(encounter.time)
            or encounter.time != encounter.start_time):
        raise NativeHistoryRejected("initial Entity capture is outside the native start fence")
    objects = encounter.universe.object_registry.object_instances
    result = {}
    for identity, view in snapshot.entities.items():
        if identity not in objects:
            raise NativeHistoryRejected("initial Entity snapshot references an absent Object")
        obj = objects[identity]
        data = dict(view.data)
        if type(obj) is BeingInstance:
            current = native_data(obj.current, (BeingDefinition,))
            state_obj = current.get("states")
            if type(state_obj) is not States:
                raise NativeHistoryRejected("initial Being state adapter is unavailable")
            state_values = dict(native_data(state_obj, (States,))["states"])
            stun_until = state_values.get("stunned_until")
            if type(stun_until) in (int, float):
                from action_evaluation import stun_active_at
                state_values["stunned"] = stun_active_at(stun_until, encounter.time)
            data["states"] = state_values
            burden = state_values.get("subdual_damage", 0)
            anchor = state_values.get("subdual_recovery_anchor")
            if type(burden) is int and type(anchor) in (int, float):
                from action_evaluation import subdual_recovery_state
                burden, _anchor = subdual_recovery_state(burden, anchor,
                                                          encounter.time)
                data["states"]["subdual_damage"] = burden
                data["states"]["subdual_damage_current"] = burden
                data["states"]["subdual_unconscious"] = (
                    burden >= current["hit_points"])
        if identity in snapshot.fatigue:
            data["physical_fatigue"] = snapshot.fatigue[identity]
            data["physiology"] = snapshot.physiology.get(identity, {})
        result[identity] = EntityInspection(
            view.category, view.obj_type, data.get("name"), view.position,
            data)
    return result


def _arena_observer_context(encounter, latest_boundary):
    """Fold committed Arena evidence as observer-owned, sparse facts.

    The ledger's immutable evidence rows carry their publication/visibility
    boundary. Replaying these rows constructs only what each observer had
    recorded; it never infers visibility from the objective Entity graph.
    """
    from arena_perception import ArenaPerceptionEvidence, ArenaPerceptionLedger
    from being import BeingInstance

    ledgers = {}
    objects = encounter.universe.object_registry.object_instances
    for owner_id in encounter.being_list:
        observer = objects.get(owner_id)
        if type(observer) is not BeingInstance:
            continue
        ledger = object.__getattribute__(observer, "__dict__").get(
            "_arena_perception_ledger")
        if ledger is None:
            continue
        if (type(ledger) is not ArenaPerceptionLedger
                or ledger.observer_id != owner_id
                or type(ledger._history) is not list):
            raise NativeHistoryRejected("Arena perception ledger owner or storage differs")
        ledgers[owner_id] = ledger

    initial = {}
    rows_by_boundary = {}
    seen_rows = set()
    for owner_id, ledger in sorted(ledgers.items()):
        for evidence in ledger._history:
            if type(evidence) is not ArenaPerceptionEvidence:
                raise NativeHistoryRejected("Arena observer evidence has an unreviewed type")
            boundary = evidence.visibility_boundary
            if (type(boundary) is not int or not 0 <= boundary <= latest_boundary
                    or evidence.observer_id != owner_id):
                raise NativeHistoryRejected("Arena observer evidence boundary or owner differs")
            identity = (owner_id, evidence.entity_id, boundary)
            if identity in seen_rows:
                raise NativeHistoryRejected(
                    "Arena observer evidence repeats an Entity at one boundary")
            seen_rows.add(identity)
            encoded = _plain(evidence)
            if boundary == 0:
                initial.setdefault(owner_id, {})[evidence.entity_id] = encoded
            else:
                rows_by_boundary.setdefault(boundary, []).append(
                    (owner_id, evidence.entity_id, encoded))

    state = initial
    changes = []
    for boundary in sorted(rows_by_boundary):
        prior = state
        state = json.loads(_canonical(state).decode("ascii"))
        for owner_id, entity_id, encoded in rows_by_boundary[boundary]:
            state.setdefault(owner_id, {})[entity_id] = encoded
        delta = _diff(prior, state)
        if delta:
            changes.append({"boundary": boundary, "changes": delta,
                            "state_sha256": hashlib.sha256(
                                _canonical(state)).hexdigest()})
    return {"available": True, "initial": initial, "changes": changes}


def _target_candidates(encounter):
    """Collect immutable committed native TargetCandidate values by boundary."""
    from action_settlement import TargetCandidate
    from atomic_publication import TargetIntervalRecord

    result = {}
    objects = encounter.universe.object_registry.object_instances
    for entity_id, entity in objects.items():
        storage = object.__getattribute__(entity, "__dict__").get(
            "_atomic_target_history", ())
        for record in storage:
            if (type(record) is not TargetIntervalRecord
                    or record.encounter_id != encounter.id):
                continue
            if (type(record.boundary) is not int or record.boundary < 1
                    or type(record.state) is not TargetCandidate
                    or record.state.target_id != entity_id):
                raise NativeHistoryRejected(
                    "native committed Target identity or boundary is malformed")
            boundary = result.setdefault(record.boundary, {})
            if entity_id in boundary:
                raise NativeHistoryRejected("native Target has duplicate committed boundary")
            boundary[entity_id] = record.state
    return result


def capture_initial_schedule(encounter):
    """Capture the exact scheduler/Choice state before the first commit.

    This closed initial projection is separate from the post-publication queue
    records stored at boundaries. It is captured only while the Encounter is
    quiescent or under the transaction's publication lock.
    """
    from interval_staging import QueueProjection
    from objective_reality import SubjectRealityCandidate
    encounter._pending_schedule()
    book = encounter._choice_book
    world_data = object.__getattribute__(encounter.universe, "__dict__")
    from interval_staging import AuthorityReference, RegistrationIntent, _data_metadata
    registrations = []
    for action_id, (choice_id, packet, _signature) in book._registered.items():
        action = world_data["event_history"].get(action_id)
        if action is None or packet.action_id != action_id:
            raise NativeHistoryRejected(
                "initial scheduler registration references a missing Action")
        initialization = {key: value for key, value in packet.initialization
                          if key != "start_position"}
        initialization.update(end_time=packet.end_time,
                              parent_event_id=encounter.id)
        metadata = _data_metadata({action_id: initialization}, encounter)[action_id]
        registrations.append(RegistrationIntent(
            AuthorityReference("event", action_id, id(action)), choice_id,
            AuthorityReference("accepted_packet", action_id, id(packet)), metadata))
    projection = QueueProjection(
        tuple(encounter.pending_action_list),
        tuple(encounter.finished_action_list),
        tuple(encounter.cancelled_action_list),
        tuple(registrations),
        MappingProxyType(dict(book._states)),
        MappingProxyType({identity: record.view.state
                          for identity, record in book._choices.items()}),
        tuple(book._reservations),
        world_data["_schedule_revision"],
    )
    return _plain(projection)


def _stable_recipients(value):
    if type(value) not in (dict, MappingProxyType):
        raise NativeHistoryRejected("native observer projections are not a mapping")
    rows = []
    for identity, projection in value.items():
        if type(identity).__module__ + "." + type(identity).__name__ != "observer_proposals.RecipientIdentity":
            raise NativeHistoryRejected("native observer identity has an unreviewed type")
        role = object.__getattribute__(identity, "__dict__").get("role")
        data = object.__getattribute__(projection, "__dict__")
        owner = data.get("observer_id")
        if owner is None:
            owner = data.get("listener_id")
        if type(role) is not str or not role or owner is not None and type(owner) is not str:
            raise NativeHistoryRejected("native observer projection has no stable owner")
        if role in ("in_world_belief_ledger", "observer_location_evidence",
                    "observer_object_evidence") and owner is None:
            raise NativeHistoryRejected("observer-owned evidence has no logical owner ID")
        if role == "in_world_received_accounts":
            # One ordinary list can be explicitly shared by multiple listeners.
            # Keep its historical projection owner-filterable by splitting the
            # immutable account/effect facts by their adopted listener identity.
            accounts = data.get("accounts", ())
            listener_ids = data.get("listener_ids", ())
            if type(listener_ids) is not tuple:
                listener_ids = ()
            listener_ids = set(listener_ids)
            listener_ids.update(getattr(account, "listener_id", None)
                                for account in accounts)
            listener_ids.discard(None)
            if listener_ids:
                effects = data.get("delivery_effect_ids", ())
                for listener_id in sorted(listener_ids):
                    owned_accounts = tuple(account for account in accounts
                        if getattr(account, "listener_id", None) == listener_id)
                    action_ids = {getattr(account, "action_id", None)
                                  for account in owned_accounts}
                    owned_effects = tuple(effect for effect in effects
                        if getattr(effect, "source_action_id", None) in action_ids)
                    projection_data = {"accounts": owned_accounts,
                        "delivery_effect_ids": owned_effects,
                        "listener_id": listener_id}
                    rows.append({"role": role, "owner_id": listener_id,
                                 "projection": _plain(projection_data)})
                continue
        projection_data = {key: item for key, item in data.items()
                           if key != "identity"}
        rows.append({"role": role, "owner_id": owner,
                     "projection": _plain(projection_data)})
    rows.sort(key=lambda row: (row["role"], row["owner_id"] or ""))
    return rows


def _merge_recipient_rows(previous, updates):
    """Carry the latest recipient projection forward without losing history.

    Native receipt metadata contains only recipients touched at that boundary.
    The read model represents their latest committed state. Current observer
    owners provide a stable replacement key; old ownerless account records are
    retained by canonical value because their historical owner is unavailable.
    """
    if previous == {}:
        previous = []
    if type(previous) is not list or type(updates) is not list:
        raise NativeHistoryRejected("native recipient projection has an invalid shape")
    keyed = {}
    for row in previous:
        if type(row) is not dict or set(row) != {"role", "owner_id", "projection"}:
            raise NativeHistoryRejected("native recipient projection row is malformed")
        owner = row["owner_id"]
        key = ((row["role"], owner) if owner is not None else
               (row["role"], None, _canonical(row["projection"])))
        keyed[key] = row
    for row in updates:
        if type(row) is not dict or set(row) != {"role", "owner_id", "projection"}:
            raise NativeHistoryRejected("native recipient update is malformed")
        owner = row["owner_id"]
        key = ((row["role"], owner) if owner is not None else
               (row["role"], None, _canonical(row["projection"])))
        keyed[key] = row
    return sorted(keyed.values(), key=lambda row: (
        row["role"], row["owner_id"] or "", _canonical(row["projection"])))


def _upgrade_recipient_rows(rows):
    """Recover listener ownership already present in legacy HeardAccount facts."""
    if rows == {}:
        return []
    if type(rows) is not list:
        raise NativeHistoryRejected("legacy native recipient projection is malformed")
    upgraded = []
    for row in rows:
        if (type(row) is not dict or set(row) != {"role", "owner_id", "projection"}
                or type(row["projection"]) is not dict):
            raise NativeHistoryRejected("legacy native recipient row is malformed")
        if row["role"] != "in_world_received_accounts" or row["owner_id"] is not None:
            upgraded.append(row)
            continue
        projection = row["projection"]
        encoded_accounts = projection.get("accounts")
        encoded_effects = projection.get("delivery_effect_ids", {"$tuple": []})
        if (type(encoded_accounts) is not dict
                or set(encoded_accounts) != {"$tuple"}
                or type(encoded_accounts["$tuple"]) is not list
                or type(encoded_effects) is not dict
                or set(encoded_effects) != {"$tuple"}
                or type(encoded_effects["$tuple"]) is not list):
            upgraded.append(row)
            continue
        by_listener = {}
        for account in encoded_accounts["$tuple"]:
            fields_value = account.get("fields", {}) if type(account) is dict else {}
            listener = fields_value.get("listener_id")
            if (type(account) is not dict
                    or account.get("$record") != "history_conversation.HeardAccount"
                    or type(listener) is not str or not listener):
                raise NativeHistoryRejected("legacy testimony account has no listener identity")
            by_listener.setdefault(listener, []).append(account)
        if not by_listener:
            upgraded.append(row)
            continue
        for listener, accounts in sorted(by_listener.items()):
            action_ids = {account["fields"]["action_id"] for account in accounts}
            effects = []
            for effect in encoded_effects["$tuple"]:
                fields_value = effect.get("fields", {}) if type(effect) is dict else {}
                if (type(effect) is dict
                        and effect.get("$record") == "action_evaluation.EffectIdentity"
                        and fields_value.get("source_action_id") in action_ids):
                    effects.append(effect)
            upgraded.append({"role": row["role"], "owner_id": listener,
                "projection": {"accounts": {"$tuple": accounts},
                    "delivery_effect_ids": {"$tuple": effects},
                    "listener_id": listener}})
    return upgraded


def _validate_recipient_state(state, participants):
    recipients = state.get("recipients")
    if recipients == {}:
        return
    if type(recipients) is not list:
        raise NativeHistoryRejected("native recipient state is not an ordered record list")
    seen = set()
    allowed = {"in_world_belief_ledger", "observer_location_evidence",
               "observer_object_evidence", "in_world_received_accounts"}
    for row in recipients:
        if (type(row) is not dict
                or set(row) != {"role", "owner_id", "projection"}
                or type(row["role"]) is not str
                or row["role"] not in allowed
                or row["owner_id"] is not None
                    and (type(row["owner_id"]) is not str
                         or row["owner_id"] not in participants)
                or type(row["projection"]) is not dict):
            raise NativeHistoryRejected("native recipient owner or projection is malformed")
        owner = row["owner_id"]
        key = (row["role"], owner)
        if owner is not None and key in seen:
            raise NativeHistoryRejected("native recipient state repeats an owner binding")
        seen.add(key)
        projection = row["projection"]
        if row["role"] == "in_world_received_accounts":
            listener = projection.get("listener_id")
            if listener is not None and (listener != owner or listener not in participants):
                raise NativeHistoryRejected("native testimony history listener owner differs")
            accounts = projection.get("accounts")
            if accounts is not None:
                if (type(accounts) is not dict or set(accounts) != {"$tuple"}
                        or type(accounts["$tuple"]) is not list):
                    raise NativeHistoryRejected("native testimony history accounts are malformed")
                for account in accounts["$tuple"]:
                    if (type(account) is not dict
                            or account.get("$record") != "history_conversation.HeardAccount"
                            or owner is not None
                                and account.get("fields", {}).get("listener_id") != owner):
                        raise NativeHistoryRejected("native testimony history account has a foreign listener")
        else:
            observer = projection.get("observer_id")
            if observer is not None and (observer != owner or observer not in participants):
                raise NativeHistoryRejected("native evidence history observer owner differs")
            if owner is None:
                raise NativeHistoryRejected("native observer evidence has no logical owner")


def _initial_state(initial):
    return {
        "encounter_id": initial["encounter_id"],
        "universe_id": initial["universe_id"],
        "start": initial["start"],
        "entities": initial["entities"],
        "participants": initial["participants"],
        "initial_schedule": initial["initial_schedule"],
        "boundary": None,
        "time": initial["start"],
        "schedule": initial["initial_schedule"],
        "objective": {},
        "objective_use": {"$tuple": []},
        "recipients": {},
        "projectile_states": {},
    }


def _rng_record(value, previous, schema=SCHEMA):
    if schema == SCHEMA and previous is not None and value == previous:
        return dict(SAME_RNG)
    return value


def _decode_rng_cursor(value):
    """Decode the closed JSON tuple encoding for Python's portable RNG state."""
    if type(value) is dict:
        if set(value) == {"$tuple"} and type(value["$tuple"]) is list:
            return tuple(_decode_rng_cursor(item) for item in value["$tuple"])
        if set(value) == {"$list"} and type(value["$list"]) is list:
            return [_decode_rng_cursor(item) for item in value["$list"]]
        if set(value) == {"$number"} and type(value["$number"]) is str:
            return float.fromhex(value["$number"])
    if type(value) is list:
        return [_decode_rng_cursor(item) for item in value]
    if type(value) in (str, bool, int) or value is None:
        return value
    raise NativeHistoryRejected("native history RNG cursor has an invalid shape")


def _validate_rng_cursor(value):
    if (type(value) is not dict or set(value) != {"$tuple"}
            or type(value["$tuple"]) is not list):
        raise NativeHistoryRejected("native history RNG cursor has an invalid shape")
    import random
    try:
        random.Random().setstate(_decode_rng_cursor(value))
    except (TypeError, ValueError, OverflowError) as exc:
        raise NativeHistoryRejected("native history RNG cursor is invalid") from exc


def _quiet_changes(row):
    """Return numeric metadata increments safe to derive across a quiet run."""
    events = row.get("events")
    if (not _quiet_events(events) or row.get("rng_after") != SAME_RNG
            or row.get("notification_intents", {"$tuple": []}) != {"$tuple": []}
            or row.get("disarm_landings", {"$tuple": []}) != {"$tuple": []}
            or not row.get("changes")):
        return None
    increments = []
    for change in row["changes"]:
        path = change.get("path")
        if (type(path) is not list or not path or change.get("before") is not True
                or change.get("after") is not True
                or "before_value" not in change or "value" not in change):
            return None
        allowed = (path == ["time"] or path == ["boundary"]
                   or path == ["schedule", "fields", "schedule_revision"]
                   or (len(path) == 4 and path[0] == "entities"
                       and path[2:] == ["fields", "boundary"]))
        before, after = change["before_value"], change["value"]
        if (not allowed or type(before) is not int
                or type(after) is not int or after == before):
            return None
        increments.append((tuple(path), before, after - before))
    increments.sort(key=lambda item: item[0])
    return increments


def _quiet_events(events):
    return (type(events) is dict and set(events) == set(_EMPTY_EVENTS)
            and events["action_ids"] == [] and events["effect_ids"] == []
            and events["actions"] == {} and events["effects"] == {}
            and events["starts"] == {"$tuple": []}
            and type(events["participants"]) is dict
            and set(events["participants"]) == {"$tuple"}
            and type(events["participants"]["$tuple"]) is list)


def _compact_quiet_rows(rows):
    """Replace only repeated clock/cursor-only rows with checked linear spans."""
    output = []
    index = 0
    while index < len(rows):
        first = rows[index]
        first_changes = _quiet_changes(first)
        group = [first] if first_changes is not None else []
        next_index = index + 1
        while group and next_index < len(rows):
            previous = group[-1]
            candidate = rows[next_index]
            candidate_changes = _quiet_changes(candidate)
            if (candidate_changes is None
                    or candidate["boundary"] != previous["boundary"] + 1
                    or candidate["events"] != first["events"]
                    or candidate["start"] != previous["end"]
                    or candidate["end"] - candidate["start"]
                    != first["end"] - first["start"]
                    or [item[0] for item in candidate_changes]
                    != [item[0] for item in first_changes]
                    or candidate.get("receipt_facts_available", False)
                    != first.get("receipt_facts_available", False)
                    or [item[2] for item in candidate_changes]
                    != [item[2] for item in first_changes]):
                break
            group.append(candidate)
            next_index += 1
        if len(group) >= 2:
            output.append({
                "kind": "quiet_span",
                "from_boundary": first["boundary"],
                "to_boundary": group[-1]["boundary"],
                "start": first["start"],
                "step": first["end"] - first["start"],
                "quiet_events": {"starts": first["events"]["starts"],
                                 "participants": first["events"]["participants"]},
                "receipt_facts_available": first.get("receipt_facts_available", False),
                "increments": [{"path": list(path), "first_before": before,
                                "step": delta}
                               for path, before, delta in first_changes],
                "rng_after": dict(SAME_RNG),
                "state_sha256": group[-1]["state_sha256"],
            })
            index = next_index
        else:
            output.append(first)
            index += 1
    return output


def _apply_quiet_span(state, row, through_boundary):
    if (type(row) is not dict or set(row) not in ({
            "kind", "from_boundary", "to_boundary", "start", "step", "quiet_events",
            "increments", "rng_after", "state_sha256"}, {
            "kind", "from_boundary", "to_boundary", "start", "step", "quiet_events",
            "increments", "rng_after", "state_sha256", "receipt_facts_available"})
            or row["kind"] != "quiet_span"
            or type(row["from_boundary"]) is not int
            or type(row["to_boundary"]) is not int
            or type(row["start"]) is not int
            or type(row["step"]) is not int
            or row["step"] <= 0 or type(row["increments"]) is not list
            or type(row["quiet_events"]) is not dict
            or set(row["quiet_events"]) != {"starts", "participants"}
            or not row["increments"] or row["to_boundary"] <= row["from_boundary"]
            or row["rng_after"] != SAME_RNG
            or type(row["state_sha256"]) is not str):
        raise NativeHistoryRejected("native quiet span schema is invalid")
    quiet_events = {"action_ids": [], "effect_ids": [], "actions": {},
                    "effects": {}, "starts": row["quiet_events"]["starts"],
                    "participants": row["quiet_events"]["participants"]}
    if (not _quiet_events(quiet_events)
            or any(type(identity) is not str or not identity
                   for identity in quiet_events["participants"]["$tuple"])):
        raise NativeHistoryRejected("native quiet span participation facts are malformed")
    prior_boundary = state["boundary"]
    if (type(prior_boundary) is not int
            or not row["from_boundary"] - 1 <= prior_boundary < through_boundary
            or not row["from_boundary"] <= through_boundary <= row["to_boundary"]):
        raise NativeHistoryRejected("native quiet span chronology differs")
    first_start = row["start"]
    time_offset = max(0, prior_boundary - row["from_boundary"] + 1)
    expected_prior_time = first_start + time_offset * row["step"]
    if state["time"] != expected_prior_time:
        raise NativeHistoryRejected("native quiet span start time differs")
    result = json.loads(_canonical(state).decode("ascii"))
    seen = set()
    for item in row["increments"]:
        if (type(item) is not dict or set(item) != {"path", "first_before", "step"}
                or type(item["path"]) is not list or not item["path"]
                or any(type(part) is not str for part in item["path"])
                or type(item["first_before"]) is not int
                or type(item["step"]) is not int or item["step"] == 0):
            raise NativeHistoryRejected("native quiet span increment is malformed")
        path = item["path"]
        allowed = (path == ["time"] or path == ["boundary"]
                   or path == ["schedule", "fields", "schedule_revision"]
                   or (len(path) == 4 and path[0] == "entities"
                       and path[2:] == ["fields", "boundary"]))
        key = tuple(path)
        if not allowed or key in seen:
            raise NativeHistoryRejected("native quiet span includes a non-cursor property")
        seen.add(key)
        parent = result
        for part in path[:-1]:
            if type(parent) is not dict or part not in parent:
                raise NativeHistoryRejected("native quiet span property owner is absent")
            parent = parent[part]
        if type(parent) is not dict or path[-1] not in parent:
            raise NativeHistoryRejected("native quiet span property is absent")
        expected_before = item["first_before"] + time_offset * item["step"]
        if parent[path[-1]] != expected_before:
            raise NativeHistoryRejected("native quiet span property preimage differs")
        count = through_boundary - prior_boundary
        parent[path[-1]] = item["first_before"] + (time_offset + count) * item["step"]
    time_increment = next((item for item in row["increments"]
                           if item["path"] == ["time"]), None)
    if time_increment is None or time_increment["step"] != row["step"]:
        raise NativeHistoryRejected("native quiet span does not advance time")
    result["boundary"] = through_boundary
    return result


def rng_state_at(log, boundary):
    """Return the exact RNG cursor after a committed boundary."""
    validate(log)
    if type(boundary) is int and boundary == 0:
        initial = log["initial"].get("rng_before_first_commit")
        if initial is None:
            raise NativeHistoryRejected(
                "initial RNG cursor is not recorded in this native history")
        return json.loads(_canonical(initial).decode("ascii"))
    if type(boundary) is not int or not 1 <= boundary <= log["latest_boundary"]:
        raise NativeHistoryRejected("requested native RNG boundary is not committed")
    current = log["initial"].get("rng_before_first_commit")
    for row in log["boundaries"]:
        if row["rng_after"] == SAME_RNG:
            if current is None:
                raise NativeHistoryRejected("native RNG reference has no prior state")
        else:
            current = row["rng_after"]
        to_boundary = row.get("to_boundary", row.get("boundary"))
        if to_boundary == boundary or (row.get("from_boundary", boundary + 1)
                                       <= boundary <= to_boundary):
            break
    if current is None:
        raise NativeHistoryRejected("native RNG state is absent")
    return current


def upgrade(log):
    """Upgrade legacy history without inventing unrecorded EntityInspection facts."""
    validate(log)
    if log["schema"] == SCHEMA:
        return decode(encode(log))
    previous = log["initial"].get("rng_before_first_commit")
    # Upgrade into detached data: shallow-copying only the envelope lets field
    # additions mutate the caller's authenticated history and invalidate its
    # digest during ordinary Load processing.
    body = decode(encode(log))
    body.pop("sha256")
    body["schema"] = SCHEMA
    if log["schema"] not in RNG_HISTORY_SCHEMAS:
        body["initial"] = dict(body["initial"], rng_before_first_commit=None)
    # Before /9 the value came from the first committed receipt, not from the
    # pre-first-commit scheduler cut. Keep it as the old delta replay anchor,
    # but never expose it as boundary-zero history.
    schedule = body["initial"]["initial_schedule"]
    if schedule is not None:
        _validate_queue_projection(schedule)
    if log["schema"] not in INITIAL_SCHEDULE_SCHEMAS:
        body["initial"]["initial_schedule_available"] = False
    if log["schema"] == ENTITY_CONTEXT_SCHEMA:
        body["entity_context"] = dict(log["entity_context"], fatigue_available=False)
    elif log["schema"] not in ENTITY_CONTEXT_SCHEMAS:
        body["entity_context"] = _unavailable_entity_context()
    has_receipt_facts = log["schema"] in RECEIPT_FACT_SCHEMAS
    body["receipt_facts_complete"] = (
        log["receipt_facts_complete"] if has_receipt_facts else False)
    body["observer_knowledge"] = (
        log["observer_knowledge"]
        if log["schema"] in OBSERVER_KNOWLEDGE_SCHEMAS
        else _unavailable_observer_knowledge())
    if log["schema"] != SCHEMA:
        body["initial"]["initial_entities_available"] = False
    rows = []
    old_state = _initial_state(log["initial"])
    previous_state = _initial_state(body["initial"])
    recipient_state = []
    for original in _expand_rows(log):
        row = dict(original)
        old_state = _apply(old_state, original["changes"])
        recipient_updates = _upgrade_recipient_rows(old_state["recipients"])
        recipient_state = _merge_recipient_rows(recipient_state, recipient_updates)
        current_state = dict(old_state, recipients=recipient_state)
        row["changes"] = _diff(previous_state, current_state)
        row["state_sha256"] = hashlib.sha256(_canonical(current_state)).hexdigest()
        previous_state = current_state
        if not has_receipt_facts:
            row["notification_intents"] = {"$tuple": []}
            row["disarm_landings"] = {"$tuple": []}
            row["receipt_facts_available"] = False
        encoded_rng = original["rng_after"]
        actual_rng = previous if encoded_rng == SAME_RNG else encoded_rng
        if actual_rng is None:
            raise NativeHistoryRejected("legacy native history RNG cursor is unanchored")
        row["rng_after"] = _rng_record(actual_rng, previous, SCHEMA)
        previous = actual_rng
        rows.append(row)
    body["boundaries"] = _compact_quiet_rows(rows)
    result = _seal(body)
    validate(result)
    return result


def _without_entity_context(log):
    """Normalize a current recording only for an authenticated legacy migration check."""
    validate(log)
    body = {key: value for key, value in log.items() if key != "sha256"}
    body["initial"] = dict(body["initial"], rng_before_first_commit=None)
    body["initial"]["initial_entities_available"] = False
    body["entity_context"] = _unavailable_entity_context()
    body["receipt_facts_complete"] = False
    body["observer_knowledge"] = _unavailable_observer_knowledge()
    rows = []
    previous = None
    for row, actual in _resolved_rng_rows(log):
        current = dict(row)
        current["notification_intents"] = {"$tuple": []}
        current["disarm_landings"] = {"$tuple": []}
        current["receipt_facts_available"] = False
        current["rng_after"] = _rng_record(actual, previous, SCHEMA)
        previous = actual
        rows.append(current)
    body["boundaries"] = _compact_quiet_rows(rows)
    result = _seal(body)
    validate(result)
    return result


def _without_initial_rng(log):
    """Normalize a current log to the information available in schema `/5`."""
    validate(log)
    body = {key: value for key, value in log.items() if key != "sha256"}
    body["initial"] = dict(body["initial"], rng_before_first_commit=None,
                            initial_entities_available=False)
    body["receipt_facts_complete"] = False
    body["observer_knowledge"] = _unavailable_observer_knowledge()
    rows = []
    previous = None
    for row, actual in _resolved_rng_rows(log):
        current = dict(row)
        current["notification_intents"] = {"$tuple": []}
        current["disarm_landings"] = {"$tuple": []}
        current["receipt_facts_available"] = False
        current["rng_after"] = _rng_record(actual, previous, SCHEMA)
        previous = actual
        rows.append(current)
    body["boundaries"] = _compact_quiet_rows(rows)
    result = _seal(body)
    validate(result)
    return result


def _seal(body):
    value = dict(body)
    value["sha256"] = hashlib.sha256(_canonical(value)).hexdigest()
    return value


def _unavailable_entity_context():
    # Older histories did not retain these per-boundary inspection facts.
    # Preserve that limitation explicitly; never infer it from current state.
    return {"available": False, "fatigue_available": False,
            "initial": None, "changes": []}


def _without_fatigue_context(log):
    """Normalize current context facts for an authenticated `/4` migration check."""
    validate(log)
    if log["schema"] != SCHEMA or not log["entity_context"]["available"]:
        return _without_entity_context(log)
    context = log["entity_context"]

    def strip(state):
        result = json.loads(_canonical(state).decode("ascii"))
        for entity in result.values():
            if type(entity) is not dict or entity.get("$record") != "encounter_inspection.EntityInspection":
                continue
            pre_action = entity["fields"].get("pre_action")
            if type(pre_action) is dict:
                pre_action.pop("physical_fatigue", None)
                pre_action.pop("physiology", None)
        return result

    prior = strip(context["initial"])
    original = context["initial"]
    changes = []
    for row in context["changes"]:
        original = _apply(original, row["changes"])
        current = strip(original)
        delta = _diff(prior, current)
        if delta:
            changes.append({"boundary": row["boundary"], "changes": delta,
                            "state_sha256": hashlib.sha256(_canonical(current)).hexdigest()})
        prior = current
    body = {key: value for key, value in log.items() if key != "sha256"}
    body["initial"] = dict(body["initial"], rng_before_first_commit=None,
                            initial_entities_available=False)
    body["entity_context"] = {"available": True, "fatigue_available": False,
                              "initial": strip(context["initial"]), "changes": changes}
    body["receipt_facts_complete"] = False
    body["observer_knowledge"] = _unavailable_observer_knowledge()
    rows = []
    previous_rng = None
    for row, actual_rng in _resolved_rng_rows(log):
        current = dict(row)
        current["notification_intents"] = {"$tuple": []}
        current["disarm_landings"] = {"$tuple": []}
        current["receipt_facts_available"] = False
        current["rng_after"] = _rng_record(actual_rng, previous_rng, SCHEMA)
        previous_rng = actual_rng
        rows.append(current)
    body["boundaries"] = _compact_quiet_rows(rows)
    result = _seal(body)
    validate(result)
    return result


def _without_receipt_facts(log):
    """Normalize current facts to a legacy receipt-free `/6` history view."""
    validate(log)
    body = {key: value for key, value in log.items() if key != "sha256"}
    body["initial"]["initial_entities_available"] = False
    body["receipt_facts_complete"] = False
    body["observer_knowledge"] = _unavailable_observer_knowledge()
    rows = []
    for original in _expand_rows(log):
        row = dict(original)
        row["notification_intents"] = {"$tuple": []}
        row["disarm_landings"] = {"$tuple": []}
        row["receipt_facts_available"] = False
        rows.append(row)
    body["boundaries"] = _compact_quiet_rows(rows)
    result = _seal(body)
    validate(result)
    return result


def _unavailable_observer_knowledge():
    return {"available": False, "initial": None, "changes": []}


def _remember_record_initial_schedule(encounter, log):
    initial = log.get("initial", {}) if type(log) is dict else {}
    if initial.get("initial_schedule_available") is True:
        with _RECORDER_LOCK:
            _INITIAL_SCHEDULES[encounter] = initial["initial_schedule"]


def _remember_record_initial_entities(encounter, log):
    initial = log["initial"]
    if initial.get("initial_entities_available") is True:
        context = log.get("entity_context", {})
        if context.get("available") is True:
            _INITIAL_ENTITIES[encounter] = _materialize_plain(context["initial"])


def _without_observer_knowledge(log):
    """Normalize /8 facts to the exact observer-knowledge scope of /7."""
    validate(log)
    body = {key: value for key, value in log.items() if key != "sha256"}
    body["initial"]["initial_entities_available"] = False
    body["observer_knowledge"] = _unavailable_observer_knowledge()
    result = _seal(body)
    validate(result)
    return result


def _validate_plain_record(value, depth=0):
    """Validate tagged values used by sparse historical EntityInspection facts."""
    if depth > MAX_DEPTH:
        raise NativeHistoryRejected("native EntityInspection nesting limit exceeded")
    if value is None or type(value) in (str, bool, int):
        return
    if type(value) is list:
        for item in value:
            _validate_plain_record(item, depth + 1)
        return
    if type(value) is not dict:
        raise NativeHistoryRejected("native EntityInspection contains an invalid value")
    if set(value) == {"$number"}:
        number = value["$number"]
        if type(number) is not str:
            raise NativeHistoryRejected("native EntityInspection number is malformed")
        try:
            parsed = float.fromhex(number)
        except ValueError as exc:
            raise NativeHistoryRejected("native EntityInspection number is malformed") from exc
        if not math.isfinite(parsed) or parsed.hex() != number:
            raise NativeHistoryRejected("native EntityInspection number is noncanonical")
        return
    if "$record" in value:
        if set(value) != {"$record", "fields"} or type(value["$record"]) is not str or type(value["fields"]) is not dict:
            raise NativeHistoryRejected("native EntityInspection record is malformed")
        tag = value["$record"]
        adapter = FIELD_ADAPTERS.get(tag)
        if tag == "interval_staging.AuthorityReference":
            allowed = required = {"key", "role"}
        elif tag == "observer_proposals.RecipientIdentity":
            allowed = required = {"role"}
        elif adapter is None and tag == "encounter_inspection.EntityInspection":
            allowed = {"category", "obj_type", "name", "position", "pre_action"}
            required = allowed
        elif adapter is not None:
            allowed, required = set(adapter["allowed"]), set(adapter["required"])
        else:
            raise NativeHistoryRejected("native EntityInspection record type is unreviewed")
        fields_value = value["fields"]
        if (not set(fields_value) <= allowed or not required <= set(fields_value)
                or "target_anchors" in fields_value or "action_anchors" in fields_value):
            raise NativeHistoryRejected("native EntityInspection fields differ from the closed schema")
        for item in fields_value.values():
            _validate_plain_record(item, depth + 1)
        return
    if any(key in value for key in ("$tuple", "$list", "$set", "$frozenset")):
        if len(value) != 1:
            raise NativeHistoryRejected("native EntityInspection sequence tag is ambiguous")
        key, items = next(iter(value.items()))
        if key not in ("$tuple", "$list", "$set", "$frozenset") or type(items) is not list:
            raise NativeHistoryRejected("native EntityInspection sequence is malformed")
        if key in ("$set", "$frozenset"):
            encoded = [_canonical(item) for item in items]
            if encoded != sorted(set(encoded)):
                raise NativeHistoryRejected("native EntityInspection set is noncanonical")
        for item in items:
            _validate_plain_record(item, depth + 1)
        return
    if "$map" in value:
        if set(value) != {"$map"} or type(value["$map"]) is not list:
            raise NativeHistoryRejected("native EntityInspection map is malformed")
        encoded_keys = []
        for pair in value["$map"]:
            if type(pair) is not list or len(pair) != 2:
                raise NativeHistoryRejected("native EntityInspection map entry is malformed")
            encoded_keys.append(_canonical(pair[0]))
            _validate_plain_record(pair[0], depth + 1)
            _validate_plain_record(pair[1], depth + 1)
        if encoded_keys != sorted(set(encoded_keys)):
            raise NativeHistoryRejected("native EntityInspection map is noncanonical")
        return
    if not all(type(key) is str for key in value):
        raise NativeHistoryRejected("native EntityInspection mapping keys are malformed")
    for item in value.values():
        _validate_plain_record(item, depth + 1)


def capture(encounter, *, initial_schedule=None,
            initial_schedule_available=None, initial_entities=None):
    """Capture committed facts from a native Encounter without resolving work.

    The returned format is a queryable historical record, not a resumable Save
    yet. Every logical boundary remains queryable. Consecutive empty-event
    intervals may use a validated numeric cursor span; Action/Event/Effect
    boundaries remain individual atomic records.
    """
    from encounter import Encounter
    if type(encounter) is not Encounter:
        raise NativeHistoryRejected("native Encounter required")
    if initial_schedule is None:
        with _RECORDER_LOCK:
            initial_schedule = _INITIAL_SCHEDULES.get(encounter)
    if initial_entities is None:
        with _RECORDER_LOCK:
            initial_entities = _INITIAL_ENTITIES.get(encounter)
    view = encounter.inspect_committed()
    receipts = tuple(encounter.__dict__.get("_atomic_interval_history", ()))
    if not receipts or len(receipts) != len(view.timeline):
        raise NativeHistoryRejected("committed native receipt chain is incomplete")
    targets_by_boundary = _target_candidates(encounter)
    initial_receipt = receipts[0]
    if initial_schedule_available is None:
        initial_schedule_available = initial_schedule is not None
    initial_entity_context = (_plain(initial_entities)
                              if initial_entities is not None else
                              _plain(initial_receipt.inspection.entities))
    initial_entities_available = initial_entities is not None
    initial = {
        "encounter_id": encounter.id,
        "universe_id": encounter.universe.id,
        "start": _plain(initial_receipt.inspection.start),
        "entities": initial_entity_context,
        "participants": _plain(initial_receipt.inspection.participants),
        "initial_entities_available": initial_entities_available,
        "initial_schedule": initial_schedule,
        "initial_schedule_available": initial_schedule_available,
        "rng_before_first_commit": _plain(
            encounter.__dict__["_native_rng_origin_state"])
            if encounter.__dict__.get("_native_rng_origin_state") is not None
            else None,
    }
    entity_context_state = initial_entity_context
    entity_context_changes = []
    prior = _initial_state(initial)
    recipient_state = []
    boundaries = []
    previous_boundary = None
    previous_rng = initial["rng_before_first_commit"]
    for receipt in receipts:
        if (receipt.encounter_id != encounter.id
                or type(receipt.boundary) is not int
                or previous_boundary is not None and receipt.boundary != previous_boundary + 1):
            raise NativeHistoryRejected("native boundary order or owner identity is invalid")
        payload = _boundary_payload(encounter, receipt, view,
                                    targets_by_boundary)
        payload["recipients"] = _merge_recipient_rows(
            recipient_state, payload["recipients"])
        recipient_state = payload["recipients"]
        if payload["entity_context"] != entity_context_state:
            context_changes = _diff(entity_context_state, payload["entity_context"])
            entity_context_state = payload["entity_context"]
            entity_context_changes.append({
                "boundary": receipt.boundary,
                "changes": context_changes,
                "state_sha256": hashlib.sha256(
                    _canonical(entity_context_state)).hexdigest(),
            })
        state = {
            "boundary": payload["boundary"],
            "time": payload["end"],
            "entities": payload["target_states"],
            "schedule": payload["schedule"],
            "objective": payload["objective"],
            "objective_use": payload["objective_use"],
            "recipients": payload["recipients"],
            "projectile_states": payload["projectile_states"],
        }
        changes = _diff(prior, state)
        boundaries.append({
            "boundary": receipt.boundary,
            "start": payload["start"], "end": payload["end"],
            "changes": changes,
            "events": {"action_ids": payload["action_ids"],
                       "effect_ids": payload["effect_ids"],
                       "actions": payload["actions"],
                       "effects": payload["effects"],
                       "starts": payload["starts"],
                       "participants": payload["participants"]},
            "notification_intents": payload["notification_intents"],
            "disarm_landings": payload["disarm_landings"],
            "receipt_facts_available": True,
            "rng_after": _rng_record(payload["rng_after"], previous_rng),
            "state_sha256": hashlib.sha256(_canonical(state)).hexdigest(),
        })
        previous_rng = payload["rng_after"]
        prior = state
        previous_boundary = receipt.boundary
    observer_context = _arena_observer_context(encounter, previous_boundary)
    body = {"schema": SCHEMA, "initial": initial,
            "boundaries": _compact_quiet_rows(boundaries),
            "latest_boundary": previous_boundary,
            "receipt_facts_complete": True,
            "entity_context": {"available": True,
                               "fatigue_available": True,
                               "initial": initial_entity_context,
                               "changes": entity_context_changes},
            "observer_knowledge": observer_context}
    _measure(body)
    return _seal(body)


def _expand_rows(log):
    """Expand validated quiet spans for append/normalization operations."""
    state = _initial_state(log["initial"])
    output = []
    for row in log["boundaries"]:
        if row.get("kind") != "quiet_span":
            output.append(json.loads(_canonical(row).decode("ascii")))
            state = _apply(state, row["changes"])
            continue
        for boundary in range(row["from_boundary"], row["to_boundary"] + 1):
            next_state = _apply_quiet_span(state, row, boundary)
            output.append({
                "boundary": boundary,
                "start": state["time"], "end": next_state["time"],
                "changes": _diff(state, next_state),
                "events": {"action_ids": [], "effect_ids": [], "actions": {},
                           "effects": {},
                           "starts": row["quiet_events"]["starts"],
                           "participants": row["quiet_events"]["participants"]},
                "notification_intents": {"$tuple": []},
                "disarm_landings": {"$tuple": []},
                "receipt_facts_available": row.get("receipt_facts_available", False),
                "rng_after": dict(SAME_RNG),
                "state_sha256": hashlib.sha256(_canonical(next_state)).hexdigest(),
            })
            state = next_state
    return output


def _resolved_rng_rows(log):
    """Yield expanded rows with their exact cursor using one linear pass."""
    current = log["initial"].get("rng_before_first_commit")
    for row in _expand_rows(log):
        encoded = row["rng_after"]
        if encoded == SAME_RNG:
            if current is None:
                raise NativeHistoryRejected("native RNG reference has no prior state")
        else:
            current = encoded
        yield row, current


def _append_compact_row(boundaries, row):
    """Append one fact row, extending a quiet span without expanding its prefix."""
    output = list(boundaries)
    if not output:
        return [row]
    previous = output[-1]
    candidate = _quiet_changes(row)
    if previous.get("kind") == "quiet_span" and candidate is not None:
        count = previous["to_boundary"] - previous["from_boundary"] + 1
        expected = [(tuple(item["path"]), item["step"])
                    for item in previous["increments"]]
        if (row["boundary"] == previous["to_boundary"] + 1
                and row["start"] == previous["start"] + count * previous["step"]
                and row["end"] - row["start"] == previous["step"]
                and row["events"]["starts"] == previous["quiet_events"]["starts"]
                and row["events"]["participants"] == previous["quiet_events"]["participants"]
                and row.get("receipt_facts_available", False)
                    == previous.get("receipt_facts_available", False)
                and [(path, delta) for path, _before, delta in candidate] == expected):
            for index, (path, _before, _delta) in enumerate(candidate):
                change = row["changes"][index]
                stored = previous["increments"][index]
                if change["before_value"] != (
                        stored["first_before"] + count * stored["step"]):
                    return output + [row]
            extended = dict(previous)
            extended["to_boundary"] = row["boundary"]
            extended["state_sha256"] = row["state_sha256"]
            output[-1] = extended
            return output
    if previous.get("kind") != "quiet_span":
        pair = _compact_quiet_rows([previous, row])
        if len(pair) == 1 and pair[0].get("kind") == "quiet_span":
            output[-1] = pair[0]
            return output
    return output + [row]


def append_committed(log, encounter):
    """Return a new history log with exactly the next authenticated commit.

    The caller invokes this only after ordinary native publication returns.
    A rolled-back candidate has no registered committed receipt and cannot be
    appended. One receipt is one atomic boundary, including a simultaneous
    multi-Action batch. The input log is never modified on refusal.
    """
    validate(log)
    from encounter import Encounter
    import atomic_publication
    from encounter_inspection import fingerprint

    if type(encounter) is not Encounter:
        raise NativeHistoryRejected("native Encounter required")
    if (log["initial"]["encounter_id"] != encounter.id
            or log["initial"]["universe_id"] != encounter.universe.id):
        raise NativeHistoryRejected("history belongs to another logical Encounter")
    history = encounter.__dict__.get("_atomic_interval_history")
    expected = log["latest_boundary"] + 1
    if type(history) is not list or not history:
        raise NativeHistoryRejected("native committed receipt is missing")
    receipt = history[-1]
    if (type(receipt) is not atomic_publication.PublishedInterval
            or receipt.encounter_id != encounter.id or receipt.boundary != expected
            or encounter.time != expected or encounter.last_processed_boundary != expected):
        raise NativeHistoryRejected("there is no next committed boundary to append")
    issued = atomic_publication._COMMITTED_RECEIPTS.get(id(receipt))
    if (issued is None or issued[0]() is not receipt or issued[1]() is not encounter
            or issued[2] != fingerprint(receipt)):
        raise NativeHistoryRejected("native boundary receipt is not authenticated")

    # inspect_committed validates the complete receipt chain and obtains the
    # authoritative, detached historical read model after publication.
    view = encounter.inspect_committed(receipt=receipt)
    targets = _target_candidates(encounter).get(expected, {})
    payload = _boundary_payload(encounter, receipt, view, {expected: targets})
    log = upgrade(log)
    previous = state_at(log, log["latest_boundary"])
    previous_rng = rng_state_at(log, log["latest_boundary"])
    payload["recipients"] = _merge_recipient_rows(
        previous["recipients"], payload["recipients"])
    state = {
        "boundary": payload["boundary"],
        "time": payload["end"],
        "entities": payload["target_states"],
        "schedule": payload["schedule"],
        "objective": payload["objective"],
        "objective_use": payload["objective_use"],
        "recipients": payload["recipients"],
        "projectile_states": payload["projectile_states"],
    }
    row = {
        "boundary": expected,
        "start": payload["start"], "end": payload["end"],
        "changes": _diff(previous, state),
        "events": {"action_ids": payload["action_ids"],
                    "effect_ids": payload["effect_ids"],
                    "actions": payload["actions"],
                    "effects": payload["effects"],
                    "starts": payload["starts"],
                    "participants": payload["participants"]},
        "notification_intents": payload["notification_intents"],
        "disarm_landings": payload["disarm_landings"],
        "receipt_facts_available": True,
        "rng_after": _rng_record(payload["rng_after"], previous_rng),
        "state_sha256": hashlib.sha256(_canonical(state)).hexdigest(),
    }
    body = {key: value for key, value in log.items() if key != "sha256"}
    body["boundaries"] = _append_compact_row(log["boundaries"], row)
    body["latest_boundary"] = expected
    body["receipt_facts_complete"] = bool(
        log["receipt_facts_complete"] and row["receipt_facts_available"])
    entity_context = json.loads(_canonical(log["entity_context"]).decode("ascii"))
    if entity_context["available"]:
        prior_context = entity_context_at(log, log["latest_boundary"])
        if prior_context != payload["entity_context"]:
            changes = _diff(prior_context, payload["entity_context"])
            entity_context["changes"].append({
                "boundary": expected,
                "changes": changes,
                "state_sha256": hashlib.sha256(
                    _canonical(payload["entity_context"])).hexdigest(),
            })
    body["entity_context"] = entity_context
    knowledge = json.loads(_canonical(log["observer_knowledge"]).decode("ascii"))
    if knowledge["available"]:
        fresh_knowledge = _arena_observer_context(encounter, expected)
        old_rows = [row for row in fresh_knowledge["changes"]
                    if row["boundary"] <= log["latest_boundary"]]
        if (fresh_knowledge["initial"] != knowledge["initial"]
                or old_rows != knowledge["changes"]):
            raise NativeHistoryRejected(
                "Arena observer evidence changed outside the appended native boundary")
        latest_rows = [row for row in fresh_knowledge["changes"]
                       if row["boundary"] == expected]
        if len(latest_rows) > 1:
            raise NativeHistoryRejected(
                "Arena observer evidence has ambiguous same-boundary reconstruction")
        if latest_rows:
            knowledge["changes"].append(latest_rows[0])
        body["observer_knowledge"] = knowledge
    else:
        body["observer_knowledge"] = knowledge
    _measure(body)
    result = _seal(body)
    validate(result)
    return result


def capture_legacy_entity_anchor(encounter, *, initial_schedule=None,
                                 initial_schedule_available=None):
    """Capture current receipts using the pre-/11 first-receipt Entity anchor."""
    receipts = tuple(encounter.__dict__.get("_atomic_interval_history", ()))
    if not receipts:
        raise NativeHistoryRejected("committed native receipt chain is incomplete")
    anchored = capture(
        encounter, initial_schedule=initial_schedule,
        initial_schedule_available=initial_schedule_available,
        initial_entities=receipts[0].inspection.entities)
    body = {key: value for key, value in anchored.items() if key != "sha256"}
    body["initial"]["initial_entities_available"] = False
    return _seal(body)


class NativeHistoryRecorder:
    """Opt-in in-memory recorder fed only after successful native publication."""

    def __init__(self, encounter, log, *, initial_schedule=None):
        self._encounter_ref = weakref(encounter)
        self._log = log
        self._initial_schedule = initial_schedule
        self.failure = None

    @property
    def encounter(self):
        encounter = self._encounter_ref()
        if encounter is None:
            raise NativeHistoryRejected("recorded Encounter no longer exists")
        return encounter

    @classmethod
    def attach(cls, encounter):
        """Attach to an already committed Encounter boundary for later steps."""
        with _RECORDER_LOCK:
            if encounter in _RECORDERS:
                raise NativeHistoryRejected("a native history recorder is already attached")
            recorder = cls(encounter, capture(encounter))
            _RECORDERS[encounter] = recorder
            return recorder

    @classmethod
    def ensure_attached(cls, encounter, *, log=None):
        """Idempotently attach only a verified log for a completed Save cut."""
        with _RECORDER_LOCK:
            recorder = _RECORDERS.get(encounter)
            if recorder is None:
                candidate = capture(encounter) if log is None else upgrade(log)
                if (candidate["initial"]["encounter_id"] != encounter.id
                        or candidate["initial"]["universe_id"] != encounter.universe.id
                        or candidate["latest_boundary"] != encounter.last_processed_boundary):
                    raise NativeHistoryRejected(
                        "native history does not match the completed Save cut")
                recorder = cls(encounter, candidate)
                _RECORDERS[encounter] = recorder
                _remember_record_initial_schedule(encounter, candidate)
                _remember_record_initial_entities(encounter, candidate)
            elif log is not None and encode(recorder._log) != encode(upgrade(log)):
                raise NativeHistoryRejected(
                    "native history recorder differs from the completed Save cut")
            return recorder

    @classmethod
    def ensure_pending_attached(cls, encounter):
        """Attach a deferred recorder at an exact pre-first-boundary Save cut."""
        from encounter import Encounter
        from transactional_progression import mode_of
        if (type(encounter) is not Encounter
                or mode_of(encounter) != 'transactional'
                or encounter.__dict__.get("_atomic_interval_history")
                or encounter.time != encounter.start_time
                or encounter.last_processed_boundary != encounter.time):
            raise NativeHistoryRejected(
                "deferred history recorder requires an uncommitted initial state")
        with _RECORDER_LOCK:
            recorder = _RECORDERS.get(encounter)
            if recorder is None:
                recorder = cls(encounter, None,
                               initial_schedule=capture_initial_schedule(encounter))
                _RECORDERS[encounter] = recorder
                _INITIAL_SCHEDULES[encounter] = recorder._initial_schedule
            elif recorder._log is not None:
                raise NativeHistoryRejected(
                    "committed history recorder differs from the initial Save cut")
            return recorder

    @classmethod
    def restore(cls, encounter, log, *, current_history=None):
        """Resume recording from an authenticated Save history after Load."""
        log = upgrade(log)
        actual_history = (encode(capture(encounter)) if current_history is None
                          else current_history)
        if (log['initial']['encounter_id'] != encounter.id
                or log['initial']['universe_id'] != encounter.universe.id
                or log['latest_boundary'] != encounter.last_processed_boundary
                or actual_history != encode(log)):
            raise NativeHistoryRejected(
                'restored Encounter does not match the saved native history')
        with _RECORDER_LOCK:
            if encounter in _RECORDERS:
                raise NativeHistoryRejected(
                    'a native history recorder is already attached')
            recorder = cls(encounter, decode(encode(log)))
            _RECORDERS[encounter] = recorder
            _remember_record_initial_schedule(encounter, log)
            _remember_record_initial_entities(encounter, log)
            return recorder

    @classmethod
    def restore_pending(cls, encounter):
        """Bind a validated initial graph to begin history at its first commit."""
        return cls.ensure_pending_attached(encounter)

    @property
    def latest_boundary(self):
        return None if self._log is None else self._log["latest_boundary"]

    def export(self):
        with _RECORDER_LOCK:
            if self.failure is not None:
                raise NativeHistoryRejected("native history recorder failed: " + self.failure)
            if self._log is None:
                raise NativeHistoryRejected("native history has no committed boundary yet")
            if self.encounter.last_processed_boundary != self.latest_boundary:
                raise NativeHistoryRejected("native history recorder is behind the Encounter")
            return decode(encode(self._log))


def has_recorder(encounter):
    with _RECORDER_LOCK:
        return encounter in _RECORDERS


def current_recording(encounter):
    with _RECORDER_LOCK:
        recorder = _RECORDERS.get(encounter)
    if recorder is None:
        return None
    if recorder.failure is not None:
        return recorder.export()
    return None if recorder._log is None else recorder.export()


def record_committed_boundary(encounter, *, initial_schedule=None,
                              initial_entities=None):
    """Append the latest commit after native publication has fully returned."""
    with _RECORDER_LOCK:
        recorder = _RECORDERS.get(encounter)
    if recorder is None:
        if initial_schedule is not None or initial_entities is not None:
            with _RECORDER_LOCK:
                if initial_entities is not None:
                    _INITIAL_ENTITIES.setdefault(encounter, initial_entities)
                    initial_entities = _INITIAL_ENTITIES.get(encounter)
                if initial_schedule is not None:
                    _INITIAL_SCHEDULES.setdefault(encounter, initial_schedule)
                    initial_schedule = _INITIAL_SCHEDULES.get(encounter)
        return
    try:
        baseline = (recorder._initial_schedule if recorder is not None
                    and recorder._initial_schedule is not None
                    else initial_schedule)
        if initial_entities is not None:
            with _RECORDER_LOCK:
                _INITIAL_ENTITIES.setdefault(encounter, initial_entities)
                initial_entities = _INITIAL_ENTITIES.get(encounter)
        updated = (capture(encounter, initial_schedule=baseline,
                           initial_entities=initial_entities)
                   if recorder._log is None
                   else append_committed(recorder._log, encounter))
        with _RECORDER_LOCK:
            recorder._log = updated
            recorder._initial_schedule = None
            _remember_record_initial_schedule(encounter, updated)
    except Exception as exc:
        # The Encounter publication is already authoritative and committed.
        # Preserve ordinary progression; make later Save fail closed until the
        # recorder is recovered from the authenticated native receipt chain.
        with _RECORDER_LOCK:
            if recorder is not None:
                recorder.failure = f"{type(exc).__name__}: {exc}"


def record_committed_disarm_landing(encounter):
    """Amend the current cut with a committed no-time Disarm landing.

    Choosing the landing has no Encounter-time cost and does not publish a new
    interval boundary.  The existing latest history cut must nevertheless
    retain its newly committed receipt and any corresponding current-state
    facts.  Re-capture from authenticated native receipts, then prove that the
    update is confined to that cut and did not change earlier history, event
    identity, RNG, or timeline.
    """
    with _RECORDER_LOCK:
        recorder = _RECORDERS.get(encounter)
    if recorder is None:
        return
    try:
        prior = upgrade(recorder._log)
        if prior["latest_boundary"] != encounter.last_processed_boundary:
            raise NativeHistoryRejected(
                "Disarm landing cannot amend a history recorder behind its Encounter")
        updated = capture(encounter,
                          initial_schedule=recorder._initial_schedule)
        if (updated["initial"] != prior["initial"]
                or updated["latest_boundary"] != prior["latest_boundary"]):
            raise NativeHistoryRejected(
                "Disarm landing changed the native history origin or boundary")
        before_rows = list(_expand_rows(prior))
        after_rows = list(_expand_rows(updated))
        boundary = prior["latest_boundary"]
        if len(before_rows) != boundary or len(after_rows) != boundary:
            raise NativeHistoryRejected(
                "Disarm landing history cut has an incomplete boundary sequence")
        if before_rows[:-1] != after_rows[:-1]:
            raise NativeHistoryRejected(
                "Disarm landing changed a previously recorded history boundary")
        before, after = before_rows[-1], after_rows[-1]
        for field in ("boundary", "start", "end", "events", "rng_after"):
            if before[field] != after[field]:
                raise NativeHistoryRejected(
                    "Disarm landing changed the latest boundary's timeline or events")
        old_facts = before["disarm_landings"]["$tuple"]
        new_facts = after["disarm_landings"]["$tuple"]
        current = [_plain(row) for row in encounter.__dict__.get(
            "_disarm_landing_receipts", ()) if row.boundary == boundary]
        if (new_facts != current or new_facts[:len(old_facts)] != old_facts
                or len(new_facts) <= len(old_facts)):
            raise NativeHistoryRejected(
                "Disarm landing receipt was not added exactly to the current history cut")
        validate(updated)
        with _RECORDER_LOCK:
            recorder._log = updated
            _remember_record_initial_schedule(encounter, updated)
    except Exception as exc:
        # The no-time publication has already committed.  Match interval
        # recording semantics: preserve the authoritative result and fail
        # subsequent Save closed if its authenticated history cannot be
        # advanced safely.
        with _RECORDER_LOCK:
            recorder.failure = f"{type(exc).__name__}: {exc}"


def validate(log):
    """Strictly validate identity, chronology, atomic deltas, and integrity."""
    base_keys = {"schema", "initial", "boundaries", "latest_boundary", "sha256"}
    current_keys = base_keys | {"entity_context"}
    version = log.get("schema") if type(log) is dict else None
    has_receipt_facts = version in RECEIPT_FACT_SCHEMAS
    has_observer_knowledge = version in OBSERVER_KNOWLEDGE_SCHEMAS
    has_initial_schedule = version in INITIAL_SCHEDULE_SCHEMAS
    has_entity_context = version in ENTITY_CONTEXT_SCHEMAS
    expected_envelope = (current_keys | {"receipt_facts_complete"}
                         if has_receipt_facts else current_keys if has_entity_context
                         else base_keys)
    if has_observer_knowledge:
        expected_envelope |= {"observer_knowledge"}
    if (type(log) is not dict
            or set(log) != expected_envelope):
        raise NativeHistoryRejected("native history envelope schema differs")
    unsigned = dict(log)
    digest = unsigned.pop("sha256")
    if (log["schema"] not in (*LEGACY_SCHEMAS, SCHEMA) or type(digest) is not str
            or hashlib.sha256(_canonical(unsigned)).hexdigest() != digest):
        raise NativeHistoryRejected("native history integrity digest differs")
    _measure(unsigned)
    initial = log["initial"]
    expected_initial = {"encounter_id", "universe_id", "start", "entities",
                        "participants", "initial_schedule"}
    if version in RNG_HISTORY_SCHEMAS:
        expected_initial.add("rng_before_first_commit")
    if has_initial_schedule:
        expected_initial.add("initial_schedule_available")
    if version == SCHEMA:
        expected_initial.add("initial_entities_available")
    if (type(initial) is not dict or set(initial) != expected_initial or type(initial["encounter_id"]) is not str
            or not initial["encounter_id"] or type(initial["universe_id"]) is not str
            or not initial["universe_id"]):
        raise NativeHistoryRejected("native history initial state schema differs")
    if version in RNG_HISTORY_SCHEMAS and initial["rng_before_first_commit"] is not None:
        _validate_rng_cursor(initial["rng_before_first_commit"])
    if version == SCHEMA and type(initial["initial_entities_available"]) is not bool:
        raise NativeHistoryRejected("initial Entity state availability marker is malformed")
    if has_initial_schedule:
        if type(initial["initial_schedule_available"]) is not bool:
            raise NativeHistoryRejected("initial scheduler availability marker is malformed")
        if initial["initial_schedule_available"] and initial["initial_schedule"] is None:
            raise NativeHistoryRejected("available initial scheduler projection is absent")
        if initial["initial_schedule"] is not None:
            _validate_queue_projection(initial["initial_schedule"])
    participant_value = initial["participants"]
    if (type(participant_value) is not dict
            or set(participant_value) != {"$tuple"}
            or type(participant_value["$tuple"]) is not list
            or any(type(identity) is not str or not identity
                   for identity in participant_value["$tuple"])
            or len(participant_value["$tuple"])
                != len(set(participant_value["$tuple"]))):
        raise NativeHistoryRejected("native history participant identities are malformed")
    participant_ids = set(participant_value["$tuple"])
    if has_receipt_facts and type(log["receipt_facts_complete"]) is not bool:
        raise NativeHistoryRejected("native receipt-fact completeness marker is malformed")
    state = _initial_state(initial)
    boundaries = log["boundaries"]
    if type(boundaries) is not list:
        raise NativeHistoryRejected("native history boundaries are not an array")
    seen_actions = set()
    seen_effects = set()
    prior_rng = initial.get("rng_before_first_commit")
    covered = 0
    receipt_completeness = []
    for row in boundaries:
        if type(row) is dict and row.get("kind") == "quiet_span":
            if has_receipt_facts:
                if (set(row) != {"kind", "from_boundary", "to_boundary", "start",
                                 "step", "quiet_events", "increments", "rng_after",
                                 "state_sha256", "receipt_facts_available"}
                        or type(row.get("receipt_facts_available")) is not bool):
                    raise NativeHistoryRejected("quiet-span receipt availability is malformed")
                receipt_completeness.append(row["receipt_facts_available"])
            elif "receipt_facts_available" in row:
                raise NativeHistoryRejected("legacy quiet span contains a future receipt field")
            if log["schema"] not in (QUIET_SPAN_SCHEMA, ENTITY_CONTEXT_SCHEMA,
                                      FATIGUE_CONTEXT_SCHEMA, INITIAL_RNG_SCHEMA,
                                      *RECEIPT_FACT_SCHEMAS):
                raise NativeHistoryRejected("legacy native history cannot contain quiet spans")
            if row.get("rng_after") != SAME_RNG or prior_rng is None:
                raise NativeHistoryRejected("native quiet span RNG reference is unanchored")
            if type(row.get("from_boundary")) is not int or row["from_boundary"] != covered + 1:
                raise NativeHistoryRejected("native quiet span boundary order differs")
            state = _apply_quiet_span(state, row, row.get("to_boundary"))
            _validate_recipient_state(state, participant_ids)
            if row["state_sha256"] != hashlib.sha256(_canonical(state)).hexdigest():
                raise NativeHistoryRejected("native quiet span state digest differs")
            covered = row["to_boundary"]
            continue
        expected = covered + 1
        expected_row_keys = {"boundary", "start", "end", "changes", "events",
                             "rng_after", "state_sha256"}
        if has_receipt_facts:
            expected_row_keys |= {"notification_intents", "disarm_landings",
                                  "receipt_facts_available"}
        if (type(row) is not dict or set(row) != expected_row_keys or type(row["boundary"]) is not int
                or row["boundary"] != expected):
            raise NativeHistoryRejected("native history boundary is missing, repeated, or malformed")
        if row["rng_after"] == SAME_RNG:
            if log["schema"] not in (QUIET_SPAN_SCHEMA, ENTITY_CONTEXT_SCHEMA,
                                      FATIGUE_CONTEXT_SCHEMA, INITIAL_RNG_SCHEMA,
                                      *RECEIPT_FACT_SCHEMAS) or prior_rng is None:
                raise NativeHistoryRejected("native history RNG reference is not versioned or anchored")
        else:
            if (type(row["rng_after"]) is not dict
                    or set(row["rng_after"]) != {"$tuple"}
                    or type(row["rng_after"]["$tuple"]) is not list):
                raise NativeHistoryRejected("native history RNG cursor has an invalid shape")
            prior_rng = row["rng_after"]
        state = _apply(state, row["changes"])
        _validate_recipient_state(state, participant_ids)
        if hashlib.sha256(_canonical(state)).hexdigest() != row["state_sha256"]:
            raise NativeHistoryRejected("native history reconstructed state digest differs")
        events = row["events"]
        if (type(events) is not dict or set(events) != {
                "action_ids", "effect_ids", "actions", "effects", "starts", "participants"}
                or type(events["action_ids"]) is not list
                or type(events["effect_ids"]) is not list):
            raise NativeHistoryRejected("native history event/effect batch is malformed")
        if len(events["action_ids"]) != len(set(events["action_ids"])):
            raise NativeHistoryRejected("native history repeats an Action identity")
        if len(events["effect_ids"]) != len(set(_canonical(item) for item in events["effect_ids"])):
            raise NativeHistoryRejected("native history repeats an Effect identity")
        if (any(type(action_id) is not str or not action_id
                for action_id in events["action_ids"])
                or set(events["action_ids"]) & seen_actions):
            raise NativeHistoryRejected("native history Action IDs are malformed or repeated")
        seen_actions.update(events["action_ids"])
        if type(events["actions"]) is not dict or set(events["actions"]) != set(events["action_ids"]):
            raise NativeHistoryRejected("native history Action facts disagree with receipt identities")
        effect_map = (events["effects"].get("$map")
                      if type(events["effects"]) is dict else None)
        if not ((events["effects"] == {} and not events["effect_ids"])
                or type(effect_map) is list):
            raise NativeHistoryRejected("native history Effect facts are not a closed mapping")
        fact_effect_ids = {_canonical(key) for key, _value in (effect_map or ())
                           if type(key) is dict and key.get("$record") == "action_evaluation.EffectIdentity"}
        if (fact_effect_ids != {_canonical(item) for item in events["effect_ids"]}
                or fact_effect_ids & seen_effects):
            raise NativeHistoryRejected("native history Effect facts disagree with receipt identities")
        seen_effects.update(fact_effect_ids)
        if has_receipt_facts:
            if type(row["receipt_facts_available"]) is not bool:
                raise NativeHistoryRejected("receipt-fact availability is malformed")
            receipt_completeness.append(row["receipt_facts_available"])
            for field in ("notification_intents", "disarm_landings"):
                facts = row[field]
                if type(facts) is not dict or set(facts) != {"$tuple"} or type(facts["$tuple"]) is not list:
                    raise NativeHistoryRejected("native committed receipt facts are malformed")
                _validate_plain_record(facts)
                if not row["receipt_facts_available"] and facts["$tuple"]:
                    raise NativeHistoryRejected("legacy receipt facts were inferred during upgrade")
            for intent in row["notification_intents"]["$tuple"]:
                fields_value = (intent.get("fields", {})
                                if type(intent) is dict else {})
                if (type(intent) is not dict
                        or intent.get("$record") != "observer_proposals.PostCommitNotificationIntent"
                        or set(fields_value) != {"source_action_id", "action_id", "topic", "after_commit"}
                        or fields_value.get("source_action_id") not in seen_actions
                        or fields_value.get("action_id") not in seen_actions
                        or type(fields_value.get("topic")) is not str
                        or not fields_value["topic"]
                        or fields_value.get("after_commit") is not True):
                    raise NativeHistoryRejected("post-commit notification references an unknown Action")
            for landing in row["disarm_landings"]["$tuple"]:
                if (type(landing) is not dict
                        or landing.get("$record") != "encounter_inspection.DisarmLandingReceipt"
                        or landing.get("fields", {}).get("boundary") != expected):
                    raise NativeHistoryRejected("Disarm landing receipt boundary or type differs")
                fields_value = landing["fields"]
                if (set(fields_value) != {"source_action_id", "target_id", "owner_id",
                                          "actor_id", "boundary", "origin_cell",
                                          "landing_cell", "margin", "maximum_landing_hexes",
                                          "position"}
                        or any(type(fields_value.get(key)) is not str or not fields_value[key]
                        for key in ("source_action_id", "target_id", "owner_id", "actor_id"))
                        or fields_value["source_action_id"] not in seen_actions
                        or any(type(fields_value.get(key)) is not int
                               for key in ("boundary", "margin", "maximum_landing_hexes"))
                        or fields_value["maximum_landing_hexes"] < 0
                        or any(type(fields_value.get(key)) is not dict
                               or set(fields_value[key]) != {"$tuple"}
                               or type(fields_value[key]["$tuple"]) is not list
                               or len(fields_value[key]["$tuple"]) != 2
                               or any(type(part) is not int
                                      for part in fields_value[key]["$tuple"])
                               for key in ("origin_cell", "landing_cell"))):
                    raise NativeHistoryRejected("Disarm landing receipt fields are malformed")
                for identity, expected_category in ((fields_value["target_id"], "weapon"),
                                                     (fields_value["owner_id"], "being"),
                                                     (fields_value["actor_id"], "being")):
                    target = state["entities"].get(identity)
                    if (type(target) is not dict
                            or target.get("$record") != "action_settlement.TargetCandidate"
                            or target.get("fields", {}).get("category") != expected_category):
                        raise NativeHistoryRejected("Disarm landing receipt has a dangling Entity reference")
                position = fields_value["position"]
                if (type(position) is not dict or set(position) != {"$tuple"}
                        or type(position["$tuple"]) is not list
                        or len(position["$tuple"]) != 3
                        or any(type(part) is not dict or set(part) != {"$number"}
                               for part in position["$tuple"])):
                    raise NativeHistoryRejected("Disarm landing position is malformed")
        covered = expected
    if (type(log["latest_boundary"]) is not int
            or not 0 <= log["latest_boundary"] <= MAX_BOUNDARIES
            or log["latest_boundary"] != covered):
        raise NativeHistoryRejected("native history latest boundary differs")
    if has_entity_context:
        _validate_entity_context(log["entity_context"], log["latest_boundary"], version)
    if version == SCHEMA and initial["initial_entities_available"]:
        context = log["entity_context"]
        if (not context["available"]
                or context["initial"] != initial["entities"]):
            raise NativeHistoryRejected(
                "initial Entity state differs from its EntityInspection baseline")
    if has_receipt_facts and log["receipt_facts_complete"] != all(receipt_completeness):
        raise NativeHistoryRejected("receipt-fact completeness marker disagrees with boundaries")
    if has_observer_knowledge:
        _validate_observer_knowledge(log["observer_knowledge"],
                                     log["latest_boundary"], initial, state)
    return True


def _validate_queue_projection(value):
    """Validate the portable initial scheduler snapshot used by schema `/9`."""
    _validate_plain_record(value)
    if (type(value) is not dict
            or value.get("$record") != "interval_staging.QueueProjection"
            or type(value.get("fields")) is not dict):
        record = value.get("$record") if type(value) is dict else type(value).__name__
        raise NativeHistoryRejected(
            f"initial scheduler projection type differs ({record!r})")
    fields_value = value["fields"]
    expected = {"pending", "finished", "cancelled", "event_registrations",
                "action_states", "choice_states", "reservations",
                "schedule_revision"}
    if set(fields_value) != expected:
        raise NativeHistoryRejected("initial scheduler projection fields differ")
    for name in ("pending", "finished", "cancelled", "event_registrations",
                 "reservations"):
        sequence = fields_value[name]
        if type(sequence) is not dict or set(sequence) != {"$tuple"} \
                or type(sequence["$tuple"]) is not list:
            raise NativeHistoryRejected("initial scheduler sequence is malformed")
    for name in ("pending", "finished", "cancelled"):
        rows = fields_value[name]["$tuple"]
        if (any(type(identity) is not str or not identity for identity in rows)
                or len(set(rows)) != len(rows)):
            raise NativeHistoryRejected("initial scheduler Action identities are malformed")
    for row in fields_value["event_registrations"]["$tuple"]:
        if (type(row) is not dict
                or row.get("$record") != "interval_staging.RegistrationIntent"
                or type(row.get("fields")) is not dict):
            raise NativeHistoryRejected("initial scheduler registration is malformed")
        registration = row["fields"]
        if (set(registration) != {"action", "choice_id", "accepted_packet", "metadata",
                                 "signature_from_final_native_declaration"}
                or type(registration["choice_id"]) is not str
                or not registration["choice_id"]
                or registration["signature_from_final_native_declaration"] is not True):
            raise NativeHistoryRejected("initial scheduler registration fields differ")
        for role_name, role in (("action", "event"),
                                ("accepted_packet", "accepted_packet")):
            reference = registration[role_name]
            if (type(reference) is not dict
                    or reference.get("$record") != "interval_staging.AuthorityReference"
                    or set(reference.get("fields", {})) != {"key", "role"}
                    or reference["fields"].get("role") != role
                    or reference["fields"].get("key") == ""):
                raise NativeHistoryRejected("initial scheduler registration reference differs")
    for name in ("action_states", "choice_states"):
        states = fields_value[name]
        if (type(states) is not dict
                or any(type(identity) is not str or not identity
                       or type(state) is not str or not state
                       for identity, state in states.items())):
            raise NativeHistoryRejected("initial scheduler state map is malformed")
    revision = fields_value["schedule_revision"]
    if type(revision) is not int or revision < 0:
        raise NativeHistoryRejected("initial scheduler revision is malformed")


def _validate_entity_context(context, latest_boundary, schema):
    expected_keys = ({"available", "initial", "changes"}
                     if schema == ENTITY_CONTEXT_SCHEMA else
                     {"available", "fatigue_available", "initial", "changes"})
    current_context_schemas = CURRENT_ENTITY_CONTEXT_SCHEMAS
    if (type(context) is not dict or set(context) != expected_keys
            or type(context["available"]) is not bool or type(context["changes"]) is not list
            or schema in current_context_schemas
            and type(context["fatigue_available"]) is not bool):
        raise NativeHistoryRejected("native EntityInspection history schema differs")
    if not context["available"]:
        if (context["initial"] is not None or context["changes"]
                or schema in current_context_schemas
                and context["fatigue_available"]):
            raise NativeHistoryRejected("legacy EntityInspection history marker is inconsistent")
        return
    if type(context["initial"]) is not dict:
        raise NativeHistoryRejected("native EntityInspection initial state is missing")
    _validate_plain_record(context["initial"])
    state = context["initial"]
    if schema in current_context_schemas and context["fatigue_available"]:
        _validate_fatigue_context_entities(state)
    previous = 0
    for row in context["changes"]:
        if (type(row) is not dict or set(row) != {"boundary", "changes", "state_sha256"}
                or type(row["boundary"]) is not int
                or not previous < row["boundary"] <= latest_boundary
                or type(row["changes"]) is not list or not row["changes"]
                or type(row["state_sha256"]) is not str):
            raise NativeHistoryRejected("native EntityInspection change chronology differs")
        state = _apply(state, row["changes"])
        _validate_plain_record(state)
        if schema in current_context_schemas and context["fatigue_available"]:
            _validate_fatigue_context_entities(state)
        if hashlib.sha256(_canonical(state)).hexdigest() != row["state_sha256"]:
            raise NativeHistoryRejected("native EntityInspection state digest differs")
        previous = row["boundary"]


def _validate_observer_knowledge(context, latest_boundary, initial, state):
    if (type(context) is not dict
            or set(context) != {"available", "initial", "changes"}
            or type(context["available"]) is not bool
            or type(context["changes"]) is not list):
        raise NativeHistoryRejected("native observer-knowledge context schema differs")
    if not context["available"]:
        if context["initial"] is not None or context["changes"]:
            raise NativeHistoryRejected("legacy observer-knowledge availability is inconsistent")
        return
    initial_knowledge = context["initial"]
    if type(initial_knowledge) is not dict:
        raise NativeHistoryRejected("native observer-knowledge initial state is missing")
    _validate_plain_record(initial_knowledge)
    participants = set(initial["participants"]["$tuple"])
    def validate_state(value, boundary):
        if type(value) is not dict:
            raise NativeHistoryRejected("native observer-knowledge state is malformed")
        for observer_id, entities in value.items():
            if (type(observer_id) is not str or observer_id not in participants
                    or type(entities) is not dict):
                raise NativeHistoryRejected("native observer-knowledge owner is invalid")
            for entity_id, evidence in entities.items():
                if type(entity_id) is not str or type(evidence) is not dict:
                    raise NativeHistoryRejected("native observer evidence row is malformed")
                _validate_plain_record(evidence)
                fields_value = evidence.get("fields", {})
                if (evidence.get("$record") != "arena_perception.ArenaPerceptionEvidence"
                        or fields_value.get("observer_id") != observer_id
                        or fields_value.get("entity_id") != entity_id
                        or any(type(fields_value.get(key)) is not str
                               or not fields_value[key]
                               for key in ("basis", "category", "name", "present_state",
                                           "type_key"))
                        or fields_value.get("basis") !=
                            "arena.r65.initial_unobstructed_perception"
                        or type(fields_value.get("boundary")) is not int
                        or fields_value["boundary"] < 0
                        or type(fields_value.get("time")) is not dict
                        or set(fields_value["time"]) != {"$number"}
                        or type(fields_value["time"].get("$number")) is not str
                        or type(fields_value.get("currently_observable")) is not bool
                        or type(fields_value.get("visibility_boundary")) is not int
                        or not 0 <= fields_value["visibility_boundary"] <= boundary
                        or fields_value["boundary"] > fields_value["visibility_boundary"]
                        or fields_value.get("category") not in ("being", "object")
                        or fields_value.get("present_state") not in
                            ("present", "ground", "carried", "unplaced")
                        or fields_value.get("position") is not None
                            and (type(fields_value["position"]) is not dict
                                 or fields_value["position"].get("$record") !=
                                    "spatial.state.CartesianPosition")
                        or fields_value.get("category") == "being"
                            and (fields_value.get("owner_id") is not None
                                 or fields_value.get("equipment_status") is not None)
                        or (fields_value.get("owner_id") is not None)
                            != (fields_value.get("equipment_status") is not None)):
                    raise NativeHistoryRejected("native observer evidence owner, time, or category differs")
                if entity_id not in state["entities"]:
                    raise NativeHistoryRejected("native observer evidence references an unknown Entity")
                if fields_value.get("owner_id") is not None:
                    if (type(fields_value["owner_id"]) is not str
                            or fields_value["owner_id"] not in participants):
                        raise NativeHistoryRejected(
                            "native observer evidence has an invalid Object owner")

    validate_state(initial_knowledge, 0)
    current = initial_knowledge
    previous = 0
    for row in context["changes"]:
        if (type(row) is not dict or set(row) != {"boundary", "changes", "state_sha256"}
                or type(row["boundary"]) is not int
                or not previous < row["boundary"] <= latest_boundary
                or type(row["changes"]) is not list or not row["changes"]
                or type(row["state_sha256"]) is not str):
            raise NativeHistoryRejected("native observer-knowledge chronology differs")
        current = _apply(current, row["changes"])
        validate_state(current, row["boundary"])
        if hashlib.sha256(_canonical(current)).hexdigest() != row["state_sha256"]:
            raise NativeHistoryRejected("native observer-knowledge state digest differs")
        previous = row["boundary"]


def _validate_fatigue_context_entities(entities):
    for identity, entity in entities.items():
        if (type(entity) is not dict
                or entity.get("$record") != "encounter_inspection.EntityInspection"):
            continue
        fields_value = entity.get("fields")
        if type(fields_value) is not dict or fields_value.get("category") != "being":
            continue
        pre_action = fields_value.get("pre_action")
        fatigue = pre_action.get("physical_fatigue") if type(pre_action) is dict else None
        physiology = pre_action.get("physiology") if type(pre_action) is dict else None
        if (type(fatigue) is not dict
                or set(fatigue) != {"b", "check_modifier", "physiology_id", "q"}
                or any(type(fatigue.get(key)) is not dict
                       or set(fatigue[key]) != {"$number"}
                       or type(fatigue[key]["$number"]) is not str
                       for key in ("b", "q"))
                or type(fatigue["check_modifier"]) is not int
                or fatigue["physiology_id"] is not None
                    and type(fatigue["physiology_id"]) is not str
                or type(physiology) is not dict
                or set(physiology) not in (set(), {"ordinary", "running"})):
            raise NativeHistoryRejected("native fatigue/physiology boundary facts are malformed")
        for mode, resolved in physiology.items():
            if (type(resolved) is not dict
                    or not {"identifier", "lineage", "mode", "profile", "version_hash"}
                    <= set(resolved)
                    or resolved.get("mode") != mode
                    or type(resolved.get("version_hash")) is not str
                    or len(resolved["version_hash"]) != 64
                    or any(char not in "0123456789abcdef"
                           for char in resolved["version_hash"])):
                raise NativeHistoryRejected("native resolved physiology boundary facts are malformed")


def state_at(log, boundary):
    """Reconstruct the historical property projection without Action resolution."""
    validate(log)
    if type(boundary) is not int or not 0 <= boundary <= log["latest_boundary"]:
        raise NativeHistoryRejected("requested native boundary is not committed")
    initial = log["initial"]
    if boundary == 0:
        result = json.loads(_canonical(_initial_state(initial)).decode("ascii"))
        if not initial.get("initial_entities_available", False):
            result["entities"] = None
        return result
    state = _initial_state(initial)
    for row in log["boundaries"]:
        if row.get("kind") == "quiet_span":
            if row["from_boundary"] <= boundary <= row["to_boundary"]:
                return _apply_quiet_span(state, row, boundary)
            state = _apply_quiet_span(state, row, row["to_boundary"])
        else:
            state = _apply(state, row["changes"])
            if row["boundary"] == boundary:
                return state
    return state


def entity_context_at(log, boundary):
    """Return committed EntityInspection facts at a boundary without re-resolving Actions.

    Legacy history remains readable but returns ``None`` because its schema did
    not record these context projections. Current histories store only changed
    context, with the initial context retained once.
    """
    validate(log)
    if type(boundary) is not int or not 0 <= boundary <= log["latest_boundary"]:
        raise NativeHistoryRejected("requested native boundary is not committed")
    context = log.get("entity_context", _unavailable_entity_context())
    if not context["available"]:
        return None
    if boundary == 0:
        if not log["initial"].get("initial_entities_available", False):
            return None
        return json.loads(_canonical(context["initial"]).decode("ascii"))
    state = json.loads(_canonical(context["initial"]).decode("ascii"))
    for row in context["changes"]:
        if row["boundary"] > boundary:
            break
        state = _apply(state, row["changes"])
        if hashlib.sha256(_canonical(state)).hexdigest() != row["state_sha256"]:
            raise NativeHistoryRejected("native EntityInspection query digest differs")
    return state


def fatigue_context_at(log, boundary):
    """Return receipt-backed Q/B and resolved physiology, or None if not recorded."""
    validate(log)
    context = log.get("entity_context", _unavailable_entity_context())
    if not context["available"] or not context.get("fatigue_available", False):
        return None
    entities = entity_context_at(log, boundary)
    result = {}
    for identity, entity in entities.items():
        fields_value = entity.get("fields", {}) if type(entity) is dict else {}
        if fields_value.get("category") == "being":
            pre_action = fields_value["pre_action"]
            result[identity] = {
                "physical_fatigue": pre_action["physical_fatigue"],
                "physiology": pre_action["physiology"],
            }
    return result


class NativeHistoryQuery:
    """Validated, detached query session for repeated history reads.

    The input is validated and copied once. State queries in increasing time
    apply only the intervening deltas; no per-boundary state snapshots are
    added to the persisted artifact. Returned values are detached JSON data.
    """

    def __init__(self, log):
        self._log = decode(encode(log))
        self._latest = self._log["latest_boundary"]
        self._segments = []
        self._segment_starts = []
        self._segment_ends = []
        self._segment_rng = []
        cursor = self._log["initial"].get("rng_before_first_commit")
        for row in self._log["boundaries"]:
            if row.get("kind") == "quiet_span":
                start, end = row["from_boundary"], row["to_boundary"]
            else:
                start = end = row["boundary"]
                cursor = cursor if row["rng_after"] == SAME_RNG else row["rng_after"]
            self._segments.append(row)
            self._segment_starts.append(start)
            self._segment_ends.append(end)
            self._segment_rng.append(cursor)
        self._actions_boundary = 0
        self._action_ids = []
        self._seen_actions = set()
        self._effect_ids = []
        self._seen_effects = set()
        self._actions = {}
        self._effect_rows = {}
        self._state_boundary = 0
        self._state = _initial_state(self._log["initial"])
        context = self._log.get("entity_context", _unavailable_entity_context())
        self._context_available = context["available"]
        self._fatigue_available = context.get("fatigue_available", False)
        self._context_boundary = 0
        self._context = (json.loads(_canonical(context["initial"]).decode("ascii"))
                         if self._context_available else None)
        self._context_changes = {row["boundary"]: row
                                 for row in context["changes"]}
        self._has_receipt_facts = self._log.get("schema") in RECEIPT_FACT_SCHEMAS
        self._initial_entities_available = bool(
            self._log["initial"].get("initial_entities_available", False))
        self._initial_schedule_available = bool(
            self._log["initial"].get("initial_schedule_available", False))
        knowledge = self._log.get("observer_knowledge",
                                  _unavailable_observer_knowledge())
        self._knowledge_available = knowledge["available"]
        self._knowledge_boundary = 0
        self._knowledge = (json.loads(_canonical(knowledge["initial"]).decode("ascii"))
                           if self._knowledge_available else None)
        self._knowledge_changes = {row["boundary"]: row
                                   for row in knowledge["changes"]}

    def _boundary(self, boundary):
        if type(boundary) is not int or not 0 <= boundary <= self._latest:
            raise NativeHistoryRejected("requested native boundary is not committed")

    def _segment(self, boundary):
        index = bisect_right(self._segment_starts, boundary) - 1
        if index < 0 or boundary > self._segment_ends[index]:
            raise NativeHistoryRejected("requested native boundary is not committed")
        return index, self._segments[index]

    @staticmethod
    def _copy(value):
        return json.loads(_canonical(value).decode("ascii"))

    def state_at(self, boundary):
        self._boundary(boundary)
        if boundary < self._state_boundary:
            state = _initial_state(self._log["initial"])
            first = 1
        else:
            state = self._state
            first = self._state_boundary + 1
        for current in range(first, boundary + 1):
            _index, row = self._segment(current)
            if row.get("kind") == "quiet_span":
                state = _apply_quiet_span(state, row, current)
            else:
                state = _apply(state, row["changes"])
            if current == boundary or row.get("kind") == "quiet_span":
                if (row.get("kind") != "quiet_span" and current == boundary
                        and hashlib.sha256(_canonical(state)).hexdigest() != row["state_sha256"]):
                    raise NativeHistoryRejected("native history query state digest differs")
        if boundary >= self._state_boundary:
            self._state = state
            self._state_boundary = boundary
        result = self._copy(state)
        if boundary == 0 and not self._initial_entities_available:
            result["entities"] = None
        if not self._initial_schedule_available:
            result["initial_schedule"] = None
            if boundary == 0:
                result["schedule"] = None
        return result

    def target_at(self, target_id, boundary):
        """Return one recorded TargetCandidate at a committed boundary.

        Boundary zero carries initial EntityInspection facts, not a committed
        TargetCandidate. Do not expose that different record type through the
        Target-history API.
        """
        self._boundary(boundary)
        if type(target_id) is not str or not target_id:
            raise NativeHistoryRejected("Target history requires a stable identity")
        entities = self.state_at(boundary)["entities"]
        if type(entities) is not dict:
            raise NativeHistoryRejected(
                "initial authoritative Entity state is unavailable")
        target = entities.get(target_id)
        if target is None:
            raise NativeHistoryRejected("requested Target is absent at this boundary")
        if (type(target) is not dict
                or target.get("$record") != "action_settlement.TargetCandidate"):
            raise NativeHistoryRejected(
                "requested Target has no committed TargetCandidate at this boundary")
        return target

    def projectile_state_at(self, object_id, boundary):
        """Return the recorded trajectory state for one Object at a boundary.

        Absence means no projectile state was recorded for that Object at the
        selected boundary; the query never infers flight from current custody
        or position.
        """
        self._boundary(boundary)
        if type(object_id) is not str or not object_id:
            raise NativeHistoryRejected("projectile history requires a stable Object identity")
        states = self.state_at(boundary)["projectile_states"]
        if type(states) is not dict:
            raise NativeHistoryRejected("native projectile-state projection is malformed")
        return states.get(object_id)

    def objective_at(self, boundary):
        """Return detached committed objective-reality inspection facts."""
        self._boundary(boundary)
        return self._copy(self.state_at(boundary)["objective"])

    def objective_use_at(self, boundary):
        """Return detached committed objective-fact use/cause rows."""
        self._boundary(boundary)
        return self._copy(self.state_at(boundary)["objective_use"])

    def schedule_at(self, boundary):
        """Return the detached committed native queue and Choice projection."""
        self._boundary(boundary)
        if boundary == 0 and not self._initial_schedule_available:
            return None
        return self._copy(self.state_at(boundary)["schedule"])

    def action_state_at(self, action_id, boundary):
        """Return a registered Action's status, or ``None`` if not present."""
        if type(action_id) is not str or not action_id:
            raise NativeHistoryRejected("Action state requires a stable identity")
        schedule = self.schedule_at(boundary)
        if schedule is None:
            return None
        fields_value = schedule.get("fields", {})
        states = fields_value.get("action_states", {})
        if type(states) is not dict:
            raise NativeHistoryRejected("native schedule Action states are malformed")
        return states.get(action_id)

    def choice_state_at(self, choice_id, boundary):
        """Return a retained Choice status, or ``None`` if it is not present."""
        if type(choice_id) is not str or not choice_id:
            raise NativeHistoryRejected("Choice state requires a stable identity")
        schedule = self.schedule_at(boundary)
        if schedule is None:
            return None
        fields_value = schedule.get("fields", {})
        states = fields_value.get("choice_states", {})
        if type(states) is not dict:
            raise NativeHistoryRejected("native schedule Choice states are malformed")
        return states.get(choice_id)

    def target_history_at(self, target_id, boundary=None):
        """Return ordered TargetCandidate facts through a checked boundary."""
        if boundary is None:
            boundary = self._latest
        self._boundary(boundary)
        if type(target_id) is not str or not target_id:
            raise NativeHistoryRejected("Target history requires a stable identity")
        rows = []
        for current in range(1, boundary + 1):
            state = self.state_at(current)
            target = state["entities"].get(target_id)
            if target is not None:
                rows.append({"boundary": current, "state": target})
        if not rows:
            raise NativeHistoryRejected("requested Target has no committed history")
        return rows

    def events_at(self, boundary):
        self._boundary(boundary)
        if boundary == 0:
            return self._copy({"action_ids": [], "effect_ids": [], "actions": {},
                               "effects": {}, "starts": {"$tuple": []},
                               "participants": self._log["initial"]["participants"]})
        _index, row = self._segment(boundary)
        if row.get("kind") == "quiet_span":
            events = {"action_ids": [], "effect_ids": [], "actions": {},
                      "effects": {}, "starts": row["quiet_events"]["starts"],
                      "participants": row["quiet_events"]["participants"]}
        else:
            events = row["events"]
        return self._copy(events)

    def timeline_at(self, boundary=None):
        """Return the committed native timeline through a boundary.

        Quiet spans are expanded only in this detached query result, never in
        the stored history or the validated query index.
        """
        if boundary is None:
            boundary = self._latest
        self._boundary(boundary)
        rows = []
        for row in self._segments:
            start_boundary = (row["from_boundary"]
                              if row.get("kind") == "quiet_span"
                              else row["boundary"])
            if start_boundary > boundary:
                break
            end_boundary = min(row.get("to_boundary", start_boundary), boundary)
            for current in range(start_boundary, end_boundary + 1):
                events = self.events_at(current)
                if row.get("kind") == "quiet_span":
                    start = _plain(_number_value(row["start"])
                                   + (current-start_boundary)
                                   * _number_value(row["step"]))
                else:
                    start = row["start"]
                rows.append({"$record": "encounter_inspection.BoundaryInspection",
                    "fields": {
                        "encounter_id": self._log["initial"]["encounter_id"],
                        "boundary": current,
                        "start": start,
                        "action_ids": {"$tuple": events["action_ids"]},
                        "effect_ids": {"$tuple": events["effect_ids"]},
                        "start_fences": events["starts"],
                    }})
        return {"$tuple": rows}

    def receipt_facts_at(self, boundary):
        """Return committed notification and Disarm landing facts, if retained."""
        self._boundary(boundary)
        if not self._has_receipt_facts:
            return None
        if boundary == 0:
            return {"notification_intents": {"$tuple": []},
                    "disarm_landings": {"$tuple": []}}
        _index, row = self._segment(boundary)
        if not row.get("receipt_facts_available", False):
            return None
        if row.get("kind") == "quiet_span":
            facts = {"notification_intents": {"$tuple": []},
                     "disarm_landings": {"$tuple": []}}
        else:
            facts = {"notification_intents": row["notification_intents"],
                     "disarm_landings": row["disarm_landings"]}
        return self._copy(facts)

    def boundary_facts_at(self, boundary):
        """Reconstruct the complete portable fact row for one committed cut.

        This is the graph-independent counterpart to the fields collected by
        ``_boundary_payload`` during capture. It contains only stable recorded
        facts; process-local Target/Action anchors and live runtime objects are
        deliberately absent. Legacy history returns ``None`` for families it
        did not record rather than deriving them from a later state.
        """
        self._boundary(boundary)
        state = self.state_at(boundary)
        events = self.events_at(boundary)
        receipt_facts = self.receipt_facts_at(boundary)
        if boundary == 0:
            start = self._log["initial"]["start"]
            end = state["time"]
        else:
            _index, row = self._segment(boundary)
            if row.get("kind") == "quiet_span":
                start = _plain(
                    _number_value(row["start"])
                    + (boundary - row["from_boundary"])
                    * _number_value(row["step"]))
            else:
                start = row["start"]
            end = state["time"]
        entities = self.entity_context_at(boundary)
        candidates = state["entities"]
        target_states = ({
            identity: value for identity, value in candidates.items()
            if type(value) is dict
            and value.get("$record") == "action_settlement.TargetCandidate"
        } if type(candidates) is dict else {})
        rng_after = (None if boundary == 0
                     and self._log["initial"].get("rng_before_first_commit") is None
                     else self.rng_state_at(boundary))
        return self._copy({
            "boundary": boundary,
            "start": start,
            "end": end,
            "action_ids": events["action_ids"],
            "effect_ids": events["effect_ids"],
            "notification_intents": (None if receipt_facts is None else
                                      receipt_facts["notification_intents"]),
            "disarm_landings": (None if receipt_facts is None else
                                receipt_facts["disarm_landings"]),
            "actions": events["actions"],
            "effects": events["effects"],
            "target_states": target_states,
            "entity_context": entities,
            "objective": state["objective"],
            "objective_use": state["objective_use"],
            "recipients": state["recipients"],
            "schedule": state["schedule"],
            "starts": events["starts"],
            "participants": events["participants"],
            "projectile_states": state["projectile_states"],
            "rng_after": rng_after,
            "observer_knowledge": self.observer_knowledge_at(boundary),
            "fatigue_context": self.fatigue_context_at(boundary),
        })

    def disarm_landings_at(self, boundary):
        facts = self.receipt_facts_at(boundary)
        return None if facts is None else facts["disarm_landings"]

    def notification_intents_at(self, boundary):
        facts = self.receipt_facts_at(boundary)
        return None if facts is None else facts["notification_intents"]

    def committed_actions_at(self, boundary):
        """Return cumulative committed Action/Event/Effect facts through a boundary.

        This is a historical read model built only from committed event rows;
        it never resolves an Action or consults the current Encounter graph.
        Pending declarations remain part of the resumable snapshot, not this
        committed-history view.
        """
        self._boundary(boundary)
        if boundary < self._actions_boundary:
            self._actions_boundary = 0
            self._action_ids = []
            self._seen_actions = set()
            self._effect_ids = []
            self._seen_effects = set()
            self._actions = {}
            self._effect_rows = {}
        for row in self._segments:
            end = row.get("to_boundary", row.get("boundary"))
            if end <= self._actions_boundary:
                continue
            if end > boundary:
                break
            if row.get("kind") == "quiet_span":
                self._actions_boundary = end
                continue
            if row["boundary"] > boundary:
                break
            batch = row["events"]
            for identity in batch["action_ids"]:
                if identity not in self._seen_actions:
                    self._seen_actions.add(identity)
                    self._action_ids.append(identity)
            for identity in batch["effect_ids"]:
                key = _canonical(identity)
                if key not in self._seen_effects:
                    self._seen_effects.add(key)
                    self._effect_ids.append(identity)
            self._actions.update(batch["actions"])
            encoded_effects = batch["effects"]
            if type(encoded_effects) is dict and set(encoded_effects) == {"$map"}:
                rows = encoded_effects["$map"]
            else:
                rows = [[key, value] for key, value in encoded_effects.items()]
            for key, value in rows:
                self._effect_rows[_canonical(key)] = [key, value]
            self._actions_boundary = row["boundary"]
        self._actions_boundary = boundary
        effect_rows = [self._effect_rows[key] for key in sorted(self._effect_rows)]
        effects = {"$map": effect_rows} if effect_rows else {}
        return self._copy({"action_ids": self._action_ids,
                           "effect_ids": self._effect_ids,
                           "actions": self._actions, "effects": effects})

    def committed_action_at(self, action_id, boundary):
        """Return the latest committed Action fact through a boundary."""
        if type(action_id) is not str or not action_id:
            raise NativeHistoryRejected("Action history requires a stable identity")
        return self.committed_actions_at(boundary)["actions"].get(action_id)

    def rng_state_at(self, boundary):
        self._boundary(boundary)
        if boundary == 0:
            cursor = self._log["initial"].get("rng_before_first_commit")
            if cursor is None:
                raise NativeHistoryRejected(
                    "initial RNG cursor is not recorded in this native history")
            return self._copy(cursor)
        index, _row = self._segment(boundary)
        cursor = self._segment_rng[index]
        if cursor is None:
            raise NativeHistoryRejected("native RNG state is absent")
        return self._copy(cursor)

    def entity_context_at(self, boundary):
        self._boundary(boundary)
        if (not self._context_available or
                boundary == 0 and not self._initial_entities_available):
            return None
        if boundary < self._context_boundary:
            context = json.loads(_canonical(
                self._log["entity_context"]["initial"]).decode("ascii"))
            first = 1
        else:
            context = self._context
            first = self._context_boundary + 1
        for current in range(first, boundary + 1):
            row = self._context_changes.get(current)
            if row is not None:
                context = _apply(context, row["changes"])
                if hashlib.sha256(_canonical(context)).hexdigest() != row["state_sha256"]:
                    raise NativeHistoryRejected("native EntityInspection query digest differs")
        if boundary >= self._context_boundary:
            self._context = context
            self._context_boundary = boundary
        return self._copy(context)

    def entity_at(self, entity_id, boundary):
        """Return one committed EntityInspection projection, or ``None``.

        This is deliberately an inspection projection, not a claim that every
        mutable runtime field is represented in native history. Older history
        schemas return ``None`` for the whole family instead of deriving past
        values from the current graph.
        """
        self._boundary(boundary)
        if type(entity_id) is not str or not entity_id:
            raise NativeHistoryRejected("entity history requires a stable identity")
        context = self.entity_context_at(boundary)
        if context is None:
            return None
        return context.get(entity_id)

    def entity_history_at(self, entity_id, boundary=None):
        """Return committed per-Entity inspection projections through a boundary.

        Every row is sourced from the validated sparse EntityInspection stream.
        Entities absent at a boundary have no row; unavailable legacy history
        returns ``None`` rather than an empty history that could be mistaken
        for a recorded absence.
        """
        if boundary is None:
            boundary = self._latest
        self._boundary(boundary)
        if type(entity_id) is not str or not entity_id:
            raise NativeHistoryRejected("entity history requires a stable identity")
        if not self._context_available:
            return None
        rows = []
        for current in range(boundary + 1):
            value = self.entity_at(entity_id, current)
            if value is not None:
                rows.append({"boundary": current, "entity": value})
        return rows

    def fatigue_context_at(self, boundary):
        self._boundary(boundary)
        if not self._context_available or not self._fatigue_available:
            return None
        entities = self.entity_context_at(boundary)
        return {identity: {
            "physical_fatigue": row["fields"]["pre_action"]["physical_fatigue"],
            "physiology": row["fields"]["pre_action"]["physiology"],
        } for identity, row in entities.items()
            if row.get("$record") == "encounter_inspection.EntityInspection"
            and row["fields"].get("category") == "being"}

    def observer_facts_at(self, boundary, observer_id):
        """Return only recipient facts explicitly owned by one observer."""
        self._boundary(boundary)
        if type(observer_id) is not str or not observer_id:
            raise NativeHistoryRejected("observer history requires a stable observer ID")
        recipients = self.state_at(boundary)["recipients"]
        if recipients == {}:
            return []
        if type(recipients) is not list:
            raise NativeHistoryRejected("native recipient history has an invalid shape")
        return self._copy([row for row in recipients
                           if type(row) is dict and row.get("owner_id") == observer_id])

    def observer_knowledge_at(self, boundary, observer_id=None):
        """Return only recorded passive evidence owned by the requested observer.

        Older schemas return ``None`` because they did not retain this ledger
        history; current Saves do not reconstruct evidence from objective state.
        """
        self._boundary(boundary)
        if observer_id is not None and (type(observer_id) is not str or not observer_id):
            raise NativeHistoryRejected("observer history requires a stable observer ID")
        if not self._knowledge_available:
            return None
        if boundary < self._knowledge_boundary:
            context = json.loads(_canonical(
                self._log["observer_knowledge"]["initial"]).decode("ascii"))
            first = 1
        else:
            context = self._knowledge
            first = self._knowledge_boundary + 1
        for current in range(first, boundary + 1):
            row = self._knowledge_changes.get(current)
            if row is not None:
                context = _apply(context, row["changes"])
                if hashlib.sha256(_canonical(context)).hexdigest() != row["state_sha256"]:
                    raise NativeHistoryRejected("native observer-knowledge digest differs")
        if boundary >= self._knowledge_boundary:
            self._knowledge = context
            self._knowledge_boundary = boundary
        result = self._copy(context)
        return result if observer_id is None else result.get(observer_id, {})


def restore_compacted_entity_context(world, histories):
    """Rebuild receipt EntityInspection maps from their authenticated history.

    Only the repeated display projection is omitted from the graph. The
    strict native-history validator authenticates each typed fact and its
    sparse before/after chronology; owner IDs and the complete receipt chain
    are checked before the historical inspection map is installed.
    """
    from encounter import Encounter
    from encounter_inspection import EntityInspection
    from being import BeingInstance
    from object import ObjectInstance
    from weapon import WeaponInstance
    from armor import ArmorInstance
    from statistical_group import StatisticalGroup
    from types import MappingProxyType
    from action_evaluation import freeze

    if type(histories) is not dict:
        raise NativeHistoryRejected(
            "compacted EntityInspection restoration requires Encounter histories")
    encounters = {row.id: row for row in world.event_history.values()
                  if type(row) is Encounter}
    if set(histories) != set(encounters):
        raise NativeHistoryRejected(
            "compacted EntityInspection histories do not cover the Universe Encounters")
    registry = world.object_registry.object_instances
    supported = {
        "being": (BeingInstance,),
        "object": (ObjectInstance, StatisticalGroup),
        "weapon": (WeaponInstance,),
        "armor": (ArmorInstance,),
        "group": (StatisticalGroup,),
    }
    for encounter_id in sorted(encounters):
        encounter = encounters[encounter_id]
        log = histories[encounter_id]
        receipts = encounter.__dict__.get("_atomic_interval_history")
        if log is None:
            if receipts or encounter.time != encounter.start_time:
                raise NativeHistoryRejected(
                    "compacted history-free Encounter has committed boundaries")
            continue
        upgraded = upgrade(log)
        validate(upgraded)
        if (upgraded["schema"] != SCHEMA
                or upgraded["initial"]["encounter_id"] != encounter_id
                or upgraded["latest_boundary"] != encounter.last_processed_boundary
                or type(receipts) is not list
                or [row.boundary for row in receipts]
                    != list(range(1, upgraded["latest_boundary"] + 1))):
            raise NativeHistoryRejected(
                "compacted EntityInspection history differs from its receipt chain")
        query = NativeHistoryQuery(upgraded)
        if query.entity_context_at(upgraded["latest_boundary"]) is None:
            raise NativeHistoryRejected(
                "compacted EntityInspection facts are unavailable")
        for receipt in receipts:
            meta = receipt.inspection
            if type(meta.entities) not in (dict, MappingProxyType) or meta.entities:
                raise NativeHistoryRejected(
                    "compacted receipt contains an unexpected EntityInspection graph")
            encoded = query.entity_context_at(receipt.boundary)
            if type(encoded) is not dict:
                raise NativeHistoryRejected(
                    "compacted EntityInspection facts are unavailable")
            entities = {}
            for identity, value in encoded.items():
                row = _materialize_plain(value)
                if type(identity) is not str or not identity:
                    raise NativeHistoryRejected(
                        "compacted EntityInspection identity is malformed")
                if type(row) is not EntityInspection:
                    raise NativeHistoryRejected(
                        "compacted EntityInspection record type is not admitted")
                if identity not in registry:
                    raise NativeHistoryRejected(
                        "compacted EntityInspection owner is not in the native registry")
                if type(registry[identity]) not in supported.get(row.category, ()):
                    raise NativeHistoryRejected(
                        "compacted EntityInspection category differs from its native owner")
                if type(row.obj_type) is not str or type(row.pre_action) is not dict:
                    raise NativeHistoryRejected(
                        "compacted EntityInspection field shape is malformed")
                object.__setattr__(row, "pre_action", freeze(row.pre_action))
                entities[identity] = row
            if len(entities) != len(encoded):
                raise NativeHistoryRejected(
                    "compacted EntityInspection identities are duplicated")
            object.__setattr__(meta, "entities", MappingProxyType(entities))
    return True


def restore_compacted_publication_facts(world, histories):
    """Rebuild repeated PublishedInterval facts from the validated history.

    The native history is the independently checksummed source for each
    boundary's Event/Effect identities, RNG cursor and notification intents.
    The graph keeps the receipt envelope and committed inspection shell, then
    restores these fields before receipt projections and publication anchors
    are validated.
    """
    from atomic_publication import PublishedInterval
    from encounter import Encounter
    if type(histories) is not dict:
        raise NativeHistoryRejected(
            "compacted publication restoration requires Encounter histories")
    encounters = {row.id: row for row in world.event_history.values()
                  if type(row) is Encounter}
    if set(histories) != set(encounters):
        raise NativeHistoryRejected(
            "compacted publication histories do not cover the Universe Encounters")
    for encounter_id in sorted(encounters):
        encounter = encounters[encounter_id]
        log = histories[encounter_id]
        receipts = encounter.__dict__.get("_atomic_interval_history")
        if log is None:
            if receipts or encounter.time != encounter.start_time:
                raise NativeHistoryRejected(
                    "compacted history-free Encounter has committed boundaries")
            continue
        upgraded = upgrade(log)
        validate(upgraded)
        if (upgraded["schema"] != SCHEMA
                or upgraded["initial"]["encounter_id"] != encounter_id
                or upgraded["latest_boundary"] != encounter.last_processed_boundary
                or type(receipts) is not list
                or [row.boundary for row in receipts]
                    != list(range(1, upgraded["latest_boundary"] + 1))):
            raise NativeHistoryRejected(
                "compacted publication facts differ from their boundary history")
        query = NativeHistoryQuery(upgraded)
        restored = []
        for shell in receipts:
            if (type(shell) is not PublishedInterval
                    or shell.encounter_id != encounter_id
                    or shell.action_ids != () or shell.effect_ids != ()
                    or shell.rng_state != ()
                    or shell.notification_intents != ()
                    or shell.committed is not True):
                raise NativeHistoryRejected(
                    "compacted publication receipt shell is malformed")
            facts = query.boundary_facts_at(shell.boundary)
            if (facts is None or facts.get("notification_intents") is None
                    or type(facts.get("action_ids")) is not list
                    or type(facts.get("effect_ids")) is not list):
                raise NativeHistoryRejected(
                    "committed publication facts are unavailable")
            action_ids = tuple(facts["action_ids"])
            effect_ids = tuple(_materialize_plain(facts["effect_ids"]))
            rng_record = query.rng_state_at(shell.boundary)
            rng_state = None if rng_record is None else _decode_rng_cursor(rng_record)
            notification_intents = _materialize_plain(
                facts["notification_intents"])
            if (any(type(identity) is not str or not identity
                    for identity in action_ids)
                    or type(rng_state) is not tuple
                    or type(notification_intents) is not tuple):
                raise NativeHistoryRejected(
                    "reconstructed publication facts have invalid shapes")
            restored.append(PublishedInterval(
                encounter_id, shell.boundary, action_ids, effect_ids, rng_state,
                notification_intents, shell.committed, shell.inspection))
        encounter.__dict__["_atomic_interval_history"] = restored
    return True


def restore_compacted_disarm_landings(world, histories):
    """Rebuild Encounter-level Disarm landing indexes from exact boundary facts."""
    from encounter import Encounter
    from encounter_inspection import DisarmLandingReceipt
    if type(histories) is not dict:
        raise NativeHistoryRejected(
            "compacted Disarm restoration requires Encounter histories")
    encounters = {row.id: row for row in world.event_history.values()
                  if type(row) is Encounter}
    if set(histories) != set(encounters):
        raise NativeHistoryRejected(
            "compacted Disarm histories do not cover the Universe Encounters")
    for encounter_id in sorted(encounters):
        encounter = encounters[encounter_id]
        log = histories[encounter_id]
        current = encounter.__dict__.get("_disarm_landing_receipts")
        if log is None:
            if current or encounter.time != encounter.start_time:
                raise NativeHistoryRejected(
                    "compacted history-free Encounter has Disarm landings")
            continue
        upgraded = upgrade(log)
        validate(upgraded)
        if (upgraded["schema"] != SCHEMA
                or upgraded["initial"]["encounter_id"] != encounter_id
                or upgraded["latest_boundary"] != encounter.last_processed_boundary
                or type(current) is not list or current):
            raise NativeHistoryRejected(
                "compacted Disarm landing shell differs from native history")
        query = NativeHistoryQuery(upgraded)
        restored = []
        for boundary in range(1, upgraded["latest_boundary"] + 1):
            facts = query.receipt_facts_at(boundary)
            if facts is None or facts.get("disarm_landings") is None:
                raise NativeHistoryRejected(
                    "committed Disarm landing facts are unavailable")
            rows = _materialize_plain(facts["disarm_landings"])
            if (type(rows) is not tuple
                    or any(type(row) is not DisarmLandingReceipt
                           or row.boundary != boundary for row in rows)):
                raise NativeHistoryRejected(
                    "reconstructed Disarm landing facts are malformed")
            restored.extend(rows)
        encounter.__dict__["_disarm_landing_receipts"] = restored
    return True


def restore_compacted_receipt_facts(world, histories):
    """Rebuild duplicated immutable receipt projections from authenticated facts.

    Action declarations/results, identified Effects, scheduler/fence state,
    participants, objective-use rows and projectile states are recorded in the
    native fact stream. The graph keeps the current simulation snapshot and
    receipt identities, but does not serialize a second copy of these committed
    inspection projections.
    """
    from encounter import Encounter
    from encounter_inspection import (ActionInspection, CommittedBoundaryRecord,
                                      ObjectiveInspection, detached)
    from action_evaluation import ActionView, ActionProposal, EffectIdentity, IdentifiedEffect
    from interval_staging import QueueProjection
    from statistical_group import StatisticalGroup
    from types import MappingProxyType

    def rebind_recipient_identities(value, action_id):
        from observer_proposals import RecipientIdentity
        if type(value) is RecipientIdentity:
            action = world.get_event_by_id(action_id)
            data = {} if action is None else object.__getattribute__(action, "__dict__")
            field_by_role = {
                "in_world_belief_ledger": "ledger",
                "in_world_received_accounts": "received_accounts",
                "observer_location_evidence": "location_ledger",
                "observer_object_evidence": "object_ledger",
            }
            field = field_by_role.get(value.role)
            handle = None if field is None else data.get(field)
            if handle is None:
                raise NativeHistoryRejected(
                    "committed receipt recipient cannot be rebound to its Action")
            return RecipientIdentity(value.role, id(handle))
        if type(value) in (dict, MappingProxyType):
            return MappingProxyType({
                rebind_recipient_identities(key, action_id):
                rebind_recipient_identities(item, action_id)
                for key, item in value.items()})
        if type(value) in (tuple, list):
            rows = tuple(rebind_recipient_identities(item, action_id)
                         for item in value)
            return rows if type(value) is tuple else list(rows)
        if type(value) in (set, frozenset):
            rows = frozenset(rebind_recipient_identities(item, action_id)
                             for item in value)
            return rows if type(value) is frozenset else set(rows)
        if is_dataclass(value) and not isinstance(value, type):
            record = object.__new__(type(value))
            for field in fields(type(value)):
                object.__setattr__(record, field.name,
                    rebind_recipient_identities(getattr(value, field.name), action_id))
            return record
        return value

    def rebind_authority_references(value, encounter):
        from interval_staging import AuthorityReference
        if type(value) is AuthorityReference:
            if value.role == "event":
                target = world.get_event_by_id(value.key)
            elif value.role == "accepted_packet":
                registered = encounter._choice_book._registered.get(value.key)
                target = None if registered is None else registered[1]
            elif value.role == "encounter":
                target = encounter if value.key == encounter.id else None
            elif value.role == "universe":
                target = world if value.key == world.id else None
            else:
                target = None
            if target is None:
                raise NativeHistoryRejected(
                    "compacted scheduler reference cannot be rebound")
            object.__setattr__(value, "identity", id(target))
            return
        if type(value) in (dict, MappingProxyType):
            for key, item in value.items():
                rebind_authority_references(key, encounter)
                rebind_authority_references(item, encounter)
        elif type(value) in (tuple, list, set, frozenset):
            for item in value:
                rebind_authority_references(item, encounter)
        elif is_dataclass(value) and not isinstance(value, type):
            for field in fields(type(value)):
                rebind_authority_references(getattr(value, field.name), encounter)

    def rebind_objective_ledger(value, ledger):
        if type(value) in (dict, MappingProxyType):
            return MappingProxyType({
                rebind_objective_ledger(key, ledger):
                rebind_objective_ledger(item, ledger)
                for key, item in value.items()})
        if type(value) in (tuple, list):
            rows = tuple(rebind_objective_ledger(item, ledger) for item in value)
            return rows if type(value) is tuple else list(rows)
        if type(value) in (set, frozenset):
            rows = frozenset(rebind_objective_ledger(item, ledger) for item in value)
            return rows if type(value) is frozenset else set(rows)
        if is_dataclass(value) and not isinstance(value, type):
            record = object.__new__(type(value))
            for field in fields(type(value)):
                field_value = (id(ledger) if type(value) is SubjectRealityCandidate
                               and field.name == "ledger_identity"
                               else rebind_objective_ledger(
                                   getattr(value, field.name), ledger))
                object.__setattr__(record, field.name, field_value)
            return record
        return value

    if type(histories) is not dict:
        raise NativeHistoryRejected("compacted receipt restoration requires Encounter histories")
    encounters = {row.id: row for row in world.event_history.values()
                  if type(row) is Encounter}
    if set(histories) != set(encounters):
        raise NativeHistoryRejected(
            "compacted receipt histories do not cover the Universe Encounters")
    for encounter_id in sorted(encounters):
        encounter = encounters[encounter_id]
        log = histories[encounter_id]
        receipts = encounter.__dict__.get("_atomic_interval_history")
        if log is None:
            if receipts or encounter.time != encounter.start_time:
                raise NativeHistoryRejected(
                    "compacted history-free Encounter has committed boundaries")
            continue
        upgraded = upgrade(log)
        validate(upgraded)
        if (upgraded["schema"] != SCHEMA
                or upgraded["initial"]["encounter_id"] != encounter_id
                or upgraded["latest_boundary"] != encounter.last_processed_boundary
                or type(receipts) is not list
                or [row.boundary for row in receipts]
                    != list(range(1, upgraded["latest_boundary"] + 1))):
            raise NativeHistoryRejected(
                "compacted receipt facts differ from their committed boundary chain")
        query = NativeHistoryQuery(upgraded)
        for receipt in receipts:
            meta = receipt.inspection
            if type(meta) is not CommittedBoundaryRecord:
                raise NativeHistoryRejected("compacted receipt record type is unsupported")
            if (meta.actions or meta.effects or meta.objective or meta.objective_use or meta.starts
                    or meta.participants or meta.schedule is not None
                    or meta.projectile_states):
                raise NativeHistoryRejected(
                    "compacted receipt graph contains an unexpected projection")
            facts = query.boundary_facts_at(receipt.boundary)
            encoded_actions = _materialize_plain(facts["actions"])
            encoded_effects = _materialize_plain(facts["effects"])
            encoded_objective = _materialize_plain(facts["objective"])
            encoded_use = _materialize_plain(facts["objective_use"])
            encoded_starts = _materialize_plain(facts["starts"])
            encoded_participants = _materialize_plain(facts["participants"])
            encoded_schedule = _materialize_plain(facts["schedule"])
            encoded_projectiles = _materialize_plain(facts["projectile_states"])
            if (type(encoded_actions) is not dict
                    or set(encoded_actions) != set(receipt.action_ids)
                    or any(type(row) is not ActionInspection
                           or type(row.declaration) is not ActionView
                           or type(row.facts) is not ActionProposal
                           for row in encoded_actions.values())):
                raise NativeHistoryRejected(
                    "compacted Action declaration/result facts are malformed")
            actions = {identity: (encoded_actions[identity].declaration,
                                  encoded_actions[identity].facts)
                       for identity in receipt.action_ids}
            actions = {
                identity: (
                    rebind_recipient_identities(declaration, identity),
                    rebind_recipient_identities(proposal, identity))
                for identity, (declaration, proposal) in actions.items()}
            if (type(encoded_effects) is not dict
                    or set(encoded_effects) != set(receipt.effect_ids)
                    or any(type(identity) is not EffectIdentity
                           or type(row) is not IdentifiedEffect
                           or row.identity != identity
                           for identity, row in encoded_effects.items())):
                raise NativeHistoryRejected(
                    "compacted identified Effect facts are malformed")
            effects = {identity: encoded_effects[identity]
                       for identity in receipt.effect_ids}
            effects = {
                identity: rebind_recipient_identities(
                    row, identity.source_action_id)
                for identity, row in effects.items()}
            from objective_reality import SubjectRealityCandidate
            if (type(encoded_objective) is not dict
                    or any(type(row) is not SubjectRealityCandidate
                           for row in encoded_objective.values())):
                raise NativeHistoryRejected(
                    "compacted objective candidate facts are malformed")
            objects = world.object_registry.object_instances
            candidates = {}
            for subject_id, row in encoded_objective.items():
                subject = objects.get(subject_id)
                if subject is None:
                    raise NativeHistoryRejected(
                        "compacted objective subject is not registered")
                ledger = (subject._composition_reality
                          if type(subject) is StatisticalGroup
                          else getattr(getattr(subject, "personal_history", None),
                                       "reality", None))
                if ledger is None or type(subject_id) is not str:
                    raise NativeHistoryRejected(
                        "compacted objective ledger cannot be rebound")
                object.__setattr__(row, "ledger_identity", id(ledger))
                object.__setattr__(row, "facts",
                    rebind_objective_ledger(row.facts, ledger))
                candidates[subject_id] = row
            if (type(encoded_use) is not tuple
                    or type(encoded_starts) is not tuple
                    or type(encoded_participants) is not tuple
                    or type(encoded_schedule) is not QueueProjection
                    or type(encoded_projectiles) is not dict
                    or any(type(identity) is not str or not identity
                           for identity in encoded_projectiles)):
                raise NativeHistoryRejected(
                    "compacted receipt projection fields have invalid shapes")
            objective = MappingProxyType(candidates)
            rebind_authority_references(encoded_starts, encounter)
            rebind_authority_references(encoded_schedule, encounter)
            for name, value in (
                    ("actions", MappingProxyType(actions)),
                    ("effects", MappingProxyType(effects)),
                    ("objective", MappingProxyType(objective)),
                    ("objective_use", detached(encoded_use)),
                    ("starts", detached(encoded_starts)),
                    ("participants", detached(encoded_participants)),
                    ("schedule", detached(encoded_schedule)),
                    ("projectile_states", MappingProxyType(encoded_projectiles))):
                object.__setattr__(meta, name, value)
    return True


def restore_compacted_target_history(world, histories):
    """Rebuild Target-owned rows omitted from the marked compact native graph.

    This restoration adapter consumes the separately validated current native
    fact logs and the exact committed receipt boundaries already present in
    the private graph. It does not evaluate or replay an Action.
    """
    from action_settlement import TargetCandidate
    from atomic_publication import TargetIntervalRecord
    from encounter import Encounter
    from object import ObjectInstance
    from weapon import WeaponInstance
    from armor import ArmorInstance
    from being import BeingInstance
    from statistical_group import StatisticalGroup

    if type(histories) is not dict:
        raise NativeHistoryRejected("compacted Target restoration requires Encounter histories")
    encounters = {row.id: row for row in world.event_history.values()
                  if type(row) is Encounter}
    if set(histories) != set(encounters):
        raise NativeHistoryRejected("compacted Target histories do not cover the Universe Encounters")
    supported = (BeingInstance, ObjectInstance, WeaponInstance, ArmorInstance,
                 StatisticalGroup)
    objects = world.object_registry.object_instances
    storage_by_id = {}
    absent_storage_ids = set()
    for identity, value in objects.items():
        if type(value) not in supported:
            continue
        data = object.__getattribute__(value, "__dict__")
        prior = data.get("_atomic_target_history", [])
        if type(prior) is not list or prior:
            raise NativeHistoryRejected(
                "compacted native graph contains nonempty Target history")
        rows = []
        if "_atomic_target_history" in data:
            object.__setattr__(value, "_atomic_target_history", rows)
        else:
            absent_storage_ids.add(identity)
        storage_by_id[identity] = rows

    for encounter_id in sorted(encounters):
        encounter = encounters[encounter_id]
        log = histories[encounter_id]
        receipts = encounter.__dict__.get("_atomic_interval_history")
        if log is None:
            if receipts or encounter.time != encounter.start_time:
                raise NativeHistoryRejected(
                    "compacted history-free Encounter has committed boundaries")
            continue
        upgraded = upgrade(log)
        validate(upgraded)
        expected_boundaries = list(range(
            math.floor(_number_value(upgraded["initial"]["start"])) + 1,
            upgraded["latest_boundary"] + 1))
        if (upgraded["schema"] != SCHEMA
                or upgraded["initial"]["encounter_id"] != encounter_id
                or upgraded["latest_boundary"] != encounter.last_processed_boundary
                or type(receipts) is not list
                or [row.boundary for row in receipts] != expected_boundaries):
            raise NativeHistoryRejected(
                "compacted Target history does not match its committed receipt chain")
        query = NativeHistoryQuery(upgraded)
        from observer_proposals import RecipientIdentity
        recipient_identities = {}
        for receipt in receipts:
            for identity, projection in receipt.inspection.recipients.items():
                if type(identity) is not RecipientIdentity:
                    raise NativeHistoryRejected(
                        "compacted receipt has an unreviewed recipient identity")
                role = identity.role
                owner_id = (getattr(projection, "observer_id", None)
                            or getattr(projection, "listener_id", None))
                if type(owner_id) is str:
                    recipient_identities.setdefault((role, owner_id), {})[
                        identity.object_identity] = identity
        for receipt in receipts:
            if (receipt.encounter_id != encounter_id
                    or type(receipt.boundary) is not int):
                raise NativeHistoryRejected(
                    "compacted Target history receipt identity differs")
            meta = receipt.inspection
            state = query.state_at(receipt.boundary)["entities"]
            candidates = {identity: _materialize_plain(value)
                for identity, value in state.items()
                if type(value) is dict and value.get("$record") ==
                "action_settlement.TargetCandidate"}
            expected_ids = set(meta.entities)
            if set(candidates) != expected_ids:
                raise NativeHistoryRejected(
                    "compacted Target facts do not cover the receipt Entity set")
            for identity, candidate in candidates.items():
                if (type(candidate) is not TargetCandidate
                        or candidate.target_id != identity
                        or identity not in storage_by_id):
                    raise NativeHistoryRejected(
                        "compacted Target fact has an unknown native owner")
                incoming = []
                for row in candidate.incoming:
                    authoritative = meta.effects.get(row.identity)
                    if (authoritative is None
                            or _plain(authoritative) != _plain(row)):
                        raise NativeHistoryRejected(
                            "compacted Target Effect differs from its committed receipt")
                    incoming.append(authoritative)
                observer = candidate.observer_state
                if observer is not None:
                    bound_identities = []
                    for marker in observer.belief_recipient_ids:
                        matches = recipient_identities.get(
                            (marker.role, observer.observer_id), {})
                        if len(matches) != 1:
                            raise NativeHistoryRejected(
                                "compacted Target observer recipient is unavailable or ambiguous")
                        bound_identities.append(next(iter(matches.values())))
                    observer = replace(observer,
                        belief_recipient_ids=tuple(bound_identities))
                candidate = replace(candidate, incoming=tuple(incoming),
                                    observer_state=observer)
                if identity in absent_storage_ids:
                    object.__setattr__(objects[identity],
                                       "_atomic_target_history",
                                       storage_by_id[identity])
                    absent_storage_ids.remove(identity)
                storage_by_id[identity].append(TargetIntervalRecord(
                    encounter_id, receipt.boundary, candidate))
        for receipt in receipts:
            for identity in receipt.inspection.entities:
                rows = storage_by_id.get(identity)
                if (rows is None or not any(type(row) is TargetIntervalRecord
                        and row.encounter_id == encounter_id
                        and row.boundary == receipt.boundary for row in rows)):
                    raise NativeHistoryRejected(
                        "compacted Target reconstruction is incomplete")
    return True


def events_at(log, boundary):
    validate(log)
    if type(boundary) is not int or not 0 <= boundary <= log["latest_boundary"]:
        raise NativeHistoryRejected("requested native boundary is not committed")
    if boundary == 0:
        return json.loads(_canonical({"action_ids": [], "effect_ids": [],
            "actions": {}, "effects": {}, "starts": {"$tuple": []},
            "participants": log["initial"]["participants"]}).decode("ascii"))
    for row in log["boundaries"]:
        if row.get("kind") == "quiet_span":
            if row["from_boundary"] <= boundary <= row["to_boundary"]:
                return {"action_ids": [], "effect_ids": [], "actions": {},
                        "effects": {},
                        "starts": row["quiet_events"]["starts"],
                        "participants": row["quiet_events"]["participants"]}
        elif row["boundary"] == boundary:
            return row["events"]
    raise NativeHistoryRejected("requested native boundary is not committed")


def receipt_facts_at(log, boundary):
    """Return a detached committed receipt-fact row, or None for old logs."""
    return NativeHistoryQuery(log).receipt_facts_at(boundary)


def timeline_at(log, boundary=None):
    """Return the detached committed boundary timeline without graph reads."""
    return NativeHistoryQuery(log).timeline_at(boundary)


def committed_actions_at(log, boundary):
    """Return detached cumulative committed Action/Event/Effect records."""
    return NativeHistoryQuery(log).committed_actions_at(boundary)


def committed_action_at(log, action_id, boundary):
    """Return the latest committed fact for one Action, or None if uncommitted."""
    return NativeHistoryQuery(log).committed_action_at(action_id, boundary)


def target_at(log, target_id, boundary):
    """Return one detached historical TargetCandidate."""
    return NativeHistoryQuery(log).target_at(target_id, boundary)


def projectile_state_at(log, object_id, boundary):
    """Return a detached recorded projectile state, or None when absent."""
    return NativeHistoryQuery(log).projectile_state_at(object_id, boundary)


def objective_at(log, boundary):
    """Return detached objective inspection facts at a committed boundary."""
    return NativeHistoryQuery(log).objective_at(boundary)


def objective_use_at(log, boundary):
    """Return detached objective-fact use rows at a committed boundary."""
    return NativeHistoryQuery(log).objective_use_at(boundary)


def schedule_at(log, boundary):
    """Return the detached committed scheduler/Choice projection."""
    return NativeHistoryQuery(log).schedule_at(boundary)


def action_state_at(log, action_id, boundary):
    """Return one committed scheduled Action status, when present."""
    return NativeHistoryQuery(log).action_state_at(action_id, boundary)


def choice_state_at(log, choice_id, boundary):
    """Return one committed Choice status, when present."""
    return NativeHistoryQuery(log).choice_state_at(choice_id, boundary)


def target_history_at(log, target_id, boundary=None):
    """Return detached ordered TargetCandidate rows through a boundary."""
    return NativeHistoryQuery(log).target_history_at(target_id, boundary)


def entity_at(log, entity_id, boundary):
    """Return one detached historical EntityInspection projection, if known."""
    return NativeHistoryQuery(log).entity_at(entity_id, boundary)


def entity_history_at(log, entity_id, boundary=None):
    """Return detached EntityInspection projections through a boundary."""
    return NativeHistoryQuery(log).entity_history_at(entity_id, boundary)


def observer_facts_at(log, boundary, observer_id):
    """Return detached observer-owned history without other recipients."""
    return NativeHistoryQuery(log).observer_facts_at(boundary, observer_id)


def observer_knowledge_at(log, boundary, observer_id=None):
    """Return detached Arena passive evidence for one owner or every owner."""
    return NativeHistoryQuery(log).observer_knowledge_at(boundary, observer_id)


def encode(log):
    validate(log)
    wire = _canonical(log)
    if len(wire) > MAX_BYTES:
        raise NativeHistoryRejected("native history exceeds portable byte limit")
    return wire


def decode(wire):
    if type(wire) is not bytes or not wire or len(wire) > MAX_BYTES:
        raise NativeHistoryRejected("native history wire is empty or oversized")
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise NativeHistoryRejected("native history has duplicate JSON keys")
            result[key] = value
        return result
    try:
        value = json.loads(wire.decode("ascii"), object_pairs_hook=unique,
                           parse_constant=lambda _v: (_ for _ in ()).throw(
                               NativeHistoryRejected("non-finite JSON number")))
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise NativeHistoryRejected("native history is malformed JSON") from exc
    if _canonical(value) != wire:
        raise NativeHistoryRejected("native history JSON is not canonical")
    validate(value)
    return value


def write(log, path):
    """Atomically publish a standalone history artifact without replacement."""
    wire = encode(log)
    target = Path(path)
    temporary = None
    linked = False
    try:
        fd, temporary = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp",
                                         dir=target.parent)
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(wire)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, target)
        linked = True
        os.unlink(temporary)
        temporary = None
        flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
        directory_fd = os.open(target.parent, flags)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except FileExistsError as exc:
        raise NativeHistoryRejected("native history destination already exists") from exc
    except OSError as exc:
        detail = " after atomic publication" if linked else " before publication"
        raise NativeHistoryRejected("native history write failed" + detail) from exc
    finally:
        if temporary is not None:
            try:
                os.unlink(temporary)
            except OSError:
                pass
