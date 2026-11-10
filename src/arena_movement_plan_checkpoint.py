"""Closed, pointer-free session input for the bounded Arena continuation.

This captures the already accepted session plan; it is not a new movement
decision and is never evaluated here. Admission to native progression belongs
to the checkpoint restoration owner.
"""
from dataclasses import dataclass
import json
import math


SCHEMA = "universe.arena-movement-plan/1"
_FIELDS = frozenset((
    "schema", "universe_id", "encounter_id", "actor_id", "decision_id",
    "accepted_at", "checkpoint_boundary", "destination", "cell",
    "layout", "rate", "facing_policy", "movement_sequence", "world_premise",
))
_RATES = frozenset(("walk", "hustle", "jog", "run", "sprint"))


class MovementPlanRejected(ValueError):
    """The closed accepted-plan representation is malformed or unsupported."""


@dataclass(frozen=True)
class ArenaMovementPlanCheckpoint:
    schema: str
    universe_id: str
    encounter_id: str
    actor_id: str
    decision_id: str
    accepted_at: float
    checkpoint_boundary: int
    destination: tuple[float, float, float]
    cell: tuple[int, int]
    layout: tuple[int, int]
    rate: str
    facing_policy: str
    movement_sequence: int
    world_premise: tuple[str, str, float, float, bool, bool]


def capture_accepted_plan(session):
    """Encode only the real pending plan from a completed native boundary-1 Arena."""
    from arena_browser_session import GeneratedArenaSession, _MovementPlan, _RATES
    from arena_hex_map import ArenaHexLayout, HexAddress
    from arena_initialization import ArenaInitializationCandidate, ArenaWorldPremise
    from encounter import ArenaMovementActivation
    from spatial.state import CartesianPosition

    if type(session) is not GeneratedArenaSession:
        raise MovementPlanRejected("native GeneratedArenaSession is required")
    with session._lock:
        candidate = session._active
        plan = session._movement_plan
        if type(candidate) is not ArenaInitializationCandidate or type(plan) is not _MovementPlan:
            raise MovementPlanRejected("an accepted, still-pending Arena movement plan is required")
        encounter = candidate.encounter
        activation = encounter.arena_movement_activation
        if (encounter.time != 1 or encounter.last_processed_boundary != 1
                or not encounter.initiated or encounter.progression_mode != "transactional"
                or type(activation) is not ArenaMovementActivation
                or activation.encounter_id != encounter.id or activation.time != 0
                or activation.activation_kind != "first_player_movement"):
            raise MovementPlanRejected("only the committed initial movement-activation boundary is supported")
        layout = candidate.arena_map.layout
        if (type(layout) is not ArenaHexLayout or type(layout.cell_ids) is not range
                or layout.cell_ids != range(layout.width_columns * layout.height_rows)):
            raise MovementPlanRejected("only the generated rectangular Arena hex layout is supported")
        premise = candidate.world_premise
        if type(premise) is not ArenaWorldPremise or not premise.unobstructed or premise.collision_adjudicated:
            raise MovementPlanRejected("only the generated unobstructed initial movement premise is supported")
        if (premise.terrain != "Plains" or premise.route != "Road"
                or premise.terrain_multiplier != 1.0 or premise.hampered_multiplier != 1.0):
            raise MovementPlanRejected("unsupported native Arena movement-rate premise")
        player = candidate.participants[0].native.being
        if (activation.actor_id != player.id or activation.movement_decision_id != plan.decision_id
                or type(plan.destination) is not CartesianPosition or type(plan.address) is not HexAddress
                or not layout.contains(plan.address) or plan.rate not in _RATES
                or plan.facing_policy not in ("turn", "maintain")
                or player.get_position() == plan.destination):
            raise MovementPlanRejected("accepted movement plan is stale or disagrees with native activation")
        if (type(session._movement_sequence) is not int or session._movement_sequence < 1
                or plan.decision_id != f"arena-movement-{session._movement_sequence}"):
            raise MovementPlanRejected("movement decision sequence does not bind to the accepted plan")
        expected = layout.center_position(plan.address, z=plan.destination.z)
        if expected != plan.destination:
            raise MovementPlanRejected("accepted destination differs from its native hex-cell center")
        row = ArenaMovementPlanCheckpoint(
            SCHEMA, candidate.universe.id, encounter.id, player.id, plan.decision_id,
            activation.time, 1,
            (plan.destination.x, plan.destination.y, plan.destination.z),
            (plan.address.column, plan.address.row),
            (layout.width_columns, layout.height_rows), plan.rate,
            plan.facing_policy, session._movement_sequence,
            (premise.terrain, premise.route, premise.terrain_multiplier,
             premise.hampered_multiplier, premise.unobstructed, premise.collision_adjudicated))
        return encode(row)


