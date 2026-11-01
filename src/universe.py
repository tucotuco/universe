#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2024 Rauthiflor LLC"
__version__ = "universe.py 2024-03-15T22:51-03:00"

# TODO: redo unit tests
# TODO: Make ''' comments on classes and methods
# TODO: Have save_to_file ignore dictionaries and object registry.
# TODO: Have save_to_file save object registry separately.
# TODO: Create exceptions for make and arm methods if expectations aren't met.

import json, sys
from threading import RLock

from armor import ArmorInstance
from being import BeingInstance
from encounter import Encounter
from event import Event
from identifiable import Identifiable
from library import Library
from object import ObjectInstance, ObjectRegistry
from weapon import WeaponInstance

class Universe(Identifiable):
    '''
    A container for a "world" and the Objects and Events that populate it.
    '''
    def __init__(self, name="", library=None, config_path="./config"):
        Identifiable.__init__(self, name, id="0")
        self.library = None
        if isinstance(library, Library):
            self.library = library
        else:
            self.library = Library(config_path)

        self.object_registry = ObjectRegistry()
        self.event_history = {}
        self._schedule_lock = RLock()
        self._schedule_revision = 0
        self._choice_books = []  # Live native Encounter commitment indexes.
        first_event = Event(self, 0, name="Origin of the Universe", id="0")
        self.event_history["0"]=first_event

    def to_json(self):
        from transactional_progression import is_quarantined
        if is_quarantined(self):
            raise ValueError('Quarantined checkpoint reconstruction cannot be serialized')
        if any(book.encounter.progression_mode == 'transactional' or book.encounter.__dict__.get('_atomic_interval_history') or
               (book.encounter.boundary_fault or {}).get('kind') == 'atomic_publication'
               for book in self._choice_books):
            raise ValueError('Transactional Universe serialization requires Increment 5C3 compatibility')
        def handle_circular_refs(obj):
            if isinstance(obj, (Library, Universe)):
                return obj.id  # Return only the ID for Universe and Event instances
            if isinstance(obj, set):
                return sorted(obj)  # Encounter awareness is a directed set
            if isinstance(obj, BeingInstance):
                # Retain the versioned Q/B record even in legacy Universe saves.
                # Full Being-instance reconstruction is a separate preexisting
                # serialization limitation; this preserves its state correctly.
                return {**obj.__dict__, 'physical_fatigue':
                        obj.physical_fatigue.to_dict(obj.physiology_id)}
            if isinstance(obj, Encounter):
                # Only persistent Encounter fields belong in the save. Active
                # frozen fatigue views are transient; recorded frame history
                # is already JSON-compatible and restored by Encounter.
                return {key: val for key, val in obj.__dict__.items()
                        if key not in ('_active_fatigue_frame', 'last_fatigue_frame', '_physiology_registry',
                                       '_coordinator_time', '_interval_start', '_advancing', '_running',
                                       '_dispatching', '_boundary_context', '_choice_book')} | {'choice_state': obj.choice_state}
            return obj.__dict__

        data = {
            "type": self.type,
            "name": self.name,
            "id": self.id,
            "library_id": self.library.get_id(),
            "object_registry": self.object_registry,
            "event_history": self.event_history
        }
        return json.dumps(data, default=handle_circular_refs, sort_keys=False, indent=2)

    def get_event_history(self):
        return self.event_history

    def get_event_by_id(self, event_id):
        return self.event_history.get(event_id)

    def add_object(self, obj):
        from transactional_progression import is_quarantined
        if is_quarantined(self):
            raise ValueError('Quarantined checkpoint reconstruction cannot accept Objects')
        if isinstance(obj, ObjectInstance):
            self.object_registry.add_object(obj)

    def get_object_by_id(self, obj_id):
        return self.object_registry.get_object_by_id(obj_id)

    def add_event(self, event):
        from transactional_progression import is_quarantined
        if is_quarantined(self):
            raise ValueError('Quarantined checkpoint reconstruction cannot accept Events')
        from action import Action
        if isinstance(event, Action):
            raise ValueError('Actions must register through native Encounter choice publication')
        if isinstance(event, Event):
            self.event_history[event.id]=event

    def save_to_file(self, filename):
        from transactional_progression import is_quarantined
        if is_quarantined(self):
            raise ValueError('Quarantined checkpoint reconstruction cannot be saved')
        for book in self._choice_books:
            book.encounter.assert_checkpoint_exportable()
        for event in self.event_history.values():
            if isinstance(event, Encounter):
                event.assert_checkpoint_exportable()
        with open(filename, "w") as f:
            f.write(self.to_json())

    def load_from_file(self, filename):
        if any(book.encounter.progression_mode == 'transactional' for book in self._choice_books):
            raise ValueError('Transactional checkpoint restoration is unsupported before D7 migration')
        with open(filename, "r") as f:
            data = json.load(f)

        if self._choice_books:
            self._choice_books[0].assert_exportable()

        # The legacy loader does not reconstruct functional Action/Being/RNG
        # checkpoints. Refuse Encounter restores before changing this Universe.
        if any(event.get('type') == 'Encounter'
               for event in data.get('event_history', {}).values()):
            raise ValueError('Encounter checkpoint restoration is unsupported; '
                             'boundary cursor and complete native state require a versioned migration')
        if any(event.get('type', 'Event') != 'Event'
               for event in data.get('event_history', {}).values()):
            raise ValueError('Action checkpoint restoration is unsupported; complete native state is required')

        if data["type"] == "Universe":
            self.name = data["name"]
        else:
            raise ValueError(f"Unexpected type: {data['type']}")

        for event_id, event_data in data["event_history"].items():
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
        return being.id
    
    def make_object(self, object_type, name):
        object_def = self.library.get_object_definition(object_type)
        if object_def is None:
            print(f"Unable to make object {name} with object_type {object_type}.")        
            return None
        obj = ObjectInstance(object_def, name)
        self.add_object(obj)
        return obj.id

    def make_weapon(self, weapon_type, name):
        weapon_def = self.library.get_weapon_definition(weapon_type)
        if weapon_def is None:
            print(f"Unable to make weapon {name} with weapon_type {weapon_type}.")        
            return None
        weapon = WeaponInstance(weapon_def, name)
        self.add_object(weapon)
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
        return new_object_id

    def make_weapon_for_being(self, being_id, weapon_type, name):
        being = self.get_object_by_id(being_id)
        if being is None or not isinstance(being, BeingInstance):
            print(f"Being {being_id} not found, no Weapon made.")        
            return None
        new_weapon_id = self.make_weapon(weapon_type, name)
        if new_weapon_id is not None:
            being.weapons.append(new_weapon_id)
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
        return True

    def make_armor(self, armor_type, name):
        armor_def = self.library.get_armor_definition(armor_type)
        if armor_def is None:
            print(f"Unable to make armor {name} with armor_type {armor_type}.")        
            return None
        armor = ArmorInstance(armor_def, name)
        self.add_object(armor)
        return armor.id

    def make_armor_for_being(self, being_id, armor_type, name):
        being = self.get_object_by_id(being_id)
        if being is None or not isinstance(being, BeingInstance):
            print(f"Being {being_id} not found, not armored.")
            return False
        new_armor_id = self.make_armor(armor_type, name)
        if new_armor_id is not None:
            being.set_armor_id(new_armor_id)
        return new_armor_id

    def armor_being(self, being_id, armor_id):
        being = self.get_object_by_id(being_id)
        if being is None or not isinstance(being, BeingInstance):
            print(f"Being {being_id} not found, not armored.")
            return False
        armor = self.get_object_by_id(armor_id)
        if armor is None or not isinstance(armor, ArmorInstance):
            print(f"Armor {armor_id} not found, being {being.name} not armored.")        
            return False
        being.set_armor_id(armor_id)
        return True
