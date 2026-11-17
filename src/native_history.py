"""Arena-session-independent, fact-only native Encounter history records.

The history wire stores an initial committed-boundary projection, atomic
state changes, sparse EntityInspection and Arena observer-knowledge context
changes, and native Action/Effect/observation/receipt facts for each commit.
``NativeHistoryQuery``
provides validated repeated historical reads without re-expanding quiet spans
or evaluating Actions. This module does not yet replace production Save/Load.
"""
from __future__ import annotations

from dataclasses import fields, is_dataclass
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
SCHEMA = "universe.native-encounter-history/9"
LEGACY_SCHEMAS = (LEGACY_SCHEMA, PREVIOUS_SCHEMA, QUIET_SPAN_SCHEMA,
                  ENTITY_CONTEXT_SCHEMA, FATIGUE_CONTEXT_SCHEMA,
                  INITIAL_RNG_SCHEMA, RECEIPT_FACT_SCHEMA,
                  OBSERVER_KNOWLEDGE_SCHEMA)
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
_RECORDER_LOCK = RLock()


def _canonical(value):
    try:
        return json.dumps(value, sort_keys=True, ensure_ascii=True,
                          separators=(",", ":"), allow_nan=False).encode("ascii")
    except (TypeError, ValueError, RecursionError, UnicodeError) as exc:
        raise NativeHistoryRejected("native history is not canonical finite JSON data") from exc


def _native_types():
    import importlib
    result = {}
    for tag in FIELD_ADAPTERS:
        module, name = tag.rsplit(".", 1)
        cls = getattr(importlib.import_module(module), name)
        if type(cls) is not type or cls.__module__ != module or cls.__name__ != name:
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
        projection_data = {key: item for key, item in data.items()
                           if key != "identity"}
        rows.append({"role": role, "owner_id": owner,
                     "projection": _plain(projection_data)})
    rows.sort(key=lambda row: (row["role"], row["owner_id"] or ""))
    return rows


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
    if log["schema"] not in (INITIAL_RNG_SCHEMA, RECEIPT_FACT_SCHEMA,
                              OBSERVER_KNOWLEDGE_SCHEMA, SCHEMA):
        body["initial"] = dict(body["initial"], rng_before_first_commit=None)
    # Before /9 the value came from the first committed receipt, not from the
    # pre-first-commit scheduler cut. Keep it as the old delta replay anchor,
    # but never expose it as boundary-zero history.
    schedule = body["initial"]["initial_schedule"]
    if schedule is not None:
        _validate_queue_projection(schedule)
    body["initial"]["initial_schedule_available"] = False
    if log["schema"] == ENTITY_CONTEXT_SCHEMA:
        body["entity_context"] = dict(log["entity_context"], fatigue_available=False)
    elif log["schema"] not in (FATIGUE_CONTEXT_SCHEMA, INITIAL_RNG_SCHEMA,
                               RECEIPT_FACT_SCHEMA, OBSERVER_KNOWLEDGE_SCHEMA,
                               SCHEMA):
        body["entity_context"] = _unavailable_entity_context()
    has_receipt_facts = log["schema"] in (RECEIPT_FACT_SCHEMA,
                                           OBSERVER_KNOWLEDGE_SCHEMA, SCHEMA)
    body["receipt_facts_complete"] = (
        log["receipt_facts_complete"] if has_receipt_facts else False)
    body["observer_knowledge"] = (
        log["observer_knowledge"]
        if log["schema"] in (OBSERVER_KNOWLEDGE_SCHEMA, SCHEMA)
        else _unavailable_observer_knowledge())
    rows = []
    for original in _expand_rows(log):
        row = dict(original)
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
    body["initial"] = dict(body["initial"], rng_before_first_commit=None)
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
    body["initial"] = dict(body["initial"], rng_before_first_commit=None)
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


def _without_observer_knowledge(log):
    """Normalize /8 facts to the exact observer-knowledge scope of /7."""
    validate(log)
    body = {key: value for key, value in log.items() if key != "sha256"}
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
            initial_schedule_available=None):
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
    view = encounter.inspect_committed()
    receipts = tuple(encounter.__dict__.get("_atomic_interval_history", ()))
    if not receipts or len(receipts) != len(view.timeline):
        raise NativeHistoryRejected("committed native receipt chain is incomplete")
    targets_by_boundary = _target_candidates(encounter)
    initial_receipt = receipts[0]
    if initial_schedule_available is None:
        initial_schedule_available = initial_schedule is not None
    initial = {
        "encounter_id": encounter.id,
        "universe_id": encounter.universe.id,
        "start": _plain(initial_receipt.inspection.start),
        "entities": _plain(initial_receipt.inspection.entities),
        "participants": _plain(initial_receipt.inspection.participants),
        "initial_schedule": initial_schedule,
        "initial_schedule_available": initial_schedule_available,
        "rng_before_first_commit": _plain(
            encounter.__dict__["_native_rng_origin_state"])
            if encounter.__dict__.get("_native_rng_origin_state") is not None
            else None,
    }
    initial_entity_context = _plain(initial_receipt.inspection.entities)
    entity_context_state = initial_entity_context
    entity_context_changes = []
    prior = _initial_state(initial)
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
    log = upgrade(log)
    previous = state_at(log, log["latest_boundary"])
    previous_rng = rng_state_at(log, log["latest_boundary"])
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


