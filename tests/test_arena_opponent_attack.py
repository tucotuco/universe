"""Native attack-only Arena opponent integration and persistence checks."""
import json
import hashlib
import io
import math
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "examples")]

from arena_browser_session import ArenaBrowserRequestError, GeneratedArenaSession
from melee_combat import MeleeStrike
from melee_defense import MeleeDefense


EMPTY_PROFILE = json.loads((ROOT / "tests/fixtures/arena/empty.json").read_text())


def create_session(seed=20261107, strategy="attack_only", equipment_mode="equipped",
                   trace_ui=False, trace_stream=None):
    session = GeneratedArenaSession(root_seed_factory=lambda: seed, trace_ui=trace_ui,
                                    trace_stream=trace_stream,
                                    ground_loadout_profile=EMPTY_PROFILE)
    view = session.generate({
        "starting_experience": "10000", "width_cells": "10", "height_cells": "5",
        "equipment_mode": equipment_mode, "opponent_strategy": strategy,
    })
    candidate = session.active_candidate
    player, opponent = (part.native.being for part in candidate.participants)
    return session, candidate, player, opponent, view


def first_move(session, candidate, destination):
    view = session.choose_destination({"column": destination[0], "row": destination[1],
                                      "rate": "sprint", "facing_policy": "turn"})
    return view


def native_continuation_state(session):
    candidate = session.active_candidate
    encounter = candidate.encounter
    rows, histories = [], []
    for participant in candidate.participants:
        being = participant.native.being
        rows.append((being.id, being.get_position(), being.hex_facing,
                     being.get_hit_points(), tuple(sorted(being.skill_experience.items())),
                     tuple(sorted(being.strategy.__dict__.items()))))
        ledger = object.__getattribute__(being, "__dict__").get("_arena_perception_ledger")
        histories.append((ledger.current, ledger.history))
    actions = []
    for event_id, action in candidate.universe.event_history.items():
        if type(action) in (MeleeStrike, MeleeDefense):
            resolution = getattr(action, "resolution", None)
            actions.append((event_id, type(action).__name__, action.actor_id, action.target_id,
                            action.instrument_id, action.start_time, action.end_time,
                            getattr(action, "kind", None), getattr(action, "target_action_id", None),
                            getattr(action, "ready_at", None), getattr(action, "result", None),
                            getattr(action, "success", None),
                            tuple(getattr(action, "defended_action_ids", ())),
                            None if resolution is None else resolution.outcome))
    return (encounter.time, encounter.last_processed_boundary, tuple(rows), tuple(sorted(actions)),
            tuple(encounter.pending_action_list), tuple(encounter.finished_action_list),
            tuple(encounter.cancelled_action_list), tuple(sorted(candidate.universe.event_history)),
            encounter.choice_state, tuple(histories), session._rng_cursor.state)


def subprocess_advance_checkpoint(wire, seconds):
    script = r'''
import sys
import npcgen.api
from tests.test_arena_opponent_attack import native_continuation_state, continuation_digest
from arena_browser_session import GeneratedArenaSession
npcgen.api.arena_ready_being = lambda *args, **kwargs: (_ for _ in ()).throw(
    AssertionError("checkpoint load must not regenerate Beings"))
session = GeneratedArenaSession()
session.load_encounter_bytes(sys.stdin.buffer.read())
for _ in range(int(sys.argv[1])):
    session.advance_one_second()
sys.stdout.write(continuation_digest(native_continuation_state(session)))
'''
    completed = subprocess.run(
        [sys.executable, "-c", script, str(seconds)],
        input=wire, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        check=True, env=os.environ.copy())
    return completed.stdout.decode("ascii")


