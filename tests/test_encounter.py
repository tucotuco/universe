#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2023 Rauthiflor LLC"
__version__ = "test_encounter.py 2023-04-11T11:33-03:00"

# TODO: Everything
# TODO: Check comprehensiveness

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath('../src'))
#print(f'{__version__}:{sys.path}')

from encounter import Encounter
from event import Event
from object import ObjectRegistry
from being import BeingDefinition, BeingInstance

import unittest

class TestEncounter(unittest.TestCase):
    def setUp(self):
        self.encounter = Encounter(0)

    def test_init(self):
        self.assertIsNone(self.encounter.location)
        self.assertEqual(self.encounter.start_time, 0)
        self.assertIsNone(self.encounter.end_time)
        self.assertEqual(self.encounter.name, "")
        self.assertIsNone(self.encounter.parent)
        self.assertIsNone(self.encounter.map)
        self.assertEqual(len(self.encounter.child_events), 0)
        self.assertIsInstance(self.encounter.objects_present, ObjectRegistry)

    def test_generate(self):
        self.encounter.generate()
#        self.assertIsNotNone(self.encounter.map)

    def test_add_being(self):
        being_def1 = BeingDefinition('Human', '6', '160', '5', '2d4', 'Chaotic Good', '9', '2')
        being_def2 = BeingDefinition('Elf', '6', '120', '5', '2d4', 'Chaotic Good', '9', '2')
        being1 = BeingInstance(being_def1, 'Tobe')
        being2 = BeingInstance(being_def2, 'Elf Dude')
        self.encounter.add_being(being1)
        self.encounter.add_being(being2)
        self.assertEqual(self.encounter.objects_present.len(),2)
        self.assertIsNotNone(self.encounter.objects_present.get_object_by_id(being1.get_id()))
        self.assertIsNotNone(self.encounter.objects_present.get_object_by_id(being2.get_id()))
        
if __name__ == '__main__':
    unittest.main()
