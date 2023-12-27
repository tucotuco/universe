#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2023 Rauthiflor LLC"
__version__ = "test_actiondictionary.py 2023-04-22T12:29-03:00"

# TODO: Check comprehensiveness

import unittest
import sys
import os
import json

from unittest.mock import patch
from io import StringIO

sys.path.insert(0, os.path.abspath('../src'))
#print(f'{__version__}:{sys.path}')

from actiondictionary import ActionDefinition, ActionDictionary
	
class TestActionDefinition(unittest.TestCase):
    def setUp(self):
        self.def1 = ActionDefinition('Action1', 'object', 'skill1')
        self.def2 = self.def1.copy()
    
    def test_copy(self):
        self.assertEqual(self.def1.name, self.def2.name)
        self.assertEqual(self.def1.required_skill, self.def2.required_skill)
        self.assertIsNot(self.def1, self.def2)
    
    def test_get_property_dict(self):
        expected_dict = {'target_type': 'object', 'required_skill': 'skill1'}
        self.assertEqual(self.def1.get_property_dict(), expected_dict)
    
    def test_to_json(self):
        expected_json = json.dumps({'Action1': {'target_type': 'object', 'required_skill': 'skill1'}})
        self.assertEqual(self.def1.to_json(), expected_json)

class TestActionDictionary(unittest.TestCase):
    def setUp(self):
        self.actions_file = '../src/config/actions.tsv'
        self.action_dict = ActionDictionary()

    def test_add_action(self):
        action = ActionDefinition("punch")
        self.action_dict.add_action(action)
        self.assertEqual(len(self.action_dict.actions), 1)
        self.assertIn("punch", self.action_dict.actions)
        self.assertIsNotNone(self.action_dict.actions["punch"])

    def test_get_action_definition(self):
        action = ActionDefinition("punch", 'being', 'unarmed combat')
        self.action_dict.add_action(action)
        action = ActionDefinition("sit")
        self.action_dict.add_action(action)
        self.assertEqual(len(self.action_dict.actions), 2)
        self.assertEqual(self.action_dict.get_action_definition("punch"), {'target_type': 'being', 'required_skill': 'unarmed combat'})
        self.assertEqual(self.action_dict.get_action_definition("sit"), {'target_type': 'object', 'required_skill': 'none'})
        self.assertIsNone(self.action_dict.get_action_definition("kick"))

    def test_load_actions(self):
        action_dict_file = StringIO('name\ttarget_type\trequired_skill\nshoot\tobject\tnone\nfeint unarmed\tbeing\tunarmed combat')
        with patch("builtins.open", return_value=action_dict_file):
            self.action_dict.load_actions("test_file.tsv")
        self.assertIn("shoot", self.action_dict.actions)
        self.assertIn("feint unarmed", self.action_dict.actions)
        self.assertEqual(self.action_dict.actions["shoot"], {'target_type': 'object', 'required_skill': 'none'})
        self.assertEqual(self.action_dict.actions["feint unarmed"], {'target_type': 'being', 'required_skill': 'unarmed combat'})

    def test_load_actions2(self):
        self.action_dict.load_actions(self.actions_file)
        self.assertEqual(len(self.action_dict.actions), 44)
        for action in self.action_dict.actions:
            action_dict = self.action_dict.actions[action]
            self.assertIsInstance(action_dict, dict)
        action = self.action_dict.actions['stun']
#        print(f'action: {action}')
        self.assertEqual(action.get('required_skill'), 'stun')

    def test_load_from_dict(self):
        action_dict = {"actions": {"punch": "unarmed combat"}}
        self.action_dict.load_from_dict(action_dict)
        self.assertIn("punch", self.action_dict.actions)
        self.assertEqual(self.action_dict.actions["punch"], "unarmed combat")

if __name__ == '__main__':
    unittest.main()
