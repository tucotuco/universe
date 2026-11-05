"""Closed local S7 claim for the fixed Ari/Bex Arena continuation.

This is data, not a receipt or a restore authorization. A separate trusted
host must approve each use. The only supported claim is the native boundary-7
Run produced by the existing C2 continuation.
"""
from __future__ import annotations

from dataclasses import dataclass
import base64
import hashlib
import json
from types import MappingProxyType

SCHEMA = "universe.arena.local-s7-claim/1"
TRUST = ("untrusted boundary-7 state/history claim; digest is not receipt "
         "authentication; requires a separate trusted-local host approval")
MAX_BYTES = 20 * 1024 * 1024
ARI = "arena/being/ari"
BEX = "arena/being/bex"
ENCOUNTER = "npc-arena/encounter/1"
RUN7 = "npc-arena/action/run-ari-boundary-7"
CHOICE7 = "npc-arena/encounter/1/draft/2"


class ArenaS7Rejected(ValueError):
    """S7 state is malformed, inconsistent, or outside its exact fixture."""


def _canonical(value):
    try:
        return json.dumps(value, sort_keys=True, ensure_ascii=False,
                          separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        raise ArenaS7Rejected(f"S7 claim is not canonical data: {exc}") from exc


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ArenaS7Rejected(f"duplicate S7 field {key!r}")
        result[key] = value
    return result


def _expected_boundary7():
    return {
        "encounter_id": ENCOUNTER,
        "boundary": 7,
        "start_time_hex": 6.0.hex(),
        "action": {
            "action_id": RUN7, "choice_id": CHOICE7,
            "actor_id": ARI, "target_id": None,
            "family": "run", "start_hex": 6.0.hex(),
            "nominal_end_hex": 7.0.hex(), "outcome": "success",
            "metadata": {"displacement": 1.0},
        },
        "effect_ids": [
            [ENCOUNTER, 7, RUN7, "effect", 0],
            [ENCOUNTER, 7, RUN7, "lifecycle", 0],
            [ENCOUNTER, 7, RUN7, "lifecycle", 1],
        ],
        "practice": {
            "target_id": ARI, "skill_name": "run", "experience": 4,
            "level_before": 0, "level_after": 0, "baseline": 0,
            "time": 7, "action_id": None, "outcome": "simultaneous",
            "exercises": [{
                "effect_id": [ENCOUNTER, 7, RUN7, "effect", 0],
                "skill_name": "run", "experience": 4,
                "action_id": RUN7, "nominal_end_hex": 7.0.hex(),
                "resolved_at": 7, "outcome": "success",
            }],
        },
        "participants": [
            {"being_id": ARI, "position_hex": [1.0.hex(), 0.0.hex(), 0.0.hex()],
             "hit_points_hex": 10.0.hex(), "aware_of": [BEX]},
            {"being_id": BEX, "position_hex": [3.0.hex(), 0.0.hex(), 0.0.hex()],
             "hit_points_hex": 10.0.hex(), "aware_of": []},
        ],
    }


def _decode_base(raw):
    from arena_local_checkpoint import decode_local_bundle
    try:
        return decode_local_bundle(raw)
    except (TypeError, ValueError) as exc:
        raise ArenaS7Rejected(f"embedded S6 bundle failed validation: {exc}") from exc


def _validate(data):
    fields = {"schema", "trust", "base_bundle_base64", "base_bundle_sha256",
              "boundary7", "content_sha256"}
    if type(data) is not dict or set(data) != fields:
        raise ArenaS7Rejected("S7 envelope has missing or unknown fields")
    if data["schema"] != SCHEMA or data["trust"] != TRUST:
        raise ArenaS7Rejected("unsupported S7 schema or trust label")
    digest = data["content_sha256"]
    body = dict(data); body.pop("content_sha256")
    if type(digest) is not str or hashlib.sha256(_canonical(body)).hexdigest() != digest:
        raise ArenaS7Rejected("S7 content digest mismatch")
    if data["boundary7"] != _expected_boundary7():
        raise ArenaS7Rejected("boundary-7 claim differs from the reviewed native Run fixture")
    try:
        raw = base64.b64decode(data["base_bundle_base64"], validate=True)
    except (ValueError, TypeError) as exc:
        raise ArenaS7Rejected("embedded S6 bundle is invalid base64") from exc
    if base64.b64encode(raw).decode("ascii") != data["base_bundle_base64"]:
        raise ArenaS7Rejected("embedded S6 bundle encoding is not canonical")
    if hashlib.sha256(raw).hexdigest() != data["base_bundle_sha256"]:
        raise ArenaS7Rejected("embedded S6 digest mismatch")
    prefix, candidate = _decode_base(raw)
    if prefix.through_boundary != 6 or candidate.view().time != 6.0:
        raise ArenaS7Rejected("S7 base is not the supported S6 Spot state")
    if _canonical(data) != _canonical(json.loads(_canonical(data))):
        raise ArenaS7Rejected("S7 claim is not canonical")
    return raw, prefix, candidate


def _freeze(value):
    if type(value) is dict:
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if type(value) is list:
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value):
    if type(value) is MappingProxyType:
        return {key: _thaw(item) for key, item in value.items()}
    if type(value) is tuple:
        return [_thaw(item) for item in value]
    return value


