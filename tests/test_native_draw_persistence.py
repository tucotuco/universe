from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "examples")]

from activities import PickUpAction, ReadyWeaponAction
from library import Library
from arena_hex_map import ArenaHexLayout, HexAddress
from native_history import capture, encode
from native_persistence import export_save
from native_scenario import NativeScenarioBuilder
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


if __name__ == "__main__":
    unittest.main()
