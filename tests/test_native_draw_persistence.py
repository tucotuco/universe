from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "examples")]

from action import Action
from activities import PickUpAction, ReadyWeaponAction
from library import Library
from arena_hex_map import ArenaHexLayout, HexAddress
from melee_combat import MeleeStrike
from native_history import capture, encode
from native_persistence import export_save
from native_scenario import NativeScenarioBuilder
from object import ObjectDefinition, ObjectInstance
from spatial.state import CartesianPosition
from strategy import Strategy
from melee_combat import effective_melee_reach_meters
from weapon import author_worn_sheath_draw_location, native_weapon_draw_location


class NativeDrawPersistenceTests(unittest.TestCase):
    def test_headless_draw_restores_and_commits_in_a_fresh_native_process(self):
        builder = NativeScenarioBuilder(
            "native-draw", Library(config_dir=str(ROOT / "src/config")),
            seed=8102, encounter_id="native-draw-encounter")
        actor = builder.add_being("Human", "Native Draw Actor")
        weapon_id = builder.world.make_weapon("Dagger", "Native Drawable Dagger")
        weapon = builder.world.get_object_by_id(weapon_id)
        actor.possessions.append(weapon.id)
        weapon.parent_container_id = actor.id
        author_worn_sheath_draw_location(weapon, actor.id)
        builder.add_object(weapon.id)
        builder.enable()
        action = ReadyWeaponAction(builder.encounter, actor.id, weapon.id,
                                   "right hand", 0,
                                   id="native-draw-action")
        builder.schedule(action)
        wire = export_save(builder.encounter)

        builder.step(1)
        self.assertEqual(builder.encounter.time, 1)
        self.assertIsNone(actor.current.body_parts["right hand"])
        self.assertIsNotNone(native_weapon_draw_location(weapon))
        builder.step(1)
        self.assertEqual(builder.encounter.time, 2)
        self.assertEqual(actor.current.body_parts["right hand"], weapon.id)
        self.assertIsNone(native_weapon_draw_location(weapon))
        expected = {
            "time": builder.encounter.time,
            "action_id": action.id,
            "finished": action.id in builder.encounter.finished_action_list,
            "hand": actor.current.body_parts["right hand"],
            "possessions": list(actor.possessions),
            "weapons": list(actor.weapons),
            "parent": weapon.parent_container_id,
            "rng": builder.rng.state,
            "history": hashlib.sha256(encode(capture(builder.encounter))).hexdigest(),
        }
        child = r'''import hashlib,json,sys
import native_history
from native_persistence import load_save
from weapon import native_weapon_draw_location
world,enc,rng=load_save(open(sys.argv[1],'rb').read())
actor=world.get_object_by_id(sys.argv[2]);weapon=world.get_object_by_id(sys.argv[3])
choice=enc.choice_for_action(sys.argv[4])
action=enc._choice_book._choices[choice.id].members[0].action
assert action.id==sys.argv[4] and choice.state=='accepted' and enc.time==0
assert actor.current.body_parts['right hand'] is None
assert native_weapon_draw_location(weapon)['owner_id']==actor.id
enc.step(1);assert actor.current.body_parts['right hand'] is None
assert native_weapon_draw_location(weapon) is not None
enc.step(1)
assert actor.current.body_parts['right hand']==weapon.id
assert native_weapon_draw_location(weapon) is None
print(json.dumps({'time':enc.time,'action_id':action.id,
 'finished':action.id in enc.finished_action_list,
 'hand':actor.current.body_parts['right hand'],
 'possessions':list(actor.possessions),'weapons':list(actor.weapons),
 'parent':weapon.parent_container_id,'rng':rng.state,
 'history':hashlib.sha256(native_history.encode(
  native_history.capture(enc))).hexdigest()},sort_keys=True))'''
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "native-draw.json"
            path.write_bytes(wire)
            result = subprocess.run(
                [sys.executable, "-B", "-c", child, str(path), actor.id,
                 weapon.id, action.id], cwd=directory,
                env={**os.environ, "PYTHONPATH": f"{ROOT / 'src'}:{ROOT / 'examples'}"},
                text=True, capture_output=True, check=False, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        restored = json.loads(result.stdout)
        expected = json.loads(json.dumps(expected))
        self.assertEqual({key: value for key, value in restored.items()
                          if key not in ("rng", "history")},
                         {key: value for key, value in expected.items()
                          if key not in ("rng", "history")})
        self.assertEqual(restored["rng"], expected["rng"])
        self.assertEqual(restored["history"], expected["history"])

    def test_headless_shield_don_and_remove_restore_in_fresh_native_processes(self):
        from activities import ShieldEquipmentAction

        builder = NativeScenarioBuilder(
            "native-shield-equipment", Library(config_dir=str(ROOT / "src/config")),
            seed=8103, encounter_id="native-shield-encounter")
        actor = builder.add_being("Human", "Native Shield Bearer")
        shield_id = builder.world.make_weapon("Medium shield", "Native carried shield")
        shield = builder.world.get_object_by_id(shield_id)
        actor.possessions.append(shield.id)
        shield.parent_container_id = actor.id
        builder.add_object(shield.id)
        builder.enable()

        child = r'''import hashlib,json,sys
import native_history
from native_persistence import load_save
world,enc,rng=load_save(open(sys.argv[1],'rb').read())
actor=world.get_object_by_id(sys.argv[2]);shield=world.get_object_by_id(sys.argv[3])
action_id=sys.argv[4];operation=sys.argv[5]
choice=enc.choice_for_action(action_id)
action=enc._choice_book._choices[choice.id].members[0].action
assert action.id==action_id and action.operation==operation
assert choice.state=='accepted'
for _ in range(int(action.end_time-enc.time)):enc.step(1)
result={'time':enc.time,'action_id':action.id,'operation':action.operation,
 'finished':action.id in enc.finished_action_list,
 'hand':actor.current.body_parts['right hand'],
 'weapons':list(actor.weapons),'possessions':list(actor.possessions),
 'parent':shield.parent_container_id,'shielded':actor.shielded_with(world),
 'rng':rng.state,'history':hashlib.sha256(native_history.encode(
  native_history.capture(enc))).hexdigest()}
print(json.dumps(result,sort_keys=True))'''

        def state(action):
            return {
                "time": builder.encounter.time,
                "action_id": action.id,
                "operation": action.operation,
                "finished": action.id in builder.encounter.finished_action_list,
                "hand": actor.current.body_parts["right hand"],
                "weapons": list(actor.weapons),
                "possessions": list(actor.possessions),
                "parent": shield.parent_container_id,
                "shielded": actor.shielded_with(builder.world),
                "rng": builder.rng.state,
                "history": hashlib.sha256(encode(capture(builder.encounter))).hexdigest(),
            }

        def fresh_continue(wire, action):
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "native-shield.json"
                path.write_bytes(wire)
                result = subprocess.run(
                    [sys.executable, "-B", "-c", child, str(path), actor.id,
                     shield.id, action.id, action.operation], cwd=directory,
                    env={**os.environ,
                         "PYTHONPATH": f"{ROOT / 'src'}:{ROOT / 'examples'}"},
                    text=True, capture_output=True, check=False, timeout=60)
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)

        don = ShieldEquipmentAction(builder.encounter, actor.id, shield.id,
                                    "right hand", "don", 0,
                                    id="native-shield-don")
        builder.schedule(don)
        don_wire = export_save(builder.encounter)
        for _ in range(don.end_time):
            builder.step(1)
        expected_don = json.loads(json.dumps(state(don)))
        self.assertEqual(expected_don["hand"], shield.id)
        self.assertIn(shield.id, expected_don["weapons"])
        self.assertEqual(fresh_continue(don_wire, don), expected_don)

        remove = ShieldEquipmentAction(builder.encounter, actor.id, shield.id,
                                       "right hand", "remove", builder.encounter.time,
                                       id="native-shield-remove")
        builder.schedule(remove)
        remove_wire = export_save(builder.encounter)
        for _ in range(int(remove.end_time - remove.start_time)):
            builder.step(1)
        expected_remove = json.loads(json.dumps(state(remove)))
        self.assertIsNone(expected_remove["hand"])
        self.assertNotIn(shield.id, expected_remove["weapons"])
        self.assertIn(shield.id, expected_remove["possessions"])
        self.assertEqual(fresh_continue(remove_wire, remove), expected_remove)

    def test_headless_pickup_contention_restores_without_duplicate_custody(self):
        layout = ArenaHexLayout.rectangle(10, 5)
        position = layout.center_position(HexAddress(4, 2))
        builder = NativeScenarioBuilder(
            "native-pickup-contention", Library(config_dir=str(ROOT / "src/config")),
            seed=8104, encounter_id="native-pickup-encounter")
        actors = [builder.add_being("Human", name, position=position.as_tuple())
                  for name in ("First Picker", "Second Picker")]
        object_id = builder.world.make_weapon("Dagger", "Contended ground Dagger")
        obj = builder.world.get_object_by_id(object_id)
        obj.set_position(position)
        builder.add_object(obj.id)
        builder.enable()
        actions = [PickUpAction(builder.encounter, actor.id, obj.id, 0,
                                map_width_cells=10, map_height_cells=5,
                                id=f"native-pickup-{index}")
                   for index, actor in enumerate(actors, 1)]
        for action in actions:
            builder.schedule(action)
        wire = export_save(builder.encounter)
        builder.step(1)
        receipt = builder.encounter.inspect_committed(1)
        outcomes = [receipt.action(action.id).facts.outcome for action in actions]
        self.assertEqual(outcomes, ["contested", "contested"])
        self.assertIsNone(obj.parent_container_id)
        self.assertIsNotNone(obj.spatial_state)
        expected = {
            "time": builder.encounter.time,
            "action_ids": [action.id for action in actions],
            "finished": [action.id in builder.encounter.finished_action_list
                         for action in actions],
            "outcomes": outcomes,
            "custody": [list(actor.possessions) for actor in actors],
            "parent": obj.parent_container_id,
            "position": obj.get_position().as_tuple(),
            "rng": builder.rng.state,
            "history": hashlib.sha256(encode(capture(builder.encounter))).hexdigest(),
        }
        child = r'''import hashlib,json,sys
import native_history
from native_persistence import load_save
world,enc,rng=load_save(open(sys.argv[1],'rb').read())
actor_ids=sys.argv[2:4];object_id=sys.argv[4];action_ids=sys.argv[5:7]
actions=[]
for action_id in action_ids:
 choice=enc.choice_for_action(action_id)
 assert choice.state=='accepted'
 actions.append(next(m.action for m in enc._choice_book._choices[choice.id].members
                     if m.action.id==action_id))
enc.step(1)
receipt=enc.inspect_committed(1);actors=[world.get_object_by_id(i) for i in actor_ids]
obj=world.get_object_by_id(object_id)
print(json.dumps({'time':enc.time,'action_ids':[a.id for a in actions],
 'finished':[a.id in enc.finished_action_list for a in actions],
 'outcomes':[receipt.action(a.id).facts.outcome for a in actions],
 'custody':[list(a.possessions) for a in actors],'parent':obj.parent_container_id,
 'position':obj.get_position().as_tuple(),'rng':rng.state,
 'history':hashlib.sha256(native_history.encode(native_history.capture(enc))).hexdigest()},
 sort_keys=True))'''
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "native-pickup.json"
            path.write_bytes(wire)
            result = subprocess.run(
                [sys.executable, "-B", "-c", child, str(path), actors[0].id,
                 actors[1].id, obj.id, actions[0].id, actions[1].id], cwd=directory,
                env={**os.environ,
                     "PYTHONPATH": f"{ROOT / 'src'}:{ROOT / 'examples'}"},
                text=True, capture_output=True, check=False, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), json.loads(json.dumps(expected)))

    def test_headless_ready_preparation_is_consumed_after_restored_strike(self):
        from activities import ReadyPreparationAction
        from weapon import native_ready_preparation

        builder = NativeScenarioBuilder(
            "native-ready-and-strike", Library(config_dir=str(ROOT / "src/config")),
            seed=8105, encounter_id="native-ready-encounter")
        attacker = builder.add_being("Human", "Ready Attacker", position=(0, 0, 0),
                                     radius=.25, hit_points=100)
        defender = builder.add_being("Human", "Ready Defender", position=(1.5, 0, 0),
                                     radius=.25, hit_points=100)
        weapon = builder.make_weapon(attacker.id, "Longsword", "Readied native Longsword",
                                     hand="right hand", participant=True)
        builder.mark_aware(attacker.id, defender.id)
        builder.mark_aware(defender.id, attacker.id)
        builder.enable()
        ready = ReadyPreparationAction(builder.encounter, attacker.id, weapon.id,
                                       "swing", 0, strategy=Strategy(),
                                       id="native-ready-action")
        builder.schedule(ready)
        initial = export_save(builder.encounter)
        ready_seconds = ready.end_time - ready.start_time
        builder.step(ready_seconds)
        prepared = native_ready_preparation(weapon)
        self.assertIsNotNone(prepared)
        expected_ready = {
            "time": builder.encounter.time,
            "ready_id": ready.id,
            "weapon_ready": prepared,
            "rng": builder.rng.state,
            "history": hashlib.sha256(encode(capture(builder.encounter))).hexdigest(),
        }
        initial_child = r'''import hashlib,json,sys
import native_history
from native_persistence import load_save
from weapon import native_ready_preparation
world,enc,rng=load_save(open(sys.argv[1],'rb').read())
actor=world.get_object_by_id(sys.argv[2]);weapon=world.get_object_by_id(sys.argv[3])
ready_id=sys.argv[4];choice=enc.choice_for_action(ready_id)
assert choice.state=='accepted'
ready=next(member.action for member in enc._choice_book._choices[choice.id].members
           if member.action.id==ready_id)
assert ready.id==ready_id and actor.current.body_parts['right hand']==weapon.id
enc.step(int(ready.end_time-ready.start_time))
print(json.dumps({'time':enc.time,'ready_id':ready.id,
 'weapon_ready':native_ready_preparation(weapon),'rng':rng.state,
 'history':hashlib.sha256(native_history.encode(native_history.capture(enc))).hexdigest()},
 sort_keys=True))'''
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "native-ready-initial.json"
            path.write_bytes(initial)
            first_restore = subprocess.run(
                [sys.executable, "-B", "-c", initial_child, str(path),
                 attacker.id, weapon.id, ready.id], cwd=directory,
                env={**os.environ,
                     "PYTHONPATH": f"{ROOT / 'src'}:{ROOT / 'examples'}"},
                text=True, capture_output=True, check=False, timeout=60)
        self.assertEqual(first_restore.returncode, 0, first_restore.stderr)
        self.assertEqual(json.loads(first_restore.stdout),
                         json.loads(json.dumps(expected_ready)))
        strike = MeleeStrike(builder.encounter, attacker.id, defender.id, weapon.id,
                             motion="swing", reach=2, strategy=Strategy())
        builder.schedule(strike)
        pending_strike = export_save(builder.encounter)
        builder.step(strike.end_time - strike.start_time)
        self.assertIn(strike.id, builder.encounter.finished_action_list)
        self.assertIsNone(native_ready_preparation(weapon))
        expected = {
            "time": builder.encounter.time,
            "ready_id": ready.id,
            "strike_id": strike.id,
            "strike_outcome": builder.encounter.inspect_committed(
                int(builder.encounter.time)).action(strike.id).facts.outcome,
            "attacker_hp": attacker.get_hit_points(),
            "defender_hp": defender.get_hit_points(),
            "weapon_ready": native_ready_preparation(weapon),
            "weapon_parent": weapon.parent_container_id,
            "rng": builder.rng.state,
            "history": hashlib.sha256(encode(capture(builder.encounter))).hexdigest(),
        }
        child = r'''import hashlib,json,sys
import native_history
from native_persistence import load_save
from weapon import native_ready_preparation
world,enc,rng=load_save(open(sys.argv[1],'rb').read())
actor=world.get_object_by_id(sys.argv[2]);target=world.get_object_by_id(sys.argv[3])
weapon=world.get_object_by_id(sys.argv[4]);ready_id=sys.argv[5];strike_id=sys.argv[6]
assert native_ready_preparation(weapon)['ready_action_id']==ready_id
choice=enc.choice_for_action(strike_id)
assert choice.state=='accepted'
strike=next(member.action for member in enc._choice_book._choices[choice.id].members
            if member.action.id==strike_id)
enc.step(int(strike.end_time-strike.start_time))
receipt=enc.inspect_committed(int(enc.time))
assert strike.id in enc.finished_action_list
assert native_ready_preparation(weapon) is None
print(json.dumps({'time':enc.time,'ready_id':ready_id,'strike_id':strike.id,
 'strike_outcome':receipt.action(strike.id).facts.outcome,
 'attacker_hp':actor.get_hit_points(),'defender_hp':target.get_hit_points(),
 'weapon_ready':native_ready_preparation(weapon),
 'weapon_parent':weapon.parent_container_id,'rng':rng.state,
 'history':hashlib.sha256(native_history.encode(native_history.capture(enc))).hexdigest()},
 sort_keys=True))'''
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "native-ready-strike.json"
            path.write_bytes(pending_strike)
            result = subprocess.run(
                [sys.executable, "-B", "-c", child, str(path), attacker.id,
                 defender.id, weapon.id, ready.id, strike.id], cwd=directory,
                env={**os.environ,
                     "PYTHONPATH": f"{ROOT / 'src'}:{ROOT / 'examples'}"},
                text=True, capture_output=True, check=False, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), json.loads(json.dumps(expected)))

    def test_headless_object_strike_hit_and_damage_restore_with_exact_facts(self):
        builder = NativeScenarioBuilder(
            "native-object-strike", Library(config_dir=str(ROOT / "src/config")),
            seed=5, encounter_id="native-object-strike-encounter")
        attacker = builder.add_being("Human", "Object Striker", position=(0, 0, 0),
                                     radius=.25, hit_points=100)
        weapon = builder.make_weapon(attacker.id, "Longsword", "Object-strike Longsword",
                                     hand="right hand")
        target = ObjectInstance(ObjectDefinition(
            "authored hardwood save target", 12, 12, 12, 20, 1, 2, 6),
            name="Native hardwood target")
        target.set_position(CartesianPosition(.5, 0, 0))
        builder.world.add_object(target)
        builder.add_object(target.id)
        builder.mark_aware(attacker.id, target.id)
        path = builder.encounter.physical_path(attacker.id, target.id)
        self.assertEqual(path.intersections, ())
        self.assertEqual(path.unmodeled_entity_ids, ())
        builder.enable()
        action = Action(builder.world, 0, 1, "strike object", attacker.id,
                        target.id, weapon.id, id="native-object-strike-action")
        action.object_motion = "thrust"
        action.reach = effective_melee_reach_meters(attacker.current, weapon.current)
        action.end_time = max(1, math.ceil(weapon.Tt()))
        builder.schedule(action)
        pending = export_save(builder.encounter)
        builder.step(action.end_time - action.start_time)
        receipt = builder.encounter.inspect_committed(action.end_time).action(action.id)
        damage = [effect for effect in receipt.facts.effects
                  if getattr(effect, "component", None) == "object"]
        self.assertEqual(receipt.facts.outcome, "normal")
        self.assertEqual(len(damage), 1)
        self.assertEqual(target.hit_points(), 2)
        expected = {
            "time": builder.encounter.time,
            "action_id": action.id,
            "object_id": target.id,
            "outcome": receipt.facts.outcome,
            "object_damage": damage[0].amount,
            "object_hp": target.hit_points(),
            "position": target.get_position().as_tuple(),
            "parent": target.parent_container_id,
            "rng": builder.rng.state,
            "history": hashlib.sha256(encode(capture(builder.encounter))).hexdigest(),
        }
        child = r'''import hashlib,json,sys
import native_history
from native_persistence import load_save
world,enc,rng=load_save(open(sys.argv[1],'rb').read())
object_id,action_id=sys.argv[2:]
target=world.get_object_by_id(object_id)
choice=enc.choice_for_action(action_id)
assert choice.state=='accepted'
action=next(member.action for member in enc._choice_book._choices[choice.id].members
            if member.action.id==action_id)
assert action.id==action_id and target.hit_points()==6
enc.step(int(action.end_time-enc.time))
receipt=enc.inspect_committed(int(action.end_time)).action(action.id)
damage=[effect for effect in receipt.facts.effects
        if getattr(effect,'component',None)=='object']
print(json.dumps({'time':enc.time,'action_id':action.id,'object_id':target.id,
 'outcome':receipt.facts.outcome,'object_damage':damage[0].amount,
 'object_hp':target.hit_points(),'position':target.get_position().as_tuple(),
 'parent':target.parent_container_id,'rng':rng.state,
 'history':hashlib.sha256(native_history.encode(native_history.capture(enc))).hexdigest()},
 sort_keys=True))'''
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "native-object-strike.json"
            path.write_bytes(pending)
            result = subprocess.run(
                [sys.executable, "-B", "-c", child, str(path), target.id, action.id],
                cwd=directory,
                env={**os.environ,
                     "PYTHONPATH": f"{ROOT / 'src'}:{ROOT / 'examples'}"},
                text=True, capture_output=True, check=False, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), json.loads(json.dumps(expected)))

    def test_headless_simultaneous_object_strikes_preserve_common_snapshot_durability(self):
        builder = NativeScenarioBuilder(
            "native-simultaneous-object-strikes",
            Library(config_dir=str(ROOT / "src/config")), seed=5,
            encounter_id="native-simultaneous-object-encounter")
        actors = [builder.add_being("Human", name, position=position,
                                    radius=.25, hit_points=100)
                  for name, position in (("Left Striker", (0, 0, 0)),
                                         ("Right Striker", (1.5, 0, 0)))]
        weapons = [builder.make_weapon(actor.id, "Longsword", f"Longsword {index}",
                                       hand="right hand")
                   for index, actor in enumerate(actors, 1)]
        target = ObjectInstance(ObjectDefinition(
            "simultaneous hardwood target", 12, 12, 12, 20, 1, 1, 3),
            name="Simultaneous native target")
        target.set_position(CartesianPosition(.75, 0, 0))
        builder.world.add_object(target)
        builder.add_object(target.id)
        actions = []
        for index, (actor, weapon) in enumerate(zip(actors, weapons), 1):
            builder.mark_aware(actor.id, target.id)
            clear = builder.encounter.physical_path(actor.id, target.id)
            self.assertEqual(clear.intersections, ())
            self.assertEqual(clear.unmodeled_entity_ids, ())
            action = Action(builder.world, 0, 1, "strike object", actor.id,
                            target.id, weapon.id, id=f"native-object-batch-{index}")
            action.object_motion = "thrust"
            action.reach = effective_melee_reach_meters(actor.current, weapon.current)
            action.end_time = math.ceil(weapon.Tt())
            actions.append(action)
        builder.enable()
        for action in actions:
            builder.schedule(action)
        pending = export_save(builder.encounter)
        builder.step(actions[0].end_time)
        receipt = builder.encounter.inspect_committed(int(builder.encounter.time))
        outcomes = [receipt.action(action.id).facts.outcome for action in actions]
        damage = [[effect.amount for effect in receipt.action(action.id).facts.effects
                   if getattr(effect, "component", None) == "object"]
                  for action in actions]
        self.assertEqual(outcomes, ["normal", "normal"])
        self.assertEqual([sum(row) for row in damage], [5, 6])
        self.assertEqual(target.hit_points(), -8)
        expected = {
            "time": builder.encounter.time,
            "object_id": target.id,
            "action_ids": [action.id for action in actions],
            "outcomes": outcomes,
            "damage": damage,
            "target_hp": target.hit_points(),
            "parent": target.parent_container_id,
            "position": target.get_position().as_tuple(),
            "rng": builder.rng.state,
            "history": hashlib.sha256(encode(capture(builder.encounter))).hexdigest(),
        }
        child = r'''import hashlib,json,sys
import native_history
from native_persistence import load_save
world,enc,rng=load_save(open(sys.argv[1],'rb').read())
object_id=sys.argv[2];action_ids=sys.argv[3:5];target=world.get_object_by_id(object_id)
actions=[]
for action_id in action_ids:
 choice=enc.choice_for_action(action_id);assert choice.state=='accepted'
 actions.append(next(m.action for m in enc._choice_book._choices[choice.id].members
                     if m.action.id==action_id))
enc.step(int(actions[0].end_time-enc.time))
receipt=enc.inspect_committed(int(enc.time))
print(json.dumps({'time':enc.time,'object_id':target.id,
 'action_ids':[action.id for action in actions],
 'outcomes':[receipt.action(action.id).facts.outcome for action in actions],
 'damage':[[effect.amount for effect in receipt.action(action.id).facts.effects
            if getattr(effect,'component',None)=='object'] for action in actions],
 'target_hp':target.hit_points(),'parent':target.parent_container_id,
 'position':target.get_position().as_tuple(),'rng':rng.state,
 'history':hashlib.sha256(native_history.encode(native_history.capture(enc))).hexdigest()},
 sort_keys=True))'''
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "native-simultaneous-object-strikes.json"
            path.write_bytes(pending)
            result = subprocess.run(
                [sys.executable, "-B", "-c", child, str(path), target.id,
                 actions[0].id, actions[1].id], cwd=directory,
                env={**os.environ,
                     "PYTHONPATH": f"{ROOT / 'src'}:{ROOT / 'examples'}"},
                text=True, capture_output=True, check=False, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), json.loads(json.dumps(expected)))

    def test_headless_subdual_burden_and_continuation_restore_exactly(self):
        from activities import DelayAction, declare_subdue

        builder = NativeScenarioBuilder(
            "native-subdual", Library(config_dir=str(ROOT / "src/config")),
            seed=5, encounter_id="native-subdual-encounter")
        actor = builder.add_being("Human", "Subduer", position=(0, 0, 0),
                                  radius=.25, hit_points=100)
        target = builder.add_being("Human", "Subdual target", position=(.2, 0, 0),
                                   radius=.25, hit_points=100)
        club = builder.make_weapon(actor.id, "Club", "Subdual Club",
                                   hand="right hand")
        actor.set_weapon_skill_level(builder.world.get_skill_dictionary(), "Club", 3)
        builder.mark_aware(actor.id, target.id)
        builder.mark_aware(target.id, actor.id)
        builder.encounter.difficulty_class = 1
        builder.enable()
        subdue = declare_subdue(builder.world, builder.encounter, actor.id, target.id,
                                club.id, motion="swing", strategy=Strategy(),
                                id="native-subdue-action")
        builder.schedule(subdue)
        initial = export_save(builder.encounter)
        builder.step(int(subdue.end_time - subdue.start_time))
        receipt = builder.encounter.inspect_committed(int(builder.encounter.time))
        subdual = next(effect for effect in receipt.action(subdue.id).facts.effects
                       if type(effect).__name__ == "SubdualEffect")
        body_damage = next(effect.amount for effect in receipt.action(subdue.id).facts.effects
                           if getattr(effect, "component", None) == "body")
        self.assertEqual(receipt.action(subdue.id).facts.outcome, "critical")
        self.assertEqual((body_damage, subdual.amount, target.get_hit_points()), (4, 9, 96))
        self.assertEqual(target.current.states.states["subdual_damage"], 9)
        self.assertEqual(target.current.states.states["subdual_recovery_anchor"],
                         builder.encounter.time)
        self.assertFalse(target.current.states.states["subdual_unconscious"])
        expected_subdue = {
            "time": builder.encounter.time,
            "action_id": subdue.id,
            "outcome": receipt.action(subdue.id).facts.outcome,
            "body_damage": body_damage,
            "subdual_amount": subdual.amount,
            "hp": target.get_hit_points(),
            "states": dict(target.current.states.states),
            "rng": builder.rng.state,
            "history": hashlib.sha256(encode(capture(builder.encounter))).hexdigest(),
        }
        initial_child = r'''import hashlib,json,sys
import native_history
from native_persistence import load_save
world,enc,rng=load_save(open(sys.argv[1],'rb').read())
actor=world.get_object_by_id(sys.argv[2]);target=world.get_object_by_id(sys.argv[3])
action_id=sys.argv[4];choice=enc.choice_for_action(action_id)
assert choice.state=='accepted'
action=next(m.action for m in enc._choice_book._choices[choice.id].members
            if m.action.id==action_id)
enc.step(int(action.end_time-enc.time))
receipt=enc.inspect_committed(int(enc.time)).action(action.id)
subdual=next(effect for effect in receipt.facts.effects if type(effect).__name__=='SubdualEffect')
body_damage=next(effect.amount for effect in receipt.facts.effects
                 if getattr(effect,'component',None)=='body')
print(json.dumps({'time':enc.time,'action_id':action.id,'outcome':receipt.facts.outcome,
 'body_damage':body_damage,'subdual_amount':subdual.amount,
 'hp':target.get_hit_points(),'states':dict(target.current.states.states),
 'rng':rng.state,'history':hashlib.sha256(native_history.encode(
  native_history.capture(enc))).hexdigest()},sort_keys=True))'''
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "native-subdual-initial.json"
            path.write_bytes(initial)
            restored = subprocess.run(
                [sys.executable, "-B", "-c", initial_child, str(path), actor.id,
                 target.id, subdue.id], cwd=directory,
                env={**os.environ,
                     "PYTHONPATH": f"{ROOT / 'src'}:{ROOT / 'examples'}"},
                text=True, capture_output=True, check=False, timeout=60)
        self.assertEqual(restored.returncode, 0, restored.stderr)
        self.assertEqual(json.loads(restored.stdout),
                         json.loads(json.dumps(expected_subdue)))

        delay = DelayAction(builder.encounter, target.id, defense=0,
                            start_time=builder.encounter.time,
                            id="native-subdual-delay")
        builder.schedule(delay)
        pending = export_save(builder.encounter)
        builder.step(1)
        expected_continue = {
            "time": builder.encounter.time,
            "delay_id": delay.id,
            "hp": target.get_hit_points(),
            "states": dict(target.current.states.states),
            "rng": builder.rng.state,
            "history": hashlib.sha256(encode(capture(builder.encounter))).hexdigest(),
        }
        continuation_child = r'''import hashlib,json,sys
import native_history
from native_persistence import load_save
world,enc,rng=load_save(open(sys.argv[1],'rb').read())
target=world.get_object_by_id(sys.argv[2]);action_id=sys.argv[3]
choice=enc.choice_for_action(action_id);assert choice.state=='accepted'
action=next(m.action for m in enc._choice_book._choices[choice.id].members
            if m.action.id==action_id)
enc.step(1)
print(json.dumps({'time':enc.time,'delay_id':action.id,
 'hp':target.get_hit_points(),'states':dict(target.current.states.states),
 'rng':rng.state,'history':hashlib.sha256(native_history.encode(
  native_history.capture(enc))).hexdigest()},sort_keys=True))'''
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "native-subdual-continuation.json"
            path.write_bytes(pending)
            continued = subprocess.run(
                [sys.executable, "-B", "-c", continuation_child, str(path),
                 target.id, delay.id], cwd=directory,
                env={**os.environ,
                     "PYTHONPATH": f"{ROOT / 'src'}:{ROOT / 'examples'}"},
                text=True, capture_output=True, check=False, timeout=60)
        self.assertEqual(continued.returncode, 0, continued.stderr)
        self.assertEqual(json.loads(continued.stdout),
                         json.loads(json.dumps(expected_continue)))

    def test_headless_feint_and_one_followup_continue_with_original_action_identity(self):
        builder = NativeScenarioBuilder(
            "native-feint", Library(config_dir=str(ROOT / "src/config")),
            seed=3, encounter_id="native-feint-encounter")
        actor = builder.add_being("Human", "Feinting Being", position=(0, 0, 0),
                                  radius=.25, hit_points=100)
        target = builder.add_being("Human", "Feint Target", position=(.2, 0, 0),
                                   radius=.25, hit_points=100)
        weapon = builder.make_weapon(actor.id, "Dagger", "Feint Dagger",
                                     hand="right hand")
        actor.current.skills.weapon_skills["Dagger"] = 2
        builder.mark_aware(actor.id, target.id)
        builder.mark_aware(target.id, actor.id)
        builder.enable()
        feint = Action(builder.world, 0, 1, "feint", actor.id, target.id, weapon.id,
                       id="native-feint-action")
        feint.feint_motion = "thrust"
        feint.reach = effective_melee_reach_meters(actor.current, weapon.current)
        feint.end_time = math.ceil(weapon.Tt() / 2)
        builder.schedule(feint)
        builder.step(feint.end_time)
        committed_feint = builder.encounter.inspect_committed(
            int(builder.encounter.time)).action(feint.id)
        self.assertEqual(committed_feint.facts.outcome, "success")
        self.assertEqual(committed_feint.facts.effects, ())
        self.assertEqual(target.get_hit_points(), 100)

        strike = MeleeStrike(builder.encounter, actor.id, target.id, weapon.id,
                             motion="thrust", reach=2)
        strike.feint_source_action_id = feint.id
        builder.schedule(strike)
        pending = export_save(builder.encounter)
        builder.step(int(strike.end_time - builder.encounter.time))
        receipt = builder.encounter.inspect_committed(
            int(builder.encounter.time)).action(strike.id)
        self.assertEqual(strike.feint_source_action_id, feint.id)
        self.assertEqual(receipt.facts.outcome, "normal")
        self.assertTrue(any(getattr(effect, "component", None) == "body"
                            for effect in receipt.facts.effects))
        expected = {
            "time": builder.encounter.time,
            "feint_id": feint.id,
            "strike_id": strike.id,
            "source_id": strike.feint_source_action_id,
            "outcome": receipt.facts.outcome,
            "effects": [type(effect).__name__ for effect in receipt.facts.effects],
            "target_hp": target.get_hit_points(),
            "rng": builder.rng.state,
            "history": hashlib.sha256(encode(capture(builder.encounter))).hexdigest(),
        }
        child = r'''import hashlib,json,sys
import native_history
from native_persistence import load_save
world,enc,rng=load_save(open(sys.argv[1],'rb').read())
target=world.get_object_by_id(sys.argv[2]);feint_id,strike_id=sys.argv[3:]
feint=world.get_event_by_id(feint_id);assert feint is not None
choice=enc.choice_for_action(strike_id);assert choice.state=='accepted'
strike=next(member.action for member in enc._choice_book._choices[choice.id].members
            if member.action.id==strike_id)
assert strike.feint_source_action_id==feint.id and feint.resolution.outcome=='success'
enc.step(int(strike.end_time-enc.time))
receipt=enc.inspect_committed(int(enc.time)).action(strike.id)
print(json.dumps({'time':enc.time,'feint_id':feint.id,'strike_id':strike.id,
 'source_id':strike.feint_source_action_id,'outcome':receipt.facts.outcome,
 'effects':[type(effect).__name__ for effect in receipt.facts.effects],
 'target_hp':target.get_hit_points(),'rng':rng.state,
 'history':hashlib.sha256(native_history.encode(native_history.capture(enc))).hexdigest()},
 sort_keys=True))'''
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "native-feint-followup.json"
            path.write_bytes(pending)
            result = subprocess.run(
                [sys.executable, "-B", "-c", child, str(path), target.id,
                 feint.id, strike.id], cwd=directory,
                env={**os.environ,
                     "PYTHONPATH": f"{ROOT / 'src'}:{ROOT / 'examples'}"},
                text=True, capture_output=True, check=False, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), json.loads(json.dumps(expected)))


if __name__ == "__main__":
    unittest.main()
