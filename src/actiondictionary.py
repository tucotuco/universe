#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2023 Rauthiflor LLC"
__version__ = "actiondictionary.py 2023-12-27T13:09-03:00"

# TODO: Make action categories and populate the config/action_categories.tsv

import json

from object import ObjectInstance

class ActionDefinition():
    '''
    A template for characteristics of an Action.
    '''
    def __init__(self, name, target_type = 'object', required_skill = 'none', is_melee = False):
        self.name = name
        self.target_type = target_type
        self.required_skill = required_skill
        self.is_melee = is_melee

    def copy(self):
        '''
        Get an independent copy of the ActionDefinition.
        '''
        new_definition = ActionDefinition(
            self.name,
            self.target_type,
            self.required_skill,
            self.is_melee)
        return new_definition
    def to_json(self):
        '''
        Get a representation of a ActionDefinition as JSON.
        '''
        data = {
            self.name: self.get_property_dict()
        }
        return json.dumps(data)
    def get_property_dict(self):
        '''
        Get a dictionary with the properties of a ActionDefinition.
        '''
        return {'target_type': self.target_type, 'required_skill': self.required_skill, 'is_melee': self.is_melee}

class ActionDictionary():
    '''
    A reference for information about ActionDefinitions.
    '''
    def __init__(self, dictionary_file=None):
        self.actions = {}

        if dictionary_file is not None:
            self.load_actions(dictionary_file)

    def to_json(self):
        '''
        Get a representation of a ActionDictionary as JSON.
        '''
        return json.dumps(self.actions, indent=2)

    def add_action(self, action_definition):
        '''
        Use a ActionDefinition to add a action to a ActionDictionary
        '''
        if not isinstance(action_definition, ActionDefinition):
            raise TypeError('action_definition must be an instance of ActionDefinition')
            return
        self.actions[action_definition.name]=action_definition.get_property_dict()

    def get_action_definition(self, action_name):
        '''
        Get the ActionDefinition out of the ActionDictionary. 
        If not in the dictionary, return None
        '''
        return self.actions.get(action_name)

    def load_actions(self, filename):
        '''
        Load the ActionDictionary from file.
        '''
        p = True
        with open(filename, 'r') as f:
            lines = f.readlines()
            headers = lines[0].strip().split('\t')
#            print(f"actiondictionary: load_actions(): headers: {headers}")
            if p==True:
                p = False
            for line in lines[1:]:
                fields = line.strip().split('\t')
#                print(f"actiondictionary: load_actions(): fields: {fields}")
                action_dict = {}
                for i in range(len(headers)):
                    action_dict[headers[i]] = fields[i]
#                print(f"actiondictionary: load_actions(): action_dict: {action_dict}")
                action = ActionDefinition(**action_dict)
                self.add_action(action)

    def load_from_dict(self, action_dict):
        '''
        Load the ActionDictionary from a dictionary.
        '''
        self.actions = action_dict.get('actions')

    def __iter__(self):
        '''
        Establish an iterable that iterates over the items in the actions dictioanry.
        '''
        return iter(self.actions.items())
