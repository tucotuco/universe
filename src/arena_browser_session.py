"""Server-owned empty/generated Arena browser session and safe projection."""

from __future__ import annotations

import copy
import re
import random
import secrets
import threading
import math
from dataclasses import dataclass

from arena_initialization import ArenaInitializationRefusal, initialize_two_being_arena
from activities import RunAction
from atomic_publication import RNGCursor
from arena_hex_map import HexAddress
from movement_intent import MovementIntent, MovementRateConditions
from arena_ui_trace import ArenaUITerminalTrace


_DECIMAL = re.compile(r"[0-9]+\Z")
_SPOT_DISABLED = (
    "Spot is unavailable for generated Beings: the native Spot resolver requires target geometry; "
    "the generated candidate has none and resolves as unmodeled_target."
)
_MOVEMENT_DISABLED = (
    "Destination movement is unavailable because the player's native posture or facing is unknown."
)
_RATES = frozenset(("walk", "hustle", "jog", "run", "sprint"))
_CLIENT_SEQUENCE = re.compile(r"[1-9][0-9]{0,9}\Z")


@dataclass(frozen=True)
class _MovementPlan:
    decision_id: str
    destination: object
    address: HexAddress
    rate: str
    facing_policy: str


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

    def __init__(self, *, root_seed_factory=None, trace_ui=False, trace_stream=None,
                 ground_item_descriptions=None, ground_loadout_profile=None):
        self._root_seed_factory = root_seed_factory or (lambda: secrets.randbits(256))
        self._lock = threading.RLock()
        self._active = None
        self._encounter_name = None
        self._player_name = None
        self._rng_cursor = None
        self._player_action_id = None
        self._player_action_outcome = None
        self._pickup_action_id = None
        self._pickup_action_outcome = None
        self._movement_plan = None
        self._movement_sequence = 0
        self._movement_outcome = None
        self._trace = ArenaUITerminalTrace(trace_ui, stream=trace_stream)
        # Optional caller-owned initial conditions; the browser still exposes
        # only its existing three Generate fields and has no gear distribution.
        self._ground_item_descriptions = copy.deepcopy(ground_item_descriptions)
        self._ground_loadout_profile = copy.deepcopy(ground_loadout_profile)
        self._view_handles = {}
        self._selected_entity_handle = None
        self._display_names = {}

    @property
    def trace_ui_enabled(self):
        return self._trace.enabled

    def begin_trace_request(self, action, client_sequence_header=None):
        client_sequence = None
        if (type(client_sequence_header) is str
                and _CLIENT_SEQUENCE.fullmatch(client_sequence_header)):
            client_sequence = int(client_sequence_header)
        return self._trace.begin_request(action, client_sequence)

    def finish_trace_request(self, request_id, client_sequence, action, status,
                             http_status, *, classification=None, detail=None):
        self._trace.http_result(request_id, client_sequence, action, status,
                                http_status, classification=classification, detail=detail)

    def accept_client_trace(self, payload):
        return self._trace.client_event(payload)

    @staticmethod
    def _trace_position(position):
        if position is None:
            return "none"
        return "(" + ",".join(f"{value:.6g}" for value in position.as_tuple()) + ")"

    @staticmethod
    def _trace_cell(candidate, position):
        if position is None:
            return "none"
        address = candidate.arena_map.layout.cell_at_position(position)
        return "none" if address is None else f"({address.column},{address.row})"

    def _trace_advance_state(self, candidate, request_id, client_sequence,
                             before_time, before_position, before_cell, plan,
                             status, *, reason=None):
        if not self._trace.enabled:
            return
        after_time = candidate.encounter.time
        after_position = candidate.participants[0].native.being.get_position()
        after_cell = self._trace_cell(candidate, after_position)
        displacement = (None if before_position is None or after_position is None else
                        math.dist(before_position.as_tuple(), after_position.as_tuple()))
        plan_text = "none"
        remaining = "none"
        if plan is not None:
            plan_text = (f"cell=({plan.address.column},{plan.address.row}),"
                         f"rate={plan.rate},policy={plan.facing_policy}")
            remaining = ("unknown" if after_position is None else
                         f"{math.dist(after_position.as_tuple(), plan.destination.as_tuple()):.6g}")
        movement = "no_plan" if plan is None else (
            "arrival" if after_position == plan.destination else
            "zero_displacement" if displacement == 0 else
            "movement_unknown" if displacement is None else "moving")
        parts = [f"action=advance status={status}",
                 f"time={before_time}->{after_time}",
                 f"position={self._trace_position(before_position)}->{self._trace_position(after_position)}",
                 f"cell={before_cell}->{after_cell}",
                 f"displacement_m={'unknown' if displacement is None else format(displacement, '.6g')}",
                 f"movement={movement}", f"plan={plan_text}", f"remaining_m={remaining}"]
        if reason:
            parts.append(f"reason={reason}")
        self._trace.native_advance(request_id, client_sequence, " ".join(parts))

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
                "movement_available": False,
                "movement_reason": _MOVEMENT_DISABLED,
            }
        candidate = self._active
        player = candidate.participants[0]
        from arena_perception import ArenaPerceptionLedger
        ledger = object.__getattribute__(player.native.being, "__dict__").get("_arena_perception_ledger")
        if type(ledger) is not ArenaPerceptionLedger or ledger.observer_id != player.native.being.id:
            raise ArenaBrowserRequestError("player perception evidence is unavailable")
        position = player.native.being.get_position()
        address = candidate.arena_map.layout.cell_at_position(position)
        cell = None if address is None else {"column": address.column, "row": address.row}
        action = None
        if self._player_action_id is not None:
            action = {"name": "Run", "status": "completed" if self._player_action_outcome else "executing",
                      "outcome": self._player_action_outcome}
        pickup_action = None
        if self._pickup_action_id is not None:
            pickup_action = {"name": "Pick up", "status": "completed" if self._pickup_action_outcome else "executing",
                             "outcome": self._pickup_action_outcome}
        movement_plan = None
        movement_available = player.native.being.posture in ("standing", "crouching", "lying")
        movement_available = movement_available and player.native.being.hex_facing is not None
        if self._movement_plan is not None:
            target = self._movement_plan.destination
            remaining = math.dist(position.as_tuple(), target.as_tuple())
            movement_plan = {
                "destination_cell": {"column": self._movement_plan.address.column,
                                     "row": self._movement_plan.address.row},
                "destination_position_meters": {"x": target.x, "y": target.y, "z": target.z},
                "rate": self._movement_plan.rate,
                "facing_policy": self._movement_plan.facing_policy,
                "remaining_distance_meters": remaining,
            }
        perceived = []
        for evidence in ledger.current:
            handle = self._view_handles.get(evidence.entity_id)
            if handle is None:
                handle = secrets.token_urlsafe(18)
                self._view_handles[evidence.entity_id] = handle
            p = evidence.position
            address = None if p is None else candidate.arena_map.layout.cell_at_position(p)
            perceived.append({
                "handle": handle, "category": evidence.category,
                "name": self._display_names.get(evidence.entity_id, evidence.name),
                "type": evidence.type_key,
                "present_state": evidence.present_state,
                "position_meters": None if p is None else {"x": p.x, "y": p.y, "z": p.z},
                "cell": None if address is None else {"column": address.column, "row": address.row},
                "pickup_available": (evidence.category == "object" and evidence.present_state == "ground"
                    and p is not None and candidate.encounter.initiated
                    and address == candidate.arena_map.layout.cell_at_position(position)),
            })
        selected = next((row for row in perceived
                         if row["handle"] == self._selected_entity_handle), None)
        return {
            "state": "active",
            "load_available": False,
            "encounter_name": self._encounter_name,
            "time_seconds": candidate.encounter.time,
            "map": {"width_cells": candidate.arena_map.width_cells,
                    "height_cells": candidate.arena_map.height_cells,
                    "origin": candidate.arena_map.origin,
                    "world_premise": candidate.world_premise.public_view(),
                    **candidate.arena_map.public_geometry()},
            "player": {"name": self._player_name,
                       "hex_facing": player.native.being.hex_facing,
                       "posture": player.native.being.posture,
                       "posture_source": player.posture_provenance,
                       "cell": cell,
                       "position_meters": {"x": position.x, "y": position.y, "z": position.z}},
            "player_action": action,
            "pickup_action": pickup_action,
            "entities": perceived,
            "selected_entity": selected,
            "run_available": self._player_action_id is None and not candidate.encounter.initiated,
            "advance_available": ((self._player_action_id is not None
                                    and self._player_action_outcome is None)
                                   or (self._pickup_action_id is not None
                                       and self._pickup_action_outcome is None)
                                   or movement_plan is not None),
            "movement_available": movement_available,
            "movement_reason": None if movement_available else _MOVEMENT_DISABLED,
            "movement_plan": movement_plan,
            "movement_outcome": self._movement_outcome,
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
                    starting_experience, width_cells, height_cells, root_seed,
                    ground_item_descriptions=self._ground_item_descriptions,
                    ground_loadout_profile=self._ground_loadout_profile)
                encounter = candidate.encounter
                encounter.set_name("Encounter")
                candidate.participants[0].native.being.set_name(
                    candidate.participants[0].native.being.name or "Player")
                from arena_perception import refresh_candidate_names
                refresh_candidate_names(encounter)
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
            self._pickup_action_id = None
            self._pickup_action_outcome = None
            self._movement_plan = None
            self._movement_sequence = 0
            self._movement_outcome = None
            self._view_handles = {}
            self._selected_entity_handle = None
            self._display_names = {}
            return self._view_unlocked()

    def choose_destination(self, payload):
        if type(payload) is not dict or set(payload) != {"column", "row", "rate", "facing_policy"}:
            raise ArenaBrowserRequestError(
                "destination requires exactly column, row, rate, and facing_policy")
        column, row = payload["column"], payload["row"]
        if type(column) is not int or type(row) is not int:
            raise ArenaBrowserRequestError("destination cell coordinates must be native integers")
        rate, facing_policy = payload["rate"], payload["facing_policy"]
        if type(rate) is not str or rate not in _RATES:
            raise ArenaBrowserRequestError("rate must be Walk, Hustle, Jog, Run, or Sprint")
        if type(facing_policy) is not str or facing_policy not in ("turn", "maintain"):
            raise ArenaBrowserRequestError("facing_policy must be turn or maintain")
        with self._lock:
            if self._active is None:
                raise ArenaBrowserRequestError("Generate an Encounter before choosing a destination")
            candidate = self._active
            layout = candidate.arena_map.layout
            address = HexAddress(column, row)
            if not layout.contains(address):
                raise ArenaBrowserRequestError("destination cell is outside the generated hex footprint")
            player = candidate.participants[0].native.being
            if not self._view_unlocked()["movement_available"]:
                raise ArenaBrowserRequestError(_MOVEMENT_DISABLED)
            current = player.get_position()
            destination = layout.center_position(address, z=current.z)
            if destination == current:
                self._movement_plan = None
                self._movement_outcome = "already_at_destination"
                return self._view_unlocked()
            decision_id = f"arena-movement-{self._movement_sequence + 1}"
            if not candidate.encounter.initiated:
                try:
                    candidate.encounter.activate_arena_for_player_movement(
                        player.id, decision_id, rng_owner=self._rng_cursor)
                except Exception as exc:
                    raise ArenaBrowserRequestError(
                        "native movement Choice was not accepted; Arena state is unchanged") from exc
            self._movement_sequence += 1
            self._movement_plan = _MovementPlan(decision_id, destination, address,
                                                rate, facing_policy)
            self._movement_outcome = "destination_selected"
            return self._view_unlocked()

    def stop_movement(self, payload):
        if type(payload) is not dict or payload:
            raise ArenaBrowserRequestError("Stop accepts an empty request")
        with self._lock:
            if self._active is None:
                raise ArenaBrowserRequestError("Generate an Encounter before stopping movement")
            self._movement_plan = None
            self._movement_outcome = "stopped"
            return self._view_unlocked()

    def choose_run(self):
        """Accept the player's first native target-free Run Choice."""
        with self._lock:
            if self._active is None:
                raise ArenaBrowserRequestError("Generate an Encounter before choosing Run")
            if self._player_action_id is not None:
                raise ArenaBrowserRequestError("the first player Action has already been chosen")
            candidate = self._active
            if candidate.encounter.initiated:
                raise ArenaBrowserRequestError("the Arena timeline has already been activated")
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

    def inspect_entity(self, payload):
        from arena_perception import ArenaPerceptionLedger
        if type(payload) is not dict or set(payload) != {"handle"}:
            raise ArenaBrowserRequestError("inspection requires one visible entity handle")
        handle = payload["handle"]
        with self._lock:
            if self._active is None or type(handle) is not str:
                raise ArenaBrowserRequestError("visible entity handle is unavailable")
            entity_id = next((key for key, value in self._view_handles.items() if value == handle), None)
            ledger = object.__getattribute__(self._active.participants[0].native.being,
                                             "__dict__").get("_arena_perception_ledger")
            if (type(ledger) is not ArenaPerceptionLedger
                    or ledger.observer_id != self._active.participants[0].native.being.id
                    or entity_id is None
                    or entity_id not in {row.entity_id for row in ledger.current}):
                raise ArenaBrowserRequestError("entity is not supported by current observer evidence")
            self._selected_entity_handle = handle
            return self._view_unlocked()

    def rename_entity(self, payload):
        """Edit only the player's session-local display name for a perceived Entity."""
        from arena_perception import ArenaPerceptionLedger
        if type(payload) is not dict or set(payload) != {"handle", "name"}:
            raise ArenaBrowserRequestError("entity rename requires exactly handle and name")
        handle = payload["handle"]
        name = self._validate_name(payload["name"])
        with self._lock:
            if self._active is None or type(handle) is not str:
                raise ArenaBrowserRequestError("visible entity handle is unavailable")
            entity_id = next((key for key, value in self._view_handles.items() if value == handle), None)
            player = self._active.participants[0].native.being
            ledger = object.__getattribute__(player, "__dict__").get("_arena_perception_ledger")
            if (type(ledger) is not ArenaPerceptionLedger or ledger.observer_id != player.id
                    or entity_id is None):
                raise ArenaBrowserRequestError("entity is not supported by current observer evidence")
            evidence = next((row for row in ledger.current if row.entity_id == entity_id), None)
            if evidence is None:
                raise ArenaBrowserRequestError("entity is no longer perceived by this observer")
            self._display_names[entity_id] = name
            self._selected_entity_handle = handle
            return self._view_unlocked()

    def choose_pickup(self, payload):
        from activities import PickUpAction
        from arena_perception import ArenaPerceptionLedger
        if type(payload) is not dict or set(payload) != {"handle"}:
            raise ArenaBrowserRequestError("Pick up requires one visible entity handle")
        handle = payload["handle"]
        with self._lock:
            if self._active is None or type(handle) is not str:
                raise ArenaBrowserRequestError("visible ground Object handle is unavailable")
            if self._pickup_action_id is not None and self._pickup_action_outcome is None:
                raise ArenaBrowserRequestError("a Pick up Action is already resolving")
            entity_id = next((key for key, value in self._view_handles.items() if value == handle), None)
            player = self._active.participants[0].native.being
            ledger = object.__getattribute__(player, "__dict__").get("_arena_perception_ledger")
            if (type(ledger) is not ArenaPerceptionLedger
                    or ledger.observer_id != player.id):
                raise ArenaBrowserRequestError("player perception evidence is unavailable")
            evidence = None if entity_id is None else next(
                (row for row in ledger.current if row.entity_id == entity_id), None)
            if evidence is None or evidence.category != "object" or evidence.present_state != "ground":
                raise ArenaBrowserRequestError("Pick up requires a currently perceived ground Object")
            obj = self._active.universe.get_object_by_id(entity_id)
            if (obj is None or obj.parent_container_id is not None or obj.get_position() is None
                    or obj.geometry is not None or obj.visual_occlusion is not None):
                raise ArenaBrowserRequestError("current native Object state does not support this visible ground target")
            if obj.get_position() != evidence.position:
                raise ArenaBrowserRequestError("visible Object evidence is stale against current native position")
            layout = self._active.arena_map.layout
            player_cell, object_cell = layout.cell_at_position(player.get_position()), layout.cell_at_position(obj.get_position())
            if player_cell is None or player_cell != object_cell:
                raise ArenaBrowserRequestError("Pick up requires the player and free ground Object in the same hex")
            if not self._active.encounter.initiated:
                raise ArenaBrowserRequestError("activate the native Encounter before choosing Pick up")
            action = PickUpAction(self._active.encounter, player.id, entity_id,
                self._active.encounter.time, map_width_cells=self._active.arena_map.width_cells,
                map_height_cells=self._active.arena_map.height_cells)
            try:
                self._active.encounter.schedule_action(action)
            except Exception as exc:
                raise ArenaBrowserRequestError("native Pick up Choice was not accepted; Arena state is unchanged") from exc
            self._pickup_action_id = action.id
            self._pickup_action_outcome = None
            self._selected_entity_handle = handle
            return self._view_unlocked()

    def advance_one_second(self, *, trace_request_id=None, trace_client_sequence=None):
        """Commit exactly the native next boundary for the accepted player decision."""
        with self._lock:
            if self._active is None:
                raise ArenaBrowserRequestError("Generate an Encounter before advancing")
            candidate = self._active
            player = candidate.participants[0].native.being
            before_time = candidate.encounter.time
            before_position = player.get_position()
            before_cell = self._trace_cell(candidate, before_position)
            accepted_plan = self._movement_plan
            if self._player_action_id is None and self._pickup_action_id is None and self._movement_plan is None:
                self._trace_advance_state(candidate, trace_request_id, trace_client_sequence,
                                          before_time, before_position, before_cell, None,
                                          "refused", reason="no_movement_plan")
                raise ArenaBrowserRequestError("choose a destination or an explicit Run Choice before advancing")
            if (self._movement_plan is None and self._player_action_id is not None
                    and self._player_action_outcome is not None):
                self._trace_advance_state(candidate, trace_request_id, trace_client_sequence,
                                          before_time, before_position, before_cell, None,
                                          "refused", reason="run_choice_resolved")
                raise ArenaBrowserRequestError("the accepted Run Choice has already resolved")
            if (self._movement_plan is None and self._pickup_action_id is not None
                    and self._pickup_action_outcome is not None):
                raise ArenaBrowserRequestError("the accepted Pick up Choice has already resolved")
            try:
                if self._movement_plan is not None:
                    plan = self._movement_plan
                    conditions = self._movement_conditions(candidate)
                    next_boundary = candidate.encounter.last_processed_boundary + 1
                    intent = MovementIntent(
                        candidate.participants[0].native.being.id, plan.destination,
                        plan.rate, f"{plan.decision_id}:boundary:{next_boundary}", next_boundary,
                        facing_policy=plan.facing_policy)
                    candidate.encounter.step(1, movement_intent=intent,
                                             movement_conditions=conditions)
                    position = candidate.participants[0].native.being.get_position()
                    if position == plan.destination:
                        self._movement_plan = None
                        self._movement_outcome = "arrived"
                    else:
                        self._movement_outcome = "progressed"
                else:
                    candidate.encounter.step(1)
                if (self._player_action_id is not None
                        and candidate.encounter.time >= 1
                        and self._player_action_outcome is None):
                    result = candidate.encounter.inspect_committed(
                        int(candidate.encounter.time)).action(self._player_action_id)
                    self._player_action_outcome = result.facts.outcome
                if (self._pickup_action_id is not None
                        and candidate.encounter.time >= 1
                        and self._pickup_action_outcome is None):
                    result = candidate.encounter.inspect_committed(
                        int(candidate.encounter.time)).action(self._pickup_action_id)
                    self._pickup_action_outcome = result.facts.outcome
            except Exception as exc:
                after_time = candidate.encounter.time
                after_position = player.get_position()
                rolled_back = (after_time == before_time and after_position == before_position)
                self._trace_advance_state(
                    candidate, trace_request_id, trace_client_sequence,
                    before_time, before_position, before_cell, accepted_plan,
                    "rolled_back" if rolled_back else "failed_after_state_change",
                    reason=type(exc).__name__)
                raise ArenaBrowserRequestError(
                    "native one-second advancement failed; committed Arena state is unchanged") from exc
            self._trace_advance_state(candidate, trace_request_id, trace_client_sequence,
                                      before_time, before_position, before_cell, accepted_plan,
                                      "committed")
            return self._view_unlocked()

    @staticmethod
    def _movement_conditions(candidate):
        from activities import RunAction
        from movement_intent import MovementIntentRefusal

        for action_id in candidate.encounter.pending_action_list:
            action = candidate.universe.event_history.get(action_id)
            if type(action) is not RunAction:
                raise MovementIntentRefusal(
                    "unknown_action_demand", "movement cannot classify another active Action's demand")
        premise = candidate.world_premise
        return MovementRateConditions(
            terrain_multiplier=premise.terrain_multiplier,
            hampered_multiplier=premise.hampered_multiplier,
            direction=None,
            concurrent_demanding_action=False)

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
