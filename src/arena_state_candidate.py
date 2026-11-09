"""Closed, detached post-Spot state candidate for the fixed native Arena.

This is an inspectable data claim, not a checkpoint or an authorization. It
captures only the supported two-Being, six-boundary Arena after its successful
Spot and validates the candidate against the separate Arena history prefix.
Nothing in this module constructs or advances a native simulation.
"""
from __future__ import annotations

from dataclasses import dataclass
import base64
import hashlib
import json
import math
import random
from types import MappingProxyType

from arena_history_prefix import (
    ArenaHistoryRejected,
    ArenaSpotHistoryPrefix,
    capture_arena_history_prefix,
    decode_arena_history_prefix,
)


SCHEMA = "universe.arena.detached-post-spot-state-candidate/1"
TRUST = (
    "untrusted detached native-state claim; digest detects byte changes only; "
    "not publisher-authenticated and not a live restored Encounter"
)
MAX_WIRE_BYTES = 12 * 1024 * 1024
_TOP_FIELDS = frozenset((
    "schema", "trust", "history_prefix_sha256", "scenario",
    "source_bindings", "participants", "target_histories", "encounter",
    "native_data_graph", "content_sha256",
))
_ENCOUNTER_FIELDS = frozenset((
    "_active_fatigue_frame", "_advancing", "_atomic_interval_history",
    "_boundary_context", "_choice_book", "_coordinator_time", "_dispatching",
    "_interval_start", "_physiology_registry", "_running", "_transactional_mode",
    "active_boundary", "awareness", "being_list", "boundary_fault", "cancelled_action_list",
    "difficulty_class", "end_time", "event_type", "fatigue_frame_history",
    "finished_action_list", "id", "initiated", "initiation", "arena_activation",
    "arena_activation_enabled", "arena_movement_activation", "last_fatigue_frame",
    "last_processed_boundary", "local_frame", "location", "map", "name",
    "non_being_object_list", "parent_event_id", "pending_action_list", "start_time",
    "time", "type", "universe",
))
_UNIVERSE_FIELDS = frozenset((
    "_choice_books", "_reproduction_group_registry", "_schedule_lock",
    "_schedule_revision", "event_history", "id", "library", "name",
    "object_registry", "type",
))
_CHOICE_BOOK_FIELDS = frozenset((
    "encounter", "lock", "_counter", "_drafts", "_closed_drafts", "_tokens",
    "_choices", "_reservations", "_registered", "_states",
))
_SPOT_ACTION_FIELDS = frozenset((
    "id", "name", "type", "universe", "event_type", "start_time", "end_time",
    "location", "parent_event_id", "actor_id", "target_id", "instrument_id",
    "strategy", "resolution", "spotting_conditions", "declared_roll", "roll",
    "path_status", "_encounter", "ledger", "group_fully_visible",
    "_activity_started", "_atomic_effect_ids", "_atomic_lifecycle",
))
_REPRODUCTION_REGISTRY_FIELDS = frozenset((
    "_world", "world_identity", "_groups_by_id", "_group_id_aliases",
    "_group_id_by_parent_set", "_group_id_by_offspring", "_parent_set_by_offspring",
    "_person_id_reservations", "_group_id_reservations", "_requests",
    "_offspring_origin_ticks", "_generation_requests", "_generation_parent_set_scopes",
    "_progressive_histories", "_progressive_parent_set_scopes", "_progressive_requests",
    "_native_beings_by_person_id", "_native_being_requests", "_revision",
))


class ArenaStateRejected(ValueError):
    """The native Arena state is outside this closed projection."""


def _require(ok, message):
    if not ok:
        raise ArenaStateRejected(message)


def _canonical(value):
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        raise ArenaStateRejected(f"state candidate is not canonical data: {exc}") from exc


def _pairs_no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ArenaStateRejected(f"duplicate state-candidate field {key!r}")
        result[key] = value
    return result


def _unhex(value, name):
    if type(value) is not str:
        raise ArenaStateRejected(f"{name} must be a hexadecimal binary64 value")
    try:
        number = float.fromhex(value)
    except ValueError as exc:
        raise ArenaStateRejected(f"{name} is not hexadecimal binary64") from exc
    if not math.isfinite(number) or number.hex() != value:
        raise ArenaStateRejected(f"{name} is not canonical finite binary64")
    return number


def _hex(value, name):
    if isinstance(value, bool) or type(value) not in (int, float):
        raise ArenaStateRejected(f"{name} must be a finite number")
    value = float(value)
    if not math.isfinite(value):
        raise ArenaStateRejected(f"{name} must be finite")
    return value.hex()


def _to_json_data(value, *, depth=0):
    """Convert the reviewed inventory's tuple graph to strict JSON values."""
    if depth > 120:
        raise ArenaStateRejected("native state graph exceeds the supported depth")
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float:
        _require(math.isfinite(value), "non-finite native state value")
        return {"$binary64": value.hex()}
    if type(value) is dict:
        _require(all(type(key) is str for key in value),
                 "native data mapping has a non-text key")
        return {key: _to_json_data(item, depth=depth + 1)
                for key, item in value.items()}
    if type(value) in (tuple, list):
        return [_to_json_data(item, depth=depth + 1) for item in value]
    raise ArenaStateRejected("native data graph contains an unreviewed mutable/opaque value")


def _freeze_json(value, *, depth=0):
    if depth > 120:
        raise ArenaStateRejected("candidate exceeds the supported depth")
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float:
        _require(math.isfinite(value), "non-finite candidate number")
        return value
    if type(value) is list:
        return tuple(_freeze_json(item, depth=depth + 1) for item in value)
    if type(value) is dict:
        return MappingProxyType({key: _freeze_json(item, depth=depth + 1)
                                 for key, item in value.items()})
    raise ArenaStateRejected("unsupported decoded candidate value")


@dataclass(frozen=True)
class ArenaBeingStateView:
    being_id: str
    name: str
    native_type: str
    definition_name: str
    definition_graph_sha256: str
    position_hex: tuple
    geometry: tuple
    top_facing: int
    front_facing: int
    hit_points: int | float
    aware_of: tuple
    target_history_boundaries: tuple


@dataclass(frozen=True)
class ArenaPostSpotStateView:
    schema: str
    trust: str
    history_prefix_sha256: str
    universe_id: str
    universe_name: str
    library_id: str
    encounter_id: str
    start_time: float
    time: float
    committed_boundary: int
    participants: tuple
    rng_role: str
    rng_scope: str
    continuation: str


