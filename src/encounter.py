#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2023 Rauthiflor LLC"
__version__ = "encounter.py 2023-01-02T15:45-03:00"

# TODO: Just about everything
# TODO: Make ''' comments on classes and methods
# TODO: Deprecate EncounterHistory in favor of EventHistory?

from event import Event
from actiontimeline import ActionTimeline
from object import ObjectRegistry
from being import BeingInstance
from action import ActionDictionary
from weapon import WeaponDictionary

# An Encounter is a container for the activity that occurs in a location over a period
# of time. Each Encounter has a start time in seconds from a base epoch that anchors it 
# in a broder historical context.
class Encounter(Event):
    '''
    A subtype of Event that captures the interactions of Beings.
    '''
    def __init__(self, location, starttime, endtime=None, name="", parent=None, id=None, initiated=False, map=None, action_dict=None, weapon_dict=None, action_timeline=None, beings_present=None):
        Event.__init__(self, location, starttime, endtime, name, parent)
        self.map = map
        self.beings_present = beings_present or ObjectRegistry()
        self.action_dict = action_dict or ActionDictionary()
        self.weapon_dict = weapon_dict or WeaponDictionary()
        self.action_timeline = action_timeline or ActionTimeline()

    # Generate an Encounter.
    def generate(self):
        if self.map is None:
#            self.map = EncounterMap(location)
            pass
        if self.action_timeline is None:
            self.action_timeline = ActionTimeline()

    def add_being(self, being_inst):
        if isinstance(being_inst, BeingInstance):
            self.beings_present.add_object(being_inst)

    # Load an Encounter from storage.
    def load(self):
        action_dict_file = '../src/config/actions.tsv'
        self.action_dict.load_actions(action_dict_file)

        weapon_dict_file = '../src/config/weapons.tsv'
        weapon_categories_file = '../src/config/weapon_categories.json'
        self.weapon_dict.load_objects(weapon_dict_file)
        self.weapon_dict.load_object_categories(weapon_categories_file)

    # Cycle through the events in an encounter.
    # 1. make movement decisions: set movement targets, whether stationary or moving, relative or absolute.
    # 2. update acceleration, velocity, location, position, facings, engagement, etc. (include moving targets and accelerating targets)
    # 3. resolve non-movement actions and their effects
    # 4. update environment
    # 5. make action decisions (continue, change) based on currently knowable state
    # 6. map actions on timeline
    # 7. update current new round
    # 8. save state
    # 9. prompt to continue playing: if continue, go to 1 else exit
    def run(self):
        if self.initiated == False:
            self.generate()
  
        keep_going = True
        while keep_going:
            self.make_movement_decisions()
            self.move()
            self.resolve_actions()
            self.update_environment()
            self.make_action_decisions()
            self.update_timeline()
            self.save()
      
    def make_movement_decisions(self):
        pass

    def move(self):
        pass

    def resolve_actions(self):
        pass
    
    def update_environment(self):
        pass

    def make_action_decisions(self):
        for being in self.beings_present:
            self.decide_action(being)

    def decide_action(self, being):
        if isinstance(being, BeingInstance):
            # randomly decide an action among those available
            chosen_action = being.choose_actions(self.action_dict, self.weapon_dict)
            
    def update_timeline(self):
        pass

    def save(self):
        pass

class EncounterHistory:
    '''
    A reference for information about Encounters.
    '''
    def __init__(self):
      self.encounters = []

    def add_encounter(self, encounter):
      self.encounters.append(encounter)
