import base64
import hashlib
import json
import os
from dataclasses import FrozenInstanceError
from pathlib import Path
import random
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import atomic_publication
from arena_history_admission import (
    ExpectedArenaBinding, ExpectedArenaScenario, _host_authorize_arena_history,
    _prepare_arena_history_view,
)
from arena_history_prefix import capture_arena_history_prefix, decode_arena_history_prefix
from arena_state_candidate import (
    ArenaStateRejected, capture_arena_post_spot_state,
    decode_arena_post_spot_state, validate_arena_post_spot_state,
)
from examples.npc_encounter_arena import build_arena


def _approval(summary, prefix):
    scenario = ExpectedArenaScenario(
        "0", "npc-arena/encounter/1", "npc-arena/action/spot-ari-bex",
        "arena/being/ari", "arena/being/bex", "0x0.0p+0", 6)
    bindings = tuple(ExpectedArenaBinding(
        row.binding_key, summary["candidates"][key].content_sha256,
        row.display_name, row.native_being_id, row.native_definition_name,
        tuple(float(value).hex() for value in row.position))
        for key, row in zip(("ari", "bex"), summary["candidate_bindings"]))
    token = _host_authorize_arena_history(
        prefix, expected_content_sha256=prefix.content_sha256,
        expected_scenario=scenario, expected_bindings=bindings)
    return _prepare_arena_history_view(prefix, token)


