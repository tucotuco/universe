#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2023 Rauthiflor LLC"
__version__ = "world.py 2023-01-02T15:43-03:00"

# TODO: Everything

# A WorldMap defines the spatial context of a World. How the world is populated over time
# can change, but it's dimensions do not.
# Refer to Triangular Mesh Grid system: https://tinyurl.com/tri-mesh-grid
class WorldMap:
  def __init__(self, x, y):
    self.x = x
    self.y = y

  # Create a new WorldMap.
  def generate(self):
    pass
