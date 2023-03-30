#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2023 Rauthiflor LLC"
__version__ = "test_actiontimline.py 2023-03-27T04:06-03:00"

# TODO: Check comprehensiveness

import unittest
import sys
import os
import json
from unittest.mock import patch
from io import StringIO

sys.path.insert(0, os.path.abspath('../src'))
#print(f'{__version__}:{sys.path}')

from actiontimeline import ActionTimeline
from being import BeingDefinition, BeingInstance

class TestActionTimeline(unittest.TestCase):
    def setUp(self):
        self.timeline = ActionTimeline()
        self.being_def1 = BeingDefinition('Human', '6', '160', '5', '2d4', 'Chaotic Good', '9', '2')
        self.being_inst1 = BeingInstance(self.being_def1, 'Tobe')
        self.action1 = None
        self.action2 = None
        self.action3 = None

    def test_add_action(self):
        self.timeline.clear_actions()
        self.timeline.add_action(self.being_inst1, 5, 10, "attack")
        self.timeline.add_action(self.being_inst1, 7, 12, "dodge")
        self.timeline.add_action(self.being_inst1, 15, 20, "block")
        self.assertEqual(len(self.timeline.action_heap), 3)

    def test_resolve_actions(self):
        self.timeline.clear_actions()
        self.timeline.add_action(self.being_inst1, 5, 10, "attack")
        self.timeline.add_action(self.being_inst1, 7, 12, "dodge")
        self.timeline.add_action(self.being_inst1, 15, 20, "block")
        finished_actions = self.timeline.resolve_actions(8)
        self.assertEqual(len(finished_actions), 2)
        self.assertEqual(finished_actions[0].action_type, "attack")
        self.assertEqual(finished_actions[1].action_type, "dodge")

if __name__ == '__main__':
    unittest.main()
