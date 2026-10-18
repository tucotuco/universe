"""Correlated generation: exact cohort quotas and lazy conditional attributes."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'examples')]

from conditional_attributes import ConditionalAttributes
from correlated_group_attributes import run_experiment
from library import Library
from statistical_group import StatisticalGroup
from universe import Universe


def make_group():
    config = deepcopy(json.loads((ROOT / 'examples/nomadic_group.json').read_text()))
    config.update(json.loads((ROOT / 'examples/nomadic_group_correlations.json').read_text()))
    world = Universe('Correlated generation tests',
                     library=Library(config_dir=str(ROOT / 'src/config')))
    group = StatisticalGroup(config['group_name'], config['group_id'], config, config['seed'])
    world.add_object(group)
    return world, group, config


def keys(group):
    return [(household, 'adults', index)
            for household in range(group.household_count)
            for index in range(group.household(household)['adults'])]


class CorrelatedFormationTests(unittest.TestCase):
    def test_only_queried_attributes_and_parents_commit(self):
        _, group, _ = make_group()
        key = keys(group)[0]
        self.assertEqual(group.committed_formation_attributes(*key), {})
        group.formation_attribute(*key, 'role')
        self.assertEqual(set(group.committed_formation_attributes(*key)),
                         {'age_band', 'role'})
        self.assertEqual(group.materialized_count, 0)
        self.assertEqual(group.realized_being_count, 0)
        group.formation_attribute(*key, 'years_in_role')
        self.assertEqual(len(group.committed_formation_attributes(*key)), 3)

    def test_realization_request_order_independence(self):
        w1, g1, _ = make_group()
        w2, g2, _ = make_group()
        for key in reversed(keys(g1)):
            g1.formation_attribute(*key, 'years_in_role')
        for key in keys(g2):
            g2.formation_attribute(*key, 'age_band')
            g2.formation_attribute(*key, 'role')
            g2.formation_attribute(*key, 'years_in_role')
        for key in keys(g1):
            self.assertEqual(g1.committed_formation_attributes(*key),
                             g2.committed_formation_attributes(*key))
        self.assertEqual(g1.counts(), g2.counts())
        self.assertEqual(g1.realized_being_count, 0)
        self.assertEqual(w1.get_object_registry().len(), 1)

    def test_fixed_quota_is_valid_parent_condition(self):
        _, group, _ = make_group()
        assigned = group._adult_formation_assignments('trained_spotter')
        for key in keys(group):
            identifier = f'{group.id}/{key[0]}/adults/{key[2]}'
            age = group.formation_attribute(*key, 'age_band')
            if identifier in assigned:
                self.assertIn(age, {'mature', 'elder'})
            else:
                self.assertIn(age, {'young', 'mature', 'elder'})
        self.assertEqual(group.formation_trait_state('trained_spotter')['unresolved_qualified'], 2)

    def test_conditional_role_and_tenure_constraints(self):
        _, group, _ = make_group()
        role_experience = {
            'herder': {0, 2, 6}, 'hunter': {1, 5, 12}, 'guide': {8, 15}}
        for key in keys(group):
            role = group.formation_attribute(*key, 'role')
            years = group.formation_attribute(*key, 'years_in_role')
            age = group.formation_attribute(*key, 'age_band')
            if age == 'young':
                self.assertEqual(role, 'herder')
            self.assertIn(years, role_experience[role])

    def test_original_attributes_survive_being_learning(self):
        world, group, _ = make_group()
        key = keys(group)[0]
        formation = {name: group.formation_attribute(*key, name)
                     for name in ('age_band', 'role', 'years_in_role')}
        being = group.realize_being(world, *key)
        being.set_skill_level(world.get_skill_dictionary(), 'spot', 8)
        self.assertEqual(group.committed_formation_attributes(*key), formation)
        self.assertEqual(group.realized_being_count, 1)
        self.assertEqual(group.counts()['adults'], len(keys(group)))

    def test_invalid_specs_rejected_before_realization(self):
        _, _, config = make_group()
        for bad in (
            {'a': {'given': 'b', 'conditional_cdfs': {'x': [[1, 1.0]]}},
             'b': {'given': 'a', 'conditional_cdfs': {'x': [[1, 1.0]]}}},
            {'a': {'cdf': [['x', 0.4]]}},
            {'a': {'cdf': [['x', 0.5], ['x', 1.0]]}},
            {'a': {'cdf': [['x', 1.0]]},
             'b': {'given': 'a', 'conditional_cdfs': {'z': [[0, 1.0]]}}},
            {'a': {'given': 'absent', 'conditional_cdfs': {'x': [[0, 1.0]]}}},
        ):
            with self.subTest(spec=bad):
                config['formation_attributes']['adults'] = bad
                with self.assertRaises(ValueError):
                    StatisticalGroup(config['group_name'], config['group_id'],
                                     config, config['seed'])

    def test_group_config_mutation_cannot_rewrite_formed_attributes(self):
        _, group, config = make_group()
        key = keys(group)[0]
        before = group.formation_attribute(*key, 'role')
        config['formation_attributes']['adults']['role']['conditional_cdfs']['young'] = [['bogus', 1.0]]
        self.assertEqual(group.formation_attribute(*key, 'role'), before)

    def test_sampler_has_statistically_distinct_conditions(self):
        from random import Random
        from hashlib import sha256
        spec = {'rank': {'given': 'trained', 'conditional_cdfs': {
            'true': [[5, 1.0]], 'false': [[0, 1.0]]}},
            'role': {'given': 'rank', 'conditional_cdfs': {
                '5': [['hunter', 1.0]], '0': [['herder', 1.0]]}}}
        model = ConditionalAttributes(spec, lambda ident, attr: Random(
            int.from_bytes(sha256(f'{ident}:{attr}'.encode()).digest()[:8], 'big')),
            external_names={'trained'})
        self.assertEqual(model.resolve('a', 'role', {'trained': True}), 'hunter')
        self.assertEqual(model.resolve('b', 'role', {'trained': False}), 'herder')
        self.assertEqual(model.committed('a'), {'rank': 5, 'role': 'hunter'})

    def test_example(self):
        result = run_experiment()
        self.assertEqual(result['before'], {})
        self.assertEqual(set(result['after_role']), {'age_band', 'role'})
        self.assertEqual(result['group'].realized_being_count, 1)


if __name__ == '__main__':
    unittest.main()