@dataclass(frozen=True)
class ArenaS7Candidate:
    _wire: bytes

    def to_bytes(self):
        decode_s7_candidate(self._wire)
        return bytes(self._wire)

    @property
    def content_sha256(self):
        return json.loads(self._wire)["content_sha256"]


@dataclass(frozen=True)
class ArenaS7View:
    content_sha256: str
    base_bundle: bytes
    boundary7: object
    history_trust: str = "imported/host-accepted claim; original receipt authenticity not established"


def decode_s7_candidate(wire):
    if type(wire) is not bytes or not wire or len(wire) > MAX_BYTES:
        raise ArenaS7Rejected("S7 claim is empty or exceeds its size bound")
    try:
        data = json.loads(wire.decode("utf-8"), object_pairs_hook=_pairs)
    except ArenaS7Rejected:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ArenaS7Rejected(f"S7 claim is not valid UTF-8 JSON: {exc}") from exc
    raw, _, _ = _validate(data)
    if _canonical(data) != wire:
        raise ArenaS7Rejected("S7 claim is not in canonical encoding")
    return ArenaS7Candidate(bytes(wire))


def s7_view(candidate):
    if type(candidate) is not ArenaS7Candidate:
        raise ArenaS7Rejected("exact immutable S7 candidate required")
    data = json.loads(candidate.to_bytes().decode("utf-8"))
    raw, _, _ = _validate(data)
    return ArenaS7View(data["content_sha256"], raw, _freeze(data["boundary7"]))


def _encode_s7_claim(s6_bundle_bytes):
    """Internal encoder; callers must first validate an actual native boundary 7."""
    if type(s6_bundle_bytes) is not bytes:
        raise ArenaS7Rejected("S6 base must be immutable bytes")
    _decode_base(s6_bundle_bytes)
    body = {
        "schema": SCHEMA, "trust": TRUST,
        "base_bundle_base64": base64.b64encode(s6_bundle_bytes).decode("ascii"),
        "base_bundle_sha256": hashlib.sha256(s6_bundle_bytes).hexdigest(),
        "boundary7": _expected_boundary7(),
    }
    envelope = dict(body, content_sha256=hashlib.sha256(_canonical(body)).hexdigest())
    wire = _canonical(envelope)
    if len(wire) > MAX_BYTES:
        raise ArenaS7Rejected("S7 claim exceeds its size bound")
    return decode_s7_candidate(wire)


