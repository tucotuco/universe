#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Encounter uses explicit 3D geometry for a bounded sightline query."""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath('../src'))

from encounter import Encounter
from library import Library
from perception import GeometricPathPerception
from spatial import AxisAlignedBox, CartesianPosition, LocalFrame, Sphere, VisualOcclusion
from universe import Universe

P = CartesianPosition


class TestEncounterVisibility(unittest.TestCase):
    def setUp(self):
        self.world = Universe(name='Test', library=Library(config_dir='../src/config'))
        self.encounter = Encounter(self.world, 10, 0)
        self.observer_id = self.world.make_being('Human', 'Observer')
        self.target_id = self.world.make_being('Human', 'Target')
        self.wall_id = self.world.make_object('Brick', 'Occluder')
        self.encounter.add_being(self.observer_id)
        self.encounter.add_being(self.target_id)
        self.encounter.add_object(self.wall_id)
        self.observer = self.world.get_object_by_id(self.observer_id)
        self.target = self.world.get_object_by_id(self.target_id)
        self.wall = self.world.get_object_by_id(self.wall_id)
        self.observer.set_position(P(0, 0, 0))
        self.target.set_position(P(10, 0, 0))
        self.target.set_geometry(Sphere(.5))
        self.wall.set_position(P(5, 0, 0))
        self.wall.set_geometry(AxisAlignedBox(1, 2, 2))
        self.wall.set_visual_occlusion(VisualOcclusion(1))

    def test_blocker_prevents_opt_in_path_perception(self):
        result = self.encounter.line_of_sight(self.observer_id, self.target_id)
        self.assertEqual(result.status, 'blocked')
        self.assertEqual(result.intersections[0].entity_id, self.wall_id)
        self.assertFalse(self.encounter.is_aware(self.observer_id, self.target_id))
        observations = self.encounter.perceive(self.observer_id,
                                               GeometricPathPerception(15))
        self.assertNotIn(self.target_id, [o.target_id for o in observations])
        self.assertFalse(self.encounter.is_aware(self.observer_id, self.target_id))

    def test_move_blocker_out_of_path_and_acquire_awareness(self):
        self.wall.set_position(P(5, 3, 0))
        result = self.encounter.line_of_sight(self.observer_id, self.target_id)
        self.assertTrue(result.clear)
        observations = self.encounter.perceive_geometric_paths(self.observer_id, 15)
        self.assertEqual([o.target_id for o in observations], [self.target_id, self.wall_id])
        self.assertTrue(all(o.mode == 'geometric_path_only' for o in observations))
        self.assertTrue(self.encounter.is_aware(self.observer_id, self.target_id))
        self.assertFalse(self.encounter.is_aware(self.target_id, self.observer_id))

    def test_unknown_or_partial_obstruction_yields_no_claim_of_clear_path(self):
        self.wall.set_visual_occlusion(None)
        self.assertEqual(self.encounter.line_of_sight(self.observer_id,
                                                      self.target_id).status, 'unknown')
        self.assertFalse(any(o.target_id == self.target_id for o in
                             self.encounter.perceive_geometric_paths(self.observer_id, 15)))
        self.wall.set_visual_occlusion(VisualOcclusion(.25))
        self.assertEqual(self.encounter.line_of_sight(self.observer_id,
                                                      self.target_id).status, 'partial')
        self.assertFalse(any(o.target_id == self.target_id for o in
                             self.encounter.perceive_geometric_paths(self.observer_id, 15)))

    def test_no_shape_never_means_transparent_target_in_perception(self):
        self.target.set_geometry(None)
        self.wall.set_position(P(5, 3, 0))
        observations = self.encounter.perceive_geometric_paths(self.observer_id, 15)
        self.assertNotIn(self.target_id, [o.target_id for o in observations])

    def test_local_frame_does_not_change_global_visibility(self):
        result = self.encounter.line_of_sight(self.observer_id, self.target_id)
        self.encounter.set_local_frame(LocalFrame.aligned_at(P(100, -20, 7)))
        self.assertEqual(result, self.encounter.line_of_sight(self.observer_id,
                                                               self.target_id))

    def test_explicit_sightline_can_aim_above_obstacle(self):
        self.assertEqual(self.encounter.line_of_sight(self.observer_id,
                                                      self.target_id).status, 'blocked')
        result = self.encounter.line_of_sight(self.observer_id, self.target_id,
                                             source_point=P(0, 0, 3),
                                             target_point=P(10, 0, 3))
        self.assertTrue(result.clear)

    def test_unplaced_and_invalid_entity(self):
        self.assertIsNone(self.encounter.line_of_sight('missing', self.target_id))
        self.target.set_spatial_state(None)
        self.assertIsNone(self.encounter.line_of_sight(self.observer_id, self.target_id))
        with self.assertRaises(TypeError):
            self.encounter.line_of_sight(self.observer_id, self.target_id,
                                         source_point=(0, 0, 0))


if __name__ == '__main__':
    unittest.main()
