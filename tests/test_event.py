#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2023 Rauthiflor LLC"
__version__ = "test_event.py 2023-02-10T23:12-03:00"

# TODO: Check comprehensiveness

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath('../src'))
#print(f'{__version__}:{sys.path}')

from event import Event
from identifiable import Identifiable

class TestEvent(unittest.TestCase):
    def test_event_creation(self):
        location = "Earth"
        starttime = 1234567890
        endtime = 1234567930
        name = "My Event"
        parent = None
        event = Event(location, starttime, endtime, name, parent)

        self.assertIsInstance(event, Event)
        self.assertIsInstance(event, Identifiable)
        self.assertEqual(event.location, location)
        self.assertEqual(event.starttime, starttime)
        self.assertEqual(event.endtime, endtime)
        self.assertEqual(event.name, name)
        self.assertEqual(event.parent, parent)
        self.assertIsInstance(event.id, str)
        self.assertEqual(event.type, "Event")
        
    def test_event_equality(self):
        event1 = Event(location="location1", starttime=0, endtime=10)
        event2 = Event(location="location1", starttime=0, endtime=10)
        event3 = Event(location="location2", starttime=0, endtime=10)
        event4 = Event(location="location1", starttime=0, endtime=None)

        self.assertEqual(event1, event2)
        self.assertNotEqual(event1, event3)
        self.assertNotEqual(event1, event4)

if __name__ == '__main__':
    unittest.main()
