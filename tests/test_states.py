#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2023 Rauthiflor LLC"
__version__ = "test_states.py 2023-03-29T01:34-03:00"

# TODO: Check comprehensiveness

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath('../src'))
#print(f'{__version__}:{sys.path}')

from states import States, StatesList

class TestStates(unittest.TestCase):
    def setUp(self):
        self.states_file = '../src/config/states.tsv'
        self.states_list = StatesList()
        self.states_list.load_states(self.states_file)
        self.states = States()

    def test_set_state_valid(self):
        self.states.set_state(self.states_list, 'conscious', True)
        self.assertEqual(self.states.get_state('conscious'), True)

    def test_set_state_invalid(self):
        self.states.set_state(self.states_list, 'not_a_state', True)
        self.assertNotIn('not_a_state', self.states.get_states())

    def test_remove_state_valid(self):
        self.states.set_state(self.states_list, 'mobile', True)
        self.states.remove_state('mobile')
        self.assertNotIn('mobile', self.states.get_states())

    def test_remove_state_invalid(self):
        with self.assertRaises(ValueError):
            self.states.remove_state('not_a_state')

    def test_copy(self):
        self.states.set_state(self.states_list, 'asleep', True)
        copy = self.states.copy()
        self.assertIsNot(self.states, copy)
        self.assertEqual(self.states.get_states(), copy.get_states())

if __name__ == '__main__':
    unittest.main()
