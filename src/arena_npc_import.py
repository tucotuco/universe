"""Small, provenance-preserving import boundary for NPC Generator candidates.

This module does not translate NPC Generator rules into Universe mechanics. It
validates the currently exported ``npcgen-npc`` v1 envelope, retains the exact
UTF-8 source bytes, and binds a display name to an explicitly identified native
Being created from a separately selected Universe definition.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from threading import RLock


NPCGEN_FORMAT = "npcgen-npc"
NPCGEN_SCHEMA_VERSION = 1
_ROOT_FIELDS = {
    "format", "schema_version", "engine", "generation", "edits",
    "state", "sheet", "notes",
}
_STATE_FIELDS = {
    "name", "classes", "xps", "levels", "race", "subrace", "sex",
    "scores", "exc_str", "age", "month", "day", "height", "weight",
    "hps", "psionics", "possessions", "family", "seed",
}
_SHEET_FIELDS = {
    "identity", "abilities", "age", "classes", "hit_points", "psionics",
    "possessions", "family",
}
_NOTE_FIELDS = {
    "identity", "abilities", "age", "classes", "hit_points", "psionics",
    "possessions", "family", "general",
}
_EDIT_OPERATIONS = {
    "set_name", "set_ability", "reroll_age", "reroll_birthday", "reroll_size",
    "reroll_weight", "reroll_hit_points", "reroll_extras", "set_level",
    "change_class", "change_race", "toggle_sex", "add_class", "remove_class",
}
_RULE_HASH = re.compile(r"^sha256:[0-9a-f]{64}$")
_MAX_SOURCE_BYTES = 2_000_000


class NPCandidateError(ValueError):
    """Candidate input is malformed or outside the supported export contract."""


def _object_without_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise NPCandidateError(f"duplicate JSON object key {key!r}")
        result[key] = value
    return result


def _is_int(value):
    return type(value) is int


@dataclass(frozen=True)
class NPCandidate:
    """Immutable source envelope; the original JSON bytes are the authority."""

    source_bytes: bytes
    content_sha256: str
    display_name: str
    generation_seed: int
    engine_version: str
    rules_hash: str

    @classmethod
    def from_json(cls, source):
        if isinstance(source, str):
            try:
                raw = source.encode("utf-8")
            except UnicodeEncodeError as exc:
                raise NPCandidateError("source JSON must be UTF-8") from exc
        elif isinstance(source, bytes):
            raw = source
        else:
            raise TypeError("source must be UTF-8 JSON text or bytes")
        if not raw or len(raw) > _MAX_SOURCE_BYTES:
            raise NPCandidateError("source record is empty or exceeds 2 MB")
        try:
            text = raw.decode("utf-8")
            record = json.loads(text, object_pairs_hook=_object_without_duplicate_keys)
        except NPCandidateError:
            raise
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise NPCandidateError(f"invalid UTF-8 NPC Generator JSON: {exc}") from None
        _validate_record(record)
        return cls(
            source_bytes=raw,
            content_sha256=hashlib.sha256(raw).hexdigest(),
            display_name=record["state"]["name"],
            generation_seed=record["generation"]["seed"],
            engine_version=record["engine"]["version"],
            rules_hash=record["engine"]["rules_hash"],
        )

    @classmethod
    def from_file(cls, path):
        from pathlib import Path
        return cls.from_json(Path(path).read_bytes())

    def source_record_copy(self):
        """Return a detached parsed copy; edits cannot change preserved bytes."""
        return json.loads(self.source_bytes)


def _validate_record(record):
    if type(record) is not dict:
        raise NPCandidateError("expected a JSON object")
    if set(record) != _ROOT_FIELDS:
        missing = sorted(_ROOT_FIELDS - set(record))
        extra = sorted(set(record) - _ROOT_FIELDS)
        raise NPCandidateError(f"npcgen-npc v1 fields differ (missing={missing}, extra={extra})")
    if record.get("format") != NPCGEN_FORMAT:
        raise NPCandidateError("unsupported NPC source format; expected npcgen-npc")
    if type(record.get("schema_version")) is not int or record["schema_version"] != NPCGEN_SCHEMA_VERSION:
        raise NPCandidateError("unsupported npcgen-npc schema_version; expected 1")

    engine = record["engine"]
    if type(engine) is not dict or not {"name", "version", "rules_hash"} <= set(engine):
        raise NPCandidateError("engine must contain name, version, and rules_hash")
    if engine["name"] != "npcgen" or type(engine["version"]) is not str:
        raise NPCandidateError("unsupported or malformed NPC Generator engine identity")
    if not _RULE_HASH.fullmatch(engine["rules_hash"] if type(engine["rules_hash"]) is str else ""):
        raise NPCandidateError("engine.rules_hash must be sha256 followed by 64 lowercase hex digits")

    generation = record["generation"]
    if type(generation) is not dict or not {"seed", "mode"} <= set(generation):
        raise NPCandidateError("generation must contain seed and mode")
    if not _is_int(generation["seed"]) or generation["seed"] < 0:
        raise NPCandidateError("generation.seed must be a nonnegative integer")
    if generation["mode"] not in ("random", "class"):
        raise NPCandidateError("generation.mode must be random or class")
    if "class" in generation and not _is_int(generation["class"]):
        raise NPCandidateError("generation.class must be an integer")
    if "class_name" in generation and type(generation["class_name"]) is not str:
        raise NPCandidateError("generation.class_name must be text")

    edits = record["edits"]
    if type(edits) is not list:
        raise NPCandidateError("edits must be a list")
    for index, edit in enumerate(edits):
        if (type(edit) is not dict or set(edit) != {"op", "args"}
                or edit.get("op") not in _EDIT_OPERATIONS or type(edit.get("args")) is not list):
            raise NPCandidateError(f"edits[{index}] is not a supported recorded edit")

    state = record["state"]
    if type(state) is not dict or not _STATE_FIELDS <= set(state):
        raise NPCandidateError("state is missing fields required by npcgen-npc v1")
    if type(state["name"]) is not str or not state["name"].strip():
        raise NPCandidateError("state.name must be nonempty text")
    if not _is_int(state["seed"]) or state["seed"] != generation["seed"]:
        raise NPCandidateError("state.seed must match generation.seed")

    sheet = record["sheet"]
    if type(sheet) is not dict or not _SHEET_FIELDS <= set(sheet):
        raise NPCandidateError("sheet is missing fields required by npcgen-npc v1")
    notes = record["notes"]
    if type(notes) is not dict or not set(notes) <= _NOTE_FIELDS:
        raise NPCandidateError("notes contains unsupported sections")
    if any(type(note) is not str for note in notes.values()):
        raise NPCandidateError("notes values must be text")


@dataclass(frozen=True)
class NativeBeingBinding:
    """Session binding; source digest and native Being identity stay distinct."""

    binding_key: str
    source_sha256: str
    display_name: str
    native_being_id: str
    native_definition_name: str
    position: tuple[float, float, float]


class ArenaBindingBook:
    """Bind validated candidates to explicit native definitions and identities."""

    def __init__(self, universe):
        self.universe = universe
        self._lock = RLock()
        self._bindings = {}

    def bind(self, candidate, *, binding_key, native_being_id,
             native_definition_name, position, geometry=None):
        from being import BeingInstance
        from spatial import CartesianPosition, Geometry3D

        if not isinstance(candidate, NPCandidate):
            raise TypeError("candidate must be an NPCandidate")
        if type(binding_key) is not str or not binding_key.strip():
            raise NPCandidateError("binding_key must be nonempty text")
        if type(native_being_id) is not str or not native_being_id.strip():
            raise NPCandidateError("native_being_id must be explicit nonempty text")
        if type(native_definition_name) is not str or not native_definition_name.strip():
            raise NPCandidateError("native_definition_name must be explicit nonempty text")
        if not isinstance(position, CartesianPosition):
            raise TypeError("position must be a Universe CartesianPosition")
        if geometry is not None and not isinstance(geometry, Geometry3D):
            raise TypeError("geometry must be a native Geometry3D or None")
        pos = tuple(float(v) for v in position.as_tuple())
        geometry_signature = None if geometry is None else json.dumps(
            geometry.to_dict(), sort_keys=True, separators=(",", ":"))
        signature = (candidate.source_bytes, native_being_id, native_definition_name,
                     pos, geometry_signature)

        with self._lock, self.universe._schedule_lock:
            previous = self._bindings.get(binding_key)
            if previous is not None:
                if previous[0] != signature:
                    raise NPCandidateError("binding key was already used for different source or native setup")
                if self.universe.get_object_by_id(native_being_id) is not previous[1]:
                    raise NPCandidateError("bound native Being is missing or no longer has the same identity")
                return previous[2]
            if any(row[2].native_being_id == native_being_id for row in self._bindings.values()):
                raise NPCandidateError("native Being identity is already bound to another candidate")
            if self.universe.get_object_by_id(native_being_id) is not None:
                raise NPCandidateError("native Being identity collides with an existing Universe Object")
            definition = self.universe.get_being_definition(native_definition_name)
            if definition is None:
                raise NPCandidateError(f"unknown native Being definition {native_definition_name!r}")

            being = BeingInstance(definition, candidate.display_name, id=native_being_id)
            being.set_position(position)
            if geometry is not None:
                being.set_geometry(geometry)
            # Universe.add_object is the native ObjectRegistry ownership boundary.
            self.universe.add_object(being)
            if self.universe.get_object_by_id(native_being_id) is not being:
                raise NPCandidateError("Universe did not register the requested native Being identity")
            binding = NativeBeingBinding(
                binding_key, candidate.content_sha256, candidate.display_name,
                native_being_id, native_definition_name, pos)
            self._bindings[binding_key] = (signature, being, binding)
            return binding

    def binding(self, binding_key):
        row = self._bindings.get(binding_key)
        return None if row is None else row[2]
