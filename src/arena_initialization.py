"""Bounded, unpublished two-Being Arena initialization using installed npcgen."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import random
from pathlib import Path

from encounter import Encounter
from library import Library
from arena_hex_map import ArenaHexLayout
from arena_ground_objects import (ArenaGroundObjectRefusal, realize_arena_ground_objects)
from npcgen_arena_adapter import ArenaNPCRefusal, ArenaNativeBeing, prepare_npcgen_arena_being
from spatial.state import CartesianPosition
from universe import Universe


YARDS_TO_METERS = 0.9144
MAX_ATTEMPTS_PER_ROLE = 32
MAX_MAP_CELLS = 1_000_000
HIGH_XP_AGE_DIAGNOSTIC = "The starting experience is probably unreasonably high. Try reducing the XP value."
_RETRYABLE_CODES = frozenset(("unsupported_native_race", "skill_profile_unresolved"))


class ArenaInitializationRefusal(ValueError):
    """A structured refusal that leaves no candidate published to the caller."""

    def __init__(self, code: str, message: str, *, details: dict | None = None):
        self.code, self.message, self.details = code, message, details or {}
        super().__init__(f"{code}: {message}")

    def to_dict(self) -> dict:
        return {"code": self.code, "message": self.message, "details": dict(self.details)}


@dataclass(frozen=True)
class ArenaAttempt:
    role: str
    attempt: int
    seed: int
    outcome: str
    code: str | None = None
    details: dict | None = None
    source_sha256: str | None = None


@dataclass(frozen=True)
class ArenaPlacement:
    role: str
    being_id: str
    column: int
    row: int
    position: CartesianPosition


@dataclass(frozen=True)
class ArenaParticipant:
    role: str
    native: ArenaNativeBeing
    placement: ArenaPlacement
    selected_seed: int
    facing_seed: int
    facing_provenance: str
    posture_provenance: str


@dataclass(frozen=True)
class ArenaMap:
    width_cells: int
    height_cells: int
    layout: ArenaHexLayout
    origin: str = "southwest footprint edge at (0, 0, 0); x east, y north, z up"
    authority: str = "initialization/presentation coordinates only; native positions remain continuous"

    @property
    def cell_size_meters(self) -> float:
        """Adopted one-yard distance between opposite hex sides."""
        return self.layout.side_to_side_meters

    def public_geometry(self) -> dict:
        regular = (type(self.layout.cell_ids) is range
                   and self.layout.cell_ids == range(self.width_cells * self.height_cells))
        columns = None if regular else [
            [column, [list(row_range) for row_range in ranges]]
            for column, ranges in self.layout.column_row_ranges()]
        return {
            "orientation": "flat_top_odd_column_north_offset",
            "cell_size_meters": self.cell_size_meters,
            "hex_vertex_offsets_meters": [list(point) for point in self.layout.vertex_offsets_meters],
            "column_step_meters": self.layout.column_step_meters,
            "row_step_meters": self.layout.row_step_meters,
            "odd_column_offset_meters": self.layout.odd_column_offset_meters,
            "origin_offset_meters": list(self.layout.origin_offset_meters),
            "column_row_ranges": columns,
        }


@dataclass(frozen=True)
class ArenaWorldPremise:
    """Authored rate/environment facts for the bounded generated Arena."""

    terrain: str = "Plains"
    route: str = "Road"
    terrain_multiplier: float = 1.0
    hampered_multiplier: float = 1.0
    unobstructed: bool = True
    collision_adjudicated: bool = False

    def public_view(self) -> dict:
        return {"terrain": self.terrain, "route": self.route,
                "terrain_multiplier": self.terrain_multiplier,
                "hampered_multiplier": self.hampered_multiplier,
                "unobstructed": self.unobstructed,
                "collision_adjudicated": self.collision_adjudicated}


@dataclass(frozen=True)
class ArenaInitializationCandidate:
    universe: Universe
    encounter: Encounter
    arena_map: ArenaMap
    world_premise: ArenaWorldPremise
    starting_experience: int
    root_seed: int
    placement_seed: int
    engine_identity: dict
    participants: tuple[ArenaParticipant, ArenaParticipant]
    attempts: tuple[ArenaAttempt, ...]
    ground_objects: tuple = ()
    ground_item_bindings: tuple[tuple[str, str], ...] = ()
    ground_layout: ArenaHexLayout | None = None
    ground_placement_seed: int | None = None
    ground_loadout_provenance: tuple[dict, ...] = ()


def _reject(code: str, message: str, **details):
    raise ArenaInitializationRefusal(code, message, details=details)


def _attempt_dict(attempt: ArenaAttempt) -> dict:
    return {"role": attempt.role, "attempt": attempt.attempt, "seed": attempt.seed,
            "outcome": attempt.outcome, "code": attempt.code,
            "details": dict(attempt.details or {}), "source_sha256": attempt.source_sha256}


def _seed(root_seed: int, identity: dict, purpose: str, role_index: int = 0, attempt: int = 0) -> int:
    identity_bytes = json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    payload = (b"universe-arena-initialization-v1\0" + identity_bytes + b"\0"
               + str(root_seed).encode("ascii") + b"\0" + purpose.encode("ascii") + b"\0"
               + str(role_index).encode("ascii") + b"\0" + str(attempt).encode("ascii"))
    return int.from_bytes(hashlib.sha256(payload).digest(), "big")


def _validate_request(starting_experience, width_cells, height_cells, root_seed):
    values = ((starting_experience, "starting_experience", 0),
              (width_cells, "width_cells", 5), (height_cells, "height_cells", 5),
              (root_seed, "root_seed", 0))
    for value, name, minimum in values:
        if type(value) is not int or value < minimum:
            _reject("invalid_request", f"{name} must be an integer >= {minimum}", field=name)
    if width_cells > MAX_MAP_CELLS // height_cells:
        _reject("map_too_large", "initial map exceeds the bounded cell footprint",
                maximum_cells=MAX_MAP_CELLS)


def initialize_two_being_arena(starting_experience: int, width_cells: int, height_cells: int,
                               root_seed: int, *, library: Library | None = None,
                               ground_item_descriptions=None,
                               ground_loadout_profile: dict | None = None) -> ArenaInitializationCandidate:
    """Prepare a complete time-zero Arena in a fresh Universe, then return it atomically.

    Candidate seeds are SHA-256-derived by role and attempt. Placement uses an
    independently namespaced seed and a private ``random.Random`` instance.
    """
    _validate_request(starting_experience, width_cells, height_cells, root_seed)
    try:
        from npcgen import api
        identity = api.engine_identity()
    except ImportError as exc:
        _reject("npcgen_unavailable", "install the npcgen package before Arena initialization", error=str(exc))
    if type(identity) is not dict:
        _reject("engine_identity_unavailable", "npcgen returned no engine identity")
    if ground_item_descriptions is not None and ground_loadout_profile is not None:
        _reject("ambiguous_ground_equipment_source",
                "supply typed test items or a Generator profile, not both")
    if (ground_item_descriptions is not None
            and type(ground_item_descriptions) not in (list, tuple)):
        _reject("invalid_ground_items", "ground item descriptions must be a finite list")
    normalized_loadout_profile = None
    if ground_loadout_profile is not None:
        if not callable(getattr(api, "arena_loadout", None)) or not callable(
                getattr(api, "validate_loadout_profile", None)) or not callable(
                getattr(api, "validate_loadout", None)):
            _reject("npcgen_loadout_unavailable",
                    "installed npcgen package lacks the validated ordinary loadout API")
        try:
            normalized_loadout_profile = api.validate_loadout_profile(ground_loadout_profile)
        except Exception as exc:
            _reject("invalid_ground_loadout_profile", "caller-supplied npcgen profile was refused",
                    error=type(exc).__name__, message=str(exc)[:256])

    if library is None:
        library = Library(config_dir=str(Path(__file__).resolve().parent / "config"))
    world = Universe("Arena candidate", library=library)
    roles = ("player_controlled", "arena_controlled")
    selected: list[tuple[str, ArenaNativeBeing, int]] = []
    attempts: list[ArenaAttempt] = []

    for role_index, role in enumerate(roles):
        failures = []
        for attempt_index in range(MAX_ATTEMPTS_PER_ROLE):
            candidate_seed = _seed(root_seed, identity, "candidate", role_index, attempt_index)
            try:
                native = prepare_npcgen_arena_being(
                    world, seed=candidate_seed, starting_experience=starting_experience,
                    cost_modifiers="character")
            except ArenaNPCRefusal as exc:
                attempts.append(ArenaAttempt(role, attempt_index + 1, candidate_seed,
                                             "rejected", exc.code, dict(exc.details)))
                if exc.code not in _RETRYABLE_CODES:
                    _reject("candidate_terminal_failure", "npcgen candidate failed a terminal validation",
                            role=role, attempt=attempt_index + 1, refusal=exc.to_dict(),
                            attempt_history=[_attempt_dict(item) for item in attempts])
                failures.append(exc)
                continue
            attempts.append(ArenaAttempt(role, attempt_index + 1, candidate_seed,
                                         "selected", source_sha256=native.source_sha256))
            selected.append((role, native, candidate_seed))
            break
        else:
            failure_details = [{"code": err.code, **err.details} for err in failures]
            if failures and all(err.details.get("age_unavailable") is True for err in failures):
                _reject("high_experience_age_exhaustion", HIGH_XP_AGE_DIAGNOSTIC,
                        role=role, attempts=MAX_ATTEMPTS_PER_ROLE, failures=failure_details,
                        attempt_history=[_attempt_dict(item) for item in attempts])
            _reject("candidate_retries_exhausted", "bounded candidate retries did not find a supported Being",
                    role=role, attempts=MAX_ATTEMPTS_PER_ROLE, failures=failure_details,
                    attempt_history=[_attempt_dict(item) for item in attempts])

    first, second = selected[0][1], selected[1][1]
    if first.being.id == second.being.id:
        _reject("native_identity_collision", "two prepared Beings have the same native identity")

    placement_seed = _seed(root_seed, identity, "placement")
    layout = ArenaHexLayout.rectangle(width_cells, height_cells)
    cells = random.Random(placement_seed).sample(range(width_cells * height_cells), 2)
    placements = []
    for (role, native, candidate_seed), cell in zip(selected, cells):
        address = layout.address_for_index(cell)
        column, row = address.column, address.row
        position = layout.center_position(address)
        native.being.set_position(position)
        placements.append(ArenaPlacement(role, native.being.id, column, row, position))

    encounter = Encounter(world, difficulty_class=0, start_time=0, name="Arena",
                          arena_activation_enabled=True)
    for native in (first, second):
        encounter.add_being(native.being.id)

    # The Universe is still private. Register the Beings before constructing
    # Objects so the native registry can enforce cross-type identity uniqueness.
    for native in (first, second):
        if world.get_object_by_id(native.being.id) is not None:
            _reject("native_identity_collision", "generated native Being identity already exists")
    world.add_object(first.being)
    world.add_object(second.being)

    ground_descriptions = list(ground_item_descriptions or ())
    loadout_provenance = []
    if normalized_loadout_profile is not None:
        for role_index, (role, native, _candidate_seed) in enumerate(selected):
            sampling_seed = _seed(root_seed, identity, "npcgen-arena-loadout-v1", role_index)
            try:
                loadout = api.arena_loadout(
                    json.loads(native.source_record_bytes), normalized_loadout_profile, sampling_seed)
                errors = api.validate_loadout(loadout, normalized_loadout_profile)
            except Exception as exc:
                _reject("npcgen_loadout_refused", "installed npcgen refused the caller profile",
                        role=role, error=type(exc).__name__, message=str(exc)[:256])
            if errors:
                _reject("invalid_npcgen_loadout", "npcgen output failed its versioned profile validation",
                        role=role, errors=list(errors)[:16])
            if (type(loadout) is not dict or loadout.get("format") != "npcgen-arena-loadout"
                    or loadout.get("schema_version") != 1 or loadout.get("origin") != "arena-loadout"):
                _reject("invalid_npcgen_loadout", "npcgen returned an unsupported loadout contract", role=role)
            for item in loadout.get("items", ()):
                ground_descriptions.append({
                    "source_item_id": item.get("source_item_id"),
                    "category": item.get("category"),
                    "native_type_key": item.get("native_type_key"),
                    "quantity": item.get("quantity"),
                    "ordinary": item.get("ordinary"),
                    "magical": item.get("magical"),
                    "mechanics": item.get("mechanics"),
                    "origin": item.get("origin"),
                })
            loadout_provenance.append({
                "role": role,
                "format": loadout["format"],
                "schema_version": loadout["schema_version"],
                "source": loadout["source"],
                "profile": loadout["profile"],
                "sampling_seed": sampling_seed,
            })

    ground_objects = ()
    ground_item_bindings = ()
    ground_layout = None
    ground_placement_seed = None
    if ground_descriptions:
        ground_placement_seed = _seed(root_seed, identity, "ground-placement-v1")
        try:
            ground_set = realize_arena_ground_objects(
                world, ground_descriptions, layout,
                tuple(layout.cell_at_position(placement.position) for placement in placements),
                ground_placement_seed)
        except ArenaGroundObjectRefusal as exc:
            _reject(exc.code, exc.message, **exc.details)
        ground_objects = ground_set.placements
        ground_item_bindings = ground_set.source_to_native_object_id
        ground_layout = ground_set.layout
        # Native Actions may target only participating Encounter entities.
        # Registration supplies the Object reference to the closed snapshot;
        # it does not grant an observer evidence or a browser-visible identity.
        for placement in ground_objects:
            encounter.add_object(placement.native_object_id)

    world.add_event(encounter)
    if (world.get_object_by_id(first.being.id) is not first.being
            or world.get_object_by_id(second.being.id) is not second.being
            or world.get_event_by_id(encounter.id) is not encounter):
        _reject("native_registration_failed", "fresh Universe did not retain the complete candidate")

    participants = []
    for role_index, ((role, native, seed), placement) in enumerate(zip(selected, placements)):
        facing_seed = _seed(root_seed, identity, "initial-facing-v1", role_index)
        facing = random.Random(facing_seed).randrange(12)
        native.being.set_hex_facing(facing)
        native.being.set_posture("standing")
        participants.append(ArenaParticipant(
            role, native, placement, seed, facing_seed,
            "arena.initial-facing.v1/private-seed", "arena.initial-posture.v1/scenario"))
    return ArenaInitializationCandidate(
        world, encounter, ArenaMap(width_cells, height_cells, layout), ArenaWorldPremise(), starting_experience,
        root_seed, placement_seed, dict(identity), tuple(participants), tuple(attempts),
        ground_objects, ground_item_bindings, ground_layout, ground_placement_seed,
        tuple(loadout_provenance))
