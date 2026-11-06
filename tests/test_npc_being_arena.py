"""Opt-in developer Arena: source-derived Being, one native transactional thrust."""

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "examples"))
sys.path.insert(0, str(ROOT / "src"))

from npc_being_arena import _format_developer_view, build_arena


class TestNpcBeingArena(unittest.TestCase):
    def test_one_operator_action_is_native_transactional_and_one_shot(self):
        arena = build_arena(seed=72002)
        view = arena.developer_view()

        self.assertEqual(arena.encounter.progression_mode, "transactional")
        self.assertEqual(view["audience"],
                         "local omniscient developer view; not an Agent observation")
        self.assertEqual(view["source_derived"]["display_name"], "Tobe")
        self.assertEqual(view["source_derived"]["abilities"],
                         {"Str": 12, "Int": 11, "Wis": 16,
                          "Dex": 12, "Con": 9, "Cha": 14})
        self.assertEqual(view["source_derived"]["skills"], {
            "skills": {"armed combat": 1}, "weapon_skills": {"Dagger": 2}})
        self.assertEqual(view["source_derived"]["initial_hit_points"], {
            "value": 23, "source_path": "state.hps",
            "meaning": "generated initial HP value; not a maximum-HP or Hit Dice mapping"})
        self.assertEqual(view["npc_native"]["skills"],
                         {"armed combat": 1, "Dagger": 2})
        self.assertEqual(view["npc_native"]["initial_HP"], 23)
        self.assertEqual(view["npc_native"]["current_HP"], 23)
        self.assertAlmostEqual(view["source_derived"]["physical"]["stature_inches"],
                               49.59000015258789)
        self.assertAlmostEqual(view["source_derived"]["physical"]["body_weight_pounds"],
                               46.8067626953125)
        self.assertAlmostEqual(view["npc_native"]["length_inches"], 49.59000015258789)
        self.assertAlmostEqual(view["npc_native"]["weight_pounds"], 46.8067626953125)
        self.assertEqual(view["npc_native"]["geometry"]["type"], "sphere")
        self.assertEqual(view["npc_native"]["geometry"]["radius"], 0.25)
        self.assertAlmostEqual(view["npc_native"]["personal_arm_length_inches"],
                               49.59000015258789 * 15 / 37)
        self.assertEqual(view["npc_native"]["dagger_length_inches"], 15)
        self.assertAlmostEqual(view["npc_native"]["effective_reach_inches"],
                               (49.59000015258789 * 15 / 37) + 15)
        self.assertAlmostEqual(view["npc_native"]["effective_reach_meters"],
                               ((49.59000015258789 * 15 / 37) + 15) * 0.0254)
        self.assertFalse(view["npc_native"]["reach_uses_geometry"])
        self.assertEqual(view["melee_eligibility"]["target_center_distance_meters"], 0.75)
        self.assertEqual(view["melee_eligibility"]["expected_status"], "in_reach")
        self.assertEqual(arena.strike._status(arena.encounter)[0], "in_reach")
        self.assertAlmostEqual(view["opponent_arena_authored"]["position"][0],
                               0.75 / 0.9144)
        self.assertEqual(view["npc_native"]["position"], (0.0, 0.0, 0.0))
        self.assertEqual(view["npc_native"]["position_unit"], "yard")
        self.assertEqual(view["npc_native"]["geometry_unit"], "meter")
        self.assertEqual(view["opponent_arena_authored"]["position_unit"], "yard")
        self.assertEqual(view["opponent_arena_authored"]["geometry_unit"], "meter")
        self.assertEqual(view["opponent_arena_authored"]["initial_HP"], 10)
        self.assertEqual(view["opponent_arena_authored"]["current_HP"], 10)
        self.assertEqual(view["opponent_arena_authored"]["AC"], 11)
        self.assertEqual((arena.opponent.original.length, arena.opponent.original.weight), (1.7, 70))
        self.assertNotIn("source_record", view)
        self.assertNotIn("race", view["source_derived"])
        rendered = _format_developer_view(view)
        self.assertIn("Source-derived acquired ranks", rendered)
        self.assertIn("Source-derived initial HP=23 (state.hps)", rendered)
        self.assertIn("Arena-authored", rendered)
        self.assertNotIn("High Elf", rendered)
        self.assertNotIn("family", rendered.lower())
        self.assertEqual(tuple(arena.encounter.__dict__.get("_atomic_interval_history", ())), ())

        result = arena.resolve_one_thrust()
        self.assertEqual(result["progression_mode"], "transactional")
        self.assertEqual(result["action_id"], arena.strike.id)
        self.assertEqual(result["boundary"], arena.strike.end_time)
        self.assertEqual(result["outcome"], "normal")
        self.assertEqual(result["metadata"], {"distance": 0.75})
        self.assertEqual(result["causal_damage"], {"body": 4})
        self.assertEqual(result["target_hp_after"], 6)
        self.assertEqual(result["native_receipt_boundaries"], (1, 2, 3, 4))
        self.assertEqual(arena.encounter.inspect_committed().action(arena.strike.id).facts.outcome,
                         result["outcome"])
        time_after = arena.encounter.time
        receipts_after = tuple(arena.encounter.__dict__.get("_atomic_interval_history", ()))
        hp_after = arena.opponent.get_hit_points()
        with self.assertRaisesRegex(RuntimeError, "already been submitted"):
            arena.resolve_one_thrust()
        self.assertEqual(arena.encounter.time, time_after)
        self.assertEqual(tuple(arena.encounter.__dict__.get("_atomic_interval_history", ())),
                         receipts_after)
        self.assertEqual(arena.opponent.get_hit_points(), hp_after)

    def test_melee_status_uses_reach_boundary_and_geometry_is_not_a_reach_input(self):
        initial = build_arena()
        reach = initial.strike.reach
        self.assertAlmostEqual(reach, ((49.59000015258789 * 15 / 37) + 15) * 0.0254)
        initial_geometry = initial.npc.geometry
        from spatial.geometry import Sphere
        initial.npc.set_geometry(Sphere(4.0))
        from melee_combat import effective_melee_reach_meters
        self.assertEqual(effective_melee_reach_meters(
            initial.npc.original, initial.world.get_object_by_id(initial.dagger_id).original), reach)
        initial.npc.set_geometry(initial_geometry)
        at_boundary = build_arena(target_distance_meters=reach)
        above_boundary = build_arena(target_distance_meters=reach + 0.0001)
        self.assertEqual(at_boundary.strike._status(at_boundary.encounter)[0], "in_reach")
        self.assertEqual(above_boundary.strike._status(above_boundary.encounter)[0], "out_of_reach")

    def test_measured_reach_boundary_is_in_range_and_immediately_above_is_not(self):
        initial = build_arena()
        reach = initial.strike.reach
        at_boundary = build_arena(target_distance_meters=reach)
        above = build_arena(target_distance_meters=reach + 0.0001)
        self.assertEqual(at_boundary.strike._status(at_boundary.encounter)[0], "in_reach")
        self.assertEqual(above.strike._status(above.encounter)[0], "out_of_reach")

    def test_out_of_reach_is_committed_without_damage_or_rng_advance(self):
        arena = build_arena(target_distance_meters=1.5)
        initial_rng = arena.rng.state
        result = arena.resolve_one_thrust()
        self.assertEqual(result["outcome"], "out_of_reach")
        self.assertEqual(result["metadata"], {"distance": 1.5})
        self.assertEqual(result["causal_damage"], {})
        self.assertEqual(result["target_hp_after"], 10)
        self.assertEqual(arena.rng.state, initial_rng)
        self.assertEqual(result["native_receipt_boundaries"], (1, 2, 3, 4))
        inspection = arena.encounter.inspect_committed(result["boundary"])
        self.assertEqual(inspection.action(arena.strike.id).facts.outcome, "out_of_reach")

    def test_transactional_reach_uses_post_movement_position_at_impact(self):
        moving_into_reach = build_arena(target_distance_meters=1.5)
        moving_into_reach.submit_thrust()
        moving_into_reach.encounter.step(
            3, velocities={moving_into_reach.opponent.id: (-0.25, 0, 0)})
        self.assertAlmostEqual(moving_into_reach.opponent.get_position().x, 0.75)
        entered = moving_into_reach.advance_to_commit()
        self.assertEqual(entered["outcome"], "normal")
        self.assertEqual(entered["metadata"], {"distance": 0.75})
        self.assertEqual(entered["target_hp_after"], 6)

        moving_out_of_reach = build_arena(target_distance_meters=0.75)
        moving_out_of_reach.submit_thrust()
        moving_out_of_reach.encounter.step(
            3, velocities={moving_out_of_reach.opponent.id: (0.25, 0, 0)})
        self.assertAlmostEqual(moving_out_of_reach.opponent.get_position().x, 1.5)
        exited = moving_out_of_reach.advance_to_commit()
        self.assertEqual(exited["outcome"], "out_of_reach")
        self.assertEqual(exited["metadata"], {"distance": 1.5})
        self.assertEqual(exited["target_hp_after"], 10)

    def test_full_precision_position_is_preserved_at_each_committed_boundary(self):
        arena = build_arena(target_distance_meters=1.5)
        arena.submit_thrust()
        expected_positions = (1.25, 1.0, 0.75)

        for boundary, expected_x in enumerate(expected_positions, start=1):
            arena.encounter.step(
                1, velocities={arena.opponent.id: (-0.25, 0.0, 0.0)})
            self.assertEqual(arena.encounter.time, boundary)
            self.assertEqual(arena.opponent.get_position().x, expected_x)
            self.assertEqual(
                arena.encounter.inspect_committed(boundary)
                .target(arena.opponent.id).position.x,
                expected_x,
            )
            receipt = arena.encounter._atomic_interval_history[-1]
            self.assertEqual(receipt.boundary, boundary)

        result = arena.advance_to_commit()
        self.assertEqual(result["outcome"], "normal")
        self.assertEqual(result["metadata"], {"distance": 0.75})
        self.assertEqual(result["target_hp_after"], 6)


if __name__ == "__main__":
    unittest.main()
