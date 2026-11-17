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
from native_history import NativeHistoryQuery, _plain, capture, decode, encode
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
        history_query = NativeHistoryQuery(decode(encode(capture(builder.encounter))))
        historical_actions = history_query.committed_actions_at(
            int(builder.encounter.time))
        self.assertEqual(historical_actions["actions"], _plain(receipt.actions))
        self.assertEqual(historical_actions["effects"], _plain(receipt.effects))
        boundary_receipt = next(row for row in receipt.timeline
                                if row.boundary == int(builder.encounter.time))
        self.assertEqual(historical_actions["action_ids"],
                         [action.id for action in actions])
        self.assertEqual(historical_actions["effect_ids"],
                         [_plain(identity) for identity in boundary_receipt.effect_ids])
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
        feint_history = NativeHistoryQuery(
            decode(encode(capture(builder.encounter))))
        historical_feint = feint_history.committed_actions_at(
            int(builder.encounter.time))
        self.assertEqual(historical_feint["actions"],
                         _plain(builder.encounter.inspect_committed(
                             int(builder.encounter.time)).actions))
        self.assertEqual(historical_feint["effects"], _plain(
            builder.encounter.inspect_committed(
                int(builder.encounter.time)).effects))
        self.assertEqual(historical_feint["action_ids"], [feint.id])
        feint_receipt = builder.encounter.inspect_committed(
            int(builder.encounter.time))
        feint_boundary = next(row for row in feint_receipt.timeline
                              if row.boundary == int(builder.encounter.time))
        self.assertEqual(historical_feint["effect_ids"], [
            _plain(identity) for identity in feint_boundary.effect_ids])

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

    def test_headless_touch_grab_trip_history_continues_after_fresh_process_load(self):
        builder = NativeScenarioBuilder(
            "native-touch-trip", Library(config_dir=str(ROOT / "src/config")),
            seed=7, encounter_id="native-touch-trip-encounter")
        actor = builder.add_being("Human", "Contact Actor", position=(0, 0, 0),
                                  radius=.25, hit_points=100)
        target = builder.add_being("Human", "Contact Target", position=(.2, 0, 0),
                                   radius=.25, hit_points=100)
        actor.set_posture("standing")
        target.set_posture("standing")
        actor.size_category = target.size_category = "medium"
        builder.mark_aware(actor.id, target.id)
        builder.mark_aware(target.id, actor.id)
        builder.enable()
        touch = Action(builder.world, 0, 1, "touch", actor.id, target.id, None,
                       id="native-touch-trip-touch")
        touch.end_time = 1
        builder.schedule(touch)
        builder.step(1)
        touch_receipt = builder.encounter.inspect_committed(1).action(touch.id)
        self.assertEqual(touch_receipt.facts.outcome, "touched")
        self.assertEqual(target.get_posture(), "standing")
        grab = Action(builder.world, 1, 2, "grab", actor.id, target.id, None,
                      id="native-touch-trip-grab")
        grab.touch_action_id = touch.id
        grab.grab_hand = "left hand"
        grab.end_time = 2
        builder.schedule(grab)
        builder.step(1)
        grab_receipt = builder.encounter.inspect_committed(2).action(grab.id)
        self.assertEqual(grab_receipt.facts.outcome, "success")
        trip = Action(builder.world, 2, 4, "trip", actor.id, target.id, None,
                      id="native-touch-trip-trip")
        trip.trip_source_action_id = grab.id
        trip.trip_defender_ability = "DEX"
        trip.end_time = 4
        builder.schedule(trip)
        pending = export_save(builder.encounter)

        builder.step(2)
        trip_receipt = builder.encounter.inspect_committed(4).action(trip.id)
        self.assertEqual(trip_receipt.facts.outcome, "success")
        self.assertEqual(target.get_posture(), "lying")
        expected = {
            "time": builder.encounter.time,
            "touch_id": touch.id,
            "touch_outcome": touch_receipt.facts.outcome,
            "grab_id": grab.id,
            "grab_outcome": grab_receipt.facts.outcome,
            "trip_id": trip.id,
            "trip_source": trip.trip_source_action_id,
            "trip_outcome": trip_receipt.facts.outcome,
            "posture": target.get_posture(),
            "rng": builder.rng.state,
            "history": hashlib.sha256(encode(capture(builder.encounter))).hexdigest(),
        }
        child = r'''import hashlib,json,sys
import native_history
from native_persistence import load_save
world,enc,rng=load_save(open(sys.argv[1],'rb').read())
touch_id,grab_id,trip_id,target_id=sys.argv[2:]
choice=enc.choice_for_action(trip_id)
assert choice.state=='accepted'
trip=next(m.action for m in enc._choice_book._choices[choice.id].members
          if m.action.id==trip_id)
assert trip.trip_source_action_id==grab_id
target=world.get_object_by_id(target_id)
assert enc.inspect_committed(1).action(touch_id).facts.outcome=='touched'
assert enc.inspect_committed(2).action(grab_id).facts.outcome=='success'
assert trip.trip_source_action_id==grab_id
assert target.get_posture()=='standing'
enc.step(2);receipt=enc.inspect_committed(4).action(trip_id)
assert receipt.facts.outcome=='success' and target.get_posture()=='lying'
print(json.dumps({'time':enc.time,'touch_id':touch_id,
 'touch_outcome':enc.inspect_committed(1).action(touch_id).facts.outcome,
 'grab_id':grab_id,'grab_outcome':enc.inspect_committed(2).action(grab_id).facts.outcome,
 'trip_id':trip.id,'trip_source':trip.trip_source_action_id,
 'trip_outcome':receipt.facts.outcome,'posture':target.get_posture(),
 'rng':rng.state,'history':hashlib.sha256(native_history.encode(
 native_history.capture(enc))).hexdigest()},sort_keys=True))'''
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "native-touch-trip.json"
            path.write_bytes(pending)
            result = subprocess.run(
                [sys.executable, "-B", "-c", child, str(path), touch.id,
                 grab.id, trip.id, target.id], cwd=directory,
                env={**os.environ,
                     "PYTHONPATH": f"{ROOT / 'src'}:{ROOT / 'examples'}"},
                text=True, capture_output=True, check=False, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), json.loads(json.dumps(expected)))

    def test_headless_grapple_control_takedown_and_history_continue_after_restore(self):
        """A committed Grapple control and pending Takedown restore natively."""
        from physical_contact import active_contact_state

        builder = NativeScenarioBuilder(
            "native-grapple-control", Library(config_dir=str(ROOT / "src/config")),
            seed=5, encounter_id="native-grapple-control-encounter")
        actor = builder.add_being("Human", "Grappler", position=(0, 0, 0),
                                  radius=.25, hit_points=100)
        target = builder.add_being("Human", "Target", position=(.2, 0, 0),
                                   radius=.25, hit_points=100)
        actor.set_posture("standing")
        target.set_posture("standing")
        actor.size_category = target.size_category = "medium"
        actor.current.skills.skills["improved grapple"] = 10
        target.current.skills.skills["improved grapple"] = 0
        builder.mark_aware(actor.id, target.id)
        builder.mark_aware(target.id, actor.id)
        builder.enable()

        touch = Action(builder.world, 0, 1, "touch", actor.id, target.id, None,
                       id="native-grapple-touch")
        touch.end_time = 1
        builder.schedule(touch)
        builder.step(1)
        self.assertEqual(builder.encounter.inspect_committed(1).action(
            touch.id).facts.outcome, "touched")
        grab = Action(builder.world, 1, 2, "grab", actor.id, target.id, None,
                      id="native-grapple-grab")
        grab.touch_action_id = touch.id
        grab.grab_hand = "left hand"
        grab.end_time = 2
        builder.schedule(grab)
        builder.step(1)
        self.assertEqual(builder.encounter.inspect_committed(2).action(
            grab.id).facts.outcome, "success")
        grapple = Action(builder.world, 2, 8, "grapple", actor.id, target.id,
                          None, id="native-grapple-control")
        grapple.grip_id = grab.id
        grapple.end_time = 8
        builder.schedule(grapple)
        builder.step(6)
        grapple_receipt = builder.encounter.inspect_committed(8).action(grapple.id)
        self.assertEqual(grapple_receipt.facts.outcome, "success")
        self.assertEqual(len(active_contact_state(builder.encounter)[0]), 1)
        self.assertEqual(tuple(row[0] for row in active_contact_state(
            builder.encounter)[1]), (grapple.id,))

        takedown = Action(builder.world, 8, 14, "takedown", actor.id, target.id,
                          None, id="native-grapple-takedown")
        takedown.grapple_id = grapple.id
        takedown.grapple_position = "prone"
        takedown.end_time = 14
        builder.schedule(takedown)
        pending = export_save(builder.encounter)
        builder.step(6)
        takedown_receipt = builder.encounter.inspect_committed(14).action(takedown.id)
        self.assertEqual(takedown_receipt.facts.outcome, "success")
        self.assertEqual(target.get_posture(), "lying")
        controls = active_contact_state(builder.encounter)[1]
        self.assertEqual(controls[0][0], grapple.id)
        expected = {
            "world_id": builder.world.id,
            "encounter_id": builder.encounter.id,
            "being_ids": [actor.id, target.id],
            "touch_id": touch.id,
            "grab_id": grab.id,
            "grapple_id": grapple.id,
            "takedown_id": takedown.id,
            "takedown_source": takedown.grapple_id,
            "time": builder.encounter.time,
            "outcome": takedown_receipt.facts.outcome,
            "posture": target.get_posture(),
            "grips": active_contact_state(builder.encounter)[0],
            "controls": controls,
            "rng": builder.rng.state,
            "history": hashlib.sha256(encode(capture(builder.encounter))).hexdigest(),
            "history_rows": [hashlib.sha256(json.dumps(row, sort_keys=True,
                separators=(",", ":")).encode()).hexdigest()
                for row in capture(builder.encounter)["boundaries"]],
            "history_last_row": capture(builder.encounter)["boundaries"][-1],
        }
        child = r'''import hashlib,json,sys
import native_history
from native_persistence import load_save
from physical_contact import active_contact_state
world,enc,rng=load_save(open(sys.argv[1],'rb').read())
touch_id,grab_id,grapple_id,takedown_id,actor_id,target_id=sys.argv[2:]
assert enc.time==8 and enc.progression_mode=='transactional'
assert enc.inspect_committed(1).action(touch_id).facts.outcome=='touched'
assert enc.inspect_committed(2).action(grab_id).facts.outcome=='success'
assert enc.inspect_committed(8).action(grapple_id).facts.outcome=='success'
choice=enc.choice_for_action(takedown_id);assert choice.state=='accepted'
takedown=next(m.action for m in enc._choice_book._choices[choice.id].members
              if m.action.id==takedown_id)
assert takedown.grapple_id==grapple_id and takedown.grapple_position=='prone'
target=world.get_object_by_id(target_id)
assert target.get_posture()=='standing'
assert tuple(row[0] for row in active_contact_state(enc)[1])==(grapple_id,)
enc.step(6);receipt=enc.inspect_committed(14).action(takedown_id)
assert receipt.facts.outcome=='success' and target.get_posture()=='lying'
history_log=native_history.capture(enc)
print(json.dumps({'world_id':world.id,'encounter_id':enc.id,
 'being_ids':[actor_id,target_id],'touch_id':touch_id,'grab_id':grab_id,
 'grapple_id':grapple_id,'takedown_id':takedown.id,
 'takedown_source':takedown.grapple_id,'time':enc.time,
 'outcome':receipt.facts.outcome,'posture':target.get_posture(),
 'grips':active_contact_state(enc)[0],'controls':active_contact_state(enc)[1],
 'rng':rng.state,'history':hashlib.sha256(native_history.encode(
 history_log)).hexdigest(),
 'history_rows':[hashlib.sha256(json.dumps(row,sort_keys=True,
 separators=(',',':')).encode()).hexdigest()
                 for row in history_log['boundaries']],
 'history_last_row':history_log['boundaries'][-1]},sort_keys=True))'''
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "native-grapple-control.json"
            path.write_bytes(pending)
            result = subprocess.run(
                [sys.executable, "-B", "-c", child, str(path), touch.id, grab.id,
                 grapple.id, takedown.id, actor.id, target.id], cwd=directory,
                env={**os.environ,
                     "PYTHONPATH": f"{ROOT / 'src'}:{ROOT / 'examples'}"},
                text=True, capture_output=True, check=False, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        actual = json.loads(result.stdout)
        expected_json = json.loads(json.dumps(expected))
        def leaf_differences(left, right, path=()):
            if isinstance(left, dict) and isinstance(right, dict):
                for key in sorted(set(left) | set(right)):
                    yield from leaf_differences(left.get(key), right.get(key), path + (key,))
            elif isinstance(left, list) and isinstance(right, list):
                for index, (left_item, right_item) in enumerate(zip(left, right)):
                    yield from leaf_differences(left_item, right_item, path + (index,))
                if len(left) != len(right):
                    yield path + ("length",), len(left), len(right)
            elif left != right:
                yield path, left, right

        differing = list(leaf_differences(actual, expected_json))
        self.assertEqual(differing, [], repr(differing[:25]))

    def test_headless_failed_grapple_escape_retains_control_after_restore(self):
        """A failed Escape maintains the exact control and advances its check."""
        from physical_contact import active_contact_state

        builder = NativeScenarioBuilder(
            "native-grapple-escape", Library(config_dir=str(ROOT / "src/config")),
            seed=5, encounter_id="native-grapple-escape-encounter")
        holder = builder.add_being("Human", "Grapple Holder", position=(0, 0, 0),
                                   radius=.25, hit_points=100)
        captive = builder.add_being("Human", "Grapple Captive", position=(.2, 0, 0),
                                    radius=.25, hit_points=100)
        holder.set_posture("standing")
        captive.set_posture("standing")
        holder.size_category = captive.size_category = "medium"
        holder.current.skills.skills["improved grapple"] = 10
        captive.current.skills.skills["improved grapple"] = 0
        builder.mark_aware(holder.id, captive.id)
        builder.mark_aware(captive.id, holder.id)
        builder.enable()

        touch = Action(builder.world, 0, 1, "touch", holder.id, captive.id, None,
                       id="native-grapple-escape-touch")
        builder.schedule(touch)
        builder.step(1)
        self.assertEqual(builder.encounter.inspect_committed(1).action(
            touch.id).facts.outcome, "touched")
        grab = Action(builder.world, 1, 2, "grab", holder.id, captive.id, None,
                      id="native-grapple-escape-grab")
        grab.touch_action_id = touch.id
        grab.grab_hand = "left hand"
        builder.schedule(grab)
        builder.step(1)
        self.assertEqual(builder.encounter.inspect_committed(2).action(
            grab.id).facts.outcome, "success")
        grapple = Action(builder.world, 2, 8, "grapple", holder.id, captive.id,
                          None, id="native-grapple-escape-control")
        grapple.grip_id = grab.id
        grapple.end_time = 8
        builder.schedule(grapple)
        builder.step(6)
        self.assertEqual(builder.encounter.inspect_committed(8).action(
            grapple.id).facts.outcome, "success")
        takedown = Action(builder.world, 8, 14, "takedown", holder.id, captive.id,
                          None, id="native-grapple-escape-takedown")
        takedown.grapple_id = grapple.id
        takedown.grapple_position = "prone"
        takedown.end_time = 14
        builder.schedule(takedown)
        builder.step(6)
        self.assertEqual(builder.encounter.inspect_committed(14).action(
            takedown.id).facts.outcome, "success")

        escape = Action(builder.world, 14, 20, "grapple escape", captive.id,
                        holder.id, None, id="native-grapple-escape-action")
        escape.grapple_id = grapple.id
        escape.end_time = 20
        builder.schedule(escape)
        pending = export_save(builder.encounter)
        builder.step(6)
        receipt = builder.encounter.inspect_committed(20).action(escape.id)
        self.assertEqual(receipt.facts.outcome, "failed")
        grips, controls = active_contact_state(builder.encounter)
        self.assertEqual(controls[0], (grapple.id, holder.id, captive.id, None,
                                       8, 26, "advantaged_takedown_top"))
        expected = {
            "world_id": builder.world.id,
            "encounter_id": builder.encounter.id,
            "being_ids": [holder.id, captive.id],
            "action_ids": [touch.id, grab.id, grapple.id, takedown.id, escape.id],
            "outcome": receipt.facts.outcome,
            "posture": captive.get_posture(),
            "grips": grips,
            "controls": controls,
            "rng": builder.rng.state,
            "history": hashlib.sha256(encode(capture(builder.encounter))).hexdigest(),
            "history_rows": [hashlib.sha256(json.dumps(row, sort_keys=True,
                separators=(",", ":")).encode()).hexdigest()
                for row in capture(builder.encounter)["boundaries"]],
        }
        child = r'''import hashlib,json,sys
import native_history
from native_persistence import load_save
from physical_contact import active_contact_state
world,enc,rng=load_save(open(sys.argv[1],'rb').read())
touch_id,grab_id,grapple_id,takedown_id,escape_id,holder_id,captive_id=sys.argv[2:]
assert enc.time==14 and enc.progression_mode=='transactional'
assert enc.inspect_committed(1).action(touch_id).facts.outcome=='touched'
assert enc.inspect_committed(2).action(grab_id).facts.outcome=='success'
assert enc.inspect_committed(8).action(grapple_id).facts.outcome=='success'
assert enc.inspect_committed(14).action(takedown_id).facts.outcome=='success'
choice=enc.choice_for_action(escape_id);assert choice.state=='accepted'
escape=next(m.action for m in enc._choice_book._choices[choice.id].members
            if m.action.id==escape_id)
assert escape.actor_id==captive_id and escape.target_id==holder_id
assert escape.grapple_id==grapple_id
enc.step(6);receipt=enc.inspect_committed(20).action(escape_id)
assert receipt.facts.outcome=='failed'
grips,controls=active_contact_state(enc)
assert controls[0]==(grapple_id,holder_id,captive_id,None,8,26,'advantaged_takedown_top')
captive=world.get_object_by_id(captive_id)
assert captive.get_posture()=='lying'
history_log=native_history.capture(enc)
print(json.dumps({'world_id':world.id,'encounter_id':enc.id,
 'being_ids':[holder_id,captive_id],
 'action_ids':[touch_id,grab_id,grapple_id,takedown_id,escape_id],
 'outcome':receipt.facts.outcome,'posture':captive.get_posture(),
 'grips':grips,'controls':controls,'rng':rng.state,
 'history':hashlib.sha256(native_history.encode(history_log)).hexdigest(),
 'history_rows':[hashlib.sha256(json.dumps(row,sort_keys=True,
 separators=(',',':')).encode()).hexdigest()
                 for row in history_log['boundaries']]},sort_keys=True))'''
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "native-grapple-escape.json"
            path.write_bytes(pending)
            result = subprocess.run(
                [sys.executable, "-B", "-c", child, str(path), touch.id, grab.id,
                 grapple.id, takedown.id, escape.id, holder.id, captive.id],
                cwd=directory,
                env={**os.environ,
                     "PYTHONPATH": f"{ROOT / 'src'}:{ROOT / 'examples'}"},
                text=True, capture_output=True, check=False, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), json.loads(json.dumps(expected)))

    def test_headless_successful_grapple_escape_releases_control_after_restore(self):
        """A successful standing Escape releases only its identified control."""
        from physical_contact import active_contact_state

        builder = NativeScenarioBuilder(
            "native-grapple-escape-success",
            Library(config_dir=str(ROOT / "src/config")), seed=5,
            encounter_id="native-grapple-escape-success-encounter")
        holder = builder.add_being("Human", "Grapple Holder", position=(0, 0, 0),
                                   radius=.25, hit_points=100)
        captive = builder.add_being("Human", "Grapple Captive", position=(.2, 0, 0),
                                    radius=.25, hit_points=100)
        for being in (holder, captive):
            being.set_posture("standing")
            being.size_category = "medium"
        holder.current.skills.skills["improved grapple"] = 10
        captive.current.skills.skills["improved grapple"] = 0
        captive.current.skills.skills["escape artist"] = 20
        builder.mark_aware(holder.id, captive.id)
        builder.mark_aware(captive.id, holder.id)
        builder.enable()

        touch = Action(builder.world, 0, 1, "touch", holder.id, captive.id, None,
                       id="native-grapple-success-touch")
        builder.schedule(touch)
        builder.step(1)
        self.assertEqual(builder.encounter.inspect_committed(1).action(
            touch.id).facts.outcome, "touched")
        grab = Action(builder.world, 1, 2, "grab", holder.id, captive.id, None,
                      id="native-grapple-success-grab")
        grab.touch_action_id = touch.id
        grab.grab_hand = "left hand"
        builder.schedule(grab)
        builder.step(1)
        self.assertEqual(builder.encounter.inspect_committed(2).action(
            grab.id).facts.outcome, "success")
        grapple = Action(builder.world, 2, 8, "grapple", holder.id, captive.id,
                          None, id="native-grapple-success-control")
        grapple.grip_id = grab.id
        grapple.end_time = 8
        builder.schedule(grapple)
        builder.step(6)
        self.assertEqual(builder.encounter.inspect_committed(8).action(
            grapple.id).facts.outcome, "success")
        escape = Action(builder.world, 8, 14, "grapple escape", captive.id,
                        holder.id, None, id="native-grapple-success-escape")
        escape.grapple_id = grapple.id
        escape.end_time = 14
        builder.schedule(escape)
        pending = export_save(builder.encounter)
        builder.step(6)
        receipt = builder.encounter.inspect_committed(14).action(escape.id)
        self.assertEqual(receipt.facts.outcome, "success")
        grips, controls = active_contact_state(builder.encounter)
        self.assertEqual(controls, ())
        expected = {
            "world_id": builder.world.id,
            "encounter_id": builder.encounter.id,
            "being_ids": [holder.id, captive.id],
            "action_ids": [touch.id, grab.id, grapple.id, escape.id],
            "outcome": receipt.facts.outcome,
            "posture": captive.get_posture(),
            "grips": grips,
            "controls": controls,
            "rng": builder.rng.state,
            "history": hashlib.sha256(encode(capture(builder.encounter))).hexdigest(),
            "history_rows": [hashlib.sha256(json.dumps(row, sort_keys=True,
                separators=(",", ":")).encode()).hexdigest()
                for row in capture(builder.encounter)["boundaries"]],
        }
        child = r'''import hashlib,json,sys
import native_history
from native_persistence import load_save
from physical_contact import active_contact_state
world,enc,rng=load_save(open(sys.argv[1],'rb').read())
touch_id,grab_id,grapple_id,escape_id,holder_id,captive_id=sys.argv[2:]
assert enc.time==8 and enc.progression_mode=='transactional'
assert enc.inspect_committed(1).action(touch_id).facts.outcome=='touched'
assert enc.inspect_committed(2).action(grab_id).facts.outcome=='success'
assert enc.inspect_committed(8).action(grapple_id).facts.outcome=='success'
choice=enc.choice_for_action(escape_id);assert choice.state=='accepted'
escape=next(m.action for m in enc._choice_book._choices[choice.id].members
            if m.action.id==escape_id)
assert escape.actor_id==captive_id and escape.target_id==holder_id
assert escape.grapple_id==grapple_id
enc.step(6);receipt=enc.inspect_committed(14).action(escape_id)
assert receipt.facts.outcome=='success'
grips,controls=active_contact_state(enc);assert controls==()
captive=world.get_object_by_id(captive_id)
history_log=native_history.capture(enc)
print(json.dumps({'world_id':world.id,'encounter_id':enc.id,
 'being_ids':[holder_id,captive_id],
 'action_ids':[touch_id,grab_id,grapple_id,escape_id],
 'outcome':receipt.facts.outcome,'posture':captive.get_posture(),
 'grips':grips,'controls':controls,'rng':rng.state,
 'history':hashlib.sha256(native_history.encode(history_log)).hexdigest(),
 'history_rows':[hashlib.sha256(json.dumps(row,sort_keys=True,
 separators=(',',':')).encode()).hexdigest()
                 for row in history_log['boundaries']]},sort_keys=True))'''
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "native-grapple-success.json"
            path.write_bytes(pending)
            result = subprocess.run(
                [sys.executable, "-B", "-c", child, str(path), touch.id, grab.id,
                 grapple.id, escape.id, holder.id, captive.id], cwd=directory,
                env={**os.environ,
                     "PYTHONPATH": f"{ROOT / 'src'}:{ROOT / 'examples'}"},
                text=True, capture_output=True, check=False, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), json.loads(json.dumps(expected)))

    def test_headless_charge_and_bull_rush_continue_after_restore_without_guessing_displacement(self):
        """Charge movement and its Bull Rush source survive native restore."""
        builder = NativeScenarioBuilder(
            "native-charge-rush", Library(config_dir=str(ROOT / "src/config")),
            seed=5, encounter_id="native-charge-rush-encounter")
        charger = builder.add_being("Human", "Charger", position=(0, 0, 0),
                                    radius=.25, hit_points=100)
        target = builder.add_being("Human", "Charge Target", position=(8.5, 0, 0),
                                   radius=.25, hit_points=100)
        charger.set_hex_facing(0)
        charger.set_ability("strength", 30)
        target.set_ability("strength", 10)
        charger.size_category = target.size_category = "medium"
        charger.set_weapon_skill_level(
            builder.world.get_weapon_dictionary(), "Dagger", 100)
        builder.mark_aware(charger.id, target.id)
        builder.mark_aware(target.id, charger.id)
        weapon = builder.make_weapon(charger.id, "Dagger", "Charge Dagger",
                                     hand="right hand")
        builder.enable()

        charge = MeleeStrike(
            builder.encounter, charger.id, target.id, weapon.id, motion="thrust",
            reach=2, strategy=Strategy(timing=3), charge=True)
        builder.schedule(charge)
        builder.encounter.step(2, velocities={charger.id: (4.0, 0.0, 0.0)})
        charge_receipt = builder.encounter.inspect_committed(2).action(charge.id)
        self.assertEqual(charge_receipt.facts.outcome, "critical")
        self.assertEqual(charger.get_position(), CartesianPosition(8.0, 0.0, 0.0))
        self.assertEqual(target.get_position(), CartesianPosition(8.5, 0.0, 0.0))

        rush = Action(builder.world, 2, 3, "bull rush", charger.id, target.id,
                      None, id="native-charge-bull-rush")
        rush.charge_continuation_source_id = charge.id
        builder.schedule(rush)
        pending = export_save(builder.encounter)
        builder.step(1)
        rush_receipt = builder.encounter.inspect_committed(3).action(rush.id)
        self.assertEqual(rush_receipt.facts.outcome, "success_pending_displacement")
        self.assertEqual(target.get_position(), CartesianPosition(8.5, 0.0, 0.0))
        expected = {
            "world_id": builder.world.id,
            "encounter_id": builder.encounter.id,
            "being_ids": [charger.id, target.id],
            "weapon_id": weapon.id,
            "charge_id": charge.id,
            "rush_id": rush.id,
            "charge_outcome": charge_receipt.facts.outcome,
            "rush_outcome": rush_receipt.facts.outcome,
            "positions": [charger.get_position().as_tuple(),
                          target.get_position().as_tuple()],
            "hp": [charger.get_hit_points(), target.get_hit_points()],
            "rng": builder.rng.state,
            "history": hashlib.sha256(encode(capture(builder.encounter))).hexdigest(),
            "history_rows": [hashlib.sha256(json.dumps(row, sort_keys=True,
                separators=(",", ":")).encode()).hexdigest()
                for row in capture(builder.encounter)["boundaries"]],
        }
        child = r'''import hashlib,json,sys
import native_history
from native_persistence import load_save
world,enc,rng=load_save(open(sys.argv[1],'rb').read())
charger_id,target_id,weapon_id,charge_id,rush_id=sys.argv[2:]
assert enc.time==2 and enc.progression_mode=='transactional'
assert enc.inspect_committed(2).action(charge_id).facts.outcome=='critical'
choice=enc.choice_for_action(rush_id);assert choice.state=='accepted'
rush=next(m.action for m in enc._choice_book._choices[choice.id].members
          if m.action.id==rush_id)
assert rush.actor_id==charger_id and rush.target_id==target_id
assert rush.charge_continuation_source_id==charge_id
charger=world.get_object_by_id(charger_id);target=world.get_object_by_id(target_id)
assert charger.get_position().as_tuple()==(8.0,0.0,0.0)
assert target.get_position().as_tuple()==(8.5,0.0,0.0)
enc.step(1);receipt=enc.inspect_committed(3).action(rush_id)
assert receipt.facts.outcome=='success_pending_displacement'
assert target.get_position().as_tuple()==(8.5,0.0,0.0)
history_log=native_history.capture(enc)
print(json.dumps({'world_id':world.id,'encounter_id':enc.id,
 'being_ids':[charger_id,target_id],'weapon_id':weapon_id,
 'charge_id':charge_id,'rush_id':rush_id,
 'charge_outcome':enc.inspect_committed(2).action(charge_id).facts.outcome,
 'rush_outcome':receipt.facts.outcome,
 'positions':[charger.get_position().as_tuple(),target.get_position().as_tuple()],
 'hp':[charger.get_hit_points(),target.get_hit_points()],
 'rng':rng.state,
 'history':hashlib.sha256(native_history.encode(history_log)).hexdigest(),
 'history_rows':[hashlib.sha256(json.dumps(row,sort_keys=True,
 separators=(',',':')).encode()).hexdigest()
                 for row in history_log['boundaries']]},sort_keys=True))'''
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "native-charge-rush.json"
            path.write_bytes(pending)
            result = subprocess.run(
                [sys.executable, "-B", "-c", child, str(path), charger.id,
                 target.id, weapon.id, charge.id, rush.id], cwd=directory,
                env={**os.environ,
                     "PYTHONPATH": f"{ROOT / 'src'}:{ROOT / 'examples'}"},
                text=True, capture_output=True, check=False, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), json.loads(json.dumps(expected)))

    def test_headless_bull_rush_overrun_commits_adopted_prone_continuation_after_restore(self):
        """The lawful Bull Rush→Overrun continuation restores without Arena."""
        builder = NativeScenarioBuilder(
            "native-rush-overrun", Library(config_dir=str(ROOT / "src/config")),
            seed=3, encounter_id="native-rush-overrun-encounter")
        actor = builder.add_being("Human", "Rusher", position=(0, 0, 0),
                                  radius=.25, hit_points=100)
        target = builder.add_being("Human", "Overrun Target", position=(.2, 0, 0),
                                   radius=.25, hit_points=100)
        for being in (actor, target):
            being.set_posture("standing")
            being.size_category = "medium"
            being.set_ability("strength", 10)
            being.set_ability("dexterity", 10)
        actor.set_hex_facing(0)
        builder.mark_aware(actor.id, target.id)
        builder.mark_aware(target.id, actor.id)
        builder.enable()

        rush = Action(builder.world, 0, 1, "bull rush", actor.id, target.id,
                      None, id="native-rush-overrun-rush")
        builder.schedule(rush)
        builder.step(1)
        self.assertEqual(builder.encounter.inspect_committed(1).action(
            rush.id).facts.outcome, "success_pending_displacement")

        overrun = Action(builder.world, 1, 5, "overrun", actor.id, target.id,
                         None, id="native-rush-overrun-overrun")
        overrun.charge_continuation_source_id = rush.id
        prepared = builder.encounter.prepare_action(overrun)
        self.assertEqual(prepared.end_time, 7)
        builder.schedule(overrun)
        pending = export_save(builder.encounter)
        builder.step(6)
        receipt = builder.encounter.inspect_committed(7).action(overrun.id)
        self.assertEqual(receipt.facts.outcome, "success")
        self.assertEqual(target.get_posture(), "lying")
        self.assertEqual(target.get_position(), CartesianPosition(.2, 0, 0))
        expected = {
            "world_id": builder.world.id,
            "encounter_id": builder.encounter.id,
            "being_ids": [actor.id, target.id],
            "action_ids": [rush.id, overrun.id],
            "outcomes": [builder.encounter.inspect_committed(1).action(
                rush.id).facts.outcome, receipt.facts.outcome],
            "posture": target.get_posture(),
            "positions": [actor.get_position().as_tuple(),
                          target.get_position().as_tuple()],
            "rng": builder.rng.state,
            "history": hashlib.sha256(encode(capture(builder.encounter))).hexdigest(),
            "history_rows": [hashlib.sha256(json.dumps(row, sort_keys=True,
                separators=(",", ":")).encode()).hexdigest()
                for row in capture(builder.encounter)["boundaries"]],
        }
        child = r'''import hashlib,json,sys
import native_history
from native_persistence import load_save
world,enc,rng=load_save(open(sys.argv[1],'rb').read())
actor_id,target_id,rush_id,overrun_id=sys.argv[2:]
assert enc.time==1 and enc.progression_mode=='transactional'
assert enc.inspect_committed(1).action(rush_id).facts.outcome=='success_pending_displacement'
choice=enc.choice_for_action(overrun_id);assert choice.state=='accepted'
overrun=next(m.action for m in enc._choice_book._choices[choice.id].members
             if m.action.id==overrun_id)
assert overrun.charge_continuation_source_id==rush_id
assert overrun.start_time==1 and overrun.end_time==5
enc.step(6);receipt=enc.inspect_committed(7).action(overrun_id)
assert receipt.facts.outcome=='success'
actor=world.get_object_by_id(actor_id);target=world.get_object_by_id(target_id)
assert target.get_posture()=='lying'
assert target.get_position().as_tuple()==(.2,0.0,0.0)
history_log=native_history.capture(enc)
print(json.dumps({'world_id':world.id,'encounter_id':enc.id,
 'being_ids':[actor_id,target_id],'action_ids':[rush_id,overrun_id],
 'outcomes':[enc.inspect_committed(1).action(rush_id).facts.outcome,
             receipt.facts.outcome],
 'posture':target.get_posture(),
 'positions':[actor.get_position().as_tuple(),target.get_position().as_tuple()],
 'rng':rng.state,
 'history':hashlib.sha256(native_history.encode(history_log)).hexdigest(),
 'history_rows':[hashlib.sha256(json.dumps(row,sort_keys=True,
 separators=(',',':')).encode()).hexdigest()
                 for row in history_log['boundaries']]},sort_keys=True))'''
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "native-rush-overrun.json"
            path.write_bytes(pending)
            result = subprocess.run(
                [sys.executable, "-B", "-c", child, str(path), actor.id,
                 target.id, rush.id, overrun.id], cwd=directory,
                env={**os.environ,
                     "PYTHONPATH": f"{ROOT / 'src'}:{ROOT / 'examples'}"},
                text=True, capture_output=True, check=False, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), json.loads(json.dumps(expected)))

    def test_headless_failed_bull_rush_restores_the_resisted_contest_without_movement(self):
        """A real resisted contest failure remains failure after native Load."""
        builder = NativeScenarioBuilder(
            "native-bull-rush-failure",
            Library(config_dir=str(ROOT / "src/config")), seed=1,
            encounter_id="native-bull-rush-failure-encounter")
        actor = builder.add_being("Human", "Rusher", position=(0, 0, 0),
                                  radius=.25, hit_points=100)
        target = builder.add_being("Human", "Resisting Target", position=(.2, 0, 0),
                                   radius=.25, hit_points=100)
        for being in (actor, target):
            being.set_posture("standing")
            being.size_category = "medium"
            being.set_ability("strength", 10)
            being.set_ability("dexterity", 10)
        actor.set_hex_facing(0)
        builder.mark_aware(actor.id, target.id)
        builder.mark_aware(target.id, actor.id)
        builder.enable()

        rush = Action(builder.world, 0, 1, "bull rush", actor.id, target.id,
                      None, id="native-bull-rush-failed-action")
        builder.schedule(rush)
        pending = export_save(builder.encounter)
        before_positions = [actor.get_position().as_tuple(),
                            target.get_position().as_tuple()]
        builder.step(1)
        receipt = builder.encounter.inspect_committed(1).action(rush.id)
        self.assertEqual(receipt.facts.outcome, "failed")
        self.assertEqual([actor.get_position().as_tuple(), target.get_position().as_tuple()],
                         before_positions)
        expected = {
            "world_id": builder.world.id,
            "encounter_id": builder.encounter.id,
            "being_ids": [actor.id, target.id],
            "action_id": rush.id,
            "outcome": receipt.facts.outcome,
            "positions": [actor.get_position().as_tuple(),
                          target.get_position().as_tuple()],
            "hp": [actor.get_hit_points(), target.get_hit_points()],
            "rng": builder.rng.state,
            "history": hashlib.sha256(encode(capture(builder.encounter))).hexdigest(),
        }
        child = r'''import hashlib,json,sys
import native_history
from native_persistence import load_save
world,enc,rng=load_save(open(sys.argv[1],'rb').read())
actor_id,target_id,rush_id=sys.argv[2:]
assert enc.time==0 and enc.progression_mode=='transactional'
choice=enc.choice_for_action(rush_id);assert choice.state=='accepted'
rush=next(m.action for m in enc._choice_book._choices[choice.id].members
          if m.action.id==rush_id)
assert rush.actor_id==actor_id and rush.target_id==target_id
actor=world.get_object_by_id(actor_id);target=world.get_object_by_id(target_id)
before=[actor.get_position().as_tuple(),target.get_position().as_tuple()]
enc.step(1);receipt=enc.inspect_committed(1).action(rush_id)
assert receipt.facts.outcome=='failed'
assert [actor.get_position().as_tuple(),target.get_position().as_tuple()]==before
history_log=native_history.capture(enc)
print(json.dumps({'world_id':world.id,'encounter_id':enc.id,
 'being_ids':[actor_id,target_id],'action_id':rush_id,
 'outcome':receipt.facts.outcome,
 'positions':[actor.get_position().as_tuple(),target.get_position().as_tuple()],
 'hp':[actor.get_hit_points(),target.get_hit_points()], 'rng':rng.state,
 'history':hashlib.sha256(native_history.encode(history_log)).hexdigest()},
 sort_keys=True))'''
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "native-bull-rush-failure.json"
            path.write_bytes(pending)
            result = subprocess.run(
                [sys.executable, "-B", "-c", child, str(path), actor.id,
                 target.id, rush.id], cwd=directory,
                env={**os.environ,
                     "PYTHONPATH": f"{ROOT / 'src'}:{ROOT / 'examples'}"},
                text=True, capture_output=True, check=False, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), json.loads(json.dumps(expected)))

    def test_headless_failed_overrun_restores_standing_without_displacement(self):
        """A failed four-second Overrun remains failed and non-displacing."""
        builder = NativeScenarioBuilder(
            "native-overrun-failure", Library(config_dir=str(ROOT / "src/config")),
            seed=1, encounter_id="native-overrun-failure-encounter")
        actor = builder.add_being("Human", "Overrunner", position=(0, 0, 0),
                                  radius=.25, hit_points=100)
        target = builder.add_being("Human", "Resisting Target", position=(.2, 0, 0),
                                   radius=.25, hit_points=100)
        for being in (actor, target):
            being.set_posture("standing")
            being.size_category = "medium"
            being.set_ability("strength", 10)
            being.set_ability("dexterity", 10)
        actor.set_hex_facing(0)
        builder.mark_aware(actor.id, target.id)
        builder.mark_aware(target.id, actor.id)
        builder.enable()

        overrun = Action(builder.world, 0, 4, "overrun", actor.id, target.id,
                         None, id="native-overrun-failed-action")
        builder.schedule(overrun)
        pending = export_save(builder.encounter)
        before_positions = [actor.get_position().as_tuple(),
                            target.get_position().as_tuple()]
        builder.step(4)
        receipt = builder.encounter.inspect_committed(4).action(overrun.id)
        self.assertEqual(receipt.facts.outcome, "failed")
        self.assertEqual(target.get_posture(), "standing")
        self.assertEqual([actor.get_position().as_tuple(), target.get_position().as_tuple()],
                         before_positions)
        expected = {
            "world_id": builder.world.id,
            "encounter_id": builder.encounter.id,
            "being_ids": [actor.id, target.id],
            "action_id": overrun.id,
            "outcome": receipt.facts.outcome,
            "posture": target.get_posture(),
            "positions": [actor.get_position().as_tuple(),
                          target.get_position().as_tuple()],
            "hp": [actor.get_hit_points(), target.get_hit_points()],
            "rng": builder.rng.state,
            "history": hashlib.sha256(encode(capture(builder.encounter))).hexdigest(),
        }
        child = r'''import hashlib,json,sys
import native_history
from native_persistence import load_save
world,enc,rng=load_save(open(sys.argv[1],'rb').read())
actor_id,target_id,overrun_id=sys.argv[2:]
assert enc.time==0 and enc.progression_mode=='transactional'
choice=enc.choice_for_action(overrun_id);assert choice.state=='accepted'
overrun=next(m.action for m in enc._choice_book._choices[choice.id].members
             if m.action.id==overrun_id)
assert overrun.actor_id==actor_id and overrun.target_id==target_id
actor=world.get_object_by_id(actor_id);target=world.get_object_by_id(target_id)
before=[actor.get_position().as_tuple(),target.get_position().as_tuple()]
enc.step(4);receipt=enc.inspect_committed(4).action(overrun_id)
assert receipt.facts.outcome=='failed' and target.get_posture()=='standing'
assert [actor.get_position().as_tuple(),target.get_position().as_tuple()]==before
history_log=native_history.capture(enc)
print(json.dumps({'world_id':world.id,'encounter_id':enc.id,
 'being_ids':[actor_id,target_id],'action_id':overrun_id,
 'outcome':receipt.facts.outcome,'posture':target.get_posture(),
 'positions':[actor.get_position().as_tuple(),target.get_position().as_tuple()],
 'hp':[actor.get_hit_points(),target.get_hit_points()], 'rng':rng.state,
 'history':hashlib.sha256(native_history.encode(history_log)).hexdigest()},
 sort_keys=True))'''
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "native-overrun-failure.json"
            path.write_bytes(pending)
            result = subprocess.run(
                [sys.executable, "-B", "-c", child, str(path), actor.id,
                 target.id, overrun.id], cwd=directory,
                env={**os.environ,
                     "PYTHONPATH": f"{ROOT / 'src'}:{ROOT / 'examples'}"},
                text=True, capture_output=True, check=False, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), json.loads(json.dumps(expected)))

    def test_headless_charge_overrun_restores_and_commits_represented_forward_hex(self):
        """An adopted one-hex landing survives continuation in a new process."""
        from arena_hex_map import encounter_map_descriptor
        from hex_facing import facing_vector
        from measured_values import truncate_position

        layout = ArenaHexLayout.rectangle(20, 10)
        origin = layout.center_position(HexAddress(1, 4))
        dx, dy = facing_vector(1)
        builder = NativeScenarioBuilder(
            "native-charge-overrun",
            Library(config_dir=str(ROOT / "src/config")), seed=3,
            encounter_id="native-charge-overrun-encounter")
        actor = builder.add_being("Human", "Charger", position=origin.as_tuple(),
                                  radius=.25, hit_points=100)
        target_position = CartesianPosition(origin.x + 8.4 * dx,
                                            origin.y + 8.4 * dy, origin.z)
        target = builder.add_being("Human", "Charge Target",
                                   position=target_position.as_tuple(),
                                   radius=.25, hit_points=100)
        builder.encounter.map = encounter_map_descriptor(layout)
        actor.set_hex_facing(1)
        actor.size_category = target.size_category = "medium"
        actor.set_ability("strength", 10)
        target.set_ability("strength", 10)
        actor.set_ability("dexterity", 10)
        target.set_ability("dexterity", 10)
        actor.set_weapon_skill_level(
            builder.world.get_weapon_dictionary(), "Dagger", 100)
        actor.set_posture("standing")
        target.set_posture("standing")
        builder.mark_aware(actor.id, target.id)
        builder.mark_aware(target.id, actor.id)
        weapon = builder.make_weapon(actor.id, "Dagger", "Charge Dagger",
                                     hand="right hand")
        builder.enable()

        charge = MeleeStrike(
            builder.encounter, actor.id, target.id, weapon.id, motion="thrust",
            reach=2, strategy=Strategy(timing=3), charge=True)
        builder.schedule(charge)
        builder.encounter.step(2, velocities={actor.id: (3.8 * dx, 3.8 * dy, 0)})
        self.assertEqual(builder.encounter.inspect_committed(2).action(
            charge.id).facts.outcome, "normal")
        charge_position = actor.get_position()
        target_before = target.get_position()

        overrun = Action(builder.world, 2, 6, "overrun", actor.id, target.id,
                         None, id="native-charge-overrun-action")
        overrun.charge_continuation_source_id = charge.id
        prepared = builder.encounter.prepare_action(overrun)
        self.assertEqual(prepared.end_time, 8)
        builder.schedule(overrun)
        pending = export_save(builder.encounter)
        builder.step(6)
        receipt = builder.encounter.inspect_committed(8).action(overrun.id)
        self.assertEqual(receipt.facts.outcome, "success")

        start_cell = layout.cell_at_position(target_before)
        neighbors = [address for address in layout.neighbors(start_cell)
                     if layout.contains(address)]
        expected_position = layout.center_position(
            max(neighbors, key=lambda address: (
                layout.center_yards(address)[0] * dx
                + layout.center_yards(address)[1] * dy)), z=target_before.z)
        expected_position = truncate_position(expected_position)
        self.assertEqual(target.get_position(), expected_position)
        self.assertEqual(target.get_posture(), "lying")
        expected = {
            "world_id": builder.world.id,
            "encounter_id": builder.encounter.id,
            "being_ids": [actor.id, target.id],
            "weapon_id": weapon.id,
            "action_ids": [charge.id, overrun.id],
            "outcomes": [builder.encounter.inspect_committed(2).action(
                charge.id).facts.outcome, receipt.facts.outcome],
            "positions": [actor.get_position().as_tuple(),
                          target.get_position().as_tuple()],
            "hp": [actor.get_hit_points(), target.get_hit_points()],
            "posture": target.get_posture(),
            "rng": builder.rng.state,
            "history": hashlib.sha256(encode(capture(builder.encounter))).hexdigest(),
            "history_rows": [hashlib.sha256(json.dumps(row, sort_keys=True,
                separators=(",", ":")).encode()).hexdigest()
                for row in capture(builder.encounter)["boundaries"]],
        }
        child = r'''import hashlib,json,sys
import native_history
from native_persistence import load_save
world,enc,rng=load_save(open(sys.argv[1],'rb').read())
actor_id,target_id,weapon_id,charge_id,overrun_id=sys.argv[2:]
assert enc.time==2 and enc.progression_mode=='transactional'
assert enc.inspect_committed(2).action(charge_id).facts.outcome=='normal'
choice=enc.choice_for_action(overrun_id);assert choice.state=='accepted'
overrun=next(m.action for m in enc._choice_book._choices[choice.id].members
             if m.action.id==overrun_id)
assert overrun.charge_continuation_source_id==charge_id
assert overrun.start_time==2 and overrun.end_time==6
enc.step(6);receipt=enc.inspect_committed(8).action(overrun_id)
assert receipt.facts.outcome=='success'
actor=world.get_object_by_id(actor_id);target=world.get_object_by_id(target_id)
history_log=native_history.capture(enc)
print(json.dumps({'world_id':world.id,'encounter_id':enc.id,
 'being_ids':[actor_id,target_id],'weapon_id':weapon_id,
 'action_ids':[charge_id,overrun_id],
 'outcomes':[enc.inspect_committed(2).action(charge_id).facts.outcome,
             receipt.facts.outcome],
 'positions':[actor.get_position().as_tuple(),target.get_position().as_tuple()],
 'hp':[actor.get_hit_points(),target.get_hit_points()],
 'posture':target.get_posture(),'rng':rng.state,
 'history':hashlib.sha256(native_history.encode(history_log)).hexdigest(),
 'history_rows':[hashlib.sha256(json.dumps(row,sort_keys=True,
 separators=(',',':')).encode()).hexdigest()
                 for row in history_log['boundaries']]},sort_keys=True))'''
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "native-charge-overrun.json"
            path.write_bytes(pending)
            result = subprocess.run(
                [sys.executable, "-B", "-c", child, str(path), actor.id,
                 target.id, weapon.id, charge.id, overrun.id], cwd=directory,
                env={**os.environ,
                     "PYTHONPATH": f"{ROOT / 'src'}:{ROOT / 'examples'}"},
                text=True, capture_output=True, check=False, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), json.loads(json.dumps(expected)))

    def test_headless_failed_charge_restores_pending_choice_and_speed_result(self):
        """A below-threshold Charge remains a failed native fact after Load."""
        builder = NativeScenarioBuilder(
            "native-charge-failure", Library(config_dir=str(ROOT / "src/config")),
            seed=19, encounter_id="native-charge-failure-encounter")
        actor = builder.add_being("Human", "Slow Charger", position=(0, 0, 0),
                                  radius=.25, hit_points=100)
        target = builder.add_being("Human", "Charge Target", position=(7.4, 0, 0),
                                   radius=.25, hit_points=100)
        actor.set_hex_facing(0)
        actor.size_category = target.size_category = "medium"
        actor.set_weapon_skill_level(
            builder.world.get_weapon_dictionary(), "Dagger", 100)
        builder.mark_aware(actor.id, target.id)
        builder.mark_aware(target.id, actor.id)
        weapon = builder.make_weapon(actor.id, "Dagger", "Charge Dagger",
                                     hand="right hand")
        builder.enable()
        charge = MeleeStrike(
            builder.encounter, actor.id, target.id, weapon.id, motion="thrust",
            reach=2, strategy=Strategy(timing=3), charge=True)
        builder.schedule(charge)
        pending = export_save(builder.encounter)

        movement = {actor.id: (3.5, 0.0, 0.0)}
        builder.encounter.step(2, velocities=movement)
        receipt = builder.encounter.inspect_committed(2).action(charge.id)
        self.assertEqual(receipt.facts.outcome, "insufficient_charge_speed")
        self.assertEqual(target.get_hit_points(), 100)
        expected = {
            "world_id": builder.world.id,
            "encounter_id": builder.encounter.id,
            "being_ids": [actor.id, target.id],
            "weapon_id": weapon.id,
            "action_id": charge.id,
            "outcome": receipt.facts.outcome,
            "positions": [actor.get_position().as_tuple(),
                          target.get_position().as_tuple()],
            "hp": [actor.get_hit_points(), target.get_hit_points()],
            "rng": builder.rng.state,
            "history": hashlib.sha256(encode(capture(builder.encounter))).hexdigest(),
        }
        child = r'''import hashlib,json,sys
import native_history
from native_persistence import load_save
world,enc,rng=load_save(open(sys.argv[1],'rb').read())
actor_id,target_id,weapon_id,charge_id=sys.argv[2:]
assert enc.time==0 and enc.progression_mode=='transactional'
choice=enc.choice_for_action(charge_id);assert choice.state=='accepted'
charge=next(m.action for m in enc._choice_book._choices[choice.id].members
            if m.action.id==charge_id)
assert charge.actor_id==actor_id and charge.target_id==target_id
assert charge.instrument_id==weapon_id and charge.charge is True
enc.step(2,velocities={actor_id:(3.5,0.0,0.0)})
receipt=enc.inspect_committed(2).action(charge_id)
assert receipt.facts.outcome=='insufficient_charge_speed'
actor=world.get_object_by_id(actor_id);target=world.get_object_by_id(target_id)
history_log=native_history.capture(enc)
print(json.dumps({'world_id':world.id,'encounter_id':enc.id,
 'being_ids':[actor_id,target_id],'weapon_id':weapon_id,
 'action_id':charge_id,'outcome':receipt.facts.outcome,
 'positions':[actor.get_position().as_tuple(),target.get_position().as_tuple()],
 'hp':[actor.get_hit_points(),target.get_hit_points()],
 'rng':rng.state,
 'history':hashlib.sha256(native_history.encode(history_log)).hexdigest()},
 sort_keys=True))'''
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "native-charge-failure.json"
            path.write_bytes(pending)
            result = subprocess.run(
                [sys.executable, "-B", "-c", child, str(path), actor.id,
                 target.id, weapon.id, charge.id], cwd=directory,
                env={**os.environ,
                     "PYTHONPATH": f"{ROOT / 'src'}:{ROOT / 'examples'}"},
                text=True, capture_output=True, check=False, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), json.loads(json.dumps(expected)))

    def test_headless_fatal_coup_preserves_fatal_effect_after_restore(self):
        """FatalEffect is part of native history and same-Encounter restore."""
        from states import StatesList

        builder = NativeScenarioBuilder(
            "native-fatal-coup", Library(config_dir=str(ROOT / "src/config")),
            seed=1, encounter_id="native-fatal-coup-encounter")
        attacker = builder.add_being("Human", "Attacker", position=(0, 0, 0),
                                     radius=.25, hit_points=100)
        target = builder.add_being("Human", "Helpless Target", position=(.2, 0, 0),
                                   radius=.25, hit_points=100)
        states = StatesList()
        states.load_states(str(ROOT / "src/config/states.tsv"))
        target.stun(states)
        builder.mark_aware(attacker.id, target.id)
        builder.mark_aware(target.id, attacker.id)
        weapon = builder.make_weapon(attacker.id, "Dagger", "Coup Dagger",
                                     hand="right hand")
        builder.enable()

        action = Action(builder.world, 0, 1, "coup de grace", attacker.id,
                        target.id, weapon.id, id="native-fatal-coup-action")
        action.coup_motion = "thrust"
        action.reach = effective_melee_reach_meters(attacker.current, weapon.current)
        action.end_time = math.ceil(weapon.Tt())
        builder.schedule(action)
        duration = math.ceil(action.end_time)
        pending = export_save(builder.encounter)
        builder.step(duration)
        receipt = builder.encounter.inspect_committed(duration).action(action.id)
        self.assertEqual(receipt.facts.outcome, "fatal")
        self.assertIn(target.id, receipt.fatal_targets)
        fatal_effects = [row for row in receipt.facts.effects
                         if type(row).__name__ == "FatalEffect"]
        self.assertEqual(len(fatal_effects), 1)
        self.assertLessEqual(target.get_hit_points(), -10)
        expected = {
            "world_id": builder.world.id,
            "encounter_id": builder.encounter.id,
            "being_ids": [attacker.id, target.id],
            "weapon_id": weapon.id,
            "action_id": action.id,
            "outcome": receipt.facts.outcome,
            "fatal_targets": list(receipt.fatal_targets),
            "effect_types": [type(row).__name__ for row in receipt.facts.effects],
            "effects": [(row.identity.encounter_id, row.identity.boundary,
                         row.identity.source_action_id, row.identity.channel,
                         row.identity.slot, type(row.effect).__name__)
                        for row in receipt.effects],
            "hp": [attacker.get_hit_points(), target.get_hit_points()],
            "rng": builder.rng.state,
            "history": hashlib.sha256(encode(capture(builder.encounter))).hexdigest(),
        }
        child = r'''import hashlib,json,sys
import native_history
from native_persistence import load_save
world,enc,rng=load_save(open(sys.argv[1],'rb').read())
attacker_id,target_id,weapon_id,action_id=sys.argv[2:]
choice=enc.choice_for_action(action_id);assert choice.state=='accepted'
action=next(m.action for m in enc._choice_book._choices[choice.id].members
            if m.action.id==action_id)
assert action.actor_id==attacker_id and action.target_id==target_id
assert action.instrument_id==weapon_id and action.event_type=='coup de grace'
duration=enc._choice_book._choices[choice.id].members[0].action.end_time
enc.step(int(duration))
receipt=enc.inspect_committed(int(duration)).action(action_id)
assert receipt.facts.outcome=='fatal' and target_id in receipt.fatal_targets
assert sum(type(row).__name__=='FatalEffect' for row in receipt.facts.effects)==1
target=world.get_object_by_id(target_id);attacker=world.get_object_by_id(attacker_id)
history_log=native_history.capture(enc)
print(json.dumps({'world_id':world.id,'encounter_id':enc.id,
 'being_ids':[attacker_id,target_id],'weapon_id':weapon_id,'action_id':action_id,
 'outcome':receipt.facts.outcome,'fatal_targets':list(receipt.fatal_targets),
 'effect_types':[type(row).__name__ for row in receipt.facts.effects],
 'effects':[(row.identity.encounter_id,row.identity.boundary,
             row.identity.source_action_id,row.identity.channel,
             row.identity.slot,type(row.effect).__name__)
            for row in receipt.effects],
 'hp':[attacker.get_hit_points(),target.get_hit_points()], 'rng':rng.state,
 'history':hashlib.sha256(native_history.encode(history_log)).hexdigest()},
 sort_keys=True))'''
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "native-fatal-coup.json"
            path.write_bytes(pending)
            result = subprocess.run(
                [sys.executable, "-B", "-c", child, str(path), attacker.id,
                 target.id, weapon.id, action.id], cwd=directory,
                env={**os.environ,
                     "PYTHONPATH": f"{ROOT / 'src'}:{ROOT / 'examples'}"},
                text=True, capture_output=True, check=False, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), json.loads(json.dumps(expected)))

    def test_headless_break_weapon_failure_preserves_later_attack_after_restore(self):
        attacking = NativeScenarioBuilder(
            "native-break-weapon", Library(config_dir=str(ROOT / "src/config")),
            seed=1, encounter_id="native-break-weapon-encounter")
        breaker = attacking.add_being("Human", "Weapon Breaker", position=(0, 0, 0),
                                      radius=.25, hit_points=100)
        defender = attacking.add_being("Human", "Weapon Holder", position=(.2, 0, 0),
                                       radius=.25, hit_points=100)
        attack_weapon = attacking.make_weapon(breaker.id, "Dagger", "Breaker Dagger",
                                              hand="right hand")
        target_weapon = attacking.make_weapon(defender.id, "Dagger", "Defender Dagger",
                                              hand="right hand")
        breaker.current.skills.weapon_skills["Dagger"] = 2
        attacking.mark_aware(breaker.id, defender.id)
        attacking.mark_aware(defender.id, breaker.id)
        attacking.enable()
        duration = max(1, math.ceil(attack_weapon.St()))
        followup = MeleeStrike(attacking.encounter, defender.id, breaker.id,
                               target_weapon.id, motion="thrust", reach=2)
        followup.end_time = duration + 1
        attacking.schedule(followup)
        action = Action(attacking.world, 0, 1, "break weapon", breaker.id,
                        defender.id, attack_weapon.id,
                        id="native-break-weapon-action")
        action.break_weapon_id = target_weapon.id
        action.break_motion = "swing"
        action.reach = effective_melee_reach_meters(breaker.current,
                                                    attack_weapon.current)
        action.end_time = duration
        attacking.schedule(action)
        initial = export_save(attacking.encounter)
        attacking.step(duration)
        first_receipt = attacking.encounter.inspect_committed(duration)
        self.assertEqual(first_receipt.action(action.id).facts.outcome, "miss")
        original_target_weapon_hp = target_weapon.hit_points()
        attacking.step(1)
        second_receipt = attacking.encounter.inspect_committed(duration + 1)
        self.assertNotEqual(second_receipt.action(followup.id).facts.outcome,
                            "weapon_unavailable")
        expected = {
            "time": attacking.encounter.time,
            "break_id": action.id,
            "followup_id": followup.id,
            "break_outcome": first_receipt.action(action.id).facts.outcome,
            "followup_outcome": second_receipt.action(followup.id).facts.outcome,
            "target_weapon_id": target_weapon.id,
            "target_weapon_hp": target_weapon.hit_points(),
            "original_target_weapon_hp": original_target_weapon_hp,
            "rng": attacking.rng.state,
            "history": hashlib.sha256(encode(capture(attacking.encounter))).hexdigest(),
        }
        child = r'''import hashlib,json,sys
import native_history
from native_persistence import load_save
world,enc,rng=load_save(open(sys.argv[1],'rb').read())
break_id,follow_id,weapon_id=sys.argv[2:]
break_choice=enc.choice_for_action(break_id);follow_choice=enc.choice_for_action(follow_id)
assert break_choice.state=='accepted' and follow_choice.state=='accepted'
break_action=next(m.action for m in enc._choice_book._choices[break_choice.id].members
                  if m.action.id==break_id)
followup=next(m.action for m in enc._choice_book._choices[follow_choice.id].members
              if m.action.id==follow_id)
enc.step(int(break_action.end_time-enc.time))
first=enc.inspect_committed(int(enc.time))
target_weapon=world.get_object_by_id(weapon_id)
initial_hp=target_weapon.hit_points()
enc.step(1);second=enc.inspect_committed(int(enc.time))
print(json.dumps({'time':enc.time,'break_id':break_action.id,'followup_id':followup.id,
 'break_outcome':first.action(break_id).facts.outcome,
 'followup_outcome':second.action(follow_id).facts.outcome,
 'target_weapon_id':target_weapon.id,'target_weapon_hp':target_weapon.hit_points(),
 'original_target_weapon_hp':initial_hp,'rng':rng.state,
 'history':hashlib.sha256(native_history.encode(native_history.capture(enc))).hexdigest()},
 sort_keys=True))'''
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "native-break-weapon.json"
            path.write_bytes(initial)
            result = subprocess.run(
                [sys.executable, "-B", "-c", child, str(path), action.id,
                 followup.id, target_weapon.id], cwd=directory,
                env={**os.environ,
                     "PYTHONPATH": f"{ROOT / 'src'}:{ROOT / 'examples'}"},
                text=True, capture_output=True, check=False, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), json.loads(json.dumps(expected)))

    def test_headless_standard_weapon_break_commits_and_disables_followup_after_restore(self):
        builder = NativeScenarioBuilder(
            "native-standard-break", Library(config_dir=str(ROOT / "src/config")),
            seed=3, encounter_id="native-standard-break-encounter")
        breaker = builder.add_being("Human", "Bastard Sword User",
                                    position=(0, 0, 0), radius=.25, hit_points=100)
        defender = builder.add_being("Human", "Dagger User", position=(.2, 0, 0),
                                     radius=.25, hit_points=100)
        attacking = builder.make_weapon(breaker.id, "Bastard sword", "Standard Bastard sword",
                                        hand="right hand")
        target_weapon = builder.make_weapon(defender.id, "Dagger", "Standard Target Dagger",
                                            hand="right hand")
        breaker.current.skills.weapon_skills["Bastard sword"] = 2
        builder.mark_aware(breaker.id, defender.id)
        builder.mark_aware(defender.id, breaker.id)
        builder.enable()
        duration = max(1, math.ceil(attacking.St()))
        followup = MeleeStrike(builder.encounter, defender.id, breaker.id,
                               target_weapon.id, motion="thrust", reach=2)
        followup.end_time = duration + 1
        builder.schedule(followup)
        action = Action(builder.world, 0, 1, "break weapon", breaker.id,
                        defender.id, attacking.id, id="native-standard-break-action")
        action.break_weapon_id = target_weapon.id
        action.break_motion = "swing"
        action.reach = effective_melee_reach_meters(breaker.current, attacking.current)
        action.end_time = duration
        builder.schedule(action)
        initial = export_save(builder.encounter)

        builder.step(duration)
        break_receipt = builder.encounter.inspect_committed(duration).action(action.id)
        self.assertEqual(break_receipt.facts.outcome, "broken")
        self.assertLessEqual(target_weapon.hit_points(), 0)
        target_hp_after_break = target_weapon.hit_points()
        builder.step(1)
        follow_receipt = builder.encounter.inspect_committed(duration + 1).action(followup.id)
        self.assertEqual(follow_receipt.facts.outcome, "weapon_unavailable")
        expected = {
            "time": builder.encounter.time,
            "break_id": action.id,
            "break_outcome": break_receipt.facts.outcome,
            "followup_id": followup.id,
            "followup_outcome": follow_receipt.facts.outcome,
            "attacking_weapon_id": attacking.id,
            "target_weapon_id": target_weapon.id,
            "target_weapon_hp": target_weapon.hit_points(),
            "target_hp_after_break": target_hp_after_break,
            "rng": builder.rng.state,
            "history": hashlib.sha256(encode(capture(builder.encounter))).hexdigest(),
        }
        child = r'''import hashlib,json,sys
import native_history
from native_persistence import load_save
world,enc,rng=load_save(open(sys.argv[1],'rb').read())
break_id,follow_id,attacking_id,target_id=sys.argv[2:]
break_choice=enc.choice_for_action(break_id);follow_choice=enc.choice_for_action(follow_id)
assert break_choice.state=='accepted' and follow_choice.state=='accepted'
action=next(m.action for m in enc._choice_book._choices[break_choice.id].members
            if m.action.id==break_id)
attacking=world.get_object_by_id(attacking_id);target=world.get_object_by_id(target_id)
enc.step(int(action.end_time-enc.time));first=enc.inspect_committed(int(enc.time))
assert first.action(break_id).facts.outcome=='broken' and target.hit_points()<=0
target_hp_after_break=target.hit_points()
enc.step(1);second=enc.inspect_committed(int(enc.time))
assert second.action(follow_id).facts.outcome=='weapon_unavailable'
print(json.dumps({'time':enc.time,'break_id':action.id,
 'break_outcome':first.action(break_id).facts.outcome,'followup_id':follow_id,
 'followup_outcome':second.action(follow_id).facts.outcome,
 'attacking_weapon_id':attacking.id,'target_weapon_id':target.id,
 'target_weapon_hp':target.hit_points(),'target_hp_after_break':target_hp_after_break,
 'rng':rng.state,'history':hashlib.sha256(native_history.encode(
 native_history.capture(enc))).hexdigest()},sort_keys=True))'''
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "native-standard-break.json"
            path.write_bytes(initial)
            result = subprocess.run(
                [sys.executable, "-B", "-c", child, str(path), action.id,
                 followup.id, attacking.id, target_weapon.id], cwd=directory,
                env={**os.environ,
                     "PYTHONPATH": f"{ROOT / 'src'}:{ROOT / 'examples'}"},
                text=True, capture_output=True, check=False, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), json.loads(json.dumps(expected)))


if __name__ == "__main__":
    unittest.main()
