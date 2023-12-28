#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2023 Rauthiflor LLC"
__version__ = "states.py 2023-12-27T13:15-03:00"

# TODO: Make ''' comments on classes and methods

import csv

from utils import convert_to_boolean

class StatesList():
    def __init__(self):
        self.states = []

    def load_states(self, filename):
        with open(filename, 'r') as f:
            reader = csv.reader(f)
            next(reader)  # skip header row
            for row in reader:
                state_name = row[0]
                self.states.append(state_name)

class States():
    '''
    A dictionary of physical and mental states and whether or not they are in effect.
    '''
    def __init__(self):
        self.states = {}

    def get_states(self):
        '''
        Get the states dictionary.
        '''
        return self.states

    def get_state(self, state_name):
        '''
        Get the the value of a state.
        '''
        return self.states.get(state_name)

    def set_state(self, state_list, state_name, state):
        '''
        Set or add a state to the current set of states if it is valid.
        '''
        b = convert_to_boolean(state)
        if b is None:
            return
        if isinstance(state_list, StatesList):
            if state_name in state_list.states:
                self.states[state_name] = b

    def remove_state(self, state_name):
        if state_name in self.states:
            del self.states[state_name]
        else:
            raise ValueError(f"State {state_name} not found")

    def copy(self):
        '''
        Get an independent copy of the States instance.
        '''
        new_states = States()
        for state, value in self.states.items():
            new_states.states[state] = value
        return new_states
