#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2023 Rauthiflor LLC"
__version__ = "skill.py 2023-12-27T13:14-03:00"

# TODO: Make skill categories and populate the config/skill_categories.tsv

import json
import math

from weapon import WeaponDictionary
from utils import convert_to_numeric, convert_to_boolean

class SkillDefinition():
    '''
    A template for characteristics of a Skill.
    '''
    def __init__(self, name, is_ordinary, is_progressive):
        self.name = name
        self.is_ordinary = convert_to_boolean(is_ordinary)
        self.is_progressive = convert_to_boolean(is_progressive)

    def copy(self):
        '''
        Get an independent copy of the SkillDefinition.
        '''
        new_definition = SkillDefinition(
            self.name,
            self.is_ordinary,
            self.is_progressive)
        return new_definition

    def to_json(self):
        '''
        Get a representation of a SkillDefinition as JSON.
        '''
        data = {
            self.name: self.get_property_dict()
        }
        return json.dumps(data)

    def get_property_dict(self):
        '''
        Get a dictionary with the properties of a SkillDefinition.
        '''
        return {'is_ordinary': self.is_ordinary, 'is_progressive': self.is_progressive}

class SkillDictionary():
    '''
    A reference for information about SkillDefinitions.
    '''
    def __init__(self, skill_dictionary_file=None):
        self.skills = {}
        if skill_dictionary_file is not None:
            self.load_skills(skill_dictionary_file)

    def add_weapon_skills(self, weapon_dictionary):
        '''
        Load weapon skills from a WeaponDictionary into the SkillDictionary.
        '''
        for weapon_category_name, weapon_list in weapon_dictionary.object_categories.items():
            skill_definition = SkillDefinition(weapon_category_name, is_ordinary=True, is_progressive=True)
            self.add_skill(skill_definition)
            for weapon_name in weapon_list:
                skill_definition = SkillDefinition(weapon_name, is_ordinary=True, is_progressive=True)
                self.add_skill(skill_definition)

    def to_json(self):
        '''
        Get a representation of a SkillDictionary as JSON.
        '''
        return json.dumps(self.skills, indent=2)

    def add_skill(self, skill_definition):
        '''
        Use a SkillDefinition to add a skill to a SkillDictionary
        '''
        if not isinstance(skill_definition, SkillDefinition):
            raise TypeError('skill_definition must be an instance of SkillDefinition')
            return
        self.skills[skill_definition.name]=skill_definition.get_property_dict()

    def get_skill_definition(self, skill_name):
        '''
        Get the SkillDefinition out of the SkillDictionary. 
        If not in the dictionary, return None
        '''
        return self.skills.get(skill_name)

    def load_skills(self, filename):
        '''
        Load the SkillDictionary from file.
        '''
        p = True
        with open(filename, 'r') as f:
            lines = f.readlines()
            headers = lines[0].strip().split('\t')
            if p==True:
                p = False
            for line in lines[1:]:
                fields = line.strip().split('\t')
                skill_dict = {}
                for i in range(len(headers)):
                    skill_dict[headers[i]] = fields[i]
                skill = SkillDefinition(**skill_dict)
                self.add_skill(skill)

    def load_from_dict(self, skill_dict):
        '''
        Load the SkillDictionary from a dictionary.
        '''
        self.skills = skill_dict.get('skills')

class Skills():
    '''
    A simple dictionary of skill names and levels. All other information for the skills 
    can be found from the SkillDictionary by looking up the name.
    '''
    def __init__(self):
        self.skills = {}
        self.weapon_skills = {}

    def get_skills(self):
        '''
        Get the skills dictionary from Skills.
        '''
        return self.skills

    def get_skill_level(self, skill_name):
        '''
        Get the level of a Skill. Return None if not in the Skills dictionary.
        '''
        return self.skills.get(skill_name)

    def set_skill_level(self, skill_dictionary, skill_name, level=0):
        '''
        Add a skill with level or set the level of an existing skill.
        skill_dictionary is the SkillDictionary in which to verify that the 
        SkillDefinition given by skill_name exists.
        '''
        n = convert_to_numeric(level)
        if n is None:
            return
        if n < 0:
            n = 0
        if isinstance(skill_dictionary, SkillDictionary):
            skill_definition = skill_dictionary.get_skill_definition(skill_name)
            if skill_definition is not None:
                self.skills[skill_name] = n

    def get_weapon_skills(self):
        '''
        Get the weapon skill dictionary from Skills.
        '''
        return self.weapon_skills

    def get_weapon_skill_level(self, weapon_name):
        '''
        Get the level of a weapon skill from Skills.
        '''
        if weapon_name not in self.weapon_skills:
            return 0
        return self.weapon_skills.get(weapon_name)

    def get_max_weapon_skill_level(self):
        '''
        Get the highest level of a weapon skill from Skills.
        '''
        max_weapon_skill_level = 0
        for weapon, level in self.weapon_skills.items():
            if level > max_weapon_skill_level:
                max_weapon_skill_level = level
        return max_weapon_skill_level

    def set_weapon_skill_level(self, weapon_dict, weapon_name, level=0):
        '''
        Add a weapon skill with level or set the level of an existing weapon skill. 
        Add the corresponding skill levels of all other weapons in the weapon categories
        in which the weapon is found.
        '''
        n = convert_to_numeric(level)
        if n is None:
            return
        if n < 0:
            n = 0
        if not isinstance(weapon_dict, WeaponDictionary):
#            print(f'weapon_dict not a WeaponDictionary')
            return
        if weapon_name not in weapon_dict.objects:
#            print(f'weapon name: {weapon_name} not in weapon_dict.objects: {weapon_dict.objevts}')
            return
#        print(f'weapon name: {weapon_name} set to {level} converted to {n}')
        self.weapon_skills[weapon_name] = n
#        print(f'weapon_skills: {self.weapon_skills}')
        categories = []
        for category, weapons in weapon_dict.object_categories.items():
            if weapon_name in weapons:
                categories.append(category)
#        print(f'categories: {categories}')
        for category in categories:
            for weapon in weapon_dict.object_categories.get(category):
                weapon_level = self.get_weapon_skill_level(weapon)
#                print(f'{weapon} before: {weapon_level}')
#                print(f'weapon_skills: {self.weapon_skills}')
                if weapon_level is None or weapon_level < math.floor(n/2):
                    self.weapon_skills[weapon] = math.floor(n/2)
                weapon_level = self.get_weapon_skill_level(weapon)
#                print(f'{weapon} after: {weapon_level}')
        return

    def copy(self):
        '''
        Get an independent copy of the Skills instance.
        '''
        new_skills = Skills()
        for skill, level in self.skills.items():
            new_skills.skills[skill] = level
        for skill, level in self.weapon_skills.items():
            new_skills.weapon_skills[skill] = level
        return new_skills

    def to_json(self):
        '''
        Get a representation of a SkillDictionary as JSON.
        '''
        data = {
            'skills': self.skills,
            'weapon_skills': self.weapon_skills
        }

#     def __iter__(self):
#         return iter(self.skills.items())
