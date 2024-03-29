#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2024 Rauthiflor LLC"
__version__ = "test_being.py 2024-03-15T10:53-03:00"

# TODO: Check comprehensiveness

import json
import unittest
import sys
import os

sys.path.insert(0, os.path.abspath('../src'))

from abilities import Abilities
from actiondictionary import ActionDictionary
from being import BeingDefinition, BeingInstance, BeingDictionary
from library import Library
from speeds import Speed
from skill import SkillDictionary
from states import StatesList
from strategy import Strategy
from universe import Universe
from weapon import WeaponDictionary

class TestBeingDefinition(unittest.TestCase):
    def setUp(self):
        self.universe = Universe(name="Test Universe", library=Library(config_dir="../src/config"))
#         self.skills_file = '../src/config/skills.tsv'
#         self.weapons_file = '../src/config/weapons.tsv'
#         self.weapon_categories_file = '../src/config/weapon_categories.json'
#         self.skill_dictionary = SkillDictionary()
#         self.skill_dictionary.load_skills(self.skills_file)
# 
#         self.weapon_dictionary = WeaponDictionary()
#         self.weapon_dictionary.load(self.weapons_file)
#         self.weapon_dictionary.load_object_categories(self.weapon_categories_file)
#         self.skill_dictionary.add_weapon_skills(self.weapon_dictionary)

        self.reset_being_def = BeingDefinition('Human', '6', '160', '5', '2d4', 'Chaotic Good', '9', '2')

    def test_init(self):
        self.assertEqual(self.reset_being_def.obj_type, 'Human')
        self.assertEqual(self.reset_being_def.length, 6)
        self.assertEqual(self.reset_being_def.weight, 160)
        self.assertEqual(self.reset_being_def.hit_points, 5)
        self.assertEqual(self.reset_being_def.hit_dice, '2d4')
        self.assertEqual(self.reset_being_def.alignment, 'Chaotic Good')
        self.assertEqual(self.reset_being_def.armor_class, 9)
        self.assertEqual(self.reset_being_def.challenge_rating, 2)
        self.assertEqual(self.reset_being_def.width, 0)
        self.assertEqual(self.reset_being_def.height, 0)
        self.assertEqual(self.reset_being_def.cost, 0)
        self.assertEqual(self.reset_being_def.hardness, 0)
        self.assertFalse(self.reset_being_def.is_magical)
        self.assertEqual(self.reset_being_def.tags, {})
        self.assertEqual(self.reset_being_def.weapon_categories, [])
        self.assertEqual(self.reset_being_def.experience, 0)
        self.assertEqual(self.reset_being_def.sprint(),0)
        self.assertEqual(self.reset_being_def.burrow(),0)
        self.assertEqual(self.reset_being_def.climb(),0)
        self.assertEqual(self.reset_being_def.fly(),0)
        self.assertEqual(self.reset_being_def.swim(),0)
        self.assertEqual(self.reset_being_def.STR(),10)
        self.assertEqual(self.reset_being_def.DEX(),10)
        self.assertEqual(self.reset_being_def.CON(),10)
        self.assertEqual(self.reset_being_def.INT(),10)
        self.assertEqual(self.reset_being_def.WIS(),10)
        self.assertEqual(self.reset_being_def.CHA(),10)
        self.assertEqual(len(self.reset_being_def.skills.skills), 0)
        self.assertEqual(self.reset_being_def.senses, {})
        self.assertEqual(self.reset_being_def.vulnerabilities, {})
        self.assertEqual(self.reset_being_def.immunities, {})
        self.assertEqual(self.reset_being_def.languages, {})
        self.assertEqual(self.reset_being_def.psionics, {})
        self.assertEqual(self.reset_being_def.spells, {})
        self.assertEqual(self.reset_being_def.traits, {})
        self.assertEqual(self.reset_being_def.actions, {})
        self.assertEqual(self.reset_being_def.reactions, {})

    def test_setters_getters(self):
        self.being_def = self.reset_being_def.copy()
        self.being_def.set_tag('tag1', 'tag1_value')
        self.being_def.set_tag('tag2', 'tag2_value')
        self.assertEqual(self.being_def.tags, {'tag1': 'tag1_value', 'tag2': 'tag2_value'})
        self.being_def.add_weapon_category('Unarmed')
        self.being_def.add_weapon_category('Thrown')
        self.assertEqual(self.being_def.weapon_categories, ['Unarmed', 'Thrown'])
        self.being_def.set_max_speed('ambulate', 6)
        self.being_def.set_max_speed('burrow', 1)
        self.being_def.set_max_speed('climb', 1)
        self.being_def.set_max_speed('fly', 30)
        self.being_def.set_max_speed('swim', 1)
        self.assertEqual(self.being_def.sprint(), 6)
        self.assertEqual(self.being_def.burrow(), 1)
        self.assertEqual(self.being_def.climb(), 1)
        self.assertEqual(self.being_def.fly(), 30)
        self.assertEqual(self.being_def.swim(), 1)
        self.being_def.set_abilities(Abilities('11',12,'13',14,'15',16))
        self.assertEqual(self.being_def.STR(),11)
        self.assertEqual(self.being_def.DEX(),12)
        self.assertEqual(self.being_def.CON(),13)
        self.assertEqual(self.being_def.INT(),14)
        self.assertEqual(self.being_def.WIS(),15)
        self.assertEqual(self.being_def.CHA(),16)
        self.being_def.set_ability('str', 10)
        self.being_def.set_ability('DEX', 9)
        self.being_def.set_ability('Constitution', 8)
        self.being_def.set_ability('intelligence', 7)
        self.being_def.set_ability('WISDOM', 6)
        self.being_def.set_ability('Character', 5)
        self.assertEqual(self.being_def.STR(),10)
        self.assertEqual(self.being_def.DEX(),9)
        self.assertEqual(self.being_def.CON(),8)
        self.assertEqual(self.being_def.INT(),7)
        self.assertEqual(self.being_def.WIS(),6)
        self.assertEqual(self.being_def.CHA(),5)
        self.being_def.set_skill_level(self.universe.get_skill_dictionary(), 'ki', 6)
        self.being_def.set_skill_level(self.universe.get_skill_dictionary(), 'bardiche', 1)
        self.assertEqual(self.being_def.get_skill_level('ki'), 6)
        self.assertIsNone(self.being_def.get_skill_level('astronomy'))
        self.assertEqual(len(self.being_def.get_states()),0)

    def test_set_and_body_part_remove_object(self):
        being = BeingDefinition(obj_type='humanoid', length=6, weight=180, hit_points=50, hit_dice='5d10', 
                 alignment='neutral', armor_class=15, challenge_rating=2, body_parts={'left hand': 'dagger', 'right hand': 'sword'})
        # Test set_body_part_holds_object()
        being.set_body_part_holds_object('head', 'helmet')
        self.assertEqual(being.body_parts['head'], 'helmet')
        # Test body_part_remove_object()
        removed_weapon = being.body_part_remove_object('left hand')
        self.assertEqual(removed_weapon, 'dagger')
        self.assertNotIn('left', being.body_parts)

