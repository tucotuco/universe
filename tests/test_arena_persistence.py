"""Portable generated-Arena save/load integration tests."""
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from arena_browser_session import GeneratedArenaSession


class TestArenaPersistence(unittest.TestCase):
    @staticmethod
    def _tuplify(value):
        return tuple(TestArenaPersistence._tuplify(row) for row in value) if type(value) is list else value

    def _new_moving_session(self, *, ground_loadout_profile=None):
        session = GeneratedArenaSession(root_seed_factory=lambda: 20261107,
                                       ground_loadout_profile=ground_loadout_profile)
        session.generate({"starting_experience": "10000",
                          "width_cells": "5", "height_cells": "5"})
        candidate = session.active_candidate
        position = candidate.participants[0].native.being.get_position()
        address = max(candidate.arena_map.layout.addresses(), key=lambda cell:
            math.dist(candidate.arena_map.layout.center_position(cell, z=position.z).as_tuple(),
                      position.as_tuple()))
        session.choose_destination({"column": address.column, "row": address.row,
                                   "rate": "walk", "facing_policy": "turn"})
        return session

    def test_pristine_ground_objects_restore_with_native_identity_and_evidence(self):
        profile = json.loads((ROOT / "tests/fixtures/arena/test_ground_loadout_profile.json").read_text())
        source = GeneratedArenaSession(root_seed_factory=lambda: 20261107,
                                       ground_loadout_profile=profile)
        source.generate({"starting_experience": "10000",
                         "width_cells": "5", "height_cells": "5"})
        candidate = source.active_candidate
        object_ids = tuple(candidate.encounter.non_being_object_list)
        saved = source.save_encounter_bytes()
        restored = GeneratedArenaSession()
        view = restored.load_encounter_bytes(saved)
        loaded = restored.active_candidate
        self.assertEqual(tuple(loaded.encounter.non_being_object_list), object_ids)
        self.assertEqual(len(loaded.ground_objects), 8)
        self.assertEqual(len(view["entities"]), 9)
        for object_id in object_ids:
            before = candidate.universe.get_object_by_id(object_id)
            after = loaded.universe.get_object_by_id(object_id)
            self.assertIs(type(after), type(before))
            self.assertEqual(after.original.obj_type, before.original.obj_type)
            self.assertEqual(after.get_position(), before.get_position())
            self.assertEqual(after.parent_container_id, before.parent_container_id)
        for source_being, loaded_participant in zip(
                candidate.participants, loaded.participants):
            self.assertEqual(source_being.native.being._arena_perception_ledger.history,
                             loaded_participant.native.being._arena_perception_ledger.history)

    def test_repeatable_three_process_movement_continuation(self):
        uninterrupted = self._new_moving_session()
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "boundary-1.json"
            second = Path(directory) / "boundary-2.json"
            first.write_bytes(uninterrupted.save_encounter_bytes())
            uninterrupted.advance_one_second()
            first.write_bytes(uninterrupted.save_encounter_bytes())

            script_b = """
import pathlib,sys
from arena_browser_session import GeneratedArenaSession
s=GeneratedArenaSession();s.load_encounter_bytes(pathlib.Path(sys.argv[1]).read_bytes())
s.advance_one_second();pathlib.Path(sys.argv[2]).write_bytes(s.save_encounter_bytes())
print(s.active_candidate.encounter.time)
"""
            env = {"PYTHONPATH": str(ROOT / "src")}
            b = subprocess.run([sys.executable, "-S", "-c", script_b,
                                str(first), str(second)], cwd=ROOT, env=env,
                               capture_output=True, text=True, check=True)
            self.assertEqual(b.stdout.strip(), "2")

            script_c = """
import json,pathlib,sys
from arena_browser_session import GeneratedArenaSession
s=GeneratedArenaSession();s.load_encounter_bytes(pathlib.Path(sys.argv[1]).read_bytes())
s.advance_one_second();c=s.active_candidate;e=c.encounter;p=c.participants[0].native.being
print(json.dumps({'time':e.time,'position':p.get_position().as_tuple(),
 'facing':p.hex_facing,'rng':s._rng_cursor.state,
 'target_history':len(p._atomic_target_history),
 'receipt_history':len(e._atomic_interval_history)},separators=(',',':')))
"""
            c = subprocess.run([sys.executable, "-S", "-c", script_c,
                                str(second)], cwd=ROOT, env=env,
                               capture_output=True, text=True, check=True)
            restored = json.loads(c.stdout)
            uninterrupted.advance_one_second()
            uninterrupted.advance_one_second()
            candidate = uninterrupted.active_candidate
            encounter = candidate.encounter
            player = candidate.participants[0].native.being
            self.assertEqual(restored["time"], 3)
            self.assertEqual(tuple(restored["position"]), player.get_position().as_tuple())
            self.assertEqual(restored["facing"], player.hex_facing)
            self.assertEqual(self._tuplify(restored["rng"]), uninterrupted._rng_cursor.state)
            self.assertEqual(restored["target_history"], len(player._atomic_target_history))
            self.assertEqual(restored["receipt_history"], len(encounter._atomic_interval_history))

    def test_repeatable_three_process_continuation_with_ground_objects(self):
        profile = json.loads((ROOT / "tests/fixtures/arena/test_ground_loadout_profile.json").read_text())
        uninterrupted = self._new_moving_session(ground_loadout_profile=profile)
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "objects-boundary-1.json"
            second = Path(directory) / "objects-boundary-2.json"
            first.write_bytes(uninterrupted.save_encounter_bytes())
            uninterrupted.advance_one_second()
            first.write_bytes(uninterrupted.save_encounter_bytes())

            script_b = """
import pathlib,sys
from arena_browser_session import GeneratedArenaSession
s=GeneratedArenaSession();s.load_encounter_bytes(pathlib.Path(sys.argv[1]).read_bytes())
c=s.active_candidate;e=c.encounter
assert len(e.non_being_object_list)==8
assert all(len(c.universe.get_object_by_id(i)._atomic_target_history)==1 for i in e.non_being_object_list)
s.advance_one_second();pathlib.Path(sys.argv[2]).write_bytes(s.save_encounter_bytes())
print(e.time)
"""
            env = {"PYTHONPATH": str(ROOT / "src")}
            b = subprocess.run([sys.executable, "-S", "-c", script_b,
                                str(first), str(second)], cwd=ROOT, env=env,
                               capture_output=True, text=True, check=True)
            self.assertEqual(b.stdout.strip(), "2")

            script_c = """
import json,pathlib,sys
from arena_browser_session import GeneratedArenaSession
s=GeneratedArenaSession();s.load_encounter_bytes(pathlib.Path(sys.argv[1]).read_bytes())
c=s.active_candidate;e=c.encounter
ids=list(e.non_being_object_list);objects=[c.universe.get_object_by_id(i) for i in ids]
assert all(len(o._atomic_target_history)==2 for o in objects)
s.advance_one_second()
print(json.dumps({'time':e.time,'ids':ids,'objects':[(o.id,o.type,o.get_position().as_tuple(),len(o._atomic_target_history)) for o in objects], 'rng':s._rng_cursor.state,'receipts':len(e._atomic_interval_history)},separators=(',',':')))
"""
            c = subprocess.run([sys.executable, "-S", "-c", script_c,
                                str(second)], cwd=ROOT, env=env,
                               capture_output=True, text=True, check=True)
            restored = json.loads(c.stdout)
            uninterrupted.advance_one_second()
            uninterrupted.advance_one_second()
            candidate = uninterrupted.active_candidate
            encounter = candidate.encounter
            universe = candidate.universe
            expected_objects = [universe.get_object_by_id(key)
                                for key in encounter.non_being_object_list]
            self.assertEqual(restored["time"], 3)
            self.assertEqual(restored["ids"], list(encounter.non_being_object_list))
            self.assertEqual(restored["objects"], [
                [obj.id, obj.type, list(obj.get_position().as_tuple()),
                 len(obj._atomic_target_history)] for obj in expected_objects])
            self.assertEqual(self._tuplify(restored["rng"]), uninterrupted._rng_cursor.state)
            self.assertEqual(restored["receipts"], len(encounter._atomic_interval_history))


if __name__ == "__main__":
    unittest.main()
