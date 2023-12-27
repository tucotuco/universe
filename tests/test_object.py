#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2023 Rauthiflor LLC"
__version__ = "test_object.py 2023-12-26T17:00-03:00"

# TODO: Check comprehensiveness
# TODO: Make sure an ObjectInstance is inside one and only one ObjectInstance as it's immediate container

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath('../src'))
#print(f'{__version__}:{sys.path}')

from object import ObjectInstance, ObjectDefinition, ObjectDictionary, ObjectRegistry

import unittest

class TestObjectDefinition(unittest.TestCase):
    def setUp(self):
        self.apple_def = ObjectDefinition('Sword', '3', '0.16', '0.5', '2.5', '50', 10, 20)
        tags = {'tag1': 'tag1_value', 'tag2': 'tag2_value'}
        self.apple_def.set_tags(tags)
        self.def2 = ObjectDefinition('Sword', 3, 0.16, 0.5, 2.5, 50, 10, 20)
        self.def2.set_tag('tag1', 'tag1_value')
        self.def2.set_tag('tag2', 'tag2_value')

    def test_constructor_with_valid_values(self):
        self.assertEqual(self.apple_def.obj_type, 'Sword')
        self.assertEqual(self.apple_def.length, 3)
        self.assertEqual(self.apple_def.width, 0.16)
        self.assertEqual(self.apple_def.height, 0.5)
        self.assertEqual(self.apple_def.weight, 2.5)
        self.assertEqual(self.apple_def.cost, 50)
        self.assertEqual(self.apple_def.hardness, 10)
        self.assertEqual(self.apple_def.hit_points, 20)
        self.assertEqual(self.apple_def.is_magical, False)
        self.assertEqual(self.apple_def.tags, {'tag1': 'tag1_value', 'tag2': 'tag2_value'})
        self.assertEqual(self.apple_def.weapon_categories, [])

        self.assertEqual(self.def2.obj_type, 'Sword')
        self.assertEqual(self.def2.length, 3)
        self.assertEqual(self.def2.width, 0.16)
        self.assertEqual(self.def2.height, 0.5)
        self.assertEqual(self.def2.weight, 2.5)
        self.assertEqual(self.def2.cost, 50)
        self.assertEqual(self.def2.hardness, 10)
        self.assertEqual(self.def2.hit_points, 20)
        self.assertEqual(self.def2.is_magical, False)
        self.assertEqual(self.def2.tags, {'tag1': 'tag1_value', 'tag2': 'tag2_value'})
        self.assertEqual(self.def2.weapon_categories, [])
        
    def test_get_tag(self):
        tags = {'tag1': 'tag1_value', 'tag2': 'tag2_value'}
        self.apple_def.set_tags(tags)
        self.assertEqual(self.apple_def.tag('tag1'), 'tag1_value')
        self.assertEqual(self.apple_def.tag('tag2'), 'tag2_value')
        self.assertEqual(self.apple_def.tag('missing_tage'), None)

    def test_set_tag(self):
        tags = {'tag1': 'tag1_value', 'tag2': 'tag2_value'}
        self.apple_def.set_tags(tags)
        self.apple_def.set_tag('weapon', 'melee')
        self.assertEqual(self.apple_def.tags, {'tag1': 'tag1_value', 'tag2': 'tag2_value', 'weapon': 'melee'})
        self.apple_def.set_tag('creator', 'Tobe')
        self.assertEqual(self.apple_def.tags, {'tag1': 'tag1_value', 'tag2': 'tag2_value', 'weapon': 'melee', 'creator': 'Tobe'})
        self.apple_def.set_tag('weapon', 'ranged')
        self.assertEqual(self.apple_def.tags, {'tag1': 'tag1_value', 'tag2': 'tag2_value', 'weapon': 'ranged', 'creator': 'Tobe'})
    
    def test_set_tags(self):
        self.apple_def.set_tags({'weapon': 'melee'})
        self.assertEqual(self.apple_def.tags, {'weapon': 'melee'})
        self.apple_def.set_tags({'creator': 'Tobe'})
        self.assertEqual(self.apple_def.tags, {'creator': 'Tobe'})

    def test_set_weapon_categories(self):
        self.apple_def.set_weapon_categories(['Staves', 'Hand'])
        self.assertEqual(self.apple_def.weapon_categories, ['Staves', 'Hand'])
    
    def test_add_weapon_category(self):
        self.apple_def.add_weapon_category('Staves')
        self.assertEqual(self.apple_def.weapon_categories, ['Staves'])
        self.apple_def.add_weapon_category('Hand')
        self.assertEqual(self.apple_def.weapon_categories, ['Staves', 'Hand'])

    def test_to_json(self):
        tags = {'tag1': 'tag1_value', 'tag2': 'tag2_value'}
        self.apple_def.set_tags(tags)
        json_data = self.apple_def.to_json()
        self.assertIn('"type": "Sword"', json_data)
        self.assertIn('"length": 3', json_data)
        self.assertIn('"width": 0.16', json_data)
        self.assertIn('"height": 0.5', json_data)
        self.assertIn('"weight": 2.5', json_data)
        self.assertIn('"cost": 50', json_data)
        self.assertIn('"hardness": 10', json_data)
        self.assertIn('"hit_points": 20', json_data)
        self.assertIn('"is_magical": false', json_data)
        self.assertIn('"tags": {"tag1": "tag1_value", "tag2": "tag2_value"}', json_data)
        self.assertIn('"weapon_categories": []', json_data)