class TestBeingInstance(unittest.TestCase):
    def setUp(self):
        self.universe = Universe(name="Test Universe", library=Library(config_dir="../src/config"))

#         self.skills_file = '../src/config/skills.tsv'
#         self.skill_dictionary = SkillDictionary(self.skills_file)
# 
#         self.weapons_file = '../src/config/weapons.tsv'
#         self.categories_file = '../src/config/weapon_categories.json'
# 
#         self.weapon_dict = WeaponDictionary()
#         self.weapon_dict.load_object_categories(self.categories_file)
#         self.weapon_dict.load(self.weapons_file)

        self.states_file = '../src/config/states.tsv'
        self.states_list = StatesList()
        self.states_list.load_states(self.states_file)

        self.being_def = BeingDefinition('Human', 6, 170, 7, '2d6', 'Neutral', 10, 1)
        self.being_inst = BeingInstance(self.being_def, name='Tobe')
        self.universe.add_object(self.being_inst)
        self.assertEqual(self.being_inst.possessions, [])

        current_being_state = self.being_inst.current
        original_being_state = self.being_inst.original

        self.assertEqual(original_being_state.obj_type, 'Human')
        self.assertEqual(original_being_state.length, 6)
        self.assertEqual(original_being_state.weight, 170)
        self.assertEqual(original_being_state.hit_points, 7)
        self.assertEqual(original_being_state.hit_dice, '2d6')
        self.assertEqual(original_being_state.alignment, 'Neutral')
        self.assertEqual(original_being_state.armor_class, 10)
        self.assertEqual(original_being_state.challenge_rating, 1)
        self.assertEqual(original_being_state.width, 0)
        self.assertEqual(original_being_state.height, 0)
        self.assertEqual(original_being_state.cost, 0)
        self.assertEqual(original_being_state.hardness, 0)
        self.assertFalse(original_being_state.is_magical)
        self.assertEqual(original_being_state.tags, {})
        self.assertEqual(original_being_state.weapon_categories, [])
        self.assertEqual(original_being_state.experience, 0)
        self.assertEqual(original_being_state.sprint(),0)
        self.assertEqual(original_being_state.burrow(),0)
        self.assertEqual(original_being_state.climb(),0)
        self.assertEqual(original_being_state.fly(),0)
        self.assertEqual(original_being_state.swim(),0)
        self.assertEqual(original_being_state.STR(),10)
        self.assertEqual(original_being_state.DEX(),10)
        self.assertEqual(original_being_state.CON(),10)
        self.assertEqual(original_being_state.INT(),10)
        self.assertEqual(original_being_state.WIS(),10)
        self.assertEqual(original_being_state.CHA(),10)
        self.assertEqual(len(original_being_state.skills.skills), 0)
        self.assertEqual(original_being_state.senses, {})
        self.assertEqual(original_being_state.vulnerabilities, {})
        self.assertEqual(original_being_state.resistances, {})
        self.assertEqual(original_being_state.immunities, {})
        self.assertEqual(original_being_state.languages, {})
        self.assertEqual(original_being_state.psionics, {})
        self.assertEqual(original_being_state.spells, {})
        self.assertEqual(original_being_state.traits, {})
        self.assertEqual(original_being_state.actions, {})
        self.assertEqual(original_being_state.reactions, {})
        self.assertEqual(len(original_being_state.get_states()),0)

        self.assertEqual(current_being_state.obj_type, 'Human')
        self.assertEqual(current_being_state.length, 6)
        self.assertEqual(current_being_state.weight, 170)
        self.assertEqual(current_being_state.hit_points, 7)
        self.assertEqual(current_being_state.hit_dice, '2d6')
        self.assertEqual(current_being_state.alignment, 'Neutral')
        self.assertEqual(current_being_state.armor_class, 10)
        self.assertEqual(current_being_state.challenge_rating, 1)
        self.assertEqual(current_being_state.width, 0)
        self.assertEqual(current_being_state.height, 0)
        self.assertEqual(current_being_state.cost, 0)
        self.assertEqual(current_being_state.hardness, 0)
        self.assertFalse(current_being_state.is_magical)
        self.assertEqual(current_being_state.tags, {})
        self.assertEqual(current_being_state.weapon_categories, [])
        self.assertEqual(current_being_state.experience, 0)
        self.assertEqual(current_being_state.sprint(),0)
        self.assertEqual(current_being_state.burrow(),0)
        self.assertEqual(current_being_state.climb(),0)
        self.assertEqual(current_being_state.fly(),0)
        self.assertEqual(current_being_state.swim(),0)
        self.assertEqual(current_being_state.STR(),10)
        self.assertEqual(current_being_state.DEX(),10)
        self.assertEqual(current_being_state.CON(),10)
        self.assertEqual(current_being_state.INT(),10)
        self.assertEqual(current_being_state.WIS(),10)
        self.assertEqual(current_being_state.CHA(),10)
        self.assertEqual(len(current_being_state.skills.skills), 0)
        self.assertEqual(current_being_state.senses, {})
        self.assertEqual(current_being_state.vulnerabilities, {})
        self.assertEqual(current_being_state.resistances, {})
        self.assertEqual(current_being_state.immunities, {})
        self.assertEqual(current_being_state.languages, {})
        self.assertEqual(current_being_state.psionics, {})
        self.assertEqual(current_being_state.spells, {})
        self.assertEqual(current_being_state.traits, {})
        self.assertEqual(current_being_state.get_states(),{})
        self.assertEqual(current_being_state.actions, {})
        self.assertEqual(current_being_state.reactions, {})

