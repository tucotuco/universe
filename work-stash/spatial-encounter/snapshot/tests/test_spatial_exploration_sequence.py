"""The integrated exploration slice reflects interim exact Spot evidence."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'examples')]

from spatial_exact_group_spot import demo_data, run_scenario


class TestSpatialExplorationSequence(unittest.TestCase):
    def test_two_observers_receive_exact_private_group_count_without_inquiry(self):
        result = run_scenario()
        _, encounter, observers, group, ledgers, actions, inspection, inquiries, _ = result
        self.assertEqual(encounter.time, 6)
        self.assertEqual(tuple(row.boundary for row in inspection.timeline), tuple(range(1, 7)))
        self.assertEqual([inspection.action(action.id).resolved_boundary for action in actions], [6, 6])
        self.assertEqual(inquiries, [None, None])
        self.assertEqual([ledger.evidence[0].reports['visible_count'].uncertainty
                          for ledger in ledgers], [0, 0])
        self.assertEqual([ledger.evidence[0].reports['visible_count'].estimate
                          for ledger in ledgers], [sum((group.counts()['humans'],
                          group.counts()['livestock'], group.counts()['dogs']))] * 2)
        self.assertEqual(group.materialized_count, 0)
        self.assertEqual([observer.get_skill_experience('spot') for observer in observers], [0, 0])

    def test_developer_example_reports_changed_inquiry_branch_and_no_position_disclosure(self):
        first, second = demo_data(), demo_data()
        self.assertIn('not an Agent interface', first['presentation'])
        self.assertEqual(first['observations'], second['observations'])
        for observation in first['observations']:
            self.assertEqual(observation['uncertainty'], 0)
            self.assertIsNone(observation['reported_position'])
            self.assertIsNone(observation['inquiry_policy_result'])
            self.assertEqual(observation['species_categories_disclosed'], ())
            self.assertTrue(observation['owner_has_evidence'])
            self.assertFalse(observation['other_observer_has_evidence'])


if __name__ == '__main__':
    unittest.main()
