"""HTTP and native-boundary tests for the generated Arena browser shell."""

import json
import io
import math
from pathlib import Path
import random
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "examples"))
sys.path.insert(0, str(ROOT / "src"))

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
        self.assertIn("req('/api/generated/advance',{seconds:1},sequence)", page)
        self.assertIn("/api/generated/rename-entity", page)
        self.assertIn("const sequence=traceUI('rename_entity_clicked')", page)
        self.assertIn("b.textContent=", page)
        self.assertNotIn("innerHTML", page)
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

    def test_shipped_option_handlers_replace_active_plan_and_serialize_advance(self):
        _, page = self.request("/")
        self.assertIn("function serializeMutation(operation)", page)
        self.assertIn("function optionChanged(event,detail)", page)
        self.assertIn("updatePlanFromSelection(sequence,rate,policy)", page)
        self.assertIn("server accepted ${plan.rate}/${plan.facing_policy}", page)
        self.assertIn("selected ${selectedRate}/${selectedPolicy}", page)
        self.assertIn("Movement plan accepted: ${state.movement_plan.rate}/${state.movement_plan.facing_policy}", page)
        self.assertIn("await serializeMutation(async()=>{try{const state=await req('/api/generated/destination'", page)
        self.assertIn("serializeMutation(async()=>{if(planUpdateFailure)", page)
        self.assertIn("req('/api/generated/advance',{seconds:1},sequence)", page)

    @unittest.skipUnless(sys.platform == "darwin" and shutil.which("swift"),
                         "JavaScriptCore via Swift is available on macOS only")
    def test_actual_shipped_javascript_handlers_order_sprint_update_before_immediate_advance(self):
        stream = self.enable_trace()
        loadout_profile = json.loads((ROOT / "tests/fixtures/arena/test_ground_loadout_profile.json").read_text())
        self.session = GeneratedArenaSession(root_seed_factory=lambda: 20261107,
            trace_ui=True, trace_stream=stream, ground_loadout_profile=loadout_profile)
        _, page = self.request("/")
        self.assertNotIn('id="characterPanel"', page)
        self.assertIn('id="entityDialog"', page)
        self.assertIn('id="characterButton"', page)
        state = self.session.generate({
            "starting_experience": "10000", "width_cells": "10", "height_cells": "5"})
        object_view = next(row for row in state["entities"]
                           if row["category"] == "object" and row["type"] == "Dagger")
        target = HexAddress(object_view["cell"]["column"], object_view["cell"]["row"])
        self.session.rename_entity({"handle": object_view["handle"], "name": "Renamed Dagger"})
        self.session.choose_destination({"column": target.column, "row": target.row,
                                         "rate": "sprint", "facing_policy": "turn"})
        for _ in range(100):
            if self.session.public_view()["movement_plan"] is None:
                break
            self.session.advance_one_second()
        self.assertIsNone(self.session.public_view()["movement_plan"])
        self.session.inspect_entity({"handle": object_view["handle"]})
        self.session.choose_pickup({"handle": object_view["handle"]})
        self.session.advance_one_second()
        picked_up_view = self.session.public_view()
        self.assertEqual(picked_up_view["character"]["inventory"]["items"][0]["name"],
                         "Renamed Dagger")

        with tempfile.TemporaryDirectory(prefix="arena-browser-js-") as temp:
            page_path = Path(temp) / "page.html"
            state_path = Path(temp) / "initial-state.json"
            cell_path = Path(temp) / "target-cell.json"
            picked_up_path = Path(temp) / "picked-up-view.json"
            page_path.write_text(page, encoding="utf-8")
            state_path.write_text(json.dumps(state), encoding="utf-8")
            cell_path.write_text(json.dumps({"column": target.column, "row": target.row}),
                                 encoding="utf-8")
            picked_up_path.write_text(json.dumps(picked_up_view), encoding="utf-8")
            module_cache = Path(tempfile.gettempdir()) / "universe-arena-jsc-module-cache"
            module_cache.mkdir(parents=True, exist_ok=True)
            harness = ROOT / "tests" / "arena_browser_js_harness.swift"
            run = subprocess.run(
                [shutil.which("swift"), "-module-cache-path", str(module_cache), str(harness),
                 str(page_path), str(state_path), str(cell_path), str(picked_up_path)],
                check=True, capture_output=True, text=True, timeout=60)
        result = json.loads(run.stdout)
        movement_requests = [call for call in result["calls"]
                             if call["path"] in ("/api/generated/destination", "/api/generated/advance")]
        self.assertEqual([call["path"] for call in movement_requests], [
            "/api/generated/destination", "/api/generated/destination",
            "/api/generated/destination", "/api/generated/advance",
            "/api/generated/advance"])
        self.assertEqual([call["body"]["rate"] for call in movement_requests[:3]],
                         ["sprint", "walk", "sprint"])
        self.assertIn("Dagger", result["entityDetails"])
        self.assertIn("Pick up", result["pickupStatus"])
        self.assertIn("/api/generated/inspect", [call["path"] for call in result["calls"]])
        self.assertIn("/api/generated/pickup", [call["path"] for call in result["calls"]])
        self.assertIn("/api/generated/rename-entity", [call["path"] for call in result["calls"]])
        rename_call = next(call for call in result["calls"] if call["path"] == "/api/generated/rename-entity")
        self.assertEqual(rename_call["body"]["name"], "Renamed Dagger")
        self.assertNotIn("native_id", json.dumps(rename_call["body"]))
        self.assertEqual(result["finalEntity"]["name"], "Renamed Dagger")
        self.assertEqual(result["finalEntity"]["present_state"], "carried")
        self.assertIn("Renamed Dagger", result["entityDetails"])
        self.assertIn("carried", result["entityDetails"])
        inventory_output = " ".join(result["characterInventory"])
        self.assertIn("Renamed Dagger", inventory_output)
        self.assertIn("carried; not readied", inventory_output)
        character_text = json.dumps(result["characterSummary"])
        for label in ("Fitness", "Total native XP", "Hit points", "Skills and recorded practice",
                      "Position and movement", "Age is not represented", "Class XP"):
            self.assertIn(label, character_text)
        self.assertIn("Represented carried weight", character_text)
        for call in movement_requests[:3]:
            self.assertEqual(call["body"]["facing_policy"], "turn")
            self.assertEqual(call["body"]["column"], target.column)
            self.assertEqual(call["body"]["row"], target.row)
        self.assertEqual(int(movement_requests[3]["headers"]["X-Arena-Client-Seq"]),
                         int(movement_requests[2]["headers"]["X-Arena-Client-Seq"]) + 1)
        self.assertLess(result["calls"].index(movement_requests[2]),
                        result["calls"].index(movement_requests[3]))
        self.assertEqual(result["plan"]["rate"], "sprint")
        self.assertIn("Destination reached", result["status"])
        self.assertEqual(result["time"], 2)
        self.assertEqual(result["error"], "One native Encounter second committed.")
        self.assertTrue(any(label.lower().startswith("small shield · ground")
                            for label in result["entityLabels"]))
        self.assertFalse(any("small shield · small shield" in label.lower()
                             for label in result["entityLabels"]))

    def test_destination_then_sprint_updates_accepted_plan_before_native_step(self):
        stream = self.enable_trace()
        self.request("/api/generated/generate", {
            "starting_experience": "10000", "width_cells": "10", "height_cells": "5"})
        candidate = self.session.active_candidate
        encounter = candidate.encounter
        player, hidden = candidate.participants
        being = player.native.being
        start = being.get_position()
        layout = candidate.arena_map.layout
        address = max(
            (HexAddress(column, row)
             for column in range(candidate.arena_map.width_cells)
             for row in range(candidate.arena_map.height_cells)),
            key=lambda cell: math.dist(start.as_tuple(), layout.center_position(cell, z=start.z).as_tuple()))
        before_history = dict(candidate.universe.event_history)
        before_choices = dict(encounter._choice_book._choices)
        before_awareness = (encounter.aware_beings(being.id),
                            encounter.aware_beings(hidden.native.being.id))
        before_rng = self.session._rng_cursor.state

        self.request("/api/generated/trace", {"seq": 1, "event": "canvas_hex_selected",
                     "column": address.column, "row": address.row})
        status, walk = self.request("/api/generated/destination", {
            "column": address.column, "row": address.row,
            "rate": "walk", "facing_policy": "turn"},
            headers={"X-Arena-Client-Seq": "1"})
        self.assertEqual(status, 200)
        self.assertEqual(walk["movement_plan"]["rate"], "walk")
        self.request("/api/generated/trace", {"seq": 2, "event": "rate_selected", "rate": "sprint"})
        status, sprint = self.request("/api/generated/destination", {
            **walk["movement_plan"]["destination_cell"],
            "rate": "sprint", "facing_policy": "turn"},
            headers={"X-Arena-Client-Seq": "2"})
        self.assertEqual(status, 200)
        self.assertEqual(sprint["movement_plan"]["rate"], "sprint")
        self.assertEqual(sprint["movement_plan"]["destination_cell"],
                         {"column": address.column, "row": address.row})
        self.assertEqual(sprint["time_seconds"], 0)
        self.assertEqual(being.get_position(), start)
        self.assertEqual(candidate.universe.event_history, before_history)
        self.assertEqual(encounter._choice_book._choices, before_choices)
        self.assertEqual(before_awareness, (encounter.aware_beings(being.id),
                                           encounter.aware_beings(hidden.native.being.id)))
        self.assertEqual(self.session._rng_cursor.state, before_rng)
        self.assertNotIn(hidden.native.being.id, json.dumps(sprint))

        self.request("/api/generated/trace", {"seq": 3, "event": "advance_clicked"})
        status, advanced = self.request("/api/generated/advance", {"seconds": 1},
                                        headers={"X-Arena-Client-Seq": "3"})
        self.assertEqual(status, 200)
        self.assertEqual(advanced["time_seconds"], 1)
        self.assertGreater(math.dist(start.as_tuple(), being.get_position().as_tuple()), 0.9144)
        self.assertIn("event=rate_selected rate=sprint", stream.getvalue())
        self.assertIn("client_seq=2 action=destination status=accepted http=200", stream.getvalue())
        self.assertIn("rate=sprint policy=turn plan=accepted", stream.getvalue())
        self.assertIn("status=committed time=0->1", stream.getvalue())
        self.assertIn("rate=sprint,policy=turn", stream.getvalue())
        self.assertNotIn(hidden.native.being.id, stream.getvalue())
        self.assertNotIn("seed=", stream.getvalue())

    def test_sprint_before_destination_and_rapid_policy_rate_edits_use_latest_plan(self):
        stream = self.enable_trace()
        self.request("/api/generated/generate", {
            "starting_experience": "10000", "width_cells": "10", "height_cells": "5"})
        candidate = self.session.active_candidate
        being = candidate.participants[0].native.being
        start = being.get_position()
        layout = candidate.arena_map.layout
        address = max(
            (HexAddress(column, row)
             for column in range(candidate.arena_map.width_cells)
             for row in range(candidate.arena_map.height_cells)),
            key=lambda cell: math.dist(start.as_tuple(), layout.center_position(cell, z=start.z).as_tuple()))
        self.request("/api/generated/trace", {"seq": 1, "event": "rate_selected", "rate": "sprint"})
        self.request("/api/generated/trace", {"seq": 2, "event": "facing_policy_selected",
                     "facing_policy": "turn"})
        status, selected = self.request("/api/generated/destination", {
            "column": address.column, "row": address.row,
            "rate": "sprint", "facing_policy": "turn"},
            headers={"X-Arena-Client-Seq": "3"})
        self.assertEqual(status, 200)
        self.assertEqual(selected["movement_plan"]["rate"], "sprint")

        # Serialized selector edits followed immediately by Advance represent
        # the browser queue's required causal order.
        self.request("/api/generated/trace", {"seq": 4, "event": "facing_policy_selected",
                     "facing_policy": "maintain"})
        status, maintained = self.request("/api/generated/destination", {
            **selected["movement_plan"]["destination_cell"],
            "rate": "sprint", "facing_policy": "maintain"},
            headers={"X-Arena-Client-Seq": "4"})
        self.assertEqual(status, 200)
        self.assertEqual(maintained["movement_plan"]["facing_policy"], "maintain")
        self.request("/api/generated/trace", {"seq": 5, "event": "rate_selected", "rate": "jog"})
        status, jog = self.request("/api/generated/destination", {
            **maintained["movement_plan"]["destination_cell"],
            "rate": "jog", "facing_policy": "maintain"},
            headers={"X-Arena-Client-Seq": "5"})
        self.assertEqual(status, 200)
        self.assertEqual(jog["movement_plan"]["rate"], "jog")
        self.request("/api/generated/trace", {"seq": 6, "event": "rate_selected", "rate": "sprint"})
        status, sprint = self.request("/api/generated/destination", {
            **jog["movement_plan"]["destination_cell"],
            "rate": "sprint", "facing_policy": "maintain"},
            headers={"X-Arena-Client-Seq": "6"})
        self.assertEqual(status, 200)
        self.assertEqual(sprint["movement_plan"]["rate"], "sprint")
        self.assertEqual(sprint["movement_plan"]["facing_policy"], "maintain")
        self.request("/api/generated/trace", {"seq": 7, "event": "advance_clicked"})
        status, advanced = self.request("/api/generated/advance", {"seconds": 1},
                                        headers={"X-Arena-Client-Seq": "7"})
        self.assertEqual(status, 200)
        self.assertEqual(advanced["time_seconds"], 1)
        self.assertIn("rate=sprint,policy=maintain", stream.getvalue())

    def test_invalid_rate_update_keeps_previous_server_plan(self):
        self.request("/api/generated/generate", {
            "starting_experience": "0", "width_cells": "5", "height_cells": "5"})
        candidate = self.session.active_candidate
        start_cell = candidate.arena_map.layout.cell_at_position(
            candidate.participants[0].native.being.get_position())
        destination = next(HexAddress(column, row)
            for column in range(candidate.arena_map.width_cells)
            for row in range(candidate.arena_map.height_cells)
            if HexAddress(column, row) != start_cell)
        _, accepted = self.request("/api/generated/destination", {
            "column": destination.column, "row": destination.row,
            "rate": "walk", "facing_policy": "turn"})
        before = self.session.public_view()
        status, _ = self.request("/api/generated/destination", {
            "column": destination.column, "row": destination.row,
            "rate": "sprint-invalid", "facing_policy": "maintain"})
        self.assertEqual(status, 409)
        after = self.session.public_view()
        self.assertEqual(after, before)
        self.assertEqual(after["movement_plan"]["rate"], accepted["movement_plan"]["rate"])
        self.assertEqual(after["movement_plan"]["facing_policy"],
                         accepted["movement_plan"]["facing_policy"])

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

    def test_character_sheet_trace_event_contains_no_private_details(self):
        stream = self.enable_trace()
        status, result = self.request("/api/generated/trace", {
            "seq": 1, "event": "character_sheet_opened"})
        self.assertEqual(status, 200)
        self.assertEqual(result, {"accepted": True})
        self.assertIn("event=character_sheet_opened", stream.getvalue())
        self.assertNotIn("name", stream.getvalue())

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
        player_participant, other_participant = candidate.participants
        self.assertEqual(state["player"]["hex_facing"], player_participant.native.being.hex_facing)
        self.assertEqual(state["player"]["posture"], "standing")
        self.assertEqual(state["player"]["posture_source"],
                         "arena.initial-posture.v1/scenario")
        self.assertEqual(player_participant.native.being.posture, "standing")
        self.assertEqual(other_participant.native.being.posture, "standing")
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
        for forbidden in ("source_sha256", "source_record", "native_id", "awareness",
                          "target_id", "action_id", "participants"):
            self.assertNotIn(forbidden, encoded)
        self.assertIsNone(state["character"]["identity"]["class_levels"])
        self.assertIsNone(state["character"]["experience"]["class_allocation"])
        self.assertEqual(state["character"]["experience"]["total"], 0)
        self.assertNotIn(other_participant.native.being.id, encoded)
        self.assertEqual(len(state["entities"]), 1)
        self.assertEqual(state["entities"][0]["category"], "being")
        self.assertEqual(state["entities"][0]["type"], "Being")
        self.assertEqual(state["entities"][0]["name"], other_participant.native.being.name)
        hidden_position = other_participant.native.being.get_position()
        self.assertEqual(state["entities"][0]["position_meters"], {
            "x": hidden_position.x, "y": hidden_position.y, "z": hidden_position.z})
        ledgers = [participant.native.being._arena_perception_ledger
                   for participant in candidate.participants]
        self.assertIsNot(ledgers[0], ledgers[1])
        self.assertIsNot(ledgers[0]._current, ledgers[1]._current)
        self.assertIsNot(ledgers[0].history[0], ledgers[1].history[0])
        self.assertEqual(candidate.encounter.time, 0)
        self.assertEqual(candidate.encounter._choice_book._choices, {})
        self.assertEqual(set(state["player"]),
                         {"name", "hex_facing", "posture", "posture_source",
                          "cell", "position_meters"})
        hidden_position_payload = json.dumps({"x": hidden_position.x,
                                              "y": hidden_position.y,
                                              "z": hidden_position.z})
        self.assertIn(hidden_position_payload, encoded)
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

    def test_http_visible_object_selection_pickup_and_custody_use_native_action(self):
        trace_stream = io.StringIO()
        self.session = GeneratedArenaSession(root_seed_factory=lambda: 20261107,
            trace_ui=True, trace_stream=trace_stream,
            ground_item_descriptions=[{"source_item_id": "http-dagger", "category": "weapon",
                "native_type_key": "Dagger", "quantity": 1, "ordinary": True,
                "magical": False, "mechanics": None, "origin": "http-test.v1"}])
        status, state = self.request("/api/generated/generate", {
            "starting_experience": "10000", "width_cells": "10", "height_cells": "5"})
        self.assertEqual(status, 200)
        target = next(row for row in state["entities"] if row["type"] == "Dagger")
        candidate = self.session.active_candidate
        placement = next(row for row in candidate.ground_objects if row.native_type_key == "Dagger")
        native = candidate.universe.get_object_by_id(placement.native_object_id)
        player = candidate.participants[0].native.being
        character = state["character"]
        self.assertEqual(character["identity"]["display_name"], state["player"]["name"])
        self.assertEqual(character["identity"]["native_type"], player.current.obj_type)
        self.assertEqual(character["identity"]["race"], player.current.race)
        self.assertIsNone(character["identity"]["age"])
        self.assertIsNone(character["identity"]["class_levels"])
        self.assertEqual(character["identity"]["stature_inches"], player.current.length)
        self.assertEqual(character["identity"]["body_weight_pounds"], player.current.weight)
        self.assertEqual(character["experience"]["total"], player.get_experience())
        self.assertEqual(character["condition"]["hit_points_current"], player.get_hit_points())
        self.assertIsNone(character["condition"]["hit_points_maximum"])
        self.assertEqual(character["movement"]["position_meters"], state["player"]["position_meters"])
        self.assertEqual(character["inventory"]["status"], "available")
        self.assertEqual(character["inventory"]["items"], [])
        self.assertEqual(character["inventory"]["carried_weight_pounds"], 0.0)
        ledgers = tuple(participant.native.being._arena_perception_ledger
                        for participant in candidate.participants)
        evidence_before = tuple((dict(ledger._current), tuple(ledger.history)) for ledger in ledgers)
        rng_before, time_before = self.session._rng_cursor.state, candidate.encounter.time
        native_name, native_id = native.name, native.id
        self.assertNotIn(native.id, json.dumps(state))
        self.assertEqual(self.request("/api/generated/pickup", {"handle": target["handle"]})[0], 409)
        self.request("/api/generated/trace", {"seq": 1, "event": "entity_selected"})
        status, inspected = self.request("/api/generated/inspect", {"handle": target["handle"]},
                                         {"X-Arena-Client-Seq": "1"})
        self.assertEqual(status, 200)
        self.assertEqual(inspected["selected_entity"]["name"], "Dagger")
        self.request("/api/generated/trace", {"seq": 2, "event": "rename_entity_clicked"})
        status, renamed = self.request("/api/generated/rename-entity",
            {"handle": target["handle"], "name": "My Dagger"}, {"X-Arena-Client-Seq": "2"})
        self.assertEqual(status, 200)
        self.assertEqual(renamed["selected_entity"]["name"], "My Dagger")
        self.assertEqual(renamed["character"]["inventory"]["items"], [])
        self.assertEqual(native.id, native_id)
        self.assertEqual(native.name, native_name)
        self.assertEqual(candidate.encounter.time, time_before)
        self.assertEqual(self.session._rng_cursor.state, rng_before)
        for ledger, before in zip(ledgers, evidence_before):
            self.assertEqual(ledger._current, before[0])
            self.assertEqual(tuple(ledger.history), before[1])
        self.assertEqual(candidate.encounter._choice_book._choices, {})
        cell = target["cell"]
        if player.get_position() != self.session.active_candidate.arena_map.layout.center_position(
                HexAddress(cell["column"], cell["row"])):
            status, moving = self.request("/api/generated/destination", {
                **cell, "rate": "sprint", "facing_policy": "turn"})
            self.assertEqual(status, 200)
            for _ in range(100):
                if self.session.public_view()["movement_plan"] is None:
                    break
                status, moving = self.request("/api/generated/advance", {"seconds": 1})
                self.assertEqual(status, 200)
                self.assertEqual(moving["character"]["movement"]["position_meters"],
                                 moving["player"]["position_meters"])
        expected_destination = self.session.active_candidate.arena_map.layout.center_position(
            HexAddress(cell["column"], cell["row"]))
        self.assertEqual(player.get_position(), expected_destination)
        if not self.session.active_candidate.encounter.initiated:
            self.assertEqual(self.request("/api/generated/run", {})[0], 200)
            self.assertEqual(self.request("/api/generated/advance", {"seconds": 1})[0], 200)
        self.request("/api/generated/trace", {"seq": 3, "event": "pickup_clicked"})
        status, pickup = self.request("/api/generated/pickup", {"handle": target["handle"]},
                                      {"X-Arena-Client-Seq": "3"})
        self.assertEqual(status, 200)
        self.assertEqual(pickup["pickup_action"]["status"], "executing")
        status, settled = self.request("/api/generated/advance", {"seconds": 1})
        self.assertEqual(status, 200)
        self.assertEqual(settled["pickup_action"]["outcome"], "success")
        self.assertEqual(native.parent_container_id, player.id)
        inventory = settled["character"]["inventory"]
        self.assertEqual(inventory["status"], "available")
        self.assertEqual(len(inventory["items"]), 1)
        self.assertEqual(inventory["items"][0]["name"], "My Dagger")
        self.assertEqual(inventory["items"][0]["status"], "carried; not readied")
        self.assertEqual(inventory["items"][0]["kind"], "weapon")
        self.assertEqual(inventory["items"][0]["weight_pounds"], native.current.weight)
        self.assertEqual(inventory["carried_weight_pounds"], native.current.weight)
        self.assertNotIn(native.id, json.dumps(inventory))
        self.assertIsNone(player.current.armor_id)
        self.assertEqual(player.current.body_parts, {})
        self.assertEqual(player.weapons, [])
        carried = next(row for row in settled["entities"] if row["handle"] == target["handle"])
        self.assertEqual(carried["present_state"], "carried")
        self.assertIsNone(carried["position_meters"])
        self.assertNotIn(native.id, json.dumps(settled))
        self.assertEqual(carried["name"], "My Dagger")
        status, renamed_carried = self.request("/api/generated/rename-entity",
            {"handle": target["handle"], "name": "Carried Dagger"})
        self.assertEqual(status, 200)
        self.assertEqual(renamed_carried["selected_entity"]["present_state"], "carried")
        self.assertEqual(renamed_carried["selected_entity"]["name"], "Carried Dagger")
        self.assertEqual(renamed_carried["character"]["inventory"]["items"][0]["name"],
                         "Carried Dagger")
        self.assertEqual(native.name, "Dagger")
        self.assertIsNone(native.spatial_state)
        self.assertEqual(native.parent_container_id, self.session.active_candidate.participants[0].native.being.id)
        next_cell = next(cell for cell in candidate.arena_map.layout.neighbors(
            HexAddress(target["cell"]["column"], target["cell"]["row"]))
                         if candidate.arena_map.layout.contains(cell))
        status, moving = self.request("/api/generated/destination", {
            "column": next_cell.column, "row": next_cell.row,
            "rate": "sprint", "facing_policy": "turn"})
        self.assertEqual(status, 200)
        status, moving = self.request("/api/generated/advance", {"seconds": 1})
        self.assertEqual(status, 200)
        self.assertEqual(moving["character"]["movement"]["position_meters"],
                         moving["player"]["position_meters"])
        self.assertEqual(len(moving["character"]["inventory"]["items"]), 1)
        self.assertEqual(moving["character"]["inventory"]["items"][0]["name"], "Carried Dagger")
        valid_weight = native.current.weight
        native.current.weight = math.nan
        invalid_inventory = self.session.public_view()["character"]["inventory"]
        self.assertEqual(invalid_inventory["status"], "unavailable")
        self.assertEqual(invalid_inventory["items"], [])
        self.assertIsNone(invalid_inventory["carried_weight_pounds"])
        native.current.weight = valid_weight
        trace = trace_stream.getvalue()
        self.assertIn("action=inspect status=accepted", trace)
        self.assertIn("action=pickup status=accepted", trace)
        self.assertIn("action=rename_entity status=accepted", trace)
        self.assertIn("entity_type=object type=Dagger", trace)
        self.assertNotIn(native.id, trace)
        self.assertNotIn("http-dagger", trace)
        self.assertNotIn("My Dagger", trace)
        self.assertNotIn("Carried Dagger", trace)

    def test_display_name_overlay_is_safe_observer_scoped_and_replacement_atomic(self):
        original_history = None
        self.session = GeneratedArenaSession(root_seed_factory=lambda: 20261107)
        initial = self.session.generate({"starting_experience": "0", "width_cells": "5", "height_cells": "5"})
        candidate = self.session.active_candidate
        candidate_identity = candidate
        self.assertEqual(candidate.ground_objects, ())
        self.assertEqual(initial["character"]["inventory"]["status"], "available")
        self.assertEqual(initial["character"]["inventory"]["items"], [])
        self.assertEqual(initial["character"]["inventory"]["carried_weight_pounds"], 0.0)
        player, opponent = (row.native.being for row in candidate.participants)
        opponent_view = next(row for row in initial["entities"] if row["category"] == "being")
        native_name, native_id = opponent.name, opponent.id
        ledger = player._arena_perception_ledger
        original_history = tuple(ledger.history)
        original_current = dict(ledger._current)
        awareness = candidate.encounter.aware_beings(player.id)
        choices = dict(candidate.encounter._choice_book._choices)
        time_before = candidate.encounter.time
        rng_before = self.session._rng_cursor.state
        status, renamed = self.request("/api/generated/rename-entity", {
            "handle": opponent_view["handle"], "name": "Mira <b>"})
        self.assertEqual(status, 200)
        self.assertEqual(renamed["selected_entity"]["name"], "Mira <b>")
        self.assertEqual(opponent.id, native_id)
        self.assertEqual(opponent.name, native_name)
        self.assertEqual(tuple(ledger.history), original_history)
        self.assertEqual(ledger._current, original_current)
        self.assertEqual(candidate.encounter.aware_beings(player.id), awareness)
        self.assertEqual(candidate.encounter._choice_book._choices, choices)
        self.assertEqual(candidate.encounter.time, time_before)
        self.assertEqual(self.session._rng_cursor.state, rng_before)
        self.assertNotIn(native_id, json.dumps(renamed))
        self.assertNotIn("source_record", json.dumps(renamed))
        before_refusal = self.session.public_view()
        for invalid_name in ("", " " * 2, "x" * 41):
            status, _ = self.request("/api/generated/rename-entity", {
                "handle": opponent_view["handle"], "name": invalid_name})
            self.assertEqual(status, 409)
            self.assertEqual(self.session.public_view(), before_refusal)
        status, _ = self.request("/api/generated/rename-entity", {
            "handle": "forged-handle", "name": "Nope"})
        self.assertEqual(status, 409)
        status, _ = self.request("/api/generated/rename-entity", {
            "handle": opponent_view["handle"], "name": "Nope", "extra": 1})
        self.assertEqual(status, 409)
        status, _ = self.request("/api/generated/generate", {
            "starting_experience": "not-an-integer", "width_cells": "5", "height_cells": "5"})
        self.assertEqual(status, 409)
        self.assertEqual(next(row for row in self.session.public_view()["entities"]
                              if row["handle"] == opponent_view["handle"])["name"], "Mira <b>")
        self.assertIs(self.session.active_candidate, candidate_identity)
        self.session.generate({"starting_experience": "0", "width_cells": "5", "height_cells": "5"})
        fresh = self.session.public_view()
        self.assertTrue(all(row["name"] != "Mira <b>" for row in fresh["entities"]))
        status, _ = self.request("/api/generated/rename-entity", {
            "handle": opponent_view["handle"], "name": "Stale"})
        self.assertEqual(status, 409)
        self.assertEqual(self.session.active_candidate.encounter.time, 0)

    def test_character_sheet_reads_native_state_without_history_or_opponent_disclosure(self):
        self.session = GeneratedArenaSession(root_seed_factory=lambda: 20261107)
        initial = self.session.generate({"starting_experience": "10000",
                                         "width_cells": "10", "height_cells": "5"})
        candidate = self.session.active_candidate
        player, opponent = (row.native.being for row in candidate.participants)
        rng_before, time_before = self.session._rng_cursor.state, candidate.encounter.time
        event_history_before = dict(candidate.universe.event_history)
        player_ledger = player._arena_perception_ledger
        history_before = tuple(player_ledger.history)
        character_a = self.session.public_view()["character"]
        character_b = self.session.public_view()["character"]
        self.assertEqual(character_a, character_b)
        self.assertEqual(character_a["experience"]["total"], player.get_experience())
        self.assertEqual({row["name"]: row["score"] for row in character_a["abilities"]},
                         player.current.get_abilities())
        self.assertEqual(character_a["condition"]["physical_fatigue_reserves"], {
            "q": player.physical_fatigue.q, "b": player.physical_fatigue.b,
            "profile_status": "unresolved"})
        opponent_view = next(row for row in initial["entities"]
                             if row["category"] == "being" and row["handle"] != initial["player"].get("handle"))
        inspected = self.session.inspect_entity({"handle": opponent_view["handle"]})
        self.assertEqual(inspected["selected_entity"]["category"], "being")
        for private_key in ("abilities", "skills", "experience", "condition", "possessions", "source_record"):
            self.assertNotIn(private_key, inspected["selected_entity"])
        self.assertEqual(inspected["character"]["identity"]["display_name"], initial["player"]["name"])
        self.assertEqual(candidate.encounter.time, time_before)
        self.assertEqual(self.session._rng_cursor.state, rng_before)
        self.assertEqual(candidate.universe.event_history, event_history_before)
        self.assertEqual(tuple(player_ledger.history), history_before)

        player.possessions.append("missing-native-object-reference")
        unavailable = self.session.public_view()["character"]["inventory"]
        self.assertEqual(unavailable["status"], "unavailable")
        self.assertEqual(unavailable["items"], [])
        self.assertIn("validation failed", unavailable["encumbrance_status"])
        self.assertNotIn("missing-native-object-reference", json.dumps(unavailable))
        player.possessions.clear()

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
        self.assertEqual(encounter.aware_beings(player.native.being.id), [hidden.native.being.id])
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
        self.assertEqual(encounter.aware_beings(player.native.being.id), [hidden.native.being.id])
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
            perceived_opponent = next(row for row in view["entities"]
                                      if row["category"] == "being")
            opponent_position = hidden.native.being.get_position()
            self.assertEqual(perceived_opponent["position_meters"], {
                "x": opponent_position.x, "y": opponent_position.y, "z": opponent_position.z})
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
        self.assertEqual(encounter.aware_beings(being.id), [hidden.native.being.id])
        self.assertEqual(encounter.aware_beings(hidden.native.being.id), [being.id])
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

    def test_initial_passive_awareness_makes_spot_intent_unnecessary_without_geometry(self):
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
        self.assertFalse(intent.accepted)
        self.assertEqual(intent.status, "not_accepted")
        self.assertEqual(encounter.aware_beings(player.native.being.id), [hidden.native.being.id])

    def test_passive_refresh_refuses_later_unmodeled_geometry_without_partial_publication(self):
        from spatial.geometry import Sphere
        self.session.generate({"starting_experience": "10000", "width_cells": "10", "height_cells": "5"})
        candidate = self.session.active_candidate
        player = candidate.participants[0].native.being
        other = candidate.participants[1].native.being
        initial_view = self.session.public_view()
        initial_ledger = (dict(player._arena_perception_ledger._current),
                          list(player._arena_perception_ledger._history))
        other.set_geometry(Sphere(.25))
        target = next(cell for cell in candidate.arena_map.layout.addresses()
                      if candidate.arena_map.layout.center_position(cell) != player.get_position())
        self.session.choose_destination({"column": target.column, "row": target.row,
                                         "rate": "walk", "facing_policy": "turn"})
        with self.assertRaisesRegex(ArenaBrowserRequestError, "state is unchanged"):
            self.session.advance_one_second()
        self.assertEqual(candidate.encounter.time, 0)
        self.assertEqual(player._arena_perception_ledger._current, initial_ledger[0])
        self.assertEqual(player._arena_perception_ledger._history, initial_ledger[1])
        self.assertEqual(self.session.public_view()["player"], initial_view["player"])


if __name__ == "__main__":
    unittest.main()
