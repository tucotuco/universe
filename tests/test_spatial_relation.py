#!/usr/bin/env python
# -*- coding: utf-8 -*-

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath('../src'))

from object import ObjectDefinition, ObjectInstance
from spatial import CartesianPosition, ISEAGrid, SpatialRelation


class TestSpatialRelation(unittest.TestCase):
    def test_continuous_relation_uses_real_3d_geometry(self):
        relation = SpatialRelation(
            CartesianPosition(1.0, 2.0, 3.0),
            CartesianPosition(4.0, 6.0, 15.0),
        )
        self.assertEqual(relation.displacement, (3.0, 4.0, 12.0))
        self.assertEqual(relation.distance, 13.0)
        self.assertEqual(
            relation.unit_direction,
            (3.0 / 13.0, 4.0 / 13.0, 12.0 / 13.0),
        )
        self.assertFalse(relation.coincident)

    def test_reverse_relation_is_symmetric_in_distance(self):
        a = CartesianPosition(-2.0, 5.0, 7.0)
        b = CartesianPosition(3.0, -1.0, 11.0)
        forward = SpatialRelation(a, b)
        reverse = SpatialRelation(b, a)
        self.assertEqual(forward.distance, reverse.distance)
        self.assertEqual(
            reverse.displacement,
            tuple(-component for component in forward.displacement),
        )

    def test_coincident_positions_have_no_direction(self):
        position = CartesianPosition(2.0, 3.0, 4.0)
        relation = SpatialRelation(position, position)
        self.assertTrue(relation.coincident)
        self.assertEqual(relation.distance, 0.0)
        self.assertIsNone(relation.unit_direction)

    def test_grid_relation_is_derived_from_continuous_positions(self):
        grid = ISEAGrid(radius=1.0)
        source_lat, source_lon = grid.centroid('A0')
        target_lat, target_lon = grid.centroid('A1')
        relation = SpatialRelation(
            CartesianPosition.from_lat_lon(source_lat, source_lon),
            CartesianPosition.from_lat_lon(target_lat, target_lon),
        )

        self.assertFalse(relation.shares_cell(grid, 1))
        self.assertEqual(str(relation.deepest_shared_cell(grid, 1)), 'A')
        self.assertTrue(math.isfinite(relation.distance))
        self.assertGreater(relation.distance, 0.0)

    def test_radial_separation_does_not_change_overlay_cell(self):
        grid = ISEAGrid(radius=1.0)
        relation = SpatialRelation(
            CartesianPosition.from_lat_lon(12.0, 34.0, 1.0),
            CartesianPosition.from_lat_lon(12.0, 34.0, 10.0),
        )
        self.assertTrue(relation.shares_cell(grid, 8))
        self.assertEqual(relation.distance, 9.0)


class TestObjectSpatialRelation(unittest.TestCase):
    def setUp(self):
        definition = ObjectDefinition('marker', 1, 1, 1, 1, 0, 0, 1)
        self.a = ObjectInstance(definition, 'a')
        self.b = ObjectInstance(definition, 'b')

    def test_relation_requires_both_objects_to_be_placed(self):
        self.assertIsNone(self.a.spatial_relation_to(self.b))
        self.a.set_position(CartesianPosition(0.0, 0.0, 0.0))
        self.assertIsNone(self.a.spatial_relation_to(self.b))

    def test_relation_is_available_to_all_object_subtypes(self):
        self.a.set_position(CartesianPosition(0.0, 0.0, 0.0))
        self.b.set_position(CartesianPosition(0.0, 3.0, 4.0))
        relation = self.a.spatial_relation_to(self.b)
        self.assertEqual(relation.distance, 5.0)
        self.assertEqual(relation.displacement, (0.0, 3.0, 4.0))


if __name__ == '__main__':
    unittest.main()
