"""Integrated source-record, loadout-profile, and equipped-protagonist checks."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

from arena_browser_session import GeneratedArenaSession, ArenaBrowserRequestError
from arena_initialization import ArenaInitializationRefusal, initialize_two_being_arena
from arena_loadout_profiles import bundled_profiles, preview, realize
from library import Library
from armor import ArmorInstance
from weapon import WeaponInstance


ROOT = Path(__file__).resolve().parents[1]


class TestArenaCompleteProfilesAndKits(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.library = Library(config_dir=str(ROOT / "src" / "config"))
        cls.profiles = bundled_profiles()

    def test_complete_current_npcgen_record_is_source_and_save_load_preserved(self):
        session = GeneratedArenaSession(root_seed_factory=lambda: 11,
                                        default_equipment_mode="equipped")
        view = session.generate({"starting_experience": "1000", "width_cells": "5",
                                 "height_cells": "5", "equipment_mode": "equipped"})
        original_source = tuple(row.native.source_record_bytes for row in session.active_candidate.participants)
        specification = view["character"]["npcgen_specification"]
        self.assertEqual(set(specification), {"format", "schema_version", "engine", "generation",
            "edits", "state", "sheet", "notes"})
        self.assertEqual(specification["schema_version"], 2)
        self.assertIn("family", specification["state"])
        self.assertIn("possessions", specification["state"])
        self.assertIn("psionics", specification["state"])
        self.assertEqual(hashlib.sha256(original_source[0]).hexdigest(),
                         session.active_candidate.participants[0].native.source_sha256)
        saved = session.save_encounter_bytes()
        restored = GeneratedArenaSession()
        loaded_view = restored.load_encounter_bytes(saved)
        self.assertEqual(tuple(row.native.source_record_bytes for row in restored.active_candidate.participants),
                         original_source)
        self.assertEqual(loaded_view["character"]["npcgen_specification"], specification)
        player = restored.active_candidate.participants[0].native.being
        self.assertEqual(player.get_experience(), specification["state"]["xps"][0]
                         + sum(specification["state"]["xps"][1:]))
        self.assertIsNot(player.original, player.current)

    def test_checked_profiles_match_the_native_catalog_and_record_exact_selection(self):
        weapons = self.library.weapon_dictionary
        sword_types = sorted(name for name in weapons.object_categories["Swords"]
                             if name in weapons.objects and weapons.objects[name].weight > 0
                             and weapons.objects[name].is_magical is False)
        all_swords = self.profiles["all_swords"]
        self.assertEqual([row["native_type_key"] for row in all_swords["items"]], sword_types)
        group_profile = self.profiles["one_random_per_weapon_group"]
        first, provenance = realize(group_profile, self.library, root_seed=12345)
        second, provenance_again = realize(group_profile, self.library, root_seed=12345)
        self.assertEqual(first, second)
        self.assertEqual(provenance, provenance_again)
        selected = provenance[0]["selected_items"]
        groups = weapons.object_categories
        self.assertEqual([row["weapon_group"] for row in selected], list(groups))
        self.assertEqual(len(selected), len(groups))
        for row in selected:
            self.assertIn(row["native_type_key"], groups[row["weapon_group"]])

        session = GeneratedArenaSession(root_seed_factory=lambda: 101)
        session.select_ground_profile({"profile_id": "all_swords"})
        session.generate({"starting_experience": "5000", "width_cells": "5", "height_cells": "5",
                          "equipment_mode": "unequipped"})
        candidate = session.active_candidate
        self.assertEqual([row.native_type_key for row in candidate.ground_objects], sword_types)
        saved = session.save_encounter_bytes()
        loaded = GeneratedArenaSession()
        loaded.load_encounter_bytes(saved)
        self.assertEqual(loaded.active_candidate.ground_loadout_provenance,
                         candidate.ground_loadout_provenance)
        self.assertEqual([row.native_object_id for row in loaded.active_candidate.ground_objects],
                         [row.native_object_id for row in candidate.ground_objects])

    def test_empty_and_starter_bundled_profiles_generate_only_their_ground_objects(self):
        for profile_id, expected_count in (
                ("empty", 0), ("universe-arena-starter-ground-equipment", 8)):
            with self.subTest(profile_id=profile_id):
                session = GeneratedArenaSession(root_seed_factory=lambda: 101)
                session.select_ground_profile({"profile_id": profile_id})
                session.generate({"starting_experience": "1000", "width_cells": "5",
                                  "height_cells": "5", "equipment_mode": "equipped"})
                candidate = session.active_candidate
                self.assertEqual(len(candidate.ground_objects), expected_count)
                selected_profile = candidate.ground_loadout_provenance[0].get("profile_id")
                if selected_profile is None:
                    selected_profile = candidate.ground_loadout_provenance[0]["profile"]["profile_id"]
                self.assertEqual(selected_profile, profile_id)
                self.assertEqual(len(candidate.initial_equipment_provenance), 2)
                for row in candidate.ground_objects:
                    obj = candidate.universe.get_object_by_id(row.native_object_id)
                    self.assertIsNone(obj.parent_container_id)
                    self.assertIsNotNone(obj.get_position())

    def test_profile_upload_is_closed_and_map_capacity_fails_before_generation(self):
        session = GeneratedArenaSession()
        good = (ROOT / "tests" / "fixtures" / "arena" / "all-swords.json").read_bytes()
        uploaded = session.upload_ground_profile(good)
        self.assertTrue(uploaded["selected_profile_id"].startswith("uploaded:"))
        with self.assertRaises(ArenaBrowserRequestError):
            session.upload_ground_profile(b'{"format":"wrong","schema_version":1}')
        with self.assertRaises(ArenaBrowserRequestError):
            session.upload_ground_profile(b'{"format":"universe-arena-ground-loadout-profile",'
                b'"format":"duplicate","schema_version":1}')

        profile = {"format": "npcgen-arena-loadout-profile", "schema_version": 1,
            "profile_id": "too-many-ground-items", "profile_version": "1",
            "catalog_id": "universe-test", "catalog_version": "1",
            "catalog": [{"native_type_key": "Dagger", "category": "weapon"}],
            "categories": {"weapon": {"count": 12, "items": [{"native_type_key": "Dagger", "weight": 1}]},
                "armor": {"count": 0, "items": []}, "shield": {"count": 0, "items": []}}}
        with self.assertRaises(ArenaInitializationRefusal) as caught:
            initialize_two_being_arena(1000, 5, 5, 1, ground_loadout_profile=profile)
        self.assertEqual(caught.exception.code, "ground_profile_exceeds_map_capacity")
        self.assertIn("requires 24 distinct cells", caught.exception.message)
        self.assertIn("at least 26 total cells", caught.exception.message)

    def test_two_beings_receive_real_class_skill_strength_and_level_based_native_kits(self):
        candidate = initialize_two_being_arena(1000, 5, 5, 11, equipment_mode="equipped")
        kits = candidate.initial_equipment_provenance
        self.assertEqual(len(kits), 2)
        self.assertNotEqual(kits[0]["armor"]["type"], kits[1]["armor"]["type"])
        by_id = {being.id: being for being in (p.native.being for p in candidate.participants)}
        for kit in kits:
            being = by_id[kit["being_id"]]
            weapon = candidate.universe.get_object_by_id(kit["weapon"]["object_id"])
            armor = candidate.universe.get_object_by_id(kit["armor"]["object_id"])
            self.assertIs(type(weapon), WeaponInstance)
            self.assertIs(type(armor), ArmorInstance)
            self.assertEqual(weapon.parent_container_id, being.id)
            self.assertEqual(armor.parent_container_id, being.id)
            self.assertIsNone(weapon.get_position())
            self.assertIsNone(armor.get_position())
            self.assertIn(weapon.id, being.possessions)
            self.assertIn(armor.id, being.possessions)
            self.assertIn(weapon.id, being.weapons)
            self.assertEqual(being.current.body_parts[kit["weapon"]["hand"]], weapon.id)
            self.assertEqual(being.current.armor_id, armor.id)
            self.assertEqual(weapon.current.obj_type, kit["weapon"]["type"])
            self.assertEqual(armor.current.obj_type, kit["armor"]["type"])
            self.assertTrue(armor.current.defenses)
        unequipped = initialize_two_being_arena(1000, 5, 5, 11, equipment_mode="unequipped")
        self.assertEqual(unequipped.initial_equipment_provenance, ())
        self.assertTrue(all(not p.native.being.possessions and not p.native.being.weapons
                            and p.native.being.current.armor_id is None
                            for p in unequipped.participants))


if __name__ == "__main__":
    unittest.main()
