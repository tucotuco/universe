#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2023 Rauthiflor LLC"
__version__ = "abilities.py 2023-03-30T01:38:08-03:00"

# TODO:

from utils import convert_to_numeric, convert_to_ability

class Abilities():
    '''
    A template for characteristics of Being abilities.
    '''
    def __init__(self, strength=10, dexterity=10, constitution=10, intelligence=10, wisdom=10, charisma=10):
        self.abilities = {}
        self.abilities['STR'] = convert_to_ability(strength)
        self.abilities['DEX'] = convert_to_ability(dexterity)
        self.abilities['CON'] = convert_to_ability(constitution)
        self.abilities['INT'] = convert_to_ability(intelligence)
        self.abilities['WIS'] = convert_to_ability(wisdom)
        self.abilities['CHA'] = convert_to_ability(charisma)

    def copy(self):
        '''
        Get an independent copy of an Abilities instance.
        '''
        return Abilities(self.STR(), self.DEX(), self.CON(), 
                         self.INT(), self.WIS(), self.CHA())
    def STR(self):
        '''
        Set the value of the Strength ability.
        '''
        return self.abilities.get('STR')

    def DEX(self):
        '''
        Set the value of the Dexterity ability.
        '''
        return self.abilities.get('DEX')

    def CON(self):
        '''
        Set the value of the Constitution ability.
        '''
        return self.abilities.get('CON')

    def INT(self):
        '''
        Set the value of the Intelligence ability.
        '''
        return self.abilities.get('INT')

    def WIS(self):
        '''
        Set the value of the Wisdom ability.
        '''
        return self.abilities.get('WIS')

    def CHA(self):
        '''
        Set the value of the Charisma ability.
        '''
        return self.abilities.get('CHA')

    def get_abilities(self):
        '''
        Get the entire ability dictionary.
        '''
        return self.abilities

    def set_ability(self, ability, new_value):
        '''
        Set the value of an ability.
        '''
        if convert_to_numeric(new_value) is None:
            return
        v = convert_to_ability(new_value)
        a = ability[:3].upper()
        if v >= 0 and a in ['STR', 'DEX', 'CON', 'INT', 'WIS', 'CHA']:
            self.abilities[a] = v
