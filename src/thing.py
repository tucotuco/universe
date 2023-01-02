#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2022 Rauthiflor LLC"
__version__ = "thing.py 2023-01-02T17:07-03:00"

import uuid

# A Thing is a generic entity with a Universal Unique Identifier (UUID) and a name.
class Thing:
  def __init__(self, name=''):
    self.typestr = 'Thing'
    self.id = uuid.uuid4() # immutable once created
    self.name = name
    
  def rename(self, new_name):
    self.name = new_name

  def as_text(self, separator='\n'):
    s = f'Type: {self.typestr}'
    s += f'{separator}Id: {self.id}'
    s += f'{separator}Name: {self.name}'
    return s

