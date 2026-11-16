#!/usr/bin/env python3
"""Fresh-process native Encounter resume proof; independent of Arena packages."""
from __future__ import annotations

import hashlib
import json
import math
import platform
import resource
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "examples"))

import encounter_delta_headless as delta  # noqa: E402
from action_choice import ChoiceDraft, ChoiceMember, ChoiceView, _Accepted, declaration  # noqa: E402
from action_evaluation import (ActionProposal, DamageEffect, DelayDefenseEffect,
    EffectIdentity, PracticeEffect)  # noqa: E402
from activities import DelayAction, RunAction  # noqa: E402
from atomic_publication import RNGCursor  # noqa: E402
from being import BeingInstance  # noqa: E402
from encounter import Encounter  # noqa: E402
from event import Event  # noqa: E402
from library import Library  # noqa: E402
from melee_combat import MeleeStrike  # noqa: E402
from observer_proposals import LifecycleEffect  # noqa: E402
from scheduling import PreparedSchedule  # noqa: E402
from spatial.geometry import Sphere  # noqa: E402
from spatial.state import CartesianPosition  # noqa: E402
from universe import Universe  # noqa: E402
from weapon import WeaponInstance  # noqa: E402
from physical_fatigue import PhysicalFatigueState  # noqa: E402
from experience import SkillUse, BatchSkillUse, SkillExercise  # noqa: E402
from frozen_practice import CandidatePracticeUse  # noqa: E402
from strategy import Strategy  # noqa: E402


SCHEMA = "universe.headless-native-resume/1"
CHECKPOINT_BOUNDARY = 4
ATTACK_ID = "action-native-dagger-strike"
BEING_IDS = ("being-ada", "being-bram")
WEAPON_ID = "weapon-ada-dagger"


class ResumeRejected(ValueError):
    pass


def _source_compatibility():
    """Pin interpreter, source, Encounter rules and Library source bytes."""
    roots = [ROOT / "src", ROOT / "docs/encounters"]
    paths = [ROOT / "examples/encounter_delta_headless.py",
             ROOT / "examples/native_headless_resume.py"]
    for root in roots:
        if root.is_file():
            paths.append(root)
        else:
            paths.extend(path for path in root.rglob("*") if path.is_file()
                         and (path.suffix == ".py" or path.suffix == ".json"
                              or root.name == "encounters" and path.suffix == ".md"))
    h = hashlib.sha256()
    for path in sorted(set(paths)):
        relative = path.relative_to(ROOT).as_posix().encode("utf-8")
        data = path.read_bytes()
        h.update(len(relative).to_bytes(4, "big")); h.update(relative)
        h.update(len(data).to_bytes(8, "big")); h.update(data)
    return {"python": list(sys.version_info[:3]), "source_and_rules_sha256": h.hexdigest(),
            "library_profile": "src/config; Human and Dagger definitions pinned by digest"}


def _canonical(value):
    return delta.canonical_bytes(value)


def _seal(body):
    return hashlib.sha256(_canonical(body)).hexdigest()


def _strict_json(data):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ResumeRejected("duplicate JSON key")
            result[key] = value
        return result
    try:
        return json.loads(data.decode("utf-8"), object_pairs_hook=unique,
                          parse_constant=lambda _v: (_ for _ in ()).throw(ResumeRejected("non-finite JSON number")))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ResumeRejected("checkpoint JSON is malformed") from exc


def _decode(value):
    if type(value) is list:
        return tuple(_decode(item) for item in value)
    if type(value) is dict:
        if set(value) == {"$type", "value"} and value["$type"] == "CartesianPosition":
            coords = value["value"]
            if type(coords) is not list or len(coords) != 3:
                raise ResumeRejected("invalid encoded Cartesian position")
            return CartesianPosition(*coords)
        if (set(value) == {"$type", "fields"}
                and value["$type"] == "physical_fatigue.PhysicalFatigueState"):
            fields = value["fields"]
            if type(fields) is not dict or set(fields) != {"q", "b"}:
                raise ResumeRejected("invalid physical fatigue state")
            return PhysicalFatigueState(**fields)
        if set(value) == {"$type", "fields"}:
            classes = {"experience.SkillUse": SkillUse,
                       "experience.BatchSkillUse": BatchSkillUse,
                       "experience.SkillExercise": SkillExercise,
                       "frozen_practice.CandidatePracticeUse": CandidatePracticeUse,
                       "action_evaluation.EffectIdentity": EffectIdentity}
            cls = classes.get(value["$type"])
            if cls is None:
                raise ResumeRejected("unsupported persisted native dataclass")
            fields = {key: _decode(item) for key, item in value["fields"].items()}
            try:
                return cls(**fields)
            except (TypeError, ValueError) as exc:
                raise ResumeRejected("invalid persisted native dataclass") from exc
        return {key: _decode(item) for key, item in value.items()}
    return value


def _tuple_tree(value):
    if type(value) is list:
        return tuple(_tuple_tree(item) for item in value)
    if type(value) is dict:
        return {key: _tuple_tree(item) for key, item in value.items()}
    return value


def _capture_resume_artifact(*, seed=0, action_id_prefix=""):
    base = delta.build_demo(until=CHECKPOINT_BOUNDARY, seed=seed,
        action_id_prefix=action_id_prefix)
    checkpoint = base["checkpoint"]
    if checkpoint["boundary"] != CHECKPOINT_BOUNDARY:
        raise AssertionError("fixture did not reach the intended quiescent boundary")
    body = {
        "schema": SCHEMA,
        "compatibility": _source_compatibility(),
        "initial_state": base["initial"],
        "deltas": [row["delta"] for row in base["boundaries"]],
        "checkpoint": checkpoint,
        "native_inputs": {
            "history": base["native_inputs"],
            "continuation": {
                "after_boundary": CHECKPOINT_BOUNDARY,
                "action": {"kind": "melee_strike", "action_id": ATTACK_ID,
                    "actor_id": BEING_IDS[0], "target_id": BEING_IDS[1],
                    "weapon_id": WEAPON_ID, "motion": "thrust", "reach": 2},
                "steps": 5,
            },
        },
    }
    body["integrity_sha256"] = _seal(body)
    return base, body


def save_checkpoint(path):
    _base, body = _capture_resume_artifact()
    path = Path(path)
    path.write_bytes(_canonical(body))
    return body


