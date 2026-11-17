"""Headless native Encounter Save/Load API.

This API composes fact history with the repository's strict typed native graph
codec. It has no Arena session, HTTP, browser, or npcgen dependency. The graph
adapter currently admits only its reviewed native type closure; the coverage
matrix remains the gate for expanding that closure.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import tempfile

import native_history


SCHEMA = "universe.native-encounter-save/2"
LEGACY_SCHEMA = "universe.native-encounter-save/1"
MAX_BYTES = 64 * 1024 * 1024


class NativeSaveRejected(ValueError):
    """Native Save is malformed, incompatible, or outside the supported closure."""


def _canonical(value):
    try:
        return json.dumps(value, sort_keys=True, ensure_ascii=True,
                          separators=(",", ":"), allow_nan=False).encode("ascii")
    except (TypeError, ValueError, RecursionError, UnicodeError) as exc:
        raise NativeSaveRejected("native Save is not canonical finite JSON") from exc


def _unique(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise NativeSaveRejected("native Save contains duplicate JSON keys")
        value[key] = item
    return value


def _encounter_rows(world, selected, selected_rng_owner):
    from encounter import Encounter
    from interval_staging import _rng_input
    from transactional_progression import _BINDINGS

    encounters = sorted((event for event in world.event_history.values()
                         if type(event) is Encounter), key=lambda row: row.id)
    rows = []
    for saved in encounters:
        binding = _BINDINGS.get(id(saved))
        owner = (selected_rng_owner if saved is selected else
                 binding.rng_owner if binding is not None and binding.encounter() is saved
                 else None)
        if owner is None:
            raise NativeSaveRejected(
                "every registered Encounter requires a separately owned native RNG")
        state = _rng_input(saved, None, owner)[2]
        history = native_history.current_recording(saved)
        receipts = saved.__dict__.get("_atomic_interval_history")
        if history is None and receipts:
            history = native_history.capture(saved)
        rows.append({"encounter_id": saved.id,
                     "rng_state": _rng_json(state),
                     "history": history})
    if not rows or selected.id not in {row["encounter_id"] for row in rows}:
        raise NativeSaveRejected("selected Encounter is absent from the Universe registry")
    return rows


def _entity_context_history_available(world):
    """Use graph compaction only when every committed root has exact facts."""
    from encounter import Encounter
    from native_history import (NativeHistoryQuery, current_recording,
                                capture, upgrade, validate)

    encounters = [event for event in world.event_history.values()
                  if type(event) is Encounter]
    for encounter in encounters:
        if not encounter.__dict__.get("_atomic_interval_history"):
            continue
        history = current_recording(encounter)
        if history is None:
            history = capture(encounter)
        if history is None:
            return False
        # Earlier native fact versions can expose EntityInspection while
        # lacking later-added fatigue, receipt, or observer subfamilies. Keep
        # their complete graph projection intact; only the current schema is
        # sufficient to replace the full receipt field.
        if history.get("schema") != native_history.SCHEMA:
            return False
        normalized = upgrade(history)
        validate(normalized)
        context = normalized.get("entity_context")
        if (normalized["latest_boundary"] != encounter.last_processed_boundary
                or type(context) is not dict or context.get("available") is not True
                or NativeHistoryQuery(normalized).entity_context_at(
                    normalized["latest_boundary"]) is None):
            return False
    return True


def _rng_json(value, depth=0):
    if depth > 8:
        raise NativeSaveRejected("native RNG state exceeds its nesting limit")
    if type(value) is tuple:
        return [_rng_json(row, depth + 1) for row in value]
    if value is None or type(value) in (int, float):
        return value
    raise NativeSaveRejected("native RNG owner has an unsupported state value")


def _rng_tuple(value, depth=0):
    if depth > 8:
        raise NativeSaveRejected("saved RNG state exceeds its nesting limit")
    if type(value) is list:
        return tuple(_rng_tuple(row, depth + 1) for row in value)
    if value is None or type(value) in (int, float):
        return value
    raise NativeSaveRejected("saved RNG state is malformed")


def export_save(encounter, *, recipient_bindings=()):
    """Return a self-contained native graph plus authenticated fact history.

    Caller-owned observer ledgers and account lists must be supplied as
    explicit :class:`checkpoint_adapters.RecipientBinding` values. Their data
    is included once in the graph; no external process handle is serialized.
    """
    try:
        from atomic_publication import coordinated_access
        with coordinated_access(encounter.universe):
            return _export_save_coordinated(encounter,
                                            recipient_bindings=recipient_bindings)
    except NativeSaveRejected:
        raise
    except Exception as exc:
        raise NativeSaveRejected(f"native Encounter could not be saved: {exc}") from exc


def _export_save_coordinated(encounter, *, recipient_bindings=()):
    try:
        from checkpoint_inventory import (capture_checkpoint_candidate,
                                          validate_checkpoint_candidate)
        from native_graph_snapshot import encode as encode_graph
        compact_entity_context = _entity_context_history_available(
            encounter.universe)
        candidate = capture_checkpoint_candidate(
            encounter.universe, encounter, quiescent=True,
            rng_scope="exclusive_encounter", native_adapters=True,
            full_native=True, compact_native_target_history=True,
            compact_native_entity_context=compact_entity_context,
            compact_native_receipt_facts=compact_entity_context,
            compact_native_publication_facts=compact_entity_context,
            compact_native_disarm_landings=compact_entity_context,
            bindings=recipient_bindings,
            rng_owner=_native_rng_owner(encounter))
        if candidate.diagnostics:
            codes = ", ".join(sorted({row.code for row in candidate.diagnostics}))
            raise NativeSaveRejected("native semantic closure refused: " + codes)
        graph = encode_graph(candidate.envelope, native=True)
        encounter_rows = _encounter_rows(encounter.universe, encounter,
                                         _native_rng_owner(encounter))
        # Bind the detached history copy to the exact graph candidate. A
        # commit racing Save between graph capture and recorder export must
        # refuse this bundle rather than mix two valid but different cuts.
        validate_checkpoint_candidate(
            encounter.universe, encounter, candidate, quiescent=True)
        if len(encounter_rows) == 1:
            # Keep the established single-Encounter contract and byte-level
            # migration behavior unchanged. Version /2 is only needed when a
            # Save must carry independent state for multiple Encounter roots.
            body = {"schema": LEGACY_SCHEMA,
                    "graph_b64": base64.b64encode(graph).decode("ascii"),
                    "history": encounter_rows[0]["history"]}
        else:
            body = {"schema": SCHEMA,
                    "selected_encounter_id": encounter.id,
                    "graph_b64": base64.b64encode(graph).decode("ascii"),
                    "encounters": encounter_rows}
        body["sha256"] = hashlib.sha256(_canonical(body)).hexdigest()
        wire = _canonical(body)
        if len(wire) > MAX_BYTES:
            raise NativeSaveRejected("native Save exceeds the portable size limit")
        from encounter import Encounter
        by_id = {event.id: event for event in encounter.universe.event_history.values()
                 if type(event) is Encounter}
        for row in encounter_rows:
            saved = by_id[row['encounter_id']]
            if native_history.current_recording(saved) is None:
                if row['history'] is None:
                    native_history.NativeHistoryRecorder.ensure_pending_attached(saved)
                else:
                    native_history.NativeHistoryRecorder.ensure_attached(
                        saved, log=row['history'])
        return wire
    except NativeSaveRejected:
        raise
    except Exception as exc:
        raise NativeSaveRejected(f"native Encounter could not be saved: {exc}") from exc


def _native_rng_owner(encounter):
    from transactional_progression import mode_of, _BINDINGS
    if mode_of(encounter) != "transactional":
        raise NativeSaveRejected("native Save requires ordinary transactional Encounter mode")
    binding = _BINDINGS.get(id(encounter))
    if binding is None or binding.encounter() is not encounter:
        raise NativeSaveRejected("native Encounter RNG owner is not bound")
    return binding.rng_owner


def rng_owner_for(encounter):
    """Return the independently restored native RNG owner for one Encounter."""
    try:
        from transactional_progression import _BINDINGS
        binding = _BINDINGS.get(id(encounter))
        if binding is None or binding.encounter() is not encounter:
            raise NativeSaveRejected("Encounter has no bound native RNG owner")
        return binding.rng_owner
    except NativeSaveRejected:
        raise
    except Exception as exc:
        raise NativeSaveRejected("Encounter RNG owner is unavailable") from exc


def load_save(wire):
    """Restore every registered native Encounter from a strict Save cut."""
    if type(wire) is not bytes or not wire or len(wire) > MAX_BYTES:
        raise NativeSaveRejected("native Save is empty or exceeds the portable size limit")
    try:
        value = json.loads(wire.decode("ascii"), object_pairs_hook=_unique,
                           parse_constant=lambda _v: (_ for _ in ()).throw(
                               NativeSaveRejected("native Save contains a non-finite number")))
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise NativeSaveRejected("native Save is malformed JSON") from exc
    if type(value) is not dict:
        raise NativeSaveRejected("native Save schema differs")
    if value.get("schema") == LEGACY_SCHEMA:
        return _load_v1_save(wire)
    return _load_v2_save(wire, value)


def _load_v2_save(wire, value):
    expected_fields = {"schema", "selected_encounter_id", "graph_b64",
                       "encounters", "sha256"}
    if set(value) != expected_fields or value.get("schema") != SCHEMA:
        raise NativeSaveRejected("native Save schema differs")
    unsigned = {key: item for key, item in value.items() if key != "sha256"}
    if (type(value["sha256"]) is not str
            or hashlib.sha256(_canonical(unsigned)).hexdigest() != value["sha256"]
            or _canonical(value) != wire):
        raise NativeSaveRejected("native Save integrity or canonical encoding differs")
    if (type(value["selected_encounter_id"]) is not str
            or not value["selected_encounter_id"]
            or type(value["graph_b64"]) is not str
            or type(value["encounters"]) is not list
            or len(value["encounters"]) < 2):
        raise NativeSaveRejected("native Save roots or Encounter table are malformed")
    rows = value["encounters"]
    ids = []
    companion_owners = {}
    restore_histories = {}
    from atomic_publication import RNGCursor
    for row in rows:
        if type(row) is not dict or set(row) != {"encounter_id", "rng_state", "history"}:
            raise NativeSaveRejected("native Save Encounter row is malformed")
        identity = row["encounter_id"]
        if type(identity) is not str or not identity:
            raise NativeSaveRejected("native Save Encounter identity is malformed")
        ids.append(identity)
        state = _rng_tuple(row["rng_state"])
        try:
            import random
            random.Random(0).setstate(state)
        except (TypeError, ValueError, OverflowError) as exc:
            raise NativeSaveRejected("native Save Encounter RNG state is invalid") from exc
        if row["history"] is not None:
            native_history.validate(row["history"])
            restore_histories[identity] = native_history.upgrade(row["history"])
            initial = row["history"]["initial"]
            if (initial["encounter_id"] != identity
                    or row["history"]["latest_boundary"] < 0):
                raise NativeSaveRejected("native history belongs to another Encounter")
        else:
            restore_histories[identity] = None
        if identity != value["selected_encounter_id"]:
            companion_owners[identity] = RNGCursor(state)
    if ids != sorted(set(ids)) or value["selected_encounter_id"] not in ids:
        raise NativeSaveRejected("native Save Encounter identities are duplicated or noncanonical")
    try:
        graph_wire = base64.b64decode(value["graph_b64"].encode("ascii"), validate=True)
        if base64.b64encode(graph_wire).decode("ascii") != value["graph_b64"]:
            raise NativeSaveRejected("native graph payload is not canonical base64")
        from native_graph_snapshot import decode as decode_graph, restore as restore_graph
        world, selected, selected_rng = restore_graph(
            decode_graph(graph_wire, native=True), native=True,
            companion_rng_owners=companion_owners,
            native_histories=restore_histories)
        from encounter import Encounter
        encounters = {event.id: event for event in world.event_history.values()
                      if type(event) is Encounter}
        if (selected.id != value["selected_encounter_id"]
                or set(encounters) != set(ids)):
            raise NativeSaveRejected("native Save graph Encounter roots differ")
        from transactional_progression import _BINDINGS
        for row in rows:
            saved = encounters[row["encounter_id"]]
            binding = _BINDINGS.get(id(saved))
            if binding is None or binding.encounter() is not saved:
                raise NativeSaveRejected("restored Encounter RNG ownership is missing")
            if _rng_json(binding.rng_owner.state if hasattr(binding.rng_owner, "state")
                         else binding.rng_owner.getstate()) != row["rng_state"]:
                raise NativeSaveRejected("restored Encounter RNG differs from its Save row")
            log = row["history"]
            receipts = saved.__dict__.get("_atomic_interval_history")
            if log is None:
                if (receipts or saved.time != saved.start_time
                        or saved.last_processed_boundary != saved.time):
                    raise NativeSaveRejected(
                        "history-free native Encounter is not at its initial boundary")
                native_history.NativeHistoryRecorder.restore_pending(saved)
                continue
            expected_log = native_history.upgrade(log)
            expected_wire = native_history.encode(expected_log)
            initial = expected_log["initial"]
            actual_log = native_history.capture(
                saved, initial_schedule=initial["initial_schedule"],
                initial_schedule_available=initial.get(
                    "initial_schedule_available", False),
                initial_entities=(native_history._materialize_plain(
                    initial["entities"])
                    if initial.get("initial_entities_available") is True
                    else None))
            actual_wire = native_history.encode(actual_log)
            if actual_wire != expected_wire:
                raise NativeSaveRejected(
                    "restored native Encounter disagrees with its saved history")
            native_history.NativeHistoryRecorder.restore(
                saved, actual_log, current_history=actual_wire)
        return world, selected, selected_rng
    except NativeSaveRejected:
        raise
    except Exception as exc:
        raise NativeSaveRejected(f"native Save restoration refused: {exc}") from exc


def _load_v1_save(wire):
    """Strictly restore an exact native graph and verify its historical view."""
    if type(wire) is not bytes or not wire or len(wire) > MAX_BYTES:
        raise NativeSaveRejected("native Save is empty or exceeds the portable size limit")
    try:
        value = json.loads(wire.decode("ascii"), object_pairs_hook=_unique,
                           parse_constant=lambda _v: (_ for _ in ()).throw(
                               NativeSaveRejected("native Save contains a non-finite number")))
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise NativeSaveRejected("native Save is malformed JSON") from exc
    if (type(value) is not dict
            or set(value) != {"schema", "graph_b64", "history", "sha256"}
            or value["schema"] != LEGACY_SCHEMA):
        raise NativeSaveRejected("native Save schema differs")
    unsigned = {key: item for key, item in value.items() if key != "sha256"}
    if (type(value["sha256"]) is not str
            or hashlib.sha256(_canonical(unsigned)).hexdigest() != value["sha256"]
            or _canonical(value) != wire):
        raise NativeSaveRejected("native Save integrity or canonical encoding differs")
    if type(value["graph_b64"]) is not str:
        raise NativeSaveRejected("native graph payload is not encoded data")
    try:
        graph_wire = base64.b64decode(value["graph_b64"].encode("ascii"), validate=True)
        if base64.b64encode(graph_wire).decode("ascii") != value["graph_b64"]:
            raise NativeSaveRejected("native graph payload is not canonical base64")
        from native_graph_snapshot import decode as decode_graph, restore as restore_graph
        if value["history"] is not None:
            native_history.validate(value["history"])
            expected_history_log = native_history.upgrade(value["history"])
            expected_history = native_history.encode(expected_history_log)
        else:
            expected_history_log = None
        world, encounter, rng_owner = restore_graph(
            decode_graph(graph_wire, native=True), native=True,
            native_histories=(None if expected_history_log is None else
                {expected_history_log["initial"]["encounter_id"]:
                 expected_history_log}))
        if value["history"] is None:
            if (encounter.__dict__.get("_atomic_interval_history")
                    or encounter.time != encounter.start_time
                    or encounter.last_processed_boundary != encounter.time):
                raise NativeSaveRejected(
                    "history-free native Save is not at the initial committed boundary")
            native_history.NativeHistoryRecorder.restore_pending(encounter)
            return world, encounter, rng_owner
        saved_initial = expected_history_log["initial"]
        source_schema = value["history"]["schema"]
        capture = (native_history.capture_legacy_entity_anchor
                   if source_schema != native_history.SCHEMA
                   else native_history.capture)
        actual_log = capture(
            encounter,
            initial_schedule=saved_initial["initial_schedule"],
            initial_schedule_available=saved_initial.get(
                "initial_schedule_available", False),
            **({} if source_schema != native_history.SCHEMA else {
                "initial_entities": (native_history._materialize_plain(
                    saved_initial["entities"])
                    if saved_initial.get("initial_entities_available") is True
                    else None)}))
        actual_history = native_history.encode(actual_log)
        if actual_history != expected_history:
            source_schema = value["history"]["schema"]
            compatible_actual = None
            if source_schema in (native_history.LEGACY_SCHEMA,
                                  native_history.PREVIOUS_SCHEMA,
                                  native_history.QUIET_SPAN_SCHEMA):
                compatible_actual = native_history.encode(
                    native_history._without_entity_context(actual_log))
            elif source_schema == native_history.ENTITY_CONTEXT_SCHEMA:
                compatible_actual = native_history.encode(
                    native_history._without_fatigue_context(actual_log))
            elif source_schema == native_history.FATIGUE_CONTEXT_SCHEMA:
                compatible_actual = native_history.encode(
                    native_history._without_initial_rng(actual_log))
            elif source_schema == native_history.INITIAL_RNG_SCHEMA:
                compatible_actual = native_history.encode(
                    native_history._without_receipt_facts(actual_log))
            elif source_schema == native_history.RECEIPT_FACT_SCHEMA:
                compatible_actual = native_history.encode(
                    native_history._without_observer_knowledge(actual_log))
            if compatible_actual != expected_history:
                raise NativeSaveRejected("restored native graph disagrees with saved history")
        if encounter.id != value["history"]["initial"]["encounter_id"]:
            raise NativeSaveRejected("restored Encounter logical identity differs")
        native_history.NativeHistoryRecorder.restore(
            encounter, actual_log, current_history=actual_history)
        return world, encounter, rng_owner
    except NativeSaveRejected:
        raise
    except Exception as exc:
        raise NativeSaveRejected(f"native Save restoration refused: {exc}") from exc


def load_legacy_arena_save(wire):
    """Strictly read an accepted generated-Arena /10–/12 archive as native state.

    This compatibility entry point delegates archive/version validation to the
    existing portable reader, then uses the closed graph restorer. It does not
    create an Arena session or import the browser/server or npcgen. New writes
    should use :func:`export_save`; this reader never modifies its input.
    """
    if type(wire) is not bytes or not wire or len(wire) > MAX_BYTES:
        raise NativeSaveRejected(
            "legacy native Save is empty or exceeds the portable size limit")
    try:
        from arena_persistence import decode as decode_legacy
        from native_graph_snapshot import restore as restore_graph
        decoded = decode_legacy(wire)
        schema = (decoded.get("schema")
                  or decoded.get("manifest", {}).get("save_schema"))
        if schema not in {
                "universe.generated-arena-save/10",
                "universe.generated-arena-save/11",
                "universe.generated-arena-save/12"}:
            raise NativeSaveRejected("legacy native Save version is outside /10–/12")
        world, encounter, rng_owner = restore_graph(
            decoded["decoded_native"], native=False)
        if (encounter.universe is not world
                or world.event_history.get(encounter.id) is not encounter):
            raise NativeSaveRejected("legacy native roots or Encounter identity differ")
        return world, encounter, rng_owner
    except NativeSaveRejected:
        raise
    except Exception as exc:
        raise NativeSaveRejected(
            f"legacy generated-Arena Save restoration refused: {exc}") from exc


def write_save(encounter, path, *, recipient_bindings=()):
    """Durably publish one new Save without replacing an existing path."""
    wire = export_save(encounter, recipient_bindings=recipient_bindings)
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
        # A hard-link publication is atomic and fails if target already exists;
        # unlike replace(), it cannot overwrite a user Save or follow its link.
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
        return len(wire)
    except FileExistsError as exc:
        raise NativeSaveRejected("native Save destination already exists") from exc
    except OSError as exc:
        detail = " after atomic publication" if linked else " before publication"
        raise NativeSaveRejected("native Save write failed" + detail) from exc
    finally:
        if temporary is not None:
            try:
                os.unlink(temporary)
            except OSError:
                pass


def load_path(path):
    """Read a bounded Save file and pass it through the strict loader."""
    try:
        with Path(path).open("rb") as stream:
            wire = stream.read(MAX_BYTES + 1)
    except OSError as exc:
        raise NativeSaveRejected("native Save file could not be read") from exc
    if len(wire) > MAX_BYTES:
        raise NativeSaveRejected("native Save file exceeds the portable size limit")
    return load_save(wire)
