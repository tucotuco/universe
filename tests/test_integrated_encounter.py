"""Revision-60 Spot timing, movement, awareness and legitimate Run practice."""
from pathlib import Path
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'examples')); sys.path.insert(0, str(ROOT / 'src'))
from integrated_encounter import run_scenario


class TestIntegratedEncounter(unittest.TestCase):
    def setUp(self):
        self.result = run_scenario()
        self.encounter = self.result['encounter']; self.states = self.result['states']
        self.actions = self.result['actions']; self.scout = self.result['scout']; self.ids = self.result['ids']

    def test_spot_uses_post_movement_six_second_boundary(self):
        self.assertEqual([s['time'] for s in self.states], list(range(7)))
        self.assertEqual([s['sightline'] for s in self.states],
                         ['blocked', 'blocked', 'clear', 'clear', 'clear', 'clear', 'clear'])
        self.assertEqual([s['cache_aware'] for s in self.states],
                         [False, False, False, False, False, False, True])
        self.assertEqual(self.states[2]['position'], (0, 3.0, 0))
        self.assertEqual(self.encounter.time, 6)
        self.assertEqual(self.actions['spot'].end_time, 6)
        self.assertEqual(self.actions['spot'].resolution.outcome, 'success')
        self.assertFalse(self.encounter.is_aware(self.ids['companion'], self.ids['cache']))

    def test_run_is_the_only_practice_producing_action(self):
        self.assertEqual(self.actions['run'].resolution.outcome, 'success')
        self.assertEqual(self.scout.get_skill_experience('run'), 250)
        self.assertEqual(self.scout.get_skill_experience('spot'), 0)
        self.assertEqual([record.skill_name for record in self.scout.skill_use_history], ['run'])
        self.assertEqual(self.scout.skill_use_history[0].action_id, self.actions['run'].id)
        self.assertEqual(self.encounter.pending_action_list, [])
        self.assertEqual(len(self.encounter.finished_action_list), 2)

    def test_recorded_awareness_is_observer_specific(self):
        data = json.loads(self.encounter.to_json())
        self.assertEqual(data['time'], 6)
        self.assertTrue(data['initiated'])
        self.assertEqual(data['awareness'][self.ids['scout']],
                         sorted([self.ids['companion'], self.ids['cache']]))
        observations = self.actions['spot'].resolution.observations
        self.assertEqual(len(observations), 1)
        self.assertEqual(observations[0].target_id, self.ids['cache'])


if __name__ == '__main__': unittest.main()
