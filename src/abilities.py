#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2023 Rauthiflor LLC"
__version__ = "abilities.py 2023-03-15T10:49:08-03:00"

# TODO:

from utils import convert_to_numeric, convert_to_ability

class Abilities():
    '''
    A class to capture Being abilities.
    '''
    def __init__(self, strength=10, dexterity=10, constitution=10, intelligence=10, wisdom=10, charisma=10):
        self.abilities = {}
        self.abilities['STR'] = convert_to_ability(strength)
        self.abilities['DEX'] = convert_to_ability(dexterity)
        self.abilities['CON'] = convert_to_ability(constitution)
        self.abilities['INT'] = convert_to_ability(intelligence)
        self.abilities['WIS'] = convert_to_ability(wisdom)
        self.abilities['CHA'] = convert_to_ability(charisma)

    def STR(self):
        return self.abilities.get('STR')

    def DEX(self):
        return self.abilities.get('DEX')

    def CON(self):
        return self.abilities.get('CON')

    def INT(self):
        return self.abilities.get('INT')

    def WIS(self):
        return self.abilities.get('WIS')

    def CHA(self):
        return self.abilities.get('CHA')

    def set_ability(self, ability, new_value):
        if convert_to_numeric(new_value) is None:
            return
        v = convert_to_ability(new_value)
        a = ability[:3].upper()
        if v >= 0 and a in ['STR', 'DEX', 'CON', 'INT', 'WIS', 'CHA']:
            self.abilities[a] = v

    def get_abilities(self):
        return self.abilities

    def copy(self):
        '''
        Get an independent copy of the Abilities instance.
        '''
        return Abilities(self.STR(), self.DEX(), self.CON(), 
                         self.INT(), self.WIS(), self.CHA())
