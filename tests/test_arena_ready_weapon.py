"""Revision-61 weapon timing and fail-closed Arena readiness boundaries."""
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
from melee_combat import MeleeStrike
from weapon import WeaponInstance, re_ready_time_after_strike

GENERATE = {"starting_experience": "10000", "width_cells": "10", "height_cells": "5"}
DAGGER = [{"source_item_id": "ready-test:dagger", "category": "weapon",
           "native_type_key": "Dagger", "quantity": 1, "ordinary": True,
           "magical": False, "mechanics": None, "origin": "ready-test.v1"}]


def arena(seed=20261108):
    session = GeneratedArenaSession(root_seed_factory=lambda: seed,
                                    ground_item_descriptions=DAGGER)
    session.generate(GENERATE)
    candidate = session.active_candidate
    player = candidate.participants[0].native.being
    placement = candidate.ground_objects[0]
    weapon = candidate.universe.get_object_by_id(placement.native_object_id)
    if type(weapon) is not WeaponInstance or player.current.hit_points <= 0:
        raise AssertionError("deterministic fixture must contain a Dagger and positive-HP player")
    return session, candidate, player, placement, weapon


def acquire_dagger(session, candidate, player, placement):
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
    picked = session.advance_one_second()
    return visible["handle"], picked


class TestArenaReadyWeapon(unittest.TestCase):
    def test_revision_61_re_ready_timing_uses_eligible_native_table_motion(self):
        _, candidate, _, _, dagger = arena()
        weapons = candidate.universe.get_weapon_dictionary()
        dagger_definition = weapons.get_object_definition("Dagger")
        longsword = weapons.get_object_definition("Longsword")
        repeating_crossbow = weapons.get_object_definition("Repeating crossbow")
        self.assertEqual([re_ready_time_after_strike(dagger, motion)
                          for motion in ("range", "swing", "thrust")], [1, 1, 1])
        self.assertEqual(re_ready_time_after_strike(dagger_definition, "thrust"), 1)
        self.assertEqual(longsword.attacks["S"]["t"], 6)
        self.assertEqual(re_ready_time_after_strike(longsword, "swing"), 2)
        self.assertEqual(repeating_crossbow.attacks["R"]["t"], 2)
        self.assertEqual(re_ready_time_after_strike(repeating_crossbow, "range"), 0)
        self.assertEqual(weapons.get_object_definition("Dagger").attacks["R"]["t"], 4)

    def test_carried_dagger_readiness_fails_closed_without_drawable_location_state(self):
        session, candidate, player, placement, weapon = arena()
        self.assertEqual(player.current.body_parts, {})
        # This test premise supplies a free hand explicitly, but native custody
        # still carries no distinction between a drawable location and storage.
        player.current.body_parts["right hand"] = None
        handle, picked = acquire_dagger(session, candidate, player, placement)
        self.assertEqual(picked["character"]["inventory"]["items"][0]["status"],
                         "carried; not readied")
        ready = next(row for row in picked["action_catalog"]["entries"]
                     if row["name"] == "ready weapon")
        self.assertEqual(ready["status"], "unavailable")
        self.assertEqual(ready["hands"], [])
        self.assertIn("drawable location", ready["reason"])
        self.assertIn("timing is undetermined", ready["reason"])
        before = session.public_view()
        with self.assertRaisesRegex(ArenaBrowserRequestError, "drawable location"):
            session.choose_ready_weapon({"handle": handle, "hand": "right hand"})
        self.assertEqual(session.public_view(), before)
        self.assertEqual(player.possessions, [weapon.id])
        self.assertEqual(player.current.body_parts, {"right hand": None})
        self.assertEqual(player.weapons, [])
        self.assertEqual(weapon.parent_container_id, player.id)
        self.assertNotIn(candidate.participants[1].native.being.id,
                         str(session.public_view()["character"]))

    def test_two_second_candidate_action_stays_unready_at_first_boundary_and_refuses_at_second(self):
        session, candidate, player, placement, weapon = arena(seed=20261109)
        acquire_dagger(session, candidate, player, placement)
        player.current.body_parts["right hand"] = None
        start = int(candidate.encounter.time)
        action = ReadyWeaponAction(candidate.encounter, player.id, weapon.id,
                                   "right hand", start)
        self.assertEqual(action.end_time - action.start_time, 2)
        candidate.encounter.schedule_action(action)
        candidate.encounter.step(1)
        self.assertEqual(candidate.encounter.time, start + 1)
        self.assertNotIn(action.id, candidate.encounter.inspect_committed(start + 1).actions)
        self.assertEqual(player.current.body_parts["right hand"], None)
        self.assertEqual(player.weapons, [])
        candidate.encounter.step(1)
        second = candidate.encounter.inspect_committed(start + 2).action(action.id)
        self.assertEqual(second.facts.outcome, "unavailable")
        self.assertEqual(player.current.body_parts["right hand"], None)
        self.assertEqual(player.weapons, [])
        self.assertEqual(player.possessions, [weapon.id])

    def test_quick_draw_exception_is_not_forced_into_two_second_action(self):
        _, candidate, player, _, weapon = arena(seed=20261113)
        player.set_skill_level(candidate.universe.get_skill_dictionary(), "quick-draw", 1)
        player.set_weapon_skill_level(candidate.universe.get_weapon_dictionary(), "Dagger", 2)
        with self.assertRaisesRegex(ValueError, "Quick-draw.*essentially no-time"):
            ReadyWeaponAction(candidate.encounter, player.id, weapon.id,
                              "right hand", int(candidate.encounter.time))

    def test_simultaneous_internal_claims_remain_atomic_and_contested(self):
        session, candidate, player, placement, weapon = arena(seed=20261110)
        acquire_dagger(session, candidate, player, placement)
        player.current.body_parts["right hand"] = None
        start = int(candidate.encounter.time)
        first = ReadyWeaponAction(candidate.encounter, player.id, weapon.id,
                                  "right hand", start)
        second = ReadyWeaponAction(candidate.encounter, player.id, weapon.id,
                                   "right hand", start)
        # This explicit test-only eligibility seam exercises the preserved
        # same-snapshot contention machinery; production eligibility fails
        # closed because no drawable-location state exists.
        with patch("action_evaluation.ready_weapon_eligibility", return_value=None):
            candidate.encounter.schedule_action(first)
            candidate.encounter.schedule_action(second)
            candidate.encounter.step(2)
        record = candidate.encounter.inspect_committed(start + 2)
        self.assertEqual(record.action(first.id).facts.outcome, "contested")
        self.assertEqual(record.action(second.id).facts.outcome, "contested")
        self.assertNotIn(weapon.id, player.weapons)
        self.assertIsNone(player.current.body_parts["right hand"])
        self.assertEqual(player.possessions.count(weapon.id), 1)

    def test_atomic_publication_failure_rolls_back_two_second_draw_candidate(self):
        session, candidate, player, placement, weapon = arena(seed=20261111)
        handle, _ = acquire_dagger(session, candidate, player, placement)
        player.current.body_parts["right hand"] = None
        start = int(candidate.encounter.time)
        action = ReadyWeaponAction(candidate.encounter, player.id, weapon.id,
                                   "right hand", start)
        candidate.encounter.schedule_action(action)
        session._ready_weapon_action_id = action.id
        session._ready_weapon_action_outcome = None
        before_rng = session._rng_cursor.state
        before_inventory = session.public_view()["character"]["inventory"]
        original_apply = _WritePlan.apply_phase

        def fail_after_target_write(plan, phase):
            original_apply(plan, phase)
            if phase == "targets":
                raise RuntimeError("injected ready publication fault")

        with patch("action_evaluation.ready_weapon_eligibility", return_value=None):
            pending = session.advance_one_second()
            self.assertEqual(candidate.encounter.time, start + 1)
            self.assertEqual(pending["ready_weapon_action"]["duration_seconds"], 2)
            self.assertEqual(pending["ready_weapon_action"]["seconds_remaining"], 1)
            with patch.object(_WritePlan, "apply_phase", fail_after_target_write):
                with self.assertRaises(ArenaBrowserRequestError) as caught:
                    session.advance_one_second()
            failure = caught.exception.__cause__
            self.assertIsInstance(failure, PublicationFailure)
            self.assertFalse(failure.rollback_errors)
            self.assertEqual(candidate.encounter.time, start + 1)
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

    def test_same_boundary_strike_cannot_use_uncommitted_two_second_draw(self):
        session, candidate, player, placement, weapon = arena(seed=20261112)
        acquire_dagger(session, candidate, player, placement)
        player.current.body_parts["right hand"] = None
        action = ReadyWeaponAction(candidate.encounter, player.id, weapon.id,
                                   "right hand", candidate.encounter.time)
        candidate.encounter.schedule_action(action)
        opponent = candidate.participants[1].native.being
        strike = MeleeStrike(candidate.encounter, player.id, opponent.id, weapon.id,
                             motion="thrust", reach=100)
        with self.assertRaisesRegex(ValueError, "actor does not hold that weapon"):
            candidate.encounter.schedule_action(strike)
        self.assertIsNone(player.current.body_parts["right hand"])
        self.assertEqual(player.weapons, [])
        self.assertEqual(player.possessions, [weapon.id])


if __name__ == "__main__":
    unittest.main()
