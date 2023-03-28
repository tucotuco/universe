#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2023 Rauthiflor LLC"
__version__ = "test_armor.py 2023-03-20T18:57-03:00"

# TODO:

import json
import unittest
import sys
import os

sys.path.insert(0, os.path.abspath('../src'))

from armor import ArmorInstance, ArmorDefinition, ArmorDictionary

class TestArmorDefinition(unittest.TestCase):
    def setUp(self):
        self.def1 = ArmorDefinition('Cold clothing', 1780, 8, 3, 5, 0, 0, 0, 0, 0, 0, 5)
        self.def1.set_tag('tag1', 'tag1_value')
        self.def1.set_tag('tag2', 'tag2_value')

    def test_constructor_with_valid_values(self):
        self.assertEqual(self.def1.obj_type, 'Cold clothing')
        self.assertEqual(self.def1.cost, 1780)
        self.assertEqual(self.def1.weight, 8)
        self.assertEqual(self.def1.HB(), 3)
        self.assertEqual(self.def1.HP(), 5)
        self.assertEqual(self.def1.HS(), 0)
        self.assertEqual(self.def1.DB(), 0)
        self.assertEqual(self.def1.DP(), 0)
        self.assertEqual(self.def1.DS(), 0)
        self.assertEqual(self.def1.armor_check_penalty, 0)
        self.assertEqual(self.def1.dexterity_check_penalty, 0)
        self.assertEqual(self.def1.hit_points, 5)
        self.assertEqual(self.def1.is_magical, False)
        self.assertEqual(self.def1.length, 0)
        self.assertEqual(self.def1.width, 0)
        self.assertEqual(self.def1.height, 0)
        self.assertEqual(self.def1.hardness, 0)
        self.assertDictEqual(self.def1.tags, 
            {'tag1': 'tag1_value', 'tag2': 'tag2_value'})
        self.assertEqual(self.def1.weapon_categories, [])

    def test_to_json(self):
        json_data = self.def1.to_json()
        self.assertIn('"type": "Cold clothing"', json_data)
        self.assertIn('"length": 0', json_data)
        self.assertIn('"width": 0', json_data)
        self.assertIn('"height": 0', json_data)
        self.assertIn('"weight": 8', json_data)
        self.assertIn('"cost": 1780', json_data)
        self.assertIn('"hardness": 0', json_data)
        self.assertIn('"hit_points": 5', json_data)
        self.assertIn('"is_magical": false', json_data)
        t = '{"tag1": "tag1_value", "tag2": "tag2_value"}'
        tags = f'"tags": {t}'
        self.assertIn(tags, json_data)
        self.assertIn('"weapon_categories": []', json_data)

class TestArmorInstance(unittest.TestCase):
    def setUp(self):
        self.armor_def = ArmorDefinition('Cold clothing', 1780, 8, 3, 5, 0, 0, 0, 0, 0, 0, 5)
        self.armor_def.set_tag('tag1', 'tag1_value')
        self.armor_def.set_tag('tag2', 'tag2_value')
        self.armor_inst = ArmorInstance(self.armor_def, 'Cuddles')

    def test_armor_instance_creation(self):
        self.assertEqual(self.armor_inst.type, 'ArmorInstance')
        self.assertEqual(self.armor_inst.name, 'Cuddles')
        self.assertEqual(self.armor_inst.current.obj_type, 'Cold clothing')
        self.assertEqual(self.armor_inst.current.weight, 8)
        self.assertEqual(self.armor_inst.current.HB(), 3)
        self.assertEqual(self.armor_inst.current.HP(), 5)
        self.assertEqual(self.armor_inst.current.HS(), 0)
        self.assertEqual(self.armor_inst.current.DB(), 0)
        self.assertEqual(self.armor_inst.current.DP(), 0)
        self.assertEqual(self.armor_inst.current.DS(), 0)
        self.assertEqual(self.armor_inst.current.armor_check_penalty, 0)
        self.assertEqual(self.armor_inst.current.dexterity_check_penalty, 0)
        self.assertEqual(self.armor_inst.current.hit_points, 5)
        self.assertEqual(self.armor_inst.current.length, 0)
        self.assertEqual(self.armor_inst.current.width, 0)
        self.assertEqual(self.armor_inst.current.height, 0)
        self.assertEqual(self.armor_inst.current.is_magical, False)
        self.assertDictEqual(self.armor_inst.current.tags, 
            {'tag1': 'tag1_value', 'tag2': 'tag2_value'})
        self.assertEqual(self.armor_inst.current.is_magical, False)
        self.assertEqual(self.armor_inst.current.weapon_categories, [])

    def test_set_armor_check_penalty(self):
        original_armor_check_penalty = self.armor_inst.original.armor_check_penalty
        self.armor_inst.set_armor_check_penalty('3')
        self.assertEqual(self.armor_inst.original.armor_check_penalty, original_armor_check_penalty)
        self.assertEqual(self.armor_inst.current.armor_check_penalty, 3)

    def test_set_dexterity_check_penalty(self):
        original_dexterity_check_penalty = self.armor_inst.original.dexterity_check_penalty
        self.armor_inst.set_dexterity_check_penalty('-1')
        self.assertEqual(self.armor_inst.original.dexterity_check_penalty, original_dexterity_check_penalty)
        self.assertEqual(self.armor_inst.current.dexterity_check_penalty, -1)

    def test_set_defenses(self):
        original_defenses = self.armor_inst.original.defenses
        new_defenses = {
            'H': {'B': 1, 'P': 2, 'S': 3},
            'D': {'B': 3, 'P': 2, 'S': 1}}
        self.armor_inst.set_defenses(new_defenses)
        self.assertDictEqual(self.armor_inst.original.defenses, original_defenses)
        self.assertDictEqual(self.armor_inst.current.defenses, new_defenses)

    def test_modify_defenses(self):
        original_defenses = self.armor_inst.original.defenses
        current_defenses_before = self.armor_inst.original.defenses
        defense_modifications = {
            'H': {'B': -1, 'P': 0, 'S': 1},
            'D': {'B': 1, 'P': -1, 'S': 0}}
        self.armor_inst.modify_defenses(defense_modifications)
        self.assertDictEqual(self.armor_inst.original.defenses, original_defenses)
        self.assertEqual(self.armor_inst.current.HB(),2)
        self.assertEqual(self.armor_inst.current.HP(),5)
        self.assertEqual(self.armor_inst.current.HS(),1)
        self.assertEqual(self.armor_inst.current.DB(),1)
        self.assertEqual(self.armor_inst.current.DP(),0)
        self.assertEqual(self.armor_inst.current.DS(),0)

