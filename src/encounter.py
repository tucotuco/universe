#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2023 Rauthiflor LLC"
__version__ = "encounter.py 2024-01-20T14:55-08:00"

# TODO: Make ''' comments on classes and methods

import json
import random

from utils import convert_to_dc
from action import Action
from event import Event
from library import Library
from being import BeingInstance
from object import ObjectInstance
from strategy import Strategy
from weapon import WeaponInstance

# An Encounter is a container for the activity that occurs in a location over a period
# of time. Each Encounter has a start time in seconds from a base epoch that anchors it 
# in a broder historical context. 
class Encounter(Event):
    '''
    A subtype of Event that captures the interactions of Beings.
    '''
    def __init__(self, universe, difficulty_class, start_time, end_time=None, 
                 event_type=None, location=None, name="", parent_event=None, id=None, 
                 initiated=False, map=None):
        Event.__init__(self, universe, start_time, end_time, 
                 event_type, location, name, parent_event, id)
        self.difficulty_class = convert_to_dc(difficulty_class)
        self.initiated = initiated
        self.map = map
        self.time = start_time
        self.being_list = [] # A list of ids of Beings involved in the Encounter
        self.non_being_object_list = [] # A list of ids of Objects involved in the Encounter
        self.pending_action_list = []
        self.finished_action_list = []

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
            "universe_id": self.universe.get_id(),
            "start_time": self.start_time,
            "end_time": self.end_time,
            "parent_event_id": parent_event_id,
            "location": self.location,
            "difficulty_class": self.difficulty_class,
            "map": self.map,
            "being_list": self.being_list,
            "object_list": self.non_being_object_list
        }
        return json.dumps(data, default=handle_circular_refs, sort_keys=False, indent=2)

    # Generate an Encounter.
    def generate(self):
        if self.map is None:
#            self.map = EncounterMap(location)
            pass
	
    def make_being(self, being_type, name):
        new_being_id = self.universe.make_being(being_type, name)
        self.add_being(new_being_id)
        return new_being_id
    
    def make_object(self, object_type, name):
        new_object_id = self.universe.make_object(object_type, name)
        self.add_object(new_object_id)
        return new_object_id

    def make_weapon(self, weapon_type, name):
        new_weapon_id = self.universe.make_weapon(weapon_type, name)
        self.add_object(new_weapon_id)
        return new_weapon_id

    def make_weapon_for_being(self, being_id, weapon_type, name):
        return self.universe.make_weapon_for_being(being_id, weapon_type, name)
    
    def make_object_for_being(self, being_id, object_type, name):
        new_object_id = self.universe.make_object_for_being(being_id, object_type, name)
        if new_object_id is None:
            return None
        self.non_being_object_list.append(new_object_id)
        return new_object_id

    def make_weapon_for_being(self, being_id, weapon_type, name):
        new_weapon_id = self.universe.make_weapon_for_being(being_id, weapon_type, name)
        if new_weapon_id is None:
            return None
        self.non_being_object_list.append(new_weapon_id)
        return new_weapon_id

    def arm_being(self, being_id, weapon_id, body_location):
        return self.universe.arm_being(being_id, weapon_id, body_location)

    def add_object(self, object_id):
        if object_id not in self.non_being_object_list:
            self.non_being_object_list.append(object_id)

    def add_being(self, being_id):
        if being_id not in self.being_list:
            self.being_list.append(being_id)

    # Load an Encounter from storage.
#    def load(self):

    # Cycle through the events in an encounter.
    # 1. make movement decisions: set movement targets, whether stationary or moving, relative or absolute.
    # 2. update acceleration, velocity, location, position, facings, engagement, etc. (include moving targets and accelerating targets)
    # 3. resolve non-movement actions and their effects
    # 4. update environment
    # 5. make action decisions (continue, change) based on currently knowable state and map actions on timeline
    # 6. save state
    # 7. prompt to continue playing: if continue, go to 1 else exit
    def run(self, run_children=True):
        if not self.initiated:
            self.generate()

        continue_turns = True
        while continue_turns:
            print(f"----- {self.name} turn {self.time} -----")
