"""Patch 1: Q/B persistence and the native Encounter post-movement freeze.

This suite deliberately does not claim to test work accounting, physical-check
application to attack rolls, or atomic multi-actor combat transactions.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import unittest
from dataclasses import FrozenInstanceError

sys.path.insert(0, os.path.abspath('../src'))

from action import Action
from being import BeingDefinition
from encounter import Encounter
from encounter_fatigue_bridge import FrozenFatigueFrame
from library import Library
from physical_fatigue import PhysicalFatigueState, read_physical_fatigue
from spatial.state import CartesianPosition
from standard_fatigue_check import physical_check_penalty
from universe import Universe


class TestPhysicalFatigueState(unittest.TestCase):
    def setUp(self):
        self.world = Universe('Q/B', library=Library(config_dir='../src/config'))
        self.being = self.world.get_object_by_id(self.world.make_being('Human', 'Scout'))

    def test_fresh_and_reset_retain_no_legacy_inference(self):
        self.assertEqual(self.being.get_physical_fatigue(), PhysicalFatigueState(1, 1))
        self.assertIsNone(self.being.physiology_id)
        self.being.set_physical_fatigue(.234567890123456, .876543210987654)
        self.being.set_fatigue_level(5)  # legacy is unrelated
        self.assertEqual(self.being.get_physical_fatigue().q, .234567890123456)
        self.being.reset()
        self.assertEqual(self.being.get_physical_fatigue(), PhysicalFatigueState())
        self.assertEqual(self.being.get_fatigue_level(), 0)

    def test_immutable_and_validated(self):
        self.being.set_physical_fatigue(.12345, .54321)
        before = self.being.get_physical_fatigue()
        with self.assertRaises(FrozenInstanceError):
            before.q = 0.0
        for val in (-.0001, 1.0001, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                self.being.set_physical_fatigue(val, .5)
        for val in (True, '0.5', None):
            with self.assertRaises(TypeError):
                self.being.set_physical_fatigue(.5, val)
        self.assertIs(self.being.get_physical_fatigue(), before)

    def test_round_trip_and_versioned_reference(self):
        self.being.set_physiology_id('physiology/human-trained@4')
        self.being.set_physical_fatigue(.1372345234523, .9623942034234)
        payload = json.loads(self.being.to_json())
        self.assertEqual(payload['physical_fatigue'], {
            'version': 1, 'q': .1372345234523, 'b': .9623942034234,
            'physiology_id': 'physiology/human-trained@4'})
        other = self.world.get_object_by_id(self.world.make_being('Human', 'Other'))
        other.restore_physical_fatigue(payload)
        self.assertEqual(other.get_physical_fatigue(), self.being.get_physical_fatigue())
        self.assertEqual(other.physiology_id, self.being.physiology_id)
        self.assertEqual(other.get_physical_fatigue().to_dict(other.physiology_id),
                         payload['physical_fatigue'])
        with self.assertRaises(ValueError):
            other.set_physiology_id('')

    def test_older_save_migration_requires_explicit_opt_in(self):
        old = {'fatigue_level': 5}  # must NOT turn into empty Q/B
        self.being.set_physical_fatigue(.4, .6)
        with self.assertRaisesRegex(ValueError, 'opt in'):
            self.being.restore_physical_fatigue(old)
        self.assertEqual(self.being.get_physical_fatigue(), PhysicalFatigueState(.4, .6))
        self.being.restore_physical_fatigue(old, missing='fresh')
        self.assertEqual(self.being.get_physical_fatigue(), PhysicalFatigueState())
        self.assertEqual(self.being.get_fatigue_level(), 0)
        # Reject invalid restored reserves atomically.
        self.being.set_physical_fatigue(.4, .6)
        before = self.being.get_physical_fatigue()
        with self.assertRaises(ValueError):
            self.being.restore_physical_fatigue({'physical_fatigue': {
                'version': 1, 'q': .5, 'b': math.nan, 'physiology_id': 'x@1'}})
        self.assertIs(self.being.get_physical_fatigue(), before)
        with self.assertRaises(ValueError):
            read_physical_fatigue({'physical_fatigue': {
                'version': 2, 'q': 1.0, 'b': 1.0, 'physiology_id': None}})

    def test_definition_copy_inherits_reference(self):
        definition = BeingDefinition('Human', 6, 160, 5, '2d4', 'N', 10, 0,
                                     physiology_id='human@r4')
        clone = definition.copy()
        self.assertEqual(clone.physiology_id, 'human@r4')
        self.assertEqual(clone.physiology_id, definition.physiology_id)

    def test_reference_math_is_reused_byte_for_byte(self):
        root = Path(__file__).resolve().parents[1]
        for filename in ('standard_fatigue_check.py', 'universe_physical_fatigue_r4.py'):
            native = (root / 'src' / filename).read_bytes()
            workbench = (root / 'universe-fatigue-workbench' / filename).read_bytes()
            self.assertEqual(hashlib.sha256(native).digest(), hashlib.sha256(workbench).digest())
        self.assertEqual(physical_check_penalty(1, 1), 0)
        self.assertEqual(physical_check_penalty(0, 0), 4)
        self.assertEqual(physical_check_penalty(.5, .5), 2)


class TestEncounterFatigueFrame(unittest.TestCase):
    def setUp(self):
        self.world = Universe('Native freeze', library=Library(config_dir='../src/config'))
        self.encounter = Encounter(self.world, 10, 0)
        self.world.add_event(self.encounter)
        self.a = self.world.get_object_by_id(self.world.make_being('Human', 'A'))
        self.b = self.world.get_object_by_id(self.world.make_being('Human', 'B'))
        for being in (self.a, self.b):
            self.encounter.add_being(being.id)
        self.a.set_position(CartesianPosition(0, 0, 0))
        self.b.set_position(CartesianPosition(1, 0, 0))
        self.encounter.mark_aware(self.a.id, self.b.id)
        self.encounter.decide_to_act(self.a.id, self.b.id)

    def make_action(self, actor):
        action = Action(self.world, self.encounter.time, None, 'inspect',
                        actor.id, self.b.id if actor is self.a else self.a.id, None)
        action.end_time = 1
        self.encounter.schedule_action(action)
        return action

    def test_common_snapshot_even_after_earlier_actor_changes_fatigue_and_hp(self):
        self.a.set_physical_fatigue(.3, .2)
        self.b.set_physical_fatigue(.7, .8)
        first = self.make_action(self.a)
        second = self.make_action(self.b)
        seen = []
        def first_resolve(dc):
            seen.append(('first', self.encounter.fatigue_view(self.a.id),
                         self.encounter.fatigue_view(self.b.id), self.a.get_position()))
            self.a.set_physical_fatigue(.01, .01)
            self.b.set_physical_fatigue(.01, .02)
            self.b.current.hit_points = 0
        def second_resolve(dc):
            seen.append(('second', self.encounter.fatigue_view(self.a.id),
                         self.encounter.fatigue_view(self.b.id), self.a.get_position()))
        first.resolve = first_resolve
        second.resolve = second_resolve
        result = self.encounter.step(velocities={self.a.id: (1, 0, 0)})
        self.assertEqual(result.completed_action_ids, (first.id, second.id))
        self.assertEqual(seen[0][1:3], seen[1][1:3])
        self.assertEqual((seen[1][1].q, seen[1][1].b), (.3, .2))
        self.assertEqual((seen[1][2].q, seen[1][2].b), (.7, .8))
        self.assertEqual(seen[1][1].check_modifier, -physical_check_penalty(.3, .2))
        self.assertEqual(seen[0][3], CartesianPosition(1, 0, 0))
        self.assertEqual(seen[1][3], CartesianPosition(1, 0, 0))
        self.assertEqual(self.b.get_hit_points(), 0)
        self.assertEqual(self.b.get_physical_fatigue().q, .01)  # mutation in test, not settlement
        self.assertEqual(len(self.encounter.fatigue_frame_history), 1)
        self.assertEqual(self.encounter.fatigue_frame_history[0]['views'][self.b.id]['q'], .7)
        self.assertEqual(self.encounter.fatigue_frame_history[0]['time'], 1)
        self.assertEqual(json.loads(self.encounter.to_json())['fatigue_frame_history'],
                         self.encounter.fatigue_frame_history)
        with self.assertRaises(RuntimeError):
            self.encounter.fatigue_view(self.a.id)
        with self.assertRaises(FrozenInstanceError):
            seen[0][1].q = .9

    def test_empty_step_snapshot_and_universe_event_serialization(self):
        self.encounter.step()
        self.assertEqual(len(self.encounter.fatigue_frame_history), 1)
        serialized = json.loads(self.world.to_json())
        entry = serialized['event_history'][self.encounter.id]
        self.assertNotIn('_active_fatigue_frame', entry)
        self.assertNotIn('last_fatigue_frame', entry)
        self.assertEqual(entry['fatigue_frame_history'], self.encounter.fatigue_frame_history)
        saved_being = serialized['object_registry']['object_instances'][self.a.id]
        self.assertEqual(saved_being['physical_fatigue'],
                         {'version': 1, 'q': 1.0, 'b': 1.0, 'physiology_id': None})
        with tempfile.TemporaryDirectory() as folder:
            filename = os.path.join(folder, 'world.json')
            self.world.save_to_file(filename)
            loaded = Universe('restored', library=Library(config_dir='../src/config'))
            before = loaded.to_json()
            with self.assertRaisesRegex(ValueError, 'checkpoint restoration is unsupported'):
                loaded.load_from_file(filename)
            self.assertEqual(loaded.to_json(), before)

    def test_snapshot_is_not_a_write_through_and_follows_next_step(self):
        before = self.a.get_physical_fatigue()
        self.encounter.step()
        view = self.encounter.last_fatigue_frame.view(self.a.id)
        self.assertEqual(view.q, before.q)
        self.a.set_physical_fatigue(.5, .6)
        self.assertEqual(view.q, 1.0)
        self.encounter.step()
        self.assertEqual(self.encounter.last_fatigue_frame.view(self.a.id).q, .5)
        self.assertEqual(self.encounter.fatigue_frame_history[0]['views'][self.a.id]['q'], 1.0)


if __name__ == '__main__':
    unittest.main()
