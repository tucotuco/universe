"""A real noncombat Action drives the complete Encounter->practice loop."""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath('../src'))

from activities import RunAction
from encounter import Encounter
from library import Library
from spatial.state import CartesianPosition
from universe import Universe


class TestRunningAction(unittest.TestCase):
    def setUp(self):
        self.universe = Universe(name='Runner', library=Library(config_dir='../src/config'))
        self.actor_id = self.universe.make_being('Human', 'Runner')
        self.target_id = self.universe.make_object('Brick', 'Marker')
        self.actor = self.universe.get_object_by_id(self.actor_id)
        self.marker = self.universe.get_object_by_id(self.target_id)
        self.actor.set_position(CartesianPosition(0, 0, 0))
        self.marker.set_position(CartesianPosition(12, 0, 0))
        self.encounter = Encounter(self.universe, difficulty_class=10, start_time=0)
        self.encounter.add_being(self.actor_id)
        self.encounter.add_object(self.target_id)
        self.encounter.mark_aware(self.actor_id, self.target_id)
        self.encounter.decide_to_act(self.actor_id, self.target_id, 'approach')

    def make_running(self, duration=2, minimum_distance=3, experience=250):
        action = RunAction(self.universe, self.actor_id, self.encounter.time,
                           duration, minimum_distance, experience)
        self.encounter.schedule_action(action)
        return action

    def test_completed_run_changes_position_records_history_and_advances(self):
        action = self.make_running()
        result = self.encounter.step(duration=1, velocities={self.actor_id: (2, 0, 0)})
        self.assertEqual(result.completed_action_ids, ())
        self.assertEqual(self.actor.get_skill_experience('run'), 0)
        result = self.encounter.step(duration=1, velocities={self.actor_id: (2, 0, 0)})
        self.assertEqual(result.completed_action_ids, (action.id,))
        self.assertEqual(self.actor.get_position(), CartesianPosition(4, 0, 0))
        self.assertEqual(action.displacement, 4)
        self.assertEqual(action.resolution.outcome, 'success')
        self.assertEqual(self.actor.get_skill_experience('run'), 250)
        self.assertEqual(self.actor.get_skill_level('run'), 1)
        self.assertEqual(len(self.actor.skill_use_history), 1)
        self.assertEqual(self.actor.skill_use_history[0].action_id, action.id)
        self.assertEqual(self.actor.skill_use_history[0].time, 2)
        self.assertEqual(json.loads(action.to_json())['resolution']['outcome'], 'success')
        self.assertEqual(json.loads(action.to_json())['displacement'], 4.0)
        self.assertEqual(json.loads(action.to_json())['minimum_distance'], 3.0)
        self.encounter.step()
        self.assertEqual(self.actor.get_skill_experience('run'), 250)

    def test_partial_run_exercises_skill_at_configured_award(self):
        action = self.make_running(minimum_distance=10, experience=7)
        self.encounter.step(duration=2, velocities={self.actor_id: (1, 0, 0)})
        self.assertEqual(action.resolution.outcome, 'partial')
        self.assertEqual(action.displacement, 2)
        self.assertEqual(self.actor.get_skill_experience('run'), 7)
        self.assertEqual(self.actor.get_skill_level('run') or 0, 0)

    def test_two_real_actions_accumulate_experience_without_definition_change(self):
        original_definition = self.actor.original.get_skill_level('run')
        first = self.make_running(duration=1, minimum_distance=1, experience=100)
        self.encounter.step(duration=1, velocities={self.actor_id: (1, 0, 0)})
        second = self.make_running(duration=1, minimum_distance=1, experience=150)
        self.encounter.step(duration=1, velocities={self.actor_id: (1, 0, 0)})
        self.assertEqual([first.resolution.outcome, second.resolution.outcome],
                         ['success', 'success'])
        self.assertEqual(self.actor.get_skill_experience('run'), 250)
        self.assertEqual(self.actor.get_skill_level('run'), 1)
        self.assertEqual(len(self.actor.skill_use_history), 2)
        self.assertEqual(self.actor.original.get_skill_level('run'), original_definition)

    def test_no_movement_no_award(self):
        action = self.make_running(experience=250)
        self.encounter.step(duration=2)
        self.assertEqual(action.resolution.outcome, 'no_movement')
        self.assertEqual(self.actor.skill_use_history, [])
        self.assertEqual(self.actor.get_skill_experience('run'), 0)

    def test_pre_scheduling_movement_does_not_count(self):
        action = RunAction(self.universe, self.actor_id, 0, 1, 2, 250)
        self.actor.set_position(CartesianPosition(50, 0, 0))
        self.encounter.schedule_action(action)
        self.encounter.step(duration=1)
        self.assertEqual(action.resolution.outcome, 'no_movement')

    def test_future_schedule_rejected_without_registering_event(self):
        action = RunAction(self.universe, self.actor_id, 1, 2, 2, 250)
        with self.assertRaisesRegex(ValueError, 'scheduling time'):
            self.encounter.schedule_action(action)
        self.assertNotIn(action.id, self.encounter.pending_action_list)
        self.assertIsNone(self.universe.get_event_by_id(action.id))
        self.assertIsNone(action.start_position)

    def test_requires_position(self):
        self.actor.set_spatial_state(None)
        action = RunAction(self.universe, self.actor_id, 0, 1, 2)
        with self.assertRaisesRegex(ValueError, 'positioned'):
            self.encounter.schedule_action(action)
        self.assertIsNone(action.start_position)

    def test_invalid_parameters(self):
        for value in (0, -1, float('inf'), float('nan'), True):
            with self.assertRaises(ValueError):
                RunAction(self.universe, self.actor_id, 0, value, 1)
            with self.assertRaises(ValueError):
                RunAction(self.universe, self.actor_id, 0, 1, value)
        for award in (True, -3, 3.5):
            with self.assertRaises(ValueError):
                RunAction(self.universe, self.actor_id, 0, 1, 1, award)


if __name__ == '__main__':
    unittest.main()
