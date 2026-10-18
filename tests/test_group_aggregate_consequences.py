"""Individual consequences projected back into group-level summaries."""
from pathlib import Path
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'examples')]

from group_aggregate_consequences import run_scenario_with_consequences
from statistical_group import StatisticalGroup
from spatial.state import CartesianPosition

CONFIG = json.loads((ROOT / 'examples' / 'nomadic_group.json').read_text())


class GroupAggregateConsequencesTests(unittest.TestCase):
    def test_unrealized_members_do_not_acquire_fictitious_status(self):
        group = StatisticalGroup(CONFIG['group_name'], CONFIG['group_id'],
                                 CONFIG, CONFIG['seed'])
        state = group.aggregate_state()
        self.assertEqual(state['composition'], group.counts())
        for category, count in group.counts().items():
            if category not in group.CATEGORIES:
                continue
            record = state['categories'][category]
            self.assertEqual(record['committed'], count)
            self.assertEqual(record['unresolved'], count)
            self.assertEqual(record['realized'], 0)
            self.assertEqual(record['known_living'], 0)
            self.assertEqual(record['known_dead'], 0)

    def test_action_consequences_update_derived_state_without_count_mutation(self):
        outcome = run_scenario_with_consequences()
        group, herder = outcome['group'], outcome['herder']
        before = outcome['before']['categories']['adults']
        midway = outcome['incapacitated']['categories']['adults']
        after = outcome['deceased']['categories']['adults']
        self.assertEqual(before['known_living'], 1)
        self.assertEqual(before['known_dead'], 0)
        self.assertEqual(midway['known_living'], 1)
        self.assertEqual(midway['known_incapacitated'], 1)
        self.assertEqual(midway['known_injured'], 1)
        self.assertEqual(after['known_living'], 0)
        self.assertEqual(after['known_dead'], 1)
        self.assertEqual(after['known_incapacitated'], 0)
        self.assertEqual(after['known_injured'], 0)
        for snapshot in (before, midway, after):
            self.assertEqual(snapshot['realized'], 1)
            self.assertEqual(snapshot['unresolved'], snapshot['committed'] - 1)
        self.assertEqual(outcome['deceased']['composition'], outcome['counts_before'])
        self.assertEqual(group.counts(), outcome['counts_before'])
        self.assertIs(group.realize_being(outcome['world'], 0, 'adults', 0, name='Herder'), herder)
        self.assertTrue(herder.is_dead())
        self.assertEqual(herder.get_hit_points(), -10)
        self.assertTrue(all(outcome['world'].get_event_by_id(e.id) is e
                            for e in outcome['health_actions']))
        self.assertTrue(all(e.id in outcome['encounter'].finished_action_list
                            for e in outcome['health_actions']))

    def test_skill_change_reaches_group_view_but_not_unknown_members(self):
        outcome = run_scenario_with_consequences()
        sample = outcome['group'].known_skill_state('run')
        self.assertEqual(sample['known'][outcome['herder'].id], {
            'level': 1, 'practice_experience': 250})
        self.assertEqual(sample['unresolved_adults'],
                         outcome['counts_before']['adults'] - 1)
        self.assertEqual(outcome['practiced'], sample)
        with self.assertRaises(ValueError):
            outcome['group'].known_skill_state('')

    def test_view_is_derived_fresh_from_authoritative_being(self):
        outcome = run_scenario_with_consequences()
        group, being = outcome['group'], outcome['herder']
        frozen_view = group.aggregate_state()
        being.set_hit_points(5)
        current_view = group.aggregate_state()
        self.assertEqual(frozen_view['categories']['adults']['known_dead'], 1)
        self.assertEqual(current_view['categories']['adults']['known_living'], 1)
        self.assertEqual(current_view['categories']['adults']['known_dead'], 0)
        self.assertEqual(current_view['categories']['adults']['known_injured'],
                         int(5 < being.original.hit_points))
        self.assertEqual(group.member_position(outcome['member']), being.get_position())


if __name__ == '__main__':
    unittest.main()
