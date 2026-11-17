"""Arena-session-independent, fact-only native Encounter history records.

The history wire stores an initial committed-boundary projection, atomic
state changes, and the native Action/Effect/observation facts for each commit.
It never evaluates an Action. This module is an implementation component of
native persistence; it does not replace the current production Save/Load path.
"""
from __future__ import annotations

from dataclasses import fields, is_dataclass
import hashlib
import json
import math
from pathlib import Path
from threading import RLock
from types import MappingProxyType
from weakref import WeakKeyDictionary, ref as weakref

from checkpoint_fields import FIELD_ADAPTERS


SCHEMA = "universe.native-encounter-history/1"
MAX_BYTES = 64 * 1024 * 1024
MAX_NODES = 10_000_000
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
        "objective": _plain(meta.objective),
        "objective_use": _plain(meta.objective_use),
        "recipients": _stable_recipients(meta.recipients),
        "schedule": _plain(meta.schedule),
        "starts": _plain(meta.starts),
        "participants": _plain(meta.participants),
        "projectile_states": _plain(meta.projectile_states),
        "rng_after": _plain(receipt.rng_state),
    }


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


def _seal(body):
    value = dict(body)
    value["sha256"] = hashlib.sha256(_canonical(value)).hexdigest()
    return value


def capture(encounter):
    """Capture committed facts from a native Encounter without resolving work.

    The returned format is a queryable historical record, not a resumable Save
    yet. Every boundary remains one atomic record, including Event-free quiet
    intervals, failed/no-diff Actions, and simultaneous batches.
    """
    from encounter import Encounter
    if type(encounter) is not Encounter:
        raise NativeHistoryRejected("native Encounter required")
    view = encounter.inspect_committed()
    receipts = tuple(encounter.__dict__.get("_atomic_interval_history", ()))
    if not receipts or len(receipts) != len(view.timeline):
        raise NativeHistoryRejected("committed native receipt chain is incomplete")
    histories = view.histories
    targets_by_boundary = {}
    for target_id, rows in histories.items():
        for row in rows:
            targets_by_boundary.setdefault(row.boundary, {})[target_id] = row
    initial_receipt = receipts[0]
    initial = {
        "encounter_id": encounter.id,
        "universe_id": encounter.universe.id,
        "start": _plain(initial_receipt.inspection.start),
        "entities": _plain(initial_receipt.inspection.entities),
        "participants": _plain(initial_receipt.inspection.participants),
        "initial_schedule": _plain(initial_receipt.inspection.schedule),
    }
    prior = _initial_state(initial)
    boundaries = []
    previous_boundary = None
    for receipt in receipts:
        if (receipt.encounter_id != encounter.id
                or type(receipt.boundary) is not int
                or previous_boundary is not None and receipt.boundary != previous_boundary + 1):
            raise NativeHistoryRejected("native boundary order or owner identity is invalid")
        payload = _boundary_payload(encounter, receipt, view,
                                    targets_by_boundary)
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
            "rng_after": payload["rng_after"],
            "state_sha256": hashlib.sha256(_canonical(state)).hexdigest(),
        })
        prior = state
        previous_boundary = receipt.boundary
    body = {"schema": SCHEMA, "initial": initial,
            "boundaries": boundaries,
            "latest_boundary": previous_boundary}
    _measure(body)
    return _seal(body)


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
    targets = {}
    for target_id, rows in view.histories.items():
        for row in rows:
            if row.boundary == expected:
                targets[target_id] = row
                break
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
    previous = state_at(log, log["latest_boundary"])
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
        "rng_after": payload["rng_after"],
        "state_sha256": hashlib.sha256(_canonical(state)).hexdigest(),
    }
    body = {key: value for key, value in log.items() if key != "sha256"}
    body["boundaries"] = list(log["boundaries"]) + [row]
    body["latest_boundary"] = expected
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
    def ensure_attached(cls, encounter):
        """Idempotently start or retrieve the recorder for a saved Encounter."""
        with _RECORDER_LOCK:
            recorder = _RECORDERS.get(encounter)
            if recorder is None:
                recorder = cls(encounter, capture(encounter))
                _RECORDERS[encounter] = recorder
            return recorder

    @classmethod
    def restore(cls, encounter, log, *, current_history=None):
        """Resume recording from an authenticated Save history after Load."""
        validate(log)
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
    if type(log) is not dict or set(log) != {
            "schema", "initial", "boundaries", "latest_boundary", "sha256"}:
        raise NativeHistoryRejected("native history envelope schema differs")
    unsigned = dict(log)
    digest = unsigned.pop("sha256")
    if (log["schema"] != SCHEMA or type(digest) is not str
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
    for expected, row in enumerate(boundaries, 1):
        if (type(row) is not dict or set(row) != {
                "boundary", "start", "end", "changes", "events", "rng_after",
                "state_sha256"} or type(row["boundary"]) is not int
                or row["boundary"] != expected):
            raise NativeHistoryRejected("native history boundary is missing, repeated, or malformed")
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
    if log["latest_boundary"] != len(boundaries):
        raise NativeHistoryRejected("native history latest boundary differs")
    return True


def state_at(log, boundary):
    """Reconstruct the historical property projection without Action resolution."""
    validate(log)
    if type(boundary) is not int or not 1 <= boundary <= len(log["boundaries"]):
        raise NativeHistoryRejected("requested native boundary is not committed")
    initial = log["initial"]
    state = _initial_state(initial)
    for row in log["boundaries"][:boundary]:
        state = _apply(state, row["changes"])
    return state


def events_at(log, boundary):
    validate(log)
    if type(boundary) is not int or not 1 <= boundary <= len(log["boundaries"]):
        raise NativeHistoryRejected("requested native boundary is not committed")
    return log["boundaries"][boundary - 1]["events"]


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
    """Atomically replace a standalone history artifact after complete encode."""
    wire = encode(log)
    target = Path(path)
    temporary = target.with_name(target.name + ".tmp")
    try:
        with temporary.open("xb") as stream:
            stream.write(wire)
            stream.flush()
            import os
            os.fsync(stream.fileno())
        import os
        os.link(temporary, target)
        temporary.unlink()
    except FileExistsError as exc:
        raise NativeHistoryRejected("native history temporary path already exists") from exc
    except OSError as exc:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise NativeHistoryRejected("native history write failed without replacing destination") from exc
