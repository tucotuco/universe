#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2024 Rauthiflor LLC"
__version__ = "test_universe.py 2024-03-02T03:37-03:00"

# TODO: Check comprehensiveness
# TODO: For all classes, set consistent method order: __init__, copy, to_json, get/set combos
# TODO: Test adding objects to the object registry and getting them back out of the loaded file
# TODO: Test adding encounters to the event_history and getting them back out of the loaded file
# TODO: Determine if a numerical Event identifier tracked by the Universe would be more efficient.

import unittest
import uuid
import json
import os
import sys

sys.path.insert(0, os.path.abspath('../src'))
#print(f'{__version__}:{sys.path}')

from event import Event
from encounter import Encounter
from library import Library
from universe import Universe

class TestUniverse(unittest.TestCase):
    def setUp(self):
        self.universe = Universe(name="Test Universe", library=Library(config_dir="../src/config"))
        self.event1 = Event(self.universe, 100, 200, 'war', "France", "French Revolution")
#universe, start_time, end_time=None, event_type='Event', location=None, name=None, parent_event_id=None, id=None
#        print(f'event1: {self.event1.to_json()}')
        self.event2 = Encounter(self.universe, 10, 300, 400, "battle", "Florence", "Battle of Florence")
#universe, difficulty_class, start_time, end_time=None, event_type=None, location=None, name="", parent_event_id=None, id=None, initiated=False, map=None
#        print(f'event2: {self.event2.to_json()}')
        self.universe.add_event(self.event1)
        self.universe.add_event(self.event2)

    def test_add_event(self):
        self.assertEqual(len(self.universe.event_history), 3)
        self.assertEqual(self.universe.event_history[self.event1.id], self.event1)
        self.assertEqual(self.universe.event_history[self.event2.id], self.event2)

    def test_to_json(self):
        json_str = self.universe.to_json()
#        print(f'{json_str}')
        json_obj = json.loads(json_str)
        self.assertEqual(json_obj["name"], "Test Universe")
        self.assertEqual(json_obj["type"], "Universe")
#        print(f'{json_obj}')
        self.assertEqual(len(self.universe.event_history), 3)
        self.assertEqual(self.universe.event_history["0"].event_type, "Event")
        self.assertIsNone(self.universe.event_history["0"].location)
        self.assertEqual(self.universe.event_history["0"].start_time, 0)
        self.assertIsNone(self.universe.event_history["0"].end_time)
        self.assertEqual(self.universe.event_history[self.event1.id].name, "French Revolution")
        self.assertEqual(self.universe.event_history[self.event1.id].event_type, "war")
        self.assertEqual(self.universe.event_history[self.event1.id].location, "France")
        self.assertEqual(self.universe.event_history[self.event1.id].start_time, 100)
        self.assertEqual(self.universe.event_history[self.event1.id].end_time, 200)
        self.assertEqual(self.universe.event_history[self.event1.id].name, "French Revolution")
        self.assertEqual(self.universe.event_history[self.event2.id].event_type, "battle")
        self.assertEqual(self.universe.event_history[self.event2.id].location, "Florence")
        self.assertEqual(self.universe.event_history[self.event2.id].start_time, 300)
        self.assertEqual(self.universe.event_history[self.event2.id].end_time, 400)
        self.assertEqual(self.universe.event_history[self.event2.id].name, "Battle of Florence")

    def test_from_file_with_encounters(self):
        filename = "results/test_universe.json"
        # Clean up the file if it already exists
        if os.path.exists(filename):
            # the file exists, remove it
            os.remove(filename)

        saved_event_history = self.universe.event_history
        saved_event0 = saved_event_history["0"]
        saved_event1 = saved_event_history[self.event1.id]
        saved_event2 = saved_event_history[self.event2.id]
        self.assertIsInstance(saved_event0, Event)
        self.assertIsInstance(saved_event1, Event)
        self.assertIsInstance(saved_event2, Event)
        self.assertIsInstance(saved_event2, Encounter)
        self.assertEqual(len(saved_event_history), 3)

        # Save the Universe to a file
        self.universe.save_to_file(filename)
        
        # Load the Universe from the file
        loaded_universe = Universe("Loaded Universe", library=Library(config_dir="../src/config"))
        loaded_universe.load_from_file(filename)
        
        loaded_event_history = loaded_universe.event_history
        loaded_event0 = loaded_event_history["0"]
        loaded_event1 = loaded_event_history[self.event1.id]
        loaded_event2 = loaded_event_history[self.event2.id]

        # assert that the loaded Universe is the same as the original Universe
        self.assertEqual(self.universe.id, loaded_universe.id)
        self.assertEqual(self.universe.name, loaded_universe.name)
        self.assertEqual(self.universe.type, loaded_universe.type)
        self.assertEqual(len(saved_event_history), len(loaded_event_history))
        self.assertIsInstance(loaded_event0, Event)
        self.assertIsInstance(loaded_event1, Event)
        self.assertIsInstance(loaded_event2, Encounter)

#        print(f'{loaded_universe.to_json()}')

if __name__ == '__main__':
    unittest.main()
