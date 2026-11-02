"""Strict combined reproduction/native Being checkpoint tests."""
import hashlib
import json
from dataclasses import replace
from pathlib import Path
import random
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from abilities import Abilities
from being import BeingDefinition, BeingInstance
from library import Library
from object import ObjectDefinition, ObjectInstance
from reproduction_being_bridge import materialize_reproductive_offspring
from reproduction_being_checkpoint import (
    CombinedBeingCheckpointError, InjectedCombinedBeingCheckpointFailure,
    combined_being_checkpoint_digest, decode_combined_being_checkpoint,
    encode_combined_being_checkpoint, restore_combined_being_checkpoint,
)
from reproduction_checkpoint import encode_reproduction_checkpoint
from reproduction_generation import ProgressiveReproductionRequest, TestOnlyIntervalReproductionProfile
from skill import Skills
from universe import Universe


PROFILE = TestOnlyIntervalReproductionProfile("v6-checkpoint-test", "1", ((0, 1), (1, 2), (2, 3)))


def world(name="test"):
    return Universe(name, library=Library(config_dir=str(ROOT / "src/config")))


def definition():
    skills = Skills()
    skills.skills = {"authored skill": 3}
    return BeingDefinition(
        "authored-v6-human", 1.7, 62, 13, "1d8", "Neutral", 11, 0,
        abilities=Abilities(strength=14, dexterity=12), skills=skills,
        tags={"authored": ["test-only"]}, physiology_id="test:unresolved-v1",
    )


def progress(instance, parents, horizon, key):
    return instance.resolve_progressive_reproduction(
        ProgressiveReproductionRequest(tuple(parents), 7, horizon, PROFILE),
        request_key=key, expected_revision=instance.reproduction_group_snapshot().revision,
    )


def prefix(instance):
    ab = progress(instance, ("P", "Q"), 1, "PQ-T1")
    child = ab.all_offspring_ids[0]
    progress(instance, ("P", "R"), 0, "PR-T0")
    progress(instance, (child, "S"), 1, "child-S-T1")
    return child


def bind(instance, child):
    return materialize_reproductive_offspring(
        instance, child, being_definition=definition(), name="Authored C", request_key="bind-C",
        expected_revision=instance.reproduction_group_snapshot().revision,
    )


def ready():
    source = world("source")
    child = prefix(source)
    being = bind(source, child)
    return source, child, being, encode_combined_being_checkpoint(source)


def retag(text, change):
    envelope = json.loads(text)
    change(envelope)
    unsigned = {key: value for key, value in envelope.items() if key != "sha256"}
    canonical = json.dumps(unsigned, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False)
    envelope["sha256"] = hashlib.sha256(canonical.encode("ascii")).hexdigest()
    return json.dumps(envelope, sort_keys=True, ensure_ascii=True, indent=2, allow_nan=False) + "\n"


def container_refs(instance):
    r = instance._reproduction_group_registry
    return (r._groups_by_id, r._group_id_by_parent_set, r._group_id_by_offspring,
            r._parent_set_by_offspring, r._person_id_reservations, r._group_id_reservations,
            r._requests, r._offspring_origin_ticks, r._generation_requests,
            r._generation_parent_set_scopes, r._progressive_histories,
            r._progressive_parent_set_scopes, r._progressive_requests,
            r._native_beings_by_person_id, r._native_being_requests,
            instance.object_registry.object_instances)


