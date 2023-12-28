#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2023 Rauthiflor LLC"
__version__ = "weapon.py 2023-12-28T13:16-03:00"

# TODO: WeaponDefinitions from file will need widths and heights eventually
# TODO: Deprecate weapon_size in favor of a function based on actual size and size of wielder
# TODO: Make ''' comments on classes and methods

import json
from object import ObjectInstance, ObjectDefinition, ObjectDictionary
from utils import convert_to_numeric

class WeaponDefinition(ObjectDefinition):
    '''
    A template for characteristics of a Weapon, which is a subtype of Object.
    R - Throw  t - timing
    S - Swing  d - damage
    T - Thrust p - penetration types
    '''
    def __init__(self, obj_type, length, weight, cost, hardness, hit_points, Rt, Rd, Rp, 
                 St, Sd, Sp, Tt, Td, Tp, weapon_size, width=0, height=0, is_magical=False, 
                 tags=None, weapon_categories=None):
        super().__init__(obj_type, length, width, height, weight, cost, hardness, 
                         hit_points, is_magical, tags, weapon_categories)
        self.attacks = {
            'R': {'t': convert_to_numeric(Rt), 'd': convert_to_numeric(Rd), 'p': Rp},
            'S': {'t': convert_to_numeric(St), 'd': convert_to_numeric(Sd), 'p': Sp},
            'T': {'t': convert_to_numeric(Tt), 'd': convert_to_numeric(Td), 'p': Tp}
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
            self.Rt(), # Throw timing
            self.Rd(), # Throw damage
            self.Rp(), # Throw penetration types
            self.St(), # Swing timing
            self.Sd(), # Swing damage
            self.Sp(), # Swing penetration types
            self.Tt(), # Thrust timing
            self.Td(), # Thrust damage
            self.Tp(), # Thrust penetration types
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

    def Rt(self):
        return self.attacks.get('R').get('t')

    def Rd(self):
        return self.attacks.get('R').get('d')

    def Rp(self):
        return self.attacks.get('R').get('p')

    def St(self):
        return self.attacks.get('S').get('t')

    def Sd(self):
        return self.attacks.get('S').get('d')

    def Sp(self):
        return self.attacks.get('S').get('p')

    def Tt(self):
        return self.attacks.get('T').get('t')

    def Td(self):
        return self.attacks.get('T').get('d')

    def Tp(self):
        return self.attacks.get('T').get('p')

class WeaponInstance(ObjectInstance):
    ''' 
    An ObjectInstance based on a WeaponDefinition.
    '''
    def __init__(self, weapon_definition, name=None):
        ObjectInstance.__init__(self, weapon_definition, name)
        self.original = weapon_definition
        self.current = weapon_definition.copy()

    def get_weapon_size(self):
        return self.current.weapon_size

    def set_weapon_size(self, new_weapon_size):
        self.current.weapon_size = new_weapon_size

    def Rt(self):
        return self.current.attacks.get('R').get('t')

    def Rd(self):
        return self.current.attacks.get('R').get('d')

    def Rp(self):
        return self.current.attacks.get('R').get('p')

    def St(self):
        return self.current.attacks.get('S').get('t')

    def Sd(self):
        return self.current.attacks.get('S').get('d')

    def Sp(self):
        return self.current.attacks.get('S').get('p')

    def Tt(self):
        return self.current.attacks.get('T').get('t')

    def Td(self):
        return self.current.attacks.get('T').get('d')

    def Tp(self):
        return self.current.attacks.get('T').get('p')

    def get_penetration_types(self, attack_type):
        if attack_type == 'swing':
            return self.Sp()
        if attack_type == 'thrust':
            return self.Tp()
        return self.Rp()

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
                if attack_attribute != 'p':
                    try:
                        new_value = mod_attack_dict[attack_type][attack_attribute]
                        self.current.attacks[attack_type][attack_attribute] += new_value
                        if self.current.attacks[attack_type][attack_attribute] < 1:
                            self.current.attacks[attack_type][attack_attribute] = 1
                    except Exception as e:
                        print(f'Version: {__version__}: {e}')

# A dictionary of all information about weapons
class WeaponDictionary(ObjectDictionary):
    def __init__(self, dictionary_file=None):
        ObjectDictionary.__init__(self)

        if dictionary_file is not None:
            self.load_objects(dictionary_file)

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
