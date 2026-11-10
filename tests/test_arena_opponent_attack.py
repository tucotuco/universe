"""Native attack-only Arena opponent integration and persistence checks."""
import json
from pathlib import Path
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "examples")]

from arena_browser_session import GeneratedArenaSession
from melee_combat import MeleeStrike


EMPTY_PROFILE = json.loads((ROOT / "tests/fixtures/arena/empty.json").read_text())


def create_session(seed=20261107):
    session = GeneratedArenaSession(root_seed_factory=lambda: seed,
                                    ground_loadout_profile=EMPTY_PROFILE)
    view = session.generate({
        "starting_experience": "10000", "width_cells": "10", "height_cells": "5",
        "equipment_mode": "equipped", "opponent_strategy": "attack_only",
    })
    candidate = session.active_candidate
    player, opponent = (part.native.being for part in candidate.participants)
    return session, candidate, player, opponent, view


def first_move(session, candidate, destination):
    view = session.choose_destination({"column": destination[0], "row": destination[1],
                                      "rate": "sprint", "facing_policy": "turn"})
    return view


class TestArenaOpponentAttack(unittest.TestCase):
    def test_attack_only_native_thrust_pending_restore_and_completed_restore(self):
        source, candidate, player, opponent, view = create_session()
        self.assertEqual(view["opponent_strategy"], "attack_only")
        self.assertEqual(candidate.ground_objects, ())
        self.assertEqual(len(candidate.initial_equipment_provenance), 2)
        for participant in candidate.participants:
            being = participant.native.being
            initial_dagger_id = source._initial_ready_dagger_id(candidate, being)
            self.assertIsNotNone(initial_dagger_id)
            self.assertIn(initial_dagger_id, being.armed_with(candidate.universe).values())
        self.assertIsNone(view["opponent_melee_action"])
        first_move(source, candidate, (5, 4))

        # A player's first ordinary movement choice activates the Arena. The
        # AI uses only the opposing Being's current native evidence and state.
        view = source.advance_one_second()
        action = source._opponent_melee_action(candidate, opponent)
        self.assertIs(type(action), MeleeStrike)
        weapon_id = source._initial_ready_dagger_id(candidate, opponent)
        weapon = candidate.universe.get_object_by_id(weapon_id)
        self.assertEqual((action.actor_id, action.target_id, action.instrument_id),
                         (opponent.id, player.id, weapon_id))
        self.assertIn(weapon_id, opponent.armed_with(candidate.universe).values())
        self.assertEqual(weapon.parent_container_id, opponent.id)
        self.assertEqual(action.event_type, "thrust")
        self.assertEqual(action.end_time - action.start_time, 4)
        self.assertEqual(view["opponent_melee_action"]["status"], "executing")
        self.assertEqual(view["opponent_melee_action"]["seconds_remaining"], 3)
        self.assertNotIn(opponent.id, json.dumps(view))
        self.assertNotIn(weapon_id, json.dumps(view))

        pending_wire = source.save_encounter_bytes()
        restored = GeneratedArenaSession()
        with mock.patch("npcgen.api.arena_ready_being",
                        side_effect=AssertionError("Load must not regenerate NPC or equipment")):
            restored_view = restored.load_encounter_bytes(pending_wire)
        restored_candidate = restored.active_candidate
        restored_player, restored_opponent = (
            part.native.being for part in restored_candidate.participants)
        restored_action = restored._opponent_melee_action(restored_candidate, restored_opponent)
        self.assertEqual(restored_view["opponent_strategy"], "attack_only")
        self.assertEqual(restored_action.id, action.id)
        self.assertEqual(restored_action.instrument_id, weapon_id)
        self.assertEqual(restored_view["opponent_melee_action"], view["opponent_melee_action"])

        for _ in range(3):
            left = source.advance_one_second()
            right = restored.advance_one_second()
            self.assertEqual(left["time_seconds"], right["time_seconds"])
            self.assertEqual(left["opponent_melee_action"], right["opponent_melee_action"])
        left_result = source.public_view()["opponent_melee_action"]
        right_result = restored.public_view()["opponent_melee_action"]
        self.assertEqual(left_result, right_result)
        self.assertEqual(left_result["status"], "completed")
        self.assertEqual(left_result["outcome"], "normal")
        self.assertEqual(left_result["duration_seconds"], 4)
        self.assertEqual(source._rng_cursor.state, restored._rng_cursor.state)
        self.assertEqual(source.active_candidate.encounter.time, restored.active_candidate.encounter.time)
        self.assertEqual(source.active_candidate.encounter.finished_action_list,
                         restored.active_candidate.encounter.finished_action_list)
        self.assertEqual(set(source.active_candidate.universe.event_history),
                         set(restored.active_candidate.universe.event_history))
        self.assertEqual(source.active_candidate.encounter.choice_state,
                         restored.active_candidate.encounter.choice_state)
        for left_part, right_part in zip(source.active_candidate.participants,
                                         restored.active_candidate.participants):
            left_ledger = object.__getattribute__(left_part.native.being, "__dict__")["_arena_perception_ledger"]
            right_ledger = object.__getattribute__(right_part.native.being, "__dict__")["_arena_perception_ledger"]
            self.assertEqual(left_ledger.history, right_ledger.history)
        self.assertEqual(source.active_candidate.participants[0].native.being.get_hit_points(),
                         restored.active_candidate.participants[0].native.being.get_hit_points())

        completed_wire = restored.save_encounter_bytes()
        completed_restore = GeneratedArenaSession()
        completed_view = completed_restore.load_encounter_bytes(completed_wire)
        self.assertEqual(completed_view["opponent_melee_action"], right_result)
        # The next autonomous declaration is repeatable after another Save/Load.
        left_next = source.advance_one_second()
        right_next = completed_restore.advance_one_second()
        self.assertEqual(left_next["opponent_melee_action"], right_next["opponent_melee_action"])
        self.assertEqual(source._opponent_melee_action(
            source.active_candidate, source.active_candidate.participants[1].native.being).id,
            completed_restore._opponent_melee_action(
                completed_restore.active_candidate,
                completed_restore.active_candidate.participants[1].native.being).id)

    def test_native_impact_legality_out_of_reach_and_pending_deduplication(self):
        session, candidate, _player, opponent, _ = create_session()
        first_move(session, candidate, (0, 0))
        view = session.advance_one_second()
        action = session._opponent_melee_action(candidate, opponent)
        self.assertIsInstance(action, MeleeStrike)
        action_id = action.id
        self.assertFalse(session._opponent_attack_preflight(candidate)[0])
        self.assertEqual(session._opponent_attack_refusal, "opponent_melee_already_pending")
        self.assertIsNone(session._schedule_opponent_attack(candidate))
        self.assertEqual(session._opponent_melee_action(candidate, opponent).id, action_id)
        self.assertTrue(view["advance_available"])
        for _ in range(3):
            view = session.advance_one_second()
        self.assertEqual(view["opponent_melee_action"]["status"], "completed")
        self.assertEqual(view["opponent_melee_action"]["outcome"], "out_of_reach")

    def test_ineligible_opponent_requests_do_not_create_choices_or_consume_native_rng(self):
        cases = ("no_evidence", "unready", "missing_weapon", "unable")
        for case in cases:
            with self.subTest(case=case):
                session, candidate, player, opponent, _ = create_session()
                first_move(session, candidate, (5, 4))
                ledger = object.__getattribute__(opponent, "__dict__")["_arena_perception_ledger"]
                weapon_id = session._initial_ready_dagger_id(candidate, opponent)
                if case == "no_evidence":
                    ledger._current.pop(player.id, None)
                    candidate.encounter.awareness[opponent.id].discard(player.id)
                elif case == "unready":
                    for slot, held in tuple(opponent.current.body_parts.items()):
                        if held == weapon_id:
                            opponent.current.body_parts[slot] = None
                            break
                elif case == "missing_weapon":
                    opponent.weapons.remove(weapon_id)
                else:
                    opponent.set_hit_points(0)
                revision = candidate.encounter._choice_book.revision
                rng_state = session._rng_cursor.state
                event_ids = set(candidate.universe.event_history)
                action = session._schedule_opponent_attack(candidate)
                self.assertIsNone(action)
                self.assertEqual(candidate.encounter._choice_book.revision, revision)
                self.assertEqual(session._rng_cursor.state, rng_state)
                self.assertEqual(set(candidate.universe.event_history), event_ids)
                self.assertFalse(session._opponent_melee_pending(candidate, opponent))
                expected = {
                    "no_evidence": "opponent_has_no_current_awareness_evidence",
                    "unready": "opponent_has_no_ready_native_thrust_dagger",
                    "missing_weapon": "opponent_has_no_ready_native_thrust_dagger",
                    "unable": "opponent_unable_to_act",
                }[case]
                self.assertEqual(session._opponent_attack_refusal, expected)

    def test_player_and_opponent_strikes_share_native_same_boundary_settlement(self):
        session, candidate, player, opponent, view = create_session()
        first_move(session, candidate, (5, 4))
        target = next(row for row in view["entities"] if row["category"] == "being")
        session.inspect_entity({"handle": target["handle"]})
        session.choose_melee_strike({"handle": target["handle"], "motion": "thrust"})
        source_action = session._player_melee_action(candidate, player)
        self.assertIsInstance(source_action, MeleeStrike)
        session.advance_one_second()
        opponent_action = session._opponent_melee_action(candidate, opponent)
        self.assertIsInstance(opponent_action, MeleeStrike)
        self.assertEqual(source_action.start_time, opponent_action.start_time)
        self.assertEqual(source_action.start_time, 0)
        for _ in range(3):
            session.advance_one_second()
        record = candidate.encounter.inspect_committed(4)
        self.assertIn(source_action.id, record.actions)
        self.assertIn(opponent_action.id, record.actions)
        self.assertEqual(session.public_view()["opponent_melee_action"]["status"], "completed")

    def test_old_arena_save_schema_loads_with_autonomous_strategy_disabled(self):
        import hashlib
        from arena_persistence import _canonical, _PREVIOUS_SCHEMA

        session, _candidate, _player, _opponent, _ = create_session()
        # A legacy file never selected an opponent strategy. Re-encode its
        # exact old closed field set and digest, then exercise normal loading.
        data = json.loads(session.save_encounter_bytes())
        data.pop("sha256")
        data["schema"] = _PREVIOUS_SCHEMA
        data["session"].pop("opponent_strategy")
        data["sha256"] = hashlib.sha256(_canonical(data)).hexdigest()
        wire = _canonical(data)
        restored = GeneratedArenaSession()
        view = restored.load_encounter_bytes(wire)
        self.assertEqual(view["opponent_strategy"], "none")


if __name__ == "__main__":
    unittest.main()
