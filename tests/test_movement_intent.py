"""Native movement-rate and one-boundary intent foundation tests."""

import random
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "examples"))
sys.path.insert(0, str(ROOT / "src"))

from arena_browser_session import GeneratedArenaSession
from arena_hex_map import HexAddress
from action_evaluation import capture_snapshot
from movement_intent import (MovementIntent, MovementIntentRefusal,
                             MovementRateConditions, evaluate_movement_rate)
from skill import SkillDictionary
from spatial.state import CartesianPosition


class TestNativeMovementIntent(unittest.TestCase):
    def setUp(self):
        self.session = GeneratedArenaSession(root_seed_factory=lambda: 20261107)
        self.session.generate({"starting_experience": "0", "width_cells": "5", "height_cells": "5"})
        self.candidate = self.session.active_candidate
        self.encounter = self.candidate.encounter
        self.player = self.candidate.participants[0].native.being
        self.opponent = self.candidate.participants[1].native.being
        # Test-only authored positions. The movement test below separately
        # declares its corridor premise; the map does not prove clearance.
        self.player.set_position(CartesianPosition(0.0, 0.0, 0.0))
        self.opponent.set_position(CartesianPosition(0.0, 100.0, 0.0))
        self.rng = self.session._rng_cursor
        self.assertEqual(self.rng.state, random.Random(self.candidate.root_seed).getstate())
        self.global_rng = random.getstate()

    def conditions(self, *, demanding=False):
        # Explicit test-only rate premises: Plains/Road, unhampered, no
        # carried equipment, upright, forward-aligned corridor, and known Action demand.
        self.assertEqual(self.player.possessions, [])
        self.assertEqual(self.player.weapons, [])
        return MovementRateConditions(
            terrain_multiplier=1.0,
            hampered_multiplier=1.0,
            posture="standing",
            direction="forward",
            concurrent_demanding_action=demanding)

    def activate_run_observer(self):
        self.session.choose_run()
        return self.candidate.universe.event_history[self.session._player_action_id]

    def test_rate_categories_and_run_skill_increment_follow_adopted_units(self):
        conditions = self.conditions()
        self.assertEqual(self.player.get_fatigue_level(), 0)
        skills = self.candidate.universe.get_skill_dictionary()
        self.assertEqual(skills.get_skill_definition("run"),
                         {"is_ordinary": True, "is_progressive": True})
        self.assertIsNone(skills.get_skill_definition("Run"))
        self.assertIsNone(self.player.get_skill_level("run"))
        original_experience = dict(self.player.skill_experience)
        original_history = list(self.player.skill_use_history)
        expected = {"sprint": 7.0, "run": 14.0 / 3.0, "jog": 3.5,
                    "hustle": 7.0 / 3.0, "walk": 1.75}
        for category, yards_per_second in expected.items():
            result = evaluate_movement_rate(self.player, category, conditions,
                                            universe=self.candidate.universe)
            self.assertEqual(result.run_level, 0)
            self.assertEqual(result.encumbrance_lb, 0.0)
            self.assertAlmostEqual(result.sprint_yards_per_second, 7.0)
            self.assertAlmostEqual(result.yards_per_second, yards_per_second)
            self.assertAlmostEqual(result.meters_per_second, yards_per_second * 0.9144)

        self.player.set_skill_level(skills, "run", 3)
        for category, ratio in {"sprint": 1.0, "run": 2.0 / 3.0,
                                "jog": 0.5, "hustle": 1.0 / 3.0,
                                "walk": 0.25}.items():
            skilled = evaluate_movement_rate(self.player, category, conditions,
                                             universe=self.candidate.universe)
            self.assertEqual(skilled.run_level, 3)
            self.assertAlmostEqual(skilled.sprint_yards_per_second, 8.0)
            self.assertAlmostEqual(skilled.yards_per_second, 8.0 * ratio)
            self.assertAlmostEqual(skilled.meters_per_second, 8.0 * ratio * 0.9144)
        self.assertEqual(self.player.skill_experience, original_experience)
        self.assertEqual(self.player.skill_use_history, original_history)

    def test_nonexistent_run_definition_refuses_instead_of_defaulting_missing_rank(self):
        conditions = self.conditions()
        with self.assertRaises(MovementIntentRefusal) as refused:
            evaluate_movement_rate(self.player, "walk", conditions,
                                   universe=self.candidate.universe,
                                   skill_dictionary=SkillDictionary())
        self.assertEqual(refused.exception.code, "unknown_run_skill")

    def test_native_object_weights_derive_carried_mass(self):
        conditions = self.conditions()
        brick_id = self.candidate.universe.make_object_for_being(
            self.player.id, "Brick", "Test carried brick")
        self.assertIsNotNone(brick_id)
        result = evaluate_movement_rate(self.player, "sprint", conditions,
                                        universe=self.candidate.universe)
        self.assertEqual(result.encumbrance_lb, 1.5)
        self.assertAlmostEqual(result.maximum_yards_per_second, 7.0 * (1 - 1.5 / 300.0))

    def test_movement_load_uses_common_pre_action_inventory_snapshot(self):
        conditions = self.conditions()
        brick_id = self.candidate.universe.make_object_for_being(
            self.player.id, "Brick", "Test carried brick")
        self.encounter.time = 1
        snapshot = capture_snapshot(self.encounter, 1)
        brick = self.candidate.universe.get_object_by_id(brick_id)
        brick.current.weight = 100.0
        result = evaluate_movement_rate(
            self.player, "sprint", conditions, universe=self.candidate.universe,
            pre_action_snapshot=snapshot)
        self.assertEqual(snapshot.entity(brick_id).data["weight"], 1.5)
        self.assertEqual(result.encumbrance_lb, 1.5)

    def test_native_physical_fatigue_adjusts_fitness_strength_and_category_cap(self):
        self.player.set_fatigue_level(2)
        result = evaluate_movement_rate(
            self.player, "sprint", self.conditions(), universe=self.candidate.universe)
        self.assertEqual(result.physical_fatigue_level, 2)
        self.assertAlmostEqual(result.sprint_yards_per_second, 6.5)
        self.assertAlmostEqual(result.yards_per_second, 3.25)

    def test_incapacitating_native_fatigue_refuses_movement(self):
        self.player.set_fatigue_level(5)
        with self.assertRaises(MovementIntentRefusal) as refused:
            evaluate_movement_rate(
                self.player, "walk", self.conditions(), universe=self.candidate.universe)
        self.assertEqual(refused.exception.code, "incapacitated")

    def test_missing_rate_cap_input_refuses_instead_of_assuming_neutral(self):
        missing_terrain = MovementRateConditions(
            hampered_multiplier=1.0,
            posture="standing", direction="forward",
            concurrent_demanding_action=False)
        with self.assertRaises(MovementIntentRefusal) as refused:
            evaluate_movement_rate(self.player, "walk", missing_terrain,
                                   universe=self.candidate.universe)
        self.assertEqual(refused.exception.code, "unknown_movement_limit")
        self.assertIn("terrain_multiplier", str(refused.exception))

    def test_strength_table_boundary_is_used_and_out_of_table_values_refuse(self):
        conditions = self.conditions()
        self.player.set_ability("STR", 23)
        self.assertAlmostEqual(
            evaluate_movement_rate(self.player, "walk", conditions,
                                   universe=self.candidate.universe).yards_per_second,
            1.75)
        self.player.set_ability("STR", 24)
        with self.assertRaises(MovementIntentRefusal) as refused:
            evaluate_movement_rate(self.player, "walk", conditions,
                                   universe=self.candidate.universe)
        self.assertEqual(refused.exception.code, "unsupported_strength")

    def test_intent_moves_before_co_resolving_run_observer_at_native_boundary(self):
        action = self.activate_run_observer()
        layout = self.candidate.arena_map.layout
        start = layout.center_position(HexAddress(0, 0))
        self.player.set_position(start)
        self.opponent.set_position(CartesianPosition(100.0, 100.0, 0.0))
        public_before = self.session.public_view()
        self.assertEqual(public_before["player"]["cell"], {"column": 0, "row": 0})
        # Test-only authored clear corridor points toward the adjacent hex
        # center. No production geometry or clearance is inferred.
        direction = (3**0.5 / 2, 0.5)
        destination = CartesianPosition(start.x + direction[0] * 20.0,
                                        start.y + direction[1] * 20.0, start.z)
        intent = MovementIntent(self.player.id, destination, "walk", "arena-move-1", 1)
        # Action declarations have no adopted demanding/non-demanding flag;
        # this one-second cap is an explicit premise for this fixture.
        conditions = self.conditions(demanding=True)

        step = self.encounter.step(1, movement_intent=intent,
                                   movement_conditions=conditions)
        end = self.player.get_position()
        self.assertEqual(step.movement_decision_ids, ("arena-move-1",))
        self.assertIn(self.player.id, step.moved_entity_ids)
        self.assertEqual((step.start_time, step.end_time), (0, 1))
        self.assertAlmostEqual(end.x - start.x, direction[0] * 0.9144)
        self.assertAlmostEqual(end.y - start.y, direction[1] * 0.9144)
        self.assertEqual(end.z, start.z)
        self.assertEqual(layout.cell_at_position(end), HexAddress(1, 0))
        self.assertEqual(self.encounter.time, 1)
        result = self.encounter.inspect_committed(1).action(action.id)
        self.assertEqual(result.facts.outcome, "success")
        self.session._player_action_outcome = result.facts.outcome
        public_after = self.session.public_view()
        public_keys = {"state", "load_available", "encounter_name", "time_seconds", "map",
                       "player", "player_action", "run_available", "advance_available",
                       "spot_available", "spot_reason"}
        for projection in (public_before, public_after):
            encoded = repr(projection)
            self.assertEqual(set(projection), public_keys)
            self.assertNotIn(self.opponent.id, encoded)
            self.assertNotIn("opponent", projection)
        self.assertEqual(public_after["time_seconds"], 1)
        self.assertAlmostEqual(public_after["player"]["position_meters"]["x"], end.x)
        self.assertAlmostEqual(public_after["player"]["position_meters"]["y"], end.y)
        self.assertEqual(public_after["player"]["cell"], {"column": 1, "row": 0})
        self.assertEqual(self.encounter.aware_beings(self.player.id), [])
        self.assertEqual(self.encounter.aware_beings(self.opponent.id), [])
        self.assertEqual(self.rng.state, random.Random(self.candidate.root_seed).getstate())
        self.assertEqual(random.getstate(), self.global_rng)

    def test_invalid_unknown_stale_and_arrival_intents_change_no_state(self):
        self.activate_run_observer()
        conditions = self.conditions(demanding=True)
        start = self.player.get_position()
        before_history = dict(self.candidate.universe.event_history)
        before_pending = list(self.encounter.pending_action_list)
        before_choices = self.encounter.choice_state
        before_public_view = self.session.public_view()
        before_time = self.encounter.time
        before_rng = self.rng.state
        before_global_rng = random.getstate()

        far = CartesianPosition(start.x + 20.0, start.y, start.z)
        valid_shape = MovementIntent(self.player.id, far, "walk", "bad-context", 1)
        with self.assertRaises(MovementIntentRefusal):
            self.encounter.step(1, movement_intent=valid_shape,
                                movement_conditions=MovementRateConditions())

        too_close = MovementIntent(self.player.id,
                                   CartesianPosition(start.x + 0.5, start.y, start.z),
                                   "walk", "arrival", 1)
        with self.assertRaises(MovementIntentRefusal) as refused:
            self.encounter.step(1, movement_intent=too_close,
                                movement_conditions=conditions)
        self.assertEqual(refused.exception.code, "arrival_unsupported")

        stale = MovementIntent(self.player.id, far, "walk", "stale", 2)
        with self.assertRaises(MovementIntentRefusal) as refused:
            self.encounter.step(1, movement_intent=stale,
                                movement_conditions=conditions)
        self.assertEqual(refused.exception.code, "stale_boundary")

        self.assertEqual(self.encounter.time, before_time)
        self.assertEqual(self.player.get_position(), start)
        self.assertEqual(self.candidate.universe.event_history, before_history)
        self.assertEqual(self.encounter.pending_action_list, before_pending)
        self.assertEqual(self.encounter.choice_state, before_choices)
        self.assertEqual(self.session.public_view(), before_public_view)
        self.assertEqual(self.rng.state, before_rng)
        self.assertEqual(random.getstate(), before_global_rng)
        self.assertEqual(self.encounter.aware_beings(self.player.id), [])


if __name__ == "__main__":
    unittest.main()
