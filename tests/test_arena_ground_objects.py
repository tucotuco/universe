"""Typed, private ground combat Objects in the generated Arena."""

import json
import math
from pathlib import Path
import random
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "examples"))
sys.path.insert(0, str(ROOT / "src"))

from arena_browser_session import ArenaBrowserRequestError, GeneratedArenaSession
from arena_hex_map import ArenaHexLayout, HexAddress
from arena_initialization import initialize_two_being_arena
from armor import ArmorInstance
from object import ObjectInstance
from weapon import WeaponInstance


PROFILE = json.loads((ROOT / "tests/fixtures/arena/test_ground_loadout_profile.json").read_text())
GENERATE = {"starting_experience": "10000", "width_cells": "10", "height_cells": "5"}


def typed_fixture(count):
    types = (("weapon", "Dagger"), ("armor", "Leather armor"), ("shield", "Small shield"))
    return [{"source_item_id": f"arena-test-fixture:v1:{index:04d}",
             "category": types[index % len(types)][0],
             "native_type_key": types[index % len(types)][1],
             "quantity": 1, "ordinary": True, "magical": False,
             "mechanics": None, "origin": "universe-authored-test-fixture.v1"}
            for index in range(count)]


def placement_signature(candidate):
    return tuple((item.source_item_id, item.category, item.native_type_key,
                  item.column, item.row, item.position.as_tuple())
                 for item in candidate.ground_objects)


