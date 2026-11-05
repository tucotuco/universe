"""Fixed S7 trusted-local save/reopen/continue acceptance tests."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import patch
import re

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "examples"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from arena_s7_checkpoint import ArenaS7Rejected, decode_s7_candidate
from arena_local_checkpoint import (
    ArenaLocalCheckpointRejected, activate_approved_local_bundle,
    encode_local_bundle, write_local_bundle,
)
from arena_history_prefix import capture_arena_history_prefix
from arena_state_candidate import capture_arena_post_spot_state


class ArenaS7CandidateTests(unittest.TestCase):
    def _active_at7(self):
        from examples.npc_encounter_arena import build_arena
        from examples.arena_web import ArenaSession
        from arena_s7_checkpoint import capture_s7_candidate
        summary = build_arena(die_roll=20)
        prefix = capture_arena_history_prefix(summary)
        state = capture_arena_post_spot_state(summary, prefix)
        s6 = encode_local_bundle(prefix, state)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        s6_path, s7_path = Path(directory.name) / "s6", Path(directory.name) / "s7"
        write_local_bundle(s6_path, s6, repository_root=ROOT)
        active = activate_approved_local_bundle(
            s6_path, repository_root=ROOT, fixture_root=ROOT / "examples" / "npc_candidates",
            host_approved=True, rng_seed=90210)
        session = ArenaSession(active=active, save_path=s7_path)
        session.submit_run(); session.advance_one_second()
        return s6, active, session

    def _s7(self):
        from arena_s7_checkpoint import capture_s7_candidate
        s6, active, _ = self._active_at7()
        return capture_s7_candidate(s6, active).to_bytes()

    def test_s7_is_closed_and_binds_exact_unchanged_s6_bytes(self):
        wire = self._s7()
        candidate = decode_s7_candidate(wire)
        self.assertEqual(candidate.to_bytes(), wire)
        self.assertEqual(json.loads(wire)["boundary7"]["practice"]["experience"], 4)
        data = json.loads(wire)
        data["unexpected"] = True
        with self.assertRaisesRegex(ArenaS7Rejected, "unknown fields"):
            decode_s7_candidate(json.dumps(data).encode())

    def test_s7_rejects_semantically_forged_run_even_with_recomputed_digest(self):
        from arena_s7_checkpoint import _canonical
        data = json.loads(self._s7())
        data["boundary7"]["action"]["action_id"] = "forged/run"
        body = dict(data); body.pop("content_sha256")
        data["content_sha256"] = hashlib.sha256(_canonical(body)).hexdigest()
        with self.assertRaisesRegex(ArenaS7Rejected, "boundary-7 claim"):
            decode_s7_candidate(_canonical(data))

    def test_s7_atomic_write_failure_leaves_no_destination_and_retry_is_possible(self):
        from arena_local_checkpoint import write_local_bundle
        s7 = self._s7()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "s7.bundle"
            with patch("arena_local_checkpoint.os.link", side_effect=OSError("injected link failure")):
                with self.assertRaisesRegex(ArenaLocalCheckpointRejected, "atomic local bundle write failed"):
                    write_local_bundle(path, s7, repository_root=ROOT)
            self.assertFalse(path.exists())
            self.assertEqual(list(Path(directory).glob(".universe-arena-*.tmp")), [])
            write_local_bundle(path, s7, repository_root=ROOT)
            self.assertTrue(path.is_file())

    def test_s7_capture_refuses_stale_target_state_and_open_action(self):
        from activities import RunAction
        from arena_s7_checkpoint import capture_s7_candidate
        s6, active, _ = self._active_at7()
        active.encounter.get_being("arena/being/ari").skill_experience["run"] = 99
        with self.assertRaisesRegex(ArenaS7Rejected, "practice"):
            capture_s7_candidate(s6, active)

        s6, active, _ = self._active_at7()
        pending = RunAction(active.world, "arena/being/ari", 7, 1, 0.5,
                            experience=4, id="arena/run/unsupported-pending")
        active.encounter.schedule_choice((pending,))
        with self.assertRaisesRegex(ArenaS7Rejected, "ChoiceBook"):
            capture_s7_candidate(s6, active)


class ArenaS7ThreeProcessHTTPContinuationTests(unittest.TestCase):
    @staticmethod
    def _start(arguments):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        process = subprocess.Popen(
            [sys.executable, "examples/npc_encounter_arena_web.py", *arguments],
            cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1)
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            line = process.stdout.readline()
            match = re.search(r"http://127\.0\.0\.1:(\d+)/", line)
            if match:
                return process, f"http://127.0.0.1:{match.group(1)}"
            if process.poll() is not None:
                output = process.stdout.read()
                raise AssertionError(f"Arena process exited {process.returncode}: {line}{output}")
        process.terminate(); process.wait(timeout=5)
        raise AssertionError("Arena server did not announce its loopback endpoint")

    @staticmethod
    def _request(base, path, body=None):
        data = None if body is None else json.dumps(body).encode("utf-8")
        request = Request(base + path, data=data,
                          headers={"Content-Type": "application/json"},
                          method="GET" if body is None else "POST")
        try:
            with urlopen(request, timeout=5) as response:
                raw = response.read()
                return response.status, json.loads(raw) if "json" in response.headers.get("Content-Type", "") else raw
        except HTTPError as response:
            try:
                return response.code, json.loads(response.read())
            finally:
                response.close()

    @staticmethod
    def _stop(process):
        if process.poll() is None:
            process.terminate()
        process.wait(timeout=10)
        if process.stdout:
            process.stdout.close()

    def test_three_process_s6_s7_boundary8_matches_uninterrupted_native_run(self):
        from examples.arena_trusted_continuation import _run_new_boundary
        from examples.npc_encounter_arena import build_arena
        from activities import RunAction

        with tempfile.TemporaryDirectory() as directory:
            s6, s7 = Path(directory) / "arena-s6.bundle", Path(directory) / "arena-s7.bundle"

            # Process A: native Spot, boundary 6, S6 save.
            process_a, base_a = self._start(["--port", "0", "--save-path", str(s6)])
            try:
                self.assertEqual(self._request(base_a, "/api/spot", {"operation": "ari_spots_bex"})[0], 200)
                for _ in range(6):
                    status, state = self._request(base_a, "/api/advance", {"seconds": 1})
                    self.assertEqual(status, 200)
                self.assertEqual(state["time"], 6)
                self.assertEqual(self._request(base_a, "/api/save", {})[0], 200)
                self.assertEqual(s6.stat().st_mode & 0o777, 0o600)
            finally:
                self._stop(process_a)
            s6_bytes = s6.read_bytes()
            s6_digest = hashlib.sha256(s6_bytes).hexdigest()

            # Process B: separately approve S6, publish boundary 7, save S7.
            process_b, base_b = self._start([
                "--port", "0", "--resume-from", str(s6), "--approve-local-checkpoint",
                "--rng-seed", "90210", "--save-path", str(s7),
            ])
            try:
                before = self._request(base_b, "/api/gm")[1]
                self.assertEqual(before["time"], 6)
                self.assertEqual(before["native_receipt_boundaries"], [])
                self.assertEqual(self._request(base_b, "/api/run", {"operation": "ari_run_plus_x"})[0], 200)
                self.assertEqual(self._request(base_b, "/api/advance", {"seconds": 1})[0], 200)
                committed = self._request(base_b, "/api/gm")[1]
                self.assertEqual(committed["native_receipt_boundaries"], [7])
                self.assertEqual(committed["participants"][0]["run_experience"], 4)
                status, saved = self._request(base_b, "/api/save", {})
                self.assertEqual(status, 200)
                self.assertEqual(saved["bundle_schema"], "universe.arena.local-s7-claim/1")
                self.assertTrue(s7.is_file())
                self.assertEqual(s7.stat().st_mode & 0o777, 0o600)
                self.assertEqual(hashlib.sha256(s6.read_bytes()).hexdigest(), s6_digest)
            finally:
                self._stop(process_b)
            s7_bytes = s7.read_bytes()

            # The older generic S6 approval must not authorize S7.
            denied = subprocess.run([
                sys.executable, "examples/npc_encounter_arena_web.py", "--port", "0",
                "--resume-from", str(s7), "--approve-local-checkpoint", "--rng-seed", "90210"],
                cwd=ROOT, capture_output=True, text=True, timeout=15,
                env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
            self.assertEqual(denied.returncode, 2)
            self.assertIn("separate --approve-local-s7-checkpoint", denied.stderr)
            denied_without_flag = subprocess.run([
                sys.executable, "examples/npc_encounter_arena_web.py", "--port", "0",
                "--resume-from", str(s7), "--rng-seed", "90210"],
                cwd=ROOT, capture_output=True, text=True, timeout=15,
                env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
            self.assertEqual(denied_without_flag.returncode, 2)
            self.assertIn("separate --approve-local-s7-checkpoint", denied_without_flag.stderr)

            # Process C: separate S7 approval; no imported receipts/actions are installed.
            process_c, base_c = self._start([
                "--port", "0", "--resume-from", str(s7), "--approve-local-s7-checkpoint",
                "--rng-seed", "123456",
            ])
            try:
                initial = self._request(base_c, "/api/gm")[1]
                self.assertEqual(initial["time"], 7)
                self.assertEqual(initial["native_receipt_boundaries"], [])
                self.assertEqual(initial["native_inspection_boundaries"], [])
                self.assertEqual([row["boundary"] for row in initial["committed_timeline"]], list(range(1, 8)))
                self.assertTrue(all(row["provenance"].startswith("imported/host-accepted claim")
                                    for row in initial["committed_timeline"]))
                self.assertEqual(initial["historical_run_claim"]["id"], "npc-arena/action/run-ari-boundary-7")
                self.assertEqual(initial["participants"][0]["position"], {"x": 1.0, "y": 0.0})
                self.assertEqual(initial["participants"][0]["run_experience"], 4)
                self.assertEqual(self._request(base_c, "/api/advance", {"seconds": 1})[0], 409)
                status, accepted = self._request(base_c, "/api/run", {"operation": "ari_run_plus_x"})
                self.assertEqual(status, 200)
                self.assertEqual(accepted["choice_id"], "npc-arena/encounter/1/draft/3")
                self.assertEqual(accepted["action_ids"], ["npc-arena/action/run-ari-boundary-8"])
                queued = self._request(base_c, "/api/gm")[1]
                self.assertEqual(queued["native_receipt_boundaries"], [])
                status, final = self._request(base_c, "/api/advance", {"seconds": 1})
                self.assertEqual(status, 200)
                self.assertEqual(final["time"], 8)
                self.assertEqual(final["native_receipt_boundaries"], [8])
                self.assertEqual(final["native_inspection_boundaries"], [8])
                self.assertEqual([row["boundary"] for row in final["committed_timeline"]], list(range(1, 9)))
                self.assertTrue(all(row["provenance"].startswith("imported/host-accepted claim")
                                    for row in final["committed_timeline"][:7]))
                self.assertEqual(final["committed_timeline"][7]["provenance"], "native/publisher-issued in this process")
                self.assertEqual(final["spot"]["id"], "npc-arena/action/run-ari-boundary-8")
                self.assertEqual(final["spot"]["choice_id"], "npc-arena/encounter/1/draft/3")
                self.assertEqual(final["spot"]["outcome"], "success")
                self.assertEqual(final["participants"][0]["position"], {"x": 2.0, "y": 0.0})
                self.assertEqual(final["participants"][0]["run_experience"], 8)
                self.assertEqual(final["spot"]["practice"], [
                    {"being_id": "arena/being/ari", "skill": "run", "experience": 4,
                     "time": 7, "causal_action_ids": ["npc-arena/action/run-ari-boundary-7"]},
                    {"being_id": "arena/being/ari", "skill": "run", "experience": 4,
                     "time": 8, "causal_action_ids": ["npc-arena/action/run-ari-boundary-8"]},
                ])
                self.assertTrue(final["rng_unchanged"])
            finally:
                self._stop(process_c)

            # Uninterrupted native Spot -> Run7 -> Run8 comparison.
            baseline = build_arena(die_roll=20)
            _run_new_boundary(baseline["encounter"].universe, baseline["encounter"], baseline["rng"])
            action = RunAction(baseline["encounter"].universe, "arena/being/ari", 7, 1, 0.5,
                               experience=4, id="npc-arena/action/run-ari-boundary-8")
            choice = baseline["encounter"].schedule_choice((action,))
            baseline["encounter"].step(1, velocities={"arena/being/ari": (1, 0, 0),
                                                       "arena/being/bex": (0, 0, 0)})
            expected = baseline["encounter"].inspect_committed(8)
            expected_action = expected.action(action.id)
            self.assertEqual(final["spot"]["outcome"], expected_action.facts.outcome)
            self.assertEqual(final["spot"]["metadata"], dict(expected_action.facts.metadata))
            self.assertEqual(final["spot"]["effect_ids"], [str(row.identity) for row in expected_action.effects])
            self.assertEqual(final["spot"]["choice_id"], choice.id)
            self.assertEqual(final["participants"][0]["position"], {"x": 2.0, "y": 0.0})
            self.assertEqual(final["participants"][1]["position"], {"x": 3.0, "y": 0.0})
            self.assertEqual(final["participants"][0]["hit_points"], baseline["encounter"].universe.get_object_by_id("arena/being/ari").get_hit_points())
            self.assertEqual(hashlib.sha256(s6.read_bytes()).hexdigest(), s6_digest)
            self.assertEqual(hashlib.sha256(s7_bytes).hexdigest(), hashlib.sha256(s7.read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
