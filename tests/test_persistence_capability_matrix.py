from __future__ import annotations

import re
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from arena_native_snapshot import _ARENA_TAGS
from checkpoint_fields import FIELD_ADAPTERS
from checkpoint_inventory import _TYPES


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
            evidence_links = re.findall(r'\[[^\]]+\]\(([^)]+)\)', cells[4])
            self.assertTrue(evidence_links, f'{tag}: no source/test evidence links')
            for link in evidence_links:
                if '://' in link:
                    continue
                evidence_path = (MATRIX.parent / link.split('#', 1)[0]).resolve()
                self.assertTrue(evidence_path.is_file(), (tag, link))

    def test_executable_native_type_registry_matches_all_reviewed_field_adapters(self):
        tags = {f'{cls.__module__}.{cls.__name__}' for cls in _TYPES}
        self.assertEqual(tags, set(FIELD_ADAPTERS))

    def test_matrix_states_arena_only_and_native_restore_boundary(self):
        text = MATRIX.read_text()
        self.assertIn('159 types', text)
        self.assertIn('104 domain types plus five structural container types', text)
        self.assertIn('not a general native persistence API', text)
        self.assertIn('no production native restore path', text)
        self.assertIn('**Open**', text)
        self.assertIn('test_progressive_reproduction_history_restores_and_continues_in_fresh_process', text)
        self.assertIn('test_statistical_reproduction_outcomes_resume_with_positive_and_zero_results', text)
        self.assertIn('test_initial_history_precedes_first_boundary_movement_and_survives_fresh_load', text)
        import native_history
        self.assertEqual(native_history.RECIPIENT_HISTORY_SCHEMA,
                         'universe.native-encounter-history/9')
        self.assertEqual(native_history.SCHEMA, 'universe.native-encounter-history/11')
        self.assertTrue(callable(native_history.entity_context_at))
        self.assertTrue(callable(native_history.entity_at))
        self.assertTrue(callable(native_history.entity_history_at))
        self.assertTrue(callable(native_history.objective_at))
        self.assertTrue(callable(native_history.objective_use_at))
        self.assertTrue(callable(native_history.schedule_at))
        self.assertTrue(callable(native_history.action_state_at))
        self.assertTrue(callable(native_history.choice_state_at))
        self.assertTrue(callable(native_history.observer_knowledge_at))
        self.assertTrue(callable(native_history.timeline_at))
        self.assertTrue(callable(native_history.NativeHistoryQuery))


if __name__ == '__main__':
    unittest.main()
