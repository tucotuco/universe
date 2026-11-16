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


if __name__ == "__main__":
    unittest.main()
