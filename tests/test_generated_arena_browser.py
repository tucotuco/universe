"""HTTP and native-boundary tests for the generated Arena browser shell."""

import json
import io
import math
from pathlib import Path
import random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "examples"))
sys.path.insert(0, str(ROOT / "src"))

from activities import SpotAction
from arena_browser_session import ArenaBrowserRequestError, GeneratedArenaSession
from arena_web import ArenaSession, make_handler
from atomic_publication import RNGCursor
from attention_intent import accept_spot_attention
from arena_hex_map import HexAddress
from spatial.state import CartesianPosition
from hex_facing import nearest_facing


class TestGeneratedArenaBrowser(unittest.TestCase):
    def setUp(self):
        self.session = GeneratedArenaSession(root_seed_factory=lambda: 20261107)

    def request(self, path, payload=None, headers=None):
        handler_type = make_handler(self.session)
        handler = object.__new__(handler_type)
        handler.path = path
        handler.server = type("FakeServer", (), {"server_port": 8000})()
        handler.wfile = io.BytesIO()
        handler.headers = dict(headers or {})
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            handler.rfile = io.BytesIO(body)
            handler.headers["Content-Length"] = str(len(body))
            handler.headers.setdefault("Content-Type", "application/json")
        result = {}
        handler._send = lambda status, body, content_type="application/json; charset=utf-8": result.update(
            status=status, body=body, content_type=content_type)
        (handler.do_GET if payload is None else handler.do_POST)()
        body = result["body"]
        if result["content_type"].startswith("application/json"):
            body = json.loads(json.dumps(body) if type(body) is not str else body)
        return result["status"], body

    def enable_trace(self):
        import io
        stream = io.StringIO()
        self.session = GeneratedArenaSession(root_seed_factory=lambda: 20261107,
                                             trace_ui=True, trace_stream=stream)
        return stream

    def test_legacy_handler_still_selects_its_original_fixed_scenario_page(self):
        legacy_handler = object.__new__(make_handler(ArenaSession(die_roll=20)))
        legacy_handler.path = "/"
        legacy_handler.wfile = io.BytesIO()
        result = {}
        legacy_handler._send = lambda status, body, content_type="application/json; charset=utf-8": result.update(
            status=status, body=body, content_type=content_type)
        legacy_handler.do_GET()
        self.assertEqual(result["status"], 200)
        self.assertIn("GM / developer Reality view", result["body"])

    def test_empty_page_and_state_are_empty_with_real_disabled_load_affordance(self):
        status, page = self.request("/")
        self.assertEqual(status, 200)
        self.assertIn('id="load" disabled', page)
        self.assertIn('id="generate" disabled', page)
        self.assertIn('id="spot" disabled', page)
        self.assertIn('id="rate"', page)
        self.assertIn('id="facingPolicy"', page)
        self.assertIn('id="stop"', page)
        self.assertIn("/api/generated/destination", page)
        self.assertIn("/api/generated/stop", page)
        self.assertIn('hex_vertex_offsets_meters', page)
        self.assertIn('ctx.closePath()', page)
        self.assertNotIn("p.column+.5", page)
        status, state = self.request("/api/generated/state")
        self.assertEqual(status, 200)
        self.assertEqual(state["state"], "empty")
        self.assertFalse(state["load_available"])
        self.assertFalse(state["spot_available"])
        self.assertIsNone(self.session.active_candidate)
        self.assertEqual(self.request("/api/gm")[0], 404)

    def test_trace_off_is_quiet_and_diagnostic_route_is_unavailable(self):
        import io
        stream = io.StringIO()
        self.session = GeneratedArenaSession(root_seed_factory=lambda: 20261107,
                                             trace_stream=stream)
        status, page = self.request("/")
        self.assertEqual(status, 200)
        self.assertIn("const traceEnabled=false", page)
        self.assertEqual(self.request("/api/generated/trace", {
            "seq": 1, "event": "advance_clicked"})[0], 404)
        self.request("/api/generated/generate", {
            "starting_experience": "0", "width_cells": "5", "height_cells": "5"})
        self.assertEqual(stream.getvalue(), "")

    def test_trace_events_and_native_advance_report_authoritative_transitions(self):
        from concurrent.futures import ThreadPoolExecutor

        stream = self.enable_trace()
        status, page = self.request("/")
        self.assertEqual(status, 200)
        self.assertIn("const traceEnabled=true", page)
        # This source-level contract verifies that shipped handlers correlate a
        # fire-and-forget client event with the destination/advance request.
        self.assertIn("traceUI('canvas_hex_selected',cell)", page)
        self.assertIn("req('/api/generated/destination'", page)
        self.assertIn("traceUI('advance_clicked')", page)
        self.assertIn("req('/api/generated/advance',{seconds:1},seq)", page)
        self.assertIn("Already at that hex center", page)

        trace_empty = self.session.public_view()
        self.request("/api/generated/trace", {"seq": 1, "event": "generate_clicked"})
        self.request("/api/generated/trace", {
            "seq": 2, "event": "rate_selected", "rate": "walk"})
        self.request("/api/generated/trace", {
            "seq": 3, "event": "facing_policy_selected", "facing_policy": "turn"})
        self.assertEqual(self.session.public_view(), trace_empty)
        status, generated = self.request("/api/generated/generate", {
            "starting_experience": "0", "width_cells": "5", "height_cells": "5"},
            headers={"X-Arena-Client-Seq": "4"})
        self.assertEqual(status, 200)
        candidate = self.session.active_candidate
        player = candidate.participants[0].native.being
        hidden = candidate.participants[1].native.being
        start = player.get_position()
        rng_state = self.session._rng_cursor.state
        self.assertNotIn(hidden.id, json.dumps(generated))
        self.assertNotIn("client_seq", json.dumps(generated))
        self.assertNotIn("source_record", json.dumps(generated))

        # Clicking the occupied center is a real accepted no-op, not an active
        # plan; the browser now says so and keeps Advance disabled.
        current_cell = generated["player"]["cell"]
        self.request("/api/generated/trace", {
            "seq": 5, "event": "canvas_hex_selected", **current_cell})
        status, no_op = self.request("/api/generated/destination", {
            **current_cell, "rate": "walk", "facing_policy": "turn"},
            headers={"X-Arena-Client-Seq": "5"})
        self.assertEqual(status, 200)
        self.assertEqual(no_op["movement_outcome"], "already_at_destination")
        self.assertFalse(no_op["advance_available"])
        self.request("/api/generated/trace", {"seq": 6, "event": "advance_clicked"})
        status, refused = self.request("/api/generated/advance", {"seconds": 1},
                                       headers={"X-Arena-Client-Seq": "6"})
        self.assertEqual(status, 409)
        self.assertEqual(candidate.encounter.time, 0)

        for payload in (
            {"column": 99, "row": 0, "rate": "walk", "facing_policy": "turn"},
            {"column": "1", "row": 0, "rate": "walk", "facing_policy": "turn"},
        ):
            status, _ = self.request("/api/generated/destination", payload)
            self.assertEqual(status, 409)
        self.assertEqual(candidate.encounter.time, 0)
        self.assertIsNone(self.session.public_view()["movement_plan"])
        self.assertEqual(self.session._rng_cursor.state, rng_state)

        # Concurrent repeated clicks serialize under the session lock. Each
        # accepted destination is a plan replacement, not an interval commit.
        current = current_cell
        alternatives = [(column, row) for column in range(5) for row in range(5)
                        if (column, row) != (current["column"], current["row"])][:8]
        with ThreadPoolExecutor(max_workers=8) as workers:
            results = list(workers.map(lambda cell: self.request(
                "/api/generated/destination", {"column": cell[0], "row": cell[1],
                 "rate": "walk", "facing_policy": "turn"}), alternatives))
        self.assertTrue(all(status == 200 for status, _ in results))
        self.assertEqual(candidate.encounter.time, 0)
        plan = self.session.public_view()["movement_plan"]
        self.assertIsNotNone(plan)
        destination_cell = plan["destination_cell"]
        target = candidate.arena_map.layout.center_position(
            HexAddress(destination_cell["column"], destination_cell["row"]), z=start.z)

        # Injected native failure must log a rollback and leave time/position,
        # plan, ChoiceBook, and RNG untouched.
        from unittest.mock import patch
        before_view = self.session.public_view()
        before_choices = dict(candidate.encounter._choice_book._choices)
        self.request("/api/generated/trace", {"seq": 15, "event": "advance_clicked"})
        with patch.object(candidate.encounter, "step", side_effect=RuntimeError("injected step fault")):
            status, _ = self.request("/api/generated/advance", {"seconds": 1},
                                     headers={"X-Arena-Client-Seq": "15"})
        self.assertEqual(status, 409)
        self.assertEqual(candidate.encounter.time, 0)
        self.assertEqual(player.get_position(), start)
        self.assertEqual(self.session.public_view(), before_view)
        self.assertEqual(candidate.encounter._choice_book._choices, before_choices)
        self.assertEqual(self.session._rng_cursor.state, rng_state)

        self.request("/api/generated/trace", {"seq": 16, "event": "advance_clicked"})
        status, moving = self.request("/api/generated/advance", {"seconds": 1},
                                      headers={"X-Arena-Client-Seq": "16"})
        self.assertEqual(status, 200)
        self.assertEqual(moving["time_seconds"], 1)
        self.assertNotEqual(player.get_position(), start)
        self.assertNotIn(hidden.id, json.dumps(moving))
        while self.session.public_view()["movement_plan"] is not None:
            status, view = self.request("/api/generated/advance", {"seconds": 1})
            self.assertEqual(status, 200)
            self.assertNotIn(hidden.id, json.dumps(view))
        self.assertEqual(player.get_position(), target)
        self.assertIn("event=canvas_hex_selected", stream.getvalue())
        self.assertIn("event=rate_selected rate=walk", stream.getvalue())
        self.assertIn("action=generate status=accepted http=200 xp=0 map=5x5", stream.getvalue())
        self.assertIn("plan=already_at_destination", stream.getvalue())
        self.assertIn("movement=no_plan", stream.getvalue())
        self.assertIn("status=rolled_back", stream.getvalue())
        self.assertIn("reason=RuntimeError", stream.getvalue())
        self.assertIn("action=advance status=accepted http=200", stream.getvalue())
        self.assertIn("movement=arrival", stream.getvalue())
        self.assertEqual(self.session._rng_cursor.state, rng_state)
        for forbidden in (hidden.id, hidden.name, "source_record", "root_seed"):
            self.assertNotIn(forbidden, stream.getvalue())

    def test_trace_schema_rejects_arbitrary_fields_and_client_sequence_is_bounded(self):
        stream = self.enable_trace()
        before = self.session.public_view()
        for payload in (
            {"seq": 1, "event": "rate_selected", "rate": "walk", "name": "private"},
            {"seq": 2**40, "event": "advance_clicked"},
            {"seq": 2, "event": "rate_selected", "rate": "private-value"},
        ):
            status, _ = self.request("/api/generated/trace", payload)
            self.assertEqual(status, 409)
        self.assertEqual(self.session.public_view(), before)
        self.assertEqual(stream.getvalue(), "")

    def test_trace_diagnostic_route_refuses_nonlocal_origin(self):
        stream = self.enable_trace()
        status, _ = self.request("/api/generated/trace", {
            "seq": 1, "event": "advance_clicked"},
            headers={"Origin": "https://example.invalid"})
        self.assertEqual(status, 404)
        self.assertEqual(stream.getvalue(), "")

    def test_client_trace_has_a_per_second_rate_limit(self):
        import io
        from arena_ui_trace import ArenaUITerminalTrace
        now = [0.0]
        trace = ArenaUITerminalTrace(True, stream=io.StringIO(), clock=lambda: now[0])
        for seq in range(1, 31):
            trace.client_event({"seq": seq, "event": "advance_clicked"})
        with self.assertRaisesRegex(ValueError, "rate limit"):
            trace.client_event({"seq": 31, "event": "advance_clicked"})
        now[0] = 1.0
        self.assertEqual(trace.client_event({"seq": 32, "event": "advance_clicked"}),
                         {"accepted": True})

    def test_generate_returns_only_player_allowlist_and_rename_preserves_native_identity(self):
        status, state = self.request("/api/generated/generate", {
            "starting_experience": "0", "width_cells": "5", "height_cells": "5"})
        self.assertEqual(status, 200)
        self.assertEqual(state["state"], "active")
        self.assertEqual(state["time_seconds"], 0)
        self.assertEqual(state["map"]["width_cells"], 5)
        self.assertEqual(state["map"]["height_cells"], 5)
        self.assertEqual(state["map"]["orientation"], "flat_top_odd_column_north_offset")
        self.assertEqual(state["map"]["cell_size_meters"], 0.9144)
        self.assertEqual(state["map"]["column_row_ranges"], None)
        self.assertEqual(state["map"]["world_premise"], {
            "terrain": "Plains", "route": "Road", "terrain_multiplier": 1.0,
            "hampered_multiplier": 1.0, "unobstructed": True,
            "collision_adjudicated": False})
        self.assertTrue(state["movement_available"])
        self.assertFalse(state["spot_available"])
        candidate = self.session.active_candidate
        self.assertEqual(candidate.encounter.time, 0)
        self.assertEqual(len(candidate.participants), 2)
        self.assertNotEqual(candidate.participants[0].native.being.id,
                            candidate.participants[1].native.being.id)
        player_participant, hidden_participant = candidate.participants
        self.assertEqual(state["player"]["hex_facing"], player_participant.native.being.hex_facing)
        self.assertEqual(state["player"]["posture"], "standing")
        self.assertEqual(state["player"]["posture_source"],
                         "arena.initial-posture.v1/scenario")
        self.assertEqual(player_participant.native.being.posture, "standing")
        self.assertEqual(hidden_participant.native.being.posture, "standing")
        self.assertTrue(0 <= state["player"]["hex_facing"] < 12)
        self.assertEqual(state["player"]["cell"], {
            "column": player_participant.placement.column,
            "row": player_participant.placement.row})
        self.assertEqual(state["player"]["position_meters"], {
            "x": player_participant.native.being.get_position().x,
            "y": player_participant.native.being.get_position().y,
            "z": player_participant.native.being.get_position().z})
        self.assertEqual([p.native.being.get_experience() for p in candidate.participants], [0, 0])
        encoded = json.dumps(state).lower()
        for forbidden in ("source_sha256", "source_record", "native_id", "class", "level",
                          "experience", "awareness", "target_id", "action_id", "participants"):
            self.assertNotIn(forbidden, encoded)
        self.assertNotIn(hidden_participant.native.being.id, encoded)
        self.assertEqual(set(state["player"]),
                         {"name", "hex_facing", "posture", "posture_source",
                          "cell", "position_meters"})
        hidden_position = hidden_participant.native.being.get_position()
        hidden_position_payload = json.dumps({"x": hidden_position.x,
                                              "y": hidden_position.y,
                                              "z": hidden_position.z})
        self.assertNotIn(hidden_position_payload, encoded)
        _, generated_page = self.request("/")
        self.assertIn("movementStatus", generated_page)
        self.assertIn("s.player.hex_facing*Math.PI/6", generated_page)
        player = candidate.participants[0].native.being
        native_id, source_bytes = player.id, candidate.participants[0].native.source_record_bytes

        status, renamed = self.request("/api/generated/player-name", {"name": "Mira"})
        self.assertEqual(status, 200)
        self.assertEqual(renamed["player"]["name"], "Mira")
        self.assertEqual(player.id, native_id)
        self.assertEqual(player.name, "Mira")
        self.assertEqual(candidate.participants[0].native.source_record_bytes, source_bytes)
        status, named = self.request("/api/generated/encounter-name", {"name": "Trial"})
        self.assertEqual(status, 200)
        self.assertEqual(named["encounter_name"], "Trial")
        self.assertEqual(candidate.encounter.name, "Trial")

    def test_strict_server_inputs_and_failed_regeneration_leave_active_session_unchanged(self):
        for payload in (
            {"starting_experience": 0, "width_cells": "5", "height_cells": "5"},
            {"starting_experience": "0.0", "width_cells": "5", "height_cells": "5"},
            {"starting_experience": "0", "width_cells": "4", "height_cells": "5"},
            {"starting_experience": "0", "width_cells": "1001", "height_cells": "1000"},
        ):
            status, body = self.request("/api/generated/generate", payload)
            self.assertEqual(status, 409)
            self.assertIn("error", body)
        status, original = self.request("/api/generated/generate", {
            "starting_experience": "0", "width_cells": "5", "height_cells": "5"})
        self.assertEqual(status, 200)
        self.request("/api/generated/player-name", {"name": "Keep me"})
        active = self.session.active_candidate
        previous = self.session.public_view()
        status, body = self.request("/api/generated/generate", {
            "starting_experience": str(2**53), "width_cells": "5", "height_cells": "5"})
        self.assertEqual(status, 409)
        self.assertIn("npcgen", body["error"].lower())
        self.assertIs(self.session.active_candidate, active)
        self.assertEqual(self.session.public_view(), previous)
        self.assertEqual(active.encounter.time, original["time_seconds"])
        self.assertEqual(self.request("/api/load", {})[0], 404)

    def test_name_refusals_and_unavailable_routes_do_not_change_active_world(self):
        self.request("/api/generated/generate", {
            "starting_experience": "0", "width_cells": "5", "height_cells": "5"})
        before = self.session.public_view()
        for path, body in (("/api/generated/player-name", {"name": "  "}),
                            ("/api/generated/player-name", {"name": "x" * 41}),
                            ("/api/generated/encounter-name", {"name": "ok", "extra": 1}),
                            ("/api/generated/spot", {"operation": "spot"}),
                            ("/api/generated/advance", {"seconds": 1}),
                            ("/api/spot", {"operation": "ari_spots_bex"}),
                            ("/api/advance", {"seconds": 1})):
            status, _ = self.request(path, body)
            self.assertNotEqual(status, 200)
            self.assertEqual(self.session.public_view(), before)

    def test_native_invalid_first_choice_leaves_unstarted_arena_unchanged(self):
        from activities import RunAction
        from action_choice import ChoiceRejected

        self.session.generate({"starting_experience": "0", "width_cells": "5", "height_cells": "5"})
        candidate = self.session.active_candidate
        encounter = candidate.encounter
        player = candidate.participants[0].native.being
        # The declaration is otherwise a valid Run Choice but collides with the
        # already-registered Encounter Event identity during native preflight.
        action = RunAction(candidate.universe, player.id, 0, 1, 0.1,
                          experience=0, id=encounter.id)
        before_history = dict(candidate.universe.event_history)
        before_view = self.session.public_view()
        before_revision = encounter._choice_book.revision
        before_counter = encounter._choice_book._counter
        rng_state = self.session._rng_cursor.state
        with self.assertRaises(ChoiceRejected):
            encounter.activate_arena_for_player_action(
                player.id, action, rng_owner=self.session._rng_cursor)
        self.assertFalse(encounter.initiated)
        self.assertIsNone(encounter.arena_activation)
        self.assertEqual(encounter.time, 0)
        self.assertEqual(candidate.universe.event_history, before_history)
        self.assertEqual(encounter.pending_action_list, [])
        self.assertEqual(encounter._choice_book._choices, {})
        self.assertEqual(encounter._choice_book._counter, before_counter)
        self.assertEqual(encounter._choice_book._drafts, {})
        self.assertEqual(encounter._choice_book._tokens, {})
        self.assertEqual(encounter._choice_book.revision, before_revision)
        self.assertEqual(self.session._rng_cursor.state, rng_state)
        self.assertEqual(self.session.public_view(), before_view)

    def test_activation_rolls_back_if_native_mode_selection_aborts_after_publication(self):
        from activities import RunAction
        from unittest.mock import patch

        self.session.generate({"starting_experience": "0", "width_cells": "5", "height_cells": "5"})
        candidate = self.session.active_candidate
        encounter = candidate.encounter
        player = candidate.participants[0].native.being
        action = RunAction(candidate.universe, player.id, 0, 1, 0.1, experience=0)
        before_history = dict(candidate.universe.event_history)
        before_view = self.session.public_view()
        before_revision = encounter._choice_book.revision
        before_counter = encounter._choice_book._counter
        rng_state = self.session._rng_cursor.state
        with patch("transactional_progression._enable_transactional_progression_owned",
                   side_effect=RuntimeError("injected pre-commit abort")):
            with self.assertRaises(RuntimeError):
                encounter.activate_arena_for_player_action(
                    player.id, action, rng_owner=self.session._rng_cursor)
        self.assertFalse(encounter.initiated)
        self.assertIsNone(encounter.arena_activation)
        self.assertEqual(encounter.time, 0)
        self.assertEqual(candidate.universe.event_history, before_history)
        self.assertEqual(encounter.pending_action_list, [])
        self.assertEqual(encounter._choice_book._choices, {})
        self.assertEqual(encounter._choice_book._registered, {})
        self.assertEqual(encounter._choice_book._counter, before_counter)
        self.assertEqual(encounter._choice_book._drafts, {})
        self.assertEqual(encounter._choice_book._tokens, {})
        self.assertEqual(encounter._choice_book.revision, before_revision)
        self.assertEqual(self.session._rng_cursor.state, rng_state)
        self.assertEqual(self.session.public_view(), before_view)

    def test_movement_activation_rolls_back_without_choice_or_rng_changes(self):
        from unittest.mock import patch

        self.session.generate({"starting_experience": "0", "width_cells": "5", "height_cells": "5"})
        candidate = self.session.active_candidate
        encounter = candidate.encounter
        player = candidate.participants[0].native.being
        before_view = self.session.public_view()
        before_history = dict(candidate.universe.event_history)
        before_choices = dict(encounter._choice_book._choices)
        before_revision = encounter._choice_book.revision
        rng_state = self.session._rng_cursor.state
        with patch("transactional_progression._enable_transactional_progression_owned",
                   side_effect=RuntimeError("injected pre-commit abort")):
            with self.assertRaises(ArenaBrowserRequestError):
                self.session.choose_destination({"column": 4, "row": 4,
                    "rate": "walk", "facing_policy": "turn"})
        self.assertFalse(encounter.initiated)
        self.assertIsNone(encounter.arena_movement_activation)
        self.assertIsNone(encounter.arena_activation)
        self.assertIsNone(encounter.initiation)
        self.assertEqual(encounter.time, 0)
        self.assertEqual(candidate.universe.event_history, before_history)
        self.assertEqual(encounter._choice_book._choices, before_choices)
        self.assertEqual(encounter._choice_book.revision, before_revision)
        self.assertEqual(self.session._rng_cursor.state, rng_state)
        self.assertEqual(self.session.public_view(), before_view)

    def test_generated_run_choice_activates_then_commits_one_native_second(self):
        self.session.generate({"starting_experience": "0", "width_cells": "5", "height_cells": "5"})
        candidate = self.session.active_candidate
        encounter = candidate.encounter
        player, hidden = candidate.participants
        start = player.native.being.get_position()

        status, accepted = self.request("/api/generated/run", {})
        self.assertEqual(status, 200)
        self.assertEqual(accepted["time_seconds"], 0)
        self.assertTrue(accepted["advance_available"])
        self.assertEqual(encounter.progression_mode, "transactional")
        self.assertTrue(encounter.initiated)
        activation = encounter.arena_activation
        self.assertEqual(activation.actor_id, player.native.being.id)
        self.assertEqual(activation.time, 0)
        self.assertEqual(activation.activation_kind, "first_player_choice")
        self.assertFalse(hasattr(activation, "target_id"))
        self.assertIsNone(encounter.initiation)
        self.assertEqual(encounter.aware_beings(player.native.being.id), [])
        encoded = json.dumps(accepted).lower()
        for forbidden in (hidden.native.being.id.lower(), "target_id", "activation", "source_record"):
            self.assertNotIn(forbidden, encoded)

        status, advanced = self.request("/api/generated/advance", {"seconds": 1})
        self.assertEqual(status, 200)
        self.assertEqual(advanced["time_seconds"], 1)
        self.assertEqual(advanced["player"]["cell"], accepted["player"]["cell"])
        self.assertEqual(advanced["player_action"],
                         {"name": "Run", "status": "completed", "outcome": "no_movement"})
        self.assertEqual(advanced["player"]["position_meters"],
                         {"x": start.x, "y": start.y, "z": start.z})
        action_id = encounter._choice_book._choices[activation.choice_id].view.action_ids[0]
        native_result = encounter.inspect_committed(1).action(action_id)
        self.assertEqual(native_result.facts.outcome, "no_movement")
        self.assertEqual(encounter.time, 1)
        self.assertEqual(encounter.aware_beings(player.native.being.id), [])
        self.assertNotIn(hidden.native.being.id, json.dumps(advanced))
        before = self.session.public_view()
        self.assertNotEqual(self.request("/api/generated/advance", {"seconds": 1})[0], 200)
        self.assertEqual(self.session.public_view(), before)

    def test_destination_movement_activates_without_action_and_arrives_from_native_commits(self):
        self.request("/api/generated/generate", {
            "starting_experience": "0", "width_cells": "5", "height_cells": "5"})
        candidate = self.session.active_candidate
        encounter = candidate.encounter
        player, hidden = candidate.participants
        being = player.native.being
        start = being.get_position()
        layout = candidate.arena_map.layout
        addresses = [HexAddress(column, row)
                     for column in range(candidate.arena_map.width_cells)
                     for row in range(candidate.arena_map.height_cells)]
        target_address = max(addresses, key=lambda address: math.dist(
            start.as_tuple(), layout.center_position(address, z=start.z).as_tuple()))
        target = layout.center_position(target_address, z=start.z)
        self.assertGreater(math.dist(start.as_tuple(), target.as_tuple()), 0)
        expected_facing = nearest_facing((target.x - start.x, target.y - start.y,
                                           target.z - start.z))
        before_history = dict(candidate.universe.event_history)
        before_choices = dict(encounter._choice_book._choices)
        before_awareness = (encounter.aware_beings(being.id),
                            encounter.aware_beings(hidden.native.being.id))
        before_rng = self.session._rng_cursor.state
        before_global_rng = random.getstate()

        status, selected = self.request("/api/generated/destination", {
            "column": target_address.column, "row": target_address.row,
            "rate": "walk", "facing_policy": "turn"})
        self.assertEqual(status, 200)
        self.assertEqual(encounter.time, 0)
        self.assertTrue(encounter.initiated)
        self.assertEqual(encounter.progression_mode, "transactional")
        activation = encounter.arena_movement_activation
        self.assertEqual(activation.actor_id, being.id)
        self.assertEqual(activation.movement_decision_id, "arena-movement-1")
        self.assertEqual(activation.time, 0)
        self.assertIsNone(encounter.arena_activation)
        self.assertIsNone(encounter.initiation)
        self.assertEqual(candidate.universe.event_history, before_history)
        self.assertEqual(encounter._choice_book._choices, before_choices)
        self.assertEqual(before_awareness, (encounter.aware_beings(being.id),
                                           encounter.aware_beings(hidden.native.being.id)))
        self.assertTrue(selected["advance_available"])
        self.assertEqual(selected["movement_plan"]["rate"], "walk")
        self.assertNotIn(hidden.native.being.id, json.dumps(selected))

        committed = []
        while self.session.public_view()["movement_plan"] is not None:
            before = being.get_position()
            status, view = self.request("/api/generated/advance", {"seconds": 1})
            self.assertEqual(status, 200)
            after = being.get_position()
            committed.append(after)
            self.assertEqual(view["player"]["position_meters"],
                             {"x": after.x, "y": after.y, "z": after.z})
            self.assertGreater((after.x - before.x) ** 2 + (after.y - before.y) ** 2, 0)
            self.assertEqual(view["time_seconds"], encounter.time)
            self.assertNotIn(hidden.native.being.id, json.dumps(view))
            if len(committed) == 1:
                self.assertEqual(being.hex_facing, expected_facing)
        final = self.session.public_view()
        self.assertGreater(len(committed), 1)
        self.assertEqual(being.get_position(), target)
        self.assertEqual(final["player"]["position_meters"],
                         {"x": target.x, "y": target.y, "z": target.z})
        self.assertEqual(final["player"]["cell"], {
            "column": target_address.column, "row": target_address.row})
        self.assertEqual(final["movement_outcome"], "arrived")
        self.assertIsNone(final["movement_plan"])
        self.assertEqual(encounter.aware_beings(being.id), [])
        self.assertEqual(encounter.aware_beings(hidden.native.being.id), [])
        self.assertEqual(encounter._choice_book._choices, {})
        self.assertEqual(self.session._rng_cursor.state, before_rng)
        self.assertEqual(random.getstate(), before_global_rng)

    def test_destination_can_be_changed_or_stopped_at_a_committed_boundary(self):
        self.request("/api/generated/generate", {
            "starting_experience": "0", "width_cells": "5", "height_cells": "5"})
        candidate = self.session.active_candidate
        being = candidate.participants[0].native.being
        start = candidate.arena_map.layout.center_position(HexAddress(0, 0))
        being.set_position(start)
        being.set_hex_facing(0)
        self.request("/api/generated/destination", {
            "column": 4, "row": 4, "rate": "walk", "facing_policy": "maintain"})
        self.request("/api/generated/advance", {"seconds": 1})
        committed = being.get_position()
        status, changed = self.request("/api/generated/destination", {
            "column": 0, "row": 4, "rate": "walk", "facing_policy": "turn"})
        self.assertEqual(status, 200)
        self.assertEqual(being.get_position(), committed)
        self.assertEqual(changed["movement_plan"]["destination_cell"], {"column": 0, "row": 4})
        self.assertEqual(changed["movement_plan"]["facing_policy"], "turn")
        self.assertEqual(changed["time_seconds"], 1)
        status, stopped = self.request("/api/generated/stop", {})
        self.assertEqual(status, 200)
        self.assertEqual(being.get_position(), committed)
        self.assertIsNone(stopped["movement_plan"])
        self.assertEqual(stopped["movement_outcome"], "stopped")
        before = self.session.public_view()
        self.assertNotEqual(self.request("/api/generated/advance", {"seconds": 1})[0], 200)
        self.assertEqual(self.session.public_view(), before)

    def test_unknown_posture_rejects_destination_without_activation_or_publication(self):
        self.request("/api/generated/generate", {
            "starting_experience": "0", "width_cells": "5", "height_cells": "5"})
        candidate = self.session.active_candidate
        encounter = candidate.encounter
        being = candidate.participants[0].native.being
        being.set_posture(None)
        before = self.session.public_view()
        with self.assertRaises(ArenaBrowserRequestError):
            self.session.choose_destination({"column": 4, "row": 4,
                                             "rate": "walk", "facing_policy": "turn"})
        self.assertEqual(self.session.public_view(), before)
        self.assertFalse(encounter.initiated)
        self.assertIsNone(encounter.arena_movement_activation)
        self.assertEqual(encounter.time, 0)
        self.assertEqual(encounter._choice_book._choices, {})

    def test_native_spot_proof_fails_closed_without_generated_geometry(self):
        self.session.generate({"starting_experience": "0", "width_cells": "5", "height_cells": "5"})
        candidate = self.session.active_candidate
        encounter = candidate.encounter
        player, hidden = candidate.participants
        self.assertIsNone(player.native.being.geometry)
        self.assertIsNone(hidden.native.being.geometry)
        # This explicit flag isolates the geometry gate in this test. It is
        # not a generated-Arena activation path or an initiation proof.
        encounter.initiated = True
        cursor = RNGCursor(random.Random(17).getstate())
        encounter.enable_transactional_progression(quiescent=True, rng_owner=cursor)
        intent = accept_spot_attention(encounter, player.native.being.id)
        self.assertTrue(intent.accepted)
        action = next(member.action for choice in encounter._choice_book._choices.values()
                      for member in choice.members if type(member.action) is SpotAction)
        self.assertNotIn(hidden.native.being.id, repr(intent))
        self.assertEqual((action.actor_id, action.target_id),
                         (player.native.being.id, hidden.native.being.id))
        for expected_time in range(1, 7):
            encounter.step(1)
            self.assertEqual(encounter.time, expected_time)
        result = encounter.inspect_committed(6).action(action.id)
        self.assertEqual(result.facts.outcome, "unmodeled_target")
        self.assertEqual(encounter.aware_beings(player.native.being.id), [])
        self.assertFalse(any(type(effect.effect).__name__ == "AwarenessEffect"
                             for effect in result.effects))
        self.assertIsNone(hidden.native.being.geometry)


if __name__ == "__main__":
    unittest.main()
