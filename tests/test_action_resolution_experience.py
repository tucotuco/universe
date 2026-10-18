"""Action outcomes carry explicit evidence of actual skill exercise."""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath('../src'))

from action import Action
from encounter import Encounter
from experience import ActionResolution, SkillExercise
from library import Library
from universe import Universe


class ResultAction(Action):
    def __init__(self, universe, actor_id, target_id, result, start_time=0):
        super().__init__(universe, start_time, None, 'inspect', actor_id,
                         target_id, instrument_id=None)
        self.result = result
        self.end_time = start_time + 1
        self.calls = 0

    def resolve(self, difficulty_class):
        self.calls += 1
        return self.result


class TestActionResolutionExperience(unittest.TestCase):
    def setUp(self):
        self.universe = Universe(name='Skill exercises',
                                 library=Library(config_dir='../src/config'))
        self.actor_id = self.universe.make_being('Human', 'Learner')
        self.other_id = self.universe.make_being('Human', 'Target')
        self.actor = self.universe.get_object_by_id(self.actor_id)
        self.encounter = Encounter(self.universe, difficulty_class=10, start_time=0)
        self.encounter.add_being(self.actor_id)
        self.encounter.add_being(self.other_id)
        self.encounter.mark_aware(self.actor_id, self.other_id)
        self.encounter.decide_to_act(self.actor_id, self.other_id, 'inspect')

    def schedule(self, resolution):
        action = ResultAction(self.universe, self.actor_id, self.other_id, resolution,
                              start_time=self.encounter.time)
        self.encounter.schedule_action(action)
        return action

    def test_automatic_recording_and_progression_on_completion(self):
        action = self.schedule(ActionResolution('failure', (SkillExercise('run', 250),)))
        self.assertEqual(self.actor.get_skill_experience('run'), 0)
        completed = self.encounter.step().completed_action_ids
        self.assertEqual(completed, (action.id,))
        self.assertEqual(self.actor.get_skill_experience('run'), 250)
        self.assertEqual(self.actor.get_skill_level('run'), 1)
        record = self.actor.skill_use_history[-1]
        self.assertEqual((record.action_id, record.outcome, record.time),
                         (action.id, 'failure', 1))
        self.assertEqual(json.loads(action.to_json())['resolution'], {
            'outcome': 'failure',
            'skill_exercises': [{'skill_name': 'run', 'experience': 250}]})
        self.encounter.step()
        self.assertEqual(action.calls, 1)
        self.assertEqual(self.actor.get_skill_experience('run'), 250)

    def test_multiple_actual_skills_and_zero_xp_use(self):
        action = self.schedule(ActionResolution('partial', (
            SkillExercise('run', 100), SkillExercise('aerial combat', 0))))
        self.encounter.step()
        records = self.actor.skill_use_history
        self.assertEqual([(r.skill_name, r.experience, r.outcome) for r in records],
                         [('run', 100, 'partial'), ('aerial combat', 0, 'partial')])
        self.assertEqual([r.action_id for r in records], [action.id, action.id])
        self.assertIsNone(self.actor.get_skill_level('aerial combat'))

    def test_legacy_none_or_no_exercise_result_earns_no_xp(self):
        a = self.schedule(None)
        self.encounter.step()
        self.assertIsNone(json.loads(a.to_json())['resolution'])
        b = self.schedule(ActionResolution('success'))
        self.encounter.step()
        self.assertEqual(json.loads(b.to_json())['resolution']['outcome'], 'success')
        self.assertEqual(self.actor.skill_use_history, [])

    def test_invalid_practice_does_not_partially_apply_awards(self):
        action = self.schedule(ActionResolution('success', (
            SkillExercise('run', 250), SkillExercise('ki', 200))))
        with self.assertRaisesRegex(ValueError, 'prior training'):
            self.encounter.step()
        self.assertEqual(self.actor.get_skill_experience('run'), 0)
        self.assertEqual(self.actor.skill_use_history, [])
        self.assertIn(action.id, self.encounter.pending_action_list)
        self.assertNotIn(action.id, self.encounter.finished_action_list)
        self.assertIsNone(action.resolution)
        self.assertEqual(self.encounter.time, 0)

    def test_invalid_result_data_and_no_duplicate_skill(self):
        for value in (True, -1, 1.5):
            with self.assertRaises(ValueError):
                SkillExercise('run', value)
        with self.assertRaises(ValueError):
            ActionResolution('success', (SkillExercise('run'), SkillExercise('run')))
        with self.assertRaises(ValueError):
            ActionResolution('')
        with self.assertRaises(TypeError):
            ActionResolution('success', ('run',))

    def test_manual_award_was_recorded_so_auto_retry_is_rejected(self):
        action = self.schedule(ActionResolution('success', (SkillExercise('run', 250),)))
        # Existing public method only accepts a completed action, so simulate
        # historic practice attributed directly to the Being before the cycle.
        self.actor.record_skill_use(self.universe.get_skill_dictionary(), 'run',
                                    10, action_id=action.id, outcome='practice')
        with self.assertRaisesRegex(ValueError, 'already been recorded'):
            self.encounter.step()
        self.assertEqual(self.actor.get_skill_experience('run'), 10)
        self.assertIn(action.id, self.encounter.pending_action_list)


if __name__ == '__main__':
    unittest.main()
