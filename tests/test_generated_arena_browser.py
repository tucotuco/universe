"""HTTP and native-boundary tests for the generated Arena browser shell."""

import json
import io
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


class TestGeneratedArenaBrowser(unittest.TestCase):
    def setUp(self):
        self.session = GeneratedArenaSession(root_seed_factory=lambda: 20261107)

    def request(self, path, payload=None):
        handler_type = make_handler(self.session)
        handler = object.__new__(handler_type)
        handler.path = path
        handler.wfile = io.BytesIO()
        handler.headers = {}
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            handler.rfile = io.BytesIO(body)
            handler.headers["Content-Length"] = str(len(body))
        result = {}
        handler._send = lambda status, body, content_type="application/json; charset=utf-8": result.update(
            status=status, body=body, content_type=content_type)
        (handler.do_GET if payload is None else handler.do_POST)()
        body = result["body"]
        if result["content_type"].startswith("application/json"):
            body = json.loads(json.dumps(body) if type(body) is not str else body)
        return result["status"], body

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
        status, state = self.request("/api/generated/state")
        self.assertEqual(status, 200)
        self.assertEqual(state["state"], "empty")
        self.assertFalse(state["load_available"])
        self.assertFalse(state["spot_available"])
        self.assertIsNone(self.session.active_candidate)
        self.assertEqual(self.request("/api/gm")[0], 404)

    def test_generate_returns_only_player_allowlist_and_rename_preserves_native_identity(self):
        status, state = self.request("/api/generated/generate", {
            "starting_experience": "0", "width_cells": "5", "height_cells": "5"})
        self.assertEqual(status, 200)
        self.assertEqual(state["state"], "active")
        self.assertEqual(state["time_seconds"], 0)
        self.assertEqual(state["map"]["width_cells"], 5)
        self.assertEqual(state["map"]["height_cells"], 5)
        self.assertFalse(state["spot_available"])
        candidate = self.session.active_candidate
        self.assertEqual(candidate.encounter.time, 0)
        self.assertEqual(len(candidate.participants), 2)
        self.assertNotEqual(candidate.participants[0].native.being.id,
                            candidate.participants[1].native.being.id)
        self.assertEqual([p.native.being.get_experience() for p in candidate.participants], [0, 0])
        encoded = json.dumps(state).lower()
        for forbidden in ("source_sha256", "source_record", "native_id", "class", "level",
                          "experience", "awareness", "target_id", "action_id", "participants"):
            self.assertNotIn(forbidden, encoded)
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
