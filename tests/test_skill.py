#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2023 Rauthiflor LLC"
__version__ = "test_skills.py 2023-03-20T11:28-03:00"

# TODO: Check comprehensiveness

import unittest
import sys
import os
from io import StringIO
from unittest.mock import patch
from unittest.mock import Mock

sys.path.insert(0, os.path.abspath('../src'))
#print(f'{__version__}:{sys.path}')

from skill import SkillDefinition, Skills, SkillDictionary
#from skill import SkillInstance
from weapon import WeaponDefinition, WeaponDictionary

class TestSkillDefinition(unittest.TestCase):
    def setUp(self):
        self.skill_def = SkillDefinition('climbing', True, False)

    def test_copy(self):
        new_def = self.skill_def.copy()
        self.assertEqual(new_def.name, self.skill_def.name)
        self.assertEqual(new_def.is_ordinary, self.skill_def.is_ordinary)
        self.assertEqual(new_def.is_progressive, self.skill_def.is_progressive)

    def test_to_json(self):
        expected_json = '{"climbing": {"is_ordinary": true, "is_progressive": false}}'
        self.assertEqual(self.skill_def.to_json(), expected_json)

class TestSkillDictionary(unittest.TestCase):
    def setUp(self):
        self.skills_file = '../src/config/skills.tsv'
        self.weapons_file = '../src/config/weapons.tsv'
        self.weapon_categories_file = '../src/config/weapon_categories.json'
        self.skill_dictionary = SkillDictionary()
        self.weapon_dictionary = WeaponDictionary()

    def test_init_skills(self):
        skill_dict = SkillDictionary(self.skills_file)
        self.assertEqual(len(skill_dict.skills), 23)
        for skill in skill_dict.skills:
            skill = skill_dict.skills[skill]
            self.assertIsInstance(skill, dict)
        skill = skill_dict.skills['tumble']
        self.assertEqual(skill.get('is_ordinary'), True)
        self.assertEqual(skill.get('is_progressive'), True)

    def test_load_skills(self):
        data = 'name\tis_ordinary\tis_progressive\nclimbing\tTrue\tFalse\nsneaking\tTrue\tTrue\n'
        with patch('builtins.open', return_value=StringIO(data)) as mock_file:
            self.skill_dictionary.load_skills('testfile')
        self.assertEqual(len(self.skill_dictionary.skills), 2)
        self.assertIn('climbing', self.skill_dictionary.skills)
        self.assertIn('sneaking', self.skill_dictionary.skills)
        self.assertIsNotNone(self.skill_dictionary.get_skill_definition('climbing'))
        self.assertIsNotNone(self.skill_dictionary.get_skill_definition('sneaking'))

    def test_load_skills2(self):
        self.skill_dictionary.load_skills(self.skills_file)
        self.assertEqual(len(self.skill_dictionary.skills), 23)
        for skill in self.skill_dictionary.skills:
            skill_dict = self.skill_dictionary.skills[skill]
            self.assertIsInstance(skill_dict, dict)
        skill = self.skill_dictionary.skills['aerial combat']
        self.assertEqual(skill.get('is_ordinary'), True)
        self.assertEqual(skill.get('is_progressive'), False)

    def test_to_json(self):
        skill_def1 = SkillDefinition('climbing', True, False)
        skill_def2 = SkillDefinition('sneaking', True, True)
        self.skill_dictionary.add_skill(skill_def1)
        self.skill_dictionary.add_skill(skill_def2)
        expected_json = '{\n  "climbing": {\n    "is_ordinary": true,\n    "is_progressive": false\n  },\n  "sneaking": {\n    "is_ordinary": true,\n    "is_progressive": true\n  }\n}'
        self.assertEqual(self.skill_dictionary.to_json(), expected_json)

    def test_add_weapon_skills(self):
        self.skill_dictionary.load_skills(self.skills_file)
        self.weapon_dictionary.load_object_categories(self.weapon_categories_file)
        self.skill_dictionary.add_weapon_skills(self.weapon_dictionary)
        self.assertIn('Axes', self.skill_dictionary.skills)
        self.assertIn('Longsword', self.skill_dictionary.skills)
#        print(f'{self.dictionary.to_json()}')

class TestSkills(unittest.TestCase):
    def setUp(self):
        self.skills_file = '../src/config/skills.tsv'
        self.weapons_file = '../src/config/weapons.tsv'
        self.weapon_categories_file = '../src/config/weapon_categories.json'
        self.skill_dictionary = SkillDictionary()
        self.weapon_dictionary = WeaponDictionary()

        self.skill_dictionary.load_skills(self.skills_file)
        self.weapon_dictionary.load_object_categories(self.weapon_categories_file)
        self.weapon_dictionary.load_objects(self.weapons_file)
        self.skill_dictionary.add_weapon_skills(self.weapon_dictionary)

        self.skills = Skills()
        self.skills.set_skill_level(self.skill_dictionary, 'escape artist', 1)
        self.assertEqual(self.skills.get_skill_level('escape artist'), 1)
#        print(f'skills1: {self.skills.skills}\nweapon skills: {self.skills.weapon_skills}')
        self.skills.set_weapon_skill_level(self.weapon_dictionary, 'Longsword', 4)
        self.assertEqual(self.skills.get_weapon_skill_level('Longsword'), 4)
        self.skills.set_skill_level(self.skill_dictionary, 'escape artist', 2)
        self.assertEqual(self.skills.get_skill_level('escape artist'), 2)

    def test_get_weapon_skill_level(self):
        level = self.skills.get_weapon_skill_level('Longsword')
#        print(f'skills: {self.skills.skills}\nweapon skills: {self.skills.weapon_skills}')
        self.assertEqual(level, 4)
        level = self.skills.get_weapon_skill_level('Falchion')
        self.assertEqual(level, 2)
        level = self.skills.get_weapon_skill_level('Bec de corbin')
        self.assertEqual(level, 0)
        self.skills.set_weapon_skill_level(self.weapon_dictionary, 'Bec de corbin', 4)
        level = self.skills.get_weapon_skill_level('Bec de corbin')
        self.assertEqual(level, 4)
        self.skills.set_weapon_skill_level(self.weapon_dictionary, 'Spear', 7)
        level = self.skills.get_weapon_skill_level('Spear')
        self.assertEqual(level, 7)
        level = self.skills.get_weapon_skill_level('Halberd')
        self.assertEqual(level, 2)
        level = self.skills.get_weapon_skill_level('Spetum')
        self.assertEqual(level, 3)
        self.skills.set_weapon_skill_level(self.weapon_dictionary, 'Halberd', 8)
        level = self.skills.get_weapon_skill_level('Halberd')
        self.assertEqual(level, 8)
        level = self.skills.get_weapon_skill_level('Handaxe')
        self.assertEqual(level, 4)
        
    def test_set_skill_level_invalid_value(self):
        l = self.skills.get_skill_level('Longsword')
        self.skills.set_skill_level('Longsword', 'invalid_value')
        self.assertEqual(self.skills.get_skill_level('Longsword'), l)

if __name__ == '__main__':
    unittest.main()