def continuation_digest(state):
    canonical = json.dumps(state, default=repr, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class TestArenaOpponentAttack(unittest.TestCase):
    def test_player_native_dodge_waits_for_observed_strike_and_restores(self):
        trace = io.StringIO()
        source, candidate, player, opponent, _ = create_session(
            seed=20261107, trace_ui=True, trace_stream=trace)
        source.choose_run()
        source.advance_one_second()
        view = source.advance_one_second()
        strike = source._opponent_melee_action(candidate, opponent)
        self.assertIsInstance(strike, MeleeStrike)
        self.assertEqual((strike.start_time, strike.end_time), (1, 5))
        handle = next(row["handle"] for row in view["entities"]
                      if row["category"] == "being")
        view = source.inspect_entity({"handle": handle})
        dodge = next(row for row in view["action_catalog"]["entries"]
                     if row["name"] == "Dodge")
        self.assertEqual(dodge["status"], "available")
        self.assertNotIn(strike.id, str(dodge))
        accepted = source.choose_dodge({"handle": handle})
        self.assertEqual(accepted["defense_action"]["status"], "accepted")
        self.assertEqual(accepted["defense_action"]["seconds_remaining"], 3)
        defense = source._latest_melee_defense(candidate, player)
        self.assertIsInstance(defense, MeleeDefense)
        self.assertEqual(defense.target_action_id, strike.id)
        self.assertNotIn(defense.id, str(accepted))
        self.assertIn("action=player_defense kind=dodge preparation=2s", trace.getvalue())

        wire = source.save_encounter_bytes()
        restored = GeneratedArenaSession()
        with mock.patch("npcgen.api.arena_ready_being",
                        side_effect=AssertionError("Load must not regenerate Beings")):
            restored.load_encounter_bytes(wire)
        for _ in range(2):
            source.advance_one_second()
            restored.advance_one_second()
            self.assertEqual(native_continuation_state(source),
                             native_continuation_state(restored))
        self.assertEqual(subprocess_advance_checkpoint(wire, 2),
                         continuation_digest(native_continuation_state(source)))
        ready_view = source.public_view()
        self.assertEqual(ready_view["defense_action"]["status"], "committed")
        self.assertEqual(ready_view["defense_action"]["preparation_ready_at"], 4)
        self.assertEqual(ready_view["time_seconds"], 4)
        ready_wire = source.save_encounter_bytes()
        ready_restore = GeneratedArenaSession()
        with mock.patch("npcgen.api.arena_ready_being",
                        side_effect=AssertionError("Load must not regenerate a ready Dodge")):
            ready_restore.load_encounter_bytes(ready_wire)
        source.advance_one_second()
        ready_restore.advance_one_second()
        self.assertEqual(native_continuation_state(source),
                         native_continuation_state(ready_restore))
        result = source.public_view()
        self.assertEqual(result["defense_action"]["status"], "completed")
        self.assertIn(result["defense_action"]["outcome"],
                      ("evaded", "failed", "no_threat", "unable_to_defend"))
        native_defense = source._latest_melee_defense(source.active_candidate,
                                                      source.active_candidate.participants[0].native.being)
        record = source.active_candidate.encounter.inspect_committed(5).action(native_defense.id)
        if record.facts.outcome in ("evaded", "failed"):
            self.assertEqual(player.skill_experience.get("tumble", 0), 10)
        else:
            self.assertEqual(player.skill_experience.get("tumble", 0), 0)
        completed_wire = source.save_encounter_bytes()
        completed_restore = GeneratedArenaSession()
        with mock.patch("npcgen.api.arena_ready_being",
                        side_effect=AssertionError("Load must not regenerate completed combat")):
            completed_restore.load_encounter_bytes(completed_wire)
        self.assertEqual(native_continuation_state(source),
                         native_continuation_state(completed_restore))

    def test_defense_only_opponent_dodges_only_an_observed_player_strike(self):
        source, candidate, player, opponent, view = create_session(
            seed=20261107, strategy="defense_only")
        self.assertEqual(view["opponent_strategy"], "defense_only")
        self.assertEqual(view["opponent_activity"], "waiting")
        source.choose_run()
        view = source.advance_one_second()
        self.assertEqual(source._opponent_decision(candidate)["kind"], "none")
        handle = next(row["handle"] for row in view["entities"]
                      if row["category"] == "being")
        view = source.inspect_entity({"handle": handle})
        no_threat = next(row for row in view["action_catalog"]["entries"]
                         if row["name"] == "Dodge")
        self.assertEqual(no_threat["status"], "unavailable")
        before = (candidate.encounter.time, candidate.encounter.choice_state,
                  source._rng_cursor.state)
        with self.assertRaisesRegex(ArenaBrowserRequestError, "No currently perceived"):
            source.choose_dodge({"handle": handle})
        self.assertEqual((candidate.encounter.time, candidate.encounter.choice_state,
                          source._rng_cursor.state), before)

        # Use the adopted map and movement system to close to an in-reach hex;
        # the opponent remains stationary and makes no strike.
        layout = candidate.arena_map.layout
        player_cell = layout.cell_at_position(player.get_position())
        opponent_cell = layout.cell_at_position(opponent.get_position())
        destinations = [address for address in layout.neighbors(opponent_cell)
                        if layout.contains(address) and address != player_cell]
        destination = min(destinations, key=lambda address: math.dist(
            player.get_position().as_tuple(),
            layout.center_position(address).as_tuple()))
        source.choose_destination({"column": destination.column, "row": destination.row,
                                   "rate": "sprint", "facing_policy": "turn"})
        view = source.advance_one_second()
        self.assertEqual(layout.cell_at_position(player.get_position()), destination)
        self.assertEqual(source._opponent_defense_decision(candidate)["kind"], "none")
        self.assertFalse(any(action.actor_id == opponent.id
                             for action in source._all_melee_actions(candidate)))

        view = source.inspect_entity({"handle": handle})
        catalog_strike = next(row for row in view["action_catalog"]["entries"]
                              if row["name"] == "thrust at being")
        self.assertEqual(catalog_strike["status"], "available")
        native_probe = source._melee_strike_preflight(
            candidate, player, opponent.id,
            next(row for row in object.__getattribute__(player, "__dict__")
                 ["_arena_perception_ledger"].current if row.entity_id == opponent.id),
            "thrust")
        self.assertEqual(native_probe[0]._status(candidate.encounter)[0], "in_reach")
        attack_view = source.choose_melee_strike({"handle": handle, "motion": "thrust"})
        player_strike = source._player_melee_action(candidate, player)
        self.assertIsInstance(player_strike, MeleeStrike)
        self.assertEqual(source._opponent_decision(candidate)["kind"], "none")
        self.assertFalse(source._all_melee_defenses(candidate))
        view = source.advance_one_second()
        self.assertEqual(view["time_seconds"], player_strike.start_time + 1)
        self.assertEqual(source._opponent_decision(candidate)["kind"], "defend")
        self.assertIsNone(view["opponent_defense_action"])

        view = source.advance_one_second()
        self.assertEqual(view["time_seconds"], player_strike.start_time + 2)
        self.assertEqual(view["opponent_defense_action"]["name"], "Dodge")
        self.assertEqual(view["opponent_defense_action"]["status"], "preparing")
        defense = source._latest_melee_defense(candidate, opponent)
        self.assertEqual(defense.target_action_id, player_strike.id)
        self.assertEqual([action for action in source._all_melee_defenses(candidate)
                          if action.actor_id == opponent.id], [defense])
        self.assertFalse(any(action.actor_id == opponent.id
                             for action in source._all_melee_actions(candidate)))

        wire = source.save_encounter_bytes()
        restored = GeneratedArenaSession()
        with mock.patch("npcgen.api.arena_ready_being",
                        side_effect=AssertionError("Load must not regenerate Defense-only Beings")):
            restored.load_encounter_bytes(wire)
        for _ in range(2):
            source.advance_one_second()
            restored.advance_one_second()
            self.assertEqual(native_continuation_state(source),
                             native_continuation_state(restored))
            self.assertEqual([action for action in source._all_melee_defenses(
                source.active_candidate)
                if action.actor_id == source.active_candidate.participants[1].native.being.id],
                [source._latest_melee_defense(source.active_candidate,
                    source.active_candidate.participants[1].native.being)])
        self.assertEqual(subprocess_advance_checkpoint(wire, 2),
                         continuation_digest(native_continuation_state(source)))
        completed = source.public_view()
        self.assertEqual(completed["opponent_defense_action"]["status"], "completed")
        self.assertIn(completed["opponent_defense_action"]["outcome"],
                      ("evaded", "failed", "no_threat", "unable_to_defend"))
        self.assertFalse(any(action.actor_id == opponent.id
                             for action in source._all_melee_actions(source.active_candidate)))
        after_wire = source.save_encounter_bytes()
        after_restore = GeneratedArenaSession()
        with mock.patch("npcgen.api.arena_ready_being",
                        side_effect=AssertionError("Load must not regenerate completed Defense-only Beings")):
            after_restore.load_encounter_bytes(after_wire)
        self.assertEqual(native_continuation_state(source),
                         native_continuation_state(after_restore))

    def test_targeted_dodge_refuses_when_two_seconds_cannot_fit_before_impact(self):
        source, candidate, player, opponent, _ = create_session(seed=20261107)
        source.choose_run()
        source.advance_one_second()
        source.advance_one_second()
        view = source.public_view()
        handle = next(row["handle"] for row in view["entities"]
                      if row["category"] == "being")
        for _ in range(2):
            source.advance_one_second()
        before = (candidate.encounter.time, candidate.encounter.choice_state,
                  tuple(candidate.universe.event_history), source._rng_cursor.state,
                  tuple(candidate.encounter.pending_action_list))
        with self.assertRaisesRegex(ArenaBrowserRequestError, "cannot be ready"):
            source.choose_dodge({"handle": handle})
        self.assertEqual((candidate.encounter.time, candidate.encounter.choice_state,
                          tuple(candidate.universe.event_history), source._rng_cursor.state,
                          tuple(candidate.encounter.pending_action_list)), before)

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
        # A player Run Choice activates the Encounter without moving either
        # Being; the opponent then makes a native approach decision.
        source.choose_run()
        view = source.advance_one_second()
        self.assertNotEqual(player.get_position(), opponent.get_position())
        self.assertIsNone(source._opponent_melee_action(candidate, opponent))
        self.assertEqual(view["time_seconds"], 1)
        self.assertEqual(source._opponent_decision(candidate)["kind"], "attack")
        # Attack only after the approach leaves a current Thrust opportunity.
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
        session, candidate, player, opponent, _ = create_session()
        session.choose_run()
        session.advance_one_second()
        view = session.advance_one_second()
        action = session._opponent_melee_action(candidate, opponent)
        self.assertIsInstance(action, MeleeStrike)
        action_id = action.id
        self.assertFalse(session._opponent_attack_preflight(candidate)[0])
        self.assertEqual(session._opponent_attack_refusal, "opponent_melee_already_pending")
        self.assertIsNone(session._schedule_opponent_attack(candidate))
        self.assertEqual(session._opponent_melee_action(candidate, opponent).id, action_id)
        self.assertTrue(view["advance_available"])
        old_position = player.get_position()
        session.choose_destination({"column": 0, "row": 0, "rate": "sprint",
                                   "facing_policy": "turn"})
        for _ in range(3):
            view = session.advance_one_second()
        self.assertEqual(view["opponent_melee_action"]["status"], "completed")
        self.assertEqual(view["opponent_melee_action"]["outcome"], "out_of_reach")
        self.assertNotEqual(player.get_position(), old_position)

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
        session.choose_run()
        view = session.advance_one_second()
        target = next(row for row in view["entities"] if row["category"] == "being")
        session.inspect_entity({"handle": target["handle"]})
        session.choose_melee_strike({"handle": target["handle"], "motion": "thrust"})
        source_action = session._player_melee_action(candidate, player)
        self.assertIsInstance(source_action, MeleeStrike)
        session.advance_one_second()
        opponent_action = session._opponent_melee_action(candidate, opponent)
        self.assertIsInstance(opponent_action, MeleeStrike)
        self.assertEqual(source_action.start_time, opponent_action.start_time)
        self.assertEqual(source_action.start_time, 1)
        for _ in range(3):
            session.advance_one_second()
        record = candidate.encounter.inspect_committed(5)
        self.assertIn(source_action.id, record.actions)
        self.assertIn(opponent_action.id, record.actions)
        self.assertEqual(session.public_view()["opponent_melee_action"]["status"], "completed")

    def test_approach_and_pending_thrust_restore_continue_deterministically(self):
        source, candidate, player, opponent, _ = create_session(seed=20261123)
        initial_player_position = player.get_position()
        initial_opponent_position = opponent.get_position()
        source.choose_run()
        source.advance_one_second()
        self.assertNotEqual(opponent.get_position(), initial_opponent_position)
        self.assertEqual(player.get_position(), initial_player_position)
        self.assertIsNone(source._opponent_melee_action(candidate, opponent))
        self.assertEqual(source._opponent_decision(candidate)["kind"], "move")

        approach_wire = source.save_encounter_bytes()
        process_reference = GeneratedArenaSession()
        process_reference.load_encounter_bytes(approach_wire)
        process_reference.advance_one_second()
        self.assertEqual(subprocess_advance_checkpoint(approach_wire, 1),
                         continuation_digest(native_continuation_state(process_reference)))
        restored = GeneratedArenaSession()
        with mock.patch("npcgen.api.arena_ready_being",
                        side_effect=AssertionError("Load must not regenerate either Being")):
            restored.load_encounter_bytes(approach_wire)
        restored_candidate = restored.active_candidate
        restored_player, restored_opponent = (
            part.native.being for part in restored_candidate.participants)

        for _ in range(3):
            left = source.advance_one_second()
            right = restored.advance_one_second()
            self.assertEqual(left["time_seconds"], right["time_seconds"])
            self.assertEqual(native_continuation_state(source),
                             native_continuation_state(restored))
            if source._opponent_melee_pending(candidate, opponent):
                break
        self.assertTrue(source._opponent_melee_pending(candidate, opponent))
        pending_wire = source.save_encounter_bytes()
        pending_restore = GeneratedArenaSession()
        with mock.patch("npcgen.api.arena_ready_being",
                        side_effect=AssertionError("Load must not regenerate a pending Thrust")):
            pending_restore.load_encounter_bytes(pending_wire)
        restored_action = pending_restore._opponent_melee_action(
            pending_restore.active_candidate,
            pending_restore.active_candidate.participants[1].native.being)
        self.assertEqual(restored_action.id,
                         source._opponent_melee_action(candidate, opponent).id)
        self.assertEqual(restored_action.instrument_id,
                         source._opponent_melee_action(candidate, opponent).instrument_id)
        for _ in range(3):
            source.advance_one_second()
            pending_restore.advance_one_second()
            self.assertEqual(native_continuation_state(source),
                             native_continuation_state(pending_restore))
        self.assertEqual(subprocess_advance_checkpoint(pending_wire, 3),
                         continuation_digest(native_continuation_state(source)))
        self.assertEqual(source.public_view()["opponent_melee_action"],
                         pending_restore.public_view()["opponent_melee_action"])
        self.assertEqual(source.public_view()["opponent_melee_action"]["status"], "completed")
        self.assertEqual(source._rng_cursor.state, pending_restore._rng_cursor.state)
        self.assertEqual(source.active_candidate.encounter.choice_state,
                         pending_restore.active_candidate.encounter.choice_state)
        self.assertEqual(source.active_candidate.encounter.finished_action_list,
                         pending_restore.active_candidate.encounter.finished_action_list)
        for left_part, right_part in zip(source.active_candidate.participants,
                                         pending_restore.active_candidate.participants):
            left_ledger = object.__getattribute__(left_part.native.being, "__dict__")["_arena_perception_ledger"]
            right_ledger = object.__getattribute__(right_part.native.being, "__dict__")["_arena_perception_ledger"]
            self.assertEqual(left_ledger.history, right_ledger.history)

    def test_player_movement_is_independent_during_approach_and_pending_thrust(self):
        session, candidate, player, opponent, _ = create_session(seed=20261123)
        session.choose_run()
        session.advance_one_second()
        before_player, before_opponent = player.get_position(), opponent.get_position()
        session.choose_destination({"column": 8, "row": 0, "rate": "walk",
                                   "facing_policy": "turn"})
        session.advance_one_second()
        self.assertNotEqual(player.get_position(), before_player)
        self.assertNotEqual(opponent.get_position(), before_opponent)

        # Separate case: retain U-012's close generated seed and move the
        # player only after the opponent's genuine Thrust has been accepted.
        moving, moved_candidate, moving_player, moving_opponent, _ = create_session()
        moving.choose_run()
        moving.advance_one_second()
        moving.advance_one_second()
        self.assertTrue(moving._opponent_melee_pending(moved_candidate, moving_opponent))
        old_position = moving_player.get_position()
        moving.choose_destination({"column": 0, "row": 0, "rate": "sprint",
                                  "facing_policy": "turn"})
        moving.advance_one_second()
        self.assertNotEqual(moving_player.get_position(), old_position)
        self.assertTrue(moving._opponent_melee_pending(moved_candidate, moving_opponent))

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
