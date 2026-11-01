"""Bounded realization of a member already counted in one StatisticalGroup."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'examples')]

from atomic_publication import PublicationFailure
from realize_counted_group_member import prepare_scenario, run_scenario


class TestRealizeCountedGroupMember(unittest.TestCase):
    def test_one_counted_adult_is_realized_then_acts_without_disclosure(self):
        result = run_scenario()
        self.assertEqual(result['realization_timing'],
                         'initial configuration, before Encounter construction')
        self.assertTrue(result['member']['group_member'])
        self.assertEqual(result['member']['beings_realized'], 1)
        self.assertEqual(result['member']['formation_slot'], (0, 'adults', 0))
        self.assertTrue(result['group_counts_unchanged'])
        self.assertFalse(result['observer_one']['member_identity_in_evidence'])
        self.assertFalse(result['observer_two_received_evidence'])
        self.assertEqual(result['observer_one']['uncertainty'], 0)
        self.assertEqual(result['observer_one']['spot_action_boundary'], 6)
        self.assertEqual(result['native_run']['outcome'], 'success')
        self.assertEqual(result['native_run']['displacement_m'], 2)
        self.assertEqual(result['native_run']['target_owned_run_experience'], 7)
        self.assertEqual(result['spot_experience'], (0, 0))
        self.assertTrue(result['rng_unchanged'])
        self.assertTrue(result['member_registry_identity_preserved'])

    def test_same_seed_and_slot_repeat_with_stable_identity_and_state(self):
        first, second = run_scenario(), run_scenario()
        self.assertEqual(first['member']['logical_id'], second['member']['logical_id'])
        self.assertEqual(first['member']['position'], second['member']['position'])
        self.assertEqual(first['group_counts'], second['group_counts'])
        self.assertEqual(first['observer_one']['exact_visible_aggregate_count'],
                         second['observer_one']['exact_visible_aggregate_count'])
        self.assertEqual(first['native_run'], second['native_run'])

    def test_invalid_slot_and_unsupported_category_do_not_add_a_being(self):
        world, _, _, group, member, _, _, _, counts = prepare_scenario()
        registry_count = world.get_object_registry().len()
        reality = group._composition_reality.view().all_facts()
        group_state = (group.realized_being_count, group.materialized_count,
                       group.current_counts())
        with self.assertRaises(IndexError):
            group.realize_being(world, 0, 'adults', 10_000)
        with self.assertRaises(NotImplementedError):
            group.realize_being(world, 0, 'dogs', 0, 0)
        self.assertEqual(world.get_object_registry().len(), registry_count)
        self.assertEqual((group.realized_being_count, group.materialized_count,
                          group.current_counts()), group_state)
        self.assertEqual(group._composition_reality.view().all_facts(), reality)
        self.assertEqual(group.counts(), counts)
        self.assertIs(group.realize_being(world, 0, 'adults', 0), member)

    def test_spot_publication_fault_preserves_preexisting_realization_and_reality(self):
        (world, encounter, observers, group, member, ledgers, _, rng,
         counts) = prepare_scenario()
        before = {
            'registry_count': world.get_object_registry().len(),
            'facts': group._composition_reality.view().all_facts(),
            'group_counts': group.counts(),
            'current_counts': group.current_counts(),
            'rng': rng.state,
            'member_position': member.get_position(),
        }
        import atomic_publication
        publish = atomic_publication.publish_interval_candidate

        def fail_after_observers(*args, **kwargs):
            kwargs['_fail_after'] = 'observers'
            return publish(*args, **kwargs)

        with patch('atomic_publication.publish_interval_candidate',
                   side_effect=fail_after_observers):
            with self.assertRaises(PublicationFailure):
                encounter.step(6)
        self.assertEqual(encounter.time, 0)
        self.assertEqual(world.get_object_registry().len(), before['registry_count'])
        self.assertIs(world.get_object_by_id(member.id), member)
        self.assertTrue(group.has_realized_member(member))
        self.assertEqual(group._composition_reality.view().all_facts(), before['facts'])
        self.assertEqual(group.counts(), before['group_counts'])
        self.assertEqual(group.current_counts(), before['current_counts'])
        self.assertEqual(group.counts(), counts)
        self.assertEqual(member.get_position(), before['member_position'])
        self.assertEqual(rng.state, before['rng'])
        self.assertTrue(all(not ledger.evidence for ledger in ledgers))
        self.assertTrue(all(not encounter.is_aware(observer.id, group.id)
                            for observer in observers))


if __name__ == '__main__':
    unittest.main()
