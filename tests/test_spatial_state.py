#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath('../src'))

from object import ObjectDefinition, ObjectInstance
from spatial import CartesianPosition, ISEAGrid, SpatialState


class TestCartesianPosition(unittest.TestCase):
    def test_from_lat_lon_round_trip(self):
        position = CartesianPosition.from_lat_lon(37.5, -122.25, 10.0)
        latitude, longitude = position.angular_coordinate()
        self.assertAlmostEqual(latitude, 37.5, places=12)
        self.assertAlmostEqual(longitude, -122.25, places=12)
        self.assertAlmostEqual(position.radial_distance(), 10.0, places=12)

    def test_nonzero_origin(self):
        origin = CartesianPosition(100.0, -25.0, 7.0)
        position = CartesianPosition.from_lat_lon(0.0, 90.0, 5.0, origin)
        self.assertAlmostEqual(position.x, 100.0, places=12)
        self.assertAlmostEqual(position.y, -20.0, places=12)
        self.assertAlmostEqual(position.z, 7.0, places=12)
        self.assertEqual(position.angular_coordinate(origin), (0.0, 90.0))

    def test_angular_coordinate_undefined_at_origin(self):
        position = CartesianPosition(1.0, 2.0, 3.0)
        with self.assertRaises(ValueError):
            position.angular_coordinate((1.0, 2.0, 3.0))


class TestSpatialState(unittest.TestCase):
    def test_cell_is_derived_from_continuous_position(self):
        grid = ISEAGrid(radius=10.0)
        position = CartesianPosition.from_lat_lon(-17.25, 143.75, 12.0)
        state = SpatialState(position)
        self.assertEqual(
            state.cell(grid, 6),
            grid.cell_at(-17.25, 143.75, 6),
        )

    def test_radial_distance_does_not_change_surface_cell(self):
        grid = ISEAGrid(radius=10.0)
        near = SpatialState(CartesianPosition.from_lat_lon(20.0, 30.0, 10.0))
        far = SpatialState(CartesianPosition.from_lat_lon(20.0, 30.0, 1000.0))
        self.assertEqual(near.cell(grid, 7), far.cell(grid, 7))


class TestObjectSpatialState(unittest.TestCase):
    def setUp(self):
        definition = ObjectDefinition('marker', 1, 1, 1, 1, 0, 0, 1)
        self.obj = ObjectInstance(definition, 'marker')
        self.grid = ISEAGrid()

    def test_object_has_no_position_until_placed(self):
        self.assertIsNone(self.obj.get_position())
        self.assertIsNone(self.obj.spatial_cell(self.grid, 3))

    def test_object_position_is_continuous_and_cell_is_derived(self):
        position = CartesianPosition.from_lat_lon(12.0, -45.0, 1.25)
        self.obj.set_position(position)
        self.assertIs(self.obj.get_position(), position)
        self.assertEqual(
            self.obj.spatial_cell(self.grid, 5),
            self.grid.cell_at(12.0, -45.0, 5),
        )

    def test_object_serializes_continuous_spatial_state(self):
        position = CartesianPosition(1.0, 2.0, 3.0)
        self.obj.set_position(position)
        data = json.loads(self.obj.to_json())
        self.assertEqual(
            data["spatial_state"]["position"],
            {"x": 1.0, "y": 2.0, "z": 3.0},
        )

    def test_object_can_move_without_storing_a_cell(self):
        first = CartesianPosition.from_lat_lon(0.0, 0.0, 1.0)
        second = CartesianPosition.from_lat_lon(0.0, 90.0, 1.0)
        self.obj.set_position(first)
        first_cell = self.obj.spatial_cell(self.grid, 4)
        self.obj.set_position(second)
        second_cell = self.obj.spatial_cell(self.grid, 4)
        self.assertNotEqual(first_cell, second_cell)
        self.assertEqual(self.obj.get_position(), second)
        self.assertFalse(hasattr(self.obj.spatial_state, 'cell_address'))


if __name__ == '__main__':
    unittest.main()
