#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2023 Rauthiflor LLC"
__version__ = "weapon.py 2023-03-20T18:57-03:00"

# TODO: WeaponDefinitions from file will need widths and heights eventually
# TODO: deprecate weapon_size in favor of a function based on actual size?

import json
from object import ObjectInstance, ObjectDefinition, ObjectDictionary
from utils import convert_to_numeric

class WeaponDefinition(ObjectDefinition):
    def __init__(self, obj_type, length, weight, cost, hardness, hit_points, RT, RD, RP, 
                 ST, SD, SP, TT, TD, TP, weapon_size, width=0, height=0, is_magical=False, 
                 tags=None, weapon_categories=None):
        super().__init__(obj_type, length, width, height, weight, cost, hardness, 
                         hit_points, is_magical, tags, weapon_categories)
        self.attacks = {
            'R': {'T': convert_to_numeric(RT), 'D': convert_to_numeric(RD), 'P': RP},
            'S': {'T': convert_to_numeric(ST), 'D': convert_to_numeric(SD), 'P': SP},
            'T': {'T': convert_to_numeric(TT), 'D': convert_to_numeric(TD), 'P': TP}
        }
        self.weapon_size = weapon_size

    def copy(self):
        '''
        Get an independent copy of the WeaponDefinition.
        '''
        new_weapon_definition = WeaponDefinition(
            self.obj_type,
            self.length,
            self.weight,
            self.cost,
            self.hardness,
            self.hit_points,
            self.RT(), # Throw timing
            self.RD(), # Throw damage
            self.RP(), # Throw penetration types
            self.ST(), # Swing timing
            self.SD(), # Swing damage
            self.SP(), # Swing penetration types
            self.TT(), # Thrust timing
            self.TD(), # Thrust damage
            self.TP(), # Thrust penetration types
            self.weapon_size,
            self.width,
            self.height,
            self.is_magical,
            self.tags.copy(),
            self.weapon_categories.copy())
        return new_weapon_definition

    def to_json(self):
        '''
        Get a representation of a WeaponDefinition as JSON.
        '''
        parent_json = super().to_json()
        data = {
            **json.loads(parent_json),
            'attacks': self.attacks,
            'weapon_size': self.weapon_size
        }
        return json.dumps(data)

    def RT(self):
        return self.attacks.get('R').get('T')

    def RD(self):
        return self.attacks.get('R').get('D')

    def RP(self):
        return self.attacks.get('R').get('P')

    def ST(self):
        return self.attacks.get('S').get('T')

    def SD(self):
        return self.attacks.get('S').get('D')

    def SP(self):
        return self.attacks.get('S').get('P')

    def TT(self):
        return self.attacks.get('T').get('T')

    def TD(self):
        return self.attacks.get('T').get('D')

    def TP(self):
        return self.attacks.get('T').get('P')

class WeaponInstance(ObjectInstance):
    def __init__(self, weapon_definition, name=''):
        ObjectInstance.__init__(self, weapon_definition, name)
        self.original = weapon_definition
        self.current = weapon_definition.copy()

    def get_weapon_size(self):
        return self.current.weapon_size

    def set_weapon_size(self, new_weapon_size):
        self.current.weapon_size = new_weapon_size

    def set_attack(self, attack_type, attack_attribute, new_value):
        try:
            self.attacks[attack_type][attack_attribute] = new_value
            if self.attacks[attack_type][attack_attribute] < 1:
                self.attacks[attack_type][attack_attribute] = 1
        except Exception(e):
            return

    def set_attacks(self, new_attacks_dict):
        self.current.attacks = new_attacks_dict

    def modify_attacks(self, mod_attack_dict):
        for attack_type in mod_attack_dict:
            for attack_attribute in mod_attack_dict[attack_type]:
                if attack_attribute != 'P':
                    try:
                        new_value = mod_attack_dict[attack_type][attack_attribute]
                        self.current.attacks[attack_type][attack_attribute] += new_value
                        if self.current.attacks[attack_type][attack_attribute] < 1:
                            self.current.attacks[attack_type][attack_attribute] = 1
                    except Exception as e:
                        print(f'Version: {__version__}: {e}')

# A dictionary of all information about weapons
class WeaponDictionary(ObjectDictionary):
    def __init__(self):
        ObjectDictionary.__init__(self)

#     def to_json(self):
#         '''
#         Get a representation of a WeaponDictionary as JSON.
#         '''
#         data = {
#             'weapon_categories': self.weapon_categories,
#             'weapons': self.weapons,
#         }
#         return json.dumps(data, indent=2)

#     def load_weapon_categories(self, file_path):
#         with open(file_path) as f:
#             self.weapon_categories = json.load(f)
            
    def load_objects(self, filename):
        p = True
        with open(filename, 'r') as f:
            lines = f.readlines()
            headers = lines[0].strip().split('\t')
            if p==True:
                p = False
            for line in lines[1:]:
                fields = line.strip().split('\t')
                weapon_dict = {}
                for i in range(len(headers)):
                    weapon_dict[headers[i]] = fields[i]
                weapon = WeaponDefinition(**weapon_dict)
                self.objects[weapon.obj_type] = weapon
