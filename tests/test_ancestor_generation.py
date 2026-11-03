"""Tests for bounded world-only reverse-direction ancestor generation."""
import json
from pathlib import Path
import random
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ancestor_generation import (
    AncestorGenerationError, ResolveParentsRequest, prepare_resolve_parents,
    resolve_parents,
)
from library import Library
from reproduction_checkpoint import (
    decode_reproduction_checkpoint, encode_reproduction_checkpoint,
)
from reproduction_generation import (
    StatisticalReproductionRequest, TestOnlyOffspringCountDistribution,
)
from reproduction_group import (
    InjectedReproductionGroupFailure, ReproductionGroupProposal,
    ReproductionGroupPublicationError, StaleReproductionGroupRevision,
    prepare_reproduction_group,
)
from universe import Universe


SIBLINGS = TestOnlyOffspringCountDistribution("v9-sibling-counts", "1", ((0, 1), (1, 2), (2, 1)))
ZERO_SIBLINGS = TestOnlyOffspringCountDistribution("v9-zero-siblings", "1", ((0, 1),))
PUBLICATION_PHASES = (
    "group", "parent_set_index", "offspring_indexes", "person_reservations",
    "group_reservation", "idempotency", "revision", "consistency",
)


def make_world(name="V9 tests"):
    return Universe(name, library=Library(config_dir=str(ROOT / "src/config")))


def establish_p_and_child(world):
    candidate = prepare_reproduction_group(ReproductionGroupProposal(
        "RG-V9-INITIAL", ("P", "Q"), ("C",), "v9:test:initial-P-child",
    ))
    return world.publish_reproduction_group(candidate, request_key="v9:initial", expected_revision=0)


def request(person="P", parent_count=2, seed=0, distribution=SIBLINGS):
    return ResolveParentsRequest(person, parent_count, seed, distribution)


def registry_refs(world):
    registry = world._reproduction_group_registry
    names = (
        "_groups_by_id", "_group_id_by_parent_set", "_group_id_by_offspring",
        "_parent_set_by_offspring", "_person_id_reservations", "_group_id_reservations",
        "_requests", "_offspring_origin_ticks", "_generation_requests",
        "_generation_parent_set_scopes", "_progressive_histories",
        "_progressive_parent_set_scopes", "_progressive_requests",
    )
    return tuple(getattr(registry, name) for name in names)


