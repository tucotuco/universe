"""Inert import of Target-owned native Run practice from a detached projection."""
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
import inspect
import random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tests'))

from action_evaluation import EffectIdentity
from checkpoint_projection import project_quarantined_run_boundary
from checkpoint_wire import decode_run_spot_wire
from experience import BatchSkillUse
from frozen_practice import (CandidatePracticeUse, ImportedPracticeRejected,
    freeze_imported_run_practice, merge_imported_practice_uses,
    capture_practice_inputs)
from test_checkpoint_projection import committed_run_wire


def fixture_projection():
    wire, _ = committed_run_wire()
    return project_quarantined_run_boundary(decode_run_spot_wire(wire))


def actor_target_for(projection):
    return next(row for row in projection.targets
                if row.target_id == projection.actions[0].actor_id)


class TestImportedFrozenPractice(unittest.TestCase):
    def setUp(self):
        self.projection = fixture_projection()

    def test_import_preserves_one_causal_run_award_without_reapplying_xp(self):
        projection_data = self.projection.to_data()
        module_rng = random.getstate()
        prefix = freeze_imported_run_practice(self.projection)
        merged = merge_imported_practice_uses(prefix, prefix.target_id)
        target = actor_target_for(self.projection)

        self.assertEqual(prefix.boundary, 1)
        self.assertEqual(prefix.action_ids, (self.projection.actions[0].action_id,))
        self.assertEqual(len(merged), 1)
        batch = merged[0]
        self.assertIs(type(batch), BatchSkillUse)
        self.assertEqual((batch.being_id, batch.skill_name, batch.experience,
                          batch.level_before, batch.level_after, batch.time),
                         (prefix.target_id, 'run', 4, 0, 0, 1))
        exercise = batch.exercises[0]
        self.assertEqual(exercise.action_id, prefix.action_ids[0])
        self.assertEqual(exercise.effect_identity,
            EffectIdentity(*target.practice_exercises[0].effect_id[1:]))
        # The post-boundary Target owns the already-settled experience; imported
        # history is prior-use context and is not added to that materialized XP.
        practice = dict(target.state_data[1])['practice_state'][1]
        self.assertEqual(dict(dict(practice)['skill_experience'][1])['run'], ('integer', '4'))
        self.assertEqual(prefix.to_data(), prefix.to_data())
        with self.assertRaises(FrozenInstanceError):
            prefix.boundary = 2
        self.assertEqual(self.projection.to_data(), projection_data)
        self.assertEqual(random.getstate(), module_rng)

    def test_later_native_suffix_merges_once_and_requires_later_time(self):
        prefix = freeze_imported_run_practice(self.projection)
        effect = EffectIdentity(prefix.encounter_id, 2, 'future-run-action', 'effect', 0)
        suffix_use = CandidatePracticeUse(effect, 'run', 2, 'future-run-action',
            2.0, 2, 'success')
        source = [BatchSkillUse(prefix.target_id, 'run', 2, 0, 0, 2, (suffix_use,))]
        merged = merge_imported_practice_uses(prefix, prefix.target_id, source)
        self.assertEqual([(row.time, row.experience) for row in merged], [(1, 4), (2, 2)])
        self.assertIsNot(merged[1], source[0])
        self.assertIsNot(merged[1].exercises[0], suffix_use)
        source.clear()
        self.assertEqual(len(merged), 2)
        duplicate = BatchSkillUse(prefix.target_id, 'run', 1, 0, 0, 2,
            (CandidatePracticeUse(EffectIdentity(prefix.encounter_id, 2,
                prefix.action_ids[0], 'effect', 0), 'run', 1, prefix.action_ids[0],
                2.0, 2, 'success'),))
        stale = BatchSkillUse(prefix.target_id, 'run', 1, 0, 0, 1,
            (CandidatePracticeUse(EffectIdentity(prefix.encounter_id, 1,
                'old-run-action', 'effect', 0), 'run', 1, 'old-run-action',
                1.0, 1, 'success'),))
        for suffix in ((duplicate,), (stale,), (object(),)):
            with self.subTest(suffix=suffix):
                with self.assertRaises(ImportedPracticeRejected):
                    merge_imported_practice_uses(prefix, prefix.target_id, suffix)
        with self.assertRaises(ImportedPracticeRejected):
            merge_imported_practice_uses(prefix, 'other-target')

    def test_forged_target_effect_action_and_history_data_refuse(self):
        target = actor_target_for(self.projection)
        exercise = target.practice_exercises[0]
        wrong_action = replace(exercise, action_id='wrong-action')
        altered_target = replace(target, practice_exercises=(wrong_action,))
        altered = replace(self.projection, targets=tuple(
            altered_target if row.target_id == target.target_id else row
            for row in self.projection.targets))
        with self.assertRaises(ImportedPracticeRejected):
            freeze_imported_run_practice(altered)

        wrong_transition = replace(target.practice_transitions[0], target_id='wrong-target')
        wrong_target_state = replace(target, practice_transitions=(wrong_transition,))
        # An invalid projection value is rejected before it can become a frozen input.
        altered = replace(self.projection, targets=tuple(
            wrong_target_state if row.target_id == target.target_id else row
            for row in self.projection.targets))
        with self.assertRaises((ImportedPracticeRejected, AttributeError, TypeError)):
            freeze_imported_run_practice(altered)

    def test_normal_capture_surface_is_unchanged(self):
        self.assertEqual(tuple(inspect.signature(capture_practice_inputs).parameters),
                         ('world', 'objects', 'entity_views'))


if __name__ == '__main__':
    unittest.main()
