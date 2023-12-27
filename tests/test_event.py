#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2023 Rauthiflor LLC"
__version__ = "test_event.py 2023-04-20T16:42-03:00"

# TODO: Check comprehensiveness

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath('../src'))
#print(f'{__version__}:{sys.path}')

from event import Event
from action import Action
from identifiable import Identifiable
from being import BeingDefinition, BeingInstance

class TestEvent(unittest.TestCase):
    def setUp(self):
        start_time = 1234567890
        end_time = 1234567930
        event_type = "meteor collision"
        location = "Earth"
        name = "Catastrophe 1"
        parent = None
        id = "event1"
        self.event = Event(start_time, end_time, event_type, location, name, parent, id)

        self.assertIsInstance(self.event, Event)
        self.assertIsInstance(self.event, Identifiable)
        self.assertEqual(self.event.start_time, start_time)
        self.assertEqual(self.event.end_time, end_time)
        self.assertEqual(self.event.event_type, event_type)
        self.assertEqual(self.event.location, location)
        self.assertEqual(self.event.name, name)
        self.assertEqual(self.event.id, id)
        self.assertIsNone(self.event.parent)
        self.assertIsInstance(self.event.id, str)
        self.assertEqual(self.event.type, "Event")
        self.assertEqual(len(self.event), 0)

        self.being_def1 = BeingDefinition('Human', '6', '160', '5', '2d4', 'Chaotic Good', '9', '2')
        self.being_inst1 = BeingInstance(self.being_def1, 'Tobe')

    def test_init(self):
        event1 = Event(100)

        self.assertIsInstance(event1, Event)
        self.assertIsInstance(event1, Identifiable)
        self.assertEqual(event1.start_time, 100)
        self.assertIsNone(event1.end_time)
        self.assertEqual(event1.event_type, "Event")
        self.assertIsNone(event1.location)
        self.assertIsNone(event1.name)
        self.assertIsNone(event1.parent)
        self.assertIsInstance(event1.id, str)
        self.assertEqual(event1.type, "Event")
        self.assertEqual(len(event1), 0)

        event_type = "war"
        location = "Earth"
        start_time = 1234567890
        end_time = 1234567930
        name = "Catastrophe 1"
        parent = event1
        id = "Event2"
        
        event2 = Event(start_time, end_time, event_type, location, name, parent, id)

        self.assertEqual(event2.start_time, start_time)
        self.assertEqual(event2.end_time, end_time)
        self.assertEqual(event2.event_type, event_type)
        self.assertEqual(event2.location, location)
        self.assertEqual(event2.name, name)
        self.assertIsInstance(event2.parent, Event)
        self.assertEqual(event2.id, id)
        self.assertEqual(event2.type, "Event")
        self.assertEqual(len(self.event), 0)

    def test_add_event(self):
        self.event.clear_events()
        action1 = Action(self.being_inst1, "attack", "location1", 5, 10)
        action2 = Action(self.being_inst1, "dodge", "location1", 7, 10)
        action3 = Action(self.being_inst1, "block", "location1", 15, 20)
        self.event.add_event(action1)
        self.event.add_event(action2)
        self.event.add_event(action3)
        self.assertEqual(len(self.event), 3)
        self.event.clear_events()
        self.assertEqual(len(self.event), 0)
        action0 = Action(self.being_inst1, "multi-action", "location1", 5, 10)
        self.event.add_event(action0)
        action0.add_event(action1)
        action0.add_event(action2)
        self.assertEqual(len(self.event), 1)
        self.assertEqual(len(action0), 2)

    def test_lt(self):
        event1 = Event(0, 10, "eventtype1", "location1", "eventname", "eventparent", "event1")
        event2 = Event(1, 5, "eventtype1", "location1", "eventname", "eventparent", "event1")
        event3 = Event(2, 12, "eventtype1", "location2", "eventname", "eventparent", "event1")

        self.assertTrue(event1 < event2)
        self.assertTrue(event1 < event3)
        self.assertTrue(event2 < event3)

    def test_contains_time(self):
        event = Event(1, 10)
        self.assertFalse(event.contains_time(0))
        self.assertTrue(event.contains_time(1))
        self.assertTrue(event.contains_time(5))
        self.assertTrue(event.contains_time(10))
        self.assertFalse(event.contains_time(11))

    def test_contains_event_time(self):
        event1 = Event(1, 10)
        event2 = Event(1, 10)
        event3 = Event(0, 10)
        event4 = Event(0)
        event5 = Event(1, 11)
        event6 = Event(2, 9)
        event7 = Event(11, 12)

        self.assertTrue(event1.contains_event_time(event2))

    def test_equalivent_to(self):
        event1 = Event(1, 10)
        event2 = Event(1, 10)

        self.assertTrue(event1.equivalent_to(event2))

if __name__ == '__main__':
    unittest.main()
