"""Arena-session-independent, fact-only native Encounter history records.

The history wire stores an initial committed-boundary projection, atomic
state changes, sparse EntityInspection context changes, and native
Action/Effect/observation facts for each commit. ``NativeHistoryQuery`` provides
validated repeated historical reads without re-expanding quiet spans or
evaluating Actions. This module does not yet replace production Save/Load.
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
SCHEMA = "universe.native-encounter-history/4"
LEGACY_SCHEMAS = (LEGACY_SCHEMA, PREVIOUS_SCHEMA, QUIET_SPAN_SCHEMA)
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
    return {
        "boundary": receipt.boundary,
        "start": _plain(meta.start),
        "end": _plain(meta.end),
        "action_ids": list(receipt.action_ids),
        "effect_ids": [_plain(value) for value in receipt.effect_ids],
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


def _quiet_changes(row):
    """Return numeric metadata increments safe to derive across a quiet run."""
    events = row.get("events")
    if (not _quiet_events(events) or row.get("rng_after") != SAME_RNG
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
    if (type(row) is not dict or set(row) != {
            "kind", "from_boundary", "to_boundary", "start", "step", "quiet_events",
            "increments", "rng_after", "state_sha256"}
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
    if type(boundary) is not int or not 1 <= boundary <= log["latest_boundary"]:
        raise NativeHistoryRejected("requested native RNG boundary is not committed")
    current = None
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
    previous = None
    body = {key: value for key, value in log.items() if key != "sha256"}
    body["schema"] = SCHEMA
    body["entity_context"] = _unavailable_entity_context()
    rows = []
    for original in _expand_rows(log):
        row = dict(original)
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
    body = {key: value for key, value in log.items() if key != "sha256"}
    body["entity_context"] = _unavailable_entity_context()
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
    return {"available": False, "initial": None, "changes": []}


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
        if adapter is None and tag == "encounter_inspection.EntityInspection":
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


def capture(encounter):
    """Capture committed facts from a native Encounter without resolving work.

    The returned format is a queryable historical record, not a resumable Save
    yet. Every logical boundary remains queryable. Consecutive empty-event
    intervals may use a validated numeric cursor span; Action/Event/Effect
    boundaries remain individual atomic records.
    """
    from encounter import Encounter
    if type(encounter) is not Encounter:
        raise NativeHistoryRejected("native Encounter required")
    view = encounter.inspect_committed()
    receipts = tuple(encounter.__dict__.get("_atomic_interval_history", ()))
    if not receipts or len(receipts) != len(view.timeline):
        raise NativeHistoryRejected("committed native receipt chain is incomplete")
    targets_by_boundary = _target_candidates(encounter)
    initial_receipt = receipts[0]
    initial = {
        "encounter_id": encounter.id,
        "universe_id": encounter.universe.id,
        "start": _plain(initial_receipt.inspection.start),
        "entities": _plain(initial_receipt.inspection.entities),
        "participants": _plain(initial_receipt.inspection.participants),
        "initial_schedule": _plain(initial_receipt.inspection.schedule),
    }
    initial_entity_context = _plain(initial_receipt.inspection.entities)
    entity_context_state = initial_entity_context
    entity_context_changes = []
    prior = _initial_state(initial)
    boundaries = []
    previous_boundary = None
    previous_rng = None
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
            "rng_after": _rng_record(payload["rng_after"], previous_rng),
            "state_sha256": hashlib.sha256(_canonical(state)).hexdigest(),
        })
        previous_rng = payload["rng_after"]
        prior = state
        previous_boundary = receipt.boundary
    body = {"schema": SCHEMA, "initial": initial,
            "boundaries": _compact_quiet_rows(boundaries),
            "latest_boundary": previous_boundary,
            "entity_context": {"available": True,
                               "initial": initial_entity_context,
                               "changes": entity_context_changes}}
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
                "rng_after": dict(SAME_RNG),
                "state_sha256": hashlib.sha256(_canonical(next_state)).hexdigest(),
            })
            state = next_state
    return output


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
        "rng_after": _rng_record(payload["rng_after"], previous_rng),
        "state_sha256": hashlib.sha256(_canonical(state)).hexdigest(),
    }
    body = {key: value for key, value in log.items() if key != "sha256"}
    body["boundaries"] = _append_compact_row(log["boundaries"], row)
    body["latest_boundary"] = expected
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
    _measure(body)
    result = _seal(body)
    validate(result)
    return result


class NativeHistoryRecorder:
    """Opt-in in-memory recorder fed only after successful native publication."""

    def __init__(self, encounter, log):
        self._encounter_ref = weakref(encounter)
        self._log = log
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
            elif log is not None and encode(recorder._log) != encode(upgrade(log)):
                raise NativeHistoryRejected(
                    "native history recorder differs from the completed Save cut")
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
            return recorder

    @property
    def latest_boundary(self):
        return self._log["latest_boundary"]

    def export(self):
        with _RECORDER_LOCK:
            if self.failure is not None:
                raise NativeHistoryRejected("native history recorder failed: " + self.failure)
            if self.encounter.last_processed_boundary != self.latest_boundary:
                raise NativeHistoryRejected("native history recorder is behind the Encounter")
            return decode(encode(self._log))


def has_recorder(encounter):
    with _RECORDER_LOCK:
        return encounter in _RECORDERS


def current_recording(encounter):
    with _RECORDER_LOCK:
        recorder = _RECORDERS.get(encounter)
    return None if recorder is None else recorder.export()


def record_committed_boundary(encounter):
    """Append the latest commit after native publication has fully returned."""
    with _RECORDER_LOCK:
        recorder = _RECORDERS.get(encounter)
    if recorder is None:
        return
    try:
        updated = append_committed(recorder._log, encounter)
        with _RECORDER_LOCK:
            recorder._log = updated
    except Exception as exc:
        # The Encounter publication is already authoritative and committed.
        # Preserve ordinary progression; make later Save fail closed until the
        # recorder is recovered from the authenticated native receipt chain.
        with _RECORDER_LOCK:
            recorder.failure = f"{type(exc).__name__}: {exc}"


def validate(log):
    """Strictly validate identity, chronology, atomic deltas, and integrity."""
    base_keys = {"schema", "initial", "boundaries", "latest_boundary", "sha256"}
    current_keys = base_keys | {"entity_context"}
    if (type(log) is not dict
            or set(log) != (current_keys if log.get("schema") == SCHEMA else base_keys)):
        raise NativeHistoryRejected("native history envelope schema differs")
    unsigned = dict(log)
    digest = unsigned.pop("sha256")
    if (log["schema"] not in (*LEGACY_SCHEMAS, SCHEMA) or type(digest) is not str
            or hashlib.sha256(_canonical(unsigned)).hexdigest() != digest):
        raise NativeHistoryRejected("native history integrity digest differs")
    _measure(unsigned)
    initial = log["initial"]
    if (type(initial) is not dict or set(initial) != {
            "encounter_id", "universe_id", "start", "entities", "participants",
            "initial_schedule"} or type(initial["encounter_id"]) is not str
            or not initial["encounter_id"] or type(initial["universe_id"]) is not str
            or not initial["universe_id"]):
        raise NativeHistoryRejected("native history initial state schema differs")
    state = _initial_state(initial)
    boundaries = log["boundaries"]
    if type(boundaries) is not list:
        raise NativeHistoryRejected("native history boundaries are not an array")
    seen_actions = set()
    seen_effects = set()
    prior_rng = None
    covered = 0
    for row in boundaries:
        if type(row) is dict and row.get("kind") == "quiet_span":
            if log["schema"] not in (QUIET_SPAN_SCHEMA, SCHEMA):
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
        if (type(row) is not dict or set(row) != {
                "boundary", "start", "end", "changes", "events", "rng_after",
                "state_sha256"} or type(row["boundary"]) is not int
                or row["boundary"] != expected):
            raise NativeHistoryRejected("native history boundary is missing, repeated, or malformed")
        if row["rng_after"] == SAME_RNG:
            if log["schema"] not in (QUIET_SPAN_SCHEMA, SCHEMA) or prior_rng is None:
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
        covered = expected
    if (type(log["latest_boundary"]) is not int
            or not 0 <= log["latest_boundary"] <= MAX_BOUNDARIES
            or log["latest_boundary"] != covered):
        raise NativeHistoryRejected("native history latest boundary differs")
    if log["schema"] == SCHEMA:
        _validate_entity_context(log["entity_context"], log["latest_boundary"])
    return True


def _validate_entity_context(context, latest_boundary):
    if (type(context) is not dict or set(context) != {"available", "initial", "changes"}
            or type(context["available"]) is not bool or type(context["changes"]) is not list):
        raise NativeHistoryRejected("native EntityInspection history schema differs")
    if not context["available"]:
        if context["initial"] is not None or context["changes"]:
            raise NativeHistoryRejected("legacy EntityInspection history marker is inconsistent")
        return
    if type(context["initial"]) is not dict:
        raise NativeHistoryRejected("native EntityInspection initial state is missing")
    _validate_plain_record(context["initial"])
    state = context["initial"]
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
        if hashlib.sha256(_canonical(state)).hexdigest() != row["state_sha256"]:
            raise NativeHistoryRejected("native EntityInspection state digest differs")
        previous = row["boundary"]


def state_at(log, boundary):
    """Reconstruct the historical property projection without Action resolution."""
    validate(log)
    if type(boundary) is not int or not 1 <= boundary <= log["latest_boundary"]:
        raise NativeHistoryRejected("requested native boundary is not committed")
    initial = log["initial"]
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
    if type(boundary) is not int or not 1 <= boundary <= log["latest_boundary"]:
        raise NativeHistoryRejected("requested native boundary is not committed")
    context = log.get("entity_context", _unavailable_entity_context())
    if not context["available"]:
        return None
    state = json.loads(_canonical(context["initial"]).decode("ascii"))
    for row in context["changes"]:
        if row["boundary"] > boundary:
            break
        state = _apply(state, row["changes"])
        if hashlib.sha256(_canonical(state)).hexdigest() != row["state_sha256"]:
            raise NativeHistoryRejected("native EntityInspection query digest differs")
    return state


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
        cursor = None
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
        self._state_boundary = 0
        self._state = _initial_state(self._log["initial"])
        context = self._log.get("entity_context", _unavailable_entity_context())
        self._context_available = context["available"]
        self._context_boundary = 0
        self._context = (json.loads(_canonical(context["initial"]).decode("ascii"))
                         if self._context_available else None)
        self._context_changes = {row["boundary"]: row
                                 for row in context["changes"]}

    def _boundary(self, boundary):
        if type(boundary) is not int or not 1 <= boundary <= self._latest:
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
        return self._copy(state)

    def events_at(self, boundary):
        self._boundary(boundary)
        _index, row = self._segment(boundary)
        if row.get("kind") == "quiet_span":
            events = {"action_ids": [], "effect_ids": [], "actions": {},
                      "effects": {}, "starts": row["quiet_events"]["starts"],
                      "participants": row["quiet_events"]["participants"]}
        else:
            events = row["events"]
        return self._copy(events)

    def rng_state_at(self, boundary):
        self._boundary(boundary)
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


def events_at(log, boundary):
    validate(log)
    if type(boundary) is not int or not 1 <= boundary <= log["latest_boundary"]:
        raise NativeHistoryRejected("requested native boundary is not committed")
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
