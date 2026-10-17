#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2024 Rauthiflor LLC"
__version__ = "test_Exertion.py 2024-03-29T02:21-03:00"

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath('../src'))

from exertion import Exertion
	
class TestExertion(unittest.TestCase):

    def setUp(self):
        self.exertion_tracker = Exertion()

    # Test setters
    def test_init(self):
        self.setUp()
#        print(f"{self.exertion_tracker.to_json()}")
        self.assertEqual(self.exertion_tracker.start_time, 0)
        self.assertEqual(self.exertion_tracker.end_time, 3600)
        self.assertEqual(self.exertion_tracker.activity_level, "inactive")
        self.assertEqual(self.exertion_tracker.load_level, "light")
        self.assertEqual(self.exertion_tracker.accumulated_exertion, 0)

    def test_set_start_time(self):
        self.setUp()
        self.exertion_tracker.set_start_time(99)
        self.assertEqual(self.exertion_tracker.start_time, 99)
        self.exertion_tracker.set_start_time("88")
        self.assertEqual(self.exertion_tracker.start_time, 88)
        
    def test_set_end_time(self):
        self.setUp()
        self.exertion_tracker.set_end_time(99)
        self.assertEqual(self.exertion_tracker.end_time, 99)
        self.exertion_tracker.set_end_time("88")
        self.assertEqual(self.exertion_tracker.end_time, 88)
        self.exertion_tracker.set_end_time(-1)
        self.assertEqual(self.exertion_tracker.end_time, 0)
 
    def test_set_activity_level(self):
        self.setUp()
        self.exertion_tracker.set_activity_level("invalid")
        self.assertEqual(self.exertion_tracker.activity_level, "inactive")
        self.exertion_tracker.set_activity_level("normal")
        self.assertEqual(self.exertion_tracker.activity_level, "normal")
        self.exertion_tracker.set_activity_level("invalid")
        self.assertEqual(self.exertion_tracker.activity_level, "normal")
        self.exertion_tracker.set_activity_level("inactive")
        self.assertEqual(self.exertion_tracker.activity_level, "inactive")
        self.exertion_tracker.set_activity_level("above normal")
        self.assertEqual(self.exertion_tracker.activity_level, "above normal")
        self.exertion_tracker.set_activity_level("abnormal")
        self.assertEqual(self.exertion_tracker.activity_level, "above normal")
        self.exertion_tracker.set_activity_level("jogging")
        self.assertEqual(self.exertion_tracker.activity_level, "jogging")
        self.exertion_tracker.set_activity_level("swimming")
        self.assertEqual(self.exertion_tracker.activity_level, "swimming")
        self.exertion_tracker.set_activity_level("running")
        self.assertEqual(self.exertion_tracker.activity_level, "running")
        self.exertion_tracker.set_activity_level("combat")
        self.assertEqual(self.exertion_tracker.activity_level, "combat")
        self.exertion_tracker.set_activity_level("sprinting")
        self.assertEqual(self.exertion_tracker.activity_level, "sprinting")

    def test_set_fatigue_level(self):
        self.setUp()
        self.exertion_tracker.set_fatigue_level("4")
        self.assertEqual(self.exertion_tracker.fatigue_level, 4)
        self.exertion_tracker.set_fatigue_level(-1)
        self.assertEqual(self.exertion_tracker.fatigue_level, 0)
        self.exertion_tracker.set_fatigue_level(4.3)
        self.assertEqual(self.exertion_tracker.fatigue_level, 0)
        self.exertion_tracker.set_fatigue_level("3.14")
        self.assertEqual(self.exertion_tracker.fatigue_level, 0)
        self.exertion_tracker.set_fatigue_level(6)
        self.assertEqual(self.exertion_tracker.fatigue_level, 5)
        self.exertion_tracker.set_fatigue_level(None)
        self.assertEqual(self.exertion_tracker.fatigue_level, 0)

    def test_set_load_level(self):
        self.setUp()
        self.exertion_tracker.set_load_level("invalid")
        self.assertEqual(self.exertion_tracker.load_level, "light")
        self.exertion_tracker.set_load_level("medium")
        self.assertEqual(self.exertion_tracker.load_level, "medium")
        self.exertion_tracker.set_load_level("light")
        self.assertEqual(self.exertion_tracker.load_level, "light")
        self.exertion_tracker.set_load_level("invalid")
        self.assertEqual(self.exertion_tracker.load_level, "light")
        self.exertion_tracker.set_load_level("heavy")
        self.assertEqual(self.exertion_tracker.load_level, "heavy")

    def test_set_accumulated_exertion(self):
        self.setUp()
        self.exertion_tracker.set_accumulated_exertion("4")
        self.assertEqual(self.exertion_tracker.accumulated_exertion, 4)
        self.exertion_tracker.set_accumulated_exertion(-1)
        self.assertEqual(self.exertion_tracker.accumulated_exertion, 0)
        self.exertion_tracker.set_accumulated_exertion(4.3)
        self.assertEqual(self.exertion_tracker.accumulated_exertion, 4.3)

    def test_add_exertion(self):
        self.setUp()
        self.exertion_tracker.add_exertion(10)
        self.assertEqual(self.exertion_tracker.accumulated_exertion, 10)
        self.exertion_tracker.add_exertion("5")
        self.assertEqual(self.exertion_tracker.accumulated_exertion, 15)
        self.exertion_tracker.add_exertion(-20)
        self.assertEqual(self.exertion_tracker.accumulated_exertion, 0)

    # Test getters
    def test_get_start_time(self):
        self.setUp()
        self.assertEqual(self.exertion_tracker.get_start_time(), 0)
        
    def test_get_end_time(self):
        self.setUp()
        self.assertEqual(self.exertion_tracker.get_end_time(), 3600)

    def test_get_activity_level(self):
        self.setUp()
        self.assertEqual(self.exertion_tracker.get_activity_level(), "inactive")

    def test_get_load_level(self):
        self.setUp()
        self.assertEqual(self.exertion_tracker.get_load_level(), "light")

    def test_get_accumulated_exertion(self):
        self.setUp()
        self.assertEqual(self.exertion_tracker.get_accumulated_exertion(), 0)

    def test_get_check_period(self):
        self.setUp()
        self.assertEqual(self.exertion_tracker.get_check_period(),3600)
        self.exertion_tracker.set_load_level("medium")
        self.assertEqual(self.exertion_tracker.get_check_period(),1800)
        self.exertion_tracker.set_load_level("heavy")
        self.assertEqual(self.exertion_tracker.get_check_period(),900)
        self.exertion_tracker.set_load_level("light")
        self.assertEqual(self.exertion_tracker.get_check_period(),3600)

        self.exertion_tracker.set_activity_level("normal")
        self.assertEqual(self.exertion_tracker.get_check_period(),600)
        self.exertion_tracker.set_load_level("medium")
        self.assertEqual(self.exertion_tracker.get_check_period(),300)
        self.exertion_tracker.set_load_level("heavy")
        self.assertEqual(self.exertion_tracker.get_check_period(),150)
        self.exertion_tracker.set_load_level("light")
        self.assertEqual(self.exertion_tracker.get_check_period(),600)

        self.exertion_tracker.set_activity_level("above normal")
        self.assertEqual(self.exertion_tracker.get_check_period(),300)
        self.exertion_tracker.set_load_level("medium")
        self.assertEqual(self.exertion_tracker.get_check_period(),150)
        self.exertion_tracker.set_load_level("heavy")
        self.assertEqual(self.exertion_tracker.get_check_period(),45)
        self.exertion_tracker.set_load_level("light")
        self.assertEqual(self.exertion_tracker.get_check_period(),300)

        self.exertion_tracker.set_activity_level("jogging")
        self.assertEqual(self.exertion_tracker.get_check_period(),60)
        self.exertion_tracker.set_load_level("medium")
        self.assertEqual(self.exertion_tracker.get_check_period(),30)
        self.exertion_tracker.set_load_level("heavy")
        self.assertEqual(self.exertion_tracker.get_check_period(),15)
        self.exertion_tracker.set_load_level("light")
        self.assertEqual(self.exertion_tracker.get_check_period(),60)

        self.exertion_tracker.set_activity_level("swimming")
        self.assertEqual(self.exertion_tracker.get_check_period(),30)
        self.exertion_tracker.set_load_level("medium")
        self.assertEqual(self.exertion_tracker.get_check_period(),15)
        self.exertion_tracker.set_load_level("heavy")
        self.assertEqual(self.exertion_tracker.get_check_period(),1)
        self.exertion_tracker.set_load_level("light")
        self.assertEqual(self.exertion_tracker.get_check_period(),30)

        self.exertion_tracker.set_activity_level("running")
        self.assertEqual(self.exertion_tracker.get_check_period(),30)
        self.exertion_tracker.set_load_level("medium")
        self.assertEqual(self.exertion_tracker.get_check_period(),15)
        self.exertion_tracker.set_load_level("heavy")
        self.assertEqual(self.exertion_tracker.get_check_period(),1)
        self.exertion_tracker.set_load_level("light")
        self.assertEqual(self.exertion_tracker.get_check_period(),30)

        self.exertion_tracker.set_activity_level("combat")
        self.assertEqual(self.exertion_tracker.get_check_period(),6)
        self.exertion_tracker.set_load_level("medium")
        self.assertEqual(self.exertion_tracker.get_check_period(),3)
        self.exertion_tracker.set_load_level("heavy")
        self.assertEqual(self.exertion_tracker.get_check_period(),1)
        self.exertion_tracker.set_load_level("light")
        self.assertEqual(self.exertion_tracker.get_check_period(),6)

        self.exertion_tracker.set_activity_level("sprinting")
        self.assertEqual(self.exertion_tracker.get_check_period(),1)
        self.exertion_tracker.set_load_level("medium")
        self.assertEqual(self.exertion_tracker.get_check_period(),1)
        self.exertion_tracker.set_load_level("heavy")
        self.assertEqual(self.exertion_tracker.get_check_period(),1)
        self.exertion_tracker.set_load_level("light")
        self.assertEqual(self.exertion_tracker.get_check_period(),1)

        self.exertion_tracker.activity_level="invalid"
        self.assertEqual(self.exertion_tracker.get_check_period(),0)

        self.exertion_tracker.set_activity_level("inactive")
        self.assertEqual(self.exertion_tracker.get_check_period(),3600)

        self.exertion_tracker.load_level="invalid"
        self.assertEqual(self.exertion_tracker.get_check_period(),0)

    def test_calculate_end_time(self):
        self.setUp()
        self.assertEqual(self.exertion_tracker.calculate_end_time(),3600)
        self.exertion_tracker.set_load_level("medium")
        self.assertEqual(self.exertion_tracker.calculate_end_time(),1800)
        self.exertion_tracker.set_load_level("heavy")
        self.assertEqual(self.exertion_tracker.calculate_end_time(),900)
        self.exertion_tracker.set_load_level("light")
        self.assertEqual(self.exertion_tracker.calculate_end_time(),3600)

        self.exertion_tracker.set_activity_level("normal")
        self.assertEqual(self.exertion_tracker.calculate_end_time(),600)
        self.exertion_tracker.set_load_level("medium")
        self.assertEqual(self.exertion_tracker.calculate_end_time(),300)
        self.exertion_tracker.set_load_level("heavy")
        self.assertEqual(self.exertion_tracker.calculate_end_time(),150)
        self.exertion_tracker.set_load_level("light")
        self.assertEqual(self.exertion_tracker.calculate_end_time(),600)

        self.exertion_tracker.set_activity_level("above normal")
        self.assertEqual(self.exertion_tracker.calculate_end_time(),300)
        self.exertion_tracker.set_load_level("medium")
        self.assertEqual(self.exertion_tracker.calculate_end_time(),150)
        self.exertion_tracker.set_load_level("heavy")
        self.assertEqual(self.exertion_tracker.calculate_end_time(),45)
        self.exertion_tracker.set_load_level("light")
        self.assertEqual(self.exertion_tracker.calculate_end_time(),300)

        self.exertion_tracker.set_activity_level("jogging")
        self.assertEqual(self.exertion_tracker.calculate_end_time(),60)
        self.exertion_tracker.set_load_level("medium")
        self.assertEqual(self.exertion_tracker.calculate_end_time(),30)
        self.exertion_tracker.set_load_level("heavy")
        self.assertEqual(self.exertion_tracker.calculate_end_time(),15)
        self.exertion_tracker.set_load_level("light")
        self.assertEqual(self.exertion_tracker.calculate_end_time(),60)

        self.exertion_tracker.set_activity_level("swimming")
        self.assertEqual(self.exertion_tracker.calculate_end_time(),30)
        self.exertion_tracker.set_load_level("medium")
        self.assertEqual(self.exertion_tracker.calculate_end_time(),15)
        self.exertion_tracker.set_load_level("heavy")
        self.assertEqual(self.exertion_tracker.calculate_end_time(),1)
        self.exertion_tracker.set_load_level("light")
        self.assertEqual(self.exertion_tracker.calculate_end_time(),30)

        self.exertion_tracker.set_activity_level("running")
        self.assertEqual(self.exertion_tracker.calculate_end_time(),30)
        self.exertion_tracker.set_load_level("medium")
        self.assertEqual(self.exertion_tracker.calculate_end_time(),15)
        self.exertion_tracker.set_load_level("heavy")
        self.assertEqual(self.exertion_tracker.calculate_end_time(),1)
        self.exertion_tracker.set_load_level("light")
        self.assertEqual(self.exertion_tracker.calculate_end_time(),30)

        self.exertion_tracker.set_activity_level("combat")
        self.assertEqual(self.exertion_tracker.calculate_end_time(),6)
        self.exertion_tracker.set_load_level("medium")
        self.assertEqual(self.exertion_tracker.calculate_end_time(),3)
        self.exertion_tracker.set_load_level("heavy")
        self.assertEqual(self.exertion_tracker.calculate_end_time(),1)
        self.exertion_tracker.set_load_level("light")
        self.assertEqual(self.exertion_tracker.calculate_end_time(),6)

        self.exertion_tracker.set_activity_level("sprinting")
        self.assertEqual(self.exertion_tracker.calculate_end_time(),1)
        self.exertion_tracker.set_load_level("medium")
        self.assertEqual(self.exertion_tracker.calculate_end_time(),1)
        self.exertion_tracker.set_load_level("heavy")
        self.assertEqual(self.exertion_tracker.calculate_end_time(),1)
        self.exertion_tracker.set_load_level("light")
        self.assertEqual(self.exertion_tracker.calculate_end_time(),1)

        self.exertion_tracker.activity_level="invalid"
        self.assertEqual(self.exertion_tracker.calculate_end_time(),0)

        self.exertion_tracker.set_activity_level("inactive")
        self.assertEqual(self.exertion_tracker.calculate_end_time(),3600)

        self.exertion_tracker.load_level="invalid"
        self.assertEqual(self.exertion_tracker.calculate_end_time(),0)

        self.exertion_tracker.set_activity_level("inactive")
        self.exertion_tracker.set_load_level("light")
        self.exertion_tracker.set_start_time(10)
        self.assertEqual(self.exertion_tracker.calculate_end_time(),3610)

    def test_check(self):
        self.setUp()	
        self.assertFalse(self.exertion_tracker.check(0))
        self.assertFalse(self.exertion_tracker.check(1))
        self.assertTrue(self.exertion_tracker.check(20))

if __name__ == '__main__':
    unittest.main()

if __name__ == '__main__':
    unittest.main()
