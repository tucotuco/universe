#!/usr/bin/env python3
"""Fresh-process native Encounter resume proof; independent of Arena packages."""
from __future__ import annotations

import hashlib
import json
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


def _capture_resume_artifact():
    base = delta.build_demo(until=CHECKPOINT_BOUNDARY)
    checkpoint = base["checkpoint"]
    if checkpoint["boundary"] != CHECKPOINT_BOUNDARY:
        raise AssertionError("fixture did not reach the intended quiescent boundary")
    body = {
        "schema": SCHEMA,
        "compatibility": _source_compatibility(),
        "initial_state": base["initial"],
        "deltas": [row["delta"] for row in base["boundaries"]],
        "checkpoint": checkpoint,
    }
    body["integrity_sha256"] = _seal(body)
    return base, body


def save_checkpoint(path):
    _base, body = _capture_resume_artifact()
    path = Path(path)
    path.write_bytes(_canonical(body))
    return body


def validate_artifact(body):
    required = {"schema", "compatibility", "initial_state", "deltas", "checkpoint", "integrity_sha256"}
    if type(body) is not dict or set(body) != required or body["schema"] != SCHEMA:
        raise ResumeRejected("checkpoint schema mismatch")
    unsigned = dict(body); supplied = unsigned.pop("integrity_sha256")
    if type(supplied) is not str or _seal(unsigned) != supplied:
        raise ResumeRejected("checkpoint integrity digest mismatch")
    if body["compatibility"] != _source_compatibility():
        raise ResumeRejected("Encounter source, rules, Library or Python compatibility mismatch")
    checkpoint = body["checkpoint"]
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


def continue_native(encounter, rng_owner, *, previous_state, prior_action_ids):
    """Schedule a real melee hit, then commit one quiet boundary via Encounter.step."""
    strike = MeleeStrike(encounter, BEING_IDS[0], BEING_IDS[1], WEAPON_ID,
                         motion="thrust", reach=2)
    strike.id = ATTACK_ID
    encounter.schedule_action(strike)
    rows = []
    known_actions = set(prior_action_ids)
    for boundary in range(CHECKPOINT_BOUNDARY + 1, CHECKPOINT_BOUNDARY + 6):
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
        "native_step_ns": [row["step_ns"] for row in rows]}
    return final


def _main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resume", type=Path, help="validate and continue a saved native checkpoint")
    parser.add_argument("--write-checkpoint", type=Path, help="write the boundary-4 native checkpoint")
    args = parser.parse_args(argv)
    if args.resume:
        body = _strict_json(args.resume.read_bytes())
        started = time.perf_counter_ns()
        _world, encounter, rng = restore_private_checkpoint(body)
        load_ns = time.perf_counter_ns() - started
        result = continue_native(encounter, rng,
            previous_state=body["checkpoint"]["state"],
            prior_action_ids=body["checkpoint"]["finished_action_ids"])
        result["strict_load_and_rehydrate_ns"] = load_ns
        result["peak_rss_platform_units"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        forbidden = ("arena_native_snapshot", "arena_session", "arena_controller",
                     "arena_server", "npcgen")
        result["forbidden_runtime_imports"] = sorted(
            name for name in sys.modules if any(name == prefix or name.startswith(prefix + ".")
                for prefix in forbidden))
        print(_canonical(result).decode("utf-8"))
        return 0
    base, body = _capture_resume_artifact()
    if args.write_checkpoint:
        args.write_checkpoint.write_bytes(_canonical(body))
        print(f"wrote native headless checkpoint at boundary {body['checkpoint']['boundary']}: {args.write_checkpoint}")
        return 0
    result = continue_native(base["encounter"], base["rng_owner"],
        previous_state=body["checkpoint"]["state"],
        prior_action_ids=body["checkpoint"]["finished_action_ids"])
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
