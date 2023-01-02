#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "John Wieczorek"
__copyright__ = "Copyright 2022 Rauthiflor LLC"
__version__ = "object.py 2022-01-02T15:49-03:00"

from thing import Thing

# An Object is a Thing with mass that occupies space for a period of time. This does not 
# mean that it is necessarily stationary, nor that it is permanent. There are normal and 
# current values for various characteristics. Normal values are those that characterize 
# original state of the Object. Current values are those that are in effect.
class Object(Thing):
  def __init__(self, mass=0, length=0, width=0, height=0, hp = 0, name=''):
    # hit points
    # mass
    # size (length, width, height)
    # name

    Thing.__init__(self, name)
    self.typestr = 'Object'
    self.rename(name)
    self.normal_hit_points = hp
    self.normal_mass = mass
    self.normal_size = Size(length,width,height)
    self.top_facing = 0 # up 
    self.front_facing = 1 # whichever horizontal orientation (1-6 on hex) 1 refers to
    self.current_hit_points = hp
    self.current_mass = self.normal_mass
    self.current_size = self.normal_size
    self.as_weapon_categories = []

  def set_facing(self, new_front_facing, new_top_facing):
    self.top_facing = new_top_facing
    self.front_facing = new_front_facing
    
  def set_normal_hit_points(self, new_hit_points):
    self.normal_hit_points = new_hit_points

  def set_current_hit_points(self, new_hit_points):
    self.current_hit_points = new_hit_points

  def set_normal_mass(self, new_mass):
    self.normal_mass = new_mass

  def set_current_mass(self, new_mass):
    self.current_mass = new_mass
    
  def remass_percent(self, new_percent):
    self.current_mass = self.current_mass*new_percent/100

  # set the dimensions to newly provided values
  def set_size(new_length, new_width, new_height):
    self.current_size.set_size(new_length, new_width, new_height)

  # add to the length
  def lengthen(added_length):
    self.current_size.lengthen(added_length)

  # add to the width
  def widen(added_width):
    self.current_size.widen(added_width)

  # add to the height
  def deepen(added_height):
    self.current_size.deepen(added_height)

  # set all dimensions to a percentage of their current values
  def resize_percent(new_percent):
    self.current_size.resize_percent(new_percent)

  def as_json(self):
    pass

  def add_as_weapon_category(self, weapon_category):
    self.as_weapon_categories.append(weapon_category)

  def as_text(self, separator='\n'):
    s = f'Type: {self.typestr}'
    s += f'{separator}Id: {self.id}'
    s += f'{separator}Name: {self.name}'
    s += f'{separator}normal mass: {self.normal_mass}'
    s += f'{separator}normal size: {self.normal_size.as_text(" ")}'
    s += f'{separator}normal hit points: {self.normal_hit_points}'
    s += f'{separator}current mass: {self.current_mass}'
    s += f'{separator}current size: {self.current_size.as_text(" ")}'
    s += f'{separator}current hit points: {self.current_hit_points}'
    s += f'{separator}top facing: {self.top_facing}'
    s += f'{separator}front facing: {self.front_facing}'
    if len(self.as_weapon_categories) > 0:
        s += f'{separator}Use as weapon Categories:'
        for weapon_category in self.as_weapon_categories:
          s += f'[separator]  {weapon_category}'
    return s

# A Size is a three-dimensional definition of occupied space where the dimensions are 
# the extremes measures of length, width, and height that form a minimum bounding box.
class Size():
  def __init__(self, length=0, width=0, height=0):
    self.length = length
    self.width = width
    self.height = height

  # set the dimensions to newly provided values
  def set_size(new_length, new_width, new_height):
    self.length = new_length
    self.width = new_width
    self.height = new_height

  # add to the length
  def lengthen(added_length):
    self.length = self.length + added_length

  # add to the width
  def widen(added_width):
    self.width = self.width + added_width

  # add to the height
  def deepen(added_height):
    self.height = self.height + added_height

  # set all dimensions to a percentage of their current values
  def resize_percent(new_percent):
    self.length = self.length*new_percent/100
    self.width = self.width*new_percent/100
    self.height = self.height*new_percent/100

  def as_text(self, separator='\n'):
    s = f'{separator}length: {self.length}'
    s += f'{separator}width: {self.width}'
    s += f'{separator}height: {self.height}'
    return s
