"""Read-only, world-level multigenerational ReproductionGroup queries."""
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from reproduction_generation import (
    ProgressiveReproductionRequest,
    TestOnlyIntervalReproductionProfile,
    prepare_progressive_reproduction,
)
from reproduction_group import (
    ReproductionGroupProposal,
    ReproductionGroupPublicationError,
    UnsupportedReproductionKinshipQuery,
    prepare_reproduction_group,
)
from test_reproduction_group_publication import make_world


PROFILE = TestOnlyIntervalReproductionProfile(
    "u-rel-001v3-demo", "1", ((0, 1), (1, 2), (2, 3))
)


def progressive(world, parents, seed, horizon, key):
    request = ProgressiveReproductionRequest(tuple(parents), seed, horizon, PROFILE)
    return world.resolve_progressive_reproduction(
        request, request_key=key, expected_revision=world.reproduction_group_snapshot().revision,
    )


class MultigenerationalReproductionTests(unittest.TestCase):
    def build_network(self):
        world = make_world("multigenerational reproduction")
        ab = progressive(world, ("A", "B"), 0, 1, "AB-T1")
        c1, c2 = ab.all_offspring_ids
        ad = progressive(world, ("A", "D"), 0, 0, "AD-T0")
        c3 = ad.all_offspring_ids[0]
        ce = progressive(world, (c1, "E"), 2, 1, "C1E-T1")
        grandchild = ce.all_offspring_ids[0]
        return world, ab, ad, ce, c1, c2, c3, grandchild

    def test_full_half_grandparent_queries_and_shared_offspring_parent_identity(self):
        world, ab, ad, ce, c1, c2, c3, grandchild = self.build_network()
        state_before_queries = world.reproduction_group_snapshot()
        view = state_before_queries
        self.assertEqual(view.known_parents(c1), ("A", "B"))
        self.assertIn(c2, view.known_full_siblings(c1))
        self.assertEqual(view.known_parents(c3), ("A", "D"))
        self.assertIn(c3, view.known_half_siblings(c1))
        self.assertIn((c3, ("A",), ("A", "D")), view.known_shared_parent_relatives(c1))
        self.assertEqual(view.known_parents(grandchild), tuple(sorted((c1, "E"))))
        self.assertIn((c1, ("A", "B")), view.known_grandparent_paths(grandchild))

        self.assertEqual(len(state_before_queries.groups), 3)
        self.assertEqual(len(state_before_queries.group_id_by_parent_set), 3)
        self.assertEqual(ad.parent_ids, ("A", "D"))
        self.assertEqual(ce.parent_ids, tuple(sorted((c1, "E"))))
        self.assertEqual(world.reproduction_group_snapshot(), state_before_queries)
        self.assertFalse(ab.parent_global_history_complete)
        self.assertFalse(world.get_reproduction_group(ab.group_id).offspring_enumeration_complete)

    def test_positive_to_positive_extension_preserves_linked_prior_groups_on_failure(self):
        world, ab, ad, ce, c1, c2, c3, grandchild = self.build_network()
        self.assertEqual(tuple(row.count for row in ab.added_periods), (2, 0))
        old_ids = ab.all_offspring_ids
        before = world.reproduction_group_snapshot()
        request = ProgressiveReproductionRequest(("B", "A"), 0, 2, PROFILE)
        extension = prepare_progressive_reproduction(world, request)
        self.assertGreater(extension.new_periods[-1].count, 0)
        with self.assertRaisesRegex(RuntimeError, "injected failure"):
            world.publish_progressive_reproduction(
                extension, request_key="AB-T2-failed", expected_revision=extension.base_revision,
                _fail_after="progressive_consistency",
            )
        self.assertEqual(world.reproduction_group_snapshot(), before)
        self.assertEqual(world.get_reproduction_group(ab.group_id).offspring_ids, old_ids)
        prior_by_id = {group.group_id: group for group in before.groups}
        self.assertEqual(world.get_reproduction_group(ad.group_id), prior_by_id[ad.group_id])
        self.assertEqual(world.get_reproduction_group(ce.group_id), prior_by_id[ce.group_id])

        extended = progressive(world, ("B", "A"), 0, 2, "AB-T2")
        self.assertGreater(extended.added_periods[0].count, 0)
        self.assertEqual(extended.all_offspring_ids[:len(old_ids)], old_ids)
        self.assertEqual(extended.group_id, ab.group_id)
        self.assertEqual(world.get_reproduction_group(extended.group_id).parent_ids, ("A", "B"))

    def test_later_group_partial_publication_failure_preserves_earlier_groups(self):
        world = make_world()
        ab = progressive(world, ("A", "B"), 0, 1, "AB")
        ad = progressive(world, ("A", "D"), 0, 0, "AD")
        c1 = ab.all_offspring_ids[0]
        before = world.reproduction_group_snapshot()
        prior_records = {group.group_id: group for group in before.groups}
        candidate = prepare_progressive_reproduction(
            world,
            ProgressiveReproductionRequest((c1, "E"), 2, 1, PROFILE),
        )
        with self.assertRaisesRegex(RuntimeError, "injected failure"):
            world.publish_progressive_reproduction(
                candidate, request_key="C1E-failed", expected_revision=candidate.base_revision,
                _fail_after="progressive_group",
            )
        self.assertEqual(world.reproduction_group_snapshot(), before)
        self.assertIsNone(world.get_reproduction_group(candidate.proposed_group_id))
        self.assertIs(world.get_reproduction_group(ab.group_id), prior_records[ab.group_id])
        self.assertIs(world.get_reproduction_group(ad.group_id), prior_records[ad.group_id])
        retry = progressive(world, (c1, "E"), 2, 1, "C1E-retry")
        self.assertEqual(retry.parent_ids, tuple(sorted((c1, "E"))))
        self.assertEqual(world.get_reproduction_group(ab.group_id).offspring_ids, ab.all_offspring_ids)
        self.assertEqual(world.get_reproduction_group(ad.group_id).offspring_ids, ad.all_offspring_ids)

    def test_zero_scope_no_group_cycle_refusal_and_no_world_or_observer_side_effects(self):
        world, ab, ad, ce, c1, c2, c3, grandchild = self.build_network()
        events = world.event_history
        objects = world.object_registry.object_instances
        rng_before = random.getstate()
        snapshot = world.reproduction_group_snapshot()
        self.assertIsNone(snapshot.known_parents("not-generated"))
        self.assertEqual(snapshot.known_full_siblings("not-generated"), ())

        cycle = prepare_reproduction_group(
            ReproductionGroupProposal("cycle", (c1,), ("A",), "test-cycle")
        )
        with self.assertRaisesRegex(ReproductionGroupPublicationError, "ancestry cycle"):
            world.publish_reproduction_group(
                cycle, request_key="cycle-attempt", expected_revision=snapshot.revision,
            )
        self.assertEqual(world.reproduction_group_snapshot(), snapshot)
        self.assertIs(world.event_history, events)
        self.assertIs(world.object_registry.object_instances, objects)
        self.assertEqual(objects, {})
        self.assertEqual(world._choice_books, [])
        self.assertEqual(random.getstate(), rng_before)

    def test_parent_order_reuse_and_exact_set_uniqueness(self):
        world = make_world()
        original = progressive(world, ("A", "B"), 0, 1, "AB")
        replay = progressive(world, ("B", "A"), 0, 1, "AB")
        self.assertIs(original, replay)
        self.assertEqual(len(world.reproduction_group_snapshot().groups), 1)
        self.assertEqual(len(world.reproduction_group_snapshot().progressive_histories), 1)

    def test_half_sibling_label_refuses_parent_sets_larger_than_two(self):
        world = make_world()
        three_parent_group = prepare_reproduction_group(
            ReproductionGroupProposal("three-parent", ("A", "B", "C"), ("CHILD",), "authored")
        )
        world.publish_reproduction_group(three_parent_group, request_key="three", expected_revision=0)
        with self.assertRaises(UnsupportedReproductionKinshipQuery):
            world.reproduction_group_snapshot().known_half_siblings("CHILD")


if __name__ == "__main__":
    unittest.main()
