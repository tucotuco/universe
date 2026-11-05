"""Detached, data-only history for the fixed native Ari/Bex Spot Arena.

This is a portable historical claim, not a receipt, Encounter restore format,
or proof that an exporter was authentic. Capture reads an already committed
Encounter through its native inspector; decode never imports the publisher or
installs data into a live Universe.
"""
from dataclasses import dataclass
import base64
import hashlib
import json
import math


SCHEMA = "universe.arena.detached-spot-history-prefix/1"
TRUST_LABEL = "detached historical claim; original publisher authenticity is not portable"
_TOP_FIELDS = frozenset((
    "schema", "trust", "universe_id", "encounter_id", "start_time",
    "through_boundary", "boundaries", "spot", "effects", "targets",
    "npc_bindings", "content_sha256",
))
_BOUNDARY_FIELDS = frozenset(("boundary", "start_time", "action_ids", "effect_ids"))
_SPOT_FIELDS = frozenset((
    "action_id", "actor_id", "target_id", "start_time", "nominal_end",
    "resolved_boundary", "outcome", "metadata",
))
_EFFECT_FIELDS = frozenset(("identity", "kind", "data"))
_TARGET_FIELDS = frozenset(("being_id", "position", "aware_of"))
_BINDING_FIELDS = frozenset((
    "binding_key", "source_bytes_base64", "source_sha256", "display_name",
    "native_being_id", "native_definition_name", "position",
))
_METADATA_KEYS = (
    "discovery_dc", "effective_dc", "path_status", "racial_action_bonus",
    "roll", "spotting_dc_adjustment",
)
_MAX_WIRE_BYTES = 6 * 1024 * 1024


class ArenaHistoryRejected(ValueError):
    """An Arena history prefix is outside the closed six-boundary contract."""


@dataclass(frozen=True)
class ArenaSpotHistoryPrefix:
    schema: str
    trust: str
    universe_id: str
    encounter_id: str
    start_time: str
    through_boundary: int
    boundaries: tuple
    spot: object
    effects: tuple
    targets: tuple
    npc_bindings: tuple
    content_sha256: str

    def payload(self):
        return {
            "schema": self.schema,
            "trust": self.trust,
            "universe_id": self.universe_id,
            "encounter_id": self.encounter_id,
            "start_time": self.start_time,
            "through_boundary": self.through_boundary,
            "boundaries": _thaw_json(self.boundaries),
            "spot": _thaw_json(self.spot),
            "effects": _thaw_json(self.effects),
            "targets": _thaw_json(self.targets),
            "npc_bindings": _thaw_json(self.npc_bindings),
        }

    def to_bytes(self):
        """Encode the validated projection in strict canonical JSON."""
        _validate_payload(self.payload())
        body = _canonical(self.payload())
        digest = hashlib.sha256(body).hexdigest()
        if self.content_sha256 != digest:
            raise ArenaHistoryRejected("historical prefix digest does not match its data")
        envelope = dict(self.payload(), content_sha256=digest)
        return _canonical(envelope)

    def summary(self):
        """Return a detached, human-readable historical-only summary."""
        data = self.payload()
        return {
            "trust": self.trust,
            "universe_id": self.universe_id,
            "encounter_id": self.encounter_id,
            "through_boundary": self.through_boundary,
            "boundaries": tuple(row["boundary"] for row in data["boundaries"]),
            "spot": data["spot"],
            "targets": tuple(data["targets"]),
            "npc_bindings": tuple({
                "binding_key": row["binding_key"],
                "source_sha256": row["source_sha256"],
                "display_name": row["display_name"],
                "native_being_id": row["native_being_id"],
                "native_definition_name": row["native_definition_name"],
            } for row in data["npc_bindings"]),
        }


def _canonical(value):
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        raise ArenaHistoryRejected(f"Arena prefix contains unsupported JSON data: {exc}") from exc


def _pairs_no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ArenaHistoryRejected(f"duplicate JSON field {key!r}")
        result[key] = value
    return result


