"""Inactive portable native accepted-choice declaration descriptors (5D2C1)."""
from dataclasses import replace
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_encounter_inspection import InspectionFixture
from activities import RunAction, SpotAction
from action_choice import Reservation, declaration
from checkpoint_choices import (ChoiceDescriptorRejected, DESCRIPTOR_SCHEMA,
    describe_accepted_choice, describe_native_declaration)
from checkpoint_inventory import capture_checkpoint_candidate


class TestPortableChoiceDescriptors(InspectionFixture):
    def accepted(self, actions):
        self.enable()
        return self.enc.schedule_choice(actions)

    def descriptor(self, view):
        return describe_accepted_choice(self.world, self.enc, view.id)

    def test_supported_run_and_spot_choice_is_detached_deterministic_and_exact(self):
        run = RunAction(self.world, self.a.id, .125, 1.375, 1.25, experience=7)
        spot = self.f.spot(self.c, start=1.75, duration=1.125, maximum=12)
        view = self.accepted((run, spot))
        before = self.raw()
        one = self.descriptor(view)
        two = self.descriptor(view)
        self.assertEqual(one, two)
        self.assertEqual(one.schema, DESCRIPTOR_SCHEMA)
        self.assertEqual(one.action_ids, (run.id, spot.id))
        self.assertEqual(one.first_start, ('binary64', float(.125).hex()))
        data = one.to_data()
        self.assertTrue(all(type(x) in (str, int, bool, float, tuple, type(None))
                            for x in self._walk(data)))
        flattened = tuple(self._walk(data))
        self.assertNotIn('identity', flattened)
        self.assertNotIn('native_signature_rebuild_required', flattened)
        self.assertEqual(before, self.raw())
        self.assertEqual(self.enc.get_choice(view.id).state, 'accepted')

    def test_equivalent_distinct_action_objects_share_logical_descriptor(self):
        self.enable()
        original = self.f.spot(self.c, start=.375, duration=1.25, maximum=17)
        counterpart = SpotAction(self.world, original.actor_id, original.target_id,
                                 original.start_time, duration=1.25, max_distance=17,
                                 experience=original.practice_experience,
                                 die_roll=original.declared_roll)
        counterpart.id = original.id
        self.assertIsNot(original, counterpart)
        self.assertEqual(describe_native_declaration(original, self.world, self.enc),
                         describe_native_declaration(counterpart, self.world, self.enc))

    def test_unknown_callbacks_and_custom_subclasses_refuse(self):
        self.enable()
        action = self.f.spot()
        action.on_schedule = lambda *_: None
        with self.assertRaises(ChoiceDescriptorRejected):
            describe_native_declaration(action, self.world, self.enc)

        class CustomSpot(SpotAction):
            pass
        custom = CustomSpot(self.world, self.a.id, self.b.id, 2)
        with self.assertRaises(ChoiceDescriptorRejected):
            describe_native_declaration(custom, self.world, self.enc)

    def test_changed_timing_member_order_reservations_and_ambiguous_ids_refuse(self):
        one, two = self.f.spot(start=2), self.f.spot(self.c, start=3)
        view = self.accepted((one, two))
        book = self.enc._choice_book
        record = book._choices[view.id]

        one.start_time = 2.25
        with self.assertRaisesRegex(ChoiceDescriptorRejected, 'signature is stale'):
            self.descriptor(view)
        one.start_time = 2

        book._choices[view.id] = replace(record, members=tuple(reversed(record.members)))
        with self.assertRaises(ChoiceDescriptorRejected):
            self.descriptor(view)
        book._choices[view.id] = record

        book._reservations = (Reservation(view.id, one.id, self.a.id, 2, 3),)
        with self.assertRaisesRegex(ChoiceDescriptorRejected, 'reservations disagree'):
            self.descriptor(view)
        book._reservations = ()

        two_id = two.id
        two.id = one.id
        duplicate_signatures = tuple((member.key, declaration(member.action))
                                     for member in record.members)
        book._choices[view.id] = replace(record, signatures=duplicate_signatures)
        with self.assertRaisesRegex(ChoiceDescriptorRejected, 'duplicate Action logical ID'):
            self.descriptor(view)
        two.id = two_id
        book._choices[view.id] = record

        self.world.object_registry.object_instances['ambiguous-alias'] = self.a
        try:
            with self.assertRaisesRegex(ChoiceDescriptorRejected, 'ambiguous'):
                self.descriptor(view)
        finally:
            del self.world.object_registry.object_instances['ambiguous-alias']

    def test_inventory_uses_portable_choice_descriptor_without_claiming_readiness(self):
        view = self.accepted((self.f.spot(start=2),))
        candidate = capture_checkpoint_candidate(self.world, self.enc, quiescent=True,
            rng_scope='exclusive_encounter', native_adapters=True)
        codes = {d.code for d in candidate.diagnostics}
        self.assertNotIn('native_signature_rebuild_required', codes)
        self.assertFalse(candidate.closure_validated)
        self.assertFalse(candidate.portable_schema_defined)
        self.assertFalse(candidate.restore_verified)
        self.assertIn(DESCRIPTOR_SCHEMA, tuple(self._walk(candidate.envelope)))

    @staticmethod
    def _walk(value):
        yield value
        if type(value) is tuple:
            for child in value:
                yield from TestPortableChoiceDescriptors._walk(child)


if __name__ == '__main__':
    unittest.main()
