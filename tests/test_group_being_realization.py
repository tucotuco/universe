"""Tests for resolution from statistical member to an Encounter Being."""
from pathlib import Path
import json
import math
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "examples")]

from being import BeingInstance
from library import Library
from statistical_group import StatisticalGroup
from universe import Universe
from realized_herder_encounter import run_scenario

CONFIG = json.loads((ROOT / "examples" / "nomadic_group.json").read_text())


def make_world_and_group():
    world = Universe("Realization test", library=Library(config_dir=str(ROOT / "src" / "config")))
    group = StatisticalGroup(CONFIG["group_name"], CONFIG["group_id"], CONFIG, CONFIG["seed"])
    world.add_object(group)
    return world, group


class TestGroupBeingRealization(unittest.TestCase):
    def test_realize_one_adult_without_realizing_population(self):
        world, group = make_world_and_group()
        counts = group.counts()
        registry_count = world.get_object_registry().len()
        member = group.member(0, "adults", 0)
        expected_position = group.member_position(member)
        being = group.realize_being(world, 0, "adults", 0, name="Herder")
        self.assertIsInstance(being, BeingInstance)
        self.assertEqual(being.id, member.id)
        self.assertEqual(being.get_position(), expected_position)
        self.assertIs(world.get_object_by_id(being.id), being)
        self.assertEqual(world.get_object_registry().len(), registry_count + 1)
        self.assertEqual(group.counts(), counts)
        self.assertEqual(group.realized_being_count, 1)
        self.assertEqual(group.materialized_count, 1)

    def test_repeat_realization_returns_same_mutable_instance(self):
        world, group = make_world_and_group()
        a = group.realize_being(world, 0, "adults", 0)
        a.set_skill_level(world.get_skill_dictionary(), "run", 2)
        b = group.realize_being(world, 0, "adults", 0)
        self.assertIs(a, b)
        self.assertEqual(b.get_skill_level("run"), 2)
        self.assertEqual(group.realized_being_count, 1)
        self.assertEqual(world.get_object_registry().len(), 2)
        with self.assertRaises(ValueError):
            group.realize_being(world, 0, "adults", 0, name="Another identity")

    def test_order_of_realization_does_not_change_identifiers_or_placements(self):
        w1, g1 = make_world_and_group()
        w2, g2 = make_world_and_group()
        first = g1.realize_being(w1, 0, "adults", 0)
        second = g2.realize_being(w2, 0, "adults", 0)
        self.assertEqual(first.id, second.id)
        self.assertEqual(first.get_position(), second.get_position())
        self.assertEqual(g1.counts(), g2.counts())
        self.assertEqual(g1.realized_being_count, 1)

    def test_original_member_record_and_authoritative_being_position(self):
        world, group = make_world_and_group()
        member = group.member(0, "adults", 0)
        being = group.realize_being(world, 0, "adults", 0)
        start = being.get_position()
        from spatial.state import CartesianPosition
        being.set_position(CartesianPosition(start.x + 2, start.y, start.z))
        self.assertEqual(group.member_position(member), being.get_position())
        group.advance(2)
        translated = being.get_position()
        self.assertAlmostEqual(translated.x, start.x + 2)
        self.assertAlmostEqual(translated.y - start.y, -6 + .5 * .005 * 4)
        self.assertEqual(group.member_position(member), translated)
        self.assertEqual(group.counts()["humans"], group.counts()["adults"] + group.counts()["children"])

    def test_invalid_categories_missing_registry_and_collision(self):
        world, group = make_world_and_group()
        with self.assertRaises(NotImplementedError):
            group.realize_being(world, 0, "dogs", 0)
        with self.assertRaises(IndexError):
            group.realize_being(world, 0, "adults", 999)
        self.assertEqual(group.realized_being_count, 0)
        with self.assertRaises(ValueError):
            group.realize_being(Universe("Other", library=world.library), 0, "adults", 0)
        from object import ObjectDefinition, ObjectInstance
        conflicting_id = f"{group.id}/0/adults/0"
        conflict = ObjectInstance(ObjectDefinition("marker", 0, 0, 0, 0, 0, 0, 0),
                                  "Conflict", id=conflicting_id)
        world.add_object(conflict)
        with self.assertRaises(ValueError):
            group.realize_being(world, 0, "adults", 0)

    def test_encounter_actions_use_realized_being(self):
        outcome = run_scenario()
        group = outcome["group"]
        herder = outcome["herder"]
        self.assertIs(herder, outcome["herder_again"])
        self.assertIn(herder.id, outcome["encounter"].being_list)
        self.assertIn(outcome["action"].id, outcome["encounter"].finished_action_list)
        self.assertEqual(outcome["action"].resolution.outcome, "success")
        self.assertEqual(herder.get_skill_level("run"), 1)
        self.assertEqual(herder.get_skill_experience("run"), 250)
        self.assertEqual(len(herder.skill_use_history), 1)
        self.assertEqual(group.counts(), outcome["counts_before"])
        self.assertEqual(group.realized_being_count, 1)
        self.assertEqual(group.member_position(outcome["member"]), herder.get_position())


if __name__ == "__main__":
    unittest.main()
