"""Vertical-slice tests: Groups, Beings, Encounter, evidence and realization."""
from pathlib import Path
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'examples')]

from encounter import Encounter
from history_conversation import AskAboutPastAction
from integrated_discovery import propose_childhood, run_scenario
from personal_history import PersonalHistory
from realization import Fact, ImpossibleRealization
from spatial.state import CartesianPosition


class IntegratedDiscoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.first_run = run_scenario()

    def test_observer_interrogates_one_persistent_group_member(self):
        s = self.first_run
        herder, group, world = s['herder'], s['group'], s['world']
        self.assertIs(world.get_object_by_id(herder.id), herder)
        self.assertIs(group.realize_being(world, 0, 'adults', 0), herder)
        self.assertEqual(group.realized_being_count, 1)
        self.assertEqual(s['later_use'].time, 50)
        self.assertIn(s['later_use'], herder.skill_use_history)
        self.assertEqual(herder.get_skill_level('run'), 2)
        self.assertEqual(s['encounter'].time, 103)
        self.assertEqual(s['group'].time, 103)
        self.assertAlmostEqual(s['encounter'].distance_between_beings(
            s['observer'].id, herder.id), 2.0)

    def test_group_evidence_stays_fallible_and_agent_relative(self):
        s = self.first_run
        self.assertEqual(s['survey'].resolution.outcome, 'success')
        self.assertIsNotNone(s['survey'].field_observation)
        self.assertEqual(len(s['belief'].evidence), 1)
        self.assertEqual(s['belief'].observer_id, s['observer'].id)
        self.assertEqual(s['survey'].field_observation.observer_id, s['observer'].id)
        self.assertEqual(s['group'].realized_being_count, 1)
        # BeliefLedger is used for group count evidence only, not life history.
        self.assertNotIn('early_running', repr(s['belief'].to_dict()))

    def test_history_realized_by_first_question_only(self):
        s = self.first_run
        self.assertTrue(s['first'].newly_realized)
        self.assertFalse(s['second'].newly_realized)
        self.assertEqual(s['history'].reality.revision, 1)
        self.assertEqual(len(s['history'].facts_at(10)), 2)
        self.assertEqual(s['history'].reality.view().get(
            s['history'].skill_key(10, 'run')), 1)
        self.assertEqual(s['first'].heard_account.words,
                         s['history'].inspect_episode(10, 'early_running').value['description'])
        self.assertEqual(s['herder'].get_skill_level('run'), 2)
        self.assertEqual(s['herder'].skill_use_history, [s['later_use']])

    def test_heard_testimony_does_not_reveal_truth_value(self):
        s = self.first_run
        self.assertEqual(len(s['heard']), 2)
        self.assertNotEqual(s['heard'][0].words, s['heard'][1].words)
        self.assertEqual(s['heard'][0].speaker_id, s['herder'].id)
        self.assertEqual(s['heard'][0].listener_id, s['observer'].id)
        self.assertEqual(s['heard'][0].claimed_time, 10)
        self.assertLess(s['heard'][0].heard_at, s['heard'][1].heard_at)
        self.assertNotIn('true', s['heard'][1].to_dict())
        self.assertNotIn('deceptive', s['heard'][1].to_dict())
        # An independent out-of-world inspection can compare those claims.
        objective = s['history'].inspect_episode(10, 'early_running').value['description']
        self.assertNotEqual(s['heard'][1].words, objective)

    def test_encounter_owns_completed_conversations_and_perceptions(self):
        s = self.first_run
        for action in (s['survey'], s['first'], s['second']):
            self.assertIn(action.id, s['encounter'].finished_action_list)
            self.assertIs(s['world'].get_event_by_id(action.id), action)
        for action in (s['first'], s['second']):
            self.assertEqual(action.resolution.outcome, 'heard')
            self.assertEqual(action.resolution.observations[0].observer_id,
                             s['observer'].id)
        self.assertGreaterEqual(s['observer'].get_skill_experience('spot'), 12)

    def test_historical_group_state_unchanged_by_life_discovery(self):
        s = self.first_run
        earlier = s['group'].state_at(50)
        current = s['group'].state_at(100)
        life = s['history']
        already = life.realize_episode(10, 'early_running',
                    lambda view: self.fail('existing fact must not be generated'))
        self.assertFalse(already.newly_realized)
        self.assertEqual(s['group'].state_at(50), earlier)
        self.assertEqual(s['group'].state_at(100), current)

    def test_replay_new_world_uses_same_keyed_proposal_without_uuid_seeding(self):
        a = self.first_run
        b = run_scenario(seed=391)
        self.assertEqual(a['history'].inspect_episode(10, 'early_running').value,
                         b['history'].inspect_episode(10, 'early_running').value)
        # Choosing another world-generation seed MAY yield different detail;
        # nothing about the contract promises different choices for every seed.
        c = run_scenario(seed=392)
        self.assertTrue(c['history'].inspect_episode(10, 'early_running').value)

    def test_inadmissible_past_rejected_atomically(self):
        s = run_scenario()
        history = s['history']
        before = history.reality.revision
        key = history.episode_key(20, 'impossible_lesson')
        rank = history.skill_key(20, 'run')
        with self.assertRaises(ImpossibleRealization):
            history.realize_episode(20, 'impossible_lesson', lambda view: (
                Fact(key, {'description': 'Already expert', 'skill': 'run',
                           'rank_after': 3}, 'bad_proposal'),
                Fact(rank, 3, 'bad_proposal')))
        self.assertEqual(history.reality.revision, before)
        self.assertIsNone(history.inspect_episode(20, 'impossible_lesson'))

    def test_failed_range_gate_does_not_realize_history_or_record_testimony(self):
        s = run_scenario()
        speaker, observer, encounter = s['herder'], s['observer'], s['encounter']
        history = s['history']
        before = history.reality.revision
        received = list(s['heard'])
        observer.set_position(CartesianPosition(10000, 10000, 0))
        action = AskAboutPastAction(
            s['world'], observer.id, speaker.id, encounter.time,
            episode_time=20, topic='unanswered_question', max_distance=5,
            generate=lambda history, view: self.fail('no realization out of range'),
            received_accounts=received)
        encounter.schedule_action(action)
        encounter.step(1)
        self.assertEqual(action.resolution.outcome, 'out_of_range')
        self.assertIsNone(action.heard_account)
        self.assertEqual(len(received), 2)
        self.assertEqual(history.reality.revision, before)

    def test_unaware_listener_cannot_schedule_conversation(self):
        s = run_scenario()
        encounter = Encounter(s['world'], difficulty_class=10, start_time=104)
        observer, herder = s['observer'], s['herder']
        encounter.add_being(observer.id)
        encounter.add_being(herder.id)
        # Initiate via range detection then intentionally forget target.
        encounter.mark_aware(observer.id, herder.id)
        encounter.decide_to_act(observer.id, herder.id, 'talk')
        encounter.clear_awareness(observer.id, herder.id)
        action = AskAboutPastAction(s['world'], observer.id, herder.id, 104,
                                   episode_time=15, topic='unasked',
                                   generate=lambda *_: ())
        with self.assertRaises(ValueError):
            encounter.schedule_action(action)
        self.assertIsNone(s['history'].inspect_episode(15, 'unasked'))

    def test_committed_history_survives_export_and_testimony_serializes(self):
        s = self.first_run
        payload = json.loads(json.dumps(s['history'].to_jsonable()))
        restored = PersonalHistory.from_jsonable(s['herder'], payload)
        self.assertEqual(restored.inspect_episode(10, 'early_running'),
                         s['history'].inspect_episode(10, 'early_running'))
        report = json.loads(s['first'].to_json())
        self.assertEqual(report['heard_account']['words'], s['heard'][0].words)
        self.assertEqual(report['newly_realized'], True)
        self.assertNotIn('description', report)  # no objective audit field


if __name__ == '__main__':
    unittest.main()
