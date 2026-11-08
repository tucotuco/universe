"""The adopted Action pipeline must fail closed without a ground-item rule adapter."""

import json
import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "examples"))
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from action import Action
from arena_browser_session import GeneratedArenaSession
from action_evaluation import UnsupportedEvaluation


def one_dagger_fixture():
    return [{"source_item_id": "arena-test-acquisition:v1:dagger-1",
             "category": "weapon", "native_type_key": "Dagger", "quantity": 1,
             "ordinary": True, "magical": False, "mechanics": None,
             "origin": "universe-authored-acquisition-test.v1"}]


class TestArenaAcquisitionBoundary(unittest.TestCase):
    def test_native_scheduler_refuses_unimplemented_grab_and_ready_without_side_effects(self):
        session = GeneratedArenaSession(root_seed_factory=lambda: 20261107,
                                        ground_item_descriptions=one_dagger_fixture())
        initial = session.generate({"starting_experience": "10000",
                                   "width_cells": "10", "height_cells": "5"})
        candidate = session.active_candidate
        player = candidate.participants[0].native.being
        ground = candidate.ground_objects[0]
        ground_object = candidate.universe.get_object_by_id(ground.native_object_id)
        self.assertEqual(ground.native_type_key, "Dagger")
        self.assertIsNotNone(ground_object)
        self.assertIsNone(ground_object.parent_container_id)
        self.assertEqual(player.possessions, [])
        self.assertEqual(player.weapons, [])
        self.assertIsNone(player.current.armor_id)

        # The test harness knows the hidden fixture ID. The ordinary player view
        # does not; no browser route or perception result is created here.
        visible = json.dumps(initial, sort_keys=True)
        self.assertNotIn(ground.native_object_id, visible)
        self.assertNotIn(ground.source_item_id, visible)
        self.assertNotIn("Dagger", visible)

        start = player.get_position()
        destination_address = max(candidate.arena_map.layout.addresses(), key=lambda address: math.dist(
            start.as_tuple(), candidate.arena_map.layout.center_position(address, z=start.z).as_tuple()))
        session.choose_destination({"column": destination_address.column,
                                    "row": destination_address.row,
                                    "rate": "walk", "facing_policy": "turn"})
        accepted = session.choose_destination({"column": destination_address.column,
                                               "row": destination_address.row,
                                               "rate": "sprint", "facing_policy": "turn"})
        self.assertEqual(accepted["movement_plan"]["rate"], "sprint")
        self.assertEqual(candidate.encounter.progression_mode, "transactional")

        event_history_before = dict(candidate.universe.event_history)
        pending_before = tuple(candidate.encounter.pending_action_list)
        choice_before = candidate.encounter.choice_state
        cursor_before = session._rng_cursor.state
        time_before = candidate.encounter.time
        position_before = player.get_position()
        object_position_before = ground_object.get_position()
        object_weight_before = ground_object.current.weight
        projection_before = session.public_view()

        # These are native action-catalog labels, but no reviewed native Action
        # family/resolver exists for either operation. Going through Encounter
        # scheduling therefore refuses before Choice publication.
        for label in ("grab object", "ready weapon", "ready object"):
            attempt = Action(candidate.universe, time_before, None, label,
                             player.id, ground.native_object_id, None)
            with self.assertRaisesRegex(UnsupportedEvaluation,
                                        "unsupported transactional base Action activity"):
                candidate.encounter.schedule_action(attempt)
            self.assertEqual(candidate.universe.event_history, event_history_before)
            self.assertEqual(tuple(candidate.encounter.pending_action_list), pending_before)
            self.assertEqual(candidate.encounter.choice_state, choice_before)
            self.assertEqual(session._rng_cursor.state, cursor_before)
            self.assertEqual(candidate.encounter.time, time_before)
            self.assertEqual(player.get_position(), position_before)
            self.assertEqual(ground_object.get_position(), object_position_before)
            self.assertEqual(ground_object.current.weight, object_weight_before)
            self.assertEqual(player.possessions, [])
            self.assertEqual(player.weapons, [])
            self.assertIsNone(player.current.armor_id)
            self.assertEqual(session.public_view(), projection_before)

        # Rejection has not consumed movement, exposed the test-known item, or
        # changed the committed ground Object identity/state.
        steps = 0
        while session.public_view()["movement_plan"] is not None:
            view = session.advance_one_second()
            steps += 1
            self.assertNotIn(ground.native_object_id, json.dumps(view))
            self.assertNotIn(ground.source_item_id, json.dumps(view))
            self.assertLessEqual(steps, 100)
        self.assertEqual(player.get_position(),
                         candidate.arena_map.layout.center_position(destination_address,
                                                                    z=start.z))
        self.assertEqual(ground_object.get_position(), object_position_before)
        self.assertEqual(ground_object.id, ground.native_object_id)
        self.assertEqual(player.possessions, [])
        self.assertEqual(player.weapons, [])
        self.assertIsNone(player.current.armor_id)
        self.assertNotIn(ground.native_object_id, json.dumps(session.public_view()))


if __name__ == "__main__":
    unittest.main()
