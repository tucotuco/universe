"""Opt-in retrospective Being history, grounded by later skill-use Events."""
from pathlib import Path
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src')]

from being import BeingDefinition, BeingInstance
from library import Library
from personal_history import PersonalHistory
from realization import Fact, FactKey, ImpossibleRealization
from statistical_group import StatisticalGroup
from universe import Universe


def make_being():
    definition = BeingDefinition('Human', 6, 170, 10, '2d6', 'Neutral', 10, 1)
    return BeingInstance(definition, 'Explorer')


class PersonalHistoryTests(unittest.TestCase):
    def setUp(self):
        self.being = make_being()
        self.world = Universe('History', library=Library(config_dir=str(ROOT/'src/config')))
        self.world.add_object(self.being)
        self.skills = self.world.get_skill_dictionary()

    def history(self):
        return self.being.begin_personal_history(
            earliest=0, known_through=90, nondeclining_skills=('run',))

    @staticmethod
    def episode(history, time=10, rank=1):
        return lambda view: (
            Fact(history.episode_key(time, 'first_running_lessons'),
                 {'description': 'Learned to run along the river',
                  'skill': 'run', 'rank_after': rank}, 'conditional_history'),
            Fact(history.skill_key(time, 'run'), rank, 'conditional_history'),
        )

    def test_inspect_does_not_realize_and_repeated_inquiry_is_idempotent(self):
        self.being.set_skill_level(self.skills, 'run', 2)
        use = self.being.record_skill_use(self.skills, 'run', 0,
                                          time=50, action_id='later-run')
        self.assertEqual(use.level_before, 2)
        history = self.history()
        self.assertIsNone(history.inspect_episode(10, 'first_running_lessons'))
        self.assertEqual(history.facts_at(10), ())
        self.assertEqual(history.reality.revision, 0)
        first = history.realize_episode(10, 'first_running_lessons', self.episode(history))
        self.assertTrue(first.newly_realized)
        self.assertEqual(first.record.value['rank_after'], 1)
        self.assertEqual(len(history.facts_at(10)), 2)
        self.assertEqual(history.reality.revision, 1)
        second = history.realize_episode(10, 'first_running_lessons',
                                         lambda view: self.fail('generator should not run'))
        self.assertFalse(second.newly_realized)
        self.assertEqual(second.record, first.record)
        self.assertEqual(self.being.get_skill_level('run'), 2)
        self.assertEqual(self.being.skill_use_history, [use])

    def test_later_practice_rules_out_incompatible_earlier_rank_atomically(self):
        self.being.set_skill_level(self.skills, 'run', 2)
        self.being.record_skill_use(self.skills, 'run', 0, time=50)
        history = self.history()
        with self.assertRaises(ImpossibleRealization):
            history.realize_episode(10, 'first_running_lessons', self.episode(history, rank=3))
        self.assertEqual(history.reality.revision, 0)
        self.assertIsNone(history.inspect_episode(10, 'first_running_lessons'))
        accepted = history.realize_episode(10, 'first_running_lessons', self.episode(history))
        self.assertEqual(accepted.record.value['rank_after'], 1)
        with self.assertRaises(ImpossibleRealization):
            history.commit_skill_rank(10, 'run', 3)
        self.assertEqual(history.reality.revision, 1)

    def test_later_history_may_constrain_but_does_not_determine_episodes(self):
        self.being.record_skill_use(self.skills, 'run', 0, time=50)
        history = self.history()
        key = history.episode_key(5, 'childhood_trip')
        history.realize_episode(5, 'childhood_trip', lambda view: (
            Fact(key, {'description': 'Visited a neighboring village'}, 'history_generator'),))
        self.assertEqual(history.reality.revision, 1)
        self.assertEqual(history.facts_at(50), ())  # practice history is not copied
        self.assertEqual(len(self.being.skill_use_history), 1)

    def test_training_episode_requires_matching_rank_in_same_transaction(self):
        history = self.history()
        key = history.episode_key(10, 'first_running_lessons')
        with self.assertRaises(ImpossibleRealization):
            history.realize_episode(10, 'first_running_lessons', lambda view: (
                Fact(key, {'description': 'Training', 'skill': 'run', 'rank_after': 1}),))
        self.assertEqual(history.reality.revision, 0)
        history.realize_episode(10, 'first_running_lessons', self.episode(history))
        with self.assertRaises(ImpossibleRealization):
            history.commit_skill_rank(20, 'run', 0)

    def test_a_later_action_cannot_invalidate_an_earlier_commitment(self):
        history = self.history()
        history.realize_episode(10, 'first_running_lessons', self.episode(history, rank=2))
        self.assertEqual(self.being.get_skill_experience('run'), 0)
        with self.assertRaises(ImpossibleRealization):
            self.being.record_skill_use(self.skills, 'run', 250,
                                        action_id='incompatible', time=50)
        self.assertEqual(self.being.get_skill_experience('run'), 0)
        self.assertEqual(self.being.skill_use_history, [])
        self.assertIsNone(self.being.get_skill_level('run'))
        self.being.set_skill_level(self.skills, 'run', 2)
        allowed = self.being.record_skill_use(self.skills, 'run', 0,
                                              action_id='compatible', time=50)
        self.assertEqual(allowed.level_before, 2)

    def test_history_enforces_consistent_order_and_time_bounds(self):
        history = self.history()
        for t in (-1, 91, float('nan'), 'unknown', True):
            with self.subTest(t=t), self.assertRaises(ValueError):
                history.episode_key(t, 'story')
        with self.assertRaises(ValueError):
            history.skill_key(3, 'spot')
        history.commit_skill_rank(10, 'run', 2)
        with self.assertRaises(ImpossibleRealization):
            history.commit_skill_rank(20, 'run', 1)
        history.commit_skill_rank(20, 'run', 2)
        self.assertEqual(history.reality.revision, 2)

    def test_export_restore_checks_original_being_and_objective_events(self):
        self.being.set_skill_level(self.skills, 'run', 2)
        self.being.record_skill_use(self.skills, 'run', 0, time=50)
        history = self.history()
        history.realize_episode(10, 'first_running_lessons', self.episode(history))
        payload = json.loads(json.dumps(history.to_jsonable()))
        reloaded = PersonalHistory.from_jsonable(self.being, payload)
        self.assertEqual(reloaded.reality.revision, history.reality.revision)
        self.assertEqual(reloaded.inspect_episode(10, 'first_running_lessons'),
                         history.inspect_episode(10, 'first_running_lessons'))
        self.assertIn('personal_history', json.loads(self.being.to_json()))
        with self.assertRaises(ValueError):
            PersonalHistory.from_jsonable(make_being(), payload)
        conflict = json.loads(json.dumps(payload))
        for fact in conflict['facts']:
            if fact['attribute'] == 'skill_rank':
                fact['value'] = 3
        with self.assertRaises(ImpossibleRealization):
            PersonalHistory.from_jsonable(self.being, conflict)

    def test_reset_rejects_discarding_committed_history(self):
        history = self.history()
        history.realize_episode(10, 'first_running_lessons', self.episode(history))
        with self.assertRaises(ValueError):
            self.being.reset()
        self.assertIs(self.being.personal_history, history)
        self.assertEqual(history.reality.revision, 1)
        new_being = make_being()
        new_being.begin_personal_history(earliest=0, known_through=80)
        new_being.reset()  # uncommitted scaffold may be reset
        self.assertIsNone(new_being.personal_history)

    def test_realized_group_member_retains_personal_history_across_departure(self):
        config = json.loads((ROOT/'examples/nomadic_group.json').read_text())
        group = StatisticalGroup('Nomads', 'nomads', config, 81)
        self.world.add_object(group)
        being = group.realize_being(self.world, 0, 'adults', 0)
        self.assertIs(being, self.world.get_object_by_id(being.id))
        being.set_skill_level(self.skills, 'run', 2)
        group.advance(60)
        being.record_skill_use(self.skills, 'run', 0, time=50, action_id='long-run')
        group.counts()  # explicitly commit the original composition before comparison
        historical = group.state_at(20)
        life = being.begin_personal_history(earliest=-15, known_through=60,
                                            nondeclining_skills=('run',))
        life.realize_episode(10, 'first_running_lessons', self.episode(life))
        self.assertEqual(historical, group.state_at(20))
        group.leave_being(self.world, being)
        self.assertEqual(group.state_at(50)['current_composition']['adults'],
                         group.counts()['adults'])
        self.assertEqual(group.current_counts()['adults'], group.counts()['adults'] - 1)
        self.assertIs(being.personal_history, life)
        self.assertIs(group.realize_being(self.world, 0, 'adults', 0), being)


if __name__ == '__main__':
    unittest.main()