class TestObjectInstance(unittest.TestCase):
#    def __init__(self, name, length, width, height, weight, cost, hardness, hit_points, 
#                 is_magical = False, tags = None, weapon_categories = None):
    def setUp(self):
        self.apple_def = ObjectDefinition('An apple', '3', '0.16', '0.5', '2.5', '50', 10, 20)
        self.apple_inst = ObjectInstance(self.apple_def, 'This apple')
        self.backpack_def = ObjectDefinition('A backpack', 3.1, 0.2, 0.6, 1.5, 30, 5, 5)
        self.backpack_inst = ObjectInstance(self.backpack_def, 'This backpack')
    
    def test_object_instance_creation(self):
        self.assertEqual(self.apple_inst.type, 'ObjectInstance')
        self.assertEqual(self.apple_inst.name, 'This apple')
        self.assertEqual(self.apple_inst.current.obj_type, 'An apple')
        self.assertEqual(self.apple_inst.current.weight, 2.5)
        self.assertEqual(self.apple_inst.current.cost, 50)
        self.assertEqual(self.apple_inst.current.length, 3)
        self.assertEqual(self.apple_inst.current.width, 0.16)
        self.assertEqual(self.apple_inst.current.height, 0.5)
        self.assertEqual(self.apple_inst.current.hardness, 10)
        self.assertEqual(self.apple_inst.current.hit_points, 20)
        self.assertDictEqual(self.apple_inst.current.tags, {})
        self.assertEqual(self.apple_inst.current.is_magical, False)
        self.assertEqual(self.apple_inst.current.weapon_categories, [])

    def test_reweight_percent(self):
        self.apple_inst.reweight_percent(50)
        self.assertEqual(self.apple_inst.current.weight, 1.25)
    
    def test_set_size(self):
