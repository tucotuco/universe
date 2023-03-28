#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2023 Rauthiflor LLC"
__version__ = "test_being.py 2023-03-17T08:43-03:00"

# TODO: Make comprehensive test coverage (all methods)

import json
import unittest
import sys
import os

sys.path.insert(0, os.path.abspath('../src'))

from action import ActionDictionary
from being import BeingDefinition, BeingInstance
from weapon import WeaponDictionary
from speeds import Speed
from abilities import Abilities
from skill import SkillDictionary

class TestBeingDefinition(unittest.TestCase):
    def setUp(self):
        self.skills_file = '../src/config/skills.tsv'
        self.weapons_file = '../src/config/weapons.tsv'
        self.weapon_categories_file = '../src/config/weapon_categories.json'
        self.skill_dictionary = SkillDictionary()
        self.skill_dictionary.load_skills(self.skills_file)

        self.weapon_dictionary = WeaponDictionary()
        self.weapon_dictionary.load_objects(self.weapons_file)
        self.weapon_dictionary.load_object_categories(self.weapon_categories_file)
        self.skill_dictionary.add_weapon_skills(self.weapon_dictionary)

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
        self.being_def.set_skill_level(self.skill_dictionary, 'ki', 6)
        self.being_def.set_skill_level(self.skill_dictionary, 'bardiche', 1)
        self.assertEqual(self.being_def.get_skill_level('ki'), 6)
        self.assertIsNone(self.being_def.get_skill_level('astronomy'))
        self.assertEqual(len(self.being_def.states),0)

    def test_set_and_remove_arm(self):
        being = BeingDefinition(obj_type='humanoid', length=6, weight=180, hit_points=50, hit_dice='5d10', 
                 alignment='neutral', armor_class=15, challenge_rating=2, arms={'left': 'dagger', 'right': 'sword'})
        # Test set_arm()
        being.set_arm('head', 'helmet')
        self.assertEqual(being.arms['head'], 'helmet')
        # Test remove_arm()
        removed_weapon = being.remove_arm('left')
        self.assertEqual(removed_weapon, 'dagger')
        self.assertNotIn('left', being.arms)

class TestBeingInstance(unittest.TestCase):
    def setUp(self):
        self.skills_file = '../src/config/skills.tsv'
        self.skill_dictionary = SkillDictionary(self.skills_file)

        self.weapons_file = '../src/config/weapons.tsv'
        self.categories_file = '../src/config/weapon_categories.json'
        self.weapon_dict = WeaponDictionary()
        self.weapon_dict.load_object_categories(self.categories_file)
        self.weapon_dict.load_objects(self.weapons_file)

        self.being_def = BeingDefinition('Human', 6, 170, 7, '2d6', 'Neutral', 10, 1)
        self.being_inst = BeingInstance(self.being_def, name='Tobe')
        self.assertEqual(self.being_inst.possessions, {})
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
        self.assertEqual(len(original_being_state.states),0)

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
        self.assertEqual(current_being_state.states,{})
        self.assertEqual(current_being_state.actions, {})
        self.assertEqual(current_being_state.reactions, {})

    def test_setters_getters(self):
        current_being_state = self.being_inst.current
        original_being_state = self.being_inst.original
        self.being_inst.add_hit_points(-3)
        self.assertEqual(self.being_inst.get_hit_points(), 4)
        self.being_inst.add_experience('50')
        self.assertEqual(self.being_inst.get_experience(), 50)
        self.being_inst.set_skill_level(self.skill_dictionary, 'run', 3)
        self.assertEqual(self.being_inst.get_skill_level('run'), 3)

    def test_states(self):
        current_states = self.being_inst.current.states
        self.assertEqual(current_states, {})
        self.being_inst.un_paralyze()
        self.assertEqual(current_states, {})
        self.being_inst.paralyze()
        self.assertEqual(self.being_inst.is_paralyzed(), True)
        self.being_inst.un_paralyze()
        self.assertEqual(self.being_inst.is_paralyzed(), False)

        self.assertEqual(self.being_inst.is_stunned(), False)
        self.being_inst.stun()
        self.assertEqual(self.being_inst.is_stunned(), True)
        self.being_inst.un_stun()
        self.assertEqual(self.being_inst.is_stunned(), False)
        
        self.assertEqual(self.being_inst.is_paralyzed(), False)
        self.assertEqual(self.being_inst.is_stunned(), False)
        self.assertEqual(self.being_inst.get_hit_points()>0, True)
