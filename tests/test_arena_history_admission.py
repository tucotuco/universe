"""Host-local one-shot admission for detached Arena Spot history only."""
from dataclasses import FrozenInstanceError, replace
import base64
import hashlib
import json
from pathlib import Path
import pickle
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from arena_history_admission import (
    ArenaAdmissionRejected,
    ExpectedArenaBinding,
    ExpectedArenaScenario,
    VIEW_SCHEMA,
    VIEW_TRUST,
    _host_authorize_arena_history,
    _prepare_arena_history_view,
)
from arena_history_prefix import (
    ArenaHistoryRejected,
    capture_arena_history_prefix,
    decode_arena_history_prefix,
)
from examples.npc_encounter_arena import build_arena


EXPECTED = (
    ExpectedArenaBinding(
        "arena-ari",
        "fbbee87dab9b7047b13ee11bb4ad37385779381f60d1dfc3c230afc5251befde",
        "Ari", "arena/being/ari", "Human",
        ("0x0.0p+0", "0x0.0p+0", "0x0.0p+0")),
    ExpectedArenaBinding(
        "arena-bex",
        "9da574a288bd4f62832324e30c38426c9e666988628e2989c713db28c8007570",
        "Bex", "arena/being/bex", "Human",
        ("0x1.8000000000000p+1", "0x0.0p+0", "0x0.0p+0")),
)
EXPECTED_SCENARIO = ExpectedArenaScenario(
    "0", "npc-arena/encounter/1", "npc-arena/action/spot-ari-bex",
    "arena/being/ari", "arena/being/bex", "0x0.0p+0", 6)


class ArenaHistoryAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.scenario = build_arena(die_roll=20)
        self.encounter = self.scenario["encounter"]
        self.prefix = capture_arena_history_prefix(self.scenario)
        self.wire = self.prefix.to_bytes()

    def _state(self):
        import atomic_publication
        world = self.encounter.universe
        beings = []
        for row in self.scenario["candidate_bindings"]:
            being = world.get_object_by_id(row.native_being_id)
            beings.append((
                id(being), being.id, id(being.current), repr(being.current.__dict__),
                repr(being._atomic_target_history), repr(being.skill_use_history),
                repr(being.skill_experience),
            ))
        book = self.encounter._choice_book
        choice_state = (
            id(book), book._counter,
            tuple((key, repr(value)) for key, value in book._choices.items()),
            tuple(sorted(book._states.items())),
            repr(book._reservations),
        )
        return (
            self.encounter.time,
            self.encounter.last_processed_boundary,
            tuple(self.encounter._atomic_interval_history),
            tuple(self.encounter.pending_action_list),
            tuple(self.encounter.finished_action_list),
            tuple(self.encounter.cancelled_action_list),
            self.scenario["rng"].state,
            tuple(sorted((key, tuple(value)) for key, value in self.encounter.awareness.items())),
            tuple(sorted((key, tuple(position.as_tuple()) if position else None)
                         for key, position in ((row.native_being_id, world.get_object_by_id(
                             row.native_being_id).get_position())
                                               for row in self.scenario["candidate_bindings"]))),
            tuple(beings),
            choice_state,
            tuple(sorted((key, id(value)) for key, value in world.object_registry.object_instances.items())),
            dict(atomic_publication._COMMITTED_RECEIPTS),
        )

    def _approve(self, *, prefix=None, digest=None, bindings=EXPECTED):
        prefix = self.prefix if prefix is None else prefix
        digest = prefix.content_sha256 if digest is None else digest
        return _host_authorize_arena_history(
            prefix, expected_content_sha256=digest,
            expected_scenario=EXPECTED_SCENARIO, expected_bindings=bindings)

    def test_explicit_approval_yields_detached_immutable_readonly_host_view(self):
        before = self._state()
        capability = self._approve()
        self.assertNotIn("arena/being/", repr(capability).lower())
        self.assertNotIn("fbbee87d", repr(capability))
        with self.assertRaises(TypeError):
            pickle.dumps(capability)
        with self.assertRaises(TypeError):
            json.dumps(capability)
        view = _prepare_arena_history_view(self.prefix, capability)
        self.assertEqual(self._state(), before)
        self.assertEqual(view.schema, VIEW_SCHEMA)
        self.assertEqual(view.trust, VIEW_TRUST)
        self.assertIn("detached historical claim", view.source_trust)
        self.assertEqual(view.boundaries, (1, 2, 3, 4, 5, 6))
        self.assertEqual(view.spot.resolved_boundary, 6)
        self.assertEqual(view.spot.outcome, "success")
        self.assertEqual(dict(view.spot.metadata)["roll"], 20)
        self.assertEqual(tuple(row.native_being_id for row in view.npc_bindings),
                         ("arena/being/ari", "arena/being/bex"))
        self.assertEqual(tuple(row.source_bytes for row in view.npc_bindings),
                         tuple(row.source_bytes for row in self.prefix_bindings()))
        self.assertFalse(hasattr(view, "encounter"))
        self.assertFalse(hasattr(view, "step"))
        self.assertFalse(hasattr(view, "restore_verified"))
        with self.assertRaises(FrozenInstanceError):
            view.through_boundary = 5
        summary = view.host_summary()
        summary["targets"].clear()
        self.assertEqual(len(view.targets), 2)

    def prefix_bindings(self):
        from base64 import b64decode
        from arena_history_admission import ArenaHistoricalBinding
        return tuple(ArenaHistoricalBinding(
            row["binding_key"], row["source_sha256"],
            b64decode(row["source_bytes_base64"]), row["display_name"],
            row["native_being_id"], row["native_definition_name"],
            tuple(row["position"]))
            for row in self.prefix.payload()["npc_bindings"])

    def test_host_policy_must_select_exact_digest_and_bindings(self):
        with self.assertRaisesRegex(ArenaAdmissionRejected, "host-selected digest"):
            self._approve(digest="0" * 64)
        changed = (replace(EXPECTED[0], source_sha256="0" * 64), EXPECTED[1])
        with self.assertRaisesRegex(ArenaAdmissionRejected, "differ from host expectations"):
            self._approve(bindings=changed)
        wrong_scenario = replace(EXPECTED_SCENARIO, encounter_id="npc-arena/encounter/other")
        with self.assertRaisesRegex(ArenaAdmissionRejected, "expected scenario is outside"):
            _host_authorize_arena_history(
                self.prefix, expected_content_sha256=self.prefix.content_sha256,
                expected_scenario=wrong_scenario, expected_bindings=EXPECTED)
        with self.assertRaisesRegex(ArenaAdmissionRejected, "exactly two expected"):
            self._approve(bindings=EXPECTED[:1])
        with self.assertRaisesRegex(ArenaAdmissionRejected, "process-local host admission"):
            _prepare_arena_history_view(self.prefix, object())
        from arena_history_admission import _ArenaAdmissionCapability
        with self.assertRaisesRegex(ArenaAdmissionRejected, "foreign, stale, or already consumed"):
            _prepare_arena_history_view(self.prefix, _ArenaAdmissionCapability())

    def test_single_use_exact_object_and_tamper_refusals(self):
        capability = self._approve()
        equivalent_but_foreign_object = decode_arena_history_prefix(self.wire)
        with self.assertRaisesRegex(ArenaAdmissionRejected, "different validated prefix object"):
            _prepare_arena_history_view(equivalent_but_foreign_object, capability)
        with self.assertRaisesRegex(ArenaAdmissionRejected, "already consumed"):
            _prepare_arena_history_view(self.prefix, capability)

        capability = self._approve()
        object.__setattr__(self.prefix, "content_sha256", "0" * 64)
        with self.assertRaisesRegex(ArenaAdmissionRejected, "failed revalidation"):
            _prepare_arena_history_view(self.prefix, capability)
        with self.assertRaisesRegex(ArenaAdmissionRejected, "already consumed"):
            _prepare_arena_history_view(self.prefix, capability)

    def test_owner_filtered_awareness_and_no_automatic_belief(self):
        before = self._state()
        view = _prepare_arena_history_view(self.prefix, self._approve())
        ari = view.observer_view("arena/being/ari")
        bex = view.observer_view("arena/being/bex")
        self.assertEqual(ari.aware_of, ("arena/being/bex",))
        self.assertEqual(bex.aware_of, ())
        self.assertEqual(ari.trust, VIEW_TRUST)
        self.assertFalse(hasattr(ari, "position_hex"))
        with self.assertRaisesRegex(ArenaAdmissionRejected, "not a participant"):
            view.observer_view("arena/being/third-party")
        self.assertEqual(self._state(), before)

    def test_corrupt_version_effect_or_chronology_never_gets_host_admission(self):
        for edit in (
                lambda d: d.__setitem__("schema", "universe.arena.detached-spot-history-prefix/99"),
                lambda d: d["effects"][0].__setitem__("kind", "unsupported"),
                lambda d: d["boundaries"].reverse(),
                lambda d: d["npc_bindings"][0].__setitem__("native_being_id", "arena/being/other")):
            data = json.loads(self.wire)
            edit(data)
            raw = json.dumps(data, sort_keys=True, separators=(",", ":")).encode()
            with self.subTest(edit=edit), self.assertRaises(ArenaHistoryRejected):
                decode_arena_history_prefix(raw)

        data = json.loads(self.wire)
        source_row = data["npc_bindings"][0]
        source = json.loads(base64.b64decode(source_row["source_bytes_base64"]))
        source["generation"]["seed"] += 1
        source["state"]["seed"] += 1
        source_bytes = json.dumps(source, indent=2).encode("utf-8")
        source_row["source_bytes_base64"] = base64.b64encode(source_bytes).decode("ascii")
        source_row["source_sha256"] = hashlib.sha256(source_bytes).hexdigest()
        payload = dict(data)
        payload.pop("content_sha256")
        data["content_sha256"] = hashlib.sha256(json.dumps(
            payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        altered_source = decode_arena_history_prefix(json.dumps(
            data, sort_keys=True, separators=(",", ":"), allow_nan=False).encode())
        with self.assertRaisesRegex(ArenaAdmissionRejected, "differ from host expectations"):
            self._approve(prefix=altered_source)

        changed = json.loads(self.wire)
        changed["encounter_id"] = "npc-arena/encounter/forged"
        for effect in changed["effects"]:
            effect["identity"][0] = changed["encounter_id"]
        changed["boundaries"][5]["effect_ids"] = [
            row["identity"] for row in changed["effects"]]
        payload = dict(changed)
        payload.pop("content_sha256")
        changed["content_sha256"] = hashlib.sha256(json.dumps(
            payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        wrong_scenario = decode_arena_history_prefix(json.dumps(
            changed, sort_keys=True, separators=(",", ":"), allow_nan=False).encode())
        with self.assertRaisesRegex(ArenaAdmissionRejected, "host-selected scenario"):
            self._approve(prefix=wrong_scenario)

    def test_fresh_process_host_approval_does_not_import_native_publisher(self):
        child = r'''
import json,sys
sys.path.insert(0,sys.argv[1])
from arena_history_prefix import decode_arena_history_prefix
from arena_history_admission import ExpectedArenaBinding,ExpectedArenaScenario,_host_authorize_arena_history,_prepare_arena_history_view
assert 'atomic_publication' not in sys.modules and 'encounter' not in sys.modules
assert 'checkpoint_restore_preparation' not in sys.modules
assert 'checkpoint_inventory' not in sys.modules
p=decode_arena_history_prefix(sys.stdin.buffer.read())
expected=(
 ExpectedArenaBinding('arena-ari','fbbee87dab9b7047b13ee11bb4ad37385779381f60d1dfc3c230afc5251befde','Ari','arena/being/ari','Human',('0x0.0p+0','0x0.0p+0','0x0.0p+0')),
 ExpectedArenaBinding('arena-bex','9da574a288bd4f62832324e30c38426c9e666988628e2989c713db28c8007570','Bex','arena/being/bex','Human',('0x1.8000000000000p+1','0x0.0p+0','0x0.0p+0')))
scenario=ExpectedArenaScenario('0','npc-arena/encounter/1','npc-arena/action/spot-ari-bex','arena/being/ari','arena/being/bex','0x0.0p+0',6)
try:
 _prepare_arena_history_view(p,None)
except ValueError: pass
else: raise AssertionError('digest/decoded data alone must not authorize')
t=_host_authorize_arena_history(p,expected_content_sha256=p.content_sha256,expected_scenario=scenario,expected_bindings=expected)
v=_prepare_arena_history_view(p,t)
assert 'atomic_publication' not in sys.modules and 'encounter' not in sys.modules
print(json.dumps(v.host_summary(),sort_keys=True,separators=(',',':')))
'''
        proc = subprocess.run(
            [sys.executable, "-c", child, str(ROOT / "src")],
            input=self.wire, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            cwd=ROOT, check=False)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8", errors="replace"))
        output = json.loads(proc.stdout)
        self.assertEqual(output["boundaries"], [1, 2, 3, 4, 5, 6])
        self.assertIn("not a live restored Encounter", output["continuation"])
        self.assertEqual(output["trust"], VIEW_TRUST)
        self.assertEqual(output["spot"]["outcome"], "success")


if __name__ == "__main__":
    unittest.main()
