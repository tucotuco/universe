#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2023 Rauthiflor LLC"
__version__ = "test_utils.py 2023-01-03T14:43+02:00"

# TODO: Check comprehensiveness

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath('../src'))
#print(f'{__version__}:{sys.path}')

from utils import get_random_key
from utils import roll_dice
from utils import convert_to_numeric, convert_to_boolean, convert_to_dc
from utils import convert_to_ability, convert_to_speed, convert_to_experience
from utils import convert_to_fatigue

class TestGetRandomKey(unittest.TestCase):
    def test_with_empty_dict(self):
        result = get_random_key({})
        self.assertIsNone(result)
    
    def test_with_non_dict_input(self):
        result = get_random_key([])
        self.assertIsNone(result)
    
    def test_with_single_entry_dict(self):
        the_dict = {'a': 1}
        result = get_random_key(the_dict)
        self.assertEqual(result, 'a')
    
    def test_with_multi_entry_dict(self):
        the_dict = {'a': 1, 'b': 2, 'c': 3}
        result = get_random_key(the_dict)
        self.assertIn(result, the_dict.keys())

class TestRollDice(unittest.TestCase):    
    def test_valid_input(self):
        i=0
        for _ in range(1000):
            result = roll_dice('1d20-5')
            self.assertLessEqual(result,15)
            self.assertGreaterEqual(result,-4)

        i=0
        for _ in range(1000):
            result = roll_dice('1d8')
            self.assertLessEqual(result,8)
            self.assertGreaterEqual(result,1)

        i=0
        for _ in range(1000):
            result = roll_dice('1d20+5')
            self.assertLessEqual(result,25)
            self.assertGreaterEqual(result,6)

        i=0
        for _ in range(1000):
            result = roll_dice('20d20+100')
            self.assertLessEqual(result,500)
            self.assertGreaterEqual(result,120)

        i=0
        for _ in range(1000):
            result = roll_dice('20d20-100')
            self.assertLessEqual(result,300)
            self.assertGreaterEqual(result,-80)

        i=0
        for _ in range(1000):
            result = roll_dice('2d4-1')
            self.assertLessEqual(result,7)
            self.assertGreaterEqual(result,1)
    
    def test_invalid_input(self):
        with self.assertRaises(ValueError) as cm:
            roll_dice('d20')  # Missing number of dice
        self.assertEqual(str(cm.exception), 'Invalid dice string: d20')
        
        with self.assertRaises(ValueError) as cm:
            roll_dice('1d')  # Missing number of sides
        self.assertEqual(str(cm.exception), 'Invalid dice string: 1d')
        
        with self.assertRaises(ValueError) as cm:
            roll_dice('1d20-')  # Missing modifier value
        self.assertEqual(str(cm.exception), 'Invalid dice string: 1d20-')
        
        with self.assertRaises(ValueError) as cm:
            roll_dice('1d20++5')  # Invalid modifier format
        self.assertEqual(str(cm.exception), 'Invalid dice string: 1d20++5')
        
        with self.assertRaises(ValueError) as cm:
            roll_dice('1d20+5.5')  # Invalid modifier format
        self.assertEqual(str(cm.exception), 'Invalid dice string: 1d20+5.5')
        
        with self.assertRaises(ValueError) as cm:
            roll_dice('1d20+-5')  # Invalid modifier format
        self.assertEqual(str(cm.exception), 'Invalid dice string: 1d20+-5')
        
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

class TestConvertToFatigue(unittest.TestCase):
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

class TestConvertToDC(unittest.TestCase):
    def test_int(self):
        self.assertEqual(convert_to_dc(0), 0)
        self.assertEqual(convert_to_dc(1), 1)
        self.assertEqual(convert_to_dc(-1), 0)
        self.assertEqual(convert_to_dc(30), 30)
        self.assertEqual(convert_to_dc(31), 30)

    def test_float(self):
        self.assertEqual(convert_to_dc(3.14), 0)

    def test_bool(self):
        self.assertEqual(convert_to_dc(True), 1)
        self.assertEqual(convert_to_dc(False), 0)

    def test_str_int(self):
        self.assertEqual(convert_to_dc("0"), 0)
        self.assertEqual(convert_to_dc("21"), 21)
        self.assertEqual(convert_to_dc("-1"), 0)
        self.assertEqual(convert_to_dc("30"), 30)

    def test_str_float(self):
        self.assertEqual(convert_to_dc("3.14"), 0)

    def test_other_str(self):
        self.assertEqual(convert_to_dc("whatever"), 0)

    def test_none(self):
        self.assertEqual(convert_to_dc(None), 0)

if __name__ == '__main__':
    unittest.main()
