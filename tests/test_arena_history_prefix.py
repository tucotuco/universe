"""Portable detached history for the fixed six-boundary Arena Spot."""
import base64
from dataclasses import FrozenInstanceError
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from arena_history_prefix import (
    ArenaHistoryRejected,
    capture_arena_history_prefix,
    decode_arena_history_prefix,
)
from examples.npc_encounter_arena import build_arena


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _wire_with_edit(prefix, edit, *, resign=True):
    data = json.loads(prefix.to_bytes())
    edit(data)
    if resign:
        payload = dict(data)
        payload.pop("content_sha256")
        data["content_sha256"] = hashlib.sha256(_canonical(payload)).hexdigest()
    return _canonical(data)


class ArenaHistoryPrefixTests(unittest.TestCase):
    def setUp(self):
        self.scenario = build_arena(die_roll=20)
        self.prefix = capture_arena_history_prefix(self.scenario)
        self.wire = self.prefix.to_bytes()

    def test_capture_is_canonical_detached_and_does_not_issue_receipts(self):
        import atomic_publication
        encounter = self.scenario["encounter"]
        before = (encounter.time, encounter.last_processed_boundary,
                  tuple(encounter._atomic_interval_history),
                  dict(atomic_publication._COMMITTED_RECEIPTS),
                  self.scenario["rng"].state,
                  tuple(encounter.aware_beings("arena/being/ari")),
                  tuple(encounter.aware_beings("arena/being/bex")))
        again = capture_arena_history_prefix(self.scenario)
        self.assertEqual(self.wire, again.to_bytes())
        after = (encounter.time, encounter.last_processed_boundary,
                 tuple(encounter._atomic_interval_history),
                 dict(atomic_publication._COMMITTED_RECEIPTS),
                 self.scenario["rng"].state,
                 tuple(encounter.aware_beings("arena/being/ari")),
                 tuple(encounter.aware_beings("arena/being/bex")))
        self.assertEqual(before, after)
        decoded = decode_arena_history_prefix(self.wire)
        self.assertEqual(decoded.to_bytes(), self.wire)
        self.assertEqual(decoded.summary()["boundaries"], (1, 2, 3, 4, 5, 6))
        self.assertEqual(decoded.summary()["spot"]["outcome"], "success")
        self.assertIn("not portable", decoded.trust)
        with self.assertRaises(FrozenInstanceError):
            decoded.through_boundary = 5
        copied = decoded.payload()
        copied["npc_bindings"].clear()
        self.assertEqual(decoded.to_bytes(), self.wire)
        rows = {row["native_being_id"]: row for row in decoded.payload()["npc_bindings"]}
        for binding, candidate in zip(
                self.scenario["candidate_bindings"],
                (self.scenario["candidates"]["ari"], self.scenario["candidates"]["bex"])):
            self.assertEqual(base64.b64decode(rows[binding.native_being_id]["source_bytes_base64"]),
                             candidate.source_bytes)
            self.assertEqual(rows[binding.native_being_id]["source_sha256"],
                             candidate.content_sha256)

    def test_fresh_process_decodes_historical_data_without_publisher_authority(self):
        script = r'''
import json,sys
sys.path.insert(0,sys.argv[1])
from arena_history_prefix import decode_arena_history_prefix
assert 'atomic_publication' not in sys.modules
assert 'encounter' not in sys.modules
prefix=decode_arena_history_prefix(sys.stdin.buffer.read())
print(json.dumps(prefix.summary(),ensure_ascii=False,sort_keys=True,separators=(',',':')))
'''
        proc = subprocess.run([sys.executable, "-c", script, str(ROOT / "src")],
                              input=self.wire, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, cwd=ROOT, check=False)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8", errors="replace"))
        self.assertEqual(json.loads(proc.stdout), json.loads(json.dumps(self.prefix.summary())))

    def test_refuses_missing_duplicate_gapped_and_reordered_boundaries(self):
        edits = (
            lambda d: d["boundaries"].pop(),
            lambda d: d["boundaries"].__setitem__(1, dict(d["boundaries"][0])),
            lambda d: d["boundaries"][1].__setitem__("boundary", 3),
            lambda d: d["boundaries"].reverse(),
        )
        for edit in edits:
            with self.subTest(edit=edit), self.assertRaises(ArenaHistoryRejected):
                decode_arena_history_prefix(_wire_with_edit(self.prefix, edit))

    def test_refuses_tampering_unknown_schema_effects_and_references(self):
        def bad_outer_digest(data):
            data["content_sha256"] = "0" * 64
        with self.assertRaisesRegex(ArenaHistoryRejected, "digest mismatch"):
            decode_arena_history_prefix(_wire_with_edit(
                self.prefix, bad_outer_digest, resign=False))

        def bad_source_digest(data):
            data["npc_bindings"][0]["source_sha256"] = "0" * 64
        with self.assertRaisesRegex(ArenaHistoryRejected, "source bytes, digest"):
            decode_arena_history_prefix(_wire_with_edit(self.prefix, bad_source_digest))

        def tampered_source_bytes(data):
            data["npc_bindings"][0]["source_bytes_base64"] = base64.b64encode(b"not NPC JSON").decode("ascii")
        with self.assertRaisesRegex(ArenaHistoryRejected, "NPC source record is invalid"):
            decode_arena_history_prefix(_wire_with_edit(self.prefix, tampered_source_bytes))

        def swapped_binding(data):
            left, right = data["npc_bindings"]
            left["native_being_id"], right["native_being_id"] = (
                right["native_being_id"], left["native_being_id"])
        with self.assertRaisesRegex(ArenaHistoryRejected, "binding identity"):
            decode_arena_history_prefix(_wire_with_edit(self.prefix, swapped_binding))

        def unsupported_version(data):
            data["schema"] = "universe.arena.detached-spot-history-prefix/2"
        with self.assertRaisesRegex(ArenaHistoryRejected, "unsupported Arena prefix schema"):
            decode_arena_history_prefix(_wire_with_edit(self.prefix, unsupported_version))

        def unsupported_effect(data):
            data["effects"][0]["kind"] = "unknown-effect"
        with self.assertRaises(ArenaHistoryRejected):
            decode_arena_history_prefix(_wire_with_edit(self.prefix, unsupported_effect))

        def duplicate_effect_identity(data):
            data["effects"][1]["identity"] = list(data["effects"][0]["identity"])
        with self.assertRaises(ArenaHistoryRejected):
            decode_arena_history_prefix(_wire_with_edit(self.prefix, duplicate_effect_identity))

        def forged_actor(data):
            data["spot"]["actor_id"] = "arena/being/hidden"
        with self.assertRaises(ArenaHistoryRejected):
            decode_arena_history_prefix(_wire_with_edit(self.prefix, forged_actor))

    def test_refuses_failed_or_non_six_boundary_spot_without_mutation(self):
        failed = build_arena(die_roll=1)
        before = (failed["encounter"].time,
                  tuple(failed["encounter"]._atomic_interval_history),
                  failed["rng"].state)
        with self.assertRaisesRegex(ArenaHistoryRejected, "successful native six-second Spot"):
            capture_arena_history_prefix(failed)
        self.assertEqual(before, (failed["encounter"].time,
                                  tuple(failed["encounter"]._atomic_interval_history),
                                  failed["rng"].state))

        unstarted = build_arena(resolve=False)
        before = (unstarted["encounter"].time,
                  tuple(unstarted["encounter"].__dict__.get("_atomic_interval_history", ())),
                  unstarted["rng"].state)
        with self.assertRaisesRegex(ArenaHistoryRejected, "six committed native Arena boundaries"):
            capture_arena_history_prefix(unstarted)
        self.assertEqual(before, (unstarted["encounter"].time,
                                  tuple(unstarted["encounter"].__dict__.get("_atomic_interval_history", ())),
                                  unstarted["rng"].state))


if __name__ == "__main__":
    unittest.main()
