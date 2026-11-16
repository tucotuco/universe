#!/usr/bin/env python3
"""Arena-independent native Encounter delta/replay proof (experimental only).

Run from the repository root with ``.venv/bin/python examples/encounter_delta_headless.py``.
The recorder observes native committed state; it never evaluates an Action or
changes simulation state. Its projection is deliberately a declared domain
closure, not a resumable checkpoint or replacement save format.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
import time
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


class DeltaError(ValueError):
    """An experimental delta is duplicate, misordered, or has a bad preimage."""


def canonical_bytes(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def state_digest(state) -> str:
    return hashlib.sha256(canonical_bytes(state)).hexdigest()


def native_state(encounter, rng_owner):
    """The full state closure claimed by this experiment, captured from native objects.

    Historical completed Actions/receipts are encoded separately as Events.
    Immutable definitions, physiology, unmodeled conditions and checkpoint
    reconstruction dependencies are explicit exclusions (see findings doc).
    """
    beings = {}
    for being_id in encounter.being_list:  # preserve native participant ordering below
        being = encounter.get_being(being_id)
        position = being.get_position()
        beings[being_id] = {
            "id": being.id,
            "type": "BeingInstance",
            "name": being.name,
            "definition_key": being.original.obj_type,
            "position": (None if position is None else list(position.as_tuple())),
            "hit_points": being.current.hit_points,
            "possessions": list(being.possessions),
            "weapons": list(being.weapons),
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
            "awareness_by_observer": awareness,
        },
        "beings": beings,
        "rng_state": _json_value(rng_owner.state),
    }


def _json_value(value):
    if value is None or type(value) in (str, int, float, bool):
        return value
    if type(value) in (tuple, list):
        return [_json_value(item) for item in value]
    if type(value) is dict:
        return {str(key): _json_value(item) for key, item in value.items()}
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
        result.append({
            "event_id": event.id,
            "event_type": event.event_type,
            "parent_event_id": event.parent_event_id,
            "action_id": action_id,
            "actor_id": event.actor_id,
            "target_id": event.target_id,
            "start_time": event.start_time,
            "end_time": event.end_time,
            "outcome": outcome,
            "effect_ids": [effect_id.source_action_id + ":" + effect_id.channel + ":" + str(effect_id.slot)
                           for effect_id in receipt.effect_ids if effect_id.source_action_id == action_id],
        })
    return result


def _capture_boundary(encounter, rng_owner, prior_state, boundary, prior_action_ids):
    started = time.perf_counter_ns()
    actual = native_state(encounter, rng_owner)
    changes = _walk(prior_state, actual)
    events = _boundary_events(encounter, prior_action_ids, boundary)
    delta = {"boundary": boundary, "time": encounter.time, "changes": changes,
             "events": events, "state_sha256": state_digest(actual)}
    elapsed_ns = time.perf_counter_ns() - started
    return actual, delta, elapsed_ns


def build_demo():
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
    encounter = Encounter(universe, difficulty_class=10, start_time=0, initiated=True,
                          name="Headless delta proof", id="headless-encounter")
    for being in (a, b):
        encounter.add_being(being.id)
    for observer in (a, b):
        encounter.mark_aware(observer.id, a.id if observer is b else b.id)
    universe.add_event(encounter)
    rng_owner = RNGCursor(random.Random(20261116).getstate())
    encounter.enable_transactional_progression(quiescent=True, rng_owner=rng_owner)
    actors = {"ada": a, "bram": b}
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
    # A legal Run moves Ada by one represented metre and resolves natively.
    run = RunAction(universe, a.id, 0, 1, 1, experience=0, id="action-run-ada")
    encounter.schedule_action(run)
    step_started = time.perf_counter_ns()
    encounter.step(1, velocities={a.id: (1, 0, 0)})
    record(1, time.perf_counter_ns() - step_started)
    # A quiet second still commits native time/fatigue/history bookkeeping.
    step_started = time.perf_counter_ns()
    encounter.step(1)
    record(2, time.perf_counter_ns() - step_started)
    # Delay resolves as an actual native Event without changing projected properties.
    delay = DelayAction(encounter, b.id, start_time=2, id="action-delay-bram")
    encounter.schedule_action(delay)
    step_started = time.perf_counter_ns()
    encounter.step(1)
    record(3, time.perf_counter_ns() - step_started)
    # Two independent Actions share the same native boundary snapshot and commit.
    one = RunAction(universe, a.id, 3, 1, 1, experience=0, id="action-run-ada-2")
    two = RunAction(universe, b.id, 3, 1, 1, experience=0, id="action-run-bram")
    encounter.schedule_choice((one, two))
    step_started = time.perf_counter_ns()
    encounter.step(1, velocities={a.id: (1, 0, 0), b.id: (-1, 0, 0)})
    record(4, time.perf_counter_ns() - step_started)
    # A few quiet boundaries expose recurring bookkeeping cost without GUI work.
    for boundary in (5, 6, 7):
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
            "elapsed_ns": elapsed_ns}


def artifact(result):
    """Canonical artifact whose bytes are measured in the findings report."""
    return {"schema": "universe.headless-encounter-delta-log/1",
            "initial_state": result["initial"],
            "deltas": [row["delta"] for row in result["boundaries"]],
            "snapshot": result["snapshot"]}


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
