from __future__ import annotations

import re
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from arena_native_snapshot import _ARENA_TAGS
from checkpoint_fields import FIELD_ADAPTERS


MATRIX = ROOT / 'docs/design/persistence-capability-matrix.md'


class NativePersistenceCapabilityMatrixTests(unittest.TestCase):
    def test_matrix_exactly_tracks_closed_native_field_registry(self):
        text = MATRIX.read_text()
        rows = {}
        for line in text.splitlines():
            if not line.startswith('| `'):
                continue
            cells = [cell.strip() for cell in line.strip('|').split('|')]
            self.assertEqual(len(cells), 5, line)
            match = re.fullmatch(r'`([^`]+)`', cells[0])
            self.assertIsNotNone(match, line)
            tag = match.group(1)
            self.assertNotIn(tag, rows)
            rows[tag] = cells

        self.assertEqual(set(rows), set(FIELD_ADAPTERS))
        for tag, adapter in FIELD_ADAPTERS.items():
            cells = rows[tag]
            allowed = set(re.findall(r'`([^`]+)`', cells[1]))
            required = set(re.findall(r'`([^`]+)`', cells[2]))
            self.assertEqual(allowed, set(adapter['allowed']), tag)
            self.assertEqual(required, set(adapter['required']), tag)
            self.assertTrue(required <= allowed, tag)
            source = ROOT / 'src' / (tag.rsplit('.', 1)[0].replace('.', '/') + '.py')
            self.assertTrue(source.is_file(), (tag, source))
            self.assertIn('Arena snapshot schema', cells[3]) if tag in _ARENA_TAGS else self.assertIn('Outside Arena snapshot schema', cells[3])

    def test_matrix_states_arena_only_and_native_restore_boundary(self):
        text = MATRIX.read_text()
        self.assertIn('152 types', text)
        self.assertIn('104 domain types plus five structural container types', text)
        self.assertIn('not a general native persistence API', text)
        self.assertIn('no production native restore path', text)
        self.assertIn('**Open**', text)


if __name__ == '__main__':
    unittest.main()
