#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath('../src'))

from encounter import Encounter, EncounterInitiation
from library import Library
from spatial.state import CartesianPosition
from universe import Universe


class TestEncounterInitiation(unittest.TestCase):
    def setUp(self):
        self.universe = Universe(
            name="Test Universe",
            library=Library(config_dir="../src/config"),
        )
        self.encounter = Encounter(self.universe, 10, 0)
        self.observer_id = self.universe.make_being("Human", "Observer")
        self.other_id = self.universe.make_being("Human", "Other")
        self.object_id = self.universe.make_object("Brick", "Loose brick")

        self.encounter.add_being(self.observer_id)
        self.encounter.add_being(self.other_id)
        self.encounter.add_object(self.object_id)

        self.universe.get_object_by_id(self.observer_id).set_position(
            CartesianPosition(0, 0, 0)
        )
        self.universe.get_object_by_id(self.other_id).set_position(
            CartesianPosition(3, 4, 0)
        )
        self.universe.get_object_by_id(self.object_id).set_position(
            CartesianPosition(6, 8, 0)
        )

    def test_awareness_alone_does_not_initiate(self):
        self.encounter.perceive_within(self.observer_id, 5)
        self.assertTrue(self.encounter.is_aware(self.observer_id, self.other_id))
        self.assertFalse(self.encounter.initiated)
        self.assertIsNone(self.encounter.initiation)

    def test_aware_being_decision_initiates_encounter(self):
        self.encounter.perceive_within(self.observer_id, 5)
        initiation = self.encounter.decide_to_act(
            self.observer_id, self.other_id, intent="approach"
        )

        self.assertIsInstance(initiation, EncounterInitiation)
        self.assertTrue(self.encounter.initiated)
        self.assertEqual(initiation.actor_id, self.observer_id)
        self.assertEqual(initiation.target_id, self.other_id)
        self.assertEqual(initiation.intent, "approach")
        self.assertEqual(initiation.time, 0)

    def test_decision_requires_awareness(self):
        self.assertIsNone(
            self.encounter.decide_to_act(self.observer_id, self.other_id, "approach")
        )
        self.assertFalse(self.encounter.initiated)

    def test_non_being_entity_cannot_initiate(self):
        self.encounter.mark_aware(self.observer_id, self.object_id)
        self.assertIsNone(
            self.encounter.decide_to_act(self.object_id, self.observer_id, "act")
        )
        self.assertFalse(self.encounter.initiated)

    def test_object_may_be_initiation_target(self):
        self.encounter.perceive_within(self.observer_id, 10)
        initiation = self.encounter.decide_to_act(
            self.observer_id, self.object_id, intent="inspect"
        )
        self.assertIsNotNone(initiation)
        self.assertEqual(initiation.target_id, self.object_id)
        self.assertEqual(initiation.intent, "inspect")

    def test_first_initiating_decision_is_retained(self):
        self.encounter.perceive_within(self.observer_id, 10)
        first = self.encounter.decide_to_act(
            self.observer_id, self.other_id, intent="approach"
        )
        second = self.encounter.decide_to_act(
            self.observer_id, self.object_id, intent="inspect"
        )
        self.assertIsNone(second)
        self.assertIs(self.encounter.initiation, first)

    def test_initiation_serializes(self):
        self.encounter.perceive_within(self.observer_id, 5)
        self.encounter.decide_to_act(self.observer_id, self.other_id, "approach")
        data = json.loads(self.encounter.to_json())

        self.assertTrue(data["initiated"])
        self.assertEqual(data["time"], 0)
        self.assertEqual(
            data["initiation"],
            {
                "actor_id": self.observer_id,
                "target_id": self.other_id,
                "intent": "approach",
                "time": 0,
            },
        )

    def test_intent_validation(self):
        self.encounter.perceive_within(self.observer_id, 5)
        with self.assertRaises(TypeError):
            self.encounter.decide_to_act(self.observer_id, self.other_id, None)
        with self.assertRaises(ValueError):
            self.encounter.decide_to_act(self.observer_id, self.other_id, "   ")


if __name__ == '__main__':
    unittest.main()
