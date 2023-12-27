#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2023 Rauthiflor LLC"
__version__ = "armor.py 2023-12-21T15:09-03:00"

# TODO: ArmorDefinitions will need widths and heights eventually
# TODO: *** Implement damage_to_armor()
# TODO: Write a script to figure out damage through each armor for each attack of each weapon

import json
from object import ObjectInstance, ObjectDefinition, ObjectDictionary
from utils import convert_to_numeric

class ArmorDefinition(ObjectDefinition):
    '''
    A template for characteristics of an Armor, which is a subtype of Object.
    '''
    def __init__(self, obj_type, cost, weight, Bh, Ph, Sh, Bd, Pd, Sd, 
                 armor_check_penalty, dexterity_check_penalty, hit_points, 
                 length=0, width=0, height=0, hardness=0, is_magical=False, tags=None, 
                 weapon_categories=None):
        super().__init__(obj_type, length, width, height, weight, cost, hardness, 
                         hit_points, is_magical, tags, weapon_categories)
        self.defenses = {
            'B': {'h': convert_to_numeric(Bh), 
                  'd': convert_to_numeric(Bd)},
            'P': {'h': convert_to_numeric(Ph), 
                  'd': convert_to_numeric(Pd)},
            'S': {'h': convert_to_numeric(Sh), 
                  'd': convert_to_numeric(Sd)}
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
            self.Bh(),
            self.Ph(),
            self.Sh(),
            self.Bd(),
            self.Pd(),
            self.Sd(),
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
        Get a representation of an ArmorDefinition as JSON.
        '''
        parent_json = super().to_json()
        data = {
            **json.loads(parent_json),
            'defenses': self.defenses,
            'armor_check_penalty': self.armor_check_penalty,
            'dexterity_check_penalty': self.dexterity_check_penalty,
        }
        return json.dumps(data)

    def Bh(self):
        '''
        Get the value of hardness against a bludgeon penetration type.
        '''
        return self.defenses.get('B').get('h')

    def Ph(self):
        '''
        Get the value of hardness against a pierce penetration type.
        '''
        return self.defenses.get('P').get('h')

    def Sh(self):
        '''
        Get the value of hardness against a slash penetration type.
        '''
        return self.defenses.get('S').get('h')

    def Bd(self):
        '''
        Get the value of damage stopped for a bludgeon penetration type.
        '''
        return self.defenses.get('B').get('d')

    def Pd(self):
        '''
        Get the value of damage stopped for a pierce penetration type.
        '''
        return self.defenses.get('P').get('d')

    def Sd(self):
        '''
        Get the value of damage stopped for a slash penetration type.
        '''
        return self.defenses.get('S').get('d')

class ArmorInstance(ObjectInstance):
    ''' 
    An ObjectInstance based on an ArmorDefinition.
    '''
    def __init__(self, armor_definition, name=None):
        ObjectInstance.__init__(self, armor_definition, name)
        self.original = armor_definition
        self.current = armor_definition.copy()

    def Bh(self):
        '''
        Get the current value of hardness against a bludgeon penetration type.
        '''
        return self.current.Bh()

    def Ph(self):
        '''
        Get the current value of hardness against a pierce penetration type.
        '''
        return self.current.Ph()

    def Sh(self):
        '''
        Get the current value of hardness against a slash penetration type.
        '''
        return self.current.Sh()

    def Bd(self):
        '''
        Get the current value of damage stopped for a bludgeon penetration type.
        '''
        return self.current.Bd()

    def Pd(self):
        '''
        Get the current value of damage stopped for a pierce penetration type.
        '''
        return self.current.Pd()

    def Sd(self):
        '''
        Get the current value of damage stopped for a slash penetration type.
        '''
        return self.current.Sd()

    def set_armor_check_penalty(self, new_armor_check_penalty):
        '''
        Set the armor_check_penalty to a new value.
        '''
        self.current.armor_check_penalty = convert_to_numeric(new_armor_check_penalty)
        if self.current.armor_check_penalty < 0:
            self.current.armor_check_penalty = 0
        if self.current.armor_check_penalty > 8:
            self.current.armor_check_penalty = 8

    def set_dexterity_check_penalty(self, new_dexterity_check_penalty):
        '''
        Set the dexterity_check_penalty to a new value.
        '''
        self.current.dexterity_check_penalty = \
            convert_to_numeric(new_dexterity_check_penalty)
        if self.current.dexterity_check_penalty < -4:
            self.current.dexterity_check_penalty = -4
        if self.current.dexterity_check_penalty > 0:
            self.current.dexterity_check_penalty = 0

    def set_defense(self, defense_type, defense_attribute, new_value):
        '''
        Set a given defense attribute of a defense type to a new value.
        '''
        try:
            self.defenses[defense_type][defense_attribute] = new_value
            if self.defenses[defense_type][defense_attribute] < 0:
                self.defenses[defense_type][defense_attribute] = 0
        except Exception(e):
            return

    def set_defenses(self, new_defenses_dict):
        '''
        Set the current defenses of the armor via a dictionary of defenses.
        '''
        self.current.defenses = new_defenses_dict

    def worst_defense_damage_stopped(self, penetration_types):
        '''
        Return the amount of damage stopped by the armor for the worst defense among the 
        given list of penetration types.
        '''
        least_defense_damage = 1000
        for p in penetration_types.split(','):
            pdamage = self.current.defenses[p]['d']
#            print(f'damage stopped for pt {p} is {pdamage}')
            if pdamage < least_defense_damage:
                least_defense_damage = pdamage
        return least_defense_damage

    def worst_defense_hardness(self, penetration_types):
        '''
        Return the hardness that is the worst among those for the given list of 
        penetration types. The list must be a comma-separated string of valid penetration
        types (e.g., "B,P,S").
        '''
        least_defense_hardness = 1000
        for p in penetration_types.split(','):
            phardness = self.current.defenses[p]['h']
#            print(f'hardness for pt {p} is {phardness}')
            if phardness < least_defense_hardness:
                least_defense_hardness = phardness
        return least_defense_hardness

    def damage_to_armor(self, damage, penetrations_types):
        '''
        Calculate the amount of damage that would be done to the armor for a given 
        weapon penetration type.
        '''
        hardness = worst_defense_hardness(penetration_types)
        armor_damage = damage - hardness
        if armor_damage > 0:
            return armor_damage
        return 0

    def worst_defense(self):
        '''
        Return a list of penetration types that the armor is worst at defending against.
        '''
        worst = []
        dmg = self.worst_defense_damage_stopped('B,P,S')
        for p in ['B', 'P', 'S']:
            pdamage = self.current.defenses[p]['d']
            if pdamage == dmg:
                worst.append(p)
        return worst

    def damage_through(self, damage, weapon, attack_type):
        '''
        Calculate the amount of damage that would get through the armor for a given 
        weapon and attack type.
        '''
#        print(f'damage: {damage} weapon: {weapon.name} attack_type: {attack_type}')
#        print(f'weapon: {weapon.to_json()}')
        # Get the penetration types of the attack with the weapon
        penetration_types = weapon.get_penetration_types(attack_type)
        
        # Get least damage stopped given the penetration types of the attack
#        print(f'penetration_types_for {attack_type}: {penetration_types}')
#        print(f'defenses: {self.current.defenses}')
        least_defense_damage = self.worst_defense_damage_stopped(penetration_types)

#        print(f'least damage stopped is {least_defense_damage}')
        if least_defense_damage <= damage:
            return damage - least_defense_damage
        return 0

class ArmorDictionary(ObjectDictionary):
    '''
    A reference for information about ArmorDefinitions.
    '''
    def __init__(self, dictionary_file=None):
        ObjectDictionary.__init__(self)

        if dictionary_file is not None:
            self.load_objects(dictionary_file)

    def load_objects(self, filename):
        '''
        Get ArmorDefinitions from a CSV file.
        '''
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

