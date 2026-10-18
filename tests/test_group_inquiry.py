"""An Agent's conflicting beliefs motivate a real follow-up Encounter Action."""
import json
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'examples')]

from field_observation import BeliefLedger, CountReport, FieldObservation, InquiryProposal
from field_inquiry import InquiryPolicy
from spatial.state import CartesianPosition
from group_inquiry_encounter import run_inquiry_scenario
from group_observation import SampledGroupObservation
from group_observation_encounter import run_scenario


def synthetic_observation(identifier, estimate, uncertainty=1, time=0):
    return FieldObservation(identifier, 'son', 'group', time,
                            CartesianPosition(0, 0, 0), 1.0,
                            {'dogs': CountReport(estimate, uncertainty)}, 'proxy')


class TestInquiryPolicy(unittest.TestCase):
    def test_conflict_selects_evidence_not_objective_truth(self):
        ledger = BeliefLedger('son')
        ledger.learn(synthetic_observation('first', 3, 1))
        ledger.learn(synthetic_observation('second', 9, 1))
        proposal = InquiryPolicy().propose(ledger, 'group', 10)
        self.assertEqual(proposal.category, 'dogs')
        self.assertEqual(proposal.reason, 'conflicting_reports')
        self.assertEqual(proposal.evidence_ids, ('first', 'second'))
        self.assertEqual(ledger.inquiry_history, ())  # proposal is not an Action
        ledger.record_inquiry(proposal, 'action-one')
        self.assertEqual(ledger.inquiry_history[0].proposal, proposal)
        exported = json.loads(json.dumps(ledger.to_dict()))
        self.assertEqual(exported['inquiry_history'][0]['action_id'], 'action-one')
        self.assertEqual(exported['inquiry_history'][0]['proposal']['evidence_ids'],
                         ['first', 'second'])
        self.assertEqual(len(ledger.belief_history), 2)  # decision != new belief

    def test_single_scout_can_request_followup_without_conflict(self):
        ledger = BeliefLedger('son')
        ledger.learn(synthetic_observation('one', 4, 4))
        proposal = InquiryPolicy(relative_uncertainty_threshold=0.7).propose(ledger, 'group', 5)
        self.assertEqual(proposal.reason, 'uncertain_estimate')
        self.assertEqual(proposal.evidence_ids, ('one',))
        self.assertIsNone(InquiryPolicy(relative_uncertainty_threshold=1.1).propose(
            ledger, 'group', 5))
        self.assertIsNone(InquiryPolicy().propose(ledger, 'unseen', 5))

    def test_rejects_fabricated_and_cross_observer_inquiries(self):
        ledger = BeliefLedger('son')
        ledger.learn(synthetic_observation('one', 4, 3))
        proposal = InquiryPolicy().propose(ledger, 'group', 1)
        with self.assertRaises(ValueError):
            ledger.record_inquiry(proposal, '')
        with self.assertRaises(ValueError):
            ledger.record_inquiry(InquiryProposal('father', 'group', 'dogs',
                                  proposal.reason, ('one',), 1), 'action')
        with self.assertRaises(ValueError):
            ledger.record_inquiry(InquiryProposal('son', 'group', 'dogs',
                                  proposal.reason, ('unknown',), 1), 'action')
        with self.assertRaises(ValueError):
            ledger.record_inquiry(InquiryProposal('son', 'group', 'horses',
                                  proposal.reason, ('one',), 1), 'action')
        ledger.record_inquiry(proposal, 'action')
        with self.assertRaises(ValueError):
            ledger.record_inquiry(proposal, 'action')
        with self.assertRaises(ValueError):
            InquiryPolicy().propose(ledger, 'group', -1)

    def test_focused_sensor_sharpens_uncertainty_only_in_chosen_category(self):
        scenario = run_scenario(seed=62)
        group = scenario['group']
        instrument = SampledGroupObservation(1000, 450)
        from random import Random
        first = instrument.sample(group, 'son', 101, 400, 1, 'first', Random(11))
        focused = instrument.sample(group, 'son', 101, 400, 1, 'second', Random(11),
                                    focus_category='humans')
        self.assertLessEqual(focused.reports['humans'].uncertainty,
                             first.reports['humans'].uncertainty)
        self.assertEqual(focused.reports['dogs'], first.reports['dogs'])
        self.assertEqual(focused.reports['livestock'], first.reports['livestock'])
        self.assertEqual(scenario['group'].materialized_count, 0)

    def test_inquiry_schedules_real_action_and_keeps_history(self):
        scenario = run_inquiry_scenario()
        proposal, action = scenario['proposal'], scenario['followup']
        self.assertIsNotNone(proposal)
        self.assertEqual(proposal.reason, 'conflicting_reports')
        self.assertEqual(proposal.category, 'humans')
        self.assertEqual(action.focus_category, proposal.category)
        self.assertIn(action.resolution.outcome, ('success', 'failure', 'out_of_range'))
        self.assertIn(action.id, scenario['result']['encounter'].finished_action_list)
        ledger = scenario['result']['ledgers']['son']
        self.assertEqual(ledger.inquiry_history[-1].action_id, action.id)
        self.assertEqual(ledger.inquiry_history[-1].proposal, proposal)
        self.assertEqual(scenario['result']['group'].materialized_count, 0)
        self.assertEqual(action.resolution.outcome, 'success')  # seeded fixture
        self.assertEqual(len(ledger.evidence), scenario['original_evidence_count'] + 1)
        self.assertEqual(action.field_observation.focus_category, proposal.category)
        self.assertEqual(json.loads(action.to_json())['focus_category'], proposal.category)
        self.assertGreaterEqual(scenario['result']['scouts']['son'].get_skill_experience('spot'), 36)

    def test_failed_followup_does_not_make_up_an_observation(self):
        # Use a specific random seed selected so the feasible skill check fails.
        failed = run_inquiry_scenario(followup_seed=0)
        self.assertEqual(failed['followup'].resolution.outcome, 'failure')
        self.assertEqual(len(failed['result']['ledgers']['son'].evidence),
                         failed['original_evidence_count'])
        self.assertIsNone(failed['followup'].field_observation)
        self.assertEqual(len(failed['result']['ledgers']['son'].inquiry_history), 1)


if __name__ == '__main__':
    unittest.main()
