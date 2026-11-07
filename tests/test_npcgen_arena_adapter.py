"""Direct installed-npcgen generation into the bounded native Being model."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from library import Library
from npcgen import api
from npcgen_arena_adapter import ArenaNPCRefusal, generate_npcgen_arena_being
from universe import Universe


def _world():
    return Universe("npcgen Arena adapter test", library=Library(config_dir=str(ROOT / "src/config")))


class TestNpcgenArenaAdapter(unittest.TestCase):
    def test_zero_and_positive_xp_import_exact_ranks_provenance_and_distinct_ids(self):
        world = _world()
        zero = generate_npcgen_arena_being(
            world, seed=1, starting_experience=0, cost_modifiers="character")
        positive = generate_npcgen_arena_being(
            world, seed=1, starting_experience=12000, cost_modifiers="character")
        positive_again = generate_npcgen_arena_being(
            world, seed=1, starting_experience=12000, cost_modifiers="character")

        self.assertEqual(zero.being.get_experience(), 0)
        self.assertEqual(positive.being.get_experience(), 12000)
        self.assertEqual(positive.being.current.experience, 12000)
        self.assertEqual(positive.being.original.experience, 12000)
        half_elf_template = world.library.get_being_definition("Half-elf")
        self.assertIsNotNone(half_elf_template)
        for result, requested in ((zero, 0), (positive, 12000)):
            record = json.loads(result.source_record_bytes)
            self.assertEqual(record["generation"]["starting_experience"], requested)
            self.assertEqual(record["generation"]["starting_experience_meaning"], "arena-starting-total")
            self.assertEqual(sum(record["state"]["xps"]), requested)
            self.assertEqual(result.being.original.obj_type, "Half-elf")
            self.assertEqual(result.being.original.race, half_elf_template.race)
            self.assertEqual(result.being.original.hit_dice, half_elf_template.hit_dice)
            self.assertEqual(result.being.original.alignment, half_elf_template.alignment)
            self.assertEqual(result.being.original.armor_class, half_elf_template.armor_class)
            self.assertEqual(result.being.original.challenge_rating, half_elf_template.challenge_rating)
            self.assertIsNone(result.being.geometry)
            self.assertEqual(result.being.possessions, [])
            self.assertEqual(result.being.get_skill_level("armed combat"), 1)
            self.assertEqual(result.being.get_weapon_skill_level("Dagger"), 1)
            self.assertEqual(result.being.skill_experience, {})
            self.assertEqual(result.being.skill_use_history, [])
            self.assertEqual(result.being._skill_practice_baselines, {})
            self.assertEqual(result.source_sha256, hashlib.sha256(result.source_record_bytes).hexdigest())
            self.assertEqual(result.engine_identity, record["engine"])
            # Generator class/level data is retained verbatim, not translated to a native class.
            self.assertEqual(len(record["state"]["classes"]), len(record["state"]["levels"]))
        self.assertEqual(positive.source_record_bytes, positive_again.source_record_bytes)
        self.assertNotEqual(positive.being.id, positive_again.being.id)
        self.assertIs(world.get_object_by_id(positive.being.id), positive.being)
        self.assertIs(world.get_object_by_id(positive_again.being.id), positive_again.being)

    def test_resolved_empty_is_imported_but_unresolved_refuses_without_registration(self):
        world = _world()
        empty = generate_npcgen_arena_being(
            world, seed=76, starting_experience=0, cost_modifiers="neutral")
        self.assertEqual(empty.skills_status["status"], "resolved")
        self.assertEqual(empty.being.get_skills(), {})
        before = set(world.object_registry.object_instances)

        with self.assertRaises(ArenaNPCRefusal) as raised:
            generate_npcgen_arena_being(
                world, seed=1, starting_experience=12000, cost_modifiers="neutral")

        self.assertEqual(raised.exception.code, "skill_profile_unresolved")
        self.assertEqual(raised.exception.to_dict()["details"]["cost_modifiers"], "neutral")
        self.assertEqual(set(world.object_registry.object_instances), before)

    def test_unmatched_race_and_dead_age_refuse_without_registration(self):
        world = _world()
        before = set(world.object_registry.object_instances)
        cases = ((4, 12000, "character", "unsupported_native_race"),
                 (1, 9999999, "character", "skill_profile_unresolved"))
        for seed, xp, policy, code in cases:
            with self.subTest(seed=seed, xp=xp):
                with self.assertRaises(ArenaNPCRefusal) as raised:
                    generate_npcgen_arena_being(
                        world, seed=seed, starting_experience=xp, cost_modifiers=policy)
                self.assertEqual(raised.exception.code, code)
                self.assertEqual(set(world.object_registry.object_instances), before)
        self.assertIn("Dead", raised.exception.to_dict()["details"]["reason"])

    def test_unsupported_native_skill_refuses_before_registration(self):
        genuine = api.generate_arena_candidate(1, 12000, cost_modifiers="character")
        tampered = deepcopy(genuine.record)
        tampered["state"]["skills"]["skills"]["unknown source skill"] = 1
        tampered["sheet"]["skills"] = deepcopy(tampered["state"]["skills"])
        altered_candidate = type(genuine)(genuine.npc, genuine.skills_status, tampered)
        world = _world()
        before = set(world.object_registry.object_instances)

        with patch("npcgen.api.generate_arena_candidate", return_value=altered_candidate):
            with self.assertRaises(ArenaNPCRefusal) as raised:
                generate_npcgen_arena_being(
                    world, seed=1, starting_experience=12000, cost_modifiers="character")

        self.assertEqual(raised.exception.code, "unsupported_skill")
        self.assertEqual(set(world.object_registry.object_instances), before)

    def test_invalid_experience_domain_is_not_coerced(self):
        world = _world()
        for value in (True, 1.0, -1):
            with self.subTest(value=value):
                with self.assertRaises(ArenaNPCRefusal) as raised:
                    generate_npcgen_arena_being(
                        world, seed=1, starting_experience=value, cost_modifiers="character")
                self.assertEqual(raised.exception.code, "invalid_request")
        self.assertEqual(world.object_registry.object_instances, {})


if __name__ == "__main__":
    unittest.main()
