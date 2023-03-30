#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2023 Rauthiflor LLC"
__version__ = "world.py 2023-03-30T01:23-03:00"

# TODO: Everything
# TODO: Make ''' comments on classes and methods

# Refer to Triangular Mesh Grid system: https://tinyurl.com/tri-mesh-grid
class WorldMap:
    '''
    The spatial context of a World.
    How the WorldMap is populated over time can change, but it's structure does not. It is
    the coordinate reference system of a World.
    '''
    def __init__(self, x, y):
        self.x = x
        self.y = y

    # Create a new WorldMap.
    def generate(self):
        pass
