"""Measure and verify a 64-Action headless native Save/Load continuation.

Run from the repository root:
    .venv/bin/python -B examples/native_persistence_scale.py

The scenario uses legal adopted Dagger Feints against an explicitly placed,
aware opponent. It contains no Arena, browser, session, or npcgen dependency.
"""
from __future__ import annotations

import base64
import hashlib
import json
import math
import os
from pathlib import Path
import random
import resource
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / 'src', ROOT / 'examples'):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from action import Action
from activities import DelayAction
from atomic_publication import RNGCursor
from encounter import Encounter
from library import Library
from melee_combat import effective_melee_reach_meters
from native_history import encode as encode_history
from native_persistence import export_save, load_path
from spatial import CartesianPosition, Sphere
from universe import Universe


def _being_count(world):
    return sum(type(value).__name__ == 'BeingInstance'
               for value in world.object_registry.object_instances.values())


def _continue(path):
    world, encounter, rng = load_path(path)
    before = len(encounter.finished_action_list)
    action = DelayAction(encounter, encounter.being_list[0], defense=0,
                         start_time=encounter.time,
                         id='native-scale-post-load-delay')
    encounter.schedule_action(action)
    encounter.step(1)
    return {
        'time': encounter.time,
        'rng': rng.state,
        'hp': [encounter.get_being(identity).get_hit_points()
               for identity in encounter.being_list],
        'history_sha256': hashlib.sha256(
            encode_history(__import__('native_history').capture(encounter))).hexdigest(),
        'prior_finished_actions': before,
        'being_registry_count': _being_count(world),
        'continuation_action': action.id,
        'arena_modules': sorted(set(sys.modules) & {
            'arena_browser_session', 'arena_server', 'npcgen'}),
    }


