"""Focused tests for bounded, atomic two-Being Arena initialization."""

import hashlib
import json
from pathlib import Path
import random
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from arena_initialization import (
    HIGH_XP_AGE_DIAGNOSTIC,
    MAX_ATTEMPTS_PER_ROLE,
    ArenaInitializationRefusal,
    initialize_two_being_arena,
)
from arena_hex_map import HexAddress
from library import Library
from npcgen_arena_adapter import ArenaNPCRefusal, prepare_npcgen_arena_being
from spatial.state import CartesianPosition
from universe import Universe


def _library():
    return Library(config_dir=str(ROOT / "src/config"))


class TestArenaInitialization(unittest.TestCase):
    def test_exact_zero_and_positive_xp_time_zero_native_pair_and_one_yard_hexes(self):
        for xp in (0, 12000):
            with self.subTest(xp=xp):
                candidate = initialize_two_being_arena(xp, 5, 5, 42, library=_library())
                self.assertEqual(len(candidate.participants), 2)
                self.assertEqual(candidate.encounter.time, 0)
                self.assertEqual(candidate.encounter.last_processed_boundary, 0)
                self.assertEqual(candidate.encounter.pending_action_list, [])
                player_id, opponent_id = candidate.encounter.being_list
                self.assertEqual(candidate.encounter.awareness,
                                 {player_id: {opponent_id}, opponent_id: {player_id}})
                for observer_id, target_id in ((player_id, opponent_id),
                                               (opponent_id, player_id)):
                    observer = candidate.encounter.get_being(observer_id)
                    ledger = observer._arena_perception_ledger
                    self.assertEqual(ledger.observer_id, observer_id)
                    self.assertEqual({row.entity_id for row in ledger.current}, {target_id})
                self.assertEqual(candidate.encounter.being_list,
                                 [p.native.being.id for p in candidate.participants])
                self.assertEqual(candidate.arena_map.width_cells, 5)
                self.assertEqual(candidate.arena_map.height_cells, 5)
                self.assertEqual(len(candidate.arena_map.layout.cell_ids), 25)
                self.assertEqual([p.role for p in candidate.participants],
                                 ["player_controlled", "arena_controlled"])
                self.assertEqual(len({(p.placement.column, p.placement.row)
                                      for p in candidate.participants}), 2)
                self.assertEqual(len({p.native.being.id for p in candidate.participants}), 2)
                for p in candidate.participants:
                    self.assertEqual(p.native.being.get_experience(), xp)
                    self.assertEqual(p.native.being.get_position(), p.placement.position)
                    self.assertEqual(p.placement.position, CartesianPosition(
                        *candidate.arena_map.layout.center_position(
                            HexAddress(p.placement.column, p.placement.row)).as_tuple()))
                    self.assertAlmostEqual(candidate.arena_map.cell_size_meters, 0.9144)
                    self.assertEqual(p.native.skills_status["cost_modifiers"], "character")
                    source = json.loads(p.native.source_record_bytes)
                    self.assertEqual(source["generation"]["starting_experience"], xp)
                    self.assertEqual(source["generation"]["skill_resolution"]["status"], "resolved")
                    self.assertEqual(p.native.source_sha256,
                                     hashlib.sha256(p.native.source_record_bytes).hexdigest())
                    self.assertEqual(p.native.being.skill_experience, {})
                    self.assertEqual(p.native.being.skill_use_history, [])
                    self.assertEqual(p.native.being._skill_practice_baselines, {})
                    self.assertIs(candidate.universe.get_object_by_id(p.native.being.id), p.native.being)
                self.assertEqual(len({p.native.source_sha256 for p in candidate.participants}), 2)

    def test_same_inputs_reproduce_source_choices_attempts_and_placements(self):
        first = initialize_two_being_arena(12000, 7, 6, 909, library=_library())
        second = initialize_two_being_arena(12000, 7, 6, 909, library=_library())
        self.assertEqual(first.placement_seed, second.placement_seed)
        self.assertEqual(first.attempts, second.attempts)
        self.assertEqual([p.native.source_record_bytes for p in first.participants],
                         [p.native.source_record_bytes for p in second.participants])
        self.assertEqual([(p.placement.column, p.placement.row) for p in first.participants],
                         [(p.placement.column, p.placement.row) for p in second.participants])
        self.assertNotEqual([p.native.being.id for p in first.participants],
                            [p.native.being.id for p in second.participants])

    def test_private_random_stream_does_not_mutate_module_global_state(self):
        before = random.getstate()
        initialize_two_being_arena(0, 5, 5, 1, library=_library())
        self.assertEqual(random.getstate(), before)

    def test_invalid_dimensions_and_generator_xp_bound_fail_closed(self):
        for args in ((True, 5, 5, 1), (0, 4, 5, 1), (0, 5, 5, True),
                     (0, 1001, 1000, 1)):
            with self.subTest(args=args), self.assertRaises(ArenaInitializationRefusal):
                initialize_two_being_arena(*args, library=_library())
        with self.assertRaises(ArenaInitializationRefusal) as raised:
            initialize_two_being_arena(2**53, 5, 5, 1, library=_library())
        self.assertEqual(raised.exception.code, "candidate_terminal_failure")
        self.assertEqual(raised.exception.details["refusal"]["code"], "generator_refusal")
        self.assertEqual(raised.exception.details["attempt"], 1)

    def test_second_terminal_failure_leaves_staged_universe_and_active_world_unchanged(self):
        active = Universe("existing active session", library=_library())
        active_objects = dict(active.object_registry.object_instances)
        staging = []
        real_prepare = prepare_npcgen_arena_being
        calls = 0

        def fail_second(world, **kwargs):
            nonlocal calls
            if not staging:
                staging.append(world)
            calls += 1
            if calls == 1:
                return real_prepare(world, **kwargs)
            raise ArenaNPCRefusal("engine_identity_mismatch", "injected terminal failure")

        with patch("arena_initialization.prepare_npcgen_arena_being", side_effect=fail_second):
            with self.assertRaises(ArenaInitializationRefusal) as raised:
                initialize_two_being_arena(0, 5, 5, 1, library=_library())
        self.assertEqual(raised.exception.code, "candidate_terminal_failure")
        self.assertEqual(staging[0].object_registry.object_instances, {})
        self.assertEqual(active.object_registry.object_instances, active_objects)

    def test_retry_exhaustion_is_bounded_and_age_diagnostic_requires_clear_age_cause(self):
        calls = []

        def age_failure(world, **kwargs):
            calls.append(kwargs["seed"])
            raise ArenaNPCRefusal("skill_profile_unresolved", "no age class",
                                  details={"age_unavailable": True, "reason": "Dead"})

        with patch("arena_initialization.prepare_npcgen_arena_being", side_effect=age_failure):
            with self.assertRaises(ArenaInitializationRefusal) as raised:
                initialize_two_being_arena(9999999, 5, 5, 2, library=_library())
        self.assertEqual(len(calls), MAX_ATTEMPTS_PER_ROLE)
        self.assertEqual(raised.exception.code, "high_experience_age_exhaustion")
        self.assertEqual(raised.exception.message, HIGH_XP_AGE_DIAGNOSTIC)

        calls.clear()

        def unresolved_other(world, **kwargs):
            calls.append(kwargs["seed"])
            raise ArenaNPCRefusal("skill_profile_unresolved", "unknown resolution issue",
                                  details={"age_unavailable": False})

        with patch("arena_initialization.prepare_npcgen_arena_being", side_effect=unresolved_other):
            with self.assertRaises(ArenaInitializationRefusal) as raised:
                initialize_two_being_arena(0, 5, 5, 2, library=_library())
        self.assertEqual(len(calls), MAX_ATTEMPTS_PER_ROLE)
        self.assertEqual(raised.exception.code, "candidate_retries_exhausted")

    def test_unsupported_race_can_be_retried_but_terminal_corruption_is_not(self):
        real_prepare = prepare_npcgen_arena_being
        seen = []

        def reject_once(world, **kwargs):
            seen.append(kwargs["seed"])
            if len(seen) == 1:
                raise ArenaNPCRefusal("unsupported_native_race", "no supported native type")
            return real_prepare(world, **kwargs)

        with patch("arena_initialization.prepare_npcgen_arena_being", side_effect=reject_once):
            result = initialize_two_being_arena(0, 5, 5, 10, library=_library())
        self.assertGreaterEqual(len(seen), 3)  # one rejection, then two selected roles
        self.assertEqual(result.attempts[0].code, "unsupported_native_race")

        seen.clear()

        def corrupt(world, **kwargs):
            seen.append(1)
            raise ArenaNPCRefusal("invalid_generator_record", "corrupt source")

        with patch("arena_initialization.prepare_npcgen_arena_being", side_effect=corrupt):
            with self.assertRaises(ArenaInitializationRefusal) as raised:
                initialize_two_being_arena(0, 5, 5, 10, library=_library())
        self.assertEqual(len(seen), 1)
        self.assertEqual(raised.exception.code, "candidate_terminal_failure")


if __name__ == "__main__":
    unittest.main()
