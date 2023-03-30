#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2023 Rauthiflor LLC"
__version__ = "test_utils.py 2023-03-15T10:26-03:00"

# TODO: Check comprehensiveness

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath('../src'))
#print(f'{__version__}:{sys.path}')

from utils import convert_to_numeric, convert_to_boolean
from utils import convert_to_ability, convert_to_speed, convert_to_experience
from utils import convert_to_fatigue

class TestConvertToNumeric(unittest.TestCase):
    def test_int(self):
        self.assertEqual(convert_to_numeric(5), 5)

    def test_float(self):
        self.assertEqual(convert_to_numeric(3.14), 3.14)

    def test_bool(self):
        self.assertEqual(convert_to_numeric(True), 1)
        self.assertEqual(convert_to_numeric(False), 0)

    def test_str_int(self):
        self.assertEqual(convert_to_numeric("10"), 10)

    def test_str_float(self):
        self.assertEqual(convert_to_numeric("3.14"), 3.14)

    def test_empty_str(self):
        self.assertIsNone(convert_to_numeric(""))

    def test_none(self):
        self.assertIsNone(convert_to_numeric(None))

    def test_other_type(self):
        self.assertIsNone(convert_to_numeric("abc"""))
            
    def test_already_int(self):
        self.assertEqual(convert_to_numeric(10), 10)
        
    def test_already_float(self):
        self.assertEqual(convert_to_numeric(3.14), 3.14)

class TestConvertToBoolean(unittest.TestCase):
    def test_int(self):
        self.assertEqual(convert_to_boolean(5), None)

    def test_float(self):
        self.assertEqual(convert_to_boolean(3.14), None)

    def test_bool(self):
        self.assertEqual(convert_to_boolean(True), True)
        self.assertEqual(convert_to_boolean(False), False)

    def test_str_int(self):
        self.assertEqual(convert_to_boolean("10"), None)

    def test_str_float(self):
        self.assertEqual(convert_to_boolean("3.14"), None)

    def test_other_str(self):
        self.assertIsNone(convert_to_boolean("whatever"))
        self.assertIsNone(convert_to_boolean("not true"))
        self.assertIsNone(convert_to_boolean("not false"))

    def test_none(self):
        self.assertIsNone(convert_to_boolean(None))

    def test_bool_str(self):
        self.assertEqual(convert_to_boolean("True"), True)
        self.assertEqual(convert_to_boolean("true"), True)
        self.assertEqual(convert_to_boolean("T"), True)
        self.assertEqual(convert_to_boolean("t"), True)
        self.assertEqual(convert_to_boolean("Tlue"), True)
        self.assertEqual(convert_to_boolean("False"), False)
        self.assertEqual(convert_to_boolean("false"), False)
        self.assertEqual(convert_to_boolean("F"), False)
        self.assertEqual(convert_to_boolean("f"), False)
        self.assertEqual(convert_to_boolean("Flase"), False)

class TestConvertToAbility(unittest.TestCase):
    def test_int(self):
        self.assertEqual(convert_to_ability(0), 0)
        self.assertEqual(convert_to_ability(1), 1)
        self.assertEqual(convert_to_ability(-1), 0)

    def test_float(self):
        self.assertEqual(convert_to_ability(3.14), 0)

    def test_bool(self):
        self.assertEqual(convert_to_ability(True), 1)
        self.assertEqual(convert_to_ability(False), 0)

    def test_str_int(self):
        self.assertEqual(convert_to_ability("0"), 0)
        self.assertEqual(convert_to_ability("10"), 10)
        self.assertEqual(convert_to_ability("-1"), 0)

    def test_str_float(self):
        self.assertEqual(convert_to_ability("3.14"), 0)

    def test_other_str(self):
        self.assertEqual(convert_to_ability("whatever"), 0)

    def test_none(self):
        self.assertEqual(convert_to_ability(None), 0)

class TestConvertToSpeed(unittest.TestCase):
    def test_int(self):
        self.assertEqual(convert_to_speed(0), 0)
        self.assertEqual(convert_to_speed(1), 1)
        self.assertEqual(convert_to_speed(-1), 0)

    def test_float(self):
        self.assertEqual(convert_to_speed(3.14), 0)

    def test_bool(self):
        self.assertEqual(convert_to_speed(True), 1)
        self.assertEqual(convert_to_speed(False), 0)

    def test_str_int(self):
        self.assertEqual(convert_to_speed("0"), 0)
        self.assertEqual(convert_to_speed("10"), 10)
        self.assertEqual(convert_to_speed("-1"), 0)

    def test_str_float(self):
        self.assertEqual(convert_to_speed("3.14"), 0)

    def test_other_str(self):
        self.assertEqual(convert_to_speed("whatever"), 0)

    def test_none(self):
        self.assertEqual(convert_to_speed(None), 0)

class TestConvertToExperience(unittest.TestCase):
    def test_int(self):
        self.assertEqual(convert_to_experience(0), 0)
        self.assertEqual(convert_to_experience(1), 1)
        self.assertEqual(convert_to_experience(-1), 0)

    def test_float(self):
        self.assertEqual(convert_to_experience(3.14), 0)

    def test_bool(self):
        self.assertEqual(convert_to_experience(True), 1)
        self.assertEqual(convert_to_experience(False), 0)

    def test_str_int(self):
        self.assertEqual(convert_to_experience("0"), 0)
        self.assertEqual(convert_to_experience("10"), 10)
        self.assertEqual(convert_to_experience("-1"), 0)

    def test_str_float(self):
        self.assertEqual(convert_to_experience("3.14"), 0)

    def test_other_str(self):
        self.assertEqual(convert_to_experience("whatever"), 0)

    def test_none(self):
        self.assertEqual(convert_to_experience(None), 0)

class TestConvertToFatiguee(unittest.TestCase):
    def test_int(self):
        self.assertEqual(convert_to_fatigue(0), 0)
        self.assertEqual(convert_to_fatigue(1), 1)
        self.assertEqual(convert_to_fatigue(-1), 0)
        self.assertEqual(convert_to_fatigue(6), 5)

    def test_float(self):
        self.assertEqual(convert_to_fatigue(3.14), 0)

    def test_bool(self):
        self.assertEqual(convert_to_fatigue(True), 1)
        self.assertEqual(convert_to_fatigue(False), 0)

    def test_str_int(self):
        self.assertEqual(convert_to_fatigue("0"), 0)
        self.assertEqual(convert_to_fatigue("10"), 5)
        self.assertEqual(convert_to_fatigue("-1"), 0)

    def test_str_float(self):
        self.assertEqual(convert_to_fatigue("3.14"), 0)

    def test_other_str(self):
        self.assertEqual(convert_to_fatigue("whatever"), 0)

    def test_none(self):
        self.assertEqual(convert_to_fatigue(None), 0)

if __name__ == '__main__':
    unittest.main()
