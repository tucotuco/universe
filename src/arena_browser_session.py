"""Server-owned empty/generated Arena browser session and safe projection."""

from __future__ import annotations

import re
import random
import secrets
import threading

from arena_initialization import ArenaInitializationRefusal, initialize_two_being_arena
from activities import RunAction
from atomic_publication import RNGCursor


_DECIMAL = re.compile(r"[0-9]+\Z")
_SPOT_DISABLED = (
    "Spot is unavailable for generated Beings: the native Spot resolver requires target geometry; "
    "the generated candidate has none and resolves as unmodeled_target."
)


class ArenaBrowserRequestError(ValueError):
    """A malformed or unavailable generated-Arena browser request."""


def _parse_decimal(payload, key, minimum):
    value = payload.get(key)
    if type(value) is not str or _DECIMAL.fullmatch(value) is None:
        raise ArenaBrowserRequestError(f"{key} must be a decimal integer string")
    try:
        number = int(value, 10)
    except ValueError as exc:
        raise ArenaBrowserRequestError(f"{key} is too large to parse exactly") from exc
    if number < minimum:
        raise ArenaBrowserRequestError(f"{key} must be at least {minimum}")
    return number


class GeneratedArenaSession:
    """A replace-on-success generated Arena session with no initial Encounter."""

    def __init__(self, *, root_seed_factory=None):
        self._root_seed_factory = root_seed_factory or (lambda: secrets.randbits(256))
        self._lock = threading.RLock()
        self._active = None
        self._encounter_name = None
        self._player_name = None
        self._rng_cursor = None
        self._player_action_id = None
        self._player_action_outcome = None

    @property
    def active_candidate(self):
        """Internal authoritative candidate accessor for tests and host integration."""
        with self._lock:
            return self._active

    def _view_unlocked(self):
        if self._active is None:
            return {
                "state": "empty",
                "load_available": False,
                "spot_available": False,
                "spot_reason": _SPOT_DISABLED,
                "run_available": False,
                "advance_available": False,
            }
        candidate = self._active
        player = candidate.participants[0]
        position = player.native.being.get_position()
        action = None
        if self._player_action_id is not None:
            action = {"name": "Run", "status": "completed" if self._player_action_outcome else "executing",
                      "outcome": self._player_action_outcome}
        return {
            "state": "active",
            "load_available": False,
            "encounter_name": self._encounter_name,
            "time_seconds": candidate.encounter.time,
            "map": {"width_cells": candidate.arena_map.width_cells,
                    "height_cells": candidate.arena_map.height_cells,
                    "cell_size_meters": candidate.arena_map.cell_size_meters,
                    "origin": candidate.arena_map.origin},
            "player": {"name": self._player_name,
                       "cell": {"column": player.placement.column,
                                "row": player.placement.row},
                       "position_meters": {"x": position.x, "y": position.y, "z": position.z}},
            "player_action": action,
            "run_available": self._player_action_id is None,
            "advance_available": self._player_action_id is not None
                and self._player_action_outcome is None and candidate.encounter.time == 0,
            "spot_available": False,
            "spot_reason": _SPOT_DISABLED,
        }

    def public_view(self):
        """Return an allowlisted player-facing projection, never Reality/source data."""
        with self._lock:
            return self._view_unlocked()

    def generate(self, payload):
        if type(payload) is not dict or set(payload) != {
                "starting_experience", "width_cells", "height_cells"}:
            raise ArenaBrowserRequestError("Generate requires exactly starting_experience, width_cells, and height_cells")
        starting_experience = _parse_decimal(payload, "starting_experience", 0)
        width_cells = _parse_decimal(payload, "width_cells", 5)
        height_cells = _parse_decimal(payload, "height_cells", 5)

        # Serialize generation with all session edits/reads. The prior candidate
        # stays active until a complete new candidate and native RNG owner exist.
        with self._lock:
            root_seed = self._root_seed_factory()
            if type(root_seed) is not int or root_seed < 0:
                raise ArenaBrowserRequestError("host root seed source must return a nonnegative integer")
            try:
                candidate = initialize_two_being_arena(
                    starting_experience, width_cells, height_cells, root_seed)
                encounter = candidate.encounter
                encounter.set_name("Encounter")
                candidate.participants[0].native.being.set_name(
                    candidate.participants[0].native.being.name or "Player")
            except ArenaInitializationRefusal as exc:
                refusal = exc.details.get("refusal", {})
                message = refusal.get("message", exc.message) if type(refusal) is dict else exc.message
                raise ArenaBrowserRequestError(message) from exc
            except (TypeError, ValueError, RuntimeError) as exc:
                raise ArenaBrowserRequestError(f"Arena candidate could not be activated: {exc}") from exc
            except Exception as exc:
                raise ArenaBrowserRequestError(
                    "Arena generation failed; the previous active session was preserved.") from exc

            self._active = candidate
            self._encounter_name = encounter.name
            self._player_name = candidate.participants[0].native.being.name
            self._rng_cursor = RNGCursor(random.Random(candidate.root_seed).getstate())
            self._player_action_id = None
            self._player_action_outcome = None
            return self._view_unlocked()

    def choose_run(self):
        """Accept the player's first native target-free Run Choice."""
        with self._lock:
            if self._active is None:
                raise ArenaBrowserRequestError("Generate an Encounter before choosing Run")
            if self._player_action_id is not None:
                raise ArenaBrowserRequestError("the first player Action has already been chosen")
            candidate = self._active
            player = candidate.participants[0].native.being
            action = RunAction(candidate.universe, player.id, candidate.encounter.time,
                               duration=1, minimum_distance=0.1, experience=0)
            try:
                candidate.encounter.activate_arena_for_player_action(
                    player.id, action, rng_owner=self._rng_cursor)
            except Exception as exc:
                raise ArenaBrowserRequestError("native player Choice was not accepted; the Arena remains unchanged") from exc
            self._player_action_id = action.id
            return self._view_unlocked()

    def advance_one_second(self):
        """Commit exactly the native next boundary for the accepted Run Choice."""
        with self._lock:
            if self._active is None or self._player_action_id is None:
                raise ArenaBrowserRequestError("choose Run before advancing the Encounter")
            candidate = self._active
            if candidate.encounter.time != 0 or self._player_action_outcome is not None:
                raise ArenaBrowserRequestError("this Arena supports one committed first-player second")
            try:
                candidate.encounter.step(1)
                result = candidate.encounter.inspect_committed(1).action(self._player_action_id)
                self._player_action_outcome = result.facts.outcome
            except Exception as exc:
                raise ArenaBrowserRequestError("native one-second advancement failed") from exc
            return self._view_unlocked()

    def rename_encounter(self, payload):
        if type(payload) is not dict or set(payload) != {"name"}:
            raise ArenaBrowserRequestError("Encounter name request requires exactly one name")
        name = self._validate_name(payload["name"])
        with self._lock:
            if self._active is None:
                raise ArenaBrowserRequestError("Generate an Encounter before renaming it")
            self._active.encounter.set_name(name)
            self._encounter_name = name
            return self._view_unlocked()

    def rename_player(self, payload):
        if type(payload) is not dict or set(payload) != {"name"}:
            raise ArenaBrowserRequestError("Player name request requires exactly one name")
        name = self._validate_name(payload["name"])
        with self._lock:
            if self._active is None:
                raise ArenaBrowserRequestError("Generate an Encounter before renaming the player")
            being = self._active.participants[0].native.being
            being.set_name(name)
            self._player_name = name
            return self._view_unlocked()

    @staticmethod
    def _validate_name(value):
        if type(value) is not str or not value.strip() or len(value.strip()) > 40:
            raise ArenaBrowserRequestError("name must contain 1 to 40 characters")
        return value.strip()
