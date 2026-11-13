"""Regression for adopted fixed-priority overlap penalties."""

import sys
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))

from multiple_action_rules import (MultipleActionRuleError,
    validate_priority_penalties, validate_priority_schedule)


class TestMultipleActionRules(unittest.TestCase):
    def test_adopted_priority_rows_and_permutations(self):
        cases=((0,),(0,3),(1,2),(0,1,5),(0,2,4),(1,2,3),
               (0,1,2,6),(0,1,3,5),(0,2,3,4))
        for row in cases:
            for permutation in set(__import__('itertools').permutations(row)):
                with self.subTest(penalties=permutation):
                    self.assertEqual(validate_priority_penalties(permutation),tuple(sorted(row)))

    def test_non_table_allocations_do_not_pass_by_total_alone(self):
        for penalties in ((2,2),(0,0),(0,0,0,9),(),(0,)*5,
                          (-1,4),(True,2),(0,2,5)):
            with self.subTest(penalties=penalties), self.assertRaises(MultipleActionRuleError):
                validate_priority_penalties(penalties)

    def test_fixed_priorities_are_checked_for_each_overlap_set(self):
        intervals={'long-dagger':(0,4),'short-dagger-first':(0,2),
                   'short-dagger-second':(2,4)}
        self.assertTrue(validate_priority_schedule(intervals,
            {'long-dagger':0,'short-dagger-first':3,'short-dagger-second':3}))
        self.assertTrue(validate_priority_schedule(intervals,
            {'long-dagger':1,'short-dagger-first':2,'short-dagger-second':2}))
        with self.assertRaises(MultipleActionRuleError):
            validate_priority_schedule(intervals,
                {'long-dagger':0,'short-dagger-first':1,'short-dagger-second':3})

    def test_three_simultaneous_actions_use_exact_adopted_multiset(self):
        intervals={'long':(0,6),'short-first':(0,2),'short-second':(4,6)}
        self.assertTrue(validate_priority_schedule(intervals,
            {'long':0,'short-first':3,'short-second':3}))
        with self.assertRaises(MultipleActionRuleError):
            validate_priority_schedule(intervals,
                {'long':0,'short-first':1,'short-second':3})


if __name__=='__main__':
    unittest.main()
