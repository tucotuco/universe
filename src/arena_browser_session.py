"""Server-owned empty/generated Arena browser session and safe projection."""

from __future__ import annotations

import copy
import csv
import hashlib
import inspect
import json
import re
import random
import secrets
import threading
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from arena_initialization import ArenaInitializationRefusal, initialize_two_being_arena
from activities import RunAction, ReadyWeaponAction
from melee_combat import MeleeStrike, effective_melee_reach_meters
from atomic_publication import RNGCursor
from arena_hex_map import HexAddress
from movement_intent import MovementIntent, MovementRateConditions
from arena_ui_trace import ArenaUITerminalTrace
from melee_defense import MeleeDefense
from measured_values import truncate_measurement


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


@lru_cache(maxsize=1)
def _native_action_catalog():
    """Read the checked-in native Action catalog; labels are not support claims."""
    path = Path(__file__).resolve().parent / "config" / "actions.tsv"
    try:
        with path.open(encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream, delimiter="\t")
            expected = ("name", "target_type", "required_skill", "is_melee")
            if tuple(reader.fieldnames or ()) != expected:
                raise ValueError("native Action catalog schema is not supported")
            rows = []
            names = set()
            for row in reader:
                name = row["name"]
                if (type(name) is not str or not name or name in names
                        or row["target_type"] not in ("none", "being", "object", "weapon", "attack")
                        or type(row["required_skill"]) is not str
                        or row["is_melee"] not in ("True", "False")):
                    raise ValueError("native Action catalog row is malformed")
                names.add(name)
                rows.append({"name": name, "target_type": row["target_type"],
                             "required_skill": row["required_skill"],
                             "is_melee": row["is_melee"] == "True"})
            if not rows:
                raise ValueError("native Action catalog is empty")
            return tuple(rows)
    except (OSError, csv.Error, KeyError, ValueError) as exc:
        raise ArenaBrowserRequestError("native Action catalog is unavailable") from exc


@lru_cache(maxsize=None)
def _has_native_transactional_action_contract(action_type):
    """Confirm exact scheduler-preparer and resolver registrations read-only."""
    try:
        from scheduling import native_preparer
        from observer_proposals import _NATIVE_RESOLVERS
        resolver = inspect.getattr_static(action_type, "resolve", None)
        preparer = inspect.getattr_static(action_type, "prepare_schedule", None)
        return (_NATIVE_RESOLVERS.get(action_type) is resolver
                and native_preparer(object.__new__(action_type)) is preparer)
    except (AttributeError, TypeError, ValueError):
        return False


@dataclass(frozen=True)
class _MovementPlan:
    decision_id: str
    destination: object
    address: HexAddress
    rate: str
    facing_policy: str


class ArenaBrowserRequestError(ValueError):
    """A malformed or unavailable generated-Arena browser request."""

    def __init__(self, message, *, movement_refusal=None):
        super().__init__(message)
        self.movement_refusal = movement_refusal


