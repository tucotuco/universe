#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2024 Rauthiflor LLC"
__version__ = "test_event.py 2024-02-28T03:22-03:00"

# TODO: Check comprehensiveness

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath('../src'))
#print(f'{__version__}:{sys.path}')

from action import Action
from being import BeingDefinition, BeingInstance
from identifiable import Identifiable
from event import Event
from library import Library
from universe import Universe

class TestEvent(unittest.TestCase):
    def setUp(self):
        self.universe = Universe(name="Test Universe", library=Library(config_dir="../src/config"))

        start_time = 1234567890
        end_time = 1234567930
        event_type = "meteor collision"
        location = "Earth"
        name = "Catastrophe 1"
        parent_event_id = None
        id = "event1"
        self.event = Event(self.universe, start_time, end_time, event_type, location, name, parent_event_id, id)

        self.assertIsInstance(self.event, Event)
        self.assertIsInstance(self.event, Identifiable)
        self.assertEqual(self.event.start_time, start_time)
        self.assertEqual(self.event.end_time, end_time)
        self.assertEqual(self.event.event_type, event_type)
        self.assertEqual(self.event.location, location)
        self.assertEqual(self.event.name, name)
        self.assertEqual(self.event.id, id)
        self.assertIsNone(self.event.parent_event_id)
        self.assertIsInstance(self.event.id, str)
        self.assertEqual(self.event.type, "Event")

        self.being_def1 = BeingDefinition('Human', '6', '160', '5', '2d4', 'Chaotic Good', '9', '2')
        self.being_inst1 = BeingInstance(self.being_def1, 'Tobe')

    def test_init(self):
        event1 = Event(self.universe, 100)

        self.assertIsInstance(event1, Event)
        self.assertIsInstance(event1, Identifiable)
        self.assertEqual(event1.start_time, 100)
        self.assertIsNone(event1.end_time)
        self.assertEqual(event1.event_type, "Event")
        self.assertIsNone(event1.location)
        self.assertIsNone(event1.name)
        self.assertIsNone(event1.parent_event_id)
        self.assertIsInstance(event1.id, str)
        self.assertEqual(event1.type, "Event")

        event_type = "war"
        location = "Earth"
        start_time = 1234567890
        end_time = 1234567930
        name = "Catastrophe 1"
        parent_event_id = event1.id
        id2 = "Event2"
        
        event2 = Event(self.universe, start_time, end_time, event_type, location, name, parent_event_id, id2)
        self.assertEqual(event2.start_time, start_time)
        self.assertEqual(event2.end_time, end_time)
        self.assertEqual(event2.event_type, event_type)
        self.assertEqual(event2.location, location)
        self.assertEqual(event2.name, name)
        self.assertEqual(event2.parent_event_id, event1.id)
        self.assertEqual(event2.id, id2)
        self.assertEqual(event2.type, "Event")

    def test_lt(self):
        event1 = Event(self.universe, 0, 10, "eventtype1", "location1", "eventname", "eventparent", "event1")
        event2 = Event(self.universe, 1, 5, "eventtype1", "location1", "eventname", "eventparent", "event1")
        event3 = Event(self.universe, 2, 12, "eventtype1", "location2", "eventname", "eventparent", "event1")

        self.assertTrue(event1 < event2)
        self.assertTrue(event1 < event3)
        self.assertTrue(event2 < event3)

    def test_contains_time(self):
        event = Event(self.universe, 1, 10)
        self.assertFalse(event.contains_time(0))
        self.assertTrue(event.contains_time(1))
        self.assertTrue(event.contains_time(5))
        self.assertTrue(event.contains_time(10))
        self.assertFalse(event.contains_time(11))

    def test_contains_event_time(self):
        event1 = Event(self.universe, 1, 10)
        event2 = Event(self.universe, 1, 10)
        event3 = Event(self.universe, 0, 10)
        event4 = Event(self.universe, 0)
        event5 = Event(self.universe, 1, 11)
        event6 = Event(self.universe, 2, 9)
        event7 = Event(self.universe, 11, 12)

        self.assertTrue(event1.contains_event_time(event2))

    def test_equalivent_to(self):
        event1 = Event(self.universe, 1, 10)
        event2 = Event(self.universe, 1, 10)

        self.assertTrue(event1.equivalent_to(event2))

if __name__ == '__main__':
    unittest.main()
