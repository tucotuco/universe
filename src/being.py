#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2022 Rauthiflor LLC"
__version__ = "being.py 2023-01-02T16:57-03:00"

from object import Object

class Being(Object):
  def __init__(self, mass = 0, length=0, width=0, height=0, hp = 0, name = '', 
               being_type = 'Being'):

    Object.__init__(self, mass, length, width, height, hp, name)
    self.typestr = 'Being'
    self.rename(name)
    self.being_type = being_type
    self.skills = []
    self.abilities = {}
    self.possessions = []
    self.left_weapon = None
    self.right_weapon = None
    self.weapon_skills = []
    self.armor = None
    self.experience = 0
