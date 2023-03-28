#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2023 Rauthiflor LLC"
__version__ = "being.py 2023-03-20T18:56-03:00"

# TODO: Make class BeingDictionary and tests
# TODO: Make BeingInstance to_json()
# TODO: Make file to load dictionary from
# TODO: Make character class based on Being?
# TODO: Make a SkillDefinition class with name, experience, level? SkillDictionary to load from file, subclass WeaponSkill?
# TODO: Make possessions class with named containers (and Container class) (backpack, left_hand, right_hand, body, head, etc.)
# TODO: Make methods such as isArmored, isArmed, isShielded
# TODO: Check for properties that need constraints and implement them (done example, experience)
# TODO: Add dict key removers.
# TODO: BeingDictionary should probably be saved and loaded as JSON.
# TODO: Make ''' comments on classes and methods

import json
import random

from abilities import Abilities
from action import ActionDictionary
from object import ObjectDefinition, ObjectInstance, ObjectDictionary
from skill import Skills
from speeds import Speed
from utils import convert_to_numeric, convert_to_experience, convert_to_fatigue
from weapon import WeaponDictionary

class BeingDefinition(ObjectDefinition):
    def __init__(self, obj_type, length, weight, hit_points, hit_dice, alignment, 
                 armor_class, challenge_rating, width=0, height=0, cost=0, hardness=0, 
                 is_magical=False, tags=None, weapon_categories=None, experience=0, 
                 max_speed=None, abilities=None, skills=None, senses=None, 
                 vulnerabilities=None, resistances=None, immunities=None, languages=None, 
                 psionics=None, spells=None, traits=None, states=None, actions=None, reactions=None,
                 arms=None, armor=None, fatigue_level=0):
        super().__init__(obj_type, length, width, height, weight, cost, hardness, 
                         hit_points, is_magical, tags, weapon_categories)
        self.experience = convert_to_experience(experience)
        self.hit_dice = hit_dice
        self.alignment = alignment
        self.armor_class = convert_to_numeric(armor_class)
        self.challenge_rating = convert_to_numeric(challenge_rating)
        self.max_speed = max_speed or Speed()
        self.abilities = abilities or Abilities()
        self.skills = skills or Skills()
        self.senses = senses or {}
        self.vulnerabilities = vulnerabilities or {}
        self.resistances = resistances or {}
        self.immunities = immunities or {}
        self.languages = languages or {}
        self.psionics = psionics or {}
        self.spells = spells or {}
        self.traits = traits or {}
        # TODO: Make a States class with all of the functionally useful states as a dict?
        self.states = states or {}
        self.actions = actions or {}
        self.reactions = reactions or {}
        # TODO: Make an Arms class with all of the body locations (arm, leg, tail. etc.) 
        # that can hold something or attack
        # arms are expected to be a body location and the weapon in that location
        self.arms = arms or {}
        self.armor = armor
        self.fatigue_level = 0

    def copy(self):
        '''
        Get an independent copy of the BeingDefinition.
        '''
        new_being_definition = BeingDefinition(
            self.obj_type,
            self.length,
            self.weight,
            self.hit_points,
            self.hit_dice,
            self.alignment,
            self.armor_class,
            self.challenge_rating,
            self.width,
            self.height,
            self.cost,
            self.hardness,
            self.is_magical,
            self.tags.copy(),
            self.weapon_categories.copy(),
            self.experience,
            self.max_speed.copy(), 
            self.abilities.copy(), 
            self.skills.copy(), 
            self.senses.copy(), 
            self.vulnerabilities.copy(), 
            self.resistances.copy(), 
            self.immunities.copy(), 
            self.languages.copy(), 
            self.psionics.copy(), 
            self.spells.copy(), 
            self.traits.copy(), 
            self.states.copy(), 
            self.actions.copy(), 
            self.reactions.copy(),
            self.arms.copy(),
            self.armor,
            self.fatigue_level)
        return new_being_definition

    def to_json(self):
        '''
        Get a representation of a BeingDefinition as JSON.
        '''
        data = {
            'obj_type': self.obj_type,
            'length': self.length,
            'width': self.width,
            'height': self.height,
            'weight': self.weight,
            'cost': self.cost,
            'hardness': self.hardness,
            'hit_points': self.hit_points,
            'is_magical': self.is_magical,
            'tags': self.tags,
            'weapon_categories': self.weapon_categories,
            'experience': self.experience,
            'hit_dice': self.hit_dice,
            'alignment': self.alignment,
            'armor_class': self.armor_class,
            'challenge_rating': self.challenge_rating,
            'max_speed': self.max_speed,
            'abilities': self.abilities,
            'skills': self.skills,
            'senses': self.senses,
            'vulnerabilities': self.vulnerabilities,
            'resistences': self.resistences,
            'immunities': self.immunities,
            'languages': self.languages,
            'psionics': self.psionics,
            'spells': self.spells,
            'traits': self.traits,
            'states': self.states,
            'actions': self.actions,
            'reactions': self.reactions,
            'arms': self.arms,
            'armor': self.armor,
            'fatigue_level': self.fatigue_level
        }
        return json.dumps(data)

    def sprint(self):
        return self.max_speed.sprint()

    def burrow(self):
        return self.max_speed.burrow()

    def climb(self):
        return self.max_speed.climb()

    def fly(self):
        return self.max_speed.fly()

    def swim(self):
        return self.max_speed.swim()

    def set_speed(self, speed=Speed()):
        if isinstance(speed, Speed):
            self.max_speed = speed

    def set_max_speed(self, speed_type, new_value):
        self.max_speed.set_max_speed(speed_type, new_value)

    def get_abilities(self):
        return self.abilities.get_abilities()

    def STR(self):
        return self.abilities.STR()

    def DEX(self):
        return self.abilities.DEX()

    def CON(self):
        return self.abilities.CON()

    def INT(self):
        return self.abilities.INT()

    def WIS(self):
        return self.abilities.WIS()

    def CHA(self):
        return self.abilities.CHA()

    def set_ability(self, ability, new_value):
        self.abilities.set_ability(ability, new_value)

    def set_abilities(self, abilities=Abilities()):
        if isinstance(abilities, Abilities):
            self.abilities = abilities

    def get_skills(self):
        return self.skills.get_skills()

    def get_skill_level(self, skill_name):
        return self.skills.get_skill_level(skill_name)

    def set_skill_level(self, skill_dictionary, skill_name, level=0):
        self.skills.set_skill_level(skill_dictionary, skill_name, level)

    def get_weapon_skills(self):
        return self.skills.get_weapon_skills()

    def get_weapon_skill_level(self, weapon_name):
        return self.skills.get_weapon_skill_level(weapon_name)

    def get_max_weapon_skill_level(self):
        return self.skills.get_max_weapon_skill_level()

    def set_weapon_skill_level(self, weapon_dict, weapon_name, level=0):
        self.skills.set_weapon_skill_level(weapon_dict, weapon_name, level)

    def get_arms(self):
        return self.arms

    def set_arm(self, body_location, weapon):
        self.arms[body_location] = weapon

    def remove_arm(self, body_location):
        weapon = self.arms.get(body_location)
        if weapon is not None:
            del self.arms[body_location]
        return weapon

    def get_fatigue_level(self):
        return self.fatigue_level
        
    def set_fatigue_level(self, new_fatigue_level):
        self.fatigue_level = convert_to_fatigue(new_fatigue_level)
        

