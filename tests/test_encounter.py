#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2024 Rauthiflor LLC"
__version__ = "test_encounter.py 2024-02-28T03:00-03:00"

# TODO: Everything
# TODO: Check comprehensiveness

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath('../src'))
#print(f'{__version__}:{sys.path}')

from being import BeingDefinition, BeingInstance
from encounter import Encounter
from event import Event
from library import Library
from object import ObjectRegistry
from universe import Universe

import unittest

class TestEncounter(unittest.TestCase):
    def setUp(self):
        self.universe = Universe(name="Test Universe", library=Library(config_dir="../src/config"))
        self.encounter = Encounter(self.universe, 10, 0)

    def test_init(self):
        self.assertIsNone(self.encounter.location)
        self.assertEqual(self.encounter.start_time, 0)
        self.assertIsNone(self.encounter.end_time)
        self.assertEqual(self.encounter.name, "")
        self.assertIsNone(self.encounter.parent_event_id)
        self.assertIsNone(self.encounter.map)
        self.assertEqual(len(self.encounter.being_list),0)
        self.assertEqual(len(self.encounter.pending_action_list),0)
        self.assertEqual(len(self.encounter.finished_action_list),0)

    def test_generate(self):
        self.encounter.generate()
#        self.assertIsNotNone(self.encounter.map)

    def test_add_being(self):
        being_id1 = self.universe.make_being("Human", "Tobe")
        being_id2 = self.universe.make_being("High elf", "Elf dude")
        self.assertIsNotNone(self.universe.get_object_by_id(being_id1))
        self.assertIsNotNone(self.universe.get_object_by_id(being_id2))
        self.encounter.add_being(being_id1)
        self.encounter.add_being(being_id2)
        self.assertEqual(len(self.encounter.being_list),2)
        self.assertEqual(len(self.encounter.non_being_object_list),0)
        
if __name__ == '__main__':
    unittest.main()
