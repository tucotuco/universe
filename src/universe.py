#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2023 Rauthiflor LLC"
__version__ = "universe.py 2023-03-20T18:56-03:00"

# TODO: Make ''' comments on classes and methods
# TODO: Everything

import json, sys
from armor import ArmorDictionary
from being import BeingDictionary
from object import ObjectDefinition, ObjectDictionary, ObjectInstance, ObjectRegistry
from skill import SkillDictionary
from weapon import WeaponDictionary

from identifiable import Identifiable
from event import Event
from encounter import Encounter

class Universe(ObjectInstance):
    '''
    A template for characteristics of a Universe, which is a subtype of Object.
    '''
    def __init__(self, name="", is_magical=True):
        universe_def = ObjectDefinition('universe', sys.maxsize, sys.maxsize, sys.maxsize,
                                        sys.maxsize, 0, sys.maxsize, sys.maxsize, 
                                        is_magical)
        ObjectInstance.__init__(self, universe_def, name, id='universe')
        self.armor_dict = ArmorDictionary()
        self.being_dict = BeingDictionary()
        self.object_dict = ObjectDictionary()
        self.skill_dict = SkillDictionary()
        self.weapon_dict = WeaponDictionary()
        self.object_registry = ObjectRegistry()

    def new_universe(self, config_path='./config'):
        self.config_path = config_path
        self.events = []
        self.load_dictionaries()

    def load_dictionaries(self):
        # Load dictionaries...
        self.object_dict.load_objects(f'{self.config_path}/objects.tsv')
        self.object_dict.load_object_categories(f'{self.config_path}/object_categories.json')
        self.armor_dict.load_objects(f'{self.config_path}/armors.tsv')
        self.armor_dict.load_object_categories(f'{self.config_path}/armor_categories.json')
        self.weapon_dict.load_objects(f'{self.config_path}/weapons.tsv')
        self.weapon_dict.load_object_categories(f'{self.config_path}/weapon_categories.json')
        self.skill_dict.load_skills(f'{self.config_path}/skills.tsv')
        self.skill_dict.add_weapon_skills(self.weapon_dict)
#        self.being_dict.load_beings(f'{self.config_path}/beings.tsv')

    def add_object(self, obj):
        if isinstance(obj, ObjectInstance):
            self.object_registry.add_object(obj)

    def get_object_by_id(self, obj_id):
        return self.object_registry.get_object_by_id(obj_id)

    def add_event(self, event):
        if isinstance(event, Event):
            self.events.append(event)
            self.sort_events()

    def sort_events(self):
        self.events.sort(key=lambda x: (x.starttime, x.endtime))
        
    def save_to_file(self, filename):
        with open(filename, "w") as f:
            f.write(self.to_json())

    def load_from_file(self, filename):
        with open(filename, "r") as f:
            data = json.load(f)

        if data["type"] == "Universe":
            print(f'name: {data["name"]}')
            self.name = data["name"]
        else:
            raise ValueError(f"Unexpected type: {data['type']}")

        self.events = []
        for event_data in data["events"]:
            event_type = event_data.get("type", "Event")
            if event_type == "Event":
                event = Event(**{k: v for k, v in event_data.items() if k != 'type'})
            elif event_type == "Encounter":
                event = Encounter(**{k: v for k, v in event_data.items() if k != 'type'})
            else:
                raise ValueError(f"Unexpected event type: {event_type}")
            self.events.append(event)

        object_dict = data.get('object_dict')
        self.object_dict.load_from_dict(object_dict)
        armor_dict = data.get('armor_dict')
        self.armor_dict.load_from_dict(armor_dict)
        weapon_dict = data.get('weapon_dict')
        self.weapon_dict.load_from_dict(weapon_dict)
        being_dict = data.get('being_dict')
        self.being_dict.load_from_dict(being_dict)
        skill_dict = data.get('skill_dict')
        self.skill_dict.load_from_dict(skill_dict)
        object_registry_dict = data.get('object_registry')
        self.object_registry.load_from_dict(object_registry_dict)
