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
scenario.mark_aware(first.id,second.id);scenario.mark_aware(second.id,first.id)
scenario.enable()
action=DelayAction(scenario.encounter,first.id,defense=0,start_time=0,id='scenario-delay')
scenario.schedule(action);scenario.step(1)
wire=export_save(scenario.encounter)
world,enc,rng=load_save(wire)
assert enc.id==scenario.encounter.id and world.id==scenario.world.id
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


if __name__ == "__main__":
    unittest.main()
