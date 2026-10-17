#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath('../src'))

from encounter import Encounter
from library import Library
from perception import RangePerception
from spatial.state import CartesianPosition
from universe import Universe


class TestMinimalPerception(unittest.TestCase):
    def setUp(self):
        self.universe = Universe(
            name="Test Universe",
            library=Library(config_dir="../src/config"),
        )
        self.encounter = Encounter(self.universe, 10, 0)
        self.observer_id = self.universe.make_being("Human", "Observer")
        self.near_being_id = self.universe.make_being("Human", "Near being")
        self.far_being_id = self.universe.make_being("Human", "Far being")
        self.object_id = self.universe.make_object("Brick", "Loose brick")

        for being_id in (self.observer_id, self.near_being_id, self.far_being_id):
            self.encounter.add_being(being_id)
        self.encounter.add_object(self.object_id)

        self.observer = self.universe.get_object_by_id(self.observer_id)
        self.near_being = self.universe.get_object_by_id(self.near_being_id)
        self.far_being = self.universe.get_object_by_id(self.far_being_id)
        self.obj = self.universe.get_object_by_id(self.object_id)

        self.observer.set_position(CartesianPosition(0, 0, 0))
        self.near_being.set_position(CartesianPosition(3, 4, 0))       # 5
        self.obj.set_position(CartesianPosition(6, 8, 0))              # 10
        self.far_being.set_position(CartesianPosition(30, 40, 0))      # 50

    def test_range_perception_detects_entities_and_creates_awareness(self):
        observations = self.encounter.perceive_within(self.observer_id, 10)

        self.assertEqual(
            [observation.target_id for observation in observations],
            [self.near_being_id, self.object_id],
        )
        self.assertTrue(self.encounter.is_aware(self.observer_id, self.near_being_id))
        self.assertTrue(self.encounter.is_aware(self.observer_id, self.object_id))
        self.assertFalse(self.encounter.is_aware(self.observer_id, self.far_being_id))

    def test_perception_records_explicit_range_basis(self):
        observations = self.encounter.perceive_within(self.observer_id, 5)
        self.assertEqual(len(observations), 1)
        observation = observations[0]
        self.assertEqual(observation.mode, "range")
        self.assertEqual(observation.distance, 5.0)
        self.assertEqual(observation.threshold, 5.0)

    def test_perception_is_directed(self):
        self.encounter.perceive_within(self.observer_id, 10)
        self.assertTrue(self.encounter.is_aware(self.observer_id, self.near_being_id))
        self.assertFalse(self.encounter.is_aware(self.near_being_id, self.observer_id))

    def test_detection_does_not_mutate_awareness_until_encounter_applies_it(self):
        model = RangePerception(10)
        observations = model.detect(self.encounter, self.observer_id)
        self.assertEqual(len(observations), 2)
        self.assertEqual(self.encounter.aware_entities(self.observer_id), [])

    def test_unplaced_entities_are_not_detected(self):
        self.obj.set_spatial_state(None)
        observations = self.encounter.perceive_within(self.observer_id, 10)
        self.assertEqual(
            [observation.target_id for observation in observations],
            [self.near_being_id],
        )

    def test_non_being_entity_cannot_be_observer(self):
        self.assertEqual(self.encounter.perceive_within(self.object_id, 100), [])

    def test_range_validation(self):
        with self.assertRaises(ValueError):
            RangePerception(-1)
        with self.assertRaises(ValueError):
            RangePerception(float("inf"))
        with self.assertRaises(TypeError):
            RangePerception("near")


if __name__ == '__main__':
    unittest.main()
