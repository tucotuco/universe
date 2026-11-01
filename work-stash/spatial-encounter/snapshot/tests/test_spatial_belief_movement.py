"""Belief-conditioned movement through native transactional progression."""
import unittest
from unittest.mock import patch

from activities import RunAction
from atomic_publication import PublicationFailure
from field_inquiry import InquiryPolicy
from field_observation import BeliefLedger, KnownWaypoint
from spatial import CartesianPosition, LocalFrame, LocalPosition
from spatial_belief_inquiry import _decide
from spatial_belief_movement import (
    INITIAL_WAYPOINT_ID, INITIAL_WAYPOINT_SOURCE, _prepare_two_boundaries,
    _velocity_to_waypoint, demo_data, run_scenario)
from spatial_group_observation import _build_scenario


class TestSpatialBeliefMovement(unittest.TestCase):
    def test_owner_owned_waypoint_conditions_native_choice_and_movement(self):
        result = run_scenario()
        proposal = result['proposal']
        waypoint = result['waypoint']
        self.assertIsNotNone(proposal)
        evidence = result['second_ledger'].evidence[-1]
        self.assertEqual(proposal.evidence_ids, (evidence.id,))
        self.assertEqual((proposal.observer_id, proposal.group_id,
                          proposal.category, proposal.reason),
                         (result['second_observer'].id, result['group'].id,
                          'dogs', 'uncertain_estimate'))
        self.assertIs(type(waypoint), KnownWaypoint)
        self.assertEqual((waypoint.owner_id, waypoint.source_id, waypoint.acquired_at),
                         (result['second_observer'].id,
                          'scenario-map-card:south-trail', 0.0))
        self.assertEqual(waypoint.position, LocalPosition(0, -250, 1000))
        self.assertIs(waypoint.frame, result['frame'])
        self.assertIs(result['second_ledger'].known_waypoint(
            waypoint.id, owner_id=result['second_observer'].id,
            frame=result['frame']), waypoint)
        from observer_proposals import _capture_belief
        frozen_belief = _capture_belief(result['second_ledger'],
                                        result['second_observer'].id)
        frozen_waypoint = frozen_belief.auxiliary['_known_waypoints'][waypoint.id]
        self.assertEqual(frozen_waypoint, waypoint)
        self.assertIsNot(frozen_waypoint, waypoint)

        # BeliefLedger's owner scope prevents observer one from retrieving this
        # record, and observer one received no automatic copy.
        self.assertFalse(result['first_ledger'].known_waypoints)
        self.assertIsNone(result['first_ledger'].known_waypoint(
            waypoint.id, owner_id=result['first_observer'].id,
            frame=result['frame']))
        with self.assertRaises(PermissionError):
            result['second_ledger'].known_waypoint(
                waypoint.id, owner_id=result['first_observer'].id,
                frame=result['frame'])

        self.assertEqual(result['before_position'], (0, -300, 1000))
        self.assertEqual(result['after_position'], (0.0, -250.0, 1000.0))
        self.assertEqual(result['velocity'], (0.0, 50.0, 0.0))
        self.assertEqual(tuple(row.boundary for row in
                         result['encounter'].__dict__['_atomic_interval_history']),
                         (1, 2, 3))
        self.assertEqual(result['record'].declaration.actor_id,
                         result['second_observer'].id)
        self.assertEqual(result['record'].resolved_boundary, 3)
        self.assertEqual(result['record'].facts.outcome, 'success')
        self.assertEqual(dict(result['record'].facts.metadata)['displacement'], 50)

        target = result['inspection'].target(result['second_observer'].id)
        run_batches = [batch for batch in target.practice_history
                       if any(exercise.action_id == result['run_action'].id
                              for exercise in batch.exercises)]
        self.assertEqual(len(run_batches), 1)
        practice = run_batches[0]
        self.assertEqual((practice.time, practice.experience), (3, 9))
        self.assertEqual(tuple(exercise.action_id for exercise in practice.exercises),
                         (result['run_action'].id,))
        self.assertEqual(result['second_observer'].get_skill_experience('run'), 9)
        self.assertEqual(result['group'].get_position().as_tuple(), (0, 0, 1000))
        self.assertEqual(result['group'].materialized_count, 0)
        data = demo_data()
        self.assertEqual(data['destination_knowledge']['owner_id'],
                         data['decision']['observer_id'])
        self.assertEqual(data['run_action']['measured_displacement'], 50)

    def test_only_changing_owned_waypoint_changes_destination(self):
        original = run_scenario()
        changed = run_scenario(waypoint_position=(0, -240, 1000))
        self.assertEqual(original['waypoint'].source_id, changed['waypoint'].source_id)
        self.assertEqual((original['proposal'].category, original['proposal'].reason),
                         (changed['proposal'].category, changed['proposal'].reason))
        self.assertEqual(original['second_ledger'].evidence[-1].reports,
                         changed['second_ledger'].evidence[-1].reports)
        self.assertEqual(original['proposal'].evidence_ids,
                         (original['second_action'].id,))
        self.assertEqual(changed['proposal'].evidence_ids,
                         (changed['second_action'].id,))
        self.assertEqual(original['velocity'], (0.0, 50.0, 0.0))
        self.assertEqual(changed['velocity'], (0.0, 60.0, 0.0))
        self.assertEqual(original['after_position'], (0.0, -250.0, 1000.0))
        self.assertEqual(changed['after_position'], (0.0, -240.0, 1000.0))
        self.assertEqual(original['group'].get_position(),
                         changed['group'].get_position())
        self.assertEqual(original['group'].counts(), changed['group'].counts())
        self.assertEqual(original['second_ledger'].count_estimate(
            original['group'].id, 'dogs'),
            changed['second_ledger'].count_estimate(changed['group'].id, 'dogs'))
        self.assertFalse(original['first_ledger'].known_waypoints)
        self.assertFalse(changed['first_ledger'].known_waypoints)

    def test_missing_grant_wrong_owner_or_wrong_frame_declines_action(self):
        for options in (
                {'grant_waypoint': False},
                {'lookup_owner_id': 'not-the-owner'},
                {'lookup_frame': LocalFrame.aligned_at(CartesianPosition(10, 0, 0))}):
            with self.subTest(options=options):
                result = run_scenario(**options)
                self.assertIsNotNone(result['proposal'])
                self.assertIsNone(result['waypoint'])
                self.assertIsNone(result['run_action'])
                self.assertIsNone(result['choice'])
                self.assertEqual(result['encounter'].time, 2)
                self.assertEqual(result['second_observer'].get_position().as_tuple(),
                                 (0, -300, 1000))
                self.assertEqual(result['second_observer'].get_skill_experience('run'), 0)
                self.assertEqual(result['second_ledger'].inquiry_history, ())

    def test_invalid_source_and_wrong_owner_are_rejected(self):
        (world, encounter, first, second, group, first_ledger, second_ledger,
         *_rest) = _build_scenario(advance=False)
        frame = LocalFrame.aligned_at(CartesianPosition(0, 0, 0))
        encounter.set_local_frame(frame)
        with self.assertRaises(ValueError):
            KnownWaypoint(INITIAL_WAYPOINT_ID, second.id, '  ', 0,
                          LocalPosition(0, -250, 1000), frame)
        self.assertFalse(second_ledger.known_waypoints)
        self.assertEqual(encounter.time, 0)
        with self.assertRaises(ValueError):
            BeliefLedger(second.id, initial_waypoints=(KnownWaypoint(
                INITIAL_WAYPOINT_ID, first.id, INITIAL_WAYPOINT_SOURCE, 0,
                LocalPosition(0, -250, 1000), frame),))
        self.assertFalse(second_ledger.known_waypoints)
        encounter.step(1)
        self.assertEqual(second_ledger.evidence, ())
        self.assertFalse(second_ledger.known_waypoints)
        self.assertFalse(hasattr(second_ledger, 'seed_initial_waypoint'))

    def test_absent_evidence_and_default_no_inquiry_make_no_run_choice(self):
        (world, encounter, first_observer, second_observer, group,
         first_ledger, _empty_second_ledger, *_rest) = _build_scenario(advance=False)
        frame = LocalFrame.aligned_at(CartesianPosition(0, 0, 0))
        second_ledger = BeliefLedger(second_observer.id, initial_waypoints=(
            KnownWaypoint(INITIAL_WAYPOINT_ID, second_observer.id,
                INITIAL_WAYPOINT_SOURCE, 0, LocalPosition(0, -250, 1000), frame),))
        before = (second_observer.get_position().as_tuple(), encounter.time,
                  tuple(encounter._choice_book._choices),
                  tuple(world.event_history.items()))
        self.assertFalse(second_ledger.evidence)
        self.assertEqual(len(second_ledger.known_waypoints), 1)
        self.assertIsNone(_decide(group.id, second_ledger, encounter.time))
        self.assertEqual((second_observer.get_position().as_tuple(), encounter.time,
                          tuple(encounter._choice_book._choices),
                          tuple(world.event_history.items())), before)

        result = _prepare_two_boundaries()
        world, encounter, first_observer, second_observer, group = result[:5]
        ledger = result[6]
        before = (second_observer.get_position().as_tuple(), encounter.time,
                  tuple(encounter._choice_book._choices),
                  tuple(world.event_history.items()))
        self.assertIsNone(InquiryPolicy().propose(ledger, group.id, encounter.time))
        self.assertEqual((second_observer.get_position().as_tuple(), encounter.time,
                          tuple(encounter._choice_book._choices),
                          tuple(world.event_history.items())), before)

    def test_failed_publication_restores_knowledge_and_prior_state_then_retries_once(self):
        (world, encounter, first_observer, second_observer, group,
         first_ledger, second_ledger, first_action, first_choice, rng,
         second_action, second_choice, frame, landmark,
         source_provenance) = _prepare_two_boundaries()
        proposal = _decide(group.id, second_ledger, encounter.time)
        self.assertIsNotNone(proposal)
        waypoint = second_ledger.known_waypoint(
            INITIAL_WAYPOINT_ID, owner_id=second_observer.id, frame=frame)
        action = RunAction(world, second_observer.id, encounter.time, 1,
                           minimum_distance=25, experience=9)
        encounter.schedule_choice((action,))
        velocity = _velocity_to_waypoint(encounter, second_observer, waypoint)
        prior_receipts = tuple(encounter.__dict__['_atomic_interval_history'])
        prior_events = tuple(world.event_history.items())
        prior_evidence = (tuple(first_ledger.evidence), tuple(second_ledger.evidence))
        prior_beliefs = (tuple(first_ledger.belief_history),
                         tuple(second_ledger.belief_history))
        prior_waypoints = (tuple(first_ledger.known_waypoints),
                           tuple(second_ledger.known_waypoints))
        prior_facts = tuple(group._composition_reality._records.items())
        prior_positions = (first_observer.get_position().as_tuple(),
                           second_observer.get_position().as_tuple(),
                           group.get_position().as_tuple())
        prior_practice = (first_observer.get_skill_experience('spot'),
                          second_observer.get_skill_experience('spot'),
                          second_observer.get_skill_experience('run'))
        prior_rng = rng.state

        from atomic_publication import publish_interval_candidate
        original_publish = publish_interval_candidate

        def fail_after_movement(enc, candidate, **kwargs):
            kwargs['_fail_after'] = 'movement'
            return original_publish(enc, candidate, **kwargs)

        with patch('atomic_publication.publish_interval_candidate',
                   side_effect=fail_after_movement):
            with self.assertRaises(PublicationFailure) as caught:
                encounter.step(1, velocities={second_observer.id: velocity},
                               velocity_frame='local')

        self.assertEqual(caught.exception.phase, 'movement')
        self.assertEqual(encounter.time, 2)
        self.assertEqual(tuple(encounter.__dict__['_atomic_interval_history']), prior_receipts)
        self.assertEqual(tuple(world.event_history.items()), prior_events)
        self.assertEqual((tuple(first_ledger.evidence), tuple(second_ledger.evidence)), prior_evidence)
        self.assertEqual((tuple(first_ledger.belief_history),
                          tuple(second_ledger.belief_history)), prior_beliefs)
        self.assertEqual((tuple(first_ledger.known_waypoints),
                          tuple(second_ledger.known_waypoints)), prior_waypoints)
        self.assertTrue(all(k1 is k2 and v1 is v2 for (k1, v1), (k2, v2)
                            in zip(prior_facts, group._composition_reality._records.items())))
        self.assertEqual((first_observer.get_position().as_tuple(),
                          second_observer.get_position().as_tuple(),
                          group.get_position().as_tuple()), prior_positions)
        self.assertEqual((first_observer.get_skill_experience('spot'),
                          second_observer.get_skill_experience('spot'),
                          second_observer.get_skill_experience('run')), prior_practice)
        self.assertEqual(rng.state, prior_rng)

        encounter.recover_transactional_progression(caught.exception.recovery_token)
        encounter.step(1, velocities={second_observer.id: velocity},
                       velocity_frame='local')
        inspection = encounter.inspect_committed()
        record = inspection.action(action.id)
        self.assertEqual(record.facts.outcome, 'success')
        self.assertEqual(dict(record.facts.metadata)['displacement'], 50)
        self.assertEqual(tuple(row.boundary for row in
                         encounter.__dict__['_atomic_interval_history']), (1, 2, 3))
        self.assertEqual(second_observer.get_position().as_tuple(), (0, -250, 1000))
        self.assertEqual(second_observer.get_skill_experience('run'), 9)
        self.assertEqual(len([exercise for batch in
                              inspection.target(second_observer.id).practice_history
                              for exercise in batch.exercises
                              if exercise.action_id == action.id]), 1)


if __name__ == '__main__':
    unittest.main()
