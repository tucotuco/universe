#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2023 Rauthiflor LLC"
__version__ = "test_universe.py 2023-04-11T11:31-03:00"

# TODO: Check comprehensiveness
# TODO: For all classes, set consistent method order: __init__, copy, to_json, get/set combos
# TODO: Test adding objects to the object registry and getting them back out of the loaded file

import unittest
import uuid
import json
import os
import sys

sys.path.insert(0, os.path.abspath('../src'))
#print(f'{__version__}:{sys.path}')

from universe import Universe
from event import Event
from encounter import Encounter

class TestUniverse(unittest.TestCase):
    def setUp(self):
        self.universe = Universe(name="Test Universe")
        self.universe.new_universe(config_path='../src/config')
        self.event1 = Event(100, 200, 'war', "France")
#        print(f'event1: {self.event1.to_json()}')
        self.event2 = Encounter(300, 400, "battle", "Florence")
#        print(f'event2: {self.event2.to_json()}')
        self.universe.add_event(self.event1)
        self.universe.add_event(self.event2)

    def test_add_event(self):
        self.assertEqual(len(self.universe.event_history.child_events), 2)
        self.assertEqual(self.universe.event_history.child_events[0], self.event1)
        self.assertEqual(self.universe.event_history.child_events[1], self.event2)

    def test_to_json(self):
        json_str = self.universe.to_json()
#        print(f'{json_str}')
        json_obj = json.loads(json_str)
        self.assertEqual(json_obj["name"], "Test Universe")
        self.assertEqual(json_obj["type"], "Universe")
#        print(f'event history: {json_obj["event_history"]}')
        child_events = json_obj["event_history"]["child_events"]
        self.assertEqual(len(child_events), 2)
        self.assertEqual(child_events[0]["event_type"], "war")
        self.assertEqual(child_events[0]["location"], "France")
        self.assertEqual(child_events[0]["start_time"], 100)
        self.assertEqual(child_events[0]["end_time"], 200)
        self.assertEqual(child_events[1]["event_type"], "battle")
        self.assertEqual(child_events[1]["location"], "Florence")
        self.assertEqual(child_events[1]["start_time"], 300)
        self.assertEqual(child_events[1]["end_time"], 400)

    def test_from_file_with_encounters(self):
        filename = "results/test_universe.json"
        # Clean up the file if it already exists
        if os.path.exists(filename):
            # the file exists, remove it
            os.remove(filename)

        saved_event_history = self.universe.event_history
        saved_child_events = saved_event_history.child_events
        saved_event0 = saved_child_events[0]
        saved_event1 = saved_child_events[1]
        self.assertIsInstance(saved_event_history, Event)
        self.assertIsInstance(saved_event0, Event)
        self.assertIsInstance(saved_event1, Event)
        self.assertIsInstance(saved_event1, Encounter)
        self.assertEqual(len(saved_event_history), 2)
        self.assertEqual(len(saved_event0), 0)
        self.assertEqual(len(saved_event1), 0)

        # Save the Universe to a file
        self.universe.save_to_file(filename)
        
        # Load the Universe from the file
        loaded_universe = Universe("Loaded Universe")
        loaded_universe.load_from_file(filename)
        
        loaded_event_history = loaded_universe.event_history
        loaded_child_events = loaded_event_history.child_events
        loaded_event0 = loaded_child_events[0]
        loaded_event1 = loaded_child_events[1]

        # assert that the loaded Universe is the same as the original Universe
        self.assertEqual(self.universe.id, loaded_universe.id)
        self.assertEqual(self.universe.name, loaded_universe.name)
        self.assertEqual(self.universe.type, loaded_universe.type)
        self.assertEqual(len(saved_event_history), len(loaded_event_history))
        self.assertIsInstance(loaded_event0, Event)
        self.assertIsInstance(loaded_event1, Event)
        self.assertIsInstance(loaded_event1, Encounter)

#        print(f'{loaded_universe.to_json()}')

if __name__ == '__main__':
    unittest.main()