def run(action_count=64, registry_count=2):
    if type(action_count) is not int or action_count < 64:
        raise ValueError('the scale acceptance scenario requires at least 64 Actions')
    if type(registry_count) is not int or registry_count < 2:
        raise ValueError('the scale scenario requires at least two registered Beings')
    started = time.perf_counter()
    world = Universe('native-scale', library=Library(config_dir=str(ROOT / 'src/config')))
    first_id = world.make_being('Human', 'Scale Attacker')
    second_id = world.make_being('Human', 'Scale Target')
    first, second = (world.get_object_by_id(identity)
                     for identity in (first_id, second_id))
    first.set_position(CartesianPosition(0.0, 0.0, 0.0))
    second.set_position(CartesianPosition(0.2, 0.0, 0.0))
    for being in (first, second):
        being.set_geometry(Sphere(0.25))
        being.set_hit_points(100)
    for index in range(registry_count - 2):
        world.make_being('Human', f'Native Registry Extra {index:03d}')
    weapon_id = world.make_weapon_for_being(first.id, 'Dagger', 'Scale Dagger')
    world.arm_being(first.id, weapon_id, 'right hand')
    first.current.skills.weapon_skills['Dagger'] = 2
    encounter = Encounter(world, 10, 0, initiated=True)
    encounter.add_being(first.id)
    encounter.add_being(second.id)
    encounter.mark_aware(first.id, second.id)
    encounter.mark_aware(second.id, first.id)
    world.add_event(encounter)
    rng = RNGCursor(random.Random(9018).getstate())
    encounter.enable_transactional_progression(quiescent=True, rng_owner=rng)
    weapon = world.get_object_by_id(weapon_id)
    reach = effective_melee_reach_meters(first.current, weapon.current)
    duration = math.ceil(weapon.current.Tt() / 2)
    resolved = []
    for index in range(action_count):
        action = Action(world, encounter.time, encounter.time + duration,
                        'feint', first.id, second.id, weapon_id,
                        id=f'native-scale-feint-{index:03d}')
        action.feint_motion = 'thrust'
        action.reach = reach
        action.end_time = encounter.time + duration
        encounter.schedule_action(action)
        encounter.step(duration)
        if action.resolution is None:
            raise RuntimeError(f'Feint {index} did not resolve')
        resolved.append(action.id)
    authored_seconds = time.perf_counter() - started
    export_started = time.perf_counter()
    wire = export_save(encounter)
    export_seconds = time.perf_counter() - export_started
    body = json.loads(wire)
    history_bytes = len(json.dumps(body['history'], sort_keys=True,
                                   separators=(',', ':')).encode('ascii'))
    graph_bytes = len(base64.b64decode(body['graph_b64'], validate=True))
    before = {
        'time': encounter.time,
        'rng': rng.state,
        'hp': [encounter.get_being(identity).get_hit_points()
               for identity in encounter.being_list],
        'actions': resolved,
    }
    with tempfile.TemporaryDirectory(prefix='universe-native-scale-') as directory:
        save_path = Path(directory) / 'native-64-action-save.json'
        save_path.write_bytes(wire)
        command = [sys.executable, '-B', str(Path(__file__).resolve()),
                   '--continue', str(save_path)]
        child_started = time.perf_counter()
        child = subprocess.run(command, cwd=ROOT,
            env={**os.environ, 'PYTHONPATH': f'{ROOT / "src"}:{ROOT / "examples"}'},
            text=True, capture_output=True, check=False, timeout=1800)
        load_continue_seconds = time.perf_counter() - child_started
        if child.returncode:
            raise RuntimeError('fresh-process native continuation failed: ' + child.stderr)
        restored = json.loads(child.stdout)
        if restored['prior_finished_actions'] != action_count:
            raise RuntimeError('fresh process did not restore all committed Action identities')
        if restored['being_registry_count'] != registry_count:
            raise RuntimeError('fresh process did not restore the full Being registry')
        if restored['arena_modules']:
            raise RuntimeError('native child imported an Arena/npcgen application module')
        action = DelayAction(encounter, first.id, defense=0,
                             start_time=encounter.time,
                             id='native-scale-post-load-delay')
        encounter.schedule_action(action)
        encounter.step(1)
        control = {
            'time': encounter.time, 'rng': rng.state,
            'hp': [encounter.get_being(identity).get_hit_points()
                   for identity in encounter.being_list],
            'history_sha256': hashlib.sha256(encode_history(
                __import__('native_history').capture(encounter))).hexdigest(),
            'prior_finished_actions': action_count,
            'being_registry_count': registry_count,
            'continuation_action': action.id,
            'arena_modules': [],
        }
        if restored != json.loads(json.dumps(control)):
            raise RuntimeError('fresh-process continuation differs from uninterrupted control')
    return {
        'actions_resolved': action_count,
        'being_registry_count': registry_count,
        'committed_boundaries': encounter.last_processed_boundary,
        'save_bytes': len(wire), 'graph_bytes': graph_bytes,
        'history_bytes': history_bytes,
        'scenario_seconds': round(authored_seconds, 3),
        'export_seconds': round(export_seconds, 3),
        'fresh_process_load_and_continue_seconds': round(load_continue_seconds, 3),
        'peak_rss_platform_units': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        'same_encounter_identifiers_preserved': True,
        'fresh_process_matches_uninterrupted_control': True,
        'save_then_load_then_continue_then_save_history': 'verified by native API tests',
        'uninterrupted_control': {key: control[key] for key in ('time', 'hp')},
    }


