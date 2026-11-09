"""Native two-second Draw from explicitly authored source and hand state."""
from pathlib import Path
import json
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from activities import ReadyWeaponAction
from arena_browser_session import ArenaBrowserRequestError, GeneratedArenaSession
from arena_hex_map import HexAddress
from arena_perception import ArenaPerceptionEvidence
from atomic_publication import PublicationFailure, _WritePlan
from melee_combat import MeleeStrike
from weapon import (DRAWABLE_WORN_SHEATH, NATIVE_DRAW_LOCATION_TAG, WeaponInstance,
                    author_worn_sheath_draw_location, native_weapon_draw_location,
                    re_ready_time_after_strike)

GENERATE = {"starting_experience": "10000", "width_cells": "10", "height_cells": "5"}
DAGGER = [{"source_item_id": "ready-test:dagger", "category": "weapon",
           "native_type_key": "Dagger", "quantity": 1, "ordinary": True,
           "magical": False, "mechanics": None, "origin": "ready-test.v1"}]


def arena(seed=20261108, *, ground_dagger=False):
    session = GeneratedArenaSession(root_seed_factory=lambda: seed,
        ground_item_descriptions=DAGGER if ground_dagger else ())
    session.generate(GENERATE)
    candidate = session.active_candidate
    player = candidate.participants[0].native.being
    if player.current.hit_points <= 0:
        raise AssertionError("deterministic fixture must contain a positive-HP player")
    return session, candidate, player


def add_authored_drawable_dagger(session, candidate, player, *, hand="right hand"):
    """Author one carried weapon, a drawable-source tag, and an explicit free hand."""
    object_id = candidate.encounter.make_weapon("Dagger", "Test Dagger")
    weapon = candidate.universe.get_object_by_id(object_id)
    if type(weapon) is not WeaponInstance:
        raise AssertionError("test fixture requires an exact native WeaponInstance")
    player.possessions.append(weapon.id)
    weapon.parent_container_id = player.id
    player.current.body_parts[hand] = None
    author_worn_sheath_draw_location(weapon, player.id)
    ledger = object.__getattribute__(player, "__dict__")["_arena_perception_ledger"]
    evidence = ArenaPerceptionEvidence(player.id, weapon.id, "object", weapon.name,
        "Dagger", None, "carried", 0, 0.0)
    ledger._current[weapon.id] = evidence
    ledger._history.append(evidence)
    return weapon


def activate(session):
    session.choose_run()
    return session.advance_one_second()


def select_draw(session, weapon):
    entity = next(row for row in session.public_view()["entities"]
                  if row["name"] == weapon.name and row["type"] == "Dagger")
    inspected = session.inspect_entity({"handle": entity["handle"]})
    return entity["handle"], inspected


def draw_scenario():
    return json.loads((ROOT / "examples/arena_scenarios/ordinary-dagger-draw.json")
                      .read_text(encoding="utf-8"))


