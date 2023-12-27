#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2023 Rauthiflor LLC"
__version__ = "event.py 2023-12-27T03:30-03:00"

# TODO: Redo unit tests for library parent

import heapq
import json

from identifiable import Identifiable

class Event(Identifiable):
    '''
    Something that happens at a place and time. Instances have unique identifiers.
    '''
    def __init__(self, universe, start_time, end_time=None, event_type='Event', location=None, 
                 name=None, parent_event=None, id=None, child_events=None):
        Identifiable.__init__(self, name, id)
        self.universe = universe
        self.event_type = event_type
        self.start_time = start_time
        self.end_time = end_time
        self.location = location
        self.parent_event = None
        if isinstance(parent_event, Event):
            self.parent_event = parent_event

    def to_json(self):
        def handle_circular_refs(obj):
            if isinstance(obj, (Universe)):
                return obj.id  # Return only the ID for Universe and Event instances
            return obj.__dict__

        parent_event_id = None
        if isinstance(self.parent_event, Event):
            parent_event_id = self.parent_event.get_id()
        data = {
            "type": self.type,
            "event_type": self.event_type,
            "name": self.name,
            "universe_id": self.universe.id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "parent_event_id": parent_event_id,
            "location": self.location
        }
        return json.dumps(data, default=handle_circular_refs, sort_keys=False, indent=2)

    def get_action_dictionary(self):
        return self.universe.library.get_action_dictionary()

    def get_armor_dictionary(self):
        return self.universe.library.get_armor_dictionary()

    def get_being_dictionary(self):
        return self.universe.library.get_being_dictionary()

    def get_object_dictionary(self):
        return self.universe.library.get_object_dictionary()

    def get_skill_dictionary(self):
        return self.universe.library.get_skill_dictionary()

    def get_weapon_dictionary(self):
        return self.universe.library.get_weapon_dictionary()

    def get_action_definition(self, action_name):
        return self.get_action_dictionary().get_action_definition(action_name)

    def get_armor_definition(self, armor_name):
        return self.get_armor_dictionary().get_object_definition(armor_name)

    def get_being_definition(self, being_name):
        return self.get_being_dictionary().get_object_definition(being_name)

    def get_object_definition(self, object_name):
        return self.get_object_dictionary().get_object_definition(object_name)

    def get_skill_definition(self, skill_name):
        return self.get_skill_dictionary().get_object_definition(skill_name)

    def get_weapon_definition(self, weapon_name):
        return self.get_weapon_dictionary().get_object_definition(weapon_name)

    def contains_time(self, time):
        '''
        Method to establish if a time is in the Event interval.
        '''
        if self.end_time is not None:
            return time >= self.start_time and time <= self.end_time
        return time >= self.start_time

    def contains_event_time(self, event):
        '''
        Method to establish if a location is within the Event location.
        '''
        if isinstance(event, Event):
            return self.contains_time(event.start_time) and \
                   self.contains_time(event.end_time)

    def contains_location(self, location):
        '''
        Method to establish if a location is within the Event location.
        '''
        # TODO: Consider allowing location to be a str or a Location instance
        pass

    def __lt__(self, other):
        '''
        Method to establish order of two Event instances.
        '''
        return self.start_time < other.start_time

    def __len__(self):
        return len(self.child_events)

    def equivalent_to(self, other):
        if self.name != other.name:
            return False
        if self.event_type != other.event_type:
            return False
        if self.start_time != other.start_time:
            return False
        if self.end_time != other.end_time:
            return False
        if self.location != other.location:
            return False
        if self.parent_event != other.parent_event:
            return False
        return True
