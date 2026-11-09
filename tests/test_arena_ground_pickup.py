"""Revision-64 native ground Pick up integration and custody tests."""
import json
import math
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from dataclasses import replace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "examples"))
sys.path.insert(0, str(ROOT / "src"))

from activities import PickUpAction
from arena_browser_session import GeneratedArenaSession
from arena_hex_map import HexAddress
from being import BeingInstance
from weapon import WeaponInstance
from atomic_publication import PublicationFailure, _WritePlan
from action_settlement import SettlementIntegrityError


GENERATE = {"starting_experience": "10000", "width_cells": "10", "height_cells": "5"}
ONE_DAGGER = [{"source_item_id": "arena-test-pickup:v1:dagger-1",
               "category": "weapon", "native_type_key": "Dagger", "quantity": 1,
               "ordinary": True, "magical": False, "mechanics": None,
               "origin": "universe-authored-pickup-test.v1"}]


def fixture(seed=20261107):
    session = GeneratedArenaSession(root_seed_factory=lambda: seed,
                                    ground_item_descriptions=ONE_DAGGER)
    initial = session.generate(GENERATE)
    candidate = session.active_candidate
    player = candidate.participants[0].native.being
    placement = candidate.ground_objects[0]
    item = candidate.universe.get_object_by_id(placement.native_object_id)
    return session, initial, candidate, player, placement, item


def move_player_to(session, candidate, player, address):
    layout = candidate.arena_map.layout
    destination = layout.center_position(address, z=player.get_position().z)
    if player.get_position() == destination:
        return
    session.choose_destination({"column": address.column, "row": address.row,
                                "rate": "sprint", "facing_policy": "turn"})
    for _ in range(100):
        if session.public_view()["movement_plan"] is None:
            break
        session.advance_one_second()
    if player.get_position() != destination:
        raise AssertionError("native destination plan did not arrive")