def validate_artifact(body):
    required = {"schema", "compatibility", "initial_state", "deltas", "checkpoint",
                "native_inputs", "integrity_sha256"}
    if type(body) is not dict or set(body) != required or body["schema"] != SCHEMA:
        raise ResumeRejected("checkpoint schema mismatch")
    unsigned = dict(body); supplied = unsigned.pop("integrity_sha256")
    if type(supplied) is not str or _seal(unsigned) != supplied:
        raise ResumeRejected("checkpoint integrity digest mismatch")
    if body["compatibility"] != _source_compatibility():
        raise ResumeRejected("Encounter source, rules, Library or Python compatibility mismatch")
    checkpoint = body["checkpoint"]
    inputs = body["native_inputs"]
    if (type(inputs) is not dict or set(inputs) != {"history", "continuation"}
            or type(inputs["history"]) is not dict
            or set(inputs["history"]) != {"schema", "seed", "boundaries"}
            or type(inputs["history"]["seed"]) is not int):
        raise ResumeRejected("recorded native input manifest is invalid")
    if (inputs["history"] != delta.native_input_manifest(inputs["history"]["seed"])
            or type(inputs["continuation"]) is not dict
            or set(inputs["continuation"]) != {"after_boundary", "action", "steps"}
            or inputs["continuation"]["after_boundary"] != CHECKPOINT_BOUNDARY
            or inputs["continuation"]["steps"] != 5
            or type(inputs["continuation"]["action"]) is not dict
            or set(inputs["continuation"]["action"]) != {
                "kind", "action_id", "actor_id", "target_id", "weapon_id", "motion", "reach"}
            or inputs["continuation"]["action"]["kind"] != "melee_strike"):
        raise ResumeRejected("recorded native input manifest is invalid")
    expected_checkpoint = {"boundary", "time", "start_time", "state", "finished_action_ids",
                           "choice_state", "choice_counter", "closed_draft_ids",
                           "schedule_revision", "action_history"}
    if type(checkpoint) is not dict or set(checkpoint) != expected_checkpoint:
        raise ResumeRejected("checkpoint field closure mismatch")
    if (checkpoint["boundary"] != CHECKPOINT_BOUNDARY
            or checkpoint["time"] != CHECKPOINT_BOUNDARY
            or checkpoint["start_time"] != 0
            or type(checkpoint["finished_action_ids"]) is not list
            or type(checkpoint["action_history"]) is not list
            or type(checkpoint["choice_counter"]) is not int
            or type(checkpoint["schedule_revision"]) is not int):
        raise ResumeRejected("checkpoint cursor or scheduler metadata is invalid")
    if len(body["deltas"]) != checkpoint["boundary"]:
        raise ResumeRejected("history does not end at the checkpoint boundary")
    try:
        reconstructed = delta.replay(body["initial_state"], body["deltas"])
    except delta.DeltaError as exc:
        raise ResumeRejected(f"committed delta history rejected: {exc}") from exc
    if _canonical(reconstructed) != _canonical(checkpoint["state"]):
        raise ResumeRejected("checkpoint snapshot differs from initial+delta reconstruction")
    committed_events = [event for delta_row in body["deltas"]
                        for event in delta_row["events"]]
    if _canonical(committed_events) != _canonical(checkpoint["action_history"]):
        raise ResumeRejected("checkpoint Action history differs from its boundary Event stream")
    _validate_native_history(checkpoint)
    return checkpoint