def _finite_hex(value, name):
    if type(value) is not str:
        raise ArenaHistoryRejected(f"{name} must be a hexadecimal binary64 value")
    try:
        number = float.fromhex(value)
    except ValueError as exc:
        raise ArenaHistoryRejected(f"{name} is not a hexadecimal binary64 value") from exc
    if not math.isfinite(number) or number.hex() != value:
        raise ArenaHistoryRejected(f"{name} is not canonical finite binary64")
    return number


def _text(value, name):
    if type(value) is not str or not value.strip():
        raise ArenaHistoryRejected(f"{name} must be nonempty text")
    return value


def _keys(value, fields, name):
    if type(value) is not dict or set(value) != fields:
        raise ArenaHistoryRejected(f"{name} has missing or unknown fields")


def _sequence(value, name):
    if type(value) is not list:
        raise ArenaHistoryRejected(f"{name} must be an array")
    return value


def _position(value, name):
    if type(value) is not list or len(value) != 3:
        raise ArenaHistoryRejected(f"{name} must contain three coordinates")
    for index, coordinate in enumerate(value):
        _finite_hex(coordinate, f"{name}[{index}]")


def _validate_payload(data):
    _keys(data, _TOP_FIELDS - {"content_sha256"}, "Arena prefix")
    if data["schema"] != SCHEMA:
        raise ArenaHistoryRejected("unsupported Arena prefix schema")
    if data["trust"] != TRUST_LABEL:
        raise ArenaHistoryRejected("unknown Arena history trust label")
    universe_id = _text(data["universe_id"], "Universe ID")
    encounter_id = _text(data["encounter_id"], "Encounter ID")
    if _finite_hex(data["start_time"], "start time") != 0.0:
        raise ArenaHistoryRejected("only the Arena Encounter starting at time zero is supported")
    if type(data["through_boundary"]) is not int or data["through_boundary"] != 6:
        raise ArenaHistoryRejected("only the six-boundary Arena prefix is supported")

    boundaries = _sequence(data["boundaries"], "boundaries")
    if len(boundaries) != 6:
        raise ArenaHistoryRejected("Arena prefix requires exactly six boundaries")
    for expected, row in enumerate(boundaries, 1):
        _keys(row, _BOUNDARY_FIELDS, f"boundary {expected}")
        if type(row["boundary"]) is not int or row["boundary"] != expected:
            raise ArenaHistoryRejected("Arena boundary history is missing, duplicate, or unordered")
        if _finite_hex(row["start_time"], f"boundary {expected} start") != expected - 1:
            raise ArenaHistoryRejected("Arena boundary chronology is inconsistent")
        action_ids = _sequence(row["action_ids"], "boundary Action IDs")
        effect_ids = _sequence(row["effect_ids"], "boundary effect IDs")
        if (any(type(value) is not str or not value for value in action_ids)
                or len(action_ids) != len(set(action_ids))):
            raise ArenaHistoryRejected("boundary Action references are invalid or duplicated")
        if any(type(value) is not list for value in effect_ids):
            raise ArenaHistoryRejected("boundary effect references must be identity arrays")
        if expected < 6 and (action_ids or effect_ids):
            raise ArenaHistoryRejected("unexpected Action/effect before the Spot commit boundary")
        if expected == 6 and len(action_ids) != 1:
            raise ArenaHistoryRejected("boundary 6 must contain exactly the Arena Spot Action")

    spot = data["spot"]
    _keys(spot, _SPOT_FIELDS, "Spot record")
    action_id = _text(spot["action_id"], "Spot Action ID")
    actor_id = _text(spot["actor_id"], "Spot actor ID")
    target_id = _text(spot["target_id"], "Spot target ID")
    if actor_id == target_id:
        raise ArenaHistoryRejected("Spot actor and target must be distinct Beings")
    if boundaries[5]["action_ids"] != [action_id]:
        raise ArenaHistoryRejected("boundary Action reference does not match Spot record")
    if (_finite_hex(spot["start_time"], "Spot start") != 0.0
            or _finite_hex(spot["nominal_end"], "Spot nominal end") != 6.0
            or type(spot["resolved_boundary"]) is not int
            or spot["resolved_boundary"] != 6 or spot["outcome"] != "success"):
        raise ArenaHistoryRejected("Spot is not the supported successful six-second Action")
    metadata = spot["metadata"]
    _keys(metadata, frozenset(_METADATA_KEYS), "Spot metadata")
    if (type(metadata["discovery_dc"]) is not int or metadata["discovery_dc"] != 15
            or type(metadata["effective_dc"]) is not int or metadata["effective_dc"] != 15
            or type(metadata["roll"]) is not int or metadata["roll"] != 20
            or type(metadata["path_status"]) is not str or metadata["path_status"] != "clear"
            or type(metadata["racial_action_bonus"]) is not int or metadata["racial_action_bonus"] != 0
            or type(metadata["spotting_dc_adjustment"]) is not int or metadata["spotting_dc_adjustment"] != 0):
        raise ArenaHistoryRejected("Spot result metadata is outside the authored Arena fixture")

    effects = _sequence(data["effects"], "effects")
    effect_ids = []
    awareness = []
    kinds = []
    for index, row in enumerate(effects):
        _keys(row, _EFFECT_FIELDS, f"effect {index}")
        identity = row["identity"]
        if (type(identity) is not list or len(identity) != 5
                or identity[0] != encounter_id or type(identity[1]) is not int
                or identity[1] != 6 or identity[2] != action_id
                or identity[3] not in ("effect", "lifecycle")
                or type(identity[4]) is not int or identity[4] < 0):
            raise ArenaHistoryRejected("Spot effect identity has a foreign Action/boundary reference")
        kind = row["kind"]
        expected_ids = {
            "awareness": [encounter_id, 6, action_id, "effect", 0],
            "action_outcome": [encounter_id, 6, action_id, "lifecycle", 0],
            "lifecycle": [encounter_id, 6, action_id, "lifecycle", 1],
        }
        if kind not in expected_ids or identity != expected_ids[kind]:
            raise ArenaHistoryRejected("Spot effect identity does not match its supported effect role")
        identity_tuple = tuple(identity)
        if identity_tuple in effect_ids:
            raise ArenaHistoryRejected("duplicate Spot effect identity")
        effect_ids.append(identity_tuple)
        kinds.append(kind)
        payload = row["data"]
        if kind == "awareness":
            if (type(payload) is not dict
                    or set(payload) != {"observer_id", "observed_id", "distance", "max_distance", "basis"}
                    or payload["observer_id"] != actor_id or payload["observed_id"] != target_id
                    or _finite_hex(payload["distance"], "Spot distance") != 3.0
                    or payload["max_distance"] is not None
                    or payload["basis"] != "spot_check_geometric_path"):
                raise ArenaHistoryRejected("unsupported or inconsistent Spot Awareness effect")
            awareness.append((payload["observer_id"], payload["observed_id"]))
        elif kind == "action_outcome":
            if payload != {"action_id": action_id, "outcome": "success"}:
                raise ArenaHistoryRejected("unsupported or inconsistent Action outcome effect")
        elif kind == "lifecycle":
            if (type(payload) is not dict
                    or set(payload) != {"status", "from_queue", "to_queue", "choice_id", "boundary"}
                    or payload["status"] != "finished" or payload["from_queue"] != "pending"
                    or payload["to_queue"] != "finished" or type(payload["choice_id"]) is not str
                    or not payload["choice_id"] or payload["boundary"] != 6):
                raise ArenaHistoryRejected("unsupported or inconsistent Spot lifecycle effect")
        else:
            raise ArenaHistoryRejected("unsupported effect in Arena Spot prefix")
    if (len(effects) != 3 or len(set(kinds)) != 3
            or set(kinds) != {"awareness", "action_outcome", "lifecycle"}):
        raise ArenaHistoryRejected("Spot prefix effect coverage is incomplete")
    if boundaries[5]["effect_ids"] != [list(row) for row in effect_ids]:
        raise ArenaHistoryRejected("boundary effect references do not match the Spot effects")
    if awareness != [(actor_id, target_id)]:
        raise ArenaHistoryRejected("Spot Awareness must belong only to its observer")

    targets = _sequence(data["targets"], "Targets")
    if len(targets) != 2:
        raise ArenaHistoryRejected("Arena prefix must contain exactly its two Spot participants")
    target_ids = []
    for row in targets:
        _keys(row, _TARGET_FIELDS, "Target row")
        target_id_value = _text(row["being_id"], "Target Being ID")
        target_ids.append(target_id_value)
        _position(row["position"], "Target position")
        aware_of = _sequence(row["aware_of"], "Target Awareness")
        if any(type(value) is not str for value in aware_of) or aware_of != sorted(set(aware_of)):
            raise ArenaHistoryRejected("Target Awareness references are duplicate or unordered")
    if sorted(target_ids) != sorted((actor_id, target_id)):
        raise ArenaHistoryRejected("Spot actor/target references do not match Target state")
    target_awareness = {row["being_id"]: tuple(row["aware_of"]) for row in targets}
    if target_awareness != {actor_id: (target_id,), target_id: ()}:
        raise ArenaHistoryRejected("Target-owned Awareness does not match the successful Spot effect")

    bindings = _sequence(data["npc_bindings"], "NPC bindings")
    if len(bindings) != 2:
        raise ArenaHistoryRejected("Arena prefix requires two NPC provenance bindings")
    from arena_npc_import import NPCandidate, NPCandidateError
    binding_keys, source_hashes, native_ids = [], [], []
    for row in bindings:
        _keys(row, _BINDING_FIELDS, "NPC binding")
        binding_keys.append(_text(row["binding_key"], "NPC binding key"))
        source_hash = _text(row["source_sha256"], "NPC source SHA-256")
        source_hashes.append(source_hash)
        native_id = _text(row["native_being_id"], "native Being binding")
        native_ids.append(native_id)
        _text(row["display_name"], "NPC display name")
        _text(row["native_definition_name"], "native definition name")
        _position(row["position"], "binding position")
        encoded = row["source_bytes_base64"]
        if type(encoded) is not str:
            raise ArenaHistoryRejected("NPC source bytes must be base64 text")
        try:
            source = base64.b64decode(encoded, validate=True)
            candidate = NPCandidate.from_json(source)
        except (ValueError, NPCandidateError) as exc:
            raise ArenaHistoryRejected(f"NPC source record is invalid: {exc}") from exc
        if (base64.b64encode(source).decode("ascii") != encoded
                or hashlib.sha256(source).hexdigest() != source_hash
                or candidate.content_sha256 != source_hash
                or candidate.display_name != row["display_name"]):
            raise ArenaHistoryRejected("NPC source bytes, digest, and binding disagree")
    if (len(set(binding_keys)) != 2 or len(set(source_hashes)) != 2
            or len(set(native_ids)) != 2 or sorted(native_ids) != sorted((actor_id, target_id))):
        raise ArenaHistoryRejected("NPC provenance bindings are duplicate or mismatched")
    expected_bindings = {
        "arena-ari": ("Ari", "arena/being/ari"),
        "arena-bex": ("Bex", "arena/being/bex"),
    }
    for binding in bindings:
        if expected_bindings.get(binding["binding_key"]) != (
                binding["display_name"], binding["native_being_id"]):
            raise ArenaHistoryRejected("NPC source binding identity does not match the Arena participant")
        target = next(row for row in targets if row["being_id"] == binding["native_being_id"])
        if target["position"] != binding["position"]:
            raise ArenaHistoryRejected("NPC binding and committed Target positions disagree")


