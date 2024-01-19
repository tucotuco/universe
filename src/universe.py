#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2023 Rauthiflor LLC"
__version__ = "universe.py 2024-01-09T13:51-03:00"

# TODO: redo unit tests
# TODO: Make ''' comments on classes and methods
# TODO: Have save_to_file ignore dictionaries and object registry.
# TODO: Have save_to_file save object registry separately.
# TODO: add make_being() and other make() functions that have been built for encounter. Have encounter invoke them from here.
# Create exceptions for make and arm methods if expectations aren't met.

import json, sys

from library import Library
from being import BeingInstance
from object import ObjectInstance, ObjectRegistry
from weapon import WeaponInstance
from identifiable import Identifiable
from event import Event
from encounter import Encounter

class Universe(Identifiable):
    '''
    A container for a "world" and the Objects and Events that populate it.
    '''
    def __init__(self, name="", library=None, config_path="./config"):
        Identifiable.__init__(self, name)
        self.library = None
        if isinstance(library, Library):
            self.library = library

        self.object_registry = ObjectRegistry()
        self.event_history = []
        first_event = Event(self, 0, name="History of the Universe")
        self.event_history.append(first_event)

    def to_json(self):
        def handle_circular_refs(obj):
            if isinstance(obj, (Library, Universe)):
                return obj.id  # Return only the ID for Universe and Event instances
            return obj.__dict__

        data = {
            "type": self.type,
            "name": self.name,
            "id": self.id,
            "library_id": self.library.get_id(),
            "object_registry": self.object_registry,
            "event_history": [event for event in self.event_history]
        }
        return json.dumps(data, default=handle_circular_refs, sort_keys=False, indent=2)

    def get_event_history(self):
        return self.event_history

    def get_event_by_id(self, event_id):
        for event in self.event_history:
            if event.id == event_id:
              return event
        return None

    def add_object(self, obj):
        if isinstance(obj, ObjectInstance):
            self.object_registry.add_object(obj)

    def get_object_by_id(self, obj_id):
        return self.object_registry.get_object_by_id(obj_id)

    def add_event(self, event):
        if isinstance(event, Event):
            self.event_history.append(event)

    def save_to_file(self, filename):
        with open(filename, "w") as f:
            f.write(self.to_json())

    def load_from_file(self, filename):
        with open(filename, "r") as f:
            data = json.load(f)

        if data["type"] == "Universe":
#            print(f'name: {data["name"]}')
            self.name = data["name"]
        else:
            raise ValueError(f"Unexpected type: {data['type']}")

        for event_data in data["event_history"]["child_events"]:
            event_type = event_data.get("type", "Event")
            if event_type == "Event":
                event = Event(**{k: v for k, v in event_data.items() if k != 'type'})
            elif event_type == "Encounter":
                event = Encounter(**{k: v for k, v in event_data.items() if k != 'type'})
            else:
                raise ValueError(f"Unexpected event type: {event_type}")
            self.add_event(event)

        object_registry_dict = data.get('object_registry')
        self.object_registry.load_from_dict(object_registry_dict)

    def get_library(self):
        return self.library

    def get_object_registry(self):
        return self.object_registry

    def get_action_dictionary(self):
        return self.library.action_dictionary

    def get_armor_dictionary(self):
        return self.library.armor_dictionary

    def get_being_dictionary(self):
        return self.library.being_dictionary

    def get_object_dictionary(self):
        return self.library.object_dictionary

    def get_skill_dictionary(self):
        return self.library.skill_dictionary

    def get_weapon_dictionary(self):
        return self.library.weapon_dictionary

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

    def make_being(self, being_type, name):
        being_def = self.library.get_being_definition(being_type)
        if being_def is None:
            print(f"Unable to make being {name} with being_type {being_type}.")        
            return None
        being = BeingInstance(being_def, name)
        self.add_object(being)
        print(f"Made {being_type} {name} (id={being.id})).")
        return being.id
    
    def make_object(self, object_type, name):
        object_def = self.library.get_object_definition(object_type)
        if object_def is None:
            print(f"Unable to make object {name} with object_type {object_type}.")        
            return None
        obj = ObjectInstance(object_def, name)
        self.add_object(obj)
        print(f"Made {object_type} {name} (id={obj.id})).")
        return obj.id

    def make_weapon(self, weapon_type, name):
        weapon_def = self.library.get_weapon_definition(weapon_type)
        if weapon_def is None:
            print(f"Unable to make weapon {name} with weapon_type {weapon_type}.")        
            return None
        weapon = WeaponInstance(weapon_def, name)
        self.add_object(weapon)
        print(f"Made {weapon_type} {name} (id={weapon.id})).")
        return weapon.id

    def make_object_for_being(self, being_id, object_type, name):
        being = self.get_object_by_id(being_id)
        if being is None or not isinstance(being, BeingInstance):
            print(f"Being {being_id} not found, no Object made.")        
            return None
        new_object_id = self.make_object(object_type, name)
        if new_object_id is None:
            print(f"Unable to make object {name} with object_type {object_type}.")        
            return None
        being.add_possession(new_object_id)
        print(f"Made {object_type} {name} ({new_object_id})) for {being.name}.")
        return new_object_id

    def make_weapon_for_being(self, being_id, weapon_type, name):
        being = self.get_object_by_id(being_id)
        if being is None or not isinstance(being, BeingInstance):
            print(f"Being {being_id} not found, no Weapon made.")        
            return None
        new_weapon_id = self.make_weapon(weapon_type, name)
        if new_weapon_id is not None:
            being.weapons.append(new_weapon_id)
            print(f"Made {weapon_type} {name} ({new_weapon_id})) for {being.name}.")
        return new_weapon_id

    def arm_being(self, being_id, weapon_id, body_location):
        being = self.get_object_by_id(being_id)
        if being is None or not isinstance(being, BeingInstance):
            print(f"Being {being_id} not found, not armed.")
            return False
        weapon = self.get_object_by_id(weapon_id)
        if weapon is None or not isinstance(weapon, WeaponInstance):
            print(f"Weapon {weapon_id} not found, being {being.name} not armed.")        
            return False
        being.set_body_part_holds_object(body_location, weapon_id)
        print(f"Being {being.name} armed with {weapon.type} {weapon.name}.")        
        return True