class BeingInstance(ObjectInstance):
    def __init__(self, being_definition, name=''):
        ObjectInstance.__init__(self, being_definition, name)
        self.original = being_definition
        self.current = being_definition.copy()
        self.possessions = {}

    def get_experience(self):
        return self.current.experience

    def set_experience(self, new_experience):
        self.current.experience = convert_to_experience(new_experience)

    def add_experience(self, experience):
        self.current.experience += convert_to_numeric(experience)
        self.current.experience = convert_to_experience(self.current.experience)

    def get_fatigue_level(self):
        return self.current.fatigue_level

    def set_fatigue_level(self, new_fatigue_level):
        self.current.fatigue_level = convert_to_fatigue(new_fatigue_level)

    def add_fatigue_level(self, fatigue_change):
        self.current.fatigue += convert_to_numeric(fatigue_change)
        self.current.fatigue = convert_to_fatigue(self.current.fatigue)

    def get_hit_points(self):
        return self.current.hit_points

    def set_hit_points(self, new_hit_points):
        self.current.hit_points = convert_to_numeric(new_hit_points)

    def add_hit_points(self, hit_points):
        self.current.hit_points += convert_to_numeric(hit_points)

    def get_hit_dice(self):
        return self.current.hit_dice

    def get_alignment(self):
        return self.current.alignment

    def set_alignment(self, new_alignment):
        self.alignment = new_alignment

    def get_armor_class(self):
        return self.current.armor_class

    def set_armor_class(self, new_armor_class):
        # ToDo: make convert_to_armor_class method in utils
        self.current_armor_class = convert_to_numeric(new_armor_class)

    def get_challenge_rating(self):
        # ToDo: make convert_to_challenge_rating method in utils
        return self.current.challenge_rating

    def sprint(self):
        return self.current.max_speed.sprint()

    def burrow(self):
        return self.current.max_speed.burrow()

    def climb(self):
        return self.current.max_speed.climb()

    def fly(self):
        return self.current.max_speed.fly()

    def swim(self):
        return self.current.max_speed.swim()

    def set_max_speed(self, speed_type, new_value):
        self.current.max_speed.set_max_speed(speed_type, new_value)

    def get_abilities(self):
        return self.current.abilities.get_abilities()

    def STR(self):
        return self.current.abilities.STR()

    def DEX(self):
        return self.current.abilities.DEX()

    def CON(self):
        return self.current.abilities.CON()

    def INT(self):
        return self.current.abilities.INT()

    def WIS(self):
        return self.current.abilities.WIS()

    def CHA(self):
        return self.current.abilities.CHA()

    def set_ability(self, ability, new_value):
        self.current.set_ability(ability, new_value)

    def get_skills(self):
        return self.current.get_skills()

    def get_weapon_skills(self):
        return self.current.get_weapon_skills()

    def get_skill_level(self, skill_name):
        return self.current.get_skill_level(skill_name)

    def set_skill_level(self, skill_dictionary, skill_name, level=0):
        self.current.set_skill_level(skill_dictionary, skill_name, level)

    def get_weapon_skill_level(self, weapon_name):
        return self.current.get_weapon_skill_level(weapon_name)

    def get_max_weapon_skill_level(self):
        return self.current.get_max_weapon_skill_level()

    def set_weapon_skill_level(self, weapon_dictionary, weapon_name, level=0):
        self.current.set_weapon_skill_level(weapon_dictionary, weapon_name, level)

    def fitness(self):
        return self.current.fitness

    def set_fitness(self, new_fitness):
        self.current.fitness += convert_to_numeric(new_fitness)
        if self.current.fitness < 0:
            self.current.fitness = 0

    def fitness(self, add_fitness):
        self.current.fitness += convert_to_numeric(add_fitness)
        if self.current.fitness < 0:
            self.current.fitness = 0

    def set_possession(self, added_possession): 
        self.current.possessions.add_possession(added_possession)
        # TODO: Implement posssession as a dict with ObjectDefinition categories and a dictionary of instances inside those with ids as keys

    def remove_possession(self, possession_id):
        # TODO: Possessions will have to have identifiers and be removed by identifier
        pass

    def get_arms(self):
        return self.current.arms

    def set_arm(self, body_location, weapon):
        self.current.arms[body_location] = weapon

    def remove_arm(self, body_location):
        weapon = self.current.arms.get(body_location)
        if weapon is not None:
            del self.current.arms[body_location]
        return weapon

    def set_armor(self, armor):
        self.current.armor = armor

    def is_immobilized(self):
        if is_pinned():
            return True
        return is_helpless()

    def is_helpless(self):
        if self.is_paralyzed():
            return True
        if self.is_stunned():
            return True
        if self.get_hit_points() <= 0:
            return True
        if self.get_fatigue_level() == 5:
            return True
        if self.STR() == 0 or self.DEX() == 0 or self.CON() == 0:
            return True
        return False

    def is_pinned(self):
        if len(self.current.states) == 0:
            return False
        if self.current.states.get('isPinned') is None:
            return False
        return self.current.states.get('isPinned')

    def pin(self):
        self.current.states['isPinned'] = True

    def un_pin(self):
        if self.current.states.get('isPinned') is None:
            return
        self.current.states['isPinned'] = False

    def is_paralyzed(self):
        if len(self.current.states) == 0:
            return False
        if self.current.states.get('isParalyzed') is None:
            return False
        return self.current.states.get('isParalyzed')

    def paralyze(self):
        self.current.states['isParalyzed'] = True

    def un_paralyze(self):
        if self.current.states.get('isParalyzed') is None:
            return
        self.current.states['isParalyzed'] = False

    def is_stunned(self):
        if len(self.current.states) == 0:
            return False
        if self.current.states.get('isStunned') is None:
            return False
        return self.current.states.get('isStunned')

    def stun(self):
        self.current.states['isStunned'] = True

    def un_stun(self):
        if self.current.states.get('isStunned') is None:
            return
        self.current.states['isStunned'] = False

    def choose_action(self, action_dict, weapon_dict):
        currently_possible_actions = self.currently_possible_actions(action_dict, weapon_dict)
        options = []
        for action in currently_possible_actions:
            options.append(action)
        if len(options) == 0:
            return None
        return random.choice(options)

    # Make an actions list based on the Being's skills
    def possible_actions(self, action_dict):
        if not isinstance(action_dict, ActionDictionary):
            return {}
        actions = {}
        for action, properties in action_dict:
            required_skill = properties.get('required_skill')
            if required_skill == 'none':
                actions[action] = properties
            elif required_skill == 'advanced weapon' and self.get_max_weapon_skill_level() > 1:
                actions[action] = properties
            elif required_skill in self.current.get_skills():
                actions[action] = properties
        return actions

    # Make an actions dictionary based on Being's current situation
    def currently_possible_actions(self, action_dict, weapon_dict):
        # TODO: implement multi-action
        possible_actions = self.possible_actions(action_dict)

        if self.is_helpless():
            return {}
        actions = {}
        has_free_hand = False
        armed_with = []
        shielded_with = []
        for body_location, weapon in self.get_arms().items():
            if weapon is None: # at least one hand unarmed
                has_free_hand = True
                break

        for body_location, weapon in self.get_arms().items():
            if self.get_weapon_skill_level(weapon) > 0:
                armed_with.append(weapon)

        if isinstance(weapon_dict, WeaponDictionary):
            for body_location, weapon in self.get_arms().items():
                if weapon in weapon_dict.get_objects_in_category('Shields'):
                    shielded_with.append(weapon)

