"""Progressive test-only world-level reproduction proof."""
import random
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from reproduction_generation import (
    ProgressiveReproductionRequest,
    TestOnlyIntervalReproductionProfile,
    prepare_progressive_reproduction,
)
from reproduction_group import (
    InjectedReproductionGroupFailure,
    ReproductionGroupPublicationError,
    StaleReproductionGroupRevision,
)
from field_observation import BeliefLedger
from test_reproduction_group_publication import make_world


PROFILE = TestOnlyIntervalReproductionProfile(
    "v2-progressive-demo", "1", ((0, 1), (1, 2), (2, 3))
)


def request(seed, through, parents=("P-B", "P-A"), profile=PROFILE):
    return ProgressiveReproductionRequest(parents, seed, through, profile)


class ProgressiveReproductionTests(unittest.TestCase):
    def prepare_publish(self, world, req, key, **kwargs):
        candidate = prepare_progressive_reproduction(world, req)
        return world.publish_progressive_reproduction(
            candidate, request_key=key, expected_revision=candidate.base_revision, **kwargs
        )

    def test_split_horizon_matches_fresh_one_shot_and_preserves_prefix(self):
        split, one_shot = make_world("split"), make_world("one shot")
        initial_request = request(0, 1)
        first = self.prepare_publish(split, initial_request, "T1")
        prefix = first.added_periods
        prefix_ids = tuple(child for row in prefix for child in row.offspring_ids)
        prefix_parentage = tuple((child, first.parent_ids) for child in prefix_ids)
        first_group_id = first.group_id
        extended = self.prepare_publish(split, request(0, 2), "T2")
        direct = self.prepare_publish(one_shot, request(0, 2), "T2-direct")

        split_history = split.reproduction_group_snapshot().progressive_histories[0]
        direct_history = one_shot.reproduction_group_snapshot().progressive_histories[0]
        self.assertEqual(
            (split_history.parent_ids, split_history.world_seed, split_history.profile_id,
             split_history.profile_version, split_history.scope_digest, split_history.through_period,
             split_history.group_id, split_history.periods),
            (direct_history.parent_ids, direct_history.world_seed, direct_history.profile_id,
             direct_history.profile_version, direct_history.scope_digest, direct_history.through_period,
             direct_history.group_id, direct_history.periods),
        )
        self.assertEqual(extended.added_periods, direct.added_periods[2:])
        self.assertEqual(extended.group_id, first_group_id)
        self.assertEqual(extended.all_offspring_ids, direct.all_offspring_ids)
        self.assertEqual(extended.all_offspring_ids[:len(prefix_ids)], prefix_ids)
        self.assertEqual(tuple((child, extended.parent_ids) for child in prefix_ids), prefix_parentage)
        self.assertEqual(split.get_reproduction_group(first_group_id).offspring_ids, prefix_ids + tuple(
            child for row in extended.added_periods for child in row.offspring_ids
        ))
        self.assertFalse(split_history.parent_global_history_complete)
        self.assertFalse(split.get_reproduction_group(first_group_id).offspring_enumeration_complete)

    def test_zero_period_then_positive_extension_creates_group_only_when_needed(self):
        world = make_world()
        zero = self.prepare_publish(world, request(25, 0, ("P-SOLO",)), "zero")
        self.assertEqual(tuple(row.count for row in zero.added_periods), (0,))
        self.assertIsNone(zero.group_id)
        self.assertEqual(world.reproduction_group_snapshot().groups, ())
        self.assertEqual(world.reproduction_group_snapshot().person_id_reservations, ())
        positive = self.prepare_publish(world, request(25, 1, ("P-SOLO",)), "positive")
        self.assertGreater(positive.added_periods[0].count, 0)
        group = world.get_reproduction_group(positive.group_id)
        self.assertEqual(group.parent_ids, ("P-SOLO",))
        self.assertEqual(group.offspring_ids, positive.all_offspring_ids)
        self.assertEqual(len(set(positive.all_offspring_ids)), len(positive.all_offspring_ids))

    def test_idempotent_retry_returns_before_private_rng_and_rejects_key_reuse(self):
        world = make_world()
        req = request(8, 1)
        first = world.resolve_progressive_reproduction(req, request_key="stable", expected_revision=0)
        snapshot = world.reproduction_group_snapshot()
        with patch("reproduction_generation.random.Random", side_effect=AssertionError("retry drew")):
            replay = world.resolve_progressive_reproduction(req, request_key="stable", expected_revision=0)
        self.assertIs(first, replay)
        self.assertEqual(world.reproduction_group_snapshot(), snapshot)
        with self.assertRaisesRegex(ReproductionGroupPublicationError, "reused with different inputs"):
            world.resolve_progressive_reproduction(request(8, 2), request_key="stable", expected_revision=0)
        self.assertEqual(world.reproduction_group_snapshot(), snapshot)

    def test_overlap_profile_conflict_stale_revision_and_cross_path_scope_refuse(self):
        world = make_world()
        self.prepare_publish(world, request(4, 1), "first")
        with self.assertRaisesRegex(ValueError, "overlapping"):
            prepare_progressive_reproduction(world, request(4, 1))
        other_profile = TestOnlyIntervalReproductionProfile("different", "1", ((0, 1),))
        with self.assertRaisesRegex(ValueError, "different progressive profile"):
            prepare_progressive_reproduction(world, request(4, 2, profile=other_profile))
        stale = prepare_progressive_reproduction(world, request(4, 2))
        world.resolve_progressive_reproduction(request(4, 2), request_key="second", expected_revision=1)
        before = world.reproduction_group_snapshot()
        with self.assertRaises(StaleReproductionGroupRevision):
            world.publish_progressive_reproduction(stale, request_key="stale", expected_revision=1)
        self.assertEqual(world.reproduction_group_snapshot(), before)

    def test_extension_faults_restore_all_indexes_and_retry_preserves_aliases(self):
        phases = (
            "progressive_group", "progressive_offspring_indexes", "progressive_origin_ticks",
            "progressive_person_reservations", "progressive_history", "progressive_scope",
            "progressive_idempotency", "progressive_revision", "progressive_consistency",
        )
        for phase in phases:
            with self.subTest(phase=phase):
                world = make_world()
                first = self.prepare_publish(world, request(0, 1), "first")
                registry = world._reproduction_group_registry
                names = (
                    "_groups_by_id", "_group_id_by_parent_set", "_group_id_by_offspring",
                    "_parent_set_by_offspring", "_person_id_reservations", "_group_id_reservations",
                    "_requests", "_offspring_origin_ticks", "_generation_requests",
                    "_generation_parent_set_scopes", "_progressive_histories",
                    "_progressive_parent_set_scopes", "_progressive_requests",
                )
                aliases = tuple(getattr(registry, name) for name in names)
                before = world.reproduction_group_snapshot()
                rng_before = random.getstate()
                extension = prepare_progressive_reproduction(world, request(0, 2))
                with self.assertRaises(InjectedReproductionGroupFailure):
                    world.publish_progressive_reproduction(
                        extension, request_key="extension", expected_revision=extension.base_revision,
                        _fail_after=phase,
                    )
                self.assertEqual(world.reproduction_group_snapshot(), before)
                self.assertEqual(random.getstate(), rng_before)
                for name, alias in zip(names, aliases):
                    self.assertIs(getattr(registry, name), alias)
                self.assertIs(world.get_reproduction_group(first.group_id).offspring_ids,
                              before.groups[0].offspring_ids)
                result = self.prepare_publish(world, request(0, 2), "extension")
                self.assertEqual(result.all_offspring_ids[:len(first.all_offspring_ids)], first.all_offspring_ids)

    def test_initial_positive_publication_faults_rollback_and_retry(self):
        phases = (
            "progressive_group", "progressive_parent_set_index", "progressive_offspring_indexes",
            "progressive_origin_ticks", "progressive_person_reservations",
            "progressive_group_reservation", "progressive_history", "progressive_scope",
            "progressive_idempotency", "progressive_revision", "progressive_consistency",
        )
        for phase in phases:
            with self.subTest(phase=phase):
                world = make_world()
                prepared = prepare_progressive_reproduction(world, request(0, 1))
                before = world.reproduction_group_snapshot()
                rng_before = random.getstate()
                with self.assertRaises(InjectedReproductionGroupFailure):
                    world.publish_progressive_reproduction(
                        prepared, request_key="retry", expected_revision=0, _fail_after=phase,
                    )
                self.assertEqual(world.reproduction_group_snapshot(), before)
                self.assertEqual(random.getstate(), rng_before)
                self.assertEqual(world.resolve_progressive_reproduction(
                    request(0, 1), request_key="retry", expected_revision=0
                ).all_offspring_ids,
                    tuple(child for row in prepared.new_periods for child in row.offspring_ids))

    def test_no_encounter_being_observer_or_global_rng_side_effects(self):
        world = make_world()
        events = world.event_history
        objects = world.object_registry.object_instances
        rng = random.getstate()
        observer_belief = BeliefLedger("observer")
        observer_before = (observer_belief.evidence, observer_belief.belief_history,
                           observer_belief.inquiry_history)
        result = self.prepare_publish(world, request(0, 2), "world-only")
        self.assertIs(world.event_history, events)
        self.assertIs(world.object_registry.object_instances, objects)
        self.assertEqual(events.keys(), {"0"})
        self.assertEqual(objects, {})
        self.assertEqual(world._choice_books, [])
        self.assertEqual(random.getstate(), rng)
        self.assertEqual((observer_belief.evidence, observer_belief.belief_history,
                          observer_belief.inquiry_history), observer_before)
        self.assertTrue(result.all_offspring_ids)


if __name__ == "__main__":
    unittest.main()