#        print(f'{self.being_inst.current.states} {self.being_inst.get_abilities()}')
        self.assertEqual(self.being_inst.is_helpless(), False)
        self.being_inst.paralyze()
        self.assertEqual(self.being_inst.is_helpless(), True)
        self.being_inst.un_paralyze()
        self.assertEqual(self.being_inst.is_helpless(), False)
        self.being_inst.stun()
        self.assertEqual(self.being_inst.is_helpless(), True)
        self.being_inst.un_stun()
        self.assertEqual(self.being_inst.is_helpless(), False)
        self.being_inst.set_ability('str', 2)
        self.assertEqual(self.being_inst.is_helpless(), False)
        self.being_inst.set_ability('str', 0)
        self.assertEqual(self.being_inst.is_helpless(), True)
        self.being_inst.set_ability('str', 10)
        self.assertEqual(self.being_inst.is_helpless(), False)

        self.being_inst.set_fatigue_level(5)
        self.assertEqual(self.being_inst.is_helpless(), True)
        self.being_inst.set_fatigue_level(4)
        self.assertEqual(self.being_inst.is_helpless(), False)
        self.being_inst.set_fatigue_level(0)
        self.assertEqual(self.being_inst.is_helpless(), False)

    def test_possible_actions(self):
        action_dict_file = '../src/config/actions.tsv'
        action_dict = ActionDictionary()
        action_dict.load_actions(action_dict_file)

        skill_dict_file = '../src/config/skills.tsv'
        skill_dict = SkillDictionary()
        skill_dict.load_skills(skill_dict_file)
#        print(f'skill dict: {skill_dict.to_json()}')

        self.being_inst.set_skill_level(skill_dict, 'stun', 1)
        self.being_inst.set_skill_level(skill_dict, 'unarmed combat', 2)
        possible_actions = self.being_inst.possible_actions(action_dict)
#        print(f'{possible_actions}')
        self.assertIn('stun', possible_actions)
        self.assertIn('parry unarmed', possible_actions)
        self.assertNotIn('astronomy', possible_actions)
        self.assertNotIn('parry with weapon', possible_actions)
        self.assertEqual(len(possible_actions), 40)
        self.being_inst.set_weapon_skill_level(self.weapon_dict, 'Longsword', 4)
#        print(f'{self.being_inst.get_weapon_skills()}')
        possible_actions = self.being_inst.possible_actions(action_dict)
        self.assertIn('parry with weapon', possible_actions)
        self.assertEqual(len(possible_actions), 43)

    def test_set_arm(self):
        self.assertEqual(self.being_inst.current.arms, {})
        self.being_inst.set_arm("right_arm", "Longsword")
        self.assertEqual(self.being_inst.current.arms, {"right_arm": "Longsword"})
        self.being_inst.set_arm("left_arm", "Small wooden shield")
        self.assertEqual(self.being_inst.current.arms, {"right_arm": "Longsword", "left_arm": "Small wooden shield"})

    def test_currently_possible_actions(self):
        action_dict_file = '../src/config/actions.tsv'
        action_dict = ActionDictionary()
        action_dict.load_actions(action_dict_file)

        skill_dict_file = '../src/config/skills.tsv'
        skill_dict = SkillDictionary()
        skill_dict.load_skills(skill_dict_file)

        weapon_dict_file = '../src/config/weapons.tsv'
        weapon_categories_file = '../src/config/weapon_categories.json'
        weapon_dict = WeaponDictionary()
        weapon_dict.load_objects(weapon_dict_file)
        weapon_dict.load_object_categories(weapon_categories_file)

        possible_actions = self.being_inst.possible_actions(action_dict)
