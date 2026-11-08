"""Native movement-rate and one-boundary intent foundation tests."""

import random
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "examples"))
sys.path.insert(0, str(ROOT / "src"))

from activities import RunAction
from arena_initialization import initialize_two_being_arena
from atomic_publication import RNGCursor
from movement_intent import (MovementIntent, MovementIntentRefusal,
                             MovementRateConditions, evaluate_movement_rate)
from skill import SkillDefinition
from spatial.state import CartesianPosition


class TestNativeMovementIntent(unittest.TestCase):
    def setUp(self):
        self.candidate = initialize_two_being_arena(0, 5, 5, 20261107)
        self.encounter = self.candidate.encounter
        self.player = self.candidate.participants[0].native.being
        self.opponent = self.candidate.participants[1].native.being
        # Test-only authored positions and world premise: the corridor from
        # (0,0,0) to (20,0,0) m is clear for this demonstration. No Arena grid,
        # reference-point separation, or invented Being volume proves that.
        self.player.set_position(CartesianPosition(0.0, 0.0, 0.0))
        self.opponent.set_position(CartesianPosition(0.0, 100.0, 0.0))
        self.rng = RNGCursor(random.Random(self.candidate.root_seed).getstate())
        self.global_rng = random.getstate()

    def conditions(self, *, demanding=False):
        # Explicit test-only rate premises: Plains/Road, unhampered, fresh, no
        # carried equipment, upright, forward-aligned corridor, and known Action demand.
        self.assertEqual(self.player.possessions, [])
        self.assertEqual(self.player.weapons, [])
        self.assertEqual(self.player.get_fatigue_level(), 0)
        return MovementRateConditions(
            terrain_multiplier=1.0,
            hampered_multiplier=1.0,
            encumbrance_lb=0.0,
            posture="standing",
            direction="forward",
            concurrent_demanding_action=demanding)

    def activate_run_observer(self):
        action = RunAction(self.candidate.universe, self.player.id, 0, 1,
                           minimum_distance=0.5, experience=0)
        self.encounter.activate_arena_for_player_action(
            self.player.id, action, rng_owner=self.rng)
        return action

    def test_rate_categories_and_run_skill_increment_follow_adopted_units(self):
        conditions = self.conditions()
        expected = {"sprint": 7.0, "run": 14.0 / 3.0, "jog": 3.5,
                    "hustle": 7.0 / 3.0, "walk": 1.75}
        for category, yards_per_second in expected.items():
            result = evaluate_movement_rate(self.player, category, conditions)
            self.assertEqual(result.run_level, 0)
            self.assertAlmostEqual(result.sprint_yards_per_second, 7.0)
            self.assertAlmostEqual(result.yards_per_second, yards_per_second)
            self.assertAlmostEqual(result.meters_per_second, yards_per_second * 0.9144)

        skill_dictionary = self.candidate.universe.get_skill_dictionary()
        # Run is adopted by r61 but absent from this installed native skill
        # dictionary; declare its adopted definition in this test fixture.
        skill_dictionary.add_skill(SkillDefinition("Run", True, True))
        self.player.set_skill_level(skill_dictionary, "Run", 3)
        for category, ratio in {"sprint": 1.0, "run": 2.0 / 3.0,
                                "jog": 0.5, "hustle": 1.0 / 3.0,
                                "walk": 0.25}.items():
            skilled = evaluate_movement_rate(self.player, category, conditions)
            self.assertEqual(skilled.run_level, 3)
            self.assertAlmostEqual(skilled.sprint_yards_per_second, 8.0)
            self.assertAlmostEqual(skilled.yards_per_second, 8.0 * ratio)
            self.assertAlmostEqual(skilled.meters_per_second, 8.0 * ratio * 0.9144)

    def test_missing_rate_cap_input_refuses_instead_of_assuming_neutral(self):
        missing_terrain = MovementRateConditions(
            hampered_multiplier=1.0, encumbrance_lb=0.0,
            posture="standing", direction="forward",
            concurrent_demanding_action=False)
        with self.assertRaises(MovementIntentRefusal) as refused:
            evaluate_movement_rate(self.player, "walk", missing_terrain)
        self.assertEqual(refused.exception.code, "unknown_movement_limit")
        self.assertIn("terrain_multiplier", str(refused.exception))

    def test_strength_table_boundary_is_used_and_out_of_table_values_refuse(self):
        conditions = self.conditions()
        self.player.set_ability("STR", 23)
        self.assertAlmostEqual(
            evaluate_movement_rate(self.player, "walk", conditions).yards_per_second,
            1.75)
        self.player.set_ability("STR", 24)
        with self.assertRaises(MovementIntentRefusal) as refused:
            evaluate_movement_rate(self.player, "walk", conditions)
        self.assertEqual(refused.exception.code, "unsupported_strength")

    def test_intent_moves_before_co_resolving_run_observer_at_native_boundary(self):
        action = self.activate_run_observer()
        start = self.player.get_position()
        destination = CartesianPosition(start.x + 20.0, start.y, start.z)
        intent = MovementIntent(self.player.id, destination, "walk", "arena-move-1", 1)
        conditions = self.conditions(demanding=True)

        step = self.encounter.step(1, movement_intent=intent,
                                   movement_conditions=conditions)
        end = self.player.get_position()
        self.assertEqual(step.movement_decision_ids, ("arena-move-1",))
        self.assertIn(self.player.id, step.moved_entity_ids)
        self.assertEqual((step.start_time, step.end_time), (0, 1))
        self.assertAlmostEqual(end.x - start.x, 0.9144)
        self.assertEqual(end.y, start.y)
        self.assertEqual(end.z, start.z)
        self.assertEqual(self.encounter.time, 1)
        result = self.encounter.inspect_committed(1).action(action.id)
        self.assertEqual(result.facts.outcome, "success")
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
        self.assertEqual(self.rng.state, before_rng)
        self.assertEqual(random.getstate(), before_global_rng)
        self.assertEqual(self.encounter.aware_beings(self.player.id), [])


if __name__ == "__main__":
    unittest.main()