class AncestorGenerationTests(unittest.TestCase):
    def test_reverse_generation_attaches_existing_p_and_derives_siblings_and_grandparents(self):
        world = make_world()
        establish_p_and_child(world)
        before = world.reproduction_group_snapshot()
        self.assertIsNone(before.known_parents("P"))
        self.assertEqual(before.known_parents("C"), ("P", "Q"))
        old_group = before.groups[0]
        object_map, event_map = world.object_registry.object_instances, world.event_history
        rng_before = random.getstate()
        result = resolve_parents(world, request(), request_key="v9:resolve-P", expected_revision=before.revision)
        after = world.reproduction_group_snapshot()
        self.assertEqual(len(result.parent_ids), 2)
        self.assertEqual(result.parent_ids, tuple(sorted(result.parent_ids)))
        self.assertEqual(result.offspring_ids[0], "P")
        self.assertEqual(after.known_parents("P"), result.parent_ids)
        self.assertEqual(after.known_parents("C"), ("P", "Q"))
        self.assertIs(next(group for group in after.groups if group.group_id == old_group.group_id), old_group)
        self.assertEqual(after.known_full_siblings("P"), result.offspring_ids[1:])
        self.assertEqual(after.known_grandparent_paths("C"), (("P", result.parent_ids),))
        self.assertFalse(next(group for group in after.groups if group.group_id == result.group_id).offspring_enumeration_complete)
        prepared = prepare_resolve_parents(world, request(), request_key="v9:resolve-P")
        self.assertFalse(prepared.offspring_enumeration_complete)
        self.assertEqual(len(after.groups), 2)
        self.assertEqual(after.person_id_reservations.count("P"), 1)
        self.assertEqual(after.revision, before.revision + 1)
        self.assertIs(world.object_registry.object_instances, object_map)
        self.assertEqual(object_map, {})
        self.assertIs(world.event_history, event_map)
        self.assertEqual(set(world.event_history), {"0"})
        self.assertEqual(world._choice_books, [])
        self.assertEqual(random.getstate(), rng_before)

    def test_zero_additional_siblings_keeps_p_as_nonempty_group_offspring(self):
        world = make_world()
        establish_p_and_child(world)
        result = resolve_parents(world, request(seed=2, distribution=ZERO_SIBLINGS), request_key="v9:zero")
        snapshot = world.reproduction_group_snapshot()
        self.assertEqual(result.offspring_ids, ("P",))
        self.assertEqual(snapshot.known_full_siblings("P"), ())
        group = next(group for group in snapshot.groups if group.group_id == result.group_id)
        self.assertEqual(group.offspring_ids, ("P",))
        self.assertFalse(group.offspring_enumeration_complete)

    def test_explicit_one_parent_support_does_not_infer_another_parent(self):
        world = make_world()
        establish_p_and_child(world)
        result = resolve_parents(
            world, request(parent_count=1, seed=2, distribution=ZERO_SIBLINGS),
            request_key="v9:one-parent",
        )
        snapshot = world.reproduction_group_snapshot()
        self.assertEqual(len(result.parent_ids), 1)
        self.assertEqual(snapshot.known_parents("P"), result.parent_ids)
        self.assertEqual(snapshot.known_grandparent_paths("C"), (("P", result.parent_ids),))

    def test_seeded_ids_repeat_across_worlds_and_retry_is_idempotent(self):
        outcomes = []
        for name in ("first", "second"):
            world = make_world(name)
            establish_p_and_child(world)
            args = request(seed=0)
            outcome = resolve_parents(world, args, request_key="v9:stable")
            committed = world.reproduction_group_snapshot()
            replay = resolve_parents(world, args, request_key="v9:stable", expected_revision=1)
            self.assertEqual(world.reproduction_group_snapshot(), committed)
            self.assertEqual(replay, outcome)
            outcomes.append(outcome)
        self.assertEqual(outcomes[0].group_id, outcomes[1].group_id)
        self.assertEqual(outcomes[0].parent_ids, outcomes[1].parent_ids)
        self.assertEqual(outcomes[0].offspring_ids, outcomes[1].offspring_ids)

    def test_missing_person_and_nonparent_focal_refuse(self):
        world = make_world()
        empty = world.reproduction_group_snapshot()
        with self.assertRaisesRegex(AncestorGenerationError, "must already exist"):
            prepare_resolve_parents(world, request(), request_key="missing")
        self.assertEqual(world.reproduction_group_snapshot(), empty)
        establish_p_and_child(world)
        with self.assertRaisesRegex(AncestorGenerationError, "logical parent"):
            prepare_resolve_parents(world, request(person="C"), request_key="not-parent")

    def test_conflicting_existing_parentage_and_request_key_reuse_refuse(self):
        world = make_world()
        establish_p_and_child(world)
        result = resolve_parents(world, request(), request_key="v9:parentage")
        committed = world.reproduction_group_snapshot()
        with self.assertRaisesRegex(ReproductionGroupPublicationError, "already has an established"):
            resolve_parents(world, request(seed=1), request_key="v9:second-set")
        with self.assertRaisesRegex(ReproductionGroupPublicationError, "different normalized content"):
            resolve_parents(world, request(parent_count=1), request_key="v9:parentage")
        self.assertEqual(world.reproduction_group_snapshot(), committed)
        self.assertEqual(world.reproduction_group_snapshot().known_parents("P"), result.parent_ids)

    def test_known_ancestry_cycle_refuses_without_mutation(self):
        world = make_world()
        establish_p_and_child(world)
        before = world.reproduction_group_snapshot()
        for group_id, parents, offspring, key in (
            ("RG-V9-CYCLE", ("C",), ("P",), "v9:cycle"),
            ("RG-V9-SELF", ("P",), ("P",), "v9:self"),
        ):
            candidate = prepare_reproduction_group(ReproductionGroupProposal(
                group_id, parents, offspring, f"v9:test:{key}",
            ))
            with self.subTest(key=key), self.assertRaisesRegex(
                ReproductionGroupPublicationError, "known ancestry cycle"
            ):
                world.publish_reproduction_group(candidate, request_key=key, expected_revision=1)
            self.assertEqual(world.reproduction_group_snapshot(), before)
        self.assertEqual(world.reproduction_group_snapshot(), before)

    def test_stale_candidate_and_generated_identity_collision_refuse(self):
        world = make_world()
        establish_p_and_child(world)
        stale = prepare_resolve_parents(world, request(), request_key="v9:stale")
        unrelated = prepare_reproduction_group(ReproductionGroupProposal(
            "RG-V9-UNRELATED", ("U",), ("V",), "v9:test:unrelated",
        ))
        world.publish_reproduction_group(unrelated, request_key="v9:unrelated", expected_revision=1)
        committed = world.reproduction_group_snapshot()
        with self.assertRaises(StaleReproductionGroupRevision):
            world.publish_reproduction_group(stale.candidate, request_key="v9:stale",
                                              expected_revision=stale.base_revision)
        self.assertEqual(world.reproduction_group_snapshot(), committed)

        other = make_world()
        establish_p_and_child(other)
        prepared = prepare_resolve_parents(other, request(), request_key="v9:collision")
        blocker = prepare_reproduction_group(ReproductionGroupProposal(
            "RG-V9-BLOCKER", (prepared.parent_ids[0],), ("BLOCKER-CHILD",), "v9:test:blocker",
        ))
        other.publish_reproduction_group(blocker, request_key="v9:blocker", expected_revision=1)
        before_collision = other.reproduction_group_snapshot()
        with self.assertRaisesRegex(ReproductionGroupPublicationError, "identity collides"):
            prepare_resolve_parents(other, request(), request_key="v9:collision")
        self.assertEqual(other.reproduction_group_snapshot(), before_collision)

    def test_generated_id_cannot_reuse_person_reference_in_zero_only_v1_scope(self):
        world = make_world()
        establish_p_and_child(world)
        planned = prepare_resolve_parents(world, request(), request_key="v9:future")
        existing_reference = planned.parent_ids[0]
        world.resolve_statistical_reproduction(
            StatisticalReproductionRequest(
                (existing_reference,), 7, 0, (0,),
                TestOnlyOffspringCountDistribution("v9-existing-zero", "1", ((0, 1),)),
            ),
            request_key="v9:zero-reference", expected_revision=1,
        )
        before = world.reproduction_group_snapshot()
        with self.assertRaisesRegex(ReproductionGroupPublicationError, "identity collides"):
            prepare_resolve_parents(world, request(), request_key="v9:future")
        self.assertEqual(world.reproduction_group_snapshot(), before)

    def test_every_publication_failure_rolls_back_in_place_then_retries(self):
        for phase in PUBLICATION_PHASES:
            with self.subTest(phase=phase):
                world = make_world()
                establish_p_and_child(world)
                prepared = prepare_resolve_parents(world, request(), request_key="v9:fault")
                before = world.reproduction_group_snapshot()
                aliases = registry_refs(world)
                object_map, event_map = world.object_registry.object_instances, world.event_history
                rng_before = random.getstate()
                with self.assertRaises(InjectedReproductionGroupFailure):
                    world.publish_reproduction_group(
                        prepared.candidate, request_key="v9:fault",
                        expected_revision=prepared.base_revision, _fail_after=phase,
                    )
                self.assertEqual(world.reproduction_group_snapshot(), before)
                self.assertTrue(all(a is b for a, b in zip(registry_refs(world), aliases)))
                self.assertIs(world.object_registry.object_instances, object_map)
                self.assertIs(world.event_history, event_map)
                self.assertEqual(random.getstate(), rng_before)
                self.assertEqual(world._choice_books, [])
                retry = world.publish_reproduction_group(
                    prepared.candidate, request_key="v9:fault", expected_revision=prepared.base_revision,
                )
                self.assertEqual(retry.revision, before.revision + 1)
                self.assertEqual(world.reproduction_group_snapshot().known_parents("P"), prepared.parent_ids)

    def test_existing_checkpoint_contract_carries_new_authored_ancestry(self):
        source = make_world("checkpoint source")
        establish_p_and_child(source)
        result = resolve_parents(source, request(), request_key="v9:checkpoint")
        encoded = encode_reproduction_checkpoint(source)
        detached = decode_reproduction_checkpoint(encoded)
        self.assertIn("P", next(group.offspring_ids for group in detached.groups
                                if group.group_id == result.group_id))

        code = "\n".join((
            "import json, sys",
            "sys.path.insert(0, 'src')",
            "from library import Library",
            "from reproduction_checkpoint import decode_reproduction_checkpoint, restore_reproduction_checkpoint",
            "from universe import Universe",
            "world = Universe('fresh-process', library=Library(config_dir='src/config'))",
            "restore_reproduction_checkpoint(world, decode_reproduction_checkpoint(sys.stdin.read()))",
            "s = world.reproduction_group_snapshot()",
            "print(json.dumps({'parents': s.known_parents('P'), 'siblings': s.known_full_siblings('P'),",
            "'grandparents': s.known_grandparent_paths('C'), 'groups': len(s.groups)}))",
        ))
        process = subprocess.run(
            [sys.executable, "-c", code], cwd=ROOT, input=encoded,
            text=True, check=True, capture_output=True,
        )
        restored = json.loads(process.stdout)
        self.assertEqual(restored["parents"], list(result.parent_ids))
        self.assertEqual(restored["siblings"], list(result.offspring_ids[1:]))
        self.assertEqual(restored["grandparents"], [["P", list(result.parent_ids)]])
        self.assertEqual(restored["groups"], 2)


if __name__ == "__main__":
    unittest.main()
