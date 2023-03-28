#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2023 Rauthiflor LLC"
__version__ = "test_weapon.py 2023-03-20T11:31-03:00"

# TODO:

import json
import unittest
import sys
import os

sys.path.insert(0, os.path.abspath('../src'))

from weapon import WeaponInstance, WeaponDefinition, WeaponDictionary

import unittest

class TestWeaponDefinition(unittest.TestCase):
    def setUp(self):
        self.def1 = WeaponDefinition(
            'Longsword', 3.5, 6, 3600, 10, 6, 6, 7, 'P', 6, 8, 'S', 5, 7, 'P', 'M')
        self.def1.set_tag('tag1', 'tag1_value')
        self.def1.set_tag('tag2', 'tag2_value')

    def test_constructor_with_valid_values(self):
        self.assertEqual(self.def1.obj_type, 'Longsword')
        self.assertEqual(self.def1.length, 3.5)
        self.assertEqual(self.def1.width, 0)
        self.assertEqual(self.def1.height, 0)
        self.assertEqual(self.def1.weight, 6)
        self.assertEqual(self.def1.cost, 3600)
        self.assertEqual(self.def1.hardness, 10)
        self.assertEqual(self.def1.hit_points, 6)
        self.assertEqual(self.def1.is_magical, False)
        self.assertDictEqual(self.def1.tags, 
            {'tag1': 'tag1_value', 'tag2': 'tag2_value'})
        self.assertEqual(self.def1.weapon_categories, [])
        self.assertEqual(self.def1.RT(), 6)
        self.assertEqual(self.def1.RD(), 7)
        self.assertEqual(self.def1.RP(), 'P')
        self.assertEqual(self.def1.ST(), 6)
        self.assertEqual(self.def1.SD(), 8)
        self.assertEqual(self.def1.SP(), 'S')
        self.assertEqual(self.def1.TT(), 5)
        self.assertEqual(self.def1.TD(), 7)
        self.assertEqual(self.def1.TP(), 'P')
        self.assertEqual(self.def1.weapon_size, 'M')

    def test_to_json(self):
        json_data = self.def1.to_json()
        self.assertIn('"type": "Longsword"', json_data)
        self.assertIn('"length": 3.5', json_data)
        self.assertIn('"width": 0', json_data)
        self.assertIn('"height": 0', json_data)
        self.assertIn('"weight": 6', json_data)
        self.assertIn('"cost": 3600', json_data)
        self.assertIn('"hardness": 10', json_data)
        self.assertIn('"hit_points": 6', json_data)
        self.assertIn('"is_magical": false', json_data)
        t = '{"tag1": "tag1_value", "tag2": "tag2_value"}'
        tags = f'"tags": {t}'
        self.assertIn(tags, json_data)
        self.assertIn('"weapon_categories": []', json_data)
        self.assertIn('"weapon_size": "M"', json_data)

