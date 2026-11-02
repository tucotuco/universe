"""Exact-ID bridge from logical reproductive offspring to native Being."""
import random
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from being import BeingDefinition, BeingInstance
from library import Library
from object import ObjectDefinition, ObjectInstance
from reproduction_being_bridge import (
    InjectedReproductionBeingBridgeFailure, ReproductionBeingBridgeError,
    _definition_signature, materialize_reproductive_offspring,
)
from reproduction_checkpoint import encode_reproduction_checkpoint, restore_reproduction_checkpoint
from reproduction_generation import StatisticalReproductionRequest, TestOnlyOffspringCountDistribution
from universe import Universe


COUNT_ONE = TestOnlyOffspringCountDistribution("bridge-one", "1", ((1, 1),))


def make_world(name="bridge-test"):
    return Universe(name, library=Library(config_dir=str(ROOT / "src/config")))


def generate(world):
    return world.resolve_statistical_reproduction(
        StatisticalReproductionRequest(("P", "Q"), 17, 0, (0,), COUNT_ONE),
        request_key="genealogy-PQ", expected_revision=world.reproduction_group_snapshot().revision,
    )


def authored_definition(**changes):
    values = dict(
        obj_type="Explicit bridge fixture", length=1.8, weight=70, hit_points=10,
        hit_dice="1d8", alignment="Neutral", armor_class=10, challenge_rating=0,
    )
    values.update(changes)
    return BeingDefinition(**values)


def materialize(world, child_id, *, name="C", definition=None, key="materialize-C", revision=None, **kwargs):
    if revision is None:
        revision = world.reproduction_group_snapshot().revision
    return materialize_reproductive_offspring(
        world, child_id, being_definition=definition or authored_definition(),
        name=name, request_key=key, expected_revision=revision, **kwargs,
    )


