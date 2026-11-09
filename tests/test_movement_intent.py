"""Native movement-rate and one-boundary intent foundation tests."""

import random
import math
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "examples"))
sys.path.insert(0, str(ROOT / "src"))

from arena_browser_session import GeneratedArenaSession
from arena_hex_map import HexAddress
from action_evaluation import capture_snapshot
from movement_intent import (MovementIntent, MovementIntentRefusal,
                             MovementRateConditions, evaluate_movement_rate)
from hex_facing import FacingSector, classify_vector, facing_vector, nearest_facing
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
        # Explicit test-only rate premises. ``demanding`` is an authored
        # context fact and is never inferred from a co-resolving RunAction.
        self.assertEqual(self.player.possessions, [])
        self.assertEqual(self.player.weapons, [])
        return MovementRateConditions(
            terrain_multiplier=1.0,
            hampered_multiplier=1.0,
            direction="forward",
            concurrent_demanding_action=demanding)

    def snapshot(self):
        # Rate-only unit cases freeze the native Being at a test boundary while
        # returning the Encounter cursor to its unchanged setup state.
        old_time = self.encounter.time
        self.encounter.time = 1
        try:
            return capture_snapshot(self.encounter, 1)
        finally:
            self.encounter.time = old_time

    def evaluate(self, being, rate, conditions, **kwargs):
        kwargs.setdefault("pre_action_snapshot", self.snapshot())
        return evaluate_movement_rate(being, rate, conditions,
                                      universe=self.candidate.universe, **kwargs)

    def test_another_demanding_action_cap_is_one_yard_per_second(self):
        # The action classification is a premise for this arithmetic test;
        # no native action-wide demanding flag exists to infer it.
        capped = self.evaluate(self.player, "walk", self.conditions(demanding=True))
        self.assertEqual(capped.yards_per_second, 1.0)
        self.assertAlmostEqual(capped.meters_per_second, 0.9144)
        self.assertNotEqual(capped.meters_per_second, 1.0)

        backward = self.evaluate(
            self.player, "sprint", MovementRateConditions(
                terrain_multiplier=1.0, hampered_multiplier=1.0,
                direction="backward",
                concurrent_demanding_action=False),
        )
        self.assertEqual(backward.yards_per_second, 1.0)
        self.assertAlmostEqual(backward.meters_per_second, 0.9144)

        self.player.set_posture("lying")
        stricter = self.evaluate(
            self.player, "sprint", MovementRateConditions(
                terrain_multiplier=1.0, hampered_multiplier=1.0,
                direction="forward",
                concurrent_demanding_action=True),
        )
        self.player.set_posture("standing")
        self.assertEqual(stricter.yards_per_second, 0.5)
        self.assertAlmostEqual(stricter.meters_per_second, 0.4572)

        lateral = MovementRateConditions(
            terrain_multiplier=1.0, hampered_multiplier=1.0,
            direction="sideways",
            concurrent_demanding_action=False)
        sideways = self.evaluate(self.player, "sprint", lateral)
        self.assertEqual(sideways.yards_per_second, 1.0)
        self.assertAlmostEqual(sideways.meters_per_second, 0.9144)

    def test_posture_is_native_snapshot_state_and_legacy_prone_is_compatible(self):
        conditions = self.conditions()
        self.assertEqual(self.player.posture, "standing")
        for invalid in (True, "prone", [], 1):
            with self.assertRaises(ValueError):
                self.player.set_posture(invalid)
        self.player.set_posture("crouching")
        crouching = self.evaluate(self.player, "sprint", conditions)
        self.assertEqual(crouching.yards_per_second, 1.0)
        self.player.set_posture("lying")
        lying = self.evaluate(self.player, "sprint", conditions)
        self.assertEqual(lying.yards_per_second, 0.5)

        self.player.current.states.states["prone"] = True
        self.assertEqual(self.player.posture, "lying")
        with self.assertRaisesRegex(ValueError, "conflicts"):
            self.player.set_posture("standing")
        self.player.set_posture(None)
        self.assertEqual(self.player.posture, "lying")
        self.player.current.states.states["prone"] = False
        self.assertIsNone(self.player.posture)
        self.player.set_posture("standing")

    def test_rate_uses_posture_from_the_common_snapshot(self):
        self.player.set_posture("lying")
        snapshot = self.snapshot()
        self.player.set_posture("standing")
        result = self.evaluate(self.player, "sprint", self.conditions(),
                               pre_action_snapshot=snapshot)
        self.assertEqual(snapshot.entity(self.player.id).data["posture"], "lying")
        self.assertEqual(result.yards_per_second, 0.5)

    def test_unknown_posture_and_caller_posture_override_fail_closed(self):
        conditions = self.conditions()
        self.player.set_posture(None)
        before = (self.encounter.time, self.player.get_position(), self.rng.state,
                  random.getstate())
        with self.assertRaises(MovementIntentRefusal) as refused:
            self.evaluate(self.player, "walk", conditions)
        self.assertEqual(refused.exception.code, "unknown_posture")
        self.player.set_posture("standing")
        with self.assertRaises(MovementIntentRefusal) as refused:
            self.evaluate(self.player, "walk", MovementRateConditions(
                terrain_multiplier=1.0, hampered_multiplier=1.0, posture="standing",
                direction="forward", concurrent_demanding_action=False))
        self.assertEqual(refused.exception.code, "caller_posture_forbidden")
        self.assertEqual((self.encounter.time, self.player.get_position(), self.rng.state,
                          random.getstate()), before)

    def test_native_facing_fields_do_not_supply_a_twelve_orientation_snapshot(self):
        self.assertEqual((self.player.front_facing, self.player.top_facing), (1, 0))
        self.player.set_hex_facing(None)
        self.encounter.time = 1
        snapshot = capture_snapshot(self.encounter, 1)
        data = snapshot.entity(self.player.id).data
        self.assertIsNone(data["hex_facing"])

    def test_twelve_facings_front_endpoints_are_inclusive_and_other_headings_nonforward(self):
        for facing in range(12):
            angle = facing * 30.0
            for offset in (-30.0, 0.0, 30.0):
                theta = math.radians(angle + offset)
                self.assertIs(classify_vector(facing, (math.cos(theta), math.sin(theta), 0)),
                              FacingSector.FRONT)
            for offset in (-60.0, 60.0, 90.0, 120.0, 150.0, 180.0):
                theta = math.radians(angle + offset)
                self.assertIs(classify_vector(facing, (math.cos(theta), math.sin(theta), 0)),
                              FacingSector.NON_FORWARD)
            self.assertEqual(classify_vector(facing, (*facing_vector(facing), 0)), FacingSector.FRONT)
            self.assertEqual(nearest_facing((*facing_vector(facing), 0)), facing)
        for lower in range(12):
            theta = math.radians((lower + .5) * 30.0)
            self.assertEqual(nearest_facing((math.cos(theta), math.sin(theta), 0)),
                             min(lower, (lower + 1) % 12))
        with self.assertRaises(ValueError):
            self.player.set_hex_facing(12)

    def test_unknown_facing_refuses_and_explicit_maintained_nonforward_caps_at_one_yard(self):
        self.player.set_hex_facing(None)
        start = self.player.get_position()
        conditions = self.conditions()
        intent = MovementIntent(self.player.id,
            CartesianPosition(start.x, start.y + 20.0, start.z), "sprint", "north", 1)
        self.activate_run_observer()
        with self.assertRaises(MovementIntentRefusal) as refused:
            self.encounter.step(1, movement_intent=intent, movement_conditions=conditions)
        self.assertEqual(refused.exception.code, "unknown_facing")
        self.player.set_hex_facing(0)
        self.opponent.set_position(CartesianPosition(100.0, 100.0, 0.0))
        self.encounter.step(1, movement_intent=intent, movement_conditions=conditions)
        end = self.player.get_position()
        self.assertAlmostEqual(math.dist(start.as_tuple(), end.as_tuple()), 0.9144)

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
            result = self.evaluate(self.player, category, conditions)
            self.assertEqual(result.run_level, 0)
            self.assertEqual(result.encumbrance_lb, 0.0)
            self.assertAlmostEqual(result.sprint_yards_per_second, 7.0)
            self.assertAlmostEqual(result.yards_per_second, yards_per_second)
            self.assertAlmostEqual(result.meters_per_second, yards_per_second * 0.9144)

        self.player.set_skill_level(skills, "run", 3)
        for category, ratio in {"sprint": 1.0, "run": 2.0 / 3.0,
                                "jog": 0.5, "hustle": 1.0 / 3.0,
                                "walk": 0.25}.items():
            skilled = self.evaluate(self.player, category, conditions)
            self.assertEqual(skilled.run_level, 3)
            self.assertAlmostEqual(skilled.sprint_yards_per_second, 8.0)
            self.assertAlmostEqual(skilled.yards_per_second, 8.0 * ratio)
            self.assertAlmostEqual(skilled.meters_per_second, 8.0 * ratio * 0.9144)
        self.assertEqual(self.player.skill_experience, original_experience)
        self.assertEqual(self.player.skill_use_history, original_history)

    def test_nonexistent_run_definition_refuses_instead_of_defaulting_missing_rank(self):
        conditions = self.conditions()
        with self.assertRaises(MovementIntentRefusal) as refused:
            self.evaluate(self.player, "walk", conditions,
                          skill_dictionary=SkillDictionary())
        self.assertEqual(refused.exception.code, "unknown_run_skill")

    def test_native_object_weights_derive_carried_mass(self):
        conditions = self.conditions()
        brick_id = self.candidate.universe.make_object_for_being(
            self.player.id, "Brick", "Test carried brick")
        self.assertIsNotNone(brick_id)
        result = self.evaluate(self.player, "sprint", conditions)
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
        result = self.evaluate(self.player, "sprint", conditions,
                               pre_action_snapshot=snapshot)
        self.assertEqual(snapshot.entity(brick_id).data["weight"], 1.5)
        self.assertEqual(result.encumbrance_lb, 1.5)

    def test_native_physical_fatigue_adjusts_fitness_strength_and_category_cap(self):
        self.player.set_fatigue_level(2)
        result = self.evaluate(self.player, "sprint", self.conditions())
        self.assertEqual(result.physical_fatigue_level, 2)
        self.assertAlmostEqual(result.sprint_yards_per_second, 6.5)
        self.assertAlmostEqual(result.yards_per_second, 3.25)

    def test_incapacitating_native_fatigue_refuses_movement(self):
        self.player.set_fatigue_level(5)
        with self.assertRaises(MovementIntentRefusal) as refused:
            self.evaluate(self.player, "walk", self.conditions())
        self.assertEqual(refused.exception.code, "incapacitated")

    def test_missing_rate_cap_input_refuses_instead_of_assuming_neutral(self):
        missing_terrain = MovementRateConditions(
            hampered_multiplier=1.0,
            direction="forward",
            concurrent_demanding_action=False)
        with self.assertRaises(MovementIntentRefusal) as refused:
            self.evaluate(self.player, "walk", missing_terrain)
        self.assertEqual(refused.exception.code, "unknown_movement_limit")
        self.assertIn("terrain_multiplier", str(refused.exception))

    def test_strength_table_boundary_is_used_and_out_of_table_values_refuse(self):
        conditions = self.conditions()
        self.player.set_ability("STR", 23)
        self.assertAlmostEqual(
            self.evaluate(self.player, "walk", conditions).yards_per_second,
            1.75)
        self.player.set_ability("STR", 24)
        with self.assertRaises(MovementIntentRefusal) as refused:
            self.evaluate(self.player, "walk", conditions)
        self.assertEqual(refused.exception.code, "unsupported_strength")

    def test_intent_moves_before_co_resolving_run_observer_at_native_boundary(self):
        action = self.activate_run_observer()
        layout = self.candidate.arena_map.layout
        start = layout.center_position(HexAddress(0, 0))
        self.player.set_position(start)
        self.player.set_hex_facing(1)  # Explicit test-world facing at the included +30° boundary.
        self.opponent.set_position(CartesianPosition(100.0, 100.0, 0.0))
        public_before = self.session.public_view()
        self.assertEqual(public_before["player"]["cell"], {"column": 0, "row": 0})
        # Test-only authored clear corridor points toward the adjacent hex
        # center. No production geometry or clearance is inferred.
        direction = (3**0.5 / 2, 0.5)
        destination = CartesianPosition(start.x + direction[0] * 20.0,
                                        start.y + direction[1] * 20.0, start.z)
        intent = MovementIntent(self.player.id, destination, "walk", "arena-move-1", 1)
        # RunAction records the movement's displacement; it is not classified
        # as another demanding Action and must not impose the 1 yd/s cap.
        conditions = self.conditions(demanding=False)
        facing_fields = (self.player.front_facing, self.player.top_facing)

        step = self.encounter.step(1, movement_intent=intent,
                                   movement_conditions=conditions)
        end = self.player.get_position()
        self.assertEqual(step.movement_decision_ids, ("arena-move-1",))
        self.assertIn(self.player.id, step.moved_entity_ids)
        self.assertEqual((step.start_time, step.end_time), (0, 1))
        self.assertAlmostEqual(end.x - start.x, direction[0] * 1.75 * 0.9144)
        self.assertAlmostEqual(end.y - start.y, direction[1] * 1.75 * 0.9144)
        self.assertEqual(end.z, start.z)
        self.assertEqual(layout.cell_at_position(end), HexAddress(2, 1))
        self.assertEqual((self.player.front_facing, self.player.top_facing), facing_fields)
        self.assertEqual(self.encounter.time, 1)
        result = self.encounter.inspect_committed(1).action(action.id)
        self.assertEqual(result.facts.outcome, "success")
        self.session._player_action_outcome = result.facts.outcome
        public_after = self.session.public_view()
        public_keys = {"state", "load_available", "encounter_name", "time_seconds", "map",
                       "player", "character", "player_action", "pickup_action", "entities", "selected_entity",
                       "action_catalog",
                       "run_available", "advance_available",
                       "movement_available", "movement_reason", "movement_plan", "movement_outcome",
                       "ready_weapon_action", "spot_available", "spot_reason"}
        for projection in (public_before, public_after):
            encoded = repr(projection)
            self.assertEqual(set(projection), public_keys)
            self.assertNotIn(self.opponent.id, encoded)
            self.assertNotIn("opponent", projection)
        self.assertEqual(public_after["time_seconds"], 1)
        self.assertAlmostEqual(public_after["player"]["position_meters"]["x"], end.x)
        self.assertAlmostEqual(public_after["player"]["position_meters"]["y"], end.y)
        self.assertEqual(public_after["player"]["cell"], {"column": 2, "row": 1})
        self.assertEqual(self.encounter.aware_beings(self.player.id), [self.opponent.id])
        self.assertEqual(self.encounter.aware_beings(self.opponent.id), [self.player.id])
        self.assertEqual(self.rng.state, random.Random(self.candidate.root_seed).getstate())
        self.assertEqual(random.getstate(), self.global_rng)

    def test_explicit_turn_commits_with_movement_and_is_in_same_second_snapshot(self):
        action = self.activate_run_observer()
        start = self.player.get_position()
        self.player.set_hex_facing(0)
        self.opponent.set_position(CartesianPosition(100.0, 100.0, 0.0))
        destination = CartesianPosition(start.x, start.y + 20.0, start.z)
        intent = MovementIntent(self.player.id, destination, "walk", "turn-north", 1,
                                facing_policy="turn", target_facing=3)
        seen = []
        import interval_staging
        original = interval_staging.capture_observer_context
        def capture(*args, **kwargs):
            context = original(*args, **kwargs)
            seen.append(context.snapshot.entity(self.player.id).data["hex_facing"])
            return context
        with patch.object(interval_staging, "capture_observer_context", capture):
            self.encounter.step(1, movement_intent=intent,
                                movement_conditions=self.conditions(demanding=False))
        self.assertEqual(self.player.hex_facing, 3)
        self.assertEqual(seen, [3])
        self.assertGreater(self.player.get_position().y, start.y)
        self.assertEqual(self.encounter.inspect_committed(1).action(action.id).facts.outcome, "success")

    def test_movement_and_turn_rollback_together_after_injected_publication_failure(self):
        action = self.activate_run_observer()
        start = self.player.get_position()
        self.player.set_hex_facing(0)
        pending_before = tuple(self.encounter.pending_action_list)
        rng_before = self.rng.state
        awareness_before = (tuple(self.encounter.aware_beings(self.player.id)),
                            tuple(self.encounter.aware_beings(self.opponent.id)))
        destination = CartesianPosition(start.x, start.y + 0.5, start.z)
        intent = MovementIntent(self.player.id, destination, "walk", "rollback-turn", 1,
                                facing_policy="turn", target_facing=3)
        import atomic_publication
        import transactional_progression
        original = atomic_publication.publish_interval_candidate
        def fail_after_movement(encounter, candidate, **kwargs):
            kwargs["_fail_after"] = "movement"
            return original(encounter, candidate, **kwargs)
        with patch.object(atomic_publication, "publish_interval_candidate", fail_after_movement):
            from atomic_publication import PublicationFailure
            with self.assertRaises(PublicationFailure) as failure:
                self.encounter.step(1, movement_intent=intent,
                                    movement_conditions=self.conditions(demanding=False))
        self.assertFalse(failure.exception.rollback_errors)
        self.assertEqual(self.player.get_position(), start)
        self.assertEqual(self.player.hex_facing, 0)
        self.assertEqual(self.encounter.time, 0)
        self.assertEqual(tuple(self.encounter.pending_action_list), pending_before)
        self.assertIsNone(action.resolution)
        self.assertEqual(self.rng.state, rng_before)
        self.assertEqual((tuple(self.encounter.aware_beings(self.player.id)),
                          tuple(self.encounter.aware_beings(self.opponent.id))), awareness_before)
        self.encounter.recover_transactional_progression(failure.exception.recovery_token)

    def test_invalid_unknown_stale_intents_change_no_state_and_arrival_is_exact(self):
        self.activate_run_observer()
        self.player.set_hex_facing(1)
        conditions = self.conditions(demanding=False)
        start = self.player.get_position()
        before_history = dict(self.candidate.universe.event_history)
        before_pending = list(self.encounter.pending_action_list)
        before_choices = self.encounter.choice_state
        before_public_view = self.session.public_view()
        before_time = self.encounter.time
        before_rng = self.rng.state
        before_global_rng = random.getstate()

        zero_distance = MovementIntent(self.player.id, start, "walk", "zero-distance", 1,
                                       facing_policy="turn")
        with self.assertRaises(MovementIntentRefusal) as refused:
            self.encounter.step(1, movement_intent=zero_distance,
                                movement_conditions=conditions)
        self.assertEqual(refused.exception.code, "zero_distance")

        far = CartesianPosition(start.x + 20.0, start.y, start.z)
        valid_shape = MovementIntent(self.player.id, far, "walk", "bad-context", 1)
        with self.assertRaises(MovementIntentRefusal):
            self.encounter.step(1, movement_intent=valid_shape,
                                movement_conditions=MovementRateConditions())

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
        self.assertEqual(self.encounter.aware_beings(self.player.id), [self.opponent.id])

        exact = CartesianPosition(start.x + 0.5, start.y, start.z)
        arrival = MovementIntent(self.player.id, exact, "walk", "arrival", 1,
                                 facing_policy="turn")
        self.encounter.step(1, movement_intent=arrival, movement_conditions=conditions)
        self.assertEqual(self.player.get_position(), exact)
        self.assertEqual(self.encounter.time, 1)
        result = self.encounter.inspect_committed(1).action(self.session._player_action_id)
        self.assertEqual(result.facts.outcome, "success")

    def test_generated_facing_stream_is_reproducible_and_does_not_consume_other_rng(self):
        another = GeneratedArenaSession(root_seed_factory=lambda: 20261107)
        global_before_generation = random.getstate()
        second_view = another.generate({"starting_experience": "0", "width_cells": "5",
                                        "height_cells": "5"})
        self.assertEqual(random.getstate(), global_before_generation)
        left, right = self.candidate.participants, another.active_candidate.participants
        self.assertEqual(self.candidate.placement_seed, another.active_candidate.placement_seed)
        self.assertEqual([row.native.being.hex_facing for row in left],
                         [row.native.being.hex_facing for row in right])
        self.assertEqual(second_view["player"]["hex_facing"], left[0].native.being.hex_facing)
        self.assertEqual([row.facing_seed for row in left], [row.facing_seed for row in right])
        self.assertEqual([row.selected_seed for row in left], [row.selected_seed for row in right])
        self.assertEqual([row.native.source_sha256 for row in left],
                         [row.native.source_sha256 for row in right])
        self.assertEqual([(row.placement.column, row.placement.row, row.placement.position)
                          for row in left],
                         [(row.placement.column, row.placement.row, row.placement.position)
                          for row in right])
        self.assertEqual(len({row.facing_seed for row in left}), 2)
        self.assertTrue(all(0 <= row.native.being.hex_facing < 12 for row in left))
        self.assertTrue(all(row.facing_provenance == "arena.initial-facing.v1/private-seed"
                            for row in left))
        self.assertNotEqual(self.candidate.placement_seed, left[0].facing_seed)
        self.assertEqual(self.session._rng_cursor.state,
                         random.Random(self.candidate.root_seed).getstate())
        self.assertEqual(random.getstate(), self.global_rng)


if __name__ == "__main__":
    unittest.main()
