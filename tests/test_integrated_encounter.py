"""The first complete, reproducible Encounter causal-loop regression test."""
from pathlib import Path
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "examples"))
sys.path.insert(0, str(ROOT / "src"))

from integrated_encounter import run_scenario


class TestIntegratedEncounter(unittest.TestCase):
    def setUp(self):
        self.result = run_scenario()
        self.encounter = self.result["encounter"]
        self.states = self.result["states"]
        self.actions = self.result["actions"]
        self.scout = self.result["scout"]
        self.ids = self.result["ids"]

    def test_visibility_movement_and_awareness_are_distinct(self):
        self.assertEqual([s["time"] for s in self.states], [0, 1, 2, 3, 4])
        self.assertEqual([s["sightline"] for s in self.states],
                         ["blocked", "blocked", "clear", "clear", "clear"])
        self.assertEqual([s["cache_aware"] for s in self.states],
                         [False, False, False, False, True])
        self.assertEqual(self.states[2]["position"], (0, 3.0, 0))
        self.assertFalse(self.encounter.is_aware(self.ids["companion"], self.ids["cache"]))
        self.assertEqual(self.encounter.aware_objects(self.ids["scout"]),
                         [self.ids["cache"]])
        self.assertEqual(self.encounter.time, 4)

    def test_action_schedule_and_outcomes(self):
        self.assertEqual([action.resolution.outcome for action in self.actions.values()],
                         ["success", "no_clear_path", "failure", "success"])
        self.assertEqual(self.actions["obstructed_spot"].path_status, "blocked")
        self.assertIsNone(self.actions["obstructed_spot"].roll)
        self.assertEqual(self.actions["first_spot"].skill_level_used, 0)
        self.assertEqual(self.actions["second_spot"].skill_level_used, 1)
        self.assertEqual(self.actions["first_spot"].roll,
                         self.actions["second_spot"].roll)
        self.assertEqual(self.encounter.pending_action_list, [])
        self.assertEqual(len(self.encounter.finished_action_list), 4)
        self.assertEqual([len(step.completed_action_ids) for step in self.result["steps"]],
                         [1, 1, 1, 1])

    def test_experience_is_actor_specific_and_traced_to_actions(self):
        self.assertEqual(self.scout.get_skill_experience("run"), 250)
        self.assertEqual(self.scout.get_skill_experience("spot"), 250)
        self.assertEqual(self.scout.get_skill_level("run"), 1)
        self.assertEqual(self.scout.get_skill_level("spot"), 1)
        self.assertEqual([(record.skill_name, record.outcome, record.time,
                           record.experience, record.level_before, record.level_after)
                          for record in self.scout.skill_use_history], [
            ("spot", "no_clear_path", 1, 0, 0, 0),
            ("run", "success", 2, 250, 0, 1),
            ("spot", "failure", 3, 250, 0, 1),
            ("spot", "success", 4, 0, 1, 1),
        ])
        self.assertEqual(
            [record.action_id for record in self.scout.skill_use_history],
            [self.actions[name].id for name in
             ("obstructed_spot", "run", "first_spot", "second_spot")])
        self.assertEqual(self.result["companion"].skill_use_history, [])
        self.assertIsNone(self.scout.original.get_skill_level("spot"))

    def test_recorded_event_state_and_observation(self):
        data = json.loads(self.encounter.to_json())
        self.assertEqual(data["time"], 4)
        self.assertTrue(data["initiated"])
        self.assertEqual(data["initiation"]["intent"], "search nearby")
        self.assertEqual(data["awareness"][self.ids["scout"]],
                         sorted([self.ids["companion"], self.ids["cache"]]))
        self.assertEqual(data["finished_action_list"],
                         self.encounter.finished_action_list)
        observations = self.actions["second_spot"].resolution.observations
        self.assertEqual(len(observations), 1)
        self.assertEqual(observations[0].target_id, self.ids["cache"])


if __name__ == "__main__":
    unittest.main()
