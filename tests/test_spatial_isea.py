#!/usr/bin/env python
# -*- coding: utf-8 -*-

import math
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.abspath('../src'))

from spatial.cell import CellAddress
from spatial.isea import ISEAGrid


class TestISEAGrid(unittest.TestCase):
    def setUp(self):
        self.grid = ISEAGrid()

    def test_root_faces_cover_known_points(self):
        samples = [
            (90.0, 0.0),
            (-90.0, 0.0),
            (0.0, 0.0),
            (0.0, 90.0),
            (0.0, -90.0),
            (40.0, -75.0),
            (-41.0, 174.0),
        ]
        for latitude, longitude in samples:
            with self.subTest(latitude=latitude, longitude=longitude):
                cell = self.grid.cell_at(latitude, longitude, 0)
                self.assertEqual(cell.level, 0)
                self.assertTrue(self.grid.contains(cell, latitude, longitude))

    def test_centroid_round_trip(self):
        # A representative selection across roots, orientations and levels.
        cells = [
            "A", "F", "K", "P", "T",
            "A0", "A1", "A2", "A3",
            "H203", "M3312", "T01230",
        ]
        for value in cells:
            with self.subTest(cell=value):
                cell = CellAddress.parse(value)
                latitude, longitude = self.grid.centroid(cell)
                self.assertEqual(self.grid.cell_at(latitude, longitude, cell.level), cell)

    def test_all_children_have_equal_area_and_sum_to_parent(self):
        parent = CellAddress.parse("G203")
        child_areas = [self.grid.area(child) for child in parent.children]
        self.assertTrue(all(math.isclose(child_areas[0], area) for area in child_areas[1:]))
        self.assertTrue(math.isclose(sum(child_areas), self.grid.area(parent), rel_tol=1e-14))

    def test_root_area_sums_to_sphere(self):
        radius = 6_371_000.0
        grid = ISEAGrid(radius=radius)
        total = sum(grid.area(CellAddress(face)) for face in range(20))
        self.assertTrue(math.isclose(total, 4.0 * math.pi * radius * radius, rel_tol=1e-14))

    def test_same_level_cells_have_equal_area(self):
        cells = [CellAddress.parse(value) for value in ("A012", "F333", "K201", "T120")]
        areas = [self.grid.area(cell) for cell in cells]
        self.assertTrue(all(math.isclose(areas[0], area, rel_tol=1e-14) for area in areas[1:]))

    def test_vertices_are_valid_angular_coordinates(self):
        for value in ("A", "A3", "H203", "T0123"):
            for latitude, longitude in self.grid.vertices(value):
                self.assertGreaterEqual(latitude, -90.0)
                self.assertLessEqual(latitude, 90.0)
                self.assertGreaterEqual(longitude, -180.0)
                self.assertLessEqual(longitude, 180.0)

    def test_random_cell_centroids_round_trip(self):
        random.seed(42)
        for _ in range(100):
            face = random.randrange(20)
            level = random.randrange(0, 7)
            path = tuple(random.randrange(4) for _ in range(level))
            cell = CellAddress(face, path)
            latitude, longitude = self.grid.centroid(cell)
            self.assertEqual(self.grid.cell_at(latitude, longitude, level), cell)

    def test_longitude_wraps(self):
        self.assertEqual(self.grid.cell_at(10.0, 10.0, 4), self.grid.cell_at(10.0, 370.0, 4))

    def test_invalid_input(self):
        with self.assertRaises(ValueError):
            self.grid.cell_at(91.0, 0.0, 0)
        with self.assertRaises(ValueError):
            self.grid.cell_at(0.0, 0.0, -1)
        with self.assertRaises(ValueError):
            ISEAGrid(radius=0.0)


if __name__ == '__main__':
    unittest.main()
