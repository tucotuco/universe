import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "examples"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from arena_local_checkpoint import (
    ArenaLocalCheckpointRejected,
    activate_approved_local_bundle,
    decode_local_bundle,
    encode_local_bundle,
    write_local_bundle,
)
from arena_web import ArenaRequestError, ArenaSession
from atomic_publication import _COMMITTED_RECEIPTS


def _finish_spot(session):
    session.submit_spot()
    for _ in range(6):
        session.advance_one_second()


class ArenaLocalBundleTests(unittest.TestCase):
    def test_save_requires_successful_quiescent_boundary_six_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "arena.bundle"
            session = ArenaSession(save_path=path)
            with self.assertRaisesRegex(ArenaRequestError, "boundary-6"):
                session.save_supported_state()
            self.assertFalse(path.exists())
            _finish_spot(session)
            result = session.save_supported_state()
            self.assertTrue(result["saved"])
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            prefix, candidate = decode_local_bundle(path.read_bytes())
            self.assertEqual(prefix.through_boundary, 6)
            self.assertEqual(candidate.view().history_prefix_sha256, prefix.content_sha256)
            before = path.read_bytes()
            failed_write = Path(directory) / "injected-failure.bundle"
            with patch("arena_local_checkpoint.os.link", side_effect=OSError("injected link failure")):
                with self.assertRaisesRegex(ArenaLocalCheckpointRejected, "atomic local bundle write failed"):
                    write_local_bundle(failed_write, before, repository_root=ROOT)
            self.assertFalse(failed_write.exists())
            self.assertEqual(list(Path(directory).glob(".universe-arena-*.tmp")), [])
            with self.assertRaisesRegex(ArenaRequestError, "already saved"):
                session.save_supported_state()
            with self.assertRaisesRegex(ArenaLocalCheckpointRejected, "overwrite"):
                write_local_bundle(path, before, repository_root=ROOT)
            self.assertEqual(path.read_bytes(), before)

    def test_failed_spot_and_invalid_or_repository_paths_do_not_write(self):
        with tempfile.TemporaryDirectory() as directory:
            failed_path = Path(directory) / "failed.bundle"
            failed = ArenaSession(die_roll=1, save_path=failed_path)
            _finish_spot(failed)
            self.assertEqual(failed.encounter.inspect_committed(6).action(
                "npc-arena/action/spot-ari-bex").facts.outcome, "failure")
            with self.assertRaisesRegex(ArenaRequestError, "successful boundary-6"):
                failed.save_supported_state()
            self.assertFalse(failed_path.exists())
            elsewhere = Path(directory) / "not-created.bundle"
            with self.assertRaisesRegex(ArenaLocalCheckpointRejected, "absolute"):
                write_local_bundle(Path("relative.bundle"), b"x", repository_root=ROOT)
            with self.assertRaisesRegex(ArenaLocalCheckpointRejected, "outside the repository"):
                write_local_bundle(ROOT / "examples" / "saved" / "forbidden-arena.bundle",
                                   b"x", repository_root=ROOT)
            self.assertFalse((ROOT / "examples" / "saved" / "forbidden-arena.bundle").exists())

    def test_bundle_rejects_tampering_and_host_approval_is_required(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "arena.bundle"
            session = ArenaSession(save_path=path)
            _finish_spot(session)
            session.save_supported_state()
            before = path.read_bytes()
            receipts_before = set(_COMMITTED_RECEIPTS)
            with self.assertRaisesRegex(ArenaLocalCheckpointRejected, "approval"):
                activate_approved_local_bundle(
                    path, repository_root=ROOT,
                    fixture_root=ROOT / "examples" / "npc_candidates",
                    host_approved=False, rng_seed=90210)
            data = json.loads(before)
            with self.assertRaisesRegex(ArenaLocalCheckpointRejected, "unsupported schema or field set"):
                decode_local_bundle(json.dumps(dict(data, unexpected="field")).encode())
            unsupported = dict(data, schema="universe.arena.operator-bundle/999")
            with self.assertRaisesRegex(ArenaLocalCheckpointRejected, "unsupported schema or field set"):
                decode_local_bundle(json.dumps(unsupported).encode())
            data["state_candidate_base64"] = data["state_candidate_base64"][:-4] + "AAAA"
            path.write_bytes(json.dumps(data).encode())
            with self.assertRaises(ArenaLocalCheckpointRejected):
                activate_approved_local_bundle(
                    path, repository_root=ROOT,
                    fixture_root=ROOT / "examples" / "npc_candidates",
                    host_approved=True, rng_seed=90210)
            self.assertEqual(set(_COMMITTED_RECEIPTS), receipts_before)
            self.assertEqual(session.encounter.time, 6)
            self.assertEqual(len(session.encounter.__dict__.get("_atomic_interval_history", ())), 6)


class ArenaOperatorHTTPContinuationTests(unittest.TestCase):
    def _start(self, arguments):
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
        process.terminate()
        process.wait(timeout=5)
        raise AssertionError("Arena server did not announce its loopback endpoint")

    @staticmethod
    def _request(base, path, body=None):
        data = None if body is None else json.dumps(body).encode("utf-8")
        request = Request(base + path, data=data, headers={"Content-Type": "application/json"},
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

    def test_two_process_browser_save_approved_reopen_run_and_native_commit(self):
        from examples.arena_trusted_continuation import _run_new_boundary
        from examples.npc_encounter_arena import build_arena

        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory) / "supported-arena.bundle"
            process_a, base_a = self._start(["--port", "0", "--save-path", str(bundle)])
            try:
                status, page = self._request(base_a, "/")
                self.assertEqual(status, 200)
                self.assertIn(b"Save supported Arena state", page)
                self.assertEqual(self._request(base_a, "/api/spot", {"operation": "ari_spots_bex"})[0], 200)
                for expected in range(1, 7):
                    status, state = self._request(base_a, "/api/advance", {"seconds": 1})
                    self.assertEqual(status, 200)
                    self.assertEqual(state["time"], expected)
                self.assertTrue(state["save_available"])
                self.assertEqual(self._request(base_a, "/api/save", {"path": str(bundle)})[0], 409)
                status, saved = self._request(base_a, "/api/save", {})
                self.assertEqual(status, 200)
                self.assertTrue(saved["saved"])
                self.assertEqual(saved["historical_trust"], "untrusted data until separately host-admitted")
                self.assertTrue(bundle.is_file())
            finally:
                self._stop(process_a)

            # The bundle's existence does not imply host approval.
            denied = subprocess.run(
                [sys.executable, "examples/npc_encounter_arena_web.py", "--port", "0",
                 "--resume-from", str(bundle), "--rng-seed", "90210"],
                cwd=ROOT, capture_output=True, text=True, timeout=15,
                env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
            self.assertEqual(denied.returncode, 2)
            self.assertIn("requires the separate --approve-local-checkpoint", denied.stderr)

            process_b, base_b = self._start([
                "--port", "0", "--resume-from", str(bundle),
                "--approve-local-checkpoint", "--rng-seed", "90210",
            ])
            try:
                status, page = self._request(base_b, "/")
                self.assertEqual(status, 200)
                self.assertIn(b"Submit Ari Run +X Choice", page)
                status, before = self._request(base_b, "/api/gm")
                self.assertEqual(status, 200)
                self.assertEqual(before["time"], 6)
                self.assertEqual(before["native_receipt_boundaries"], [])
                self.assertEqual(before["native_inspection_boundaries"], [])
                self.assertEqual([row["boundary"] for row in before["committed_timeline"]], list(range(1, 7)))
                self.assertTrue(all(row["provenance"].startswith("imported/host-accepted claim")
                                    for row in before["committed_timeline"]))
                self.assertEqual(before["historical_spot_claim"]["outcome"], "success")
                self.assertIn("not established", before["imported_history_trust"])
                self.assertEqual(self._request(base_b, "/api/advance", {"seconds": 1})[0], 409)
                ari = self._request(base_b, "/api/observer/ari")[1]
                bex = self._request(base_b, "/api/observer/bex")[1]
                self.assertEqual(ari["aware_participants"], ["Bex"])
                self.assertEqual(bex["aware_participants"], [])
                self.assertNotIn("position", json.dumps(ari))
                self.assertNotIn("position", json.dumps(bex))
                self.assertEqual(self._request(base_b, "/api/run", {"operation": "wrong"})[0], 409)
                status, choice = self._request(base_b, "/api/run", {"operation": "ari_run_plus_x"})
                self.assertEqual(status, 200)
                self.assertEqual(choice["choice_id"], "npc-arena/encounter/1/draft/2")
                self.assertEqual(self._request(base_b, "/api/run", {"operation": "ari_run_plus_x"})[0], 409)
                status, uncommitted = self._request(base_b, "/api/gm")
                self.assertEqual(uncommitted["time"], 6)
                self.assertEqual(uncommitted["native_receipt_boundaries"], [])
                status, final = self._request(base_b, "/api/advance", {"seconds": 1})
                self.assertEqual(status, 200)
                self.assertEqual(final["time"], 7)
                self.assertEqual(final["native_receipt_boundaries"], [7])
                self.assertEqual(final["native_inspection_boundaries"], [7])
                timeline = final["committed_timeline"]
                self.assertEqual([row["boundary"] for row in timeline], list(range(1, 8)))
                self.assertTrue(all(row["provenance"].startswith("imported/host-accepted claim")
                                    for row in timeline[:6]))
                self.assertEqual(timeline[6]["provenance"], "native/publisher-issued in this process")
                participants = {row["id"]: row for row in final["participants"]}
                self.assertEqual(participants["arena/being/ari"]["position"], {"x": 1.0, "y": 0.0})
                self.assertEqual(participants["arena/being/bex"]["position"], {"x": 3.0, "y": 0.0})
                self.assertEqual(final["spot"]["id"], "npc-arena/action/run-ari-boundary-7")
                self.assertEqual(final["spot"]["actor_id"], "arena/being/ari")
                self.assertIsNone(final["spot"]["target_id"])
                self.assertEqual(final["spot"]["choice_id"], "npc-arena/encounter/1/draft/2")
                self.assertEqual(final["spot"]["outcome"], "success")
                self.assertEqual(final["spot"]["practice"][0]["experience"], 4)
                self.assertEqual(final["spot"]["practice"][0]["causal_action_ids"],
                                 ["npc-arena/action/run-ari-boundary-7"])
                ari_after = self._request(base_b, "/api/observer/ari")[1]
                bex_after = self._request(base_b, "/api/observer/bex")[1]
                self.assertEqual(ari_after["aware_participants"], ["Bex"])
                self.assertEqual(bex_after["aware_participants"], [])
                self.assertEqual(self._request(base_b, "/api/save", {})[0], 409)
            finally:
                self._stop(process_b)

            baseline = build_arena(die_roll=20)
            expected = _run_new_boundary(
                baseline["encounter"].universe, baseline["encounter"], baseline["rng"])
            self.assertEqual(final["spot"]["outcome"], expected["outcome"])
            self.assertEqual(final["spot"]["metadata"], dict(expected["metadata"]))
            self.assertEqual(final["spot"]["id"], expected["action_id"])
            self.assertEqual(final["spot"]["actor_id"], expected["actor_id"])
            self.assertEqual(final["spot"]["target_id"], expected["target_id"])
            self.assertEqual(final["spot"]["choice_id"], expected["choice_id"])
            baseline_action = baseline["encounter"].inspect_committed(7).action(expected["action_id"])
            self.assertEqual(final["spot"]["effect_ids"],
                             [str(effect.identity) for effect in baseline_action.effects])
            self.assertEqual(participants["arena/being/ari"]["position"],
                             {"x": expected["ari_position"][0], "y": expected["ari_position"][1]})
            self.assertEqual(participants["arena/being/bex"]["position"],
                             {"x": expected["bex_position"][0], "y": expected["bex_position"][1]})
            self.assertEqual(ari_after["aware_participants"], ["Bex"])
            self.assertEqual(expected["ari_hp"], 10)
            self.assertEqual(expected["bex_hp"], 10)
            self.assertEqual(participants["arena/being/ari"]["hit_points"], expected["ari_hp"])
            self.assertEqual(participants["arena/being/bex"]["hit_points"], expected["bex_hp"])
            expected_sources = {row.native_being_id: row.source_sha256
                                for row in baseline["candidate_bindings"]}
            self.assertEqual({identity: row["source_sha256"]
                              for identity, row in participants.items()}, expected_sources)


if __name__ == "__main__":
    unittest.main()
