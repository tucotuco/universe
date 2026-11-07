"""Bounded, unpublished two-Being Arena initialization using installed npcgen."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import random
from pathlib import Path

from encounter import Encounter
from library import Library
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


@dataclass(frozen=True)
class ArenaMap:
    width_cells: int
    height_cells: int
    cell_size_meters: float = YARDS_TO_METERS
    origin: str = "southwest corner at (0, 0, 0); x east, y north, z up"
    authority: str = "initialization/presentation coordinates only; native positions remain continuous"


@dataclass(frozen=True)
class ArenaInitializationCandidate:
    universe: Universe
    encounter: Encounter
    arena_map: ArenaMap
    starting_experience: int
    root_seed: int
    placement_seed: int
    engine_identity: dict
    participants: tuple[ArenaParticipant, ArenaParticipant]
    attempts: tuple[ArenaAttempt, ...]


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
                               root_seed: int, *, library: Library | None = None) -> ArenaInitializationCandidate:
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
    cells = random.Random(placement_seed).sample(range(width_cells * height_cells), 2)
    placements = []
    for (role, native, candidate_seed), cell in zip(selected, cells):
        column, row = cell % width_cells, cell // width_cells
        position = CartesianPosition((column + 0.5) * YARDS_TO_METERS,
                                    (row + 0.5) * YARDS_TO_METERS, 0.0)
        native.being.set_position(position)
        placements.append(ArenaPlacement(role, native.being.id, column, row, position))

    encounter = Encounter(world, difficulty_class=0, start_time=0, name="Arena")
    for native in (first, second):
        encounter.add_being(native.being.id)

    # The Universe is still private. Only the complete pair is registered, and
    # this candidate is returned only after every native assembly step succeeds.
    for native in (first, second):
        if world.get_object_by_id(native.being.id) is not None:
            _reject("native_identity_collision", "generated native Being identity already exists")
    world.add_object(first.being)
    world.add_object(second.being)
    world.add_event(encounter)
    if (world.get_object_by_id(first.being.id) is not first.being
            or world.get_object_by_id(second.being.id) is not second.being
            or world.get_event_by_id(encounter.id) is not encounter):
        _reject("native_registration_failed", "fresh Universe did not retain the complete candidate")

    participants = tuple(ArenaParticipant(role, native, placement, seed)
                         for (role, native, seed), placement in zip(selected, placements))
    return ArenaInitializationCandidate(
        world, encounter, ArenaMap(width_cells, height_cells), starting_experience,
        root_seed, placement_seed, dict(identity), participants, tuple(attempts))
