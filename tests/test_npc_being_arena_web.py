"""Loopback browser interaction for the bounded imported-NPC Arena."""

import json
from http.server import ThreadingHTTPServer
from pathlib import Path
import sys
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "examples"))
sys.path.insert(0, str(ROOT / "src"))

from npc_being_arena import build_arena
from npc_being_arena_web import make_handler, serve_local


class NpcBeingArenaWebTests(unittest.TestCase):
    def setUp(self):
        self.arena = build_arena(seed=72002)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.arena))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def get(self, path):
        with urlopen(self.base + path, timeout=3) as response:
            return response.status, response.headers, response.read()

    def request(self, path, body=None, *, method=None, raw=None, content_type="application/json"):
        data = raw if raw is not None else (None if body is None else json.dumps(body).encode("utf-8"))
        request = Request(
            self.base + path, data=data,
            headers={} if content_type is None else {"Content-Type": content_type},
            method=method or ("GET" if body is None and raw is None else "POST"),
        )
        try:
            with urlopen(request, timeout=3) as response:
                body_bytes = response.read()
                parsed = json.loads(body_bytes) if "json" in response.headers.get("Content-Type", "") else body_bytes
                return response.status, parsed
        except HTTPError as response:
            try:
                body_bytes = response.read()
                try:
                    parsed = json.loads(body_bytes)
                except json.JSONDecodeError:
                    parsed = body_bytes
                return response.code, parsed
            finally:
                response.close()

    def fingerprint(self):
        encounter = self.arena.encounter
        return (
            encounter.time,
            self.arena.rng.state,
            tuple(sorted(self.arena.world.object_registry.object_instances)),
            tuple(sorted(self.arena.world.event_history)),
            tuple(encounter.pending_action_list),
            tuple(encounter.finished_action_list),
            encounter.choice_state,
            tuple(row.boundary for row in encounter.__dict__.get("_atomic_interval_history", ())),
            self.arena.opponent.get_hit_points(),
            self.arena.submitted,
            self.arena.committed_result,
        )

    def test_browser_submit_precommit_commit_result_and_refusal_paths(self):
        before = self.fingerprint()
        status, headers, page = self.get("/")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers["Content-Type"])
        self.assertIn(b"Source-derived NPC", page)
        self.assertIn(b"Arena-authored mechanics", page)
        self.assertIn(b"not imported", page)
        self.assertIn(b"does not calculate the full revision-60 strategy pool", page)
        self.assertNotIn(b"High Elf", page)
        self.assertNotIn(b"7881", page)

        status, initial = self.request("/api/state")
        self.assertEqual(status, 200)
        self.assertEqual(initial["time"], 0)
        self.assertFalse(initial["submitted"])
        self.assertFalse(initial["committed"])
        self.assertIsNone(initial["choice"])
        source = initial["developer_view"]["source_derived"]
        self.assertEqual(source["display_name"], "Tobe")
        self.assertEqual(source["skills"]["weapon_skills"], {"Dagger": 2})
        serialized = json.dumps(initial, sort_keys=True)
        for hidden in ("High Elf", "7881.735", "family", "possessions", "psionics"):
            self.assertNotIn(hidden, serialized)
        self.assertEqual(before, self.fingerprint())

        # Unsupported routes, malformed/extra input and non-JSON requests are read-only.
        self.assertEqual(self.request("/api/observer/tobe")[0], 404)
        self.assertEqual(self.request("/api/submit", raw=b"{")[0], 400)
        self.assertEqual(self.request("/api/submit", {"operation": "submit_fixed_thrust",
                                                        "target_id": self.arena.opponent.id})[0], 400)
        self.assertEqual(self.request("/api/submit", {"operation": "submit_fixed_thrust"},
                                      content_type="text/plain")[0], 415)
        self.assertEqual(self.request("/api/advance", {"seconds": 4})[0], 400)
        self.assertEqual(self.request("/api/submit", {"operation": "submit_fixed_thrust"},
                                      method="PUT")[0], 405)
        self.assertEqual(before, self.fingerprint())

        status, accepted = self.request("/api/submit", {"operation": "submit_fixed_thrust"})
        self.assertEqual(status, 200)
        self.assertTrue(accepted["accepted"])
        self.assertEqual(accepted["action_id"], self.arena.strike.id)
        after_accept = self.fingerprint()
        self.assertEqual(self.arena.encounter.time, 0)
        self.assertEqual(self.arena.rng.state, before[1])
        state = self.request("/api/state")[1]
        self.assertTrue(state["precommit"])
        self.assertEqual(state["choice"]["state"], "accepted")
        self.assertEqual(state["native_receipt_boundaries"], [])
        self.assertIsNone(state["committed_result"])

        self.assertEqual(self.request("/api/submit", {"operation": "submit_fixed_thrust"})[0], 409)
        self.assertEqual(self.fingerprint(), after_accept)
        self.assertEqual(self.request("/api/advance", {"operation": "advance_to_commit"})[0], 200)
        final = self.request("/api/state")[1]
        result = final["committed_result"]
        self.assertTrue(final["committed"])
        self.assertEqual(final["time"], 4)
        self.assertEqual(result["outcome"], "normal")
        self.assertEqual(result["metadata"], {"distance": 1.5})
        self.assertEqual(result["causal_damage"], {"body": 4})
        self.assertEqual(result["target_hp_after"], 6)
        self.assertEqual(result["boundary"], 4)
        self.assertEqual(result["native_receipt_boundaries"], [1, 2, 3, 4])
        self.assertNotIn("roll", result["metadata"])
        self.assertEqual(final["native_receipt_boundaries"], [1, 2, 3, 4])
        self.assertEqual(self.arena.encounter.inspect_committed(4).action(
            self.arena.strike.id).facts.outcome, "normal")
        after_commit = self.fingerprint()
        self.assertEqual(self.request("/api/advance", {"operation": "advance_to_commit"})[0], 409)
        self.assertEqual(self.fingerprint(), after_commit)

    def test_server_refuses_non_loopback_binding(self):
        with self.assertRaisesRegex(ValueError, "IPv4 loopback"):
            serve_local(0, host="0.0.0.0")


if __name__ == "__main__":
    unittest.main()