#     def test_setters_getters(self):
#         current_being_state = self.being_inst.current
#         original_being_state = self.being_inst.original
#         self.being_inst.add_hit_points(-3)
#         self.assertEqual(self.being_inst.get_hit_points(), 4)
#         self.being_inst.add_experience('50')
#         self.assertEqual(self.being_inst.get_experience(), 50)
#         self.being_inst.set_skill_level(self.skill_dictionary, 'run', 3)
#         self.assertEqual(self.being_inst.get_skill_level('run'), 3)
# 
#     def test_states(self):
#         current_states = self.being_inst.get_states()
#         self.assertEqual(current_states, {})
#         self.being_inst.un_paralyze(self.states_list)
#         self.assertEqual(current_states, {})
#         self.being_inst.paralyze(self.states_list)
#         self.assertEqual(self.being_inst.is_paralyzed(), True)
#         self.being_inst.un_paralyze(self.states_list)
#         self.assertEqual(self.being_inst.is_paralyzed(), False)
# 
#         self.assertEqual(self.being_inst.is_stunned(), False)
#         self.being_inst.stun(self.states_list)
#         self.assertEqual(self.being_inst.is_stunned(), True)
#         self.being_inst.un_stun(self.states_list)
#         self.assertEqual(self.being_inst.is_stunned(), False)
#         
#         self.assertEqual(self.being_inst.is_paralyzed(), False)
#         self.assertEqual(self.being_inst.is_stunned(), False)
#         self.assertEqual(self.being_inst.get_hit_points()>0, True)
# #        print(f'{self.being_inst.current.states} {self.being_inst.get_abilities()}')
#         self.assertEqual(self.being_inst.is_helpless(), False)
#         self.being_inst.paralyze(self.states_list)
#         self.assertEqual(self.being_inst.is_helpless(), True)
#         self.being_inst.un_paralyze(self.states_list)
#         self.assertEqual(self.being_inst.is_helpless(), False)
#         self.being_inst.stun(self.states_list)
#         self.assertEqual(self.being_inst.is_helpless(), True)
#         self.being_inst.un_stun(self.states_list)
#         self.assertEqual(self.being_inst.is_helpless(), False)
#         self.being_inst.set_ability('str', 2)
#         self.assertEqual(self.being_inst.is_helpless(), False)
#         self.being_inst.set_ability('str', 0)
#         self.assertEqual(self.being_inst.is_helpless(), True)
#         self.being_inst.set_ability('str', 10)
#         self.assertEqual(self.being_inst.is_helpless(), False)
# 
#         self.being_inst.set_fatigue_level(5)
#         self.assertEqual(self.being_inst.is_helpless(), True)
#         self.being_inst.set_fatigue_level(4)
#         self.assertEqual(self.being_inst.is_helpless(), False)
#         self.being_inst.set_fatigue_level(0)
#         self.assertEqual(self.being_inst.is_helpless(), False)
# 
#     def test_possible_actions(self):
#         action_dict_file = '../src/config/actions.tsv'
#         action_dict = ActionDictionary()
#         action_dict.load_actions(action_dict_file)
# 
#         skill_dict_file = '../src/config/skills.tsv'
#         skill_dict = SkillDictionary()
#         skill_dict.load_skills(skill_dict_file)
# #        print(f'skill dict: {skill_dict.to_json()}')
# 
#         self.being_inst.set_skill_level(skill_dict, 'stun', 1)
#         self.being_inst.set_skill_level(skill_dict, 'unarmed combat', 2)
#         possible_actions = self.being_inst.possible_actions(action_dict)
# #        print(f'{possible_actions}')
#         self.assertIn('stun', possible_actions)
#         self.assertIn('parry (unarmed)', possible_actions)
#         self.assertNotIn('astronomy', possible_actions)
#         self.assertNotIn('parry (armed)', possible_actions)
#         self.assertEqual(len(possible_actions), 51)
#         self.being_inst.set_weapon_skill_level(self.weapon_dict, 'Longsword', 4)
# #        print(f'{self.being_inst.get_weapon_skills()}')
#         possible_actions = self.being_inst.possible_actions(action_dict)
#         self.assertIn('parry (armed)', possible_actions)
#         self.assertEqual(len(possible_actions), 54)
# 
#     def test_set_body_part_holds_object(self):
#         self.assertEqual(self.being_inst.current.body_parts, {})
#         self.being_inst.set_body_part_holds_object("right_arm", "Longsword")
#         self.assertEqual(self.being_inst.current.body_parts, {"right_arm": "Longsword"})
#         self.being_inst.set_body_part_holds_object("left_arm", "Small wooden shield")
#         self.assertEqual(self.being_inst.current.body_parts, {"right_arm": "Longsword", "left_arm": "Small wooden shield"})

    def test_currently_possible_actions(self):
        action_dict = self.universe.get_action_dictionary()
        skill_dict = self.universe.get_skill_dictionary()
        weapon_dict = self.universe.get_weapon_dictionary()

        possible_actions = self.being_inst.possible_actions(self.universe)
