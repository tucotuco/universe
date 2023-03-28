#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2023 Rauthiflor LLC"
__version__ = "identifiable.py 2023-03-18T20:23-03:00"

# TODO:

import uuid
import json

class Identifiable:
    def __init__(self, name="", id=None):
        if id:
            self.id = id
        else:
            self.id = str(uuid.uuid4())
        self.name = name
        self.type = self.__class__.__name__

    def get_id(self):
        return self.id

    def to_json(self):
        '''
        Get a representation of a Identifiable as JSON.
        '''
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=2)

    def rename(self, new_name):
        self.name = new_name
