"""Read-only validation and sampling for historical weighted-count tables."""
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "src"))

from abilities import Abilities
from being import BeingDefinition, BeingInstance
from library import Library
from universe import Universe
from explore_legacy_reproduction import (
    PARSER_VERSION, SAMPLER_VERSION, ProfileValidationError, WeightedCountProfile,
    load_weighted_profile, sample_weighted_values,
)


class LegacyReproductionExplorerTests(unittest.TestCase):
    def test_sixteen_actual_species_profiles_validate_with_provenance(self):
        paths = sorted((ROOT / "legacy/src/data").glob("offspring_*_wlist.csv"))
        self.assertEqual(len(paths), 16)
        for path in paths:
            with self.subTest(path=path.name):
                profile = load_weighted_profile(path)
                self.assertEqual(len(profile.sha256), 64)
                self.assertGreater(profile.total_weight, 0)
                self.assertTrue(any(value == 0 for value, _weight in profile.rows))
                self.assertEqual(len({value for value, _weight in profile.rows}), len(profile.rows))

    def test_two_profiles_normalize_and_seed_repeatably_with_zero_support(self):
        human = load_weighted_profile(ROOT / "legacy/src/data/offspring_human_wlist.csv")
        darkelf = load_weighted_profile(ROOT / "legacy/src/data/offspring_darkelf_wlist.csv")
        self.assertEqual(human.total_weight, 848)
        self.assertEqual(darkelf.total_weight, 216)
        self.assertAlmostEqual(human.normalized_rows()[0][2], 100 / 848)
        self.assertAlmostEqual(darkelf.normalized_rows()[0][2], 45 / 216)
        self.assertIn((0, 100), human.rows)
        self.assertIn((0, 45), darkelf.rows)
        for profile in (human, darkelf):
            first = sample_weighted_values(profile, seed=5, draws=20)
            self.assertEqual(first, sample_weighted_values(profile, seed=5, draws=20))
            self.assertEqual(len(first), 20)
            self.assertTrue(all(value in {v for v, _w in profile.rows} for value in first))
        self.assertEqual(
            sample_weighted_values(human, seed=5, draws=20),
            (5, 2, 6, 3, 7, 5, 6, 5, 4, 0, 3, 7, 2, 5, 0, 1, 1, 3, 3, 2),
        )
        self.assertEqual(
            sample_weighted_values(darkelf, seed=5, draws=20),
            (2, 1, 3, 1, 4, 3, 6, 3, 3, 2, 0, 6, 2, 3, 1, 3, 0, 0, 0, 1),
        )

    def test_invalid_schema_weights_values_duplicates_and_encoding_refuse(self):
        invalid_text = (
            ("count,weight\n1,2\n", "header"),
            ("weight,value\n-1,0\n", "nonnegative"),
            ("weight,value\nx,0\n", "weight is not an integer"),
            ("weight,value\n1,-1\n", "candidate count must be nonnegative"),
            ("weight,value\n0,0\n", "total weight"),
            ("weight,value\n1,0\n1,0\n", "duplicates candidate value"),
            ("weight,value\n1,0,extra\n", "exactly two columns"),
        )
        with tempfile.TemporaryDirectory() as directory:
            for text, message in invalid_text:
                path = Path(directory) / "invalid.csv"
                path.write_text(text, encoding="utf-8")
                with self.subTest(message=message), self.assertRaisesRegex(ProfileValidationError, message):
                    load_weighted_profile(path)
            path = Path(directory) / "bad-encoding.csv"
            path.write_bytes(b"weight,value\n\xff,0\n")
            with self.assertRaisesRegex(ProfileValidationError, "strict UTF-8"):
                load_weighted_profile(path)

    def test_zero_weight_rows_are_reported_but_never_sampled(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "zero.csv"
            path.write_text("weight,value\n0,0\n1,1\n", encoding="utf-8")
            profile = load_weighted_profile(path)
            self.assertEqual(profile.normalized_rows(), ((0, 0, 0.0), (1, 1, 1.0)))
            self.assertEqual(sample_weighted_values(profile, seed=3, draws=50), (1,) * 50)

    def test_manually_constructed_invalid_profile_is_revalidated_by_sampler(self):
        digest = "0" * 64
        for rows, message in (
                (((0, -1),), "nonnegative integer"),
                (((1, 1), (1, 2)), "duplicate candidate value"),
                (((0, 0),), "total weight must be positive")):
            profile = WeightedCountProfile("fixture.csv", digest, rows)
            with self.subTest(rows=rows), self.assertRaisesRegex(ProfileValidationError, message):
                sample_weighted_values(profile, seed=1, draws=1)

    def test_sampling_isolated_from_world_being_registry_and_global_rng(self):
        profile = load_weighted_profile(ROOT / "legacy/src/data/offspring_gnome_wlist.csv")
        world = Universe("read-only explorer test", library=Library(config_dir=str(ROOT / "src/config")))
        being = BeingInstance(
            BeingDefinition("authored test being", 1, 1, 10, "1d8", "N", 10, 0,
                            abilities=Abilities(strength=13)),
            name="unchanged", id="READ-ONLY-BEING",
        )
        registry = world._reproduction_group_registry
        registry_refs = (registry._groups_by_id, registry._group_id_by_parent_set,
                         registry._group_id_by_offspring, registry._person_id_reservations)
        before_snapshot = world.reproduction_group_snapshot()
        before_objects = dict(world.object_registry.object_instances)
        before_being = (being.id, being.name, being.original.STR(), being.current.hit_points,
                        being.skill_experience.copy(), being.skill_use_history.copy())
        before_rng = random.getstate()
        sample_weighted_values(profile, seed=19, draws=30)
        after_snapshot = world.reproduction_group_snapshot()
        self.assertEqual(after_snapshot, before_snapshot)
        self.assertEqual(world.object_registry.object_instances, before_objects)
        self.assertEqual((being.id, being.name, being.original.STR(), being.current.hit_points,
                          being.skill_experience.copy(), being.skill_use_history.copy()), before_being)
        self.assertTrue(all(a is b for a, b in zip(registry_refs,
                                                   (registry._groups_by_id, registry._group_id_by_parent_set,
                                                    registry._group_id_by_offspring, registry._person_id_reservations))))
        self.assertEqual(random.getstate(), before_rng)

    def test_cli_reports_versions_seed_hash_normalized_rows_and_two_real_profiles(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools/explore_legacy_reproduction.py"),
             "--source", "legacy/src/data/offspring_human_wlist.csv",
             "legacy/src/data/offspring_darkelf_wlist.csv", "--seed", "5", "--draws", "20"],
            cwd=ROOT, check=True, text=True, capture_output=True,
        )
        self.assertIn(PARSER_VERSION, result.stdout)
        self.assertIn(SAMPLER_VERSION, result.stdout)
        self.assertIn("interpretation: UNRESOLVED / EXPERIMENTAL", result.stdout)
        self.assertIn("explicit seed: 5; draws: 20; total relative weight: 848", result.stdout)
        self.assertIn("total relative weight: 216", result.stdout)
        self.assertIn("sha256: 9763d3587340c2b4acc475af7c23a960d49930e1c8e18878658f617876b221a7", result.stdout)
        self.assertIn("legacy/src/data/offspring_darkelf_wlist.csv", result.stdout)
        self.assertIn("no Universe/Reality publication", result.stdout)


if __name__ == "__main__":
    unittest.main()