#        print(f'possible: {possible_actions}')
        self.assertNotIn('stun', possible_actions)
        self.assertNotIn('parry (unarmed)', possible_actions)
        self.assertNotIn('parry (armed))', possible_actions)
        self.assertEqual(len(possible_actions), 43)
        currently_possible = self.being_inst.currently_possible_actions(self.universe)
        self.assertEqual(len(currently_possible), 0)

        self.being_inst.set_weapon_skill_level(weapon_dict, 'Longsword', 4)
        possible_actions = self.being_inst.possible_actions(self.universe)
        self.assertIn('parry (armed)', possible_actions)
        self.assertEqual(len(possible_actions), 46)

        currently_possible = self.being_inst.currently_possible_actions(self.universe)
        self.assertEqual(len(currently_possible), 0)

        self.assertEqual(self.being_inst.current.body_parts, {})
        weapon_id = self.universe.make_weapon_for_being(self.being_inst.id, "Longsword", "Longey")
        weapon = self.universe.get_object_by_id(weapon_id)
        self.universe.arm_being(self.being_inst.id, weapon_id, "right hand")
        self.being_inst.set_body_part_holds_object("left hand", None)
        self.assertEqual(self.being_inst.current.body_parts, {"right hand": weapon_id, "left hand": None})
        currently_possible = self.being_inst.currently_possible_actions(self.universe)
        self.assertIn('swing at being', currently_possible)
        self.assertIn('thrust at being', currently_possible)
        self.assertIn('two-handed swing at being', currently_possible)
        self.assertIn('two-handed thrust at being', currently_possible)
        self.assertEqual(len(currently_possible), 8)