@dataclass(frozen=True)
class ArenaPostSpotStateCandidate:
    """Immutable canonical bytes; decoding never creates native references."""
    _wire: bytes

    def to_bytes(self):
        _decode_payload(self._wire)
        return bytes(self._wire)

    @property
    def content_sha256(self):
        return _decode_payload(self._wire)["content_sha256"]

    def view(self):
        data = _decode_payload(self._wire)
        scenario = data["scenario"]
        participants = tuple(ArenaBeingStateView(
            row["being_id"], row["name"], row["native_type"],
            row["definition_name"], row["definition_graph_sha256"],
            tuple(row["position_hex"]),
            (row["geometry"]["kind"], row["geometry"]["radius_hex"]),
            row["top_facing"], row["front_facing"],
            _unhex(row["hit_points_hex"], "participant hit points"),
            tuple(row["aware_of"]), tuple(row["target_history_boundaries"]))
            for row in data["participants"])
        return ArenaPostSpotStateView(
            SCHEMA, TRUST, data["history_prefix_sha256"],
            scenario["universe_id"], scenario["universe_name"], scenario["library_id"],
            scenario["encounter_id"],
            _unhex(scenario["start_time_hex"], "Encounter start"),
            _unhex(scenario["time_hex"], "Encounter time"),
            scenario["committed_boundary"], participants,
            data["encounter"]["rng_role"], data["encounter"]["rng_scope"],
            "NOT a live restored Encounter; cannot continue")


def _validate_graph(graph):
    """Validate the inert closed data graph against current reviewed adapters."""
    _require(type(graph) is dict and set(graph) == {"root", "nodes"},
             "native graph fields are not closed")
    _require(type(graph["nodes"]) is list and 1 <= len(graph["nodes"]) <= 50000,
             "native graph node count is outside the supported bound")
    from checkpoint_fields import FIELD_ADAPTERS
    known_tags = set(FIELD_ADAPTERS)
    node_refs = set()
    for node in graph["nodes"]:
        _require(type(node) is list and len(node) == 3,
                 "native graph node has an unsupported shape")
        ref, kind, rows = node
        _require(type(ref) is list and ref and all(type(item) in (str, int) for item in ref),
                 "native graph reference is malformed")
        ref_key = _canonical(ref)
        _require(ref_key not in node_refs, "duplicate native graph node reference")
        node_refs.add(ref_key)
        _require(type(kind) is str, "native graph type tag is malformed")
        if kind in ("ordered-map", "tuple", "list", "set", "frozenset"):
            _require(type(rows) is list, "native graph container payload is malformed")
            if kind == "ordered-map":
                _require(all(type(pair) is list and len(pair) == 2 for pair in rows),
                         "native graph map entry is malformed")
        else:
            _require(kind in known_tags, "native graph contains an unsupported native type")
            _require(kind in FIELD_ADAPTERS, "native graph type has no closed field adapter")
            adapter = FIELD_ADAPTERS[kind]
            _require(type(rows) is list and all(type(row) is list and len(row) == 2
                    and type(row[0]) is str for row in rows),
                     "native graph field payload is malformed")
            names = [row[0] for row in rows]
            _require(len(names) == len(set(names)) and not set(names) - set(adapter["allowed"])
                     and not set(adapter["required"]) - set(names),
                     "native graph fields differ from the reviewed closed adapter")
    _require(type(graph["root"]) is list and len(graph["root"]) == 3,
             "native graph roots are malformed")
    for node in graph["nodes"]:
        if node[1] in ("ordered-map", "tuple", "list", "set", "frozenset"):
            payload = [item for pair in node[2] for item in pair] if node[1] == "ordered-map" else node[2]
        else:
            payload = [item[1] for item in node[2]]
        for item in payload:
            _validate_graph_atom(item, node_refs, depth=0)
    for item in graph["root"]:
        _validate_graph_atom(item, node_refs, depth=0)


def _validate_graph_atom(value, node_refs, *, depth):
    _require(depth <= 120, "native graph value is too deeply nested")
    if type(value) in (str, int, bool) or value is None:
        return
    if type(value) is list:
        if value and value[0] == "reference":
            _require(len(value) == 2 and _canonical(value[1]) in node_refs,
                     "native graph contains a dangling reference")
            return
        if value and value[0] == "binary64":
            _require(len(value) == 2 and type(value[1]) is str,
                     "native graph binary64 is malformed")
            _unhex(value[1], "native graph binary64")
            return
        if value and value[0] in ("null", "boolean", "string", "integer"):
            _require(len(value) == (1 if value[0] == "null" else 2),
                     "native graph scalar token is malformed")
            return
        for item in value:
            _validate_graph_atom(item, node_refs, depth=depth + 1)
        return
    raise ArenaStateRejected("native graph contains a non-data value")


