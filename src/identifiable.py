#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2023 Rauthiflor LLC"
__version__ = "identifiable.py 2023-12-27T13:12-03:00"

# TODO:

import uuid
import json

class Identifiable:
    '''
    Something that has an optional name and a unique identifier.
    '''
    def __init__(self, name=None, id=None):
        if id:
            self.id = id
        else:
            self.id = str(uuid.uuid4())
        self.name = name
        self.type = self.__class__.__name__

    def get_id(self):
        '''
        Get the value of the identifier for the instance.
        '''
        return self.id

    def to_json(self):
        '''
        Get a representation of an Identifiable as JSON.
        '''
        # Specify properties in a particular order
        data = {
            "type": self.type,
            "name": self.name,
            "id": self.id,
        }
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=2)

    def set_name(self, new_name):
        '''
        Set the value of the name.
        '''
        self.name = new_name