class TestWeaponInstance(unittest.TestCase):
    def setUp(self):
        self.def1 = WeaponDefinition(
            'Longsword', 3.5, 6, 3600, 10, 6, 6, 7, 'P', 6, 8, 'S', 5, 7, 'P', 'M')
        self.def1.set_tag('tag1', 'tag1_value')
        self.def1.set_tag('tag2', 'tag2_value')
        self.weapon_inst = WeaponInstance(self.def1, 'Nail biter')

    def test_weapon_instance_creation(self):
        self.assertEqual(self.weapon_inst.type, 'WeaponInstance')
        self.assertEqual(self.weapon_inst.name, 'Nail biter')
        self.assertEqual(self.weapon_inst.current.obj_type, 'Longsword')
        self.assertEqual(self.weapon_inst.current.weight, 6)
        self.assertEqual(self.weapon_inst.current.cost, 3600)
        self.assertEqual(self.weapon_inst.current.length, 3.5)
        self.assertEqual(self.weapon_inst.current.width, 0)
        self.assertEqual(self.weapon_inst.current.height, 0)
        self.assertEqual(self.weapon_inst.current.hardness, 10)
        self.assertEqual(self.weapon_inst.current.hit_points, 6)
        self.assertEqual(self.weapon_inst.current.RT(), 6)
        self.assertEqual(self.weapon_inst.current.RD(), 7)
        self.assertEqual(self.weapon_inst.current.RP(), 'P')
        self.assertEqual(self.weapon_inst.current.ST(), 6)
        self.assertEqual(self.weapon_inst.current.SD(), 8)
        self.assertEqual(self.weapon_inst.current.SP(), 'S')
        self.assertEqual(self.weapon_inst.current.TT(), 5)
        self.assertEqual(self.weapon_inst.current.TD(), 7)
        self.assertEqual(self.weapon_inst.current.TP(), 'P')
        self.assertEqual(self.weapon_inst.current.weapon_size, 'M')
        self.assertDictEqual(self.weapon_inst.current.tags, 
            {'tag1': 'tag1_value', 'tag2': 'tag2_value'})
        self.assertEqual(self.weapon_inst.current.is_magical, False)
        self.assertEqual(self.weapon_inst.current.weapon_categories, [])

    def test_set_weapon_size(self):
        original_weapon_size = self.weapon_inst.original.weapon_size
        self.weapon_inst.set_weapon_size('L')
        self.assertEqual(self.weapon_inst.original.weapon_size, original_weapon_size)
        self.assertEqual(self.weapon_inst.current.weapon_size, 'L')

    def test_set_attacks(self):
        original_attacks = self.weapon_inst.original.attacks
        new_attacks = {'R': {'T': 6, 'D': 5, 'P': 'P'},
                    'S': {'T': 6, 'D': 5, 'P': 'B'},
                    'T': {'T': 4, 'D': 3, 'P': 'P'}}
        self.weapon_inst.set_attacks(new_attacks)
        self.assertDictEqual(self.weapon_inst.original.attacks, original_attacks)
        self.assertDictEqual(self.weapon_inst.current.attacks, new_attacks)

    def test_modify_attacks(self):
        original_attacks = self.weapon_inst.original.attacks
        current_attacks_before = self.weapon_inst.original.attacks
        attack_modifications = {'R': {'T': 0, 'D': -1, 'P': 'P'},
                    'S': {'T': 1, 'D': 0, 'P': 'B'},
                    'T': {'T': -1, 'D': 1, 'P': 'P'}}
        self.weapon_inst.modify_attacks(attack_modifications)
        self.assertDictEqual(self.weapon_inst.original.attacks, original_attacks)
        self.assertEqual(self.weapon_inst.current.RT(),6)
        self.assertEqual(self.weapon_inst.current.RD(),6)
        self.assertEqual(self.weapon_inst.current.RP(),'P')
        self.assertEqual(self.weapon_inst.current.ST(),7)
        self.assertEqual(self.weapon_inst.current.SD(),8)
        self.assertEqual(self.weapon_inst.current.SP(),'S')
        self.assertEqual(self.weapon_inst.current.TT(),4)
        self.assertEqual(self.weapon_inst.current.TD(),8)
        self.assertEqual(self.weapon_inst.current.TP(),'P')

