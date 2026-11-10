#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Physical geometry tests independent of any spatial indexing grid."""

import unittest
import os
import sys

sys.path.insert(0, os.path.abspath('../src'))

from spatial import (AxisAlignedBox, Bounds3D, CartesianPosition, Sphere,
                     geometry_from_dict, VisualOcclusion)


P = CartesianPosition


class TestSphere(unittest.TestCase):
    def test_radius_is_truncated_at_authoritative_geometry_creation(self):
        self.assertEqual(Sphere(1.239).radius, 1.23)
        with self.assertRaises(ValueError):
            Sphere(0.009)

    def test_containment_and_bounds_are_continuous(self):
        shape = Sphere(2)
        center = P(100, 20, -30)
        self.assertTrue(shape.contains(P(102, 20, -30), center))
        self.assertFalse(shape.contains(P(102.01, 20, -30), center))
        box = shape.bounds(center)
        self.assertEqual(box, Bounds3D(P(98, 18, -32), P(102, 22, -28)))
        self.assertTrue(box.contains(P(100, 21, -30)))
        self.assertFalse(box.contains(P(100, 23, -30)))

    def test_segment_crossing_tangent_and_miss(self):
        shape, center = Sphere(1), P(10, 0, 0)
        self.assertEqual(shape.segment_interval(P(8, 0, 0), P(12, 0, 0), center),
                         (0.25, 0.75))
        self.assertEqual(shape.segment_interval(P(8, 1, 0), P(12, 1, 0), center),
                         (0.5, 0.5))
        self.assertIsNone(shape.segment_interval(P(8, 2, 0), P(12, 2, 0), center))
        self.assertIsNone(shape.segment_interval(P(0, 0, 0), P(1, 0, 0), center))

    def test_inside_and_degenerate_segments(self):
        shape, center = Sphere(2), P(0, 0, 0)
        self.assertEqual(shape.segment_interval(P(-1, 0, 0), P(1, 0, 0), center), (0, 1))
        self.assertEqual(shape.segment_interval(P(0, 0, 0), P(0, 0, 0), center), (0, 0))
        self.assertIsNone(shape.segment_interval(P(4, 0, 0), P(4, 0, 0), center))
        self.assertEqual(shape.segment_interval(P(2, 0, 0), P(3, 0, 0), center), (0, 0))

    def test_invalid_radius_and_input(self):
        for value in (0, -1, float('nan'), float('inf')):
            with self.subTest(radius=value), self.assertRaises(ValueError):
                Sphere(value)
        with self.assertRaises(TypeError):
            Sphere(None)
        with self.assertRaises(TypeError):
            Sphere(1).bounds((0, 0, 0))


class TestBox(unittest.TestCase):
    def test_axis_lengths_are_truncated_at_authoritative_geometry_creation(self):
        self.assertEqual(AxisAlignedBox(1.239, 2.349, 3.459),
                         AxisAlignedBox(1.23, 2.34, 3.45))

    def test_containment_bounds_and_segment(self):
        shape, center = AxisAlignedBox(4, 2, 6), P(50, 10, 20)
        self.assertEqual(shape.bounds(center),
                         Bounds3D(P(48, 9, 17), P(52, 11, 23)))
        self.assertTrue(shape.contains(P(52, 11, 23), center))
        self.assertFalse(shape.contains(P(52.001, 10, 20), center))
        self.assertEqual(shape.segment_interval(P(46, 10, 20), P(54, 10, 20), center),
                         (0.25, 0.75))
        self.assertEqual(shape.segment_interval(P(50, 10, 20), P(54, 10, 20), center),
                         (0, 0.5))
        self.assertEqual(shape.segment_interval(P(50, 10, 20), P(50, 10, 20), center), (0, 1))
        self.assertIsNone(shape.segment_interval(P(46, 12, 20), P(54, 12, 20), center))
        # A corner contact counts as a geometric intersection.
        self.assertEqual(shape.segment_interval(P(46, 7, 20), P(50, 9, 20), center),
                         (1.0, 1.0))

    def test_parallel_and_unplaced_validation(self):
        box = AxisAlignedBox(2, 2, 2)
        self.assertIsNone(box.segment_interval(P(0, 3, 0), P(0, 4, 0), P(0, 0, 0)))
        self.assertEqual(box.segment_interval(P(1, 0, 0), P(2, 0, 0), P(0, 0, 0)), (0, 0))
        with self.assertRaises(TypeError):
            box.segment_interval((0, 0, 0), P(0, 0, 0), P(0, 0, 0))

    def test_invalid_dimensions(self):
        for value in (0, -0.1, float('nan'), float('inf')):
            with self.subTest(size=value), self.assertRaises(ValueError):
                AxisAlignedBox(1, value, 2)
        with self.assertRaises(TypeError):
            AxisAlignedBox(1, 'abc', 2)


class TestGeometryMetadata(unittest.TestCase):
    def test_shape_serialization_is_explicit_and_roundtrips(self):
        for shape in (Sphere(1.5), AxisAlignedBox(2, 4, 6)):
            with self.subTest(shape=shape):
                self.assertEqual(geometry_from_dict(shape.to_dict()), shape)
        with self.assertRaises(ValueError):
            geometry_from_dict({"type": "unknown"})
        with self.assertRaises(TypeError):
            geometry_from_dict(None)

    def test_visual_opacity_is_independent_of_geometry(self):
        self.assertEqual(VisualOcclusion().opacity, 0)
        self.assertFalse(VisualOcclusion().opaque)
        self.assertEqual(VisualOcclusion(0.3).to_dict(), {'opacity': 0.3})
        self.assertTrue(VisualOcclusion(1).opaque)
        for value in (-0.001, 1.001, float('nan'), float('inf')):
            with self.subTest(opacity=value), self.assertRaises(ValueError):
                VisualOcclusion(value)
        with self.assertRaises(TypeError):
            VisualOcclusion('opaque')


if __name__ == '__main__':
    unittest.main()
