import base64
from dataclasses import FrozenInstanceError, replace
import hashlib
import json
import os
from pathlib import Path
import pickle
import random
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import atomic_publication
from arena_history_admission import (
    ArenaAdmissionRejected, ExpectedArenaBinding, ExpectedArenaScenario,
    _host_authorize_arena_history, _prepare_arena_history_view,
)
from arena_history_prefix import capture_arena_history_prefix
from arena_state_candidate import (
    ArenaPostSpotStateCandidate, ArenaStateRejected,
    capture_arena_post_spot_state, decode_arena_post_spot_state,
)
from arena_state_admission import (
    ArenaStateAdmissionRejected, ExpectedArenaSource,
    _host_authorize_arena_state, _prepare_arena_state, _private_native_beings,
)
from examples.npc_encounter_arena import build_arena


def _scenario():
    return ExpectedArenaScenario(
        "0", "npc-arena/encounter/1", "npc-arena/action/spot-ari-bex",
        "arena/being/ari", "arena/being/bex", "0x0.0p+0", 6)


def _bindings(prefix):
    return tuple(ExpectedArenaBinding(
        row["binding_key"], row["source_sha256"], row["display_name"],
        row["native_being_id"], row["native_definition_name"], tuple(row["position"]))
        for row in prefix.payload()["npc_bindings"])


def _source_bytes():
    return tuple(ExpectedArenaSource(
        f"arena-{name}", (ROOT / "examples" / "npc_candidates" / f"{name}.npcgen.json").read_bytes())
        for name in ("ari", "bex"))


def _prepared_history(prefix):
    bindings = _bindings(prefix)
    token = _host_authorize_arena_history(
        prefix, expected_content_sha256=prefix.content_sha256,
        expected_scenario=_scenario(), expected_bindings=bindings)
    return _prepare_arena_history_view(prefix, token)


def _authorize(candidate, prefix, history, sources=None):
    return _host_authorize_arena_state(
        candidate, prefix, history, expected_content_sha256=candidate.content_sha256,
        expected_scenario=_scenario(), expected_bindings=_bindings(prefix),
        expected_sources=_source_bytes() if sources is None else sources)


def _prepare(candidate, prefix, history, token, sources=None):
    return _prepare_arena_state(
        candidate, prefix, history, token, expected_content_sha256=candidate.content_sha256,
        expected_scenario=_scenario(), expected_bindings=_bindings(prefix),
        expected_sources=_source_bytes() if sources is None else sources)


class ArenaStateAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.source = build_arena(die_roll=20)
        self.encounter = self.source["encounter"]
        self.prefix = capture_arena_history_prefix(self.source)
        self.candidate = capture_arena_post_spot_state(self.source, self.prefix)
        self.history = _prepared_history(self.prefix)

    def test_explicit_admission_reconstructs_private_quarantined_beings(self):
        token = _authorize(self.candidate, self.prefix, self.history)
        result = _prepare(self.candidate, self.prefix, self.history, token)
        self.assertEqual(result.view.schema, "universe.arena.host-accepted-quarantined-being-state/1")
        self.assertIn("host-accepted post-Spot state claim", result.view.trust)
        self.assertEqual(result.logical_ids, ("arena/being/ari", "arena/being/bex"))
        self.assertEqual((result.view.time, result.view.committed_boundary), (6.0, 6))
        self.assertEqual(tuple((row.being_id, row.hit_points, row.position_hex,
                                row.geometry_kind, row.geometry_radius_hex, row.quarantined)
                               for row in result.view.beings), (
            ("arena/being/ari", 10, ("0x0.0p+0",) * 3, "Sphere", "0x1.0000000000000p-1", True),
            ("arena/being/bex", 10, ("0x1.8000000000000p+1", "0x0.0p+0", "0x0.0p+0"),
             "Sphere", "0x1.0000000000000p-1", True)))
        self.assertEqual(result.view.history_view.observer_view("arena/being/ari").aware_of,
                         ("arena/being/bex",))
        self.assertEqual(result.view.history_view.observer_view("arena/being/bex").aware_of, ())
        self.assertEqual(result.view.candidate_state_view.participants[0].aware_of,
                         ("arena/being/bex",))
        self.assertIn("NO LIVE ENCOUNTER OR CONTINUATION", result.view.continuation)
        self.assertFalse(hasattr(result, "step"))
        self.assertFalse(hasattr(result, "accept_choice"))
        self.assertFalse(hasattr(result.view, "encounter"))
        self.assertFalse(any(type(value).__name__ == "BeingInstance"
                             for value in vars(result).values()))
        with self.assertRaises(FrozenInstanceError):
            result.view.time = 7
        with self.assertRaises(FrozenInstanceError):
            result.view.beings[0].hit_points = 1
        private = _private_native_beings(result)
        self.assertEqual(tuple(type(value).__name__ for value in private),
                         ("BeingInstance", "BeingInstance"))
        self.assertTrue(all(value.id in result.logical_ids for value in private))
        self.assertTrue(all(value._checkpoint_quarantined is True for value in private))
        self.assertIs(private[0].original, private[1].original)
        self.assertIsNot(private[0].current, private[1].current)

    def test_native_admission_does_not_mutate_source_encounter_rng_or_receipts(self):
        world = self.encounter.universe
        beings = tuple(world.get_object_by_id(identity)
                       for identity in ("arena/being/ari", "arena/being/bex"))
        containers = (world.object_registry.object_instances, self.encounter.being_list,
                      self.encounter.pending_action_list, self.encounter.finished_action_list,
                      self.encounter.awareness, self.encounter._atomic_interval_history,
                      self.encounter._choice_book._choices)
        before = (
            tuple(id(row) for row in (world, self.encounter, *beings, *containers)),
            tuple((being.get_hit_points(), being.get_position().as_tuple(),
                   tuple(self.encounter.awareness[being.id]), len(being._atomic_target_history))
                  for being in beings), self.source["rng"].state, random.getstate(),
            dict(atomic_publication._COMMITTED_RECEIPTS),
            tuple(sorted(world.object_registry.object_instances)),
        )
        result = _prepare(self.candidate, self.prefix, self.history,
                          _authorize(self.candidate, self.prefix, self.history))
        after = (
            tuple(id(row) for row in (world, self.encounter, *beings, *containers)),
            tuple((being.get_hit_points(), being.get_position().as_tuple(),
                   tuple(self.encounter.awareness[being.id]), len(being._atomic_target_history))
                  for being in beings), self.source["rng"].state, random.getstate(),
            dict(atomic_publication._COMMITTED_RECEIPTS),
            tuple(sorted(world.object_registry.object_instances)),
        )
        self.assertEqual(after, before)
        self.assertEqual(result.view.rng_role, "caller_cursor")
        self.assertIn("not portable", result.view.rng_scope)

    def test_b1_history_alone_cannot_authorize_b2_native_state(self):
        prefix_token = _host_authorize_arena_history(
            self.prefix, expected_content_sha256=self.prefix.content_sha256,
            expected_scenario=_scenario(), expected_bindings=_bindings(self.prefix))
        with self.assertRaises(ArenaStateAdmissionRejected):
            _prepare_arena_state(self.candidate, self.prefix, self.history, prefix_token,
                expected_content_sha256=self.candidate.content_sha256,
                expected_scenario=_scenario(), expected_bindings=_bindings(self.prefix),
                expected_sources=_source_bytes())
        forged_view = replace(self.history)
        with self.assertRaises(ArenaStateAdmissionRejected):
            _authorize(self.candidate, self.prefix, forged_view)

    def test_capability_is_nonserializable_single_use_and_consumed_on_failed_attempt(self):
        token = _authorize(self.candidate, self.prefix, self.history)
        with self.assertRaises(TypeError):
            pickle.dumps(token)
        alternate = ArenaPostSpotStateCandidate(self.candidate.to_bytes())
        with self.assertRaises(ArenaStateAdmissionRejected):
            _prepare(alternate, self.prefix, self.history, token)
        with self.assertRaises(ArenaStateAdmissionRejected):
            _prepare(self.candidate, self.prefix, self.history, token)

    def test_tampered_exact_candidate_after_approval_consumes_capability(self):
        token = _authorize(self.candidate, self.prefix, self.history)
        original = self.candidate._wire
        digest = self.candidate.content_sha256
        object.__setattr__(self.candidate, "_wire", original + b" ")
        try:
            with self.assertRaises(ArenaStateAdmissionRejected):
                _prepare_arena_state(self.candidate, self.prefix, self.history, token,
                    expected_content_sha256=digest, expected_scenario=_scenario(),
                    expected_bindings=_bindings(self.prefix), expected_sources=_source_bytes())
            with self.assertRaises(ArenaStateAdmissionRejected):
                _prepare_arena_state(self.candidate, self.prefix, self.history, token,
                    expected_content_sha256=digest, expected_scenario=_scenario(),
                    expected_bindings=_bindings(self.prefix), expected_sources=_source_bytes())
        finally:
            object.__setattr__(self.candidate, "_wire", original)

    def test_source_bytes_must_match_host_expectations_history_and_candidate(self):
        correct = list(_source_bytes())
        bad = (ExpectedArenaSource(correct[0].binding_key, b"changed local source"), correct[1])
        with self.assertRaises(ArenaStateAdmissionRejected):
            _authorize(self.candidate, self.prefix, self.history, tuple(bad))
        wrong_binding = (ExpectedArenaBinding(
            "arena-ari", "0" * 64, "Ari", "arena/being/ari", "Human", ("0x0.0p+0",) * 3),
            _bindings(self.prefix)[1])
        with self.assertRaises(ArenaStateAdmissionRejected):
            _host_authorize_arena_state(self.candidate, self.prefix, self.history,
                expected_content_sha256=self.candidate.content_sha256,
                expected_scenario=_scenario(), expected_bindings=wrong_binding,
                expected_sources=_source_bytes())

    def test_changed_geometry_candidate_refuses_before_native_construction(self):
        data = json.loads(self.candidate.to_bytes())
        data["participants"][0]["geometry"]["radius_hex"] = float(0.6).hex()
        body = dict(data)
        body.pop("content_sha256")
        data["content_sha256"] = hashlib.sha256(json.dumps(
            body, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
            allow_nan=False).encode("utf-8")).hexdigest()
        changed = json.dumps(data, ensure_ascii=False, sort_keys=True,
            separators=(",", ":"), allow_nan=False).encode("utf-8")
        with self.assertRaises(ArenaStateRejected):
            decode_arena_post_spot_state(changed)

    def test_candidate_state_requires_exact_history_object_and_consumes_on_mismatch(self):
        token = _authorize(self.candidate, self.prefix, self.history)
        with self.assertRaises(ArenaStateAdmissionRejected):
            _prepare(self.candidate, self.prefix, object(), token)
        with self.assertRaises(ArenaStateAdmissionRejected):
            _prepare(self.candidate, self.prefix, self.history, token)

    def test_fresh_process_demo_constructs_native_beings_without_encounter_or_publisher(self):
        result = subprocess.run(
            [sys.executable, "examples/arena_state_admission.py"], cwd=ROOT,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            capture_output=True, text=True, check=True)
        self.assertIn("Process B reconstructed quarantined native BeingInstances", result.stdout)
        self.assertIn('"committed_boundary": 6', result.stdout)
        self.assertIn('"quarantined": true', result.stdout)
        self.assertIn("NO LIVE ENCOUNTER OR CONTINUATION", result.stdout)
        self.assertIn('"ari_aware_of": [', result.stdout)
        self.assertIn('"bex_aware_of": []', result.stdout)


if __name__ == "__main__":
    unittest.main()
