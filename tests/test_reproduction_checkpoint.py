"""Versioned reproduction-only checkpoint and continuation tests."""
import hashlib
import json
from pathlib import Path
import random
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from reproduction_checkpoint import (
    RESTORE_FAILURE_PHASES,
    ReproductionCheckpointRestoreError, ReproductionCheckpointValidationError,
    decode_reproduction_checkpoint, encode_reproduction_checkpoint,
    logical_reproduction_checkpoint_digest, restore_reproduction_checkpoint,
)
from reproduction_generation import (
    ProgressiveReproductionRequest, StatisticalReproductionRequest,
    TestOnlyIntervalReproductionProfile, TestOnlyOffspringCountDistribution,
)
from reproduction_group import (
    InjectedReproductionGroupFailure, ReproductionGroupProposal, prepare_reproduction_group,
)
from library import Library
from universe import Universe


def make_world(name="checkpoint test"):
    return Universe(name, library=Library(config_dir=str(ROOT / "src/config")))


PROFILE = TestOnlyIntervalReproductionProfile(
    "u-rel-001v4-test", "1", ((0, 1), (1, 2), (2, 3))
)
ZERO_POSITIVE = TestOnlyIntervalReproductionProfile(
    "u-rel-001v4-zero-positive-test", "1", ((0, 1), (1, 1))
)


def progressive(world, parents, seed, through, key, profile=PROFILE, **kwargs):
    return world.resolve_progressive_reproduction(
        ProgressiveReproductionRequest(tuple(parents), seed, through, profile),
        request_key=key, expected_revision=world.reproduction_group_snapshot().revision, **kwargs,
    )


def v3_prefix(world):
    ab = progressive(world, ("A", "B"), 0, 1, "AB-through-T1")
    ad = progressive(world, ("A", "D"), 0, 0, "AD-through-T0")
    progressive(world, (ab.all_offspring_ids[0], "E"), 2, 1, "C1E-through-T1")
    zero = progressive(world, ("ZERO-PARENT",), 5, 0, "zero-parent-through-T0", ZERO_POSITIVE)
    return ab, ad, zero


def _retag(envelope):
    unsigned = {key: value for key, value in envelope.items() if key != "sha256"}
    canonical = json.dumps(unsigned, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False)
    envelope["sha256"] = hashlib.sha256(canonical.encode("ascii")).hexdigest()
    return json.dumps(envelope, sort_keys=True, ensure_ascii=True, indent=2) + "\n"


def _container_refs(world):
    registry = world._reproduction_group_registry
    names = (
        "_groups_by_id", "_group_id_by_parent_set", "_group_id_by_offspring",
        "_parent_set_by_offspring", "_person_id_reservations", "_group_id_reservations",
        "_requests", "_offspring_origin_ticks", "_generation_requests",
        "_generation_parent_set_scopes", "_progressive_histories",
        "_progressive_parent_set_scopes", "_progressive_requests",
    )
    return tuple(getattr(registry, name) for name in names)


