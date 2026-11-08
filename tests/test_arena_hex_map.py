"""One-yard flat-top Arena hex layout and read-only occupancy projection."""

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from arena_hex_map import ArenaHexLayout, HexAddress, YARDS_TO_METERS
from spatial.state import CartesianPosition


class TestArenaHexMap(unittest.TestCase):
    def setUp(self):
        self.layout = ArenaHexLayout.rectangle(6, 5)

    def test_hex_across_flats_is_one_yard_and_neighbors_share_edges(self):
        side = self.layout.side_length_meters
        self.assertAlmostEqual(self.layout.side_to_side_meters, YARDS_TO_METERS)
        vertices = self.layout.vertex_offsets_meters
        self.assertAlmostEqual(max(point[1] for point in vertices)
                               - min(point[1] for point in vertices), YARDS_TO_METERS)
        self.assertAlmostEqual(max(point[0] for point in vertices)
                               - min(point[0] for point in vertices), 2 * side)
        center = self.layout.center_position(HexAddress(2, 2))
        center_yards = tuple(value / YARDS_TO_METERS for value in center.as_tuple())
        self.assertEqual(center_yards[2], 0.0)
        neighbors = self.layout.neighbors(HexAddress(2, 2))
        self.assertEqual(len(neighbors), 6)
        self.assertEqual(len(set(neighbors)), 6)
        for neighbor in neighbors:
            other = self.layout.center_position(neighbor)
            distance = sum((a - b) ** 2 for a, b in zip(center.as_tuple(), other.as_tuple())) ** 0.5
            self.assertAlmostEqual(distance, YARDS_TO_METERS)
            first_vertices = [(center.x + dx, center.y + dy)
                              for dx, dy in self.layout.vertex_offsets_meters]
            other_vertices = [(other.x + dx, other.y + dy)
                              for dx, dy in self.layout.vertex_offsets_meters]
            shared = sum(1 for first_point in first_vertices for second_point in other_vertices
                         if sum((a - b) ** 2 for a, b in zip(first_point, second_point)) < 1e-20)
            self.assertEqual(shared, 2)

    def test_offset_addresses_map_deterministically_to_hex_centers(self):
        even = self.layout.center_position(HexAddress(2, 1))
        odd = self.layout.center_position(HexAddress(3, 1))
        self.assertAlmostEqual(even.x / YARDS_TO_METERS,
                               1 / 3**0.5 + 2 * (3**0.5 / 2))
        self.assertAlmostEqual(even.y / YARDS_TO_METERS, 1.5)
        self.assertAlmostEqual(odd.y - even.y, YARDS_TO_METERS * 0.5)
        self.assertEqual(self.layout.address_for_index(13), HexAddress(2, 3))

    def test_exact_edge_ties_choose_smallest_in_map_address_and_outside_is_none(self):
        first = self.layout.center_position(HexAddress(0, 0))
        second = self.layout.center_position(HexAddress(1, 0))
        edge = CartesianPosition((first.x + second.x) / 2,
                                 (first.y + second.y) / 2, 19.0)
        first_vertices = [(first.x + dx, first.y + dy)
                          for dx, dy in self.layout.vertex_offsets_meters]
        second_vertices = [(second.x + dx, second.y + dy)
                           for dx, dy in self.layout.vertex_offsets_meters]
        shared_vertex = next(point for point in first_vertices
                             if any(sum((a - b) ** 2 for a, b in zip(point, other)) < 1e-20
                                    for other in second_vertices))
        vertex = CartesianPosition(shared_vertex[0], shared_vertex[1], -3.0)
        self.assertEqual(self.layout.cell_at_position(first), HexAddress(0, 0))
        self.assertEqual(self.layout.cell_at_position(edge), HexAddress(0, 0))
        self.assertEqual(self.layout.cell_at_position(vertex), HexAddress(0, 0))
        self.assertIsNone(self.layout.cell_at_position(CartesianPosition(-10, -10, 0)))

    def test_irregular_finite_footprint_has_deterministic_neighbors_and_ranges(self):
        layout = ArenaHexLayout.irregular(4, 4, (
            HexAddress(0, 0), HexAddress(0, 1), HexAddress(1, 0), HexAddress(3, 3)))
        self.assertEqual(len(layout.cell_ids), 4)
        self.assertTrue(layout.contains(HexAddress(3, 3)))
        self.assertFalse(layout.contains(HexAddress(2, 2)))
        self.assertEqual(layout.column_row_ranges(), (
            (0, ((0, 1),)), (1, ((0, 0),)), (3, ((3, 3),))))
        self.assertIn(HexAddress(1, 1), layout.neighbors(HexAddress(0, 1)))
        expanded = ArenaHexLayout.irregular(4, 4, (
            HexAddress(0, 0), HexAddress(0, 1), HexAddress(1, 0),
            HexAddress(1, 1), HexAddress(2, 1), HexAddress(3, 3)))
        self.assertTrue(expanded.contains(HexAddress(2, 1)))
        self.assertIn(HexAddress(2, 1), expanded.neighbors(HexAddress(1, 1)))


if __name__ == "__main__":
    unittest.main()