def _validate_native_history(checkpoint):
    events = checkpoint["action_history"]
    expected_event_fields = {"event_id", "action_class", "event_type", "parent_event_id",
        "action_id", "actor_id", "target_id", "start_time", "end_time", "outcome",
        "target_ids", "proposal_effects", "proposal_metadata", "choice_id",
        "choice_member_key", "choice", "action_data", "effect_ids"}
    if any(type(row) is not dict or set(row) != expected_event_fields for row in events):
        raise ResumeRejected("committed Event field closure mismatch")
    action_ids = [row.get("action_id") for row in events if type(row) is dict]
    if (len(action_ids) != len(events) or len(set(action_ids)) != len(action_ids)
            or action_ids != checkpoint["finished_action_ids"]):
        raise ResumeRejected("completed native Event identities do not match the finished queue")
    if len(events) != 4 or [row["action_class"] for row in events] != [
            "RunAction", "DelayAction", "RunAction", "RunAction"]:
        raise ResumeRejected("checkpoint contains an unsupported historical Action family")
    choice_ids = []
    grouped = {}
    for row in events:
        if (row["event_id"] != row["action_id"]
                or row["parent_event_id"] != "headless-encounter"
                or row["outcome"] != "success"
                or type(row["effect_ids"]) is not list
                or type(row["choice_id"]) is not str):
            raise ResumeRejected("committed historical Event identity/outcome is inconsistent")
        if (type(row["start_time"]) not in (int, float)
                or type(row["end_time"]) not in (int, float)
                or row["start_time"] < checkpoint["start_time"]
                or row["end_time"] > checkpoint["time"]):
            raise ResumeRejected("committed historical Event lies outside the checkpoint timeline")
        grouped.setdefault(row["choice_id"], row["choice"])
        if grouped[row["choice_id"]] != row["choice"]:
            raise ResumeRejected("members disagree on their committed Choice packet")
        choice = row["choice"]
        if (type(choice) is not dict or set(choice) != {
                "id", "version", "state", "action_ids", "first_start", "origin", "members"}
                or type(choice["members"]) is not list):
            raise ResumeRejected("committed Choice packet field closure mismatch")
        for member in choice["members"]:
            if type(member) is not dict or set(member) != {
                    "key", "action_id", "target_action_key", "priority_penalty", "packet"}:
                raise ResumeRejected("committed Choice member field closure mismatch")
            if type(member["packet"]) is not dict:
                raise ResumeRejected("committed scheduler packet is malformed")
        expected_action_fields = {
            "RunAction": {"minimum_distance", "practice_experience", "start_position", "activity_started"},
            "DelayAction": {"defense"}}
        if (type(row["action_data"]) is not dict
                or set(row["action_data"]) != expected_action_fields[row["action_class"]]):
            raise ResumeRejected("committed Action field closure mismatch")
    choices = list(grouped.values())
    if len(choices) != checkpoint["choice_counter"]:
        raise ResumeRejected("ChoiceBook counter does not match its completed programs")
    if len(checkpoint["closed_draft_ids"]) != len(choices):
        raise ResumeRejected("settled ChoiceBook draft history is incomplete")
    if len(choices) != 3 or any(choice["state"] != "finished"
                                or choice["origin"] not in ("choice", "single-adapter")
                                or any(member["priority_penalty"] is not None for member in choice["members"])
                                for choice in choices):
        raise ResumeRejected("history includes a Choice program outside the settled non-repeat closure")
    summary = checkpoint["choice_state"]
    if (type(summary) is not dict or summary.get("version") != 1
            or summary.get("reservations") != []
            or set(summary.get("actions", {})) != set(action_ids)
            or any(state != "finished" for state in summary["actions"].values())):
        raise ResumeRejected("checkpoint ChoiceBook summary is not fully settled")
    state = checkpoint["state"]
    expected_encounter_fields = {"id", "difficulty_class", "participants",
        "pending_action_ids", "cancelled_action_ids", "time", "start_time",
        "last_processed_boundary", "coordinator_time", "interval_start",
        "initiated", "awareness_by_observer"}
    expected_being_fields = {"id", "type", "name", "definition_key", "position",
        "hit_points", "armor_id", "body_parts", "states", "posture",
        "size_category", "hex_facing", "fatigue_level", "physical_fatigue",
        "physiology_id", "geometry", "abilities", "skills", "weapon_skills",
        "skill_experience", "skill_practice_baselines", "skill_use_history",
        "strategy", "personal_history", "possessions", "weapons", "armed"}
    expected_weapon_fields = {"id", "type", "name", "definition_key", "position",
        "parent_container_id", "hit_points", "weapon_size", "attacks", "geometry"}
    if type(state) is not dict or set(state) != {
            "schema", "encounter", "beings", "weapons", "rng_state"}:
        raise ResumeRejected("native current-state field closure mismatch")
    if type(state["encounter"]) is not dict or set(state["encounter"]) != expected_encounter_fields:
        raise ResumeRejected("native Encounter field closure mismatch")
    if any(type(row) is not dict or set(row) != expected_being_fields
           for row in state["beings"].values()):
        raise ResumeRejected("native Being field closure mismatch")
    if any(type(row) is not dict or set(row) != expected_weapon_fields
           for row in state["weapons"].values()):
        raise ResumeRejected("native Object field closure mismatch")
    enc = state["encounter"]
    if (enc["id"] != "headless-encounter" or enc["time"] != checkpoint["time"]
            or enc["start_time"] != checkpoint["start_time"]
            or enc["last_processed_boundary"] != checkpoint["boundary"]
            or enc["coordinator_time"] != checkpoint["time"]
            or enc["interval_start"] != checkpoint["time"]
            or enc["pending_action_ids"] or enc["cancelled_action_ids"]
            or enc["initiated"] is not True):
        raise ResumeRejected("Encounter cursor or lifecycle differs from quiescent checkpoint")
    if (any(type(row) is not dict or row.get("id") != identity
            or row.get("type") != "BeingInstance" for identity, row in state["beings"].items())
            or any(type(row) is not dict or row.get("id") != identity
            or row.get("type") != "WeaponInstance" for identity, row in state["weapons"].items())):
        raise ResumeRejected("native registry identity/reference mismatch")
    weapon_ids = set(state["weapons"])
    being_ids = set(state["beings"])
    for being in state["beings"].values():
        if (any(identity not in weapon_ids for identity in being["weapons"])
                or any(identity not in weapon_ids for identity in being["possessions"])
                or any(identity is not None and identity not in weapon_ids
                       for identity in being["body_parts"].values())
                or any(identity is not None and identity not in weapon_ids
                       for identity in being["armed"].values())):
            raise ResumeRejected("native custody/awareness reference is dangling")
    if any(observer not in being_ids or any(target not in being_ids for target in targets)
           for observer, targets in enc["awareness_by_observer"].items()):
        raise ResumeRejected("observer knowledge references an absent Being")
    if (set(state["beings"]) != set(BEING_IDS)
            or set(state["weapons"]) != {WEAPON_ID}
            or state["beings"][BEING_IDS[0]]["weapons"] != [WEAPON_ID]
            or state["beings"][BEING_IDS[0]]["armed"].get("right hand") != WEAPON_ID
            or state["beings"][BEING_IDS[1]]["hit_points"] <= 0):
        raise ResumeRejected("checkpoint object inventory/custody closure is unsupported")


def _validate_replay_path_closure(initial_state, delta_row):
    """Reject changes outside the explicitly captured headless projection."""
    encounter_fields = {"difficulty_class", "participants", "pending_action_ids",
        "cancelled_action_ids", "time", "start_time", "last_processed_boundary",
        "coordinator_time", "interval_start", "initiated", "awareness_by_observer"}
    being_fields = {"name", "definition_key", "position", "hit_points", "armor_id",
        "body_parts", "states", "posture", "size_category", "hex_facing",
        "fatigue_level", "physical_fatigue", "physiology_id", "geometry",
        "abilities", "skills", "weapon_skills", "skill_experience",
        "skill_practice_baselines", "skill_use_history", "strategy",
        "personal_history", "possessions", "weapons", "armed"}
    weapon_fields = {"name", "position", "parent_container_id", "hit_points",
        "weapon_size", "attacks", "geometry"}
    nested_maps = {"body_parts", "states", "abilities", "skills", "weapon_skills",
                   "skill_experience", "skill_practice_baselines", "strategy", "armed"}
    for change in delta_row.get("changes", []):
        path = change.get("path")
        if type(path) is not list or not path:
            raise ResumeRejected("delta contains an invalid projection path")
        if path == ["rng_state"]:
            continue
        if len(path) == 2 and path[0] == "encounter" and path[1] in encounter_fields:
            continue
        if path[0] in ("beings", "weapons") and len(path) in (3, 4):
            collection = initial_state.get(path[0], {})
            entity = collection.get(path[1]) if type(collection) is dict else None
            allowed = being_fields if path[0] == "beings" else weapon_fields
            if type(entity) is not dict or path[2] not in allowed:
                raise ResumeRejected("delta property is outside the captured entity field closure")
            if len(path) == 4:
                field, key = path[2], path[3]
                if field not in nested_maps:
                    raise ResumeRejected("delta nested path is outside the captured field closure")
                current = entity.get(field)
                if type(current) is not dict:
                    raise ResumeRejected("delta nested path parent is not a captured map")
                if key not in current and not (
                        field in ("skill_experience", "skill_practice_baselines")
                        and key in ("run", "Dagger")):
                    raise ResumeRejected("delta introduces an unmodeled map entry")
            continue
        raise ResumeRejected("delta property path is outside the captured projection")


