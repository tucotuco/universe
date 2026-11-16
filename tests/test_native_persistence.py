from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "examples"))

import encounter_delta_headless
import native_history
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
        action = DelayAction(encounter, actor_id, defense=0, start_time=4,
                             id="native-save-pending-delay")
        encounter.schedule_action(action)
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

        second = MeleeStrike(encounter, attacker.id, defender.id, weapon_id,
                             motion="thrust", reach=2, strategy=Strategy())
        encounter.schedule_action(second)
        save = export_save(encounter)
        encounter.step(4)
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


if __name__ == "__main__":
    unittest.main()
