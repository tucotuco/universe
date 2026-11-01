"""Integrated native spatial Encounter, Spot, awareness and practice example."""
from pathlib import Path
import random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'examples'))

from spatial_spot_encounter import _build_scenario, demo_data
from action_evaluation import AwarenessEffect, PracticeEffect
from spatial import ISEAGrid


class TestSpatialSpotEncounter(unittest.TestCase):
    def test_native_positions_cells_spot_awareness_and_target_practice_join(self):
        module_rng_before = random.getstate()
        world, encounter, observer, observed, action, choice, rng, inspection = _build_scenario()
        self.assertEqual(random.getstate(), module_rng_before)
        self.assertEqual(encounter.time, 6)
        self.assertEqual(encounter.last_processed_boundary, 6)
        self.assertEqual(tuple(encounter.being_list), (observer.id, observed.id))
        self.assertIs(encounter.get_being(observer.id), observer)
        self.assertIs(encounter.get_being(observed.id), observed)

        grid = ISEAGrid(radius=1.0)
        for being in (observer, observed):
            self.assertEqual(being.spatial_cell(grid, 5),
                grid.cell_at(*being.get_position().angular_coordinate(), 5))
        self.assertEqual(observer.get_position().as_tuple(), (1.0, 0.0, 0.0))
        self.assertEqual(observer.get_position().angular_coordinate(), (0.0, 0.0))
        self.assertEqual(observed.get_position().angular_coordinate(), (0.0, 1.0))
        distance = encounter.distance_between_entities(observer.id, observed.id)
        self.assertGreater(distance, 0)
        self.assertGreater(distance, 0)

        action_result = inspection.action(action.id)
        self.assertEqual(action_result.declaration.actor_id, observer.id)
        self.assertEqual(action_result.facts.target_ids, (observed.id,))
        self.assertEqual(action_result.facts.outcome, 'success')
        self.assertEqual(dict(action_result.facts.metadata)['roll'], 20)
        self.assertTrue(any(type(row.effect) is AwarenessEffect
                            and row.effect.source_action_id == action.id
                            for row in action_result.effects))
        self.assertTrue(encounter.is_aware(observer.id, observed.id))
        self.assertFalse(encounter.is_aware(observed.id, observer.id))

        observer_history = inspection.target(observer.id).practice_history
        self.assertEqual(observer_history, ())
        self.assertEqual(observer.get_skill_experience('spot'), 0)
        self.assertFalse(any(type(row.effect) is PracticeEffect for row in action_result.effects))
        self.assertIsNone(encounter.location)  # Event metadata is not a physical Entity position.
        self.assertEqual(inspection.objective_use, ())
        self.assertEqual(rng.state[0], 3)

    def test_example_view_is_reproducible_and_uses_native_state(self):
        first = demo_data()
        second = demo_data()
        for view in (first, second):
            self.assertEqual(view['encounter']['time'], 6)
            self.assertEqual(view['spot']['outcome'], 'success')
            self.assertTrue(view['spot']['observer_aware_of_target'])
            self.assertFalse(view['spot']['target_aware_of_observer'])
            self.assertFalse(view['practice']['spot_awards_experience'])
            self.assertEqual(view['practice']['target_owned_spot_practice_records'], 0)
            self.assertEqual(view['objective_vs_observation']['objective_fact_uses'], 0)
        for role in ('observer', 'observed'):
            self.assertEqual(first['beings'][role]['cartesian'],
                             second['beings'][role]['cartesian'])
            self.assertEqual(first['beings'][role]['isea_trifold_cell'],
                             second['beings'][role]['isea_trifold_cell'])
        self.assertEqual(first['spot']['distance'], second['spot']['distance'])


if __name__ == '__main__':
    unittest.main()
