#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath('../src'))

from encounter import Encounter
from library import Library
from spatial.state import CartesianPosition
from universe import Universe


class TestEncounterSpatialBridge(unittest.TestCase):
    def setUp(self):
        self.universe = Universe(
            name="Test Universe",
            library=Library(config_dir="../src/config"),
        )
        self.encounter = Encounter(self.universe, 10, 0)
        self.a_id = self.universe.make_being("Human", "A")
        self.b_id = self.universe.make_being("Human", "B")
        self.c_id = self.universe.make_being("Human", "C")
        self.object_id = self.universe.make_object("Brick", "Loose brick")
        for being_id in (self.a_id, self.b_id, self.c_id):
            self.encounter.add_being(being_id)
        self.encounter.add_object(self.object_id)

        self.a = self.universe.get_object_by_id(self.a_id)
        self.b = self.universe.get_object_by_id(self.b_id)
        self.c = self.universe.get_object_by_id(self.c_id)
        self.obj = self.universe.get_object_by_id(self.object_id)
        self.a.set_position(CartesianPosition(0, 0, 0))
        self.b.set_position(CartesianPosition(3, 4, 0))
        self.c.set_position(CartesianPosition(30, 40, 0))
        self.obj.set_position(CartesianPosition(6, 8, 0))

    def test_distance_uses_continuous_positions(self):
        self.assertEqual(self.encounter.distance_between_beings(self.a_id, self.b_id), 5.0)
        self.assertEqual(self.encounter.distance_between_beings(self.a_id, self.c_id), 50.0)

    def test_within_distance_and_candidate_list(self):
        self.assertTrue(self.encounter.within_distance(self.a_id, self.b_id, 5))
        self.assertFalse(self.encounter.within_distance(self.a_id, self.b_id, 4.999))
        self.assertEqual(self.encounter.beings_within(self.a_id, 5), [self.b_id])
        self.assertEqual(self.encounter.beings_within(self.a_id, 50), [self.b_id, self.c_id])


    def test_entity_queries_include_non_being_objects(self):
        self.assertEqual(
            self.encounter.distance_between_entities(self.a_id, self.object_id),
            10.0,
        )
        self.assertTrue(self.encounter.entity_within(self.a_id, self.object_id, 10))
        self.assertFalse(self.encounter.entity_within(self.a_id, self.object_id, 9.999))
        self.assertEqual(
            self.encounter.entities_within(self.a_id, 10),
            [self.b_id, self.object_id],
        )
        self.assertEqual(self.encounter.beings_within(self.a_id, 10), [self.b_id])
        self.assertEqual(self.encounter.objects_within(self.a_id, 10), [self.object_id])

    def test_being_can_be_aware_of_non_being_object(self):
        self.assertTrue(self.encounter.mark_aware(self.a_id, self.object_id))
        self.assertTrue(self.encounter.is_aware(self.a_id, self.object_id))
        self.assertEqual(self.encounter.aware_entities(self.a_id), [self.object_id])
        self.assertEqual(self.encounter.aware_objects(self.a_id), [self.object_id])
        self.assertEqual(self.encounter.aware_beings(self.a_id), [])

        # Non-Being Objects can be perceived, but they are not observers.
        self.assertFalse(self.encounter.mark_aware(self.object_id, self.a_id))

    def test_constructor_preserves_explicit_object_list(self):
        encounter = Encounter(
            self.universe,
            10,
            0,
            being_list=[self.a_id],
            non_being_object_list=[self.object_id],
        )
        self.assertEqual(encounter.entity_ids(), [self.a_id, self.object_id])

    def test_unplaced_being_has_no_distance(self):
        self.c.set_spatial_state(None)
        self.assertIsNone(self.encounter.distance_between_beings(self.a_id, self.c_id))
        self.assertFalse(self.encounter.within_distance(self.a_id, self.c_id, 1000))
        self.assertNotIn(self.c_id, self.encounter.beings_within(self.a_id, 1000))

    def test_awareness_is_directed_and_independent_of_proximity(self):
        self.assertFalse(self.encounter.is_aware(self.a_id, self.b_id))
        self.assertFalse(self.encounter.is_aware(self.b_id, self.a_id))

        self.assertTrue(self.encounter.mark_aware(self.a_id, self.b_id))
        self.assertTrue(self.encounter.is_aware(self.a_id, self.b_id))
        self.assertFalse(self.encounter.is_aware(self.b_id, self.a_id))
        self.assertEqual(self.encounter.aware_beings(self.a_id), [self.b_id])

        # Awareness does not disappear merely because physical distance changes.
        self.b.set_position(CartesianPosition(3000, 4000, 0))
        self.assertEqual(self.encounter.distance_between_beings(self.a_id, self.b_id), 5000.0)
        self.assertTrue(self.encounter.is_aware(self.a_id, self.b_id))

    def test_clear_awareness(self):
        self.encounter.mark_aware(self.a_id, self.b_id)
        self.assertTrue(self.encounter.clear_awareness(self.a_id, self.b_id))
        self.assertFalse(self.encounter.is_aware(self.a_id, self.b_id))
        self.assertFalse(self.encounter.clear_awareness(self.a_id, self.b_id))

    def test_awareness_serializes_as_lists(self):
        self.encounter.mark_aware(self.a_id, self.b_id)
        data = json.loads(self.encounter.to_json())
        self.assertEqual(data["awareness"][self.a_id], [self.b_id])

    def test_distance_validation(self):
        with self.assertRaises(ValueError):
            self.encounter.within_distance(self.a_id, self.b_id, -1)
        with self.assertRaises(ValueError):
            self.encounter.within_distance(self.a_id, self.b_id, float("inf"))
        with self.assertRaises(TypeError):
            self.encounter.within_distance(self.a_id, self.b_id, "near")


if __name__ == '__main__':
    unittest.main()