def encode(row):
    if type(row) is not ArenaMovementPlanCheckpoint:
        raise MovementPlanRejected("closed Arena movement plan required")
    payload = {
        "schema": row.schema, "universe_id": row.universe_id,
        "encounter_id": row.encounter_id, "actor_id": row.actor_id,
        "decision_id": row.decision_id, "accepted_at": row.accepted_at,
        "checkpoint_boundary": row.checkpoint_boundary,
        "destination": list(row.destination), "cell": list(row.cell),
        "layout": list(row.layout), "rate": row.rate,
        "facing_policy": row.facing_policy,
        "movement_sequence": row.movement_sequence,
        "world_premise": list(row.world_premise),
    }
    _validate(row)
    return json.dumps(payload, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise MovementPlanRejected("duplicate movement-plan field")
        result[key] = value
    return result


def decode(raw):
    if type(raw) is not bytes or not raw or len(raw) > 4096:
        raise MovementPlanRejected("movement-plan wire must be 1..4096 bytes")
    try:
        payload = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_pairs,
                             parse_constant=lambda _value: (_ for _ in ()).throw(
                                 MovementPlanRejected("non-finite movement-plan number")))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise MovementPlanRejected("movement-plan wire is invalid UTF-8 JSON") from exc
    if type(payload) is not dict or set(payload) != _FIELDS:
        raise MovementPlanRejected("movement-plan wire has missing or unsupported fields")
    try:
        row = ArenaMovementPlanCheckpoint(
            payload["schema"], payload["universe_id"], payload["encounter_id"],
            payload["actor_id"], payload["decision_id"], payload["accepted_at"],
            payload["checkpoint_boundary"], tuple(payload["destination"]),
            tuple(payload["cell"]), tuple(payload["layout"]), payload["rate"],
            payload["facing_policy"], payload["movement_sequence"],
            tuple(payload["world_premise"]))
    except (TypeError, KeyError) as exc:
        raise MovementPlanRejected("movement-plan field has an unsupported shape") from exc
    _validate(row)
    if encode(row) != raw:
        raise MovementPlanRejected("movement-plan wire is not canonical")
    return row


def _validate(row):
    def identifier(value):
        return type(value) is str and bool(value.strip()) and len(value) <= 512

    if (row.schema != SCHEMA or not all(identifier(value) for value in
            (row.universe_id, row.encounter_id, row.actor_id, row.decision_id))
            or row.decision_id != f"arena-movement-{row.movement_sequence}"):
        raise MovementPlanRejected("movement-plan identity is malformed")
    if (type(row.accepted_at) not in (int, float) or not math.isfinite(row.accepted_at)
            or row.accepted_at != 0 or type(row.checkpoint_boundary) is not int
            or row.checkpoint_boundary != 1 or type(row.movement_sequence) is not int
            or row.movement_sequence < 1):
        raise MovementPlanRejected("movement-plan chronology is unsupported")
    if (type(row.destination) is not tuple or len(row.destination) != 3
            or any(type(value) not in (int, float) or not math.isfinite(value)
                   for value in row.destination)):
        raise MovementPlanRejected("movement destination coordinates are malformed")
    if (type(row.cell) is not tuple or len(row.cell) != 2
            or any(type(value) is not int for value in row.cell)
            or type(row.layout) is not tuple or len(row.layout) != 2
            or any(type(value) is not int or value < 1 for value in row.layout)
            or not (0 <= row.cell[0] < row.layout[0]
                    and 0 <= row.cell[1] < row.layout[1])):
        raise MovementPlanRejected("movement cell/layout is malformed")
    if (row.rate not in _RATES or row.facing_policy not in ("turn", "maintain")):
        raise MovementPlanRejected("movement rate or facing policy is unsupported")
    if (type(row.world_premise) is not tuple or len(row.world_premise) != 6
            or row.world_premise != ("Plains", "Road", 1.0, 1.0, True, False)):
        raise MovementPlanRejected("movement premise is outside the initial Arena contract")