#        print(f'currently possible: {currently_possible}')

        # The following will change as new actions are implemented
        self.assertEqual(len(currently_possible), 8)

        self.being_inst.set_skill_level(skill_dict, 'stun', 4)
        possible_actions = self.being_inst.possible_actions(self.universe)
        self.assertIn('stun', possible_actions)
        self.assertNotIn('parry (unarmed)', possible_actions)
        self.assertIn('parry (armed)', possible_actions)
        self.assertEqual(len(possible_actions), 47)
        currently_possible = self.being_inst.currently_possible_actions(self.universe)
        self.assertIn('stun', currently_possible)
        self.assertEqual(len(currently_possible), 9)        
        
        self.being_inst.set_hit_points(0)
        currently_possible = self.being_inst.currently_possible_actions(self.universe)
        self.assertEqual(len(currently_possible), 0)
        
        self.being_inst.set_hit_points(10)
        currently_possible = self.being_inst.currently_possible_actions(self.universe)
        self.assertEqual(len(currently_possible), 9)
        self.being_inst.set_fatigue_level(5)
        currently_possible = self.being_inst.currently_possible_actions(self.universe)
        self.assertEqual(len(currently_possible), 0)

        self.being_inst.set_fatigue_level(0)
        currently_possible = self.being_inst.currently_possible_actions(self.universe)
        self.assertEqual(len(currently_possible), 9)
        self.being_inst.paralyze(self.states_list)
        currently_possible = self.being_inst.currently_possible_actions(self.universe)
        self.assertEqual(len(currently_possible), 0)
        self.being_inst.un_paralyze(self.states_list)
        currently_possible = self.being_inst.currently_possible_actions(self.universe)
        self.assertEqual(len(currently_possible), 9)
        self.being_inst.stun(self.states_list)
        currently_possible = self.being_inst.currently_possible_actions(self.universe)
        self.assertEqual(len(currently_possible), 0)
        self.being_inst.un_stun(self.states_list)
        currently_possible = self.being_inst.currently_possible_actions(self.universe)
        self.assertEqual(len(currently_possible), 9)
        chosen = self.being_inst.choose_action(self.universe)
        self.assertIn(chosen, currently_possible)
#        print(f'Chose: {chosen}')

