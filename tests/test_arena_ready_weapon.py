"""Bounded native Ready weapon Action and generated Arena projection tests."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from activities import ReadyWeaponAction
from arena_browser_session import ArenaBrowserRequestError, GeneratedArenaSession
from arena_hex_map import HexAddress
from atomic_publication import PublicationFailure, _WritePlan
from movement_intent import derive_native_movement_inputs
from melee_combat import MeleeStrike
from weapon import WeaponInstance

GENERATE = {"starting_experience": "10000", "width_cells": "10", "height_cells": "5"}
DAGGER = [{"source_item_id": "ready-test:dagger", "category": "weapon",
           "native_type_key": "Dagger", "quantity": 1, "ordinary": True,
           "magical": False, "mechanics": None, "origin": "ready-test.v1"}]


def arena(seed=20261107):
    session = GeneratedArenaSession(root_seed_factory=lambda: seed,
                                    ground_item_descriptions=DAGGER)
    state = session.generate(GENERATE)
    candidate = session.active_candidate
    player = candidate.participants[0].native.being
    placement = candidate.ground_objects[0]
    weapon = candidate.universe.get_object_by_id(placement.native_object_id)
    if type(weapon) is not WeaponInstance or player.current.hit_points <= 0:
        raise AssertionError("deterministic fixture must contain a Dagger and positive-HP player")
    # Test-world premise: explicitly author one native vacant hand slot. The
    # current Arena templates do not supply hand state and production does not
    # synthesize it.
    player.current.body_parts["right hand"] = None
    state = session.public_view()
    return session, state, candidate, player, placement, weapon


def acquire_dagger(session, candidate, player, placement, weapon):
    address = HexAddress(placement.column, placement.row)
    destination = candidate.arena_map.layout.center_position(address, z=player.get_position().z)
    if player.get_position() != destination:
        session.choose_destination({"column": address.column, "row": address.row,
                                   "rate": "sprint", "facing_policy": "turn"})
        for _ in range(100):
            if session.public_view()["movement_plan"] is None:
                break
            session.advance_one_second()
    visible = next(row for row in session.public_view()["entities"] if row["type"] == "Dagger")
    session.inspect_entity({"handle": visible["handle"]})
    session.choose_pickup({"handle": visible["handle"]})
    pickup_view = session.advance_one_second()
    return visible["handle"], pickup_view


class TestArenaReadyWeapon(unittest.TestCase):
    def test_browser_session_pickup_ready_and_live_character_equipment_projection(self):
        session, initial, candidate, player, placement, weapon = arena()
        initial_ready = next(row for row in initial["action_catalog"]["entries"]
                             if row["name"] == "ready weapon")
        self.assertEqual(initial_ready["status"], "unavailable")
        self.assertIn("carried Weapon", initial_ready["reason"])
        before_rng = session._rng_cursor.state
        handle, picked = acquire_dagger(session, candidate, player, placement, weapon)
        self.assertEqual(picked["pickup_action"]["outcome"], "success")
        self.assertEqual(picked["character"]["inventory"]["items"][0]["status"],
                         "carried; not readied")
        weight = picked["character"]["inventory"]["carried_weight_pounds"]
        ready_entry = next(row for row in picked["action_catalog"]["entries"]
                           if row["name"] == "ready weapon")
        self.assertEqual(ready_entry["status"], "available")
        self.assertEqual(ready_entry["hands"], ["right hand"])
        self.assertEqual(ready_entry["target"]["handle"], handle)
        accepted = session.choose_ready_weapon({"handle": handle, "hand": "right hand"})
        self.assertEqual(accepted["ready_weapon_action"]["status"], "executing")
        self.assertEqual(next(row for row in accepted["action_catalog"]["entries"]
                              if row["name"] == "ready weapon")["status"], "unavailable")
        resolved = session.advance_one_second()
        self.assertEqual(resolved["ready_weapon_action"]["outcome"], "success")
        self.assertEqual(player.current.body_parts, {"right hand": weapon.id})
        self.assertEqual(player.weapons, [weapon.id])
        self.assertIn(weapon.id, player.armed_with(candidate.universe).values())
        self.assertEqual(player.possessions, [weapon.id])
        self.assertEqual(weapon.parent_container_id, player.id)
        self.assertIsNone(weapon.spatial_state)
        inventory = resolved["character"]["inventory"]
        self.assertEqual(len(inventory["items"]), 1)
        self.assertEqual(inventory["items"][0]["status"], "readied in right hand")
        self.assertEqual(inventory["items"][0]["weight_pounds"], weapon.current.weight)
        self.assertEqual(inventory["carried_weight_pounds"], weight)
        self.assertEqual(derive_native_movement_inputs(player, candidate.universe).encumbrance_lb, weight)
        record = candidate.encounter.inspect_committed(int(candidate.encounter.time))
        self.assertEqual(record.action(session._ready_weapon_action_id).facts.outcome, "success")
        opponent_id = candidate.participants[1].native.being.id
        self.assertNotIn("possessions", resolved["selected_entity"] or {})
        self.assertNotIn(opponent_id, str(resolved["character"]))
        self.assertEqual(session._rng_cursor.state, before_rng)

    def test_invalid_hand_wrong_object_and_unsupported_hand_state_fail_closed(self):
        session, _, candidate, player, placement, weapon = arena(seed=20261109)
        handle, _ = acquire_dagger(session, candidate, player, placement, weapon)
        before = session.public_view()
        with self.assertRaisesRegex(ValueError, "currently free native hands"):
            session.choose_ready_weapon({"handle": handle, "hand": "left hand"})
        self.assertEqual(session.public_view(), before)
        player.current.body_parts.pop("right hand")
        without_hand = session.public_view()
        self.assertEqual(next(row for row in without_hand["action_catalog"]["entries"]
                              if row["name"] == "ready weapon")["status"], "unavailable")
        self.assertIn("No explicitly modeled", next(row for row in without_hand["action_catalog"]["entries"]
                                                     if row["name"] == "ready weapon")["reason"])
        player.current.body_parts["right hand"] = None
        player.current.hit_points = 0
        downed = session.public_view()
        ready = next(row for row in downed["action_catalog"]["entries"]
                     if row["name"] == "ready weapon")
        self.assertEqual(ready["status"], "unavailable")
        self.assertIn("cannot perform a voluntary Action", ready["reason"])
        with self.assertRaisesRegex(ValueError, "cannot perform a voluntary Action"):
            session.choose_ready_weapon({"handle": handle, "hand": "right hand"})

    def test_simultaneous_same_hand_and_weapon_claims_are_both_contested(self):
        session, _, candidate, player, placement, weapon = arena(seed=20261110)
        acquire_dagger(session, candidate, player, placement, weapon)
        first = ReadyWeaponAction(candidate.encounter, player.id, weapon.id,
                                  "right hand", candidate.encounter.time)
        second = ReadyWeaponAction(candidate.encounter, player.id, weapon.id,
                                   "right hand", candidate.encounter.time)
        candidate.encounter.schedule_action(first)
        candidate.encounter.schedule_action(second)
        boundary = int(candidate.encounter.time) + 1
        candidate.encounter.step(1)
        record = candidate.encounter.inspect_committed(boundary)
        self.assertEqual(record.action(first.id).facts.outcome, "contested")
        self.assertEqual(record.action(second.id).facts.outcome, "contested")
        self.assertNotIn(weapon.id, player.weapons)
        self.assertIsNone(player.current.body_parts["right hand"])
        self.assertEqual(player.possessions.count(weapon.id), 1)

    def test_same_boundary_strike_cannot_use_the_uncommitted_ready_weapon(self):
        session, _, candidate, player, placement, weapon = arena(seed=20261113)
        handle, _ = acquire_dagger(session, candidate, player, placement, weapon)
        session.choose_ready_weapon({"handle": handle, "hand": "right hand"})
        opponent = candidate.participants[1].native.being
        strike = MeleeStrike(candidate.encounter, player.id, opponent.id, weapon.id,
                             motion="thrust", reach=100)
        with self.assertRaisesRegex(ValueError, "actor does not hold that weapon"):
            candidate.encounter.schedule_action(strike)
        self.assertIsNone(player.current.body_parts["right hand"])
        self.assertEqual(player.weapons, [])
        self.assertEqual(player.possessions, [weapon.id])

    def test_interrupted_ready_action_makes_no_equipment_transition(self):
        session, _, candidate, player, placement, weapon = arena(seed=20261111)
        handle, _ = acquire_dagger(session, candidate, player, placement, weapon)
        session.choose_ready_weapon({"handle": handle, "hand": "right hand"})
        action_id = session._ready_weapon_action_id
        choice_id = next(key for key, record in candidate.encounter._choice_book._choices.items()
                         if action_id in record.view.action_ids)
        candidate.encounter._choice_book.undo(choice_id)
        self.assertNotIn(action_id, candidate.universe.event_history)
        self.assertEqual(player.current.body_parts, {"right hand": None})
        self.assertEqual(player.weapons, [])
        self.assertEqual(player.possessions, [weapon.id])

    def test_publication_failure_restores_ready_state_then_retry_commits(self):
        session, _, candidate, player, placement, weapon = arena(seed=20261112)
        handle, _ = acquire_dagger(session, candidate, player, placement, weapon)
        session.choose_ready_weapon({"handle": handle, "hand": "right hand"})
        before_time = candidate.encounter.time
        before_rng = session._rng_cursor.state
        before_inventory = session.public_view()["character"]["inventory"]
        original_apply = _WritePlan.apply_phase

        def fail_after_target_write(plan, phase):
            original_apply(plan, phase)
            if phase == "targets":
                raise RuntimeError("injected ready publication fault")

        with patch.object(_WritePlan, "apply_phase", fail_after_target_write):
            with self.assertRaises(ArenaBrowserRequestError) as caught:
                session.advance_one_second()
        failure = caught.exception.__cause__
        self.assertIsInstance(failure, PublicationFailure)
        self.assertFalse(failure.rollback_errors)
        self.assertEqual(candidate.encounter.time, before_time)
        self.assertEqual(session._rng_cursor.state, before_rng)
        self.assertEqual(player.current.body_parts, {"right hand": None})
        self.assertEqual(player.weapons, [])
        self.assertEqual(player.possessions, [weapon.id])
        self.assertEqual(session.public_view()["character"]["inventory"], before_inventory)
        candidate.encounter.recover_transactional_progression(failure.recovery_token)
        resolved = session.advance_one_second()
        self.assertEqual(resolved["ready_weapon_action"]["outcome"], "success")
        self.assertEqual(player.current.body_parts["right hand"], weapon.id)
        self.assertEqual(player.weapons, [weapon.id])


if __name__ == "__main__":
    unittest.main()