def decode_arena_history_prefix(raw):
    """Decode and validate a detached prefix; never imports native receipts."""
    if type(raw) is not bytes:
        raise ArenaHistoryRejected("Arena prefix wire must be bytes")
    if not raw or len(raw) > _MAX_WIRE_BYTES:
        raise ArenaHistoryRejected("Arena prefix wire is empty or exceeds the closed size bound")
    try:
        data = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs_no_duplicates,
                          parse_constant=lambda value: (_ for _ in ()).throw(
                              ArenaHistoryRejected(f"invalid JSON number {value}")))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ArenaHistoryRejected("Arena prefix is not valid UTF-8 JSON") from exc
    _keys(data, _TOP_FIELDS, "Arena prefix envelope")
    digest = data["content_sha256"]
    if type(digest) is not str or len(digest) != 64:
        raise ArenaHistoryRejected("invalid Arena prefix SHA-256")
    payload = dict(data)
    payload.pop("content_sha256")
    _validate_payload(payload)
    expected = hashlib.sha256(_canonical(payload)).hexdigest()
    if digest != expected:
        raise ArenaHistoryRejected("Arena prefix content digest mismatch")
    if _canonical(data) != raw:
        raise ArenaHistoryRejected("Arena prefix JSON is not canonical")
    # Tuples inside the public object prevent callers from mutating its nested
    # records. Wire projection remains a detached copy through payload().
    return ArenaSpotHistoryPrefix(
        data["schema"], data["trust"], data["universe_id"], data["encounter_id"],
        data["start_time"], data["through_boundary"],
        tuple(_freeze_json(row) for row in data["boundaries"]),
        _freeze_json(data["spot"]), tuple(_freeze_json(row) for row in data["effects"]),
        tuple(_freeze_json(row) for row in data["targets"]),
        tuple(_freeze_json(row) for row in data["npc_bindings"]), digest)