def capture_s7_candidate(s6_bundle_bytes, active):
    """Capture only after native boundary 7 actually committed in this process."""
    from arena_state_activation import _ActiveArenaContinuation
    if type(active) is not _ActiveArenaContinuation or active.start_boundary != 6:
        raise ArenaS7Rejected("S7 capture requires the fixed C2 boundary-6 continuation")
    if active.encounter.time != 7 or active.encounter.last_processed_boundary != 7:
        raise ArenaS7Rejected("S7 capture requires committed native boundary 7")
    if (active.encounter.pending_action_list or active.encounter.__dict__.get("_dispatching")
            or active.encounter.__dict__.get("_advancing") or active.encounter.__dict__.get("_running")):
        raise ArenaS7Rejected("S7 capture requires a quiescent Encounter")
    from arena_local_checkpoint import decode_local_bundle
    prefix, base_candidate = decode_local_bundle(s6_bundle_bytes)
    if (prefix.content_sha256 != active.imported_prefix.content_sha256
            or base_candidate.view().time != 6.0
            or tuple(active.encounter._atomic_interval_history[i].boundary
                     for i in range(len(active.encounter._atomic_interval_history))) != (7,)
            or tuple(active.encounter.finished_action_list) != (RUN7,)
            or tuple(active.encounter.pending_action_list) != ()
            or tuple(active.encounter.cancelled_action_list) != ()):
        raise ArenaS7Rejected("S7 native lifecycle/history is not exactly one boundary-7 Run")
    book = active.encounter._choice_book
    if (book._counter != 2 or set(book._choices) != {CHOICE7}
            or set(book._registered) != {RUN7} or book._states != {RUN7: "finished"}
            or book._reservations or book._tokens or set(book._drafts) != book._closed_drafts):
        raise ArenaS7Rejected("S7 ChoiceBook is open, stale, or has unexpected identities")
    try:
        view = active.encounter.inspect_committed(7)
    except Exception as exc:
        raise ArenaS7Rejected(f"native S7 inspection rejected stale or unreceipted state: {exc}") from exc
    if tuple(view.timeline[i].boundary for i in range(len(view.timeline))) != (7,):
        raise ArenaS7Rejected("fresh native inspection must contain only boundary 7")
    action = view.action(RUN7)
    if action.facts.outcome != "success" or action.resolved_boundary != 7:
        raise ArenaS7Rejected("the exact successful native boundary-7 Run is required")
    _validate_actual_run(active, view)
    return _encode_s7_claim(s6_bundle_bytes)


def _validate_actual_run(active, view):
    expected = _expected_boundary7()
    action = view.action(RUN7)
    if (action.declaration.id, action.lifecycle.choice_id, action.declaration.actor_id,
            action.declaration.target_id, action.declaration.start,
            action.declaration.nominal_end, action.facts.outcome,
            dict(action.facts.metadata)) != (
            RUN7, CHOICE7, ARI, None, 6, 7, "success", {"displacement": 1.0}):
        raise ArenaS7Rejected("native boundary-7 Action declaration/result differs")
    if [[x.identity.encounter_id, x.identity.boundary, x.identity.source_action_id,
         x.identity.channel, x.identity.slot] for x in action.effects] != expected["effect_ids"]:
        raise ArenaS7Rejected("native boundary-7 causal effect identities differ")
    for row in expected["participants"]:
        target = view.target(row["being_id"])
        pos = tuple(float(v).hex() for v in target.position.as_tuple())
        aware = sorted(target.state.aware_of)
        being = active.world.get_object_by_id(row["being_id"])
        if (list(pos) != row["position_hex"] or float(being.get_hit_points()).hex() != row["hit_points_hex"]
                or aware != row["aware_of"]
                or tuple(float(v).hex() for v in being.get_position().as_tuple()) != tuple(pos)
                or tuple(sorted(active.encounter.awareness[row["being_id"]])) != tuple(aware)
                or len(being._atomic_target_history) != 1
                or being._atomic_target_history[0].boundary != 7):
            raise ArenaS7Rejected("committed Target state differs from the S7 claim")
    target = view.target(ARI)
    if len(target.practice_history) != 1:
        raise ArenaS7Rejected("boundary 7 must contain exactly one Target-owned Run practice transition")
    practice = target.practice_history[0]
    if (practice.skill_name, practice.experience, practice.time,
            tuple(row.action_id for row in practice.exercises)) != ("run", 4, 7, (RUN7,)):
        raise ArenaS7Rejected("Target-owned Run practice provenance differs")
    ari = active.world.get_object_by_id(ARI)
    if (ari.skill_experience != {"run": 4} or ari._skill_practice_baselines != {"run": 0}
            or ari.skill_use_history != [practice]):
        raise ArenaS7Rejected("live Being practice does not match the committed Target transition")
    if (active.world.get_object_by_id(BEX).skill_experience
            or active.world.get_object_by_id(BEX).skill_use_history):
        raise ArenaS7Rejected("boundary-7 Run altered the uninvolved participant's practice")