#        print(f'free hand: {has_free_hand} armed with: {armed_with} shielded with: {shielded_with}')
        for action, properties in possible_actions.items():
            required_skill = properties.get('required_skill')
            if required_skill == 'advanced weapon':
                # Check to see if the Being is armed and has advanced skill with an 
                # armed_with weapon
                # Includes: disarm with weapon, feint with weapon, parry with weapon
                for weapon in armed_with:
                    if self.get_weapon_skill_level(weapon) > 1:
                        actions[action] = properties
            if required_skill == 'unarmed combat':
                # Check to see if the Being has one unoccupied unarmed attack
                # Includes: disarm unarmed, feint, unarmed, deflect unarmed, 
                # parry unarmed
                if has_free_hand == True:
                    actions[action] = properties
            if action == 'break hold':
                # TODO: implement break hold
                # Must be held
                pass
            elif action == 'armed break weapon':
                # TODO: implement armed break weapon
                # Must be armed and target must be armed
                pass
            elif action == 'unarmed break weapon':
                # TODO: implement unarmed break weapon
                # Must have an unarmed attack and target must be armed
                pass
            elif action == 'bull rush':
                # TODO: implement bull rush
                # Must be able to move 
                pass
            elif action == 'charge':
                # TODO: implement charge
                # Must not be engaged by target. Must be able to move <= 4 yps
                pass
            elif action == 'coup de grace':
                # TODO: implement coup de grace
                # Target must be helpless and undefended
                pass
            elif action == 'end run':
                # TODO: implement end run
                # Must have a target within moving distance
                pass
            elif action == 'grab':
                # TODO: implement grab
                # Target must be within reach, success makes target held
                pass
            elif action == 'hold':
                # TODO: implement hold
                # Target must be held
                pass
            elif action == 'takedown':
                # TODO: implement takedown
                # Target must be held
                pass
            elif action == 'reverse':
                # TODO: implement reverse
                # Self must be pinned or in disadvantaged takedown position
                pass
            elif action == 'pin from above':
                # TODO: implement pin from above
                # Self must be in advantaged takedown position over target
                pass
            elif action == 'pin from below':
                # TODO: implement pin from below
                # Self must be in advantaged takedown position over target
                pass
            elif action == 'escape':
                # TODO: implement escape
                # Self must be pinned or in disadvantaged takedown position
                pass
            elif action == 'dismount rider':
                # TODO: implement dismount rider
                # Target must be mounted
                pass
            elif action == 'overrun':
                # TODO: implement overrun
                # Must be able to move 
                pass
            elif action == 'ready':
                # TODO: implement ready
                # Must have object to ready
                pass
            elif action == 'shield bash':
                # Must be armed with a shield
                if len(shielded_with) > 0:
                    actions[action] = properties
            elif action == 'shoot':
                # Must be armed with a weapon of the bows category
                for body_location, weapon in self.get_arms().items():
                    if weapon in weapon_dict.get_objects_in_category('Bows'):
                        actions[action] = properties
                        break
            elif action == 'launch':
                # Must be armed with a weapon of the catapults category
                for body_location, weapon in self.get_arms().items():
                    if weapon in weapon_dict.get_objects_in_category('Catapults'):
                        actions[action] = properties
                        break
            elif action == 'stun':
                if has_free_hand == True:
                    actions[action] = properties
            elif action == 'swing':
                # Could be armed or unarmed
                actions[action] = properties
            elif action == 'thrust':
                # Could be armed or unarmed
                actions[action] = properties
            elif action == 'subdue':
                # TODO: implement subdue
                # Must be armed with a weapon that can do bludgeon penetration type
                # This includes unarmed
                pass
            elif action == 'throw':
                # TODO: implement throw
                # Must have object ready that can be thrown
                pass
            elif action == 'touch':
                # TODO: implement touch
                # Target must be within reach
                pass
            elif action == 'trip':
                # TODO: implement trip
                # Must first make a successful touch, grab, bull rush, or strike against 
                pass
            elif action == 'two-handed swing':
                # Must be armed with one hand free
                if len(armed_with) > 0 and has_free_hand:
                        actions[action] = properties
            elif action == 'two-handed thrust':
                # Must be armed with one hand free
                if len(armed_with) > 0 and has_free_hand:
                        actions[action] = properties
            elif action == 'undefended attack':
                # TODO: implement undefended attack
                # This isn't an action, but rather a defender state for a chosen action
                pass
            elif action == 'wrest':
                # TODO: implement wrest
                # Target object must be held and held by opponent
                pass
            elif action == 'block':
                # Must be armed with a shield
                if len(shielded_with) > 0:
                    actions[action] = properties
            elif action == 'disengage':
                # TODO: implement disengage
                # Must be able to move 
                pass
            elif action == 'dodge':
                # TODO: implement dodge
                # Cannot be part of multi-action except with other dodges
                pass
            elif action == 'yield':
                # TODO: implement yield
                # Must be able to move 
                pass
            else: # Every other kind of action isn't defined
                pass
#        print(f'currently possible actions: {actions}')
        return actions

# A dictionary of all information categories of beings
class BeingDictionary(ObjectDictionary):
    def __init__(self):
        ObjectDictionary.__init__(self)

    def load_beings(self, filename):
        p = True
        with open(filename, 'r') as f:
            lines = f.readlines()
            headers = lines[0].strip().split('\t')
            if p==True:
                p = False
            for line in lines[1:]:
                fields = line.strip().split('\t')
                being_dict = {}
                for i in range(len(headers)):
                    being_dict[headers[i]] = fields[i]
                being = BeingDefinition(**being_dict)
                self.objects[being.obj_type] = being

# Define a class to represent actions
class Action:
    def __init__(self, actor, start_time, end_time, action_type):
        self.start_time = start_time
        self.end_time = end_time
        self.action_type = action_type
        self.actor = self.set_actor(actor)

    # Define a method to compare actions by start time
    def __lt__(self, other):
        return self.start_time < other.start_time

    # Define a method to add an actor to the action
    def set_actor(self, actor):
        if isinstance(actor, BeingInstance):
            self.actor = actor
            return actor
        else:
            raise TypeError('actor must be an instance of the BeingInstance class')
        return None
