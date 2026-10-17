#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for the first bounded, explicit Encounter simulation cycle."""

import json
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath('../src'))

from action import Action
from encounter import Encounter, EncounterStep
from library import Library
from spatial.state import CartesianPosition
from universe import Universe


class RecordingAction(Action):
    """Real Action timeline contract without invoking unfinished combat rules."""

    def __init__(self, universe, actor_id, target_id, start_time, log, kind='inspect'):
        super().__init__(universe, start_time, None, kind, actor_id,
                         target_id, instrument_id=None)
        self.log = log

    def resolve(self, difficulty_class):
        self.log.append((self.event_type, self.end_time, difficulty_class))


class FailingAction(RecordingAction):
    def resolve(self, difficulty_class):
        raise RuntimeError('Action could not resolve')


class TestEncounterCycle(unittest.TestCase):
    def setUp(self):
        self.universe = Universe(name='Cycle test', library=Library(config_dir='../src/config'))
        self.encounter = Encounter(self.universe, difficulty_class=10, start_time=7)
        self.a_id = self.universe.make_being('Human', 'Observer')
        self.b_id = self.universe.make_being('Human', 'Other')
        self.item_id = self.universe.make_object('Brick', 'Brick')
        self.encounter.add_being(self.a_id)
        self.encounter.add_being(self.b_id)
        self.encounter.add_object(self.item_id)
        self.a = self.universe.get_object_by_id(self.a_id)
        self.b = self.universe.get_object_by_id(self.b_id)
        self.item = self.universe.get_object_by_id(self.item_id)
        self.a.set_position(CartesianPosition(0, 0, 0))
        self.b.set_position(CartesianPosition(10, 0, 0))
        self.item.set_position(CartesianPosition(4, 0, 0))
        self.log = []

    def initiate(self):
        self.encounter.mark_aware(self.a_id, self.b_id)
        self.encounter.decide_to_act(self.a_id, self.b_id, 'approach')

    def make_action(self, actor=None, target=None, start=None, kind='inspect', cls=RecordingAction):
        return cls(self.universe, actor or self.a_id, target or self.item_id,
                   self.encounter.time if start is None else start, self.log, kind)

    def test_uninitiated_cannot_step_or_schedule(self):
        with self.assertRaises(RuntimeError):
            self.encounter.step()
        with self.assertRaises(RuntimeError):
            self.encounter.schedule_action(self.make_action())
        self.assertEqual(self.encounter.time, 7)

    def test_simultaneous_continuous_movement_for_beings_and_objects(self):
        self.initiate()
        result = self.encounter.step(duration=2, velocities={
            self.a_id: (1.0, 2, 0),
            self.b_id: (-2, 0, 1),
            self.item_id: (0, -1, 0),
        })
        self.assertIsInstance(result, EncounterStep)
        self.assertEqual((result.start_time, result.end_time), (7, 9))
        self.assertEqual(result.moved_entity_ids, (self.a_id, self.b_id, self.item_id))
        self.assertEqual(result.completed_action_ids, ())
        self.assertEqual(self.a.get_position(), CartesianPosition(2, 4, 0))
        self.assertEqual(self.b.get_position(), CartesianPosition(6, 0, 2))
        self.assertEqual(self.item.get_position(), CartesianPosition(4, -2, 0))
        self.assertEqual(self.encounter.time, 9)
        self.assertAlmostEqual(self.encounter.distance_between_entities(self.a_id, self.b_id), 6)

    def test_scheduled_action_resolves_only_when_due(self):
        self.initiate()
        action = self.make_action()
        action.end_time = 9
        self.encounter.schedule_action(action)
        self.assertIs(self.universe.get_event_by_id(action.id), action)
        self.assertEqual(action.parent_event_id, self.encounter.id)
        first = self.encounter.step()
        self.assertEqual(first.completed_action_ids, ())
        self.assertEqual(self.encounter.pending_action_list, [action.id])
        second = self.encounter.step()
        self.assertEqual(second.completed_action_ids, (action.id,))
        self.assertEqual(self.log, [('inspect', 9, 10)])
        self.assertEqual(self.encounter.pending_action_list, [])
        self.assertEqual(self.encounter.finished_action_list, [action.id])
        self.assertEqual(self.encounter.step().completed_action_ids, ())
        self.assertEqual(len(self.log), 1)
        data = json.loads(self.encounter.to_json())
        self.assertEqual(data['pending_action_list'], [])
        self.assertEqual(data['finished_action_list'], [action.id])

    def test_schedule_multiple_actions_by_due_time_then_queue_order(self):
        self.initiate()
        late = self.make_action(kind='late')
        early = self.make_action(kind='early')
        same = self.make_action(kind='same')
        late.end_time = 10
        early.end_time = 8
        same.end_time = 8
        for action in (late, early, same):
            self.encounter.schedule_action(action)
        result = self.encounter.step(duration=3)
        self.assertEqual(result.completed_action_ids, (early.id, same.id, late.id))
        self.assertEqual([entry[0] for entry in self.log], ['early', 'same', 'late'])

    def test_failed_resolution_does_not_mark_action_completed(self):
        self.initiate()
        action = self.make_action(cls=FailingAction)
        self.encounter.schedule_action(action)
        with self.assertRaisesRegex(RuntimeError, 'could not resolve'):
            self.encounter.step()
        self.assertEqual(self.encounter.pending_action_list, [action.id])
        self.assertEqual(self.encounter.finished_action_list, [])
        self.assertEqual(self.encounter.time, 7)

    def test_movement_validation_before_any_position_changes(self):
        self.initiate()
        initial = self.a.get_position()
        with self.assertRaises(ValueError):
            self.encounter.step(velocities={self.a_id: (2, 0, 0), 'absent': (0, 1, 0)})
        self.assertEqual(self.a.get_position(), initial)
        self.assertEqual(self.encounter.time, 7)
        with self.assertRaises(ValueError):
            self.encounter.step(velocities={self.a_id: (math.inf, 0, 0)})
        with self.assertRaises(ValueError):
            self.encounter.step(velocities={self.a_id: (0, 0, 0), self.b_id: (0, 0, math.nan)})
        with self.assertRaises(ValueError):
            self.encounter.step(duration=0)
        with self.assertRaises(ValueError):
            self.encounter.step(duration=math.inf)
        self.assertEqual(self.a.get_position(), initial)

    def test_end_time_boundary(self):
        self.initiate()
        self.encounter.end_time = 8
        self.encounter.step()
        with self.assertRaises(ValueError):
            self.encounter.step()
        self.assertEqual(self.encounter.time, 8)

    def test_step_applies_movement_before_action_and_environment_hook(self):
        self.initiate()
        timeline = []
        action = self.make_action()

        def resolve(_difficulty_class):
            timeline.append(('action', self.a.get_position(), self.encounter.time))

        def update_environment():
            timeline.append(('environment', self.a.get_position(), self.encounter.time))

        action.resolve = resolve
        self.encounter.update_environment = update_environment
        self.encounter.schedule_action(action)
        self.encounter.step(velocities={self.a_id: (2, 0, 0)})
        self.assertEqual(timeline, [
            ('action', CartesianPosition(2, 0, 0), 7),
            ('environment', CartesianPosition(2, 0, 0), 7),
        ])
        self.assertEqual(self.encounter.time, 8)

    def test_reject_duplicate_and_foreign_actions(self):
        self.initiate()
        action = self.make_action()
        self.encounter.schedule_action(action)
        with self.assertRaises(ValueError):
            self.encounter.schedule_action(action)
        foreign = self.make_action(actor='outsider')
        with self.assertRaises(ValueError):
            self.encounter.schedule_action(foreign)
        foreign_target = self.make_action(target='outsider')
        with self.assertRaises(ValueError):
            self.encounter.schedule_action(foreign_target)
        past = self.make_action(start=6)
        with self.assertRaises(ValueError):
            self.encounter.schedule_action(past)
        self.encounter.end_time = 8
        late = self.make_action()
        late.end_time = 9
        with self.assertRaises(ValueError):
            self.encounter.schedule_action(late)


if __name__ == '__main__':
    unittest.main()