class TestArenaReadyWeapon(unittest.TestCase):
    def test_opt_in_authored_scenario_draws_as_first_choice_and_regenerates_cleanly(self):
        session = GeneratedArenaSession(root_seed_factory=iter((20261120, 20261121)).__next__,
                                        authored_draw_scenario=draw_scenario())
        first_view = session.generate(GENERATE)
        candidate = session.active_candidate
        player = candidate.participants[0].native.being
        opponent = candidate.participants[1].native.being
        self.assertEqual(candidate.encounter.time, 0)
        self.assertFalse(candidate.encounter.initiated)
        self.assertIsNone(candidate.encounter.initiation)
        self.assertEqual(player.current.body_parts, {"right hand": None})
        self.assertEqual(len(player.possessions), 1)
        weapon = candidate.universe.get_object_by_id(player.possessions[0])
        self.assertIs(type(weapon), WeaponInstance)
        self.assertEqual(weapon.current.obj_type, "Dagger")
        self.assertEqual(weapon.name, "Drawable Dagger")
        self.assertEqual(weapon.parent_container_id, player.id)
        self.assertEqual(player.weapons, [])
        self.assertIsNone(player.current.armor_id)
        self.assertEqual(native_weapon_draw_location(weapon),
                         {"kind": "worn_sheath", "owner_id": player.id})
        own_ledger = object.__getattribute__(player, "__dict__")["_arena_perception_ledger"]
        opponent_ledger = object.__getattribute__(opponent, "__dict__")["_arena_perception_ledger"]
        self.assertIn(weapon.id, {row.entity_id for row in own_ledger.current})
        self.assertNotIn(weapon.id, {row.entity_id for row in opponent_ledger.current})
        self.assertNotIn(weapon.id, opponent.possessions)
        self.assertNotIn(weapon.id, json.dumps(first_view))
        self.assertEqual(candidate.encounter.pending_action_list, [])
        self.assertFalse(any(type(event) is ReadyWeaponAction
                             for event in candidate.universe.event_history.values()))

        entity = next(row for row in first_view["entities"]
                      if row["name"] == "Drawable Dagger")
        inspected = session.inspect_entity({"handle": entity["handle"]})
        catalog = next(row for row in inspected["action_catalog"]["entries"]
                       if row["name"] == "ready weapon")
        self.assertEqual((catalog["status"], catalog["display_name"], catalog["hands"]),
                         ("available", "Draw (2 s)", ["right hand"]))
        weight = weapon.current.weight
        activation_awareness = dict((key, set(value)) for key, value in candidate.encounter.awareness.items())
        accepted = session.choose_ready_weapon({"handle": entity["handle"], "hand": "right hand"})
        self.assertTrue(candidate.encounter.initiated)
        self.assertIsNone(candidate.encounter.initiation)
        self.assertEqual(candidate.encounter.awareness, activation_awareness)
        self.assertIsNotNone(candidate.encounter.arena_activation)
        self.assertEqual(candidate.encounter.arena_activation.activation_kind,
                         "first_player_choice")
        self.assertNotIn("target_id", candidate.encounter.arena_activation.to_dict())
        self.assertEqual(accepted["ready_weapon_action"]["seconds_remaining"], 2)
        self.assertEqual(accepted["character"]["inventory"]["items"][0]["status"],
                         "carried; not readied")
        one = session.advance_one_second()
        self.assertEqual(one["time_seconds"], 1)
        self.assertEqual(one["ready_weapon_action"]["seconds_remaining"], 1)
        self.assertEqual(one["character"]["inventory"]["items"][0]["status"],
                         "carried; not readied")
        self.assertIsNone(player.current.body_parts["right hand"])
        self.assertIsNotNone(native_weapon_draw_location(weapon))
        two = session.advance_one_second()
        self.assertEqual(two["time_seconds"], 2)
        self.assertEqual(two["ready_weapon_action"]["outcome"], "success")
        self.assertEqual(two["character"]["inventory"]["items"][0]["status"],
                         "readied in right hand")
        self.assertEqual(two["character"]["inventory"]["items"][0]["weight_pounds"], weight)
        self.assertEqual(two["character"]["inventory"]["carried_weight_pounds"], weight)
        self.assertEqual(player.current.body_parts["right hand"], weapon.id)
        self.assertEqual(player.possessions, [weapon.id])
        self.assertEqual(weapon.parent_container_id, player.id)
        self.assertIsNone(native_weapon_draw_location(weapon))
        self.assertNotIn(opponent.id, json.dumps(two["character"]))
        old_id = weapon.id

        session.generate(GENERATE)
        replacement = session.active_candidate
        replacement_player = replacement.participants[0].native.being
        replacement_weapon = replacement.universe.get_object_by_id(replacement_player.possessions[0])
        self.assertNotEqual(replacement_weapon.id, old_id)
        self.assertEqual(replacement.encounter.time, 0)
        self.assertEqual(replacement_player.current.body_parts, {"right hand": None})
        self.assertEqual(replacement_player.weapons, [])
        self.assertIsNotNone(native_weapon_draw_location(replacement_weapon))

    def test_opt_in_scenario_is_strict_and_failed_replacement_preserves_active_candidate(self):
        from arena_browser_session import ArenaBrowserRequestError

        invalid = draw_scenario()
        invalid["player_hand_slots"] = {"right hand": "forged-object-id"}
        with self.assertRaisesRegex(ArenaBrowserRequestError, "exactly one free right hand"):
            GeneratedArenaSession(authored_draw_scenario=invalid)

        session = GeneratedArenaSession(root_seed_factory=iter((20261122, 20261123)).__next__,
                                        authored_draw_scenario=draw_scenario())
        session.generate(GENERATE)
        original = session.active_candidate
        original_view = session.public_view()
        with patch("arena_authored_draw_scenario.author_scenario",
                   side_effect=ValueError("fixture native preflight refusal")):
            with self.assertRaisesRegex(ArenaBrowserRequestError, "candidate could not be activated"):
                session.generate(GENERATE)
        self.assertIs(session.active_candidate, original)
        self.assertEqual(session.public_view(), original_view)

    def test_normal_generated_arena_does_not_receive_authored_hand_or_weapon(self):
        session, candidate, player = arena(seed=20261124)
        self.assertEqual(player.current.body_parts, {})
        self.assertEqual(player.possessions, [])
        self.assertEqual(player.weapons, [])
        self.assertFalse(candidate.ground_objects)
        self.assertFalse(any(type(obj) is WeaponInstance and obj.parent_container_id == player.id
                             for obj in candidate.universe.object_registry.object_instances.values()))

    def test_revision_61_re_ready_timing_uses_weapon_and_motion_table_values(self):
        _, candidate, _ = arena()
        weapons = candidate.universe.get_weapon_dictionary()
        dagger = weapons.get_object_definition("Dagger")
        longsword = weapons.get_object_definition("Longsword")
        repeating_crossbow = weapons.get_object_definition("Repeating crossbow")
        self.assertEqual([re_ready_time_after_strike(dagger, motion)
                          for motion in ("range", "swing", "thrust")], [1, 1, 1])
        self.assertEqual(re_ready_time_after_strike(longsword, "swing"), 2)
        # This native-config row is absent from the adopted r61 appendix. The
        # helper preserves its arithmetic zero without creating any Action.
        self.assertEqual(re_ready_time_after_strike(repeating_crossbow, "range"), 0)

    def test_draw_commits_only_at_two_second_boundary_and_consumes_source_evidence(self):
        session, candidate, player = arena(seed=20261109)
        weapon = add_authored_drawable_dagger(session, candidate, player)
        other_ledger = object.__getattribute__(
            candidate.participants[1].native.being, "__dict__")["_arena_perception_ledger"]
        self.assertNotIn(weapon.id, {row.entity_id for row in other_ledger.current})
        activate(session)
        start = int(candidate.encounter.time)
        handle, view = select_draw(session, weapon)
        entry = next(row for row in view["action_catalog"]["entries"]
                     if row["name"] == "ready weapon")
        self.assertEqual(entry["status"], "available")
        self.assertEqual(entry["display_name"], "Draw (2 s)")
        self.assertEqual(entry["hands"], ["right hand"])
        self.assertIn("worn sheath", entry["reason"])
        weight = view["character"]["inventory"]["carried_weight_pounds"]
        accepted = session.choose_ready_weapon({"handle": handle, "hand": "right hand"})
        action_id = session._ready_weapon_action_id
        self.assertEqual(accepted["ready_weapon_action"]["duration_seconds"], 2)
        self.assertEqual(accepted["ready_weapon_action"]["seconds_remaining"], 2)

        first = session.advance_one_second()
        self.assertEqual(first["time_seconds"], start + 1)
        self.assertEqual(first["ready_weapon_action"]["status"], "executing")
        self.assertEqual(first["ready_weapon_action"]["seconds_remaining"], 1)
        self.assertEqual(first["character"]["inventory"]["items"][0]["status"],
                         "carried; not readied")
        self.assertEqual(player.current.body_parts["right hand"], None)
        self.assertEqual(player.weapons, [])
        self.assertIsNotNone(native_weapon_draw_location(weapon))

        second = session.advance_one_second()
        self.assertEqual(second["time_seconds"], start + 2)
        self.assertEqual(second["ready_weapon_action"]["outcome"], "success")
        self.assertEqual(second["character"]["inventory"]["items"][0]["status"],
                         "readied in right hand")
        self.assertEqual(second["character"]["inventory"]["carried_weight_pounds"], weight)
        self.assertEqual(player.possessions, [weapon.id])
        self.assertEqual(weapon.parent_container_id, player.id)
        self.assertEqual(player.weapons, [weapon.id])
        self.assertEqual(player.current.body_parts, {"right hand": weapon.id})
        self.assertIsNone(native_weapon_draw_location(weapon))
        self.assertEqual(candidate.encounter.inspect_committed(start + 2)
                         .action(action_id).facts.outcome, "success")
        self.assertNotIn(candidate.participants[1].native.being.id,
                         json.dumps(second["character"]))

    def test_ground_pickup_remains_carried_unreadied_and_does_not_create_draw_location(self):
        session, candidate, player = arena(seed=20261110, ground_dagger=True)
        placement = candidate.ground_objects[0]
        ground = candidate.universe.get_object_by_id(placement.native_object_id)
        player.current.body_parts["right hand"] = None
        address = HexAddress(placement.column, placement.row)
        destination = candidate.arena_map.layout.center_position(address, z=player.get_position().z)
        if player.get_position() != destination:
            session.choose_destination({"column": address.column, "row": address.row,
                                       "rate": "sprint", "facing_policy": "turn"})
            while session.public_view()["movement_plan"] is not None:
                session.advance_one_second()
        visible = next(row for row in session.public_view()["entities"]
                       if row["handle"] in session._view_handles.values()
                       and row["type"] == "Dagger")
        session.inspect_entity({"handle": visible["handle"]})
        session.choose_pickup({"handle": visible["handle"]})
        picked = session.advance_one_second()
        self.assertEqual(picked["pickup_action"]["outcome"], "success")
        self.assertEqual(ground.parent_container_id, player.id)
        self.assertIn(ground.id, player.possessions)
        self.assertEqual(player.current.body_parts["right hand"], None)
        self.assertEqual(player.weapons, [])
        self.assertIsNone(native_weapon_draw_location(ground))
        draw = next(row for row in picked["action_catalog"]["entries"]
                    if row["name"] == "ready weapon")
        self.assertEqual(draw["status"], "unavailable")
        self.assertIn("no authored drawable source location", draw["reason"])
        self.assertEqual(picked["character"]["inventory"]["items"][0]["status"],
                         "carried; not readied")

    def test_missing_occupied_malformed_or_wrong_owner_evidence_fails_closed(self):
        session, candidate, player = arena(seed=20261111)
        weapon = add_authored_drawable_dagger(session, candidate, player)
        activate(session)
        handle, _ = select_draw(session, weapon)
        time_before = candidate.encounter.time
        choices_before = dict(candidate.encounter._choice_book._choices)
        player.current.body_parts["right hand"] = weapon.id
        with self.assertRaisesRegex(ValueError, "already held/readied"):
            session.choose_ready_weapon({"handle": handle, "hand": "right hand"})
        player.current.body_parts["right hand"] = None
        weapon.current.tags[NATIVE_DRAW_LOCATION_TAG] = {"kind": DRAWABLE_WORN_SHEATH}
        malformed = session.public_view()
        self.assertEqual(next(row for row in malformed["action_catalog"]["entries"]
                             if row["name"] == "ready weapon")["status"], "unavailable")
        self.assertIn("malformed", next(row for row in malformed["action_catalog"]["entries"]
                                        if row["name"] == "ready weapon")["reason"])
        malformed_action = ReadyWeaponAction(candidate.encounter, player.id, weapon.id,
                                             "right hand", int(candidate.encounter.time))
        with self.assertRaisesRegex(ValueError, "draw-location record is malformed"):
            candidate.encounter.schedule_action(malformed_action)
        author_worn_sheath_draw_location(weapon, candidate.participants[1].native.being.id)
        wrong_owner = session.public_view()
        self.assertEqual(next(row for row in wrong_owner["action_catalog"]["entries"]
                             if row["name"] == "ready weapon")["status"], "unavailable")
        self.assertIn("not assigned", next(row for row in wrong_owner["action_catalog"]["entries"]
                                            if row["name"] == "ready weapon")["reason"])
        self.assertEqual(player.weapons, [])
        self.assertEqual(player.possessions, [weapon.id])
        self.assertEqual(player.current.body_parts["right hand"], None)
        self.assertEqual(candidate.encounter.time, time_before)
        self.assertEqual(candidate.encounter._choice_book._choices, choices_before)

    def test_same_second_action_cannot_use_draw_that_has_not_committed(self):
        session, candidate, player = arena(seed=20261112)
        weapon = add_authored_drawable_dagger(session, candidate, player)
        activate(session)
        handle, _ = select_draw(session, weapon)
        session.choose_ready_weapon({"handle": handle, "hand": "right hand"})
        opponent = candidate.participants[1].native.being
        with self.assertRaisesRegex(ValueError, "actor does not hold that weapon"):
            MeleeStrike(candidate.encounter, player.id, opponent.id, weapon.id,
                        motion="thrust", reach=100).prepare_schedule(candidate.encounter)
        session.advance_one_second()
        self.assertEqual(player.current.body_parts["right hand"], None)
        self.assertEqual(player.weapons, [])
        session.advance_one_second()
        self.assertEqual(player.current.body_parts["right hand"], weapon.id)

    def test_simultaneous_same_hand_and_weapon_claims_are_contested(self):
        session, candidate, player = arena(seed=20261113)
        weapon = add_authored_drawable_dagger(session, candidate, player)
        activate(session)
        start = int(candidate.encounter.time)
        first = ReadyWeaponAction(candidate.encounter, player.id, weapon.id, "right hand", start)
        second = ReadyWeaponAction(candidate.encounter, player.id, weapon.id, "right hand", start)
        candidate.encounter.schedule_action(first)
        candidate.encounter.schedule_action(second)
        candidate.encounter.step(2)
        record = candidate.encounter.inspect_committed(start + 2)
        self.assertEqual(record.action(first.id).facts.outcome, "contested")
        self.assertEqual(record.action(second.id).facts.outcome, "contested")
        self.assertEqual(player.possessions, [weapon.id])
        self.assertEqual(player.weapons, [])
        self.assertEqual(player.current.body_parts["right hand"], None)
        self.assertIsNotNone(native_weapon_draw_location(weapon))

    def test_interruption_and_publication_rollback_preserve_draw_location_and_identity(self):
        session, candidate, player = arena(seed=20261114)
        weapon = add_authored_drawable_dagger(session, candidate, player)
        activate(session)
        handle, _ = select_draw(session, weapon)
        session.choose_ready_weapon({"handle": handle, "hand": "right hand"})
        action_id = session._ready_weapon_action_id
        choice_id = next(key for key, row in candidate.encounter._choice_book._choices.items()
                         if action_id in row.view.action_ids)
        candidate.encounter._choice_book.undo(choice_id)
        self.assertNotIn(action_id, candidate.universe.event_history)
        self.assertEqual(player.current.body_parts["right hand"], None)
        self.assertIsNotNone(native_weapon_draw_location(weapon))

        session, candidate, player = arena(seed=20261115)
        weapon = add_authored_drawable_dagger(session, candidate, player)
        activate(session)
        handle, _ = select_draw(session, weapon)
        session.choose_ready_weapon({"handle": handle, "hand": "right hand"})
        before_rng = session._rng_cursor.state
        before_view = session.public_view()
        original_apply = _WritePlan.apply_phase

        def fail_after_target_write(plan, phase):
            original_apply(plan, phase)
            if phase == "targets":
                raise RuntimeError("injected Draw publication fault")

        session.advance_one_second()
        with patch.object(_WritePlan, "apply_phase", fail_after_target_write):
            with self.assertRaises(ArenaBrowserRequestError) as caught:
                session.advance_one_second()
        failure = caught.exception.__cause__
        self.assertIsInstance(failure, PublicationFailure)
        self.assertFalse(failure.rollback_errors)
        self.assertEqual(candidate.encounter.time, before_view["time_seconds"] + 1)
        self.assertEqual(session._rng_cursor.state, before_rng)
        self.assertEqual(player.current.body_parts["right hand"], None)
        self.assertEqual(player.weapons, [])
        self.assertEqual(player.possessions, [weapon.id])
        self.assertEqual(native_weapon_draw_location(weapon)["owner_id"], player.id)
        candidate.encounter.recover_transactional_progression(failure.recovery_token)
        drawn = session.advance_one_second()
        self.assertEqual(drawn["ready_weapon_action"]["outcome"], "success")
        self.assertEqual(player.current.body_parts["right hand"], weapon.id)
        self.assertIsNone(native_weapon_draw_location(weapon))

    def test_re_ready_formula_zero_config_case_is_not_a_zero_duration_action(self):
        _, candidate, _ = arena()
        weapons = candidate.universe.get_weapon_dictionary()
        self.assertEqual(re_ready_time_after_strike(
            weapons.get_object_definition("Repeating crossbow"), "range"), 0)
        self.assertEqual(ReadyWeaponAction.DRAW_DURATION_SECONDS, 2)


if __name__ == "__main__":
    unittest.main()
