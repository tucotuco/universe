"""Inactive bounded Run/Spot checkpoint-envelope assembly tests."""
from dataclasses import replace
import random
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tests'))

import test_interval_staging as interval_fixtures
from activities import RunAction
from atomic_publication import RNGCursor
from checkpoint_envelope import (
    ENVELOPE_SCHEMA,
    EnvelopeRejected,
    assemble_native_run_spot_envelope,
    validate_native_run_spot_envelope,
    _digest,
)
from interval_staging import _read_set


def assert_detached(test, value):
    if value is None or type(value) in (str, int, bool):
        return
    test.assertIs(type(value), tuple)
    for item in value:
        assert_detached(test, item)


class TestNativeRunSpotEnvelope(unittest.TestCase):
    def setUp(self):
        self.f = interval_fixtures.TestIntervalStaging()
        self.f.setUp()
        self.world, self.enc = self.f.world, self.f.enc
        self.cursor = RNGCursor(random.Random(808).getstate())
        self.enc.enable_transactional_progression(quiescent=True, rng_owner=self.cursor)

    def capture(self):
        return assemble_native_run_spot_envelope(
            self.world, self.enc, quiescent=True, rng_scope='exclusive_encounter')

    def test_initial_capture_is_detached_repeatable_pure_and_not_ready(self):
        before = _read_set(self.enc)
        rng_before = self.cursor.state
        one = self.capture()
        two = self.capture()
        self.assertEqual(one.schema, ENVELOPE_SCHEMA)
        self.assertEqual(one.to_data(), two.to_data())
        self.assertEqual(one.boundary_sequence, ())
        self.assertTrue(one.bounded_envelope_validated)
        self.assertFalse(one.closure_validated)
        self.assertFalse(one.portable_schema_defined)
        self.assertFalse(one.restore_verified)
        assert_detached(self, one.to_data())
        result = validate_native_run_spot_envelope(
            self.world, self.enc, one, quiescent=True)
        self.assertTrue(result.bounded_envelope_validated)
        self.assertFalse(result.closure_validated)
        self.assertEqual(before, _read_set(self.enc))
        self.assertEqual(rng_before, self.cursor.state)

    def test_two_boundaries_future_choice_and_batch_practice_compose_together(self):
        first = RunAction(self.world, self.f.a.id, 0, 1, .5, experience=3)
        simultaneous = RunAction(self.world, self.f.a.id, 0, 1, .5, experience=4)
        self.enc.schedule_choice((first, simultaneous))
        self.enc.step(1, velocities={self.f.a.id: (1, 0, 0)})
        runner = RunAction(self.world, self.f.a.id, 1, 1, 1, experience=7)
        self.enc.schedule_choice((runner,))
        self.enc.step(1)
        future = self.f.spot(actor=self.f.a, start=4.25)
        accepted = self.enc.schedule_choice((future,))

        envelope = self.capture()
        self.assertEqual(envelope.boundary_sequence, (1, 2))
        self.assertEqual(len(envelope.committed_receipt_chain), 8)
        self.assertEqual(envelope.committed_receipt_chain[0],
                         'universe.committed-native-receipt-chain/1')
        self.assertEqual(len(envelope.accepted_choice_descriptors), 1)
        choice = envelope.accepted_choice_descriptors[0]
        self.assertEqual(choice[1], accepted.id)
        self.assertIn(future.id, choice[5])
        from experience import BatchSkillUse
        self.assertTrue(any(type(use) is BatchSkillUse for use in self.f.a.skill_use_history))
        self.assertTrue(validate_native_run_spot_envelope(
            self.world, self.enc, envelope, quiescent=True).bounded_envelope_validated)

    def test_stale_state_modified_or_inconsistent_components_refuse(self):
        envelope = self.capture()
        self.f.a.current.hit_points += 1
        with self.assertRaisesRegex(EnvelopeRejected, 'stale'):
            validate_native_run_spot_envelope(
                self.world, self.enc, envelope, quiescent=True)

        fresh = self.capture()
        with self.assertRaisesRegex(EnvelopeRejected, 'schema'):
            validate_native_run_spot_envelope(
                self.world, self.enc, replace(fresh, schema='future/99'), quiescent=True)
        altered = replace(fresh, committed_receipt_chain=('alien-receipt',),
                          content_digest='')
        altered = replace(altered, content_digest=_digest(altered.payload()))
        with self.assertRaisesRegex(EnvelopeRejected, 'components'):
            validate_native_run_spot_envelope(
                self.world, self.enc, altered, quiescent=True)
        object.__setattr__(fresh, 'content_digest', '0' * 64)
        with self.assertRaisesRegex(EnvelopeRejected, 'digest'):
            validate_native_run_spot_envelope(
                self.world, self.enc, fresh, quiescent=True)

    def test_one_boundary_and_invalid_alias_refuse(self):
        action = RunAction(self.world, self.f.a.id, 0, 1, .5, experience=3)
        self.enc.schedule_choice((action,))
        self.enc.step(1)
        envelope = self.capture()
        self.assertEqual(envelope.boundary_sequence, (1,))
        self.assertTrue(validate_native_run_spot_envelope(
            self.world, self.enc, envelope, quiescent=True).bounded_envelope_validated)

        current = self.f.a.current
        self.f.a.__dict__['current'] = self.f.b.current
        try:
            with self.assertRaises((EnvelopeRejected, ValueError, TypeError)):
                self.capture()
        finally:
            self.f.a.__dict__['current'] = current

    def test_unsupported_family_and_legacy_export_guard_remain_refused(self):
        from encounter import BoundaryInvariantError
        with self.assertRaises(BoundaryInvariantError):
            self.enc.assert_checkpoint_exportable()
        from field_observation import BeliefLedger
        group = self.f.f.f.group()
        unsupported = self.f.f.observe(
            self.f.a, group, ledger=BeliefLedger(self.f.a.id))
        self.enc.schedule_choice((unsupported,))
        with self.assertRaises((EnvelopeRejected, ValueError, TypeError)):
            self.capture()
        with self.assertRaises(BoundaryInvariantError):
            self.enc.assert_checkpoint_exportable()
        with self.assertRaises(ValueError):
            self.world.to_json()

    def test_external_recipient_callback_and_shared_rng_refuse_without_execution(self):
        from field_observation import BeliefLedger
        group = self.f.f.f.group()
        observer_action = self.f.f.observe(
            self.f.a, group, ledger=BeliefLedger(self.f.a.id))
        self.enc.schedule_choice((observer_action,))
        with self.assertRaises((EnvelopeRejected, ValueError, TypeError)):
            self.capture()

        import transactional_progression
        with patch.dict(transactional_progression._BINDINGS,
                        {object(): SimpleNamespace(encounter=lambda: object(),
                                                   rng_owner=self.cursor)}):
            with self.assertRaises((EnvelopeRejected, ValueError, TypeError)):
                self.capture()

    def test_custom_callback_is_refused_without_execution(self):
        history = self.f.f.f.history()
        called = []
        from history_conversation import AskAboutPastAction
        ask = AskAboutPastAction(
            self.world, self.f.c.id, self.f.a.id, 0,
            episode_time=0, topic='lessons',
            generate=self.f.f.f.recipe(history), received_accounts=[])
        self.enc.schedule_choice((ask,))
        ask.generate = lambda *args: called.append('executed')
        with self.assertRaises((EnvelopeRejected, ValueError, TypeError)):
            self.capture()
        self.assertEqual(called, [])


if __name__ == '__main__':
    unittest.main()
