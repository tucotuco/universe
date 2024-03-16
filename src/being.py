#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2024 Rauthiflor LLC"
__version__ = "being.py 2024-03-15T22:47-03:00"

# TODO: BeingDictionary should probably be saved and loaded as JSON.
# TODO: Check for properties that need constraints and implement them (a finished example is experience)
# TODO: Implement drop_weapon(object_id)
# TODO: Implement accumulation of Fatigue
# TODO: Resolve issues surrounding default weapons if not armed with another weapon.

import json
import random

from abilities import Abilities
from actiondictionary import ActionDictionary
from object import ObjectDefinition, ObjectInstance, ObjectDictionary
from skill import Skills
from speeds import Speed
from states import States
from strategy import Strategy
from utils import convert_to_numeric, convert_to_experience, convert_to_fatigue, roll_dice
from utils import experience_level, saving_throw_experience_modifier
from weapon import WeaponInstance, WeaponDictionary

class BeingDefinition(ObjectDefinition):
    '''
    A template for characteristics of a Being, which is a subtype of Object.
    '''
    def __init__(self, obj_type, length, weight, hit_points, hit_dice, alignment, 
                 armor_class, challenge_rating, width=0, height=0, cost=0, hardness=0, 
                 is_magical=False, tags=None, weapon_categories=None, experience=0, 
                 max_speed=None, abilities=None, skills=None, senses=None, 
                 vulnerabilities=None, resistances=None, immunities=None, languages=None, 
                 psionics=None, spells=None, traits=None, states=None, actions=None, 
                 reactions=None, body_parts=None, armor_id=None, fatigue_level=0):
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
        self.states = states or States()
        self.actions = actions or {}
        self.reactions = reactions or {}
        # body_parts are expected to include a body location and the object or natural 
        # weapon in that location
        self.body_parts = body_parts or {}
        self.armor_id = armor_id
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
            self.body_parts.copy(),
            self.armor_id,
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
            'resistances': self.resistances,
            'immunities': self.immunities,
            'languages': self.languages,
            'psionics': self.psionics,
            'spells': self.spells,
            'traits': self.traits,
            'states': self.states,
            'actions': self.actions,
            'reactions': self.reactions,
            'body_parts': self.body_parts,
            'armor_id': self.armor_id,
            'fatigue_level': self.fatigue_level
        }
        return json.dumps(data)

    def sprint(self):
        '''
        Get the maximum sprinting speed for this BeingDefinition.
        '''
        return self.max_speed.sprint()

    def burrow(self):
        '''
        Get the maximum burrowing speed for this BeingDefinition.
        '''
        return self.max_speed.burrow()

    def climb(self):
        '''
        Get the maximum climbing speed for this BeingDefinition.
        '''
        return self.max_speed.climb()

    def fly(self):
        '''
        Get the maximum flying speed for this BeingDefinition.
        '''
        return self.max_speed.fly()

    def swim(self):
        '''
        Get the maximum swimming speed for this BeingDefinition.
        '''
        return self.max_speed.swim()

    def set_speed(self, speed=Speed()):
        '''
        
        Set the speeds for this BeingDefinition.
        '''
        if isinstance(speed, Speed):
            self.max_speed = speed

    def set_max_speed(self, speed_type, new_value):
        '''
        Set the maximum speed of the given type for this BeingDefinition.
        '''
        self.max_speed.set_max_speed(speed_type, new_value)

    def get_abilities(self):
        '''
        Get the set of Abilities for this BeingDefinition.
        '''
        return self.abilities.get_abilities()

    def STR(self):
        '''
        Get the strength ability for this BeingDefinition.
        '''
        return self.abilities.STR()

    def DEX(self):
        '''
        Get the dexterity ability for this BeingDefinition.
        '''
        return self.abilities.DEX()

    def CON(self):
        '''
        Get the constitution ability for this BeingDefinition.
        '''
        return self.abilities.CON()

    def INT(self):
        '''
        Get the intelligence ability for this BeingDefinition.
        '''
        return self.abilities.INT()

    def WIS(self):
        '''
        Get the wisdom ability for this BeingDefinition.
        '''
        return self.abilities.WIS()

    def CHA(self):
        '''
        Get the charisma ability for this BeingDefinition.
        '''
        return self.abilities.CHA()

    def set_ability(self, ability, new_value):
        '''
        Set the given ability to a new value for this BeingDefinition.
        '''
        self.abilities.set_ability(ability, new_value)

    def set_abilities(self, abilities=Abilities()):
        '''
        Set the set of Abilities for this BeingDefinition.
        '''
        if isinstance(abilities, Abilities):
            self.abilities = abilities

    def get_skills(self):
        '''
        Get the set of Skills for this BeingDefinition.
        '''
        return self.skills.get_skills()

    def get_skill_level(self, skill_name):
        '''
        Get the skill level for a given skill for this BeingDefinition.
        '''
        return self.skills.get_skill_level(skill_name)

    def set_skill_level(self, skill_dictionary, skill_name, level=0):
        '''
        Set the skill level for a given skill for this BeingDefinition.
        '''
        self.skills.set_skill_level(skill_dictionary, skill_name, level)

    def get_weapon_skills(self):
        '''
        Get the set of weapon skills for this BeingDefinition.
        '''
        return self.skills.get_weapon_skills()

    def get_weapon_skill_level(self, weapon_name):
        '''
        Get the skill level for a given weapon for this BeingDefinition.
        '''
        return self.skills.get_weapon_skill_level(weapon_name)

    def get_max_weapon_skill_level(self):
        '''
        Get the highest level of the weapon skill levels for this BeingDefinition.
        '''
        return self.skills.get_max_weapon_skill_level()

    def set_weapon_skill_level(self, weapon_dict, weapon_name, level=0):
        '''
        Set the weapon skill level for a given weapon for this BeingDefinition.
        '''
        self.skills.set_weapon_skill_level(weapon_dict, weapon_name, level)

    def get_body_parts(self):
        '''
        Get the dictionary of body parts for this BeingDefinition.
        '''
        return self.body_parts

    def set_body_part_holds_object(self, body_part, object_id):
        '''
        Set the object "held" by a body part for this BeingDefinition.
        '''
        self.body_parts[body_part] = object_id

    def body_part_remove_object(self, body_part):
        '''
        Remove an object "held" by the given body part for this BeingDefinition.
        '''
        object_id = self.body_parts.get(body_part)
        if object_id is not None:
            del self.body_parts[body_part]
        return object_id

    def get_fatigue_level(self):
        '''
        Get the defined fatigue level for this BeingDefinition.
        '''
        return self.fatigue_level
        
    def set_fatigue_level(self, new_fatigue_level):
        '''
        Set the defined fatigue level for this BeingDefinition.
        '''
        self.fatigue_level = convert_to_fatigue(new_fatigue_level)
        
    def get_states(self):
        '''
        Get the physical and mental States for this BeingDefinition.
        '''
        return self.states.get_states()
        
    def get_state(self, state_name):
        '''
        Get the given physical and mental State for this BeingDefinition.
        '''
        return self.states.get_state(state_name)
        
    def set_state(self, state_list, state_name, value):
        '''
        Set the given physical and mental State for this BeingDefinition.
        '''
        self.states.set_state(state_list, state_name, value)

