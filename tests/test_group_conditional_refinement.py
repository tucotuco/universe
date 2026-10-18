"""Exact baseline trait quotas survive selective realization and later state change."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'examples')]

from statistical_group import StatisticalGroup
from library import Library
from universe import Universe

BASE_CONFIG = json.loads((ROOT / 'examples' / 'nomadic_group.json').read_text())


def make_group(quota=2, level=4, name='trained_spotter'):
    config = deepcopy(BASE_CONFIG)
    config['formation_traits'] = {
        'adults': {name: {'count': quota, 'initial_skills': {'spot': level}}}}
    world = Universe('Conditional cohort test', library=Library(config_dir=str(ROOT / 'src' / 'config')))
    group = StatisticalGroup(config['group_name'], config['group_id'], config, config['seed'])
    world.add_object(group)
    return world, group, config


def adult_keys(group):
    return [(household, 'adults', index)
            for household in range(group.household_count)
            for index in range(group.household(household)['adults'])]


class GroupConditionalRefinementTests(unittest.TestCase):
    def test_committed_quota_without_realizing_anyone(self):
        _, group, config = make_group()
        state = group.formation_trait_state('trained_spotter')
        self.assertEqual(state['committed_qualified'], 2)
        self.assertEqual(state['realized_qualified'], 0)
        self.assertEqual(state['unresolved_qualified'], 2)
        self.assertEqual(state['unresolved_other'], group.counts()['adults'] - 2)
        self.assertEqual(group.materialized_count, 0)
        self.assertEqual(group.realized_being_count, 0)
        # Changing the caller's config cannot rewrite committed formation rules.
        config['formation_traits']['adults']['trained_spotter']['count'] = 0
        self.assertEqual(group.formation_trait_state('trained_spotter'), state)

    def test_repeated_realization_and_order_do_not_change_initial_assignment(self):
        w1, g1, _ = make_group()
        w2, g2, _ = make_group()
        keys = adult_keys(g1)
        self.assertGreaterEqual(len(keys), 3)
        assert_sorted = []
        for key in keys[:3]:
            b = g1.realize_being(w1, *key)
            assert_sorted.append((b.id, b.get_skill_level('spot') or 0))
        reversed_order = []
        for key in reversed(keys[:3]):
            b = g2.realize_being(w2, *key)
            reversed_order.append((b.id, b.get_skill_level('spot') or 0))
        self.assertEqual(dict(assert_sorted), dict(reversed_order))
        self.assertEqual(g1.formation_trait_state('trained_spotter'),
                         g2.formation_trait_state('trained_spotter'))
        self.assertEqual(g1.counts(), g2.counts())
        self.assertIs(g1.realize_being(w1, *keys[0]), w1.get_object_by_id(assert_sorted[0][0]))

    def test_exact_quota_is_conditioned_on_observed_realizations(self):
        w, group, _ = make_group()
        cohort_size = group.counts()['adults']
        selections = []
        for key in adult_keys(group):
            being = group.realize_being(w, *key)
            selections.append(being)
            state = group.formation_trait_state('trained_spotter')
            self.assertEqual(state['committed_qualified'], 2)
            self.assertEqual(state['realized_qualified'] + state['unresolved_qualified'], 2)
            self.assertEqual(state['realized_other'] + state['unresolved_other'], cohort_size - 2)
            self.assertEqual(state['unresolved_qualified'] + state['unresolved_other'],
                             cohort_size - len(selections))
        self.assertEqual(sum((b.get_skill_level('spot') or 0) == 4 for b in selections), 2)
        self.assertEqual(group.formation_trait_state('trained_spotter')['unresolved_qualified'], 0)
        self.assertEqual(group.counts()['adults'], cohort_size)

    def test_later_learning_and_health_do_not_rewrite_formation_quota(self):
        world, group, _ = make_group()
        candidates = adult_keys(group)
        realized = [group.realize_being(world, *key) for key in candidates[:2]]
        state_before = group.formation_trait_state('trained_spotter')
        initial_levels = [being.get_skill_level('spot') or 0 for being in realized]
        for being in realized:
            being.set_skill_level(world.get_skill_dictionary(), 'spot', 7)
        realized[0].set_hit_points(-10)
        self.assertEqual(group.formation_trait_state('trained_spotter'), state_before)
        self.assertEqual(group.counts()['adults'], len(candidates))
        self.assertEqual(group.aggregate_state()['categories']['adults']['known_dead'], 1)
        self.assertTrue(all(rec['level'] == 7
                            for rec in group.known_skill_state('spot')['known'].values()))
        # Initial formation status is not recalculated from these new skill levels.
        self.assertTrue(all(value in (0, 4) for value in initial_levels))

    def test_invalid_quota_cannot_create_a_being(self):
        world, group, _ = make_group(quota=999)
        with self.assertRaises(ValueError):
            group.formation_trait_state('trained_spotter')
        with self.assertRaises(ValueError):
            group.realize_being(world, *adult_keys(group)[0])
        self.assertEqual(group.realized_being_count, 0)
        self.assertEqual(group.materialized_count, 0)
        self.assertEqual(world.get_object_registry().len(), 1)

    def test_unknown_skill_and_invalid_level_leave_world_unchanged(self):
        for trait in ({'count': 2, 'initial_skills': {'no_such_skill': 1}},
                      {'count': 2, 'initial_skills': {'spot': -1}}):
            with self.subTest(trait=trait):
                world, group, _ = make_group()
                group._formation_traits['adults']['trained_spotter'] = trait
                with self.assertRaises(ValueError):
                    group.realize_being(world, *adult_keys(group)[0])
                self.assertEqual(group.materialized_count, 0)
                self.assertEqual(group.realized_being_count, 0)
                self.assertEqual(world.get_object_registry().len(), 1)

    def test_zero_and_full_formation_quotas(self):
        for full in (False, True):
            world, group, _ = make_group(quota=0)
            if full:
                group._formation_traits['adults']['trained_spotter']['count'] = group.counts()['adults']
            quota = group.counts()['adults'] if full else 0
            before = group.formation_trait_state('trained_spotter')
            self.assertEqual(before['unresolved_qualified'], quota)
            first = group.realize_being(world, *adult_keys(group)[0])
            self.assertEqual(first.get_skill_level('spot') or 0, 4 if full else 0)
            state = group.formation_trait_state('trained_spotter')
            self.assertEqual(state['unresolved_qualified'], quota - int(full))

    def test_unconfigured_groups_unchanged(self):
        config = deepcopy(BASE_CONFIG)
        world = Universe('Unconstrained test', library=Library(config_dir=str(ROOT / 'src' / 'config')))
        group = StatisticalGroup(config['group_name'], config['group_id'], config, config['seed'])
        world.add_object(group)
        being = group.realize_being(world, 0, 'adults', 0)
        self.assertIsNotNone(being)
        with self.assertRaises(ValueError):
            group.formation_trait_state('trained_spotter')


if __name__ == '__main__':
    unittest.main()