#        print(f'possible: {possible_actions}')
        self.assertNotIn('stun', possible_actions)
        self.assertNotIn('parry unarmed', possible_actions)
        self.assertNotIn('parry with weapon', possible_actions)
        self.assertEqual(len(possible_actions), 34)
        currently_possible = self.being_inst.currently_possible_actions(action_dict, weapon_dict)
        self.assertEqual(len(currently_possible), 2)

        self.being_inst.set_weapon_skill_level(self.weapon_dict, 'Longsword', 4)
        possible_actions = self.being_inst.possible_actions(action_dict)
        self.assertIn('parry with weapon', possible_actions)
        self.assertEqual(len(possible_actions), 37)

        currently_possible = self.being_inst.currently_possible_actions(action_dict, weapon_dict)
        self.assertEqual(len(currently_possible), 2)

        self.assertEqual(self.being_inst.current.arms, {})
        self.being_inst.set_arm("right_arm", "Longsword")
        self.being_inst.set_arm("left_arm", None)
        self.assertEqual(self.being_inst.current.arms, {"right_arm": "Longsword", "left_arm": None})
        currently_possible = self.being_inst.currently_possible_actions(action_dict, weapon_dict)
        self.assertEqual(len(currently_possible), 7)

        self.being_inst.set_skill_level(skill_dict, 'stun', 4)
        possible_actions = self.being_inst.possible_actions(action_dict)
        self.assertIn('stun', possible_actions)
        self.assertNotIn('parry unarmed', possible_actions)
        self.assertIn('parry with weapon', possible_actions)
        self.assertEqual(len(possible_actions), 38)
        currently_possible = self.being_inst.currently_possible_actions(action_dict, weapon_dict)
        self.assertIn('stun', currently_possible)
        self.assertEqual(len(currently_possible), 8)        
        
        self.being_inst.set_hit_points(0)
        currently_possible = self.being_inst.currently_possible_actions(action_dict, weapon_dict)
        self.assertEqual(len(currently_possible), 0)
        
        self.being_inst.set_hit_points(10)
        currently_possible = self.being_inst.currently_possible_actions(action_dict, weapon_dict)
        self.assertEqual(len(currently_possible), 8)
        self.being_inst.set_fatigue_level(5)
        currently_possible = self.being_inst.currently_possible_actions(action_dict, weapon_dict)
        self.assertEqual(len(currently_possible), 0)

        self.being_inst.set_fatigue_level(0)
        currently_possible = self.being_inst.currently_possible_actions(action_dict, weapon_dict)
        self.assertEqual(len(currently_possible), 8)
        self.being_inst.paralyze()
        currently_possible = self.being_inst.currently_possible_actions(action_dict, weapon_dict)
        self.assertEqual(len(currently_possible), 0)
        self.being_inst.un_paralyze()
        currently_possible = self.being_inst.currently_possible_actions(action_dict, weapon_dict)
        self.assertEqual(len(currently_possible), 8)
        self.being_inst.stun()
        currently_possible = self.being_inst.currently_possible_actions(action_dict, weapon_dict)
        self.assertEqual(len(currently_possible), 0)
        self.being_inst.un_stun()
        currently_possible = self.being_inst.currently_possible_actions(action_dict, weapon_dict)
        self.assertEqual(len(currently_possible), 8)
        chosen = self.being_inst.choose_action(action_dict, weapon_dict)
        self.assertIn(chosen, currently_possible)
        print(f'Chose: {chosen}')

    def test_remove_arm(self):
        self.being_inst.current.arms = {"right_arm": "Longsword", "left_arm": "Small wooden shield"}
        self.assertEqual(self.being_inst.current.arms, {"right_arm": "Longsword", "left_arm": "Small wooden shield"})
        removed_weapon = self.being_inst.remove_arm("right_arm")
        self.assertEqual(self.being_inst.current.arms, {"left_arm": "Small wooden shield"})
        self.assertEqual(removed_weapon, "Longsword")
        removed_weapon = self.being_inst.remove_arm("right_arm")
        self.assertEqual(self.being_inst.current.arms, {"left_arm": "Small wooden shield"})
        self.assertIsNone(removed_weapon)

    def test_set_armor(self):
        self.assertIsNone(self.being_inst.current.armor)
        self.being_inst.set_armor("plate armor")
        self.assertEqual(self.being_inst.current.armor, "plate armor")

class TestBeingDictionary(unittest.TestCase):
    def setUp(self):
        pass

        # clean up the file
#        os.remove(filename)

if __name__ == '__main__':
    unittest.main()