class TestWeaponDictionary(unittest.TestCase):
    def setUp(self):
        self.weapons_file = '../src/config/weapons.tsv'
        self.categories_file = '../src/config/weapon_categories.json'
        self.weapon_dict = WeaponDictionary()
        self.expected_categories = {
    "Axes": [
        "Battleaxe", "Bardiche", "Bec de corbin", "Greataxe", "Guisarme-voulge", 
        "Halberd", "Handaxe", "Lochaber axe", "Tomahawk", "Voulge"
    ],
    "Bows": [
        "Shortbow", "Pelletbow", "Longbow", "Composite shortbow", "Composite longbow",
        "Hand crossbow", "Light crossbow", "Heavy crossbow", "Repeating crossbow", 
        "Ballista"
    ],
    "Catapults": [
        "Light catapult", "Heavy catapult", "Trebuchet"
    ],
    "Clubs": [
        "Bo stick", "Club", "Greatclub", "Jo stick", "Kiseru", "Heavy mace", "Light mace",
        "Morningstar", "Tetsubo"
    ],
    "Entanglers": [
        "Bola", "Chain", "Chijiriki", "Hooked net", "Kawanaga", "Kusari-gama", "Lasso", 
        "Net", "Spiked chain", "Whip"
    ],
    "Flails": [
        "Heavy flail", "Light flail", "Kau sin ke", "Kusari-gama", "Nunchaku",
        "Sap (Blackjack)", "Scourge", "Three-piece staff"
    ],
    "Hammers": [
        "Fang", "Hammer", "Lucern hammer", "Heavy pick", "Light pick", "Warhammer"
    ],
    "Hand Weapons": [
        "Dagger", "Punching dagger (Katar)", "Gauntlet", "Locked gauntlet", 
        "Spiked gauntlet", "Knife", "Kukri", "Needle (Pin)", "Nekode", "Sai (Jitte)", 
        "Siangham", "Stone", "Uichi-ne"
    ],
    "Lances": [
        "Heavy lance", "Light lance", "Medium lance"
    ],
    "Rams": [
        "Portable ram", "Six-person ram", "Suspended ram"
    ],
    "Scythes": [
        "Battle scythe", "Fauchard", "Fauchard-fork", "Glaive", "Glaive-guisarme",
        "Guisarme (Bill hook)", "Guisarme-voulge", "Hook fauchard", "Kama (Sickle)",
        "Kusari-gama", "Nagimaki", "Naginata"
    ],
    "Shields": [
        "Wooden buckler", "Buckler", "Small wooden shield", "Small shield", 
        "Medium wooden shield", "Medium shield", "Large wooden shield", "Large shield", 
        "Tower shield", "Spiked wooden buckler", "Spiked buckler", 
        "Spiked small wooden shield", "Spiked small shield", 
        "Spiked medium wooden shield", "Spiked medium shield", 
        "Spiked large wooden shield", "Spiked large shield", "Spiked tower shield"
    ],
    "Slings": [
        "Sling", "Staff-sling"
    ],
    "Spears": [
        "Bec de corbin", "Chijiriki", "Fauchard-fork", "Halfspear", "Harpoon", 
        "Hook fauchard", "Javelin", "Kumade", "Military fork", "Partisan", "Pike", 
        "Ranseur", "Spear", "Spetum", "Trident"
    ],
    "Special": [
        "Aklys", "Armor spike", "Atlatl", "Blowgun", "Caltrops (Tetsu-bishi)", "Garrote", 
        "Lajatang", "Man catcher"
    ], 
    "Staves": [
        "Bo stick", "Nunchaku", "Quarterstaff", "Staff-sling", "Three-piece staff"
    ],
    "Swords": [
        "Bastard sword", "Broadsword", "Falchion", "Greatsword (2-handed)", "Katana", 
        "Longsword", "Machete (Parang)", "Rapier", "Scimitar", "Short sword", "Wakizashi"
    ], 
    "Thrown": [
        "Boomerang", "Chakram", "Dagger", "Dart", "Javelin", "Knife", "Needle (Pin)", 
        "Shuriken", "Stone", "Uichi-ne"
    ], 
    "Unarmed": [
        "Arm", "Leg", "Gauntlet", "Locked gauntlet", "Spiked gauntlet", "Nekode", "Stone"
    ]
}
    def test_load_object_categories(self):
        self.weapon_dict.load_object_categories(self.categories_file)
        self.assertEqual(len(self.weapon_dict.object_categories), 19)
        self.assertDictEqual(self.weapon_dict.object_categories, self.expected_categories)

    def test_load_objects(self):
        self.weapon_dict.load_objects(self.weapons_file)
        self.assertEqual(len(self.weapon_dict.objects), 141)
        for weapon in self.weapon_dict.objects:
            weapon_dict = self.weapon_dict.objects[weapon]
            self.assertIsInstance(weapon_dict, WeaponDefinition)
        weapon = self.weapon_dict.objects['Aklys']
        self.assertEqual(weapon.obj_type, 'Aklys')
        self.assertEqual(weapon.cost, 400)
        self.assertEqual(weapon.weight, 3.5)
        self.assertEqual(weapon.length, 2)
        self.assertDictEqual(weapon.attacks, {'R': {'T': 6, 'D': 5, 'P': 'P'},
                                              'S': {'T': 6, 'D': 5, 'P': 'B'},
                                              'T': {'T': 4, 'D': 3, 'P': 'P'}})
        self.assertEqual(weapon.hardness, 5)
        self.assertEqual(weapon.hit_points, 2)
        self.assertEqual(weapon.weapon_size, 'S')

    def test_all_weapons_in_categories(self):
        self.weapon_dict.load_object_categories(self.categories_file)
        self.weapon_dict.load_objects(self.weapons_file)
        for weapon in self.weapon_dict.objects:
            weapon_dict = self.weapon_dict.objects[weapon]
            found = False
            for category in self.weapon_dict.object_categories.values():
                if weapon_dict.obj_type in category:
                    found = True
                    break
            self.assertTrue(found, f"WeaponDefinition {weapon} with name {weapon_dict.obj_type} not found in any weapon category")
    
    def test_all_categories_in_weapons(self):
        self.weapon_dict.load_object_categories(self.categories_file)
        self.weapon_dict.load_objects(self.weapons_file)
        for category_name, category in self.weapon_dict.object_categories.items():
            for weapon_name in category:
                self.assertIn(weapon_name, self.weapon_dict.objects, 
                              f"WeaponDefinition {weapon_name} in category {category_name} not found in weapons list")

if __name__ == '__main__':
    unittest.main()
