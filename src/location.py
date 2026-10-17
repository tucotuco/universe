#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "John Wieczorek"
__copyright__ = "Copyright 2024 Rauthiflor LLC"
__version__ = "location.py 2024-05-12T15:52-03:00"

# TODO: 

#import json

from identifiable import Identifiable

class Location(Identifiable):
    '''
    A Location defined in terms of a hierarchical system of spherical equilateral 
    triangles filling the faces of a regular icosahedron, simulating a circumscribed 
    sphere with accuracy increasing with increasing levels of triangle subdivision. The 
    vertices and edges of every triangle are on the surface of the sphere. The coordinate 
    system consists of a letter (A-T) designating the icosahedral cell followed by any 
    number of digits. Each digit is an integer in the set [1,3,4,5,6,7] corresponding to 
    one of the four interior triangles at that subdivision level. The position of each 
    subdivision triangle within it enclosing triangle based on the integer is given by:
    1 - north (only in a north-pointing triangle)
    2 - southwest corner (only in a north-pointing triangle)
    3 - south center (only in a north-pointing triangle)
    4 - south east corner (only in a north-pointing triangle)
    5 - northeast corner (only in a south-pointing triangle)
    6 - north center (only in a south-pointing triangle)
    7 - northwest corner (only in a south-pointing triangle)
    8 - south  (only in a south-pointing triangle)
    Triangles with indices 1, 2, 3, and 4 occupy an enclosing triangle that points north.
    Triangles with indices 5, 6, 7, and 8 occupy an enclosing triangle that points south.
    Triangles with indices 1, 2, 4, and 6 have a vertex pointing north.
    Triangles with indices 3, 5, 7, and 8 have a vertex pointing south.
    '''
    def __init__(self, id, name=None, worldname=None):
        Identifiable.__init__(self, name, id)
        self.worldname = worldname

    def to_json(self):
        def handle_circular_refs(obj):
            from library import Library
            from universe import Universe
            if isinstance(obj, (Library, Universe)):
                return obj.id  # Return only the ID for Universe and Event instances
            return obj.__dict__

        data = {
            "worldname": self.worldname,
            "name": self.name,
            "id": self.id
        }
        return json.dumps(data, default=handle_circular_refs, sort_keys=False, indent=2)

    def to_lat_long(self, location_id):
    
    def from_lat_long(self, lat, long):
    
    def to_ne(self):
