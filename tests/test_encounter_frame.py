#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Encounter-local views do not overwrite the authoritative global positions."""

import json
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath('../src'))

from encounter import Encounter
from library import Library
from spatial.frame import LocalFrame, LocalPosition
from spatial.state import CartesianPosition
from universe import Universe


class TestEncounterLocalFrame(unittest.TestCase):
    def setUp(self):
        self.universe = Universe('Frame test', library=Library(config_dir='../src/config'))
        self.encounter = Encounter(self.universe, 10, 0)
        self.being_id = self.universe.make_being('Human', 'Traveler')
        self.object_id = self.universe.make_object('Brick', 'Marker')
        self.encounter.add_being(self.being_id)
        self.encounter.add_object(self.object_id)
        self.being = self.universe.get_object_by_id(self.being_id)
        self.marker = self.universe.get_object_by_id(self.object_id)
        self.being.set_position(CartesianPosition(1000, 0, 0))
        self.marker.set_position(CartesianPosition(1000, 20, 5))

    def initiate(self):
        self.encounter.mark_aware(self.being_id, self.object_id)
        self.encounter.decide_to_act(self.being_id, self.object_id, 'approach')

    def test_local_frame_views_being_and_object_without_changing_state(self):
        before_being = self.being.get_position()
        before_marker = self.marker.get_position()
        self.encounter.set_local_frame(LocalFrame.tangent_at(before_being))
        self.assertEqual(self.encounter.entity_local_position(self.being_id),
                         LocalPosition(0, 0, 0))
        self.assertEqual(self.encounter.entity_local_position(self.object_id),
                         LocalPosition(20, 5, 0))
        with self.assertRaises(TypeError):
            self.being.set_position(self.encounter.entity_local_position(self.being_id))
        self.assertEqual(self.encounter.global_position(LocalPosition(20, 5, 0)),
                         before_marker)
        self.assertEqual(self.encounter.distance_between_entities(
            self.being_id, self.object_id), math.hypot(20, 5))
        self.assertEqual(self.being.get_position(), before_being)
        self.assertEqual(self.marker.get_position(), before_marker)
        self.assertEqual(self.encounter.entity_local_position('missing'), None)
        self.assertEqual(json.loads(self.encounter.to_json())['local_frame'],
                         self.encounter.local_frame.to_dict())

    def test_locally_expressed_velocity_changes_only_global_position(self):
        self.encounter.set_local_frame(LocalFrame.tangent_at(self.being.get_position()))
        self.initiate()
        result = self.encounter.step(duration=2, velocities={
            self.being_id: (4, 2, 1),
            self.object_id: (-1, 0, 0),
        }, velocity_frame='local')
        self.assertEqual(result.moved_entity_ids, (self.being_id, self.object_id))
        self.assertEqual(self.encounter.entity_local_position(self.being_id),
                         LocalPosition(8, 4, 2))
        self.assertEqual(self.encounter.entity_local_position(self.object_id),
                         LocalPosition(18, 5, 0))
        self.assertEqual(self.being.get_position(), CartesianPosition(1002, 8, 4))
        self.assertEqual(self.marker.get_position(), CartesianPosition(1000, 18, 5))

    def test_existing_global_motion_remains_global_with_local_frame_attached(self):
        self.encounter.set_local_frame(LocalFrame.tangent_at(self.being.get_position()))
        self.initiate()
        self.encounter.step(velocities={self.being_id: (1, 2, 3)})
        self.assertEqual(self.being.get_position(), CartesianPosition(1001, 2, 3))
        self.assertEqual(self.encounter.entity_local_position(self.being_id),
                         LocalPosition(2, 3, 1))

    def test_missing_frame_and_invalid_local_velocity_do_not_move_entities(self):
        initial = self.being.get_position()
        self.initiate()
        with self.assertRaises(RuntimeError):
            self.encounter.entity_local_position(self.being_id)
        with self.assertRaises(RuntimeError):
            self.encounter.global_position(LocalPosition(0, 0, 0))
        with self.assertRaises(RuntimeError):
            self.encounter.step(velocities={self.being_id: (1, 0, 0)},
                                velocity_frame='local')
        with self.assertRaises(ValueError):
            self.encounter.step(velocity_frame='planetary')
        self.assertEqual(self.being.get_position(), initial)
        with self.assertRaises(TypeError):
            self.encounter.set_local_frame('not a frame')
        frame = LocalFrame.aligned_at(initial)
        self.encounter.set_local_frame(frame)
        with self.assertRaises(ValueError):
            self.encounter.step(velocities={
                self.being_id: (1, 0, 0), self.object_id: (math.inf, 0, 0)
            }, velocity_frame='local')
        self.assertEqual(self.being.get_position(), initial)
        self.encounter.set_local_frame(None)
        self.assertIsNone(json.loads(self.encounter.to_json())['local_frame'])


if __name__ == '__main__':
    unittest.main()
