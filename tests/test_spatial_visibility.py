#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Sightline intersection uses continuous 3D geometry, not cell adjacency."""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath('../src'))

from object import ObjectDefinition, ObjectInstance
from spatial import (AxisAlignedBox, CartesianPosition, Sphere,
                     VisualOcclusion, trace_sightline)

P = CartesianPosition


class TestSightline(unittest.TestCase):
    def obstacle(self, name, position, geometry=None, opacity=None):
        entity = ObjectInstance(ObjectDefinition('test', 1, 1, 1, 1, 0, 0, 1), name)
        entity.set_position(position)
        entity.set_geometry(geometry)
        if opacity is not None:
            entity.set_visual_occlusion(VisualOcclusion(opacity))
        return entity

    def trace(self, *candidates):
        return trace_sightline(P(0, 0, 0), P(10, 0, 0), candidates)

    def test_empty_scene_and_objects_outside_segment(self):
        self.assertTrue(self.trace().clear)
        behind = self.obstacle('behind', P(-3, 0, 0), Sphere(.5), 1)
        beyond = self.obstacle('beyond', P(12, 0, 0), Sphere(.5), 1)
        off_axis = self.obstacle('off', P(5, 4, 0), Sphere(.5), 1)
        result = self.trace(('behind', behind), ('beyond', beyond), ('off', off_axis))
        self.assertEqual(result.status, 'clear')
        self.assertFalse(result.intersections)

    def test_opaque_blocker_and_fractional_intersection(self):
        obstacle = self.obstacle('wall', P(5, 0, 0), AxisAlignedBox(2, 2, 2), 1)
        result = self.trace(('wall', obstacle))
        self.assertEqual(result.status, 'blocked')
        self.assertEqual(result.intersections[0].entity_id, 'wall')
        self.assertAlmostEqual(result.intersections[0].entry, .4)
        self.assertAlmostEqual(result.intersections[0].exit, .6)

    def test_transparent_partial_and_unassigned_optics(self):
        obstacle = self.obstacle('glass', P(5, 0, 0), Sphere(1), 0)
        self.assertEqual(self.trace(('glass', obstacle)).status, 'clear')
        obstacle.set_visual_occlusion(VisualOcclusion(.3))
        self.assertEqual(self.trace(('glass', obstacle)).status, 'partial')
        obstacle.set_visual_occlusion(None)
        result = self.trace(('glass', obstacle))
        self.assertEqual(result.status, 'unknown')
        self.assertIsNone(result.intersections[0].opacity)

    def test_opaque_is_conclusive_even_with_unknown_or_partial(self):
        unknown = self.obstacle('unknown', P(2, 0, 0), Sphere(.5))
        partial = self.obstacle('partial', P(5, 0, 0), Sphere(.5), .5)
        opaque = self.obstacle('opaque', P(8, 0, 0), Sphere(.5), 1)
        result = self.trace(('opaque', opaque), ('partial', partial), ('unknown', unknown))
        self.assertEqual(result.status, 'blocked')
        self.assertEqual([h.entity_id for h in result.intersections],
                         ['unknown', 'partial', 'opaque'])

    def test_unmodeled_geometry_is_reported_not_called_transparent(self):
        missing = self.obstacle('missing', P(4, 0, 0))
        result = self.trace(('missing', missing))
        self.assertEqual(result.status, 'unknown')  # absent geometry is not transparent
        self.assertEqual(result.unmodeled_entity_ids, ('missing',))

    def test_movement_recalculates_occlusion(self):
        obstacle = self.obstacle('moving', P(5, 0, 0), Sphere(1), 1)
        self.assertEqual(self.trace(('moving', obstacle)).status, 'blocked')
        obstacle.set_position(P(5, 3, 0))
        self.assertEqual(self.trace(('moving', obstacle)).status, 'clear')

    def test_isolated_endpoint_touch_and_internal_tangent(self):
        start_touch = self.obstacle('start', P(-1, 0, 0), Sphere(1), 1)
        end_touch = self.obstacle('end', P(11, 0, 0), Sphere(1), 1)
        tangent = self.obstacle('tangent', P(5, 1, 0), Sphere(1), 1)
        self.assertEqual(self.trace(('start', start_touch), ('end', end_touch)).status,
                         'clear')
        self.assertEqual(self.trace(('tangent', tangent)).status, 'blocked')

    def test_explicit_source_and_target_excluded(self):
        observer = self.obstacle('observer', P(0, 0, 0), Sphere(2), 1)
        target = self.obstacle('target', P(10, 0, 0), Sphere(2), 1)
        result = trace_sightline(P(0, 0, 0), P(10, 0, 0),
                                 [('observer', observer), ('target', target)],
                                 exclude_ids=('observer', 'target'))
        self.assertEqual(result.status, 'clear')
        self.assertEqual(len(result.intersections), 0)

    def test_wrong_endpoints_and_degenerate_path(self):
        with self.assertRaises(TypeError):
            trace_sightline((0, 0, 0), P(1, 0, 0), [])
        with self.assertRaises(ValueError):
            trace_sightline(P(1, 0, 0), P(1, 0, 0), [])


if __name__ == '__main__':
    unittest.main()