#            print(f"choose movement: not implemented")
            self.choose_movement()
#            print(f"move: not implemented")
            self.move()
#            print(f"resolve actions: not implemented")
            self.resolve_actions()
#            print(f"update environment: not implemented")
            self.update_environment()
#            print(f"choose actions")
#            self.choose_actions()
#            print(f"choose fight actions")
            self.choose_fight_actions()
#             print("Pending actions:")
#             for action_id in self.pending_action_list:
#                 action = self.universe.get_event_by_id(action_id)
#                 if action is None:
#                     print(f"Action {action_id} not found in event history")
#                 else:
#                     print(f"{action.get_actor().name} targets {action.get_target().name} with {action.name} starting: {action.start_time} ending: {action.end_time}")
            self.time += 1
            continue_turns = self.keep_going()

    def keep_going(self):
        # Do just one round
#        if self.time == 10:
#            return False
        # Go until one or no one left standing
        being_count = len(self.being_list)
#        print(f"Being count turn {self.time}: {being_count}")
        beings_alive = 0
        for being_id in self.being_list:
            being = self.universe.get_object_by_id(being_id)
            print(f"Current hit points for {being.name}: {being.current.hit_points}")
            if being.current.hit_points > 0:
                beings_alive += 1
                if beings_alive > 1:
                    return True
        return False

    def choose_movement(self):
        pass

    def move(self):
        # If not immobile
        pass

    def resolve_actions(self):
        finish = []
        for action in self.pending_action_list:
            action = self.universe.get_event_by_id(action)
            if action is not None:
                if action.end_time == self.time:
                    action.resolve(self.difficulty_class)
                    self.finished_action_list.append(action.id)
                    finish.append(action.id)
        for action_id in finish:
            self.pending_action_list.remove(action_id)
    
    def update_environment(self):
        pass

    def is_being_occupied(self, being_id):
        for action_id in self.pending_action_list:
            action = self.universe.get_event_by_id(action_id)
            if action.actor_id == being_id:
                if action.event_type == "delay":
                    return False
                if action.end_time > self.time:
                    return True
        return False

    def choose_target_being(self, subject_being_id):
        if len(self.being_list) == 0:
            return None
        if len(self.being_list) == 1:
            return subject_being_id
        while True:
            choice = random.choice(self.being_list)
            if choice != subject_being_id:
                return choice

    def choose_target_object(self, subject_being_id):
#        print(f"Encounter Objects: {self.non_being_object_list}")
        # TODO: Could implement logic about whose Object
        if len(self.non_being_object_list) == 0:
            return None
        choice = random.choice(self.non_being_object_list)
        return choice

    def choose_target_attack(self, subject_being_id):
        # Make a list of attacks that aren't mine to try to target
        attack_list = None
        return random.choice(self.attack_list)

    def choose_target_weapon(self, subject_being_id):
        # Make a list of possible target weapons
        weapon_list = None
        return random.choice(self.weapon_list)

    def choose_fight_actions(self):
        for subject_being_id in self.being_list:
            subject_being = self.universe.get_object_by_id(subject_being_id)
#            print(f"Choosing fight action for {subject_being.name}")

            if subject_being.is_dead():
                print(f"{subject_being.name} is dead")
                continue

            if subject_being.is_helpless():
                print(f"{subject_being.name} is helpless")
                continue

            if self.is_being_occupied(subject_being_id):
                print(f"{subject_being.name} is occupied")
                continue

            action_dict = self.universe.get_action_dictionary()
            object_registry = self.universe.object_registry

            target = None
            if isinstance(subject_being, (BeingInstance)):
                # Randomly decide an melee action among those available
#                chosen_action = subject_being.choose_melee_action(self.universe.library.get_action_dictionary(), self.universe.library.get_weapon_dictionary())
                chosen_action = subject_being.choose_melee_action(self.universe)
                # At this point the chosen action should already be one the Being has
                # the required skills to do.
                action_definition = action_dict.get_action_definition(chosen_action)
                target_id = None
                target = None
                # If the Action requires a target Being, choose the target
                if action_definition["target_type"] == 'being':
                    target_id = self.choose_target_being(subject_being_id)
                    target = self.universe.get_object_by_id(target_id)
                # Otherwise if the Action requires a target Object, choose the target
                elif action_definition["target_type"] == 'object':
                    target_id = self.choose_target_object(subject_being_id)
                    target = self.universe.get_object_by_id(target_id)
                # Otherwise if the Action requires a target Attack, choose the target
