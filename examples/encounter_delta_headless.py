#!/usr/bin/env python3
"""Arena-independent native Encounter delta/replay proof (experimental only).

Run from the repository root with ``.venv/bin/python examples/encounter_delta_headless.py``.
The recorder observes native committed state; it never evaluates an Action or
changes simulation state. Its current projection is a declared bounded domain
closure. ``native_headless_resume.py`` uses that representation for an isolated
fresh-process resume proof, not a replacement save format.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
import time
from dataclasses import fields, is_dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from atomic_publication import RNGCursor  # noqa: E402
from activities import DelayAction, RunAction  # noqa: E402
from being import BeingInstance  # noqa: E402
from encounter import Encounter  # noqa: E402
from library import Library  # noqa: E402
from spatial.geometry import Sphere  # noqa: E402
from spatial.state import CartesianPosition  # noqa: E402
from universe import Universe  # noqa: E402
from weapon import WeaponInstance  # noqa: E402


class DeltaError(ValueError):
    """An experimental delta is duplicate, misordered, or has a bad preimage."""


def native_input_manifest(seed=0):
    """Recorded lawful inputs for the fixed two-Being replay fixture."""
    return {
        "schema": "universe.headless-native-inputs/1",
        "seed": seed,
        "boundaries": [
            {"boundary": 1, "mode": "single", "actions": [{
                "kind": "run", "action_id": "action-run-ada", "actor_id": "being-ada",
                "start_time": 0, "duration": 1, "minimum_distance": 1,
                "experience": 0}], "velocities": {"being-ada": [1, 0, 0]}},
            {"boundary": 2, "mode": "single", "actions": [], "velocities": {}},
            {"boundary": 3, "mode": "single", "actions": [{
                "kind": "delay", "action_id": "action-delay-bram", "actor_id": "being-bram",
                "start_time": 2, "defense": 0}], "velocities": {}},
            {"boundary": 4, "mode": "choice", "actions": [
                {"kind": "run", "action_id": "action-run-ada-2", "actor_id": "being-ada",
                 "start_time": 3, "duration": 1, "minimum_distance": 1, "experience": 0},
                {"kind": "run", "action_id": "action-run-bram", "actor_id": "being-bram",
                 "start_time": 3, "duration": 1, "minimum_distance": 1, "experience": 0}],
             "velocities": {"being-ada": [1, 0, 0], "being-bram": [-1, 0, 0]}},
        ],
    }


def canonical_bytes(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def state_digest(state) -> str:
    return hashlib.sha256(canonical_bytes(state)).hexdigest()


def native_state(encounter, rng_owner):
    """The full state closure claimed by this experiment, captured from native objects.

    Historical completed Actions/receipts are encoded separately as Events.
    This is a bounded resume test closure, not an inventory of every Universe
    field; readers and external/excluded values are listed in the findings doc.
    """
    beings = {}
    weapons = {}
    for being_id in encounter.being_list:  # preserve native participant ordering below
        being = encounter.get_being(being_id)
        position = being.get_position()
        armed = being.armed_with(encounter.universe)
        beings[being_id] = {
            "id": being.id,
            "type": "BeingInstance",
            "name": being.name,
            "definition_key": being.original.obj_type,
            "position": (None if position is None else list(position.as_tuple())),
            "hit_points": being.current.hit_points,
            "armor_id": being.get_armor_id(),
            "body_parts": dict(being.get_body_parts()),
            "states": dict(being.get_states()),
            "posture": being.posture,
            "size_category": being.size_category,
            "hex_facing": being.hex_facing,
            "fatigue_level": being.get_fatigue_level(),
            "physical_fatigue": _json_value(being.physical_fatigue),
            "physiology_id": being.physiology_id,
            "geometry": None if being.geometry is None else being.geometry.to_dict(),
            "abilities": dict(being.current.get_abilities()),
            "skills": dict(being.current.get_skills()),
            "weapon_skills": dict(being.current.get_weapon_skills()),
            "skill_experience": dict(being.skill_experience),
            "skill_practice_baselines": dict(being._skill_practice_baselines),
            "skill_use_history": [_json_value(entry) for entry in being.skill_use_history],
            "strategy": {name: getattr(being.strategy, name)
                         for name in ("attack", "defense", "timing", "extra_damage")},
            "personal_history": (None if being.personal_history is None
                                 else being.personal_history.to_jsonable()),
            "possessions": list(being.possessions),
            "weapons": list(being.weapons),
            "armed": {hand: armed[hand] for hand in sorted(armed)},
        }
        for weapon_id in being.weapons:
            weapon = encounter.universe.get_object_by_id(weapon_id)
            if type(weapon) is not WeaponInstance:
                raise TypeError("headless closure includes only native WeaponInstances")
            weapons[weapon_id] = {
                "id": weapon.id,
                "type": "WeaponInstance",
                "name": weapon.name,
                "definition_key": weapon.original.obj_type,
                "position": (None if weapon.get_position() is None
                             else list(weapon.get_position().as_tuple())),
                "parent_container_id": weapon.parent_container_id,
                "hit_points": weapon.current.hit_points,
                "weapon_size": weapon.current.weapon_size,
                "attacks": _json_value(weapon.current.attacks),
                "geometry": None if weapon.geometry is None else weapon.geometry.to_dict(),
            }
    awareness = {
        observer_id: sorted(encounter.awareness.get(observer_id, ()))
        for observer_id in encounter.being_list
    }
    return {
        "schema": "universe.headless-encounter-domain-state/1",
        "encounter": {
            "id": encounter.id,
            "difficulty_class": encounter.difficulty_class,
            "participants": list(encounter.being_list),
            "pending_action_ids": list(encounter.pending_action_list),
            "cancelled_action_ids": list(encounter.cancelled_action_list),
            "time": encounter.time,
            "start_time": encounter.start_time,
            "last_processed_boundary": encounter.last_processed_boundary,
            "coordinator_time": encounter._coordinator_time,
            "interval_start": encounter._interval_start,
            "initiated": encounter.initiated,
            "awareness_by_observer": awareness,
        },
        "beings": beings,
        "weapons": weapons,
        "rng_state": _json_value(rng_owner.state),
    }


def _json_value(value):
    if value is None or type(value) in (str, int, float, bool):
        return value
    if type(value) is CartesianPosition:
        return {"$type": "CartesianPosition", "value": list(value.as_tuple())}
    if type(value) in (tuple, list):
        return [_json_value(item) for item in value]
    if type(value) is dict:
        return {str(key): _json_value(item) for key, item in value.items()}
    if is_dataclass(value) and not isinstance(value, type):
        return {"$type": f"{type(value).__module__}.{type(value).__name__}",
                "fields": {field.name: _json_value(getattr(value, field.name))
                           for field in fields(value)}}
    raise TypeError(f"experimental state contains unsupported value: {type(value).__name__}")


def _walk(before, after, path=()):
    """Produce one sorted atomic property set, including explicit add/remove."""
    if type(before) is dict and type(after) is dict:
        changes = []
        for key in sorted(set(before) | set(after)):
            if key not in before:
                changes.append({"path": list(path + (key,)), "before_present": False,
                                "after_present": True, "after": after[key]})
            elif key not in after:
                changes.append({"path": list(path + (key,)), "before_present": True,
                                "before": before[key], "after_present": False})
            else:
                changes.extend(_walk(before[key], after[key], path + (key,)))
        return changes
    if before != after or type(before) is not type(after):
        return [{"path": list(path), "before_present": True, "before": before,
                 "after_present": True, "after": after}]
    return []


def apply_delta(state, delta):
    """Validate/apply a boundary delta to a deep JSON-compatible state copy."""
    if type(delta) is not dict or set(delta) != {"boundary", "time", "changes", "events", "state_sha256"}:
        raise DeltaError("delta schema mismatch")
    if (type(delta["boundary"]) is not int or delta["boundary"] <= 0
            or type(delta["time"]) not in (int, float)
            or not math.isfinite(delta["time"])
            or delta["time"] != delta["boundary"]
            or not isinstance(delta["events"], list)
            or not isinstance(delta["changes"], list)
            or type(delta["state_sha256"]) is not str):
        raise DeltaError("invalid boundary")
    result = json.loads(canonical_bytes(state))
    previous_paths = set()
    for change in delta["changes"]:
        path = change.get("path")
        if type(path) is not list or not path or any(type(key) is not str for key in path):
            raise DeltaError("invalid property path")
        key_path = tuple(path)
        if key_path in previous_paths:
            raise DeltaError("duplicate property path")
        previous_paths.add(key_path)
        parent = result
        for key in path[:-1]:
            if type(parent) is not dict or key not in parent:
                raise DeltaError("property parent is absent")
            parent = parent[key]
        key = path[-1]
        before_present = change.get("before_present")
        if type(parent) is not dict or (key in parent) != before_present:
            raise DeltaError("property presence preimage mismatch")
        if before_present and parent[key] != change.get("before"):
            raise DeltaError("property value preimage mismatch")
        if change.get("after_present"):
            parent[key] = change["after"]
        else:
            parent.pop(key)
    if state_digest(result) != delta["state_sha256"]:
        raise DeltaError("reconstructed state digest mismatch")
    return result


def replay(initial, deltas):
    """Replay a complete ordered stream, refusing gaps, duplicates and reordering."""
    state = json.loads(canonical_bytes(initial))
    expected = 1
    for delta in deltas:
        if type(delta) is not dict or delta.get("boundary") != expected:
            raise DeltaError("duplicate, missing, or out-of-order boundary")
        state = apply_delta(state, delta)
        expected += 1
    return state


def _boundary_events(encounter, previous_action_ids, boundary):
    """Read newly completed native Action Events and committed receipt references."""
    receipts = [row for row in encounter._atomic_interval_history if row.boundary == boundary]
    if len(receipts) != 1:
        raise AssertionError(f"expected one native committed receipt at {boundary}, got {len(receipts)}")
    receipt = receipts[0]
    result = []
    for action_id in receipt.action_ids:
        if action_id in previous_action_ids:
            raise AssertionError("completed Action identity repeated across boundaries")
        event = encounter.universe.get_event_by_id(action_id)
        if event is None:
            raise AssertionError(f"native Action Event {action_id} missing")
        resolution = event.resolution
        outcome = getattr(resolution, "outcome", None)
        from action_evaluation import (ActionProposal, PracticeEffect,
            DelayDefenseEffect, DamageEffect)
        if type(resolution) is not ActionProposal:
            raise AssertionError("committed headless Action lacks a native proposal")
        effects = []
        for effect in resolution.effects:
            if type(effect) not in (PracticeEffect, DelayDefenseEffect, DamageEffect):
                raise AssertionError(f"unsupported effect in headless history: {type(effect).__name__}")
            effects.append({"type": type(effect).__name__,
                            "fields": {name: _json_value(getattr(effect, name))
                                       for name in effect.__dataclass_fields__}})
        from action_choice import ChoiceMember
        book = encounter._choice_book
        lifecycle = getattr(event, "_atomic_lifecycle", None)
        choice_id = None if lifecycle is None else lifecycle.choice_id
        accepted = book._choices.get(choice_id)
        choice_packet = None
        if accepted is not None:
            member_packets = []
            for member, packet in zip(accepted.members, accepted.prepared):
                if type(member) is not ChoiceMember:
                    raise AssertionError("headless history has an unsupported ChoiceMember")
                member_packets.append({
                    "key": member.key,
                    "action_id": member.action.id,
                    "target_action_key": member.target_action_key,
                    "priority_penalty": member.priority_penalty,
                    "packet": {name: _json_value(getattr(packet, name))
                               for name in packet.__dataclass_fields__},
                })
            choice_packet = {"id": accepted.view.id,
                "version": accepted.view.version, "state": accepted.view.state,
                "action_ids": list(accepted.view.action_ids),
                "first_start": accepted.view.first_start,
                "origin": accepted.origin, "members": member_packets}
        result.append({
            "event_id": event.id,
            "action_class": type(event).__name__,
            "event_type": event.event_type,
            "parent_event_id": event.parent_event_id,
            "action_id": action_id,
            "actor_id": event.actor_id,
            "target_id": event.target_id,
            "start_time": event.start_time,
            "end_time": event.end_time,
            "outcome": outcome,
            "target_ids": list(resolution.target_ids),
            "proposal_effects": effects,
            "proposal_metadata": _json_value(resolution.metadata),
            "choice_id": choice_id,
            "choice_member_key": (None if accepted is None else next(
                member.key for member in accepted.members if member.action.id == action_id)),
            "choice": choice_packet,
            "action_data": _history_action_data(event),
            "effect_ids": [[effect_id.encounter_id, effect_id.boundary,
                            effect_id.source_action_id, effect_id.channel, effect_id.slot]
                           for effect_id in receipt.effect_ids
                           if effect_id.source_action_id == action_id],
        })
    return result


def _history_action_data(action):
    if type(action) is RunAction:
        position = action.start_position
        return {"minimum_distance": action.minimum_distance,
                "practice_experience": action.practice_experience,
                "start_position": (None if position is None else list(position.as_tuple())),
                "activity_started": bool(getattr(action, "_activity_started", False))}
    if type(action) is DelayAction:
        return {"defense": action.strategy.defense}
    from melee_combat import MeleeStrike
    if type(action) is MeleeStrike:
        return {"weapon_id": action.instrument_id, "motion": action.event_type,
                "reach": action.reach, "hit_type": action.hit_type,
                "combat_result": _json_value(action.combat_result)}
    raise AssertionError(f"unsupported Action history family: {type(action).__name__}")


def _capture_boundary(encounter, rng_owner, prior_state, boundary, prior_action_ids):
    started = time.perf_counter_ns()
    actual = native_state(encounter, rng_owner)
    changes = _walk(prior_state, actual)
    events = _boundary_events(encounter, prior_action_ids, boundary)
    delta = {"boundary": boundary, "time": encounter.time, "changes": changes,
             "events": events, "state_sha256": state_digest(actual)}
    elapsed_ns = time.perf_counter_ns() - started
    return actual, delta, elapsed_ns


def build_demo(until=7, seed=0, *, inputs=None, action_id_prefix=""):
    """Run authored facts through the native transactional Encounter engine."""
    universe = Universe("Headless delta proof", library=Library(config_dir=str(ROOT / "src/config")))
    definition = universe.get_being_definition("Human")
    a = BeingInstance(definition, "Ada", id="being-ada")
    b = BeingInstance(definition, "Bram", id="being-bram")
    universe.add_object(a)
    universe.add_object(b)
    for being, position in ((a, (0, 0, 0)), (b, (2, 0, 0))):
        being.set_position(CartesianPosition(*position))
        being.set_geometry(Sphere(0.2))
    dagger = WeaponInstance(universe.get_weapon_definition("Dagger"), "Ada's dagger")
    dagger.id = "weapon-ada-dagger"
    universe.add_object(dagger)
    a.weapons.append(dagger.id)
    a.set_body_part_holds_object("right hand", dagger.id)
    encounter = Encounter(universe, difficulty_class=10, start_time=0, initiated=True,
                          name="Headless delta proof", id="headless-encounter")
    for being in (a, b):
        encounter.add_being(being.id)
    for observer in (a, b):
        encounter.mark_aware(observer.id, a.id if observer is b else b.id)
    universe.add_event(encounter)
    rng_owner = RNGCursor(random.Random(seed).getstate())
    encounter.enable_transactional_progression(quiescent=True, rng_owner=rng_owner)
    actors = {"being-ada": a, "being-bram": b}
    inputs = native_input_manifest(seed) if inputs is None else inputs
    if (type(inputs) is not dict or set(inputs) != {"schema", "seed", "boundaries"}
            or inputs["schema"] != "universe.headless-native-inputs/1"
            or type(inputs["seed"]) is not int or type(inputs["boundaries"]) is not list
            or len(inputs["boundaries"]) != 4):
        raise ValueError("unsupported native replay input manifest")
    if inputs["seed"] != seed:
        raise ValueError("native replay seed differs from its recorded input manifest")
    previous_action_ids = set()
    initial = native_state(encounter, rng_owner)
    boundaries = []
    captured = initial

    def record(boundary, step_ns):
        nonlocal captured
        actual, delta, capture_ns = _capture_boundary(
            encounter, rng_owner, captured, boundary, previous_action_ids)
        if encounter.last_processed_boundary != boundary or encounter.time != delta["time"]:
            raise AssertionError("native time/cursor does not match committed boundary metadata")
        previous_action_ids.update(row["action_id"] for row in delta["events"])
        # Every boundary is independently reconstructed before the next engine step.
        reconstructed = apply_delta(captured, delta)
        if canonical_bytes(reconstructed) != canonical_bytes(actual):
            raise AssertionError(f"headless reconstruction differed at boundary {boundary}")
        boundaries.append({"actual": actual, "delta": delta, "capture_ns": capture_ns,
                           "step_ns": step_ns})
        captured = actual

    start = time.perf_counter_ns()
    for expected_boundary, declaration in enumerate(inputs["boundaries"], 1):
        if (type(declaration) is not dict or set(declaration) != {
                "boundary", "mode", "actions", "velocities"}
                or declaration["boundary"] != expected_boundary
                or declaration["mode"] not in ("single", "choice")
                or type(declaration["actions"]) is not list
                or type(declaration["velocities"]) is not dict):
            raise ValueError("invalid native input boundary declaration")
        actions = []
        for row in declaration["actions"]:
            action_id = action_id_prefix + row["action_id"]
            if row["kind"] == "run" and set(row) == {
                    "kind", "action_id", "actor_id", "start_time", "duration",
                    "minimum_distance", "experience"}:
                action = RunAction(universe, row["actor_id"], row["start_time"],
                    row["duration"], row["minimum_distance"], experience=row["experience"], id=action_id)
            elif row["kind"] == "delay" and set(row) == {
                    "kind", "action_id", "actor_id", "start_time", "defense"}:
                action = DelayAction(encounter, row["actor_id"], defense=row["defense"],
                                     start_time=row["start_time"], id=action_id)
            else:
                raise ValueError("native replay declaration contains an unsupported Action family")
            actions.append(action)
        if declaration["mode"] == "choice" and actions:
            encounter.schedule_choice(tuple(actions))
        elif declaration["mode"] == "single" and len(actions) <= 1:
            for action in actions:
                encounter.schedule_action(action)
        else:
            raise ValueError("native Action group does not match its declared scheduling mode")
        velocities = {actor_id: tuple(vector)
                      for actor_id, vector in declaration["velocities"].items()}
        step_started = time.perf_counter_ns()
        encounter.step(1, velocities=velocities or None)
        record(expected_boundary, time.perf_counter_ns() - step_started)
    checkpoint = {
        "boundary": 4,
        "time": encounter.time,
        "start_time": encounter.start_time,
        "state": captured,
        "finished_action_ids": list(encounter.finished_action_list),
        "choice_state": encounter._choice_book.summary(),
        "choice_counter": encounter._choice_book._counter,
        "closed_draft_ids": sorted(encounter._choice_book._closed_drafts),
        "schedule_revision": universe._schedule_revision,
        "action_history": [event for row in boundaries for event in row["delta"]["events"]],
    }
    if until <= 4:
        elapsed_ns = time.perf_counter_ns() - start
        snapshot = {"boundary": encounter.last_processed_boundary, "time": encounter.time,
                    "state": native_state(encounter, rng_owner)}
        return {"universe": universe, "encounter": encounter, "rng_owner": rng_owner,
                "initial": initial, "boundaries": boundaries, "snapshot": snapshot,
        "checkpoint": checkpoint, "native_inputs": inputs, "elapsed_ns": elapsed_ns}
    # A few quiet boundaries expose recurring bookkeeping cost without GUI work.
    for boundary in range(5, until + 1):
        step_started = time.perf_counter_ns()
        encounter.step(1)
        record(boundary, time.perf_counter_ns() - step_started)
    elapsed_ns = time.perf_counter_ns() - start
    snapshot = {"boundary": encounter.last_processed_boundary, "time": encounter.time,
                "state": native_state(encounter, rng_owner)}
    if canonical_bytes(captured) != canonical_bytes(snapshot["state"]):
        raise AssertionError("complete experimental snapshot differs from final replay")
    if canonical_bytes(replay(initial, [row["delta"] for row in boundaries])) != canonical_bytes(snapshot["state"]):
        raise AssertionError("full-stream replay differs from final native snapshot")
    return {"universe": universe, "encounter": encounter, "rng_owner": rng_owner,
            "initial": initial, "boundaries": boundaries, "snapshot": snapshot,
                "checkpoint": checkpoint, "native_inputs": inputs,
                "elapsed_ns": elapsed_ns}


def artifact(result):
    """Canonical artifact whose bytes are measured in the findings report."""
    return {"schema": "universe.headless-encounter-delta-log/1",
            "initial_state": result["initial"],
            "deltas": [row["delta"] for row in result["boundaries"]],
            "snapshot": result["snapshot"],
            "checkpoint": result["checkpoint"], "native_inputs": result["native_inputs"]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print canonical measurement artifact")
    args = parser.parse_args(argv)
    result = build_demo()
    payload = artifact(result)
    if args.json:
        print(canonical_bytes(payload).decode("utf-8"))
    else:
        events = [event for row in payload["deltas"] for event in row["events"]]
        event_bytes = sum(len(canonical_bytes(row["events"])) for row in payload["deltas"])
        change_bytes = sum(len(canonical_bytes(row["changes"])) for row in payload["deltas"])
        capture_ns = sum(row["capture_ns"] for row in result["boundaries"])
        step_ns = sum(row["step_ns"] for row in result["boundaries"])
        print(f"native boundaries: {len(payload['deltas'])}; events: {len(events)}")
        print("state digests: " + ", ".join(row["state_sha256"][:12] for row in payload["deltas"]))
        print(f"initial bytes: {len(canonical_bytes(payload['initial_state']))}; property-diff bytes: {change_bytes}; event bytes: {event_bytes}")
        print(f"complete snapshot bytes: {len(canonical_bytes(payload['snapshot']))}; artifact bytes: {len(canonical_bytes(payload))}")
        print(f"native step time: {step_ns/1e6:.3f} ms; recorder capture/diff/hash: {capture_ns/1e6:.3f} ms; end-to-end: {result['elapsed_ns']/1e6:.3f} ms")
        print("final native boundary: " + str(result["snapshot"]["boundary"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