class ReproductionBeingCheckpointTests(unittest.TestCase):
    def test_real_native_instance_round_trips_and_v4_refusal_remains(self):
        source, child, original, encoded = ready()
        with self.assertRaisesRegex(ValueError, "logical reproduction IDs collide with native Objects"):
            encode_reproduction_checkpoint(source)
        target = world("fresh target")
        before_rng = random.getstate()
        before_containers = container_refs(target)
        restored = restore_combined_being_checkpoint(target, encoded)
        self.assertIs(type(restored), BeingInstance)
        self.assertEqual(restored.id, child)
        self.assertIs(target.get_object_by_id(child), restored)
        self.assertEqual(restored.name, original.name)
        self.assertEqual(restored.original.obj_type, original.original.obj_type)
        self.assertEqual(restored.original.hit_points, original.original.hit_points)
        self.assertEqual(restored.original.STR(), original.original.STR())
        self.assertEqual(restored.original.DEX(), original.original.DEX())
        self.assertEqual(restored.original.skills.skills, original.original.skills.skills)
        self.assertEqual(restored.original.tags, original.original.tags)
        self.assertEqual(restored.physiology_id, original.physiology_id)
        self.assertEqual(len(target.object_registry.object_instances), 1)
        self.assertEqual(set(target.event_history), {"0"})
        self.assertEqual(target._choice_books, [])
        self.assertEqual(random.getstate(), before_rng)
        self.assertTrue(all(a is b for a, b in zip(container_refs(target), before_containers)))
        self.assertEqual(
            target.reproduction_group_snapshot().known_parents(child),
            source.reproduction_group_snapshot().known_parents(child),
        )

    def test_idempotent_original_bridge_retry_returns_restored_native_instance(self):
        _source, child, _being, encoded = ready()
        target = world()
        restored = restore_combined_being_checkpoint(target, encoded)
        before = target.reproduction_group_snapshot()
        retry = materialize_reproductive_offspring(
            target, child, being_definition=restored.original, name=restored.name,
            request_key="bind-C", expected_revision=before.revision,
        )
        self.assertIs(retry, restored)
        self.assertEqual(target.reproduction_group_snapshot(), before)

    def test_same_seed_restored_continuation_matches_uninterrupted_native_control(self):
        _source, child, _being, encoded = ready()
        resumed = world("resumed")
        resumed_being = restore_combined_being_checkpoint(resumed, encoded)
        before = resumed.reproduction_group_snapshot()
        prior = next(row for row in before.groups if row.parent_ids == ("P", "Q"))
        progress(resumed, ("Q", "P"), 2, "PQ-T2")
        after = resumed.reproduction_group_snapshot()
        continued = next(row for row in after.groups if row.parent_ids == ("P", "Q"))
        self.assertEqual(continued.group_id, prior.group_id)
        self.assertEqual(continued.offspring_ids[:len(prior.offspring_ids)], prior.offspring_ids)
        self.assertIs(resumed.get_object_by_id(child), resumed_being)

        control = world("uninterrupted")
        control_child = prefix(control)
        control_being = bind(control, control_child)
        self.assertEqual(control_child, child)
        progress(control, ("Q", "P"), 2, "PQ-T2")
        self.assertEqual(
            combined_being_checkpoint_digest(encode_combined_being_checkpoint(resumed)),
            combined_being_checkpoint_digest(encode_combined_being_checkpoint(control)),
        )
        self.assertEqual(resumed_being.id, control_being.id)
        self.assertEqual(resumed_being.original.hit_points, control_being.original.hit_points)

    def test_corrupt_version_unknown_identity_definition_and_state_refuse(self):
        _source, _child, _being, encoded = ready()
        with self.assertRaisesRegex(CombinedBeingCheckpointError, "unsupported.*version"):
            decode_combined_being_checkpoint(encoded.replace('"version": 1', '"version": 2', 1))
        bad_digest = json.loads(encoded)
        bad_digest["sha256"] = "0" * 64
        with self.assertRaisesRegex(CombinedBeingCheckpointError, "digest mismatch"):
            decode_combined_being_checkpoint(json.dumps(bad_digest))
        with self.assertRaises(CombinedBeingCheckpointError):
            decode_combined_being_checkpoint(retag(encoded, lambda e: e.update(version=99)))
        with self.assertRaisesRegex(CombinedBeingCheckpointError, "unknown fields"):
            decode_combined_being_checkpoint(retag(encoded, lambda e: e["being"].update(extra="x")))
        with self.assertRaisesRegex(CombinedBeingCheckpointError, "not a referenced"):
            decode_combined_being_checkpoint(retag(encoded, lambda e: e["being"].update(person_id="NOT-CHILD")))
        with self.assertRaisesRegex(CombinedBeingCheckpointError, "pristine authored state"):
            decode_combined_being_checkpoint(retag(encoded, lambda e: e["being"]["state"].update(type="ObjectInstance")))

    def test_unsupported_mutable_native_being_state_fails_export_closed(self):
        source, _child, being, _encoded = ready()
        being.set_physical_fatigue(0.8, 0.9)
        with self.assertRaisesRegex(CombinedBeingCheckpointError, "modified physical fatigue"):
            encode_combined_being_checkpoint(source)
        source, _child, being, _encoded = ready()
        being.skill_experience["authored skill"] = 1
        with self.assertRaisesRegex(CombinedBeingCheckpointError, "practice or personal history"):
            encode_combined_being_checkpoint(source)
        source, _child, being, _encoded = ready()
        being.current.hit_points += 1
        with self.assertRaisesRegex(CombinedBeingCheckpointError, "unmodified authored Being definition"):
            encode_combined_being_checkpoint(source)

    def test_collision_and_nonempty_target_refuse_without_partial_writes(self):
        _source, child, _being, encoded = ready()
        target = world("collision")
        collision = ObjectInstance(ObjectDefinition("marker", 0, 0, 0, 0, 0, 0, 0), "marker", id=child)
        target.add_object(collision)
        objects = target.object_registry.object_instances
        before = dict(objects)
        with self.assertRaises(ValueError):
            restore_combined_being_checkpoint(target, encoded)
        self.assertIs(target.object_registry.object_instances, objects)
        self.assertEqual(objects, before)
        self.assertIs(target.get_object_by_id(child), collision)
        self.assertEqual(target.reproduction_group_snapshot().revision, 0)

    def test_caller_constructed_detached_record_is_revalidated_before_restore(self):
        _source, _child, _being, encoded = ready()
        detached = decode_combined_being_checkpoint(encoded)
        forged_record = replace(detached, person_id="NOT-A-CHILD")
        target = world("forged detached record")
        with self.assertRaisesRegex(CombinedBeingCheckpointError, "not a referenced"):
            restore_combined_being_checkpoint(target, forged_record)
        self.assertEqual(target.reproduction_group_snapshot().revision, 0)
        self.assertEqual(target.object_registry.object_instances, {})

    def test_fault_after_every_combined_restore_phase_rolls_back_and_retry_succeeds(self):
        phases = (
            "reproduction_groups", "reproduction_indexes", "reproduction_authored_requests",
            "reproduction_v1_records", "reproduction_v2_records", "reproduction_revision",
            "reproduction_consistency", "reproduction_complete", "object_registry",
            "binding_index", "request_index", "combined_consistency",
        )
        for phase in phases:
            with self.subTest(phase=phase):
                _source, child, _being, encoded = ready()
                target = world("fault target")
                refs = container_refs(target)
                snapshot = target.reproduction_group_snapshot()
                rng_before = random.getstate()
                with self.assertRaises(InjectedCombinedBeingCheckpointFailure):
                    restore_combined_being_checkpoint(target, encoded, _fail_after=phase)
                self.assertEqual(target.reproduction_group_snapshot(), snapshot)
                self.assertEqual(target.object_registry.object_instances, {})
                self.assertTrue(all(a is b for a, b in zip(container_refs(target), refs)))
                self.assertEqual(random.getstate(), rng_before)
                self.assertIsNone(target.get_object_by_id(child))
                restored = restore_combined_being_checkpoint(target, encoded)
                self.assertIs(target.get_object_by_id(child), restored)

    def test_actual_save_restore_continuation_runs_in_two_python_processes(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "examples/reproduction_being_checkpoint_continuation.py")],
            cwd=ROOT, check=True, text=True, capture_output=True,
        )
        self.assertIn("separate Python processes=true", result.stdout)
        self.assertIn("uninterrupted digest match=True", result.stdout)
        self.assertIn("V4 reproduction-only refusal=preserved", result.stdout)


if __name__ == "__main__":
    unittest.main()
