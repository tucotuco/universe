"""Cognitive spotting exercise with earned skill improvement and awareness."""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath('../src'))

from activities import SpotAction
from encounter import Encounter
from experience import ActionResolution, SkillExercise
from library import Library
from perception import Perception
from spatial import AxisAlignedBox, CartesianPosition, Sphere, VisualOcclusion
from universe import Universe

P = CartesianPosition


class TestSpotAction(unittest.TestCase):
    def setUp(self):
        self.world = Universe('Spotting', library=Library(config_dir='../src/config'))
        self.observer_id = self.world.make_being('Human', 'Observer')
        self.partner_id = self.world.make_being('Human', 'Known partner')
        self.target_id = self.world.make_object('Brick', 'Hidden object')
        self.observer = self.world.get_object_by_id(self.observer_id)
        self.partner = self.world.get_object_by_id(self.partner_id)
        self.target = self.world.get_object_by_id(self.target_id)
        self.observer.set_position(P(0, 0, 0))
        self.partner.set_position(P(0, 5, 0))
        self.partner.set_geometry(Sphere(.5))
        self.target.set_position(P(10, 0, 0))
        self.target.set_geometry(Sphere(.5))
        self.encounter = Encounter(self.world, difficulty_class=11, start_time=0)
        for being_id in (self.observer_id, self.partner_id):
            self.encounter.add_being(being_id)
        self.encounter.add_object(self.target_id)
        self.encounter.mark_aware(self.observer_id, self.partner_id)
        self.encounter.decide_to_act(self.observer_id, self.partner_id, 'look around')

    def attempt(self, roll=10, experience=0, distance=20):
        action = SpotAction(self.world, self.observer_id, self.target_id,
                            self.encounter.time, duration=1,
                            max_distance=distance,
                            experience=experience, die_roll=roll)
        self.encounter.schedule_action(action)
        return action

    def test_failure_then_progression_enables_success_with_same_roll(self):
        definition = self.world.get_being_definition('Human')
        self.assertIsNotNone(definition)
        self.assertFalse(self.encounter.is_aware(self.observer_id, self.target_id))
        first = self.attempt(roll=10, experience=250)
        self.assertEqual(self.encounter.step().completed_action_ids, (first.id,))
        self.assertEqual(first.resolution.outcome, 'failure')
        self.assertFalse(self.encounter.is_aware(self.observer_id, self.target_id))
        self.assertEqual(self.observer.get_skill_level('spot'), 1)
        self.assertEqual(self.observer.get_skill_experience('spot'), 250)
        second = self.attempt(roll=10, experience=0)
        self.encounter.step()
        self.assertEqual(second.resolution.outcome, 'success')
        self.assertEqual(second.skill_level_used, 1)
        self.assertTrue(self.encounter.is_aware(self.observer_id, self.target_id))
        self.assertFalse(self.encounter.is_aware(self.partner_id, self.target_id))
        self.assertEqual([h.action_id for h in self.observer.skill_use_history],
                         [first.id, second.id])
        self.assertEqual([h.outcome for h in self.observer.skill_use_history],
                         ['failure', 'success'])
        self.assertIsNone(definition.get_skill_level('spot'))  # no mutation of original
        data = json.loads(second.to_json())
        self.assertEqual(data['skill_level_used'], 1)
        self.assertEqual(data['roll'], 10)
        self.assertEqual(data['path_status'], 'clear')
        self.assertEqual(data['resolution']['observations'][0]['target_id'], self.target_id)

    def test_observation_is_not_applied_until_action_finishes(self):
        action = SpotAction(self.world, self.observer_id, self.target_id, 0,
                            duration=2, die_roll=20)
        self.encounter.schedule_action(action)
        self.encounter.step(duration=1)
        self.assertFalse(self.encounter.is_aware(self.observer_id, self.target_id))
        self.encounter.step(duration=1)
        self.assertTrue(self.encounter.is_aware(self.observer_id, self.target_id))

    def test_opaque_obstacle_precludes_spotting_regardless_of_roll(self):
        blocker_id = self.world.make_object('Brick', 'Wall')
        wall = self.world.get_object_by_id(blocker_id)
        wall.set_position(P(5, 0, 0))
        wall.set_geometry(AxisAlignedBox(1, 2, 2))
        wall.set_visual_occlusion(VisualOcclusion(1))
        self.encounter.add_object(blocker_id)
        action = self.attempt(roll=20, experience=10)
        self.encounter.step()
        self.assertEqual(action.resolution.outcome, 'no_clear_path')
        self.assertEqual(action.path_status, 'blocked')
        self.assertIsNone(action.roll)
        self.assertFalse(self.encounter.is_aware(self.observer_id, self.target_id))
        self.assertEqual(self.observer.get_skill_experience('spot'), 10)

    def test_unknown_and_partial_optics_do_not_justify_awareness(self):
        blocker_id = self.world.make_object('Brick', 'Obstacle')
        blocker = self.world.get_object_by_id(blocker_id)
        blocker.set_position(P(5, 0, 0))
        blocker.set_geometry(Sphere(1))
        self.encounter.add_object(blocker_id)
        action = self.attempt(roll=20)
        self.encounter.step()
        self.assertEqual(action.path_status, 'unknown')
        self.assertFalse(self.encounter.is_aware(self.observer_id, self.target_id))
        blocker.set_visual_occlusion(VisualOcclusion(.5))
        action = self.attempt(roll=20)
        self.encounter.step()
        self.assertEqual(action.path_status, 'partial')
        self.assertFalse(self.encounter.is_aware(self.observer_id, self.target_id))

    def test_out_of_range_and_missing_geometry(self):
        action = self.attempt(roll=20, distance=5)
        self.encounter.step()
        self.assertEqual(action.resolution.outcome, 'out_of_range')
        self.target.set_geometry(None)
        action = self.attempt(roll=20)
        self.encounter.step()
        self.assertEqual(action.resolution.outcome, 'unmodeled_target')
        self.assertFalse(self.encounter.is_aware(self.observer_id, self.target_id))

    def test_natural_one_fails_and_twenty_succeeds(self):
        self.observer.set_skill_level(self.world.get_skill_dictionary(), 'spot', 20)
        first = self.attempt(roll=1)
        self.encounter.step()
        self.assertEqual(first.resolution.outcome, 'failure')
        self.observer.set_skill_level(self.world.get_skill_dictionary(), 'spot', 0)
        self.encounter.difficulty_class = 100
        second = self.attempt(roll=20)
        self.encounter.step()
        self.assertEqual(second.resolution.outcome, 'success')

    def test_preflight_invalid_observation_does_not_award_experience(self):
        from action import Action

        class BadAction(Action):
            def __init__(self, universe, actor_id):
                super().__init__(universe, 0, None, 'bad', actor_id, None, None)
                self.end_time = 1

            def resolve(self, dc):
                return ActionResolution('success', (SkillExercise('spot', 250),),
                                        (Perception(self.partner_id, self.target_id, 'fake', 1, 10),))

        action = BadAction(self.world, self.observer_id)
        action.partner_id = self.partner_id
        action.target_id = self.target_id
        self.encounter.schedule_action(action)
        with self.assertRaisesRegex(ValueError, 'must belong to its actor'):
            self.encounter.step()
        self.assertEqual(self.observer.get_skill_experience('spot'), 0)
        self.assertFalse(self.encounter.is_aware(self.observer_id, self.target_id))
        self.assertIn(action.id, self.encounter.pending_action_list)

    def test_spot_input_validation(self):
        for kwargs in ({'die_roll': 0}, {'die_roll': 1.5}, {'die_roll': True},
                       {'max_distance': -1}, {'duration': 0}, {'experience': -1}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                SpotAction(self.world, self.observer_id, self.target_id, 0, **kwargs)
        with self.assertRaises(ValueError):
            SpotAction(self.world, self.observer_id, self.observer_id, 0)


if __name__ == '__main__':
    unittest.main()
