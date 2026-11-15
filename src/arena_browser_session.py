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

from action import Action
from arena_initialization import ArenaInitializationRefusal, initialize_two_being_arena
from activities import RunAction, ReadyWeaponAction, ThrowAction
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


def _native_spot_actions(candidate, actor_id, sense=None):
    """Return exact native discovery Actions, including accepted Choice members."""
    from activities import SpotAction
    actions = {item.id: item for item in candidate.universe.event_history.values()
               if type(item) is SpotAction and item.actor_id == actor_id
               and (sense is None or item.event_type == sense)}
    for record in candidate.encounter._choice_book._choices.values():
        for member in record.members:
            item = member.action
            if (type(item) is SpotAction and item.actor_id == actor_id
                    and (sense is None or item.event_type == sense)):
                actions[item.id] = item
    return tuple(actions[key] for key in sorted(actions))


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
        self._authored_scenario_id = None
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
        self._encounter_mode = "player_vs_arena"
        self._arena_strategies = ["none", "none"]
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
                    by_being[being_id], being, source_by_being[being_id], candidate.universe,
                    candidate.encounter)
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
            if meta.get('authored_scenario_id') == 'ordinary-dagger-draw':
                from weapon import WeaponInstance
                from arena_authored_draw_scenario import native_scenario_source
                player = universe.get_object_by_id(meta['player_id'])
                authored = [universe.get_object_by_id(object_id) for object_id in player.possessions]
                if not any(type(item) is WeaponInstance and item.current.obj_type == 'Dagger'
                           and native_scenario_source(item) == {'scenario_id': 'ordinary-dagger-draw',
                                                               'owner_id': player.id}
                           for item in authored):
                    raise ArenaBrowserRequestError(
                        "Saved authored scenario provenance does not match its native Dagger facts")
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
            old=(self._active,self._authored_scenario_id,self._encounter_name,self._player_name,self._rng_cursor,
                 self._movement_plan,self._movement_sequence,self._display_names,
                 self._view_handles,self._selected_entity_handle,self._movement_outcome,
                self._opponent_strategy,self._encounter_mode,self._arena_strategies,self._opponent_attack_refusal,
                 self._player_action_id,self._player_action_outcome,self._pickup_action_id,
                 self._pickup_action_outcome,self._ready_weapon_action_id,
                 self._ready_weapon_action_outcome,self._ready_weapon_end_time)
            try:
                self._active=candidate;self._authored_scenario_id=meta.get('authored_scenario_id');self._encounter_name=meta['encounter_name']
                self._player_name=meta['player_name'];self._rng_cursor=rng_owner
                self._opponent_strategy=meta['opponent_strategy']
                self._encounter_mode=meta.get('encounter_mode', 'player_vs_arena')
                self._arena_strategies=list(meta.get('arena_strategies', ['none', meta['opponent_strategy']]))
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
                (self._active,self._authored_scenario_id,self._encounter_name,self._player_name,self._rng_cursor,
                 self._movement_plan,self._movement_sequence,self._display_names,
                 self._view_handles,self._selected_entity_handle,self._movement_outcome,
                 self._opponent_strategy,self._encounter_mode,self._arena_strategies,self._opponent_attack_refusal,
                 self._player_action_id,self._player_action_outcome,self._pickup_action_id,
                 self._pickup_action_outcome,self._ready_weapon_action_id,
                 self._ready_weapon_action_outcome,self._ready_weapon_end_time)=old
                raise

    def _action_program_views(self, candidate, player, ledger):
        """Project live declared program members without exposing native IDs."""
        result = []
        now = candidate.encounter.time
        for record in candidate.encounter._choice_book._choices.values():
            if (record.view.state not in ("accepted", "executing")
                    or not any(member.action.actor_id == player.id for member in record.members)):
                continue
            components = []
            for index, (member, packet) in enumerate(zip(record.members, record.prepared), 1):
                action = member.action
                if action.actor_id != player.id:
                    continue
                target_evidence = (None if action.target_id is None else next(
                    (row for row in ledger.current if row.entity_id == action.target_id), None))
                components.append({
                    "order": index,
                    "name": action.event_type.replace("_", " ").title(),
                    "status": ("paused" if candidate.encounter._choice_book.is_paused(action.id)
                        else "executing" if action.id in candidate.encounter.pending_action_list
                        else "accepted"),
                    "start_seconds": packet.start_time,
                    "end_seconds": packet.end_time,
                    "duration_seconds": packet.end_time - packet.start_time,
                    "seconds_remaining": max(0, math.ceil(
                        candidate.encounter._choice_book.effective_end(action) - now)),
                    "priority_penalty": member.priority_penalty,
                    "target_name": (None if target_evidence is None else
                        self._display_names.get(target_evidence.entity_id, target_evidence.name)),
                    "resources": {name: getattr(action.strategy, name, 0)
                        for name in ("attack", "defense", "timing", "extra_damage")},
                })
            result.append({"status": record.view.state,
                           "first_start_seconds": record.view.first_start,
                           "components": components})
        return result

    def _view_unlocked(self):
        if self._active is None:
            return {
                "state": "empty",
                "encounter_mode": "player_vs_arena",
                "arena_strategies": ["none", "none"],
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
                "playable_scenario_available": True,
            }
        candidate = self._active
        from activities import PickUpAction, RunAction, SpotAction, ReadyWeaponAction, ReadyPreparationAction, DelayAction
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
        spot_action = None
        discovery_actions = {}
        if self._authored_scenario_id == "arena-spot-demo":
            for sense in ('spot', 'search', 'listen'):
                spot_candidates = _native_spot_actions(candidate, player.native.being.id, sense)
                native_spot = (max(spot_candidates, key=lambda item: (item.start_time, item.end_time, item.id))
                               if spot_candidates else None)
                if native_spot is None:
                    discovery_actions[sense] = {"name": sense.title(), "status": "available",
                                                "outcome": None, "duration_seconds": 6,
                                                "seconds_remaining": 0}
                    continue
                accepted_choice = any(native_spot.id in record.view.action_ids
                    and record.view.state in ("accepted", "executing")
                    for record in candidate.encounter._choice_book._choices.values())
                if native_spot.id in candidate.encounter.cancelled_action_list:
                    spot_status, spot_outcome = "cancelled", None
                elif native_spot.id in candidate.encounter.finished_action_list:
                    spot_status = "completed"
                    spot_outcome = (None if native_spot.resolution is None
                                    else native_spot.resolution.outcome)
                else:
                    spot_status, spot_outcome = ("executing" if accepted_choice
                                                  or native_spot.id in candidate.encounter.pending_action_list
                                                  else "accepted"), None
                discovery_actions[sense] = {"name": sense.title(), "status": spot_status,
                    "outcome": spot_outcome, "duration_seconds": 6,
                    "seconds_remaining": max(0, math.ceil(native_spot.end_time-candidate.encounter.time))}
            spot_action = discovery_actions.get('spot')
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
        ready_preparation_action = None
        ready_action = self._player_base_action(candidate, player.native.being, "ready object")
        if ready_action is not None:
            active_choice = any(ready_action.id in row.view.action_ids
                and row.view.state in ("accepted", "executing")
                for row in candidate.encounter._choice_book._choices.values())
            if ready_action.id in candidate.encounter.pending_action_list or active_choice:
                ready_preparation_action = {"name": "Ready",
                    "status": "executing", "outcome": None,
                    "motion": ready_action.ready_motion,
                    "duration_seconds": ready_action.readying_seconds,
                    "seconds_remaining": max(0, math.ceil(ready_action.end_time-candidate.encounter.time))}
            elif ready_action.id in candidate.encounter.cancelled_action_list:
                ready_preparation_action = {"name": "Ready", "status": "cancelled",
                    "outcome": None, "motion": ready_action.ready_motion,
                    "duration_seconds": ready_action.readying_seconds, "seconds_remaining": 0}
            else:
                record = candidate.encounter.inspect_committed(int(ready_action.end_time)).action(ready_action.id)
                ready_preparation_action = {"name": "Ready", "status": "completed",
                    "outcome": record.facts.outcome, "motion": ready_action.ready_motion,
                    "duration_seconds": ready_action.readying_seconds, "seconds_remaining": 0}
        delay_action = self._named_base_action_view(candidate, player.native.being,
                                                    "delay", "Delay")
        book=candidate.encounter._choice_book
        pending_owned=[candidate.universe.get_event_by_id(aid)
            for aid in candidate.encounter.pending_action_list
            if candidate.universe.get_event_by_id(aid) is not None
            and candidate.universe.get_event_by_id(aid).actor_id==player.native.being.id]
        paused_action=next((action for action in pending_owned if book.is_paused(action.id)),None)
        pause_candidates=[action for action in pending_owned if not book.is_paused(action.id)
            and action.start_time<candidate.encounter.time
            and action.event_type not in ('swing','thrust','charge','spell','cast','spellcasting')
            and book._states.get(action.id)=='executing']
        pause_resume={"paused_action":(None if paused_action is None else {
                "name":paused_action.event_type.replace('_',' ').title(),
                "seconds_remaining":book._paused[paused_action.id]['remaining']}),
            "pause_available":bool(pause_candidates),"resume_available":paused_action is not None}
        melee_action = self._melee_action_view(candidate, player.native.being)
        melee_pending = (melee_action is not None and melee_action["status"] == "executing")
        touch_action = self._touch_action_view(candidate, player.native.being)
        touch_pending = touch_action is not None and touch_action["status"] == "executing"
        grappling_action = self._grappling_action_view(candidate, player.native.being)
        grappling_pending = grappling_action is not None and grappling_action["status"] == "executing"
        from physical_contact import active_contact_state
        active_grips, active_controls = active_contact_state(candidate.encounter)
        contact_check_boundaries = tuple(row[5] for row in (*active_grips, *active_controls))
        contact_wait_available = any(boundary >= candidate.encounter.time + 1
                                     for boundary in contact_check_boundaries)
        contact_status = []
        now = candidate.encounter.time
        for row in active_grips:
            _, holder_id, held_id, hand, _, next_check = row
            check_text=f"; next maintenance check in {max(0,next_check-now)} s"
            if holder_id == player.native.being.id:
                other = candidate.encounter.get_being(held_id)
                contact_status.append(f"You hold {self._display_names.get(held_id, other.name)} with {hand}{check_text}")
            elif held_id == player.native.being.id:
                other = candidate.encounter.get_being(holder_id)
                contact_status.append(f"{self._display_names.get(holder_id, other.name)} holds you{check_text}")
        for row in active_controls:
            _, controller_id, controlled_id, _, _, next_check, *position_detail = row
            position_label = position_detail[0] if position_detail else "standing"
            check_text=f"; next Grapple check in {max(0,next_check-now)} s"
            if controller_id == player.native.being.id:
                other = candidate.encounter.get_being(controlled_id)
                contact_status.append(f"You have Grapple control of {self._display_names.get(controlled_id, other.name)} ({position_label}){check_text}")
            elif controlled_id == player.native.being.id:
                other = candidate.encounter.get_being(controller_id)
                contact_status.append(f"{self._display_names.get(controller_id, other.name)} has Grapple control of you ({position_label}){check_text}")
        from physical_contact import active_object_grip_state
        for row in active_object_grip_state(candidate.encounter):
            object_id,_,actor_id,holder_id,actor_hand,holder_hand,_=row
            if actor_id!=player.native.being.id:continue
            obj=candidate.universe.get_object_by_id(object_id)
            holder=candidate.encounter.get_being(holder_id)
            evidence=next((item for item in ledger.current if item.entity_id==object_id),None)
            if obj is None or holder is None or evidence is None or evidence.present_state!='carried':
                continue
            object_name=self._display_names.get(object_id,evidence.name)
            holder_name=self._display_names.get(holder_id,holder.name)
            contact_status.append(f"You grip {object_name} with {actor_hand}; {holder_name} holds it in {holder_hand}")
        from physical_contact import shared_object_holders
        for object_id, obj in candidate.universe.object_registry.object_instances.items():
            holders=shared_object_holders(candidate.encounter,object_id)
            own_hand=next((hand for being_id,hand in holders
                           if being_id==player.native.being.id),None)
            if own_hand is None:
                continue
            evidence=next((item for item in ledger.current if item.entity_id==object_id),None)
            if evidence is not None and evidence.present_state=='carried':
                object_name=self._display_names.get(object_id,evidence.name)
                contact_status.append(f"You jointly hold {object_name} in {own_hand}")
        feint_action = self._feint_action_view(candidate, player.native.being)
        feint_pending = feint_action is not None and feint_action["status"] == "executing"
        coup_de_grace_action = self._named_base_action_view(candidate, player.native.being, "coup de grace", "Coup de grace")
        coup_de_grace_pending = coup_de_grace_action is not None and coup_de_grace_action["status"] == "executing"
        object_strike_action = self._named_base_action_view(candidate, player.native.being, "strike object", "Strike an object")
        object_strike_pending = object_strike_action is not None and object_strike_action["status"] == "executing"
        disarm_action = self._named_base_action_view(candidate, player.native.being, "disarm", "Disarm")
        disarm_pending = disarm_action is not None and disarm_action["status"] == "executing"
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
            for action_type in (Action, RunAction, SpotAction, PickUpAction, ReadyWeaponAction,
                                ReadyPreparationAction, DelayAction, ThrowAction,
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
            projectile_evidence = None
            if evidence.category == 'object':
                observed = candidate.universe.get_object_by_id(evidence.entity_id)
                from throwing import ProjectileFlight
                flight = (None if observed is None else object.__getattribute__(
                    observed, '__dict__').get('_projectile_flight'))
                if type(flight) is ProjectileFlight:
                    projectile_evidence = {
                        "status": flight.status,
                        "outcome": flight.impact_outcome,
                        "miss_direction": flight.miss_direction,
                    }
            perceived.append({
                "handle": handle, "category": evidence.category,
                "name": self._display_names.get(evidence.entity_id, evidence.name),
                "type": evidence.type_key,
                "present_state": evidence.present_state,
                "equipment_status": evidence.equipment_status,
                "position_meters": None if p is None else {"x": p.x, "y": p.y, "z": p.z},
                "observed_motion_interval": (None if evidence.motion_interval is None
                    else list(evidence.motion_interval)),
                "currently_observable": evidence.currently_observable,
                "visibility_boundary": evidence.visibility_boundary,
                "cell": None if address is None else {"column": address.column, "row": address.row},
                "pickup_available": pickup_available,
                "pickup_unavailable_reason": pickup_unavailable_reason,
                "projectile": projectile_evidence,
            })
        # Keep observer history inspectable separately from the current
        # projection. The records come only from this Being's native ledger;
        # native Entity IDs are replaced with the session's opaque handles.
        observation_history = []
        for evidence in ledger.history:
            handle = self._view_handles.get(evidence.entity_id)
            if handle is None:
                handle = secrets.token_urlsafe(18)
                self._view_handles[evidence.entity_id] = handle
            p = evidence.position
            observation_history.append({
                "handle": handle,
                "category": evidence.category,
                "name": self._display_names.get(evidence.entity_id, evidence.name),
                "type": evidence.type_key,
                "present_state": evidence.present_state,
                "position_meters": None if p is None else
                    {"x": p.x, "y": p.y, "z": p.z},
                "observed_motion_interval": (None if evidence.motion_interval is None
                    else list(evidence.motion_interval)),
                "currently_observable": evidence.currently_observable,
                "visibility_boundary": evidence.visibility_boundary,
                "boundary": evidence.boundary,
                "time_seconds": evidence.time,
            })
        # The player may address directly held inventory through the same
        # opaque session handle contract as perceived entities. This is
        # player-owned inventory evidence, never a handle to another Being's
        # private Object graph.
        visible_inventory_ids = tuple(dict.fromkeys(tuple(player.native.being.possessions)
            + tuple(player.native.being.weapons)
            + tuple(value for value in player.native.being.current.body_parts.values()
                    if value is not None)))
        for object_id in visible_inventory_ids:
            obj = candidate.universe.get_object_by_id(object_id)
            if (obj is not None and obj.parent_container_id in (None, player.native.being.id)
                    and object_id not in self._view_handles):
                self._view_handles[object_id] = secrets.token_urlsafe(18)
        disarm_landing_choice = None
        from weapon import WeaponInstance, native_pending_disarm_landing
        from atomic_publication import disarm_landing_options
        for object_id,obj in candidate.universe.object_registry.object_instances.items():
            if type(obj) is not WeaponInstance:continue
            pending=native_pending_disarm_landing(obj)
            if pending is None or pending['actor_id']!=player.native.being.id:continue
            evidence=next((row for row in ledger.current if row.entity_id==object_id),None)
            handle=self._view_handles.get(object_id)
            if evidence is None or handle is None or evidence.category!='object':continue
            options=disarm_landing_options(candidate.encounter,object_id)
            disarm_landing_choice={"handle":handle,"weapon_name":self._display_names.get(object_id,evidence.name),
                "maximum_landing_hexes":pending['max_landing_hexes'],
                "cells":[{"column":row.column,"row":row.row} for row in options]}
            break
        movement_available = movement_available and disarm_landing_choice is None
        selected = next((row for row in perceived
                         if row["handle"] == self._selected_entity_handle), None)
        selected_being = (self._observer_being_sheet_unlocked(candidate, selected)
                          if selected is not None and selected["category"] == "being" else None)
        character = self._player_character_sheet_unlocked(
            candidate, player, position, cell, movement_plan)
        from attention_intent import eligible_discovery_targets
        discovery_candidate_available = {
            sense: len(eligible_discovery_targets(candidate.encounter,
                player.native.being.id, sense)) == 1
            for sense in ('search', 'spot', 'listen')}
        action_catalog = self._action_catalog_unlocked(
            candidate, player.native.being, selected, supported_actions)
        action_programs = self._action_program_views(
            candidate, player.native.being, ledger)
        discovery_action_pending = any(row.get('status') in ('accepted', 'executing')
                                       for row in discovery_actions.values())
        owned_projectiles = []
        from object import ObjectInstance
        from throwing import ProjectileFlight
        for object_id in candidate.encounter.non_being_object_list:
            obj = candidate.universe.get_object_by_id(object_id)
            flight = (None if obj is None else object.__getattribute__(
                obj, '__dict__').get('_projectile_flight'))
            if (type(obj) is not ObjectInstance or type(flight) is not ProjectileFlight
                    or flight.attacker_id != player.native.being.id):
                continue
            handle = self._view_handles.get(object_id)
            if handle is None:
                handle = secrets.token_urlsafe(18)
                self._view_handles[object_id] = handle
            p = obj.get_position()
            owned_projectiles.append({
                "handle": handle,
                "status": flight.status,
                "outcome": flight.impact_outcome,
                "miss_direction": flight.miss_direction,
                "position_meters": None if p is None else
                    {"x": p.x, "y": p.y, "z": p.z},
            })
        spectator_projection = None
        if self._encounter_mode == "arena_vs_arena":
            chronology = []
            if candidate.encounter.progression_mode == "transactional":
                from encounter_inspection import inspect_encounter
                from action_evaluation import DamageEffect
                inspection = inspect_encounter(candidate.encounter)
                actions = (*self._all_melee_actions(candidate),
                           *self._all_melee_defenses(candidate))
                for spectator_action in sorted(actions, key=lambda row: (row.start_time, row.id)):
                    result = inspection.actions.get(spectator_action.id)
                    if result is None:
                        continue
                    actor_index = candidate.encounter.being_list.index(spectator_action.actor_id)
                    target_index = (1-candidate.encounter.being_list.index(spectator_action.target_id)
                                    if spectator_action.target_id in candidate.encounter.being_list else None)
                    chronology.append({
                        "actor": f"Being {'A' if actor_index == 0 else 'B'}",
                        "target": (None if target_index is None else
                                   f"Being {'A' if target_index == 0 else 'B'}"),
                        "action": spectator_action.event_type.replace("_", " ").title(),
                        "start_seconds": spectator_action.start_time,
                        "end_seconds": spectator_action.end_time,
                        "outcome": result.facts.outcome,
                        "damage": sum(effect.amount for effect in result.facts.effects
                                       if type(effect) is DamageEffect and effect.amount > 0),
                    })
            spectator_projection = {
                "label": "Spectator / referee projection; separate from Being observations and never used by strategies",
                "strategies": {"Being A": self._arena_strategies[0],
                               "Being B": self._arena_strategies[1]},
                "chronology": chronology,
            }
        return {
            "state": "active",
            "encounter_mode": self._encounter_mode,
            "arena_strategies": list(self._arena_strategies),
            "manual_controls_available": self._encounter_mode == "player_vs_arena",
            "spectator_projection": spectator_projection,
            "authored_scenario_id": self._authored_scenario_id,
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
                       "size_category": player.native.being.size_category,
                       "hex_facing": player.native.being.hex_facing,
                       "posture": player.native.being.posture,
                       "posture_source": player.posture_provenance,
                       "cell": cell,
                       "position_meters": {"x": position.x, "y": position.y, "z": position.z}},
            "character": character,
            "selected_being": selected_being,
            "player_action": action,
            "spot_action": spot_action,
            "discovery_actions": discovery_actions,
            "pickup_action": pickup_action,
            "ready_weapon_action": ready_weapon_action,
            "ready_preparation_action": ready_preparation_action,
            "delay_action": delay_action,
            **pause_resume,
            "melee_action": melee_action,
            "touch_action": touch_action,
            "grappling_action": grappling_action,
            "contact_wait_available": contact_wait_available,
            "contact_status": contact_status,
            "contact_check_seconds": (None if not contact_check_boundaries else
                max(0, min(contact_check_boundaries)-candidate.encounter.time)),
            "feint_action": feint_action,
            "coup_de_grace_action": coup_de_grace_action,
            "object_strike_action": object_strike_action,
            "disarm_action": disarm_action,
            "disarm_landing_choice": disarm_landing_choice,
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
            "observation_history": observation_history,
            "projectiles": owned_projectiles,
            "selected_entity": selected,
            "action_catalog": action_catalog,
            "action_programs": action_programs,
            "run_available": self._player_action_id is None and not candidate.encounter.initiated,
            "advance_available": (self._encounter_mode == "arena_vs_arena" or
                                   (disarm_landing_choice is None and ((self._player_action_id is not None
                                    and self._player_action_outcome is None)
                                   or (self._pickup_action_id is not None
                                       and self._pickup_action_outcome is None)
                                   or (self._ready_weapon_action_id is not None
                                       and self._ready_weapon_action_outcome is None)
                                   or (ready_preparation_action is not None
                                       and ready_preparation_action["status"] == "executing")
                                   or (delay_action is not None
                                       and delay_action["status"] == "executing")
                                   or discovery_action_pending
                                   or melee_pending
                                   or touch_pending
                                   or grappling_pending
                                   or contact_wait_available
                                   or feint_pending
                                   or coup_de_grace_pending
                                   or object_strike_pending
                                   or disarm_pending
                                   or opponent_melee_pending
                                   or (defense_action is not None
                                       and defense_action["status"] in ("accepted", "preparing", "committed"))
                                   or (opponent_defense_action is not None
                                       and opponent_defense_action["status"] in ("accepted", "preparing", "committed"))
                                   or opponent_can_act
                                   or movement_plan is not None))),
            "movement_available": movement_available,
            "movement_reason": None if movement_available else _MOVEMENT_DISABLED,
            "movement_plan": movement_plan,
            "movement_outcome": self._movement_outcome,
            "spot_available": (self._authored_scenario_id == "arena-spot-demo"
                and candidate.encounter.initiated and self._encounter_mode == "player_vs_arena"
                and discovery_candidate_available['spot'] and not discovery_action_pending),
            "spot_reason": ("Native target-free Spot is a six-second Action; it does not disclose a target identity."
                if self._authored_scenario_id == "arena-spot-demo" and candidate.encounter.initiated
                else _SPOT_DISABLED),
            "search_available": (self._authored_scenario_id == "arena-spot-demo"
                and candidate.encounter.initiated and self._encounter_mode == "player_vs_arena"
                and discovery_candidate_available['search'] and not discovery_action_pending),
            "listen_available": (self._authored_scenario_id == "arena-spot-demo"
                and candidate.encounter.initiated and self._encounter_mode == "player_vs_arena"
                and discovery_candidate_available['listen'] and not discovery_action_pending),
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
        if type(obj) is not WeaponInstance or obj.id != entity_id:
            return None, (), "Initial readying requires a native Weapon Object."
        if (entity_id not in player.possessions or player.possessions.count(entity_id) != 1
                or obj.parent_container_id != player.id or obj.get_position() is not None):
            return None, (), "The selected Weapon is not in the player's native carried custody."
        if entity_id in player.weapons or entity_id in player.current.body_parts.values():
            return None, (), "This Weapon is already held/readied."
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
            return None, (), "The native Weapon draw-location record is malformed."
        if location is None:
            return None, (), (
                "The carried Weapon has no authored drawable source location. Ground Pick up does "
                "not designate a sheath or hand; retrieval time is undetermined."
            )
        if location["owner_id"] != player.id:
            return None, (), "The Weapon's drawable sheath is not assigned to the player Being."
        body_parts = player.current.body_parts
        hands = tuple(sorted(slot for slot, held in body_parts.items()
                             if slot in ReadyWeaponAction.HANDS and held is None))
        if not hands:
            return None, (), (
                "No explicitly modeled, free native left or right hand is available for this "
                "otherwise drawable Weapon."
            )
        return obj, hands, (
            "Native Draw from the explicitly authored worn sheath takes 2 seconds. "
            "Post-strike re-ready timing is separate."
        )

    def _ready_preparation_options_unlocked(self, candidate, player, entity_id, evidence):
        from weapon import (WeaponInstance, native_ready_preparation,
                            weapon_readying_time)
        if evidence is None or evidence.category != "object":
            return (), "Select a currently perceived Weapon first."
        weapon = candidate.universe.get_object_by_id(entity_id)
        if type(weapon) is not WeaponInstance:
            return (), "Ready requires a native Weapon Object."
        if (entity_id not in player.weapons
                or entity_id not in player.armed_with(candidate.universe).values()
                or entity_id not in player.current.body_parts.values()):
            return (), "Draw the Weapon and hold it in an explicitly represented hand before Ready."
        if player.current.hit_points <= 0 or player.is_helpless():
            return (), "The player Being cannot perform a voluntary Action in its current native condition."
        try:
            preparation = native_ready_preparation(weapon)
        except (TypeError, ValueError):
            return (), "The native Weapon Ready-preparation record is malformed."
        if preparation is not None:
            return (), "This Weapon already has completed preparation; use it or wait without re-readying."
        options = []
        reasons = []
        for motion in weapon.get_melee_types():
            try:
                seconds = weapon_readying_time(weapon, motion)
            except ValueError as exc:
                reasons.append(f"{motion}: {exc}")
                continue
            options.append({"motion": motion, "duration_seconds": seconds})
        categories = candidate.universe.library.weapon_dictionary.object_categories
        pole_names = set(categories.get('Spears', ())) | set(categories.get('Lances', ()))
        if weapon.current.obj_type in pole_names and 'thrust' in weapon.get_melee_types():
            options.append({"motion": "set pole", "duration_seconds": 4})
        if not options:
            return (), ("No supported weapon motion can be readied as a positive-duration native Action. "
                        + "; ".join(reasons))
        return tuple(options), "Ready prepares only the selected motion; the benefit remains until this Weapon is used."

    @staticmethod
    def _initial_ready_weapon_id(candidate, player):
        """Return the actual primary Weapon Object committed by initial Arena-ready state."""
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
                    and type(unit.get("native_type_key")) is str):
                        return object_ids.get(unit.get("equipment_id"))
            # Strict compatibility for already-saved U-ARENA-009 initial kits.
            weapon = row.get("weapon")
            if (row.get("policy") == "universe-arena-class-xp-equipment/1"
                    and type(weapon) is dict and weapon.get("type") == "Dagger"):
                return weapon.get("object_id")
        return None

    # Kept as a private compatibility alias for adjacent Arena controls which
    # still use the historical name. The returned identity is no longer
    # restricted to a Dagger.
    _initial_ready_dagger_id = _initial_ready_weapon_id

    def _melee_weapon_options(self, candidate, player, target_id, evidence, motion):
        """Project only currently held, observer-addressable weapon/grip choices."""
        from weapon import WeaponInstance
        shield_names = set(candidate.universe.library.weapon_dictionary
                           .get_objects_in_category('Shields'))
        options = []
        for hand, object_id in sorted(player.current.body_parts.items()):
            if hand not in ('left hand', 'right hand') or object_id is None:
                continue
            weapon = candidate.universe.get_object_by_id(object_id)
            handle = self._view_handles.get(object_id)
            if (type(weapon) is not WeaponInstance or handle is None
                    or weapon.current.obj_type in shield_names):
                continue
            for two_handed in (False, True):
                try:
                    _action, _weapon, prepared, _distance, _reach = self._melee_strike_preflight(
                        candidate, player, target_id, evidence, motion,
                        weapon_id=object_id, two_handed=two_handed)
                except (ArenaBrowserRequestError, TypeError, ValueError):
                    continue
                options.append({"handle": handle, "name": weapon.name or weapon.current.obj_type,
                    "type": weapon.current.obj_type, "hand": hand,
                    "grip": "two-handed" if two_handed else "one-handed",
                    "duration_seconds": prepared.end_time - prepared.start_time})
        return options

    def _shield_bash_options(self, candidate, player, target_id, evidence):
        options = []
        for hand, shield_id in sorted(player.shielded_with(candidate.universe).items()):
            shield = candidate.universe.get_object_by_id(shield_id)
            handle = self._view_handles.get(shield_id)
            if handle is None or shield is None:
                continue
            for motion in shield.get_melee_types():
                try:
                    _action, _weapon, prepared, _distance, _reach = self._melee_strike_preflight(
                        candidate, player, target_id, evidence, motion,
                        weapon_id=shield_id, shield_bash=True)
                except (ArenaBrowserRequestError, TypeError, ValueError):
                    continue
                options.append({"handle": handle, "name": shield.name or shield.current.obj_type,
                    "type": shield.current.obj_type, "hand": hand, "motion": motion,
                    "duration_seconds": prepared.end_time - prepared.start_time})
        return options

    def _object_strike_weapon_options(self, candidate, player, object_id, evidence, motion):
        from weapon import WeaponInstance
        shield_names = set(candidate.universe.library.weapon_dictionary
                           .get_objects_in_category('Shields'))
        options = []
        for hand, weapon_id in sorted(player.current.body_parts.items()):
            if hand not in ('left hand','right hand') or weapon_id is None:
                continue
            weapon = candidate.universe.get_object_by_id(weapon_id)
            handle = self._view_handles.get(weapon_id)
            if (type(weapon) is not WeaponInstance or handle is None
                    or weapon.current.obj_type in shield_names):
                continue
            try:
                _action, prepared, _distance, _reach = self._object_strike_preflight(
                    candidate, player, object_id, evidence, motion, weapon_id=weapon_id)
            except (ArenaBrowserRequestError, TypeError, ValueError):
                continue
            options.append({"handle": handle, "name": weapon.name or weapon.current.obj_type,
                "type": weapon.current.obj_type, "hand": hand,
                "duration_seconds": prepared.end_time - prepared.start_time})
        return options

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
        from action_evaluation import DamageEffect
        outcome = record.facts.outcome
        hit = outcome in ("normal", "critical", "fatal")
        damage_committed = any(type(effect) is DamageEffect and effect.amount > 0
                               for effect in record.facts.effects)
        weapon = candidate.universe.get_object_by_id(action.instrument_id)
        return {"name": action.event_type.title(), "status": "completed",
                "outcome": outcome,
                "result_label": ("hit" if hit else outcome),
                "damage_committed": damage_committed,
                "weapon_name": None if weapon is None else weapon.name,
                "duration_seconds": action.end_time - action.start_time,
                "seconds_remaining": 0, "target_name": target_name,
                "impact_distance_meters": distance}

    @staticmethod
    def _player_touch_action(candidate, player):
        event_by_id = dict(candidate.universe.event_history)
        committed_ids = (set(candidate.encounter.pending_action_list)
                         | set(candidate.encounter.finished_action_list)
                         | set(candidate.encounter.cancelled_action_list))
        for choice in candidate.encounter._choice_book._choices.values():
            if choice.view.state not in ("accepted", "executing", "finished"):
                continue
            committed_ids.update(choice.view.action_ids)
            for member in choice.members:
                if type(member.action) is Action and member.action.event_type == "touch":
                    event_by_id[member.action.id] = member.action
        actions = [event for event in event_by_id.values()
                   if type(event) is Action and event.event_type == "touch"
                   and event.actor_id == player.id and event.id in committed_ids]
        return max(actions, key=lambda action: (action.start_time, action.id), default=None)

    @staticmethod
    def _player_trip_contact_action(candidate, player, target):
        from physical_contact import trip_contact_kind
        actions = [event for event in candidate.universe.event_history.values()
                   if type(event) in (Action, MeleeStrike) and event.actor_id == player.id
                   and event.target_id == target.id
                   and trip_contact_kind(candidate.encounter,event.id,player.id,target.id) is not None]
        return max(actions,key=lambda action:(action.end_time,action.id),default=None)

    def _touch_action_view(self, candidate, player):
        action = self._player_touch_action(candidate, player)
        if action is None:
            return None
        if self._melee_action_pending(candidate, action):
            return {"name": "Touch", "status": "executing", "outcome": None,
                    "seconds_remaining": max(0, math.ceil(action.end_time-candidate.encounter.time)),
                    "end_time": action.end_time}
        if action.id in candidate.encounter.cancelled_action_list:
            return {"name": "Touch", "status": "cancelled", "outcome": None,
                    "seconds_remaining": 0, "end_time": action.end_time}
        try:
            record = candidate.encounter.inspect_committed(
                int(math.ceil(action.end_time))).action(action.id)
        except (ValueError, KeyError, AttributeError):
            return {"name": "Touch", "status": "completed", "outcome": "unavailable",
                    "seconds_remaining": 0, "end_time": action.end_time}
        return {"name": "Touch", "status": "completed", "outcome": record.facts.outcome,
                "seconds_remaining": 0, "end_time": action.end_time}

    @staticmethod
    def _grappling_action_view(candidate, player):
        event_by_id = dict(candidate.universe.event_history)
        accepted = (set(candidate.encounter.pending_action_list)
                    | set(candidate.encounter.finished_action_list)
                    | set(candidate.encounter.cancelled_action_list))
        active_choices = set()
        prepared_ends = {}
        for choice in candidate.encounter._choice_book._choices.values():
            if choice.view.state not in ("accepted", "executing", "finished"):
                continue
            for member, packet in zip(choice.members, choice.prepared):
                if type(member.action) is Action:
                    event_by_id[member.action.id] = member.action
                    accepted.add(member.action.id)
                    prepared_ends[member.action.id] = packet.end_time
                    if choice.view.state in ("accepted", "executing"):
                        active_choices.add(member.action.id)
        actions = [event_by_id.get(action_id) for action_id in accepted]
        actions = [action for action in actions if type(action) is Action
                   and action.actor_id == player.id and action.event_type in
                   ("grab", "grab object", "wrest", "break hold", "release grip", "grapple", "grapple escape", "takedown", "reverse", "pin", "trip", "bull rush", "overrun", "end-run")]
        action = max(actions, key=lambda row: (row.start_time, row.end_time, row.id), default=None)
        if action is None:
            return None
        label = {"grab":"Grab", "grab object":"Grab held Object", "wrest":"Wrest", "hold":"Hold", "break hold":"Break hold", "release grip":"Release grip",
                 "grapple":"Grapple", "grapple escape":"Grapple Escape",
                 "takedown":"Takedown", "reverse":"Reverse", "pin":"Pin", "trip":"Trip", "bull rush":"Bull Rush", "overrun":"Overrun", "end-run":"End Run"}[action.event_type]
        if action.id in candidate.encounter.pending_action_list or action.id in active_choices:
            action_end = prepared_ends.get(action.id, action.end_time)
            return {"name":label,"status":"executing","outcome":None,
                    "seconds_remaining":max(0,math.ceil(action_end-candidate.encounter.time)),
                    "end_time":action_end}
        if action.id in candidate.encounter.cancelled_action_list:
            return {"name":label,"status":"cancelled","outcome":None,
                    "seconds_remaining":0,"end_time":action.end_time}
        try:
            record = candidate.encounter.inspect_committed(int(action.end_time)).action(action.id)
        except (ValueError, KeyError, AttributeError):
            return {"name":label,"status":"completed","outcome":"unavailable","seconds_remaining":0,
                    "end_time":action.end_time}
        return {"name":label,"status":"completed","outcome":record.facts.outcome,
                "seconds_remaining":0,"end_time":action.end_time}

    @staticmethod
    def _player_feint_action(candidate, player):
        event_by_id = dict(candidate.universe.event_history)
        committed_ids = (set(candidate.encounter.pending_action_list)
                         | set(candidate.encounter.finished_action_list)
                         | set(candidate.encounter.cancelled_action_list))
        for choice in candidate.encounter._choice_book._choices.values():
            if choice.view.state not in ("accepted", "executing", "finished"):
                continue
            committed_ids.update(choice.view.action_ids)
            for member in choice.members:
                if type(member.action) is Action and member.action.event_type == "feint":
                    event_by_id[member.action.id] = member.action
        actions = [event for event in event_by_id.values()
                   if type(event) is Action and event.event_type == "feint"
                   and event.actor_id == player.id and event.id in committed_ids]
        return max(actions, key=lambda action: (action.start_time, action.id), default=None)

    @staticmethod
    def _player_base_action(candidate, player, event_type):
        from activities import ReadyPreparationAction, DelayAction
        event_by_id=dict(candidate.universe.event_history)
        ids=(set(candidate.encounter.pending_action_list)|set(candidate.encounter.finished_action_list)
             |set(candidate.encounter.cancelled_action_list))
        for choice in candidate.encounter._choice_book._choices.values():
            if choice.view.state not in ("accepted","executing","finished"):continue
            ids.update(choice.view.action_ids)
            for member in choice.members:
                if type(member.action) in (Action,ReadyPreparationAction,DelayAction) and member.action.event_type==event_type:
                    event_by_id[member.action.id]=member.action
        rows=[event for event in event_by_id.values() if type(event) in (Action,ReadyPreparationAction,DelayAction)
            and event.actor_id==player.id and event.event_type==event_type and event.id in ids]
        return max(rows,key=lambda action:(action.start_time,action.id),default=None)

    @staticmethod
    def _named_base_action_view(candidate, player, event_type, label):
        from action_evaluation import ActionProposal
        action=GeneratedArenaSession._player_base_action(candidate,player,event_type)
        if action is None:return None
        if GeneratedArenaSession._melee_action_pending(candidate,action):
            return {"name":label,"status":"executing","outcome":None,
                "seconds_remaining":max(0,math.ceil(action.end_time-candidate.encounter.time))}
        if action.id in candidate.encounter.cancelled_action_list:
            return {"name":label,"status":"cancelled","outcome":None,"seconds_remaining":0}
        try:receipt=candidate.encounter.inspect_committed(int(math.ceil(action.end_time))).action(action.id)
        except (ValueError,KeyError,AttributeError):
            return {"name":label,"status":"completed","outcome":"unavailable","seconds_remaining":0}
        result={"name":label,"status":"completed","outcome":receipt.facts.outcome,"seconds_remaining":0}
        if event_type=='disarm':
            metadata=dict(receipt.facts.metadata)
            result.update({"margin":metadata.get('margin'),
                "maximum_landing_hexes":metadata.get('maximum_landing_hexes')})
        return result

    def _feint_action_view(self, candidate, player):
        action = self._player_feint_action(candidate, player)
        if action is None:
            return None
        if self._melee_action_pending(candidate, action):
            return {"name": "Feint", "status": "executing", "outcome": None,
                    "seconds_remaining": max(0, math.ceil(action.end_time-candidate.encounter.time))}
        if action.id in candidate.encounter.cancelled_action_list:
            return {"name": "Feint", "status": "cancelled", "outcome": None,
                    "seconds_remaining": 0}
        try:
            record = candidate.encounter.inspect_committed(
                int(math.ceil(action.end_time))).action(action.id)
        except (ValueError, KeyError, AttributeError):
            return {"name": "Feint", "status": "completed", "outcome": "unavailable",
                    "seconds_remaining": 0}
        return {"name": "Feint", "status": "completed", "outcome": record.facts.outcome,
                "seconds_remaining": 0}

    @staticmethod
    def _available_feint_source(candidate, player, target_id):
        from action_evaluation import ActionProposal
        rows = []
        for event in candidate.universe.event_history.values():
            if (type(event) is not Action or event.event_type != "feint"
                    or event.actor_id != player.id or event.target_id != target_id
                    or event.id not in candidate.encounter.finished_action_list
                    or type(event.resolution) is not ActionProposal
                    or event.resolution.outcome != "success"):
                continue
            rows.append(event)
        if not rows:
            return None
        source = max(rows, key=lambda action: (action.end_time, action.id))
        for choice in candidate.encounter._choice_book._choices.values():
            if choice.view.state not in ("accepted", "executing", "finished"):
                continue
            for member in choice.members:
                action = member.action
                if (action.actor_id == player.id and action.id != source.id
                        and action.start_time >= source.end_time):
                    return None
        return source.id

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

    def _strategy_for_participant(self, index):
        if type(index) is not int or index not in (0, 1):
            raise ValueError("Arena participant index must be 0 or 1")
        return self._arena_strategies[index]

    def _autonomous_participant_indices(self):
        if self._encounter_mode == "arena_vs_arena":
            return (0, 1)
        return (1,) if self._opponent_strategy != "none" else ()

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

    def _opponent_defense_decision(self, candidate, actor_index=1):
        actor = candidate.participants[actor_index].native.being
        target = candidate.participants[1-actor_index].native.being
        if self._strategy_for_participant(actor_index) != "defense_only":
            return {"kind": "none", "reason": "strategy_disabled"}
        encounter = candidate.encounter
        if (not encounter.initiated or encounter.progression_mode != "transactional"
                or not encounter.arena_activation_enabled):
            return {"kind": "none", "reason": "encounter_not_activated"}
        opponent = actor
        player = target
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

    def _opponent_attack_preflight(self, candidate, actor_index=1):
        """Read-only attack-only eligibility from opponent-owned current state."""
        if self._strategy_for_participant(actor_index) != "attack_only":
            return False, "strategy_disabled"
        encounter = candidate.encounter
        if (not encounter.initiated or encounter.progression_mode != "transactional"
                or not encounter.arena_activation_enabled):
            return False, "encounter_not_activated"
        opponent = candidate.participants[actor_index].native.being
        player = candidate.participants[1-actor_index].native.being
        if self._opponent_melee_pending(candidate, opponent):
            return False, "opponent_melee_already_pending"
        if any(action.actor_id == opponent.id
               for action in (candidate.universe.event_history.get(action_id)
                              for action_id in encounter.pending_action_list)
               if action is not None and action.event_type != "hold"):
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


    def _opponent_decision(self, candidate, actor_index=1):
        """Derive one attack-only choice from the opponent's current evidence."""
        if self._strategy_for_participant(actor_index) == "defense_only":
            return self._opponent_defense_decision(candidate, actor_index)
        eligible, reason = self._opponent_attack_preflight(candidate, actor_index)
        if not eligible:
            return {"kind": "none", "reason": reason}
        encounter = candidate.encounter
        opponent = candidate.participants[actor_index].native.being
        player = candidate.participants[1-actor_index].native.being
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
                "address": address, "destination": destination,
                "alternatives": tuple(options)}

    @staticmethod
    def _resolve_shared_movement_destinations(decisions):
        """Resolve duplicate AI destinations from the common pre-movement snapshot."""
        movers = [(index, row) for index, row in sorted(decisions.items())
                  if row.get("kind") == "move"]
        if len(movers) != 2 or movers[0][1]["address"] != movers[1][1]["address"]:
            return
        import itertools
        options = [tuple(row.get("alternatives", ())) for _, row in movers]
        compatible = [(left, right) for left, right in itertools.product(*options)
                      if left[-2] != right[-2]]
        if not compatible:
            for _, row in movers:
                row["kind"] = "none"
                row["reason"] = "no_noncontending_common_snapshot_destination"
            return
        left, right = min(compatible, key=lambda pair: (
            tuple(sum(item[position] for item in pair) for position in range(6)),
            tuple(sorted((item[-2].column, item[-2].row) for item in pair)),
            tuple((item[-2].column, item[-2].row) for item in pair)))
        for (_, row), option in zip(movers, (left, right)):
            row["address"], row["destination"] = option[-2], option[-1]


    def _schedule_opponent_attack(self, candidate, actor_index=1, decision=None):
        decision = self._opponent_decision(candidate, actor_index) if decision is None else decision
        self._opponent_attack_refusal = decision["reason"]
        if decision["kind"] != "attack":
            return None
        encounter = candidate.encounter
        opponent = candidate.participants[actor_index].native.being
        player = candidate.participants[1-actor_index].native.being
        weapon_id = self._initial_ready_dagger_id(candidate, opponent)
        weapon = candidate.universe.get_object_by_id(weapon_id)
        reach = effective_melee_reach_meters(opponent.current, weapon.current)
        action = MeleeStrike(encounter, opponent.id, player.id, weapon.id,
                             motion="thrust", reach=reach)
        # Event IDs are part of native Choice history. A stable encounter-local
        # name keeps a future AI declaration reproducible after save/restore.
        sequence = 1 + sum(action.actor_id == opponent.id
                           for action in self._all_melee_actions(candidate))
        action.id = f"{encounter.id}/arena-controller-{actor_index}-thrust/{sequence}"
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

    def _touch_preflight(self, candidate, player, entity_id, evidence, supported=True,
                         allow_composition=False):
        if not supported or not _has_native_transactional_action_contract(Action):
            raise ArenaBrowserRequestError("The native one-second Touch Action contract is unavailable.")
        if evidence is None or evidence.category != "being" or evidence.present_state != "present":
            raise ArenaBrowserRequestError("Select a currently perceived opposing Being first.")
        encounter = candidate.encounter
        target = encounter.get_being(entity_id) if type(entity_id) is str else None
        if (target is None or entity_id not in encounter.being_list
                or target.id == player.id or not encounter.is_aware(player.id, target.id)):
            raise ArenaBrowserRequestError("Touch requires an aware participating opposing Being.")
        if not encounter.initiated or encounter.progression_mode != "transactional":
            raise ArenaBrowserRequestError("Activate the native Encounter before choosing Touch.")
        if (not allow_composition and (encounter._choice_book.actor_planned_now(player.id)
                or self._melee_action_pending(candidate, self._player_melee_action(candidate, player))
                or self._melee_action_pending(candidate, self._player_touch_action(candidate, player)))):
            raise ArenaBrowserRequestError("The player already has an accepted Action resolving.")
        action = Action(candidate.universe, encounter.time, encounter.time + 1,
                        "touch", player.id, target.id, None)
        action.end_time = encounter.time + 1
        try:
            prepared = encounter.prepare_action(action)
        except (ValueError, TypeError, KeyError) as exc:
            raise ArenaBrowserRequestError(str(exc)) from exc
        return action, prepared

    def choose_touch(self, payload):
        if type(payload) is not dict or set(payload) != {"handle"}:
            raise ArenaBrowserRequestError("Touch requires one currently perceived Being handle")
        handle = payload["handle"]
        if type(handle) is not str:
            raise ArenaBrowserRequestError("Touch target handle must be text")
        with self._lock:
            if self._active is None:
                raise ArenaBrowserRequestError("Generate an Encounter before choosing Touch")
            candidate = self._active
            player = candidate.participants[0].native.being
            entity_id = next((key for key, value in self._view_handles.items()
                              if value == handle), None)
            ledger = object.__getattribute__(player, "__dict__").get("_arena_perception_ledger")
            if ledger is None or ledger.observer_id != player.id:
                raise ArenaBrowserRequestError("player perception evidence is unavailable")
            evidence = None if entity_id is None else next(
                (row for row in ledger.current if row.entity_id == entity_id), None)
            action, prepared = self._touch_preflight(
                candidate, player, entity_id, evidence, supported=True)
            try:
                candidate.encounter.schedule_action(action)
            except Exception as exc:
                raise ArenaBrowserRequestError(
                    "native Touch Choice was not accepted; Arena state is unchanged") from exc
            self._selected_entity_handle = handle
            self._trace.native_advance(None, None,
                f"action=touch opposed=true duration={prepared.end_time-prepared.start_time:g}s")
            return self._view_unlocked()

    def choose_multiple_touch(self, payload):
        """Declare an ordered, recurring two-Touch program from visible target handles."""
        from action_choice import ChoiceMember
        if (type(payload) is not dict or set(payload) != {"handle", "priorities"}
                or type(payload["handle"]) is not str or type(payload["priorities"]) is not list
                or len(payload["priorities"]) != 2
                or any(type(value) is not int for value in payload["priorities"])):
            raise ArenaBrowserRequestError("Multiple Touch requires a perceived Being handle and two priority values")
        if tuple(sorted(payload["priorities"])) not in ((0, 3), (1, 2)):
            raise ArenaBrowserRequestError("Two overlapping Actions need adopted priorities (0, 3) or (1, 2)")
        with self._lock:
            if self._active is None:
                raise ArenaBrowserRequestError("Generate an Encounter before declaring Multiple actions")
            candidate = self._active
            encounter = candidate.encounter
            player = candidate.participants[0].native.being
            if (player.get_skill_level("multi-action") or 0) <= 0:
                raise ArenaBrowserRequestError("Overlapping Actions require the player's acquired Multi-action skill")
            handle = payload["handle"]
            entity_id = next((key for key, value in self._view_handles.items() if value == handle), None)
            ledger = object.__getattribute__(player, "__dict__").get("_arena_perception_ledger")
            if ledger is None or ledger.observer_id != player.id:
                raise ArenaBrowserRequestError("Player-owned perception evidence is unavailable.")
            evidence = None if entity_id is None else next(
                (row for row in ledger.current if row.entity_id == entity_id), None)
            actions = []
            for _ in range(2):
                action, _prepared = self._touch_preflight(
                    candidate, player, entity_id, evidence, supported=True)
                actions.append(action)
            members = tuple(ChoiceMember(f"touch-{index + 1}", action,
                priority_penalty=payload["priorities"][index])
                for index, action in enumerate(actions))
            try:
                view = encounter.schedule_choice(members)
            except Exception as exc:
                raise ArenaBrowserRequestError(
                    "Native Multiple Touch Choice was not accepted; Arena state is unchanged") from exc
            self._selected_entity_handle = handle
            self._trace.native_advance(None, None,
                f"action=multiple_touch components=2 choice={view.state}")
            return self._view_unlocked()

    def choose_multiple_grapple_break(self, payload):
        """Declare the adopted initial Grapple + Break-hold combination."""
        from action_choice import ChoiceMember
        if (type(payload) is not dict or set(payload) != {"handle", "actions", "priorities"}
                or type(payload["handle"]) is not str
                or type(payload["actions"]) is not list
                or type(payload["priorities"]) is not list
                or len(payload["actions"]) != 2 or len(payload["priorities"]) != 2
                or any(type(value) is not str for value in payload["actions"])
                or tuple(sorted(payload["actions"])) != ("break hold", "grapple")
                or any(type(value) is not int for value in payload["priorities"])):
            raise ArenaBrowserRequestError(
                "Multiple Grapple + Break hold requires the observed target, both ordered Actions, and two priorities.")
        if tuple(sorted(payload["priorities"])) not in ((0, 3), (1, 2)):
            raise ArenaBrowserRequestError(
                "Two overlapping Actions need adopted priorities (0, 3) or (1, 2).")
        with self._lock:
            if self._active is None:
                raise ArenaBrowserRequestError("Generate an Encounter before declaring Multiple actions.")
            candidate = self._active
            encounter = candidate.encounter
            player = candidate.participants[0].native.being
            if (player.get_skill_level("multi-action") or 0) <= 0:
                raise ArenaBrowserRequestError("Overlapping Actions require the player's acquired Multi-action skill.")
            handle = payload["handle"]
            entity_id = next((key for key, value in self._view_handles.items() if value == handle), None)
            ledger = object.__getattribute__(player, "__dict__").get("_arena_perception_ledger")
            if ledger is None or ledger.observer_id != player.id:
                raise ArenaBrowserRequestError("Player-owned perception evidence is unavailable.")
            evidence = None if entity_id is None else next(
                (row for row in ledger.current if row.entity_id == entity_id), None)
            members = []
            for index, event_type in enumerate(payload["actions"]):
                action, _prepared = self._grappling_preflight(
                    candidate, player, entity_id, evidence, event_type)
                members.append(ChoiceMember(event_type, action,
                    priority_penalty=payload["priorities"][index]))
            try:
                view = encounter.schedule_choice(tuple(members))
            except Exception as exc:
                raise ArenaBrowserRequestError(
                    "Native Grapple + Break-hold Choice was not accepted; Arena state is unchanged.") from exc
            self._selected_entity_handle = handle
            self._trace.native_advance(None, None,
                f"action=multiple_grapple_break order={','.join(payload['actions'])} choice={view.state}")
            return self._view_unlocked()

    def choose_action_program(self, payload):
        """Submit an ordered, one-to-four member program using native Choice validation.

        Component selectors are intentionally limited to actions with complete Arena
        preflight contracts. The browser supplies observer-owned handles, never native
        entity identifiers. Start offsets and resource allocations remain explicit.
        """
        from action_choice import ChoiceMember
        from strategy import Strategy
        if (type(payload) is not dict or set(payload) != {"components"}
                or type(payload["components"]) is not list
                or not 1 <= len(payload["components"]) <= 4):
            raise ArenaBrowserRequestError("An Action program needs one to four ordered components.")
        allowed = {"kind", "handle", "action", "motion", "hand", "position", "unarmed",
                   "shield_handle",
                   "weapon_handle",
                   "body_region",
                   "projectile_handle",
                   "coup_de_grace",
                   "start_offset_seconds", "priority_penalty", "strategy"}
        normalized = []
        for component in payload["components"]:
            targetless = (type(component) is dict
                          and component.get("kind") in ("dodge-prepare", "delay"))
            if (type(component) is not dict or set(component) - allowed
                    or not {"kind"}.issubset(component)
                    or (not targetless and "handle" not in component)
                    or (targetless and component.get("handle") is not None)
                    or type(component["kind"]) is not str
                    or (not targetless and type(component["handle"]) is not str)
                    or type(component.get("start_offset_seconds", 0)) is not int
                    or component.get("start_offset_seconds", 0) < 0
                    or ("priority_penalty" in component
                        and type(component["priority_penalty"]) is not int)):
                raise ArenaBrowserRequestError("An Action program component has malformed selectors or timing.")
            strategy = component.get("strategy", {})
            if (type(strategy) is not dict
                    or set(strategy) - {"attack", "defense", "timing", "extra_damage"}
                    or any(type(value) is not int or value < 0 for value in strategy.values())):
                raise ArenaBrowserRequestError("Each component strategy uses nonnegative integer allocations.")
            if "unarmed" in component and type(component["unarmed"]) is not bool:
                raise ArenaBrowserRequestError("The Disarm mode selector must be boolean.")
            if ("coup_de_grace" in component
                    and type(component["coup_de_grace"]) is not bool):
                raise ArenaBrowserRequestError("The thrown Coup de grace selector must be boolean.")
            normalized.append(component)
        offsets = [component.get("start_offset_seconds", 0) for component in normalized]
        if offsets != sorted(offsets):
            raise ArenaBrowserRequestError("Component order must follow nondecreasing start offsets.")
        with self._lock:
            if self._active is None:
                raise ArenaBrowserRequestError("Generate an Encounter before declaring an Action program.")
            candidate = self._active
            encounter = candidate.encounter
            player = candidate.participants[0].native.being
            ledger = object.__getattribute__(player, "__dict__").get("_arena_perception_ledger")
            if ledger is None or ledger.observer_id != player.id:
                raise ArenaBrowserRequestError("Player-owned perception evidence is unavailable.")
            members = []
            selected_handles = []
            for index, component in enumerate(normalized):
                entity_id = (None if component["kind"] in ("dodge-prepare", "delay") else
                    next((key for key, value in self._view_handles.items()
                          if value == component["handle"]), None))
                evidence = None if entity_id is None else next(
                    (row for row in ledger.current if row.entity_id == entity_id), None)
                kind = component["kind"]
                motion = component.get("motion")
                if kind == "stun" or kind == "subdue":
                    from activities import declare_stun, declare_subdue
                    if evidence is None or evidence.category != "being" or evidence.present_state != "present":
                        raise ArenaBrowserRequestError("Stun/Subdue requires a currently perceived present Being target.")
                    if kind == "stun":
                        action = declare_stun(candidate.universe, encounter, player.id,
                            entity_id, region=component.get("body_region"),
                            motion=motion, strategy=Strategy(**component.get("strategy", {})))
                    else:
                        weapon_id = next((key for key,value in self._view_handles.items()
                                          if value == component.get("weapon_handle")), None)
                        action = declare_subdue(candidate.universe, encounter, player.id,
                            entity_id, weapon_id, motion=motion,
                            strategy=Strategy(**component.get("strategy", {})))
                elif kind == "touch":
                    action, _ = self._touch_preflight(candidate, player, entity_id,
                        evidence, allow_composition=True)
                elif kind == "melee" and motion in ("swing", "thrust"):
                    action, _, _, _, _ = self._melee_strike_preflight(
                        candidate, player, entity_id, evidence, motion)
                elif kind == "charge" and motion in ("swing", "thrust"):
                    action, _, _, _, _ = self._melee_strike_preflight(
                        candidate, player, entity_id, evidence, motion, charge=True)
                elif kind == "feint" and motion in ("swing", "thrust"):
                    action, _ = self._feint_preflight(
                        candidate, player, entity_id, evidence, motion)
                elif kind == "disarm" and motion in ("swing", "thrust"):
                    action, _, _ = self._disarm_preflight(candidate, player,
                        entity_id, evidence, motion, component.get("unarmed", False))
                elif kind == "object-strike" and motion in ("swing", "thrust"):
                    action, _, _, _ = self._object_strike_preflight(
                        candidate, player, entity_id, evidence, motion)
                elif kind == "coup-de-grace" and motion in ("swing", "thrust"):
                    action, _ = self._coup_de_grace_preflight(
                        candidate, player, entity_id, evidence, motion)
                elif kind == "break-weapon":
                    action, _, _ = self._break_weapon_preflight(
                        candidate, player, entity_id, evidence)
                elif kind == "pickup":
                    from activities import PickUpAction
                    self._pickup_target_unlocked(candidate, player, entity_id, evidence)
                    action = PickUpAction(encounter, player.id, entity_id,
                        encounter.time, map_width_cells=candidate.arena_map.width_cells,
                        map_height_cells=candidate.arena_map.height_cells)
                elif kind == "throw" and type(component.get("projectile_handle")) is str:
                    action, _prepared, _projectile_id = self._throw_preflight(
                        candidate, player, entity_id, evidence,
                        component["projectile_handle"],
                        coup_de_grace=component.get("coup_de_grace", False))
                elif kind == "deflect":
                    raise ArenaBrowserRequestError(
                        "Deflect is unavailable: this observer has no committed evidence of awareness "
                        "throughout the missile's entire trajectory, and the redirected Missing destination is unresolved.")
                elif kind == "shoot":
                    raise ArenaBrowserRequestError(
                        "Shoot is unavailable: adopted bow data do not define arrow velocity/flight time "
                        "or a native ammunition release profile.")
                elif kind == "ready-weapon":
                    from activities import ReadyWeaponAction
                    if evidence is None or evidence.category not in ("object", "weapon"):
                        raise ArenaBrowserRequestError("Ready weapon needs a currently perceived carried Weapon.")
                    hand = component.get("hand")
                    action = ReadyWeaponAction(encounter, player.id, entity_id,
                        hand, encounter.time)
                elif kind == "ready-preparation" and motion in ("swing", "thrust", "set pole"):
                    from activities import ReadyPreparationAction
                    options, reason = self._ready_preparation_options_unlocked(
                        candidate, player, entity_id, evidence)
                    if not any(row["motion"] == motion for row in options):
                        raise ArenaBrowserRequestError(reason)
                    action = ReadyPreparationAction(encounter, player.id,
                        entity_id, motion, encounter.time)
                elif kind == "delay":
                    from activities import DelayAction
                    action = DelayAction(encounter, player.id,
                        component.get("strategy", {}).get("defense", 0),
                        encounter.time)
                elif kind == "dodge":
                    action, _, _ = self._player_dodge_preflight(candidate, player,
                        entity_id, evidence, allow_composition=True)
                elif kind == "dodge-prepare":
                    strategy = component.get("strategy", {})
                    pool = MeleeDefense.dodge_strategy_pool(player, candidate.universe)
                    if strategy.get("defense", 0) + strategy.get("timing", 0) != pool:
                        raise ArenaBrowserRequestError(
                            f"Dodge preparation must allocate its current {pool}-point pool between defense and timing.")
                    action = MeleeDefense(encounter, player.id, kind="dodge",
                        strategy=Strategy(defense=strategy.get("defense", 0),
                                           timing=strategy.get("timing", 0)))
                elif kind == "block":
                    shield_id = next((key for key, value in self._view_handles.items()
                                      if value == component.get("shield_handle")), None)
                    action, _, _ = self._player_block_preflight(candidate, player,
                        entity_id, evidence, shield_id)
                elif kind == "parry":
                    attacker = encounter.get_being(entity_id) if type(entity_id) is str else None
                    weapon_id = next((key for key, value in self._view_handles.items()
                                      if value == component.get("weapon_handle")), None)
                    source = (None if weapon_id is None else
                              self._retained_defense(candidate, player, "parry", weapon_id))
                    strike = self._visible_incoming_strike(candidate, player, attacker, ledger)
                    if attacker is None or source is None or strike is None:
                        raise ArenaBrowserRequestError("Parry needs a retained weapon preparation and observed incoming strike.")
                    action = MeleeDefense(encounter, player.id, attacker.id,
                        kind="parry", target_action_id=strike.id,
                        prepared_defense_action_id=source.id, weapon_id=weapon_id,
                        parry_motion=component.get("motion"))
                    encounter.prepare_action(action)
                elif kind == "yield":
                    action, _, _ = self._player_yield_preflight(candidate, player,
                        entity_id, evidence)
                elif kind == "contact" and component.get("action") in (
                        "break hold", "release grip", "grapple", "grapple escape",
                        "takedown", "reverse", "pin", "trip", "grab", "bull rush", "overrun"):
                    action, _ = self._grappling_preflight(candidate, player,
                        entity_id, evidence, component["action"],
                        component.get("hand"), component.get("position"),
                        allow_composition=True)
                elif kind == "object-contact" and component.get("action") in ("grab object", "wrest"):
                    action, _ = self._object_grappling_preflight(candidate, player,
                        entity_id, evidence, component["action"], component.get("hand"))
                else:
                    raise ArenaBrowserRequestError(
                        f"Component {index + 1} is not a supported native Arena Action selector.")
                offset = component.get("start_offset_seconds", 0)
                action.start_time += offset
                action.end_time += offset
                effort = component.get("strategy", {})
                action.strategy = Strategy(*(effort.get(key, 0) for key in
                    ("attack", "defense", "timing", "extra_damage")))
                if effort.get("timing", 0) and action.event_type not in ("ready object", "delay"):
                    # Apply the same native timing reduction as the corresponding
                    # single Action preflight, with a one-second floor.
                    adjustment = action.strategy.timing_adjustment()
                    event_type = action.event_type
                    if event_type == "touch":
                        pass  # Touch's adopted duration is fixed at one second.
                    elif event_type == "feint":
                        from weapon import WeaponInstance
                        weapon = candidate.universe.get_object_by_id(action.instrument_id)
                        native = weapon.St() if action.feint_motion == "swing" else weapon.Tt()
                        action.end_time = action.start_time + max(1, math.ceil(native / 2) - adjustment)
                    elif event_type in ("swing", "thrust", "strike object", "disarm",
                                        "coup de grace", "break weapon"):
                        instrument = candidate.universe.get_object_by_id(action.instrument_id)
                        if event_type == "disarm" and action.instrument_id is None:
                            base = 4 if action.disarm_motion == "swing" else 3
                        else:
                            motion_name = (getattr(action, "object_motion", None)
                                or getattr(action, "disarm_motion", None)
                                or getattr(action, "coup_motion", None)
                                or getattr(action, "break_motion", None)
                                or motion)
                            base = instrument.St() if motion_name == "swing" else instrument.Tt()
                        action.end_time = action.start_time + max(1, base - adjustment)
                key = f"component-{index + 1}"
                members.append(ChoiceMember(key, action,
                    priority_penalty=component.get("priority_penalty")))
                selected_handles.append(component.get("handle"))
            try:
                view = encounter.schedule_choice(tuple(members))
            except Exception as exc:
                raise ArenaBrowserRequestError(
                    f"Native Action program rejected the complete declaration; no component was scheduled: {exc}") from exc
            if selected_handles[0] is not None:
                self._selected_entity_handle = selected_handles[0]
            self._trace.native_advance(None, None,
                f"action=general_program components={len(members)} state={view.state}")
            return self._view_unlocked()

    def cancel_multiple_action(self, payload):
        """Stop the player's own declared Multiple-action program without exposing IDs."""
        if payload != {}:
            raise ArenaBrowserRequestError("Multiple-action cancellation accepts an empty request.")
        with self._lock:
            if self._active is None:
                raise ArenaBrowserRequestError("Generate an Encounter before cancelling Multiple actions.")
            candidate = self._active
            encounter = candidate.encounter
            player_id = candidate.participants[0].native.being.id
            book = encounter._choice_book
            records = [record for record in book._choices.values()
                if record.view.state in ("accepted", "executing")
                and len(record.members) > 1
                and any(member.action.actor_id == player_id
                        for member in record.members)]
            if len(records) != 1:
                raise ArenaBrowserRequestError("There is no single active player Action program to cancel.")
            record = records[0]
            try:
                if record.view.state == "accepted":
                    book.undo(record.view.id)
                elif any(member.priority_penalty is not None for member in record.members):
                    book.abort_multiple_action(record.view.id)
                else:
                    for action_id in tuple(record.view.action_ids):
                        if action_id in encounter.pending_action_list:
                            encounter._cancel_action(action_id, reason="program_cancelled",
                                _abort_program=False)
            except (ValueError, RuntimeError) as exc:
                raise ArenaBrowserRequestError("Native Action-program cancellation was refused.") from exc
            return self._view_unlocked()

    def _grappling_preflight(self, candidate, player, entity_id, evidence,
                             event_type, hand=None, position=None, exit_cell=None,
                             allow_composition=False):
        """Prepare one supported physical-contact Action from player evidence."""
        from physical_contact import active_contact_state, successful_touch
        encounter = candidate.encounter
        target = encounter.get_being(entity_id) if type(entity_id) is str else None
        if (evidence is None or evidence.category != "being"
                or evidence.present_state != "present" or target is None
                or target.id == player.id or not encounter.is_aware(player.id, target.id)):
            raise ArenaBrowserRequestError("Select a currently perceived opposing Being.")
        if not encounter.initiated or encounter.progression_mode != "transactional":
            raise ArenaBrowserRequestError("Activate the native Encounter before physical-contact Actions.")
        if not _has_native_transactional_action_contract(Action):
            raise ArenaBrowserRequestError("The native transactional Action contract is unavailable.")
        if event_type == "end-run":
            from activities import end_run_action
            from arena_hex_map import HexAddress
            layout = candidate.arena_map.layout
            if (type(exit_cell) is not tuple or len(exit_cell) != 2
                    or any(type(value) is not int or value < 0 for value in exit_cell)):
                raise ArenaBrowserRequestError("Choose a represented exit hex beyond the selected Being.")
            try:
                destination = layout.center_position(HexAddress(*exit_cell))
            except (TypeError, ValueError) as exc:
                raise ArenaBrowserRequestError("End Run exit hex is outside the Arena map.") from exc
            if encounter._choice_book.actor_planned_now(player.id):
                raise ArenaBrowserRequestError("The player already has an accepted Action resolving.")
            premise = candidate.world_premise
            action = end_run_action(encounter, player.id, target.id, destination,
                terrain_multiplier=premise.terrain_multiplier,
                hampered_multiplier=premise.hampered_multiplier,
                direction="forward", rate="run", occupant_willing=False)
            try:
                prepared = encounter.prepare_action(action)
                from movement_intent import (MovementIntent, MovementRateConditions,
                    prepare_movement_intent, validate_end_run_path, _movement_hexes)
                from action_evaluation import capture_snapshot
                snapshot = capture_snapshot(encounter,
                    encounter.last_processed_boundary+1,_decision_preflight=True)
                row = prepare_movement_intent(encounter,
                    MovementIntent(player.id,destination,"run",action.id,
                        encounter.last_processed_boundary+1,"turn",None),
                    MovementRateConditions(premise.terrain_multiplier,
                        premise.hampered_multiplier,None,"forward",False),
                    pre_action_snapshot=snapshot)
                if row.arrival_time_seconds is None or row.arrival_time_seconds > 1:
                    raise ArenaBrowserRequestError("Selected exit is farther than one second of the chosen ordinary movement rate.")
                target_cell = candidate.arena_map.layout.cell_at_position(target.get_position())
                route_cells = _movement_hexes(row.start_position,destination,
                                               candidate.arena_map.layout)
                if target_cell not in route_cells:
                    raise ArenaBrowserRequestError("Selected route does not pass through the occupied Being hex.")
                validate_end_run_path(player.id,target.id,row.start_position,
                    destination,snapshot)
            except ArenaBrowserRequestError:
                raise
            except (ValueError,TypeError,KeyError) as exc:
                raise ArenaBrowserRequestError(str(exc)) from exc
            return action,prepared
        grips, controls = active_contact_state(encounter)
        action_data = {}
        duration = 3 if event_type == "end-run" else 4 if event_type == "overrun" else 1
        if event_type in ("overrun", "bull rush"):
            # Native preparation validates positions, sizes, timing and facing
            # without the browser choosing contest outcomes.
            if event_type in ("bull rush", "overrun"):
                from melee_combat import MeleeStrike
                from action_evaluation import ActionProposal
                source = None
                for action_id in reversed(encounter.finished_action_list):
                    prior = candidate.universe.get_event_by_id(action_id)
                    if (prior is None or prior.actor_id != player.id
                            or prior.target_id != target.id or prior.end_time != encounter.time
                            or type(prior.resolution) is not ActionProposal):
                        continue
                    if (type(prior) is MeleeStrike and prior.charge
                            and prior.resolution.outcome in ("normal", "critical")):
                        source = prior
                        break
                    if (event_type == "overrun" and type(prior) is Action
                            and prior.event_type == "bull rush"
                            and prior.resolution.outcome in ("success", "success_pending_displacement")):
                        source = prior
                        break
                if source is not None:
                    action_data["charge_continuation_source_id"] = source.id
        elif event_type == "grab":
            touch = self._player_touch_action(candidate, player)
            if (touch is None or touch.target_id != target.id
                    or not successful_touch(encounter, touch.id, player.id, target.id)):
                raise ArenaBrowserRequestError("Grab requires this player's committed successful Touch of the selected Being.")
            slots = object.__getattribute__(player, "__dict__").get("current")
            body_parts = getattr(slots, "body_parts", {}) if slots is not None else {}
            occupied = {row[3] for row in grips if row[1] == player.id}
            from physical_contact import active_object_grip_state
            occupied.update(row[4] for row in active_object_grip_state(encounter)
                            if row[2] == player.id)
            free_hands = [name for name in ("left hand", "right hand")
                          if name in body_parts and not body_parts[name] and name not in occupied]
            if hand not in free_hands:
                raise ArenaBrowserRequestError("Choose an explicitly represented free native hand.")
            action_data.update(grab_hand=hand, touch_action_id=touch.id)
        elif event_type == "hold":
            raise ArenaBrowserRequestError(
                "This Grip's six-second maintenance check resolves automatically; it is not a declared Action.")
        elif event_type == "break hold":
            matching = [row for row in grips if row[1] == target.id and row[2] == player.id]
            if len(matching) != 1:
                raise ArenaBrowserRequestError("Break hold requires exactly one identified physical grip on the player from this Being.")
            action_data["grip_id"] = matching[0][0]
        elif event_type == "release grip":
            matching = [row for row in grips if row[1] == player.id
                        and row[2] == target.id and (hand is None or row[3] == hand)]
            if len(matching) != 1:
                raise ArenaBrowserRequestError("Choose exactly one of your identified physical Grips on this Being.")
            action_data["grip_id"] = matching[0][0]
        elif event_type == "grapple":
            matching = [row for row in grips if row[1] == player.id and row[2] == target.id]
            if len(matching) != 1:
                raise ArenaBrowserRequestError("Grapple requires one established physical Grip on the selected Being.")
            if any(row[2] == target.id for row in controls):
                raise ArenaBrowserRequestError("This Being is already under an established Grapple control.")
            if matching[0][5] != encounter.time + 6:
                raise ArenaBrowserRequestError("Initial Grapple resolves at the prerequisite Grip's next six-second check.")
            action_data["grip_id"] = matching[0][0]
            duration = 6
        elif event_type == "grapple escape":
            matching = [row for row in controls if row[1] == target.id and row[2] == player.id]
            if len(matching) != 1:
                raise ArenaBrowserRequestError("Grapple Escape requires one established Grapple control by this Being.")
            if matching[0][5] != encounter.time + 6:
                raise ArenaBrowserRequestError("Grapple Escape resolves at the established control's next six-second check.")
            action_data["grapple_id"] = matching[0][0]
            duration = 6
        elif event_type in ("takedown", "reverse", "pin"):
            matching = [row for row in controls if row[1] == player.id
                        and row[2] == target.id and row[5] == encounter.time + 6]
            if len(matching) != 1:
                raise ArenaBrowserRequestError("A position transition requires your established Grapple at its next native check.")
            action_data["grapple_id"] = matching[0][0]
            if event_type in ("takedown", "pin"):
                allowed = ("kneeling", "prone") if event_type == "takedown" else ("pin_top", "pin_bottom")
                if position not in allowed:
                    raise ArenaBrowserRequestError("Choose one adopted Takedown or Pin position.")
                action_data["grapple_position"] = position
            duration = 6
        elif event_type == "trip":
            order = ("diminutive", "tiny", "small", "medium", "large", "huge", "gargantuan", "colossal")
            if (getattr(player, "size_category", None) not in order
                    or getattr(target, "size_category", None) not in order):
                raise ArenaBrowserRequestError(
                    "Trip requires explicitly represented size categories for both Beings.")
            source = self._player_trip_contact_action(candidate,player,target)
            if source is None:
                raise ArenaBrowserRequestError("Trip requires your committed successful Touch, Grab, or Swing/Thrust Strike against this Being.")
            if position not in ("STR", "DEX"):
                raise ArenaBrowserRequestError("Choose the defender's Strength or Dexterity Trip defense.")
            action_data.update(trip_source_action_id=source.id, trip_defender_ability=position)
            duration = 2
        else:
            raise ArenaBrowserRequestError("Unsupported native physical-contact Action.")
        if (not allow_composition and (encounter._choice_book.actor_planned_now(player.id)
                or any(getattr(candidate.universe.get_event_by_id(action_id), "actor_id", None) == player.id
                       and getattr(candidate.universe.get_event_by_id(action_id), "event_type", None) != "hold"
                       for action_id in encounter.pending_action_list)
                or self._melee_action_pending(candidate, self._player_melee_action(candidate, player))
                or self._melee_action_pending(candidate, self._player_touch_action(candidate, player)))):
            raise ArenaBrowserRequestError("The player already has an accepted Action resolving.")
        action = Action(candidate.universe, encounter.time, encounter.time + duration,
                        event_type, player.id, target.id, None)
        for name, value in action_data.items():
            setattr(action, name, value)
        action.end_time = encounter.time + duration
        try:
            prepared = encounter.prepare_action(action)
        except (ValueError, TypeError, KeyError) as exc:
            raise ArenaBrowserRequestError(str(exc)) from exc
        return action, prepared

    def _object_grappling_preflight(self,candidate,player,object_id,evidence,event_type,hand=None):
        from weapon import WeaponInstance
        from physical_contact import active_object_grip_state
        encounter=candidate.encounter
        obj=candidate.universe.get_object_by_id(object_id) if type(object_id) is str else None
        if (evidence is None or evidence.category!='object' or evidence.present_state!='carried'
                or evidence.owner_id is None or evidence.equipment_status not in
                ('held in left hand','held in right hand') or type(obj) is not WeaponInstance):
            raise ArenaBrowserRequestError('Select a currently perceived weapon held by an opposing Being.')
        holder=encounter.get_being(evidence.owner_id)
        holder_hand=evidence.equipment_status.removeprefix('held in ')
        if (holder is None or holder.id==player.id or not encounter.is_aware(player.id,holder.id)
                or obj.parent_container_id!=holder.id
                or holder.current.body_parts.get(holder_hand)!=obj.id):
            raise ArenaBrowserRequestError('The selected Object is no longer held by the perceived opponent.')
        if event_type=='grab object':
            hand=hand or next((name for name in ('left hand','right hand')
                if name in player.current.body_parts and player.current.body_parts[name] is None),None)
            if hand not in ('left hand','right hand') or player.current.body_parts.get(hand,'missing') is not None:
                raise ArenaBrowserRequestError('Choose an explicitly represented free receiving hand.')
            if any(row[0]==obj.id for row in active_object_grip_state(encounter)):
                raise ArenaBrowserRequestError('This Object already has an established Object Grip.')
        else:
            grip=next((row for row in active_object_grip_state(encounter)
                if row[0]==obj.id and row[2]==player.id and row[3]==holder.id),None)
            if grip is None:
                raise ArenaBrowserRequestError('Wrest requires your current receipt-backed Object Grip.')
            hand=grip[4]
        if encounter._choice_book.actor_planned_now(player.id):
            raise ArenaBrowserRequestError('The player already has an accepted Action resolving.')
        if player.get_position() is None or holder.get_position() is None:
            raise ArenaBrowserRequestError('Object Grip requires positioned participants.')
        from melee_combat import reference_arm_length_inches
        reach=reference_arm_length_inches(height_inches=player.current.height,
            length_inches=player.current.length,size_category=getattr(player,'size_category',None))*0.0254
        from action_calculations import melee_hex_occupancy_path_status
        status,_=melee_hex_occupancy_path_status(player.get_position(),holder.get_position(),reach,
            encounter.physical_path(player.id,holder.id),candidate.arena_map.layout)
        if status!='in_reach':raise ArenaBrowserRequestError('The holder is outside your native arm reach or the physical path is blocked/uncertain.')
        action=Action(candidate.universe,encounter.time,encounter.time+1,event_type,
            player.id,obj.id,None)
        action.holder_id=holder.id;action.holder_hand=holder_hand;action.grab_hand=hand
        if event_type=='wrest':action.object_grip_id=grip[1]
        try:prepared=encounter.prepare_action(action)
        except (ValueError,TypeError,KeyError) as exc:
            raise ArenaBrowserRequestError(str(exc)) from exc
        return action,prepared

    def choose_grappling(self, payload):
        if (type(payload) is not dict or set(payload) - {"handle", "action", "hand", "position", "exit_cell"}
                or not {"handle", "action"}.issubset(payload)
                or type(payload.get("handle")) is not str
                or payload.get("action") not in ("grab", "grab object", "wrest", "hold", "break hold", "release grip", "grapple", "grapple escape", "takedown", "reverse", "pin", "trip", "bull rush", "overrun", "end-run")
                or ("position" in payload and payload["position"] not in ("kneeling","prone","pin_top","pin_bottom","STR","DEX"))
                or ("hand" in payload and payload["hand"] not in ("left hand", "right hand"))
                or ("exit_cell" in payload and (type(payload["exit_cell"]) is not dict
                    or set(payload["exit_cell"]) != {"column","row"}
                    or any(type(payload["exit_cell"][key]) is not int or payload["exit_cell"][key] < 0
                           for key in ("column","row"))))
                or (payload.get("action") == "end-run") != ("exit_cell" in payload)):
            raise ArenaBrowserRequestError("Physical-contact Action request is malformed.")
        with self._lock:
            if self._active is None:
                raise ArenaBrowserRequestError("Generate an Encounter before choosing a physical-contact Action.")
            candidate = self._active
            player = candidate.participants[0].native.being
            entity_id = next((key for key, value in self._view_handles.items()
                              if value == payload["handle"]), None)
            ledger = object.__getattribute__(player, "__dict__").get("_arena_perception_ledger")
            if ledger is None or ledger.observer_id != player.id:
                raise ArenaBrowserRequestError("Player-owned perception evidence is unavailable.")
            evidence = None if entity_id is None else next(
                (row for row in ledger.current if row.entity_id == entity_id), None)
            if payload['action'] in ('grab object','wrest'):
                action,prepared=self._object_grappling_preflight(candidate,player,entity_id,evidence,
                    payload['action'],payload.get('hand'))
            else:
                action, prepared = self._grappling_preflight(
                    candidate, player, entity_id, evidence, payload["action"], payload.get("hand"), payload.get("position"),
                    None if "exit_cell" not in payload else
                        (payload["exit_cell"]["column"],payload["exit_cell"]["row"]))
            try:
                candidate.encounter.schedule_action(action)
            except Exception as exc:
                raise ArenaBrowserRequestError(
                    "Native physical-contact Choice refused; Arena state is unchanged.") from exc
            self._selected_entity_handle = payload["handle"]
            self._trace.native_advance(None, None,
                f"action={payload['action']} duration={prepared.end_time-prepared.start_time:g}s")
            return self._view_unlocked()

    def cancel_pending_contact(self, payload):
        """Let the player withdraw their own one-member contact Action."""
        if payload != {}:
            raise ArenaBrowserRequestError("Contact cancellation accepts an empty request.")
        contact_types = {"touch", "grab", "grab object", "wrest", "break hold",
                         "release grip", "grapple", "grapple escape", "takedown",
                         "reverse", "pin", "trip", "bull rush", "overrun", "end-run"}
        with self._lock:
            if self._active is None:
                raise ArenaBrowserRequestError("Generate an Encounter before cancelling an Action.")
            candidate = self._active
            encounter = candidate.encounter
            player = candidate.participants[0].native.being
            choices = encounter._choice_book._choices
            rows = []
            for choice in choices.values():
                if choice.view.state not in ("accepted", "executing"):
                    continue
                for member in choice.members:
                    action = member.action
                    if (type(action) is Action and action.actor_id == player.id
                            and action.event_type in contact_types):
                        rows.append((action, choice))
            action, choice = max(rows, key=lambda row: (row[0].start_time,
                              row[0].end_time, row[0].id), default=(None, None))
            if action is None:
                raise ArenaBrowserRequestError("You have no pending contact Action to cancel.")
            if len(choice.members) != 1:
                raise ArenaBrowserRequestError(
                    "This contact Action belongs to a multi-Action Choice and cannot be cancelled alone.")
            try:
                if action.id in encounter.pending_action_list:
                    encounter.cancel_action(action.id, reason="player_withdrawal")
                elif choice.view.state == "accepted":
                    encounter._choice_book.undo(choice.view.id)
                else:
                    raise ArenaBrowserRequestError(
                        "The contact Action has already started resolving and cannot be withdrawn.")
            except (ValueError, RuntimeError) as exc:
                if isinstance(exc, ArenaBrowserRequestError):
                    raise
                raise ArenaBrowserRequestError(
                    "The contact Action could not be withdrawn; Encounter state is unchanged.") from exc
            self._trace.native_advance(None, None,
                f"action={action.event_type} player_withdrawal=true")
            return self._view_unlocked()

    def _melee_strike_preflight(self, candidate, player, entity_id, evidence, motion,
                                supported=True, charge=False, weapon_id=None,
                                two_handed=False, shield_bash=False):
        if motion not in ("swing", "thrust"):
            raise ArenaBrowserRequestError("Choose the native weapon Swing or Thrust motion.")
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
        weapon_id = (self._initial_ready_weapon_id(candidate, player)
                     if weapon_id is None else weapon_id)
        from weapon import WeaponInstance
        weapon = candidate.universe.get_object_by_id(weapon_id) if type(weapon_id) is str else None
        shield_names = set(candidate.universe.library.weapon_dictionary
                           .get_objects_in_category("Shields"))
        equipped_shield_ids = set(player.shielded_with(candidate.universe).values())
        if (type(weapon) is not WeaponInstance or weapon.id not in player.weapons
                or (weapon.id not in equipped_shield_ids if shield_bash else
                    weapon.id not in player.armed_with(candidate.universe).values())
                or weapon.parent_container_id != player.id or weapon.get_position() is not None
                or (weapon.current.obj_type in shield_names) != shield_bash):
            raise ArenaBrowserRequestError(
                "The selected native weapon or shield is not currently held for the requested attack.")
        if motion not in weapon.get_melee_types():
            raise ArenaBrowserRequestError(f"The native {weapon.current.obj_type} does not support {motion}.")
        reach = effective_melee_reach_meters(player.current, weapon.current)
        feint_source = self._available_feint_source(candidate, player, target.id)
        action = MeleeStrike(encounter, player.id, target.id, weapon.id,
                             motion=motion, reach=reach,
                             feint_source_action_id=feint_source, charge=charge,
                             two_handed=two_handed, shield_bash=shield_bash)
        try:
            prepared = encounter.prepare_action(action)
        except Exception as exc:
            raise ArenaBrowserRequestError(
                f"Native {motion} Choice is unavailable under the current Encounter state.") from exc
        distance = encounter.distance_between_beings(player.id, target.id)
        return action, weapon, prepared, distance, reach

    def _object_strike_preflight(self, candidate, player, entity_id, evidence, motion,
                                 supported=True, weapon_id=None):
        if motion not in ('swing', 'thrust'):
            raise ArenaBrowserRequestError('Choose the native Swing or Thrust motion.')
        if not supported or not _has_native_transactional_action_contract(Action):
            raise ArenaBrowserRequestError('The native Object-strike scheduler or resolver is unavailable.')
        if evidence is None or evidence.category not in ('object','weapon','armor') or evidence.present_state not in ('ground','present'):
            raise ArenaBrowserRequestError('Select a currently perceived Object first.')
        encounter = candidate.encounter
        target = candidate.universe.get_object_by_id(entity_id) if type(entity_id) is str else None
        from object import ObjectInstance
        from weapon import WeaponInstance
        from armor import ArmorInstance
        if type(target) not in (ObjectInstance, WeaponInstance, ArmorInstance) or not encounter.is_aware(player.id, target.id):
            raise ArenaBrowserRequestError('The selected target is not an observer-authorized native Object.')
        if target.parent_container_id is not None:
            raise ArenaBrowserRequestError('This first native branch supports unattended ground Objects only.')
        if type(target.current.hardness) not in (int,float) or target.current.hardness < 0 or target.current.hit_points <= 0:
            raise ArenaBrowserRequestError('The Object has no supported material hardness and positive hit points.')
        if not encounter.initiated or encounter.progression_mode != 'transactional':
            raise ArenaBrowserRequestError('Activate the native Encounter before striking an Object.')
        weapon_id = (self._initial_ready_weapon_id(candidate, player)
                     if weapon_id is None else weapon_id)
        weapon = candidate.universe.get_object_by_id(weapon_id) if type(weapon_id) is str else None
        from weapon import WeaponInstance
        if (type(weapon) is not WeaponInstance or weapon.current.hit_points <= 0
                or weapon.id not in player.armed_with(candidate.universe).values()
                or weapon.parent_container_id != player.id or weapon.get_position() is not None):
            raise ArenaBrowserRequestError('Strike an Object requires a usable, actually held Weapon.')
        if motion not in weapon.get_melee_types():
            raise ArenaBrowserRequestError(f'The native {weapon.current.obj_type} does not support {motion}.')
        from melee_combat import effective_melee_reach_meters
        reach = effective_melee_reach_meters(player.current, weapon.current)
        action = Action(candidate.universe, encounter.time, encounter.time + 1,
                        'strike object', player.id, target.id, weapon.id)
        action.object_motion = motion
        action.reach = reach
        native_timing = weapon.St() if motion == 'swing' else weapon.Tt()
        action.end_time = encounter.time + max(1, native_timing - action.strategy.timing_adjustment())
        try:
            prepared = encounter.prepare_action(action)
        except Exception as exc:
            raise ArenaBrowserRequestError('Native Strike an object Choice is unavailable.') from exc
        distance = (None if player.get_position() is None or target.get_position() is None
                    else math.dist(player.get_position().as_tuple(),target.get_position().as_tuple()))
        return action, prepared, distance, reach

    def choose_object_strike(self, payload):
        if (type(payload) is not dict or set(payload) not in
                (frozenset({'handle','motion'}), frozenset({'handle','motion','weapon_handle'}))):
            raise ArenaBrowserRequestError('Strike an object requires a perceived target handle, motion, and optional held Weapon handle.')
        handle, motion = payload['handle'], payload['motion']
        with self._lock:
            if self._active is None:
                raise ArenaBrowserRequestError('Generate an Encounter before striking an Object.')
            candidate = self._active
            player = candidate.participants[0].native.being
            entity_id = next((key for key,value in self._view_handles.items() if value == handle), None)
            ledger = object.__getattribute__(player,'__dict__').get('_arena_perception_ledger')
            if ledger is None or ledger.observer_id != player.id:
                raise ArenaBrowserRequestError('Player perception evidence is unavailable.')
            evidence = None if entity_id is None else next((row for row in ledger.current if row.entity_id == entity_id),None)
            weapon_id = (None if 'weapon_handle' not in payload else next(
                (key for key, value in self._view_handles.items()
                 if value == payload['weapon_handle']), None))
            if 'weapon_handle' in payload and weapon_id is None:
                raise ArenaBrowserRequestError('Selected Weapon handle is not in current observer evidence.')
            action, prepared, distance, reach = self._object_strike_preflight(
                candidate,player,entity_id,evidence,motion,weapon_id=weapon_id)
            try:
                candidate.encounter.schedule_action(action)
            except Exception as exc:
                raise ArenaBrowserRequestError('Native Strike an object Choice was refused; Arena state is unchanged.') from exc
            self._selected_entity_handle = handle
            self._trace.native_advance(None,None,
                f'action=strike_object motion={motion} duration={prepared.end_time-prepared.start_time:g}s')
            return self._view_unlocked()

    def _disarm_preflight(self,candidate,player,entity_id,evidence,motion,unarmed=False,take_hand=None):
        if motion not in ('swing','thrust') or evidence is None or evidence.category!='object' or evidence.present_state!='carried':
            raise ArenaBrowserRequestError('Select a perceived weapon held by the opposing Being.')
        owner_id=evidence.owner_id
        encounter=candidate.encounter
        defender=encounter.get_being(owner_id) if type(owner_id) is str else None
        weapon=candidate.universe.get_object_by_id(entity_id) if type(entity_id) is str else None
        from weapon import WeaponInstance
        if (defender is None or defender is player or type(weapon) is not WeaponInstance
                or weapon.id not in defender.armed_with(candidate.universe).values()):
            raise ArenaBrowserRequestError('The selected Object is not an opposing Being\'s currently held weapon.')
        if not encounter.initiated or encounter.progression_mode!='transactional':
            raise ArenaBrowserRequestError('Activate the native Encounter before Disarm.')
        if unarmed:
            if (player.current.skills.get_skill_level('unarmed combat') or 0)<=0:
                raise ArenaBrowserRequestError('Unarmed Disarm requires Unarmed combat skill.')
            if not any(hand in ('left hand','right hand') and value is None
                       for hand,value in player.current.body_parts.items()):
                raise ArenaBrowserRequestError('Unarmed Disarm requires an available arm.')
            if (take_hand is not None and (take_hand not in ('left hand','right hand')
                    or player.current.body_parts.get(take_hand) is not None)):
                raise ArenaBrowserRequestError('Selected Disarm take hand is not currently available.')
            from melee_combat import reference_arm_length_inches,INCHES_TO_METERS
            reach=reference_arm_length_inches(height_inches=player.current.height,
                length_inches=player.current.length,size_category=getattr(player,'size_category',None))*INCHES_TO_METERS
            timing={'swing':4,'thrust':3}[motion]
            instrument_id=None
        else:
            attacking_id=self._initial_ready_dagger_id(candidate,player)
            attacking=candidate.universe.get_object_by_id(attacking_id) if type(attacking_id) is str else None
            if (type(attacking) is not WeaponInstance or attacking.current.hit_points<=0
                    or attacking.id not in player.armed_with(candidate.universe).values()):
                raise ArenaBrowserRequestError('Disarm requires a usable weapon actually held by the player.')
            if (player.current.skills.weapon_skills.get(attacking.original.obj_type,0)<=1
                    or motion not in attacking.get_melee_types()):
                raise ArenaBrowserRequestError('Armed Disarm requires advanced native skill and a supported motion.')
            from melee_combat import effective_melee_reach_meters
            reach=effective_melee_reach_meters(player.current,attacking.current)
            timing=attacking.St() if motion=='swing' else attacking.Tt()
            instrument_id=attacking.id
        action=Action(candidate.universe,encounter.time,encounter.time+1,'disarm',player.id,defender.id,instrument_id)
        action.disarm_weapon_id=weapon.id;action.disarm_motion=motion
        if unarmed and take_hand is not None: action.disarm_hand=take_hand
        action.reach=reach
        action.end_time=encounter.time+max(1,timing-action.strategy.timing_adjustment())
        try:prepared=encounter.prepare_action(action)
        except Exception as exc:raise ArenaBrowserRequestError('Native Disarm prerequisites are not satisfied.') from exc
        return action,prepared,defender

    def choose_disarm(self,payload):
        if (type(payload) is not dict or not {'handle','motion'}<=set(payload)
                or set(payload)-{'handle','motion','unarmed','hand'}
                or ('unarmed' in payload and type(payload['unarmed']) is not bool)):
            raise ArenaBrowserRequestError('Disarm requires a perceived held-weapon handle and attack motion.')
        handle,motion=payload['handle'],payload['motion'];unarmed=payload.get('unarmed',False)
        take_hand=payload.get('hand')
        if take_hand is not None and (not unarmed or take_hand not in ('left hand','right hand')):
            raise ArenaBrowserRequestError('A Disarm take hand is available only for unarmed Disarm.')
        with self._lock:
            if self._active is None:raise ArenaBrowserRequestError('Generate an Encounter first.')
            candidate=self._active;player=candidate.participants[0].native.being
            entity_id=next((key for key,value in self._view_handles.items() if value==handle),None)
            ledger=object.__getattribute__(player,'__dict__').get('_arena_perception_ledger')
            if ledger is None or ledger.observer_id!=player.id:raise ArenaBrowserRequestError('Player perception evidence is unavailable.')
            evidence=None if entity_id is None else next((row for row in ledger.current if row.entity_id==entity_id),None)
            action,prepared,_=self._disarm_preflight(candidate,player,entity_id,evidence,motion,unarmed,take_hand)
            try:candidate.encounter.schedule_action(action)
            except Exception as exc:raise ArenaBrowserRequestError('Native Disarm Choice refused; Arena state is unchanged.') from exc
            self._selected_entity_handle=handle
            self._trace.native_advance(None,None,f'action=disarm mode={"unarmed" if unarmed else "armed"} motion={motion} duration={prepared.end_time-prepared.start_time:g}s')
            return self._view_unlocked()

    def choose_disarm_landing(self,payload):
        if (type(payload) is not dict or set(payload)!={'handle','column','row'}
                or type(payload.get('handle')) is not str
                or type(payload.get('column')) is not int or type(payload.get('row')) is not int):
            raise ArenaBrowserRequestError('Choose a clear represented hex for the pending Disarm landing.')
        with self._lock:
            if self._active is None:raise ArenaBrowserRequestError('Generate an Encounter first.')
            candidate=self._active;player=candidate.participants[0].native.being
            entity_id=next((key for key,value in self._view_handles.items() if value==payload['handle']),None)
            from arena_perception import ArenaPerceptionLedger
            ledger=object.__getattribute__(player,'__dict__').get('_arena_perception_ledger')
            evidence=None if type(ledger) is not ArenaPerceptionLedger else next(
                (row for row in ledger.current if row.entity_id==entity_id),None)
            if evidence is None or evidence.category!='object' or evidence.present_state!='carried':
                raise ArenaBrowserRequestError('Disarm landing requires your current observed Weapon handle.')
            try:
                from atomic_publication import choose_disarm_landing
                choose_disarm_landing(candidate.encounter,entity_id,payload['column'],payload['row'])
            except Exception as exc:
                raise ArenaBrowserRequestError('Native Disarm landing choice refused; Arena state is unchanged.') from exc
            self._trace.native_advance(None,None,
                f'action=disarm_landing cell=({payload["column"]},{payload["row"]})')
            return self._view_unlocked()

    def _break_weapon_preflight(self,candidate,player,entity_id,evidence):
        if evidence is None or evidence.category!='being' or evidence.present_state!='present':
            raise ArenaBrowserRequestError('Select a perceived opposing Being first.')
        encounter=candidate.encounter
        defender=encounter.get_being(entity_id) if type(entity_id) is str else None
        if defender is None or defender is player or not encounter.is_aware(player.id,defender.id):
            raise ArenaBrowserRequestError('Break weapon requires an aware opposing Being.')
        ledger=object.__getattribute__(player,'__dict__').get('_arena_perception_ledger')
        strike=self._visible_incoming_strike(candidate,player,defender,ledger)
        if strike is None:
            raise ArenaBrowserRequestError('No currently perceived pending attack by this Being targets the player.')
        weapon_evidence=None if ledger is None else next(
            (row for row in ledger.current if row.entity_id==strike.instrument_id),None)
        if (weapon_evidence is None or weapon_evidence.category not in ('object','weapon')
                or weapon_evidence.present_state!='carried'
                or weapon_evidence.owner_id!=defender.id):
            raise ArenaBrowserRequestError('The attacking weapon is not currently identified in player-owned perception.')
        attacking_id=self._initial_ready_dagger_id(candidate,player)
        attacking=candidate.universe.get_object_by_id(attacking_id) if type(attacking_id) is str else None
        from weapon import WeaponInstance
        if (type(attacking) is not WeaponInstance or attacking.current.hit_points<=0
                or attacking.id not in player.armed_with(candidate.universe).values()
                or player.current.skills.weapon_skills.get(attacking.original.obj_type,0)<=1):
            raise ArenaBrowserRequestError('Break weapon requires an actually held, usable weapon with advanced skill.')
        if 'swing' not in attacking.get_melee_types():
            raise ArenaBrowserRequestError('The held weapon does not support the adopted Break weapon swing.')
        from melee_combat import effective_melee_reach_meters
        action=Action(candidate.universe,encounter.time,encounter.time+1,'break weapon',
                      player.id,defender.id,attacking.id)
        action.break_weapon_id=strike.instrument_id;action.break_motion='swing'
        action.reach=effective_melee_reach_meters(player.current,attacking.current)
        action.end_time=encounter.time+max(1,attacking.St()-action.strategy.timing_adjustment())
        try:prepared=encounter.prepare_action(action)
        except Exception as exc:raise ArenaBrowserRequestError(str(exc)) from exc
        return action,prepared,strike

    def choose_break_weapon(self,payload):
        if type(payload) is not dict or set(payload)!={'handle'} or type(payload['handle']) is not str:
            raise ArenaBrowserRequestError('Break weapon accepts one currently perceived opponent handle.')
        with self._lock:
            if self._active is None:raise ArenaBrowserRequestError('Generate an Encounter first.')
            candidate=self._active;player=candidate.participants[0].native.being
            entity_id=next((key for key,value in self._view_handles.items() if value==payload['handle']),None)
            ledger=object.__getattribute__(player,'__dict__').get('_arena_perception_ledger')
            if ledger is None or ledger.observer_id!=player.id:raise ArenaBrowserRequestError('Player perception evidence is unavailable.')
            evidence=None if entity_id is None else next((row for row in ledger.current if row.entity_id==entity_id),None)
            action,prepared,strike=self._break_weapon_preflight(candidate,player,entity_id,evidence)
            try:candidate.encounter.schedule_action(action)
            except Exception as exc:raise ArenaBrowserRequestError('Native Break weapon Choice refused; Arena state is unchanged.') from exc
            self._selected_entity_handle=payload['handle']
            self._trace.native_advance(None,None,
                f'action=break_weapon weapon={strike.instrument_id} duration={prepared.end_time-prepared.start_time:g}s')
            return self._view_unlocked()

    def _feint_preflight(self, candidate, player, entity_id, evidence, motion,
                         supported=True, unarmed=False, body_region=None):
        if motion not in ("swing", "thrust"):
            raise ArenaBrowserRequestError("Choose a represented Swing or Thrust motion.")
        if not supported or not _has_native_transactional_action_contract(Action):
            raise ArenaBrowserRequestError("The native Feint scheduler or resolver contract is unavailable.")
        if evidence is None or evidence.category != "being" or evidence.present_state != "present":
            raise ArenaBrowserRequestError("Select an aware opposing Being first.")
        encounter = candidate.encounter
        target = encounter.get_being(entity_id) if type(entity_id) is str else None
        if (target is None or target.id == player.id or entity_id not in encounter.being_list
                or not encounter.is_aware(player.id, target.id)):
            raise ArenaBrowserRequestError("Feint requires an aware participating opposing Being.")
        if not encounter.initiated or encounter.progression_mode != "transactional":
            raise ArenaBrowserRequestError("Activate the native Encounter before choosing Feint.")
        latest_feint = self._player_feint_action(candidate, player)
        if latest_feint is not None and self._melee_action_pending(candidate, latest_feint):
            raise ArenaBrowserRequestError("A native Feint is already resolving for the player.")
        if encounter._choice_book.actor_planned_now(player.id):
            raise ArenaBrowserRequestError("The player already has a native Action accepted or resolving.")
        if player.get_hit_points() <= 0 or target.get_hit_points() <= 0:
            raise ArenaBrowserRequestError("Both Beings must have positive native hit points to schedule Feint.")
        instrument_id = None
        if unarmed:
            if ((player.current.skills.get_skill_level('unarmed combat') or 0) <= 0
                    or body_region not in ('Arm', 'Leg')):
                raise ArenaBrowserRequestError(
                    "Unarmed Feint requires Unarmed combat skill and a represented Arm or Leg profile.")
            weapon = candidate.universe.library.weapon_dictionary.objects.get(body_region)
            if weapon is None or weapon.attacks.get('S' if motion == 'swing' else 'T', {}).get('t') is None:
                raise ArenaBrowserRequestError("The selected body profile does not support that motion.")
        else:
            weapon_id = self._initial_ready_dagger_id(candidate, player)
            from weapon import WeaponInstance
            weapon = candidate.universe.get_object_by_id(weapon_id) if type(weapon_id) is str else None
            if (type(weapon) is not WeaponInstance or weapon.id not in player.weapons
                    or weapon.id not in player.armed_with(candidate.universe).values()
                    or weapon.parent_container_id != player.id or weapon.get_position() is not None
                    or weapon.current.obj_type != "Dagger"):
                raise ArenaBrowserRequestError("Armed Feint requires the API-created Dagger to be held and readied.")
            if motion not in weapon.get_melee_types():
                raise ArenaBrowserRequestError(f"The native Dagger does not support {motion}.")
            if (player.current.skills.weapon_skills.get(weapon.original.obj_type, 0) or 0) <= 1:
                raise ArenaBrowserRequestError("Armed Feint requires advanced skill with the selected weapon.")
            instrument_id = weapon.id
        native_timing = weapon.St() if motion == "swing" else weapon.Tt()
        if type(native_timing) not in (int, float) or not math.isfinite(native_timing) or native_timing <= 0:
            raise ArenaBrowserRequestError("The selected Feint motion has no supported timing.")
        action = Action(candidate.universe, encounter.time, encounter.time + 1,
                        "feint", player.id, target.id, instrument_id)
        action.feint_motion = motion
        if unarmed:
            action.body_region = body_region
        action.reach = effective_melee_reach_meters(
            player.current, weapon if unarmed else weapon.current)
        duration = max(1, math.ceil(native_timing / 2) - action.strategy.timing_adjustment())
        action.end_time = encounter.time + duration
        try:
            prepared = encounter.prepare_action(action)
        except Exception as exc:
            raise ArenaBrowserRequestError(
                "Native Feint Choice is unavailable under the current Encounter state.") from exc
        return action, prepared

    def choose_feint(self, payload):
        if (type(payload) is not dict or not {"handle", "motion"} <= set(payload)
                or set(payload) - {"handle", "motion", "unarmed", "body_region"}
                or ("unarmed" in payload and type(payload["unarmed"]) is not bool)):
            raise ArenaBrowserRequestError("Feint requires one perceived Being handle and a supported motion")
        handle, motion = payload["handle"], payload["motion"]
        unarmed = payload.get("unarmed", False)
        body_region = payload.get("body_region")
        if unarmed != (body_region is not None):
            raise ArenaBrowserRequestError("Unarmed Feint must identify its represented Arm or Leg profile")
        if type(handle) is not str or type(motion) is not str:
            raise ArenaBrowserRequestError("Feint target and motion must be text")
        with self._lock:
            if self._active is None:
                raise ArenaBrowserRequestError("Generate an Encounter before choosing Feint")
            candidate = self._active
            player = candidate.participants[0].native.being
            entity_id = next((key for key, value in self._view_handles.items() if value == handle), None)
            ledger = object.__getattribute__(player, "__dict__").get("_arena_perception_ledger")
            if ledger is None or ledger.observer_id != player.id:
                raise ArenaBrowserRequestError("player perception evidence is unavailable")
            evidence = None if entity_id is None else next(
                (row for row in ledger.current if row.entity_id == entity_id), None)
            action, prepared = self._feint_preflight(
                candidate, player, entity_id, evidence, motion,
                unarmed=unarmed, body_region=body_region)
            try:
                candidate.encounter.schedule_action(action)
            except Exception as exc:
                raise ArenaBrowserRequestError(
                    "native Feint Choice was not accepted; Arena state is unchanged") from exc
            self._selected_entity_handle = handle
            self._trace.native_advance(None, None,
                f"action=feint mode={'unarmed' if unarmed else 'armed'} motion={motion} duration={prepared.end_time-prepared.start_time:g}s")
            return self._view_unlocked()

    def _coup_de_grace_preflight(self, candidate, player, entity_id, evidence, motion):
        if motion not in ('swing','thrust') or evidence is None or evidence.category != 'being' or evidence.present_state != 'present':
            raise ArenaBrowserRequestError('Choose a perceived helpless Being and a supported weapon motion.')
        encounter = candidate.encounter
        target = encounter.get_being(entity_id) if type(entity_id) is str else None
        if target is None or target is player or not encounter.is_aware(player.id,target.id):
            raise ArenaBrowserRequestError('Coup de grace requires an aware opposing Being.')
        if not encounter.initiated or encounter.progression_mode != 'transactional':
            raise ArenaBrowserRequestError('Activate the native Encounter before choosing Coup de grace.')
        if not target.is_helpless() or player.is_helpless():
            raise ArenaBrowserRequestError('Coup de grace requires a helpless target and an able Actor.')
        weapon_id = self._initial_ready_dagger_id(candidate,player)
        from weapon import WeaponInstance
        weapon = candidate.universe.get_object_by_id(weapon_id) if type(weapon_id) is str else None
        if (type(weapon) is not WeaponInstance or weapon.current.hit_points <= 0
                or weapon.id not in player.armed_with(candidate.universe).values()):
            raise ArenaBrowserRequestError('Coup de grace requires a usable, actually held Dagger.')
        if motion not in weapon.get_melee_types():
            raise ArenaBrowserRequestError(f'The native Dagger does not support {motion}.')
        from melee_combat import effective_melee_reach_meters
        action = Action(candidate.universe, encounter.time, encounter.time+1,
                        'coup de grace',player.id,target.id,weapon.id)
        action.coup_motion = motion
        action.reach = effective_melee_reach_meters(player.current,weapon.current)
        timing = weapon.St() if motion == 'swing' else weapon.Tt()
        action.end_time = encounter.time + max(1,timing-action.strategy.timing_adjustment())
        try: prepared = encounter.prepare_action(action)
        except Exception as exc: raise ArenaBrowserRequestError('Native Coup de grace prerequisites are not satisfied.') from exc
        return action,prepared

    def choose_coup_de_grace(self,payload):
        if type(payload) is not dict or set(payload) != {'handle','motion'}:
            raise ArenaBrowserRequestError('Coup de grace requires a perceived target handle and motion.')
        handle,motion=payload['handle'],payload['motion']
        with self._lock:
            if self._active is None: raise ArenaBrowserRequestError('Generate an Encounter first.')
            candidate=self._active;player=candidate.participants[0].native.being
            entity_id=next((key for key,value in self._view_handles.items() if value==handle),None)
            ledger=object.__getattribute__(player,'__dict__').get('_arena_perception_ledger')
            evidence=None if ledger is None else next((row for row in ledger.current if row.entity_id==entity_id),None)
            action,prepared=self._coup_de_grace_preflight(candidate,player,entity_id,evidence,motion)
            try:candidate.encounter.schedule_action(action)
            except Exception as exc:raise ArenaBrowserRequestError('Native Coup de grace Choice refused; state unchanged.') from exc
            self._selected_entity_handle=handle
            self._trace.native_advance(None,None,f'action=coup_de_grace motion={motion} duration={prepared.end_time-prepared.start_time:g}s')
            return self._view_unlocked()

    def choose_melee_strike(self, payload):
        if (type(payload) is not dict or set(payload) not in
                (frozenset(("handle", "motion")), frozenset(("handle", "motion", "charge")),
                 frozenset(("handle", "motion", "weapon_handle")),
                 frozenset(("handle", "motion", "two_handed")),
                 frozenset(("handle", "motion", "weapon_handle", "two_handed")),
                 frozenset(("handle", "motion", "weapon_handle", "shield_bash")),
                 frozenset(("handle", "motion", "weapon_handle", "shield_bash", "two_handed")),
                 frozenset(("handle", "motion", "charge", "weapon_handle")))
                or ("charge" in payload and type(payload["charge"]) is not bool)
                or ("two_handed" in payload and type(payload["two_handed"]) is not bool)
                or ("shield_bash" in payload and type(payload["shield_bash"]) is not bool)):
            raise ArenaBrowserRequestError("melee attack requires a perceived target, motion, and supported weapon/grip options")
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
            weapon_id = (None if "weapon_handle" not in payload else next(
                (key for key, value in self._view_handles.items()
                 if value == payload["weapon_handle"]), None))
            if "weapon_handle" in payload and weapon_id is None:
                raise ArenaBrowserRequestError("Selected Weapon handle is not in current observer evidence.")
            action, _, prepared, _, _ = self._melee_strike_preflight(
                candidate, player, entity_id, evidence, motion,
                charge=payload.get("charge", False), weapon_id=weapon_id,
                two_handed=payload.get("two_handed", False),
                shield_bash=payload.get("shield_bash", False))
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
                                supported=True, allow_composition=False):
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
        if not allow_composition and encounter._choice_book.actor_planned_now(player.id):
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
        from activities import PickUpAction, RunAction, SpotAction, ReadyPreparationAction, DelayAction
        from attention_intent import eligible_discovery_targets

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
            if name.casefold() == "touch being":
                status, reason, duration = "unavailable", "Select a perceived opposing Being first.", None
                target_view = (None if selected is None else {"handle": handle,
                    "name": selected["name"], "type": selected["type"],
                    "present_state": selected["present_state"]})
                if supported_actions.get(Action, False):
                    try:
                        _, prepared = self._touch_preflight(
                            candidate, player, entity_id, evidence)
                        status = "available"
                        duration = prepared.end_time - prepared.start_time
                        reason = ("One-second opposed Touch. Personal reach and both native d20 totals "
                                  "resolve at the boundary; an out-of-reach attempt makes no contact and "
                                  "Touch deals no damage.")
                    except ArenaBrowserRequestError as exc:
                        reason = str(exc)
                else:
                    reason = "The native Action scheduler or Touch resolver contract is unavailable."
                catalog_rows.append({
                    "name": name, "group": "Being targets", "target_type": "being",
                    "required_skill": source_row["required_skill"],
                    "is_melee": source_row["is_melee"], "status": status,
                    "display_name": f"Touch ({duration:g} s)" if duration is not None else "Touch",
                    "reason": reason, "target": target_view,
                    "duration_seconds": duration,
                })
                has_multiple_skill = (player.get_skill_level("multi-action") or 0) > 0
                multiple_status = "available" if status == "available" and has_multiple_skill else "unavailable"
                multiple_reason = (
                    "Declares two ordered native Touch components at this perceived Being. Choose one of "
                    "the adopted priority rows (0, 3) or (1, 2); the complete program repeats with fresh "
                    "Action identities until cancelled." if multiple_status == "available" else
                    "Overlapping Touches require the player's acquired Multi-action skill and the same "
                    "currently available perceived target." if not has_multiple_skill else reason)
                catalog_rows.append({
                    "name": "Multiple Touch", "group": "Physical contact",
                    "target_type": "being", "required_skill": "multi-action",
                    "is_melee": False, "status": multiple_status,
                    "display_name": "Two simultaneous Touches (1 s)",
                    "reason": multiple_reason, "target": target_view,
                    "event_type": "multiple-touch", "duration_seconds": duration,
                })
                continue
            if name.casefold() == "coup de grace":
                status,reason="unavailable","Select a perceived helpless opponent; use a native held weapon."
                target_view=(None if selected is None else {"handle":handle,"name":selected["name"],
                    "type":selected["type"],"present_state":selected["present_state"]})
                motions=[]
                if supported_actions.get(Action,False):
                    for motion in ('swing','thrust'):
                        try:
                            _,prepared=self._coup_de_grace_preflight(candidate,player,entity_id,evidence,motion)
                            motions.append({"motion":motion,"duration_seconds":prepared.end_time-prepared.start_time})
                        except ArenaBrowserRequestError as exc:reason=str(exc)
                    if motions:status="available";reason="Native helpless-target Coup de grace; automatic critical, ordinary weapon timing and damage, then Fortitude save at DC 10 + damage."
                catalog_rows.append({"name":name,"group":"Being targets","target_type":"being",
                    "required_skill":source_row["required_skill"],"is_melee":source_row["is_melee"],
                    "status":status,"display_name":"Coup de grace","reason":reason,
                    "target":target_view,"motions":motions,"duration_seconds":None if not motions else motions[0]["duration_seconds"]})
                continue
            if name.casefold() in ("feint (armed)", "feint (unarmed)"):
                unarmed = name.casefold() == "feint (unarmed)"
                reason = ("Select a perceived opposing Being; unarmed Feint requires Unarmed combat skill."
                    if unarmed else
                    "Select a perceived opposing Being; armed Feint requires advanced skill with a held weapon.")
                status, duration = "unavailable", None
                motions = []
                target_view = (None if selected is None else {"handle": handle,
                    "name": selected["name"], "type": selected["type"],
                    "present_state": selected["present_state"]})
                if supported_actions.get(Action, False):
                    profiles = (('Arm', 'Leg') if unarmed else (None,))
                    for region in profiles:
                        for motion in ("swing", "thrust"):
                            try:
                                _, prepared = self._feint_preflight(
                                    candidate, player, entity_id, evidence, motion,
                                    unarmed=unarmed, body_region=region)
                                motion_duration = prepared.end_time - prepared.start_time
                                row = {"motion": motion, "duration_seconds": motion_duration}
                                if region is not None:
                                    row["body_region"] = region
                                motions.append(row)
                            except ArenaBrowserRequestError as exc:
                                reason = str(exc)
                    if motions:
                        status = "available"
                        duration = motions[0]["duration_seconds"]
                        reason = (("Native unarmed Feint uses the selected body profile and Unarmed combat skill; "
                                  if unarmed else "Native armed Feint uses a false Dagger attack with no damage; ")
                                  + "the Feint deals no damage; "
                                  "base timing is half the selected attack timing, rounded up. "
                                  "A success grants +2 to the next chosen attack against this Being only.")
                else:
                    reason = "The native Action scheduler or Feint resolver contract is unavailable."
                catalog_rows.append({
                    "name": name, "group": "Being targets",
                    "target_type": "being", "required_skill": source_row["required_skill"],
                    "is_melee": source_row["is_melee"], "status": status,
                    "display_name": (f"Unarmed Feint ({duration:g} s)" if unarmed else
                        f"Feint with Dagger ({duration:g} s)") if duration is not None else
                        ("Unarmed Feint" if unarmed else "Feint with Dagger"),
                    "reason": reason, "target": target_view,
                    "motion": "thrust", "motions": motions, "unarmed": unarmed,
                    "duration_seconds": duration,
                })
                continue
            if name.casefold() in ("swing at being", "thrust at being"):
                motion = "swing" if name.casefold().startswith("swing") else "thrust"
                reason = "Select an aware opposing Being. Native reach and path are checked at impact."
                status = "unavailable"
                display_name = "Dagger " + motion.title()
                duration = None
                target_view = (None if selected is None else {"handle": handle,
                    "name": selected["name"], "type": selected["type"],
                    "present_state": selected["present_state"]})
                weapon_options = (self._melee_weapon_options(candidate, player,
                    entity_id, evidence, motion) if evidence is not None else [])
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
                elif weapon_options:
                    status = "available"
                    first = weapon_options[0]
                    duration = first["duration_seconds"]
                    display_name = f"{first['type']} {motion.title()} ({duration:g} s)"
                    reason = ("Choose a currently held native weapon and grip. Every choice uses its "
                              "native timing, reaches the target through the Action evaluator, and "
                              "validates explicit hand use.")
                catalog_rows.append({
                    "name": name, "group": "Being targets", "target_type": "being",
                    "required_skill": source_row["required_skill"],
                    "is_melee": source_row["is_melee"], "status": status,
                    "display_name": display_name, "reason": reason,
                    "target": target_view, "motion": motion,
                    "duration_seconds": duration, "weapon_options": weapon_options,
                })
                continue
            if name.casefold() in ("swing at object", "thrust at object"):
                motion = "swing" if name.casefold().startswith("swing") else "thrust"
                status, reason, duration = "unavailable", "Select a perceived, unattended Object with known hardness first.", None
                object_view = (None if selected is None else {"handle": handle,
                    "name": selected["name"], "type": selected["type"],
                    "present_state": selected["present_state"]})
                weapon_options = (self._object_strike_weapon_options(candidate, player,
                    entity_id, evidence, motion) if evidence is not None else [])
                if supported_actions.get(Action, False):
                    try:
                        _, prepared, distance, reach = self._object_strike_preflight(
                            candidate, player, entity_id, evidence, motion)
                        status = "available"
                        duration = prepared.end_time - prepared.start_time
                        reason = (f"Native Strike an object; center distance {distance:.2f} m, "
                                  f"weapon reach {reach:.2f} m. The authored hardness and hit points "
                                  "resolve in the common Action batch.")
                    except ArenaBrowserRequestError as exc:
                        reason = str(exc)
                if weapon_options:
                    status = "available"
                    duration = weapon_options[0]["duration_seconds"]
                    reason = ("Choose a currently held native weapon. Its motion timing, reach, "
                              "hardness and hit-point effects resolve in the shared Action snapshot.")
                elif not supported_actions.get(Action, False):
                    status = "not_implemented"
                    reason = "The native Object-strike resolver is unavailable."
                catalog_rows.append({"name":name,"group":"Object targets","target_type":"object",
                    "required_skill":source_row["required_skill"],"is_melee":source_row["is_melee"],
                    "status":status,"display_name":f"{weapon_options[0]['type'] if weapon_options else 'Weapon'} {motion.title()} at Object"+
                        (f" ({duration:g} s)" if duration is not None else ""),
                    "reason":reason,"target":object_view,"motion":motion,
                    "duration_seconds":duration,"weapon_options":weapon_options})
                continue
            elif name.casefold()=="disarm (armed)":
                status,reason="unavailable","Select a perceived opponent-held weapon; an advanced skill with your attacking weapon is required."
                motions=[]
                target_view=(None if selected is None else {"handle":handle,"name":selected["name"],
                    "type":selected["type"],"present_state":selected["present_state"]})
                if supported_actions.get(Action,False):
                    for motion in ('swing','thrust'):
                        try:
                            _,prepared,_=self._disarm_preflight(candidate,player,entity_id,evidence,motion)
                            motions.append({"motion":motion,"duration_seconds":prepared.end_time-prepared.start_time})
                        except ArenaBrowserRequestError as exc:reason=str(exc)
                    if motions:
                        status="available"
                        reason="Native opposed Disarm; success releases this exact weapon in the defender's occupied hex."
                catalog_rows.append({"name":name,"group":"Held Object actions","target_type":"weapon",
                    "required_skill":source_row["required_skill"],"is_melee":source_row["is_melee"],
                    "status":status,"display_name":"Disarm held weapon","reason":reason,
                    "target":target_view,"motions":motions,
                    "duration_seconds":None if not motions else motions[0]["duration_seconds"]})
                continue
            elif name.casefold()=="disarm (unarmed)":
                status,reason="unavailable","Select an opposing Being's perceived held weapon; Unarmed combat skill and a free arm are required."
                motions=[]
                target_view=(None if selected is None else {"handle":handle,"name":selected["name"],
                    "type":selected["type"],"present_state":selected["present_state"]})
                if supported_actions.get(Action,False):
                    for motion in ('swing','thrust'):
                        try:
                            _,prepared,_=self._disarm_preflight(candidate,player,entity_id,evidence,motion,True)
                            motions.append({"motion":motion,"duration_seconds":prepared.end_time-prepared.start_time})
                        except ArenaBrowserRequestError as exc:reason=str(exc)
                    if motions:
                        status="available"
                        reason="Native unarmed opposed Disarm; success releases this exact weapon in the defender's occupied hex."
                catalog_rows.append({"name":name,"group":"Held Object actions","target_type":"weapon",
                    "required_skill":source_row["required_skill"],"is_melee":source_row["is_melee"],
                    "status":status,"display_name":"Unarmed Disarm held weapon","reason":reason,
                    "target":target_view,"motions":motions,"unarmed":True,
                    "take_hands":[hand for hand in ('left hand','right hand')
                        if player.current.body_parts.get(hand) is None],
                    "duration_seconds":None if not motions else motions[0]["duration_seconds"]})
                continue
            elif name.casefold()=="break weapon (armed)":
                status,reason,duration='unavailable',(
                    'Select an aware opponent with a currently perceived pending attack that resolves one second after your native weapon Swing.'),None
                target_view=(None if selected is None else {"handle":handle,"name":selected["name"],
                    "type":selected["type"],"present_state":selected["present_state"]})
                if supported_actions.get(Action,False):
                    try:
                        _,prepared,_=self._break_weapon_preflight(candidate,player,entity_id,evidence)
                        status='available';duration=prepared.end_time-prepared.start_time
                        reason=('Native Break weapon Swing is evaluated before the already scheduled attack; '
                                'a broken weapon is unavailable only to later-boundary Actions.')
                    except ArenaBrowserRequestError as exc:reason=str(exc)
                catalog_rows.append({"name":name,"group":"Held Object actions","target_type":"being",
                    "required_skill":source_row["required_skill"],"is_melee":source_row["is_melee"],
                    "status":status,"display_name":"Break weapon"+
                    (f" ({duration:g} s)" if duration is not None else ""),"reason":reason,
                    "target":target_view,"duration_seconds":duration})
                continue
            elif name.casefold() in ("grab being", "hold being", "break hold", "release grip", "grapple", "grapple escape", "takedown", "reverse", "pin from above", "pin from below", "trip", "bull rush", "overrun", "end-run"):
                event_type = {"grab being":"grab", "hold being":"hold",
                              "break hold":"break hold", "release grip":"release grip", "grapple":"grapple",
                              "grapple escape":"grapple escape", "takedown":"takedown",
                              "reverse":"reverse", "pin from above":"pin", "pin from below":"pin", "trip":"trip", "bull rush":"bull rush", "overrun":"overrun", "end-run":"end-run"}[name.casefold()]
                display = {"grab":"Grab", "hold":"Hold", "break hold":"Break hold", "release grip":"Release grip",
                           "grapple":"Grapple", "grapple escape":"Grapple Escape",
                           "takedown":"Takedown","reverse":"Reverse","pin":"Pin","trip":"Trip","bull rush":"Bull Rush","overrun":"Overrun","end-run":"End Run"}[event_type]
                duration = 6 if event_type in ("grapple", "grapple escape","takedown","reverse","pin") else 4 if event_type=="overrun" else 3 if event_type=="end-run" else 2 if event_type=="trip" else 1
                if event_type == "hold":
                    display = "Automatic Hold check"
                    duration = None
                target_view = (None if selected is None else {"handle":handle,
                    "name":selected["name"],"type":selected["type"],
                    "present_state":selected["present_state"]})
                status, reason = "unavailable", "Select a currently perceived opposing Being."
                hands = []
                exit_cells = []
                if selected is not None and selected.get("category") == "being":
                    try:
                        if event_type == "grab":
                            slots = object.__getattribute__(player, "__dict__").get("current")
                            body_parts = getattr(slots, "body_parts", {}) if slots is not None else {}
                            from physical_contact import active_contact_state
                            active_grips, _ = active_contact_state(candidate.encounter)
                            occupied = {row[3] for row in active_grips if row[1] == player.id}
                            from physical_contact import active_object_grip_state
                            occupied.update(row[4] for row in active_object_grip_state(candidate.encounter)
                                            if row[2] == player.id)
                            hands = [part for part in ("left hand", "right hand")
                                     if part in body_parts and not body_parts[part] and part not in occupied]
                            if not hands:
                                raise ArenaBrowserRequestError("No explicitly represented free native hand is available.")
                            _, prepared = self._grappling_preflight(
                                candidate, player, entity_id, evidence, event_type, hands[0])
                        elif event_type == "release grip":
                            from physical_contact import active_contact_state
                            active_grips, _ = active_contact_state(candidate.encounter)
                            hands = [row[3] for row in active_grips
                                     if row[1] == player.id and row[2] == entity_id]
                            if not hands:
                                raise ArenaBrowserRequestError("You do not maintain a physical Grip on this Being.")
                            _, prepared = self._grappling_preflight(
                                candidate, player, entity_id, evidence, event_type, hands[0])
                        elif event_type == "trip":
                            _, prepared = self._grappling_preflight(candidate,player,entity_id,evidence,event_type,position="STR")
                        elif event_type in ("overrun", "bull rush"):
                            _, prepared = self._grappling_preflight(candidate,player,entity_id,evidence,event_type)
                        elif event_type == "end-run":
                            from arena_hex_map import HexAddress
                            for address in candidate.arena_map.layout.addresses():
                                try:
                                    _, prepared = self._grappling_preflight(candidate,player,
                                        entity_id,evidence,event_type,
                                        exit_cell=(address.column,address.row))
                                    exit_cells.append({"column":address.column,"row":address.row,
                                        "duration_seconds":prepared.end_time-prepared.start_time})
                                except ArenaBrowserRequestError:
                                    continue
                            if not exit_cells:
                                raise ArenaBrowserRequestError("No currently clear exit hex is reachable through this Being at the selected ordinary movement rate.")
                        elif event_type in ("takedown","pin"):
                            default_position = ("prone" if event_type == "takedown" else
                                "pin_top" if name.casefold() == "pin from above" else "pin_bottom")
                            _, prepared = self._grappling_preflight(candidate,player,entity_id,evidence,event_type,position=default_position)
                        else:
                            _, prepared = self._grappling_preflight(
                                candidate, player, entity_id, evidence, event_type)
                        status = "available"
                        duration = prepared.end_time - prepared.start_time
                        reason = {
                            "grab":"One-second opposed native Grab after this player's committed successful Touch; the selected free hand becomes one distinct Grip.",
                            "hold":"Automatic opposed Grab check at this Grip's six-second maintenance boundary; no Action is spent.",
                            "break hold":"One-second opposed 3d6 + Strength contest against this Being's Grip on you.",
                            "release grip":"One-second declared voluntary release of the selected Grip you maintain; no contest is rolled.",
                            "grapple":"Six-second initial Grapple check at the prerequisite Grip's next maintenance boundary.",
                            "grapple escape":"Six-second opposed Escape check at the existing Grapple control boundary; Escape Artist adds to your check.",
                            "takedown":"One opposed Grapple check at the next control boundary. Requires explicit size categories and standing control.",
                            "reverse":"One opposed Grapple check at the next control boundary from a disadvantaged position; requires explicit size categories.",
                            "pin":"One opposed Grapple check at the next control boundary; target becomes prone and immobilized.",
                            "trip":"Two-second Strength versus defender-chosen Strength/Dexterity contest after this player's successful Touch; size category is required.",
                            "bull rush":"One-second native Strength contest within one yard and ahead, including +2 for an explicitly represented side with more than two named legs; success records pending displacement without inventing a distance.",
                            "overrun":"Four-second native Strength + Dexterity contest against a standing Being within one yard and ahead, including +2 for an explicitly represented side with more than two named legs; success leaves the target prone without invented displacement.",
                            "end-run":"Three-second preparation, then a one-second ordinary-rate passage through this occupied hex. The movement-phase contest uses native Dexterity, explicit size facts and Multiple-action priority; changing occupancy or an unknown route refuses safely.",
                        }[event_type]
                        if event_type == "overrun" and duration > 4:
                            reason = ("Six-second continuation after a successful Charge or Bull Rush, with the adopted +1 contest bonus. "
                                "A Charge continuation lands the prone target one hex in the charging direction; a Bull Rush continuation "
                                "leaves it prone in its current hex because no force-to-motion distance is adopted.")
                    except ArenaBrowserRequestError as exc:
                        reason = str(exc)
                catalog_rows.append({"name":name,"group":"Physical contact",
                    "target_type":"being","required_skill":source_row["required_skill"],
                    "is_melee":source_row["is_melee"],"status":status,
                    "display_name":(f"{display} ({duration:g} s)" if duration is not None else display),"reason":reason,
                    "target":target_view,"hands":hands,"exit_cells":exit_cells,"duration_seconds":duration,
                    "event_type":event_type})
                continue
            elif name.casefold() in ("grab object","wrest"):
                event_type=name.casefold()
                target_view=(None if selected is None else {"handle":handle,"name":selected["name"],
                    "type":selected["type"],"present_state":selected["present_state"]})
                status,reason='unavailable','Select a currently perceived weapon held by an opposing Being.'
                hands=[];duration=1
                if selected is not None and selected.get('category')=='object':
                    try:
                        if event_type=='grab object':
                            hands=[part for part in ('left hand','right hand')
                                if part in player.current.body_parts and player.current.body_parts[part] is None]
                            if not hands:raise ArenaBrowserRequestError('No explicitly represented free receiving hand is available.')
                        _,prepared=self._object_grappling_preflight(candidate,player,entity_id,evidence,event_type,
                            hands[0] if hands else None)
                        status='available';duration=prepared.end_time-prepared.start_time
                        reason=('One-second native held-Object Grab using the holder’s Defense, Object-size DC modifier, and +5 DC.'
                            if event_type=='grab object' else
                            'One-second native Wrest: 3d6 plus Strength bonus against the holder; a strict win transfers the same Object ID atomically.')
                    except ArenaBrowserRequestError as exc:reason=str(exc)
                catalog_rows.append({'name':name,'group':'Physical contact','target_type':'object',
                    'required_skill':source_row['required_skill'],'is_melee':source_row['is_melee'],
                    'status':status,'display_name':('Grab held Object' if event_type=='grab object' else 'Wrest')+
                        f' ({duration:g} s)','reason':reason,'target':target_view,'hands':hands,
                    'duration_seconds':duration,'event_type':event_type})
                continue
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
                options, reason = self._ready_preparation_options_unlocked(
                    candidate, player, entity_id, evidence)
                if not supported_actions.get(ReadyPreparationAction, False):
                    options = ()
                    reason = "The native Ready-preparation Action contract is unavailable."
                catalog_rows.append({"name": name, "group": "Arena Actions",
                    "display_name": "Ready Object", "target_type": "object",
                    "required_skill": source_row["required_skill"],
                    "is_melee": source_row["is_melee"],
                    "status": "available" if options else "unavailable",
                    "reason": reason,
                    "target": (None if selected is None else {"handle": handle,
                        "name": selected["name"], "type": selected["type"],
                        "present_state": selected["present_state"]}),
                    "motions": list(options)})
                continue
            elif name.casefold() == "throw":
                target_view = (None if selected is None or selected.get("category") != "being"
                    else {"handle": handle, "name": selected["name"],
                          "type": selected["type"],
                          "present_state": selected["present_state"]})
                projectiles, reason = self._throw_projectile_options(candidate, player, entity_id)
                status = "unavailable"
                duration = None
                if target_view is None:
                    reason = "Select a currently perceived opposing Being."
                elif not projectiles:
                    reason = "No supported held Object has an observer-authorized inventory handle."
                elif supported_actions.get(ThrowAction, False):
                    try:
                        _action, prepared, _object_id = self._throw_preflight(
                            candidate, player, entity_id, evidence,
                            projectiles[0]["handle"])
                        status = "available"
                        duration = prepared.end_time - prepared.start_time
                        reason = ("Four-second native Throw aimed at the selected Being's represented point; "
                                  "projectile arrival resolves the attack and damage; a miss records its d8 "
                                  "direction with destination unresolved.")
                    except ArenaBrowserRequestError as exc:
                        reason = str(exc)
                catalog_rows.append({"name": name, "group": "Being targets",
                    "target_type": "being", "required_skill": source_row["required_skill"],
                    "is_melee": False, "status": status,
                    "display_name": f"Throw ({duration:g} s)" if duration is not None else "Throw",
                    "reason": reason, "target": target_view,
                    "projectiles": list(projectiles), "duration_seconds": duration})
                continue
            elif name.casefold() == "delay":
                available = supported_actions.get(DelayAction, False)
                catalog_rows.append({"name": name, "group": "Arena Actions",
                    "display_name": "Delay (1 s)", "target_type": "none",
                    "required_skill": source_row["required_skill"],
                    "is_melee": source_row["is_melee"],
                    "status": "available" if available else "unavailable",
                    "reason": ("Wait one committed second with the selected native defense allocation; "
                               "choose another Action at the next boundary. Repeat Delay to keep waiting."),
                    "target": None,
                    "defense_default": player.strategy.defense})
                continue
            elif name.casefold().startswith("parry"):
                continue
            elif name.casefold() == "throw":
                reason = ("The native Throw resolver has a narrow authored parameter bracket, but the Arena "
                          "has no supported control for its load and trajectory inputs.")
            elif name.casefold().startswith("deflect"):
                reason = ("Unavailable: observer-owned evidence does not establish awareness of one missile "
                          "throughout its complete trajectory, and its redirected Missing destination is unresolved.")
            elif name.casefold().startswith("shoot"):
                reason = ("Unavailable: adopted bow data provide timing, range, and damage but no arrow "
                          "velocity/flight-time or native ammunition release profile.")
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

        target_view = (None if selected is None or entity_id is None
            or evidence is None or evidence.category != "being" else {
                "handle": handle, "name": selected["name"], "type": selected["type"],
                "present_state": selected["present_state"]})
        stun_options = []
        stun_reason = "Select a currently perceived Being and acquire extraordinary Stun skill."
        if target_view is not None and (player.get_skill_level("stun") or 0) >= 1:
            from activities import declare_stun
            for region,motion in (("Arm","thrust"),("Arm","swing"),("Leg","swing")):
                try:
                    action = declare_stun(candidate.universe,candidate.encounter,player.id,
                        entity_id,region=region,motion=motion)
                    prepared = candidate.encounter.prepare_action(action)
                    stun_options.append({"body_region":region,"motion":motion,
                        "duration_seconds":prepared.end_time-prepared.start_time})
                except (ArenaBrowserRequestError,TypeError,ValueError,RuntimeError) as exc:
                    stun_reason = str(exc)
        catalog_rows.append({"name":"Stun","group":"Being targets","target_type":"being",
            "required_skill":"stun","is_melee":True,
            "status":"available" if stun_options else "unavailable",
            "display_name":"Stun","reason":("Declared unarmed Stun; an eligible threat triggers Fortitude DC 20, duration uses represented Stun ranks, and only later-second Actions are interrupted." if stun_options else stun_reason),
            "target":target_view,"motions":stun_options})

        subdue_options = []
        subdue_reason = "Select a present Being and hold a represented bludgeon weapon."
        if target_view is not None:
            from activities import declare_subdue
            from weapon import WeaponInstance
            for weapon_id in sorted(player.armed_with(candidate.universe).values()):
                weapon = candidate.universe.get_object_by_id(weapon_id)
                weapon_handle = self._view_handles.get(weapon_id)
                if type(weapon) is not WeaponInstance or weapon_handle is None:
                    continue
                for motion in ("swing","thrust"):
                    profile=weapon.current.attacks.get("S" if motion=="swing" else "T",{})
                    if profile.get("p") != "B":
                        continue
                    try:
                        action=declare_subdue(candidate.universe,candidate.encounter,
                            player.id,entity_id,weapon_id,motion=motion)
                        prepared=candidate.encounter.prepare_action(action)
                        subdue_options.append({"weapon_handle":weapon_handle,
                            "weapon_name":weapon.name or weapon.current.obj_type,
                            "motion":motion,"duration_seconds":prepared.end_time-prepared.start_time})
                    except (ArenaBrowserRequestError,TypeError,ValueError,RuntimeError) as exc:
                        subdue_reason=str(exc)
        catalog_rows.append({"name":"Subdue","group":"Being targets","target_type":"being",
            "required_skill":"none","is_melee":True,
            "status":"available" if subdue_options else "unavailable",
            "display_name":"Subdue","reason":("Declared melee bludgeon Subdue; records separate subdual and ordinary damage, with one-point-per-hour recovery." if subdue_options else subdue_reason),
            "target":target_view,"weapon_options":subdue_options})

        if (entity_id is not None and evidence is not None
                and evidence.category == "being"
                and evidence.present_state == "present"):
            charge_status, charge_reason, charge_duration = (
                "unavailable", "Select an aware opponent with a legal approach route.", None)
            try:
                _charge, _weapon, charge_prepared, _distance, _reach = (
                    self._melee_strike_preflight(candidate, player, entity_id,
                        evidence, "thrust", charge=True))
                charge_status = "available"
                charge_duration = charge_prepared.end_time-charge_prepared.start_time
                charge_reason = ("Native Charge uses the actual relative movement speed at impact; "
                    "the legal movement plan must culminate at 4 yd/s or faster and within weapon reach. "
                    "The native resolver applies +2 to hit and its adopted speed-based damage increment.")
            except ArenaBrowserRequestError as exc:
                charge_reason = str(exc)
            catalog_rows.append({"name": "Charge", "group": "Being targets",
                "target_type": "being", "required_skill": "none", "is_melee": True,
                "status": charge_status, "display_name":
                    f"Dagger Charge · thrust ({charge_duration:g} s)" if charge_duration is not None
                    else "Dagger Charge · thrust", "reason": charge_reason,
                "target": {"handle": handle, "name": selected["name"],
                           "type": selected["type"],
                           "present_state": selected["present_state"]},
                "motion": "thrust", "charge": True,
                "duration_seconds": charge_duration})

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
        for sense in ('search', 'listen'):
            sense_eligible = len(eligible_discovery_targets(
                candidate.encounter, player.id, sense)) == 1
            enabled = (self._authored_scenario_id == "arena-spot-demo"
                       and candidate.encounter.initiated
                       and self._encounter_mode == "player_vs_arena"
                       and sense_eligible)
            arena_rows.append({"name": sense.title(), "group": "Discovery Actions",
                "status": "available" if enabled else "unavailable",
                "reason": ("Native six-second target-free Action; eligibility uses the authored "
                    + ("search-access" if sense == 'search' else "audibility")
                    + " source fact and does not disclose a target identity." if enabled else
                    "No unfamiliar participant has a supported source fact for this discovery Action.")})
        if evidence is not None and evidence.category == "being":
            bash_options = self._shield_bash_options(candidate, player, entity_id, evidence)
            catalog_rows.append({
                "name": "Shield bash", "group": "Being targets", "target_type": "being",
                "required_skill": "armed combat", "is_melee": True,
                "status": "available" if bash_options else "unavailable",
                "display_name": "Shield bash",
                "reason": ("Choose an equipped non-tower shield and native attack motion. "
                    "Off-hand status uses explicit dominant-hand evidence; the adopted penalty "
                    "applies unless Ambidexterity is present." if bash_options else
                    "Shield bash requires an eligible equipped shield, known dominant hand, and supported attack motion."),
                "target": {"handle": handle, "name": selected["name"],
                           "type": selected["type"], "present_state": selected["present_state"]},
                "weapon_options": bash_options,
            })

        if not supported_actions.get(SpotAction):
            spot_status = "not_implemented"
            spot_reason = "The native Spot scheduler or resolver contract is unavailable."
        elif (self._authored_scenario_id == "arena-spot-demo"
                and candidate.encounter.initiated and self._encounter_mode == "player_vs_arena"
                and len(eligible_discovery_targets(candidate.encounter,
                    player.id, 'spot')) == 1
                and not any(item.id in candidate.encounter.pending_action_list
                    or any(item.id in record.view.action_ids
                           and record.view.state in ("accepted", "executing")
                           for record in candidate.encounter._choice_book._choices.values())
                    for item in _native_spot_actions(candidate, player.id))):
            spot_status = "available"
            spot_reason = "Native target-free Spot is a six-second Action; it does not disclose a target identity."
        else:
            spot_status, spot_reason = "unavailable", (
                "No unfamiliar participant is eligible for target-free Spot." if
                self._authored_scenario_id == "arena-spot-demo" and candidate.encounter.initiated
                else _SPOT_DISABLED)
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
        contact_program_status, contact_program_reason = (
            "unavailable", "Requires one reciprocal physical Grip and an acquired Multi-action skill.")
        if (supported_actions.get(Action, False)
                and (player.get_skill_level("multi-action") or 0) > 0
                and entity_id is not None and evidence is not None):
            try:
                self._grappling_preflight(candidate, player, entity_id, evidence, "grapple")
                self._grappling_preflight(candidate, player, entity_id, evidence, "break hold")
                contact_program_status = "available"
                contact_program_reason = (
                    "Declare initial Grapple and Break hold together using their native six-second and one-second timings.")
            except ArenaBrowserRequestError as exc:
                contact_program_reason = str(exc)
        arena_rows.append({"name": "Multiple Grapple + Break hold", "group": "Physical contact",
                           "status": contact_program_status, "reason": contact_program_reason,
                           "target": dodge_target, "event_type": "multiple-contact"})
        book = candidate.encounter._choice_book
        player_id = player.id
        has_active_program = any(record.view.state in ("accepted", "executing")
            and len(record.members) > 1
            and any(member.action.actor_id == player_id for member in record.members)
            for record in book._choices.values())
        if has_active_program:
            arena_rows.append({"name": "Cancel Action program", "group": "Active actions",
                "status": "available", "reason": "Cancel an accepted ordered program or stop its unresolved members and future cycles."})
        skill_ranks = sorted((str(name), rank) for name, rank in
            player.current.skills.get_skills().items()
            if type(name) is str and type(rank) is int and rank >= 0)
        weapon_ranks = sorted((str(name), rank) for name, rank in
            player.current.skills.weapon_skills.items()
            if type(name) is str and type(rank) is int and rank >= 0)
        resources = {"multi_action_skill": player.get_skill_level("multi-action") or 0,
            "strength_points": max(0, (player.STR() - 10) // 2),
            "dexterity_points": max(0, (player.DEX() - 10) // 2),
            "skill_ranks": [{"name": name, "rank": rank} for name, rank in skill_ranks],
            "weapon_ranks": [{"name": name, "rank": rank} for name, rank in weapon_ranks]}
        return {"catalog_source": "native Action catalog",
                "entries": catalog_rows + arena_rows,
                "program_resources": resources}

    def _throw_projectile_options(self, candidate, player, target_id):
        """Return only direct player possessions with observer-owned opaque handles."""
        from object import ObjectInstance
        from weapon import WeaponInstance
        from being import BeingInstance
        target = candidate.encounter.get_being(target_id) if type(target_id) is str else None
        coup_eligible = bool(target is not None and target is not player
            and candidate.encounter.is_aware(player.id, target.id)
            and target.is_helpless() and not player.is_helpless()
            and target.get_position() is not None and player.get_position() is not None
            and math.hypot(player.get_position().x-target.get_position().x,
                           player.get_position().y-target.get_position().y) <= 0.9144)
        rows = []
        direct_ids = tuple(dict.fromkeys(tuple(player.possessions)
            + tuple(player.weapons) + tuple(value for value in player.current.body_parts.values()
                if value is not None)))
        for object_id in direct_ids:
            obj = candidate.universe.get_object_by_id(object_id)
            handle = self._view_handles.get(object_id)
            if (type(obj) not in (ObjectInstance, WeaponInstance) or isinstance(obj, BeingInstance)
                    or handle is None or obj.parent_container_id not in (None, player.id)
                    or obj.get_position() is not None):
                continue
            weight = obj.current.weight
            is_eligible_weapon = (type(obj) is WeaponInstance
                and object_id in player.weapons
                and object_id in player.current.body_parts.values()
                and obj.current.attacks.get('R', {}).get('t') == 4
                and type(obj.current.attacks.get('R', {}).get('d')) is int
                and type(obj.current.attacks.get('R', {}).get('p')) is str)
            if ((type(obj) is ObjectInstance and object_id in player.possessions
                    or is_eligible_weapon)
                    and type(weight) in (int, float) and math.isfinite(weight)
                    and 0 < weight <= 3.3):
                rows.append({"handle": handle, "name": obj.name or obj.current.obj_type,
                    "type": obj.current.obj_type, "weight_pounds": float(weight),
                    "weapon": is_eligible_weapon,
                    "coup_de_grace": bool(is_eligible_weapon and coup_eligible)})
        return tuple(rows), ("Select an eligible held Object with a native weight and a currently authorized handle."
            if not rows else "")

    def _throw_preflight(self, candidate, player, target_id, evidence,
                         projectile_handle, *, coup_de_grace=False):
        from object import ObjectInstance
        from weapon import WeaponInstance
        from being import BeingInstance
        from movement_intent import _HEAVY_LOAD_UPPER_LB
        if (type(target_id) is not str or target_id == player.id
                or evidence is None or evidence.entity_id != target_id
                or evidence.category != "being" or evidence.present_state != "present"
                or target_id not in candidate.encounter.being_list):
            raise ArenaBrowserRequestError("Targeted Throw needs a currently perceived opposing Being.")
        projectile_id = next((key for key, value in self._view_handles.items()
                              if value == projectile_handle), None)
        obj = (None if projectile_id is None else
               candidate.universe.get_object_by_id(projectile_id))
        if (type(obj) not in (ObjectInstance,WeaponInstance) or isinstance(obj, BeingInstance)
                or (projectile_id not in player.possessions
                    and not (type(obj) is WeaponInstance and projectile_id in player.weapons
                        and projectile_id in player.current.body_parts.values()))
                or obj.parent_container_id not in (None, player.id)
                or obj.get_position() is not None
                or type(obj.current.weight) not in (int, float)
                or not math.isfinite(obj.current.weight)
                or not 0 < obj.current.weight <= 3.3):
            raise ArenaBrowserRequestError("Throw requires an authorized handle for an eligible Object in the player's custody.")
        if player.current.abilities.STR() != 10:
            raise ArenaBrowserRequestError("The current native Throw bracket supports Strength 10 only.")
        if type(coup_de_grace) is not bool:
            raise ArenaBrowserRequestError("The thrown Coup de grace selector must be Boolean.")
        if coup_de_grace and (type(obj) is not WeaponInstance
                or not candidate.encounter.is_aware(player.id, target_id)
                or player.is_helpless()):
            raise ArenaBrowserRequestError("Thrown Coup de grace requires an aware helpless target and an able Actor.")
        reference = _HEAVY_LOAD_UPPER_LB.get(10)
        if type(reference) not in (int, float) or not math.isfinite(reference) or reference <= 0:
            raise ArenaBrowserRequestError("The adopted Strength 10 heavy-load reference is unavailable.")
        action = ThrowAction(candidate.universe, player.id, projectile_id,
            candidate.encounter.time, heavy_load_reference_lb=reference,
            elevation_degrees=45.0, target_id=target_id,
            landing_elevation_m=0.0, coup_de_grace=coup_de_grace)
        try:
            prepared = action.prepare_schedule(candidate.encounter)
        except (TypeError, ValueError) as exc:
            raise ArenaBrowserRequestError(str(exc)) from exc
        return action, prepared, projectile_id

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
            managed = {'stunned_until','subdual_damage','subdual_recovery_anchor',
                       'subdual_unconscious','subdual_damage_current'}
            if type(states) is not dict or any(type(key) is not str or
                    (type(value) is not bool and key not in managed)
                    for key, value in states.items()):
                raise ArenaBrowserRequestError("native player condition states cannot be projected safely")
            visible_states = {key:value for key,value in states.items() if type(value) is bool}
            stun_until = states.get('stunned_until')
            from action_evaluation import stun_active_at
            stun_remaining = (max(0, math.ceil(stun_until-candidate.encounter.time))
                if type(stun_until) in (int,float) else 0)
            subdual = states.get('subdual_damage',0)
            recovery_anchor = states.get('subdual_recovery_anchor')
            if type(subdual) is int and type(recovery_anchor) in (int,float):
                from action_evaluation import subdual_recovery_state
                subdual, _ = subdual_recovery_state(subdual, recovery_anchor,
                    candidate.encounter.time)
            if type(subdual) is not int or subdual < 0:
                raise ArenaBrowserRequestError("native subdual burden cannot be projected safely")
            visible_states['stunned'] = stun_active_at(stun_until,
                candidate.encounter.time)
            visible_states['subdual_unconscious'] = subdual >= hit_points if subdual else False
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
                    "conditions": self._condition_labels(visible_states),
                    "stun_remaining_seconds": stun_remaining,
                    "subdual_damage": subdual,
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
            if type(value) is bool and value:
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
        from weapon import WeaponInstance, native_forearm_buckler_attachment

        registry = candidate.universe.get_object_registry().object_instances
        from physical_contact import shared_object_holders
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
            jointly_held = {object_id for object_id in reference_ids
                if any(holder_id == being.id for holder_id, _hand
                       in shared_object_holders(candidate.encounter, object_id))}
            root_order = []
            for object_id in reference_ids:
                item = registry.get(object_id)
                if item is not None and getattr(item, "parent_container_id", None) in (None, being.id):
                    root_order.append(object_id)
                elif object_id in jointly_held:
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
                    if parent_id not in (None, being.id) and object_id not in jointly_held:
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
                attachment = (native_forearm_buckler_attachment(item)
                              if type(item) is WeaponInstance and kind == "shield" else None)
                if object_id == armor_id:
                    if type(item) is not ArmorInstance:
                        raise ValueError("native armor slot does not reference an Armor Object")
                    status = "equipped armor"
                elif object_id in body_slots:
                    status = (f"held shield at {body_slots[object_id]} (native shield reference)"
                              if kind == "shield" else f"readied in {body_slots[object_id]}")
                elif (attachment is not None and attachment["owner_id"] == being.id
                      and object_id in being.possessions and parent_id == being.id):
                    status = f"attached to {attachment['arm']} forearm"
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
        allowed_keys = expected | {"ground_equipment", "equipment_mode", "opponent_strategy",
                                  "encounter_mode", "strategy_a", "strategy_b",
                                  "root_seed", "size_categories", "authored_scenario"}
        if (type(payload) is not dict or not expected <= set(payload)
                or set(payload) - allowed_keys):
            raise ArenaBrowserRequestError("Generate requires XP, dimensions, and supported Arena options")
        opponent_strategy = payload.get("opponent_strategy", "none")
        if opponent_strategy not in ("none", "attack_only", "defense_only"):
            raise ArenaBrowserRequestError("opponent_strategy must be none, attack_only, or defense_only")
        encounter_mode = payload.get("encounter_mode", "player_vs_arena")
        if encounter_mode not in ("player_vs_arena", "arena_vs_arena"):
            raise ArenaBrowserRequestError("encounter_mode must be player_vs_arena or arena_vs_arena")
        strategies = ["none", opponent_strategy]
        if encounter_mode == "arena_vs_arena":
            strategies = [payload.get("strategy_a"), payload.get("strategy_b")]
            if any(value not in ("attack_only", "defense_only") for value in strategies):
                raise ArenaBrowserRequestError("Arena vs Arena requires two supported independent strategies")
            # The legacy one-sided selector has no assignment in spectator mode.
            opponent_strategy = "none"
        starting_experience = _parse_decimal(payload, "starting_experience", 0)
        width_cells = _parse_decimal(payload, "width_cells", 5)
        height_cells = _parse_decimal(payload, "height_cells", 5)
        size_categories = payload.get("size_categories", {"player": None, "opponent": None})
        categories = ("diminutive","tiny","small","medium","large","huge","gargantuan","colossal")
        if (type(size_categories) is not dict or set(size_categories) != {"player","opponent"}
                or any(value is not None and value not in categories for value in size_categories.values())):
            raise ArenaBrowserRequestError("size_categories must explicitly name supported categories or null for both participants")
        requested_seed = payload.get("root_seed")
        if requested_seed is not None and (type(requested_seed) is not str or _DECIMAL.fullmatch(requested_seed) is None):
            raise ArenaBrowserRequestError("root_seed must be a nonnegative decimal integer string")
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
        scenario_id = payload.get("authored_scenario", self._authored_draw_scenario.get("scenario_id")
                                  if self._authored_draw_scenario is not None else None)
        if scenario_id not in (None, "ordinary-dagger-draw", "arena-spot-demo"):
            raise ArenaBrowserRequestError("authored_scenario is not an available opt-in scenario")
        if scenario_id == "ordinary-dagger-draw" and self._authored_draw_scenario is None:
            raise ArenaBrowserRequestError("the selected authored scenario is unavailable in this Arena server")
        if scenario_id == "ordinary-dagger-draw" and equipment_mode != "unequipped":
            raise ArenaBrowserRequestError("the authored Dagger Draw scenario requires unequipped protagonists")
        if scenario_id == "ordinary-dagger-draw" and opponent_strategy != "none":
            raise ArenaBrowserRequestError("the authored Dagger Draw scenario requires no autonomous opponent strategy")
        if scenario_id == "ordinary-dagger-draw" and encounter_mode != "player_vs_arena":
            raise ArenaBrowserRequestError("the authored Dagger Draw scenario is available in Player vs Arena mode")
        if scenario_id == "arena-spot-demo" and (opponent_strategy != "none"
                or encounter_mode != "player_vs_arena"):
            raise ArenaBrowserRequestError(
                "The authored Spot exercise requires Player vs Arena mode with no autonomous opponent strategy")
        if "attack_only" in strategies and equipment_mode != "equipped":
            raise ArenaBrowserRequestError(
                "Attack only requires the Arena's native equipped Being kit; choose equipped protagonists.")

        # Serialize generation with all session edits/reads. The prior candidate
        # stays active until a complete new candidate and native RNG owner exist.
        with self._lock:
            root_seed = self._root_seed_factory() if requested_seed is None else int(requested_seed, 10)
            if type(root_seed) is not int or root_seed < 0:
                raise ArenaBrowserRequestError("host root seed source must return a nonnegative integer")
            try:
                candidate = initialize_two_being_arena(
                    starting_experience, width_cells, height_cells, root_seed,
                    ground_item_descriptions=item_descriptions,
                    ground_loadout_profile=loadout_profile,
                    equipment_mode=equipment_mode)
                candidate.participants[0].native.being.size_category=size_categories["player"]
                candidate.participants[1].native.being.size_category=size_categories["opponent"]
                self._validate_initial_equipment_provenance(candidate)
                if scenario_id is not None:
                    if scenario_id == "ordinary-dagger-draw":
                        from arena_authored_draw_scenario import author_scenario
                        author_scenario(candidate, self._authored_draw_scenario)
                    else:
                        from arena_authored_spot_scenario import author_scenario
                        author_scenario(candidate)
                        # Apply authored optics before this candidate is
                        # published to the browser or its player projection.
                        from arena_perception import initialize_arena_perception
                        initialize_arena_perception(candidate.encounter)
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
            self._authored_scenario_id = scenario_id
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
            self._encounter_mode = encounter_mode
            self._arena_strategies = strategies
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
            self._authored_scenario_id = None
            self._encounter_name = self._player_name = None
            self._rng_cursor = None
            self._opponent_strategy = "none"
            self._encounter_mode = "player_vs_arena"
            self._arena_strategies = ["none", "none"]
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

    def choose_ready_preparation(self, payload):
        from activities import ReadyPreparationAction
        from arena_perception import ArenaPerceptionLedger
        if type(payload) is not dict or set(payload) != {"handle", "motion"}:
            raise ArenaBrowserRequestError("Ready requires a visible Weapon handle and selected motion")
        handle, motion = payload["handle"], payload["motion"]
        with self._lock:
            if self._active is None or type(handle) is not str or type(motion) is not str:
                raise ArenaBrowserRequestError("Ready target or attack motion is unavailable")
            if not _has_native_transactional_action_contract(ReadyPreparationAction):
                raise ArenaBrowserRequestError("The native Ready-preparation Choice contract is unavailable")
            entity_id = next((key for key, value in self._view_handles.items()
                              if value == handle), None)
            player = self._active.participants[0].native.being
            ledger = object.__getattribute__(player, "__dict__").get("_arena_perception_ledger")
            if type(ledger) is not ArenaPerceptionLedger or ledger.observer_id != player.id:
                raise ArenaBrowserRequestError("player perception evidence is unavailable")
            evidence = None if entity_id is None else next(
                (row for row in ledger.current if row.entity_id == entity_id), None)
            options, reason = self._ready_preparation_options_unlocked(
                self._active, player, entity_id, evidence)
            option = next((row for row in options if row["motion"] == motion), None)
            if option is None:
                raise ArenaBrowserRequestError(reason)
            action = ReadyPreparationAction(self._active.encounter, player.id,
                entity_id, motion, self._active.encounter.time)
            try:
                if not self._active.encounter.initiated:
                    self._active.encounter.activate_arena_for_player_action(
                        player.id, action, rng_owner=self._rng_cursor)
                else:
                    self._active.encounter.schedule_action(action)
            except Exception as exc:
                raise ArenaBrowserRequestError(
                    "native Ready Choice was not accepted; Arena state is unchanged") from exc
            self._selected_entity_handle = handle
            return self._view_unlocked()

    def choose_delay(self, payload):
        from activities import DelayAction
        if type(payload) is not dict or set(payload) != {"defense"}:
            raise ArenaBrowserRequestError("Delay requires a selected defense allocation")
        defense = payload["defense"]
        if type(defense) is not int or defense < 0:
            raise ArenaBrowserRequestError("Delay defense allocation must be a nonnegative whole number")
        with self._lock:
            if self._active is None:
                raise ArenaBrowserRequestError("Generate an Encounter before choosing Delay")
            if not _has_native_transactional_action_contract(DelayAction):
                raise ArenaBrowserRequestError("The native Delay Action contract is unavailable")
            player = self._active.participants[0].native.being
            action = DelayAction(self._active.encounter, player.id, defense,
                                 self._active.encounter.time)
            try:
                if not self._active.encounter.initiated:
                    self._active.encounter.activate_arena_for_player_action(
                        player.id, action, rng_owner=self._rng_cursor)
                else:
                    self._active.encounter.schedule_action(action)
            except Exception as exc:
                raise ArenaBrowserRequestError(
                    "native Delay Choice was not accepted; Arena state is unchanged") from exc
            return self._view_unlocked()

    def choose_spot(self, payload):
        """Accept a native target-free Spot without returning hidden target IDs."""
        if type(payload) is not dict or payload:
            raise ArenaBrowserRequestError("Spot accepts an empty request")
        return self.choose_discovery({'sense': 'spot'})

    def choose_discovery(self, payload):
        """Accept one native target-free discovery Action."""
        if type(payload) is not dict or set(payload) != {'sense'}:
            raise ArenaBrowserRequestError("Discovery accepts only a Search, Spot, or Listen choice")
        sense = payload['sense']
        if sense not in ('search', 'spot', 'listen'):
            raise ArenaBrowserRequestError("Unsupported discovery Action")
        from activities import SpotAction
        with self._lock:
            candidate = self._active
            if (candidate is None or self._authored_scenario_id != "arena-spot-demo"
                    or self._encounter_mode != "player_vs_arena"
                    or not candidate.encounter.initiated
                    or not _has_native_transactional_action_contract(SpotAction)):
                raise ArenaBrowserRequestError("Native target-free discovery is unavailable in this scenario state.")
            player = candidate.participants[0].native.being
            if any(item.id in candidate.encounter.pending_action_list
                   or any(item.id in record.view.action_ids
                          and record.view.state in ("accepted", "executing")
                          for record in candidate.encounter._choice_book._choices.values())
                   for item in _native_spot_actions(candidate, player.id, sense)):
                raise ArenaBrowserRequestError(f"A native {sense.title()} Action is already underway.")
            if any(item.id in candidate.encounter.pending_action_list
                   or any(item.id in record.view.action_ids
                          and record.view.state in ("accepted", "executing")
                          for record in candidate.encounter._choice_book._choices.values())
                   for item in _native_spot_actions(candidate, player.id)):
                raise ArenaBrowserRequestError("A native discovery Action is already underway.")
            try:
                from attention_intent import accept_discovery_attention
                result = accept_discovery_attention(candidate.encounter, player.id, sense)
            except (TypeError, ValueError, RuntimeError) as exc:
                raise ArenaBrowserRequestError(
                    "Native discovery Choice was not accepted; hidden target details are unavailable.") from exc
            if not result.accepted:
                raise ArenaBrowserRequestError(
                    "Native discovery Choice was not accepted; hidden target details are unavailable.")
            return self._view_unlocked()

    def choose_pause_action(self, payload):
        if payload!={}:raise ArenaBrowserRequestError("Pause accepts an empty request")
        with self._lock:
            if self._active is None:raise ArenaBrowserRequestError("Generate an Encounter before pausing")
            candidate=self._active; player=candidate.participants[0].native.being
            book=candidate.encounter._choice_book
            action=next((candidate.universe.get_event_by_id(aid)
                for aid in candidate.encounter.pending_action_list
                if candidate.universe.get_event_by_id(aid) is not None
                and candidate.universe.get_event_by_id(aid).actor_id==player.id
                and book._states.get(aid)=='executing' and not book.is_paused(aid)),None)
            if action is None:raise ArenaBrowserRequestError("No eligible started player Action can be paused")
            try:book.pause_action(action.id)
            except Exception as exc:raise ArenaBrowserRequestError(str(exc)) from exc
            return self._view_unlocked()

    def choose_resume_action(self, payload):
        if payload!={}:raise ArenaBrowserRequestError("Resume accepts an empty request")
        with self._lock:
            if self._active is None:raise ArenaBrowserRequestError("Generate an Encounter before resuming")
            candidate=self._active; player=candidate.participants[0].native.being
            book=candidate.encounter._choice_book
            action=next((candidate.universe.get_event_by_id(aid)
                for aid in candidate.encounter.pending_action_list
                if candidate.universe.get_event_by_id(aid) is not None
                and candidate.universe.get_event_by_id(aid).actor_id==player.id
                and book.is_paused(aid)),None)
            if action is None:raise ArenaBrowserRequestError("No paused player Action is available to resume")
            try:book.resume_action(action.id)
            except Exception as exc:raise ArenaBrowserRequestError(str(exc)) from exc
            return self._view_unlocked()

    def advance_one_second(self, *, trace_request_id=None, trace_client_sequence=None):
        """Commit exactly the native next boundary for the accepted player decision."""
        with self._lock:
            if self._active is None:
                raise ArenaBrowserRequestError("Generate an Encounter before advancing")
            candidate = self._active
            if self._encounter_mode == "arena_vs_arena" and not candidate.encounter.initiated:
                from activities import RunAction
                actor = candidate.participants[0].native.being
                action = RunAction(candidate.universe, actor.id, candidate.encounter.time,
                                   duration=1, minimum_distance=0.1, experience=0)
                try:
                    candidate.encounter.activate_arena_for_player_action(
                        actor.id, action, rng_owner=self._rng_cursor)
                    self._player_action_id = action.id
                except Exception as exc:
                    raise ArenaBrowserRequestError(
                        "Arena controller could not activate the native Encounter; state is unchanged") from exc
            player = candidate.participants[0].native.being
            before_time = candidate.encounter.time
            before_position = player.get_position()
            before_cell = self._trace_cell(candidate, before_position)
            accepted_plan = self._movement_plan
            ready_preparation_action = self._player_base_action(candidate, player, "ready object")
            ready_preparation_pending = self._melee_action_pending(candidate, ready_preparation_action)
            delay_pending = self._melee_action_pending(candidate,
                self._player_base_action(candidate, player, "delay"))
            melee_action = self._player_melee_action(candidate, player)
            melee_pending = self._melee_action_pending(candidate, melee_action)
            touch_action = self._player_touch_action(candidate, player)
            touch_pending = self._melee_action_pending(candidate, touch_action)
            grappling_action = self._grappling_action_view(candidate, player)
            grappling_pending = (grappling_action is not None
                                  and grappling_action["status"] == "executing")
            from physical_contact import active_contact_state
            active_grips, active_controls = active_contact_state(candidate.encounter)
            contact_wait_pending = any(row[5] >= before_time + 1
                                       for row in (*active_grips, *active_controls))
            feint_action = self._player_feint_action(candidate, player)
            feint_pending = self._melee_action_pending(candidate, feint_action)
            coup_pending = self._melee_action_pending(candidate,
                self._player_base_action(candidate,player,"coup de grace"))
            object_strike_pending = self._melee_action_pending(candidate,
                self._player_base_action(candidate,player,"strike object"))
            disarm_pending = self._melee_action_pending(candidate,
                self._player_base_action(candidate,player,"disarm"))
            player_defense = self._latest_melee_defense(candidate, player)
            player_defense_view = self._defense_action_view(candidate, player)
            player_defense_pending = (self._melee_defense_pending(candidate, player_defense)
                or (player_defense_view is not None and player_defense_view["status"]
                    in ("accepted", "preparing", "committed")))
            action_program_pending = any(
                record.view.state in ("accepted", "executing")
                and any(member.action.actor_id == player.id
                        and type(member.action.end_time) in (int, float)
                        and member.action.end_time > before_time
                        for member in record.members)
                for record in candidate.encounter._choice_book._choices.values())
            opponent = candidate.participants[1].native.being
            opponent_melee_pending = self._opponent_melee_pending(candidate, opponent)
            controller_decisions = {
                index: self._opponent_decision(candidate, index)
                for index in self._autonomous_participant_indices()
                if candidate.encounter.initiated
            }
            if self._encounter_mode == "arena_vs_arena":
                self._resolve_shared_movement_destinations(controller_decisions)
            opponent_decision = controller_decisions.get(1, {"kind": "none", "reason": "strategy_disabled"})
            if self._encounter_mode == "arena_vs_arena":
                opponent_decision = controller_decisions.get(1, {"kind": "none", "reason": "strategy_disabled"})
            opponent_can_act = any(row["kind"] in ("attack", "move", "defend", "prepare")
                                   for row in controller_decisions.values())
            self._opponent_attack_refusal = opponent_decision["reason"]
            if (self._player_action_id is None and self._pickup_action_id is None
                    and self._ready_weapon_action_id is None and not melee_pending
                    and not ready_preparation_pending
                    and not delay_pending
                    and not touch_pending
                    and not grappling_pending
                    and not contact_wait_pending
                    and not feint_pending
                    and not coup_pending and not object_strike_pending
                    and not disarm_pending
                    and not action_program_pending
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
                    and not ready_preparation_pending
                    and not delay_pending
                    and not melee_pending and not player_defense_pending
                    and not touch_pending
                    and not grappling_pending
                    and not contact_wait_pending
                    and not feint_pending
                    and not coup_pending and not object_strike_pending
                    and not disarm_pending
                    and not action_program_pending
                    and not opponent_melee_pending and not opponent_can_act):
                self._trace_advance_state(candidate, trace_request_id, trace_client_sequence,
                                          before_time, before_position, before_cell, None,
                                          "refused", reason="run_choice_resolved")
                raise ArenaBrowserRequestError("the accepted Run Choice has already resolved")
            if (self._movement_plan is None and self._pickup_action_id is not None
                    and self._pickup_action_outcome is not None
                    and not (self._ready_weapon_action_id is not None
                             and self._ready_weapon_action_outcome is None)
                    and not ready_preparation_pending
                    and not delay_pending
                    and not melee_pending and not player_defense_pending
                    and not touch_pending
                    and not grappling_pending
                    and not contact_wait_pending
                    and not feint_pending
                    and not coup_pending and not object_strike_pending
                    and not disarm_pending
                    and not action_program_pending
                    and not opponent_melee_pending and not opponent_can_act):
                raise ArenaBrowserRequestError("the accepted Pick up Choice has already resolved")
            if (self._movement_plan is None and self._ready_weapon_action_id is not None
                    and self._ready_weapon_action_outcome is not None and not melee_pending
                    and not ready_preparation_pending
                    and not delay_pending
                    and not melee_pending and not player_defense_pending
                    and not touch_pending
                    and not grappling_pending
                    and not contact_wait_pending
                    and not feint_pending
                    and not coup_pending and not object_strike_pending
                    and not disarm_pending
                    and not action_program_pending
                    and not opponent_melee_pending and not opponent_can_act):
                raise ArenaBrowserRequestError("the accepted Ready weapon Choice has already resolved")
            try:
                for actor_index, decision in controller_decisions.items():
                    if decision["kind"] == "attack":
                        self._schedule_opponent_attack(candidate, actor_index, decision)
                    elif decision["kind"] in ("defend", "prepare"):
                        self._schedule_opponent_defense(candidate, decision)
                    elif decision["kind"] == "move":
                        self._trace.native_advance(
                            trace_request_id, trace_client_sequence,
                            f"arena_controller={actor_index} decision=approach rate=sprint facing_policy=turn boundary={candidate.encounter.last_processed_boundary + 1}")
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
                for actor_index, decision in controller_decisions.items():
                    if decision["kind"] != "move":
                        continue
                    opponent_id = candidate.participants[actor_index].native.being.id
                    movement_intents.append(MovementIntent(
                        opponent_id, decision["destination"], "sprint",
                        f"{candidate.encounter.id}/arena-controller-{actor_index}-approach/boundary:{next_boundary}",
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
                if touch_action is not None and touch_action.end_time <= candidate.encounter.time:
                    touch_result = candidate.encounter.inspect_committed(
                        int(candidate.encounter.time)).action(touch_action.id)
                    self._trace.native_advance(trace_request_id, trace_client_sequence,
                        f"action=touch outcome={touch_result.facts.outcome}")
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
                            else (type(exc.__cause__).__name__
                                  if exc.__cause__ is not None else type(exc).__name__)))
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
            if (action is None or getattr(action, "actor_id", None) != actor_id
                    or getattr(action, "event_type", None) == "hold"):
                continue
            if type(action) is MeleeStrike:
                # Charge's attack is the culmination of its movement; treating
                # that same Action as an additional demanding task halves the
                # very run-in speed the adopted Charge test requires.
                if action.charge:
                    continue
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
