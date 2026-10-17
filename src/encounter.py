#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2024 Rauthiflor LLC"
__version__ = "encounter.py 2024-03-09T22:00-03:00"

# TODO: Make ''' comments on classes and methods

import json
import math
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
# in a broader historical context. 
class Encounter(Event):
    '''
    A subtype of Event that captures interactions among Encounter entities.
    '''
    def __init__(self, universe, difficulty_class, start_time, end_time=None, 
                 event_type=None, location=None, name="", parent_event_id=None, id=None, 
                 time=None, being_list=None, non_being_object_list=None, 
                 pending_action_list=None, finished_action_list=None, initiated=False, 
                 map=None, awareness=None):
        Event.__init__(self, universe, start_time, end_time, 
                 event_type, location, name, parent_event_id, id)
        self.difficulty_class = convert_to_dc(difficulty_class)
        self.initiated = initiated
        self.map = map
        if time is None:
            self.time = start_time
        else:
            self.time = time
        if being_list is None:
            self.being_list = [] # A list of ids of Beings involved in the Encounter
        else:
            self.being_list = being_list
        if non_being_object_list is None:
            self.non_being_object_list = [] # A list of ids of Objects involved in the Encounter
        else:
            self.non_being_object_list = non_being_object_list
        if pending_action_list is None:
            self.pending_action_list = []
        else:
            self.pending_action_list = pending_action_list
        if finished_action_list is None:
            self.finished_action_list = []
        else:
            self.finished_action_list = finished_action_list
        # Awareness is directed encounter state: observer Being id -> Entity ids
        # currently known to that observer.  It is deliberately distinct from physical proximity;
        # later sight, hearing, memory, concealment, and other perception systems can
        # decide when awareness should be added or removed.
        self.awareness = {}
        if awareness is not None:
            for observer_id, target_ids in awareness.items():
                self.awareness[observer_id] = set(target_ids)

    def to_json(self):
        def handle_circular_refs(obj):
            if isinstance(obj, (Universe)):
                return obj.id  # Return only the ID for Universe and Event instances
            return obj.__dict__

        data = {
            "type": self.type,
            "event_type": self.event_type,
            "name": self.name,
            "universe_id": self.universe.get_id(),
            "start_time": self.start_time,
            "end_time": self.end_time,
            "parent_event_id": self.parent_event_id,
            "location": self.location,
            "difficulty_class": self.difficulty_class,
            "map": self.map,
            "being_list": self.being_list,
            "object_list": self.non_being_object_list,
            "awareness": {
                observer_id: sorted(target_ids)
                for observer_id, target_ids in self.awareness.items()
            }
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

    def make_armor_for_being(self, being_id, armor_type, name):
        new_armor_id = self.universe.make_armor_for_being(being_id, armor_type, name)
        if new_armor_id is None:
            return None
        self.non_being_object_list.append(new_armor_id)
        return new_armor_id

    def armor_being(self, being_id, armor_id):
        return self.universe.armor_being(being_id, armor_id)

    def add_object(self, object_id):
        if object_id not in self.non_being_object_list:
            self.non_being_object_list.append(object_id)

    def add_being(self, being_id):
        if being_id not in self.being_list:
            self.being_list.append(being_id)

    def entity_ids(self):
        """Return ids of all participating Encounter entities in stable order.

        At present, spatially participating entities are ``ObjectInstance`` objects:
        Beings first, followed by non-Being Objects.  The method deliberately exposes
        an entity-level view so later Entity subclasses need not change spatial APIs.
        """
        result = []
        for entity_id in self.being_list + self.non_being_object_list:
            if entity_id not in result:
                result.append(entity_id)
        return result

    def get_entity(self, entity_id):
        """Return a participating spatial Entity, or ``None`` if unavailable."""
        if entity_id not in self.entity_ids():
            return None
        entity = self.universe.get_object_by_id(entity_id)
        if not isinstance(entity, ObjectInstance):
            return None
        return entity

    def get_being(self, being_id):
        """Return a participating Being, or ``None`` if it is unavailable."""
        if being_id not in self.being_list:
            return None
        being = self.get_entity(being_id)
        if not isinstance(being, BeingInstance):
            return None
        return being

    def distance_between_entities(self, first_entity_id, second_entity_id):
        """Return continuous 3D distance between two participating entities.

        ``None`` is returned if either entity is not part of this Encounter or has
        not yet been placed in continuous space.
        """
        first = self.get_entity(first_entity_id)
        second = self.get_entity(second_entity_id)
        if first is None or second is None:
            return None
        relation = first.spatial_relation_to(second)
        if relation is None:
            return None
        return relation.distance

    def distance_between_beings(self, first_being_id, second_being_id):
        """Return continuous 3D distance between two participating Beings."""
        if self.get_being(first_being_id) is None or self.get_being(second_being_id) is None:
            return None
        return self.distance_between_entities(first_being_id, second_being_id)

    @staticmethod
    def _validate_max_distance(max_distance):
        try:
            max_distance = float(max_distance)
        except (TypeError, ValueError) as exc:
            raise TypeError("max_distance must be numeric") from exc
        if not math.isfinite(max_distance) or max_distance < 0.0:
            raise ValueError("max_distance must be a finite non-negative number")
        return max_distance

    def entity_within(self, first_entity_id, second_entity_id, max_distance):
        """Return whether two participating, placed entities are within a distance.

        Distance is measured in the units of their shared continuous Cartesian
        reference frame; no grid or cell relation is used.
        """
        max_distance = self._validate_max_distance(max_distance)
        distance = self.distance_between_entities(first_entity_id, second_entity_id)
        return distance is not None and distance <= max_distance

    def within_distance(self, first_entity_id, second_entity_id, max_distance):
        """Compatibility alias for :meth:`entity_within`."""
        return self.entity_within(first_entity_id, second_entity_id, max_distance)

    def entities_within(self, subject_entity_id, max_distance):
        """Return participating entity ids within ``max_distance`` of a subject.

        The subject itself is excluded. Unplaced entities are ignored. Encounter
        order is preserved for deterministic downstream perception or interaction
        processing.
        """
        if self.get_entity(subject_entity_id) is None:
            return []
        result = []
        for entity_id in self.entity_ids():
            if entity_id == subject_entity_id:
                continue
            if self.entity_within(subject_entity_id, entity_id, max_distance):
                result.append(entity_id)
        return result

    def beings_within(self, subject_entity_id, max_distance):
        """Return nearby participating Being ids."""
        return [
            entity_id for entity_id in self.entities_within(subject_entity_id, max_distance)
            if isinstance(self.get_entity(entity_id), BeingInstance)
        ]

    def objects_within(self, subject_entity_id, max_distance):
        """Return nearby participating non-Being Object ids."""
        return [
            entity_id for entity_id in self.entities_within(subject_entity_id, max_distance)
            if not isinstance(self.get_entity(entity_id), BeingInstance)
        ]

    def mark_aware(self, observer_being_id, target_entity_id):
        """Record directed awareness of an Encounter entity by a Being."""
        if observer_being_id == target_entity_id:
            return False
        if self.get_being(observer_being_id) is None or self.get_entity(target_entity_id) is None:
            return False
        targets = self.awareness.setdefault(observer_being_id, set())
        before = len(targets)
        targets.add(target_entity_id)
        return len(targets) != before

    def clear_awareness(self, observer_being_id, target_entity_id):
        """Remove directed awareness, returning whether stored state changed."""
        targets = self.awareness.get(observer_being_id)
        if targets is None or target_entity_id not in targets:
            return False
        targets.remove(target_entity_id)
        if not targets:
            del self.awareness[observer_being_id]
        return True

    def is_aware(self, observer_being_id, target_entity_id):
        """Return whether directed awareness of an entity is recorded."""
        return target_entity_id in self.awareness.get(observer_being_id, set())

    def aware_entities(self, observer_being_id):
        """Return participating entity ids currently known to the observer."""
        if self.get_being(observer_being_id) is None:
            return []
        targets = self.awareness.get(observer_being_id, set())
        return [entity_id for entity_id in self.entity_ids() if entity_id in targets]

    def aware_beings(self, observer_being_id):
        """Return participating Being ids currently known to the observer."""
        return [
            entity_id for entity_id in self.aware_entities(observer_being_id)
            if isinstance(self.get_entity(entity_id), BeingInstance)
        ]

    def aware_objects(self, observer_being_id):
        """Return participating non-Being Object ids currently known to the observer."""
        return [
            entity_id for entity_id in self.aware_entities(observer_being_id)
            if not isinstance(self.get_entity(entity_id), BeingInstance)
        ]

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
#            print(f"----- {self.name} turn {self.time} -----")
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
        # Do one round
#       return self.do_one_round()

        # Go until one or no one left standing
#        return self.last_one_standing()

        # Go until one or no one left running
        return self.last_one_running()

    def do_one_round(self):
        # Do just one round
        if self.time == 1:
            return False
        return True

    def last_one_standing(self):
        # Go until one or no one has positive hit points
        being_count = len(self.being_list)
        beings_alive = 0
        for being_id in self.being_list:
            being = self.universe.get_object_by_id(being_id)
#            print(f"Current hit points for {being.name}: {being.current.hit_points}")
            if being.current.hit_points > 0:
                beings_alive += 1
                if beings_alive > 1:
                    return True
        return False

    def last_one_running(self):
        # Go until one or no one is not exhausted
        being_count = len(self.being_list)
        beings_exhausted = 0
        for being_id in self.being_list:
            being = self.universe.get_object_by_id(being_id)
            print(f"Current fatigue for {being.name}: {being.current.fatigue_level}")
            if being.current.fatigue_level > 4: # Fatigue level 4 is exhausted
                beings_exhausted += 1
                if beings_exhausted > 1:
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
        action_dict = self.universe.get_action_dictionary()
        object_registry = self.universe.object_registry

        for subject_being_id in self.being_list:
            subject_being = self.universe.get_object_by_id(subject_being_id)
#            print(f"Choosing fight action for {subject_being.name}")

            if subject_being.is_dead():
#                print(f"{subject_being.name} is dead")
                continue

            if subject_being.is_helpless():
#                print(f"{subject_being.name} is helpless")
                continue

            if self.is_being_occupied(subject_being_id):
#                print(f"{subject_being.name} is occupied")
                continue

            target = None
            new_action = None
            if isinstance(subject_being, (BeingInstance)):
                # Randomly decide an melee action among those available
                chosen_action = subject_being.choose_melee_action(self.universe)
                # At this point the chosen action should already be one the Being has
                # the required skills to do.
#                print(f"chosen action: {chosen_action}")
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

                # Create an Action Event with the Encounter as its parent
                armed = subject_being.armed_with(self.universe)
#                print(f"armed: {armed}")
                weapon_id = subject_being.choose_weapon(armed)
                weapon = self.universe.get_object_by_id(weapon_id)
#                print(f"weapon_id: {weapon_id} weapon_type: {weapon.obj_type}, weapon_name: {weapon.name}")
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

#                print(f"{subject_being.name} targets {target.name} with {chosen_action} using {weapon.name}")
#                print(f"{subject_being.name} targets {target.name} with {chosen_action} using {weapon.name} ending at t={new_action.end_time}")
                # Add Action to the Event History
                self.pending_action_list.append(new_action.id)
                self.universe.add_event(new_action)

    def choose_actions(self):
        for subject_being_id in self.being_list:
            subject_being = self.universe.get_object_by_id(subject_being_id)
            if isinstance(subject_being, (BeingInstance)):
                # Randomly decide an action among those available
                chosen_action = subject_being.choose_action(self.universe.get_action_dictionary(), self.universe.get_weapon_dictionary())
#                print(f"{subject_being.name} chose the Action {chosen_action}")
                # At this point the chosen action should already be one the Being has
                # the required skills to do.
                action_definition = self.universe.get_action_definition(chosen_action)
                target_id = None
                # If the Action requires a target Being, choose the target
                if action_definition["target_type"] == 'being':
                    target_id = self.choose_target_being(subject_being_id)
                    target = self.universe.get_object_by_id(target_id)
#                    print(f"Target being for {subject_being.name} is {target.name}")
                # Otherwise if the Action requires a target Object, choose the target
                elif action_definition["target_type"] == 'object':
                    target_id = self.choose_target_object(subject_being_id)
                    target = self.universe.get_object_by_id(target_id)
#                    print(f"Target object for {subject_being.name} is {target.name}")
                # Otherwise if the Action requires a target Attack, choose the target
                elif action_definition["target_type"] == 'attack':
                    target_id = self.choose_target_attack(subject_being_id)
                    #target = self.universe.get_object_by_id(target_id)
#                    print(f"Target attack for {subject_being.name} is {target.name}")
                # Otherwise if the Action requires a target Attack, choose the target
                elif action_definition["target_type"] == 'weapon':
                    target_id = self.choose_target_weapon(subject_being_id)
                    #target = self.universe.get_object_by_id(target_id)
#                    print(f"Target weapon for {subject_being.name} is {target.name}")
                # Otherwise no target is necessary

    def choose_action(self, being):
        # randomly decide an action among those available
        chosen_action = being.choose_action(self.universe)
        return chosen_action
            
    def get_object_registry(self):
        return self.universe.get_object_registry()
