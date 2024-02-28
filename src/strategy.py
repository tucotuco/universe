#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2024 Rauthiflor LLC"
__version__ = "strategy.py 2024-01-17T09:24-08:00"

# TODO:

import math
import json

from utils import convert_to_numeric, convert_to_speed
       
class Strategy():
    def __init__(self, attack=0, defense=0, timing=0, extra_damage=0):
        ''' 
        Make an instance of a combat strategy:
        attack - effort applied to the attack part of the strategy
        defense - effort applied to the defense part of the strategy
        timing - effort applied to the improving the timing of the action
        extra_damage - effort applied to increasing damage from the action
        '''
        self.attack = attack
        self.defense = defense
        self.timing = timing
        self.extra_damage = extra_damage

    def copy(self):
        '''
        Get an independent copy of the Strategy instance.
        '''
        return Strategy(self.attack, self.defense, self.timing, self.extra_damage)

    def to_json(self):
        data = {
            "attack": self.attack,
            "defense": self.defense,
            "timing": self.timing,
            "extra_damage": self.extra_damage
        }
        return json.dumps(data)

    def timing_adjustment(self):
        ''' 
        Given the effort put into the timing part of the strategy, return the number of 
        seconds by which the timing can be reduced. This result will have to be subject
        to the lower bound of one second.
        '''
        # n = (-1 + sqrt(1 + 8t)) / 2
        return math.floor((-1 + math.sqrt(1 + 8* self.timing))/2)
