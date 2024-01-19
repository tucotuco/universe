#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2023 Rauthiflor LLC"
__version__ = "test_action.py 2024-01-19T01:03-08:00"

# TODO: Check comprehensiveness

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath('../src'))

from action import Action, Swing, Thrust
from being import BeingDefinition, BeingInstance
from strategy import Strategy
from universe import Universe
from library import Library
	
class TestAction(unittest.TestCase):

    def setUp(self):
        self.universe = Universe(name="Test Universe", library=Library())
        self.start_time = 0
        self.end_time = 10
        self.actor_id = self.universe.make_being("zombie", "Tobez")
        self.target_id = self.universe.make_being("skeleton", "Gordo")
        self.instrument_id = encounter.make_weapon_for_being(self.actor_id, "Longsword", "Loki")
        encounter.arm_being(self.actor_id, self.instrument_id, "left hand")
        self.strategy = Strategy()
        self.location = None
        self.parent_event_id = None

        self.action = Action(self.universe, self.start_time, self.end_time, "action",
                             self.actor_id, self.target_id, self.instrument_id, self.strategy,
                             self.location, "Test Action", self.parent_event_id)

        self.swing = Swing(self.universe, self.start_time, self.end_time, "swing",
                             self.actor_id, self.target_id, self.instrument_id, self.strategy,
                             self.location, "Test Swing", self.parent_event_id)

        self.thrust = Thrust(self.universe, self.start_time, self.end_time, "thrust",
                             self.actor_id, self.target_id, self.instrument_id, self.strategy,
                             self.location, "Test Thrust", self.parent_event_id)

    def test_set_actor_id(self):
        # Test setting a valid actor_id
        new_actor_id = 5
        self.action.set_actor_id(new_actor_id)
        self.assertEqual(self.action.actor_id, new_actor_id)

    def test_set_target_id(self):
        # Test setting a valid actor_id
        new_target_id = 5
        self.action.set_target_id(new_target_id)
        self.assertEqual(self.action.target_id, new_target_id)

    def test_calculate_end_time(self):
        self.assertEqual(self.action.calculate_end_time(5,6), 1)
        self.assertEqual(self.action.calculate_end_time(5,5), 1)
        self.assertEqual(self.action.calculate_end_time(5,4), 1)
        self.assertEqual(self.action.calculate_end_time(5,3), 2)
        self.assertEqual(self.action.calculate_end_time(5,1), 4)
        self.assertEqual(self.action.calculate_end_time(5,0), 5)

    def test_roll_hits(self):
        # Test roll_hits method with various scenarios
        self.universe.get_object_by_id.side_effect = [Mock(), Mock()]  # Mocking actor and target
        self.action.parent_event_id = 4
        parent_event_mock = Mock()
        parent_event_mock.difficulty_class = 15
        self.universe.get_event_by_id.return_value = parent_event_mock

        roll = 15  
        self.assertTrue(self.action.roll_hits(roll))

        roll = 20  
        self.assertTrue(self.action.roll_hits(roll))

        roll = 14
        self.assertFalse(self.action.roll_hits(roll))

        roll = 1
        self.assertFalse(self.action.roll_hits(roll))

    def test_resolve(self):
        # Since resolve is expected to be overridden in subclasses, you might test it differently
        # or just check that it's correctly set up to be overridden
        pass

    # Add more tests for other methods as needed

if __name__ == '__main__':
    unittest.main()

if __name__ == '__main__':
    unittest.main()