class TestArenaGroundPickup(unittest.TestCase):
    def test_visible_remote_dagger_native_browser_pickup_and_carried_projection(self):
        session, initial, candidate, player, placement, item = fixture(seed=20261107)
        visible = next(row for row in initial["entities"] if row["type"] == "Dagger")
        self.assertEqual(visible["present_state"], "ground")
        self.assertEqual(visible["cell"], {"column": placement.column, "row": placement.row})
        self.assertNotIn(item.id, json.dumps(initial))
        self.assertFalse(visible["pickup_available"])
        with self.assertRaisesRegex(ValueError, "currently perceived"):
            session.choose_pickup({"handle": "forged-view-handle"})
        original_position = item.get_position()
        item.set_position(player.get_position())
        with self.assertRaisesRegex(ValueError, "evidence is stale"):
            session.choose_pickup({"handle": visible["handle"]})
        item.set_position(original_position)
        with self.assertRaisesRegex(ValueError, "same hex"):
            session.choose_pickup({"handle": visible["handle"]})

        inspected = session.inspect_entity({"handle": visible["handle"]})
        self.assertEqual(inspected["selected_entity"]["name"], "Dagger")
        move_player_to(session, candidate, player, HexAddress(placement.column, placement.row))
        at_item = session.public_view()
        visible = next(row for row in at_item["entities"] if row["handle"] == visible["handle"])
        self.assertTrue(visible["pickup_available"])
        accepted = session.choose_pickup({"handle": visible["handle"]})
        self.assertEqual(accepted["pickup_action"]["status"], "executing")
        resolved = session.advance_one_second()
        self.assertEqual(resolved["pickup_action"]["outcome"], "success")
        carried = next(row for row in resolved["entities"] if row["handle"] == visible["handle"])
        self.assertEqual(carried["present_state"], "carried")
        self.assertIsNone(carried["position_meters"])
        self.assertIsNone(item.spatial_state)
        self.assertEqual(item.parent_container_id, player.id)
        ledger = player._arena_perception_ledger
        history = [row for row in ledger.history if row.entity_id == item.id]
        self.assertEqual([row.present_state for row in history], ["ground", "carried"])
        session.generate(GENERATE)
        with self.assertRaisesRegex(ValueError, "currently perceived"):
            session.choose_pickup({"handle": visible["handle"]})

    def test_generated_dagger_pickup_then_native_movement_carries_same_object(self):
        session, initial, candidate, player, placement, item = fixture()
        self.assertIsInstance(item, WeaponInstance)
        self.assertIsNone(item.parent_container_id)
        public = json.dumps(initial, sort_keys=True)
        self.assertNotIn(placement.native_object_id, public)
        self.assertNotIn(placement.source_item_id, public)
        self.assertIn("Dagger", public)

        ground_cell = HexAddress(placement.column, placement.row)
        move_player_to(session, candidate, player, ground_cell)
        pickup_boundary = int(candidate.encounter.time) + 1
        pickup_rng_before = session._rng_cursor.state
        pickup = PickUpAction(candidate.encounter, player.id, item.id,
                              candidate.encounter.time,
                              map_width_cells=10, map_height_cells=5)
        candidate.encounter.schedule_action(pickup)
        candidate.encounter.step(1)

        self.assertIn(item.id, player.possessions)
        self.assertEqual(player.possessions.count(item.id), 1)
        self.assertEqual(item.parent_container_id, player.id)
        self.assertIsNone(item.spatial_state)
        self.assertEqual(session._rng_cursor.state, pickup_rng_before)
        from movement_intent import derive_native_movement_inputs
        self.assertEqual(derive_native_movement_inputs(player, candidate.universe).encumbrance_lb,
                         float(item.current.weight))
        self.assertEqual(player.weapons, [])
        self.assertIsNone(player.current.armor_id)
        self.assertTrue(all(value is None for value in player.current.body_parts.values()))
        self.assertEqual(candidate.encounter.inspect_committed(pickup_boundary).action(pickup.id).facts.outcome,
                         "success")
        self.assertNotIn(item.id, json.dumps(session.public_view(), sort_keys=True))
        self.assertNotIn(placement.source_item_id, json.dumps(session.public_view(), sort_keys=True))
        self.assertIn('"present_state": "carried"', json.dumps(session.public_view(), sort_keys=True))

        origin = player.get_position()
        destination = max(candidate.arena_map.layout.addresses(),
                          key=lambda cell: math.dist(origin.as_tuple(),
                              candidate.arena_map.layout.center_position(cell, z=origin.z).as_tuple()))
        destination_position = candidate.arena_map.layout.center_position(destination, z=origin.z)
        session.choose_destination({"column": destination.column, "row": destination.row,
                                    "rate": "sprint", "facing_policy": "turn"})
        for _ in range(100):
            if session.public_view()["movement_plan"] is None:
                break
            session.advance_one_second()
        self.assertEqual(player.get_position(), destination_position)
        self.assertEqual(player.possessions.count(item.id), 1)
        self.assertEqual(item.parent_container_id, player.id)
        self.assertIsNone(item.spatial_state)
        self.assertNotIn(item.id, json.dumps(session.public_view(), sort_keys=True))

    def test_malformed_success_proposal_without_custody_effect_is_refused_prewrite(self):
        session, _, candidate, player, placement, item = fixture(seed=20261113)
        address = HexAddress(placement.column, placement.row)
        player.set_position(candidate.arena_map.layout.center_position(address))
        candidate.encounter.activate_arena_for_player_movement(
            player.id, "pickup-malformed-test", rng_owner=session._rng_cursor)
        action = PickUpAction(candidate.encounter, player.id, item.id, 0,
                              map_width_cells=10, map_height_cells=5)
        candidate.encounter.schedule_action(action)
        from action_evaluation import evaluate_snapshot
        original = evaluate_snapshot
        def missing_effect(snapshot, action_ids=None):
            result = original(snapshot, action_ids)
            proposals = tuple(replace(proposal, effects=())
                              if proposal.action_id == action.id else proposal
                              for proposal in result.proposals)
            return replace(result, proposals=proposals, identified_effects=())
        with patch("observer_proposals.evaluate_snapshot", missing_effect):
            with self.assertRaises(SettlementIntegrityError):
                candidate.encounter.step(1)
        self.assertEqual(candidate.encounter.time, 0)
        self.assertEqual(player.possessions, [])
        self.assertIsNone(item.parent_container_id)
        self.assertIsNotNone(item.spatial_state)

    def test_common_snapshot_contention_leaves_object_on_ground(self):
        session, _, candidate, player, placement, item = fixture(seed=20261108)
        other_id = candidate.participants[1].native.being.id
        other = candidate.universe.get_object_by_id(other_id)
        address = HexAddress(placement.column, placement.row)
        center = candidate.arena_map.layout.center_position(address)
        # Explicit authored test-world placement supplies only the adopted
        # same-hex premise; it does not introduce geometry or perception.
        player.set_position(center)
        other.set_position(center)
        candidate.encounter.activate_arena_for_player_movement(
            player.id, "pickup-contention-test", rng_owner=session._rng_cursor)
        first = PickUpAction(candidate.encounter, player.id, item.id,
                             candidate.encounter.time, map_width_cells=10,
                             map_height_cells=5)
        second = PickUpAction(candidate.encounter, other.id, item.id,
                              candidate.encounter.time, map_width_cells=10,
                              map_height_cells=5)
        candidate.encounter.schedule_choice((first, second))
        candidate.encounter.step(1)
        self.assertEqual(candidate.encounter.inspect_committed(1).action(first.id).facts.outcome,
                         "contested")
        self.assertEqual(candidate.encounter.inspect_committed(1).action(second.id).facts.outcome,
                         "contested")
        self.assertEqual(player.possessions, [])
        self.assertEqual(other.possessions, [])
        self.assertIsNone(item.parent_container_id)
        self.assertIsNotNone(item.spatial_state)

    def test_ineligible_simultaneous_attempt_does_not_contest_eligible_pickup(self):
        session, _, candidate, player, placement, item = fixture(seed=20261109)
        other = candidate.participants[1].native.being
        address = HexAddress(placement.column, placement.row)
        center = candidate.arena_map.layout.center_position(address)
        player.set_position(center)
        # The opponent remains in its authored distinct hex.
        candidate.encounter.activate_arena_for_player_movement(
            player.id, "pickup-eligibility-test", rng_owner=session._rng_cursor)
        first = PickUpAction(candidate.encounter, player.id, item.id,
                             candidate.encounter.time, map_width_cells=10,
                             map_height_cells=5)
        second = PickUpAction(candidate.encounter, other.id, item.id,
                              candidate.encounter.time, map_width_cells=10,
                              map_height_cells=5)
        candidate.encounter.schedule_choice((first, second))
        candidate.encounter.step(1)
        records = candidate.encounter.inspect_committed(1)
        self.assertEqual(records.action(first.id).facts.outcome, "success")
        self.assertEqual(records.action(second.id).facts.outcome, "inaccessible")
        self.assertIn(item.id, player.possessions)
        self.assertNotIn(item.id, other.possessions)

    def test_cancellation_before_boundary_and_already_carried_item_are_noops(self):
        session, _, candidate, player, placement, item = fixture(seed=20261110)
        address = HexAddress(placement.column, placement.row)
        player.set_position(candidate.arena_map.layout.center_position(address))
        candidate.encounter.activate_arena_for_player_movement(
            player.id, "pickup-cancel-test", rng_owner=session._rng_cursor)
        cancelled = PickUpAction(candidate.encounter, player.id, item.id,
                                 candidate.encounter.time + 1, map_width_cells=10,
                                 map_height_cells=5)
        candidate.encounter.schedule_action(cancelled)
        candidate.encounter.step(1)  # Native start fence; resolution is one second later.
        self.assertIn(cancelled.id, candidate.encounter.pending_action_list)
        candidate.encounter.cancel_action(cancelled.id, reason="test cancellation")
        candidate.encounter.step(1)
        self.assertEqual(player.possessions, [])
        self.assertIsNone(item.parent_container_id)
        self.assertEqual(candidate.encounter.inspect_committed(2).action(cancelled.id).facts.outcome,
                         "interrupted")

        # A later successful acquisition makes the same native ID unavailable
        # to duplicate custody transfer attempts.
        acquire = PickUpAction(candidate.encounter, player.id, item.id,
                               candidate.encounter.time, map_width_cells=10,
                               map_height_cells=5)
        candidate.encounter.schedule_action(acquire)
        candidate.encounter.step(1)
        self.assertEqual(candidate.encounter.inspect_committed(3).action(acquire.id).facts.outcome,
                         "success")
        duplicate = PickUpAction(candidate.encounter, player.id, item.id,
                                 candidate.encounter.time, map_width_cells=10,
                                 map_height_cells=5)
        candidate.encounter.schedule_action(duplicate)
        candidate.encounter.step(1)
        self.assertEqual(candidate.encounter.inspect_committed(4).action(duplicate.id).facts.outcome,
                         "unavailable")
        self.assertEqual(player.possessions.count(item.id), 1)

    def test_capacity_and_post_movement_access_failures_leave_ground_custody(self):
        session, _, candidate, player, placement, item = fixture(seed=20261111)
        address = HexAddress(placement.column, placement.row)
        player.set_position(candidate.arena_map.layout.center_position(address))
        candidate.encounter.activate_arena_for_player_movement(
            player.id, "pickup-capacity-test", rng_owner=session._rng_cursor)
        item.current.weight = 10000
        too_heavy = PickUpAction(candidate.encounter, player.id, item.id, 0,
                                  map_width_cells=10, map_height_cells=5)
        candidate.encounter.schedule_action(too_heavy)
        candidate.encounter.step(1)
        self.assertEqual(candidate.encounter.inspect_committed(1).action(too_heavy.id).facts.outcome,
                         "over_capacity")
        self.assertEqual(player.possessions, [])
        self.assertIsNone(item.parent_container_id)
        self.assertIsNotNone(item.spatial_state)

        # Restore the authored weight and attempt pickup while a native
        # movement intent leaves the target's hex before Action resolution.
        item.current.weight = 1.0
        next_cell = next(cell for cell in candidate.arena_map.layout.neighbors(address)
                         if candidate.arena_map.layout.contains(cell))
        action = PickUpAction(candidate.encounter, player.id, item.id, 1,
                              map_width_cells=10, map_height_cells=5)
        candidate.encounter.schedule_action(action)
        destination = candidate.arena_map.layout.center_position(next_cell)
        origin = player.get_position()
        velocity = (destination.x-origin.x, destination.y-origin.y,
                    destination.z-origin.z)
        candidate.encounter.step(1, velocities={player.id: velocity})
        self.assertEqual(candidate.encounter.inspect_committed(2).action(action.id).facts.outcome,
                         "inaccessible")
        self.assertEqual(player.possessions, [])
        self.assertIsNone(item.parent_container_id)
        self.assertIsNotNone(item.spatial_state)

    def test_failed_publication_rolls_back_pickup_custody_and_can_recover(self):
        session, _, candidate, player, placement, item = fixture(seed=20261112)
        address = HexAddress(placement.column, placement.row)
        player.set_position(candidate.arena_map.layout.center_position(address))
        candidate.encounter.activate_arena_for_player_movement(
            player.id, "pickup-rollback-test", rng_owner=session._rng_cursor)
        action = PickUpAction(candidate.encounter, player.id, item.id, 0,
                              map_width_cells=10, map_height_cells=5)
        candidate.encounter.schedule_action(action)
        position_before = item.get_position()
        item_state_before = item.spatial_state
        possessions_before = list(player.possessions)
        evidence_before = (dict(player._arena_perception_ledger._current),
                           list(player._arena_perception_ledger._history))
        time_before = candidate.encounter.time
        character_inventory_before = session.public_view()["character"]["inventory"]
        original_apply_phase = _WritePlan.apply_phase
        def fail_after_targets(plan, phase):
            original_apply_phase(plan, phase)
            if phase == "targets":
                raise RuntimeError("injected pickup publication fault")
        with patch.object(_WritePlan, "apply_phase", fail_after_targets):
            with self.assertRaises(PublicationFailure) as caught:
                candidate.encounter.step(1)
        self.assertFalse(caught.exception.rollback_errors)
        self.assertEqual(player.possessions, possessions_before)
        self.assertIsNone(item.parent_container_id)
        self.assertIs(item.spatial_state, item_state_before)
        self.assertEqual(item.get_position(), position_before)
        self.assertEqual(candidate.encounter.time, time_before)
        self.assertEqual(player._arena_perception_ledger._current, evidence_before[0])
        self.assertEqual(player._arena_perception_ledger._history, evidence_before[1])
        self.assertEqual(session.public_view()["character"]["inventory"], character_inventory_before)
        candidate.encounter.recover_transactional_progression(
            caught.exception.recovery_token)
        candidate.encounter.step(1)
        self.assertEqual(player.possessions.count(item.id), 1)
        self.assertEqual(item.parent_container_id, player.id)
        self.assertIsNone(item.spatial_state)
        recovered_inventory = session.public_view()["character"]["inventory"]
        self.assertEqual(len(recovered_inventory["items"]), 1)
        self.assertEqual(recovered_inventory["items"][0]["name"], "Dagger")
        self.assertEqual(recovered_inventory["carried_weight_pounds"], item.current.weight)

    def test_character_inventory_keeps_distinct_same_type_objects(self):
        descriptions = [dict(ONE_DAGGER[0], source_item_id=f"arena-test-pickup:v1:dagger-{index}")
                        for index in (1, 2)]
        session = GeneratedArenaSession(root_seed_factory=lambda: 20261107,
                                        ground_item_descriptions=descriptions)
        initial = session.generate(GENERATE)
        candidate = session.active_candidate
        player = candidate.participants[0].native.being
        daggers = [row for row in initial["entities"]
                   if row["category"] == "object" and row["type"] == "Dagger"]
        self.assertEqual(len(daggers), 2)
        for dagger in daggers:
            address = HexAddress(dagger["cell"]["column"], dagger["cell"]["row"])
            move_player_to(session, candidate, player, address)
            session.inspect_entity({"handle": dagger["handle"]})
            session.choose_pickup({"handle": dagger["handle"]})
            session.advance_one_second()
        inventory = session.public_view()["character"]["inventory"]
        self.assertEqual(len(inventory["items"]), 2)
        self.assertEqual({row["type"] for row in inventory["items"]}, {"Dagger"})
        self.assertEqual(len({row["handle"] for row in inventory["items"]}), 2)
        self.assertEqual([row["status"] for row in inventory["items"]],
                         ["carried; not readied", "carried; not readied"])
        self.assertEqual(inventory["carried_weight_pounds"],
                         2 * candidate.universe.get_object_by_id(
                             candidate.ground_objects[0].native_object_id).current.weight)


if __name__ == "__main__":
    unittest.main()