def _make_effect(row):
    kinds = {"PracticeEffect": PracticeEffect,
             "DelayDefenseEffect": DelayDefenseEffect,
             "DamageEffect": DamageEffect}
    cls = kinds.get(row["type"])
    if cls is None or set(row) != {"type", "fields"}:
        raise ResumeRejected("unsupported persisted native Action effect")
    return cls(**row["fields"])


def _restore_action_event(row, universe, encounter):
    action_id = row["action_id"]
    data = row["action_data"]
    if row["action_class"] == "RunAction":
        action = RunAction(universe, row["actor_id"], row["start_time"],
            row["end_time"] - row["start_time"], data["minimum_distance"],
            experience=data["practice_experience"], id=action_id)
        action.start_position = _decode(data["start_position"])
        action._activity_started = data["activity_started"]
    elif row["action_class"] == "DelayAction":
        action = DelayAction(encounter, row["actor_id"],
            defense=data["defense"], start_time=row["start_time"], id=action_id)
        action._activity_started = True
    else:
        raise ResumeRejected("unsupported persisted native Action class")
    action.parent_event_id = row["parent_event_id"]
    action.target_id = row["target_id"]
    action.name = row.get("name")
    action.resolution = ActionProposal(
        action_id, row["actor_id"], tuple(row["target_ids"]), row["outcome"],
        tuple(_make_effect(effect) for effect in row["proposal_effects"]), (),
        tuple(tuple(value) for value in row["proposal_metadata"]))
    action._atomic_effect_ids = tuple(EffectIdentity(*effect_id) for effect_id in row["effect_ids"])
    choice = row["choice"]
    action._atomic_lifecycle = LifecycleEffect(
        action_id, action_id, "finished", "pending", "finished", choice["id"],
        "executing", row["end_time"], math_ceil(row["end_time"]), None, None)
    universe.event_history[action_id] = action
    return action


def math_ceil(value):
    import math
    return math.ceil(value)


def _restore_choice_book(checkpoint, encounter, actions):
    book = encounter._choice_book
    grouped = {}
    for event in checkpoint["action_history"]:
        grouped[event["choice_id"]] = event["choice"]
    for choice_id, choice_data in grouped.items():
        members, packets = [], []
        for member_data in choice_data["members"]:
            action = actions[member_data["action_id"]]
            member = ChoiceMember(member_data["key"], action,
                member_data["target_action_key"], member_data["priority_penalty"])
            packet_fields = _decode(member_data["packet"])
            packet = PreparedSchedule(**packet_fields)
            if (packet.action_id != action.id or packet.actor_id != action.actor_id
                    or packet.start_time != action.start_time or packet.end_time != action.end_time):
                raise ResumeRejected("persisted Choice packet does not match its native Action")
            members.append(member); packets.append(packet)
        view = ChoiceView(choice_id, choice_data["version"], choice_data["state"],
                          tuple(choice_data["action_ids"]), choice_data["first_start"])
        signatures = tuple((member.key, declaration(member.action)) for member in members)
        record = _Accepted(view, tuple(members), tuple(packets), signatures, choice_data["origin"])
        book._choices[choice_id] = record
        book._drafts[choice_id] = ChoiceDraft(choice_id, choice_data["version"], tuple(members))
        for member, packet in zip(members, packets):
            book._registered[member.action.id] = (choice_id, packet, declaration(member.action))
            book._states[member.action.id] = "finished"
    book._counter = checkpoint["choice_counter"]
    book._closed_drafts = set(checkpoint["closed_draft_ids"])


