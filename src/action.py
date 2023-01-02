#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2022 Rauthiflor LLC"
__version__ = "action.py 2023-01-02T16:39-03:00"

from object import Thing

class AttackCategory(Thing):
  def __init__(self, name, motion, penetration, timing, damage, reach):
    Thing.__init__(self, name)
    self.typestr = 'AttackCategory'
    self.motion = motion
    self.penetration = penetration
    self.timing = timing
    self.damage = damage
    self.reach = reach

  def as_json(self):
    pass

  def as_text(self, separator = '\n', indent = '  '):
    s =  f'{separator}{indent}Attack: {self.name}'
    s += f'{separator}{indent}Motion: {self.motion}'
    s += f'{separator}{indent}Penetration: {self.penetration}'
    s += f'{separator}{indent}Timing: {self.timing}'
    s += f'{separator}{indent}Damage: {self.damage}'
    s += f'{separator}{indent}Reach: {self.reach}'
    s += f'{separator}{indent}Damage per second: {self.damage/self.timing}'
    return s

