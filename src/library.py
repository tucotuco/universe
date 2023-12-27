#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2023 Rauthiflor LLC"
__version__ = "universe.py 2023-12-26T17:47-03:00"

# TODO: Write unit tests

from actiondictionary import ActionDictionary
from armor import ArmorDictionary
from being import BeingDictionary
from identifiable import Identifiable
from object import ObjectDictionary
from skill import SkillDictionary
from weapon import WeaponDictionary

class Library(Identifiable):
    '''
    A container for dictionaries of type definitions.
    '''
    def __init__(self, config_dir="./config", name=None, id=None):
        Identifiable.__init__(self, name, id)
        self.action_dictionary = None
        self.armor_dictionary = None
        self.being_dictionary = None
        self.object_dictionary = None
        self.skill_dictionary = None
        self.weapon_dictionary = None

        self.load_library(config_dir)

    def load_library(self, config_dir):
        try:
            dictionary_filename = f'{config_dir}/actions.tsv'
            self.action_dictionary = ActionDictionary(dictionary_filename)
            print(f"Dictionary added to library from {dictionary_filename}!")
        except Exception as e:
            print(f"Error adding dictionary {dictionary_filename}: {e}")
        
        try:
            dictionary_filename = f'{config_dir}/armors.tsv'
            categories_filename = f'{config_dir}/armor_categories.json'
            self.armor_dictionary = ArmorDictionary(dictionary_filename)
            self.armor_dictionary.load_object_categories(categories_filename)
            print(f"Dictionary added to library from {dictionary_filename}!")
        except Exception as e:
            print(f"Error adding dictionary {dictionary_filename}: {e}")

        try:
            dictionary_filename = f'{config_dir}/beings.tsv'
            categories_filename = f'{config_dir}/being_categories.json'
            self.being_dictionary = BeingDictionary(dictionary_filename)
            self.being_dictionary.load_object_categories(categories_filename)
            print(f"Dictionary added to library from {dictionary_filename}!")
        except Exception as e:
            print(f"Error adding dictionary {dictionary_filename}: {e}")

        try:
            dictionary_filename = f'{config_dir}/objects.tsv'
            categories_filename = f'{config_dir}/object_categories.json'
            self.object_dictionary = ObjectDictionary(dictionary_filename)
            self.being_dictionary.load_object_categories(categories_filename)
            print(f"Dictionary added to library from {dictionary_filename}!")
        except Exception as e:
            print(f"Error adding dictionary {dictionary_filename}: {e}")

        try:
            dictionary_filename = f'{config_dir}/skills.tsv'
            self.skill_dictionary = SkillDictionary(dictionary_filename)
#            categories_filename = f'{config_dir}/skill_categories.json'
#            self.skill_dictionary.load_object_categories(categories_filename)
            print(f"Dictionary added to library from {dictionary_filename}!")
        except Exception as e:
            print(f"Error adding dictionary {dictionary_filename}: {e}")

        try:
            dictionary_filename = f'{config_dir}/weapons.tsv'
            categories_filename = f'{config_dir}/weapon_categories.json'
            self.weapon_dictionary = WeaponDictionary(dictionary_filename)
            self.weapon_dictionary.load_object_categories(categories_filename)
            print(f"Dictionary added to library from {dictionary_filename}!")
        except Exception as e:
            print(f"Error adding dictionary {dictionary_filename}: {e}")

    def get_action_definition(self, action_name):
        return self.action_dictionary.get_action_definition(action_name)

    def get_armor_definition(self, armor_name):
        return self.armor_dictionary.get_object_definition(armor_name)

    def get_being_definition(self, being_name):
        return self.being_dictionary.get_object_definition(being_name)

    def get_object_definition(self, object_name):
        return self.object_dictionary.get_object_definition(object_name)

    def get_skill_definition(self, skill_name):
        return self.skill_dictionary.get_object_definition(skill_name)

    def get_weapon_definition(self, weapon_name):
        return self.weapon_dictionary.get_object_definition(weapon_name)
