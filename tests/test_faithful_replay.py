"""Separate-process historical playback and native replay fidelity slice."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "examples"))
import native_headless_resume as replay


class TestFaithfulNativeReplay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.body = replay.record_full_timeline()

    def test_historical_reader_reconstructs_queries_without_action_resolution(self):
        requested = [2, 3, 4, 7, 8, 9]
        with patch.object(replay.Encounter, "step",
                          side_effect=AssertionError("historical playback resolved an Action")):
            result = replay.historical_playback(self.body, requested)
        self.assertFalse(result["native_resolution_invoked"])
        boundaries = {row["boundary"]: row for row in result["boundaries"]}
        states = {0: self.body["checkpoint"]["initial_state"]}
        state = states[0]
        deltas = (self.body["checkpoint"]["deltas"]
                  + self.body["control"]["continuation_deltas"])
        native_states = {row["boundary"]: row["state"]
                         for row in self.body["native_snapshots"]}
        for row in deltas:
            state = replay.delta.apply_delta(state, row)
            states[row["boundary"]] = state
        for boundary in requested:
            with self.subTest(boundary=boundary):
                self.assertEqual(replay._canonical(boundaries[boundary]["state"]),
                                 replay._canonical(states[boundary]))
                self.assertEqual(replay._canonical(boundaries[boundary]["state"]),
                                 replay._canonical(native_states[boundary]))
                self.assertEqual(boundaries[boundary]["state_sha256"],
                                 replay.delta.state_digest(states[boundary]))
                self.assertEqual(set(states[boundary]["encounter"][
                    "awareness_by_observer"]), {"being-ada", "being-bram"})
        self.assertEqual(len(boundaries[2]["events_at_boundary"]), 0)
        self.assertEqual(len(boundaries[2]["event_history"]), 1)
        self.assertEqual(boundaries[3]["events_at_boundary"][0]["outcome"], "success")
        delay = boundaries[3]["events_at_boundary"][0]
        self.assertEqual(delay["event_type"], "delay")
        self.assertEqual(delay["outcome"], "success")
        self.assertTrue(delay["proposal_effects"])
        self.assertFalse(any(change["path"][0] == "beings"
            for change in self.body["checkpoint"]["deltas"][2]["changes"]))
        self.assertEqual(len(boundaries[4]["events_at_boundary"]), 2)
        self.assertEqual(len(boundaries[4]["event_history"]), 4)
        self.assertEqual(len(boundaries[7]["events_at_boundary"]), 0)
        self.assertEqual(boundaries[8]["state"]["beings"]["being-bram"]["hit_points"], 6)
        self.assertEqual(len(boundaries[8]["events_at_boundary"][0]["proposal_effects"]), 2)
        self.assertEqual(len(boundaries[9]["event_history"]), 5)

    def test_separate_process_playback_reexecution_and_checkpoint_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            recording = Path(directory) / "timeline.json"
            checkpoint = Path(directory) / "checkpoint.json"
            writer = subprocess.run([sys.executable, "-B",
                str(ROOT / "examples/native_headless_resume.py"),
                "--record-full", str(recording)], cwd=ROOT, check=True,
                capture_output=True, text=True)
            self.assertIn("through boundary 9", writer.stdout)
            body = json.loads(recording.read_text())
            checkpoint.write_bytes(replay._canonical(body["checkpoint"]))
            playback_run = subprocess.run([sys.executable, "-B",
                str(ROOT / "examples/native_headless_resume.py"),
                "--playback", str(recording), "--boundary", "4", "--boundary", "8"],
                cwd=ROOT, check=True, capture_output=True, text=True)
            playback = json.loads(playback_run.stdout)
            self.assertEqual(playback["forbidden_runtime_imports"], [])
            self.assertEqual(replay._canonical(playback["boundaries"][0]["state"]),
                replay._canonical(body["checkpoint"]["checkpoint"]["state"]))
            reexecute_run = subprocess.run([sys.executable, "-B",
                str(ROOT / "examples/native_headless_resume.py"),
                "--reexecute", str(recording), "--id-prefix", "independent/"],
                cwd=ROOT, check=True, capture_output=True, text=True)
            reexecution = json.loads(reexecute_run.stdout)
            self.assertEqual(reexecution["forbidden_runtime_imports"], [])
            self.assertEqual(len(reexecution["boundaries"]), 9)
            self.assertTrue(reexecution["rng_equal"])
            mapping = reexecution["event_id_map"]
            self.assertTrue(mapping)
            self.assertEqual(len(set(mapping.values())), len(mapping))
            generated_action_ids = {row["id"] for row in body["control"]["action_rows"]}
            self.assertTrue(all(mapping[action_id] != action_id
                                for action_id in generated_action_ids))
            self.assertEqual([row["event_count"] for row in reexecution["boundaries"]],
                             [1, 0, 1, 2, 0, 0, 0, 1, 0])
            self.assertTrue(all(row > 0 for row in reexecution["native_step_ns"]))
            resumed_run = subprocess.run([sys.executable, "-B",
                str(ROOT / "examples/native_headless_resume.py"),
                "--resume", str(checkpoint)], cwd=ROOT, check=True,
                capture_output=True, text=True)
            resumed = json.loads(resumed_run.stdout)
            self.assertEqual(replay._canonical(resumed["state"]),
                             replay._canonical(body["control"]["state"]))
            self.assertEqual(resumed["rng_state"], body["control"]["rng_state"])
            self.assertEqual(resumed["recent_native_receipts"],
                             body["control"]["recent_native_receipts"])
            self.assertGreater(replay._canonical(body).__len__(), 0)

    def test_tampered_or_ambiguous_recordings_fail_closed(self):
        mutations = []
        altered = copy.deepcopy(self.body)
        altered["control"]["continuation_deltas"][3]["events"][0]["outcome"] = "altered"
        mutations.append(altered)
        broken_cause = copy.deepcopy(self.body)
        broken_cause["control"]["continuation_deltas"][3]["events"][0]["parent_event_id"] = "missing"
        mutations.append(broken_cause)
        inconsistent_time = copy.deepcopy(self.body)
        inconsistent_time["control"]["continuation_deltas"][3]["events"][0]["end_time"] = 7
        unsigned = {key: value for key, value in inconsistent_time.items()
                    if key != "integrity_sha256"}
        inconsistent_time["integrity_sha256"] = replay._seal(unsigned)
        mutations.append(inconsistent_time)
        duplicate_effect = copy.deepcopy(self.body)
        effects = duplicate_effect["control"]["continuation_deltas"][3]["events"][0]["effect_ids"]
        effects.append(copy.deepcopy(effects[0]))
        mutations.append(duplicate_effect)
        snapshot_mismatch = copy.deepcopy(self.body)
        snapshot_mismatch["native_snapshots"][0]["state"]["beings"]["being-ada"][
            "hit_points"] -= 1
        unsigned = {key: value for key, value in snapshot_mismatch.items()
                    if key != "integrity_sha256"}
        snapshot_mismatch["integrity_sha256"] = replay._seal(unsigned)
        mutations.append(snapshot_mismatch)
        for body in mutations:
            with self.subTest(mutation=len(mutations)):
                with self.assertRaises(replay.ResumeRejected):
                    replay.historical_playback(body, [8])
        for mutate in (
            lambda body: body["control"]["continuation_deltas"].pop(),
            lambda body: body["control"]["continuation_deltas"].reverse(),
        ):
            malformed = copy.deepcopy(self.body)
            mutate(malformed)
            unsigned = {key: value for key, value in malformed.items()
                        if key != "integrity_sha256"}
            malformed["integrity_sha256"] = replay._seal(unsigned)
            with self.assertRaises(replay.ResumeRejected):
                replay.validate_full_timeline(malformed)
        with self.assertRaises(replay.ResumeRejected):
            replay.historical_playback(self.body, [10])

    def test_generated_identity_map_rejects_ambiguous_reference(self):
        def event(action_id, choice_id=None):
            return {"action_class": "RunAction", "event_type": "run",
                    "parent_event_id": "headless-encounter", "actor_id": "being-ada",
                    "target_id": None, "start_time": 0, "end_time": 1,
                    "outcome": "success", "target_ids": [], "event_id": action_id,
                    "action_id": action_id, "choice_id": choice_id}
        reference = [{"boundary": 1, "events": [event("left-a"), event("left-b")] }]
        ambiguous = [{"boundary": 1, "events": [event("right-a"), event("right-a")] }]
        with self.assertRaises(replay.ResumeRejected):
            replay._id_mapping(reference, ambiguous)

    def test_unknown_property_paths_outside_the_projection_are_rejected(self):
        initial = self.body["checkpoint"]["initial_state"]
        for path in (["beings", "being-ada", "unmodeled"],
                     ["beings", "being-ada", "skill_experience", "unmodeled"],
                     ["encounter", "unmodeled"]):
            with self.subTest(path=path):
                row = {"changes": [{"path": path}]}
                with self.assertRaises(replay.ResumeRejected):
                    replay._validate_replay_path_closure(initial, row)


if __name__ == "__main__":
    unittest.main()