class BeingInstance(ObjectInstance):
    ''' 
    An ObjectInstance that is a Being based on a BeingDefinition.
    '''
    def __init__(self, being_definition, name=None):
        ObjectInstance.__init__(self, being_definition, name)
        self.original = being_definition
        self.current = being_definition.copy()
        self.possessions = []
        self.weapons = []
        self.strategy = Strategy()

    def reset(self):
        '''
        Set all of the current values of the BeingInstance to their original values.
        '''
        self.current = self.original.copy()

    def set_strategy(self, attack=0, defense=0, timing=0, extra_damage=0):
        '''
        Set the melee Strategy of the BeingInstance.
        '''
        self.strategy = Strategy(attack, defense, timing, extra_damage)

    def get_experience(self):
        '''
        Get the current amount of experience accumulated by the BeingInstance.
        '''
        return self.current.experience

    def set_experience(self, new_experience):
        '''
        Set the current amount of experience accumulated by the BeingInstance.
        '''
        self.current.experience = convert_to_experience(new_experience)

    def add_experience(self, experience):
        '''
        Add the given amount of experience to the current amount of experience accumulated by the BeingInstance.
        '''
        self.current.experience += convert_to_numeric(experience)
        self.current.experience = convert_to_experience(self.current.experience)

    def get_fatigue_level(self):
        '''
        Get the current fatigue level of the BeingInstance.
        '''
        return self.current.fatigue_level

    def set_fatigue_level(self, new_fatigue_level):
        '''
        Set the current fatigue level of the BeingInstance.
        '''
        self.current.fatigue_level = convert_to_fatigue(new_fatigue_level)

    def add_fatigue_level(self, fatigue_change):
        '''
        Add an amount to the current fatigue level of the BeingInstance.
        '''
        self.current.fatigue += convert_to_numeric(fatigue_change)
        self.current.fatigue = convert_to_fatigue(self.current.fatigue)

    def get_hit_points(self):
        '''
        Get the current hit points of the BeingInstance.
        '''
        return self.current.hit_points

    def set_hit_points(self, new_hit_points):
        '''
        Set the current hit points of the BeingInstance.
        '''
        self.current.hit_points = convert_to_numeric(new_hit_points)

    def add_hit_points(self, hit_points):
        '''
        Add an amount to the current hit points of the BeingInstance.
        '''
        self.current.hit_points += convert_to_numeric(hit_points)

    def get_hit_dice(self):
        '''
        Get the current hit dice of the BeingInstance.
        '''
        return self.current.hit_dice

    def get_alignment(self):
        '''
        Get the alignment of the BeingInstance.
        '''
        return self.current.alignment

    def set_alignment(self, new_alignment):
        '''
        Set the alignment of the BeingInstance.
        '''
        self.alignment = new_alignment

    def get_armor_class(self):
        '''
        Get the armor class of the BeingInstance.
        '''
        return self.current.armor_class

    def set_armor_class(self, new_armor_class):
        '''
        Set the armor class of the BeingInstance.
        '''
        # TODO: make convert_to_armor_class method in utils
        self.current_armor_class = convert_to_numeric(new_armor_class)

    def get_challenge_rating(self):
        '''
        Get the challenge rating of the BeingInstance.
        '''
        # TODO: make convert_to_challenge_rating method in utils
        return self.current.challenge_rating

    def sprint(self):
        '''
        Get the current maximum sprinting speed for this BeingInstance.
        '''
        return self.current.max_speed.sprint()

    def burrow(self):
        '''
        Get the current maximum burrowing speed for this BeingInstance.
        '''
        return self.current.max_speed.burrow()

    def climb(self):
        '''
        Get the current maximum climbing speed for this BeingInstance.
        '''
        return self.current.max_speed.climb()

    def fly(self):
        '''
        Get the current maximum flying speed for this BeingInstance.
        '''
        return self.current.max_speed.fly()

    def swim(self):
        '''
        Get the current maximum swimming speed for this BeingInstance.
        '''
        return self.current.max_speed.swim()

    def set_max_speed(self, speed_type, new_value):
        '''
        Set the current maximum speed of the given type for this BeingInstance.
        '''
        self.current.max_speed.set_max_speed(speed_type, new_value)

    def get_abilities(self):
        '''
        Get the current set of Abilities for this BeingInstance.
        '''
        return self.current.abilities.get_abilities()

    def STR(self):
        '''
        Get the current strength for this BeingInstance.
        '''
        return self.current.abilities.STR()

    def DEX(self):
        '''
        Get the current dexterity for this BeingInstance.
        '''
        return self.current.abilities.DEX()

    def CON(self):
        '''
        Get the current constitution for this BeingInstance.
        '''
        return self.current.abilities.CON()

    def INT(self):
        '''
        Get the current intelligence for this BeingInstance.
        '''
        return self.current.abilities.INT()

    def WIS(self):
        '''
        Get the current wisdom for this BeingInstance.
        '''
        return self.current.abilities.WIS()

    def CHA(self):
        '''
        Get the current charisma for this BeingInstance.
        '''
        return self.current.abilities.CHA()

    def set_ability(self, ability, new_value):
        '''
        Set the current value of the given ability to a new value for this BeingInstance.
        '''
        self.current.set_ability(ability, new_value)

    def get_skills(self):
        '''
        Get the current set of Skills for this BeingInstance.
        '''
        return self.current.get_skills()

    def get_weapon_skills(self):
        '''
        Get the current set of weapon skills for this BeingInstance.
        '''
        return self.current.get_weapon_skills()

    def get_skill_level(self, skill_name):
        '''
        Get the current skill level for a given skill for this BeingInstance.
        '''
        return self.current.get_skill_level(skill_name)

    def set_skill_level(self, skill_dictionary, skill_name, level=0):
        '''
        Set the current skill level for a given skill for this BeingInstance.
        '''
        self.current.set_skill_level(skill_dictionary, skill_name, level)

    def get_weapon_skill_level(self, weapon_name):
        '''
        Get the current skill level for a given weapon for this BeingInstance.
        '''
        return self.current.get_weapon_skill_level(weapon_name)

    def get_max_weapon_skill_level(self):
        '''
        Get the highest level of the current weapon skill levels for this BeingInstance.
        '''
        return self.current.get_max_weapon_skill_level()

    def set_weapon_skill_level(self, weapon_dictionary, weapon_name, level=0):
        '''
        Set the current weapon skill level for a given weapon for this BeingInstance.
        '''
        self.current.set_weapon_skill_level(weapon_dictionary, weapon_name, level)

    def fitness(self):
        '''
        Get the current fitness for this BeingInstance.
        '''
        return self.current.fitness

    def set_fitness(self, new_fitness):
        '''
        Set the current fitness for this BeingInstance.
        '''
        self.current.fitness += convert_to_numeric(new_fitness)
        if self.current.fitness < 0:
            self.current.fitness = 0

    def add_fitness(self, add_fitness):
        '''
        Add the given amount of fitness to the current amount of fitness of the BeingInstance.
        '''
        self.current.fitness += convert_to_numeric(add_fitness)
        if self.current.fitness < 0:
            self.current.fitness = 0

    def add_possession(self, added_possession): 
        '''
        Add an object to the list of possessions of the BeingInstance.
        '''
        self.possessions.append(added_possession)

    def remove_possession(self, possession_id):
        '''
        Remove an object from the list of possessions of the BeingInstance.
        '''
        self.possessions.remove(possession_id)

    def add_weapon(self, weapon):
        '''
        Add a weapon to the list of weapons of the BeingInstance.
        '''
        self.weapons.append(weapon)

    def drop_weapon(self, weapon_id):
        '''
        Remove a weapon from the body part of the BeingInstance it armed and from its weapon list.
        '''
        # TODO: Can't drop natural weapons. Dropping last non-natural weapon leaves Being armed with natural weapons.
        # TODO: Remove from weapons[] and remove from body_parts
        pass
        #self.weapons.remove(weapon_id)

    def get_body_parts(self):
        '''
        Get the dictionary of body parts for this BeingInstance.
        '''
        return self.current.body_parts

    def set_body_part_holds_object(self, body_location, object_id):
        '''
        Set the object "held" by a body part for this BeingInstance.
        '''
        self.current.body_parts[body_location] = object_id

    def body_part_remove_object(self, body_location):
        '''
        Remove an object "held" by the given body part for this BeingInstance.
        '''
        object_id = self.current.body_parts.get(body_location)
        if object_id is not None:
            del self.current.body_parts[body_location]
        return object_id

    def get_armor_id(self):
        '''
        Get the id of the armor for this BeingInstance.
        '''
        return self.current.armor_id

    def set_armor_id(self, armor_id):
        '''
        Set the id of the armor for this BeingInstance.
        '''
        self.current.armor_id = armor_id

    def get_states(self):
        '''
        Get the current physical and mental States for this BeingInstance.
        '''
        return self.current.states.get_states()
        
    def get_state(self, state_name):
        '''
        Get the current given physical and mental State for this BeingInstance.
        '''
        return self.current.states.get_state(state_name)
        
    def set_state(self, state_list, state_name, value):
        '''
        Set the current given physical and mental State for this BeingInstance.
        '''
        self.current.states.set_state(state_list, state_name, value)

    def is_immobilized(self):
        '''
        Assess whether this BeingInstance is immobilized.
        '''
        if is_pinned():
            return True
        return is_helpless()

    def is_dead(self):
        '''
        Assess whether this BeingInstance is dead.
        '''
        if self.get_hit_points() <= -10:
            return True
        return False

    def is_helpless(self):
        '''
        Assess whether this BeingInstance is helpless.
        '''
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
        '''
        Assess whether this BeingInstance is pinned.
        '''
        if len(self.current.get_states()) == 0:
            return False
        if self.current.get_state('pinned') is None:
            return False
        return self.current.get_state('pinned')

    def pin(self, state_list):
        '''
        Set this pinned state of the BeingInstance to True.
        '''
        self.current.set_state(state_list, 'pinned', True)

    def un_pin(self, state_list):
        '''
        Set this pinned state of the BeingInstance to False.
        '''
        if self.current.get_state('pinned') is None:
            return
        self.current.set_state(state_list, 'pinned', False)

    def is_paralyzed(self):
        '''
        Assess whether this BeingInstance is paralyzed.
        '''
        if len(self.current.get_states()) == 0:
            return False
        if self.current.get_state('paralyzed') is None:
            return False
        return self.current.get_state('paralyzed')

    def paralyze(self, state_list):
        '''
        Set the state of paralysis of the BeingInstance to True.
        '''
        self.current.set_state(state_list, 'paralyzed', True)

    def un_paralyze(self, state_list):
        '''
        Set the state of paralysis of the BeingInstance to False.
        '''
        if self.current.get_state('paralyzed') is None:
            return
        self.current.set_state(state_list, 'paralyzed', False)

    def is_stunned(self):
        '''
        Assess whether this BeingInstance is stunned.
        '''
        if len(self.current.get_states()) == 0:
            return False
        if self.current.get_state('stunned') is None:
            return False
        return self.current.get_state('stunned')

    def stun(self, state_list):
        '''
        Set the stunned state of the BeingInstance to True.
        '''
        self.current.set_state(state_list, 'stunned', True)

    def un_stun(self, state_list):
        '''
        Set the stunned state of the BeingInstance to False.
        '''
        if self.current.get_state('stunned') is None:
            return
        self.current.set_state(state_list, 'stunned', False)

    def makes_save(self, ability_score, difficulty_class):
        '''
        Assess whether a saving throw for this BeingInstance is successful.
        '''
        roll = roll_dice('1d20')
        if roll == 1:
            return False
        if roll == 20:
            return True
        level = experience_level(self.current.experience)
        if roll >= difficulty_class - saving_throw_experience_modifier(level):
            return True
        return False

    def choose_melee_action(self, universe):
        '''
        Choose a melee action from among those currently possible for the BeingInstance.
        '''        
        from universe import Universe
        actions_possible_now = self.currently_possible_actions(universe)