def _validate_payload(data):
    _require(type(data) is dict and set(data) == _TOP_FIELDS,
             "state-candidate envelope has missing or unknown fields")
    _require(data["schema"] == SCHEMA and data["trust"] == TRUST,
             "unsupported state-candidate schema or trust label")
    digest = data["content_sha256"]
    _require(type(digest) is str and len(digest) == 64
             and all(c in "0123456789abcdef" for c in digest),
             "state-candidate content digest is malformed")
    body = dict(data)
    body.pop("content_sha256")
    _require(hashlib.sha256(_canonical(body)).hexdigest() == digest,
             "state-candidate content digest mismatch")
    _require(type(data["history_prefix_sha256"]) is str
             and len(data["history_prefix_sha256"]) == 64,
             "bound history-prefix digest is malformed")
    scenario = data["scenario"]
    expected_scenario = {"universe_id", "universe_name", "library_id", "encounter_id",
                         "start_time_hex", "time_hex",
                         "committed_boundary", "difficulty_class_hex", "initiated"}
    _require(type(scenario) is dict and set(scenario) == expected_scenario,
             "Arena scenario state is not closed")
    _require(scenario["start_time_hex"] == 0.0.hex()
             and scenario["time_hex"] == 6.0.hex()
             and scenario["committed_boundary"] == 6
             and scenario["difficulty_class_hex"] == 15.0.hex()
             and scenario["initiated"] is True,
             "only the fixed committed six-boundary Arena state is supported")
    for key in ("universe_id", "encounter_id"):
        _require(type(scenario[key]) is str and scenario[key], "Arena identity is empty")
    _require(type(scenario["universe_name"]) is str
             and type(scenario["library_id"]) is str and scenario["library_id"],
             "Universe/Library binding is malformed")
    _require(scenario["universe_name"] == "NPC candidate Arena",
             "only the reviewed Arena Universe name is supported")
    _require(type(data["source_bindings"]) is list and len(data["source_bindings"]) == 2,
             "exactly two NPC provenance bindings are required")
    _require(type(data["participants"]) is list and len(data["participants"]) == 2,
             "exactly two native Being participants are supported")
    bindings = data["source_bindings"]
    participants = data["participants"]
    _require(all(type(row) is dict and set(row) == {
        "binding_key", "source_sha256", "source_bytes_base64", "display_name",
        "native_being_id", "native_definition_name", "position_hex"} for row in bindings),
        "NPC source-binding fields are not closed")
    _require(all(type(row) is dict and set(row) == {
        "being_id", "name", "native_type", "definition_name", "definition_graph_sha256",
        "position_hex", "geometry", "top_facing", "front_facing", "hit_points_hex",
        "aware_of", "target_history_boundaries"} for row in participants),
        "participant state fields are not closed")
    ids = [row["native_being_id"] for row in bindings]
    _require(ids == [row["being_id"] for row in participants]
             and len(set(ids)) == 2, "native Being binding/participant identities disagree")
    for row in bindings:
        try:
            raw = base64.b64decode(row["source_bytes_base64"], validate=True)
        except (ValueError, TypeError) as exc:
            raise ArenaStateRejected("NPC source bytes are not valid base64") from exc
        _require(hashlib.sha256(raw).hexdigest() == row["source_sha256"],
                 "NPC source bytes do not match their digest")
        _require(type(row["native_definition_name"]) is str
                 and type(row["display_name"]) is str
                 and type(row["binding_key"]) is str
                 and type(row["native_being_id"]) is str
                 and type(row["position_hex"]) is list and len(row["position_hex"]) == 3,
                 "NPC binding fields are malformed")
        for value in row["position_hex"]:
            _unhex(value, "NPC binding position")
    _require(data["participants"][0]["aware_of"] == [ids[1]
             ] and data["participants"][1]["aware_of"] == [],
             "post-Spot Awareness differs from the fixed observer-isolated result")
    for row in participants:
        _require(row["native_type"] == "BeingInstance" and row["definition_name"] == "Human",
                 "unsupported native participant type/definition")
        _require(type(row["definition_graph_sha256"]) is str
                 and len(row["definition_graph_sha256"]) == 64,
                 "native definition graph digest is malformed")
        _require(type(row["position_hex"]) is list and len(row["position_hex"]) == 3,
                 "native position is malformed")
        for axis, value in enumerate(row["position_hex"]):
            _unhex(value, f"participant position {axis}")
        geom = row["geometry"]
        _require(type(geom) is dict and set(geom) == {"kind", "radius_hex"}
                 and geom["kind"] == "Sphere" and geom["radius_hex"] == 0.5.hex(),
                 "Arena requires its explicit native Sphere(0.5) geometry")
        _require(type(row["top_facing"]) is int and type(row["front_facing"]) is int,
                 "Being facing is malformed")
        _unhex(row["hit_points_hex"], "Being hit points")
        _require(type(row["aware_of"]) is list and type(row["target_history_boundaries"]) is list
                 and row["target_history_boundaries"] == [1, 2, 3, 4, 5, 6],
                 "Target-owned histories are incomplete")
    histories = data["target_histories"]
    _require(type(histories) is list and len(histories) == 2,
             "Target-owned histories for both participants are required")
    history_ids = [row["target_id"] for row in histories if type(row) is dict]
    _require(history_ids == ids, "Target-owned history identities differ from participants")
    for row in histories:
        _require(set(row) == {"target_id", "boundaries"}
                 and type(row["boundaries"]) is list and len(row["boundaries"]) == 6,
                 "Target history rows are not closed or complete")
        for boundary, record in enumerate(row["boundaries"], 1):
            _require(type(record) is dict and set(record) == {
                "boundary", "position_hex", "projected_hp_hex", "actual_damage_hex",
                "aware_of", "incoming_effect_ids", "outgoing_effect_ids",
                "practice_empty", "observer_effects_empty"}
                and record["boundary"] == boundary,
                "Target boundary state is malformed")
            _require(type(record["position_hex"]) is list and len(record["position_hex"]) == 3,
                     "Target boundary position is malformed")
            for value in record["position_hex"]:
                _unhex(value, "Target history position")
            _unhex(record["projected_hp_hex"], "Target projected HP")
            _unhex(record["actual_damage_hex"], "Target damage")
            _require(type(record["aware_of"]) is list
                     and type(record["incoming_effect_ids"]) is list
                     and type(record["outgoing_effect_ids"]) is list
                     and type(record["practice_empty"]) is bool
                     and type(record["observer_effects_empty"]) is bool,
                     "Target history state types are malformed")
            _require(record["practice_empty"] and record["observer_effects_empty"],
                     "unmodeled Target practice/observer consequences are unsupported")
    encounter = data["encounter"]
    expected_encounter = {
        "start_time_hex", "time_hex", "last_processed_boundary", "coordinator_time_hex",
        "interval_start_hex", "difficulty_class_hex", "initiated", "participant_ids",
        "non_being_object_ids", "pending_action_ids", "finished_action_ids",
        "cancelled_action_ids", "active_boundary", "boundary_fault", "awareness",
        "choice_counter", "choice_ids", "choice_states", "reservations_empty",
        "open_drafts_empty", "tokens_empty", "schedule_revision", "event_registry_ids",
        "object_registry_ids", "rng_role", "rng_scope", "rng_state",
        "registered_action_ids", "native_action_states", "choice_action_state"}
    expected_encounter.add("progression_mode")
    expected_encounter |= {
        "name", "native_type", "end_time_hex", "event_type", "location",
        "parent_event_id", "map", "local_frame", "initiation",
        "active_fatigue_frame", "physiology_registry", "last_fatigue_frame_boundary",
        "fatigue_frame_history", "receipt_history_scope", "receipt_record_count",
        "reproduction_registry_empty", "universe_choice_books_count",
    }
    _require(type(encounter) is dict and set(encounter) == expected_encounter,
             "Encounter state fields are not closed; missing="
             + repr(sorted(expected_encounter - set(encounter)))
             + " extra=" + repr(sorted(set(encounter) - expected_encounter)))
    _require(encounter["start_time_hex"] == 0.0.hex()
             and encounter["time_hex"] == 6.0.hex()
             and encounter["coordinator_time_hex"] == 6.0.hex()
             and encounter["interval_start_hex"] == 6.0.hex()
             and encounter["last_processed_boundary"] == 6
             and encounter["difficulty_class_hex"] == 15.0.hex()
             and encounter["initiated"] is True
             and encounter["participant_ids"] == ids
             and encounter["non_being_object_ids"] == []
             and encounter["pending_action_ids"] == []
             and encounter["finished_action_ids"] == ["npc-arena/action/spot-ari-bex"]
             and encounter["cancelled_action_ids"] == []
             and encounter["active_boundary"] is None
             and encounter["boundary_fault"] is None,
             "Encounter is not the supported quiescent boundary-6 state")
    _require(encounter["name"] == "" and encounter["native_type"] == "Encounter"
             and encounter["end_time_hex"] is None and encounter["event_type"] is None
             and encounter["location"] is None and encounter["parent_event_id"] is None
             and encounter["map"] is None and encounter["local_frame"] is None
             and encounter["initiation"] is None
             and encounter["active_fatigue_frame"] is None
             and encounter["physiology_registry"] is None
             and encounter["last_fatigue_frame_boundary"] == 6
             and encounter["receipt_history_scope"] == "native process-local receipts omitted; prefix is a detached claim"
             and encounter["receipt_record_count"] == 6
             and encounter["reproduction_registry_empty"] is True
             and encounter["universe_choice_books_count"] == 1,
             "Encounter/Universe has unsupported optional or derived state")
    frames = encounter["fatigue_frame_history"]
    _require(type(frames) is list and len(frames) == 6,
             "six committed Q/B freeze frames must be represented")
    for boundary, row in enumerate(frames, 1):
        _require(type(row) is dict and set(row) == {"start", "time", "views"}
                 and row["start"] == boundary - 1 and row["time"] == boundary
                 and type(row["views"]) is list and len(row["views"]) == 2,
                 "Encounter Q/B frame history is malformed")
        for expected_id, view in zip(ids, row["views"]):
            _require(type(view) is dict and set(view) == {
                "being_id", "q_hex", "b_hex", "physiology_id", "check_modifier"}
                and view["being_id"] == expected_id and view["q_hex"] == 1.0.hex()
                and view["b_hex"] == 1.0.hex() and view["physiology_id"] is None
                and type(view["check_modifier"]) is int,
                "Q/B frame differs from the native Being physical state")
    _require(encounter["awareness"] == [[ids[0], [ids[1]]], [ids[1], []]],
             "Encounter Awareness differs from the isolated Spot result")
    _require(encounter["choice_counter"] == 1
             and encounter["choice_ids"] == ["npc-arena/encounter/1/draft/1"]
             and encounter["choice_states"] == [["npc-arena/encounter/1/draft/1", "finished"]]
             and encounter["reservations_empty"] is True
             and encounter["open_drafts_empty"] is True
             and encounter["tokens_empty"] is True,
             "ChoiceBook contains an unsupported pending or unfinished state")
    _require(encounter["registered_action_ids"] == ["npc-arena/action/spot-ari-bex"]
             and encounter["native_action_states"] == [["npc-arena/action/spot-ari-bex", "finished"]]
             and encounter["choice_action_state"] == "finished",
             "registered native Action and Choice state differs from committed history")
    _require(type(encounter["schedule_revision"]) is int and encounter["schedule_revision"] >= 0,
             "schedule revision is malformed")
    _require(encounter["event_registry_ids"] == ["0", "npc-arena/action/spot-ari-bex",
             "npc-arena/encounter/1"]
             and encounter["object_registry_ids"] == ids,
             "Arena registries contain missing or extra native entities")
    _require(encounter["rng_role"] == "caller_cursor"
             and encounter["rng_scope"] == "bound-process-local-cursor; exclusivity is not portable",
             "RNG authority is not the captured native caller cursor")
    _require(encounter["progression_mode"] == {
        "name": "transactional", "rng_role": "caller_cursor",
        "authority_contract": "quiescent_or_coordinated_native_access",
        "identity_scope": "verified against this live process during capture; not portable",
    }, "transactional progression mode is unsupported")
    _validate_random_state(encounter["rng_state"])
    _validate_graph(data["native_data_graph"])