#         print(f'Setup():\napple_def -> {self.apple_def.__dict__}')
        self.apple_inst.set_size('2', '3', '4')
        self.assertEqual(self.apple_inst.original.length, 3)
        self.assertEqual(self.apple_inst.original.width, 0.16)
        self.assertEqual(self.apple_inst.original.height, 0.5)
        self.assertEqual(self.apple_inst.current.length, 2)
        self.assertEqual(self.apple_inst.current.width, 3)
        self.assertEqual(self.apple_inst.current.height, 4)
    
    def test_set_tag(self):
        self.apple_inst.set_tag('color', 'blue')
        self.assertEqual(self.apple_inst.original.tags.get('color'), None)
        self.assertEqual(self.apple_inst.current.tags.get('color'), 'blue')
    
    def test_set_tags(self):
        self.apple_inst.set_tags({'color': 'red'})
        self.assertEqual(self.apple_inst.original.tags, {})
        self.assertEqual(self.apple_inst.current.tags['color'], 'red')
        self.assertEqual(self.apple_inst.current.tags, {'color': 'red'})

    def test_lengthen(self):
        length = self.apple_inst.current.length
        self.apple_inst.lengthen('2')
        self.assertEqual(self.apple_inst.current.length, length+2)
        self.apple_inst.lengthen(2)
        self.assertEqual(self.apple_inst.current.length, length+4)
    
    def test_widen(self):
        width = self.apple_inst.current.width
        self.apple_inst.widen('0.14')
        self.assertEqual(self.apple_inst.current.width, width+0.14)
        self.apple_inst.widen(0.1)
        self.assertEqual(self.apple_inst.current.width, width+0.24)
    
    def test_deepen(self):
        height = self.apple_inst.current.height
        self.apple_inst.deepen('4')
        self.assertEqual(self.apple_inst.current.height, height+4)
        self.apple_inst.deepen(4)
        self.assertEqual(self.apple_inst.current.height, height+8)
    
    def test_resize_percent(self):
        length = self.apple_inst.current.length
        width = self.apple_inst.current.width
        height = self.apple_inst.current.height
        self.apple_inst.resize_percent(50)
        self.assertEqual(self.apple_inst.current.length, length/2)
        self.assertEqual(self.apple_inst.current.width, width/2)
        self.assertEqual(self.apple_inst.current.height, height/2)
    
    def test_add_weapon_category(self):
        self.apple_inst.add_weapon_category('sword')
        self.assertEqual(self.apple_inst.current.weapon_categories, ['sword'])
        self.apple_inst.add_weapon_category('hand')
        self.assertEqual(self.apple_inst.current.weapon_categories, ['sword', 'hand'])

    def test_damage(self):
        hp_before = self.apple_inst.hit_points()
        self.apple_inst.damage(hp_before)
        self.assertEqual(self.apple_inst.hit_points(), 0)

        self.apple_inst.current.hit_points = hp_before
        self.apple_inst.damage(hp_before+1)

        self.assertEqual(self.apple_inst.current.hit_points, 0)
        self.assertEqual(self.apple_inst.hit_points(), 0)

        self.apple_inst.current.hit_points = hp_before
        self.apple_inst.damage(hp_before-1)
        self.assertEqual(self.apple_inst.hit_points(), 1)

class TestObjectDictionary(unittest.TestCase):
    def setUp(self):
        self.objects_file = '../src/config/objects.tsv'
        self.categories_file = '../src/config/object_categories.json'
        self.object_dict = ObjectDictionary()

        self.expected_categories = {
        "Animal": [
            "Boar", "Bull"
        ],
        "Bedding": [
            "Linen pillow", "Silk pillow"
        ],
        "Clothing": [
            "Breeches", "Cap"
        ],
        "Drink": [
            "Ale (pint)", "Beer (pint)"
        ],
        "Equipment": [
            "Awl (leather)", "Backpack (80 lb. capacity)"
        ],
        "Healing herb": [
            "Adder's-tongue ointment (oz.)", "Birthwort (oz.)"
        ],
        "Herb": [
            "Amaryllis stalk (ea.)", "Belladonna (oz.)"
        ],
        "Material": [
            "Brick", "Brocade (yd.)", "Rock"
        ],
        "Missile": [
            "Arrow (ea.)", "Bolt, hand crossbow", "Rock"
        ],
        "Provisions": [
            "Barley, rye, corn  (lb.)", "Beef (lb.)"
        ],
        "Substance": [
            "Acid (strong, oz.)", "Acorns (lb.)"
        ],
        "Tack & Harness": [
            "Bit and Bridle", "Halter"
        ],
        "Transport": [
            "Barge", "Canoe (small)"
        ]
        }
        self.object_dict.load_objects(self.objects_file)
        self.assertEqual(len(self.object_dict.objects), 27)
        for object in self.object_dict.objects:
            object_dict = self.object_dict.objects[object]
        self.assertIsInstance(object_dict, ObjectDefinition)
        object = self.object_dict.objects['Boar']
        self.assertEqual(object.obj_type, 'Boar')
        self.assertEqual(object.cost, 8000)
        self.assertEqual(object.weight, 400)
        self.assertEqual(object.length, 6)
        self.assertEqual(object.hardness, 5)
        self.assertEqual(object.hit_points, 10)

        self.object_dict.load_object_categories(self.categories_file)
        self.assertEqual(len(self.object_dict.object_categories), 13)
        self.assertDictEqual(self.object_dict.object_categories, self.expected_categories)

    def test_all_objects_in_categories(self):
        self.object_dict.load_object_categories(self.categories_file)
        self.object_dict.load_objects(self.objects_file)
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
        self.object_dict.load_objects(self.objects_file)
        for category_name, category in self.object_dict.object_categories.items():
            for object_name in category:
                self.assertIn(object_name, self.object_dict.objects, 
                              f"ObjectDefinition {object_name} in category {category_name} not found in objects list")

    def test_get_objects_in_category(self):
        self.assertEqual(self.object_dict.get_objects_in_category('Animal'), ['Boar', 'Bull'])
        self.assertEqual(self.object_dict.get_objects_in_category('Drink'), ['Ale (pint)', 'Beer (pint)'])
        self.assertIsNone(self.object_dict.get_objects_in_category('nonexistent_category'))