def restore_private_checkpoint(body):
    """Validate fully, build privately, then bind the ordinary native step path."""
    checkpoint = validate_artifact(body)
    universe = Universe("Headless delta resume",
        library=Library(config_dir=str(ROOT / "src/config")))
    human = universe.get_being_definition("Human")
    ada = BeingInstance(human, "Ada", id=BEING_IDS[0])
    bram = BeingInstance(human, "Bram", id=BEING_IDS[1])
    for being in (ada, bram):
        universe.add_object(being)
    state = checkpoint["state"]
    for being in (ada, bram):
        row = state["beings"][being.id]
        if row["definition_key"] != "Human":
            raise ResumeRejected("Being definition key is incompatible")
        if row["position"] is not None:
            being.set_position(CartesianPosition(*row["position"]))
        being.set_hit_points(row["hit_points"])
        being.possessions = list(row["possessions"])
        being.weapons = list(row["weapons"])
        being.current.body_parts = dict(row["body_parts"])
        being.current.states.states = dict(row["states"])
        being.set_armor_id(row["armor_id"])
        being.set_posture(row["posture"])
        being.size_category = row["size_category"]
        being.set_hex_facing(row["hex_facing"])
        being.fatigue_level = row["fatigue_level"]
        fatigue = _decode(row["physical_fatigue"])
        being.physical_fatigue = fatigue
        being.physiology_id = row["physiology_id"]
        geometry = row["geometry"]
        if geometry is not None:
            if set(geometry) != {"type", "radius"} or geometry["type"] != "sphere":
                raise ResumeRejected("unsupported native Being geometry")
            being.set_geometry(Sphere(geometry["radius"]))
        being.current.abilities.abilities = dict(row["abilities"])
        being.current.skills.skills = dict(row["skills"])
        being.current.skills.weapon_skills = dict(row["weapon_skills"])
        being.skill_experience = dict(row["skill_experience"])
        being._skill_practice_baselines = dict(row["skill_practice_baselines"])
        try:
            being.skill_use_history = [_decode(item) for item in row["skill_use_history"]]
            if any(type(item) not in (SkillUse, BatchSkillUse)
                   for item in being.skill_use_history):
                raise ResumeRejected("unsupported native skill-use history")
        except (TypeError, ValueError) as exc:
            raise ResumeRejected("unsupported native skill-use history") from exc
        if row["personal_history"] is not None:
            raise ResumeRejected("personal-history continuation is outside this closure")
        being.strategy = Strategy(**row["strategy"])
    weapon_row = state["weapons"][WEAPON_ID]
    if weapon_row["definition_key"] != "Dagger":
        raise ResumeRejected("weapon definition key is incompatible")
    weapon = WeaponInstance(universe.get_weapon_definition("Dagger"), weapon_row["name"])
    weapon.id = WEAPON_ID
    if (weapon.current.hit_points != weapon_row["hit_points"]
            or weapon.current.weapon_size != weapon_row["weapon_size"]
            or delta.canonical_bytes(weapon.current.attacks) != delta.canonical_bytes(weapon_row["attacks"])):
        raise ResumeRejected("Dagger definition/current profile differs from the pinned checkpoint")
    universe.add_object(weapon)
    if weapon_row["geometry"] is not None:
        raise ResumeRejected("fixture weapon geometry is outside the declared closure")
    ada.set_body_part_holds_object("right hand", WEAPON_ID)
    for observer_id, targets in state["encounter"]["awareness_by_observer"].items():
        for target_id in targets:
            if target_id not in state["encounter"]["participants"]:
                raise ResumeRejected("awareness references an absent Being")
    encounter = Encounter(universe, state["encounter"]["difficulty_class"],
        checkpoint["time"], id="headless-encounter", time=checkpoint["time"],
        initiated=True, being_list=list(state["encounter"]["participants"]),
        finished_action_list=list(checkpoint["finished_action_ids"]),
        awareness={key: set(value) for key, value in state["encounter"]["awareness_by_observer"].items()},
        name="Headless delta proof")
    encounter.start_time = checkpoint["start_time"]
    for observer_id, targets in state["encounter"]["awareness_by_observer"].items():
        if observer_id not in BEING_IDS:
            raise ResumeRejected("awareness observer references an absent Being")
    universe.add_event(encounter)
    actions = {}
    for row in checkpoint["action_history"]:
        if row["actor_id"] not in BEING_IDS or row["target_id"] not in (None, *BEING_IDS):
            raise ResumeRejected("historical Event participant reference is outside the closure")
        actions[row["action_id"]] = _restore_action_event(row, universe, encounter)
    _restore_choice_book(checkpoint, encounter, actions)
    universe._schedule_revision = checkpoint["schedule_revision"]
    rng_owner = RNGCursor(_tuple_tree(state["rng_state"]))
    from transactional_progression import _enable_quiescent_headless_resume
    _enable_quiescent_headless_resume(encounter, rng_owner=rng_owner,
        completed_action_ids=tuple(checkpoint["finished_action_ids"]))
    if _canonical(delta.native_state(encounter, rng_owner)) != _canonical(state):
        raise ResumeRejected("reconstructed native Encounter differs from checkpoint projection")
    return universe, encounter, rng_owner


def continue_native(encounter, rng_owner, *, previous_state, prior_action_ids,
                    action_input=None, action_id_prefix=""):
    """Schedule a real melee hit, then commit one quiet boundary via Encounter.step."""
    action_input = action_input or {
        "kind": "melee_strike", "action_id": ATTACK_ID,
        "actor_id": BEING_IDS[0], "target_id": BEING_IDS[1],
        "weapon_id": WEAPON_ID, "motion": "thrust", "reach": 2}
    if type(action_input) is not dict or set(action_input) != {
            "kind", "action_id", "actor_id", "target_id", "weapon_id", "motion", "reach"}:
        raise ResumeRejected("unsupported continuation Action declaration")
    strike = MeleeStrike(encounter, action_input["actor_id"], action_input["target_id"],
                         action_input["weapon_id"], motion=action_input["motion"],
                         reach=action_input["reach"])
    strike.id = action_id_prefix + action_input["action_id"]
    encounter.schedule_action(strike)
    rows = []
    known_actions = set(prior_action_ids)
    steps = 5
    for boundary in range(CHECKPOINT_BOUNDARY + 1, CHECKPOINT_BOUNDARY + steps + 1):
        started = time.perf_counter_ns()
        encounter.step(1)
        native_ns = time.perf_counter_ns() - started
        state = delta.native_state(encounter, rng_owner)
        events = delta._boundary_events(encounter, known_actions, boundary)
        known_actions.update(event["action_id"] for event in events)
        changes = delta._walk(previous_state, state)
        record = {"boundary": boundary, "time": encounter.time, "changes": changes,
                  "events": events, "state_sha256": delta.state_digest(state)}
        replayed = delta.apply_delta(previous_state, record)
        if _canonical(replayed) != _canonical(state):
            raise AssertionError(f"continuation replay mismatch at {boundary}")
        rows.append({"state": state, "delta": record, "step_ns": native_ns})
        previous_state = state
    action_rows = []
    for action_id in encounter.finished_action_list:
        event = encounter.universe.get_event_by_id(action_id)
        action_rows.append({"id": action_id, "type": type(event).__name__,
            "event_type": event.event_type, "start_time": event.start_time,
            "end_time": event.end_time,
            "outcome": getattr(event.resolution, "outcome", None)})
    receipts = []
    for receipt in encounter._atomic_interval_history:
        if receipt.boundary <= CHECKPOINT_BOUNDARY:
            continue
        receipts.append({"boundary": receipt.boundary,
            "action_ids": list(receipt.action_ids),
            "effect_ids": [[row.encounter_id,row.boundary,row.source_action_id,row.channel,row.slot]
                           for row in receipt.effect_ids],
            "rng_state": delta._json_value(receipt.rng_state),
            "inspection_start": receipt.inspection.start,
            "inspection_end": receipt.inspection.end})
    final = {"state": previous_state,
        "time": encounter.time,
        "last_processed_boundary": encounter.last_processed_boundary,
        "start_time": encounter.start_time,
        "pending_action_ids": list(encounter.pending_action_list),
        "finished_action_ids": list(encounter.finished_action_list),
        "cancelled_action_ids": list(encounter.cancelled_action_list),
        "choice_state": encounter._choice_book.summary(),
        "choice_counter": encounter._choice_book._counter,
        "schedule_revision": encounter.universe._schedule_revision,
        "action_rows": action_rows,
        "rng_state": delta._json_value(rng_owner.state),
        "recent_native_receipts": receipts,
        "continuation_deltas": [row["delta"] for row in rows],
        "boundary_states": [{"boundary": row["delta"]["boundary"],
                             "state": row["state"]} for row in rows],
        "native_step_ns": [row["step_ns"] for row in rows]}
    return final


