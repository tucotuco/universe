#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2023 Rauthiflor LLC"
__version__ = "test_speeds.py 2023-03-30T02:11-03:00"

# TODO: Check comprehensiveness

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath('../src'))
#print(f'{__version__}:{sys.path}')

from speeds import Speed

class TestSpeeds(unittest.TestCase):
    def test_create_speeds(self):
        self.speed = Speed(6, 5, 4, 3, 2)
        self.assertEqual(self.speed.sprint(), 6)
        self.assertEqual(self.speed.burrow(), 5)
        self.assertEqual(self.speed.climb(), 4)
        self.assertEqual(self.speed.fly(), 3)
        self.assertEqual(self.speed.swim(), 2)

    def test_create_speeds_text(self):
        self.speed = Speed('6', '5', '4', '3', '2')
        self.assertEqual(self.speed.sprint(), 6)
        self.assertEqual(self.speed.burrow(), 5)
        self.assertEqual(self.speed.climb(), 4)
        self.assertEqual(self.speed.fly(), 3)
        self.assertEqual(self.speed.swim(), 2)

    def test_set_max_speed_valid(self):
        self.speed = Speed(6, 5, 4, 3, 2)
        self.speed.set_max_speed('ambulate', 'not a number')
        self.assertEqual(self.speed.sprint(), 6)
        self.speed.set_max_speed('ambulate', 40)
        self.assertEqual(self.speed.sprint(), 40)
    
    def test_copy(self):
        self.speed = Speed(6, 5, 4, 3, 2)
        copy = self.speed.copy()
        self.assertEqual(copy.sprint(), self.speed.sprint())
        self.assertEqual(copy.burrow(), self.speed.burrow())
        self.assertEqual(copy.climb(), self.speed.climb())
        self.assertEqual(copy.fly(), self.speed.fly())
        self.assertEqual(copy.swim(), self.speed.swim())

        copy.set_max_speed('ambulate', 10)
        copy.set_max_speed('burrow', 10)
        copy.set_max_speed('climb', 10)
        copy.set_max_speed('fly', 10)
        copy.set_max_speed('swim', 10)

        self.assertEqual(self.speed.sprint(), 6)
        self.assertEqual(self.speed.burrow(), 5)
        self.assertEqual(self.speed.climb(), 4)
        self.assertEqual(self.speed.fly(), 3)
        self.assertEqual(self.speed.swim(), 2)

if __name__ == '__main__':
    unittest.main()