class TestArenaGroundObjects(unittest.TestCase):
    def test_generator_profile_builds_unique_unpossessed_native_weapon_armor_and_shields(self):
        before_global_rng = random.getstate()
        session = GeneratedArenaSession(root_seed_factory=lambda: 404004,
                                        ground_loadout_profile=PROFILE)
        first_view = session.generate(GENERATE)
        candidate = session.active_candidate
        self.assertEqual(random.getstate(), before_global_rng)
        cursor_before_view = session._rng_cursor.state
        module_rng_before_view = random.getstate()
        self.assertEqual(session.public_view(), first_view)
        self.assertEqual(session._rng_cursor.state, cursor_before_view)
        self.assertEqual(random.getstate(), module_rng_before_view)
        self.assertEqual(len(candidate.participants), 2)
        self.assertEqual(len(candidate.ground_objects), 8)
        self.assertEqual(len(candidate.ground_item_bindings), 8)
        self.assertEqual(len({item.source_item_id for item in candidate.ground_objects}), 8)
        native_ids = {item.native_object_id for item in candidate.ground_objects}
        self.assertEqual(len(native_ids), 8)
        self.assertTrue(all(source != native for source, native in candidate.ground_item_bindings))

        rows = [candidate.universe.get_object_by_id(item.native_object_id)
                for item in candidate.ground_objects]
        self.assertEqual(sum(isinstance(item, WeaponInstance) for item in rows), 6)
        self.assertEqual(sum(isinstance(item, ArmorInstance) for item in rows), 2)
        self.assertEqual(sum(item.category == "shield" for item in candidate.ground_objects), 2)
        dagger_ids = [item.native_object_id for item in candidate.ground_objects
                      if item.category == "weapon" and item.native_type_key == "Dagger"]
        self.assertEqual(len(dagger_ids), 4)
        self.assertEqual(len(set(dagger_ids)), 4)

        occupied_being_cells = set()
        for participant in candidate.participants:
            being = participant.native.being
            address = HexAddress(participant.placement.column, participant.placement.row)
            self.assertTrue(candidate.arena_map.layout.contains(address))
            occupied_being_cells.add(address)
            self.assertEqual(being.possessions, [])
            self.assertEqual(being.weapons, [])
            self.assertIsNone(being.current.armor_id)
            self.assertTrue(all(value is None for value in being.current.body_parts.values()))
            self.assertEqual(being.skill_use_history, [])
            self.assertEqual(being.shielded_with(candidate.universe), {})
        object_cells = {HexAddress(item.column, item.row) for item in candidate.ground_objects}
        self.assertEqual(len(object_cells), 8)
        self.assertFalse(object_cells & occupied_being_cells)
        for placement, instance in zip(candidate.ground_objects, rows):
            self.assertIsInstance(instance, ObjectInstance)
            self.assertIsNone(instance.parent_container_id)
            self.assertIsNone(instance.geometry)
            self.assertIsNone(instance.visual_occlusion)
            self.assertEqual(instance.get_position(), placement.position)
            self.assertEqual(placement.position,
                             candidate.ground_layout.center_position(HexAddress(placement.column,
                                                                                placement.row)))
            self.assertFalse(instance.current.is_magical)
            self.assertGreater(instance.current.weight, 0)
        self.assertEqual(candidate.ground_loadout_provenance[0]["profile"]["profile_id"],
                         "universe-ground-object-test")
        self.assertEqual(candidate.ground_loadout_provenance[0]["schema_version"], 1)

        public = json.dumps(first_view, sort_keys=True)
        self.assertNotIn("ground_objects", first_view)
        self.assertNotIn("ground_item_bindings", first_view)
        self.assertNotIn("npcgen-loadout:", public)
        self.assertIn("Dagger", public)
        for item in candidate.ground_objects:
            self.assertNotIn(item.native_object_id, public)
            self.assertNotIn(item.source_item_id, public)

        second = GeneratedArenaSession(root_seed_factory=lambda: 404004,
                                       ground_loadout_profile=PROFILE)
        second.generate(GENERATE)
        self.assertEqual(placement_signature(candidate), placement_signature(second.active_candidate))
        self.assertEqual({item.source_item_id for item in candidate.ground_objects},
                         {item.source_item_id for item in second.active_candidate.ground_objects})
        self.assertNotEqual(native_ids, {item.native_object_id
                                        for item in second.active_candidate.ground_objects})

    def test_full_initial_footprint_and_edge_sharing_expansion_are_distinct_and_reproducible(self):
        full = initialize_two_being_arena(0, 5, 5, 7070,
                                           ground_item_descriptions=typed_fixture(23))
        initial_cells = set(ArenaHexLayout.rectangle(5, 5).addresses())
        being_cells = {HexAddress(row.placement.column, row.placement.row)
                       for row in full.participants}
        item_cells = {HexAddress(row.column, row.row) for row in full.ground_objects}
        self.assertEqual(len(full.ground_objects), 23)
        self.assertEqual(len(initial_cells), 25)
        self.assertEqual(being_cells | item_cells, initial_cells)
        self.assertFalse(being_cells & item_cells)
        self.assertEqual(set(full.ground_layout.addresses()), initial_cells)

        expanded = initialize_two_being_arena(0, 5, 5, 7071,
                                              ground_item_descriptions=typed_fixture(31))
        replay = initialize_two_being_arena(0, 5, 5, 7071,
                                            ground_item_descriptions=typed_fixture(31))
        expanded_cells = set(expanded.ground_layout.addresses())
        additions = expanded_cells - initial_cells
        self.assertEqual(len(additions), 8)
        self.assertEqual(len(expanded_cells), 33)
        self.assertTrue(all(expanded.ground_layout.contains(cell) for cell in initial_cells))
        self.assertTrue(any(neighbor in initial_cells for cell in additions
                            for neighbor in expanded.ground_layout.neighbors(cell)))
        # The whole finite expanded outline remains connected by native edge neighbors.
        reached = {next(iter(initial_cells))}
        while True:
            more = {neighbor for cell in reached
                    for neighbor in expanded.ground_layout.neighbors(cell)
                    if neighbor in expanded_cells}
            if more <= reached:
                break
            reached.update(more)
        self.assertEqual(reached, expanded_cells)
        self.assertEqual(placement_signature(expanded), placement_signature(replay))
        self.assertEqual(set(expanded.ground_layout.addresses()),
                         set(replay.ground_layout.addresses()))
        self.assertTrue(all(item.column >= 0 and item.row >= 0 for item in expanded.ground_objects))

    def test_invalid_type_category_provenance_and_constructor_failure_preserve_active_session(self):
        session = GeneratedArenaSession(root_seed_factory=lambda: 8080,
                                        ground_item_descriptions=typed_fixture(4))
        session.generate({"starting_experience": "0", "width_cells": "5", "height_cells": "5"})
        previous = session.active_candidate
        before_view = session.public_view()
        before_rng = session._rng_cursor.state
        before_object_ids = set(previous.universe.get_object_registry().object_instances)
        cases = [
            [{**typed_fixture(1)[0], "native_type_key": "Dagger +2"}],
            [{**typed_fixture(1)[0], "category": "shield", "native_type_key": "Dagger"}],
            [{**typed_fixture(1)[0], "source_item_id": ""}],
            [{**typed_fixture(1)[0], "quantity": 2}],
            [{**typed_fixture(1)[0], "ordinary": False}],
            [{**typed_fixture(1)[0], "origin": ""}],
        ]
        for descriptions in cases:
            session._ground_item_descriptions = descriptions
            with self.assertRaises(ArenaBrowserRequestError):
                session.generate({"starting_experience": "0", "width_cells": "5", "height_cells": "5"})
            self.assertIs(session.active_candidate, previous)
            self.assertEqual(session.public_view(), before_view)
            self.assertEqual(session._rng_cursor.state, before_rng)
            self.assertEqual(set(previous.universe.get_object_registry().object_instances), before_object_ids)

        session._ground_item_descriptions = typed_fixture(4)
        from arena_ground_objects import WeaponInstance as _WeaponInstance
        weapon_constructions = 0
        def fail_second_weapon(*args, **kwargs):
            nonlocal weapon_constructions
            weapon_constructions += 1
            if weapon_constructions == 2:
                raise RuntimeError("injected second-object construction failure")
            return _WeaponInstance(*args, **kwargs)
        with patch("arena_ground_objects.WeaponInstance", side_effect=fail_second_weapon):
            with self.assertRaises(ArenaBrowserRequestError):
                session.generate({"starting_experience": "0", "width_cells": "5", "height_cells": "5"})
        self.assertIs(session.active_candidate, previous)
        self.assertEqual(session.public_view(), before_view)
        self.assertEqual(session._rng_cursor.state, before_rng)
        self.assertEqual(set(previous.universe.get_object_registry().object_instances), before_object_ids)

    def test_ground_objects_do_not_change_native_movement_or_implicitly_equip(self):
        session = GeneratedArenaSession(root_seed_factory=lambda: 20261107,
                                        ground_loadout_profile=PROFILE)
        initial = session.generate(GENERATE)
        candidate = session.active_candidate
        being = candidate.participants[0].native.being
        hidden = candidate.participants[1].native.being
        player_armor_class = being.get_armor_class()
        hidden_armor_class = hidden.get_armor_class()
        start = being.get_position()
        layout = candidate.arena_map.layout
        target_address = max(layout.addresses(), key=lambda address: math.dist(
            start.as_tuple(), layout.center_position(address, z=start.z).as_tuple()))
        target = layout.center_position(target_address, z=start.z)
        object_positions = {item.native_object_id: item.position for item in candidate.ground_objects}

        selected = session.choose_destination({"column": target_address.column,
                                               "row": target_address.row,
                                               "rate": "walk", "facing_policy": "turn"})
        self.assertEqual(selected["movement_plan"]["rate"], "walk")
        updated = session.choose_destination({"column": target_address.column,
                                              "row": target_address.row,
                                              "rate": "sprint", "facing_policy": "turn"})
        self.assertEqual(updated["movement_plan"]["rate"], "sprint")
        self.assertEqual(candidate.encounter.time, 0)
        self.assertEqual(being.get_position(), start)
        self.assertEqual(candidate.encounter._choice_book._choices, {})
        self.assertFalse(any(item.native_object_id in being.possessions + being.weapons
                             for item in candidate.ground_objects))

        steps = 0
        while True:
            cursor_before_view = session._rng_cursor.state
            module_rng_before_view = random.getstate()
            movement_view = session.public_view()
            self.assertEqual(session._rng_cursor.state, cursor_before_view)
            self.assertEqual(random.getstate(), module_rng_before_view)
            if movement_view["movement_plan"] is None:
                break
            state = session.advance_one_second()
            steps += 1
            self.assertNotIn(hidden.id, json.dumps(state))
            self.assertLessEqual(steps, 100)
        final = session.public_view()
        self.assertEqual(being.get_position(), target)
        self.assertEqual(final["player"]["position_meters"],
                         {"x": target.x, "y": target.y, "z": target.z})
        self.assertEqual(final["movement_outcome"], "arrived")
        self.assertNotIn(hidden.id, json.dumps(final))
        self.assertNotIn("ground_objects", final)
        self.assertEqual({item.native_object_id: item.position for item in candidate.ground_objects},
                         object_positions)
        self.assertEqual(being.possessions, [])
        self.assertEqual(being.weapons, [])
        self.assertIsNone(being.current.armor_id)
        self.assertEqual(being.get_armor_class(), player_armor_class)
        self.assertEqual(hidden.get_armor_class(), hidden_armor_class)
        self.assertEqual(being.skill_use_history, [])
        self.assertEqual(candidate.encounter.aware_beings(being.id), [hidden.id])
        self.assertEqual(candidate.encounter.aware_beings(hidden.id), [being.id])
        self.assertEqual(candidate.encounter._choice_book._choices, {})
        self.assertEqual(initial["map"]["width_cells"], 10)
        self.assertEqual(final["map"]["width_cells"], 10)


if __name__ == "__main__":
    unittest.main()
