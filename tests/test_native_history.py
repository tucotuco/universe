from __future__ import annotations

import copy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "examples"))

import encounter_delta_headless
from native_history import (NativeHistoryRejected, capture, decode, encode,
                            append_committed, events_at, state_at, validate,
                            NativeHistoryRecorder, write, _plain)


class NativeHistoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.demo = encounter_delta_headless.build_demo(until=4)
        cls.log = capture(cls.demo["encounter"])
        cls.wire = encode(cls.log)

    def test_native_inspection_boundaries_round_trip_as_atomic_history(self):
        log = decode(self.wire)
        self.assertTrue(validate(log))
        self.assertEqual(log["latest_boundary"], 4)
        self.assertEqual([row["boundary"] for row in log["boundaries"]], [1, 2, 3, 4])
        self.assertEqual(events_at(log, 2)["action_ids"], [])
        self.assertEqual(len(events_at(log, 3)["action_ids"]), 1)
        action_row = next(iter(events_at(log, 3)["actions"].values()))
        self.assertEqual(action_row["$record"], "encounter_inspection.ActionInspection")
        self.assertEqual(len(events_at(log, 4)["action_ids"]), 2)
        self.assertEqual(len(events_at(log, 4)["effect_ids"]), 6)
        self.assertEqual(state_at(log, 4)["boundary"], 4)
        for boundary in range(1, 5):
            expected = {}
            for target_id, history in self.demo["encounter"].inspect_committed().histories.items():
                for target in history:
                    if target.boundary == boundary:
                        expected[target_id] = target
            self.assertEqual(state_at(log, boundary)["entities"], _plain(expected))
            receipt = next(row for row in self.demo["encounter"]._atomic_interval_history
                           if row.boundary == boundary)
            self.assertEqual(events_at(log, boundary)["action_ids"], list(receipt.action_ids))

    def test_changes_are_presence_aware_and_reconstruct_each_native_target_boundary(self):
        for boundary, delta in enumerate(self.log["boundaries"], 1):
            state = state_at(self.log, boundary)
            self.assertEqual(state["boundary"], boundary)
            expected = {}
            for target_id, history in self.demo["encounter"].inspect_committed().histories.items():
                for target in history:
                    if target.boundary == boundary:
                        expected[target_id] = target
            # Native history contains exact typed target read records. The
            # initial entity state is separate and only changes by committed deltas.
            self.assertEqual(set(state["entities"]), set(expected))
            self.assertTrue(all(row["before"] is True or row["before"] is False
                                for row in delta["changes"]))

    def test_wire_omits_process_pointer_anchors(self):
        forbidden = {"object_identity", "ledger_identity", "target_anchors", "action_anchors"}
        stack = [self.log]
        while stack:
            value = stack.pop()
            if type(value) is dict:
                self.assertTrue(forbidden.isdisjoint(value))
                stack.extend(value.values())
            elif type(value) is list:
                stack.extend(value)

    def test_capture_is_read_only_and_does_not_import_arena_application(self):
        import sys
        from encounter_inspection import fingerprint
        encounter = self.demo["encounter"]
        before = tuple((id(row), fingerprint(row))
                       for row in encounter._atomic_interval_history)
        rng_before = self.demo["rng_owner"].state
        recaptured = capture(encounter)
        after = tuple((id(row), fingerprint(row))
                      for row in encounter._atomic_interval_history)
        self.assertEqual(before, after)
        self.assertEqual(rng_before, self.demo["rng_owner"].state)
        self.assertEqual(encode(recaptured), self.wire)
        for module in ("arena_browser_session", "arena_persistence",
                       "arena_native_snapshot", "arena_server", "npcgen"):
            self.assertNotIn(module, sys.modules)

    def test_corrupt_digest_preimage_duplicate_actions_and_reordering_refuse(self):
        corrupted = copy.deepcopy(self.log)
        corrupted["boundaries"][0]["events"]["action_ids"].append("foreign")
        with self.assertRaises(NativeHistoryRejected):
            validate(corrupted)
        bad_preimage = copy.deepcopy(self.log)
        change = next(row for row in bad_preimage["boundaries"][0]["changes"]
                      if row["before"] is True)
        change["before_value"] = "incorrect"
        # Re-seal the envelope to exercise semantic preimage validation.
        import hashlib
        import json
        unsigned = dict(bad_preimage)
        unsigned.pop("sha256")
        unsigned["sha256"] = hashlib.sha256(json.dumps(
            unsigned, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("ascii")).hexdigest()
        with self.assertRaises(NativeHistoryRejected):
            validate(unsigned)
        reordered = copy.deepcopy(self.log)
        reordered["boundaries"][0], reordered["boundaries"][1] = (
            reordered["boundaries"][1], reordered["boundaries"][0])
        with self.assertRaises(NativeHistoryRejected):
            validate(reordered)

    def test_standalone_write_does_not_overwrite_existing_artifact(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.json"
            write(self.log, path)
            before = path.read_bytes()
            with self.assertRaises(NativeHistoryRejected):
                write(self.log, path)
            self.assertEqual(path.read_bytes(), before)

    def test_append_accepts_only_the_next_authenticated_native_commit(self):
        demo = encounter_delta_headless.build_demo(until=4)
        encounter = demo["encounter"]
        log = capture(encounter)
        from activities import DelayAction
        action = DelayAction(encounter, encounter.being_list[1], defense=0,
                             start_time=4, id="append-delay")
        encounter.schedule_action(action)
        encounter.step(1)

        appended = append_committed(log, encounter)
        self.assertEqual(log["latest_boundary"], 4)  # immutable input
        self.assertEqual(appended["latest_boundary"], 5)
        self.assertEqual(events_at(appended, 5)["action_ids"], ["append-delay"])
        self.assertEqual(state_at(appended, 5)["boundary"], 5)
        self.assertTrue(validate(decode(encode(appended))))
        with self.assertRaisesRegex(NativeHistoryRejected, "no next committed"):
            append_committed(appended, encounter)

    def test_rolled_back_publication_has_no_appendable_history_receipt(self):
        demo = encounter_delta_headless.build_demo(until=4)
        encounter = demo["encounter"]
        recorder = NativeHistoryRecorder.attach(encounter)
        log = recorder.export()
        from activities import DelayAction
        action = DelayAction(encounter, encounter.being_list[1], defense=0,
                             start_time=4, id="rolled-back-delay")
        encounter.schedule_action(action)
        import atomic_publication
        publish = atomic_publication.publish_interval_candidate

        def fail_after_commit_marker(*args, **kwargs):
            kwargs["_fail_after"] = "mark_committed"
            return publish(*args, **kwargs)

        with patch.object(atomic_publication, "publish_interval_candidate",
                          fail_after_commit_marker):
            with self.assertRaises(atomic_publication.PublicationFailure):
                encounter.step(1)
        self.assertEqual(encounter.time, 4)
        self.assertEqual(recorder.latest_boundary, 4)
        self.assertIsNone(recorder.failure)
        self.assertEqual(log["latest_boundary"], 4)
        with self.assertRaisesRegex(NativeHistoryRejected,
                                    "no next committed boundary"):
            append_committed(log, encounter)

    def test_attached_recorder_appends_only_after_native_commit_returns(self):
        demo = encounter_delta_headless.build_demo(until=4)
        encounter = demo["encounter"]
        recorder = NativeHistoryRecorder.attach(encounter)
        from activities import DelayAction
        action = DelayAction(encounter, encounter.being_list[1], defense=0,
                             start_time=4, id="automatic-history-delay")
        encounter.schedule_action(action)
        encounter.step(1)
        log = recorder.export()
        self.assertEqual(recorder.latest_boundary, 5)
        self.assertEqual(events_at(log, 5)["action_ids"], [action.id])
        self.assertEqual(log, capture(encounter))


if __name__ == "__main__":
    unittest.main()
