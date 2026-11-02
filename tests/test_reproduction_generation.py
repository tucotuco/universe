"""Seeded, test-only world-level reproduction-on-demand demonstration."""
from pathlib import Path
import random
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from being import BeingDefinition, BeingInstance
from reproduction_generation import (
    StatisticalReproductionRequest,
    TestOnlyOffspringCountDistribution as Distribution,
    _sample,
    prepare_statistical_reproduction,
)
from reproduction_group import (
    InjectedReproductionGroupFailure,
    ReproductionGroupPublicationError,
    StaleReproductionGroupRevision,
    ReproductionGroupProposal,
    prepare_reproduction_group,
)
from test_reproduction_group_publication import make_world


MIXED = Distribution(
    "v1-demo-counts", "1", ((0, 1), (1, 2), (2, 3))
)
ONE = Distribution("v1-single-child", "1", ((1, 1),))


def request(parents=("P-A", "P-B"), seed=5, distribution=MIXED):
    return StatisticalReproductionRequest(parents, seed, 8, (1, 3, 5, 8), distribution)


class StatisticalReproductionTests(unittest.TestCase):
    def prepare(self, world, req=None):
        return prepare_statistical_reproduction(world, req or request())

    def publish(self, world, candidate, key="generation-1", **kwargs):
        revision = candidate.base_revision if "expected_revision" not in kwargs else kwargs.pop("expected_revision")
        return world.publish_statistical_reproduction(
            candidate, request_key=key, expected_revision=revision, **kwargs
        )

    def test_positive_two_parent_result_publishes_group_parentage_and_ordered_times(self):
        world = make_world()
        global_rng = random.getstate()
        candidate = self.prepare(world, request(parents=("P-B", "P-A"), seed=5))
        self.assertEqual(random.getstate(), global_rng)
        self.assertEqual(candidate.parent_ids, ("P-A", "P-B"))
        self.assertEqual(candidate.offspring_count, 2)
        self.assertEqual(candidate.origin_ticks, (5, 8))
        result = self.publish(world, candidate)
        snapshot = world.reproduction_group_snapshot()
        group = world.get_reproduction_group(result.group_id)
        self.assertIsNotNone(group)
        self.assertEqual(group.parent_ids, ("P-A", "P-B"))
        self.assertEqual(group.offspring_ids, result.offspring_ids)
        self.assertFalse(group.offspring_enumeration_complete)
        self.assertEqual(snapshot.offspring_origin_ticks,
                         tuple(zip(result.offspring_ids, result.origin_ticks)))
        self.assertEqual(result.coverage_scope, "this-parent-set-request-through-inclusive-horizon")
        self.assertFalse(result.parent_offspring_enumeration_complete)
        self.assertEqual(snapshot.revision, 1)
        self.assertEqual(len(snapshot.groups), 1)
        self.assertEqual(world.event_history.keys(), {"0"})
        self.assertEqual(world.object_registry.object_instances, {})
        self.assertEqual(world._choice_books, [])
        self.assertEqual(random.getstate(), global_rng)

    def test_singleton_parent_positive_result_does_not_invent_a_second_parent(self):
        world = make_world()
        candidate = self.prepare(world, request(("P-SOLO",), 7, ONE))
        outcome = self.publish(world, candidate, "asexual")
        self.assertEqual(outcome.parent_ids, ("P-SOLO",))
        self.assertEqual(len(outcome.offspring_ids), 1)
        self.assertEqual(world.get_reproduction_group(outcome.group_id).parent_ids, ("P-SOLO",))

    def test_zero_draw_commits_only_bounded_outcome_and_never_rerolls(self):
        world = make_world()
        candidate = self.prepare(world, request(("P-ZERO",), 2, MIXED))
        self.assertEqual(candidate.offspring_count, 0)
        self.assertIsNone(candidate.group_id)
        self.assertEqual(candidate.offspring_ids, ())
        self.assertEqual(candidate.origin_ticks, ())
        outcome = self.publish(world, candidate, "zero-request")
        snapshot = world.reproduction_group_snapshot()
        self.assertEqual(outcome.count, 0)
        self.assertIsNone(outcome.group_id)
        self.assertEqual(snapshot.groups, ())
        self.assertEqual(snapshot.group_id_by_parent_set, ())
        self.assertEqual(snapshot.group_id_by_offspring, ())
        self.assertEqual(snapshot.person_id_reservations, ())
        self.assertEqual(snapshot.group_id_reservations, ())
        self.assertEqual(snapshot.generation_outcomes, (outcome,))
        self.assertFalse(outcome.parent_offspring_enumeration_complete)
        self.assertEqual(outcome.coverage_scope, "this-parent-set-request-through-inclusive-horizon")
        replay = self.prepare(world, request(("P-ZERO",), 2, MIXED))
        self.assertIs(self.publish(world, replay, "zero-request", expected_revision=1), outcome)
        with self.assertRaisesRegex(ValueError, "different bounded generation outcome"):
            self.prepare(world, request(("P-ZERO",), 3, MIXED))

    def test_seeded_reproducibility_across_equivalent_worlds_and_versions_are_recorded(self):
        first, second = make_world("equivalent-a"), make_world("equivalent-b")
        a = self.publish(first, self.prepare(first), "same-request")
        b = self.publish(second, self.prepare(second), "same-request")
        self.assertEqual((a.scope_digest, a.group_id, a.offspring_ids, a.origin_ticks),
                         (b.scope_digest, b.group_id, b.offspring_ids, b.origin_ticks))
        self.assertNotEqual(a.world_identity, b.world_identity)
        self.assertEqual(a.distribution_id, MIXED.distribution_id)
        self.assertEqual(a.distribution_version, MIXED.version)
        self.assertEqual(a.algorithm, candidate_algorithm())

    def test_prepared_candidate_is_bound_to_its_world_owner(self):
        destination, source = make_world("destination"), make_world("source")
        foreign_candidate = self.prepare(source)
        with self.assertRaisesRegex(ReproductionGroupPublicationError, "does not match"):
            self.publish(destination, foreign_candidate)
        self.assertEqual(destination.reproduction_group_snapshot().revision, 0)

    def test_world_request_retry_returns_committed_result_without_constructing_rng(self):
        world = make_world()
        req = request()
        first = world.resolve_statistical_reproduction(
            req, request_key="one-call", expected_revision=0
        )
        state = world.reproduction_group_snapshot()
        with patch("reproduction_generation.random.Random", side_effect=AssertionError("retry drew")):
            replay = world.resolve_statistical_reproduction(
                req, request_key="one-call", expected_revision=0
            )
        self.assertIs(replay, first)
        self.assertEqual(world.reproduction_group_snapshot(), state)

    def test_replay_is_idempotent_key_reuse_conflict_and_stale_revision_refuse(self):
        world = make_world()
        candidate = self.prepare(world)
        other = self.prepare(world, request(("P-C", "P-D"), seed=5))
        before_rng = random.getstate()
        first = self.publish(world, candidate, "idempotent")
        state = world.reproduction_group_snapshot()
        replay_candidate = self.prepare(world, request())
        second = self.publish(world, replay_candidate, "idempotent", expected_revision=1)
        self.assertIs(first, second)
        self.assertEqual(world.reproduction_group_snapshot(), state)
        self.assertEqual(random.getstate(), before_rng)

        altered = _sample(request(seed=6), 0, world.reproduction_group_snapshot().world_identity)
        with self.assertRaisesRegex(ReproductionGroupPublicationError, "different statistical inputs"):
            self.publish(world, altered, "idempotent", expected_revision=1)
        self.assertEqual(world.reproduction_group_snapshot(), state)

        with self.assertRaises(StaleReproductionGroupRevision):
            self.publish(world, other, "stale")
        self.assertEqual(world.reproduction_group_snapshot(), state)

    def test_existing_parent_set_and_native_identity_collisions_refuse(self):
        world = make_world()
        authored = prepare_reproduction_group(
            ReproductionGroupProposal("authored-group", ("P-A", "P-B"), ("AUTHORED-CHILD",), "test")
        )
        world.publish_reproduction_group(authored, request_key="authored", expected_revision=0)
        before = world.reproduction_group_snapshot()
        with self.assertRaisesRegex(ValueError, "established ReproductionGroup"):
            self.prepare(world)
        self.assertEqual(world.reproduction_group_snapshot(), before)

        collision_world = make_world()
        candidate = self.prepare(collision_world)
        native = BeingInstance(BeingDefinition("Human", 6, 170, 10, "2d6", "Neutral", 10, 1),
                               "Collision", id=candidate.group_id)
        collision_world.add_object(native)
        with self.assertRaisesRegex(ReproductionGroupPublicationError, "native Object ID"):
            self.publish(collision_world, candidate)
        self.assertEqual(collision_world.reproduction_group_snapshot().revision, 0)
        self.assertIs(collision_world.get_object_by_id(native.id), native)

    def test_invalid_distribution_and_tick_contract_refuse_without_world_changes(self):
        world = make_world()
        before = world.reproduction_group_snapshot()
        for rows in ((), ((-1, 1),), ((0, 0),), ((1, 1), (1, 2)), ((2, 1),)):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                distribution = Distribution("bad", "1", rows)
                StatisticalReproductionRequest(("P",), 1, 2, (0,), distribution)
            self.assertEqual(world.reproduction_group_snapshot(), before)
        with self.assertRaises(ValueError):
            request(("P", "P"))
        with self.assertRaises(ValueError):
            StatisticalReproductionRequest(("P",), 1, 2, (2, 1), ONE)

    def test_positive_faults_rollback_each_write_and_retry_without_alias_replacement(self):
        phases = ("group", "parent_set_index", "offspring_indexes", "origin_ticks",
                  "person_reservations", "group_reservation", "generation_outcome",
                  "generation_scope", "idempotency", "revision", "consistency")
        for phase in phases:
            with self.subTest(phase=phase):
                world = make_world()
                prepared = self.prepare(world)
                registry = world._reproduction_group_registry
                containers = tuple(getattr(registry, field) for field in (
                    "_groups_by_id", "_group_id_by_parent_set", "_group_id_by_offspring",
                    "_parent_set_by_offspring", "_person_id_reservations", "_group_id_reservations",
                    "_requests", "_offspring_origin_ticks", "_generation_requests",
                    "_generation_parent_set_scopes"))
                before = world.reproduction_group_snapshot()
                rng_before = random.getstate()
                with self.assertRaises(InjectedReproductionGroupFailure):
                    self.publish(world, prepared, "retry", _fail_after=phase)
                self.assertEqual(world.reproduction_group_snapshot(), before)
                self.assertEqual(random.getstate(), rng_before)
                for field, alias in zip((
                    "_groups_by_id", "_group_id_by_parent_set", "_group_id_by_offspring",
                    "_parent_set_by_offspring", "_person_id_reservations", "_group_id_reservations",
                    "_requests", "_offspring_origin_ticks", "_generation_requests",
                    "_generation_parent_set_scopes"), containers):
                    self.assertIs(getattr(registry, field), alias)
                result = self.publish(world, prepared, "retry")
                self.assertEqual(result.revision, 1)

    def test_zero_faults_leave_no_group_and_retry_deterministically(self):
        for phase in ("generation_outcome", "generation_scope", "idempotency", "revision", "consistency"):
            with self.subTest(phase=phase):
                world = make_world()
                prepared = self.prepare(world, request(("P-ZERO",), 2, MIXED))
                before = world.reproduction_group_snapshot()
                with self.assertRaises(InjectedReproductionGroupFailure):
                    self.publish(world, prepared, "zero", _fail_after=phase)
                self.assertEqual(world.reproduction_group_snapshot(), before)
                result = self.publish(world, prepared, "zero")
                self.assertEqual(result.count, 0)
                self.assertEqual(world.reproduction_group_snapshot().groups, ())


def candidate_algorithm():
    return "python-random-mt19937-randrange-sample-no-replacement-sorted/1"


if __name__ == "__main__":
    unittest.main()
