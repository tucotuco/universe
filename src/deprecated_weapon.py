#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2023 Rauthiflor LLC"
__version__ = "weapon.py 2023-01-02T16:02-03:00"

from thing import Thing
from object import Object
from action import AttackCategory

class Weapon(Object):
  def __init__(self, mass=0, length=0, width=0, height=0, hp = 0, name='', 
      weapon_definition=None):
    Thing.__init__(self, name)
    Object.__init__(self, mass, length, width, height, hp)
    self.typestr = 'Weapon'
    self.weapon_definition = weapon_definition

  def set_weapon_definition(self, weapon_definition):
    self.weapon_definition = weapon_definition

class WeaponDefinition(Thing):
  def __init__(self, name, weapon_category = ''):
    Thing.__init__(self, name)
    self.typestr = 'Weapon Definition'
    self.weapon_category = weapon_category
    self.attack_categories = []

  def add_attack_category(self, name, motion, penetration, timing, damage, reach):
    attack_category = AttackCategory(name, motion, penetration, timing, damage, reach)
    self.attack_categories.append(attack_category)

  def as_text(self, separator='\n', indent=''):
    s = f'{indent}Type: {self.typestr}'
    s += f'{separator}{indent}Id: {self.id}'
    s += f'{separator}{indent}Weapon name: {self.name}'
    s += f'{separator}{indent}Attacks:'
    if len(self.attack_categories) >0:
      for attack_category in self.attack_categories:
        s += f'{attack_category.as_text()}{separator}{indent}'
    return s