def record_full_timeline(*, seed=0):
    """Record the native control and its reusable action inputs at boundaries 1–9."""
    base, checkpoint = _capture_resume_artifact(seed=seed)
    control = continue_native(base["encounter"], base["rng_owner"],
        previous_state=checkpoint["checkpoint"]["state"],
        prior_action_ids=checkpoint["checkpoint"]["finished_action_ids"],
        action_input=checkpoint["native_inputs"]["continuation"]["action"])
    body = {"schema": "universe.headless-faithful-replay/1",
            "compatibility": checkpoint["compatibility"],
            "checkpoint": checkpoint, "control": control}
    body["integrity_sha256"] = _seal(body)
    return body


def validate_full_timeline(body):
    required = {"schema", "compatibility", "checkpoint", "control", "integrity_sha256"}
    if type(body) is not dict or set(body) != required or body["schema"] != "universe.headless-faithful-replay/1":
        raise ResumeRejected("faithful replay recording schema mismatch")
    unsigned = dict(body); supplied = unsigned.pop("integrity_sha256")
    if type(supplied) is not str or _seal(unsigned) != supplied:
        raise ResumeRejected("faithful replay recording integrity mismatch")
    checkpoint_body = body["checkpoint"]
    validate_artifact(checkpoint_body)
    if body["compatibility"] != checkpoint_body["compatibility"]:
        raise ResumeRejected("recording/checkpoint compatibility differs")
    control = body["control"]
    required_control = {"state", "time", "last_processed_boundary", "start_time",
        "pending_action_ids", "finished_action_ids", "cancelled_action_ids",
        "choice_state", "choice_counter", "schedule_revision", "action_rows",
        "rng_state", "recent_native_receipts", "continuation_deltas",
        "boundary_states", "native_step_ns"}
    if type(control) is not dict or set(control) != required_control:
        raise ResumeRejected("recorded continuation field closure mismatch")
    if (type(control["continuation_deltas"]) is not list
            or any(type(row) is not dict for row in control["continuation_deltas"])
            or [row["boundary"] for row in control["continuation_deltas"]]
                != [5, 6, 7, 8, 9]
            or type(control["boundary_states"]) is not list
            or len(control["boundary_states"]) != 5
            or any(type(row) is not dict or set(row) != {"boundary", "state"}
                   for row in control["boundary_states"])
            or [row["boundary"] for row in control["boundary_states"]]
                != [5, 6, 7, 8, 9]
            or type(control["native_step_ns"]) is not list
            or len(control["native_step_ns"]) != 5
            or any(type(value) is not int or value <= 0
                   for value in control["native_step_ns"])):
        raise ResumeRejected("recorded continuation timeline is incomplete or reordered")
    expected_events = checkpoint_body["checkpoint"]["action_history"]
    if len(expected_events) != 4:
        raise ResumeRejected("recording does not contain the supported boundary-1..4 history")
    deltas = checkpoint_body["deltas"] + control["continuation_deltas"]
    initial_state = checkpoint_body["initial_state"]
    state = initial_state
    action_ids, seen_effects = [], set()
    effects_by_boundary = {}
    if (type(control["action_rows"]) is not list
            or any(type(row) is not dict or set(row) != {
                "id", "type", "event_type", "start_time", "end_time", "outcome"}
                for row in control["action_rows"])):
        raise ResumeRejected("recorded native Action row schema is invalid")
    action_rows = {row.get("id"): row for row in control["action_rows"]
                   if type(row) is dict}
    if len(action_rows) != len(control["action_rows"]):
        raise ResumeRejected("duplicate native Action row identity")
    for boundary, row in enumerate(deltas, 1):
        if row.get("boundary") != boundary or row.get("time") != boundary:
            raise ResumeRejected("full replay boundary/time chronology is inconsistent")
        _validate_replay_path_closure(initial_state, row)
        state = delta.apply_delta(state, row)
        for event in row["events"]:
            if (type(event) is not dict or event.get("event_id") != event.get("action_id")
                    or event.get("parent_event_id") != initial_state["encounter"]["id"]
                    or event.get("actor_id") not in BEING_IDS
                    or event.get("target_id") not in (None, *BEING_IDS)
                    or type(event.get("end_time")) not in (int, float)
                    or not math.isfinite(event["end_time"])
                    or math.ceil(event["end_time"]) != boundary):
                raise ResumeRejected("historical Event identity/cause/time reference is invalid")
            action_id = event["action_id"]
            if action_id in action_ids:
                raise ResumeRejected("duplicate Action/Event identity in one logical Encounter")
            action_ids.append(action_id)
            action = action_rows.get(action_id)
            if (action is None or action.get("type") != event["action_class"]
                    or action.get("outcome") != event["outcome"]
                    or action.get("event_type") != event["event_type"]
                    or action.get("start_time") != event["start_time"]
                    or action.get("end_time") != event["end_time"]):
                raise ResumeRejected("Event outcome/timing differs from the committed Action row")
            event_effects = []
            for effect_id in event["effect_ids"]:
                if (type(effect_id) is not list or len(effect_id) != 5
                        or effect_id[0] != initial_state["encounter"]["id"]
                        or effect_id[1] != boundary or effect_id[2] != action_id
                        or type(effect_id[3]) is not str or type(effect_id[4]) is not int):
                    raise ResumeRejected("Effect identity has a broken causal or boundary reference")
                identity = tuple(effect_id)
                if identity in seen_effects:
                    raise ResumeRejected("duplicate Effect identity in one logical Encounter")
                seen_effects.add(identity); event_effects.append(effect_id)
            for effect in event["proposal_effects"]:
                fields = effect.get("fields", {}) if type(effect) is dict else None
                if (type(fields) is not dict or fields.get("source_action_id") != action_id
                        or fields.get("target_id") not in (None, *BEING_IDS)):
                    raise ResumeRejected("proposal Effect source/recipient reference is inconsistent")
            effects_by_boundary.setdefault(boundary, []).extend(event_effects)
    if action_ids != control["finished_action_ids"] or action_ids != list(action_rows):
        raise ResumeRejected("finished Action queue and chronological Event history disagree")
    if _canonical(state) != _canonical(control["state"]):
        raise ResumeRejected("full delta playback differs from recorded terminal snapshot")
    if (control["time"] != 9 or control["last_processed_boundary"] != 9
            or control["start_time"] != 0
            or control["state"].get("encounter", {}).get("time") != control["time"]
            or control["state"].get("encounter", {}).get("last_processed_boundary")
                != control["last_processed_boundary"]
            or control["state"].get("rng_state") != control["rng_state"]
            or type(control["pending_action_ids"]) is not list
            or type(control["cancelled_action_ids"]) is not list
            or control["pending_action_ids"] or control["cancelled_action_ids"]):
        raise ResumeRejected("native continuation cursor differs from its terminal snapshot")
    control_state = checkpoint_body["checkpoint"]["state"]
    state_by_boundary = {row["boundary"]: row["state"] for row in control["boundary_states"]}
    for row in control["continuation_deltas"]:
        control_state = delta.apply_delta(control_state, row)
        if _canonical(control_state) != _canonical(state_by_boundary[row["boundary"]]):
            raise ResumeRejected("continuation delta differs from its native boundary snapshot")
    receipts = control["recent_native_receipts"]
    receipt_fields = {"boundary", "action_ids", "effect_ids", "rng_state",
                      "inspection_start", "inspection_end"}
    if (type(receipts) is not list or len(receipts) != 5
            or any(type(row) is not dict or set(row) != receipt_fields for row in receipts)
            or [row["boundary"] for row in receipts] != [5, 6, 7, 8, 9]):
        raise ResumeRejected("continuation is missing a committed boundary receipt")
    for receipt in receipts:
        row_events = deltas[receipt["boundary"] - 1]["events"]
        if (receipt["action_ids"] != [event["action_id"] for event in row_events]
                or receipt["effect_ids"] != effects_by_boundary.get(receipt["boundary"], [])):
            raise ResumeRejected("receipt Event/Effect grouping differs from committed history")
    return checkpoint_body, control


