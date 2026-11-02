"""HYPOTHETICAL legacy-table bridge through typed isolated world publication."""
from pathlib import Path
import random
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "src"))

from explore_legacy_reproduction import PARSER_VERSION, SAMPLER_VERSION
from library import Library
from reproduction_group import ReproductionGroupRegistry
from universe import Universe
from legacy_reproduction_what_if import (
    HYPOTHETICAL_INTERPRETATION, PINNED_TABLES, WHAT_IF_DISTRIBUTION_VERSION,
    WhatIfIntegrationError, load_pinned_profile, profile_math, run_one_episode_what_if,
)


class LegacyReproductionWhatIfTests(unittest.TestCase):
    def test_hash_pins_and_math_summary_for_both_source_profiles(self):
        self.assertEqual(PARSER_VERSION, "legacy-weighted-count-csv/1")
        self.assertEqual(SAMPLER_VERSION, "integer-cumulative-randrange/1")
        expected = {
            "human": ("9763d3587340c2b4acc475af7c23a960d49930e1c8e18878658f617876b221a7", 25 / 212, 1375 / 424),
            "darkelf": ("e0fabb178a4faa032f05f0243f82c057e92a428cffae63d59d7459ee38314b45", 5 / 24, 173 / 108),
        }
        for label, (digest, p_zero, mean) in expected.items():
            with self.subTest(label=label):
                profile = load_pinned_profile(label)
                self.assertEqual(profile.source_path, PINNED_TABLES[label][0])
                self.assertEqual(profile.sha256, digest)
                actual_zero, actual_mean = profile_math(profile)
                self.assertAlmostEqual(float(actual_zero), p_zero)
                self.assertAlmostEqual(float(actual_mean), mean)

    def test_seeded_positive_human_publication_is_exact_and_idempotent(self):
        result = run_one_episode_what_if("human", seed=5)
        self.assertEqual(result.table_draw, 5)
        self.assertEqual(result.profile.sha256, PINNED_TABLES["human"][1])
        self.assertEqual(result.outcome.count, 5)
        self.assertIsNotNone(result.outcome.group_id)
        self.assertEqual(len(result.outcome.offspring_ids), 5)
        self.assertEqual(len(set(result.outcome.offspring_ids)), 5)
        self.assertEqual(result.outcome.parent_ids, ("V8-PARENT-A", "V8-PARENT-B"))
        self.assertFalse(result.outcome.parent_offspring_enumeration_complete)
        snapshot = result.world.reproduction_group_snapshot()
        self.assertEqual(len(snapshot.groups), 1)
        self.assertEqual(snapshot.groups[0].parent_ids, result.outcome.parent_ids)
        self.assertEqual(snapshot.groups[0].offspring_ids, result.outcome.offspring_ids)
        self.assertEqual(result.replayed_outcome, result.outcome)
        self.assertEqual(result.revision_before, 0)
        self.assertEqual(result.revision_after, 1)
        self.assertEqual(result.revision_after_replay, 1)
        self.assertEqual(len(result.world.object_registry.object_instances), 0)
        self.assertEqual(set(result.world.event_history), {"0"})
        self.assertEqual(result.world._choice_books, [])

    def test_seeded_zero_darkelf_publication_keeps_no_group_and_never_rerolls(self):
        result = run_one_episode_what_if("darkelf", seed=1)
        self.assertEqual(result.table_draw, 0)
        self.assertEqual(result.outcome.count, 0)
        self.assertIsNone(result.outcome.group_id)
        self.assertEqual(result.outcome.offspring_ids, ())
        self.assertEqual(result.outcome.origin_ticks, ())
        self.assertEqual(result.world.reproduction_group_snapshot().groups, ())
        self.assertFalse(result.outcome.parent_offspring_enumeration_complete)
        self.assertEqual(result.replayed_outcome, result.outcome)
        self.assertEqual(result.revision_after_replay, result.revision_after)

    def test_repeat_run_in_separate_disposable_world_reproduces_logical_ids(self):
        first = run_one_episode_what_if("human", seed=5)
        second = run_one_episode_what_if("human", seed=5)
        self.assertIsNot(first.world, second.world)
        self.assertEqual(first.outcome.group_id, second.outcome.group_id)
        self.assertEqual(first.outcome.offspring_ids, second.outcome.offspring_ids)
        self.assertEqual(first.outcome.origin_ticks, second.outcome.origin_ticks)

    def test_external_world_and_global_rng_are_unchanged(self):
        user_world = Universe("untouched caller world", library=Library(config_dir=str(ROOT / "src/config")))
        sentinel = user_world._reproduction_group_registry
        refs = (sentinel._groups_by_id, sentinel._group_id_by_parent_set,
                sentinel._group_id_by_offspring, user_world.object_registry.object_instances)
        before = user_world.reproduction_group_snapshot()
        rng_before = random.getstate()
        run_one_episode_what_if("human", seed=5)
        run_one_episode_what_if("darkelf", seed=1)
        self.assertEqual(user_world.reproduction_group_snapshot(), before)
        self.assertTrue(all(a is b for a, b in zip(refs, (
            sentinel._groups_by_id, sentinel._group_id_by_parent_set,
            sentinel._group_id_by_offspring, user_world.object_registry.object_instances))))
        self.assertEqual(random.getstate(), rng_before)

    def test_changed_pinned_digest_refuses_before_world_construction(self):
        altered = dict(PINNED_TABLES)
        altered["human"] = (altered["human"][0], "0" * 64)
        with patch.dict("legacy_reproduction_what_if.PINNED_TABLES", altered):
            with self.assertRaisesRegex(WhatIfIntegrationError, "pinned source digest changed"):
                run_one_episode_what_if("human", seed=5)

    def test_example_labels_hypothesis_shows_positive_zero_and_comparison(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "examples/legacy_reproduction_what_if.py")],
            cwd=ROOT, check=True, text=True, capture_output=True,
        )
        self.assertIn("HYPOTHETICAL / NOT ADOPTED", result.stdout)
        self.assertIn("one exact parent set in one abstract episode", result.stdout)
        self.assertIn("published_count=5", result.stdout)
        self.assertIn("group_id=RG-STAT-", result.stdout)
        self.assertIn("abstract API origin tokens=[0, 1, 2, 3, 4]; tokens are not dates or durations", result.stdout)
        self.assertIn("enumeration_complete=False", result.stdout)
        self.assertIn("published_count=0; group_id=None; offspring_ids=[]", result.stdout)
        self.assertIn("p_zero=25/212", result.stdout)
        self.assertIn("p_zero=5/24", result.stdout)
        self.assertIn("global_python_rng_unchanged=True", result.stdout)


if __name__ == "__main__":
    unittest.main()
