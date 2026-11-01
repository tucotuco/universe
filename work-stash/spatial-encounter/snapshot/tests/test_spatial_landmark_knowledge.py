"""Objective landmark and Agent-owned map-card waypoint remain distinct."""
import unittest
from unittest.mock import patch

from spatial_belief_movement import (
    INITIAL_WAYPOINT_SOURCE, _decide, _velocity_to_waypoint, run_scenario)


class TestSpatialLandmarkKnowledge(unittest.TestCase):
    def test_native_landmark_and_initial_owner_waypoint_have_explicit_provenance(self):
        result = run_scenario()
        landmark = result['landmark']
        waypoint = result['waypoint']
        self.assertIs(result['world'].get_object_by_id(landmark.id), landmark)
        self.assertIn(landmark.id, result['encounter'].non_being_object_list)
        self.assertEqual(landmark.get_position().as_tuple(), (0, -250, 1000))
        self.assertEqual(result['encounter'].entity_local_position(landmark.id),
                         waypoint.position)
        self.assertEqual(waypoint.source_id, INITIAL_WAYPOINT_SOURCE)
        self.assertEqual(waypoint.owner_id, result['second_observer'].id)
        self.assertFalse(result['first_ledger'].known_waypoints)
        self.assertEqual(result['source_provenance']['landmark_id'], landmark.id)
        self.assertEqual(result['source_provenance']['source_id'], waypoint.source_id)
        self.assertEqual(
            result['source_provenance']['waypoint_claim_local_position'],
            waypoint.position.as_tuple())
        self.assertIn('not a modeled map', result['source_provenance']['relationship'])
        # No map Object or native objective ledger entry was created by the
        # detached scenario association.
        self.assertEqual(len(result['encounter'].non_being_object_list), 2)
        self.assertEqual(result['run_action'].end_time, 3)
        self.assertEqual(result['record'].facts.outcome, 'success')
        self.assertEqual(result['practice'].experience, 9)

    def test_changing_only_waypoint_changes_movement_not_objective_state(self):
        first = run_scenario()
        second = run_scenario(waypoint_position=(0, -240, 1000))
        self.assertEqual(first['landmark'].get_position(),
                         second['landmark'].get_position())
        self.assertEqual(first['group'].counts(), second['group'].counts())
        self.assertEqual(first['waypoint'].source_id, second['waypoint'].source_id)
        self.assertEqual(first['waypoint'].position.as_tuple(), (0, -250, 1000))
        self.assertEqual(second['waypoint'].position.as_tuple(), (0, -240, 1000))
        self.assertEqual(first['velocity'], (0.0, 50.0, 0.0))
        self.assertEqual(second['velocity'], (0.0, 60.0, 0.0))
        self.assertEqual(first['after_position'], (0.0, -250.0, 1000.0))
        self.assertEqual(second['after_position'], (0.0, -240.0, 1000.0))
        self.assertEqual(first['proposal'].category, second['proposal'].category)
        self.assertEqual(first['proposal'].reason, second['proposal'].reason)
        self.assertEqual(first['second_ledger'].evidence[-1].reports,
                         second['second_ledger'].evidence[-1].reports)

    def test_changing_only_landmark_at_initialization_does_not_refresh_waypoint(self):
        first = run_scenario()
        moved_landmark = run_scenario(landmark_position=(100, 100, 1000))
        self.assertNotEqual(first['landmark'].get_position(),
                            moved_landmark['landmark'].get_position())
        self.assertEqual(first['waypoint'].position, moved_landmark['waypoint'].position)
        self.assertEqual(first['waypoint'].source_id,
                         moved_landmark['waypoint'].source_id)
        self.assertEqual(first['velocity'], moved_landmark['velocity'])
        self.assertEqual(first['after_position'], moved_landmark['after_position'])
        self.assertEqual(first['record'].facts.outcome,
                         moved_landmark['record'].facts.outcome)
        self.assertEqual(first['practice'].experience,
                         moved_landmark['practice'].experience)
        self.assertEqual(first['group'].counts(), moved_landmark['group'].counts())
        self.assertEqual(first['second_ledger'].evidence[-1].reports,
                         moved_landmark['second_ledger'].evidence[-1].reports)
        self.assertNotEqual(first['source_provenance']['landmark_local_position_at_initialization'],
                            moved_landmark['source_provenance']['landmark_local_position_at_initialization'])
        self.assertEqual(moved_landmark['source_provenance']['waypoint_claim_local_position'],
                         first['waypoint'].position.as_tuple())

    def test_decision_and_velocity_read_only_path_ignores_objective_coordinates(self):
        result = run_scenario(advance=False)
        with patch.object(result['group'], 'counts',
                          side_effect=AssertionError('objective Group counts consulted')):
            with patch.object(result['landmark'], 'get_position',
                              side_effect=AssertionError('objective landmark position consulted')):
                proposal = _decide(result['group'].id, result['second_ledger'],
                                   result['encounter'].time)
                waypoint = result['second_ledger'].known_waypoint(
                    result['waypoint'].id,
                    owner_id=result['second_observer'].id,
                    frame=result['frame'])
                velocity = _velocity_to_waypoint(result['encounter'],
                    result['second_observer'], waypoint)
        self.assertIsNotNone(proposal)
        self.assertEqual(velocity, (0.0, 50.0, 0.0))
        self.assertIsNotNone(result['run_action'])
        self.assertEqual(result['choice'].state, 'accepted')
        self.assertEqual(result['encounter'].time, 2)
        self.assertEqual(result['second_observer'].get_position().as_tuple(),
                         (0, -300, 1000))
        self.assertEqual(result['second_observer'].get_skill_experience('run'), 0)


if __name__ == '__main__':
    unittest.main()