def _validate_random_state(value):
    def tuple_tree(item):
        if type(item) is list:
            return tuple(tuple_tree(child) for child in item)
        if item is None or type(item) in (str, int, bool):
            return item
        raise ArenaStateRejected("RNG state contains unsupported data")
    try:
        probe = random.Random()
        probe.setstate(tuple_tree(value))
    except (TypeError, ValueError) as exc:
        raise ArenaStateRejected(f"invalid native RNG state: {exc}") from exc


def _decode_payload(wire):
    if type(wire) is not bytes or not wire or len(wire) > MAX_WIRE_BYTES:
        raise ArenaStateRejected("state candidate is empty or exceeds its size limit")
    try:
        data = json.loads(wire.decode("utf-8"), object_pairs_hook=_pairs_no_duplicates)
    except ArenaStateRejected:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ArenaStateRejected(f"invalid state-candidate JSON: {exc}") from None
    _validate_payload(data)
    _require(_canonical(data) == wire, "state candidate is not canonical JSON")
    return data


def decode_arena_post_spot_state(wire):
    """Decode an inert candidate and reject noncanonical, stale-schema bytes."""
    _decode_payload(wire)
    return ArenaPostSpotStateCandidate(bytes(wire))


def _identity_data(identity):
    return [identity.encounter_id, identity.boundary, identity.source_action_id,
            identity.channel, identity.slot]


def _inspection_tree(value, *, depth=0):
    """Encode only the frozen Encounter-inspection classes used by this Arena."""
    if depth > 80:
        raise ArenaStateRejected("Target history projection exceeds the supported depth")
    if value is None or type(value) in (str, bool, int, float):
        if type(value) is float and not math.isfinite(value):
            raise ArenaStateRejected("Target history contains a non-finite value")
        return value
    if type(value) in (tuple, list, set, frozenset):
        rows = value if type(value) in (tuple, list) else sorted(value, key=repr)
        return tuple(_inspection_tree(row, depth=depth + 1) for row in rows)
    if type(value) in (dict, MappingProxyType):
        return tuple((key, _inspection_tree(item, depth=depth + 1))
                     for key, item in sorted(value.items(), key=lambda row: str(row[0])))
    from encounter_inspection import TargetInspection, EntityInspection
    from action_settlement import TargetCandidate
    from action_evaluation import EffectIdentity, IdentifiedEffect, AwarenessEffect
    from frozen_practice import PracticeProjection
    from observer_proposals import ObserverProjection
    from action_evaluation import native_data
    from spatial.state import CartesianPosition
    allowed = (TargetInspection, TargetCandidate, EntityInspection, EffectIdentity,
               IdentifiedEffect, AwarenessEffect, PracticeProjection,
               ObserverProjection, CartesianPosition)
    if type(value) not in allowed:
        raise ArenaStateRejected("Target history contains an unreviewed inspection type")
    data = native_data(value, allowed)
    tag = type(value).__module__ + "." + type(value).__name__
    return ("inspection-dataclass", tag, tuple((key, _inspection_tree(item, depth=depth + 1))
            for key, item in sorted(data.items())))


def _target_history_row(record):
    state = record.state
    return {
        "boundary": record.boundary,
        "position_hex": [float(v).hex() for v in record.position.as_tuple()],
        "projected_hp_hex": _hex(state.projected_hp, "Target HP"),
        "actual_damage_hex": _hex(state.actual_damage, "Target damage"),
        "aware_of": sorted(state.aware_of),
        "incoming_effect_ids": [_identity_data(effect.identity) for effect in state.incoming],
        "outgoing_effect_ids": [_identity_data(identity) for identity in state.outgoing_effect_ids],
        "practice_empty": not (state.practice_state.ordinary_levels
            or state.practice_state.weapon_levels or state.practice_state.baselines
            or state.practice_state.skill_experience or state.practice_state.prior_uses
            or state.practice_state.exercises or state.practice_state.transitions),
        "observer_effects_empty": not (state.observer_state.observations
            or state.observer_state.interpretations or state.observer_state.heard_accounts
            or state.observer_state.belief_recipient_ids),
    }


