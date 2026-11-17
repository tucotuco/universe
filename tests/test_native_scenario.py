"""The reusable headless authoring API must use the ordinary native engine."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class NativeScenarioTests(unittest.TestCase):
    def test_headless_builder_authors_and_restores_without_arena_application(self):
        script = r'''import json,sys
from activities import DelayAction
from library import Library
from native_history import NativeHistoryQuery,capture
from native_persistence import export_save,load_save
from native_scenario import NativeScenarioBuilder
scenario=NativeScenarioBuilder('native-scenario-smoke',
 Library(config_dir=sys.argv[1]),seed=731)
first=scenario.add_being('Human','Scenario First',position=(0,0,0),radius=.25,hit_points=10)
second=scenario.add_being('Human','Scenario Second',position=(.2,0,0),radius=.25,hit_points=10)
pillow=scenario.make_object('Linen pillow','Scenario placed Object',
 position=(2,0,0))
armor=scenario.make_armor('Gauntlet','Scenario worn Armor',
 wearer_id=first.id)
carried=scenario.make_possession_object(first.id,'Linen pillow',
 'Scenario carried Object')
scenario.mark_aware(first.id,second.id);scenario.mark_aware(second.id,first.id)
scenario.enable()
action=DelayAction(scenario.encounter,first.id,defense=0,start_time=0,id='scenario-delay')
scenario.schedule(action);scenario.step(1)
wire=export_save(scenario.encounter)
world,enc,rng=load_save(wire)
assert enc.id==scenario.encounter.id and world.id==scenario.world.id
assert world.get_object_by_id(pillow.id).get_position().as_tuple()==(2,0,0)
assert world.get_object_by_id(armor.id).original is world.library.get_armor_definition('Gauntlet')
assert world.get_object_by_id(first.id).get_armor_id()==armor.id
assert carried.id in world.get_object_by_id(first.id).possessions
assert enc._atomic_interval_history[-1].action_ids==('scenario-delay',)
query=NativeHistoryQuery(capture(enc))
assert query.events_at(1)['action_ids']==['scenario-delay']
assert not (set(sys.modules)&{'arena_browser_session','arena_server','npcgen'})
print(json.dumps({'world':world.id,'encounter':enc.id,'action':action.id,
 'time':enc.time,'hp':[enc.get_being(i).get_hit_points() for i in enc.being_list]},sort_keys=True))'''
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, "-B", "-c", script, str(ROOT / "src/config")],
                cwd=ROOT, env={**__import__("os").environ,
                               "PYTHONPATH": str(ROOT / "src")},
                text=True, capture_output=True, check=False, timeout=45)
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)
        self.assertEqual(value["action"], "scenario-delay")
        self.assertEqual(value["time"], 1)
        self.assertEqual(value["hp"], [10, 10])

    def test_initial_history_precedes_first_boundary_movement_and_survives_fresh_load(self):
        """Boundary zero is captured before first-second physical movement."""
        import os
        from activities import RunAction
        from library import Library
        from native_history import NativeHistoryQuery, _materialize_plain, capture
        from native_persistence import export_save
        from native_scenario import NativeScenarioBuilder

        scenario = NativeScenarioBuilder(
            "native-initial-movement", Library(config_dir=str(ROOT / "src/config")),
            seed=41, end_time=3)
        runner = scenario.add_being("Human", "Initial Runner",
                                    position=(0.0, 0.0, 0.0), radius=.25,
                                    hit_points=10)
        scenario.enable()
        scenario.schedule(RunAction(scenario.world, runner.id, 0, 1, .5,
                                    experience=2, id="initial-movement-run"))
        scenario.step(1, velocities={runner.id: (1.0, 0.0, 0.0)})

        log = capture(scenario.encounter)
        self.assertTrue(log["initial"]["initial_entities_available"])
        query = NativeHistoryQuery(log)
        initial = _materialize_plain(query.entity_at(runner.id, 0))
        committed = _materialize_plain(query.entity_at(runner.id, 1))
        self.assertEqual(initial.position.as_tuple(), (0.0, 0.0, 0.0))
        self.assertEqual(committed.position.as_tuple(), (1.0, 0.0, 0.0))
        wire = export_save(scenario.encounter)

        child = r'''import json,sys
from native_history import NativeHistoryQuery,current_recording,_materialize_plain
from native_persistence import load_path
world,enc,rng=load_path(sys.argv[1]); q=NativeHistoryQuery(current_recording(enc))
initial=_materialize_plain(q.entity_at(enc.being_list[0],0))
current=_materialize_plain(q.entity_at(enc.being_list[0],1))
print(json.dumps({'initial':initial.position.as_tuple(),'current':current.position.as_tuple(),
 'time':enc.time},sort_keys=True))'''
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "initial-movement.json"
            path.write_bytes(wire)
            result = subprocess.run(
                [sys.executable, "-B", "-c", child, str(path)], cwd=ROOT,
                env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
                text=True, capture_output=True, check=False, timeout=45)
        self.assertEqual(result.returncode, 0, result.stderr)
        restored = json.loads(result.stdout)
        self.assertEqual(restored, {"current": [1.0, 0.0, 0.0],
                                    "initial": [0.0, 0.0, 0.0], "time": 1.0})


if __name__ == "__main__":
    unittest.main()