def historical_playback(body, boundaries=None):
    """Reconstruct selected timeline boundaries without native Action resolution."""
    started = time.perf_counter_ns()
    checkpoint, control = validate_full_timeline(body)
    deltas = checkpoint["deltas"] + control["continuation_deltas"]
    if boundaries is None:
        boundaries = list(range(0, 10))
    if (type(boundaries) not in (list, tuple) or not boundaries
            or any(type(boundary) is not int or not 0 <= boundary <= 9
                   for boundary in boundaries)):
        raise ResumeRejected("playback query boundary is outside the recorded timeline")
    states = {0: checkpoint["initial_state"]}
    events = {0: []}
    cumulative_events = []
    state = checkpoint["initial_state"]
    for row in deltas:
        state = delta.apply_delta(state, row)
        boundary = row["boundary"]
        states[boundary] = state
        events[boundary] = row["events"]
        cumulative_events.extend(row["events"])
    result = []
    for boundary in boundaries:
        result.append({"boundary": boundary,
                       "time": states[boundary]["encounter"]["time"],
                       "state": states[boundary],
                       "events_at_boundary": events[boundary],
                       "event_history": [event for event in cumulative_events
                                         if math.ceil(event["end_time"]) <= boundary],
                       "state_sha256": delta.state_digest(states[boundary])})
    return {"schema": "universe.headless-historical-playback/1",
            "boundaries": result, "native_resolution_invoked": False,
            "playback_elapsed_ns": time.perf_counter_ns() - started}


def _id_mapping(reference_deltas, candidate_deltas):
    mapping, reverse = {}, {}
    for reference, candidate in zip(reference_deltas, candidate_deltas):
        if reference["boundary"] != candidate["boundary"]:
            raise ResumeRejected("replay boundary correspondence mismatch")
        ref_events, candidate_events = reference["events"], candidate["events"]
        if len(ref_events) != len(candidate_events):
            raise ResumeRejected("replay Event multiplicity differs")
        for left, right in zip(ref_events, candidate_events):
            for key in ("action_class", "event_type", "parent_event_id", "actor_id",
                        "target_id", "start_time", "end_time", "outcome", "target_ids"):
                if left.get(key) != right.get(key):
                    raise ResumeRejected(f"replay Event semantic field differs: {key}")
            for key in ("event_id", "action_id", "choice_id"):
                first, second = left.get(key), right.get(key)
                if first is None and second is None:
                    continue
                if type(first) is not str or type(second) is not str:
                    raise ResumeRejected("replay generated identity is missing or malformed")
                if (first in mapping and mapping[first] != second
                        or second in reverse and reverse[second] != first):
                    raise ResumeRejected("replay generated-identity map is not bijective")
                mapping[first] = second; reverse[second] = first
    return mapping, reverse


def _remap_ids(value, mapping):
    if type(value) is str:
        return mapping.get(value, value)
    if type(value) is list:
        return [_remap_ids(item, mapping) for item in value]
    if type(value) is dict:
        return {_remap_ids(key, mapping): _remap_ids(item, mapping)
                for key, item in value.items()}
    return value