def record_committed_boundary(encounter, *, initial_schedule=None):
    """Append the latest commit after native publication has fully returned."""
    with _RECORDER_LOCK:
        recorder = _RECORDERS.get(encounter)
    if recorder is None:
        if initial_schedule is not None:
            with _RECORDER_LOCK:
                _INITIAL_SCHEDULES.setdefault(encounter, initial_schedule)
        return
    try:
        baseline = (recorder._initial_schedule if recorder is not None
                    and recorder._initial_schedule is not None
                    else initial_schedule)
        updated = (capture(encounter, initial_schedule=baseline)
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


def validate(log):
    """Strictly validate identity, chronology, atomic deltas, and integrity."""
    base_keys = {"schema", "initial", "boundaries", "latest_boundary", "sha256"}
    current_keys = base_keys | {"entity_context"}
    version = log.get("schema") if type(log) is dict else None
    has_receipt_facts = version in (RECEIPT_FACT_SCHEMA,
                                    OBSERVER_KNOWLEDGE_SCHEMA, SCHEMA)
    has_observer_knowledge = version in (OBSERVER_KNOWLEDGE_SCHEMA, SCHEMA)
    has_initial_schedule = version == SCHEMA
    has_entity_context = version in (ENTITY_CONTEXT_SCHEMA, FATIGUE_CONTEXT_SCHEMA,
                                     INITIAL_RNG_SCHEMA, RECEIPT_FACT_SCHEMA,
                                     OBSERVER_KNOWLEDGE_SCHEMA, SCHEMA)
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
    if version in (INITIAL_RNG_SCHEMA, RECEIPT_FACT_SCHEMA,
                   OBSERVER_KNOWLEDGE_SCHEMA, SCHEMA):
        expected_initial.add("rng_before_first_commit")
    if has_initial_schedule:
        expected_initial.add("initial_schedule_available")
    if (type(initial) is not dict or set(initial) != expected_initial or type(initial["encounter_id"]) is not str
            or not initial["encounter_id"] or type(initial["universe_id"]) is not str
            or not initial["universe_id"]):
        raise NativeHistoryRejected("native history initial state schema differs")
    if version in (INITIAL_RNG_SCHEMA, RECEIPT_FACT_SCHEMA,
                   OBSERVER_KNOWLEDGE_SCHEMA, SCHEMA) and initial["rng_before_first_commit"] is not None:
        _validate_rng_cursor(initial["rng_before_first_commit"])
    if has_initial_schedule:
        if type(initial["initial_schedule_available"]) is not bool:
            raise NativeHistoryRejected("initial scheduler availability marker is malformed")
        if initial["initial_schedule_available"] and initial["initial_schedule"] is None:
            raise NativeHistoryRejected("available initial scheduler projection is absent")
        if initial["initial_schedule"] is not None:
            _validate_queue_projection(initial["initial_schedule"])
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
                                      RECEIPT_FACT_SCHEMA,
                                      OBSERVER_KNOWLEDGE_SCHEMA, SCHEMA):
                raise NativeHistoryRejected("legacy native history cannot contain quiet spans")
            if row.get("rng_after") != SAME_RNG or prior_rng is None:
                raise NativeHistoryRejected("native quiet span RNG reference is unanchored")
            if type(row.get("from_boundary")) is not int or row["from_boundary"] != covered + 1:
                raise NativeHistoryRejected("native quiet span boundary order differs")
            state = _apply_quiet_span(state, row, row.get("to_boundary"))
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
                                      RECEIPT_FACT_SCHEMA,
                                      OBSERVER_KNOWLEDGE_SCHEMA, SCHEMA) or prior_rng is None:
                raise NativeHistoryRejected("native history RNG reference is not versioned or anchored")
        else:
            if (type(row["rng_after"]) is not dict
                    or set(row["rng_after"]) != {"$tuple"}
                    or type(row["rng_after"]["$tuple"]) is not list):
                raise NativeHistoryRejected("native history RNG cursor has an invalid shape")
            prior_rng = row["rng_after"]
        state = _apply(state, row["changes"])
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
    current_context_schemas = (FATIGUE_CONTEXT_SCHEMA, INITIAL_RNG_SCHEMA,
                               RECEIPT_FACT_SCHEMA, OBSERVER_KNOWLEDGE_SCHEMA,
                               SCHEMA)
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
        return json.loads(_canonical(_initial_state(initial)).decode("ascii"))
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
        self._has_receipt_facts = self._log.get("schema") in (
            RECEIPT_FACT_SCHEMA, OBSERVER_KNOWLEDGE_SCHEMA, SCHEMA)
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
        if not self._initial_schedule_available:
            result["initial_schedule"] = None
            if boundary == 0:
                result["schedule"] = None
        return result

    def target_at(self, target_id, boundary):
        """Return one authoritative TargetCandidate at a committed boundary."""
        self._boundary(boundary)
        if type(target_id) is not str or not target_id:
            raise NativeHistoryRejected("Target history requires a stable identity")
        target = self.state_at(boundary)["entities"].get(target_id)
        if target is None:
            raise NativeHistoryRejected("requested Target is absent at this boundary")
        return target

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
        if not self._context_available:
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


def committed_actions_at(log, boundary):
    """Return detached cumulative committed Action/Event/Effect records."""
    return NativeHistoryQuery(log).committed_actions_at(boundary)


def committed_action_at(log, action_id, boundary):
    """Return the latest committed fact for one Action, or None if uncommitted."""
    return NativeHistoryQuery(log).committed_action_at(action_id, boundary)


def target_at(log, target_id, boundary):
    """Return one detached historical TargetCandidate."""
    return NativeHistoryQuery(log).target_at(target_id, boundary)


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
