#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2023 Rauthiflor LLC"
__version__ = "armor.py 2023-03-20T18:56-03:00"

# TODO: ArmorDefinitions will need widths and heights eventually

import json
from object import ObjectInstance, ObjectDefinition, ObjectDictionary
from utils import convert_to_numeric

class ArmorDefinition(ObjectDefinition):
    def __init__(self, obj_type, cost, weight, HB, HP, HS, DB, DP, DS, 
                 armor_check_penalty, dexterity_check_penalty, hit_points, 
                 length=0, width=0, height=0, hardness=0, is_magical=False, tags=None, 
                 weapon_categories=None):
        super().__init__(obj_type, length, width, height, weight, cost, hardness, 
                         hit_points, is_magical, tags, weapon_categories)
        self.defenses = {
            'H': {'B': convert_to_numeric(HB), 
                  'P': convert_to_numeric(HP), 
                  'S': convert_to_numeric(HS)},
            'D': {'B': convert_to_numeric(DB), 
                  'P': convert_to_numeric(DP), 
                  'S': convert_to_numeric(DS)}
        }
        self.armor_check_penalty = convert_to_numeric(armor_check_penalty)
        self.dexterity_check_penalty = convert_to_numeric(dexterity_check_penalty)

    def copy(self):
        '''
        Get an independent copy of the ArmorDefinition.
        '''
        new_armor_definition = ArmorDefinition(
            self.obj_type,
            self.cost,
            self.weight,
            self.HB(),
            self.HP(),
            self.HS(),
            self.DB(),
            self.DP(),
            self.DS(),
            self.armor_check_penalty,
            self.dexterity_check_penalty,
            self.hit_points,
            self.length,
            self.width,
            self.height,
            self.hardness,
            self.is_magical,
            self.tags.copy(),
            self.weapon_categories.copy())
        return new_armor_definition

    def to_json(self):
        '''
        Get a representation of a ArmorDefinition as JSON.
        '''
        parent_json = super().to_json()
        data = {
            **json.loads(parent_json),
            'defenses': self.defenses,
            'armor_check_penalty': self.armor_check_penalty,
            'dexterity_check_penalty': self.dexterity_check_penalty,
        }
        return json.dumps(data)

    def HB(self):
        return self.defenses.get('H').get('B')

    def HP(self):
        return self.defenses.get('H').get('P')

    def HS(self):
        return self.defenses.get('H').get('S')

    def DB(self):
        return self.defenses.get('D').get('B')

    def DP(self):
        return self.defenses.get('D').get('P')

    def DS(self):
        return self.defenses.get('D').get('S')

class ArmorInstance(ObjectInstance):
    def __init__(self, armor_definition, name=''):
        ObjectInstance.__init__(self, armor_definition, name)
        self.original = armor_definition
        self.current = armor_definition.copy()

    def set_armor_check_penalty(self, new_armor_check_penalty):
        self.current.armor_check_penalty = convert_to_numeric(new_armor_check_penalty)
        if self.current.armor_check_penalty < 0:
            self.current.armor_check_penalty = 0
        if self.current.armor_check_penalty > 8:
            self.current.armor_check_penalty = 8

    def set_dexterity_check_penalty(self, new_dexterity_check_penalty):
        self.current.dexterity_check_penalty = \
            convert_to_numeric(new_dexterity_check_penalty)
        if self.current.dexterity_check_penalty < -4:
            self.current.dexterity_check_penalty = -4
        if self.current.dexterity_check_penalty > 0:
            self.current.dexterity_check_penalty = 0

    def set_defense(self, defense_type, defense_attribute, new_value):
        try:
            self.defenses[defense_type][defense_attribute] = new_value
            if self.defenses[defense_type][defense_attribute] < 0:
                self.defenses[defense_type][defense_attribute] = 0
        except Exception(e):
            return

    def set_defenses(self, new_defenses_dict):
        self.current.defenses = new_defenses_dict

    def modify_defenses(self, mod_defense_dict):
        for defense_type in mod_defense_dict:
            for defense_attribute in mod_defense_dict[defense_type]:
                if defense_attribute != 'P':
                    try:
                        new_value = mod_defense_dict[defense_type][defense_attribute]
                        self.current.defenses[defense_type][defense_attribute] += new_value
                        if self.current.defenses[defense_type][defense_attribute] < 0:
                            self.current.defenses[defense_type][defense_attribute] = 0
                    except Exception as e:
                        print(f'Version: {__version__}: {e}')

# A dictionary of all information about armors
class ArmorDictionary(ObjectDictionary):
    def __init__(self):
        ObjectDictionary.__init__(self)

    def load_objects(self, filename):
        p = True
        with open(filename, 'r') as f:
            lines = f.readlines()
            headers = lines[0].strip().split('\t')
            if p==True:
                p = False
            for line in lines[1:]:
                fields = line.strip().split('\t')
                armor_dict = {}
                for i in range(len(headers)):
                    armor_dict[headers[i]] = fields[i]
                armor = ArmorDefinition(**armor_dict)
                self.objects[armor.obj_type] = armor
