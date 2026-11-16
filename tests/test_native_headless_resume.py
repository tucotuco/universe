"""Fresh-process native Encounter checkpoint/continuation proof."""
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
import native_headless_resume as resume


class TestNativeHeadlessResume(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base, cls.body = resume._capture_resume_artifact()
        cls.control = resume.continue_native(
            cls.base["encounter"], cls.base["rng_owner"],
            previous_state=cls.body["checkpoint"]["state"],
            prior_action_ids=cls.body["checkpoint"]["finished_action_ids"])

    def test_fresh_os_process_restores_then_uses_native_engine(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "checkpoint.json"
            path.write_bytes(resume._canonical(self.body))
            result = subprocess.run([
                sys.executable, "-B", str(ROOT / "examples/native_headless_resume.py"),
                "--resume", str(path)], cwd=ROOT, check=True,
                capture_output=True, text=True)
        resumed = json.loads(result.stdout)
        self.assertEqual(resumed["forbidden_runtime_imports"], [])
        comparable = {key: value for key, value in resumed.items()
                      if key not in ("strict_load_and_rehydrate_ns",
                                     "peak_rss_platform_units",
                                     "forbidden_runtime_imports",
                                     "native_step_ns")}
        expected = {key: value for key, value in self.control.items()
                    if key != "native_step_ns"}
        self.assertEqual(resume._canonical(comparable), resume._canonical(expected))
        self.assertEqual(resumed["last_processed_boundary"], 9)
        self.assertEqual(resumed["time"], 9)
        self.assertEqual(resumed["state"]["beings"]["being-bram"]["hit_points"], 6)
        strike = next(row for row in resumed["action_rows"]
                      if row["id"] == resume.ATTACK_ID)
        self.assertEqual(strike["outcome"], "normal")
        self.assertGreater(resumed["strict_load_and_rehydrate_ns"], 0)
        self.assertGreater(resumed["peak_rss_platform_units"], 0)
        # The action boundary records both native damage and its identity.
        damage = [change for row in resumed["continuation_deltas"]
                  for change in row["changes"]
                  if change["path"] == ["beings", "being-bram", "hit_points"]]
        self.assertEqual(len(damage), 1)
        self.assertEqual((damage[0]["before"], damage[0]["after"]), (10, 6))
        attack_event = next(event for row in resumed["continuation_deltas"]
                            for event in row["events"]
                            if event["action_id"] == resume.ATTACK_ID)
        self.assertEqual(attack_event["event_type"], "thrust")
        self.assertIn({"type": "DamageEffect", "fields": {
            "source_action_id": resume.ATTACK_ID, "target_id": "being-bram",
            "amount": 4, "component": "body"}}, attack_event["proposal_effects"])
        receipt = next(receipt for receipt in resumed["recent_native_receipts"]
                       if receipt["boundary"] == 8)
        self.assertEqual(receipt["action_ids"], [resume.ATTACK_ID])
        self.assertEqual(receipt["effect_ids"][0],
            ["headless-encounter", 8, resume.ATTACK_ID, "effect", 0])

    def test_artifact_is_deterministic_and_component_sizes_are_reportable(self):
        _base, again = resume._capture_resume_artifact()
        self.assertEqual(resume._canonical(self.body), resume._canonical(again))
        self.assertGreater(len(resume._canonical(self.body)), 0)
        self.assertEqual(len(self.body["deltas"]), 4)
        self.assertEqual(len(self.body["checkpoint"]["action_history"]), 4)

    def test_unknown_fields_corruption_and_compatibility_fail_before_graph_creation(self):
        cases = []
        unknown = copy.deepcopy(self.body)
        unknown["unmodeled"] = True
        cases.append(unknown)
        bad_compat = copy.deepcopy(self.body)
        bad_compat["compatibility"]["source_and_rules_sha256"] = "0" * 64
        bad_compat["integrity_sha256"] = resume._seal(
            {key: value for key, value in bad_compat.items() if key != "integrity_sha256"})
        cases.append(bad_compat)
        bad_history = copy.deepcopy(self.body)
        bad_history["deltas"][0]["changes"][0]["before"] = [999, 0, 0]
        bad_history["integrity_sha256"] = resume._seal(
            {key: value for key, value in bad_history.items() if key != "integrity_sha256"})
        cases.append(bad_history)
        dangling = copy.deepcopy(self.body)
        dangling["checkpoint"]["state"]["beings"]["being-ada"]["weapons"] = ["missing-weapon"]
        dangling["integrity_sha256"] = resume._seal(
            {key: value for key, value in dangling.items() if key != "integrity_sha256"})
        cases.append(dangling)
        mismatched_event = copy.deepcopy(self.body)
        mismatched_event["deltas"][0]["events"][0]["action_id"] = "substituted-action"
        mismatched_event["integrity_sha256"] = resume._seal(
            {key: value for key, value in mismatched_event.items()
             if key != "integrity_sha256"})
        cases.append(mismatched_event)
        for body in cases:
            with self.subTest(case=body.get("schema")):
                with patch.object(resume, "Universe",
                                  side_effect=AssertionError("partial graph construction")):
                    with self.assertRaises(resume.ResumeRejected):
                        resume.restore_private_checkpoint(body)

    def test_missing_or_reordered_delta_commits_fail_closed(self):
        for deltas in (self.body["deltas"][:-1],
                       [self.body["deltas"][1], self.body["deltas"][0],
                        *self.body["deltas"][2:]]):
            malformed = copy.deepcopy(self.body)
            malformed["deltas"] = copy.deepcopy(deltas)
            malformed["integrity_sha256"] = resume._seal(
                {key: value for key, value in malformed.items()
                 if key != "integrity_sha256"})
            with self.assertRaises(resume.ResumeRejected):
                resume.restore_private_checkpoint(malformed)


if __name__ == "__main__":
    unittest.main()
