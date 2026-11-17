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


SCHEMA = "universe.native-encounter-save/1"
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


def export_save(encounter, *, recipient_bindings=()):
    """Return a self-contained native graph plus authenticated fact history.

    Caller-owned observer ledgers and account lists must be supplied as
    explicit :class:`checkpoint_adapters.RecipientBinding` values. Their data
    is included once in the graph; no external process handle is serialized.
    """
    try:
        from checkpoint_inventory import (capture_checkpoint_candidate,
                                          validate_checkpoint_candidate)
        from native_graph_snapshot import encode as encode_graph
        candidate = capture_checkpoint_candidate(
            encounter.universe, encounter, quiescent=True,
            rng_scope="exclusive_encounter", native_adapters=True,
            full_native=True, bindings=recipient_bindings,
            rng_owner=_native_rng_owner(encounter))
        if candidate.diagnostics:
            codes = ", ".join(sorted({row.code for row in candidate.diagnostics}))
            raise NativeSaveRejected("native semantic closure refused: " + codes)
        graph = encode_graph(candidate.envelope, native=True)
        history = native_history.current_recording(encounter)
        if history is None:
            # Build the first history copy locally. Do not mutate the weak
            # recorder registry until every graph/history check and portable
            # size check has succeeded for this Save cut.
            history = native_history.capture(encounter)
        # Bind the detached history copy to the exact graph candidate. A
        # commit racing Save between graph capture and recorder export must
        # refuse this bundle rather than mix two valid but different cuts.
        validate_checkpoint_candidate(
            encounter.universe, encounter, candidate, quiescent=True)
        body = {"schema": SCHEMA, "graph_b64": base64.b64encode(graph).decode("ascii"),
                "history": history}
        body["sha256"] = hashlib.sha256(_canonical(body)).hexdigest()
        wire = _canonical(body)
        if len(wire) > MAX_BYTES:
            raise NativeSaveRejected("native Save exceeds the portable size limit")
        if native_history.current_recording(encounter) is None:
            native_history.NativeHistoryRecorder.ensure_attached(encounter, log=history)
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


def load_save(wire):
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
            or value["schema"] != SCHEMA):
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
        native_history.validate(value["history"])
        expected_history = native_history.encode(native_history.upgrade(value["history"]))
        world, encounter, rng_owner = restore_graph(
            decode_graph(graph_wire, native=True), native=True)
        actual_log = native_history.capture(encounter)
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
