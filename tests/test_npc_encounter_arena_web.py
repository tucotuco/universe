import json
from pathlib import Path
import sys
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "examples"))
sys.path.insert(0, str(ROOT / "src"))

from arena_web import ArenaSession, make_handler
from http.server import ThreadingHTTPServer


class ArenaWebTests(unittest.TestCase):
    def setUp(self):
        self.session = ArenaSession()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.session))
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

    def post(self, path, body):
        request = Request(self.base + path, data=json.dumps(body).encode(),
                          headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urlopen(request, timeout=3) as response:
                return response.status, json.loads(response.read())
        except HTTPError as response:
            try:
                return response.code, json.loads(response.read())
            finally:
                response.close()

    def fingerprint(self):
        encounter = self.session.encounter
        return {
            "time": encounter.time,
            "rng": self.session.scenario["rng"].state,
            "objects": tuple(sorted(encounter.universe.object_registry.object_instances)),
            "events": tuple(sorted(encounter.universe.event_history)),
            "pending": tuple(encounter.pending_action_list),
            "finished": tuple(encounter.finished_action_list),
            "receipts": len(encounter.__dict__.get("_atomic_interval_history", ())),
            "choices": encounter.choice_state,
        }

    def test_get_is_read_only_and_views_keep_the_information_boundary(self):
        before = self.fingerprint()
        status, headers, page = self.get("/")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers["Content-Type"])
        self.assertIn(b"GM / developer Reality", page)
        self.assertIn(b"observer Awareness projections", page)
        _, _, gm = self.get("/api/gm")
        gm_data = json.loads(gm)
        self.assertEqual(gm_data["time"], 0)
        self.assertEqual([p["position"] for p in gm_data["participants"]],
                         [{"x": 0, "y": 0}, {"x": 3, "y": 0}])
        _, _, ari_raw = self.get("/api/observer/ari")
        ari = json.loads(ari_raw)
        self.assertEqual(ari["aware_participants"], [])
        self.assertNotIn(self.session.bex.native_being_id.encode(), ari_raw)
        self.assertNotIn(b"Bex", ari_raw)
        self.assertNotIn(b'"position"', ari_raw)
        _, _, _ = self.get("/api/observer/bex")
        self.assertEqual(before, self.fingerprint())

    def test_allowlist_duplicate_and_late_submission_refuse_without_extra_mutation(self):
        before = self.fingerprint()
        status, error = self.post("/api/spot", {"operation": "ari_spots_bex",
                                                  "target_id": self.session.bex.native_being_id})
        self.assertEqual(status, 409)
        self.assertEqual(before, self.fingerprint())
        status, _ = self.post("/api/advance", {"seconds": 2})
        self.assertEqual(status, 409)
        self.assertEqual(before, self.fingerprint())
        status, accepted = self.post("/api/spot", {"operation": "ari_spots_bex"})
        self.assertEqual(status, 200, error)
        self.assertEqual(accepted["state"], "accepted")
        after_accept = self.fingerprint()
        status, _ = self.post("/api/spot", {"operation": "ari_spots_bex"})
        self.assertEqual(status, 409)
        self.assertEqual(after_accept, self.fingerprint())
        late = ArenaSession()
        late.advance_one_second()
        state = (late.encounter.time, late.scenario["rng"].state,
                 tuple(late.encounter.pending_action_list), late.encounter.choice_state)
        with self.assertRaisesRegex(ValueError, "before the first"):
            late.submit_spot()
        self.assertEqual(state, (late.encounter.time, late.scenario["rng"].state,
                                 tuple(late.encounter.pending_action_list), late.encounter.choice_state))

    def test_native_choice_starts_on_boundary_and_commits_at_six_with_observer_isolation(self):
        status, accepted = self.post("/api/spot", {"operation": "ari_spots_bex"})
        self.assertEqual(status, 200)
        self.assertEqual(accepted["action_ids"], ["npc-arena/action/spot-ari-bex"])
        self.assertEqual(self.session.encounter.pending_action_list, [])
        self.assertEqual(self.session.encounter.get_choice(accepted["choice_id"]).state, "accepted")
        for boundary in range(1, 7):
            status, state = self.post("/api/advance", {"seconds": 1})
            self.assertEqual(status, 200)
            self.assertEqual(state["time"], boundary)
            if boundary == 1:
                self.assertIn("npc-arena/action/spot-ari-bex",
                              self.session.encounter.pending_action_list)
                self.assertIsNotNone(self.session.world.get_event_by_id(
                    "npc-arena/action/spot-ari-bex"))
                self.assertEqual(self.session.encounter.get_choice(
                    accepted["choice_id"]).state, "executing")
            ari = json.loads(self.get("/api/observer/ari")[2])
            bex = json.loads(self.get("/api/observer/bex")[2])
            if boundary < 6:
                self.assertEqual(ari["aware_participants"], [])
                self.assertNotIn(self.session.bex.native_being_id,
                                 json.dumps(ari, sort_keys=True))
                self.assertIsNone(state["spot"])
            else:
                self.assertEqual(state["spot"]["boundary"], 6)
                self.assertEqual(state["spot"]["outcome"], "success")
                self.assertEqual(ari["aware_participants"], ["Bex"])
                self.assertEqual(bex["aware_participants"], [])
                self.assertNotIn("position", json.dumps(ari))
                self.assertNotIn("position", json.dumps(bex))
        self.assertEqual([row["boundary"] for row in state["committed_timeline"]],
                         [1, 2, 3, 4, 5, 6])
        self.assertTrue(state["rng_unchanged"])
        self.assertEqual(self.session.encounter.get_choice(accepted["choice_id"]).state, "finished")
        inspection = self.session.encounter.inspect_committed(6)
        action = inspection.action("npc-arena/action/spot-ari-bex")
        self.assertEqual(action.facts.outcome, "success")
        self.assertEqual(action.resolved_boundary, 6)
        self.assertNotIn("npc-arena/action/spot-ari-bex",
                         self.session.encounter.pending_action_list)
        status, _ = self.post("/api/advance", {"seconds": 1})
        self.assertEqual(status, 409)

    def test_failed_spot_commits_at_six_without_awareness(self):
        self.session.die_roll = 1
        self.assertEqual(self.post("/api/spot", {"operation": "ari_spots_bex"})[0], 200)
        for _ in range(6):
            self.assertEqual(self.post("/api/advance", {"seconds": 1})[0], 200)
        action = self.session.encounter.inspect_committed(6).action("npc-arena/action/spot-ari-bex")
        self.assertEqual(action.facts.outcome, "failure")
        self.assertEqual(self.session.encounter.aware_beings(self.session.ari.native_being_id), [])
        ari = json.loads(self.get("/api/observer/ari")[2])
        self.assertEqual(ari["aware_participants"], [])


if __name__ == "__main__":
    unittest.main()