@dataclass(frozen=True)
class _FrozenMap:
    items: tuple


def _freeze_json(value):
    if type(value) is dict:
        return _FrozenMap(tuple((key, _freeze_json(item)) for key, item in sorted(value.items())))
    if type(value) is list:
        return tuple(_freeze_json(item) for item in value)
    return value


def _thaw_json(value):
    if type(value) is _FrozenMap:
        return {key: _thaw_json(item) for key, item in value.items}
    if type(value) is tuple:
        return [_thaw_json(row) for row in value]
    return value


def _new_prefix(data):
    """Validate primitive capture data and seal one immutable value."""
    _validate_payload(data)
    digest = hashlib.sha256(_canonical(data)).hexdigest()
    wire = dict(data, content_sha256=digest)
    return decode_arena_history_prefix(_canonical(wire))


def _capture_arena_history_prefix_locked(summary):
    """Project one coherent Arena state while native read ownership is held."""
    from action_evaluation import AwarenessEffect, EffectIdentity
    from arena_npc_import import NPCandidate
    from encounter_inspection import InspectionRejected
    from observer_proposals import ActionOutcomeEffect, LifecycleEffect

    if type(summary) is not dict or not {"encounter", "candidate_bindings", "candidates"} <= set(summary):
        raise ArenaHistoryRejected("Arena scenario summary is incomplete")
    encounter = summary["encounter"]
    if (encounter.time != 6 or encounter.last_processed_boundary != 6
            or tuple(row.boundary for row in encounter._atomic_interval_history) != (1, 2, 3, 4, 5, 6)):
        raise ArenaHistoryRejected("capture requires six committed native Arena boundaries")
    try:
        inspection = encounter.inspect_committed(6)
    except (InspectionRejected, TypeError, ValueError) as exc:
        raise ArenaHistoryRejected(f"native committed inspection refused: {exc}") from exc
    if inspection.encounter_id != encounter.id or inspection.latest_boundary != 6:
        raise ArenaHistoryRejected("native inspection belongs to another Encounter or boundary")
    action_ids = tuple(inspection.actions)
    if len(action_ids) != 1:
        raise ArenaHistoryRejected("Arena inspection must contain exactly one committed Spot Action")
    action = inspection.action(action_ids[0])
    declaration, facts = action.declaration, action.facts
    if (declaration.family != "spot" or declaration.boundary != 6
            or facts.outcome != "success" or action.resolved_boundary != 6):
        raise ArenaHistoryRejected("Arena Action is not a successful native six-second Spot")
    if tuple(row.boundary for row in inspection.timeline) != (1, 2, 3, 4, 5, 6):
        raise ArenaHistoryRejected("native inspection does not contain contiguous boundaries 1 through 6")

    boundaries = []
    for row in inspection.timeline:
        boundaries.append({
            "boundary": row.boundary,
            "start_time": float(row.start).hex(),
            "action_ids": list(row.action_ids),
            "effect_ids": [_effect_id(identity) for identity in row.effect_ids],
        })
    metadata = dict(facts.metadata)
    if set(metadata) != set(_METADATA_KEYS):
        raise ArenaHistoryRejected("Spot result contains unsupported or incomplete metadata")
    spot = {
        "action_id": declaration.id,
        "actor_id": declaration.actor_id,
        "target_id": declaration.target_id,
        "start_time": float(declaration.start).hex(),
        "nominal_end": float(declaration.nominal_end).hex(),
        "resolved_boundary": action.resolved_boundary,
        "outcome": facts.outcome,
        "metadata": {key: metadata[key] for key in _METADATA_KEYS if key in metadata},
    }
    effects = []
    for identity, identified in inspection.effects.items():
        effect = identified.effect
        if type(effect) is AwarenessEffect:
            kind = "awareness"
            payload = {
                "observer_id": effect.target_id,
                "observed_id": effect.observed_id,
                "distance": float(effect.distance).hex(),
                "max_distance": effect.max_distance,
                "basis": effect.basis,
            }
        elif type(effect) is ActionOutcomeEffect:
            kind = "action_outcome"
            payload = {"action_id": effect.action_id, "outcome": effect.outcome}
        elif type(effect) is LifecycleEffect:
            kind = "lifecycle"
            payload = {
                "status": effect.status, "from_queue": effect.from_queue,
                "to_queue": effect.to_queue, "choice_id": effect.choice_id,
                "boundary": effect.boundary,
            }
        else:
            raise ArenaHistoryRejected(f"unsupported committed Spot effect: {type(effect).__name__}")
        effects.append({"identity": _effect_id(identity), "kind": kind, "data": payload})
    effects.sort(key=lambda row: tuple(row["identity"]))

    targets = []
    for being_id in sorted(inspection.targets):
        target = inspection.target(being_id)
        targets.append({
            "being_id": being_id,
            "position": [float(value).hex() for value in target.position.as_tuple()],
            "aware_of": sorted(target.state.aware_of),
        })

    bindings = []
    if len(summary["candidate_bindings"]) != 2:
        raise ArenaHistoryRejected("Arena scenario must contain exactly two native bindings")
    for binding in sorted(summary["candidate_bindings"], key=lambda row: row.native_being_id):
        candidate = summary["candidates"].get(binding.display_name.lower())
        if type(candidate) is not NPCandidate:
            raise ArenaHistoryRejected("Arena NPC candidate binding is missing")
        if candidate.content_sha256 != binding.source_sha256:
            raise ArenaHistoryRejected("NPC candidate and native binding source digest disagree")
        bindings.append({
            "binding_key": binding.binding_key,
            "source_bytes_base64": base64.b64encode(candidate.source_bytes).decode("ascii"),
            "source_sha256": candidate.content_sha256,
            "display_name": binding.display_name,
            "native_being_id": binding.native_being_id,
            "native_definition_name": binding.native_definition_name,
            "position": [float(value).hex() for value in binding.position],
        })

    data = {
        "schema": SCHEMA,
        "trust": TRUST_LABEL,
        "universe_id": encounter.universe.id,
        "encounter_id": encounter.id,
        "start_time": float(encounter.start_time).hex(),
        "through_boundary": 6,
        "boundaries": boundaries,
        "spot": spot,
        "effects": effects,
        "targets": targets,
        "npc_bindings": bindings,
    }
    return _new_prefix(data)


def capture_arena_history_prefix(summary):
    """Project the committed six-boundary Arena under native read ownership."""
    if type(summary) is not dict or "encounter" not in summary:
        raise ArenaHistoryRejected("Arena scenario summary is incomplete")
    encounter = summary["encounter"]
    try:
        world = encounter.universe
    except AttributeError as exc:
        raise ArenaHistoryRejected("Arena Encounter has no native Universe owner") from exc
    from atomic_publication import coordinated_access
    try:
        with coordinated_access(world):
            return _capture_arena_history_prefix_locked(summary)
    except ArenaHistoryRejected:
        raise
    except (TypeError, ValueError, AttributeError, KeyError) as exc:
        raise ArenaHistoryRejected(f"Arena history capture refused: {exc}") from exc


def _effect_id(identity):
    from action_evaluation import EffectIdentity
    if type(identity) is not EffectIdentity:
        raise ArenaHistoryRejected("committed effect has an unsupported identity type")
    return [identity.encounter_id, identity.boundary, identity.source_action_id,
            identity.channel, identity.slot]
