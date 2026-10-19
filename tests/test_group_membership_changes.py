"""Independent Group-owned join/leave with a persistent ungrouped Being."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'examples')]

from activities import RunAction
from encounter import Encounter
from group_membership_changes import run_experiment
from library import Library
from statistical_group import MembershipChange, StatisticalGroup
from universe import Universe

CONFIG = json.loads((ROOT / 'examples/nomadic_group.json').read_text())


def make_world(n=3):
    world = Universe('Membership tests', library=Library(config_dir=str(ROOT / 'src/config')))
    groups = []
    for i in range(n):
        cfg = deepcopy(CONFIG)
        cfg['group_id'] = f'caravan-{i}'
        cfg['seed'] += i
        cfg['motion']['position'][0] += i * 100
        group = StatisticalGroup(f'Caravan {i}', cfg['group_id'], cfg, cfg['seed'])
        world.add_object(group)
        groups.append(group)
    return world, groups


class GroupMembershipChangeTests(unittest.TestCase):
    def test_leave_without_destination_and_join_later(self):
        world, (a, b, _) = make_world()
        being = a.realize_being(world, 0, 'adults', 0)
        formation = (a.counts(), b.counts())
        a.advance(2)
        left_position = being.get_position()
        record = a.leave_being(world, being)
        self.assertIsInstance(record, MembershipChange)
        self.assertEqual(record.to_dict(), {'time': 2, 'being_id': being.id,
            'category': 'adults', 'group_id': a.id, 'action': 'leave'})
        self.assertFalse(a.has_realized_member(being))
        self.assertFalse(b.has_realized_member(being))
        self.assertEqual(a.current_counts()['adults'], formation[0]['adults'] - 1)
        self.assertEqual(b.current_counts(), formation[1])
        a.advance(3)
        self.assertEqual(being.get_position(), left_position)
        b.advance(5)
        being.set_skill_level(world.get_skill_dictionary(), 'spot', 6)
        entered = b.join_being(world, being)
        self.assertEqual(entered.time, 5)
        self.assertEqual(entered.action, 'join')
        self.assertEqual(a.membership_history, [record])
        self.assertEqual(b.membership_history, [entered])
        self.assertEqual(b.current_counts()['adults'], formation[1]['adults'] + 1)
        self.assertEqual((a.counts(), b.counts()), formation)
        self.assertIs(world.get_object_by_id(being.id), being)
        self.assertIs(a.realize_being(world, 0, 'adults', 0), being)
        self.assertEqual(being.get_skill_level('spot'), 6)
        self.assertEqual(being.get_position(), left_position)
        b.advance(1)
        self.assertEqual(being.get_position(), left_position)  # Join is not travel.

    def test_independent_encounter_actions_remain_possible(self):
        world, (a, b, _) = make_world()
        being = a.realize_being(world, 0, 'adults', 0)
        a.leave_being(world, being)
        encounter = Encounter(world, difficulty_class=10, start_time=0)
        encounter.add_being(being.id)
        encounter.add_object(b.id)
        encounter.mark_aware(being.id, b.id)
        encounter.decide_to_act(being.id, b.id, 'approach eastern caravan')
        action = RunAction(world, being.id, start_time=0, duration=1,
                           minimum_distance=2, experience=250)
        encounter.schedule_action(action)
        encounter.step(1, velocities={being.id: (3, 0, 0)})
        self.assertEqual(action.resolution.outcome, 'success')
        self.assertEqual(being.get_skill_level('run'), 1)
        self.assertEqual(being.get_skill_experience('run'), 250)
        self.assertEqual(len(being.skill_use_history), 1)
        b.advance(2)
        b.join_being(world, being)
        self.assertEqual(being.get_skill_experience('run'), 250)
        self.assertEqual(len(being.skill_use_history), 1)
        self.assertIs(world.get_object_by_id(being.id), being)

    def test_same_group_rejoin_and_separate_subsequent_departure(self):
        world, (a, _, _) = make_world()
        being = a.realize_being(world, 0, 'adults', 0)
        original = a.counts()
        a.leave_being(world, being)
        a.advance(10)
        a.join_being(world, being)
        self.assertEqual(a.current_counts(), original)
        self.assertTrue(a.has_realized_member(being))
        self.assertEqual([event.action for event in a.membership_history], ['leave', 'join'])
        a.leave_being(world, being)
        self.assertEqual(a.current_counts()['adults'], original['adults'] - 1)
        self.assertEqual([event.action for event in a.membership_history], ['leave', 'join', 'leave'])

    def test_independent_moves_through_three_groups(self):
        world, (a, b, c) = make_world()
        being = a.realize_being(world, 0, 'adults', 0)
        a.leave_being(world, being)
        b.advance(2)
        b.join_being(world, being)
        b.advance(1)
        b.leave_being(world, being)
        c.advance(7)
        c.join_being(world, being)
        self.assertFalse(a.has_realized_member(being))
        self.assertFalse(b.has_realized_member(being))
        self.assertTrue(c.has_realized_member(being))
        self.assertEqual([len(g.membership_history) for g in (a, b, c)], [1, 2, 1])
        self.assertEqual([g.current_counts()['adults'] for g in (a, b, c)],
                         [a.counts()['adults'] - 1, b.counts()['adults'], c.counts()['adults'] + 1])

    def test_requires_explicit_leave_before_join(self):
        world, (a, b, _) = make_world()
        being = a.realize_being(world, 0, 'adults', 0)
        before = (a.current_counts(), b.current_counts())
        with self.assertRaisesRegex(ValueError, 'must leave'):
            b.join_being(world, being)
        self.assertEqual((a.current_counts(), b.current_counts()), before)
        self.assertFalse(b.membership_history)

    def test_validation_and_unchanged_state_after_failure(self):
        world, (a, b, _) = make_world()
        being = a.realize_being(world, 0, 'adults', 0)
        outsider = Universe('Other', library=world.library)
        bogus = StatisticalGroup('Bogus', 'bogus', deepcopy(CONFIG), CONFIG['seed'])
        before = (a.current_counts(), b.current_counts())
        for operation in (
            lambda: b.leave_being(world, being),
            lambda: a.leave_being(outsider, being),
            lambda: bogus.join_being(world, being),
            lambda: a.leave_being(world, being, time=10),
            lambda: a.leave_being(world, being, time=float('nan')),
            lambda: a.leave_being(world, being, time='not a number'),
            lambda: b.join_being(world, being, category='dogs'),
        ):
            with self.assertRaises((ValueError, NotImplementedError)):
                operation()
            self.assertEqual((a.current_counts(), b.current_counts()), before)
            self.assertFalse(a.membership_history)
            self.assertFalse(b.membership_history)
        a.leave_being(world, being)
        with self.assertRaises(ValueError):
            a.leave_being(world, being)
        with self.assertRaises(ValueError):
            b.join_being(world, being, time=1)
        b.join_being(world, being)
        with self.assertRaises(ValueError):
            b.join_being(world, being)
        with self.assertRaises(ValueError):
            a.join_being(world, being)
        self.assertEqual(len(a.membership_history), 1)
        self.assertEqual(len(b.membership_history), 1)

    def test_cannot_join_before_previous_departure_time(self):
        world, (a, b, _) = make_world()
        being = a.realize_being(world, 0, 'adults', 0)
        a.advance(4)
        a.leave_being(world, being)
        with self.assertRaisesRegex(ValueError, 'cannot precede'):
            b.join_being(world, being)
        self.assertEqual(len(a.membership_history), 1)
        self.assertEqual(b.membership_history, [])
        b.advance(4)
        b.join_being(world, being)

    def test_known_health_and_skill_aggregate_follow_current_membership(self):
        world, (a, b, _) = make_world()
        being = a.realize_being(world, 0, 'adults', 0)
        being.set_hit_points(-10)
        being.set_skill_level(world.get_skill_dictionary(), 'spot', 7)
        formation = (a.counts(), b.counts())
        a.leave_being(world, being)
        self.assertEqual(a.aggregate_state()['categories']['adults']['known_dead'], 0)
        self.assertNotIn(being.id, a.known_skill_state('spot')['known'])
        self.assertEqual(b.aggregate_state()['categories']['adults']['known_dead'], 0)
        b.join_being(world, being)
        self.assertEqual(b.aggregate_state()['categories']['adults']['known_dead'], 1)
        self.assertEqual(b.known_skill_state('spot')['known'][being.id]['level'], 7)
        self.assertEqual((a.counts(), b.counts()), formation)

    def test_formation_quota_and_identity_survive_membership_changes(self):
        world, (a, b, _) = make_world()
        being = a.realize_being(world, 0, 'adults', 0)
        original_formation_attributes = a.committed_formation_attributes(0, 'adults', 0)
        initial_composition = a.counts()
        a.leave_being(world, being)
        b.join_being(world, being)
        self.assertIs(a.realize_being(world, 0, 'adults', 0), being)
        self.assertEqual(a.committed_formation_attributes(0, 'adults', 0),
                         original_formation_attributes)
        self.assertEqual(a.counts(), initial_composition)
        self.assertEqual(a.materialized_count, 1)
        self.assertEqual(b.materialized_count, 0)

    def test_independently_created_being_can_join_without_previous_group(self):
        world, (a, b, _) = make_world()
        being_id = world.make_being('Human', 'Wanderer')
        being = world.get_object_by_id(being_id)
        before = b.counts()
        join = b.join_being(world, being)
        self.assertEqual(join.action, 'join')
        self.assertTrue(b.has_realized_member(being))
        self.assertEqual(b.current_counts()['adults'], before['adults'] + 1)
        b.leave_being(world, being)
        self.assertEqual(b.current_counts(), before)
        self.assertIs(world.get_object_by_id(being.id), being)
        self.assertFalse(any(g.has_realized_member(being) for g in (a, b)))

    def test_demo(self):
        output = run_experiment()
        self.assertEqual(output['alone_counts'][0]['adults'], output['baseline'][0]['adults'] - 1)
        self.assertEqual(output['alone_counts'][1], output['baseline'][1])
        self.assertEqual(output['joined_counts'][1]['adults'], output['baseline'][1]['adults'] + 1)
        self.assertEqual((output['leave'].time, output['join'].time), (1, 5))


if __name__ == '__main__':
    unittest.main()
