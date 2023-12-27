#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2023 Rauthiflor LLC"
__version__ = "test_identifiable.py 2023-03-30T02:11-03:00"

# TODO: Check comprehensiveness

import unittest
import uuid
import sys
import os

sys.path.insert(0, os.path.abspath('../src'))
#print(f'{__version__}:{sys.path}')

from identifiable import Identifiable

class TestIdentifiable(unittest.TestCase):
    def test_id_generation(self):
        id1 = Identifiable().id
        id2 = Identifiable().id
        self.assertNotEqual(id1, id2)
    
    def test_id_assignment(self):
        provided_uuid = str(uuid.uuid4())
        id = Identifiable(id=provided_uuid).id
        self.assertEqual(id, provided_uuid)
    
    def test_name_assignment(self):
        name = "Test Name"
        identifiable = Identifiable(name=name)
        self.assertEqual(identifiable.name, name)
        name = "New Name"
        identifiable.set_name(name)
        self.assertEqual(identifiable.name, name)
    
    def test_type_assignment(self):
        identifiable = Identifiable()
        self.assertEqual(identifiable.type, "Identifiable")

if __name__ == '__main__':
    unittest.main()