class ReproductionBeingBridgeTests(unittest.TestCase):
    def test_exact_logical_identity_materializes_one_native_being_without_reproductive_side_effects(self):
        world = make_world()
        outcome = generate(world)
        child_id = outcome.offspring_ids[0]
        before = world.reproduction_group_snapshot()
        object_container = world.object_registry.object_instances
        rng_before = random.getstate()
        definition = authored_definition()

        being = materialize(world, child_id, definition=definition)
        after = world.reproduction_group_snapshot()
        self.assertIsInstance(being, BeingInstance)
        self.assertEqual(being.id, child_id)
        self.assertIs(world.get_object_by_id(child_id), being)
        self.assertIs(world.object_registry.object_instances, object_container)
        self.assertEqual(tuple(world.object_registry.object_instances), (child_id,))
        self.assertEqual(after, before)
        self.assertEqual(after.known_parents(child_id), outcome.parent_ids)
        self.assertEqual(after.known_full_siblings(child_id), ())
        self.assertIsNot(being.original, definition)
        self.assertEqual(_definition_signature(being.original), _definition_signature(definition))
        self.assertEqual(random.getstate(), rng_before)
        self.assertEqual(set(world.event_history), {"0"})
        self.assertEqual(world._choice_books, [])
        self.assertEqual(world._reproduction_group_registry._native_beings_by_person_id, {child_id: being})

    def test_exact_retry_returns_same_mutable_being_and_conflicting_requests_refuse(self):
        world = make_world()
        child_id = generate(world).offspring_ids[0]
        definition = authored_definition()
        being = materialize(world, child_id, definition=definition)
        snapshot = world.reproduction_group_snapshot()
        registry = world._reproduction_group_registry
        object_count = world.object_registry.len()
        replay = materialize(world, child_id, definition=definition)
        self.assertIs(replay, being)
        self.assertEqual(world.object_registry.len(), object_count)
        self.assertEqual(world.reproduction_group_snapshot(), snapshot)

        with self.assertRaisesRegex(ReproductionBeingBridgeError, "different Being properties"):
            materialize(world, child_id, name="changed", definition=definition)
        with self.assertRaisesRegex(ReproductionBeingBridgeError, "already bound"):
            materialize(world, child_id, name="C", definition=definition, key="second-key")
        with self.assertRaisesRegex(ReproductionBeingBridgeError, "different Being properties"):
            materialize(world, child_id, name="C", definition=authored_definition(hit_points=11))
        self.assertIs(registry._native_beings_by_person_id[child_id], being)
        self.assertEqual(world.object_registry.len(), object_count)

    def test_unknown_parent_identity_collision_and_stale_revision_refuse_without_poisoning_retry(self):
        world = make_world()
        outcome = generate(world)
        child_id = outcome.offspring_ids[0]
        before = world.reproduction_group_snapshot()
        with self.assertRaisesRegex(ReproductionBeingBridgeError, "already-published logical offspring"):
            materialize(world, "UNKNOWN-C")
        with self.assertRaisesRegex(ReproductionBeingBridgeError, "already-published logical offspring"):
            materialize(world, "P")
        with self.assertRaisesRegex(ReproductionBeingBridgeError, "revision changed"):
            materialize(world, child_id, revision=0)
        self.assertEqual(world.reproduction_group_snapshot(), before)
        self.assertEqual(world.object_registry.object_instances, {})

        # The failed stale/unknown requests leave the correct later request usable.
        being = materialize(world, child_id)
        self.assertEqual(being.id, child_id)
        self.assertEqual(world.reproduction_group_snapshot(), before)

        collision_world = make_world("collision"); collision_child = generate(collision_world).offspring_ids[0]
        conflict = ObjectInstance(
            ObjectDefinition("marker", 0, 0, 0, 0, 0, 0, 0), "collision", id=collision_child,
        )
        collision_world.add_object(conflict)
        with self.assertRaises(ReproductionBeingBridgeError):
            materialize(collision_world, collision_child)
        self.assertIs(collision_world.get_object_by_id(collision_child), conflict)
        self.assertFalse(collision_world._reproduction_group_registry._native_beings_by_person_id)

    def test_failure_after_each_publication_write_rolls_back_in_place_and_retry_succeeds(self):
        phases = ("object_registry", "binding_index", "request_index", "consistency")
        for phase in phases:
            with self.subTest(phase=phase):
                world = make_world()
                child_id = generate(world).offspring_ids[0]
                existing = BeingInstance(authored_definition(), "Existing unrelated Being", id="EXISTING-BEING")
                marker = ObjectInstance(
                    ObjectDefinition("marker", 0, 0, 0, 0, 0, 0, 0), "Existing marker", id="EXISTING-MARKER",
                )
                world.add_object(existing)
                world.add_object(marker)
                registry = world._reproduction_group_registry
                object_map = world.object_registry.object_instances
                objects_before = dict(object_map)
                binding_map = registry._native_beings_by_person_id
                request_map = registry._native_being_requests
                before = world.reproduction_group_snapshot()
                before_rng = random.getstate()
                with self.assertRaises(InjectedReproductionBeingBridgeFailure):
                    materialize(world, child_id, _fail_after=phase)
                self.assertEqual(world.object_registry.object_instances, objects_before)
                self.assertIs(world.get_object_by_id("EXISTING-BEING"), existing)
                self.assertIs(world.get_object_by_id("EXISTING-MARKER"), marker)
                self.assertEqual(world.reproduction_group_snapshot(), before)
                self.assertIs(world.object_registry.object_instances, object_map)
                self.assertIs(registry._native_beings_by_person_id, binding_map)
                self.assertIs(registry._native_being_requests, request_map)
                self.assertEqual(random.getstate(), before_rng)
                self.assertEqual(binding_map, {})
                self.assertEqual(request_map, {})
                retry = materialize(world, child_id)
                self.assertIs(world.get_object_by_id(child_id), retry)

    def test_reproduction_checkpoint_restores_genealogy_then_explicit_being_is_materialized(self):
        source = make_world("checkpoint source")
        outcome = generate(source)
        child_id = outcome.offspring_ids[0]
        checkpoint = encode_reproduction_checkpoint(source)
        target = make_world("checkpoint target")
        restore_reproduction_checkpoint(target, checkpoint)
        before = target.reproduction_group_snapshot()
        being = materialize(target, child_id)
        self.assertEqual(target.reproduction_group_snapshot(), before)
        self.assertEqual(being.id, child_id)
        with self.assertRaisesRegex(ValueError, "logical reproduction IDs collide with native Objects"):
            encode_reproduction_checkpoint(target)

    def test_registered_being_cannot_be_rebound_to_a_second_native_instance(self):
        world = make_world()
        child_id = generate(world).offspring_ids[0]
        first = materialize(world, child_id)
        second = BeingInstance(authored_definition(), "other C", id=child_id)
        registry = world._reproduction_group_registry
        world.add_object(second)
        self.assertIs(world.get_object_by_id(child_id), first)
        with self.assertRaisesRegex(ReproductionBeingBridgeError, "already bound"):
            materialize(world, child_id, name="other C", key="second-binding")
        self.assertIs(registry._native_beings_by_person_id[child_id], first)
        self.assertIs(world.get_object_by_id(child_id), first)


if __name__ == "__main__":
    unittest.main()