def _reseal(payload):
    payload = json.loads(json.dumps(payload))
    payload.pop("content_sha256", None)
    body = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")
    payload["content_sha256"] = hashlib.sha256(body).hexdigest()
    return json.dumps(payload, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


class ArenaStateCandidateTests(unittest.TestCase):
    def setUp(self):
        self.scenario = build_arena(die_roll=20)
        self.prefix = capture_arena_history_prefix(self.scenario)
        self.candidate = capture_arena_post_spot_state(self.scenario, self.prefix)

    def test_detached_candidate_round_trip_and_expected_native_state(self):
        wire = self.candidate.to_bytes()
        decoded = decode_arena_post_spot_state(wire)
        self.assertEqual(decoded.to_bytes(), wire)
        self.assertEqual(decoded.content_sha256, self.candidate.content_sha256)
        view = validate_arena_post_spot_state(decoded, self.prefix,
                                               _approval(self.scenario, self.prefix))
        self.assertEqual((view.start_time, view.time, view.committed_boundary), (0, 6, 6))
        self.assertEqual(tuple(row.being_id for row in view.participants),
                         ("arena/being/ari", "arena/being/bex"))
        ari, bex = view.participants
        self.assertEqual(ari.position_hex, ("0x0.0p+0",) * 3)
        self.assertEqual(bex.position_hex, ("0x1.8000000000000p+1", "0x0.0p+0", "0x0.0p+0"))
        self.assertEqual(ari.geometry, ("Sphere", "0x1.0000000000000p-1"))
        self.assertEqual(ari.hit_points, 10)
        self.assertEqual(ari.aware_of, ("arena/being/bex",))
        self.assertEqual(bex.aware_of, ())
        self.assertEqual(ari.target_history_boundaries, (1, 2, 3, 4, 5, 6))
        self.assertEqual(view.rng_role, "caller_cursor")
        self.assertIn("not portable", view.rng_scope)
        self.assertIn("cannot continue", view.continuation)
        self.assertEqual(set(vars(self.candidate)), {"_wire"})
        with self.assertRaises(FrozenInstanceError):
            view.time = 9

    def test_candidate_capture_does_not_change_live_state_rng_or_receipts(self):
        encounter = self.scenario["encounter"]
        world = encounter.universe
        beings = tuple(world.get_object_by_id(identity)
                       for identity in ("arena/being/ari", "arena/being/bex"))
        containers = (world.object_registry.object_instances, encounter.being_list,
                      encounter.pending_action_list, encounter.finished_action_list,
                      encounter.awareness, encounter._atomic_interval_history,
                      encounter._choice_book._choices)
        before = (
            tuple(id(row) for row in (world, encounter, *beings, *containers)),
            tuple((being.get_hit_points(), being.get_position().as_tuple(),
                   tuple(encounter.awareness[being.id]), len(being._atomic_target_history),
                   tuple(being.skill_use_history), dict(being.skill_experience)) for being in beings),
            self.scenario["rng"].state, random.getstate(),
            dict(atomic_publication._COMMITTED_RECEIPTS),
        )
        recaptured = capture_arena_post_spot_state(self.scenario, self.prefix)
        after = (
            tuple(id(row) for row in (world, encounter, *beings, *containers)),
            tuple((being.get_hit_points(), being.get_position().as_tuple(),
                   tuple(encounter.awareness[being.id]), len(being._atomic_target_history),
                   tuple(being.skill_use_history), dict(being.skill_experience)) for being in beings),
            self.scenario["rng"].state, random.getstate(),
            dict(atomic_publication._COMMITTED_RECEIPTS),
        )
        self.assertEqual(after, before)
        self.assertEqual(recaptured.to_bytes(), self.candidate.to_bytes())

    def test_candidate_is_consistent_only_with_its_exact_history_prefix(self):
        payload = self.prefix.payload()
        source_row = payload["npc_bindings"][0]
        source = json.loads(base64.b64decode(source_row["source_bytes_base64"]))
        source["notes"]["general"] = "independently host-selected test source"
        changed_bytes = json.dumps(source, sort_keys=True, separators=(",", ":")).encode("utf-8")
        source_row["source_bytes_base64"] = base64.b64encode(changed_bytes).decode("ascii")
        source_row["source_sha256"] = hashlib.sha256(changed_bytes).hexdigest()
        other_prefix = decode_arena_history_prefix(_reseal(payload))
        scenario = ExpectedArenaScenario(
            "0", "npc-arena/encounter/1",
            "npc-arena/action/spot-ari-bex", "arena/being/ari",
            "arena/being/bex", "0x0.0p+0", 6)
        original = self.scenario["candidate_bindings"]
        bindings = (
            ExpectedArenaBinding("arena-ari", source_row["source_sha256"], "Ari",
                "arena/being/ari", "Human", ("0x0.0p+0",) * 3),
            ExpectedArenaBinding("arena-bex", self.scenario["candidates"]["bex"].content_sha256,
                original[1].display_name, original[1].native_being_id,
                original[1].native_definition_name,
                tuple(float(value).hex() for value in original[1].position)),
        )
        token = _host_authorize_arena_history(
            other_prefix, expected_content_sha256=other_prefix.content_sha256,
            expected_scenario=scenario, expected_bindings=bindings)
        other_view = _prepare_arena_history_view(other_prefix, token)
        with self.assertRaises(ArenaStateRejected):
            validate_arena_post_spot_state(self.candidate, other_prefix, other_view)
        with self.assertRaises(ArenaStateRejected):
            validate_arena_post_spot_state(self.candidate, self.prefix, other_view)

    def test_integrity_tampering_and_unknown_schema_fail_closed(self):
        wire = self.candidate.to_bytes()
        tampered = bytearray(wire)
        tampered[len(tampered) // 2] ^= 1
        with self.assertRaises(ArenaStateRejected):
            decode_arena_post_spot_state(bytes(tampered))
        data = json.loads(wire)
        data["schema"] = "universe.arena.detached-post-spot-state-candidate/99"
        with self.assertRaises(ArenaStateRejected):
            decode_arena_post_spot_state(_reseal(data))
        data = json.loads(wire)
        data["unreviewed"] = True
        with self.assertRaises(ArenaStateRejected):
            decode_arena_post_spot_state(_reseal(data))

    def test_invalid_geometry_and_graph_adapter_changes_fail_closed_even_when_resealed(self):
        data = json.loads(self.candidate.to_bytes())
        data["participants"][0]["geometry"]["radius_hex"] = float(0.6).hex()
        with self.assertRaises(ArenaStateRejected):
            decode_arena_post_spot_state(_reseal(data))
        data = json.loads(self.candidate.to_bytes())
        native_type = next(node for node in data["native_data_graph"]["nodes"]
                           if node[1] == "being.BeingDefinition")
        native_type[1] = "unreviewed.Extension"
        with self.assertRaises(ArenaStateRejected):
            decode_arena_post_spot_state(_reseal(data))

    def test_extra_or_open_schedule_state_refuses_capture(self):
        encounter = self.scenario["encounter"]
        encounter.pending_action_list.append("unapproved/future-action")
        try:
            with self.assertRaises(ArenaStateRejected):
                capture_arena_post_spot_state(self.scenario, self.prefix)
        finally:
            encounter.pending_action_list.clear()

    def test_unreviewed_live_fields_and_extra_universe_state_refuse_capture(self):
        encounter = self.scenario["encounter"]
        world = encounter.universe
        being = world.get_object_by_id("arena/being/ari")
        mutations = (
            (encounter, "_unreviewed_live_field", True),
            (being, "_unreviewed_live_field", True),
            (world, "_unreviewed_live_field", True),
        )
        for owner, field, value in mutations:
            setattr(owner, field, value)
            try:
                with self.subTest(owner=type(owner).__name__), self.assertRaises(ArenaStateRejected):
                    capture_arena_post_spot_state(self.scenario, self.prefix)
            finally:
                delattr(owner, field)

    def test_nonempty_reproduction_registry_is_rejected_without_mutation(self):
        registry = self.scenario["encounter"].universe._reproduction_group_registry
        registry._generation_requests["unreviewed"] = object()
        try:
            with self.assertRaises(ArenaStateRejected):
                capture_arena_post_spot_state(self.scenario, self.prefix)
            self.assertEqual(set(registry._generation_requests), {"unreviewed"})
        finally:
            registry._generation_requests.clear()

    def test_mismatched_source_binding_refuses_candidate(self):
        data = json.loads(self.candidate.to_bytes())
        altered = b"different"
        data["source_bindings"][0]["source_bytes_base64"] = base64.b64encode(altered).decode("ascii")
        data["source_bindings"][0]["source_sha256"] = hashlib.sha256(altered).hexdigest()
        forged = decode_arena_post_spot_state(_reseal(data))
        with self.assertRaises(ArenaStateRejected):
            validate_arena_post_spot_state(forged, self.prefix,
                                           _approval(self.scenario, self.prefix))

    def test_fresh_process_example_checks_b1_history_without_native_restore(self):
        result = subprocess.run(
            [sys.executable, "examples/arena_state_candidate.py"], cwd=ROOT,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            capture_output=True, text=True, check=True)
        self.assertIn("Process B decoded and checked", result.stdout)
        self.assertIn('"committed_boundary": 6', result.stdout)
        self.assertIn('"kind": "Sphere"', result.stdout)
        self.assertIn("host approval applies only to the exact history prefix", result.stdout)
        self.assertIn("NOT a live restored Encounter; cannot continue", result.stdout)


if __name__ == "__main__":
    unittest.main()
