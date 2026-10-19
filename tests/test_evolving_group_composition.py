"""Partial population constraints remain coherent as Group membership evolves."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'examples')]

from evolving_group_composition import make_world, run_experiment, trained_key


class EvolvingGroupCompositionTests(unittest.TestCase):
    def assert_partition(self, group):
        state = group.current_formation_trait_state('trained_spotter')
        native = state['resident_original_cohort']
        departed = state['departed_original_cohort']
        original = state['original_cohort']
        self.assertEqual(native['adults'] + departed['adults'], original['adults'])
        self.assertEqual(native['adults'], sum(native[k] for k in (
            'realized_qualified', 'realized_other',
            'unresolved_qualified', 'unresolved_other')))
        self.assertEqual(original['qualified'], native['realized_qualified']
                         + native['unresolved_qualified'] + departed['qualified'])
        self.assertEqual(state['current_adults'], native['adults'] + state['arrivals']['adults'])
        self.assertEqual(state['current_adults'], group.current_counts()['adults'])
        self.assertEqual(state['arrivals']['formation_trait_unknown'],
                         state['arrivals']['adults'])
        self.assertEqual(group.formation_trait_state('trained_spotter')['committed_qualified'],
                         original['qualified'])
        return state

    def test_original_quota_can_be_projected_without_realizing_beings(self):
        world, groups = make_world()
        for group in groups:
            state = self.assert_partition(group)
            self.assertEqual(state['original_cohort']['qualified'], 2)
            self.assertEqual(state['resident_original_cohort']['unresolved_qualified'], 2)
            self.assertEqual(group.realized_being_count, 0)
            self.assertEqual(group.materialized_count, 0)
        self.assertEqual(world.get_object_registry().len(), 2)

    def test_departing_qualified_member_changes_resident_quota_not_formation(self):
        world, (west, _) = make_world()
        being = west.realize_being(world, *trained_key(west))
        before = self.assert_partition(west)
        west.leave_being(world, being)
        after = self.assert_partition(west)
        self.assertEqual(before['resident_original_cohort']['realized_qualified'], 1)
        self.assertEqual(after['resident_original_cohort']['realized_qualified'], 0)
        self.assertEqual(after['departed_original_cohort']['qualified'], 1)
        self.assertEqual(after['resident_original_cohort']['unresolved_qualified'], 1)
        self.assertEqual(west.formation_trait_state('trained_spotter')['realized_qualified'], 1)
        self.assertEqual(west.realized_being_count, 1)

    def test_untrained_departure_does_not_reduce_qualified_native_count(self):
        world, (west, _) = make_world()
        qualified = west._adult_formation_assignments('trained_spotter')
        key = next((h, 'adults', i) for h in range(west.household_count)
                   for i in range(west.household(h)['adults'])
                   if f'{west.id}/{h}/adults/{i}' not in qualified)
        being = west.realize_being(world, *key)
        west.leave_being(world, being)
        state = self.assert_partition(west)
        self.assertEqual(state['departed_original_cohort']['other'], 1)
        self.assertEqual(state['resident_original_cohort']['unresolved_qualified'], 2)

    def test_arrivals_do_not_inherit_receiving_group_formation_quota(self):
        world, (west, east) = make_world()
        immigrant = east.realize_being(world, *trained_key(east))
        east.leave_being(world, immigrant)
        west.join_being(world, immigrant)
        state = self.assert_partition(west)
        self.assertEqual(state['resident_original_cohort']['unresolved_qualified'], 2)
        self.assertEqual(state['arrivals']['adults'], 1)
        self.assertEqual(west.known_skill_state('spot')['known'][immigrant.id]['level'], 4)
        immigrant.set_skill_level(world.get_skill_dictionary(), 'spot', 7)
        self.assertEqual(self.assert_partition(west), state)
        self.assertEqual(west.known_skill_state('spot')['known'][immigrant.id]['level'], 7)
        self.assertEqual(east.formation_trait_state('trained_spotter')['committed_qualified'], 2)

    def test_return_to_origin_restores_resident_native_quota(self):
        world, (west, east) = make_world()
        traveler = west.realize_being(world, *trained_key(west))
        west.leave_being(world, traveler)
        east.join_being(world, traveler)
        west_state = self.assert_partition(west)
        self.assertEqual(west_state['departed_original_cohort']['qualified'], 1)
        east.leave_being(world, traveler)
        west.join_being(world, traveler)
        returned = self.assert_partition(west)
        self.assertEqual(returned['departed_original_cohort']['adults'], 0)
        self.assertEqual(returned['resident_original_cohort']['realized_qualified'], 1)
        self.assertEqual(self.assert_partition(east)['arrivals']['adults'], 0)
        self.assertIs(west.realize_being(world, *trained_key(west)), traveler)

    def test_formation_attributes_preserved_when_original_member_moves(self):
        world, (west, east) = make_world()
        key = trained_key(west)
        role = west.formation_attribute(*key, 'role')
        committed = west.committed_formation_attributes(*key)
        traveler = west.realize_being(world, *key)
        west.leave_being(world, traveler)
        east.join_being(world, traveler)
        self.assertEqual(west.formation_attribute(*key, 'role'), role)
        self.assertEqual(west.committed_formation_attributes(*key), committed)
        self.assertEqual(west.realized_being_count, 1)
        self.assertEqual(east.realized_being_count, 0)
        self.assert_partition(west)
        self.assert_partition(east)

    def test_projection_is_pure_and_unresolved_population_stays_unrealized(self):
        world, (west, east) = make_world()
        traveler = west.realize_being(world, *trained_key(west))
        west.leave_being(world, traveler)
        east.join_being(world, traveler)
        before = (west.realized_being_count, west.materialized_count,
                  east.realized_being_count, east.materialized_count,
                  world.get_object_registry().len())
        a = self.assert_partition(west)
        b = self.assert_partition(east)
        self.assertEqual((west.realized_being_count, west.materialized_count,
                          east.realized_being_count, east.materialized_count,
                          world.get_object_registry().len()), before)
        self.assertEqual(a, west.current_formation_trait_state('trained_spotter'))
        self.assertEqual(b, east.current_formation_trait_state('trained_spotter'))

    def test_demo(self):
        result = run_experiment()
        west, east = result['west'], result['east']
        for state in result['after_joins']:
            self.assertEqual(state['arrivals']['adults'], 1)
            self.assertEqual(state['resident_original_cohort']['unresolved_qualified'], 1)
        self.assertEqual(west.realized_being_count, 1)
        self.assertEqual(east.realized_being_count, 1)
        self.assertEqual(result['after_joins'][0], result['after_learning'])
        self.assertEqual(result['known_spot']['known'][result['travelers'][1].id]['level'], 7)
        self.assertIsInstance(result['unresolved_member_role'], str)
        self.assert_partition(west)
        self.assert_partition(east)


if __name__ == '__main__':
    unittest.main()