#        print(f"being.py: choose_melee_action() actions possible now: {actions_possible_now}")
        options = []
        action_dict = universe.get_action_dictionary()
        for action in actions_possible_now:
            action_definition = action_dict.get_action_definition(action)
#            print(f"being.py: choose_melee_action: action_definition: {action_definition}")
            if action_definition.get("is_melee") == 'True':
                if self.melee_action_supported(universe) == True:
                    options.append(action)
        if len(options) == 0:
            return None
        return random.choice(options)

    def choose_action(self, universe):
        '''
        Choose an action from among those currently possible for the BeingInstance.
        '''        
        from universe import Universe
        actions_possible_now = self.currently_possible_actions(universe)
        options = []
        for action in actions_possible_now:
            options.append(action)
        if len(options) == 0:
            return None
        return random.choice(options)

    def has_swing_weapon(self, universe):
        '''
        Determine if the BeingInstance is armed with a weapon that can be used to swing.
        '''
        # TODO: Accommodate natural weapons
        arms = self.armed_with(universe)
#        print(f"arms: {arms}")
        for body_part, weapon_id in arms.items():
            weapon = universe.get_object_by_id(weapon_id)
            if weapon is not None and "swing" in weapon.get_melee_types():
                return True
        return False

    def has_thrust_weapon(self, universe):
        '''
        Determine if the BeingInstance is armed with a weapon that can be used to thrust.
        '''
        # TODO: Accommodate natural weapons
        for body_part, weapon_id in self.armed_with(universe).items():
            weapon = universe.get_object_by_id(weapon_id)
            if weapon is not None and "thrust" in weapon.get_melee_types():
                return True
        return False

    def has_entangle_weapon(self, universe):
        '''
        Determine if the BeingInstance is armed with a weapon that can be used to entangle.
        '''
        # TODO: Accommodate natural weapons
        for body_part, weapon_id in self.armed_with(universe).items():
            weapon = universe.get_object_by_id(weapon_id)
            if weapon is not None and "entangle" in weapon.get_melee_types():
                return True
        return False

    def melee_action_supported(self, universe):
        '''
        Determine if a melee action is possible given the weapons with which the the BeingInstance is armed.
        '''
        if self.has_swing_weapon(universe):
            return True
        if self.has_thrust_weapon(universe):
            return True
        return False

    def possible_actions(self, universe):
        '''
        Make a list of actions that are possible based on the skills of the BeingInstance.
        '''
        from universe import Universe
        action_dict = universe.get_action_dictionary()
        actions = {}
        for action, properties in action_dict:
#            print(f"being.py: possible_actions(): {action}: {properties}")
            required_skill = properties.get('required_skill')
            if required_skill == 'none':
                actions[action] = properties
            elif required_skill == 'advanced weapon' and self.get_max_weapon_skill_level() > 1:
                actions[action] = properties
            elif required_skill in self.current.get_skills():
                actions[action] = properties
        return actions

    def armored_with(self):
        '''
        Get the id of the armor of the BeingInstance.
        '''
        return self.get_armor_id()

    def shielded_with(self, universe):
        '''
        Get a dictionary of body parts of the BeingInstance that have shields on them.
        '''
        from universe import Universe

        weapon_dict = universe.library.weapon_dictionary
        shielded = {}
        for body_location, object_id in self.get_body_parts().items():
            an_object = universe.get_object_by_id(object_id)
            if an_object is not None and an_object.current.obj_type in weapon_dict.get_objects_in_category('Shields'):
                shielded[body_location]=object_id
        return shielded
    
    def armed_with(self, universe):
        '''
        Get a dictionary of body parts of the BeingInstance that "hold" a weapon.
        '''
        from universe import Universe

        weapon_dict = universe.get_weapon_dictionary()
        armed = {}
        for body_location, object_id in self.get_body_parts().items():
            the_object = universe.get_object_by_id(object_id)
            if the_object is not None and weapon_dict.get_object_definition(the_object.current.obj_type) is not None:
                armed[body_location]=object_id
