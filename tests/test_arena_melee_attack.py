"""End-to-end native Dagger strike coverage for the generated Arena."""

import io
import json
import math
from pathlib import Path
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "examples")]

from arena_browser_session import GeneratedArenaSession
from arena_hex_map import HexAddress
from arena_web import make_handler
from melee_combat import MeleeStrike, effective_melee_reach_meters


class TestArenaMeleeAttack(unittest.TestCase):
    def setUp(self):
        self.session = GeneratedArenaSession(root_seed_factory=lambda: 20261107)

    def request(self, path, payload=None):
        handler = object.__new__(make_handler(self.session))
        handler.path = path
        handler.server = type("Server", (), {"server_port": 8000})()
        handler.wfile = io.BytesIO()
        body = b"" if payload is None else json.dumps(payload).encode("utf-8")
        handler.rfile = io.BytesIO(body)
        handler.headers = {"Content-Length": str(len(body)),
                           "Content-Type": "application/json"}
        result = {}
        handler._send = lambda status, value, content_type="application/json; charset=utf-8": result.update(
            status=status, body=value, content_type=content_type)
        (handler.do_GET if payload is None else handler.do_POST)()
        value = result["body"]
        if result["content_type"].startswith("application/json"):
            value = json.loads(json.dumps(value) if type(value) is not str else value)
        return result["status"], value

    def generate(self, *, equipment_mode="equipped"):
        status, view = self.request("/api/generated/generate", {
            "starting_experience": "10000", "width_cells": "10",
            "height_cells": "5", "equipment_mode": equipment_mode})
        self.assertEqual(status, 200, view)
        return view

    def move_to_target_neighbor(self, view):
        candidate = self.session.active_candidate
        player, target = (p.native.being for p in candidate.participants)
        player_cell = candidate.arena_map.layout.cell_at_position(player.get_position())
        target_cell = candidate.arena_map.layout.cell_at_position(target.get_position())
        destination = min(
            (cell for cell in candidate.arena_map.layout.neighbors(target_cell)
             if cell != player_cell),
            key=lambda cell: math.dist(
                candidate.arena_map.layout.center_position(cell, z=player.get_position().z).as_tuple(),
                player.get_position().as_tuple()))
        status, view = self.request("/api/generated/destination", {
            "column": destination.column, "row": destination.row,
            "rate": "sprint", "facing_policy": "turn"})
        self.assertEqual(status, 200)
        for _ in range(100):
            if view["movement_plan"] is None:
                break
            status, view = self.request("/api/generated/advance", {"seconds": 1})
            self.assertEqual(status, 200, view)
        self.assertIsNone(view["movement_plan"])
        distance = candidate.encounter.distance_between_beings(player.id, target.id)
        provenance = candidate.initial_equipment_provenance[0]
        unit = next(row for row in provenance["specification"]["equipment"]["units"]
                    if row.get("role") == "primary_weapon")
        weapon_id = provenance["object_ids"][unit["equipment_id"]]
        weapon = candidate.universe.get_object_by_id(weapon_id)
        reach = effective_melee_reach_meters(player.current, weapon.current)
        self.assertLessEqual(distance, reach)
        target_row = next(row for row in view["entities"]
                          if row["category"] == "being"
                          and row["name"] != view["player"]["name"])
        return view, target_row, weapon_id, distance, reach

    def schedule_thrust(self):
        view = self.generate()
        view, target, weapon_id, distance, reach = self.move_to_target_neighbor(view)
        status, view = self.request("/api/generated/inspect", {"handle": target["handle"]})
        self.assertEqual(status, 200)
        entry = next(row for row in view["action_catalog"]["entries"]
                     if row["name"] == "thrust at being")
        self.assertEqual(entry["status"], "available", entry["reason"])
        self.assertEqual(entry["duration_seconds"], 4)
        self.assertIn("Reach and path resolve at impact", entry["reason"])
        status, accepted = self.request("/api/generated/melee-strike", {
            "handle": target["handle"], "motion": "thrust"})
        self.assertEqual(status, 200, accepted)
        candidate = self.session.active_candidate
        player = candidate.participants[0].native.being
        action = self.session._player_melee_action(candidate, player)
        self.assertIs(type(action), MeleeStrike)
        self.assertEqual((action.actor_id, action.target_id, action.instrument_id),
                         (player.id, candidate.participants[1].native.being.id, weapon_id))
        return accepted, target, action, weapon_id, distance, reach

    def test_native_strike_browser_route_and_pending_completed_save_load(self):
        accepted, target, action, weapon_id, distance, reach = self.schedule_thrust()
        self.assertEqual(accepted["melee_action"]["status"], "executing")
        self.assertEqual(accepted["melee_action"]["duration_seconds"], 4)
        source = self.session
        saved_pending = source.save_encounter_bytes()
        restored = GeneratedArenaSession()
        with mock.patch("npcgen.api.arena_ready_being",
                        side_effect=AssertionError("Load must not regenerate")):
            loaded = restored.load_encounter_bytes(saved_pending)
        self.assertEqual(loaded["melee_action"]["status"], "executing")
        self.assertEqual(loaded["melee_action"]["seconds_remaining"], 4)
        loaded_candidate = restored.active_candidate
        loaded_action = restored._player_melee_action(
            loaded_candidate, loaded_candidate.participants[0].native.being)
        self.assertEqual(loaded_action.id, action.id)
        self.assertEqual(loaded_action.instrument_id, weapon_id)
        self.assertTrue(loaded["advance_available"])
        for index in range(4):
            source_view = source.advance_one_second()
            loaded_view = restored.advance_one_second()
            self.assertEqual(source_view["time_seconds"], loaded_view["time_seconds"])
            if index < 3:
                self.assertEqual(loaded_view["melee_action"]["status"], "executing")
                self.assertEqual(loaded_view["melee_action"]["seconds_remaining"], 3 - index)
        source_result = source.public_view()["melee_action"]
        loaded_result = restored.public_view()["melee_action"]
        self.assertEqual(source_result["status"], "completed")
        self.assertEqual(loaded_result, source_result)
        self.assertEqual(source_result["impact_distance_meters"], distance)
        self.assertEqual(source._rng_cursor.state, restored._rng_cursor.state)
        self.assertEqual(source.active_candidate.participants[0].native.being.get_hit_points(),
                         restored.active_candidate.participants[0].native.being.get_hit_points())
        loaded_player = loaded_candidate.participants[0].native.being
        loaded_weapon = loaded_candidate.universe.get_object_by_id(weapon_id)
        self.assertIn(weapon_id, loaded_player.armed_with(loaded_candidate.universe).values())
        self.assertEqual(loaded_weapon.parent_container_id, loaded_player.id)
        completed_wire = restored.save_encounter_bytes()
        completed_restore = GeneratedArenaSession()
        completed = completed_restore.load_encounter_bytes(completed_wire)
        self.assertEqual(completed["melee_action"], source_result)
        self.assertNotIn(loaded_player.id, json.dumps(completed["character"]))
        self.assertNotIn(weapon_id, json.dumps(completed))

    @unittest.skipUnless(sys.platform == "darwin" and __import__("shutil").which("swift"),
                         "JavaScriptCore via Swift is available on macOS only")
    def test_shipped_javascript_action_selector_submits_visible_native_target(self):
        import shutil
        import subprocess
        import tempfile

        view = self.generate()
        view, target, _, _, _ = self.move_to_target_neighbor(view)
        status, view = self.request("/api/generated/inspect", {"handle": target["handle"]})
        self.assertEqual(status, 200)
        _, page = self.request("/")
        with tempfile.TemporaryDirectory(prefix="arena-melee-js-") as temp:
            temp = Path(temp)
            page_path, state_path = temp / "page.html", temp / "view.json"
            cell_path, refusal_path = temp / "cell.json", temp / "refusal.json"
            page_path.write_text(page, encoding="utf-8")
            state_path.write_text(json.dumps(view), encoding="utf-8")
            cell_path.write_text("{}", encoding="utf-8")
            refusal_path.write_text("null", encoding="utf-8")
            module_cache = Path(tempfile.gettempdir()) / "universe-arena-jsc-module-cache"
            module_cache.mkdir(parents=True, exist_ok=True)
            run = subprocess.run([
                shutil.which("swift"), "-module-cache-path", str(module_cache),
                str(ROOT / "tests" / "arena_browser_js_harness.swift"),
                str(page_path), str(state_path), str(cell_path), str(state_path),
                str(refusal_path), "false", "melee-only"],
                check=False, capture_output=True, text=True, timeout=60)
        self.assertEqual(run.returncode, 0, run.stderr)
        result = json.loads(run.stdout)
        strike = next(call for call in result["calls"]
                      if call["path"] == "/api/generated/melee-strike")
        self.assertEqual(strike["body"], {"handle": target["handle"], "motion": "thrust"})
        self.assertEqual(result["time"], view["time_seconds"] + 4)
        self.assertEqual(result["melee_action"]["status"], "completed")
        self.assertEqual(result["melee_action"]["outcome"], "uncertain_path")
        self.assertIn("Thrust resolved: uncertain_path", result["actionResult"])

    def test_native_out_of_reach_resolves_at_impact_and_unready_is_refused(self):
        view = self.generate()
        status, view = self.request("/api/generated/run", {})
        self.assertEqual(status, 200)
        status, view = self.request("/api/generated/advance", {"seconds": 1})
        self.assertEqual(status, 200)
        candidate = self.session.active_candidate
        player, target = (p.native.being for p in candidate.participants)
        row = next(row for row in view["entities"] if row["category"] == "being"
                   and row["name"] != player.name)
        status, view = self.request("/api/generated/inspect", {"handle": row["handle"]})
        self.assertEqual(status, 200)
        initial_distance = candidate.encounter.distance_between_beings(player.id, target.id)
        target_hp = target.get_hit_points()
        status, accepted = self.request("/api/generated/melee-strike", {
            "handle": row["handle"], "motion": "thrust"})
        self.assertEqual(status, 200, accepted)
        for _ in range(4):
            status, accepted = self.request("/api/generated/advance", {"seconds": 1})
            self.assertEqual(status, 200, accepted)
        self.assertEqual(accepted["melee_action"]["outcome"], "out_of_reach")
        self.assertGreater(initial_distance, 1.0)
        self.assertEqual(target.get_hit_points(), target_hp)

        unequipped = GeneratedArenaSession(root_seed_factory=lambda: 20261107)
        self.session = unequipped
        view = self.generate(equipment_mode="unequipped")
        self.assertEqual(self.request("/api/generated/run", {})[0], 200)
        self.assertEqual(self.request("/api/generated/advance", {"seconds": 1})[0], 200)
        view = unequipped.public_view()
        player = unequipped.active_candidate.participants[0].native.being
        row = next(row for row in view["entities"] if row["category"] == "being"
                   and row["name"] != player.name)
        status, view = self.request("/api/generated/inspect", {"handle": row["handle"]})
        self.assertEqual(status, 200)
        entry = next(row for row in view["action_catalog"]["entries"]
                     if row["name"] == "thrust at being")
        self.assertEqual(entry["status"], "unavailable")
        before = (unequipped.active_candidate.encounter.time,
                  dict(unequipped.active_candidate.universe.event_history),
                  dict(unequipped.active_candidate.encounter._choice_book._choices),
                  unequipped._rng_cursor.state)
        status, refused = self.request("/api/generated/melee-strike", {
            "handle": row["handle"], "motion": "thrust"})
        self.assertEqual(status, 409)
        self.assertEqual(before, (unequipped.active_candidate.encounter.time,
            dict(unequipped.active_candidate.universe.event_history),
            dict(unequipped.active_candidate.encounter._choice_book._choices),
            unequipped._rng_cursor.state))
        self.assertNotIn(unequipped.active_candidate.participants[1].native.being.id,
                         json.dumps(refused))
        self.assertIn("initial Dagger", refused["error"])

        unreadied = GeneratedArenaSession(root_seed_factory=lambda: 20261107)
        self.session = unreadied
        view = self.generate()
        self.assertEqual(self.request("/api/generated/run", {})[0], 200)
        self.assertEqual(self.request("/api/generated/advance", {"seconds": 1})[0], 200)
        candidate = unreadied.active_candidate
        player = candidate.participants[0].native.being
        dagger_id = unreadied._initial_ready_dagger_id(candidate, player)
        player.current.body_parts["right hand"] = None
        target = candidate.participants[1].native.being
        row = next(row for row in unreadied.public_view()["entities"]
                   if row["category"] == "being" and row["name"] != unreadied.public_view()["player"]["name"])
        status, inspected = self.request("/api/generated/inspect", {"handle": row["handle"]})
        self.assertEqual(status, 200)
        thrust = next(entry for entry in inspected["action_catalog"]["entries"]
                      if entry["name"] == "thrust at being")
        self.assertEqual(thrust["status"], "unavailable")
        self.assertIn("held and readied", thrust["reason"])
        before = (candidate.encounter.time, dict(candidate.universe.event_history),
                  dict(candidate.encounter._choice_book._choices), unreadied._rng_cursor.state)
        status, refused = self.request("/api/generated/melee-strike", {
            "handle": row["handle"], "motion": "thrust"})
        self.assertEqual(status, 409)
        self.assertIn("held and readied", refused["error"])
        self.assertEqual(before, (candidate.encounter.time, dict(candidate.universe.event_history),
                  dict(candidate.encounter._choice_book._choices), unreadied._rng_cursor.state))
        self.assertIn(dagger_id, player.possessions)
        self.assertEqual(target.get_hit_points(), candidate.participants[1].native.being.get_hit_points())


if __name__ == "__main__":
    unittest.main()
