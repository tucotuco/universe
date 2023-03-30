#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2023 Rauthiflor LLC"
__version__ = "test_universe.py 2023-03-20T18:55-03:00"

# TODO: Check comprehensiveness
# TODO: Make tests for loaded universe verus saved universe to make sure they are the same.
# TODO: For all classes, set consistent method order: __init__, copy, to_json, get/set combos

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
        self.event1 = Event(location="Moon", starttime=100, endtime=200)
        self.event2 = Encounter(location="Mars", starttime=300, endtime=400)
        self.universe.add_event(self.event1)
        self.universe.add_event(self.event2)

    def test_add_event(self):
        self.assertEqual(len(self.universe.events), 2)
        self.assertEqual(self.universe.events[0], self.event1)
        self.assertEqual(self.universe.events[1], self.event2)

    def test_to_json(self):
        json_str = self.universe.to_json()
#        print(f'{json_str}')
        json_obj = json.loads(json_str)
        self.assertEqual(json_obj["name"], "Test Universe")
        self.assertEqual(json_obj["type"], "Universe")
        self.assertEqual(len(json_obj["events"]), 2)
        self.assertEqual(json_obj["events"][0]["location"], "Moon")
        self.assertEqual(json_obj["events"][0]["starttime"], 100)
        self.assertEqual(json_obj["events"][0]["endtime"], 200)
        self.assertEqual(json_obj["events"][1]["location"], "Mars")
        self.assertEqual(json_obj["events"][1]["starttime"], 300)
        self.assertEqual(json_obj["events"][1]["endtime"], 400)

    def test_from_file_with_encounters(self):
        filename = "results/test_universe.json"
        # Clean up the file if it already exists
        if os.path.exists(filename):
            # the file exists, remove it
            os.remove(filename)

        # Save the Universe to a file
        self.universe.save_to_file(filename)
        
        # Load the Universe from the file
        loaded_universe = Universe("Loaded Universe")
        loaded_universe.load_from_file(filename)
        
        event0 = loaded_universe.events[0]
        event1 = loaded_universe.events[1]
        # assert that the loaded Universe is the same as the original Universe
        self.assertEqual(self.universe.id, loaded_universe.id)
        self.assertEqual(self.universe.name, loaded_universe.name)
        self.assertEqual(self.universe.type, loaded_universe.type)
        self.assertEqual(self.universe.events, loaded_universe.events)

        print(f'{loaded_universe.to_json()}')

if __name__ == '__main__':
    unittest.main()
