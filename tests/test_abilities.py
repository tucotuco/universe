#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2023 Rauthiflor LLC"
__version__ = "test_ability.py 2023-03-30T02:10-03:00"

# TODO: Check comprehensiveness

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath('../src'))
#print(f'{__version__}:{sys.path}')

from abilities import Abilities

class TestSpeeds(unittest.TestCase):
    def test_create_empty_abilities(self):
        abilities = Abilities()
        self.assertEqual(abilities.STR(), 10)
        self.assertEqual(abilities.DEX(), 10)
        self.assertEqual(abilities.CON(), 10)
        self.assertEqual(abilities.INT(), 10)
        self.assertEqual(abilities.WIS(), 10)
        self.assertEqual(abilities.CHA(), 10)

    def test_create_numeric_abilities(self):
        abilities = Abilities(10, 12, 9, 11, 13, 8)
        self.assertEqual(abilities.STR(), 10)
        self.assertEqual(abilities.DEX(), 12)
        self.assertEqual(abilities.CON(), 9)
        self.assertEqual(abilities.INT(), 11)
        self.assertEqual(abilities.WIS(), 13)
        self.assertEqual(abilities.CHA(), 8)

    def test_create_txt_abilities_text(self):
        abilities = Abilities("10", "12", "9", "11", "13", "8")
        self.assertEqual(abilities.STR(), 10)
        self.assertEqual(abilities.DEX(), 12)
        self.assertEqual(abilities.CON(), 9)
        self.assertEqual(abilities.INT(), 11)
        self.assertEqual(abilities.WIS(), 13)
        self.assertEqual(abilities.CHA(), 8)

    def test_set_ability(self):
        abilities = Abilities(10, 10, 10, 10, 10, 10)
        abilities.set_ability('strength', -1)
        self.assertEqual(abilities.STR(), 0)
        abilities.set_ability('dexterity', True)
        self.assertEqual(abilities.DEX(), 1)
        abilities.set_ability('constitution', "some string")
        self.assertEqual(abilities.CON(), 10)
        abilities.set_ability('INT', 12)
        self.assertEqual(abilities.INT(), 12)
        abilities.set_ability('wisdom', 30)
        self.assertEqual(abilities.WIS(), 30)
        abilities.set_ability('charisma', "12")
        self.assertEqual(abilities.CHA(), 12)

if __name__ == '__main__':
    unittest.main()