def _capture_payload(summary, prefix):
    from arena_history_prefix import capture_arena_history_prefix
    from atomic_publication import coordinated_access
    from being import BeingInstance
    from checkpoint_adapters import NativeInventory, _fields
    from checkpoint_inventory import _Inventory
    from spatial.geometry import Sphere
    from transactional_progression import _BINDINGS
    from universe import Universe
    from encounter import Encounter

    _require(type(summary) is dict and type(prefix) is ArenaSpotHistoryPrefix,
             "native Arena summary and validated prefix are required")
    encounter = summary.get("encounter")
    _require(type(encounter) is Encounter, "native Encounter is required")
    world = encounter.universe
    _require(type(world) is Universe, "native Universe is required")
    try:
        with coordinated_access(world):
            current_prefix = capture_arena_history_prefix(summary)
            _require(current_prefix.to_bytes() == prefix.to_bytes(),
                     "history prefix is stale relative to native Arena state")
            _require(world.event_history.get(encounter.id) is encounter,
                     "Encounter is not registered by identity in its Universe")
            universe_fields = _fields(world)
            _require(set(universe_fields) == _UNIVERSE_FIELDS
                     and world.type == "Universe"
                     and type(world.name) is str and type(world.library.id) is str,
                     "Universe has an unrepresented field or invalid Library identity")
            ids = tuple(summary["candidate_bindings"][i].native_being_id for i in range(2))
            _require(ids == ("arena/being/ari", "arena/being/bex"),
                     "only the explicit Ari/Bex native bindings are supported")
            _require(tuple(encounter.being_list) == ids
                     and encounter.non_being_object_list == [],
                     "Arena participant set/order differs from the reviewed fixture")
            _require(set(world.object_registry.object_instances) == set(ids),
                     "Arena Universe has extra or missing Objects")
            _require(set(world.event_history) == {"0", encounter.id,
                     "npc-arena/action/spot-ari-bex"},
                     "Arena Event registry has unsupported extra or missing records")
            _require(encounter.start_time == 0 and encounter.time == 6
                     and encounter.last_processed_boundary == 6
                     and encounter._coordinator_time == 6 and encounter._interval_start == 6
                     and encounter.active_boundary is None and encounter.boundary_fault is None
                     and not encounter.pending_action_list and not encounter.cancelled_action_list,
                     "Encounter is not quiescent at committed boundary 6")
            from checkpoint_adapters import _fields
            encounter_native_fields = _fields(encounter)
            _require(set(encounter_native_fields) == _ENCOUNTER_FIELDS,
                     "Encounter has an unrepresented native field")
            _require(not encounter._advancing and not encounter._running
                     and not encounter._dispatching and encounter._boundary_context is None
                     and encounter._active_fatigue_frame is None
                     and encounter._physiology_registry is None
                     and encounter.initiation is None and encounter.end_time is None
                     and encounter.event_type is None and encounter.location is None
                     and encounter.parent_event_id is None and encounter.map is None
                     and encounter.local_frame is None and encounter.name == "",
                     "Encounter has unsupported lifecycle, fatigue, location or planning state")
            _require(type(encounter.arena_activation_enabled) is bool
                     and not encounter.arena_activation_enabled
                     and encounter.arena_activation is None
                     and encounter.arena_movement_activation is None,
                     "Arena activation records are outside the detached six-boundary Spot subset")
            view = encounter.inspect_committed(6)
            _require(view.boundary == 6 and view.latest_boundary == 6
                     and tuple(view.participants) == ids,
                     "native inspection does not describe the six-boundary Arena")
            spot = view.action("npc-arena/action/spot-ari-bex")
            _require(spot.facts.outcome == "success" and spot.resolved_boundary == 6,
                     "native Spot is not the committed successful boundary-6 Action")
            history_rows = []
            for being_id in ids:
                rows = tuple(view.histories[being_id])
                _require(tuple(row.boundary for row in rows) == (1, 2, 3, 4, 5, 6),
                         "Target-owned history does not contain each committed boundary")
                live = world.get_object_by_id(being_id)
                _require(type(live) is BeingInstance and live.id == being_id
                         and encounter.get_being(being_id) is live,
                         "participant identity is not shared by registry and Encounter")
                _require(len(live._atomic_target_history) == 6,
                         "live Target history and committed inspection disagree")
                history_rows.append({"target_id": being_id,
                    "boundaries": [_target_history_row(row) for row in rows]})
            # The existing reviewed native-field adapters reject unknown fields
            # and unsupported definition graphs before this candidate is emitted.
            adapter = NativeInventory(world, encounter, ())
            definitions = world.library.being_dictionary.objects
            _require(type(definitions) is dict and type(definitions.get("Human")).__name__ == "BeingDefinition",
                     "Arena's referenced native Human definition is unavailable")
            mutable_owners = {}
            adapter._validate_being_definition(definitions["Human"])
            adapter._closed_definition_value(
                definitions["Human"], owner=("library-definition", "Human"),
                mutable_owners=mutable_owners)
            inventory = _Inventory()
            inventory._capture_world = world
            inventory.emitted = set()
            native_graph_roots = []
            participant_rows = []
            for being_id, binding in zip(ids, summary["candidate_bindings"]):
                being = world.get_object_by_id(being_id)
                d = _fields(being)
                _require(d["original"] is definitions["Human"]
                         and type(d["current"]) is type(definitions["Human"])
                         and d["current"] is not d["original"],
                         "participant original/current definition references are inconsistent")
                adapter._validate_being_definition(d["current"])
                adapter._closed_definition_value(
                    d["current"], owner=("being-current", being_id),
                    mutable_owners=mutable_owners)
                _require(type(d["geometry"]) is Sphere
                         and d["geometry"].radius == 0.5,
                         "Arena participant geometry is not the authored Sphere(0.5)")
                _require(not d["possessions"] and not d["weapons"]
                         and not d["skill_experience"] and not d["skill_use_history"]
                         and not d["_skill_practice_baselines"] and d["personal_history"] is None,
                         "Arena participant has unsupported inventory/practice/history additions")
                # The six detached TargetInspection rows replace process-local
                # receipt references in _atomic_target_history. Their actual
                # native-derived contents remain included below.
                being_fields = {key: value for key, value in d.items()
                                if key != "_atomic_target_history"}
                being_fields["_atomic_target_history"] = tuple(
                    _inspection_tree(row) for row in view.histories[being_id])
                root = ("arena-being", being_id, tuple(sorted(being_fields.items())))
                inventory.anchor(definitions["Human"], ("library-definition", "Human"))
                inventory.anchor(d["original"], ("library-definition", "Human"))
                inventory.anchor(d["current"], ("being-current-definition", being_id))
                graph_root = inventory.value(root, ("arena-state", being_id))
                native_graph_roots.append(graph_root)
                position = being.get_position()
                _require(position is not None, "Arena Being has no native Cartesian position")
                phex = [float(v).hex() for v in position.as_tuple()]
                awareness = sorted(encounter.awareness.get(being_id, set()))
                target_final = view.target(being_id)
                _require(tuple(target_final.position.as_tuple()) == tuple(position.as_tuple()),
                         "live Being location differs from committed Target inspection")
                _require(tuple(sorted(target_final.state.aware_of)) == tuple(awareness),
                         "live Awareness differs from committed Target state")
                def_graph = _Inventory()
                def_graph._capture_world = world
                def_graph.emitted = set()
                def_graph.anchor(d["original"], ("definition", "Human"))
                def_graph.anchor(d["current"], ("being-current-definition", being_id))
                original_ref = def_graph.value(d["original"], ("definition", "Human"))
                current_ref = def_graph.value(d["current"], ("being-current-definition", being_id))
                _require(not def_graph.diagnostics,
                         "native definition contains an unreviewed value")
                definition_bytes = _canonical(_to_json_data(
                    ((original_ref, current_ref), tuple(def_graph.nodes))))
                participant_rows.append({
                    "being_id": being_id, "name": being.name,
                    "native_type": "BeingInstance", "definition_name": "Human",
                    "definition_graph_sha256": hashlib.sha256(definition_bytes).hexdigest(),
                    "position_hex": phex,
                    "geometry": {"kind": "Sphere", "radius_hex": float(d["geometry"].radius).hex()},
                    "top_facing": d["top_facing"], "front_facing": d["front_facing"],
                    "hit_points_hex": _hex(being.get_hit_points(), "Being HP"),
                    "aware_of": awareness, "target_history_boundaries": [1, 2, 3, 4, 5, 6],
                })
            from encounter_fatigue_bridge import FrozenFatigueFrame
            _require(type(encounter.last_fatigue_frame) is FrozenFatigueFrame
                     and len(encounter.fatigue_frame_history) == 6,
                     "native Q/B freeze-frame history is incomplete")
            frame_root = inventory.value(encounter.last_fatigue_frame,
                ("arena-encounter", encounter.id, "last_fatigue_frame"))
            fatigue_frames = []
            for boundary, frame in enumerate(encounter.fatigue_frame_history, 1):
                _require(type(frame) is dict and set(frame) == {"start", "time", "views"}
                         and frame["start"] == boundary - 1 and frame["time"] == boundary
                         and type(frame["views"]) is dict and set(frame["views"]) == set(ids),
                         "native Q/B freeze-frame history is outside the Arena case")
                fatigue_frames.append({"start": frame["start"], "time": frame["time"],
                    "views": [{"being_id": being_id,
                        "q_hex": _hex(frame["views"][being_id]["q"], "Q/B q"),
                        "b_hex": _hex(frame["views"][being_id]["b"], "Q/B b"),
                        "physiology_id": frame["views"][being_id]["physiology_id"],
                        "check_modifier": frame["views"][being_id]["check_modifier"]}
                        for being_id in ids]})
            graph_payload = {"root": native_graph_roots + [frame_root], "nodes": inventory.nodes}
            _require(not inventory.diagnostics,
                     "Being state graph contains an unreviewed native value: "
                     + repr(tuple((row.code, row.owner, row.field) for row in inventory.diagnostics[:12])))
            _validate_graph(_to_json_data(graph_payload))
            choice_book = encounter._choice_book
            choice_fields = _fields(choice_book)
            _require(set(choice_fields) == _CHOICE_BOOK_FIELDS
                     and choice_book.encounter is encounter
                     and choice_book.lock is world._schedule_lock,
                     "ChoiceBook has an unrepresented field or foreign ownership")
            from action_choice import _Accepted
            _require(set(choice_book._drafts) == set(choice_book._closed_drafts)
                     == set(choice_book._choices) and not choice_book._tokens
                     and not choice_book._reservations and len(choice_book._choices) == 1,
                     "Arena ChoiceBook contains an open draft, token, reservation or extra Choice")
            _require(world._choice_books == [choice_book],
                     "Universe ChoiceBook registry is not uniquely bound to this Encounter")
            reproduction_registry = world._reproduction_group_registry
            _require(set(vars(reproduction_registry)) == _REPRODUCTION_REGISTRY_FIELDS
                     and reproduction_registry._world is world
                     and reproduction_registry.world_identity == id(world)
                     and not reproduction_registry._groups_by_id
                     and not reproduction_registry._group_id_aliases
                     and not reproduction_registry._group_id_by_parent_set
                     and not reproduction_registry._group_id_by_offspring
                     and not reproduction_registry._parent_set_by_offspring
                     and not reproduction_registry._person_id_reservations
                     and not reproduction_registry._group_id_reservations
                     and not reproduction_registry._requests
                     and not reproduction_registry._offspring_origin_ticks
                     and not reproduction_registry._generation_requests
                     and not reproduction_registry._generation_parent_set_scopes
                     and not reproduction_registry._progressive_histories
                     and not reproduction_registry._progressive_parent_set_scopes
                     and not reproduction_registry._progressive_requests
                     and not reproduction_registry._native_beings_by_person_id
                     and not reproduction_registry._native_being_requests
                     and reproduction_registry._revision == 0,
                     "Arena Universe has unsupported ReproductionGroup Reality")
            _require(len(encounter._atomic_interval_history) == 6
                     and all(type(row).__name__ == "PublishedInterval"
                         and row.committed and row.encounter_id == encounter.id
                         and row.boundary == boundary
                         for boundary, row in enumerate(encounter._atomic_interval_history, 1)),
                     "committed native boundary history is not exactly the six-boundary Arena")
            choice_id, accepted = next(iter(choice_book._choices.items()))
            _require(type(accepted) is _Accepted and accepted.view.state == "finished"
                     and tuple(accepted.view.action_ids) == ("npc-arena/action/spot-ari-bex",)
                     and tuple(encounter.finished_action_list) == accepted.view.action_ids,
                     "Arena Choice/Action lifecycle is not exactly the committed Spot")
            action_id = "npc-arena/action/spot-ari-bex"
            action = world.event_history.get(action_id)
            _require(action is not None and action.id == action_id
                     and type(action).__module__ == "activities"
                     and type(action).__name__ == "SpotAction"
                     and action.actor_id == ids[0] and action.target_id == ids[1]
                     and action.start_time == 0 and action.end_time == 6,
                     "native Spot Action identity/declaration differs from the history prefix")
            action_native_fields = _fields(action)
            _require(set(action_native_fields) == _SPOT_ACTION_FIELDS
                     and action._activity_started is True
                     and action.roll is None and action.path_status is None
                     and action.start_time == 0 and action.end_time == 6
                     and action.actor_id == ids[0] and action.target_id == ids[1]
                     and action.instrument_id is None and action.location is None
                     and action.parent_event_id == encounter.id
                     and action.universe is world and action._encounter is encounter
                     and action.ledger is None and action.group_fully_visible is False,
                     "native Spot Action has unsupported declaration or mutable state")
            prefix_effect_ids = tuple(tuple(row["identity"])
                for row in prefix.payload()["effects"])
            _require(tuple(tuple(_identity_data(identity)) for identity in action._atomic_effect_ids)
                     == prefix_effect_ids
                     and action._atomic_lifecycle is not None
                     and action._atomic_lifecycle.status == "finished"
                     and action._atomic_lifecycle.boundary == 6
                     and action._atomic_lifecycle.choice_id == choice_id,
                     "native Spot Action causal lifecycle differs from its validated prefix")
            registered = choice_book._registered.get(action_id)
            _require(type(registered) is tuple and len(registered) == 3
                     and registered[0] == choice_id
                     and choice_book._states == {action_id: "finished"},
                     "ChoiceBook native Action registration state differs from history")
            prepared = registered[1]
            from scheduling import PreparedSchedule
            _require(type(prepared) is PreparedSchedule
                     and prepared.action_id == action_id and prepared.actor_id == ids[0]
                     and prepared.target_id == ids[1] and prepared.start_time == 0
                     and prepared.end_time == 6,
                     "finished native Action registration descriptor is inconsistent")
            from transactional_progression import _BINDINGS
            progress = _BINDINGS.get(id(encounter))
            _require(progress is not None and progress.encounter() is encounter
                     and progress.rng_owner is summary["rng"],
                     "Encounter has no exact process-local caller RNG binding")
            from atomic_publication import RNGCursor
            _require(type(progress.rng_owner) is RNGCursor
                     and progress.mode.rng_role == "caller_cursor"
                     and progress.mode.name == "transactional"
                     and progress.mode.authority_contract == "quiescent_or_coordinated_native_access"
                     and progress.mode.encounter_identity == id(encounter)
                     and progress.mode.rng_owner_identity == id(progress.rng_owner),
                     "Arena RNG owner is not the reviewed native caller cursor")
            from interval_staging import _rng_input
            role, owner_identity, rng_state = _rng_input(encounter, None, progress.rng_owner)
            _require(role == "caller_cursor" and owner_identity == id(progress.rng_owner),
                     "native RNG capture role/owner differs from transactional binding")
            _validate_random_state(_to_json_data(rng_state))
            scenario = {
                "universe_id": world.id, "universe_name": world.name,
                "library_id": world.library.id, "encounter_id": encounter.id,
                "start_time_hex": float(encounter.start_time).hex(),
                "time_hex": float(encounter.time).hex(),
                "committed_boundary": encounter.last_processed_boundary,
                "difficulty_class_hex": float(encounter.difficulty_class).hex(),
                "initiated": encounter.initiated,
            }
            bindings = [{
                "binding_key": source.binding_key,
                "source_sha256": candidate.content_sha256,
                "source_bytes_base64": base64.b64encode(candidate.source_bytes).decode("ascii"),
                "display_name": candidate.display_name,
                "native_being_id": source.native_being_id,
                "native_definition_name": source.native_definition_name,
                "position_hex": [float(v).hex() for v in source.position],
            } for candidate, source in zip(
                (summary["candidates"]["ari"], summary["candidates"]["bex"]),
                summary["candidate_bindings"])]
            encounter_data = {
                "name": encounter.name, "native_type": encounter.type,
                "end_time_hex": None,
                "event_type": encounter.event_type, "location": encounter.location,
                "parent_event_id": encounter.parent_event_id, "map": encounter.map,
                "local_frame": encounter.local_frame, "initiation": encounter.initiation,
                "active_fatigue_frame": None, "physiology_registry": None,
                "last_fatigue_frame_boundary": 6,
                "fatigue_frame_history": fatigue_frames,
                "receipt_history_scope": "native process-local receipts omitted; prefix is a detached claim",
                "receipt_record_count": len(encounter._atomic_interval_history),
                "reproduction_registry_empty": True,
                "universe_choice_books_count": len(world._choice_books),
                "start_time_hex": float(encounter.start_time).hex(),
                "time_hex": float(encounter.time).hex(),
                "last_processed_boundary": encounter.last_processed_boundary,
                "coordinator_time_hex": float(encounter._coordinator_time).hex(),
                "interval_start_hex": float(encounter._interval_start).hex(),
                "difficulty_class_hex": float(encounter.difficulty_class).hex(),
                "initiated": encounter.initiated,
                "participant_ids": list(ids),
                "non_being_object_ids": list(encounter.non_being_object_list),
                "pending_action_ids": list(encounter.pending_action_list),
                "finished_action_ids": list(encounter.finished_action_list),
                "cancelled_action_ids": list(encounter.cancelled_action_list),
                "active_boundary": encounter.active_boundary,
                "boundary_fault": encounter.boundary_fault,
                "awareness": [[observer, sorted(encounter.awareness.get(observer, set()))]
                               for observer in ids],
                "choice_counter": choice_book._counter,
                "choice_ids": [choice_id],
                "choice_states": [[choice_id, accepted.view.state]],
                "registered_action_ids": sorted(choice_book._registered),
                "native_action_states": sorted([action_id, state]
                    for action_id, state in choice_book._states.items()),
                "choice_action_state": choice_book._states.get("npc-arena/action/spot-ari-bex"),
                "reservations_empty": not choice_book._reservations,
                "open_drafts_empty": not (set(choice_book._drafts) - choice_book._closed_drafts),
                "tokens_empty": not choice_book._tokens,
                "schedule_revision": world._schedule_revision,
                "event_registry_ids": sorted(world.event_history),
                "object_registry_ids": sorted(world.object_registry.object_instances),
                "rng_role": role,
                "rng_scope": "bound-process-local-cursor; exclusivity is not portable",
                "rng_state": _to_json_data(rng_state),
                "progression_mode": {
                    "name": progress.mode.name,
                    "rng_role": progress.mode.rng_role,
                    "authority_contract": progress.mode.authority_contract,
                    "identity_scope": "verified against this live process during capture; not portable",
                },
            }
            source = prefix.payload()
            payload = {
                "schema": SCHEMA, "trust": TRUST,
                "history_prefix_sha256": prefix.content_sha256,
                "scenario": scenario, "source_bindings": bindings,
                "participants": participant_rows, "target_histories": history_rows,
                "encounter": encounter_data,
                "native_data_graph": _to_json_data(graph_payload),
            }
            # Preserve all source binding bytes/digests from the exact prefix.
            _require(len(source["npc_bindings"]) == len(bindings),
                     "native source binding count differs from historical prefix")
            _validate_payload(dict(payload, content_sha256=hashlib.sha256(_canonical(payload)).hexdigest()))
            return _encode_payload(payload)
    except ArenaStateRejected:
        raise
    except (ArenaHistoryRejected, TypeError, ValueError, AttributeError, KeyError,
            IndexError, RuntimeError) as exc:
        raise ArenaStateRejected(f"Arena state capture refused: {exc}") from exc