#        print(f"being.py: armed_with(): {armed}")
        return armed

    def choose_weapon(self, armed):
        '''
        Select a weapon from among those "held" by the BeingInstance.
        '''
#        print(f"being.py choose_weapon() armed: {armed}")
        if armed is None or len(armed) == 0:
            return None
        choice = random.choice(list(armed))
#        print(f"being.py choose_weapon() choice: {choice}")
        return armed[choice]
    
    def currently_possible_actions(self, universe, target=None):
        '''
        Make an dictionary of actions that are currently possible based on the current circumstances of the BeingInstance.
        '''
        # TODO: implement multi-action. Could the same mechanism as an Encounter be nested?
        from universe import Universe
#        action_dict = universe.get_action_dictionary()
        weapon_dict = universe.get_weapon_dictionary()
        
        possible_actions = self.possible_actions(universe)
#        print(f"being.py: currently_possible_actions() possible_actions: {possible_actions}")

#        print(f"\ncurrently_possible_actions(): possible_actions = {possible_actions}")
        if self.is_helpless():
            return {}
        actions = {}
        has_free_hand = False
        shields = self.shielded_with(universe)
        armed_with = self.armed_with(universe)
        armored_with = self.armored_with()

        for body_location, weapon in self.get_body_parts().items():
            if weapon is None: # at least one hand unarmed
                has_free_hand = True
                break

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
            elif action == 'break weapon (armed)':
                # TODO: implement armed break weapon
                # Must be armed with a weapon that allows a swing attack and target must 
                # be armed
                pass
