#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2023 Rauthiflor LLC"
__version__ = "test_armor.py 2023-05-20T20:22-03:00"

# TODO: Check comprehensiveness

import json
import unittest
import sys
import os

sys.path.insert(0, os.path.abspath('../src'))

from armor import ArmorInstance, ArmorDefinition, ArmorDictionary
from weapon import WeaponInstance, WeaponDefinition

class TestArmorDefinition(unittest.TestCase):
    def setUp(self):
        self.def1 = ArmorDefinition('Cold clothing', 1780, 8, 3, 5, 0, 0, 0, 0, 0, 0, 5)
        self.def1.set_tag('tag1', 'tag1_value')
        self.def1.set_tag('tag2', 'tag2_value')

    def test_constructor_with_valid_values(self):
        self.assertEqual(self.def1.obj_type, 'Cold clothing')
        self.assertEqual(self.def1.cost, 1780)
        self.assertEqual(self.def1.weight, 8)
        self.assertEqual(self.def1.Bh(), 3)
        self.assertEqual(self.def1.Ph(), 5)
        self.assertEqual(self.def1.Sh(), 0)
        self.assertEqual(self.def1.Bd(), 0)
        self.assertEqual(self.def1.Pd(), 0)
        self.assertEqual(self.def1.Sd(), 0)
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
        very_cold_clothing_def = ArmorDefinition('Very cold clothing', 2880, 20, 5, 6, 0, 1, 0, 1, 1, -1, 10)
        very_cold_clothing_def.set_tag('tag1', 'tag1_value')
        very_cold_clothing_def.set_tag('tag2', 'tag2_value')
        self.very_cold_clothing = ArmorInstance(very_cold_clothing_def, 'Cuddles')

        chain_mail_def = ArmorDefinition('Chain mail', 30000, 40, 7, 6, 5, 3, 2, 5, 5, -1, 80)
        self.chain_mail = ArmorInstance(chain_mail_def, 'Chainy')

        battleaxe_def = WeaponDefinition(
            'Battleaxe', 4, 7, 1000, 10, 6, 6, 7, 'B,S', 6, 8, 'B,S', 5, 4, 'B,P', 'M')
        self.battleaxe = WeaponInstance(battleaxe_def, 'Nail biter')

        spear_def = WeaponDefinition(
            'Spear', 7, 4, 200, 5, 5, 5, 5, 'P', 5, 4, 'P,S', 4, 5, 'P', 'M')
        self.spear = WeaponInstance(spear_def, 'Pokey')

    def test_armor_armor_inst_creation(self):
        self.assertEqual(self.very_cold_clothing.type, 'ArmorInstance')
        self.assertEqual(self.very_cold_clothing.name, 'Cuddles')
        self.assertEqual(self.very_cold_clothing.current.obj_type, 'Very cold clothing')
        self.assertEqual(self.very_cold_clothing.current.weight, 20)
        self.assertEqual(self.very_cold_clothing.current.Bh(), 5)
        self.assertEqual(self.very_cold_clothing.current.Ph(), 6)
        self.assertEqual(self.very_cold_clothing.current.Sh(), 0)
        self.assertEqual(self.very_cold_clothing.current.Bd(), 1)
        self.assertEqual(self.very_cold_clothing.current.Pd(), 0)
        self.assertEqual(self.very_cold_clothing.current.Sd(), 1)
        self.assertEqual(self.very_cold_clothing.current.armor_check_penalty, 1)
        self.assertEqual(self.very_cold_clothing.current.dexterity_check_penalty, -1)
        self.assertEqual(self.very_cold_clothing.current.hit_points, 10)
        self.assertEqual(self.very_cold_clothing.current.length, 0)
        self.assertEqual(self.very_cold_clothing.current.width, 0)
        self.assertEqual(self.very_cold_clothing.current.height, 0)
        self.assertEqual(self.very_cold_clothing.current.is_magical, False)
        self.assertDictEqual(self.very_cold_clothing.current.tags, 
            {'tag1': 'tag1_value', 'tag2': 'tag2_value'})
        self.assertEqual(self.very_cold_clothing.current.weapon_categories, [])

        self.assertEqual(self.chain_mail.type, 'ArmorInstance')
        self.assertEqual(self.chain_mail.name, 'Chainy')
        self.assertEqual(self.chain_mail.current.obj_type, 'Chain mail')
        self.assertEqual(self.chain_mail.current.weight, 40)
        self.assertEqual(self.chain_mail.current.Bh(), 7)
        self.assertEqual(self.chain_mail.current.Ph(), 6)
        self.assertEqual(self.chain_mail.current.Sh(), 5)
        self.assertEqual(self.chain_mail.current.Bd(), 3)
        self.assertEqual(self.chain_mail.current.Pd(), 2)
        self.assertEqual(self.chain_mail.current.Sd(), 5)
        self.assertEqual(self.chain_mail.current.armor_check_penalty, 5)
        self.assertEqual(self.chain_mail.current.dexterity_check_penalty, -1)
        self.assertEqual(self.chain_mail.current.hit_points, 80)
        self.assertEqual(self.chain_mail.current.length, 0)
        self.assertEqual(self.chain_mail.current.width, 0)
        self.assertEqual(self.chain_mail.current.height, 0)
        self.assertEqual(self.chain_mail.current.is_magical, False)
        self.assertEqual(self.chain_mail.current.weapon_categories, [])

    def test_set_armor_check_penalty(self):
        original_armor_check_penalty = self.very_cold_clothing.original.armor_check_penalty
        self.very_cold_clothing.set_armor_check_penalty('3')
        self.assertEqual(self.very_cold_clothing.original.armor_check_penalty, original_armor_check_penalty)
        self.assertEqual(self.very_cold_clothing.current.armor_check_penalty, 3)

    def test_set_dexterity_check_penalty(self):
        original_dexterity_check_penalty = self.very_cold_clothing.original.dexterity_check_penalty
        self.very_cold_clothing.set_dexterity_check_penalty('-1')
        self.assertEqual(self.very_cold_clothing.original.dexterity_check_penalty, original_dexterity_check_penalty)
        self.assertEqual(self.very_cold_clothing.current.dexterity_check_penalty, -1)

    def test_set_defenses(self):
        original_defenses = self.very_cold_clothing.original.defenses
        new_defenses = {
            'H': {'B': 1, 'P': 2, 'S': 3},
            'D': {'B': 3, 'P': 2, 'S': 1}}
        new_defenses = {
            'B': {'h': 1, 'd': 3},
            'P': {'h': 2, 'd': 2},
            'S': {'h': 3, 'd': 1}}
        self.very_cold_clothing.set_defenses(new_defenses)
        self.assertDictEqual(self.very_cold_clothing.original.defenses, original_defenses)
        self.assertDictEqual(self.very_cold_clothing.current.defenses, new_defenses)

    def test_Bh(self):
        # Test that Bh method returns correct value
        self.assertEqual(self.very_cold_clothing.Bh(), 5)

    def test_Ph(self):
        # Test that Ph method returns correct value
        self.assertEqual(self.very_cold_clothing.Ph(), 6)

    def test_Sh(self):
        # Test that Sh method returns correct value
        self.assertEqual(self.very_cold_clothing.Sh(), 0)

    def test_Bd(self):
        # Test that Bd method returns correct value
        self.assertEqual(self.very_cold_clothing.Bd(), 1)

    def test_Pd(self):
        # Test that Pd method returns correct value
        self.assertEqual(self.very_cold_clothing.Pd(), 0)

    def test_Sd(self):
        # Test that Sd method returns correct value
        self.assertEqual(self.very_cold_clothing.Sd(), 1)

    def test_worst_defense_damage_stopped(self):
        test_damage_stopped = self.very_cold_clothing.worst_defense_hardness('B,P,S')
        self.assertEqual(test_damage_stopped, 0)

    def test_worst_defense_hardness(self):
        test_defense_hardness = self.very_cold_clothing.worst_defense_hardness("B,P,S")
        self.assertEqual(test_defense_hardness, 0)

        test_defense_hardness = self.very_cold_clothing.worst_defense_hardness("B,P")
        self.assertEqual(test_defense_hardness, 5)

        test_defense_hardness = self.very_cold_clothing.worst_defense_hardness("B,S")
        self.assertEqual(test_defense_hardness, 0)

        test_defense_hardness = self.very_cold_clothing.worst_defense_hardness("P,S")
        self.assertEqual(test_defense_hardness, 0)

        test_defense_hardness = self.very_cold_clothing.worst_defense_hardness("B")
        self.assertEqual(test_defense_hardness, 5)

        test_defense_hardness = self.very_cold_clothing.worst_defense_hardness("P")
        self.assertEqual(test_defense_hardness, 6)

        test_defense_hardness = self.very_cold_clothing.worst_defense_hardness("S")
        self.assertEqual(test_defense_hardness, 0)

    def test_damage_through(self):
        attack_type = 'swing'
        damage = 0
        weapon = self.battleaxe
        test_damage_through = self.very_cold_clothing.damage_through(damage, weapon, attack_type)
        self.assertEqual(test_damage_through, 0)

        test_damage_through = self.chain_mail.damage_through(damage, weapon, attack_type)
        self.assertEqual(test_damage_through, 0)

        damage = 10
        test_damage_through = self.very_cold_clothing.damage_through(damage, weapon, attack_type)
        self.assertEqual(test_damage_through, 9)

        test_damage_through = self.chain_mail.damage_through(damage, weapon, attack_type)
        self.assertEqual(test_damage_through, 7)

        weapon = self.spear
        test_damage_through = self.very_cold_clothing.damage_through(damage, weapon, attack_type)
        self.assertEqual(test_damage_through, 10)

        test_damage_through = self.chain_mail.damage_through(damage, weapon, attack_type)
        self.assertEqual(test_damage_through, 8)

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

    def test_worst_defense(self):
        armor_dict = ArmorDictionary()
        armor_dict.load_objects(self.armors_file)
        for armor in armor_dict.objects:
            a = ArmorInstance(armor_dict.objects[armor], armor)	
            self.assertGreater(len(a.worst_defense()), 0) 
#            print(f'armor: {a.to_json()}')
#            print(f'armor: {a.name}')
#            print(f'worst_damage_stopped: {a.worst_defense_damage_stopped("B,P,S")}')
#            print(f'worst_defenses: {a.worst_defense()}')

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
        self.assertEqual(armor.Bh(), 0)
        self.assertEqual(armor.Ph(), 0)
        self.assertEqual(armor.Sh(), 0)
        self.assertEqual(armor.Bd(), 0)
        self.assertEqual(armor.Pd(), 0)
        self.assertEqual(armor.Sd(), 0)
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
