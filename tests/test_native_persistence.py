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
import test_encounter_inspection as inspection_fixtures
import test_action_evaluation as action_fixtures
from native_history import NativeHistoryRecorder
from activities import DelayAction
from atomic_publication import RNGCursor
from encounter import Encounter
from library import Library
from melee_combat import MeleeStrike
from spatial.geometry import Sphere
from spatial.state import CartesianPosition
from strategy import Strategy
from universe import Universe
from native_persistence import (NativeSaveRejected, export_save, load_path,
                                load_save, write_save)
from checkpoint_adapters import RecipientBinding
from reproduction_group import ReproductionGroupProposal, prepare_reproduction_group
from being import BeingDefinition
from reproduction_being_bridge import materialize_reproductive_offspring
from history_conversation import AskAboutPastAction
from activities import SpotAction
from location_observation import LocationEvidenceLedger
from object_observation import ObjectObservationLedger


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
                [sys.executable, "-B", "-c", child, str(path)], cwd=ROOT,
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

    def test_strict_outer_integrity_and_duplicate_keys_are_rejected(self):
        demo = encounter_delta_headless.build_demo(until=4)
        wire = export_save(demo["encounter"])
        value = json.loads(wire)
        value["history"]["latest_boundary"] = 3
        tampered = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
        with self.assertRaisesRegex(NativeSaveRejected, "integrity"):
            load_save(tampered)
        with self.assertRaisesRegex(NativeSaveRejected, "duplicate"):
            load_save(b'{"schema":"a","schema":"b"}')

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
        group = fixture.f.f.f.group()
        expected_count = group.household_count
        expected_household = group.household(0)
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
action=DelayAction(enc,enc.being_list[0],defense=0,start_time=enc.time,
 id='native-group-continuation-delay')
enc.schedule_action(action)
enc.step(1)
print(json.dumps({'world':world.id,'encounter':enc.id,'time':enc.time,
 'rng':rng.state,'group_id':group.id,'count':group.household_count,
 'household':group.household(0),
 'history':hashlib.sha256(native_history.encode(native_history.capture(enc))).hexdigest(),
 'actions':list(enc._atomic_interval_history[-1].action_ids),
 'arena_imports':sorted(set(sys.modules)&{'arena_browser_session','arena_native_snapshot',
  'arena_persistence','arena_server','npcgen'})},sort_keys=True))'''
            import os
            result = subprocess.run(
                [sys.executable, "-B", "-c", child, str(path),
                 str(expected_count), json.dumps(expected_household)],
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


if __name__ == "__main__":
    unittest.main()
