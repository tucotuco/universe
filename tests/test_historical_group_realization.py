"""Historical Group composition and selective realization contract tests."""
from pathlib import Path
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'examples')]

from statistical_group import StatisticalGroup

CONFIG = json.loads((ROOT / "examples" / "nomadic_group.json").read_text())

def make_group():
    return StatisticalGroup(CONFIG["group_name"], CONFIG["group_id"], CONFIG, CONFIG["seed"])
from group_membership_changes import run_experiment as membership_scenario
from realization import Fact, FactKey, ImpossibleRealization


class HistoricalGroupRealizationTests(unittest.TestCase):
    def test_inspection_without_realization_then_partial_household_refinement(self):
        group = make_group()
        before = group.state_at(0)
        self.assertIsNone(before['formation_composition'])
        self.assertIsNone(before['current_composition'])
        self.assertEqual(before['households_committed'], 0)
        self.assertIsNone(before['households_unresolved'])
        self.assertEqual(group._composition_reality.revision, 0)
        group.advance(5)
        household_total = group.refine_formation_at(2)
        self.assertEqual(household_total, group.household_count)
        self.assertEqual(group.state_at(0)['households_unresolved'], household_total)
        one = group.refine_formation_at(3, household=0)
        self.assertEqual(one, group.household(0))
        snap = group.state_at(0)
        self.assertEqual(snap['households_committed'], 1)
        self.assertEqual(snap['households_unresolved'], household_total - 1)
        self.assertEqual(snap['known_formation_minima']['adults'], one['adults'])
        self.assertIsNone(snap['formation_composition'])
        self.assertEqual(group.materialized_count, 0)
        self.assertEqual(group.realized_being_count, 0)
        revision = group._composition_reality.revision
        self.assertEqual(group.refine_formation_at(0, household=0), one)
        self.assertEqual(group._composition_reality.revision, revision)

    def test_all_formation_facts_are_single_source_and_historically_fixed(self):
        group = make_group()
        counts = group.counts()
        from_start = group.state_at(0)
        self.assertEqual(from_start['formation_composition'], counts)
        self.assertEqual(from_start['current_composition'], counts)
        group.advance(100)
        self.assertEqual(group.state_at(100)['formation_composition'], counts)
        self.assertEqual(group.state_at(100)['current_composition'], counts)
        self.assertEqual(group.state_at(100)['households_unresolved'], 0)
        first = group._composition_reality.inspect(group._formation_key('household', '0'))
        self.assertEqual(first.value, group.household(0))
        with self.assertRaises(ImpossibleRealization):
            group._composition_reality.commit([
                Fact(group._formation_key('household', '0'),
                     dict(first.value, adults=first.value['adults']+1))])
        self.assertEqual(group.household(0), first.value)

    def test_historical_queries_replay_independent_leave_and_join(self):
        scenario = membership_scenario()
        a, b = scenario['western'], scenario['eastern']
        original_a, original_b = scenario['baseline']
        self.assertEqual(a.state_at(0)['current_composition'], original_a)
        self.assertEqual(b.state_at(0)['current_composition'], original_b)
        self.assertEqual(a.state_at(1)['current_composition']['adults'], original_a['adults']-1)
        self.assertEqual(a.state_at(3)['current_composition']['adults'], original_a['adults']-1)
        self.assertEqual(b.state_at(3)['current_composition'], original_b)
        self.assertEqual(b.state_at(5)['current_composition']['adults'], original_b['adults']+1)
        self.assertEqual(len(a.state_at(0)['membership_changes']), 0)
        self.assertEqual(len(a.state_at(1)['membership_changes']), 1)
        self.assertEqual(len(b.state_at(5)['membership_changes']), 1)
        revision = a._composition_reality.revision
        self.assertEqual(a.state_at(1)['formation_composition'], original_a)
        self.assertEqual(a._composition_reality.revision, revision)
        self.assertEqual(scenario['being'].get_skill_level('spot'), 6)

    def test_late_refinement_does_not_rewrite_prior_or_later_membership(self):
        from copy import deepcopy
        from statistical_group import StatisticalGroup
        from universe import Universe
        from library import Library
        base = json.loads((ROOT/'examples/nomadic_group.json').read_text())
        world = Universe('test', library=Library(config_dir=str(ROOT/'src/config')))
        group = StatisticalGroup('New arrival Group', 'new-arrival', base, 12)
        world.add_object(group)
        # A Being may join without requiring the destination Group to resolve
        # its original households or population beforehand.
        other = StatisticalGroup('Original Group', 'origin', base, 4)
        world.add_object(other)
        being = other.realize_being(world, 0, 'adults', 0)
        other.leave_being(world, being)
        group.advance(5)
        group.join_being(world, being)
        self.assertIsNone(group.state_at(0)['current_composition'])
        self.assertEqual(len(group.state_at(5)['membership_changes']), 1)
        group.refine_formation_at(0)
        h0 = group.refine_formation_at(2, 0)
        self.assertEqual(group.state_at(0)['known_formation_minima']['adults'], h0['adults'])
        self.assertIsNone(group.state_at(5)['current_composition'])
        group.counts()
        original = group.state_at(0)['current_composition']['adults']
        self.assertEqual(group.state_at(4)['current_composition']['adults'], original)
        self.assertEqual(group.state_at(5)['current_composition']['adults'], original+1)
        self.assertEqual(group.current_counts()['adults'], original+1)
        self.assertEqual(group.realized_being_count, 0)
        self.assertEqual(group.materialized_count, 0)

    def test_invalid_historical_time_and_inadmissible_fact_leave_state_unchanged(self):
        group = make_group()
        group.advance(5)
        for t in (-1, 6, float('nan'), 'xyz'):
            with self.subTest(time=t), self.assertRaises(ValueError):
                group.state_at(t)
            with self.assertRaises(ValueError):
                group.refine_formation_at(t)
        revision = group._composition_reality.revision
        with self.assertRaises(ImpossibleRealization):
            group._composition_reality.commit([
                Fact(FactKey(group.id, 'household', group.formation_time, '5'),
                     {'adults': 2, 'children': 1, 'livestock': 2, 'dogs': 1})])
        self.assertEqual(group._composition_reality.revision, revision)
        self.assertIsNone(group.state_at(0)['formation_composition'])


if __name__ == '__main__':
    unittest.main()
