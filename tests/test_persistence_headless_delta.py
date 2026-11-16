"""Independent native proof for the experimental initial+delta representation."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "examples"))
import encounter_delta_headless as proof


class TestHeadlessEncounterDelta(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = proof.build_demo()
        cls.payload = proof.artifact(cls.result)
        cls.deltas = cls.payload["deltas"]

    def test_native_boundaries_reconstruct_and_snapshot_matches(self):
        reconstructed = self.payload["initial_state"]
        for row in self.result["boundaries"]:
            reconstructed = proof.apply_delta(reconstructed, row["delta"])
            self.assertEqual(proof.canonical_bytes(reconstructed),
                             proof.canonical_bytes(row["actual"]))
            self.assertEqual(proof.state_digest(row["actual"]), row["delta"]["state_sha256"])
        self.assertEqual(proof.canonical_bytes(reconstructed),
                         proof.canonical_bytes(self.payload["snapshot"]["state"]))

    def test_zero_diff_action_event_quiet_boundary_and_atomic_simultaneous_batch(self):
        by_time = {delta["boundary"]: delta for delta in self.deltas}
        self.assertEqual(len(by_time[1]["changes"]), 1)
        self.assertEqual(by_time[1]["events"][0]["event_type"], "run")
        self.assertEqual(by_time[2]["events"], [])
        self.assertEqual(by_time[2]["changes"], [])
        self.assertEqual(by_time[3]["events"][0]["event_type"], "delay")
        self.assertEqual(by_time[3]["events"][0]["outcome"], "success")
        self.assertEqual(by_time[3]["changes"], [])
        simultaneous = by_time[4]
        self.assertEqual(len(simultaneous["events"]), 2)
        self.assertEqual({event["event_type"] for event in simultaneous["events"]}, {"run"})
        positions = [change for change in simultaneous["changes"]
                     if change["path"][-1] == "position"]
        self.assertEqual({change["path"][1] for change in positions},
                         {"being-ada", "being-bram"})
        receipt = next(row for row in self.result["encounter"]._atomic_interval_history
                       if row.boundary == 4)
        self.assertEqual(set(receipt.action_ids),
                         {event["action_id"] for event in simultaneous["events"]})
        # Observer knowledge remains two directed, separately keyed views.
        knowledge = self.payload["snapshot"]["state"]["encounter"]["awareness_by_observer"]
        self.assertEqual(set(knowledge), {"being-ada", "being-bram"})
        self.assertEqual(knowledge["being-ada"], ["being-bram"])
        self.assertEqual(knowledge["being-bram"], ["being-ada"])

    def test_reproducible_artifact_and_malformed_stream_refusal(self):
        rerun = proof.artifact(proof.build_demo())
        self.assertEqual(proof.canonical_bytes(self.payload), proof.canonical_bytes(rerun))
        self.assertEqual(proof.canonical_bytes(
            proof.replay(self.payload["initial_state"], self.deltas)),
            proof.canonical_bytes(self.payload["snapshot"]["state"]))
        with self.assertRaises(proof.DeltaError):
            proof.replay(self.payload["initial_state"], [self.deltas[0], self.deltas[0]])
        with self.assertRaises(proof.DeltaError):
            proof.replay(self.payload["initial_state"], self.deltas[1:])
        with self.assertRaises(proof.DeltaError):
            proof.replay(self.payload["initial_state"],
                         [self.deltas[1], self.deltas[0], *self.deltas[2:]])
        malformed = json.loads(proof.canonical_bytes(self.deltas[0]))
        malformed["changes"][0]["before"] = [90, 0, 0]
        with self.assertRaises(proof.DeltaError):
            proof.apply_delta(self.payload["initial_state"], malformed)
        duplicate_path = json.loads(proof.canonical_bytes(self.deltas[0]))
        duplicate_path["changes"].append(dict(duplicate_path["changes"][0]))
        with self.assertRaises(proof.DeltaError):
            proof.apply_delta(self.payload["initial_state"], duplicate_path)

    def test_cli_runs_in_independent_process_without_arena_runtime(self):
        command = [sys.executable, "-B", str(ROOT / "examples/encounter_delta_headless.py"), "--json"]
        first = subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)
        second = subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)
        self.assertEqual(first.stdout, second.stdout)
        parsed = json.loads(first.stdout)
        self.assertEqual(len(parsed["deltas"]), 7)
        self.assertFalse(any("Arena" in name or "GeneratedArenaSession" in name
                             for name in parsed.keys()))


if __name__ == "__main__":
    unittest.main()