class TestArmorDictionary(unittest.TestCase):
    def setUp(self):
        self.armors_file = '../src/config/armors.tsv'
        self.categories_file = '../src/config/armor_categories.json'
        self.dictionary = ArmorDictionary()
        self.expected_categories = {
    "Accessories": [
        "Gauntlet", "Locked gauntlet", "Spiked gauntlet"
    ],
    "Clothing": [
        "No armor", "Normal clothing", "Cold clothing", "Very cold clothing"
    ],
    "Light armor": [
        "Padded armor", "Leather armor", "Studded leather armor",  "Ring mail", 
        "Chain shirt"
    ],
    "Medium armor": [
        "Hide", "Scale mail", "Brigandine armor", "Chain mail", "Breastplate"
    ],
    "Heavy armor": [
        "Banded armor", "Half-plate armor", "Full plate armor"
    ]
}

    def test_load_armor_categories(self):
        self.dictionary.load_object_categories(self.categories_file)
        self.assertEqual(len(self.dictionary.object_categories), 5)
        self.assertDictEqual(self.dictionary.object_categories, self.expected_categories)

    def test_load_armors(self):
        self.dictionary.load_objects(self.armors_file)
        self.assertEqual(len(self.dictionary.objects), 20)
        for armor in self.dictionary.objects:
            armor_dict = self.dictionary.objects[armor]
            self.assertIsInstance(armor_dict, ArmorDefinition)
        armor = self.dictionary.objects['No armor']
        self.assertEqual(armor.obj_type, 'No armor')
        self.assertEqual(armor.cost, 0)
        self.assertEqual(armor.weight, 0)
        self.assertEqual(armor.HB(), 0)
        self.assertEqual(armor.HP(), 0)
        self.assertEqual(armor.HS(), 0)
        self.assertEqual(armor.DB(), 0)
        self.assertEqual(armor.DP(), 0)
        self.assertEqual(armor.DS(), 0)
        self.assertEqual(armor.hit_points, 0)
        self.assertEqual(armor.length, 0)
        self.assertEqual(armor.width, 0)
        self.assertEqual(armor.height, 0)

    def test_all_armors_in_categories(self):
        self.dictionary.load_object_categories(self.categories_file)
        self.dictionary.load_objects(self.armors_file)
        for armor in self.dictionary.objects:
            armor_dict = self.dictionary.objects[armor]
            found = False
            for category in self.dictionary.object_categories.values():
                if armor_dict.obj_type in category:
                    found = True
                    break
            self.assertTrue(found, f"ArmorDefinition {armor} with name {armor_dict.obj_type} not found in any armor category")
    
    def test_all_categories_in_armors(self):
        self.dictionary.load_object_categories(self.categories_file)
        self.dictionary.load_objects(self.armors_file)
        for category_name, category in self.dictionary.object_categories.items():
            for armor_name in category:
                self.assertIn(armor_name, self.dictionary.objects, 
                              f"ArmorDefinition {armor_name} in category {category_name} not found in armors list")

#    def test_show_armordict(self):
#        self.dictionary.load_armor_categories(self.categories_file)
#        self.dictionary.load_armors(self.armors_file)
#        print(f'{self.dictionary.to_json()}')

if __name__ == '__main__':
    unittest.main()
