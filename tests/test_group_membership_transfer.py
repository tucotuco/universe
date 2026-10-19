"""Group-owned transfer journal, current aggregate views, and original cohort integrity."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'examples')]
from group_membership_transfer import run_experiment
from library import Library
from statistical_group import StatisticalGroup, MembershipTransfer
from spatial.state import CartesianPosition
from universe import Universe

CONFIG = json.loads((ROOT / 'examples/nomadic_group.json').read_text())
CORRELATIONS = json.loads((ROOT / 'examples/nomadic_group_correlations.json').read_text())


def make_world(n=2):
    world = Universe('Membership test', library=Library(config_dir=str(ROOT / 'src/config')))
    groups = []
    for i in range(n):
        config = deepcopy(CONFIG)
        config.update(deepcopy(CORRELATIONS) if i == 0 else {})
        config['group_id'] = f'caravan-{i}'
        config['seed'] += i
        config['motion']['position'][0] += 100 * i
        group = StatisticalGroup(f'Caravan {i}', config['group_id'], config, config['seed'])
        world.add_object(group)
        groups.append(group)
    return world, groups


class GroupMembershipTransferTests(unittest.TestCase):
    def test_transfer_preserves_identity_original_composition_and_skills(self):
        world, (a, b) = make_world()
        a.formation_attribute(0, 'adults', 0, 'role')
        before_attributes = a.committed_formation_attributes(0, 'adults', 0)
        being = a.realize_being(world, 0, 'adults', 0)
        quota_before = a.formation_trait_state('trained_spotter')
        being.set_skill_level(world.get_skill_dictionary(), 'spot', 7)
        original_position = being.get_position()
        old_counts = (a.counts(), b.counts())
        a.advance(2)
        b.advance(2)
        original_position = being.get_position()
        record = a.transfer_being_to(world, being, b, time=2)
        self.assertIsInstance(record, MembershipTransfer)
        self.assertEqual(record.to_dict(), {'time': 2, 'being_id': being.id,
                           'category': 'adults', 'source_group_id': a.id,
                           'destination_group_id': b.id})
        self.assertIs(a.membership_history[0], b.membership_history[0])
        self.assertFalse(a.has_realized_member(being))
        self.assertTrue(b.has_realized_member(being))
        self.assertEqual(a.current_counts()['adults'], old_counts[0]['adults'] - 1)
        self.assertEqual(b.current_counts()['adults'], old_counts[1]['adults'] + 1)
        self.assertEqual((a.counts(), b.counts()), old_counts)
        self.assertEqual(a.committed_formation_attributes(0, 'adults', 0), before_attributes)
        self.assertEqual(a.formation_trait_state('trained_spotter'), quota_before)
        self.assertEqual(b.known_skill_state('spot')['known'][being.id]['level'], 7)
        self.assertNotIn(being.id, a.known_skill_state('spot')['known'])
        self.assertIs(world.get_object_by_id(being.id), being)
        self.assertIs(a.realize_being(world, 0, 'adults', 0), being)
        self.assertEqual(being.get_position(), original_position)

    def test_aggregate_state_distinguishes_formation_and_current_membership(self):
        world, (a, b) = make_world()
        being = a.realize_being(world, 0, 'adults', 0)
        base_a, base_b = a.counts(), b.counts()
        being.set_hit_points(-10)
        a.transfer_being_to(world, being, b)
        sa, sb = a.aggregate_state(), b.aggregate_state()
        self.assertEqual(sa['composition'], base_a)
        self.assertEqual(sb['composition'], base_b)
        self.assertEqual(sa['current_composition']['adults'], base_a['adults'] - 1)
        self.assertEqual(sb['current_composition']['adults'], base_b['adults'] + 1)
        self.assertEqual(sa['categories']['adults']['known_dead'], 0)
        self.assertEqual(sb['categories']['adults']['known_dead'], 1)
        self.assertEqual(sa['categories']['adults']['realized'], 0)
        self.assertEqual(sb['categories']['adults']['realized'], 1)
        self.assertEqual(sa['categories']['adults']['unresolved'], base_a['adults'] - 1)
        self.assertEqual(sb['categories']['adults']['unresolved'], base_b['adults'])
        for group in (a, b):
            adult = group.aggregate_state()['categories']['adults']
            self.assertEqual(adult['realized'] + adult['unresolved'], adult['current'])

    def test_return_preserves_origin_and_journals(self):
        world, (a, b) = make_world()
        being = a.realize_being(world, 0, 'adults', 0)
        qa = a.formation_trait_state('trained_spotter')
        original = (a.counts(), b.counts())
        a.advance(3)
        b.advance(3)
        first = a.transfer_being_to(world, being, b, time=3)
        a.advance(1)
        b.advance(1)
        second = b.transfer_being_to(world, being, a, time=4)
        self.assertEqual((a.current_counts(), b.current_counts()), original)
        self.assertTrue(a.has_realized_member(being))
        self.assertFalse(b.has_realized_member(being))
        self.assertEqual(a.membership_history, [first, second])
        self.assertEqual(b.membership_history, [first, second])
        self.assertEqual(a.formation_trait_state('trained_spotter'), qa)
        self.assertEqual(a.realized_being_count, 1)
        self.assertIs(world.get_object_by_id(being.id), being)

    def test_onward_transfer_preserves_incoming_history_and_identity(self):
        world, (a, b, c) = make_world(3)
        being = a.realize_being(world, 0, 'adults', 0)
        a.transfer_being_to(world, being, b, time=0)
        for group in (a, b, c):
            group.advance(1)
        onward = b.transfer_being_to(world, being, c, time=1)
        self.assertFalse(a.has_realized_member(being))
        self.assertFalse(b.has_realized_member(being))
        self.assertTrue(c.has_realized_member(being))
        self.assertEqual(len(a.membership_history), 1)
        self.assertEqual(len(b.membership_history), 2)
        self.assertEqual(len(c.membership_history), 1)
        self.assertIs(b.membership_history[-1], onward)
        self.assertIs(c.membership_history[-1], onward)
        self.assertEqual([a.current_counts()['adults'], b.current_counts()['adults'],
                          c.current_counts()['adults']],
                         [a.counts()['adults'] - 1, b.counts()['adults'],
                          c.counts()['adults'] + 1])

    def test_transfer_does_not_teleport_or_automatically_carry_arrival(self):
        world, (a, b) = make_world()
        being = a.realize_being(world, 0, 'adults', 0)
        other = a.realize_being(world, 0, 'adults', 1)
        first = being.get_position()
        other_first = other.get_position()
        a.transfer_being_to(world, being, b)
        self.assertEqual(first, being.get_position())
        a.advance(1)
        self.assertEqual(first, being.get_position())
        self.assertNotEqual(other_first, other.get_position())
        b.advance(1)
        self.assertEqual(first, being.get_position())
        b.transfer_being_to(world, being, a, time=1)
        a.advance(1)
        self.assertEqual(first, being.get_position())

    def test_preflight_invalid_requests_do_not_modify_groups(self):
        world, (a, b) = make_world()
        being = a.realize_being(world, 0, 'adults', 0)
        wrong = b.realize_being(world, 0, 'adults', 0)
        original = (a.current_counts(), b.current_counts())
        other_world = Universe('Different', library=world.library)
        bad_group = StatisticalGroup('Outside', 'outside', deepcopy(CONFIG), CONFIG['seed'])
        for src, entity, dest, target_world, when in (
            (a, being, a, world, 0),
            (a, wrong, b, world, 0),
            (a, being, bad_group, world, 0),
            (a, being, b, other_world, 0),
            (a, being, b, world, -1),
            (a, being, b, world, float('nan')),
        ):
            with self.subTest(case=(src.id, entity.id, dest.id, when)):
                with self.assertRaises(ValueError):
                    src.transfer_being_to(target_world, entity, dest, time=when)
                self.assertEqual((a.current_counts(), b.current_counts()), original)
                self.assertEqual((a.membership_history, b.membership_history), ([], []))
        a.transfer_being_to(world, being, b, time=0)
        before = (a.current_counts(), b.current_counts())
        with self.assertRaises(ValueError):
            a.transfer_being_to(world, being, b, time=0)
        with self.assertRaises(ValueError):
            b.transfer_being_to(world, being, a, time=2)
        a.advance(1)
        with self.assertRaises(ValueError):
            b.transfer_being_to(world, being, a)
        b.advance(1)
        self.assertEqual((a.current_counts(), b.current_counts()), before)
        self.assertEqual((a.current_counts(), b.current_counts()), before)
        self.assertEqual(len(a.membership_history), 1)

    def test_demo(self):
        output = run_experiment()
        self.assertEqual(output['after_departure'][0]['adults'],
                         output['baseline'][0]['adults'] - 1)
        self.assertEqual(output['after_departure'][1]['adults'],
                         output['baseline'][1]['adults'] + 1)
        self.assertEqual(output['after_return'], output['baseline'])
        self.assertEqual(output['known_spot_in_east'], 6)


if __name__ == '__main__':
    unittest.main()
