"""User-choice integration tests for evidence, realization, and exploration."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'examples')]

from interactive_discovery import ExplorerSession, play
from personal_history import PersonalHistory
from spatial.state import CartesianPosition


class InteractiveDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.explorer = ExplorerSession(seed=391)

    def test_passive_inquiry_does_not_realize_episode_or_evidence(self):
        session = self.explorer
        initial = session.scene['history'].reality.revision
        initial_time = session.time
        for cmd in ('look', 'notes', 'compare', 'help', '', 'ask alien',
                    'observe rocks', 'wait 0', 'wait 21', 'audit', 'unknown'):
            self.assertIsInstance(session.execute(cmd), str)
        self.assertEqual(session.scene['history'].reality.revision, initial)
        self.assertEqual(session.time, initial_time)
        self.assertEqual(len(session.scene['belief'].evidence), 0)
        self.assertEqual(len(session.scene['heard']), 0)
        self.assertIn('no evidence', session.execute('notes').lower())
        self.assertIn('Unknown command', session.execute('audit'))

    def test_first_question_realizes_only_selected_history_and_retains_current_being(self):
        session = self.explorer
        s = session.scene
        before_state = s['herder'].get_skill_level('run')
        before_uses = tuple(s['herder'].skill_use_history)
        historical_groups = (s['group'].state_at(50), s['group'].state_at(100))
        text = session.execute('ask childhood')
        episode = s['history'].inspect_episode(10, 'early_running')
        self.assertIsNotNone(episode)
        self.assertIn(episode.value['description'], text)
        self.assertIsNone(s['history'].inspect_episode(20, 'later_running'))
        self.assertEqual(s['history'].reality.revision, 1)
        self.assertEqual(s['herder'].get_skill_level('run'), before_state)
        self.assertEqual(tuple(s['herder'].skill_use_history), before_uses)
        self.assertEqual((s['group'].state_at(50), s['group'].state_at(100)),
                         historical_groups)
        self.assertEqual(s['group'].time, s['encounter'].time)
        self.assertIn(session.questions[0].id, s['encounter'].finished_action_list)

    def test_chosen_question_order_does_not_discard_prior_history(self):
        session = self.explorer
        session.execute('ask later')
        history = session.scene['history']
        later = history.inspect_episode(20, 'later_running')
        self.assertIsNotNone(later)
        self.assertIsNone(history.inspect_episode(10, 'early_running'))
        session.execute('ask childhood')
        self.assertEqual(history.inspect_episode(20, 'later_running'), later)
        self.assertEqual(history.reality.revision, 2)
        self.assertEqual(len(history.facts_at(20)), 2)
        self.assertEqual(len(history.facts_at(10)), 2)
        # Established later run rank of 2 is respected by both episodes.
        self.assertEqual(session.scene['herder'].get_skill_level('run'), 2)

    def test_repeated_account_can_conflict_without_recommitting_or_truth_leak(self):
        session = self.explorer
        session.execute('ask childhood')
        before = session.scene['history'].reality.revision
        second = session.execute('ask childhood')
        self.assertEqual(before, session.scene['history'].reality.revision)
        self.assertIn('alone', second)
        self.assertIn('conflicting accounts', session.execute('compare'))
        self.assertIn('Account 2', session.execute('notes'))
        accounts = session.scene['heard']
        self.assertNotEqual(accounts[0].words, accounts[1].words)
        for account in accounts:
            self.assertNotIn('truth', account.to_dict())
            self.assertNotIn('deceptive', account.to_dict())
        # Only a developer-only out-of-world API can read objective history.
        self.assertIn('Learned to run', session.developer_audit())
        self.assertNotIn('[Developer audit', session.execute('notes'))
        self.assertNotIn('[Developer audit', session.execute('compare'))

    def test_repeated_reconsideration_is_passive(self):
        session = self.explorer
        session.execute('ask childhood')
        revision = session.scene['history'].reality.revision
        for _ in range(4):
            session.execute('notes')
            session.execute('compare')
            session.execute('look')
        self.assertEqual(revision, session.scene['history'].reality.revision)
        self.assertEqual(session.time, 101)

    def test_observe_is_encounter_action_and_evidence_not_truth(self):
        session = self.explorer
        messages = [session.execute('observe humans') for _ in range(5)]
        self.assertTrue(any('estimated humans' in msg for msg in messages))
        self.assertEqual(len(session.observations), 5)
        self.assertEqual(session.time, 105)
        self.assertEqual(session.scene['group'].time, session.time)
        belief = session.scene['belief']
        self.assertGreater(len(belief.evidence), 0)
        self.assertEqual(belief.observer_id, session.scene['observer'].id)
        for action in session.observations:
            self.assertIn(action.id, session.scene['encounter'].finished_action_list)
            if action.field_observation is not None:
                self.assertEqual(action.field_observation.observer_id, belief.observer_id)
        self.assertIn('Observation 1', session.execute('notes'))
        self.assertEqual(session.scene['history'].reality.revision, 0)

    def test_not_following_means_real_separation_and_failed_question_is_not_realized(self):
        session = self.explorer
        s = session.scene
        a, b = s['observer'].get_position(), s['herder'].get_position()
        self.assertAlmostEqual(s['encounter'].distance_between_beings(
            s['observer'].id, s['herder'].id), 2.0)
        session.execute('follow off')
        session.execute('wait 20')
        self.assertEqual(s['observer'].get_position(), a)
        self.assertGreater(s['encounter'].distance_between_beings(
            s['observer'].id, s['herder'].id), 10)
        result = session.execute('ask childhood')
        self.assertIn('out_of_range', result)
        self.assertIsNone(s['history'].inspect_episode(10, 'early_running'))
        self.assertEqual(len(s['heard']), 0)
        self.assertEqual(s['group'].time, s['encounter'].time)

    def test_following_is_explicit_and_group_encounter_clocks_stay_aligned(self):
        session = self.explorer
        s = session.scene
        session.execute('wait 10')
        self.assertAlmostEqual(s['encounter'].distance_between_beings(
            s['observer'].id, s['herder'].id), 2.0)
        self.assertEqual(session.time, 110)
        self.assertEqual(s['group'].time, 110)
        session.execute('follow off')
        session.execute('wait 10')
        self.assertGreater(s['encounter'].distance_between_beings(
            s['observer'].id, s['herder'].id), 10)

    def test_evidence_from_failed_actions_does_not_enter_notebook(self):
        session = self.explorer
        session.scene['observer'].set_position(CartesianPosition(10000, 10000, 0))
        text = session.execute('observe dogs')
        self.assertIn('out_of_range', text)
        self.assertEqual(len(session.scene['belief'].evidence), 0)
        self.assertEqual(session.scene['history'].reality.revision, 0)

    def test_invalid_commands_and_quit_do_not_generate(self):
        session = self.explorer
        session.execute('not an action')
        self.assertEqual(session.time, 100)
        self.assertIn('leave the encounter', session.execute('quit'))
        self.assertTrue(session.closed)
        self.assertIn('ended', session.execute('ask childhood'))
        self.assertEqual(session.scene['history'].reality.revision, 0)

    def test_scripted_interface_omits_objective_audit_by_default(self):
        printed = []
        commands = ['notes', 'ask childhood', 'ask childhood', 'compare', 'quit']
        scene = play(seed=391, output_fn=printed.append, commands=commands)
        report = '\n'.join(printed)
        self.assertEqual(len(scene.scene['heard']), 2)
        self.assertIn('conflicting accounts', report)
        self.assertNotIn('Developer audit', report)
        self.assertNotIn('rank_after', report)
        self.assertTrue(scene.closed)

    def test_audit_only_when_explicitly_requested(self):
        printed = []
        session = play(seed=391, output_fn=printed.append,
                       commands=['ask childhood', 'quit'], audit=True)
        report = '\n'.join(printed)
        self.assertIn('Developer audit', report)
        self.assertIn('later: unresolved', report)
        self.assertIsNotNone(session.scene['history'].inspect_episode(10, 'early_running'))

    def test_session_keeps_same_world_identity_across_commands(self):
        session = self.explorer
        s = session.scene
        original = s['herder']
        session.execute('observe livestock')
        session.execute('ask childhood')
        session.execute('ask later')
        self.assertIs(s['world'].get_object_by_id(original.id), original)
        self.assertIs(s['group'].realize_being(s['world'], 0, 'adults', 0), original)
        self.assertEqual(s['group'].realized_being_count, 1)
        restored = PersonalHistory.from_jsonable(original, s['history'].to_jsonable())
        self.assertEqual(restored.inspect_episode(10, 'early_running'),
                         s['history'].inspect_episode(10, 'early_running'))


if __name__ == '__main__':
    unittest.main()