#                 if not isinstance(target, WeaponInstance):
#                     pass
#                 for body_part, weapon in armed_with.items():
#                     attack_types = weapon_dict.objects[weapon].attacks XXX
#                     
#                     if attack_types.get('S') is not None:
#                         actions[action] = properties
#                         break            
            elif action == 'break weapon (unarmed)':
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
            elif action == 'grab object':
                # TODO: implement grab
                # Target must be within reach, success makes target held
                pass
            elif action == 'grab being':
                # TODO: implement grab
                # Target must be within reach, success makes target held
                pass
            elif action == 'hold object':
                # TODO: implement hold
                # Target must be held
                pass
            elif action == 'hold being':
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
            elif action == 'shoot being':
                # Must be armed with a weapon of the bows category
                for body_location, weapon in self.get_body_parts().items():
                    if weapon in weapon_dict.get_objects_in_category('Bows'):
                        actions[action] = properties
                        break
            elif action == 'shoot object':
                # Must be armed with a weapon of the bows category
                for body_location, weapon_id in self.get_body_parts().items():
                    weapon = universe.get_object_by_id(weapon_id)
                    if weapon is not None and weapon.obj_type in weapon_dict.get_objects_in_category('Bows'):
                        actions[action] = properties
                        break
            elif action == 'launch at being':
                # Must be armed with a weapon of the catapults category
                for body_location, weapon_id in self.get_body_parts().items():
                    weapon = universe.get_object_by_id(weapon_id)
                    if weapon is not None and weapon.obj_type in weapon_dict.get_objects_in_category('Catapults'):
                        actions[action] = properties
                        break
            elif action == 'launch at object':
                # Must be armed with a weapon of the catapults category
                for body_location, weapon_id in self.get_body_parts().items():
                    weapon = universe.get_object_by_id(weapon_id)
                    if weapon is not None and weapon.obj_type in weapon_dict.get_objects_in_category('Catapults'):
                        actions[action] = properties
                        break
            elif action == 'stun':
                if has_free_hand == True:
                    actions[action] = properties
            elif action == 'swing at being':
                has_swing_weapon = False
                # Could be armed or unarmed
                for body_location, weapon_id in self.get_body_parts().items():
                    weapon = universe.get_object_by_id(weapon_id)
                    if weapon is not None and "swing" in weapon.get_melee_types():
                        has_swing_weapon = True
                if has_swing_weapon == True:
                    actions[action] = properties
            elif action == 'swing at object':
                has_swing_weapon = False
                # Could be armed or unarmed
                for body_location, weapon_id in self.get_body_parts().items():
                    weapon = universe.get_object_by_id(weapon_id)
                    if weapon is not None and "swing" in weapon.get_melee_types():
                        has_swing_weapon = True
                if has_swing_weapon == True:
                    actions[action] = properties
            elif action == 'thrust at being':
                has_thrust_weapon = False
                # Could be armed or unarmed
                for body_location, weapon_id in self.get_body_parts().items():
                    weapon = universe.get_object_by_id(weapon_id)
                    if weapon is not None and "thrust" in weapon.get_melee_types():
                        has_thrust_weapon = True
                if has_thrust_weapon == True:
                    actions[action] = properties
            elif action == 'thrust at object':
                has_thrust_weapon = False
                # Could be armed or unarmed
                for body_location, weapon_id in self.get_body_parts().items():
                    weapon = universe.get_object_by_id(weapon_id)
                    if weapon is not None and "thrust" in weapon.get_melee_types():
                        has_thrust_weapon = True
                if has_thrust_weapon == True:
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
            elif action == 'touch being':
                # TODO: implement touch
                # Target must be within reach
                pass
            elif action == 'touch object':
                # TODO: implement touch
                # Target must be within reach
                pass
            elif action == 'trip':
                # TODO: implement trip
                # Must first make a successful touch, grab, bull rush, or strike against 
                pass
            elif action == 'two-handed swing at being':
                # Must be armed with one hand free
                if len(armed_with) > 0 and has_free_hand == True:
                    has_swing_weapon = False
                    # Could be armed or unarmed
                    for body_location, weapon_id in self.get_body_parts().items():
                        weapon = universe.get_object_by_id(weapon_id)
                        if weapon is not None and "swing" in weapon.get_melee_types():
                            has_swing_weapon = True
                    if has_swing_weapon == True:
                        actions[action] = properties
            elif action == 'two-handed swing at object':
                # Must be armed with one hand free
                if len(armed_with) > 0 and has_free_hand == True:
                    has_swing_weapon = False
                    # Could be armed or unarmed
                    for body_location, weapon_id in self.get_body_parts().items():
                        weapon = universe.get_object_by_id(weapon_id)
                        if weapon is not None and "swing" in weapon.get_melee_types():
                            has_swing_weapon = True
                    if has_swing_weapon == True:
                        actions[action] = properties
            elif action == 'two-handed thrust at being':
                # Must be armed with one hand free
                if len(armed_with) > 0 and has_free_hand == True:
                    has_thrust_weapon = False
                    # Could be armed or unarmed
                    for body_location, weapon_id in self.get_body_parts().items():
                        weapon = universe.get_object_by_id(weapon_id)
                        if weapon is not None and "thrust" in weapon.get_melee_types():
                            has_thrust_weapon = True
                    if has_thrust_weapon == True:
                        actions[action] = properties
            elif action == 'two-handed thrust at object':
                # Must be armed with one hand free
                if len(armed_with) > 0 and has_free_hand == True:
                    has_thrust_weapon = False
                    # Could be armed or unarmed
                    for body_location, weapon_id in self.get_body_parts().items():
                        weapon = universe.get_object_by_id(weapon_id)
                        if weapon is not None and "thrust" in weapon.get_melee_types():
                            has_thrust_weapon = True
                    if has_thrust_weapon == True:
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
                if shields is not None and len(shields) > 0:
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

class BeingDictionary(ObjectDictionary):
    '''
    A reference for information about BeingDefinitions.
    '''
    def __init__(self, dictionary_file=None):
        ObjectDictionary.__init__(self)

        if dictionary_file is not None:
            self.load(dictionary_file)

    def load(self, filename):
        '''
        Get predefined BeingDefinitions from a CSV file.
        '''
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
