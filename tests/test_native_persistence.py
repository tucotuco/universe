from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "examples"))
sys.path.insert(0, str(ROOT / "tests"))

import encounter_delta_headless
import native_history
import native_persistence
import test_encounter_inspection as inspection_fixtures
import test_action_evaluation as action_fixtures
from native_history import NativeHistoryRecorder
from activities import DelayAction, RunAction
from atomic_publication import RNGCursor
from encounter import Encounter
from library import Library
from melee_combat import MeleeStrike
from spatial.geometry import Sphere
from spatial.state import CartesianPosition
from strategy import Strategy
from universe import Universe
from native_persistence import (NativeSaveRejected, export_save, load_path,
                                load_save, load_legacy_arena_save, write_save)
from checkpoint_adapters import RecipientBinding
from reproduction_group import ReproductionGroupProposal, prepare_reproduction_group
from being import BeingDefinition
from reproduction_being_bridge import materialize_reproductive_offspring
from history_conversation import AskAboutPastAction
from activities import SpotAction
from location_observation import LocationEvidenceLedger
from object_observation import ObjectObservationLedger
from statistical_group import StatisticalGroup


def _legacy_history_shape(value):
    value.pop("receipt_facts_complete", None)
    value.pop("observer_knowledge", None)
    value.get("initial", {}).pop("initial_schedule_available", None)
    for row in value.get("boundaries", ()):
        row.pop("notification_intents", None)
        row.pop("disarm_landings", None)
        row.pop("receipt_facts_available", None)
    return value