def _encode_payload(payload):
    body = _canonical(payload)
    envelope = dict(payload, content_sha256=hashlib.sha256(body).hexdigest())
    wire = _canonical(envelope)
    _require(len(wire) <= MAX_WIRE_BYTES, "state candidate exceeds its wire size limit")
    return ArenaPostSpotStateCandidate(wire)


def capture_arena_post_spot_state(summary, prefix=None):
    """Capture the one reviewed native Arena state under coordinated read access."""
    if prefix is None:
        prefix = capture_arena_history_prefix(summary)
    return _capture_payload(summary, prefix)


def _prefix_expected(prefix):
    data = prefix.payload()
    return {
        "universe_id": data["universe_id"],
        "encounter_id": data["encounter_id"],
        "action_id": data["spot"]["action_id"],
        "actor_id": data["spot"]["actor_id"],
        "target_id": data["spot"]["target_id"],
        "start_time_hex": data["start_time"],
        "through_boundary": data["through_boundary"],
    }


def _validate_against_history(data, prefix, accepted_view):
    from arena_history_admission import HostAcceptedArenaHistoryView
    _require(type(prefix) is ArenaSpotHistoryPrefix,
             "a validated Arena historical prefix is required")
    _require(type(accepted_view) is HostAcceptedArenaHistoryView,
             "the separately host-accepted 003B1 history view is required")
    expected = _prefix_expected(prefix)
    _require(data["history_prefix_sha256"] == prefix.content_sha256,
             "state candidate is bound to a different historical-prefix digest")
    scenario = data["scenario"]
    _require(scenario["universe_id"] == expected["universe_id"]
             and scenario["encounter_id"] == expected["encounter_id"]
             and scenario["start_time_hex"] == expected["start_time_hex"]
             and scenario["committed_boundary"] == expected["through_boundary"]
             and accepted_view.universe_id == scenario["universe_id"]
             and accepted_view.encounter_id == scenario["encounter_id"]
             and accepted_view.through_boundary == scenario["committed_boundary"],
             "candidate, prefix and host-accepted view identify different Arena histories")
    _require(accepted_view.spot.action_id == expected["action_id"]
             and accepted_view.spot.actor_id == expected["actor_id"]
             and accepted_view.spot.target_id == expected["target_id"]
             and accepted_view.spot.outcome == "success"
             and accepted_view.spot.resolved_boundary == 6,
             "host-accepted historical Spot differs from the candidate")
    prefix_payload = prefix.payload()
    view_bindings = {row.native_being_id: row for row in accepted_view.npc_bindings}
    _require(len(view_bindings) == 2, "host view has an unexpected NPC binding count")
    for source, binding, participant in zip(prefix_payload["npc_bindings"],
                                           data["source_bindings"], data["participants"]):
        raw = base64.b64decode(binding["source_bytes_base64"], validate=True)
        _require(source["source_bytes_base64"] == binding["source_bytes_base64"]
                 and source["source_sha256"] == binding["source_sha256"]
                 and source["native_being_id"] == binding["native_being_id"]
                 and source["native_definition_name"] == binding["native_definition_name"]
                 and source["position"] == binding["position_hex"]
                 and hashlib.sha256(raw).hexdigest() == binding["source_sha256"],
                 "candidate source bytes/digest/native binding differ from the prefix")
        accepted = view_bindings.get(binding["native_being_id"])
        _require(accepted is not None and accepted.source_bytes == raw
                 and accepted.source_sha256 == binding["source_sha256"]
                 and accepted.display_name == binding["display_name"]
                 and accepted.native_definition_name == binding["native_definition_name"]
                 and tuple(accepted.position_hex) == tuple(binding["position_hex"]),
                 "candidate source binding differs from the host-accepted historical view")
        _require(participant["being_id"] == binding["native_being_id"]
                 and participant["name"] == binding["display_name"]
                 and participant["definition_name"] == binding["native_definition_name"]
                 and participant["position_hex"] == binding["position_hex"],
                 "native participant identity/source/display/position binding mismatch")
    prefix_targets = {row["being_id"]: row for row in prefix_payload["targets"]}
    _require(set(prefix_targets) == {row["being_id"] for row in data["participants"]},
             "candidate participant set differs from historical Target set")
    histories = {row["target_id"]: row for row in data["target_histories"]}
    for participant in data["participants"]:
        target = prefix_targets[participant["being_id"]]
        _require(target["position"] == participant["position_hex"]
                 and target["aware_of"] == participant["aware_of"],
                 "post-Spot native position/Awareness contradicts historical Target state")
        last = histories[participant["being_id"]]["boundaries"][-1]
        _require(last["position_hex"] == participant["position_hex"]
                 and last["aware_of"] == participant["aware_of"],
                 "latest Target-owned candidate history contradicts the prefix")
        expected_awareness = ([expected["target_id"]]
                              if participant["being_id"] == expected["actor_id"] else [])
        rows = histories[participant["being_id"]]["boundaries"]
        _require(all(row["actual_damage_hex"] == 0.0.hex()
                     and row["aware_of"] == (expected_awareness if row["boundary"] == 6 else [])
                     and (row["boundary"] == 6 or not row["incoming_effect_ids"]
                          and not row["outgoing_effect_ids"])
                     for row in rows),
                 "Target history contains an unsupported pre-Spot effect, damage, or Awareness")
        _require(all(row["projected_hp_hex"] == participant["hit_points_hex"] for row in rows),
                 "Target-owned HP history differs from the current native Being state")
    action_effect_ids = [row["identity"] for row in prefix_payload["effects"]
                         if row["identity"][3] == "effect"]
    ari_history = histories[expected["actor_id"]]["boundaries"][-1]
    _require(ari_history["incoming_effect_ids"] == action_effect_ids,
             "Target-owned causal effect history differs from the detached history prefix")
    ari_outgoing = histories[expected["actor_id"]]["boundaries"][-1]["outgoing_effect_ids"]
    all_effect_ids = [row["identity"] for row in prefix_payload["effects"]]
    _require(ari_outgoing == all_effect_ids,
             "Action actor history differs from all causal lifecycle/effect identities")
    _require(histories[expected["target_id"]]["boundaries"][-1]["incoming_effect_ids"] == [],
             "Spot Awareness was incorrectly assigned to the observed Target")
    _require(accepted_view.boundaries == (1, 2, 3, 4, 5, 6),
             "host-accepted history has a missing, extra or unordered boundary")


def validate_arena_post_spot_state(candidate, prefix, accepted_view):
    """Check canonical data and history consistency; this does not authorize it."""
    _require(type(candidate) is ArenaPostSpotStateCandidate,
             "native Arena state candidate is required")
    data = _decode_payload(candidate._wire)
    _validate_against_history(data, prefix, accepted_view)
    return candidate.view()