class ReproductionCheckpointTests(unittest.TestCase):
    def test_round_trip_preserves_authored_v1_v2_and_zero_registry_records(self):
        source = make_world("all reproduction contracts")
        source.publish_reproduction_group(
            prepare_reproduction_group(ReproductionGroupProposal(
                "RG-AUTHORED", ("AUTH-PARENT",), ("AUTH-CHILD",), "test:authored"
            )), request_key="authored", expected_revision=0,
        )
        source.resolve_statistical_reproduction(
            StatisticalReproductionRequest(
                ("V1-PARENT",), 3, 0, (0,),
                TestOnlyOffspringCountDistribution("v1-positive", "1", ((1, 1),)),
            ), request_key="v1-positive", expected_revision=1,
        )
        source.resolve_statistical_reproduction(
            StatisticalReproductionRequest(
                ("V1-ZERO",), 4, 0, (0,),
                TestOnlyOffspringCountDistribution("v1-zero", "1", ((0, 1),)),
            ), request_key="v1-zero", expected_revision=2,
        )
        v3_prefix(source)
        snapshot_before = source.reproduction_group_snapshot()
        containers_before = _container_refs(source)
        rng_before = random.getstate()
        encoded = encode_reproduction_checkpoint(source)
        self.assertEqual(source.reproduction_group_snapshot(), snapshot_before)
        self.assertTrue(all(a is b for a, b in zip(_container_refs(source), containers_before)))
        self.assertEqual(random.getstate(), rng_before)
        detached = decode_reproduction_checkpoint(encoded)
        target = make_world("compatible empty target")
        target_containers = _container_refs(target)
        restored = restore_reproduction_checkpoint(target, detached)

        self.assertEqual(restored.revision, source.reproduction_group_snapshot().revision)
        self.assertIs(_container_refs(target)[0], target_containers[0])
        self.assertTrue(all(a is b for a, b in zip(_container_refs(target), target_containers)))
        self.assertEqual(
            logical_reproduction_checkpoint_digest(encoded),
            logical_reproduction_checkpoint_digest(encode_reproduction_checkpoint(target)),
        )
        self.assertEqual(set(target._reproduction_group_registry._requests), {"authored"})
        self.assertEqual(set(target._reproduction_group_registry._generation_requests), {"v1-positive", "v1-zero"})
        self.assertIn("AB-through-T1", target._reproduction_group_registry._progressive_requests)

    def test_idempotent_retry_after_restore_does_not_draw_or_advance_revision(self):
        import reproduction_generation
        source = make_world("source")
        ab, _, _ = v3_prefix(source)
        target = make_world("target")
        restore_reproduction_checkpoint(target, encode_reproduction_checkpoint(source))
        before = target.reproduction_group_snapshot()
        request = ProgressiveReproductionRequest(("B", "A"), 0, 1, PROFILE)
        with patch.object(reproduction_generation, "_period_draw", side_effect=AssertionError("cached retry drew")):
            replay = target.resolve_progressive_reproduction(
                request, request_key="AB-through-T1", expected_revision=before.revision,
            )
        self.assertEqual(replay.all_offspring_ids, ab.all_offspring_ids)
        self.assertEqual(target.reproduction_group_snapshot().revision, before.revision)

    def test_zero_only_checkpoint_restores_then_extends_to_positive_without_empty_group(self):
        import reproduction_generation
        source = make_world("zero source")
        zero = progressive(source, ("ZERO-PARENT",), 5, 0, "zero-T0", ZERO_POSITIVE)
        self.assertIsNone(zero.group_id)
        self.assertEqual(source.reproduction_group_snapshot().groups, ())
        target = make_world("zero target")
        restore_reproduction_checkpoint(target, encode_reproduction_checkpoint(source))
        before = target.reproduction_group_snapshot()
        with patch.object(reproduction_generation, "_period_draw", side_effect=AssertionError("zero retry drew")):
            target.resolve_progressive_reproduction(
                ProgressiveReproductionRequest(("ZERO-PARENT",), 5, 0, ZERO_POSITIVE),
                request_key="zero-T0", expected_revision=before.revision,
            )
        self.assertEqual(target.reproduction_group_snapshot().groups, ())
        result = progressive(target, ("ZERO-PARENT",), 5, 1, "positive-T1", ZERO_POSITIVE)
        self.assertIsNotNone(result.group_id)
        self.assertEqual(result.from_period, 1)
        self.assertEqual(result.added_periods[0].period, 1)
        history = target.reproduction_group_snapshot().progressive_histories[0]
        self.assertEqual((history.periods[0].count, history.periods[1].count), (0, 1))
        self.assertEqual(len(target.reproduction_group_snapshot().groups), 1)

    def test_incompatible_seed_profile_and_same_key_different_request_are_refused(self):
        source = make_world("source")
        progressive(source, ("A", "B"), 0, 1, "AB-T1")
        target = make_world("target")
        restore_reproduction_checkpoint(target, encode_reproduction_checkpoint(source))
        before = target.reproduction_group_snapshot()
        with self.assertRaises(ValueError):
            progressive(target, ("A", "B"), 9, 2, "new-seed")
        other = TestOnlyIntervalReproductionProfile("different", "1", ((1, 1),))
        with self.assertRaises(ValueError):
            progressive(target, ("A", "B"), 0, 2, "new-profile", other)
        with self.assertRaises(ValueError):
            progressive(target, ("A", "B"), 0, 2, "AB-T1")
        self.assertEqual(target.reproduction_group_snapshot(), before)

    def test_bad_digest_version_unknown_fields_duplicate_json_and_corrupt_references_fail_closed(self):
        source = make_world("source")
        progressive(source, ("P",), 1, 0, "P-T0")
        encoded = encode_reproduction_checkpoint(source)
        envelope = json.loads(encoded)
        corrupted_digest = envelope.copy()
        corrupted_digest["payload"] = json.loads(json.dumps(envelope["payload"]))
        corrupted_digest["payload"]["revision"] += 1
        with self.assertRaises(ReproductionCheckpointValidationError):
            decode_reproduction_checkpoint(json.dumps(corrupted_digest))

        unsupported = json.loads(encoded)
        unsupported["version"] = 999
        with self.assertRaises(ReproductionCheckpointValidationError):
            decode_reproduction_checkpoint(_retag(unsupported))

        unknown = json.loads(encoded)
        unknown["payload"]["surprise"] = True
        with self.assertRaises(ReproductionCheckpointValidationError):
            decode_reproduction_checkpoint(_retag(unknown))

        duplicate_raw = encoded.replace('"schema": "universe-reproduction-domain-checkpoint",',
                                        '"schema": "universe-reproduction-domain-checkpoint",\n  "schema": "universe-reproduction-domain-checkpoint",', 1)
        with self.assertRaises(ReproductionCheckpointValidationError):
            decode_reproduction_checkpoint(duplicate_raw)

        bad_reference = json.loads(encoded)
        bad_reference["payload"]["indexes"]["group_id_by_offspring"][0][1] = "MISSING-GROUP"
        with self.assertRaises(ReproductionCheckpointValidationError):
            decode_reproduction_checkpoint(_retag(bad_reference))

        duplicate_parent_set = json.loads(encoded)
        parent_index = duplicate_parent_set["payload"]["indexes"]["group_id_by_parent_set"]
        parent_index.append(parent_index[0])
        with self.assertRaises(ReproductionCheckpointValidationError):
            decode_reproduction_checkpoint(_retag(duplicate_parent_set))

    def test_retagged_cyclic_parentage_is_rejected_without_repair(self):
        source = make_world("cycle source")
        source.publish_reproduction_group(
            prepare_reproduction_group(ReproductionGroupProposal(
                "RG-CYCLE", ("P",), ("C",), "test:cycle"
            )), request_key="cycle", expected_revision=0,
        )
        envelope = json.loads(encode_reproduction_checkpoint(source))
        payload = envelope["payload"]
        payload["groups"][0]["parent_ids"] = ["C"]
        payload["indexes"]["group_id_by_parent_set"][0][0] = ["C"]
        payload["indexes"]["parent_set_by_offspring"][0][1] = ["C"]
        payload["indexes"]["person_id_reservations"] = ["C"]
        with self.assertRaises(ReproductionCheckpointValidationError):
            decode_reproduction_checkpoint(_retag(envelope))

    def test_failed_restore_at_each_phase_preserves_empty_target_and_container_aliases(self):
        source = make_world("source")
        v3_prefix(source)
        checkpoint = encode_reproduction_checkpoint(source)
        detached = decode_reproduction_checkpoint(checkpoint)
        for phase in RESTORE_FAILURE_PHASES:
            with self.subTest(phase=phase):
                target = make_world("rollback target")
                refs = _container_refs(target)
                before = target.reproduction_group_snapshot()
                with self.assertRaises(ReproductionCheckpointRestoreError):
                    restore_reproduction_checkpoint(target, detached, _fail_after=phase)
                self.assertEqual(target.reproduction_group_snapshot(), before)
                self.assertTrue(all(a is b for a, b in zip(_container_refs(target), refs)))

    def test_restore_rejects_nonempty_target_before_writing(self):
        source = make_world("source")
        v3_prefix(source)
        target = make_world("nonempty target")
        target.publish_reproduction_group(
            prepare_reproduction_group(ReproductionGroupProposal("LOCAL", ("L",), ("LC",), "test")),
            request_key="local", expected_revision=0,
        )
        before = target.reproduction_group_snapshot()
        refs = _container_refs(target)
        with self.assertRaises(ReproductionCheckpointRestoreError):
            restore_reproduction_checkpoint(target, encode_reproduction_checkpoint(source))
        self.assertEqual(target.reproduction_group_snapshot(), before)
        self.assertTrue(all(a is b for a, b in zip(_container_refs(target), refs)))

    def test_later_publication_failure_preserves_imported_prefix_and_retry_is_deterministic(self):
        source = make_world("source")
        v3_prefix(source)
        target = make_world("target")
        restore_reproduction_checkpoint(target, encode_reproduction_checkpoint(source))
        before = target.reproduction_group_snapshot()
        refs = _container_refs(target)
        with self.assertRaises(InjectedReproductionGroupFailure):
            progressive(target, ("A", "B"), 0, 2, "AB-T2", _fail_after="progressive_history")
        self.assertEqual(target.reproduction_group_snapshot(), before)
        self.assertTrue(all(a is b for a, b in zip(_container_refs(target), refs)))
        extended = progressive(target, ("A", "B"), 0, 2, "AB-T2")
        direct = make_world("uninterrupted")
        v3_prefix(direct)
        direct_extended = progressive(direct, ("A", "B"), 0, 2, "AB-T2")
        self.assertEqual(
            (extended.request_key, extended.scope_digest, extended.parent_ids,
             extended.from_period, extended.through_period, extended.added_periods,
             extended.group_id, extended.all_offspring_ids, extended.revision,
             extended.parent_global_history_complete),
            (direct_extended.request_key, direct_extended.scope_digest, direct_extended.parent_ids,
             direct_extended.from_period, direct_extended.through_period, direct_extended.added_periods,
             direct_extended.group_id, direct_extended.all_offspring_ids, direct_extended.revision,
             direct_extended.parent_global_history_complete),
        )
        self.assertEqual(
            logical_reproduction_checkpoint_digest(encode_reproduction_checkpoint(target)),
            logical_reproduction_checkpoint_digest(encode_reproduction_checkpoint(direct)),
        )

    def test_example_performs_real_fresh_process_round_trip_and_comparison(self):
        completed = subprocess.run(
            [sys.executable, str(ROOT / "examples/reproduction_checkpoint_continuation.py")],
            cwd=ROOT, text=True, capture_output=True, check=True,
        )
        self.assertIn("COMPARE distinct source/resume processes=", completed.stdout)
        self.assertIn("logical histories and known kinship equal=True", completed.stdout)
        self.assertIn("Only logical reproduction records restored", completed.stdout)


if __name__ == "__main__":
    unittest.main()
