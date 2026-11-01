"""One observer-2 Belief-driven follow-up through boundary-3 publication."""
import random
import sys
import unittest
from unittest.mock import patch

ROOT = __import__('pathlib').Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'examples')]

from atomic_publication import PublicationFailure
from field_inquiry import InquiryPolicy
from field_observation import BeliefLedger
from spatial_group_observation import _build_scenario
from spatial_two_observers import _schedule_second_observation
from spatial_belief_inquiry import _decide, run_scenario, demo_data


def _to_boundary_two():
    result = _build_scenario()
    world, encounter, first, second, group = result[:5]
    first_ledger, second_ledger = result[5:7]
    first_action = result[7]
    rng = result[9]
    second_action, second_choice = _schedule_second_observation(
        world, encounter, second, group, second_ledger)
    encounter.step(1)
    return (world, encounter, first, second, group, first_ledger,
            second_ledger, first_action, second_action, second_choice, rng)


class TestSpatialBeliefInquiry(unittest.TestCase):
    def test_policy_uses_only_observer_two_evidence_and_is_read_only(self):
        (world, encounter, first, second, group, first_ledger, second_ledger,
         first_action, second_action, _, rng) = _to_boundary_two()
        evidence_b = second_ledger.evidence[0]
        evidence_a = first_ledger.evidence[0]
        beliefs_b = second_ledger.belief_history
        beliefs_a = first_ledger.belief_history
        group_records = tuple(group._composition_reality._records.items())
        revision = group._composition_reality.revision
        before = (encounter.time, tuple(encounter.pending_action_list),
                  tuple(encounter.finished_action_list),
                  tuple(world.event_history.items()),
                  tuple(encounter._choice_book._choices.items()),
                  rng.state, random.getstate(),
                  first.get_skill_experience('spot'),
                  second.get_skill_experience('spot'))

        original_evidence = BeliefLedger.evidence.fget

        def observer_scoped_evidence(ledger):
            if ledger is first_ledger:
                raise AssertionError('policy attempted to inspect observer one evidence')
            return original_evidence(ledger)

        # The policy receives no Group or observer-one ledger. These tripwires
        # make any truth read or private-ledger access fail the test.
        with patch.object(group, 'counts', side_effect=AssertionError('objective count read')):
            with patch.object(BeliefLedger, 'evidence', property(observer_scoped_evidence)):
                proposal = _decide(group.id, second_ledger, encounter.time)

        self.assertIsNotNone(proposal)
        self.assertEqual((proposal.observer_id, proposal.group_id,
                          proposal.category, proposal.reason),
                         (second.id, group.id, 'dogs', 'uncertain_estimate'))
        self.assertEqual(proposal.evidence_ids, (second_action.id,))
        self.assertEqual(proposal.evidence_ids, (evidence_b.id,))
        self.assertNotIn(evidence_a.id, proposal.evidence_ids)
        self.assertIs(second_ledger.evidence[0], evidence_b)
        self.assertIs(first_ledger.evidence[0], evidence_a)
        self.assertTrue(all(a is b for a, b in zip(beliefs_b, second_ledger.belief_history)))
        self.assertTrue(all(a is b for a, b in zip(beliefs_a, first_ledger.belief_history)))
        self.assertEqual(group._composition_reality.revision, revision)
        self.assertTrue(all(k1 is k2 and v1 is v2 for (k1, v1), (k2, v2)
                            in zip(group_records, group._composition_reality._records.items())))
        after = (encounter.time, tuple(encounter.pending_action_list),
                 tuple(encounter.finished_action_list),
                 tuple(world.event_history.items()),
                 tuple(encounter._choice_book._choices.items()),
                 rng.state, random.getstate(),
                 first.get_skill_experience('spot'),
                 second.get_skill_experience('spot'))
        self.assertEqual(after, before)
        self.assertEqual(second_ledger.inquiry_history, ())
        self.assertEqual(first_ledger.inquiry_history, ())

    def test_no_evidence_and_default_no_inquiry_declare_no_action(self):
        (world, encounter, first, second, group, first_ledger, second_ledger,
         first_action, _, rng, _) = _build_scenario()
        before = (encounter.time, len(world.event_history),
                  len(encounter._choice_book._choices), rng.state,
                  first.get_skill_experience('spot'),
                  second.get_skill_experience('spot'))
        self.assertIsNone(_decide(group.id, second_ledger, encounter.time))
        self.assertEqual(second_ledger.inquiry_history, ())
        self.assertFalse(second_ledger.evidence)
        self.assertEqual((encounter.time, len(world.event_history),
                          len(encounter._choice_book._choices), rng.state,
                          first.get_skill_experience('spot'),
                          second.get_skill_experience('spot')), before)

        # After observer two's single report, the unmodified default policy's
        # actual result is also no inquiry. The existing threshold parameter
        # used by the demonstration is what makes the low-precision cue qualify.
        second_action, _ = _schedule_second_observation(
            world, encounter, second, group, second_ledger)
        encounter.step(1)
        state_before = (len(world.event_history), len(encounter.pending_action_list),
                        len(encounter._choice_book._choices), rng.state,
                        second.get_skill_experience('spot'))
        self.assertIsNone(InquiryPolicy().propose(second_ledger, group.id, encounter.time))
        self.assertEqual((len(world.event_history), len(encounter.pending_action_list),
                          len(encounter._choice_book._choices), rng.state,
                          second.get_skill_experience('spot')), state_before)
        self.assertEqual(second_ledger.evidence[0].id, second_action.id)

    def test_selected_existing_action_commits_at_boundary_three(self):
        result = run_scenario()
        self.assertEqual(result['encounter'].time, 3)
        self.assertEqual(tuple(row.boundary for row in
                         result['encounter'].__dict__['_atomic_interval_history']), (1, 2, 3))
        proposal, followup = result['proposal'], result['followup']
        self.assertEqual((proposal.category, proposal.reason,
                          proposal.evidence_ids),
                         ('dogs', 'uncertain_estimate',
                          (result['second_action'].id,)))
        self.assertEqual((followup.focus_category, followup.start_time,
                          followup.end_time), ('dogs', 2, 3))
        inspection = result['inspection']
        action_result = inspection.action(followup.id)
        self.assertEqual(action_result.resolved_boundary, 3)
        self.assertEqual(action_result.facts.outcome, 'success')
        self.assertEqual(action_result.declaration.actor_id,
                         result['second_observer'].id)
        self.assertEqual(action_result.facts.target_ids, (result['group'].id,))
        self.assertEqual(dict(action_result.facts.metadata)['roll'], 15)
        evidence = result['second_ledger'].evidence[-1]
        self.assertEqual((evidence.id, evidence.observer_id, evidence.group_id,
                          evidence.time, evidence.focus_category),
                         (followup.id, result['second_observer'].id,
                          result['group'].id, 3, 'dogs'))
        self.assertEqual(result['second_ledger'].inquiry_history, ())
        self.assertEqual(tuple(result['second_ledger']._evidence),
                         (result['second_action'].id, followup.id))
        self.assertEqual(tuple(result['first_ledger']._evidence),
                         (result['first_action'].id,))
        self.assertFalse(result['first_ledger']._evidence.get(followup.id))
        practices = inspection.target(result['second_observer'].id).practice_history
        self.assertEqual(tuple(row.time for row in practices), (2, 3))
        self.assertEqual(tuple(row.experience for row in practices), (12, 12))
        self.assertEqual(tuple(row.exercises[0].action_id for row in practices),
                         (result['second_action'].id, followup.id))
        self.assertEqual(result['group']._composition_reality.revision, 1)
        self.assertEqual(result['group'].materialized_count, 0)
        decision_records = result['objective_records_at_decision']
        final_records = tuple(result['group']._composition_reality._records.items())
        self.assertTrue(all(k1 is k2 and v1 is v2
                            for (k1, v1), (k2, v2)
                            in zip(decision_records, final_records)))
        self.assertEqual(result['objective_revision_at_decision'],
                         result['group']._composition_reality.revision)

    def test_reproducible_decision_and_boundary_three_publication(self):
        first, second = demo_data(), demo_data()
        for result in (first, second):
            self.assertEqual(result['encounter']['committed_boundaries'], (1, 2, 3))
            self.assertEqual(result['decision']['category'], 'dogs')
            self.assertEqual(result['decision']['reason'], 'uncertain_estimate')
            self.assertEqual(result['decision']['source_evidence_ids'],
                             (result['decision']['source_action_id'],))
            self.assertTrue(result['decision']['inquiry_history_unchanged_by_decision'])
            self.assertEqual(result['decision']['native_inquiry_history_entries'], 0)
            self.assertEqual(result['followup']['outcome'], 'success')
            self.assertEqual(result['followup']['boundary'], 3)
            self.assertEqual(result['followup']['focus_category'], 'dogs')
            self.assertEqual(result['objective_group']['reality_revision'], 1)
            self.assertEqual(result['objective_group']['reality_revision_at_decision'], 1)
            self.assertTrue(result['objective_group']['fact_storage_unchanged_since_decision'])
            self.assertEqual(result['objective_group']['fact_revisions'], (1,))
            self.assertEqual(result['objective_group']['materialized_beings'], 0)
            self.assertEqual(result['observer_isolation']['first_evidence_count'], 1)
            self.assertFalse(result['observer_isolation']['first_knows_followup_id'])
        self.assertEqual(first['decision']['source_estimates'],
                         second['decision']['source_estimates'])
        self.assertEqual(first['followup']['new_evidence_estimate'],
                         second['followup']['new_evidence_estimate'])
        self.assertEqual(first['objective_group']['composition'],
                         second['objective_group']['composition'])

    def test_boundary_three_publication_fault_preserves_prior_two_boundaries(self):
        result = run_scenario(advance=False)
        encounter, group = result['encounter'], result['group']
        first, second = result['first_observer'], result['second_observer']
        ledger_a, ledger_b = result['first_ledger'], result['second_ledger']
        followup = result['followup']
        objective_ledger = group._composition_reality
        saved_records = tuple(objective_ledger._records.items())
        saved_revision = objective_ledger.revision
        saved_receipts = tuple(encounter.__dict__['_atomic_interval_history'])
        evidence_a = ledger_a.evidence[0]
        evidence_b = ledger_b.evidence[0]
        beliefs_a, beliefs_b = ledger_a.belief_history, ledger_b.belief_history
        practice_a = tuple(first.skill_use_history)
        practice_b = tuple(second.skill_use_history)
        xp_a = first.get_skill_experience('spot')
        xp_b = second.get_skill_experience('spot')
        rng_state = result['rng'].state
        self.assertEqual((encounter.time, encounter.last_processed_boundary), (2, 2))
        self.assertEqual(ledger_b.inquiry_history, ())

        import atomic_publication
        native_publish = atomic_publication.publish_interval_candidate

        def fail_after_observers(*args, **kwargs):
            kwargs['_fail_after'] = 'observers'
            return native_publish(*args, **kwargs)

        with patch('atomic_publication.publish_interval_candidate', fail_after_observers):
            with self.assertRaises(PublicationFailure) as caught:
                encounter.step(1)
        self.assertEqual(caught.exception.phase, 'observers')
        self.assertEqual((encounter.time, encounter.last_processed_boundary), (2, 2))
        self.assertEqual(tuple(encounter.__dict__['_atomic_interval_history']), saved_receipts)
        self.assertEqual(objective_ledger.revision, saved_revision)
        self.assertTrue(all(k1 is k2 and v1 is v2
                            for (k1, v1), (k2, v2) in
                            zip(saved_records, objective_ledger._records.items())))
        self.assertEqual(ledger_a.evidence, (evidence_a,))
        self.assertEqual(ledger_b.evidence, (evidence_b,))
        self.assertTrue(all(a is b for a, b in zip(beliefs_a, ledger_a.belief_history)))
        self.assertTrue(all(a is b for a, b in zip(beliefs_b, ledger_b.belief_history)))
        self.assertEqual(tuple(first.skill_use_history), practice_a)
        self.assertEqual(tuple(second.skill_use_history), practice_b)
        self.assertEqual((first.get_skill_experience('spot'),
                          second.get_skill_experience('spot')), (xp_a, xp_b))
        self.assertEqual(result['rng'].state, rng_state)
        self.assertNotIn(followup.id, encounter.finished_action_list)
        self.assertEqual(ledger_b.inquiry_history, ())

        encounter.recover_transactional_progression(caught.exception.recovery_token)
        encounter.step(1)
        self.assertEqual(encounter.time, 3)
        self.assertEqual(ledger_b.evidence[-1].id, followup.id)
        self.assertEqual(ledger_b.inquiry_history, ())
        self.assertEqual(objective_ledger.revision, saved_revision)


if __name__ == '__main__':
    unittest.main()