class NativePersistenceTests(unittest.TestCase):
    def _combat_encounter(self):
        world = Universe("native-combat", library=Library(config_dir=str(ROOT / "src/config")))
        attacker = world.get_object_by_id(world.make_being("Human", "Attacker"))
        defender = world.get_object_by_id(world.make_being("Human", "Defender"))
        attacker.set_position(CartesianPosition(0, 0, 0))
        defender.set_position(CartesianPosition(1.5, 0, 0))
        for being in (attacker, defender):
            being.set_geometry(Sphere(.25))
            being.set_hit_points(100)
        weapon_id = world.make_weapon_for_being(attacker.id, "Dagger", "Native dagger")
        world.arm_being(attacker.id, weapon_id, "right hand")
        encounter = Encounter(world, 10, 0, initiated=True)
        encounter.add_being(attacker.id)
        encounter.add_being(defender.id)
        encounter.mark_aware(attacker.id, defender.id)
        encounter.mark_aware(defender.id, attacker.id)
        world.add_event(encounter)
        rng = RNGCursor(__import__("random").Random(9).getstate())
        encounter.enable_transactional_progression(quiescent=True, rng_owner=rng)
        return world, encounter, rng, attacker, defender, weapon_id

    def test_native_save_preserves_initial_rng_history_anchor(self):
        _world, encounter, rng, *_ = self._combat_encounter()
        origin = rng.state
        encounter.step(1)
        wire = export_save(encounter)
        restored_world, restored_encounter, restored_rng = load_save(wire)
        self.assertEqual(restored_rng.state, rng.state)
        self.assertEqual(restored_encounter.__dict__["_native_rng_origin_state"], origin)
        log = native_history.current_recording(restored_encounter)
        self.assertIsNotNone(log)
        self.assertEqual(native_history.rng_state_at(log, 0), native_history._plain(origin))
        self.assertIs(restored_world.event_history[restored_encounter.id], restored_encounter)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "initial-rng-native-save.json"
            path.write_bytes(wire)
            child = r'''import json,sys
import native_history
from native_persistence import load_path
world,encounter,rng=load_path(sys.argv[1])
log=native_history.current_recording(encounter)
print(json.dumps({'encounter':encounter.id,
 'initial_rng':native_history.rng_state_at(log,0),
 'current_rng':native_history._plain(rng.state)},sort_keys=True))'''
            result = subprocess.run(
                [sys.executable, "-B", "-c", child, str(path)], cwd=ROOT,
                env={**__import__("os").environ,
                     "PYTHONPATH": f"{ROOT / 'src'}:{ROOT / 'examples'}"},
                text=True, capture_output=True, check=False, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        child_state = json.loads(result.stdout)
        self.assertEqual(child_state["encounter"], encounter.id)
        self.assertEqual(child_state["initial_rng"], native_history._plain(origin))
        self.assertEqual(child_state["current_rng"], native_history._plain(rng.state))

    def test_generated_v12_arena_save_migrates_to_canonical_native_save(self):
        """A current legacy /12 Arena artifact can enter native Save/Load losslessly."""
        from arena_browser_session import GeneratedArenaSession

        session = GeneratedArenaSession(root_seed_factory=lambda: 20261116)
        session.generate({"starting_experience": "10000", "width_cells": "5",
                          "height_cells": "5"})
        session.choose_run()
        session.advance_one_second()
        legacy_wire = session.save_encounter_bytes()
        world, encounter, rng = load_legacy_arena_save(legacy_wire)
        self.assertIs(world.event_history[encounter.id], encounter)
        self.assertIsNotNone(encounter.arena_activation)
        activation = encounter.arena_activation.to_dict()
        awareness = {key: tuple(sorted(value))
                     for key, value in sorted(encounter.awareness.items())}
        ledgers = {being_id: world.get_object_by_id(being_id)._arena_perception_ledger
                   for being_id in encounter.being_list}
        history_log = native_history.capture(encounter)
        history_query = native_history.NativeHistoryQuery(history_log)
        for being_id, ledger in ledgers.items():
            for boundary in range(encounter.last_processed_boundary + 1):
                expected = {}
                for row in ledger._history:
                    if row.visibility_boundary <= boundary:
                        expected[row.entity_id] = native_history._plain(row)
                self.assertEqual(history_query.observer_knowledge_at(
                    boundary, being_id), expected)
        self.assertEqual(history_query.observer_knowledge_at(
            encounter.last_processed_boundary, "not-an-observer"), {})
        corrupt_history = json.loads(json.dumps(history_log))
        owner_id = next(iter(corrupt_history["observer_knowledge"]["initial"]))
        entity_id = next(iter(corrupt_history["observer_knowledge"]["initial"][owner_id]))
        corrupt_history["observer_knowledge"]["initial"][owner_id][entity_id][
            "fields"]["observer_id"] = "forged-observer"
        with self.assertRaisesRegex(native_history.NativeHistoryRejected,
                                    "observer evidence owner"):
            native_history.validate(native_history._seal(
                {key: value for key, value in corrupt_history.items()
                 if key != "sha256"}))
        native_wire = export_save(encounter)
        restored_world, restored_encounter, restored_rng = load_save(native_wire)
        self.assertEqual(export_save(restored_encounter), native_wire)
        self.assertEqual(restored_world.id, world.id)
        self.assertEqual(restored_encounter.id, encounter.id)
        self.assertEqual(restored_encounter.arena_activation.to_dict(), activation)
        self.assertEqual({key: tuple(sorted(value)) for key, value in
                          sorted(restored_encounter.awareness.items())}, awareness)
        self.assertEqual(restored_rng.state, rng.state)
        for being_id, ledger in ledgers.items():
            restored = restored_world.get_object_by_id(being_id)._arena_perception_ledger
            self.assertIsNotNone(restored)
            self.assertEqual(restored.observer_id, ledger.observer_id)
            self.assertEqual(restored._history, ledger._history)
        restored_log = native_history.current_recording(restored_encounter)
        restored_query = native_history.NativeHistoryQuery(restored_log)
        for being_id, ledger in ledgers.items():
            for boundary in range(restored_encounter.last_processed_boundary + 1):
                expected = {}
                for row in ledger._history:
                    if row.visibility_boundary <= boundary:
                        expected[row.entity_id] = native_history._plain(row)
                self.assertEqual(restored_query.observer_knowledge_at(
                    boundary, being_id), expected)

        # A valid /7 native history has no explicit schedule-availability
        # marker or passive observer timeline. Its scheduler projection came
        # from the first receipt, so it is not exposed as boundary-zero state.
        legacy_payload = json.loads(native_wire)
        legacy_history = {key: value for key, value in legacy_payload["history"].items()
                          if key != "sha256"}
        legacy_history.pop("observer_knowledge")
        legacy_history["initial"].pop("initial_schedule_available")
        legacy_history["schema"] = native_history.RECEIPT_FACT_SCHEMA
        legacy_payload["history"] = native_history._seal(legacy_history)
        legacy_unsigned = {key: value for key, value in legacy_payload.items()
                           if key != "sha256"}
        legacy_payload["sha256"] = hashlib.sha256(
            native_persistence._canonical(legacy_unsigned)).hexdigest()
        legacy_wire = native_persistence._canonical(legacy_payload)
        migrated_world, migrated_encounter, _migrated_rng = load_save(legacy_wire)
        self.assertIs(migrated_world.event_history[migrated_encounter.id],
                      migrated_encounter)
        migrated_log = native_history.current_recording(migrated_encounter)
        migrated_query = native_history.NativeHistoryQuery(migrated_log)
        self.assertFalse(migrated_log['initial']['initial_schedule_available'])
        self.assertIsNone(migrated_query.schedule_at(0))
        for boundary in range(1, encounter.last_processed_boundary + 1):
            self.assertEqual(migrated_query.schedule_at(boundary),
                             restored_query.schedule_at(boundary))
        migrated_wire = export_save(migrated_encounter)
        self.assertEqual(export_save(load_save(migrated_wire)[1]), migrated_wire)

    def test_arena_observer_knowledge_appends_only_committed_evidence_changes(self):
        from arena_browser_session import GeneratedArenaSession

        session = GeneratedArenaSession(root_seed_factory=lambda: 20261116)
        session.generate({"starting_experience": "10000", "width_cells": "5",
                          "height_cells": "5"})
        session.choose_run()
        encounter = session._active.encounter
        # Attach before the first commit, then let the ordinary native
        # publisher create boundary evidence and append it on the next turn.
        export_save(encounter)
        session.advance_one_second()
        actor_id = encounter.being_list[0]
        encounter.schedule_action(DelayAction(
            encounter, actor_id, defense=0, start_time=encounter.time,
            id="arena-observer-history-second-boundary"))
        encounter.step(1)
        log = native_history.current_recording(encounter)
        self.assertEqual(log["schema"], native_history.SCHEMA)
        reader = native_history.NativeHistoryQuery(log)
        for boundary in range(encounter.last_processed_boundary + 1):
            for observer_id in encounter.being_list:
                expected = {}
                ledger = encounter.get_being(observer_id)._arena_perception_ledger
                for evidence in ledger._history:
                    if evidence.visibility_boundary <= boundary:
                        expected[evidence.entity_id] = native_history._plain(evidence)
                self.assertEqual(reader.observer_knowledge_at(
                    boundary, observer_id), expected)

    def test_legacy_v10_v11_pristine_arena_migrate_and_start_natively(self):
        """Accepted pristine legacy files migrate without inventing an Action."""
        import os
        from activities import DelayAction

        script = r'''import hashlib,json,sys
import native_history
from activities import DelayAction
from atomic_publication import RNGCursor
from native_persistence import load_save,export_save
wire=open(sys.argv[1],'rb').read();version=sys.argv[2]
world,enc,rng=load_save(wire)
assert enc.progression_mode=='transactional'
assert export_save(enc)==wire
actor_id=enc.being_list[0]
action_id='legacy-migration-first-delay-'+version
action=DelayAction(enc,actor_id,0,enc.time,id=action_id)
wrong_rng=RNGCursor(rng.state)
try:
 enc.activate_arena_for_player_action(actor_id,action,rng_owner=wrong_rng)
 raise AssertionError('foreign RNG owner was accepted')
except RuntimeError as error:
 assert 'RNG owner differs' in str(error)
assert not enc.initiated and enc.arena_activation is None
assert action_id not in world.event_history and not enc.pending_action_list
_,activation=enc.activate_arena_for_player_action(actor_id,action,rng_owner=rng)
enc.step(1);receipt=enc.inspect_committed(1).action(action.id)
print(json.dumps({'world_id':world.id,'encounter_id':enc.id,
 'being_ids':list(enc.being_list),'time':enc.time,'boundary':enc.last_processed_boundary,
 'activation':activation.to_dict(),'action_id':action.id,
 'outcome':receipt.facts.outcome,'position':world.get_object_by_id(actor_id).get_position().as_tuple(),
 'hp':world.get_object_by_id(actor_id).get_hit_points(),'rng':rng.state,
 'history':hashlib.sha256(native_history.encode(native_history.capture(enc))).hexdigest(),
 'observers':sorted((key,tuple(sorted(value))) for key,value in enc.awareness.items()),
 'arena_imports':sorted(set(sys.modules)&{'arena_browser_session','arena_server','npcgen'})},sort_keys=True))'''
        for version, filename in (
                ('v10', 'legacy-per-scale-010-v10.uarena'),
                ('v11', 'legacy-per-scale-011-v11.uarena')):
            with self.subTest(version=version), tempfile.TemporaryDirectory() as directory:
                legacy_wire = (ROOT / 'tests/fixtures/arena' / filename).read_bytes()
                control_world, control_encounter, control_rng = load_legacy_arena_save(legacy_wire)
                control_encounter.enable_transactional_progression(
                    quiescent=True, rng_owner=control_rng)
                native_wire = export_save(control_encounter)
                control_actor = control_encounter.being_list[0]
                action_id = 'legacy-migration-first-delay-' + version
                control_action = DelayAction(control_encounter, control_actor, 0,
                                             control_encounter.time, id=action_id)
                _, control_activation = control_encounter.activate_arena_for_player_action(
                    control_actor, control_action, rng_owner=control_rng)
                control_encounter.step(1)
                control_receipt = control_encounter.inspect_committed(1).action(action_id)
                expected = {
                    'world_id': control_world.id,
                    'encounter_id': control_encounter.id,
                    'being_ids': list(control_encounter.being_list),
                    'time': control_encounter.time,
                    'boundary': control_encounter.last_processed_boundary,
                    'activation': control_activation.to_dict(),
                    'action_id': action_id,
                    'outcome': control_receipt.facts.outcome,
                    'position': control_world.get_object_by_id(control_actor).get_position().as_tuple(),
                    'hp': control_world.get_object_by_id(control_actor).get_hit_points(),
                    'rng': control_rng.state,
                    'history': hashlib.sha256(native_history.encode(
                        native_history.capture(control_encounter))).hexdigest(),
                    'observers': sorted((key, tuple(sorted(value)))
                                        for key, value in control_encounter.awareness.items()),
                    'arena_imports': [],
                }
                source = Path(directory) / f'{version}.native.json'
                source.write_bytes(native_wire)
                result = subprocess.run(
                    [sys.executable, '-B', '-c', script, str(source), version],
                    cwd=directory,
                    env={**os.environ,
                         'PYTHONPATH': f'{ROOT / "src"}:{ROOT / "examples"}'},
                    text=True, capture_output=True, check=False, timeout=60)
                self.assertEqual(result.returncode, 0, result.stderr)
                restored = json.loads(result.stdout)
                self.assertEqual(restored, json.loads(json.dumps(expected)))

    def test_legacy_arena_v10_v11_v12_read_through_native_graph_api(self):
        """The native consumer can strictly coexist with all accepted old Saves."""
        from arena_browser_session import GeneratedArenaSession

        current = GeneratedArenaSession(root_seed_factory=lambda: 20261116)
        current.generate({"starting_experience": "10000", "width_cells": "5",
                         "height_cells": "5"})
        current.choose_run()
        current.advance_one_second()
        candidate = current.active_candidate
        run_action = next(action for action in candidate.universe.event_history.values()
                          if type(action).__name__ == "RunAction")
        actor_id = run_action.actor_id
        continuation = (candidate.encounter, candidate.universe, current._rng_cursor,
                        actor_id, run_action.id)
        cases = [
            ("v10", (ROOT / "tests/fixtures/arena/legacy-per-scale-010-v10.uarena").read_bytes(), None),
            ("v11", (ROOT / "tests/fixtures/arena/legacy-per-scale-011-v11.uarena").read_bytes(), None),
            ("v12", current.save_encounter_bytes(), continuation),
        ]
        script = r'''import json,sys
import hashlib
import native_history
from native_persistence import load_legacy_arena_save
world,enc,rng=load_legacy_arena_save(open(sys.argv[1],'rb').read())
assert world.event_history.get(enc.id) is enc
assert enc.universe is world
continued=False
if len(sys.argv)==4:
 actor=world.get_object_by_id(sys.argv[2]); action=world.get_event_by_id(sys.argv[3])
 assert actor.id==action.actor_id and action.resolution is not None
 enc.step(1)
 continued=True
assert not (set(__import__('sys').modules) & {
 'arena_browser_session','arena_server','npcgen'})
if continued:
 assert native_history.NativeHistoryQuery(native_history.capture(enc)).schedule_at(0) is None
print(json.dumps({'universe':world.id,'encounter':enc.id,
 'boundary':enc.last_processed_boundary,'time':enc.time,
 'registry':len(world.object_registry.object_instances),'continued':continued,
 'action_outcome':None if not continued else action.resolution.outcome,
 'actor_position':None if not continued else actor.get_position().as_tuple(),
 'rng':None if not continued else rng.state},sort_keys=True))'''
        import os
        for label, wire, control in cases:
            with self.subTest(version=label), tempfile.TemporaryDirectory() as directory:
                source = Path(directory) / f"{label}.uarena"
                source.write_bytes(wire)
                arguments = [sys.executable, "-B", "-c", script, str(source)]
                expected = None
                if control is not None:
                    control_encounter, control_world, control_rng, control_actor, control_action = control
                    control_encounter.step(1)
                    expected = {
                        "universe": control_world.id,
                        "encounter": control_encounter.id,
                        "boundary": control_encounter.last_processed_boundary,
                        "time": control_encounter.time,
                        "registry": len(control_world.object_registry.object_instances),
                        "continued": True,
                        "action_outcome": control_world.get_event_by_id(control_action).resolution.outcome,
                        "actor_position": control_world.get_object_by_id(control_actor).get_position().as_tuple(),
                        "rng": control_rng.state,
                    }
                    arguments.extend((control_actor, control_action))
                result = subprocess.run(
                    arguments, cwd=ROOT,
                    env={**os.environ,
                         "PYTHONPATH": f"{ROOT / 'src'}:{ROOT / 'examples'}"},
                    text=True, capture_output=True, check=False, timeout=60)
                self.assertEqual(result.returncode, 0, result.stderr)
                restored = json.loads(result.stdout)
                self.assertTrue(restored["universe"])
                self.assertTrue(restored["encounter"])
                self.assertGreater(restored["registry"], 0)
                if expected is None:
                    self.assertFalse(restored["continued"])
                else:
                    self.assertEqual(restored, json.loads(json.dumps(expected)))

    def test_fresh_process_restores_pending_action_and_continues_natively(self):
        demo = encounter_delta_headless.build_demo(until=4)
        encounter = demo["encounter"]
        actor_id = encounter.being_list[1]
        recorder = NativeHistoryRecorder.attach(encounter)
        action = DelayAction(encounter, actor_id, defense=0, start_time=4,
                             id="native-save-pending-delay")
        encounter.schedule_action(action)
        with patch.object(native_history, "capture",
                          side_effect=AssertionError("recorder history was recaptured")):
            save = export_save(encounter)
        before_ids = {
            "world": encounter.universe.id,
            "encounter": encounter.id,
            "beings": sorted(encounter.universe.object_registry.object_instances),
            "actions": sorted(encounter.universe.event_history),
        }

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "native-save.json"
            self.assertEqual(write_save(encounter, path), len(save))
            saved_bytes = path.read_bytes()
            self.assertEqual(saved_bytes, save)
            with self.assertRaisesRegex(NativeSaveRejected, "already exists"):
                write_save(encounter, path)
            self.assertEqual(path.read_bytes(), saved_bytes)
            encounter.step(1)
            self.assertEqual(recorder.latest_boundary, 5)
            expected = {
                "time": encounter.time,
                "rng": demo["rng_owner"].state,
                "hp": [encounter.get_being(identity).get_hit_points()
                       for identity in encounter.being_list],
                "history": hashlib.sha256(native_history.encode(
                    native_history.capture(encounter))).hexdigest(),
                "receipt_actions": list(encounter._atomic_interval_history[-1].action_ids),
            }
            child = r'''import hashlib,json,sys
import native_history
from native_persistence import load_path
world,encounter,rng=load_path(sys.argv[1])
assert encounter.id == 'headless-encounter' and encounter.time == 4
assert any(row['state'] == 'accepted' and row['action_ids'] == ['native-save-pending-delay']
 for row in encounter._choice_book.summary()['choices'])
encounter.step(1)
print(json.dumps({'world':world.id,'encounter':encounter.id,'time':encounter.time,
 'rng':rng.state,'hp':[encounter.get_being(i).get_hit_points() for i in encounter.being_list],
 'history':hashlib.sha256(native_history.encode(native_history.capture(encounter))).hexdigest(),
 'receipt_actions':list(encounter._atomic_interval_history[-1].action_ids),
 'arena_app_imports':sorted(set(sys.modules)&{'arena_browser_session','arena_server','npcgen'})},sort_keys=True))'''
            result = subprocess.run(
                [sys.executable, "-B", "-c", child, str(path)], cwd=directory,
                env={**__import__("os").environ,
                     "PYTHONPATH": f"{ROOT / 'src'}:{ROOT / 'examples'}"},
                text=True, capture_output=True, check=False, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        restored = json.loads(result.stdout)
        self.assertEqual(restored["world"], before_ids["world"])
        self.assertEqual(restored["encounter"], before_ids["encounter"])
        self.assertEqual(restored["time"], expected["time"])
        self.assertEqual(restored["rng"], json.loads(json.dumps(expected["rng"])))
        self.assertEqual(restored["hp"], expected["hp"])
        self.assertEqual(restored["history"], expected["history"])
        self.assertEqual(restored["receipt_actions"], expected["receipt_actions"])
        self.assertEqual(restored["arena_app_imports"], [])

    def test_generated_arena_first_choice_native_save_round_trips_and_continues(self):
        from arena_browser_session import GeneratedArenaSession
        session = GeneratedArenaSession(root_seed_factory=lambda: 20261116)
        session.generate({"starting_experience": "10000", "width_cells": "5",
                          "height_cells": "5"})
        session.choose_run()
        candidate = session.active_candidate
        encounter, world = candidate.encounter, candidate.universe
        activation = encounter.arena_activation
        self.assertIsNotNone(activation)
        action = world.get_event_by_id(
            encounter._choice_book._choices[activation.choice_id].view.action_ids[0])
        self.assertIs(type(action), RunAction)
        save = export_save(encounter)

        encounter.step(1)
        receipt = encounter.inspect_committed(1).action(action.id)
        expected = {
            "world_id": world.id,
            "encounter_id": encounter.id,
            "activation": activation.to_dict(),
            "action_id": action.id,
            "outcome": receipt.facts.outcome,
            "actor_id": action.actor_id,
            "position": world.get_object_by_id(action.actor_id).get_position().as_tuple(),
            "rng": session._rng_cursor.state,
            "history": hashlib.sha256(native_history.encode(
                native_history.capture(encounter))).hexdigest(),
        }
        child = r'''import hashlib,json,sys
from native_persistence import load_save
import native_history
world,enc,rng=load_save(open(sys.argv[1],'rb').read())
actor_id,action_id,choice_id=sys.argv[2:]
activation=enc.arena_activation
assert activation is not None and activation.actor_id==actor_id
assert activation.choice_id==choice_id and activation.encounter_id==enc.id
assert enc.choice_for_action(action_id).state in ('accepted','executing')
enc.step(1);receipt=enc.inspect_committed(1).action(action_id)
print(json.dumps({'world_id':world.id,'encounter_id':enc.id,
 'activation':activation.to_dict(),'action_id':action_id,
 'outcome':receipt.facts.outcome,'actor_id':actor_id,
 'position':world.get_object_by_id(actor_id).get_position().as_tuple(),
 'rng':rng.state,'history':hashlib.sha256(native_history.encode(
  native_history.capture(enc))).hexdigest(),
 'arena_app_imports':sorted(set(sys.modules)&{'arena_browser_session','arena_server','npcgen'})},sort_keys=True))'''
        import os
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "arena-native-initial.json"
            path.write_bytes(save)
            result = subprocess.run(
                [sys.executable, "-B", "-c", child, str(path), action.actor_id,
                 action.id, activation.choice_id], cwd=directory,
                env={**os.environ,
                     "PYTHONPATH": f"{ROOT / 'src'}:{ROOT / 'examples'}"},
                text=True, capture_output=True, check=False, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        restored = json.loads(result.stdout)
        self.assertEqual(restored.pop("arena_app_imports"), [])
        self.assertEqual(restored, json.loads(json.dumps(expected)))

    def test_projectile_shield_interception_continues_after_native_fresh_process_load(self):
        """A saved in-flight projectile retains its later native shield result."""
        import random
        from being import BeingInstance
        from activities import ThrowAction
        from native_throw_arena import build_native_scene

        world, encounter, actor, projectile, rng, original = build_native_scene(seed=116)
        encounter._choice_book.undo(encounter._choice_book.for_action(original.id).id)
        definition = world.library.being_dictionary.get_object_definition("Human")
        target = BeingInstance(definition, "Native Shielded Target",
                              id="native-persist/shielded-target")
        target.set_position(CartesianPosition(8.0, 0.0, 0.0))
        world.add_object(target)
        encounter.add_being(target.id)
        shield_id = world.make_weapon_for_being(target.id, "Small shield",
                                               "Native target shield")
        world.arm_being(target.id, shield_id, "shield hand")
        encounter.add_object(shield_id)
        action = ThrowAction(world, actor.id, projectile.id, encounter.time,
            heavy_load_reference_lb=100.0, elevation_degrees=45,
            target_id=target.id, id="native-persist/shielded-throw")
        encounter.schedule_choice((action,))
        rng.state = random.Random(116).getstate()
        encounter.step(4)
        self.assertEqual(action.resolution.outcome, "released")
        self.assertIsNone(projectile.__dict__["_projectile_flight"].impact_outcome)
        wire = export_save(encounter)

        def run_to_impact(enc, world, cursor):
            from atomic_publication import target_effects_from
            thrown = world.get_object_by_id(projectile.id)
            victim = world.get_object_by_id(target.id)
            shield = world.get_object_by_id(shield_id)
            for _ in range(5):
                if thrown.__dict__["_projectile_flight"].impact_outcome is not None:
                    break
                enc.step(1)
            effects = [row.effect for row in target_effects_from(shield, action.id)]
            protection = next(effect for effect in effects
                              if type(effect).__name__ == "ProtectionEffect"
                              and effect.layer == "shield")
            durability = [effect.amount for effect in effects
                          if type(effect).__name__ == "DamageEffect"
                          and effect.component == "shield"]
            return {"time": enc.time,
                    "outcome": thrown.__dict__["_projectile_flight"].impact_outcome,
                    "hp": victim.get_hit_points(), "shield_hp": shield.hit_points(),
                    "intercepted": protection.intercepted,
                    "incoming": protection.incoming, "passed": protection.passed,
                    "durability": durability,
                    "rng": cursor.state,
                    "history": hashlib.sha256(native_history.encode(
                        native_history.capture(enc))).hexdigest()}

        expected = run_to_impact(encounter, world, rng)
        history_log = native_history.capture(encounter)
        history_query = native_history.NativeHistoryQuery(history_log)
        receipt_by_boundary = {
            receipt.boundary: receipt
            for receipt in encounter._atomic_interval_history}
        for boundary in range(encounter.last_processed_boundary + 1):
            receipt = receipt_by_boundary.get(boundary)
            states = ({} if receipt is None else
                      receipt.inspection.projectile_states)
            recorded = states.get(projectile.id)
            self.assertEqual(
                history_query.projectile_state_at(projectile.id, boundary),
                None if recorded is None else native_history._plain(recorded))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "native-shielded-projectile.json"
            path.write_bytes(wire)
            child = r'''import hashlib,json,sys
import native_history
from atomic_publication import target_effects_from
from native_persistence import load_path
world,enc,rng=load_path(sys.argv[1])
thrown=world.get_object_by_id(sys.argv[2]); victim=world.get_object_by_id(sys.argv[3])
shield=world.get_object_by_id(sys.argv[4])
for _ in range(5):
 if thrown.__dict__['_projectile_flight'].impact_outcome is not None: break
 enc.step(1)
effects=[row.effect for row in target_effects_from(shield,sys.argv[5])]
protection=next(effect for effect in effects if type(effect).__name__=='ProtectionEffect' and effect.layer=='shield')
durability=[effect.amount for effect in effects if type(effect).__name__=='DamageEffect' and effect.component=='shield']
print(json.dumps({'time':enc.time,
 'outcome':thrown.__dict__['_projectile_flight'].impact_outcome,
 'hp':victim.get_hit_points(),'shield_hp':shield.hit_points(),
 'intercepted':protection.intercepted,'incoming':protection.incoming,
 'passed':protection.passed,'durability':durability,'rng':rng.state,
 'history':hashlib.sha256(native_history.encode(native_history.capture(enc))).hexdigest()},sort_keys=True))'''
            import os
            result = subprocess.run(
                [sys.executable, "-B", "-c", child, str(path), projectile.id,
                 target.id, shield_id, action.id], cwd=ROOT,
                env={**os.environ,
                     "PYTHONPATH": f"{ROOT / 'src'}:{ROOT / 'examples'}"},
                text=True, capture_output=True, check=False, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), json.loads(json.dumps(expected)))
        self.assertEqual(expected["outcome"], "hit")
        self.assertTrue(expected["intercepted"])

    def test_strict_outer_integrity_and_duplicate_keys_are_rejected(self):
        demo = encounter_delta_headless.build_demo(until=4)
        wire = export_save(demo["encounter"])
        value = json.loads(wire)
        value["history"]["latest_boundary"] = 3
        tampered = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
        with self.assertRaisesRegex(NativeSaveRejected, "integrity"):
            load_save(tampered)

        # Recompute both public digests after corrupting a valid property
        # preimage. Integrity hashes are not a substitute for causal checks.
        value = json.loads(wire)
        history = value["history"]
        delta = next(change for row in history["boundaries"]
                     if row.get("kind") != "quiet_span"
                     for change in row["changes"]
                     if change.get("before") is True and "before_value" in change)
        delta["before_value"] = {"forged": "but rehashed"}
        history.pop("sha256")
        history["sha256"] = hashlib.sha256(
            native_persistence._canonical(history)).hexdigest()
        value.pop("sha256")
        value["sha256"] = hashlib.sha256(
            native_persistence._canonical(value)).hexdigest()
        rehashed = native_persistence._canonical(value)
        with self.assertRaisesRegex(NativeSaveRejected, "preimage"):
            load_save(rehashed)
        with self.assertRaisesRegex(NativeSaveRejected, "duplicate"):
            load_save(b'{"schema":"a","schema":"b"}')

    def test_rejected_first_export_does_not_attach_history_recorder(self):
        demo = encounter_delta_headless.build_demo(until=4)
        encounter = demo['encounter']
        self.assertFalse(native_history.has_recorder(encounter))
        with patch('native_persistence.MAX_BYTES', 1):
            with self.assertRaisesRegex(NativeSaveRejected, 'portable size limit'):
                export_save(encounter)
        self.assertFalse(native_history.has_recorder(encounter))
        accepted = export_save(encounter)
        self.assertTrue(native_history.has_recorder(encounter))
        self.assertEqual(load_save(accepted)[1].id, encounter.id)

    def test_native_melee_damage_history_and_fresh_process_continuation(self):
        world, encounter, rng, attacker, defender, weapon_id = self._combat_encounter()
        first = MeleeStrike(encounter, attacker.id, defender.id, weapon_id,
                            motion="thrust", reach=2, strategy=Strategy())
        encounter.schedule_action(first)
        encounter.step(4)
        facts = encounter.inspect_committed(4).action(first.id).facts
        self.assertEqual(facts.outcome, "normal")
        self.assertLess(defender.get_hit_points(), 100)

        recorder = NativeHistoryRecorder.attach(encounter)
        second = MeleeStrike(encounter, attacker.id, defender.id, weapon_id,
                             motion="thrust", reach=2, strategy=Strategy())
        encounter.schedule_action(second)
        save = export_save(encounter)
        encounter.step(4)
        self.assertEqual(recorder.latest_boundary, 8)
        expected = {
            "time": encounter.time,
            "rng": json.loads(json.dumps(rng.state)),
            "hp": [attacker.get_hit_points(), defender.get_hit_points()],
            "history": hashlib.sha256(native_history.encode(
                native_history.capture(encounter))).hexdigest(),
            "actions": list(encounter._atomic_interval_history[-1].action_ids),
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "native-combat-save.json"
            path.write_bytes(save)
            child = r'''import hashlib,json,sys
import native_history
from native_persistence import load_path
world,encounter,rng=load_path(sys.argv[1])
encounter.step(4)
print(json.dumps({'time':encounter.time,'rng':rng.state,
 'hp':[encounter.get_being(i).get_hit_points() for i in encounter.being_list],
 'history':hashlib.sha256(native_history.encode(native_history.capture(encounter))).hexdigest(),
 'actions':list(encounter._atomic_interval_history[-1].action_ids)},sort_keys=True))'''
            result = subprocess.run(
                [sys.executable, "-B", "-c", child, str(path)], cwd=ROOT,
                env={**__import__("os").environ,
                     "PYTHONPATH": f"{ROOT / 'src'}:{ROOT / 'examples'}"},
                text=True, capture_output=True, check=False, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), expected)

    def test_running_action_history_and_pending_continuation_in_fresh_process(self):
        """A real movement Action survives a mid-run native Save without replay."""
        world, encounter, rng, actor, _defender, _weapon_id = self._combat_encounter()
        from physiology_registry import PhysiologyRegistry, PhysiologyDefinition
        registry = PhysiologyRegistry((PhysiologyDefinition(
            "native-human@1", model="human-r4"),))
        encounter.set_physiology_registry(registry)
        for being_id in encounter.being_list:
            encounter.get_being(being_id).set_physiology_id("native-human@1")
        actor.set_physical_fatigue(.7, .8)
        actor.exertion.set_activity_level("run")
        actor.exertion.set_load_level("heavy")
        actor.exertion.set_fatigue_level(1)
        actor.exertion.set_accumulated_exertion(17)
        action = RunAction(world, actor.id, encounter.time, 2, .75, 250,
                           id="native-run-pending-continuation")
        encounter.schedule_action(action)
        encounter.step(1, velocities={actor.id: (.5, 0, 0)})
        self.assertEqual(encounter.time, 1)
        self.assertEqual(actor.get_position(), CartesianPosition(.5, 0, 0))
        self.assertEqual(action.start_position, CartesianPosition(0, 0, 0))
        self.assertIsNone(action.resolution)
        saved_fatigue_view = encounter.last_fatigue_frame.view(actor.id).to_dict()
        saved_physiology_versions = {
            mode: encounter.last_fatigue_frame.physiology(actor.id, mode=mode).version_hash
            for mode in ("ordinary", "running")}

        wire = export_save(encounter)
        query = native_history.NativeHistoryQuery(
            native_history.current_recording(encounter))
        for boundary, expected_x in ((1, .5),):
            position = query.entity_context_at(boundary)[actor.id]["fields"]["position"]["fields"]
            self.assertEqual(float.fromhex(position["x"]["$number"]), expected_x)
            fatigue = query.fatigue_context_at(boundary)[actor.id]
            self.assertEqual(float.fromhex(
                fatigue["physical_fatigue"]["q"]["$number"]), .7)
            self.assertEqual(fatigue["physiology"]["ordinary"]["version_hash"],
                             saved_physiology_versions["ordinary"])

        encounter.step(1, velocities={actor.id: (.5, 0, 0)})
        self.assertEqual(actor.get_position(), CartesianPosition(1, 0, 0))
        self.assertEqual(actor.get_skill_experience("run"), 250)
        self.assertEqual(actor.get_skill_level("run"), 1)
        run_commit = encounter.inspect_committed(boundary=2).action(action.id)
        self.assertEqual(run_commit.facts.outcome, "success")
        self.assertEqual(encounter._atomic_interval_history[-1].action_ids,
                         (action.id,))
        practice_effects = [row.effect for row in run_commit.effects
                            if type(row.effect).__name__ == "PracticeEffect"]
        self.assertEqual(len(practice_effects), 1)
        self.assertEqual(practice_effects[0].source_action_id, action.id)
        run_result = {
            "outcome": run_commit.facts.outcome,
            "practice_effect_sources": [row.source_action_id for row in practice_effects],
            "receipt_action_ids": list(encounter._atomic_interval_history[-1].action_ids),
        }
        encounter.step(1)
        expected = {
            "time": encounter.time,
            "position": actor.get_position().as_tuple(),
            "experience": actor.get_skill_experience("run"),
            "skill_uses": [{"skill": row.skill_name, "experience": row.experience,
                            "level_before": row.level_before,
                            "level_after": row.level_after, "time": row.time,
                            "exercise_experience": [use.experience for use in row.exercises]}
                           for row in actor.skill_use_history],
            "run_result": run_result,
            "receipt_action_ids": list(encounter._atomic_interval_history[-1].action_ids),
            "physical_fatigue": actor.get_physical_fatigue().to_dict(actor.physiology_id),
            "fatigue_view": encounter.last_fatigue_frame.view(actor.id).to_dict(),
            "physiology_version": encounter.last_fatigue_frame.physiology(
                actor.id).version_hash,
            "fatigue_frame_history": encounter.fatigue_frame_history,
            "exertion": json.loads(actor.exertion.to_json()),
            "rng": json.loads(json.dumps(rng.state)),
            "history": hashlib.sha256(native_history.encode(
                native_history.capture(encounter))).hexdigest(),
        }
        query = native_history.NativeHistoryQuery(
            native_history.current_recording(encounter))
        versions = {}
        for boundary in (1, 2, 3):
            context = query.entity_context_at(boundary)[actor.id]["fields"]
            position = context["position"]["fields"]
            self.assertEqual(float.fromhex(position["x"]["$number"]), .5 if boundary == 1 else 1.0)
            exertion = context["pre_action"]["exertion"]
            self.assertEqual(exertion["accumulated_exertion"], 17)
            self.assertEqual(exertion["activity_level"], "run")
            fatigue = query.fatigue_context_at(boundary)[actor.id]
            self.assertEqual(float.fromhex(
                fatigue["physical_fatigue"]["q"]["$number"]), .7)
            versions[boundary] = fatigue["physiology"]["running"]["version_hash"]
        self.assertEqual(versions[1], versions[2])
        self.assertNotEqual(versions[2], versions[3])

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "native-run-pending-save.json"
            path.write_bytes(wire)
            child = r'''import hashlib,json,sys
import native_history
from action_evaluation import PracticeEffect
from native_persistence import load_path
world,encounter,rng=load_path(sys.argv[1])
action=world.event_history['native-run-pending-continuation']
actor=world.get_object_by_id(action.actor_id)
assert actor.physiology_id == 'native-human@1'
assert encounter.last_fatigue_frame.view(actor.id).to_dict() == json.loads(sys.argv[2])
saved_versions=json.loads(sys.argv[3])
assert {mode:encounter.last_fatigue_frame.physiology(actor.id,mode=mode).version_hash
 for mode in ('ordinary','running')} == saved_versions
assert encounter.time == 1 and action.start_position.as_tuple() == (0.0,0.0,0.0)
assert action.resolution is None and actor.get_position().as_tuple() == (.5,0.0,0.0)
encounter.step(1,velocities={actor.id:(.5,0,0)})
committed=encounter.inspect_committed(boundary=2).action(action.id)
facts=committed.facts
practice=[row.effect for row in committed.effects if type(row.effect) is PracticeEffect]
run_result={'outcome':facts.outcome,
 'practice_effect_sources':[row.source_action_id for row in practice],
 'receipt_action_ids':list(encounter._atomic_interval_history[-1].action_ids)}
encounter.step(1)
print(json.dumps({'time':encounter.time,'position':actor.get_position().as_tuple(),
 'experience':actor.get_skill_experience('run'),
 'skill_uses':[{'skill':row.skill_name,'experience':row.experience,
  'level_before':row.level_before,'level_after':row.level_after,'time':row.time,
  'exercise_experience':[use.experience for use in row.exercises]}
  for row in actor.skill_use_history],
 'run_result':run_result,
 'receipt_action_ids':list(encounter._atomic_interval_history[-1].action_ids),
 'physical_fatigue':actor.get_physical_fatigue().to_dict(actor.physiology_id),
 'fatigue_view':encounter.last_fatigue_frame.view(actor.id).to_dict(),
 'physiology_version':encounter.last_fatigue_frame.physiology(actor.id).version_hash,
 'fatigue_frame_history':encounter.fatigue_frame_history,
 'exertion':json.loads(actor.exertion.to_json()),
 'rng':rng.state,
 'history':hashlib.sha256(native_history.encode(native_history.capture(encounter))).hexdigest()},
 sort_keys=True))'''
            import os
            result = subprocess.run(
                [sys.executable, "-B", "-c", child, str(path),
                 json.dumps(saved_fatigue_view), json.dumps(saved_physiology_versions)], cwd=directory,
                env={**os.environ,
                     "PYTHONPATH": f"{ROOT / 'src'}:{ROOT / 'examples'}"},
                text=True, capture_output=True, check=False, timeout=45)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout),
                         json.loads(json.dumps(expected)))

    def test_statistical_group_is_supported_and_unbound_observers_fail_closed(self):
        group_fixture = inspection_fixtures.InspectionFixture()
        group_fixture.setUp()
        group_fixture.f.f.f.group()
        group_fixture.commit()
        before = group_fixture.raw()
        group_save = export_save(group_fixture.enc)
        restored_world, restored_encounter, _ = load_save(group_save)
        self.assertEqual(restored_encounter.id, group_fixture.enc.id)
        self.assertIn("group-one", restored_world.object_registry.object_instances)
        self.assertEqual(group_fixture.raw(), before)

        observer_fixture = inspection_fixtures.InspectionFixture()
        observer_fixture.setUp()
        group = observer_fixture.f.f.f.group()
        history = observer_fixture.f.f.f.history()
        from field_observation import BeliefLedger
        from history_conversation import AskAboutPastAction
        observer_fixture.enable()
        first = observer_fixture.f.f.observe(observer_fixture.a, group,
            ledger=BeliefLedger(observer_fixture.a.id))
        second = observer_fixture.f.f.observe(observer_fixture.b, group,
            ledger=BeliefLedger(observer_fixture.b.id))
        accounts = []
        ask = AskAboutPastAction(observer_fixture.world, observer_fixture.c.id,
            observer_fixture.a.id, 0, episode_time=0, topic="lessons",
            generate=observer_fixture.f.f.f.recipe(history),
            received_accounts=accounts)
        observer_fixture.enc.schedule_choice((first, second, ask))
        observer_fixture.enc.step(1)
        before = observer_fixture.raw()
        with self.assertRaisesRegex(NativeSaveRejected,
                                    "missing durable committed recipient binding") as refused:
            export_save(observer_fixture.enc)
        self.assertEqual(observer_fixture.raw(), before)

    def test_native_stun_condition_and_interrupted_action_resume_in_fresh_process(self):
        fixture = action_fixtures.TestActionEvaluation()
        fixture.setUp()
        fixture.b.set_position(CartesianPosition(.2, 0, 0))
        skills = fixture.world.get_skill_dictionary()
        fixture.a.set_skill_level(skills, "unarmed combat", 5)
        fixture.a.set_skill_level(skills, "stun", 2)
        fixture.a.current.tags["universe.stun_categories"] = {"humanoid": 2}
        fixture.b.current.tags["universe.stun_category"] = "humanoid"
        rng = RNGCursor(__import__("random").Random(6).getstate())
        fixture.enc.enable_transactional_progression(quiescent=True, rng_owner=rng)
        from activities import declare_stun
        stun = declare_stun(fixture.world, fixture.enc, fixture.a.id,
                            fixture.b.id, region="Arm", motion="thrust")
        later = MeleeStrike(fixture.enc, fixture.b.id, fixture.a.id, fixture.w3,
                            motion="swing", reach=2)
        self.assertGreater(later.end_time, stun.end_time)
        fixture.enc.schedule_action(stun)
        fixture.enc.schedule_action(later)
        fixture.enc.step(stun.end_time)
        self.assertEqual(fixture.enc.inspect_committed().action(stun.id).facts.outcome,
                         "stunned")
        self.assertEqual(fixture.b.current.states.states["stunned_until"], 10)
        self.assertIn(later.id, fixture.enc.cancelled_action_list)
        save = export_save(fixture.enc)
        fixture.enc.step(8)
        expected = {
            "time": fixture.enc.time,
            "rng": json.loads(json.dumps(rng.state)),
            "hp": [fixture.a.get_hit_points(), fixture.b.get_hit_points()],
            "stunned_until": fixture.b.current.states.states["stunned_until"],
            "cancelled": list(fixture.enc.cancelled_action_list),
            "history": hashlib.sha256(native_history.encode(
                native_history.capture(fixture.enc))).hexdigest(),
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "native-stun-save.json"
            path.write_bytes(save)
            child = r'''import hashlib,json,sys
import native_history
from native_persistence import load_path
world,encounter,rng=load_path(sys.argv[1])
encounter.step(8)
print(json.dumps({'time':encounter.time,'rng':rng.state,
 'hp':[encounter.get_being(i).get_hit_points() for i in encounter.being_list],
 'stunned_until':encounter.get_being(encounter.being_list[1]).current.states.states['stunned_until'],
 'cancelled':list(encounter.cancelled_action_list),
 'history':hashlib.sha256(native_history.encode(native_history.capture(encounter))).hexdigest()},sort_keys=True))'''
            result = subprocess.run(
                [sys.executable, "-B", "-c", child, str(path)], cwd=ROOT,
                env={**__import__("os").environ,
                     "PYTHONPATH": f"{ROOT / 'src'}:{ROOT / 'examples'}"},
                text=True, capture_output=True, check=False, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), expected)

    def test_statistical_group_facts_and_keyed_realization_resume_in_fresh_process(self):
        fixture = inspection_fixtures.InspectionFixture()
        fixture.setUp()
        group_config = json.loads((ROOT / "examples/nomadic_group.json").read_text())
        group_config["formation_traits"] = {
            "adults": {"trained_spotter": {"count": 0, "initial_skills": {}}}}
        group_config["formation_attributes"] = {
            "adults": {"voice": {"given": "trained_spotter", "conditional_cdfs": {
                "true": [["formal", 1]], "false": [["casual", 1]]}}}}
        group = StatisticalGroup("Native group", "group-one", group_config,
                                 group_config["seed"])
        fixture.world.add_object(group)
        fixture.enc.add_object(group.id)
        expected_count = group.household_count
        expected_household = group.household(0)
        group.counts()
        first_adult = next((household, index)
            for household in range(group.household_count)
            for index in range(group.household(household)["adults"]))
        expected_voice = group.formation_attribute(first_adult[0], "adults",
            first_adult[1], "voice")
        fixture.enable()
        first = DelayAction(fixture.enc, fixture.a.id, defense=0,
                            start_time=0, id="native-group-delay")
        fixture.enc.schedule_action(first)
        fixture.enc.step(1)
        wire = export_save(fixture.enc)

        continuation_id = "native-group-continuation-delay"
        next_action = DelayAction(fixture.enc, fixture.a.id, defense=0,
                                  start_time=1, id=continuation_id)
        fixture.enc.schedule_action(next_action)
        fixture.enc.step(1)
        expected = {
            "world": fixture.world.id, "encounter": fixture.enc.id,
            "time": fixture.enc.time, "rng": fixture.rng.state,
            "group_id": group.id, "count": group.household_count,
            "household": group.household(0),
            "formation_attribute": expected_voice,
            "history": hashlib.sha256(native_history.encode(
                native_history.capture(fixture.enc))).hexdigest(),
            "actions": list(fixture.enc._atomic_interval_history[-1].action_ids),
        }
        self.assertEqual(expected["count"], expected_count)
        self.assertEqual(expected["household"], expected_household)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "native-group-save.json"
            path.write_bytes(wire)
            child = r'''import hashlib,json,sys
import native_history
from activities import DelayAction
from native_persistence import load_path
world,enc,rng=load_path(sys.argv[1])
group=world.object_registry.object_instances['group-one']
assert group.household_count == int(sys.argv[2])
assert group.household(0) == json.loads(sys.argv[3])
household,index=int(sys.argv[4]),int(sys.argv[5])
assert group.committed_formation_attributes(household,'adults',index)['voice']==sys.argv[6]
action=DelayAction(enc,enc.being_list[0],defense=0,start_time=enc.time,
 id='native-group-continuation-delay')
enc.schedule_action(action)
enc.step(1)
print(json.dumps({'world':world.id,'encounter':enc.id,'time':enc.time,
 'rng':rng.state,'group_id':group.id,'count':group.household_count,
 'household':group.household(0),
 'formation_attribute':group.committed_formation_attributes(household,'adults',index)['voice'],
 'history':hashlib.sha256(native_history.encode(native_history.capture(enc))).hexdigest(),
 'actions':list(enc._atomic_interval_history[-1].action_ids),
 'arena_imports':sorted(set(sys.modules)&{'arena_browser_session','arena_native_snapshot',
  'arena_persistence','arena_server','npcgen'})},sort_keys=True))'''
            import os
            result = subprocess.run(
                [sys.executable, "-B", "-c", child, str(path),
                 str(expected_count), json.dumps(expected_household),
                 str(first_adult[0]), str(first_adult[1]), expected_voice],
                cwd=ROOT, env={**os.environ,
                    "PYTHONPATH": f"{ROOT / 'src'}:{ROOT / 'examples'}"},
                text=True, capture_output=True, check=False, timeout=45)
        self.assertEqual(result.returncode, 0, result.stderr)
        actual = json.loads(result.stdout)
        self.assertEqual(actual.pop("arena_imports"), [])
        self.assertEqual(actual, json.loads(json.dumps(expected)))

    def test_observer_owned_group_evidence_round_trips_without_identity_leakage(self):
        fixture = inspection_fixtures.InspectionFixture()
        fixture.setUp()
        group = fixture.f.f.f.group()
        fixture.enable()
        from field_observation import BeliefLedger
        first_ledger = BeliefLedger(fixture.a.id)
        second_ledger = BeliefLedger(fixture.b.id)
        first = fixture.f.f.observe(fixture.a, group, ledger=first_ledger)
        second = fixture.f.f.observe(fixture.b, group, ledger=second_ledger)
        fixture.enc.schedule_choice((first, second))
        fixture.enc.step(1)
        bindings = (
            RecipientBinding(fixture.world, "native", "belief-a",
                "in_world_belief_ledger", (fixture.a.id,), first_ledger),
            RecipientBinding(fixture.world, "native", "belief-b",
                "in_world_belief_ledger", (fixture.b.id,), second_ledger),
        )
        wire = export_save(fixture.enc, recipient_bindings=bindings)

        continuation = DelayAction(fixture.enc, fixture.a.id, defense=0,
                                   start_time=1, id="native-observer-continuation")
        fixture.enc.schedule_action(continuation)
        fixture.enc.step(1)
        expected = {
            "time": fixture.enc.time,
            "rng": fixture.rng.state,
            "history": hashlib.sha256(native_history.encode(
                native_history.capture(fixture.enc))).hexdigest(),
            "actions": list(fixture.enc._atomic_interval_history[-1].action_ids),
            "saved_actions": sorted((first.id, second.id)),
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "native-observer-save.json"
            path.write_bytes(wire)
            child = r'''import hashlib,json,sys
import native_history
from activities import DelayAction
from native_persistence import load_path
world,enc,rng=load_path(sys.argv[1])
actions=[event for event in world.event_history.values()
 if type(event).__name__=='ObserveGroupAction']
ledgers={event.actor_id:event.ledger for event in actions}
assert set(ledgers)==set(enc.being_list[:2])
assert all(ledger.observer_id==owner and ledger.evidence for owner,ledger in ledgers.items())
action=DelayAction(enc,enc.being_list[0],defense=0,start_time=enc.time,
 id='native-observer-continuation')
enc.schedule_action(action)
enc.step(1)
print(json.dumps({'time':enc.time,'rng':rng.state,
 'history':hashlib.sha256(native_history.encode(native_history.capture(enc))).hexdigest(),
 'actions':list(enc._atomic_interval_history[-1].action_ids),
 'saved_actions':sorted(event.id for event in actions)},sort_keys=True))'''
            import os
            result = subprocess.run(
                [sys.executable, "-B", "-c", child, str(path)],
                cwd=ROOT, env={**os.environ,
                    "PYTHONPATH": f"{ROOT / 'src'}:{ROOT / 'examples'}"},
                text=True, capture_output=True, check=False, timeout=45)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), json.loads(json.dumps(expected)))


    def test_personal_history_facts_and_validator_resume_in_fresh_process(self):
        fixture = inspection_fixtures.InspectionFixture()
        fixture.setUp()
        from personal_history import PersonalHistory
        from realization import Fact
        history = PersonalHistory(fixture.a, earliest=-10, known_through=0,
                                  nondeclining_skills=())
        fixture.a.personal_history = history
        key = history.episode_key(-1, "earlier-training")
        history.realize_episode(-1, "earlier-training", lambda _view: (
            Fact(key, {"description": "practiced earlier"}),))
        fixture.enable()
        first = DelayAction(fixture.enc, fixture.a.id, defense=0,
                            start_time=0, id="native-personal-history-delay")
        fixture.enc.schedule_action(first)
        fixture.enc.step(1)
        wire = export_save(fixture.enc)
        self.assertEqual(history.inspect_episode(-1, "earlier-training").value,
                         {"description": "practiced earlier"})
        self.assertEqual(len(history.facts_at(-1)), 1)

        continuation = DelayAction(fixture.enc, fixture.a.id, defense=0,
                                   start_time=1, id="native-history-continuation")
        fixture.enc.schedule_action(continuation)
        fixture.enc.step(1)
        live_history = fixture.a.personal_history
        history_digest = hashlib.sha256(json.dumps(
            live_history.to_jsonable(), sort_keys=True, separators=(",", ":"),
            allow_nan=False).encode()).hexdigest()
        expected = {
            "time": fixture.enc.time,
            "rng": json.loads(json.dumps(fixture.rng.state)),
            "history_digest": history_digest,
            "native_history": hashlib.sha256(native_history.encode(
                native_history.capture(fixture.enc))).hexdigest(),
            "actions": list(fixture.enc._atomic_interval_history[-1].action_ids),
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "native-personal-history-save.json"
            path.write_bytes(wire)
            child = r'''import hashlib,json,sys
import native_history
from activities import DelayAction
from native_persistence import load_path
world,enc,rng=load_path(sys.argv[1])
being=world.get_object_by_id(enc.being_list[0])
history=being.personal_history
history._validate(history.reality.view())
assert history.inspect_episode(-1,'earlier-training').value=={'description':'practiced earlier'}
assert len(history.facts_at(-1))==1
action=DelayAction(enc,being.id,defense=0,start_time=enc.time,
 id='native-history-continuation')
enc.schedule_action(action)
enc.step(1)
print(json.dumps({'time':enc.time,'rng':rng.state,
 'history_digest':hashlib.sha256(json.dumps(history.to_jsonable(),sort_keys=True,
  separators=(',',':'),allow_nan=False).encode()).hexdigest(),
 'native_history':hashlib.sha256(native_history.encode(native_history.capture(enc))).hexdigest(),
 'actions':list(enc._atomic_interval_history[-1].action_ids)},sort_keys=True))'''
            import os
            result = subprocess.run(
                [sys.executable, "-B", "-c", child, str(path)], cwd=ROOT,
                env={**os.environ,
                     "PYTHONPATH": f"{ROOT / 'src'}:{ROOT / 'examples'}"},
                text=True, capture_output=True, check=False, timeout=45)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), expected)

    def test_logical_reproduction_registry_resumes_with_native_encounter(self):
        world = Universe('native-reproduction', library=Library(
            config_dir=str(ROOT / 'src/config')))
        world.publish_reproduction_group(prepare_reproduction_group(
            ReproductionGroupProposal('RG-NATIVE', ('P1', 'P2'), ('C1',),
                                      'native-save:test')),
            request_key='native-create', expected_revision=0)
        snapshot = world.reproduction_group_snapshot()
        self.assertEqual(snapshot.revision, 1)
        self.assertEqual(world.get_reproduction_group('RG-NATIVE').offspring_ids, ('C1',))
        from encounter import Encounter
        ids = [world.make_being('Human', name) for name in ('Native A', 'Native B')]
        encounter = Encounter(world, 10, 0, initiated=True, id='native-reproduction-encounter')
        for identity in ids:
            encounter.add_being(identity)
        world.add_event(encounter)
        rng = RNGCursor(__import__('random').Random(91).getstate())
        encounter.enable_transactional_progression(quiescent=True, rng_owner=rng)
        initial = DelayAction(encounter, ids[0], defense=0, start_time=0,
                              id='native-reproduction-initial')
        encounter.schedule_action(initial)
        encounter.step(1)
        wire = export_save(encounter)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'native-reproduction-save.json'
            path.write_bytes(wire)
            child = r'''import hashlib,json,sys
from activities import DelayAction
from native_persistence import load_path
world,enc,rng=load_path(sys.argv[1])
snapshot=world.reproduction_group_snapshot()
group=world.get_reproduction_group('RG-NATIVE')
assert group.parent_ids == ('P1','P2') and group.offspring_ids == ('C1',)
action=DelayAction(enc,enc.being_list[0],defense=0,start_time=enc.time,
 id='native-reproduction-continuation')
enc.schedule_action(action)
enc.step(1)
print(json.dumps({'revision':world.reproduction_group_snapshot().revision,
 'group_id':group.group_id,'parents':group.parent_ids,'offspring':group.offspring_ids,
 'time':enc.time,'rng':rng.state},sort_keys=True))'''
            import os
            result = subprocess.run(
                [sys.executable, '-B', '-c', child, str(path)], cwd=ROOT,
                env={**os.environ,
                     'PYTHONPATH': f'{ROOT / "src"}:{ROOT / "examples"}'},
                text=True, capture_output=True, check=False, timeout=45)
        self.assertEqual(result.returncode, 0, result.stderr)
        restored = json.loads(result.stdout)
        self.assertEqual(restored['revision'], snapshot.revision)
        self.assertEqual(restored['group_id'], 'RG-NATIVE')
        self.assertEqual(restored['parents'], ['P1', 'P2'])
        self.assertEqual(restored['offspring'], ['C1'])
        self.assertEqual(restored['time'], 2)

    def test_native_save_restores_and_continues_multiple_encounters(self):
        import os
        import random

        world = Universe('native-multiple-encounters', library=Library(
            config_dir=str(ROOT / 'src/config')))
        identities = [world.make_being('Human', f'Native Encounter {index}')
                      for index in range(2)]
        companion = Encounter(world, 10, 0, initiated=True,
                              id='native-multi-pristine-companion')
        companion.add_being(identities[1])
        world.add_event(companion)
        companion_rng = RNGCursor(random.Random(701).getstate())
        companion.enable_transactional_progression(
            quiescent=True, rng_owner=companion_rng)
        # The selected Encounter is deliberately not the first Encounter in
        # event-history order; the portable root role must remain unambiguous.
        selected = Encounter(world, 10, 0, initiated=True,
                             id='native-multi-selected')
        selected.add_being(identities[0])
        world.add_event(selected)
        selected_rng = RNGCursor(random.Random(700).getstate())
        selected.enable_transactional_progression(
            quiescent=True, rng_owner=selected_rng)
        initial = DelayAction(selected, identities[0], defense=0, start_time=0,
                              id='native-multi-selected-initial')
        selected.schedule_action(initial)
        selected.step(1)
        wire = export_save(selected)

        companion_rng_state = companion_rng.state

        def continue_both(native_world, first, second, first_rng,
                          second_rng_state):
            selected_next = DelayAction(
                first, identities[0], defense=0, start_time=first.time,
                id='native-multi-selected-next')
            first.schedule_action(selected_next)
            first.step(1)
            second_rng = native_persistence.rng_owner_for(second)
            if second_rng.state != second_rng_state:
                raise AssertionError('restored companion RNG cursor differs')
            companion_next = DelayAction(
                second, identities[1], defense=0, start_time=second.time,
                id='native-multi-companion-next')
            second.schedule_action(companion_next)
            second.step(1)
            return {
                'encounters': sorted(
                    event.id for event in native_world.event_history.values()
                    if type(event) is Encounter),
                'books': len(native_world._choice_books),
                'times': [first.time, second.time],
                'results': [selected_next.resolution.outcome,
                            companion_next.resolution.outcome],
                'rng': [first_rng.state, second_rng.state],
                'histories': [
                    hashlib.sha256(native_history.encode(
                        native_history.capture(first))).hexdigest(),
                    hashlib.sha256(native_history.encode(
                        native_history.capture(second))).hexdigest(),
                ],
            }

        expected = continue_both(world, selected, companion, selected_rng,
                                 companion_rng_state)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'native-multiple-encounters.json'
            path.write_bytes(wire)
            child = r'''import hashlib,json,sys
from activities import DelayAction
from encounter import Encounter
from native_persistence import load_path,rng_owner_for
import native_history
world,selected,selected_rng=load_path(sys.argv[1])
encounters={event.id:event for event in world.event_history.values()
 if type(event) is Encounter}
assert set(encounters)=={'native-multi-selected','native-multi-pristine-companion'}
companion=encounters['native-multi-pristine-companion']
assert len(world._choice_books)==2
assert all(book.lock is world._schedule_lock for book in world._choice_books)
first=DelayAction(selected,sys.argv[2],defense=0,start_time=selected.time,
 id='native-multi-selected-next')
selected.schedule_action(first);selected.step(1)
second_rng=rng_owner_for(companion)
second=DelayAction(companion,sys.argv[3],defense=0,start_time=companion.time,
 id='native-multi-companion-next')
companion.schedule_action(second);companion.step(1)
print(json.dumps({'encounters':sorted(encounters),'books':len(world._choice_books),
 'times':[selected.time,companion.time],
 'results':[first.resolution.outcome,second.resolution.outcome],
 'rng':[selected_rng.state,second_rng.state],
 'histories':[hashlib.sha256(native_history.encode(native_history.capture(enc))).hexdigest()
  for enc in (selected,companion)]},sort_keys=True))'''
            result = subprocess.run(
                [sys.executable, '-B', '-c', child, str(path),
                 identities[0], identities[1]], cwd=ROOT,
                env={**os.environ,
                     'PYTHONPATH': f'{ROOT / "src"}:{ROOT / "examples"}'},
                text=True, capture_output=True, check=False, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout),
                         json.loads(json.dumps(expected)))

        # Save again after both Encounter streams have progressed. A new OS
        # process must resume each independent cursor/history, not just the
        # selected root.
        continued_save = export_save(selected)
        tampered = json.loads(continued_save)
        tampered['encounters'].append(dict(tampered['encounters'][0]))
        tampered.pop('sha256')
        tampered['sha256'] = hashlib.sha256(
            native_persistence._canonical(tampered)).hexdigest()
        with self.assertRaisesRegex(NativeSaveRejected, 'identities are duplicated'):
            load_save(native_persistence._canonical(tampered))
        tampered = json.loads(continued_save)
        companion_row = next(row for row in tampered['encounters']
                             if row['encounter_id'] == companion.id)
        companion_row['rng_state'] = native_persistence._rng_json(
            random.Random(702).getstate())
        tampered.pop('sha256')
        tampered['sha256'] = hashlib.sha256(
            native_persistence._canonical(tampered)).hexdigest()
        with self.assertRaises(NativeSaveRejected):
            load_save(native_persistence._canonical(tampered))
        selected_second = DelayAction(
            selected, identities[0], defense=0, start_time=selected.time,
            id='native-multi-selected-second')
        companion_second = DelayAction(
            companion, identities[1], defense=0, start_time=companion.time,
            id='native-multi-companion-second')
        selected.schedule_action(selected_second)
        companion.schedule_action(companion_second)
        selected.step(1)
        companion.step(1)
        expected_second = {
            'times': [selected.time, companion.time],
            'results': [selected_second.resolution.outcome,
                        companion_second.resolution.outcome],
            'rng': [selected_rng.state, companion_rng.state],
            'histories': [hashlib.sha256(native_history.encode(
                native_history.capture(saved))).hexdigest()
                for saved in (selected, companion)],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'native-multiple-progressed.json'
            path.write_bytes(continued_save)
            child = r'''import hashlib,json,sys
from activities import DelayAction
from encounter import Encounter
from native_persistence import load_path,rng_owner_for,export_save
import native_history
world,selected,selected_rng=load_path(sys.argv[1])
assert export_save(selected)==open(sys.argv[1],'rb').read()
by_id={event.id:event for event in world.event_history.values()
 if type(event) is Encounter}
companion=by_id['native-multi-pristine-companion']
first=DelayAction(selected,selected.being_list[0],defense=0,
 start_time=selected.time,id='native-multi-selected-second')
second=DelayAction(companion,companion.being_list[0],defense=0,
 start_time=companion.time,id='native-multi-companion-second')
selected.schedule_action(first);companion.schedule_action(second)
selected.step(1);companion.step(1)
print(json.dumps({'times':[selected.time,companion.time],
 'results':[first.resolution.outcome,second.resolution.outcome],
 'rng':[selected_rng.state,rng_owner_for(companion).state],
 'histories':[hashlib.sha256(native_history.encode(native_history.capture(enc))).hexdigest()
  for enc in (selected,companion)]},sort_keys=True))'''
            result = subprocess.run(
                [sys.executable, '-B', '-c', child, str(path)], cwd=ROOT,
                env={**os.environ,
                     'PYTHONPATH': f'{ROOT / "src"}:{ROOT / "examples"}'},
                text=True, capture_output=True, check=False, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout),
                         json.loads(json.dumps(expected_second)))

    def test_native_save_restores_recipient_bindings_for_multiple_encounters(self):
        import os
        import random
        from object import ObjectDefinition, ObjectInstance
        from object_observation import ObjectObservationLedger
        from spatial.geometry import Sphere
        from spatial.occlusion import VisualOcclusion

        world = Universe('native-multi-recipients', library=Library(
            config_dir=str(ROOT / 'src/config')))
        encounters = []
        bindings = []
        for index, seed in ((0, 11), (1, 12)):
            actor_id = world.make_being('Human', f'Multi observer {index}')
            actor = world.get_object_by_id(actor_id)
            actor.set_position(CartesianPosition(0, index * 5, 0))
            actor.set_geometry(Sphere(.25))
            object_id = f'native-multi-observer-object-{index}'
            target = ObjectInstance(
                ObjectDefinition(f'Multi target {index}', 1, 1, .2, .2,
                                 1, 0, 0),
                f'Multi target {index}', id=object_id)
            world.add_object(target)
            target.set_position(CartesianPosition(1.5, index * 5, 0))
            target.set_geometry(Sphere(.1))
            target.set_visual_occlusion(VisualOcclusion(0))
            target.current.discovery_dc = 15
            encounter = Encounter(world, 10, 0, initiated=True,
                                  id=f'native-multi-observer-encounter-{index}')
            encounter.add_being(actor_id)
            encounter.add_object(object_id)
            world.add_event(encounter)
            rng = RNGCursor(random.Random(seed).getstate())
            encounter.enable_transactional_progression(
                quiescent=True, rng_owner=rng)
            ledger = ObjectObservationLedger(actor_id)
            action = SpotAction(world, actor_id, object_id, 0,
                                object_ledger=ledger,
                                id=f'native-multi-observer-spot-{index}')
            encounter.schedule_action(action)
            encounters.append((encounter, actor, target, rng, action, ledger))
            bindings.append(RecipientBinding(
                world, 'native-multi-observer', f'ledger-{index}',
                'observer_object_evidence', (actor_id,), ledger))

        # The selected Encounter is deliberately second in registry order.
        companion, selected = encounters
        selected[0].step(1)
        wire = export_save(selected[0], recipient_bindings=tuple(bindings))

        def finish(encounter):
            while encounter.time < 6:
                encounter.step(1)

        for encounter, *_ in encounters:
            finish(encounter)

        def projection():
            return {
                'times': [row[0].time for row in encounters],
                'outcomes': [row[4].resolution.outcome for row in encounters],
                'rng': [row[3].state for row in encounters],
                'evidence': [[ob.id, ob.observer_id, ob.object_id,
                              ob.source_action_id, ob.encounter_id, ob.boundary,
                              ob.time, list(ob.position.as_tuple()), ob.basis]
                             for row in encounters for ob in row[5].observations],
                'histories': [hashlib.sha256(native_history.encode(
                    native_history.capture(row[0]))).hexdigest()
                    for row in encounters],
            }

        expected = projection()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'native-multi-observers.json'
            path.write_bytes(wire)
            child = r'''import hashlib,json,sys
import native_history
from encounter import Encounter
from native_persistence import load_path,rng_owner_for
world,selected,selected_rng=load_path(sys.argv[1])
encounters={event.id:event for event in world.event_history.values()
 if type(event) is Encounter}
assert len(encounters)==2
actions=[next(member.action for choice in enc._choice_book._choices.values()
 for member in choice.members) for enc in encounters.values()]
rows=[]
for enc,action in zip(encounters.values(),actions):
 while enc.time < 6:
  enc.step(1)
 rows.append((enc,action,rng_owner_for(enc)))
evidence=[[ob.id,ob.observer_id,ob.object_id,ob.source_action_id,
 ob.encounter_id,ob.boundary,ob.time,list(ob.position.as_tuple()),ob.basis]
 for _enc,action,_rng in rows for ob in action.object_ledger.observations]
assert all(all(ob.observer_id==action.actor_id
 for ob in action.object_ledger.observations) for _enc,action,_rng in rows)
print(json.dumps({'times':[row[0].time for row in rows],
 'outcomes':[row[1].resolution.outcome for row in rows],
 'rng':[row[2].state for row in rows],'evidence':evidence,
 'histories':[hashlib.sha256(native_history.encode(
  native_history.capture(row[0]))).hexdigest() for row in rows]},sort_keys=True))'''
            result = subprocess.run(
                [sys.executable, '-B', '-c', child, str(path)], cwd=ROOT,
                env={**os.environ,
                     'PYTHONPATH': f'{ROOT / "src"}:{ROOT / "examples"}'},
                text=True, capture_output=True, check=False, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout),
                         json.loads(json.dumps(expected)))

    def test_logical_reproduction_native_being_binding_restores_by_object_identity(self):
        world = Universe('native-reproduction-binding', library=Library(
            config_dir=str(ROOT / 'src/config')))
        world.publish_reproduction_group(prepare_reproduction_group(
            ReproductionGroupProposal('RG-BINDING', ('P1', 'P2'), ('C1',),
                                      'native-save:binding')),
            request_key='native-binding-create', expected_revision=0)
        definition = BeingDefinition(
            obj_type='Native reproduction fixture', length=1.8, weight=70,
            hit_points=12, hit_dice='1d8', alignment='Neutral',
            armor_class=10, challenge_rating=0)
        being = materialize_reproductive_offspring(
            world, 'C1', being_definition=definition, name='Child',
            request_key='native-binding-materialize', expected_revision=1)
        from encounter import Encounter
        encounter = Encounter(world, 10, 0, initiated=True,
                              id='native-reproduction-binding-encounter')
        encounter.add_being(being.id)
        world.add_event(encounter)
        rng = RNGCursor(__import__('random').Random(92).getstate())
        encounter.enable_transactional_progression(quiescent=True, rng_owner=rng)
        initial = DelayAction(encounter, being.id, defense=0, start_time=0,
                              id='native-reproduction-binding-initial')
        encounter.schedule_action(initial)
        encounter.step(1)
        wire = export_save(encounter)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'native-reproduction-binding-save.json'
            path.write_bytes(wire)
            child = r'''import json,sys
from native_persistence import load_path
world,enc,rng=load_path(sys.argv[1])
registry=world._reproduction_group_registry
being=world.get_object_by_id('C1')
record=registry._native_being_requests['native-binding-materialize']
assert registry._native_beings_by_person_id['C1'] is being
assert record.being is being and record.person_id == 'C1'
assert world.get_reproduction_group('RG-BINDING').offspring_ids == ('C1',)
print(json.dumps({'being_id':being.id,'name':being.name,'request':record.request_key,
 'time':enc.time,'rng':rng.state},sort_keys=True))'''
            import os
            result = subprocess.run(
                [sys.executable, '-B', '-c', child, str(path)], cwd=ROOT,
                env={**os.environ,
                     'PYTHONPATH': f'{ROOT / "src"}:{ROOT / "examples"}'},
                text=True, capture_output=True, check=False, timeout=45)
        self.assertEqual(result.returncode, 0, result.stderr)
        restored = json.loads(result.stdout)
        self.assertEqual(restored['being_id'], 'C1')
        self.assertEqual(restored['name'], 'Child')
        self.assertEqual(restored['request'], 'native-binding-materialize')

    def test_completed_ask_about_past_and_listener_accounts_resume_with_binding(self):
        world, encounter, rng, listener, speaker, _weapon_id = self._combat_encounter()
        from personal_history import PersonalHistory
        from realization import Fact
        from objective_reality import EpisodeFacts
        speaker.personal_history = PersonalHistory(
            speaker, earliest=-10, known_through=0, nondeclining_skills=())
        accounts = []
        key = speaker.personal_history.episode_key(-1, 'native-test')
        inquiry = AskAboutPastAction(
            world, listener.id, speaker.id, 0, episode_time=-1,
            topic='native-test', duration=1,
            generate=EpisodeFacts((Fact(
                key, {'description': 'practiced a native test'},
                origin='native-test'),)),
            received_accounts=accounts)
        encounter.schedule_action(inquiry)
        encounter.step(1)
        self.assertEqual(len(accounts), 1)
        self.assertEqual(accounts[0].words, 'practiced a native test')
        binding = RecipientBinding(
            world, 'history', 'listener-accounts', 'in_world_received_accounts',
            (listener.id,), accounts)
        wire = export_save(encounter, recipient_bindings=(binding,))
        next_action = DelayAction(encounter, listener.id, defense=0,
                                  start_time=1, id='native-inquiry-continuation')
        encounter.schedule_action(next_action)
        encounter.step(1)
        history_digest = hashlib.sha256(native_history.encode(
            native_history.capture(encounter))).hexdigest()
        expected = {'time': encounter.time, 'rng': rng.state,
                    'history': history_digest,
                    'account': accounts[0].to_dict()}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'native-ask-about-past-save.json'
            path.write_bytes(wire)
            child = r'''import hashlib,json,sys
import native_history
from activities import DelayAction
from native_persistence import load_path
world,enc,rng=load_path(sys.argv[1])
inquiry=next(a for a in world.event_history.values()
 if type(a).__name__=='AskAboutPastAction')
assert inquiry.generate is not None and len(inquiry.received_accounts)==1
account=inquiry.received_accounts[0].to_dict()
action=DelayAction(enc,enc.being_list[0],defense=0,start_time=enc.time,
 id='native-inquiry-continuation')
enc.schedule_action(action)
enc.step(1)
print(json.dumps({'time':enc.time,'rng':rng.state,
 'history':hashlib.sha256(native_history.encode(native_history.capture(enc))).hexdigest(),
 'account':account},sort_keys=True))'''
            import os
            result = subprocess.run(
                [sys.executable, '-B', '-c', child, str(path)], cwd=ROOT,
                env={**os.environ,
                     'PYTHONPATH': f'{ROOT / "src"}:{ROOT / "examples"}'},
                text=True, capture_output=True, check=False, timeout=45)
        self.assertEqual(result.returncode, 0, result.stderr)
        actual = json.loads(result.stdout)
        self.assertEqual(actual['time'], expected['time'])
        self.assertEqual(actual['rng'], json.loads(json.dumps(expected['rng'])))
        self.assertEqual(actual['history'], expected['history'])
        self.assertEqual(actual['account'], expected['account'])

    def test_spot_location_evidence_restores_with_owner_and_provenance(self):
        world, encounter, rng, observer, target, _weapon_id = self._combat_encounter()
        ledger = LocationEvidenceLedger(observer.id)
        spot = SpotAction(world, observer.id, target.id, 0, die_roll=20,
                          location_ledger=ledger, id='native-location-spot')
        encounter.schedule_action(spot)
        encounter.step(6)
        self.assertEqual(len(ledger.observations), 1)
        binding = RecipientBinding(
            world, 'perception', 'observer-location', 'observer_location_evidence',
            (observer.id,), ledger)
        wire = export_save(encounter, recipient_bindings=(binding,))
        continuation = DelayAction(encounter, observer.id, defense=0,
                                   start_time=6, id='native-location-continuation')
        encounter.schedule_action(continuation)
        encounter.step(1)
        row = ledger.observations[0]
        expected = {
            'time': encounter.time, 'rng': rng.state,
            'history': hashlib.sha256(native_history.encode(
                native_history.capture(encounter))).hexdigest(),
            'observation': [row.id, row.observer_id, row.being_id,
                            row.source_action_id, row.encounter_id, row.boundary,
                            row.time, list(row.position.as_tuple()), row.basis],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'native-location-evidence-save.json'
            path.write_bytes(wire)
            child = r'''import hashlib,json,sys
import native_history
from activities import DelayAction
from native_persistence import load_path
world,enc,rng=load_path(sys.argv[1])
spot=world.get_event_by_id('native-location-spot')
ledger=spot.location_ledger
row=ledger.observations[0]
assert ledger.observer_id == spot.actor_id
assert row.source_action_id == spot.id and row.being_id == spot.target_id
action=DelayAction(enc,spot.actor_id,defense=0,start_time=enc.time,
 id='native-location-continuation')
enc.schedule_action(action)
enc.step(1)
print(json.dumps({'time':enc.time,'rng':rng.state,
 'history':hashlib.sha256(native_history.encode(native_history.capture(enc))).hexdigest(),
 'observation':[row.id,row.observer_id,row.being_id,row.source_action_id,
 row.encounter_id,row.boundary,row.time,list(row.position.as_tuple()),row.basis]},sort_keys=True))'''
            import os
            result = subprocess.run(
                [sys.executable, '-B', '-c', child, str(path)], cwd=ROOT,
                env={**os.environ,
                     'PYTHONPATH': f'{ROOT / "src"}:{ROOT / "examples"}'},
                text=True, capture_output=True, check=False, timeout=45)
        self.assertEqual(result.returncode, 0, result.stderr)
        actual = json.loads(result.stdout)
        self.assertEqual(actual['time'], expected['time'])
        self.assertEqual(actual['rng'], json.loads(json.dumps(expected['rng'])))
        self.assertEqual(actual['history'], expected['history'])
        self.assertEqual(actual['observation'], expected['observation'])

    def test_object_spot_ledgers_restore_distinct_evidence_and_projectile_continuation(self):
        from native_throw_spot import build_spot_scene
        scene = build_spot_scene(seed=5)
        world, encounter, rng = scene['world'], scene['encounter'], scene['rng']
        encounter.step(6)
        self.assertEqual(len(scene['spotter_evidence'].observations), 1)
        self.assertEqual(scene['second_evidence'].observations, ())
        bindings = tuple(RecipientBinding(
            world, 'object-evidence', name, 'observer_object_evidence',
            (ledger.observer_id,), ledger)
            for name, ledger in (('spotter', scene['spotter_evidence']),
                                 ('second', scene['second_evidence'])))
        wire = export_save(encounter, recipient_bindings=bindings)
        encounter.step(1)
        observation = scene['spotter_evidence'].observations[0]
        expected = {
            'time': encounter.time, 'rng': rng.state,
            'history': hashlib.sha256(native_history.encode(
                native_history.capture(encounter))).hexdigest(),
            'observation': [observation.id, observation.observer_id,
                            observation.object_id, observation.source_action_id,
                            observation.encounter_id, observation.boundary,
                            observation.time, list(observation.position.as_tuple()),
                            observation.projectile_status, observation.basis],
            'flight': scene['projectile'].__dict__['_projectile_flight'].status,
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'native-object-observation-save.json'
            path.write_bytes(wire)
            child = r'''import hashlib,json,sys
import native_history
from native_persistence import load_path
world,enc,rng=load_path(sys.argv[1])
spot=world.get_event_by_id('throw-demo/spotter-object-spot')
second=world.get_event_by_id('throw-demo/second-observer-object-spot')
assert len(spot.object_ledger.observations)==1
assert second.object_ledger.observations==()
observation=spot.object_ledger.observations[0]
enc.step(1)
projectile=world.get_object_by_id(observation.object_id)
flight=projectile.__dict__['_projectile_flight'].status
print(json.dumps({'time':enc.time,'rng':rng.state,
 'history':hashlib.sha256(native_history.encode(native_history.capture(enc))).hexdigest(),
 'observation':[observation.id,observation.observer_id,observation.object_id,
 observation.source_action_id,observation.encounter_id,observation.boundary,
 observation.time,list(observation.position.as_tuple()),
 observation.projectile_status,observation.basis], 'flight':flight},sort_keys=True))'''
            import os
            result = subprocess.run(
                [sys.executable, '-B', '-c', child, str(path)], cwd=ROOT,
                env={**os.environ,
                     'PYTHONPATH': f'{ROOT / "src"}:{ROOT / "examples"}'},
                text=True, capture_output=True, check=False, timeout=45)
        self.assertEqual(result.returncode, 0, result.stderr)
        actual = json.loads(result.stdout)
        self.assertEqual(actual['time'], expected['time'])
        self.assertEqual(actual['rng'], json.loads(json.dumps(expected['rng'])))
        self.assertEqual(actual['history'], expected['history'])
        self.assertEqual(actual['observation'], expected['observation'])
        self.assertEqual(actual['flight'], expected['flight'])

    def test_native_search_success_and_listen_failure_resume_with_exact_history(self):
        world, encounter, rng, observer, target, _weapon_id = self._combat_encounter()
        target.current.tags['arena_search_accessible'] = True
        target.current.tags['arena_audible'] = True
        search = SpotAction(world, observer.id, target.id, 0, die_roll=20,
                            sense='search', id='native-search-success')
        encounter.schedule_action(search)
        encounter.step(6)
        self.assertEqual(search.resolution.outcome, 'success')
        self.assertTrue(encounter.is_aware(observer.id, target.id))
        listen = SpotAction(world, observer.id, target.id, 6, die_roll=1,
                            sense='listen', id='native-listen-failure')
        encounter.schedule_action(listen)
        wire = export_save(encounter)
        self.assertEqual(native_history.current_recording(encounter)['latest_boundary'], 6)
        encounter.step(6)
        self.assertEqual(native_history.current_recording(encounter)['latest_boundary'], 12)
        expected = {
            'time': encounter.time, 'rng': rng.state,
            'history': hashlib.sha256(native_history.encode(
                native_history.capture(encounter))).hexdigest(),
            'outcomes': [search.resolution.outcome, listen.resolution.outcome],
            'awareness': encounter.is_aware(observer.id, target.id),
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'native-search-listen-save.json'
            path.write_bytes(wire)
            child = r'''import hashlib,json,sys
import native_history
from native_persistence import load_path,export_save
from native_history import current_recording
world,enc,rng=load_path(sys.argv[1])
assert export_save(enc)==open(sys.argv[1],'rb').read()
search=world.get_event_by_id('native-search-success')
choice=next(row for row in enc._choice_book._choices.values()
 if row.view.action_ids==('native-listen-failure',))
listen=choice.members[0].action
assert search.resolution.outcome=='success'
assert listen.resolution is None
enc.step(6)
recorded=current_recording(enc)
assert recorded['latest_boundary']==enc.last_processed_boundary
resaved=json.loads(export_save(enc))
assert resaved['history']==recorded
print(json.dumps({'time':enc.time,'rng':rng.state,
 'history':hashlib.sha256(native_history.encode(native_history.capture(enc))).hexdigest(),
 'outcomes':[search.resolution.outcome,listen.resolution.outcome],
 'awareness':enc.is_aware(search.actor_id,search.target_id)},sort_keys=True))'''
            import os
            result = subprocess.run(
                [sys.executable, '-B', '-c', child, str(path)], cwd=ROOT,
                env={**os.environ,
                     'PYTHONPATH': f'{ROOT / "src"}:{ROOT / "examples"}'},
                text=True, capture_output=True, check=False, timeout=45)
        self.assertEqual(result.returncode, 0, result.stderr)
        actual = json.loads(result.stdout)
        self.assertEqual(actual['time'], expected['time'])
        self.assertEqual(actual['rng'], json.loads(json.dumps(expected['rng'])))
        self.assertEqual(actual['history'], expected['history'])
        self.assertEqual(actual['outcomes'], expected['outcomes'])
        self.assertEqual(actual['awareness'], expected['awareness'])

    def test_simultaneous_native_melee_batch_restores_causal_effects_and_continues(self):
        from melee_combat import MeleeStrike, effective_melee_reach_meters
        world, encounter, rng, first, second, first_weapon_id = self._combat_encounter()
        victim_id = world.make_being('Human', 'Native Batch Victim')
        victim = world.get_object_by_id(victim_id)
        victim.set_position(CartesianPosition(.4, 0, 0))
        victim.set_geometry(Sphere(.25))
        victim.set_hit_points(100)
        encounter.add_being(victim_id)
        encounter.mark_aware(first.id, victim_id)
        encounter.mark_aware(second.id, victim_id)
        second_weapon_id = world.make_weapon_for_being(second.id, 'Dagger',
                                                       'Native Batch Dagger')
        world.arm_being(second.id, second_weapon_id, 'right hand')
        first.current.skills.weapon_skills['Dagger'] = 3
        second.current.skills.weapon_skills['Dagger'] = 3
        first_reach = effective_melee_reach_meters(
            first.current, world.get_object_by_id(first_weapon_id).current)
        second_reach = effective_melee_reach_meters(
            second.current, world.get_object_by_id(second_weapon_id).current)
        strikes = (
            MeleeStrike(encounter, first.id, victim_id, first_weapon_id,
                        motion='thrust', reach=max(2.0, first_reach)),
            MeleeStrike(encounter, second.id, victim_id, second_weapon_id,
                        motion='thrust', reach=max(2.0, second_reach)),
        )
        encounter.schedule_choice(strikes)
        encounter.step(max(action.end_time for action in strikes))
        receipt = next(row for row in reversed(encounter._atomic_interval_history)
                       if len(row.action_ids) == 2)
        self.assertEqual(len(receipt.action_ids), 2)
        self.assertTrue(receipt.effect_ids)
        self.assertLess(victim.get_hit_points(), 100)
        wire = export_save(encounter)
        encounter.schedule_action(DelayAction(
            encounter, first.id, defense=0, start_time=encounter.time,
            id='native-batch-continuation'))
        encounter.step(1)
        expected = {
            'time': encounter.time, 'rng': rng.state,
            'hp': victim.get_hit_points(),
            'history': hashlib.sha256(native_history.encode(
                native_history.capture(encounter))).hexdigest(),
            'actions': list(receipt.action_ids),
            'effects': [str(identity) for identity in receipt.effect_ids],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'native-simultaneous-melee-save.json'
            path.write_bytes(wire)
            child = r'''import hashlib,json,sys
import native_history
from activities import DelayAction
from native_persistence import load_path
world,enc,rng=load_path(sys.argv[1])
victim=world.get_object_by_id(sys.argv[2])
receipt=next(row for row in reversed(enc._atomic_interval_history)
 if len(row.action_ids)==2)
assert len(receipt.action_ids)==2
assert victim.get_hit_points()<100
actor=world.get_event_by_id(receipt.action_ids[0]).actor_id
enc.schedule_action(DelayAction(enc,actor,defense=0,
 start_time=enc.time,id='native-batch-continuation'))
enc.step(1)
print(json.dumps({'time':enc.time,'rng':rng.state,'hp':victim.get_hit_points(),
 'history':hashlib.sha256(native_history.encode(native_history.capture(enc))).hexdigest(),
 'actions':list(receipt.action_ids),
 'effects':[str(identity) for identity in receipt.effect_ids]},sort_keys=True))'''
            import os
            result = subprocess.run(
                [sys.executable, '-B', '-c', child, str(path), victim_id], cwd=ROOT,
                env={**os.environ,
                     'PYTHONPATH': f'{ROOT / "src"}:{ROOT / "examples"}'},
                text=True, capture_output=True, check=False, timeout=45)
        self.assertEqual(result.returncode, 0, result.stderr)
        actual = json.loads(result.stdout)
        self.assertEqual(actual['time'], expected['time'])
        self.assertEqual(actual['rng'], json.loads(json.dumps(expected['rng'])))
        self.assertEqual(actual['hp'], expected['hp'])
        self.assertEqual(actual['history'], expected['history'])
        self.assertEqual(actual['actions'], expected['actions'])
        self.assertEqual(actual['effects'], expected['effects'])

    def test_simultaneous_three_being_wrest_coholding_restores_and_continues(self):
        """Native Save retains one Object identity shared by concurrent holders."""
        from action import Action
        from physical_contact import shared_object_holders
        from native_scenario import NativeScenarioBuilder
        from action_evaluation import _ProvisionalRandom, RandomDraw
        from unittest.mock import patch
        builder = NativeScenarioBuilder(
            'Native simultaneous co-holding',
            Library(config_dir=str(ROOT / 'src/config')), seed=17)
        actor = builder.add_being('Human', 'First challenger',
            position=(0, 0, 0), radius=.1, hit_points=100)
        holder = builder.add_being('Human', 'Object holder',
            position=(.3, 0, 0), radius=.1, hit_points=100)
        third = builder.add_being('Human', 'Second challenger',
            position=(.3, .3, 0), radius=.1, hit_points=100)
        world, encounter = builder.world, builder.encounter
        for being in (actor, holder, third):
            being.size_category = 'medium'
            being.set_posture('standing')
            for other in (actor, holder, third):
                if other.id != being.id:
                    encounter.mark_aware(being.id, other.id)
        obj = builder.make_weapon(holder.id, 'Dagger', 'One shared Dagger')
        object_id = obj.id
        builder.arm(holder.id, object_id, 'right hand')
        obj.parent_container_id = holder.id
        builder.add_object(object_id)
        builder.mark_aware(actor.id, object_id)
        builder.mark_aware(holder.id, object_id)
        builder.mark_aware(third.id, object_id)
        builder.enable()

        def scripted_step(rolls):
            values = iter(rolls)
            def scripted(context, dice):
                value = next(values)
                context.trace.append(RandomDraw(
                    context.action_id, dice, int(dice[2:].split('+')[0]), value))
                return value
            with patch.object(_ProvisionalRandom, 'roll', scripted):
                encounter.step(1)

        actor.current.abilities.abilities['STR'] = 30
        third.current.abilities.abilities['STR'] = 30
        holder.current.abilities.abilities['STR'] = 3

        grabs = []
        for challenger in (actor, third):
            grab = Action(world, 0, 1, 'grab object', challenger.id,
                          object_id, None)
            grab.holder_id = holder.id
            grab.holder_hand = 'right hand'
            grab.grab_hand = 'left hand'
            grabs.append(grab)
        encounter.schedule_choice(tuple(grabs))
        scripted_step([20, 20])
        grips = __import__('physical_contact').active_object_grip_state(encounter)
        grip_by_actor = {row[2]: row for row in grips}
        wrests = []
        for challenger in (actor, third):
            wrest = Action(world, 2, 3, 'wrest', challenger.id,
                           object_id, None)
            wrest.holder_id = holder.id
            wrest.holder_hand = 'right hand'
            wrest.grab_hand = 'left hand'
            wrest.object_grip_id = grip_by_actor[challenger.id][1]
            wrests.append(wrest)
        encounter.schedule_choice(tuple(wrests))
        encounter.step(1)  # Activate the simultaneous contests at their common fence.
        scripted_step([6, 6, 6, 1, 1, 1, 6, 6, 6, 1, 1, 1])
        self.assertEqual([row.resolution.outcome for row in wrests],
                         ['success', 'success'])
        self.assertEqual(set(shared_object_holders(encounter, object_id)),
                         {(actor.id, 'left hand'), (third.id, 'left hand')})

        wire = export_save(encounter)
        actor_id, third_id = actor.id, third.id
        from transactional_progression import _BINDINGS
        rng_owner = _BINDINGS[id(encounter)].rng_owner
        def rng_digest(owner):
            return hashlib.sha256(json.dumps(owner.state).encode()).hexdigest()
        delay_id = 'native-coholding-continuation'
        encounter.schedule_action(DelayAction(
            encounter, actor_id, defense=0, start_time=encounter.time,
            id=delay_id))
        encounter.step(1)
        expected = {
            'time': encounter.time,
            'rng': rng_digest(rng_owner),
            'history': hashlib.sha256(native_history.encode(
                native_history.capture(encounter))).hexdigest(),
            'holders': [[identity, 'left hand']
                        for identity in sorted((actor_id, third_id))],
            'action_ids': sorted(row.id for row in wrests),
            'object_id': object_id,
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'native-coholding.json'
            path.write_bytes(wire)
            child = r'''import hashlib,json,sys
import native_history
from activities import DelayAction
from native_persistence import load_path
from physical_contact import shared_object_holders
def rng_digest(rng): return hashlib.sha256(json.dumps(rng.state).encode()).hexdigest()
world,enc,rng=load_path(sys.argv[1])
oid,actor,third,delay=sys.argv[2:]
holders=[list(row) for row in shared_object_holders(enc,oid)]
assert holders==[[identity,'left hand'] for identity in sorted((actor,third))]
obj=world.get_object_by_id(oid)
assert obj.id==oid and obj.parent_container_id==min(actor,third)
assert sum(world.get_object_by_id(x).current.body_parts.get('left hand')==oid
 for x in enc.being_list)==2
actions=[world.get_event_by_id(x) for x in enc.finished_action_list
 if getattr(world.get_event_by_id(x),'event_type',None)=='wrest']
assert len(actions)==2 and all(row.resolution.outcome=='success' for row in actions)
enc.schedule_action(DelayAction(enc,actor,defense=0,start_time=enc.time,id=delay))
enc.step(1)
print(json.dumps({'time':enc.time,'rng':rng_digest(rng),
 'history':hashlib.sha256(native_history.encode(native_history.capture(enc))).hexdigest(),
 'holders':holders,'action_ids':sorted(row.id for row in actions),'object_id':obj.id},sort_keys=True))'''
            import os
            result = subprocess.run(
                [sys.executable, '-B', '-c', child, str(path), object_id,
                 actor_id, third_id, delay_id], cwd=ROOT,
                env={**os.environ, 'PYTHONPATH': f'{ROOT / "src"}:{ROOT / "examples"}'},
                text=True, capture_output=True, check=False, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), expected)

    def test_pending_disarm_landing_choice_restores_and_commits_same_weapon(self):
        """A post-roll landing Choice remains actionable after native restore."""
        from action import Action
        from action_evaluation import _ProvisionalRandom, RandomDraw
        from arena_hex_map import ArenaHexLayout, HexAddress, encounter_map_descriptor
        from atomic_publication import disarm_landing_options, choose_disarm_landing
        from melee_combat import effective_melee_reach_meters
        from native_scenario import NativeScenarioBuilder
        from unittest.mock import patch
        builder = NativeScenarioBuilder(
            'Native Disarm landing continuation',
            Library(config_dir=str(ROOT / 'src/config')), seed=41)
        attacker = builder.add_being('Human', 'Disarmer', radius=.25,
            hit_points=100)
        defender = builder.add_being('Human', 'Weapon holder', radius=.25,
            hit_points=100)
        world, encounter = builder.world, builder.encounter
        layout = ArenaHexLayout.rectangle(10, 10)
        encounter.map = encounter_map_descriptor(layout)
        source = layout.center_position(HexAddress(5, 5))
        target = layout.center_position(HexAddress(6, 5))
        attacker.set_position(source)
        defender.set_position(target)
        from hex_facing import nearest_facing
        attacker.set_hex_facing(nearest_facing(
            (target.x-source.x, target.y-source.y, 0.0)))
        defender.set_hex_facing(6)
        for being in (attacker, defender):
            being.set_posture('standing')
            being.size_category = 'medium'
        builder.mark_aware(attacker.id, defender.id)
        builder.mark_aware(defender.id, attacker.id)
        instrument = builder.make_weapon(attacker.id, 'Dagger', 'Disarming Dagger')
        target_weapon = builder.make_weapon(defender.id, 'Dagger', 'Target Dagger')
        builder.arm(attacker.id, instrument.id, 'right hand')
        builder.arm(defender.id, target_weapon.id, 'right hand')
        attacker.current.skills.weapon_skills['Dagger'] = 2
        builder.enable()
        action = Action(world, 0, 1, 'disarm', attacker.id, defender.id,
                        instrument.id)
        action.disarm_weapon_id = target_weapon.id
        action.disarm_motion = 'thrust'
        action.reach = effective_melee_reach_meters(
            attacker.current, instrument.current)
        action.end_time = instrument.Tt()
        builder.schedule(action)
        values = iter((20, 1))
        def scripted(context, dice):
            value = next(values)
            context.trace.append(RandomDraw(context.action_id, dice,
                int(dice[2:].split('+')[0]), value))
            return value
        with patch.object(_ProvisionalRandom, 'roll', scripted):
            encounter.step(action.end_time)
        self.assertEqual(action.resolution.outcome, 'landing_choice_pending')
        self.assertTrue(disarm_landing_options(encounter, target_weapon.id))
        wire = export_save(encounter)
        actor_id, object_id, action_id = attacker.id, target_weapon.id, action.id
        saved_options = disarm_landing_options(encounter, object_id)
        chosen = saved_options[0]
        choose_disarm_landing(encounter, object_id, chosen.column, chosen.row)
        encounter.schedule_action(DelayAction(
            encounter, actor_id, defense=0, start_time=encounter.time,
            id='native-disarm-landing-continuation'))
        encounter.step(1)
        committed_history = native_history.capture(encounter)
        landing_receipt = encounter._disarm_landing_receipts[-1]
        self.assertEqual(
            native_history.NativeHistoryQuery(committed_history).disarm_landings_at(
                landing_receipt.boundary),
            native_history._plain((landing_receipt,)))
        from native_history import NativeHistoryRejected, _seal
        corrupted = json.loads(json.dumps(committed_history))
        landing_row = next(row for row in corrupted["boundaries"]
                           if row.get("boundary") == landing_receipt.boundary)
        landing_row["disarm_landings"]["$tuple"][0]["fields"]["actor_id"] = "missing-being"
        corrupted = _seal({key: value for key, value in corrupted.items()
                           if key != "sha256"})
        with self.assertRaisesRegex(NativeHistoryRejected, "dangling Entity reference"):
            native_history.validate(corrupted)
        expected = {
            'time': encounter.time,
            'rng': hashlib.sha256(json.dumps(builder.rng.state).encode()).hexdigest(),
            'history': hashlib.sha256(native_history.encode(committed_history)).hexdigest(),
            'object_id': object_id,
            'position': list(world.get_object_by_id(object_id).get_position().as_tuple()),
            'parent': world.get_object_by_id(object_id).parent_container_id,
            'holder_hand': defender.current.body_parts.get('right hand'),
            'action_id': action_id,
            'outcome': action.resolution.outcome,
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'native-disarm-pending.json'
            path.write_bytes(wire)
            child = r'''import hashlib,json,sys
import native_history
from activities import DelayAction
from atomic_publication import disarm_landing_options,choose_disarm_landing
from native_persistence import load_path
world,enc,rng=load_path(sys.argv[1])
object_id,actor_id,action_id=sys.argv[2:]
action=world.get_event_by_id(action_id)
assert action.resolution.outcome=='landing_choice_pending'
weapon=world.get_object_by_id(object_id)
from weapon import native_pending_disarm_landing
assert native_pending_disarm_landing(weapon) is not None
options=disarm_landing_options(enc,object_id)
assert options
cell=options[0]
choose_disarm_landing(enc,object_id,cell.column,cell.row)
enc.schedule_action(DelayAction(enc,actor_id,defense=0,start_time=enc.time,
 id='native-disarm-landing-continuation'))
enc.step(1)
holder=world.get_object_by_id(action.target_id)
print(json.dumps({'time':enc.time,
 'rng':hashlib.sha256(json.dumps(rng.state).encode()).hexdigest(),
 'history':hashlib.sha256(native_history.encode(native_history.capture(enc))).hexdigest(),
 'object_id':weapon.id,'position':weapon.get_position().as_tuple(),
 'parent':weapon.parent_container_id,
 'holder_hand':holder.current.body_parts.get('right hand'),
 'action_id':action.id,'outcome':action.resolution.outcome},sort_keys=True))'''
            import os
            result = subprocess.run(
                [sys.executable, '-B', '-c', child, str(path), object_id,
                 actor_id, action_id], cwd=ROOT,
                env={**os.environ, 'PYTHONPATH': f'{ROOT / "src"}:{ROOT / "examples"}'},
                text=True, capture_output=True, check=False, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), expected)

    def test_multiple_action_choice_and_simultaneous_touch_resume_from_initial_save(self):
        """An initial Save restores accepted composition and its first commits."""
        from action_choice import ChoiceMember
        from action import Action
        from native_scenario import NativeScenarioBuilder
        builder = NativeScenarioBuilder(
            'Native multiple-Action persistence',
            Library(config_dir=str(ROOT / 'src/config')), end_time=1, seed=53)
        actor = builder.add_being('Human', 'Composing Being',
            position=(0, 0, 0), radius=.2, hit_points=100)
        first_target = builder.add_being('Human', 'First Search target',
            position=(.3, 0, 0), radius=.2, hit_points=100)
        second_target = builder.add_being('Human', 'Second Search target',
            position=(0, .3, 0), radius=.2, hit_points=100)
        for target in (first_target, second_target):
            builder.mark_aware(actor.id, target.id)
        actor.set_skill_level(builder.world.get_skill_dictionary(), 'multi-action', 1)
        builder.enable()
        actions = []
        for identity, target in (('first', first_target), ('second', second_target)):
            action = Action(builder.world, 0, 1, 'touch', actor.id, target.id, None,
                            id=f'native-multi-touch-{identity}')
            action.touch_willing = True
            actions.append(action)
        actions = tuple(actions)
        builder.schedule_choice((
            ChoiceMember('first', actions[0], priority_penalty=0),
            ChoiceMember('second', actions[1], priority_penalty=3),
        ))
        choice = builder.encounter.choice_for_action(actions[0].id)
        initial_schedule = native_history.capture_initial_schedule(builder.encounter)
        self.assertEqual(choice.state, 'accepted')
        choice_record = builder.encounter._choice_book._choices[choice.id]
        self.assertEqual(tuple(row.priority_penalty for row in choice_record.members), (0, 3))
        self.assertFalse(native_history.has_recorder(builder.encounter))
        with patch('native_persistence.MAX_BYTES', 1):
            with self.assertRaisesRegex(NativeSaveRejected, 'portable size limit'):
                export_save(builder.encounter)
        self.assertFalse(native_history.has_recorder(builder.encounter))
        wire = export_save(builder.encounter)
        self.assertIsNone(native_history.current_recording(builder.encounter))
        builder.step(1)
        rows = builder.encounter._atomic_interval_history
        first_receipt = next(row for row in rows if row.boundary == 1)
        self.assertEqual(set(first_receipt.action_ids), {row.id for row in actions})
        expected = {
            'time': builder.encounter.time,
            'rng': hashlib.sha256(json.dumps(builder.rng.state).encode()).hexdigest(),
            'history': hashlib.sha256(native_history.encode(
                native_history.capture(builder.encounter))).hexdigest(),
            'choice_id': choice.id,
            'action_ids': [row.id for row in actions],
            'outcomes': [row.resolution.outcome for row in actions],
            'priority_penalties': [0, 3],
            'receipt_action_ids': list(first_receipt.action_ids),
            'initial_schedule': initial_schedule,
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'native-multiple-action.json'
            path.write_bytes(wire)
            child = r'''import hashlib,json,sys
import native_history
from native_persistence import load_path
world,enc,rng=load_path(sys.argv[1])
assert not (set(sys.modules)&{'arena_browser_session','arena_server','npcgen'})
choice_id,first_id,second_id=sys.argv[2:]
choice=enc.get_choice(choice_id)
assert choice.state=='accepted'
record=enc._choice_book._choices[choice_id]
assert [member.action.id for member in record.members]==[first_id,second_id]
assert [member.priority_penalty for member in record.members]==[0,3]
enc.step(1)
rows=enc._atomic_interval_history
first_receipt=next(row for row in rows if row.boundary==1)
assert set(first_receipt.action_ids)=={first_id,second_id}
actions=[world.get_event_by_id(identity) for identity in (first_id,second_id)]
initial_schedule=native_history.NativeHistoryQuery(
 native_history.current_recording(enc)).schedule_at(0)
print(json.dumps({'time':enc.time,
 'rng':hashlib.sha256(json.dumps(rng.state).encode()).hexdigest(),
 'history':hashlib.sha256(native_history.encode(native_history.capture(enc))).hexdigest(),
 'choice_id':choice.id,'action_ids':[row.id for row in actions],
 'outcomes':[row.resolution.outcome for row in actions],
 'priority_penalties':[member.priority_penalty for member in record.members],
 'receipt_action_ids':list(first_receipt.action_ids),
 'initial_schedule':initial_schedule},sort_keys=True))'''
            import os
            result = subprocess.run(
                [sys.executable, '-B', '-c', child, str(path), choice.id,
                 actions[0].id, actions[1].id], cwd=ROOT,
                env={**os.environ, 'PYTHONPATH': f'{ROOT / "src"}:{ROOT / "examples"}'},
                text=True, capture_output=True, check=False, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), expected)

    def test_repeating_multiple_action_successor_choice_resumes_natively(self):
        """The immutable next cycle survives Load and resolves as declared."""
        from action_choice import ChoiceMember
        from action import Action
        from native_scenario import NativeScenarioBuilder
        builder = NativeScenarioBuilder(
            'Native repeated Multiple-action cycle',
            Library(config_dir=str(ROOT / 'src/config')), end_time=3, seed=61)
        actor = builder.add_being('Human', 'Repeated actor',
            position=(0, 0, 0), radius=.2, hit_points=100)
        targets = (
            builder.add_being('Human', 'First target',
                position=(.3, 0, 0), radius=.2, hit_points=100),
            builder.add_being('Human', 'Second target',
                position=(0, .3, 0), radius=.2, hit_points=100),
        )
        for target in targets:
            builder.mark_aware(actor.id, target.id)
        actor.set_skill_level(builder.world.get_skill_dictionary(), 'multi-action', 1)
        builder.enable()
        first_cycle = []
        for key, target in zip(('first', 'second'), targets):
            action = Action(builder.world, 0, 1, 'touch', actor.id, target.id, None,
                            id=f'native-repeat-{key}')
            action.touch_willing = True
            first_cycle.append(action)
        builder.schedule_choice((
            ChoiceMember('first', first_cycle[0], priority_penalty=0),
            ChoiceMember('second', first_cycle[1], priority_penalty=3),
        ))
        builder.step(1)
        active = [record for record in builder.encounter._choice_book._choices.values()
                  if record.view.state == 'accepted']
        self.assertEqual(len(active), 1)
        successor = active[0]
        self.assertEqual(tuple(member.priority_penalty for member in successor.members), (0, 3))
        successor_action_ids = [member.action.id for member in successor.members]
        self.assertTrue(set(successor_action_ids).isdisjoint(
            {action.id for action in first_cycle}))
        wire = export_save(builder.encounter)
        builder.step(1)

        def state(world, encounter, rng):
            rows = sorted(encounter._choice_book.summary()['choices'],
                          key=lambda row: row['id'])
            action_ids = sorted(identity for identity in world.event_history
                                if getattr(world.get_event_by_id(identity),
                                           'event_type', None) == 'touch')
            return {
                'time': encounter.time,
                'rng': hashlib.sha256(json.dumps(rng.state).encode()).hexdigest(),
                'history': hashlib.sha256(native_history.encode(
                    native_history.capture(encounter))).hexdigest(),
                'choices': rows,
                'successor_actions': successor_action_ids,
                'touch_actions': action_ids,
                'outcomes': [world.get_event_by_id(identity).resolution.outcome
                             for identity in action_ids],
            }
        expected = state(builder.world, builder.encounter, builder.rng)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'native-repeat-choice.json'
            path.write_bytes(wire)
            child = r'''import hashlib,json,sys
import native_history
from native_persistence import load_path
world,enc,rng=load_path(sys.argv[1])
successor_id,*action_ids=sys.argv[2:]
choice=enc._choice_book._choices[successor_id]
assert choice.view.state=='accepted'
assert [member.action.id for member in choice.members]==action_ids
assert [member.priority_penalty for member in choice.members]==[0,3]
enc.step(1)
rows=sorted(enc._choice_book.summary()['choices'],key=lambda row:row['id'])
touch_ids=sorted(identity for identity in world.event_history
 if getattr(world.get_event_by_id(identity),'event_type',None)=='touch')
print(json.dumps({'time':enc.time,
 'rng':hashlib.sha256(json.dumps(rng.state).encode()).hexdigest(),
 'history':hashlib.sha256(native_history.encode(native_history.capture(enc))).hexdigest(),
 'choices':rows,'successor_actions':action_ids,'touch_actions':touch_ids,
 'outcomes':[world.get_event_by_id(identity).resolution.outcome
  for identity in touch_ids]},sort_keys=True))'''
            import os
            result = subprocess.run(
                [sys.executable, '-B', '-c', child, str(path), successor.view.id,
                 *successor_action_ids], cwd=ROOT,
                env={**os.environ, 'PYTHONPATH': f'{ROOT / "src"}:{ROOT / "examples"}'},
                text=True, capture_output=True, check=False, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        actual = json.loads(result.stdout)
        for key, value in expected.items():
            with self.subTest(field=key):
                self.assertEqual(actual[key], value)

    def test_native_history_v1_save_upgrades_and_resumes_commit_recording(self):
        from native_history import LEGACY_SCHEMA, SAME_RNG, _seal
        from native_persistence import _canonical
        demo = encounter_delta_headless.build_demo(until=4)
        original = demo['encounter']
        wire = export_save(original)
        body = json.loads(wire)
        boundary_rngs = {row['boundary']: native_history.rng_state_at(
            body['history'], row.get('to_boundary', row.get('boundary')))
            for row in native_history._expand_rows(body['history'])}
        legacy = _legacy_history_shape({key: value for key, value in body['history'].items()
                  if key not in ('sha256', 'entity_context')})
        legacy['schema'] = LEGACY_SCHEMA
        legacy['initial'].pop('rng_before_first_commit')
        previous = None
        for row in legacy['boundaries']:
            if row['rng_after'] == SAME_RNG:
                row['rng_after'] = (boundary_rngs[row['boundary']]
                                    if previous is None else previous)
            previous = row['rng_after']
        body['history'] = _seal({key: value for key, value in legacy.items()
                                 if key != 'sha256'})
        unsigned = {key: value for key, value in body.items() if key != 'sha256'}
        body['sha256'] = hashlib.sha256(_canonical(unsigned)).hexdigest()
        migrated_world, migrated, _ = load_save(_canonical(body))
        self.assertEqual(migrated.id, original.id)
        self.assertEqual(native_history.current_recording(migrated)['schema'],
                         native_history.SCHEMA)
        action_id = 'native-history-v1-migrated-delay'
        actor_id = original.being_list[1]
        for encounter in (original, migrated):
            encounter.schedule_action(DelayAction(
                encounter, actor_id, defense=0, start_time=4, id=action_id))
            encounter.step(1)
        original_query = native_history.NativeHistoryQuery(
            native_history.capture(original))
        migrated_query = native_history.NativeHistoryQuery(
            native_history.capture(migrated))
        self.assertIsNone(migrated_query.schedule_at(0))
        self.assertIsNone(migrated_query.state_at(0)['schedule'])
        for boundary in range(1, original.last_processed_boundary + 1):
            self.assertEqual(migrated_query.schedule_at(boundary),
                             original_query.schedule_at(boundary))
            self.assertEqual(migrated_query.events_at(boundary),
                             original_query.events_at(boundary))
        migrated_wire = export_save(migrated)
        self.assertEqual(export_save(load_save(migrated_wire)[1]), migrated_wire)

    def test_native_history_v4_save_migrates_without_fabricating_then_rebinds_current_context(self):
        from native_history import ENTITY_CONTEXT_SCHEMA, _seal
        from native_persistence import _canonical
        demo = encounter_delta_headless.build_demo(until=4)
        original = demo["encounter"]
        body = json.loads(export_save(original))
        history = native_history._without_fatigue_context(body["history"])
        legacy = _legacy_history_shape({key: value for key, value in history.items()
                                        if key != "sha256"})
        legacy["schema"] = ENTITY_CONTEXT_SCHEMA
        legacy["entity_context"].pop("fatigue_available")
        legacy["initial"].pop("rng_before_first_commit")
        body["history"] = _seal(legacy)
        unsigned = {key: item for key, item in body.items() if key != "sha256"}
        body["sha256"] = hashlib.sha256(_canonical(unsigned)).hexdigest()
        legacy_wire = _canonical(body)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "native-history-v4-save.json"
            path.write_bytes(legacy_wire)
            child = r'''import hashlib,json,sys
import native_history
from activities import DelayAction
from native_persistence import load_path
world,enc,rng=load_path(sys.argv[1])
log=native_history.current_recording(enc)
assert log['schema'] == native_history.SCHEMA
query=native_history.NativeHistoryQuery(log)
assert query.fatigue_context_at(4) is not None
assert query.schedule_at(0) is None
action=DelayAction(enc,enc.being_list[1],defense=0,start_time=4,
 id='native-history-v4-migrated-delay')
enc.schedule_action(action)
enc.step(1)
query=native_history.NativeHistoryQuery(native_history.current_recording(enc))
print(json.dumps({'time':enc.time,'rng':rng.state,
 'schedules':[query.schedule_at(boundary) for boundary in
  range(1,query._latest+1)],
 'actions':list(enc._atomic_interval_history[-1].action_ids)},sort_keys=True))'''
            result = subprocess.run(
                [sys.executable, "-B", "-c", child, str(path)], cwd=directory,
                env={**__import__("os").environ,
                     "PYTHONPATH": f"{ROOT / 'src'}:{ROOT / 'examples'}"},
                text=True, capture_output=True, check=False, timeout=45)

        action = DelayAction(original, original.being_list[1], defense=0,
                             start_time=4, id="native-history-v4-migrated-delay")
        original.schedule_action(action)
        original.step(1)
        expected = {
            "time": original.time,
            "rng": demo["rng_owner"].state,
            "schedules":[native_history.NativeHistoryQuery(
                native_history.capture(original)).schedule_at(boundary)
                for boundary in range(1,original.last_processed_boundary+1)],
            "actions": list(original._atomic_interval_history[-1].action_ids),
        }
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), json.loads(json.dumps(expected)))

    def test_native_history_v5_save_upgrades_without_inventing_origin_then_rebinds_graph(self):
        from native_history import FATIGUE_CONTEXT_SCHEMA, _seal
        from native_persistence import _canonical
        demo = encounter_delta_headless.build_demo(until=4)
        original = demo["encounter"]
        body = json.loads(export_save(original))
        prior = native_history._without_initial_rng(body["history"])
        legacy = _legacy_history_shape({key: value for key, value in prior.items()
                                       if key != "sha256"})
        legacy["schema"] = FATIGUE_CONTEXT_SCHEMA
        legacy["initial"].pop("rng_before_first_commit")
        body["history"] = _seal(legacy)
        unsigned = {key: value for key, value in body.items() if key != "sha256"}
        body["sha256"] = hashlib.sha256(_canonical(unsigned)).hexdigest()

        restored_world, restored, restored_rng = load_save(_canonical(body))
        self.assertEqual(restored.id, original.id)
        self.assertEqual(restored_rng.state, demo["rng_owner"].state)
        current = native_history.current_recording(restored)
        self.assertEqual(current["schema"], native_history.SCHEMA)
        self.assertEqual(current["initial"]["rng_before_first_commit"],
                         native_history._plain(demo["rng_owner"].state))
        self.assertEqual(restored_world.event_history[restored.id], restored)

    def test_native_history_v6_save_preserves_origin_and_rebinds_graph_receipts(self):
        from native_history import INITIAL_RNG_SCHEMA, _seal
        from native_persistence import _canonical
        demo = encounter_delta_headless.build_demo(until=4)
        body = json.loads(export_save(demo["encounter"]))
        history = {key: item for key, item in body["history"].items()
                   if key != "sha256"}
        history.pop("receipt_facts_complete")
        history.pop("observer_knowledge")
        history["initial"].pop("initial_schedule_available")
        history["schema"] = INITIAL_RNG_SCHEMA
        for row in history["boundaries"]:
            row.pop("notification_intents", None)
            row.pop("disarm_landings", None)
            row.pop("receipt_facts_available", None)
        body["history"] = _seal(history)
        unsigned = {key: item for key, item in body.items() if key != "sha256"}
        body["sha256"] = hashlib.sha256(_canonical(unsigned)).hexdigest()

        world, restored, rng = load_save(_canonical(body))
        current = native_history.current_recording(restored)
        self.assertEqual(current["schema"], native_history.SCHEMA)
        self.assertEqual(current["initial"]["rng_before_first_commit"],
                         body["history"]["initial"]["rng_before_first_commit"])
        self.assertTrue(current["receipt_facts_complete"])
        self.assertTrue(native_history.NativeHistoryQuery(current).receipt_facts_at(4))
        self.assertEqual(restored.id, demo["encounter"].id)
        self.assertIs(world.event_history[restored.id], restored)
        self.assertEqual(rng.state, demo["rng_owner"].state)


if __name__ == "__main__":
    unittest.main()