def _safe_movement_refusal(refusal):
    """Map privileged native refusal details to an allowlisted player reason."""
    from movement_intent import MovementIntentRefusal

    current = refusal
    while current is not None and not isinstance(current, MovementIntentRefusal):
        current = current.__cause__
    if current is None:
        return None
    if current.code == "ineligible_actor":
        category = "actor_unable_to_move"
        message = ("Your Being is at 0 HP or below and cannot take voluntary movement under "
                   "the adopted rules.")
    elif current.code in ("no_movement_rate", "incapacitated"):
        category = "rate_unavailable"
        message = ("Your current native condition and the selected movement rate permit no "
                   "positive movement this second.")
    elif current.code == "unsupported_race":
        category = "unsupported_movement_profile"
        message = "Your Being's native movement profile is not supported, so this rate cannot be evaluated."
    elif current.code == "invalid_rate":
        category = "unsupported_rate"
        message = "The selected movement rate is not supported by the native movement rules."
    elif current.code.startswith(("unknown_", "missing_", "invalid_native", "stale_native")):
        category = "native_prerequisite_unavailable"
        message = "A required authoritative movement condition is unavailable; movement was not committed."
    else:
        category = "movement_prerequisite_not_met"
        message = "The native movement prerequisites were not met; movement was not committed."
    message += " No Encounter time or position changed; your destination plan remains selected."
    return {"category": category, "message": message}


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
                 ground_item_descriptions=None, ground_loadout_profile=None,
                 authored_draw_scenario=None, default_equipment_mode="unequipped"):
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
        self._ready_weapon_action_id = None
        self._ready_weapon_action_outcome = None
        self._ready_weapon_end_time = None
        self._opponent_strategy = "none"
        self._opponent_attack_refusal = "strategy_disabled"
        self._movement_plan = None
        self._movement_sequence = 0
        self._movement_outcome = None
        self._trace = ArenaUITerminalTrace(trace_ui, stream=trace_stream)
        # Optional caller-owned initial conditions; the browser still exposes
        # only its existing three Generate fields and has no gear distribution.
        self._ground_item_descriptions = copy.deepcopy(ground_item_descriptions)
        self._ground_loadout_profile = copy.deepcopy(ground_loadout_profile)
        from arena_loadout_profiles import bundled_profiles
        self._bundled_ground_profiles = bundled_profiles()
        self._uploaded_ground_profiles = {}
        self._selected_ground_profile_id = (
            None if self._ground_loadout_profile is None else
            self._ground_loadout_profile.get("profile_id", "caller-profile"))
        if authored_draw_scenario is not None and (
                ground_item_descriptions is not None or ground_loadout_profile is not None):
            raise ArenaBrowserRequestError(
                "authored Draw scenario cannot be combined with another initial equipment source")
        if authored_draw_scenario is not None:
            from arena_authored_draw_scenario import validate_scenario
            try:
                authored_draw_scenario = validate_scenario(authored_draw_scenario)
            except ValueError as exc:
                raise ArenaBrowserRequestError(str(exc)) from exc
        self._authored_draw_scenario = copy.deepcopy(authored_draw_scenario)
        if default_equipment_mode not in ("equipped", "unequipped"):
            raise ArenaBrowserRequestError("default equipment mode must be equipped or unequipped")
        self._default_equipment_mode = (
            "unequipped" if authored_draw_scenario is not None else default_equipment_mode)
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

    def save_encounter_bytes(self):
        """Capture the native graph and its Arena session sidecar atomically."""
        from arena_native_snapshot import capture
        from arena_persistence import encode
        with self._lock:
            if self._active is None:
                raise ArenaBrowserRequestError("Generate an Encounter before saving")
            try:
                self._validate_initial_equipment_provenance(self._active)
                inventory=capture(self._active.universe,self._active.encounter,self._rng_cursor)
                return encode(self,inventory)
            except (TypeError,ValueError,RuntimeError) as exc:
                detail = str(exc)
                raise ArenaBrowserRequestError(
                    "This Arena state cannot be saved yet; native checkpoint validation refused it: "
                    +detail) from exc

    @staticmethod
    def _validate_initial_equipment_provenance(candidate):
        from arena_initial_equipment import validate_saved_equipment_row
        mode = candidate.equipment_mode
        rows = candidate.initial_equipment_provenance
        if mode == "unequipped":
            if rows:
                raise ArenaBrowserRequestError("unequipped Arena has an unexpected initial kit claim")
            return True
        if mode != "equipped" or type(rows) not in (tuple, list) or len(rows) != 2:
            raise ArenaBrowserRequestError("equipped Arena does not record both participants' initial kits")
        by_being = {row.get("being_id"): row for row in rows if type(row) is dict}
        if len(by_being) != 2 or set(by_being) != set(candidate.encounter.being_list):
            raise ArenaBrowserRequestError("initial kit identities do not match native Encounter participants")
        source_by_being = {participant.native.being.id: participant.native.source_record_bytes
                           for participant in candidate.participants}
        if all(row.get("policy") == "universe-arena-class-xp-equipment/1"
               for row in by_being.values()):
            return GeneratedArenaSession._validate_legacy_initial_equipment_provenance(
                candidate, by_being)
        for being_id in candidate.encounter.being_list:
            being = candidate.universe.get_object_by_id(being_id)
            try:
                validate_saved_equipment_row(
                    by_being[being_id], being, source_by_being[being_id], candidate.universe)
            except (TypeError, ValueError, KeyError) as exc:
                raise ArenaBrowserRequestError(
                    "initial equipment commitment disagrees with its source profile or native state: "
                    + str(exc)) from exc
        return True

    @staticmethod
    def _validate_legacy_initial_equipment_provenance(candidate, by_being):
        """Keep the pre-U-ARENA-009 save representation readable without regeneration."""
        from armor import ArmorInstance
        from weapon import WeaponInstance

        for being_id in candidate.encounter.being_list:
            being = candidate.universe.get_object_by_id(being_id)
            row = by_being[being_id]
            if (type(row) is not dict or set(row) !=
                    {"policy", "being_id", "weapon", "armor", "shield"}
                    or row["policy"] != "universe-arena-class-xp-equipment/1"):
                raise ArenaBrowserRequestError("legacy initial kit provenance has an unsupported field set")
            weapon_row, armor_row, shield_row = row["weapon"], row["armor"], row["shield"]
            if (type(weapon_row) is not dict or type(armor_row) is not dict
                    or set(weapon_row) != {"object_id", "type", "hand", "basis", "status"}
                    or set(armor_row) != {"object_id", "type", "basis", "status"}):
                raise ArenaBrowserRequestError("legacy initial weapon/armor provenance is malformed")
            weapon = candidate.universe.get_object_by_id(weapon_row["object_id"])
            armor = candidate.universe.get_object_by_id(armor_row["object_id"])
            if (type(weapon) is not WeaponInstance or type(armor) is not ArmorInstance
                    or weapon.current.obj_type != weapon_row["type"]
                    or armor.current.obj_type != armor_row["type"]
                    or weapon.parent_container_id != being.id or armor.parent_container_id != being.id
                    or weapon.get_position() is not None or armor.get_position() is not None
                    or weapon.id not in being.possessions or armor.id not in being.possessions
                    or weapon.id not in being.weapons
                    or being.current.body_parts.get(weapon_row["hand"]) != weapon.id
                    or being.current.armor_id != armor.id):
                raise ArenaBrowserRequestError(
                    "legacy initial equipment claims disagree with native custody or slots")
            if shield_row is not None:
                if (type(shield_row) is not dict or set(shield_row) !=
                        {"object_id", "type", "hand", "basis", "status"}):
                    raise ArenaBrowserRequestError("legacy initial shield provenance is malformed")
                shield = candidate.universe.get_object_by_id(shield_row["object_id"])
                if (type(shield) is not WeaponInstance
                        or shield.current.obj_type != shield_row["type"]
                        or shield.parent_container_id != being.id or shield.get_position() is not None
                        or shield.id not in being.possessions or shield.id not in being.weapons
                        or being.current.body_parts.get(shield_row["hand"]) != shield.id):
                    raise ArenaBrowserRequestError(
                        "legacy initial shield claim disagrees with native custody or hand state")
        return True

    def load_encounter_bytes(self, wire):
        """Validate and atomically replace this session from a portable native file."""
        import base64
        import hashlib
        from arena_persistence import decode
        from arena_native_snapshot import restore as restore_native
        from arena_initialization import (ArenaInitializationCandidate,ArenaMap,
            ArenaWorldPremise,ArenaParticipant,ArenaPlacement)
        from arena_hex_map import ArenaHexLayout
        from arena_ground_objects import ArenaGroundObject
        from npcgen_arena_adapter import ArenaNativeBeing
        from spatial.state import CartesianPosition
        from arena_movement_plan_checkpoint import decode as decode_plan

        try:
            data=decode(wire)
            meta=data['session']
            universe,encounter,rng_owner=restore_native(data['decoded_native'])
            if (len(encounter.being_list)!=2 or meta['player_id']!=encounter.being_list[0]
                    or meta['opponent_id']!=encounter.being_list[1]
                    or meta['starting_experience']!=universe.get_object_by_id(meta['player_id']).original.experience):
                raise ArenaBrowserRequestError(
                    "Saved Arena participant order or starting experience disagrees with native state")
            width,height=meta['map']
            layout=ArenaHexLayout.rectangle(width,height)
            premise_data=meta['world_premise']
            if (type(premise_data) is not list or len(premise_data)!=6
                    or premise_data[:2]!=['Plains','Road']
                    or premise_data[2:4]!=[float(1.0).hex(),float(1.0).hex()]
                    or premise_data[4:]!=[True,False]):
                raise ArenaBrowserRequestError("Saved Arena movement premise is unsupported")
            premise=ArenaWorldPremise(premise_data[0],premise_data[1],
                float.fromhex(premise_data[2]),float.fromhex(premise_data[3]),
                premise_data[4],premise_data[5])
            participants=[]
            source_rows={row[1]:row for row in meta['source_beings']}
            for index,being_id in enumerate(encounter.being_list):
                row=source_rows.get(being_id)
                if (type(row) is not list or len(row)!=6
                        or row[0]!=('player_controlled' if index==0 else 'arena_controlled')):
                    raise ArenaBrowserRequestError("Saved Arena source provenance is incomplete")
                source=base64.b64decode(row[2],validate=True)
                if hashlib.sha256(source).hexdigest()!=row[3]:
                    raise ArenaBrowserRequestError("Saved Arena source record digest is invalid")
                being=universe.get_object_by_id(being_id)
                from npcgen_arena_adapter import validate_arena_initial_profile
                profile=object.__getattribute__(being, "__dict__").get("_arena_initial_profile")
                if not validate_arena_initial_profile(profile, source):
                    raise ArenaBrowserRequestError(
                        "Saved Arena initial Age/Class/skill provenance is inconsistent")
                position=being.get_position()
                address=layout.cell_at_position(position)
                if address is None:
                    raise ArenaBrowserRequestError("Saved Being position lies outside its recorded Arena map")
                native=ArenaNativeBeing(being,source,row[3],row[4],row[5])
                placement=ArenaPlacement(row[0],being_id,address.column,address.row,position)
                participants.append(ArenaParticipant(row[0],native,placement,0,0,
                    "restored from native checkpoint", "restored from native checkpoint"))
            ground=[]
            for row in meta['ground_objects']:
                if type(row) is not list or len(row)!=8 or row[1] not in encounter.non_being_object_list:
                    raise ArenaBrowserRequestError("Saved ground Object source mapping is malformed")
                point=CartesianPosition(*(float.fromhex(value) for value in row[7]))
                ground.append(ArenaGroundObject(row[0],row[1],row[2],row[3],row[4],
                    row[5],row[6],point))
            candidate=ArenaInitializationCandidate(universe,encounter,
                ArenaMap(width,height,layout),premise,meta['starting_experience'],
                meta['root_seed'],meta['placement_seed'],
                participants[0].native.engine_identity,tuple(participants),(),tuple(ground),
                tuple((row.source_item_id,row.native_object_id) for row in ground),
                layout,0,tuple(meta['ground_loadout_provenance']),
                tuple(meta['initial_equipment_provenance']),meta['equipment_mode'])
            self._validate_initial_equipment_provenance(candidate)
            plan_wire=(None if meta['movement_plan_base64'] is None else
                base64.b64decode(meta['movement_plan_base64'],validate=True))
            plan_data=None if plan_wire is None else decode_plan(plan_wire)
            plan=(None if plan_data is None else _MovementPlan(
                plan_data.decision_id, CartesianPosition(*plan_data.destination),
                HexAddress(*plan_data.cell), plan_data.rate, plan_data.facing_policy))
            if plan_data is not None:
                if (plan_data.universe_id!=universe.id or plan_data.encounter_id!=encounter.id
                        or plan_data.actor_id!=meta['player_id'] or plan_data.checkpoint_boundary!=encounter.time
                        or (encounter.arena_movement_activation is not None
                            and (encounter.arena_movement_activation.actor_id!=plan_data.actor_id
                                 or encounter.arena_movement_activation.time!=0))):
                    raise ArenaBrowserRequestError("Saved movement plan disagrees with native activation state")
        except ArenaBrowserRequestError:
            raise
        except (TypeError,ValueError,RuntimeError,KeyError,IndexError) as exc:
            raise ArenaBrowserRequestError(f"Saved Arena file was refused: {exc}") from exc

        with self._lock:
            old=(self._active,self._encounter_name,self._player_name,self._rng_cursor,
                 self._movement_plan,self._movement_sequence,self._display_names,
                 self._view_handles,self._selected_entity_handle,self._movement_outcome,
                 self._opponent_strategy,self._opponent_attack_refusal,
                 self._player_action_id,self._player_action_outcome,self._pickup_action_id,
                 self._pickup_action_outcome,self._ready_weapon_action_id,
                 self._ready_weapon_action_outcome,self._ready_weapon_end_time)
            try:
                self._active=candidate;self._encounter_name=meta['encounter_name']
                self._player_name=meta['player_name'];self._rng_cursor=rng_owner
                self._opponent_strategy=meta['opponent_strategy']
                self._opponent_attack_refusal="restored"
                self._movement_plan=plan;self._movement_sequence=meta['movement_sequence']
                self._display_names=dict(meta['display_names']);self._view_handles={}
                self._selected_entity_handle=None;self._movement_outcome=None
                self._player_action_id=None;self._player_action_outcome=None
                self._pickup_action_id=None;self._pickup_action_outcome=None
                self._ready_weapon_action_id=None;self._ready_weapon_action_outcome=None
                self._ready_weapon_end_time=None
                from activities import RunAction, PickUpAction, ReadyWeaponAction
                from encounter_inspection import inspect_encounter
                by_id={event_id:event for event_id,event in universe.event_history.items()}
                # A newly accepted Choice is not necessarily in event_history:
                # PickUpAction is held by ChoiceBook until its scheduled
                # boundary. Include those accepted native members so pending
                # Actions survive a server restart with their original timing.
                for accepted in encounter._choice_book._choices.values():
                    for member in accepted.members:
                        action=member.action
                        if type(action) in (RunAction,PickUpAction,ReadyWeaponAction):
                            by_id[action.id]=action
                native_actions=[event for event in by_id.values()
                    if type(event) in (RunAction,PickUpAction,ReadyWeaponAction)
                    and event.actor_id==meta['player_id']]
                completed={}
                if encounter._atomic_interval_history:
                    completed=inspect_encounter(encounter).actions
                for event in sorted(native_actions,key=lambda row:(row.start_time,row.id)):
                    outcome=(completed[event.id].facts.outcome if event.id in completed else None)
                    if type(event) is RunAction:
                        self._player_action_id=event.id;self._player_action_outcome=outcome
                    elif type(event) is PickUpAction:
                        self._pickup_action_id=event.id;self._pickup_action_outcome=outcome
                    elif type(event) is ReadyWeaponAction:
                        self._ready_weapon_action_id=event.id;self._ready_weapon_action_outcome=outcome
                        self._ready_weapon_end_time=event.end_time
                result=self._view_unlocked()
                selected_id=meta['selected_entity_id']
                if selected_id is not None:
                    self._selected_entity_handle=self._view_handles.get(selected_id)
                    if self._selected_entity_handle is None:
                        raise ArenaBrowserRequestError("Saved selected Entity is not in current observer evidence")
                    result=self._view_unlocked()
                return result
            except BaseException:
                (self._active,self._encounter_name,self._player_name,self._rng_cursor,
                 self._movement_plan,self._movement_sequence,self._display_names,
                 self._view_handles,self._selected_entity_handle,self._movement_outcome,
                 self._opponent_strategy,self._opponent_attack_refusal,
                 self._player_action_id,self._player_action_outcome,self._pickup_action_id,
                 self._pickup_action_outcome,self._ready_weapon_action_id,
                 self._ready_weapon_action_outcome,self._ready_weapon_end_time)=old
                raise

    def _view_unlocked(self):
        if self._active is None:
            return {
                "state": "empty",
                "save_available": False,
                "load_available": True,
                "spot_available": False,
                "spot_reason": _SPOT_DISABLED,
                "run_available": False,
                "advance_available": False,
                "movement_available": False,
                "movement_reason": _MOVEMENT_DISABLED,
                "starter_ground_equipment_available": self._ground_loadout_profile is not None,
                "default_equipment_mode": self._default_equipment_mode,
            }
        candidate = self._active
        from activities import PickUpAction, RunAction, SpotAction, ReadyWeaponAction
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
        ready_weapon_action = None
        if self._ready_weapon_action_id is not None:
            duration = ReadyWeaponAction.DRAW_DURATION_SECONDS
            remaining = (None if self._ready_weapon_end_time is None else
                         max(0, int(self._ready_weapon_end_time - candidate.encounter.time)))
            ready_weapon_action = {"name": "Draw",
                "status": "completed" if self._ready_weapon_action_outcome is not None else "executing",
                "outcome": self._ready_weapon_action_outcome,
                "duration_seconds": duration, "seconds_remaining": remaining}
        melee_action = self._melee_action_view(candidate, player.native.being)
        melee_pending = (melee_action is not None and melee_action["status"] == "executing")
        opponent = candidate.participants[1].native.being
        opponent_melee_action = self._opponent_melee_action_view(
            candidate, opponent, player.native.being)
        opponent_melee_pending = self._opponent_melee_pending(candidate, opponent)
        defense_action = self._defense_action_view(candidate, player.native.being)
        opponent_defense_action = self._opponent_defense_action_view(
            candidate, opponent, player.native.being)
        opponent_decision = self._opponent_decision(candidate)
        opponent_can_act = opponent_decision["kind"] in ("attack", "move", "defend", "prepare")
        self._opponent_attack_refusal = opponent_decision["reason"]
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
        supported_actions = {
            action_type: _has_native_transactional_action_contract(action_type)
            for action_type in (RunAction, SpotAction, PickUpAction, ReadyWeaponAction,
                                MeleeStrike, MeleeDefense)
        }
        perceived = []
        for evidence in ledger.current:
            handle = self._view_handles.get(evidence.entity_id)
            if handle is None:
                handle = secrets.token_urlsafe(18)
                self._view_handles[evidence.entity_id] = handle
            p = evidence.position
            address = None if p is None else candidate.arena_map.layout.cell_at_position(p)
            pickup_available, pickup_unavailable_reason = self._pickup_status_unlocked(
                candidate, player.native.being, evidence.entity_id, evidence)
            perceived.append({
                "handle": handle, "category": evidence.category,
                "name": self._display_names.get(evidence.entity_id, evidence.name),
                "type": evidence.type_key,
                "present_state": evidence.present_state,
                "equipment_status": evidence.equipment_status,
                "position_meters": None if p is None else {"x": p.x, "y": p.y, "z": p.z},
                "cell": None if address is None else {"column": address.column, "row": address.row},
                "pickup_available": pickup_available,
                "pickup_unavailable_reason": pickup_unavailable_reason,
            })
        selected = next((row for row in perceived
                         if row["handle"] == self._selected_entity_handle), None)
        selected_being = (self._observer_being_sheet_unlocked(candidate, selected)
                          if selected is not None and selected["category"] == "being" else None)
        character = self._player_character_sheet_unlocked(
            candidate, player, position, cell, movement_plan)
        action_catalog = self._action_catalog_unlocked(
            candidate, player.native.being, selected, supported_actions)
        return {
            "state": "active",
            "starter_ground_equipment_available": self._ground_loadout_profile is not None,
            "default_equipment_mode": candidate.equipment_mode,
            "save_available": True,
            "load_available": True,
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
            "character": character,
            "selected_being": selected_being,
            "player_action": action,
            "pickup_action": pickup_action,
            "ready_weapon_action": ready_weapon_action,
            "melee_action": melee_action,
            "opponent_melee_action": opponent_melee_action,
            "defense_action": defense_action,
            "opponent_defense_action": opponent_defense_action,
            "opponent_strategy": self._opponent_strategy,
            "opponent_activity": ("Dodge resolving" if opponent_defense_action is not None
                                  and opponent_defense_action["status"] in ("preparing", "committed") else
                                  "Thrust resolving" if opponent_melee_pending else
                                  "approaching" if opponent_decision["kind"] == "move" else
                                  "attack opportunity" if opponent_decision["kind"] == "attack" else
                                  "waiting" if self._opponent_strategy in ("attack_only", "defense_only") else "inactive"),
            "entities": perceived,
            "selected_entity": selected,
            "action_catalog": action_catalog,
            "run_available": self._player_action_id is None and not candidate.encounter.initiated,
            "advance_available": ((self._player_action_id is not None
                                    and self._player_action_outcome is None)
                                   or (self._pickup_action_id is not None
                                       and self._pickup_action_outcome is None)
                                   or (self._ready_weapon_action_id is not None
                                       and self._ready_weapon_action_outcome is None)
                                   or melee_pending
                                   or opponent_melee_pending
                                   or (defense_action is not None
                                       and defense_action["status"] in ("accepted", "preparing", "committed"))
                                   or (opponent_defense_action is not None
                                       and opponent_defense_action["status"] in ("accepted", "preparing", "committed"))
                                   or opponent_can_act
                                   or movement_plan is not None),
            "movement_available": movement_available,
            "movement_reason": None if movement_available else _MOVEMENT_DISABLED,
            "movement_plan": movement_plan,
            "movement_outcome": self._movement_outcome,
            "spot_available": False,
            "spot_reason": _SPOT_DISABLED,
        }

    @staticmethod
    def _pickup_target_unlocked(candidate, player, entity_id, evidence):
        """Share the exact read-only Pick up preflight between UI projection and submit."""
        if evidence is None or evidence.category != "object":
            raise ArenaBrowserRequestError("Select a currently perceived ground Object first.")
        if evidence.present_state != "ground":
            raise ArenaBrowserRequestError("Pick up is available only for a free ground Object.")
        obj = candidate.universe.get_object_by_id(entity_id)
        if (obj is None or obj.parent_container_id is not None or obj.get_position() is None
                or obj.geometry is not None or obj.visual_occlusion is not None):
            raise ArenaBrowserRequestError(
                "This Object is not a supported free ground target for generated-Arena Pick up.")
        if obj.get_position() != evidence.position:
            raise ArenaBrowserRequestError(
                "Visible Object evidence is stale against current native position; inspect it again.")
        layout = candidate.arena_map.layout
        player_cell = layout.cell_at_position(player.get_position())
        object_cell = layout.cell_at_position(obj.get_position())
        if player_cell is None or player_cell != object_cell:
            raise ArenaBrowserRequestError(
                "Move into the same hex as this Object before choosing Pick up.")
        encounter = candidate.encounter
        if not encounter.initiated:
            raise ArenaBrowserRequestError(
                "Activate the native Encounter with Run or movement before choosing Pick up.")
        if encounter.progression_mode != "transactional" or not encounter.arena_activation_enabled:
            raise ArenaBrowserRequestError("The native Arena Action pathway is unavailable.")
        return obj

    def _pickup_status_unlocked(self, candidate, player, entity_id, evidence):
        from activities import PickUpAction
        if not _has_native_transactional_action_contract(PickUpAction):
            return False, "The native Pick up scheduler or resolver contract is unavailable."
        if self._pickup_action_id is not None and self._pickup_action_outcome is None:
            return False, "A native Pick up Action is already resolving."
        try:
            self._pickup_target_unlocked(candidate, player, entity_id, evidence)
        except ArenaBrowserRequestError as exc:
            return False, str(exc)
        return True, "Native one-second Pick up is currently available for this Object."

    def _ready_weapon_target_unlocked(self, candidate, player, entity_id, evidence):
        from weapon import WeaponInstance, native_weapon_draw_location
        if evidence is None or evidence.category != "object" or evidence.present_state != "carried":
            return None, (), "Select a currently perceived, carried Weapon first."
        obj = candidate.universe.get_object_by_id(entity_id)
        if (type(obj) is not WeaponInstance or obj.id != entity_id
                or obj.current.obj_type != "Dagger"):
            return None, (), "Initial readying currently supports only an ordinary native Dagger."
        if (entity_id not in player.possessions or player.possessions.count(entity_id) != 1
                or obj.parent_container_id != player.id or obj.get_position() is not None):
            return None, (), "The selected Dagger is not in the player's native carried custody."
        if entity_id in player.weapons or entity_id in player.current.body_parts.values():
            return None, (), "This Dagger is already held/readied."
        if player.current.hit_points <= 0 or player.is_helpless():
            return None, (), "The player Being cannot perform a voluntary Action in its current native condition."
        if (not candidate.encounter.arena_activation_enabled
                or (candidate.encounter.initiated
                    and candidate.encounter.progression_mode != "transactional")
                or (not candidate.encounter.initiated
                    and candidate.encounter.progression_mode != "legacy")):
            return None, (), "The native Arena Action pathway is unavailable."
        if self._ready_weapon_action_id is not None and self._ready_weapon_action_outcome is None:
            return None, (), "A native Ready weapon Action is already resolving."
        try:
            location = native_weapon_draw_location(obj)
        except (TypeError, ValueError):
            return None, (), "The native Dagger draw-location record is malformed."
        if location is None:
            return None, (), (
                "The carried Dagger has no authored drawable source location. Ground Pick up does "
                "not designate a sheath or hand; retrieval time is undetermined."
            )
        if location["owner_id"] != player.id:
            return None, (), "The Dagger's drawable sheath is not assigned to the player Being."
        body_parts = player.current.body_parts
        hands = tuple(sorted(slot for slot, held in body_parts.items()
                             if slot in ReadyWeaponAction.HANDS and held is None))
        if not hands:
            return None, (), (
                "No explicitly modeled, free native left or right hand is available for this "
                "otherwise drawable Dagger."
            )
        return obj, hands, (
            "Native Draw from the explicitly authored worn sheath takes 2 seconds. "
            "Post-strike re-ready timing is separate."
        )

    @staticmethod
    def _initial_ready_dagger_id(candidate, player):
        """Return only the actual Dagger Object committed by initial Arena-ready state."""
        for row in candidate.initial_equipment_provenance:
            if type(row) is not dict or row.get("being_id") != player.id:
                continue
            # Current versioned npcgen.arena_ready_being commitment.
            specification = row.get("specification")
            object_ids = row.get("object_ids")
            if type(specification) is dict and type(object_ids) is dict:
                for unit in specification.get("equipment", {}).get("units", ()):
                    if (unit.get("role") == "primary_weapon"
                            and unit.get("category") == "weapon"
                            and unit.get("native_type_key") == "Dagger"):
                        return object_ids.get(unit.get("equipment_id"))
            # Strict compatibility for already-saved U-ARENA-009 initial kits.
            weapon = row.get("weapon")
            if (row.get("policy") == "universe-arena-class-xp-equipment/1"
                    and type(weapon) is dict and weapon.get("type") == "Dagger"):
                return weapon.get("object_id")
        return None

    @staticmethod
    def _player_melee_action(candidate, player):
        """Find the latest accepted native player MeleeStrike from Encounter state."""
        event_by_id = dict(candidate.universe.event_history)
        committed_ids = set(candidate.encounter.pending_action_list)
        committed_ids.update(candidate.encounter.finished_action_list)
        committed_ids.update(candidate.encounter.cancelled_action_list)
        choice_action_ids = set()
        for accepted in candidate.encounter._choice_book._choices.values():
            if accepted.view.state not in ("accepted", "executing", "finished"):
                continue
            choice_action_ids.update(accepted.view.action_ids)
            for member in accepted.members:
                if type(member.action) is MeleeStrike:
                    event_by_id[member.action.id] = member.action
        actions = [action for action in event_by_id.values()
                   if type(action) is MeleeStrike and action.actor_id == player.id
                   and action.id in committed_ids | choice_action_ids]
        return max(actions, key=lambda action: (action.start_time, action.id), default=None)

    @staticmethod
    def _melee_action_pending(candidate, action):
        if action is None:
            return False
        if action.id in candidate.encounter.pending_action_list:
            return True
        return (action.end_time > candidate.encounter.time and any(
            action.id in choice.view.action_ids
            and choice.view.state in ("accepted", "executing")
            for choice in candidate.encounter._choice_book._choices.values()))

    def _melee_action_view(self, candidate, player):
        action = self._player_melee_action(candidate, player)
        if action is None:
            return None
        target_name = None
        ledger = object.__getattribute__(player, "__dict__").get("_arena_perception_ledger")
        if ledger is not None:
            evidence = next((row for row in ledger.current
                             if row.entity_id == action.target_id), None)
            if evidence is not None:
                target_name = self._display_names.get(evidence.entity_id, evidence.name)
        if self._melee_action_pending(candidate, action):
            duration = action.end_time - action.start_time
            return {"name": action.event_type.title(), "status": "executing",
                    "outcome": None, "duration_seconds": duration,
                    "seconds_remaining": max(0, math.ceil(action.end_time - candidate.encounter.time)),
                    "target_name": target_name}
        if action.id in candidate.encounter.cancelled_action_list:
            return {"name": action.event_type.title(), "status": "cancelled",
                    "outcome": None, "duration_seconds": action.end_time - action.start_time,
                    "seconds_remaining": 0, "target_name": target_name}
        try:
            record = candidate.encounter.inspect_committed(
                int(math.ceil(action.end_time))).action(action.id)
        except (ValueError, KeyError, AttributeError):
            return {"name": action.event_type.title(), "status": "completed",
                    "outcome": "unavailable", "duration_seconds": action.end_time - action.start_time,
                    "seconds_remaining": 0, "target_name": target_name}
        distance = dict(record.facts.metadata).get("distance")
        return {"name": action.event_type.title(), "status": "completed",
                "outcome": record.facts.outcome,
                "duration_seconds": action.end_time - action.start_time,
                "seconds_remaining": 0, "target_name": target_name,
                "impact_distance_meters": distance}

    @staticmethod
    def _opponent_melee_action(candidate, opponent):
        return GeneratedArenaSession._latest_melee_action(candidate, opponent)

    @staticmethod
    def _all_melee_actions(candidate):
        event_by_id = dict(candidate.universe.event_history)
        committed_ids = set(candidate.encounter.pending_action_list)
        committed_ids.update(candidate.encounter.finished_action_list)
        committed_ids.update(candidate.encounter.cancelled_action_list)
        choice_ids = set()
        for accepted in candidate.encounter._choice_book._choices.values():
            choice_ids.update(accepted.view.action_ids)
            for member in accepted.members:
                if type(member.action) is MeleeStrike:
                    event_by_id[member.action.id] = member.action
        for action_id in committed_ids:
            action = candidate.universe.get_event_by_id(action_id)
            if type(action) is MeleeStrike:
                event_by_id[action.id] = action
        return [action for action in event_by_id.values()
                if type(action) is MeleeStrike
                and action.id in committed_ids | choice_ids]

    @staticmethod
    def _latest_melee_action(candidate, actor):
        actions = [action for action in GeneratedArenaSession._all_melee_actions(candidate)
                   if action.actor_id == actor.id]
        return max(actions, key=lambda action: (action.start_time, action.id), default=None)

    def _opponent_melee_pending(self, candidate, opponent):
        return self._melee_action_pending(
            candidate, self._opponent_melee_action(candidate, opponent))

    @staticmethod
    def _all_melee_defenses(candidate):
        event_by_id = dict(candidate.universe.event_history)
        committed = (set(candidate.encounter.pending_action_list)
                     | set(candidate.encounter.finished_action_list)
                     | set(candidate.encounter.cancelled_action_list))
        choice_ids = set()
        for record in candidate.encounter._choice_book._choices.values():
            if record.view.state not in ("accepted", "executing", "finished"):
                continue
            choice_ids.update(record.view.action_ids)
            for member in record.members:
                if type(member.action) is MeleeDefense:
                    event_by_id[member.action.id] = member.action
        for action_id in committed:
            action = candidate.universe.get_event_by_id(action_id)
            if type(action) is MeleeDefense:
                event_by_id[action.id] = action
        return [action for action in event_by_id.values()
                if type(action) is MeleeDefense and action.id in committed | choice_ids]

    @staticmethod
    def _latest_melee_defense(candidate, actor):
        actions = [action for action in GeneratedArenaSession._all_melee_defenses(candidate)
                   if action.actor_id == actor.id]
        return max(actions, key=lambda action: (action.start_time, action.id), default=None)

    @staticmethod
    def _retained_defense(candidate, actor, kind, instrument_id=None):
        encounter = candidate.encounter
        used = {action.prepared_defense_action_id
                for action in GeneratedArenaSession._all_melee_defenses(candidate)
                if action.prepared_defense_action_id is not None}
        ready = []
        for action in GeneratedArenaSession._all_melee_defenses(candidate):
            if (action.actor_id != actor.id or action.kind != kind
                    or action.target_action_id is not None
                    or (instrument_id is not None and action.instrument_id != instrument_id)
                    or action.id in used or action.id not in encounter.finished_action_list
                    or action.ready_at is None or action.ready_at > encounter.time):
                continue
            try:
                result = encounter.inspect_committed(math.ceil(action.end_time)).action(action.id)
            except (ValueError, KeyError, AttributeError):
                continue
            if result.facts.outcome == "ready":
                ready.append(action)
        return max(ready, key=lambda action: (action.ready_at, action.start_time, action.id),
                   default=None)

    @staticmethod
    def _visible_incoming_strike(candidate, defender, attacker, ledger):
        """Resolve one currently observed, still-pending native strike."""
        encounter = candidate.encounter
        evidence = None if ledger is None else next(
            (row for row in ledger.current if row.entity_id == attacker.id), None)
        if (ledger is None or ledger.observer_id != defender.id
                or evidence is None or evidence.category != "being"
                or evidence.present_state != "present" or evidence.time != encounter.time
                or evidence.position is None or not encounter.is_aware(defender.id, attacker.id)):
            return None
        visible_after = [action for action in GeneratedArenaSession._all_melee_actions(candidate)
                         if action.actor_id == attacker.id and action.target_id == defender.id
                         and action.id in encounter.pending_action_list
                         and action.start_time < encounter.time
                         and evidence.time >= action.start_time + 1]
        return min(visible_after, key=lambda action: (action.end_time, action.start_time, action.id),
                   default=None)

    @staticmethod
    def _melee_defense_pending(candidate, action):
        return GeneratedArenaSession._melee_action_pending(candidate, action)

    def _defense_action_view(self, candidate, actor):
        action = self._latest_melee_defense(candidate, actor)
        if action is None:
            return None
        name = action.kind.title()
        encounter = candidate.encounter
        pending = self._melee_defense_pending(candidate, action)
        accepted = None
        for record in encounter._choice_book._choices.values():
            if action.id in record.view.action_ids and record.view.state == "accepted":
                accepted = next((packet for member, packet in
                                 zip(record.members, record.prepared)
                                 if member.action.id == action.id), None)
                break
        if accepted is not None:
            end_time = accepted.end_time
            ready_at = dict(accepted.initialization).get("ready_at")
            status = "accepted"
        else:
            end_time = action.end_time
            ready_at = action.ready_at
            status = ("preparing" if ready_at is not None and encounter.time < ready_at else
                      "committed") if pending else "completed"
        remaining = max(0, math.ceil(end_time - encounter.time))
        if pending or accepted is not None:
            return {"name": name, "status": status, "outcome": None,
                    "duration_seconds": end_time - action.start_time,
                    "seconds_remaining": remaining,
                    "preparation_ready_at": ready_at}
        if action.id in encounter.cancelled_action_list:
            return {"name": name, "status": "cancelled", "outcome": None,
                    "duration_seconds": end_time - action.start_time,
                    "seconds_remaining": 0, "preparation_ready_at": ready_at}
        try:
            result = encounter.inspect_committed(int(math.ceil(end_time))).action(action.id)
        except (ValueError, KeyError, AttributeError):
            return {"name": name, "status": "completed", "outcome": "unavailable",
                    "duration_seconds": end_time - action.start_time,
                    "seconds_remaining": 0, "preparation_ready_at": ready_at}
        if result.facts.outcome == "ready" and self._retained_defense(candidate, actor, action.kind) is action:
            return {"name": name, "status": "ready", "outcome": None,
                    "duration_seconds": end_time - action.start_time,
                    "seconds_remaining": 0, "preparation_ready_at": ready_at}
        return {"name": name, "status": "completed", "outcome": result.facts.outcome,
                "duration_seconds": end_time - action.start_time,
                "seconds_remaining": 0, "preparation_ready_at": ready_at}

    def _opponent_defense_action_view(self, candidate, opponent, player):
        action = self._latest_melee_defense(candidate, opponent)
        # A target-free retained defense is the opponent's private plan; the
        # Arena player projection never exposes that decision or its source ID.
        if action is None or action.target_id != player.id:
            return None
        ledger = object.__getattribute__(player, "__dict__").get("_arena_perception_ledger")
        evidence = None if ledger is None else next(
            (row for row in ledger.current if row.entity_id == opponent.id), None)
        if (evidence is None or evidence.category != "being"
                or evidence.present_state != "present"
                or evidence.time < action.start_time + 1
                or not candidate.encounter.is_aware(player.id, opponent.id)):
            return None
        return self._defense_action_view(candidate, opponent)

    def _opponent_defense_decision(self, candidate):
        if self._opponent_strategy != "defense_only":
            return {"kind": "none", "reason": "strategy_disabled"}
        encounter = candidate.encounter
        if (not encounter.initiated or encounter.progression_mode != "transactional"
                or not encounter.arena_activation_enabled):
            return {"kind": "none", "reason": "encounter_not_activated"}
        opponent = candidate.participants[1].native.being
        player = candidate.participants[0].native.being
        ledger = object.__getattribute__(opponent, "__dict__").get("_arena_perception_ledger")
        evidence = None if ledger is None else next(
            (row for row in ledger.current if row.entity_id == player.id), None)
        if (evidence is None or evidence.category != "being"
                or evidence.present_state != "present" or evidence.time != encounter.time
                or evidence.position is None or not encounter.is_aware(opponent.id, player.id)):
            return {"kind": "none", "reason": "opponent_has_no_current_awareness_evidence"}
        if opponent.get_hit_points() <= 0 or opponent.is_helpless():
            return {"kind": "none", "reason": "opponent_unable_to_defend"}
        if encounter._choice_book.actor_planned_now(opponent.id):
            return {"kind": "none", "reason": "opponent_action_already_pending"}
        current_defense = self._latest_melee_defense(candidate, opponent)
        if self._melee_defense_pending(candidate, current_defense):
            return {"kind": "none", "reason": "opponent_defense_already_pending"}
        strike = self._visible_incoming_strike(candidate, opponent, player, ledger)
        retained = self._retained_defense(candidate, opponent, "dodge")
        # Prefer a legal shield Block only when the opponent's actual native
        # equipment supplies one and its adopted timing reaches this strike.
        if strike is not None:
            for shield_id in sorted(opponent.shielded_with(candidate.universe).values()):
                defense = MeleeDefense(encounter, opponent.id, player.id,
                                       kind="block", target_action_id=strike.id,
                                       weapon_id=shield_id)
                try:
                    prepared = encounter.prepare_action(defense)
                except (TypeError, ValueError, RuntimeError):
                    continue
                return {"kind": "defend", "reason": "observed_strike_native_block",
                        "strike": strike, "action": defense, "prepared": prepared}
        if retained is not None:
            if strike is None:
                return {"kind": "none", "reason": "retaining_ready_native_dodge"}
            defense = MeleeDefense(encounter, opponent.id, player.id,
                kind="dodge", target_action_id=strike.id,
                prepared_defense_action_id=retained.id)
            try:
                prepared = encounter.prepare_action(defense)
            except (TypeError, ValueError, RuntimeError) as exc:
                return {"kind": "none", "reason": "retained_dodge_not_eligible:" + str(exc)}
            return {"kind": "defend", "reason": "observed_strike_retained_native_dodge",
                    "strike": strike, "action": defense, "prepared": prepared}
        from strategy import Strategy
        try:
            pool = MeleeDefense.dodge_strategy_pool(opponent, candidate.universe)
            defense = MeleeDefense(encounter, opponent.id, kind="dodge",
                                   strategy=Strategy(defense=pool, timing=0))
            prepared = encounter.prepare_action(defense)
        except (TypeError, ValueError, RuntimeError) as exc:
            return {"kind": "none", "reason": "native_dodge_preparation_unavailable:" + str(exc)}
        if strike is not None and prepared.end_time > strike.end_time:
            return {"kind": "none", "reason": "native_dodge_not_ready_before_impact"}
        return {"kind": "prepare", "reason": "target_free_native_dodge_preparation",
                "strike": strike, "action": defense, "prepared": prepared}

    def _schedule_opponent_defense(self, candidate, decision):
        if decision["kind"] not in ("defend", "prepare"):
            return None
        action = decision["action"]
        encounter = candidate.encounter
        sequence = 1 + sum(row.actor_id == action.actor_id
                           for row in self._all_melee_defenses(candidate))
        action.id = f"{encounter.id}/arena-opponent-{action.kind}/{sequence}"
        try:
            prepared = encounter.prepare_action(action)
            encounter.schedule_action(action)
        except Exception as exc:
            raise ArenaBrowserRequestError(
                "native opponent Dodge was not accepted; Arena state is unchanged") from exc
        self._trace.native_advance(None, None,
            f"action=opponent_defense kind={action.kind} preparation="
            f"{dict(prepared.initialization)['ready_at']-prepared.start_time:g}s")
        return action

    def _opponent_attack_preflight(self, candidate):
        """Read-only attack-only eligibility from opponent-owned current state."""
        if self._opponent_strategy != "attack_only":
            return False, "strategy_disabled"
        encounter = candidate.encounter
        if (not encounter.initiated or encounter.progression_mode != "transactional"
                or not encounter.arena_activation_enabled):
            return False, "encounter_not_activated"
        opponent = candidate.participants[1].native.being
        player = candidate.participants[0].native.being
        if self._opponent_melee_pending(candidate, opponent):
            return False, "opponent_melee_already_pending"
        if any(action.actor_id == opponent.id
               for action in (candidate.universe.event_history.get(action_id)
                              for action_id in encounter.pending_action_list)
               if action is not None):
            return False, "opponent_action_already_pending"
        ledger = object.__getattribute__(opponent, "__dict__").get("_arena_perception_ledger")
        evidence = (None if ledger is None else next(
            (row for row in ledger.current if row.entity_id == player.id), None))
        if (evidence is None or evidence.category != "being"
                or evidence.present_state != "present"
                or evidence.time != encounter.time or evidence.position is None
                or not encounter.is_aware(opponent.id, player.id)):
            return False, "opponent_has_no_current_awareness_evidence"
        if opponent.get_hit_points() <= 0 or opponent.is_helpless():
            return False, "opponent_unable_to_act"
        if opponent.get_fatigue_level() >= 5:
            return False, "opponent_unable_to_attack_at_current_fatigue"
        weapon_id = self._initial_ready_dagger_id(candidate, opponent)
        from weapon import WeaponInstance
        weapon = candidate.universe.get_object_by_id(weapon_id) if type(weapon_id) is str else None
        if (type(weapon) is not WeaponInstance or weapon.id not in opponent.weapons
                or weapon.id not in opponent.armed_with(candidate.universe).values()
                or weapon.parent_container_id != opponent.id or weapon.get_position() is not None
                or weapon.current.obj_type != "Dagger"
                or "thrust" not in weapon.get_melee_types()):
            return False, "opponent_has_no_ready_native_thrust_dagger"
        if encounter._choice_book.actor_planned_now(opponent.id):
            return False, "opponent_action_already_pending"
        if not _has_native_transactional_action_contract(MeleeStrike):
            return False, "native_melee_contract_unavailable"
        return True, "eligible"

    def _opponent_decision(self, candidate):
        """Derive one attack-only choice from the opponent's current evidence."""
        if self._opponent_strategy == "defense_only":
            return self._opponent_defense_decision(candidate)
        eligible, reason = self._opponent_attack_preflight(candidate)
        if not eligible:
            return {"kind": "none", "reason": reason}
        encounter = candidate.encounter
        opponent = candidate.participants[1].native.being
        player = candidate.participants[0].native.being
        weapon_id = self._initial_ready_dagger_id(candidate, opponent)
        weapon = candidate.universe.get_object_by_id(weapon_id)
        reach = effective_melee_reach_meters(opponent.current, weapon.current)
        strike = MeleeStrike(encounter, opponent.id, player.id, weapon.id,
                             motion="thrust", reach=reach)
        status, _ = strike._status(encounter)
        if status == "in_reach":
            return {"kind": "attack", "reason": "native_thrust_in_reach"}
        if status not in ("not_facing", "out_of_reach"):
            return {"kind": "none", "reason": "native_thrust_" + str(status)}
        # The current ordinary starter profile includes unmodeled ground
        # Objects. Keep its conservative path behavior; attack-only pursuit
        # is limited to explicitly empty-ground encounters.
        if candidate.ground_objects:
            return {"kind": "none", "reason": "unmodeled_ground_objects"}
        layout = candidate.arena_map.layout
        ledger = object.__getattribute__(opponent, "__dict__").get("_arena_perception_ledger")
        evidence = None if ledger is None else next(
            (row for row in ledger.current if row.entity_id == player.id), None)
        if (evidence is None or evidence.time != encounter.time
                or evidence.present_state != "present" or evidence.position is None):
            return {"kind": "none", "reason": "opponent_has_no_current_awareness_evidence"}
        observed_cell = layout.cell_at_position(evidence.position)
        start = opponent.get_position()
        if observed_cell is None or start is None or layout.cell_at_position(start) is None:
            return {"kind": "none", "reason": "unplaced_participant"}
        start_cell = layout.cell_at_position(start)
        from hex_facing import nearest_facing
        recent_cells = set()
        if type(encounter.time) is int:
            for prior_boundary in range(max(1, encounter.time - 3), encounter.time):
                try:
                    prior_position = encounter.inspect_committed(prior_boundary).target(
                        opponent.id).position
                    prior_cell = layout.cell_at_position(prior_position)
                    if prior_cell is not None:
                        recent_cells.add(prior_cell)
                except (ValueError, KeyError, AttributeError):
                    continue
        options = []
        for address in layout.neighbors(observed_cell):
            if not layout.contains(address) or address in (observed_cell, start_cell):
                continue
            destination = layout.center_position(address, z=start.z)
            delta = (destination.x - start.x, destination.y - start.y,
                     destination.z - start.z)
            if not any(delta):
                continue
            heading = nearest_facing(delta)
            target_heading = nearest_facing((evidence.position.x - destination.x,
                                             evidence.position.y - destination.y,
                                             evidence.position.z - destination.z))
            heading_delta = abs(heading - target_heading)
            heading_delta = min(heading_delta, 12 - heading_delta)
            options.append((heading_delta > 1, heading_delta,
                            address in recent_cells,
                            math.dist(start.as_tuple(), destination.as_tuple()),
                            address.column, address.row, address, destination))
        if not options:
            return {"kind": "none", "reason": "no_lawful_in_map_approach_destination"}
        # Native position history supplies a short anti-reversal tie-break so
        # a one-boundary destination is not alternated endlessly. It adds no
        # controller state and makes no collision or pathfinding claim.
        _, _, _, _, _, _, address, destination = min(options)
        return {"kind": "move", "reason": "native_turn_and_move_approach",
                "address": address, "destination": destination}

    def _schedule_opponent_attack(self, candidate):
        decision = self._opponent_decision(candidate)
        self._opponent_attack_refusal = decision["reason"]
        if decision["kind"] != "attack":
            return None
        encounter = candidate.encounter
        opponent = candidate.participants[1].native.being
        player = candidate.participants[0].native.being
        weapon_id = self._initial_ready_dagger_id(candidate, opponent)
        weapon = candidate.universe.get_object_by_id(weapon_id)
        reach = effective_melee_reach_meters(opponent.current, weapon.current)
        action = MeleeStrike(encounter, opponent.id, player.id, weapon.id,
                             motion="thrust", reach=reach)
        # Event IDs are part of native Choice history. A stable encounter-local
        # name keeps a future AI declaration reproducible after save/restore.
        sequence = 1 + sum(action.actor_id == opponent.id
                           for action in self._all_melee_actions(candidate))
        action.id = f"{encounter.id}/arena-opponent-thrust/{sequence}"
        try:
            encounter.prepare_action(action)
            encounter.schedule_action(action)
        except Exception as exc:
            self._opponent_attack_refusal = "native_scheduler_refused"
            raise ArenaBrowserRequestError(
                "native opponent Dagger strike was not accepted; Arena state is unchanged") from exc
        self._opponent_attack_refusal = "scheduled"
        self._trace.native_advance(None, None,
            f"action=opponent_melee_strike motion=thrust duration={action.end_time-action.start_time:g}s")
        return action

    def _opponent_melee_action_view(self, candidate, opponent, player):
        action = self._opponent_melee_action(candidate, opponent)
        if action is None:
            return None
        ledger = object.__getattribute__(player, "__dict__").get("_arena_perception_ledger")
        actor_evidence = (None if ledger is None else next(
            (row for row in ledger.current if row.entity_id == opponent.id), None))
        # Revision 61 timing: an Action declaration is not knowable in its
        # declaration second. Revision 65's current observer evidence supports
        # presentation beginning at the next native second.
        if (actor_evidence is None or actor_evidence.category != "being"
                or actor_evidence.present_state != "present"
                or actor_evidence.time < action.start_time + 1
                or not candidate.encounter.is_aware(player.id, opponent.id)):
            return None
        if self._melee_action_pending(candidate, action):
            return {"name": action.event_type.title(), "status": "executing",
                    "outcome": None,
                    "duration_seconds": action.end_time-action.start_time,
                    "seconds_remaining": max(0, math.ceil(action.end_time-candidate.encounter.time))}
        if action.id in candidate.encounter.cancelled_action_list:
            return {"name": action.event_type.title(), "status": "cancelled",
                    "outcome": None,
                    "duration_seconds": action.end_time-action.start_time,
                    "seconds_remaining": 0}
        try:
            result = candidate.encounter.inspect_committed(
                int(math.ceil(action.end_time))).action(action.id)
        except (ValueError, KeyError, AttributeError):
            return {"name": action.event_type.title(), "status": "completed",
                    "outcome": "unavailable",
                    "duration_seconds": action.end_time-action.start_time,
                    "seconds_remaining": 0}
        return {"name": action.event_type.title(), "status": "completed",
                "outcome": result.facts.outcome,
                "duration_seconds": action.end_time-action.start_time,
                "seconds_remaining": 0}

    def _melee_strike_preflight(self, candidate, player, entity_id, evidence, motion,
                                supported=True):
        if motion not in ("swing", "thrust"):
            raise ArenaBrowserRequestError("Choose the native Dagger Swing or Thrust motion.")
        if not supported or not _has_native_transactional_action_contract(MeleeStrike):
            raise ArenaBrowserRequestError("The native melee scheduler or resolver contract is unavailable.")
        if evidence is None or evidence.category != "being" or evidence.present_state != "present":
            raise ArenaBrowserRequestError("Select a currently perceived opposing Being first.")
        encounter = candidate.encounter
        target = encounter.get_being(entity_id) if type(entity_id) is str else None
        if (target is None or entity_id not in encounter.being_list
                or target.id == player.id or not encounter.is_aware(player.id, target.id)):
            raise ArenaBrowserRequestError("The selected target is not an aware participating Being.")
        if not encounter.initiated:
            raise ArenaBrowserRequestError("Move or choose Run to activate the native Encounter before attacking.")
        if encounter.progression_mode != "transactional":
            raise ArenaBrowserRequestError("The native transactional Arena Action pathway is unavailable.")
        latest = self._player_melee_action(candidate, player)
        if self._melee_action_pending(candidate, latest):
            raise ArenaBrowserRequestError("A native melee Action is already resolving for the player.")
        if player.get_hit_points() <= 0 or target.get_hit_points() <= 0:
            raise ArenaBrowserRequestError("Both Beings must have positive native hit points to schedule a strike.")
        weapon_id = self._initial_ready_dagger_id(candidate, player)
        from weapon import WeaponInstance
        weapon = candidate.universe.get_object_by_id(weapon_id) if type(weapon_id) is str else None
        if (type(weapon) is not WeaponInstance or weapon.id not in player.weapons
                or weapon.id not in player.armed_with(candidate.universe).values()
                or weapon.parent_container_id != player.id or weapon.get_position() is not None
                or weapon.current.obj_type != "Dagger"):
            raise ArenaBrowserRequestError(
                "The API-created initial Dagger is not currently held and readied by the player.")
        if motion not in weapon.get_melee_types():
            raise ArenaBrowserRequestError(f"The native Dagger does not support {motion}.")
        reach = effective_melee_reach_meters(player.current, weapon.current)
        action = MeleeStrike(encounter, player.id, target.id, weapon.id,
                             motion=motion, reach=reach)
        try:
            prepared = encounter.prepare_action(action)
        except Exception as exc:
            raise ArenaBrowserRequestError(
                f"Native {motion} Choice is unavailable under the current Encounter state.") from exc
        distance = encounter.distance_between_beings(player.id, target.id)
        return action, weapon, prepared, distance, reach

    def choose_melee_strike(self, payload):
        if type(payload) is not dict or set(payload) != {"handle", "motion"}:
            raise ArenaBrowserRequestError("melee attack requires exactly one perceived target and motion")
        handle, motion = payload["handle"], payload["motion"]
        if type(handle) is not str or type(motion) is not str:
            raise ArenaBrowserRequestError("melee target and motion must be text")
        with self._lock:
            if self._active is None:
                raise ArenaBrowserRequestError("Generate an Encounter before choosing a melee attack")
            candidate = self._active
            player = candidate.participants[0].native.being
            entity_id = next((key for key, value in self._view_handles.items()
                              if value == handle), None)
            ledger = object.__getattribute__(player, "__dict__").get("_arena_perception_ledger")
            if ledger is None or ledger.observer_id != player.id:
                raise ArenaBrowserRequestError("player perception evidence is unavailable")
            evidence = None if entity_id is None else next(
                (row for row in ledger.current if row.entity_id == entity_id), None)
            action, _, prepared, _, _ = self._melee_strike_preflight(
                candidate, player, entity_id, evidence, motion)
            try:
                candidate.encounter.schedule_action(action)
            except Exception as exc:
                raise ArenaBrowserRequestError(
                    "native melee Choice was not accepted; Arena state is unchanged") from exc
            self._selected_entity_handle = handle
            self._trace.native_advance(None, None,
                f"action=melee_strike motion={motion} duration={prepared.end_time-prepared.start_time:g}s")
            return self._view_unlocked()

    def _player_dodge_preflight(self, candidate, player, entity_id, evidence,
                                supported=True):
        if not supported or not _has_native_transactional_action_contract(MeleeDefense):
            raise ArenaBrowserRequestError("The native MeleeDefense scheduler or resolver contract is unavailable.")
        if evidence is None or evidence.category != "being" or evidence.present_state != "present":
            raise ArenaBrowserRequestError("Select the currently perceived attacker first.")
        encounter = candidate.encounter
        attacker = encounter.get_being(entity_id) if type(entity_id) is str else None
        if (attacker is None or attacker.id == player.id
                or not encounter.is_aware(player.id, attacker.id)):
            raise ArenaBrowserRequestError("The selected Entity is not an aware participating attacker.")
        if not encounter.initiated or encounter.progression_mode != "transactional":
            raise ArenaBrowserRequestError("Activate the native Encounter before choosing Dodge.")
        if encounter._choice_book.actor_planned_now(player.id):
            raise ArenaBrowserRequestError("The player already has a native Action accepted or resolving.")
        current_defense = self._latest_melee_defense(candidate, player)
        if self._melee_defense_pending(candidate, current_defense):
            raise ArenaBrowserRequestError("A player Dodge is already preparing or committed.")
        prepared = self._retained_defense(candidate, player, "dodge")
        if prepared is None:
            raise ArenaBrowserRequestError("Prepare a native Dodge first; an unprepared Dodge cannot be assigned to a strike.")
        ledger = object.__getattribute__(player, "__dict__").get("_arena_perception_ledger")
        strike = self._visible_incoming_strike(candidate, player, attacker, ledger)
        if strike is None:
            raise ArenaBrowserRequestError(
                "No currently perceived, pending native strike from this Being can be designated for Dodge.")
        action = MeleeDefense(encounter, player.id, attacker.id, kind="dodge",
                              target_action_id=strike.id,
                              prepared_defense_action_id=prepared.id)
        try:
            prepared = encounter.prepare_action(action)
        except Exception as exc:
            raise ArenaBrowserRequestError(
                "The native two-second Dodge cannot be ready before this strike's impact.") from exc
        return action, prepared, strike

    def choose_dodge(self, payload):
        if (type(payload) is dict and set(payload) == {"defense", "timing"}):
            return self.prepare_dodge(payload)
        if type(payload) is not dict or set(payload) != {"handle"}:
            raise ArenaBrowserRequestError("Dodge preparation requires defense/timing allocation; use requires one perceived attacker handle")
        handle = payload["handle"]
        if type(handle) is not str:
            raise ArenaBrowserRequestError("Dodge attacker handle must be text")
        with self._lock:
            if self._active is None:
                raise ArenaBrowserRequestError("Generate an Encounter before choosing Dodge")
            candidate = self._active
            player = candidate.participants[0].native.being
            entity_id = next((key for key, value in self._view_handles.items()
                              if value == handle), None)
            ledger = object.__getattribute__(player, "__dict__").get("_arena_perception_ledger")
            if ledger is None or ledger.observer_id != player.id:
                raise ArenaBrowserRequestError("player perception evidence is unavailable")
            evidence = None if entity_id is None else next(
                (row for row in ledger.current if row.entity_id == entity_id), None)
            action, prepared, _strike = self._player_dodge_preflight(
                candidate, player, entity_id, evidence)
            try:
                candidate.encounter.schedule_action(action)
            except Exception as exc:
                raise ArenaBrowserRequestError(
                    "native Dodge Choice was not accepted; Arena state is unchanged") from exc
            self._selected_entity_handle = handle
            self._trace.native_advance(None, None,
                f"action=player_defense kind=dodge preparation="
                f"{dict(prepared.initialization)['ready_at']-prepared.start_time:g}s")
            return self._view_unlocked()

    def choose_parry(self, payload):
        if type(payload) is not dict:
            raise ArenaBrowserRequestError("Parry request must be an object")
        if set(payload) == {"weapon_handle", "motion"}:
            weapon_handle, motion = payload["weapon_handle"], payload["motion"]
            if type(weapon_handle) is not str or motion not in ("swing", "thrust"):
                raise ArenaBrowserRequestError("Parry preparation requires an equipped weapon and selected swing/thrust timing")
            with self._lock:
                if self._active is None:
                    raise ArenaBrowserRequestError("Generate an Encounter before preparing Parry")
                candidate = self._active
                encounter = candidate.encounter
                player = candidate.participants[0].native.being
                weapon_id = next((key for key, value in self._view_handles.items()
                                  if value == weapon_handle), None)
                from weapon import WeaponInstance
                weapon = candidate.universe.get_object_by_id(weapon_id) if type(weapon_id) is str else None
                if (type(weapon) is not WeaponInstance or weapon.id not in player.armed_with(candidate.universe).values()
                        or player.get_weapon_skill_level(weapon.original.obj_type) <= 1):
                    raise ArenaBrowserRequestError("Parry requires an actually held weapon with advanced native skill")
                if not encounter.initiated or encounter.progression_mode != "transactional":
                    raise ArenaBrowserRequestError("Activate the native Encounter before preparing Parry")
                if encounter._choice_book.actor_planned_now(player.id):
                    raise ArenaBrowserRequestError("The player already has an accepted native Action")
                if self._retained_defense(candidate, player, "parry", weapon.id) is not None:
                    raise ArenaBrowserRequestError("This native weapon already has a retained Parry")
                action = MeleeDefense(encounter, player.id, kind="parry",
                                      weapon_id=weapon.id, parry_motion=motion)
                try:
                    prepared = encounter.prepare_action(action)
                    encounter.schedule_action(action)
                except Exception as exc:
                    raise ArenaBrowserRequestError("Native Parry preparation was refused without publishing the Choice") from exc
                self._trace.native_advance(None, None,
                    f"action=player_defense kind=parry motion={motion} preparation="
                    f"{prepared.end_time-prepared.start_time:g}s")
                return self._view_unlocked()
        if set(payload) != {"handle", "weapon_handle"}:
            raise ArenaBrowserRequestError("Parry use requires a perceived attacker and retained weapon handle")
        handle, weapon_handle = payload["handle"], payload["weapon_handle"]
        with self._lock:
            if self._active is None:
                raise ArenaBrowserRequestError("Generate an Encounter before using Parry")
            candidate = self._active
            encounter = candidate.encounter
            player = candidate.participants[0].native.being
            entity_id = next((key for key, value in self._view_handles.items() if value == handle), None)
            weapon_id = next((key for key, value in self._view_handles.items() if value == weapon_handle), None)
            ledger = object.__getattribute__(player, "__dict__").get("_arena_perception_ledger")
            evidence = None if ledger is None or entity_id is None else next(
                (row for row in ledger.current if row.entity_id == entity_id), None)
            attacker = encounter.get_being(entity_id) if type(entity_id) is str else None
            source = self._retained_defense(candidate, player, "parry", weapon_id)
            if (attacker is None or attacker.id == player.id or evidence is None
                    or evidence.category != "being" or evidence.present_state != "present"
                    or not encounter.is_aware(player.id, attacker.id)):
                raise ArenaBrowserRequestError("Parry requires a currently perceived attacker")
            if source is None:
                raise ArenaBrowserRequestError("Prepare Parry with this weapon before assigning it to an attack")
            if encounter._choice_book.actor_planned_now(player.id):
                raise ArenaBrowserRequestError("The player already has an accepted native Action")
            strike = self._visible_incoming_strike(candidate, player, attacker, ledger)
            if strike is None:
                raise ArenaBrowserRequestError("No currently perceived pending native strike can be parried")
            action = MeleeDefense(encounter, player.id, attacker.id, kind="parry",
                                  target_action_id=strike.id,
                                  prepared_defense_action_id=source.id)
            try:
                prepared = encounter.prepare_action(action)
                encounter.schedule_action(action)
            except Exception as exc:
                raise ArenaBrowserRequestError(str(exc)) from exc
            self._trace.native_advance(None, None,
                f"action=player_defense kind=parry assigned_motion={source.parry_motion}")
            self._selected_entity_handle = handle
            return self._view_unlocked()

    def prepare_dodge(self, payload):
        from strategy import Strategy
        if type(payload) is not dict or set(payload) != {"defense", "timing"}:
            raise ArenaBrowserRequestError("Dodge requires exactly the adopted defense and timing allocations")
        defense, timing = payload["defense"], payload["timing"]
        if type(defense) is not int or type(timing) is not int or min(defense, timing) < 0:
            raise ArenaBrowserRequestError("Dodge allocations must be nonnegative integer strategy points")
        with self._lock:
            if self._active is None:
                raise ArenaBrowserRequestError("Generate an Encounter before preparing Dodge")
            candidate = self._active
            encounter = candidate.encounter
            player = candidate.participants[0].native.being
            if not encounter.initiated or encounter.progression_mode != "transactional":
                raise ArenaBrowserRequestError("Activate the native Encounter before preparing Dodge")
            if encounter._choice_book.actor_planned_now(player.id):
                raise ArenaBrowserRequestError("The player already has a native Action accepted or resolving")
            if self._retained_defense(candidate, player, "dodge") is not None:
                raise ArenaBrowserRequestError("A native Dodge is already ready; retain it or commit it before preparing another")
            try:
                pool = MeleeDefense.dodge_strategy_pool(player, candidate.universe)
            except (TypeError, ValueError) as exc:
                raise ArenaBrowserRequestError(str(exc)) from exc
            if defense + timing != pool:
                raise ArenaBrowserRequestError(f"Allocate exactly the current {pool} Dodge strategy points between defense and timing")
            action = MeleeDefense(encounter, player.id, kind="dodge",
                                  strategy=Strategy(defense=defense, timing=timing))
            try:
                prepared = encounter.prepare_action(action)
                encounter.schedule_action(action)
            except Exception as exc:
                raise ArenaBrowserRequestError("Native Dodge preparation was refused without publishing the Choice") from exc
            self._trace.native_advance(None, None,
                f"action=player_defense kind=dodge preparation="
                f"{prepared.end_time-prepared.start_time:g}s strategy_pool={pool}")
            return self._view_unlocked()

    def _player_block_preflight(self, candidate, player, entity_id, evidence, shield_id):
        if not _has_native_transactional_action_contract(MeleeDefense):
            raise ArenaBrowserRequestError("The native MeleeDefense scheduler or resolver contract is unavailable.")
        if evidence is None or evidence.category != "being" or evidence.present_state != "present":
            raise ArenaBrowserRequestError("Select a currently perceived attacking Being first.")
        encounter = candidate.encounter
        attacker = encounter.get_being(entity_id) if type(entity_id) is str else None
        if attacker is None or attacker.id == player.id or not encounter.is_aware(player.id, attacker.id):
            raise ArenaBrowserRequestError("The selected Entity is not an aware participating attacker.")
        shields = player.shielded_with(candidate.universe)
        if type(shield_id) is not str or shield_id not in shields.values():
            raise ArenaBrowserRequestError("Block requires an actually equipped native shield.")
        ledger = object.__getattribute__(player, "__dict__").get("_arena_perception_ledger")
        strike = self._visible_incoming_strike(candidate, player, attacker, ledger)
        if strike is None:
            raise ArenaBrowserRequestError("No currently perceived, pending native strike is available to Block.")
        action = MeleeDefense(encounter, player.id, attacker.id, kind="block",
                              target_action_id=strike.id, weapon_id=shield_id)
        try:
            prepared = encounter.prepare_action(action)
        except Exception as exc:
            raise ArenaBrowserRequestError(str(exc)) from exc
        return action, prepared, strike

    def choose_block(self, payload):
        if type(payload) is not dict or set(payload) != {"handle", "shield_handle"}:
            raise ArenaBrowserRequestError("Block requires a perceived attacker and an equipped shield handle")
        with self._lock:
            if self._active is None:
                raise ArenaBrowserRequestError("Generate an Encounter before choosing Block")
            candidate = self._active
            player = candidate.participants[0].native.being
            entity_id = next((key for key, value in self._view_handles.items()
                              if value == payload["handle"]), None)
            shield_id = next((key for key, value in self._view_handles.items()
                              if value == payload["shield_handle"]), None)
            ledger = object.__getattribute__(player, "__dict__").get("_arena_perception_ledger")
            if ledger is None or ledger.observer_id != player.id:
                raise ArenaBrowserRequestError("player perception evidence is unavailable")
            evidence = None if entity_id is None else next(
                (row for row in ledger.current if row.entity_id == entity_id), None)
            action, prepared, strike = self._player_block_preflight(
                candidate, player, entity_id, evidence, shield_id)
            try:
                candidate.encounter.schedule_action(action)
            except Exception as exc:
                raise ArenaBrowserRequestError(
                    "native Block Choice was not accepted; Arena state is unchanged") from exc
            self._selected_entity_handle = payload["handle"]
            self._trace.native_advance(None, None,
                f"action=player_defense kind=block shield_size={action.get_instrument().get_weapon_size()} "
                f"impact={strike.end_time:g}s")
            return self._view_unlocked()

    def _player_yield_preflight(self, candidate, player, entity_id, evidence):
        if evidence is None or evidence.category != "being" or evidence.present_state != "present":
            raise ArenaBrowserRequestError("Select a currently perceived attacking Being first.")
        encounter = candidate.encounter
        attacker = encounter.get_being(entity_id) if type(entity_id) is str else None
        if attacker is None or attacker.id == player.id or not encounter.is_aware(player.id, attacker.id):
            raise ArenaBrowserRequestError("The selected Entity is not an aware participating attacker.")
        if self._movement_plan is None:
            raise ArenaBrowserRequestError("Choose a native destination away from the attacker before Yield.")
        start, destination, attacker_position = (
            player.get_position(), self._movement_plan.destination, attacker.get_position())
        if start is None or attacker_position is None or math.dist(destination.as_tuple(), attacker_position.as_tuple()) <= math.dist(start.as_tuple(), attacker_position.as_tuple()):
            raise ArenaBrowserRequestError("Yield requires an accepted destination that moves away from the attacker.")
        ledger = object.__getattribute__(player, "__dict__").get("_arena_perception_ledger")
        strike = self._visible_incoming_strike(candidate, player, attacker, ledger)
        if strike is None:
            raise ArenaBrowserRequestError("No currently perceived, pending native strike is available to Yield against.")
        if strike.end_time != encounter.time + 1:
            raise ArenaBrowserRequestError("Yield lasts one second and must complete at the incoming strike boundary.")
        action = MeleeDefense(encounter, player.id, attacker.id, kind="yield",
                              target_action_id=strike.id)
        try:
            prepared = encounter.prepare_action(action)
        except Exception as exc:
            raise ArenaBrowserRequestError(str(exc)) from exc
        return action, prepared, strike

    def choose_yield(self, payload):
        if type(payload) is not dict or set(payload) != {"handle"} or type(payload["handle"]) is not str:
            raise ArenaBrowserRequestError("Yield accepts exactly one currently perceived attacker handle")
        with self._lock:
            if self._active is None:
                raise ArenaBrowserRequestError("Generate an Encounter before choosing Yield")
            candidate = self._active
            player = candidate.participants[0].native.being
            entity_id = next((key for key, value in self._view_handles.items()
                              if value == payload["handle"]), None)
            ledger = object.__getattribute__(player, "__dict__").get("_arena_perception_ledger")
            if ledger is None or ledger.observer_id != player.id:
                raise ArenaBrowserRequestError("player perception evidence is unavailable")
            evidence = None if entity_id is None else next(
                (row for row in ledger.current if row.entity_id == entity_id), None)
            action, prepared, _strike = self._player_yield_preflight(
                candidate, player, entity_id, evidence)
            try:
                candidate.encounter.schedule_action(action)
            except Exception as exc:
                raise ArenaBrowserRequestError(
                    "native Yield Choice was not accepted; Arena state is unchanged") from exc
            self._selected_entity_handle = payload["handle"]
            self._trace.native_advance(None, None,
                f"action=player_defense kind=yield duration="
                f"{prepared.end_time-prepared.start_time:g}s movement=destination-away")
            return self._view_unlocked()

    def _action_catalog_unlocked(self, candidate, player, selected, supported_actions):
        from activities import PickUpAction, RunAction, SpotAction

        handle = None if selected is None else selected.get("handle")
        entity_id = (None if type(handle) is not str else
                     next((key for key, value in self._view_handles.items() if value == handle), None))
        ledger = object.__getattribute__(player, "__dict__").get("_arena_perception_ledger")
        evidence = None if entity_id is None else next(
            (row for row in ledger.current if row.entity_id == entity_id), None)
        ready_target, ready_hands, ready_reason = self._ready_weapon_target_unlocked(
            candidate, player, entity_id, evidence)
        ready_available = ready_target is not None and supported_actions.get(ReadyWeaponAction, False)
        catalog_rows = []
        for source_row in _native_action_catalog():
            name = source_row["name"]
            if name.casefold() in ("swing at being", "thrust at being"):
                motion = "swing" if name.casefold().startswith("swing") else "thrust"
                reason = "Select an aware opposing Being. Native reach and path are checked at impact."
                status = "unavailable"
                display_name = "Dagger " + motion.title()
                duration = None
                target_view = (None if selected is None else {"handle": handle,
                    "name": selected["name"], "type": selected["type"],
                    "present_state": selected["present_state"]})
                if supported_actions.get(MeleeStrike, False):
                    try:
                        _, weapon, prepared, distance, reach = self._melee_strike_preflight(
                            candidate, player, entity_id, evidence, motion)
                        status = "available"
                        duration = prepared.end_time - prepared.start_time
                        display_name = f"Dagger {motion.title()} ({duration:g} s)"
                        reason = (f"Native ready Dagger selected; {distance:.2f} m center distance, "
                                  f"{reach:.2f} m native reach. Reach and path resolve at impact.")
                    except ArenaBrowserRequestError as exc:
                        reason = str(exc)
                else:
                    reason = "The native MeleeStrike scheduler or resolver contract is unavailable."
                pending_melee = self._player_melee_action(candidate, player)
                if self._melee_action_pending(candidate, pending_melee):
                    status = "unavailable"
                    reason = "A player MeleeStrike is already resolving."
                catalog_rows.append({
                    "name": name, "group": "Being targets", "target_type": "being",
                    "required_skill": source_row["required_skill"],
                    "is_melee": source_row["is_melee"], "status": status,
                    "display_name": display_name, "reason": reason,
                    "target": target_view, "motion": motion,
                    "duration_seconds": duration,
                })
                continue
            elif name.casefold() == "grab object":
                reason = ("The legacy Grab object catalog Action is not admitted for this use. "
                          "Revision 64 defines Pick up as a separate native Action for a free ground Object.")
            elif name.casefold() == "ready weapon":
                reason = (ready_reason if supported_actions.get(ReadyWeaponAction, False)
                          else "The native Ready weapon scheduler or resolver contract is unavailable.")
                catalog_rows.append({
                    "name": name, "group": "Arena Actions",
                    "display_name": "Draw (2 s)",
                    "target_type": target_type, "required_skill": source_row["required_skill"],
                    "is_melee": source_row["is_melee"],
                    "status": "available" if ready_available else "unavailable",
                    "reason": reason,
                    "target": (None if selected is None else {"handle": handle,
                        "name": selected["name"], "type": selected["type"],
                        "present_state": selected["present_state"]}),
                    "hands": list(ready_hands),
                })
                continue
            elif name.casefold() == "ready object":
                reason = "No native transactional ready-object Action is implemented for the generated Arena."
            elif name.casefold().startswith("parry"):
                continue
            elif name.casefold() == "throw":
                reason = ("The native Throw resolver has a narrow authored parameter bracket, but the Arena "
                          "has no supported control for its load and trajectory inputs.")
            else:
                reason = ("No reviewed native generated-Arena submission and resolution contract is "
                          "connected to this catalog Action.")
            target_type = source_row["target_type"]
            group = {"being": "Being targets", "object": "Object targets",
                     "weapon": "Weapon targets", "attack": "Attack responses",
                     "none": "Other Actions"}[target_type]
            catalog_rows.append({
                "name": name, "group": group, "target_type": target_type,
                "required_skill": source_row["required_skill"],
                "is_melee": source_row["is_melee"],
                "status": "not_implemented", "reason": reason,
            })

        if supported_actions.get(RunAction):
            run_available = (self._player_action_id is None and not candidate.encounter.initiated)
            run_reason = ("The native target-free Run Choice can activate this Arena."
                          if run_available else
                          "Run is only accepted as the first player Action; this Encounter is already activated.")
            run_status = "available" if run_available else "unavailable"
        else:
            run_status = "not_implemented"
            run_reason = "The native Run scheduler or resolver contract is unavailable."
        arena_rows = [{"name": "Run", "group": "Arena Actions", "status": run_status,
                       "reason": run_reason}]

        if supported_actions.get(SpotAction):
            spot_status, spot_reason = "unavailable", _SPOT_DISABLED
        else:
            spot_status = "not_implemented"
            spot_reason = "The native Spot scheduler or resolver contract is unavailable."
        arena_rows.append({"name": "Spot", "group": "Arena Actions",
                           "status": spot_status, "reason": spot_reason})

        if supported_actions.get(PickUpAction):
            pickup_available, pickup_reason = self._pickup_status_unlocked(
                candidate, player, entity_id, evidence)
            pickup_status = "available" if pickup_available else "unavailable"
        else:
            pickup_status = "not_implemented"
            pickup_reason = "The native Pick up scheduler or resolver contract is unavailable."
        arena_rows.append({
            "name": "Pick up", "group": "Arena Actions", "status": pickup_status,
            "reason": pickup_reason,
            "target": (None if selected is None else {
                "handle": handle, "name": selected["name"], "type": selected["type"],
                "present_state": selected["present_state"],
            }),
        })
        dodge_reason = "Prepare a native two-second Dodge, then assign it to an observed strike before its outcome."
        dodge_status = "unavailable"
        dodge_target = None
        dodge_mode = "prepare"
        dodge_timing = []
        if selected is not None:
            dodge_target = {"handle": handle, "name": selected["name"],
                            "type": selected["type"],
                            "present_state": selected["present_state"]}
        if not supported_actions.get(MeleeDefense, False):
            dodge_status = "not_implemented"
            dodge_reason = "The native MeleeDefense scheduler or resolver contract is unavailable."
        else:
            retained = self._retained_defense(candidate, player, "dodge")
            pending_defense = self._latest_melee_defense(candidate, player)
            if retained is not None:
                dodge_mode = "use"
                try:
                    _, prepared, strike = self._player_dodge_preflight(
                        candidate, player, entity_id, evidence)
                    dodge_status = "available"
                    dodge_reason = (f"Native Dodge is ready. Assign it to the observed strike resolving at "
                                    f"second {strike.end_time:g}; its ordinary attack roll decides whether it succeeds.")
                except ArenaBrowserRequestError as exc:
                    dodge_reason = str(exc)
            elif self._melee_defense_pending(candidate, pending_defense):
                dodge_reason = "A native Dodge preparation or assignment is already resolving."
            elif candidate.encounter._choice_book.actor_planned_now(player.id):
                dodge_reason = "The player already has an accepted native Action."
            else:
                try:
                    pool = MeleeDefense.dodge_strategy_pool(player, candidate.universe)
                    dodge_timing = list(range(pool + 1))
                    dodge_status = "available"
                    dodge_reason = (f"Native Dodge: {pool} strategy points from Dexterity, Tumble ranks, and armor; "
                                    "allocate them between defense and timing before preparation.")
                except (TypeError, ValueError) as exc:
                    dodge_reason = str(exc)
        arena_rows.append({"name": "Dodge", "group": "Attack responses",
                           "status": dodge_status, "reason": dodge_reason,
                           "target": dodge_target if dodge_mode == "use" else None,
                           "dodge_mode": dodge_mode, "dodge_timing": dodge_timing,
                           "strategy_pool": (len(dodge_timing) - 1 if dodge_timing else None)})
        parry_status, parry_reason = "unavailable", "Parry requires an actually held weapon with advanced weapon skill."
        parry_mode = "prepare"
        parry_options = []
        parry_target = None
        if selected is not None:
            parry_target = {"handle": handle, "name": selected["name"],
                            "type": selected["type"], "present_state": selected["present_state"]}
        if not supported_actions.get(MeleeDefense, False):
            parry_status, parry_reason = "not_implemented", "The native MeleeDefense scheduler or resolver contract is unavailable."
        elif candidate.encounter._choice_book.actor_planned_now(player.id):
            parry_reason = "The player already has an accepted native Action."
        else:
            armed = player.armed_with(candidate.universe)
            ready_sources = [self._retained_defense(candidate, player, "parry", weapon_id)
                             for weapon_id in sorted(armed.values())]
            ready_sources = [source for source in ready_sources if source is not None]
            if ready_sources:
                parry_mode = "use"
                attacker = candidate.encounter.get_being(entity_id) if type(entity_id) is str else None
                ledger = object.__getattribute__(player, "__dict__").get("_arena_perception_ledger")
                strike = (None if attacker is None else
                          self._visible_incoming_strike(candidate, player, attacker, ledger))
                for source in ready_sources:
                    obj_handle = self._view_handles.get(source.instrument_id)
                    if obj_handle is None:
                        continue
                    parry_options.append({"weapon_handle": obj_handle,
                                          "motion": source.parry_motion or "swing",
                                          "name": candidate.universe.get_object_by_id(source.instrument_id).name})
                    if strike is not None and attacker is not None:
                        try:
                            probe = MeleeDefense(candidate.encounter, player.id, attacker.id,
                                kind="parry", target_action_id=strike.id,
                                prepared_defense_action_id=source.id)
                            candidate.encounter.prepare_action(probe)
                            parry_status = "available"
                            parry_reason = "Retained native Parry can be assigned before this observed strike's outcome."
                        except (TypeError, ValueError, RuntimeError) as exc:
                            parry_reason = str(exc)
            else:
                current = self._latest_melee_defense(candidate, player)
                if self._melee_defense_pending(candidate, current):
                    parry_reason = "A native defense Action is already preparing or resolving."
                else:
                    from weapon import WeaponInstance
                    for weapon_id in sorted(armed.values()):
                        weapon = candidate.universe.get_object_by_id(weapon_id)
                        if (type(weapon) is not WeaponInstance
                                or player.get_weapon_skill_level(weapon.original.obj_type) <= 1):
                            continue
                        weapon_handle = self._view_handles.get(weapon_id)
                        if weapon_handle is None:
                            continue
                        for motion, timing in (("swing", weapon.St()), ("thrust", weapon.Tt())):
                            parry_options.append({"weapon_handle": weapon_handle,
                                "motion": motion, "timing_seconds": timing,
                                "name": weapon.name})
                    if parry_options:
                        parry_status = "available"
                        parry_reason = "Prepare Parry target-free with an actually held, advanced-skill weapon; choose its swing or thrust timing."
        arena_rows.append({"name": "Parry", "group": "Attack responses",
                           "status": parry_status, "reason": parry_reason,
                           "target": parry_target if parry_mode == "use" else None,
                           "parry_mode": parry_mode, "parry_options": parry_options})
        shield_options = []
        block_status, block_reason = "unavailable", "No native shield is equipped in a functioning arm."
        shields = player.shielded_with(candidate.universe)
        for _slot, shield_id in sorted(shields.items()):
            shield_handle = self._view_handles.get(shield_id)
            shield = candidate.universe.get_object_by_id(shield_id)
            if shield_handle is not None and shield is not None:
                shield_options.append({"handle": shield_handle, "name": shield.name,
                                       "size": shield.get_weapon_size()})
                if entity_id is not None and evidence is not None:
                    try:
                        self._player_block_preflight(candidate, player, entity_id,
                                                     evidence, shield_id)
                        block_status = "available"
                        block_reason = (f"Native Block with {shield.name}; its {shield.get_weapon_size()}-second "
                                        "shield-size timing completes at the observed strike boundary.")
                        break
                    except ArenaBrowserRequestError as exc:
                        block_reason = str(exc)
        arena_rows.append({"name": "Block", "group": "Attack responses",
                           "status": block_status, "reason": block_reason,
                           "target": dodge_target, "shields": shield_options})
        yield_status, yield_reason = "unavailable", "Choose an accepted destination away from the attacker first."
        if supported_actions.get(MeleeDefense, False):
            try:
                self._player_yield_preflight(candidate, player, entity_id, evidence)
                yield_status = "available"
                yield_reason = "Native Yield: one second of committed movement away from the attacker, completing with its currently perceived strike."
            except ArenaBrowserRequestError as exc:
                yield_reason = str(exc)
        arena_rows.append({"name": "Yield", "group": "Attack responses",
                           "status": yield_status, "reason": yield_reason,
                           "target": dodge_target})
        return {"catalog_source": "native Action catalog", "entries": catalog_rows + arena_rows}

    def _player_character_sheet_unlocked(self, candidate, participant, position, cell,
                                         movement_plan):
        """Build an allowlisted, live projection from the player's native state.

        This intentionally does not read NPC Generator source records, the
        opponent's Being state, or the historical perception ledger for the
        inventory. Native values are read under the Universe's coordinated
        access boundary while the session lock is already held.
        """
        from atomic_publication import coordinated_access
        from being import BeingInstance

        being = participant.native.being
        if type(being) is not BeingInstance:
            raise ArenaBrowserRequestError("player character sheet requires the native player Being")

        with coordinated_access(candidate.universe):
            current = being.current
            position = being.get_position()
            if position is None:
                raise ArenaBrowserRequestError("native player position is unavailable")
            address = candidate.arena_map.layout.cell_at_position(position)
            cell = None if address is None else {"column": address.column, "row": address.row}
            abilities = current.get_abilities()
            if (type(abilities) is not dict or not abilities
                    or any(type(key) is not str or type(value) not in (int, float)
                           or not math.isfinite(value) for key, value in abilities.items())):
                raise ArenaBrowserRequestError("native player abilities cannot be projected safely")
            initial_profile = object.__getattribute__(being, "__dict__").get(
                "_arena_initial_profile")
            if type(initial_profile) is not dict or initial_profile.get("schema_version") != 1:
                raise ArenaBrowserRequestError("native initial Age/Class/skill provenance is unavailable")
            initial_skills = initial_profile.get("initial_skills")
            if type(initial_skills) is not dict:
                raise ArenaBrowserRequestError("native initial skill provenance is malformed")
            skill_experience = being.skill_experience
            if type(skill_experience) is not dict:
                raise ArenaBrowserRequestError("native skill-practice state cannot be projected safely")
            ordinary_explicit = initial_skills.get("ordinary")
            weapons_explicit = initial_skills.get("weapons")
            if type(ordinary_explicit) is not tuple or type(weapons_explicit) is not tuple:
                raise ArenaBrowserRequestError("explicit initial skill ranks are malformed")
            ordinary_map = dict(ordinary_explicit)
            weapon_map = dict(weapons_explicit)
            current_ordinary = current.skills.skills
            current_weapons = current.skills.weapon_skills
            if type(current_ordinary) is not dict or type(current_weapons) is not dict:
                raise ArenaBrowserRequestError("native effective skill ranks are malformed")
            derived_weapons = {name: rank for name, rank in current_weapons.items()
                               if name not in weapon_map and rank > 0}
            practice_names = (set(ordinary_map) | set(weapon_map)
                              | set(current_ordinary) | set(current_weapons)
                              | set(skill_experience))
            for name, practice in skill_experience.items():
                if type(name) is not str or not name or type(practice) is not int or practice < 0:
                    raise ArenaBrowserRequestError("native skill-practice state cannot be projected safely")

            def rank_rows(rank_map, *, derived=False):
                rows = []
                for name, rank in sorted(rank_map.items()):
                    if (type(name) is not str or not name
                            or type(rank) not in (int, float) or not math.isfinite(rank) or rank < 0):
                        raise ArenaBrowserRequestError("native skill ranks cannot be projected safely")
                    rows.append({"name": name, "rank": rank,
                                 "practice_experience": skill_experience.get(name, 0),
                                 "individually_acquired": not derived})
                return rows

            practice_rows = []
            for name in sorted(practice_names):
                practice = skill_experience.get(name, 0)
                if type(practice) is not int or practice < 0:
                    raise ArenaBrowserRequestError("native skill-practice state cannot be projected safely")
                practice_rows.append({"name": name, "experience": practice})
            skill_groups = [
                {"kind": "initial_ordinary", "skills": rank_rows(ordinary_map)},
                {"kind": "initial_weapon", "skills": rank_rows(weapon_map)},
                {"kind": "effective_category_weapon", "skills": rank_rows(derived_weapons, derived=True)},
                {"kind": "earned_practice", "skills": practice_rows},
            ]

            experience = being.get_experience()
            hit_points = being.get_hit_points()
            stature_inches, body_weight_pounds = current.length, current.weight
            if (type(current.obj_type) is not str or not current.obj_type.strip()
                    or current.race is not None and type(current.race) is not str
                    or type(experience) not in (int, float) or not math.isfinite(experience)
                    or experience < 0 or type(hit_points) not in (int, float)
                    or not math.isfinite(hit_points)
                    or type(stature_inches) not in (int, float) or not math.isfinite(stature_inches)
                    or stature_inches <= 0
                    or type(body_weight_pounds) not in (int, float)
                    or not math.isfinite(body_weight_pounds) or body_weight_pounds <= 0):
                raise ArenaBrowserRequestError("native player measurements or condition cannot be projected safely")
            states = current.get_states()
            if type(states) is not dict or any(type(key) is not str or type(value) is not bool
                                               for key, value in states.items()):
                raise ArenaBrowserRequestError("native player condition states cannot be projected safely")
            fatigue = being.get_physical_fatigue()
            if (not all(type(value) in (int, float) and math.isfinite(value)
                        and 0 <= value <= 1 for value in (fatigue.q, fatigue.b))
                    or type(being.get_fatigue_level()) is not int
                    or not 0 <= being.get_fatigue_level() <= 5):
                raise ArenaBrowserRequestError("native player fatigue cannot be projected safely")

            inventory = self._native_inventory_projection(candidate, being)
            inventory["carried_weight_pounds"] = truncate_measurement(
                inventory["carried_weight_pounds"])
            anatomy = self._native_hand_projection(being, inventory)
            movement = {
                "position_meters": {"x": position.x, "y": position.y, "z": position.z},
                "cell": cell,
                "hex_facing": being.hex_facing,
                "posture": being.posture,
                "selected_plan": None,
                "speed": None,
                "speed_status": "Native rate is evaluated at each committed movement boundary; no ETA is projected.",
            }
            if movement_plan is not None:
                movement["selected_plan"] = {
                    "rate": movement_plan["rate"],
                    "facing_policy": movement_plan["facing_policy"],
                    "destination_cell": dict(movement_plan["destination_cell"]),
                    "remaining_distance_meters": movement_plan["remaining_distance_meters"],
                }

            class_allocations = [dict(row) for row in initial_profile["class_allocations"]]
            try:
                npcgen_specification = json.loads(participant.native.source_record_bytes.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ArenaBrowserRequestError("complete NPC Generator source specification is malformed") from exc
            return {
                "identity": {
                    "display_name": self._player_name,
                    "native_type": current.obj_type,
                    "race": current.race,
                    "age": initial_profile["age_years"],
                    "age_category": initial_profile["age_category"],
                    "age_status": None,
                    "class_levels": class_allocations,
                    "class_levels_status": None,
                    "stature_inches": float(stature_inches),
                    "body_weight_pounds": float(body_weight_pounds),
                },
                "experience": {
                    "total": experience,
                    "initial_total": initial_profile["initial_total_experience"],
                    "class_allocation": class_allocations,
                    "class_allocation_status": None,
                },
                "abilities": [{"name": name, "score": score}
                              for name, score in sorted(abilities.items())],
                "skills": skill_groups,
                "condition": {
                    "hit_points_current": hit_points,
                    "hit_points_maximum": None,
                    "hit_points_maximum_status": "A maximum HP value is not modeled by the native Arena import.",
                    "legacy_fatigue_level": being.get_fatigue_level(),
                    "physical_fatigue_reserves": {"q": fatigue.q, "b": fatigue.b,
                                                  "profile_status": "resolved" if being.physiology_id else "unresolved"},
                    "posture": being.posture,
                    "conditions": self._condition_labels(states),
                },
                "anatomy": anatomy,
                "movement": movement,
                "inventory": inventory,
                "npcgen_specification": npcgen_specification,
            }

    @staticmethod
    def _condition_labels(states):
        labels = {
            "prone": "Prone", "unconscious": "Unconscious", "helpless": "Helpless",
            "sleeping": "Sleeping", "stunned": "Stunned", "paralyzed": "Paralyzed",
            "blinded": "Blinded", "deafened": "Deafened", "grappled": "Grappled",
            "restrained": "Restrained", "exhausted": "Exhausted", "dead": "Dead",
        }
        active = []
        for name, value in sorted(states.items()):
            if value:
                label = labels.get(name.casefold(), name.replace("_", " ").strip().capitalize())
                active.append(label)
        return active

    def _observer_being_sheet_unlocked(self, candidate, evidence):
        """Same character-sheet schema, populated only from player evidence."""
        unknown = "Unknown from player-authorized evidence."
        position = evidence.get("position_meters")
        target_id = next((entity_id for entity_id, handle in self._view_handles.items()
                          if handle == evidence.get("handle")), None)
        from arena_perception import ArenaPerceptionLedger
        player = candidate.participants[0].native.being
        ledger = object.__getattribute__(player, "__dict__").get("_arena_perception_ledger")
        if type(ledger) is not ArenaPerceptionLedger or ledger.observer_id != player.id:
            raise ArenaBrowserRequestError("player equipment observation evidence is unavailable")
        visible_inventory = []
        for item_evidence in ledger.current:
            if (item_evidence.category != "object" or item_evidence.owner_id != target_id):
                continue
            handle = self._view_handles.get(item_evidence.entity_id)
            if handle is None:
                raise ArenaBrowserRequestError("visible equipment Object has no player-authorized handle")
            visible_inventory.append({
                "handle": handle,
                "name": self._display_names.get(item_evidence.entity_id, item_evidence.name),
                "type": item_evidence.type_key,
                "status": ("carried; equipment state not represented"
                           if item_evidence.equipment_status == "carried"
                           else item_evidence.equipment_status),
            })
        return {
            "identity": {"display_name": evidence["name"],
                "native_type": evidence["type"], "race": None,
                "age": None, "age_category": None, "age_status": unknown,
                "class_levels": None, "class_levels_status": unknown,
                "stature_inches": None, "body_weight_pounds": None},
            "experience": {"total": None, "initial_total": None,
                "class_allocation": None, "class_allocation_status": unknown},
            "abilities": [{"name": name, "score": None} for name in (
                "Strength", "Constitution", "Dexterity", "Fitness",
                "Intelligence", "Wisdom", "Charisma")],
            "skills": [{"kind": kind, "skills": [], "status": "unknown"} for kind in (
                "initial_ordinary", "initial_weapon", "effective_category_weapon", "earned_practice")],
            "condition": {"hit_points_current": None, "hit_points_maximum": None,
                "hit_points_maximum_status": unknown, "legacy_fatigue_level": None,
                "physical_fatigue_reserves": None, "posture": None,
                "conditions": None, "status": unknown},
            "anatomy": {"status": "unknown", "hands": []},
            "movement": {"position_meters": position, "cell": evidence.get("cell"),
                "hex_facing": None, "posture": None, "selected_plan": None,
                "speed": None, "speed_status": unknown},
            "inventory": {"status": "available", "items": visible_inventory,
                "carried_weight_pounds": None,
                "encumbrance_status": "Weight and unobserved custody details are unavailable from player evidence."},
        }

    @staticmethod
    def _native_hand_projection(being, inventory):
        """Project represented native hand locations without exposing IDs."""
        body_parts = being.current.body_parts
        if type(body_parts) is not dict or any(
                type(key) is not str or not key
                or value is not None and type(value) is not str
                for key, value in body_parts.items()):
            return {"status": "unavailable", "hands": []}
        represented = [name for name in ("left hand", "right hand") if name in body_parts]
        if not represented:
            return {"status": "unrepresented", "hands": []}
        if inventory.get("status") != "available":
            if any(body_parts[name] is not None for name in represented):
                return {"status": "unavailable", "hands": []}
            return {"status": "available", "hands": [
                {"name": name, "occupancy": "empty"} for name in represented]}

        hands = []
        for name in represented:
            object_id = body_parts[name]
            if object_id is None:
                hands.append({"name": name, "occupancy": "empty"})
                continue
            item = next((row for row in inventory["items"]
                         if row.get("body_part") == name), None)
            if item is None:
                return {"status": "unavailable", "hands": []}
            hands.append({"name": name, "occupancy": "occupied",
                          "object": {"handle": item["handle"], "name": item["name"],
                                     "type": item["type"]}})
        return {"status": "available", "hands": hands}

    def _native_inventory_projection(self, candidate, being):
        """Resolve every native ownership/equipment reference or expose failure."""
        from armor import ArmorInstance
        from being import BeingInstance
        from object import ObjectInstance
        from weapon import WeaponInstance

        registry = candidate.universe.get_object_registry().object_instances
        inventory = {"status": "available", "items": [], "carried_weight_pounds": 0.0,
                     "encumbrance_status": "No standalone native encumbrance category is stored."}
        try:
            if type(registry) is not dict:
                raise ValueError("native Object registry is unavailable")
            if (type(being.possessions) is not list or type(being.weapons) is not list
                    or type(being.current.body_parts) is not dict):
                raise ValueError("native custody references are malformed")
            if any(type(key) is not str or not key for key in being.current.body_parts):
                raise ValueError("native body-part references are malformed")
            possession_ids = list(being.possessions)
            weapon_ids = list(being.weapons)
            body_refs = [(slot, object_id) for slot, object_id in being.current.body_parts.items()
                         if object_id is not None]
            armor_id = being.current.armor_id
            references = possession_ids + weapon_ids + [object_id for _, object_id in body_refs]
            if armor_id is not None:
                references.append(armor_id)
            if any(type(key) is not str or not key for key in references):
                raise ValueError("native custody references are malformed")
            if len(possession_ids) != len(set(possession_ids)) or len(weapon_ids) != len(set(weapon_ids)):
                raise ValueError("native inventory contains duplicate custody references")

            body_slots = {}
            for slot, object_id in body_refs:
                if object_id in body_slots:
                    raise ValueError("one native Object is assigned to multiple body parts")
                body_slots[object_id] = slot
            reference_ids = list(dict.fromkeys(references))
            root_order = []
            for object_id in reference_ids:
                item = registry.get(object_id)
                if item is not None and getattr(item, "parent_container_id", None) in (None, being.id):
                    root_order.append(object_id)
                elif object_id in weapon_ids or object_id in body_slots or object_id == armor_id:
                    raise ValueError("equipped Object has conflicting container custody")
            root_order.extend(sorted(key for key, item in registry.items()
                                     if getattr(item, "parent_container_id", None) == being.id
                                     and key not in root_order))

            shield_types = set(candidate.universe.library.weapon_dictionary
                               .get_objects_in_category("Shields"))
            rows = []
            visited = set()
            active = set()
            total_weight = 0.0

            def visit(object_id, expected_parent_id=None, parent_name=None):
                nonlocal total_weight
                if object_id in active:
                    raise ValueError("native inventory contains a custody cycle")
                if object_id in visited:
                    return
                item = registry.get(object_id)
                if (not isinstance(item, ObjectInstance) or isinstance(item, BeingInstance)
                        or item.id != object_id):
                    raise ValueError("native inventory references a missing or unsupported Object")
                parent_id = item.parent_container_id
                if expected_parent_id is None:
                    if object_id not in root_order:
                        raise ValueError("native inventory reference has no directly owned root")
                    if parent_id not in (None, being.id):
                        raise ValueError("native inventory Object has conflicting custody")
                    if item.get_position() is not None:
                        raise ValueError("native inventory Object is still spatially placed")
                elif parent_id != expected_parent_id or item.get_position() is not None:
                    raise ValueError("nested native Object has conflicting custody or spatial state")
                current = item.current
                type_key, native_name, weight = current.obj_type, item.name, current.weight
                if (type(type_key) is not str or not type_key.strip()
                        or native_name is not None and type(native_name) is not str
                        or type(weight) not in (int, float) or not math.isfinite(weight) or weight < 0):
                    raise ValueError("native inventory Object has an invalid name, type, or pound weight")
                if type(item) is ArmorInstance:
                    kind = "armor"
                elif type(item) is WeaponInstance:
                    kind = "shield" if type_key in shield_types else "weapon"
                elif type(item) is ObjectInstance:
                    kind = "object"
                else:
                    raise ValueError("native inventory Object subtype is unsupported")
                if object_id == armor_id:
                    if type(item) is not ArmorInstance:
                        raise ValueError("native armor slot does not reference an Armor Object")
                    status = "equipped armor"
                elif object_id in body_slots:
                    status = (f"held shield at {body_slots[object_id]} (native shield reference)"
                              if kind == "shield" else f"readied in {body_slots[object_id]}")
                elif parent_name is not None:
                    status = f"contained in {parent_name}"
                else:
                    status = ("carried; not readied" if kind in ("weapon", "shield")
                              else "carried")
                display_name = self._display_names.get(object_id, native_name or type_key)
                handle = self._view_handles.get(object_id)
                if handle is None:
                    raise ValueError("native inventory Object has no observer-authorized handle")
                row = {"handle": handle, "name": display_name, "type": type_key,
                       "kind": kind, "weight_pounds": float(weight), "status": status}
                if object_id in body_slots:
                    row["body_part"] = body_slots[object_id]
                rows.append(row)
                total_weight += float(weight)
                if not math.isfinite(total_weight):
                    raise ValueError("native carried weight is not finite")
                visited.add(object_id)
                active.add(object_id)
                for child_id, child in sorted(registry.items()):
                    if getattr(child, "parent_container_id", None) == object_id:
                        visit(child_id, object_id, display_name)
                active.remove(object_id)

            for object_id in root_order:
                visit(object_id)
            if not set(reference_ids).issubset(visited):
                raise ValueError("native inventory reference is outside player custody")
            inventory["items"] = rows
            inventory["carried_weight_pounds"] = total_weight
            return inventory
        except (TypeError, ValueError, AttributeError, OverflowError):
            return {"status": "unavailable", "items": [], "carried_weight_pounds": None,
                    "encumbrance_status": "Unavailable: native custody, Object identity, type, or weight validation failed."}

    def public_view(self):
        """Return an allowlisted player-facing projection, never Reality/source data."""
        with self._lock:
            return self._view_unlocked()

    @staticmethod
    @lru_cache(maxsize=1)
    def _profile_validation_library():
        from library import Library
        return Library(config_dir=str(Path(__file__).resolve().parent / "config"))

    def ground_profile_catalog(self):
        from arena_loadout_profiles import preview
        library = self._profile_validation_library()
        with self._lock:
            rows = [{"profile_id": "none", "title": "No ground Objects",
                     "count_per_encounter": 0, "type_counts": {}}]
            for profile in self._bundled_ground_profiles.values():
                summary = preview(profile, library)
                rows.append({**summary, "profile_id": profile["profile_id"]})
            for profile_id, profile in self._uploaded_ground_profiles.items():
                summary = preview(profile, library)
                rows.append({**summary, "profile_id": profile_id})
            if (self._ground_loadout_profile is not None
                    and self._selected_ground_profile_id not in {row["profile_id"] for row in rows}):
                summary = preview(self._ground_loadout_profile, library)
                rows.append({**summary, "profile_id": self._selected_ground_profile_id,
                             "title": "Server supplied: " + summary["title"]})
            return {"profiles": rows, "selected_profile_id": self._selected_ground_profile_id}

    def select_ground_profile(self, payload):
        if type(payload) is not dict or set(payload) != {"profile_id"}:
            raise ArenaBrowserRequestError("profile selection requires exactly profile_id")
        profile_id = payload["profile_id"]
        if type(profile_id) is not str:
            raise ArenaBrowserRequestError("profile_id must be text")
        with self._lock:
            if self._active is not None:
                raise ArenaBrowserRequestError("start a New Encounter before changing its ground profile")
            if profile_id == "none":
                self._selected_ground_profile_id = None
                self._ground_loadout_profile = None
                self._ground_item_descriptions = None
            else:
                profile = (self._bundled_ground_profiles.get(profile_id)
                           or self._uploaded_ground_profiles.get(profile_id))
                if (profile is None and type(self._ground_loadout_profile) is dict
                        and profile_id == self._ground_loadout_profile.get("profile_id")):
                    profile = self._ground_loadout_profile
                if profile is None:
                    raise ArenaBrowserRequestError("selected ground profile is unavailable")
                from arena_loadout_profiles import validate_profile
                try:
                    self._ground_loadout_profile = validate_profile(
                        profile, self._profile_validation_library())
                except ValueError as exc:
                    raise ArenaBrowserRequestError(f"ground profile was refused: {exc}") from exc
                self._ground_item_descriptions = None
                self._selected_ground_profile_id = profile_id
            return self.ground_profile_catalog()

    def upload_ground_profile(self, raw):
        from arena_loadout_profiles import parse_upload, preview
        try:
            profile = parse_upload(raw, self._profile_validation_library())
            digest = hashlib.sha256(raw).hexdigest()[:16]
            profile_id = "uploaded:" + digest
            with self._lock:
                if self._active is not None:
                    raise ArenaBrowserRequestError("start a New Encounter before uploading a profile")
                self._uploaded_ground_profiles[profile_id] = profile
                self._selected_ground_profile_id = profile_id
                self._ground_loadout_profile = profile
                self._ground_item_descriptions = None
                return {"selected_profile_id": profile_id,
                        "preview": {**preview(profile, self._profile_validation_library()),
                                    "profile_id": profile_id},
                        **self.ground_profile_catalog()}
        except ValueError as exc:
            raise ArenaBrowserRequestError(str(exc)) from exc

    def generate(self, payload):
        expected = {"starting_experience", "width_cells", "height_cells"}
        allowed_keys = expected | {"ground_equipment", "equipment_mode", "opponent_strategy"}
        if (type(payload) is not dict or not expected <= set(payload)
                or set(payload) - allowed_keys):
            raise ArenaBrowserRequestError("Generate requires XP, dimensions, and supported Arena options")
        opponent_strategy = payload.get("opponent_strategy", "none")
        if opponent_strategy not in ("none", "attack_only", "defense_only"):
            raise ArenaBrowserRequestError("opponent_strategy must be none, attack_only, or defense_only")
        starting_experience = _parse_decimal(payload, "starting_experience", 0)
        width_cells = _parse_decimal(payload, "width_cells", 5)
        height_cells = _parse_decimal(payload, "height_cells", 5)
        equipment_choice = payload.get("ground_equipment")
        if equipment_choice not in (None, "starter", "none"):
            raise ArenaBrowserRequestError("ground_equipment must be starter or none")
        loadout_profile = self._ground_loadout_profile
        item_descriptions = self._ground_item_descriptions
        if equipment_choice == "starter":
            if loadout_profile is None:
                raise ArenaBrowserRequestError("the checked-in starter equipment profile is unavailable")
            item_descriptions = None
        elif equipment_choice == "none":
            loadout_profile = None
            item_descriptions = None
        equipment_mode = payload.get("equipment_mode", self._default_equipment_mode)
        if equipment_mode not in ("equipped", "unequipped"):
            raise ArenaBrowserRequestError("equipment_mode must be equipped or unequipped")
        if opponent_strategy == "attack_only" and equipment_mode != "equipped":
            raise ArenaBrowserRequestError(
                "Attack only requires the Arena's native equipped Being kit; choose equipped protagonists.")

        # Serialize generation with all session edits/reads. The prior candidate
        # stays active until a complete new candidate and native RNG owner exist.
        with self._lock:
            root_seed = self._root_seed_factory()
            if type(root_seed) is not int or root_seed < 0:
                raise ArenaBrowserRequestError("host root seed source must return a nonnegative integer")
            try:
                candidate = initialize_two_being_arena(
                    starting_experience, width_cells, height_cells, root_seed,
                    ground_item_descriptions=item_descriptions,
                    ground_loadout_profile=loadout_profile,
                    equipment_mode=equipment_mode)
                self._validate_initial_equipment_provenance(candidate)
                if self._authored_draw_scenario is not None:
                    from arena_authored_draw_scenario import author_scenario
                    author_scenario(candidate, self._authored_draw_scenario)
                encounter = candidate.encounter
                encounter.set_name("Encounter")
                candidate.participants[0].native.being.set_name(
                    candidate.participants[0].native.being.name or "Player")
                from arena_perception import refresh_candidate_names
                refresh_candidate_names(encounter)
                # Keep the Encounter legacy until real Arena activation; the
                # session cursor is captured explicitly for a time-zero save.
                rng_cursor = RNGCursor(random.Random(candidate.root_seed).getstate())
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
            self._rng_cursor = rng_cursor
            self._player_action_id = None
            self._player_action_outcome = None
            self._pickup_action_id = None
            self._pickup_action_outcome = None
            self._ready_weapon_action_id = None
            self._ready_weapon_action_outcome = None
            self._ready_weapon_end_time = None
            self._opponent_strategy = opponent_strategy
            self._opponent_attack_refusal = "strategy_disabled" if opponent_strategy == "none" else "not_yet_activated"
            self._movement_plan = None
            self._movement_sequence = 0
            self._movement_outcome = None
            self._view_handles = {}
            self._selected_entity_handle = None
            self._display_names = {}
            opponent = candidate.participants[1].native.being
            if opponent.name == self._player_name:
                # NPC Generator can give both independently generated Beings
                # the same display name. Preserve both native names and
                # identities while making map and popup selection unambiguous.
                self._display_names[opponent.id] = f"{opponent.name} (Arena)"
            return self._view_unlocked()

    def new_encounter(self, payload):
        if type(payload) is not dict or payload:
            raise ArenaBrowserRequestError("New Encounter accepts an empty request")
        with self._lock:
            self._active = None
            self._encounter_name = self._player_name = None
            self._rng_cursor = None
            self._opponent_strategy = "none"
            self._opponent_attack_refusal = "strategy_disabled"
            self._player_action_id = self._player_action_outcome = None
            self._pickup_action_id = self._pickup_action_outcome = None
            self._ready_weapon_action_id = self._ready_weapon_action_outcome = None
            self._ready_weapon_end_time = None
            self._movement_plan = None
            self._movement_sequence = 0
            self._movement_outcome = None
            self._display_names = {}
            self._view_handles = {}
            self._selected_entity_handle = None
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
            from measured_values import truncate_position
            destination = truncate_position(destination)
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
                raise ArenaBrowserRequestError("A native Pick up Action is already resolving.")
            entity_id = next((key for key, value in self._view_handles.items() if value == handle), None)
            player = self._active.participants[0].native.being
            ledger = object.__getattribute__(player, "__dict__").get("_arena_perception_ledger")
            if (type(ledger) is not ArenaPerceptionLedger
                    or ledger.observer_id != player.id):
                raise ArenaBrowserRequestError("player perception evidence is unavailable")
            evidence = None if entity_id is None else next(
                (row for row in ledger.current if row.entity_id == entity_id), None)
            obj = self._pickup_target_unlocked(self._active, player, entity_id, evidence)
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

    def choose_ready_weapon(self, payload):
        from activities import ReadyWeaponAction
        from arena_perception import ArenaPerceptionLedger
        if type(payload) is not dict or set(payload) != {"handle", "hand"}:
            raise ArenaBrowserRequestError("Ready weapon requires a visible Object handle and selected hand")
        handle, hand = payload["handle"], payload["hand"]
        with self._lock:
            if self._active is None or type(handle) is not str or type(hand) is not str:
                raise ArenaBrowserRequestError("Ready weapon target or hand is unavailable")
            if not _has_native_transactional_action_contract(ReadyWeaponAction):
                raise ArenaBrowserRequestError("The native Ready weapon Choice contract is unavailable")
            if self._ready_weapon_action_id is not None and self._ready_weapon_action_outcome is None:
                raise ArenaBrowserRequestError("A native Ready weapon Action is already resolving.")
            entity_id = next((key for key, value in self._view_handles.items() if value == handle), None)
            player = self._active.participants[0].native.being
            ledger = object.__getattribute__(player, "__dict__").get("_arena_perception_ledger")
            if type(ledger) is not ArenaPerceptionLedger or ledger.observer_id != player.id:
                raise ArenaBrowserRequestError("player perception evidence is unavailable")
            evidence = None if entity_id is None else next(
                (row for row in ledger.current if row.entity_id == entity_id), None)
            obj, hands, reason = self._ready_weapon_target_unlocked(
                self._active, player, entity_id, evidence)
            if obj is None:
                raise ArenaBrowserRequestError(reason)
            if hand not in hands:
                raise ArenaBrowserRequestError("Choose one of the currently free native hands shown by the Action selector.")
            action = ReadyWeaponAction(self._active.encounter, player.id, entity_id,
                hand, self._active.encounter.time)
            try:
                if not self._active.encounter.initiated:
                    self._active.encounter.activate_arena_for_player_action(
                        player.id, action, rng_owner=self._rng_cursor)
                else:
                    self._active.encounter.schedule_action(action)
            except Exception as exc:
                raise ArenaBrowserRequestError(
                    "native Ready weapon Choice was not accepted; Arena state is unchanged") from exc
            self._ready_weapon_action_id = action.id
            self._ready_weapon_action_outcome = None
            self._ready_weapon_end_time = action.end_time
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
            melee_action = self._player_melee_action(candidate, player)
            melee_pending = self._melee_action_pending(candidate, melee_action)
            player_defense = self._latest_melee_defense(candidate, player)
            player_defense_view = self._defense_action_view(candidate, player)
            player_defense_pending = (self._melee_defense_pending(candidate, player_defense)
                or (player_defense_view is not None and player_defense_view["status"]
                    in ("accepted", "preparing", "committed")))
            opponent = candidate.participants[1].native.being
            opponent_melee_pending = self._opponent_melee_pending(candidate, opponent)
            opponent_decision = self._opponent_decision(candidate)
            opponent_can_act = opponent_decision["kind"] in ("attack", "move", "defend", "prepare")
            self._opponent_attack_refusal = opponent_decision["reason"]
            if (self._player_action_id is None and self._pickup_action_id is None
                    and self._ready_weapon_action_id is None and not melee_pending
                    and not player_defense_pending
                    and not opponent_melee_pending and not opponent_can_act
                    and self._movement_plan is None):
                self._trace_advance_state(candidate, trace_request_id, trace_client_sequence,
                                          before_time, before_position, before_cell, None,
                                          "refused", reason="no_movement_plan")
                raise ArenaBrowserRequestError("choose a destination or an explicit Run Choice before advancing")
            if (self._movement_plan is None and self._player_action_id is not None
                    and self._player_action_outcome is not None
                    and not (self._ready_weapon_action_id is not None
                             and self._ready_weapon_action_outcome is None)
                    and not melee_pending and not player_defense_pending
                    and not opponent_melee_pending and not opponent_can_act):
                self._trace_advance_state(candidate, trace_request_id, trace_client_sequence,
                                          before_time, before_position, before_cell, None,
                                          "refused", reason="run_choice_resolved")
                raise ArenaBrowserRequestError("the accepted Run Choice has already resolved")
            if (self._movement_plan is None and self._pickup_action_id is not None
                    and self._pickup_action_outcome is not None
                    and not (self._ready_weapon_action_id is not None
                             and self._ready_weapon_action_outcome is None)
                    and not melee_pending and not player_defense_pending
                    and not opponent_melee_pending and not opponent_can_act):
                raise ArenaBrowserRequestError("the accepted Pick up Choice has already resolved")
            if (self._movement_plan is None and self._ready_weapon_action_id is not None
                    and self._ready_weapon_action_outcome is not None and not melee_pending
                    and not melee_pending and not player_defense_pending
                    and not opponent_melee_pending and not opponent_can_act):
                raise ArenaBrowserRequestError("the accepted Ready weapon Choice has already resolved")
            try:
                if opponent_decision["kind"] == "attack":
                    self._schedule_opponent_attack(candidate)
                elif opponent_decision["kind"] in ("defend", "prepare"):
                    self._schedule_opponent_defense(candidate, opponent_decision)
                elif opponent_decision["kind"] == "move":
                    self._trace.native_advance(
                        trace_request_id, trace_client_sequence,
                        f"opponent_decision=approach rate=sprint facing_policy=turn boundary={candidate.encounter.last_processed_boundary + 1}")
                next_boundary = candidate.encounter.last_processed_boundary + 1
                movement_intents = []
                movement_conditions = {}
                plan = self._movement_plan
                if plan is not None:
                    player_id = candidate.participants[0].native.being.id
                    movement_intents.append(MovementIntent(
                        player_id, plan.destination, plan.rate,
                        f"{plan.decision_id}:boundary:{next_boundary}", next_boundary,
                        facing_policy=plan.facing_policy))
                    movement_conditions[player_id] = self._movement_conditions(
                        candidate, player_id)
                if opponent_decision["kind"] == "move":
                    opponent_id = candidate.participants[1].native.being.id
                    movement_intents.append(MovementIntent(
                        opponent_id, opponent_decision["destination"], "sprint",
                        f"{candidate.encounter.id}/arena-opponent-approach/boundary:{next_boundary}",
                        next_boundary, facing_policy="turn"))
                    movement_conditions[opponent_id] = self._movement_conditions(
                        candidate, opponent_id)
                if movement_intents:
                    candidate.encounter.step(1, movement_intents=tuple(movement_intents),
                                             movement_conditions=movement_conditions)
                elif plan is not None:
                    candidate.encounter.step(1)
                else:
                    candidate.encounter.step(1)
                if plan is not None:
                    if plan is self._movement_plan:
                        position = candidate.participants[0].native.being.get_position()
                        if position == plan.destination:
                            self._movement_plan = None
                            self._movement_outcome = "arrived"
                        else:
                            self._movement_outcome = "progressed"
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
                if (self._ready_weapon_action_id is not None
                        and self._ready_weapon_action_outcome is None):
                    ready_event = candidate.universe.get_event_by_id(self._ready_weapon_action_id)
                    if (ready_event is not None
                            and candidate.encounter.time >= ready_event.end_time):
                        result = candidate.encounter.inspect_committed(
                            int(candidate.encounter.time)).action(self._ready_weapon_action_id)
                        self._ready_weapon_action_outcome = result.facts.outcome
                        self._trace.native_advance(trace_request_id, trace_client_sequence,
                            f"action=ready_weapon outcome={self._ready_weapon_action_outcome}")
            except Exception as exc:
                after_time = candidate.encounter.time
                after_position = player.get_position()
                rolled_back = (after_time == before_time and after_position == before_position)
                movement_refusal = _safe_movement_refusal(exc)
                self._trace_advance_state(
                    candidate, trace_request_id, trace_client_sequence,
                    before_time, before_position, before_cell, accepted_plan,
                    "rolled_back" if rolled_back else "failed_after_state_change",
                    reason=(movement_refusal["category"] if movement_refusal
                            else type(exc).__name__))
                if movement_refusal is not None:
                    raise ArenaBrowserRequestError(
                        movement_refusal["message"],
                        movement_refusal=movement_refusal) from exc
                raise ArenaBrowserRequestError(
                    "native one-second advancement failed; committed Arena state is unchanged") from exc
            self._trace_advance_state(candidate, trace_request_id, trace_client_sequence,
                                      before_time, before_position, before_cell, accepted_plan,
                                      "committed")
            return self._view_unlocked()

    @staticmethod
    def _movement_conditions(candidate, actor_id=None):
        from activities import RunAction
        from melee_combat import MeleeStrike
        from movement_intent import MovementIntentRefusal
        player_id = candidate.participants[0].native.being.id
        actor_id = player_id if actor_id is None else actor_id
        demanding = False
        for action_id in candidate.encounter.pending_action_list:
            action = candidate.universe.event_history.get(action_id)
            if action is None or getattr(action, "actor_id", None) != actor_id:
                continue
            if type(action) is MeleeStrike:
                demanding = True
            elif type(action) is RunAction:
                continue
            else:
                raise MovementIntentRefusal(
                    "unknown_action_demand", "movement cannot classify another active Action's demand")
        premise = candidate.world_premise
        return MovementRateConditions(
            terrain_multiplier=premise.terrain_multiplier,
            hampered_multiplier=premise.hampered_multiplier,
            direction=None,
            concurrent_demanding_action=demanding)

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
