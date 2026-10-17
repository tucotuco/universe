#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath('../src'))

from spatial.cell import CellAddress


class TestCellAddress(unittest.TestCase):
    def test_parse_and_render(self):
        cell = CellAddress.parse("A0312")
        self.assertEqual(cell.face, 0)
        self.assertEqual(cell.face_label, "A")
        self.assertEqual(cell.path, (0, 3, 1, 2))
        self.assertEqual(cell.level, 4)
        self.assertEqual(str(cell), "A0312")

        self.assertEqual(str(CellAddress.parse("t303")), "T303")

    def test_hierarchy(self):
        cell = CellAddress.parse("C031")
        self.assertEqual(str(cell.parent), "C03")
        self.assertEqual(tuple(str(c) for c in cell.parent.children), ("C030", "C031", "C032", "C033"))
        self.assertEqual(tuple(str(c) for c in cell.ancestors()), ("C", "C0", "C03"))
        self.assertEqual(tuple(str(c) for c in cell.ancestors(include_self=True)), ("C", "C0", "C03", "C031"))
        self.assertTrue(CellAddress.parse("C0").is_ancestor_of(cell))
        self.assertFalse(cell.is_ancestor_of(cell))
        self.assertTrue(cell.is_ancestor_or_self_of(cell))

    def test_root_parent_is_none(self):
        self.assertIsNone(CellAddress.parse("A").parent)

    def test_invalid_addresses(self):
        for value in ("", "U", "A4", "A-1", "AA"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    CellAddress.parse(value)

        with self.assertRaises(ValueError):
            CellAddress(20)
        with self.assertRaises(ValueError):
            CellAddress(0, (4,))


if __name__ == '__main__':
    unittest.main()