#     def test_shielded_with(self):
#         self.being_inst.current.body_parts = {"right_arm": "Longsword"}
#         shielded = self.being_inst.shielded_with(self.weapon_dict)
#         self.assertEqual(shielded, {})
#         
#         # Set up a being a shield
#         self.being_inst.current.body_parts = {"right_arm": "Longsword", "left_arm": "Small wooden shield"}
#         # Test the Being is shielded with that shield
#         shielded = self.being_inst.shielded_with(self.weapon_dict)
#         self.assertEqual(shielded, {"left_arm": "Small wooden shield"})
# 
#     def test_body_part_remove_object(self):
#         self.being_inst.current.body_parts = {"right_arm": "Longsword", "left_arm": "Small wooden shield"}
#         self.assertEqual(self.being_inst.current.body_parts, {"right_arm": "Longsword", "left_arm": "Small wooden shield"})
#         removed_weapon = self.being_inst.body_part_remove_object("right_arm")
#         self.assertEqual(self.being_inst.current.body_parts, {"left_arm": "Small wooden shield"})
#         self.assertEqual(removed_weapon, "Longsword")
#         removed_weapon = self.being_inst.body_part_remove_object("right_arm")
#         self.assertEqual(self.being_inst.current.body_parts, {"left_arm": "Small wooden shield"})
#         self.assertIsNone(removed_weapon)
# 
#     def test_set_armor(self):
#         self.assertIsNone(self.being_inst.current.armor)
#         self.being_inst.set_armor("plate armor")
#         self.assertEqual(self.being_inst.current.armor, "plate armor")

class TestBeingDictionary(unittest.TestCase):
    def setUp(self):
        self.objects_file = '../src/config/beings.tsv'
        self.categories_file = '../src/config/being_categories.json'
        self.object_dict = BeingDictionary()

        self.expected_categories = {
    "Elves": [
        "Drow", "Grey elf", "High elf",  "Wood elf", "Half-elf"
    ],
    "Giants": [
        "Cloud giant", "Fire giant", "Frost giant", "Hill giant", "Stone giant", 
        "Storm giant"
    ],
    "Humanoids": [
        "Human"
    ],
    "Kobolds": [
        "Kobold"
    ],
    "Sphinx": [
        "Androsphinx", "Gymnosphinx"
    ],
    "Undead": [
    "Skeleton", "Zombie", "Ghoul", "Wight", "Mummy", "Specter", "Vampire Spawn", 
    "Ghost", "Wraith", "Mummy Lord", "Vampire", "Lich"
    ]
}
        self.object_dict.load(self.objects_file)
        self.assertEqual(len(self.object_dict.objects), 27)
        for object in self.object_dict.objects:
            object_dict = self.object_dict.objects[object]
        self.assertIsInstance(object_dict, BeingDefinition)
        object = self.object_dict.objects['Androsphinx']
        self.assertEqual(object.obj_type, 'Androsphinx')
        self.assertEqual(object.cost, 0)
        self.assertEqual(object.weight, 20000)
        self.assertEqual(object.length, 10)
        self.assertEqual(object.hardness, 0)
        self.assertEqual(object.hit_points, 199)

        self.object_dict.load_object_categories(self.categories_file)
        self.assertEqual(len(self.object_dict.object_categories), 6)
        self.assertDictEqual(self.object_dict.object_categories, self.expected_categories)

    def test_all_objects_in_categories(self):
        self.object_dict.load_object_categories(self.categories_file)
        self.object_dict.load(self.objects_file)
        for object in self.object_dict.objects:
            object_dict = self.object_dict.objects[object]
            found = False
            for category in self.object_dict.object_categories.values():
                if object_dict.obj_type in category:
                    found = True
                    break
            self.assertTrue(found, f"ObjectDefinition {object} with name {object_dict.obj_type} not found in any object category")
    
    def test_all_categories_in_objects(self):
        self.object_dict.load_object_categories(self.categories_file)
        self.object_dict.load(self.objects_file)
        for category_name, category in self.object_dict.object_categories.items():
            for object_name in category:
                self.assertIn(object_name, self.object_dict.objects, 
                              f"ObjectDefinition {object_name} in category {category_name} not found in objects list")

    def test_get_objects_in_category(self):
        self.assertEqual(self.object_dict.get_objects_in_category('Sphinx'), ['Androsphinx', 'Gymnosphinx'])
        self.assertEqual(self.object_dict.get_objects_in_category('Elves'), ['Drow', 'Grey elf', 'High elf',  'Wood elf', 'Half-elf'])
        self.assertIsNone(self.object_dict.get_objects_in_category('nonexistent_category'))

        # clean up the file
#        os.remove(filename)

if __name__ == '__main__':
    unittest.main()
