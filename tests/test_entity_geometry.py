#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Geometry and optical properties on existing physical Entities."""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath('../src'))

from being import BeingDefinition, BeingInstance
from object import ObjectDefinition, ObjectInstance
from spatial import (AxisAlignedBox, CartesianPosition, Sphere, VisualOcclusion)


P = CartesianPosition


class TestEntityGeometry(unittest.TestCase):
    def setUp(self):
        definition = ObjectDefinition('wall', 4, 0.25, 3, 50, 0, 10, 5)
        self.entity = ObjectInstance(definition, 'wall')

    def test_unmodeled_shape_is_not_inferred_from_legacy_dimensions(self):
        self.entity.set_position(P(0, 0, 0))
        self.assertIsNone(self.entity.geometry)
        self.assertIsNone(self.entity.spatial_bounds())
        self.assertFalse(self.entity.occupies_point(P(0, 0, 0)))
        self.assertIsNone(self.entity.segment_intersection(P(-1, 0, 0), P(1, 0, 0)))
        self.assertIsNone(self.entity.visual_occlusion)  # unknown, not transparent

    def test_shape_requires_placement_and_updates_after_movement(self):
        self.entity.set_geometry(AxisAlignedBox(4, .2, 3))
        self.entity.set_visual_occlusion(VisualOcclusion(1))
        self.assertIsNone(self.entity.spatial_bounds())
        self.assertIsNone(self.entity.segment_intersection(P(-5, 0, 0), P(5, 0, 0)))
        self.entity.set_position(P(10, 0, 0))
        self.assertEqual(self.entity.spatial_bounds().minimum, P(8, -.1, -1.5))
        self.assertTrue(self.entity.occupies_point(P(9, 0, 0)))
        self.assertEqual(self.entity.segment_intersection(P(0, 0, 0), P(20, 0, 0)),
                         (0.4, 0.6))
        self.entity.set_position(P(30, 0, 0))
        self.assertIsNone(self.entity.segment_intersection(P(0, 0, 0), P(20, 0, 0)))

    def test_geometry_and_visual_occlusion_are_independent(self):
        self.entity.set_position(P(0, 0, 0))
        self.entity.set_geometry(Sphere(2))
        self.assertIsNotNone(self.entity.segment_intersection(P(-4, 0, 0), P(4, 0, 0)))
        self.assertIsNone(self.entity.visual_occlusion)
        self.entity.set_visual_occlusion(VisualOcclusion(0))  # explicitly transparent
        self.assertFalse(self.entity.visual_occlusion.opaque)
        self.entity.set_visual_occlusion(VisualOcclusion(.4))
        self.assertFalse(self.entity.visual_occlusion.opaque)
        self.entity.set_visual_occlusion(VisualOcclusion(1))
        self.assertTrue(self.entity.visual_occlusion.opaque)
        self.assertIsNotNone(self.entity.segment_intersection(P(-4, 0, 0), P(4, 0, 0)))
        self.entity.set_geometry(None)
        self.assertIsNone(self.entity.segment_intersection(P(-4, 0, 0), P(4, 0, 0)))
        self.entity.set_visual_occlusion(None)
        self.assertIsNone(self.entity.visual_occlusion)

    def test_serialization_has_explicit_type(self):
        self.entity.set_geometry(Sphere(.5))
        self.entity.set_visual_occlusion(VisualOcclusion(.75))
        self.entity.set_position(P(1, 2, 3))
        data = json.loads(self.entity.to_json())
        self.assertEqual(data['geometry'], {'type': 'sphere', 'radius': 0.5})
        self.assertEqual(data['visual_occlusion'], {'opacity': 0.75})
        self.assertEqual(data['spatial_state']['position'],
                         {'x': 1.0, 'y': 2.0, 'z': 3.0})

    def test_shape_is_supported_by_beings(self):
        definition = BeingDefinition('human', 1.8, 70, 10, '1d8', 'N', 10, 1)
        being = BeingInstance(definition, 'fighter')
        being.set_geometry(Sphere(.35))
        being.set_position(P(0, 0, 0))
        self.assertTrue(being.occupies_point(P(.2, 0, 0)))
        self.assertIsNotNone(being.spatial_bounds())

    def test_type_checks(self):
        with self.assertRaises(TypeError):
            self.entity.set_geometry({'sphere': 2})
        with self.assertRaises(TypeError):
            self.entity.set_visual_occlusion(.8)
        with self.assertRaises(TypeError):
            self.entity.occupies_point((0, 0, 0))
        with self.assertRaises(TypeError):
            self.entity.segment_intersection((0, 0, 0), P(1, 0, 0))


if __name__ == '__main__':
    unittest.main()