def run_quiet(boundary_count=200, registry_count=2):
    """Measure legal empty intervals and resume after their strict native Save."""
    if type(boundary_count) is not int or boundary_count < 200:
        raise ValueError('the quiet-boundary scale case requires at least 200 boundaries')
    if type(registry_count) is not int or registry_count < 2:
        raise ValueError('the scale scenario requires at least two registered Beings')
    world = Universe('native-quiet-scale', library=Library(config_dir=str(ROOT / 'src/config')))
    first_id = world.make_being('Human', 'Quiet Observer')
    second_id = world.make_being('Human', 'Quiet Other')
    first, second = (world.get_object_by_id(identity)
                     for identity in (first_id, second_id))
    first.set_position(CartesianPosition(0.0, 0.0, 0.0))
    second.set_position(CartesianPosition(0.2, 0.0, 0.0))
    for being in (first, second):
        being.set_geometry(Sphere(0.25))
        being.set_hit_points(100)
    for index in range(registry_count - 2):
        world.make_being('Human', f'Native Quiet Registry Extra {index:03d}')
    encounter = Encounter(world, 10, 0, initiated=True)
    encounter.add_being(first.id)
    encounter.add_being(second.id)
    world.add_event(encounter)
    rng = RNGCursor(random.Random(9020).getstate())
    encounter.enable_transactional_progression(quiescent=True, rng_owner=rng)
    started = time.perf_counter()
    encounter.step(boundary_count)
    scenario_seconds = time.perf_counter() - started
    export_started = time.perf_counter()
    wire = export_save(encounter)
    export_seconds = time.perf_counter() - export_started
    body = json.loads(wire)
    graph_bytes = len(base64.b64decode(body['graph_b64'], validate=True))
    history_bytes = len(json.dumps(body['history'], sort_keys=True,
                                   separators=(',', ':')).encode('ascii'))
    with tempfile.TemporaryDirectory(prefix='universe-native-quiet-scale-') as directory:
        save_path = Path(directory) / 'native-quiet-save.json'
        save_path.write_bytes(wire)
        child_started = time.perf_counter()
        child = subprocess.run(
            [sys.executable, '-B', str(Path(__file__).resolve()),
             '--continue', str(save_path)], cwd=ROOT,
            env={**os.environ, 'PYTHONPATH': f'{ROOT / "src"}:{ROOT / "examples"}'},
            text=True, capture_output=True, check=False, timeout=1800)
        load_continue_seconds = time.perf_counter() - child_started
        if child.returncode:
            raise RuntimeError('fresh-process quiet continuation failed: ' + child.stderr)
        restored = json.loads(child.stdout)
        action = DelayAction(encounter, first.id, defense=0,
                             start_time=encounter.time,
                             id='native-scale-post-load-delay')
        encounter.schedule_action(action)
        encounter.step(1)
        control = {
            'time': encounter.time, 'rng': rng.state,
            'hp': [encounter.get_being(identity).get_hit_points()
                   for identity in encounter.being_list],
            'history_sha256': hashlib.sha256(encode_history(
                __import__('native_history').capture(encounter))).hexdigest(),
            'prior_finished_actions': 0,
            'being_registry_count': registry_count,
            'continuation_action': action.id, 'arena_modules': [],
        }
        if restored != json.loads(json.dumps(control)):
            raise RuntimeError('fresh-process quiet continuation differs from control')
    return {
        'quiet_boundaries': boundary_count,
        'being_registry_count': registry_count,
        'graph_bytes': graph_bytes, 'history_bytes': history_bytes,
        'save_bytes': len(wire), 'scenario_seconds': round(scenario_seconds, 3),
        'export_seconds': round(export_seconds, 3),
        'fresh_process_load_and_continue_seconds': round(load_continue_seconds, 3),
        'fresh_process_matches_uninterrupted_control': True,
        'peak_rss_platform_units': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    }
if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--continue':
        print(json.dumps(_continue(sys.argv[2]), sort_keys=True))
    elif len(sys.argv) == 3 and sys.argv[1] == '--quiet-boundaries':
        print(json.dumps(run_quiet(boundary_count=int(sys.argv[2])), sort_keys=True))
    else:
        registry_count = (int(sys.argv[2]) if len(sys.argv) == 3
                          and sys.argv[1] == '--registry-count' else 2)
        print(json.dumps(run(registry_count=registry_count), sort_keys=True))