class TestObjectRegistry(unittest.TestCase):
    def setUp(self):
        # Faking a Universe instance as a simple ObjectInstance
        universe_def = ObjectDefinition('universe', sys.maxsize, sys.maxsize, sys.maxsize,
                                        sys.maxsize, 0, sys.maxsize, sys.maxsize, 
                                        is_magical=True)
        self.universe = ObjectInstance(universe_def, 'This universe', id='universe')
        self.object_registry = ObjectRegistry()
        self.apple_def = ObjectDefinition('An apple', '3', '0.16', '0.5', '2.5', '50', 10, 20)
        self.apple_inst = ObjectInstance(self.apple_def, 'This apple')
        self.backpack_def = ObjectDefinition('A backpack', 3.1, 0.2, 0.6, 1.5, 30, 5, 5)
        self.backpack_inst = ObjectInstance(self.backpack_def, 'This backpack')
        self.seed_def = ObjectDefinition('An apple seed', '0.01', '0.01', '0.01', '0.01', '1', 1, 1)
        self.seed_inst = ObjectInstance(self.seed_def, 'This apple seed')

        self.object_registry.add_object(self.universe)
        self.object_registry.add_object(self.apple_inst)
        self.object_registry.add_object(self.backpack_inst)
        self.object_registry.add_object(self.seed_inst)

    def test_add_object(self):
        self.assertIn(self.universe.get_id(), self.object_registry.object_instances)
        self.assertIn(self.apple_inst.get_id(), self.object_registry.object_instances)
        self.assertIn(self.backpack_inst.get_id(), self.object_registry.object_instances)
        self.assertIn(self.seed_inst.get_id(), self.object_registry.object_instances)

    def test_get_object_by_id(self):
        obj = self.object_registry.get_object_by_id(self.universe.get_id())
        self.assertEqual(obj, self.universe)
        self.assertIsNone(obj.get_parent_container_id())
        obj = self.object_registry.get_object_by_id(self.apple_inst.get_id())
        self.assertEqual(obj, self.apple_inst)
        self.assertEqual(obj.get_parent_container_id(), None)
        obj = self.object_registry.get_object_by_id(self.backpack_inst.get_id())
        self.assertEqual(obj, self.backpack_inst)
        self.assertEqual(obj.get_parent_container_id(), None)
        obj = self.object_registry.get_object_by_id(self.seed_inst.get_id())
        self.assertEqual(obj, self.seed_inst)
        self.assertEqual(obj.get_parent_container_id(), None)

    def test_get_object_by_id_missing(self):
        obj = self.object_registry.get_object_by_id('nonexistent_id')
        self.assertIsNone(obj)

    def test_move_object(self):
        self.backpack_inst.set_parent_container_id(self.object_registry, 'universe')
        self.assertEqual(self.backpack_inst.get_parent_container_id(), 'universe')
        self.backpack_inst.set_parent_container_id(self.object_registry, 'nowhere')
        self.assertEqual(self.backpack_inst.get_parent_container_id(), 'universe')
        self.backpack_inst.set_parent_container_id(self.object_registry, None)
        self.assertEqual(self.backpack_inst.get_parent_container_id(), 'universe')
        self.backpack_inst.set_parent_container_id(self.object_registry, self.backpack_inst.get_id())
        self.assertEqual(self.backpack_inst.get_parent_container_id(), 'universe')

        self.apple_inst.set_parent_container_id(self.object_registry, self.backpack_inst.get_id())
        self.assertEqual(self.apple_inst.get_parent_container_id(), self.backpack_inst.get_id())

        self.seed_inst.set_parent_container_id(self.object_registry, self.apple_inst.get_id())
        self.assertEqual(self.seed_inst.get_parent_container_id(), self.apple_inst.get_id())

if __name__ == '__main__':
    unittest.main()