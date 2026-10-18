#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for local physical reference frames independent of the spatial grid."""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath('../src'))

from spatial.frame import LocalFrame, LocalPosition
from spatial.state import CartesianPosition


class TestLocalFrame(unittest.TestCase):
    def assert_position_near(self, first, second, places=7):
        for a, b in zip(first.as_tuple(), second.as_tuple()):
            self.assertAlmostEqual(a, b, places=places)

    def test_aligned_frame_translation_and_inverse(self):
        frame = LocalFrame.aligned_at(CartesianPosition(10, 20, 30))
        world = CartesianPosition(11, 18, 35)
        local = frame.to_local(world)
        self.assertIsInstance(local, LocalPosition)
        self.assertEqual(local, LocalPosition(1, -2, 5))
        self.assertEqual(frame.to_global(local), world)
        self.assert_position_near(frame.to_global(frame.to_local(world)), world)

    def test_orthonormal_rotation_is_reversible_and_preserves_3d_distance(self):
        frame = LocalFrame(CartesianPosition(10, -4, 20),
                           (0, 1, 0), (0, 0, 1), (1, 0, 0))
        first = CartesianPosition(12, 4, 17)
        second = CartesianPosition(17, 0, 29)
        local_first = frame.to_local(first)
        local_second = frame.to_local(second)
        self.assertEqual(local_first, LocalPosition(8, -3, 2))
        self.assertEqual(local_second, LocalPosition(4, 9, 7))
        self.assertEqual(frame.to_global(local_first), first)
        self.assertEqual(frame.to_global(local_second), second)
        global_distance = math.dist(first.as_tuple(), second.as_tuple())
        local_distance = math.dist(local_first.as_tuple(), local_second.as_tuple())
        self.assertAlmostEqual(global_distance, local_distance)
        vector = (3, 2, -5)
        self.assertEqual(frame.vector_to_global(frame.vector_to_local(vector)), vector)

    def test_spherical_tangent_east_north_up(self):
        center = CartesianPosition(500, -30, 100)
        radial_position = CartesianPosition(1500, -30, 100)
        frame = LocalFrame.tangent_at(radial_position, center)
        self.assert_position_near(frame.to_global(LocalPosition(0, 0, 0)), radial_position)
        self.assertEqual(frame.vector_to_global((1, 0, 0)), (0, 1, 0))
        self.assert_position_near(frame.to_global(LocalPosition(10, 20, 30)),
                                  CartesianPosition(1530, -20, 120))
        self.assertEqual(frame.to_local(CartesianPosition(1530, -20, 120)),
                         LocalPosition(10, 20, 30))

    def test_planetary_scale_coordinates_preserve_small_local_offsets(self):
        surface = CartesianPosition(6371000, 0, 0)
        frame = LocalFrame.tangent_at(surface)
        target = frame.to_global(LocalPosition(0.01, -0.02, 0.03))
        reconstructed = frame.to_local(target)
        for original, actual in zip((0.01, -0.02, 0.03), reconstructed.as_tuple()):
            self.assertAlmostEqual(original, actual, places=7)

    def test_tangent_frame_at_pole_is_well_defined(self):
        frame = LocalFrame.tangent_at(CartesianPosition(0, 0, 1000))
        position = CartesianPosition(2, 3, 1005)
        self.assert_position_near(frame.to_global(frame.to_local(position)), position)

    def test_origin_and_axes_survive_json_compatible_serialization(self):
        frame = LocalFrame.tangent_at(CartesianPosition(10, 20, 30),
                                      CartesianPosition(0, 0, 0))
        self.assertEqual(LocalFrame.from_dict(frame.to_dict()), frame)
        self.assertIsInstance(frame.to_dict()['origin'], list)

    def test_invalid_coordinate_frames_are_rejected(self):
        with self.assertRaises(TypeError):
            LocalFrame.aligned_at((0, 0, 0))
        with self.assertRaises(ValueError):
            LocalFrame.tangent_at(CartesianPosition(0, 0, 0))
        with self.assertRaises(ValueError):
            LocalFrame(CartesianPosition(0, 0, 0),
                       (1, 0, 0), (1, 0, 0), (0, 0, 1))
        with self.assertRaises(ValueError):
            LocalFrame(CartesianPosition(0, 0, 0),
                       (1, 0, 0), (0, 1, 0), (0, 0, -1))
        with self.assertRaises(ValueError):
            LocalFrame(CartesianPosition(0, 0, 0),
                       (2, 0, 0), (0, 1, 0), (0, 0, 1))
        with self.assertRaises(ValueError):
            LocalPosition(math.nan, 0, 0)
        with self.assertRaises(ValueError):
            LocalFrame.aligned_at(CartesianPosition(0, 0, 0)).vector_to_local(
                (math.inf, 0, 0))
        frame = LocalFrame.aligned_at(CartesianPosition(0, 0, 0))
        with self.assertRaises(TypeError):
            frame.to_global(CartesianPosition(1, 2, 3))
        with self.assertRaises(TypeError):
            frame.to_local(LocalPosition(1, 2, 3))


if __name__ == '__main__':
    unittest.main()