#                 elif action_definition["target_type"] == 'attack':
#                     target_id = self.choose_target_attack(subject_being_id)
#                     #target = self.universe.get_object_by_id(target_id)
                # Otherwise if the Action requires a target Attack, choose the target
                elif action_definition["target_type"] == 'weapon':
                    target_id = self.choose_target_weapon(subject_being_id)
                    target = self.universe.get_object_by_id(target_id)
                # Otherwise no target is necessary

                new_action = None
                # Create an Action Event with the Encounter as its parent
                armed = subject_being.armed_with(self.universe)
                weapon_id = subject_being.choose_weapon(armed)
                weapon = self.universe.get_object_by_id(weapon_id)
                if "swing" in chosen_action:
                    name = f"{subject_being.name} swing t={self.time}"
                    new_action = Action(self.universe, start_time=self.time, 
                        end_time=None, event_type="swing", actor_id=subject_being_id, 
                        target_id=target_id, instrument_id=weapon_id, strategy=None, 
                        location=None, name=name, parent_event_id=self.id)
                elif "thrust" in chosen_action:
                    name = f"{subject_being.name} thrust at t={self.time}"
                    new_action = Action(self.universe, start_time=self.time, 
                        end_time=None, event_type="thrust", actor_id=subject_being_id, 
                        target_id=target_id, instrument_id=weapon_id, strategy=None, 
                        location=None, name=name, parent_event_id=self.id)
                else:
                    pass

                print(f"{subject_being.name} targets {target.name} with {chosen_action} using {weapon.name} ending at t={new_action.end_time}")
                # Add Action to the Event History
                self.pending_action_list.append(new_action.id)
                self.universe.add_event(new_action)

    def choose_actions(self):
        for subject_being_id in self.being_list:
            subject_being = self.universe.get_object_by_id(subject_being_id)
            if isinstance(subject_being, (BeingInstance)):
                # Randomly decide an action among those available
                chosen_action = subject_being.choose_action(self.universe.get_action_dictionary(), self.universe.get_weapon_dictionary())
                print(f"{subject_being.name} chose the Action {chosen_action}")
                # At this point the chosen action should already be one the Being has
                # the required skills to do.
                action_definition = self.universe.get_action_definition(chosen_action)
                target_id = None
                # If the Action requires a target Being, choose the target
                print(f"ActionDefinition: {action_definition}")
                if action_definition["target_type"] == 'being':
                    target_id = self.choose_target_being(subject_being_id)
                    target = self.universe.get_object_by_id(target_id)
                    print(f"Target being for {subject_being.name} is {target.name}")
                # Otherwise if the Action requires a target Object, choose the target
                elif action_definition["target_type"] == 'object':
                    target_id = self.choose_target_object(subject_being_id)
                    target = self.universe.get_object_by_id(target_id)
                    print(f"Target object for {subject_being.name} is {target.name}")
                # Otherwise if the Action requires a target Attack, choose the target
                elif action_definition["target_type"] == 'attack':
                    target_id = self.choose_target_attack(subject_being_id)
                    #target = self.universe.get_object_by_id(target_id)
                    print(f"Target attack for {subject_being.name} is {target.name}")
                # Otherwise if the Action requires a target Attack, choose the target
                elif action_definition["target_type"] == 'weapon':
                    target_id = self.choose_target_weapon(subject_being_id)
                    #target = self.universe.get_object_by_id(target_id)
                    print(f"Target weapon for {subject_being.name} is {target.name}")
                # Otherwise no target is necessary

    def choose_action(self, being):
        # randomly decide an action among those available
        chosen_action = being.choose_action(self.universe)
        return chosen_action
            
    def get_object_registry(self):
        return self.universe.get_object_registry()
        
