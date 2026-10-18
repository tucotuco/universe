"""Evidence-based skill practice and advancement, independent of terrain or AI."""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath('../src'))

from action import Action
from being import BeingDefinition, BeingInstance
from encounter import Encounter
from library import Library
from universe import Universe


class SkillExperienceTests(unittest.TestCase):
    def setUp(self):
        self.universe = Universe(name='Practice', library=Library(config_dir='../src/config'))
        self.skills = self.universe.get_skill_dictionary()
        self.definition = BeingDefinition('Human', 6, 170, 10, '2d6',
                                          'Neutral', 10, 1)
        self.being = BeingInstance(self.definition, 'Learner')
        self.universe.add_object(self.being)

    def test_practice_records_evidence_and_grows_progressive_skill(self):
        a = self.being.record_skill_use(self.skills, 'run', 249,
                                        action_id='a1', time=2, outcome='success')
        self.assertEqual((a.level_before, a.level_after), (0, 0))
        b = self.being.record_skill_use(self.skills, 'run', 1,
                                        action_id='a2', time=3, outcome='failure')
        self.assertEqual((b.level_before, b.level_after), (0, 1))
        self.assertEqual(self.being.get_skill_level('run'), 1)
        c = self.being.record_skill_use(self.skills, 'run', 500)
        self.assertEqual((c.level_before, c.level_after), (1, 2))
        self.assertEqual(self.being.get_skill_experience('run'), 750)
        self.assertIsNone(self.definition.get_skill_level('run'))
        self.assertEqual(len(self.being.skill_use_history), 3)
        saved = json.loads(self.being.to_json())
        self.assertEqual(saved['skill_use_history'][0]['action_id'], 'a1')
        self.assertEqual(saved['skill_experience']['run'], 750)
        self.assertEqual(saved['skill_practice_baselines']['run'], 0)

    def test_starting_skill_level_is_respected(self):
        self.being.set_skill_level(self.skills, 'run', 2)
        self.being.record_skill_use(self.skills, 'run', 749)
        self.assertEqual(self.being.get_skill_level('run'), 2)
        entry = self.being.record_skill_use(self.skills, 'run', 1)
        self.assertEqual(entry.level_after, 3)
        self.assertEqual(self.being.original.get_skill_level('run'), None)

    def test_nonprogressive_skill_records_use_without_advancement(self):
        self.being.record_skill_use(self.skills, 'aerial combat', 2000)
        self.assertEqual(self.being.get_skill_experience('aerial combat'), 2000)
        self.assertIsNone(self.being.get_skill_level('aerial combat'))

    def test_extraordinary_requires_prior_learning(self):
        with self.assertRaises(ValueError):
            self.being.record_skill_use(self.skills, 'ki', 100)
        self.being.set_skill_level(self.skills, 'ki', 1)
        self.being.record_skill_use(self.skills, 'ki', 500)
        self.assertEqual(self.being.get_skill_level('ki'), 2)

    def test_validation_and_duplicate_awards(self):
        for award in (-1, 1.5, True):
            with self.assertRaises(ValueError):
                self.being.record_skill_use(self.skills, 'run', award)
        with self.assertRaises(ValueError):
            self.being.record_skill_use(self.skills, 'nonexistent', 0)
        with self.assertRaises(ValueError):
            self.being.record_skill_use(self.skills, 'run', 1, time=float('nan'))
        self.being.record_skill_use(self.skills, 'run', 20, action_id='same')
        with self.assertRaises(ValueError):
            self.being.record_skill_use(self.skills, 'run', 25, action_id='same')
        self.assertEqual(self.being.get_skill_experience('run'), 20)

    def test_reset_clears_practice_and_levels(self):
        self.being.record_skill_use(self.skills, 'run', 250)
        self.being.reset()
        self.assertEqual(self.being.get_skill_experience('run'), 0)
        self.assertEqual(self.being.skill_use_history, [])
        self.assertIsNone(self.being.get_skill_level('run'))

    def test_encounter_only_credits_completed_action(self):
        other = BeingInstance(self.definition, 'Target')
        self.universe.add_object(other)
        encounter = Encounter(self.universe, difficulty_class=10, start_time=0)
        encounter.add_being(self.being.id)
        encounter.add_being(other.id)
        encounter.mark_aware(self.being.id, other.id)
        encounter.decide_to_act(self.being.id, other.id, 'approach')
        action = Action(self.universe, 0, 1, 'inspect', self.being.id,
                        other.id, instrument_id=None)
        action.end_time = 1
        action.resolve = lambda difficulty_class: None
        encounter.schedule_action(action)
        with self.assertRaises(ValueError):
            encounter.record_skill_use(action.id, 'run', 250)
        step = encounter.step(1)
        self.assertIn(action.id, step.completed_action_ids)
        recorded = encounter.record_skill_use(action.id, 'run', 250, outcome='success')
        self.assertEqual(recorded.action_id, action.id)
        self.assertEqual(recorded.time, 1)
        self.assertEqual(self.being.get_skill_level('run'), 1)
        with self.assertRaises(ValueError):
            encounter.record_skill_use(action.id, 'run', 250)
        # An action should not silently credit a skill just by being completed.
        self.assertEqual(self.being.get_skill_experience('run'), 250)


if __name__ == '__main__':
    unittest.main()