def deterministic_native_reexecution(body, *, action_id_prefix="independent/"):
    """Rerun only recorded legal Action inputs through a fresh native Encounter."""
    started = time.perf_counter_ns()
    checkpoint, control = validate_full_timeline(body)
    if (type(action_id_prefix) is not str or not action_id_prefix
            or action_id_prefix in ("action", "being", "weapon")):
        raise ValueError("reexecution needs a distinct explicit Action-ID prefix")
    inputs = body["checkpoint"]["native_inputs"]
    base = delta.build_demo(until=CHECKPOINT_BOUNDARY,
        seed=inputs["history"]["seed"], inputs=inputs["history"],
        action_id_prefix=action_id_prefix)
    candidate_history = [row["delta"] for row in base["boundaries"]]
    if len(candidate_history) != len(checkpoint["deltas"]):
        raise ResumeRejected("re-executed history length differs")
    continuation_input = inputs["continuation"]["action"]
    candidate_control = continue_native(base["encounter"], base["rng_owner"],
        previous_state=base["checkpoint"]["state"],
        prior_action_ids=base["encounter"].finished_action_list,
        action_input=continuation_input, action_id_prefix=action_id_prefix)
    candidate_deltas = candidate_history + candidate_control["continuation_deltas"]
    reference_deltas = checkpoint["deltas"] + control["continuation_deltas"]
    mapping, reverse = _id_mapping(reference_deltas, candidate_deltas)
    matched = []
    reference_state = checkpoint["initial_state"]
    candidate_state = base["initial"]
    if _canonical(reference_state) != _canonical(candidate_state):
        raise ResumeRejected("re-execution initial state differs")
    candidate_states = [row["actual"] for row in base["boundaries"]]
    candidate_states.extend(row["state"] for row in candidate_control["boundary_states"])
    for index, (expected_delta, actual_delta, actual_state) in enumerate(
            zip(reference_deltas, candidate_deltas, candidate_states), 1):
        reference_state = delta.apply_delta(reference_state, expected_delta)
        candidate_state = delta.apply_delta(candidate_state, actual_delta)
        normalized_reference_state = _remap_ids(reference_state, mapping)
        if _canonical(normalized_reference_state) != _canonical(candidate_state):
            raise ResumeRejected(f"re-executed native state differs at boundary {index}")
        if _canonical(actual_state) != _canonical(candidate_state):
            raise ResumeRejected(f"re-executed boundary snapshot differs from native state at {index}")
        normalized_delta = _remap_ids(expected_delta, mapping)
        normalized_delta.pop("state_sha256", None)
        candidate_compare = dict(actual_delta); candidate_compare.pop("state_sha256", None)
        if _canonical(normalized_delta) != _canonical(candidate_compare):
            raise ResumeRejected(f"re-executed Event/effect/cause/delta differs at boundary {index}")
        matched.append({"boundary": index, "state_sha256": delta.state_digest(candidate_state),
                        "event_count": len(actual_delta["events"]),
                        "property_change_count": len(actual_delta["changes"])})
    normalized_receipts = _remap_ids(control["recent_native_receipts"], mapping)
    if _canonical(normalized_receipts) != _canonical(candidate_control["recent_native_receipts"]):
        raise ResumeRejected("native receipt/effect identity correspondence differs")
    normalized_action_rows = _remap_ids(control["action_rows"], mapping)
    if _canonical(normalized_action_rows) != _canonical(candidate_control["action_rows"]):
        raise ResumeRejected("native Action outcome/order differs")
    for key in ("time", "last_processed_boundary", "start_time", "pending_action_ids",
                "finished_action_ids", "cancelled_action_ids", "choice_state",
                "choice_counter", "schedule_revision", "rng_state"):
        if _canonical(_remap_ids(control[key], mapping)) != _canonical(candidate_control[key]):
            raise ResumeRejected(f"native final Encounter continuation field differs: {key}")
    return {"schema": "universe.headless-native-reexecution/1",
        "boundaries": matched, "event_id_map": mapping,
        "final_rng_state": candidate_control["rng_state"],
        "control_rng_state": control["rng_state"],
        "rng_equal": candidate_control["rng_state"] == control["rng_state"],
        "native_resolution_invoked": True,
        "reexecution_elapsed_ns": time.perf_counter_ns() - started,
        "native_step_ns": [row["step_ns"] for row in base["boundaries"]]
                           + candidate_control["native_step_ns"]}


def _forbidden_runtime_imports():
    forbidden = ("arena_native_snapshot", "arena_session", "arena_controller",
                 "arena_server", "npcgen")
    return sorted(name for name in sys.modules
                  if any(name == prefix or name.startswith(prefix + ".")
                         for prefix in forbidden))


def _main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resume", type=Path, help="validate and continue a saved native checkpoint")
    parser.add_argument("--write-checkpoint", type=Path, help="write the boundary-4 native checkpoint")
    parser.add_argument("--record-full", type=Path, help="record the native control timeline through boundary 9")
    parser.add_argument("--playback", type=Path, help="historically reconstruct a recorded timeline")
    parser.add_argument("--boundary", type=int, action="append", help="playback boundary query; repeatable")
    parser.add_argument("--reexecute", type=Path, help="re-run only the recorded native Action inputs")
    parser.add_argument("--id-prefix", default="independent/", help="independent replay Action-ID namespace")
    args = parser.parse_args(argv)
    if args.playback:
        body = _strict_json(args.playback.read_bytes())
        result = historical_playback(body, args.boundary)
        result["forbidden_runtime_imports"] = _forbidden_runtime_imports()
        print(_canonical(result).decode("utf-8"))
        return 0
    if args.reexecute:
        body = _strict_json(args.reexecute.read_bytes())
        result = deterministic_native_reexecution(body, action_id_prefix=args.id_prefix)
        result["forbidden_runtime_imports"] = _forbidden_runtime_imports()
        print(_canonical(result).decode("utf-8"))
        return 0
    if args.record_full:
        body = record_full_timeline()
        args.record_full.write_bytes(_canonical(body))
        print(f"wrote faithful native Encounter replay through boundary 9: {args.record_full}")
        return 0
    if args.resume:
        body = _strict_json(args.resume.read_bytes())
        started = time.perf_counter_ns()
        _world, encounter, rng = restore_private_checkpoint(body)
        load_ns = time.perf_counter_ns() - started
        result = continue_native(encounter, rng,
            previous_state=body["checkpoint"]["state"],
            prior_action_ids=body["checkpoint"]["finished_action_ids"],
            action_input=body["native_inputs"]["continuation"]["action"])
        result["strict_load_and_rehydrate_ns"] = load_ns
        result["peak_rss_platform_units"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        result["forbidden_runtime_imports"] = _forbidden_runtime_imports()
        print(_canonical(result).decode("utf-8"))
        return 0
    base, body = _capture_resume_artifact()
    if args.write_checkpoint:
        args.write_checkpoint.write_bytes(_canonical(body))
        print(f"wrote native headless checkpoint at boundary {body['checkpoint']['boundary']}: {args.write_checkpoint}")
        return 0
    result = continue_native(base["encounter"], base["rng_owner"],
        previous_state=body["checkpoint"]["state"],
        prior_action_ids=body["checkpoint"]["finished_action_ids"],
        action_input=body["native_inputs"]["continuation"]["action"])
    result["checkpoint_artifact_bytes"] = len(_canonical(body))
    result["checkpoint_components"] = {
        "initial_state": len(_canonical(body["initial_state"])),
        "prior_deltas": len(_canonical(body["deltas"])),
        "prior_events": sum(len(_canonical(row["events"])) for row in body["deltas"]),
        "resume_snapshot": len(_canonical(body["checkpoint"]["state"])),
        "compatibility_and_scheduler": len(_canonical({key: body["checkpoint"][key]
            for key in ("choice_state", "choice_counter", "closed_draft_ids", "schedule_revision")}))}
    print(_canonical(result).decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
