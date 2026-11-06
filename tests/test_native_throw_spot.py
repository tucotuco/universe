"""U-THROW-006: ordinary native Spot observes a flying Object at its boundary."""
from pathlib import Path
import random
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'examples'))

import atomic_publication
from atomic_publication import PublicationFailure
from native_throw_spot import build_spot_scene, run_native_throw_spot
from object_observation import ObjectObservation, ObjectObservationLedger
from spatial import CartesianPosition


class NativeThrowSpotTests(unittest.TestCase):
    def test_successful_spot_records_committed_airborne_boundary_six_state(self):
        scene = run_native_throw_spot(seed=5)
        enc = scene['encounter']
        evidence = scene['evidence']
        boundary6 = scene['boundary6']

        self.assertEqual(scene['throw'].resolution.outcome, 'released')
        self.assertEqual(scene['run'].resolution.outcome, 'success')
        self.assertEqual(scene['boundary4'].action(scene['throw'].id).facts.outcome, 'released')
        self.assertEqual(scene['boundary5'].action(scene['run'].id).facts.outcome, 'success')
        self.assertEqual(enc._atomic_interval_history[-4].action_ids, (scene['throw'].id,))
        self.assertEqual(enc._atomic_interval_history[-3].action_ids, (scene['run'].id,))
        self.assertEqual(enc._atomic_interval_history[-2].action_ids,
                         (scene['spot'].id, scene['second_spot'].id))
        self.assertEqual(enc.inspect_committed(6).target(scene['projectile'].id).projectile_state.status,
                         'in_flight')
        self.assertEqual(enc.inspect_committed(7).target(scene['projectile'].id).projectile_state.status,
                         'landed')
        self.assertEqual(evidence.position, boundary6.target(scene['projectile'].id).position)
        self.assertEqual(evidence.projectile_status, 'in_flight')
        self.assertEqual((evidence.observer_id, evidence.object_id, evidence.source_action_id,
                          evidence.encounter_id, evidence.boundary, evidence.time),
                         (scene['spotter'].id, scene['projectile'].id, scene['spot'].id,
                          enc.id, 6, 6))
        self.assertEqual(scene['spotter_evidence'].observations, (evidence,))
        self.assertEqual(scene['second_evidence'].observations, ())
        self.assertTrue(enc.is_aware(scene['spotter'].id, scene['projectile'].id))
        self.assertFalse(enc.is_aware(scene['second'].id, scene['projectile'].id))
        self.assertFalse(enc.is_aware(scene['runner'].id, scene['projectile'].id))
        self.assertEqual(scene['spot'].resolution.outcome, 'success')
        self.assertEqual(scene['second_spot'].resolution.outcome, 'failure')
        self.assertFalse(scene['spotter'].get_skill_experience('spot'))
        self.assertFalse(scene['second'].get_skill_experience('spot'))
        self.assertEqual(scene['rolls'], (20, 9))

    def test_failed_spot_publishes_no_object_evidence_or_awareness(self):
        scene = build_spot_scene(seed=5)
        enc = scene['encounter']
        enc.step(4)
        enc.step(1, velocities={scene['runner'].id: (1.25, 0.0, 0.0)})
        self.assertEqual(scene['second_evidence'].observations, ())
        self.assertFalse(enc.is_aware(scene['second'].id, scene['projectile'].id))
        enc.step(1)
        self.assertEqual(scene['second_spot'].resolution.outcome, 'failure')
        self.assertEqual(scene['second_evidence'].observations, ())
        self.assertFalse(enc.is_aware(scene['second'].id, scene['projectile'].id))
        view = enc.inspect_committed(6)
        self.assertEqual(view.target(scene['projectile'].id).projectile_state.status, 'in_flight')
        self.assertEqual(scene['spotter_evidence'].last_observation(scene['projectile'].id).boundary, 6)
        self.assertFalse(scene['second'].get_skill_experience('spot'))

    def test_publication_rollback_restores_object_evidence_and_retry_is_deterministic(self):
        scene = build_spot_scene(seed=5)
        enc, rng = scene['encounter'], scene['rng']
        enc.step(4)
        enc.step(1, velocities={scene['runner'].id: (1.25, 0.0, 0.0)})
        projectile, spotter = scene['projectile'], scene['spotter']
        before = (
            enc.time, enc.last_processed_boundary, projectile.get_position(),
            projectile.__dict__['_projectile_flight'],
            tuple(projectile.__dict__['_atomic_projectile_history']),
            tuple(projectile.__dict__['_atomic_target_history']),
            tuple(scene['spotter_evidence'].observations),
            tuple(scene['second_evidence'].observations),
            enc.awareness, tuple(enc.pending_action_list), tuple(enc.finished_action_list),
            tuple(enc._atomic_interval_history), rng.state,
            set(atomic_publication._COMMITTED_RECEIPTS),
            scene['spot'].resolution, scene['second_spot'].resolution,
            spotter.get_skill_experience('spot'),
        )
        publisher = atomic_publication.publish_interval_candidate

        def fail_after_target_write(owner, candidate, **kwargs):
            if candidate.boundary == 6:
                kwargs['_fail_after'] = 'targets'
            return publisher(owner, candidate, **kwargs)

        with patch.object(atomic_publication, 'publish_interval_candidate', fail_after_target_write):
            with self.assertRaises(PublicationFailure) as caught:
                enc.step(1)
        self.assertEqual(caught.exception.phase, 'targets')
        self.assertFalse(caught.exception.rollback_errors)
        after = (
            enc.time, enc.last_processed_boundary, projectile.get_position(),
            projectile.__dict__['_projectile_flight'],
            tuple(projectile.__dict__['_atomic_projectile_history']),
            tuple(projectile.__dict__['_atomic_target_history']),
            tuple(scene['spotter_evidence'].observations),
            tuple(scene['second_evidence'].observations),
            enc.awareness, tuple(enc.pending_action_list), tuple(enc.finished_action_list),
            tuple(enc._atomic_interval_history), rng.state,
            set(atomic_publication._COMMITTED_RECEIPTS),
            scene['spot'].resolution, scene['second_spot'].resolution,
            spotter.get_skill_experience('spot'),
        )
        self.assertEqual(after, before)

        enc.recover_transactional_progression(caught.exception.recovery_token)
        enc.step(1)
        evidence = scene['spotter_evidence'].last_observation(projectile.id)
        self.assertEqual(scene['spot'].resolution.outcome, 'success')
        self.assertEqual(scene['second_spot'].resolution.outcome, 'failure')
        self.assertEqual(evidence.position, enc.inspect_committed(6).target(projectile.id).position)
        self.assertEqual(evidence.projectile_status, 'in_flight')
        self.assertEqual(enc._atomic_interval_history[-1].boundary, 6)
        self.assertEqual(enc._atomic_interval_history[-1].action_ids,
                         (scene['spot'].id, scene['second_spot'].id))
        expected = random.Random(5)
        expected.randint(1, 20)
        expected.randint(1, 20)
        self.assertEqual(rng.state, expected.getstate())
        self.assertEqual(spotter.get_skill_experience('spot'), 0)

    def test_evidence_record_is_detached_immutable_and_last_seen_is_not_live(self):
        scene = run_native_throw_spot(seed=5)
        ledger = scene['spotter_evidence']
        evidence = ledger.last_observation(scene['projectile'].id)
        self.assertIsInstance(evidence, ObjectObservation)
        self.assertEqual(evidence.position, CartesianPosition(*evidence.position.as_tuple()))
        with self.assertRaises((AttributeError, TypeError)):
            evidence.position = CartesianPosition(999.0, 999.0, 999.0)
        enc = scene['encounter']
        receipt_count = len(enc._atomic_interval_history)
        current_position = scene['projectile'].get_position()
        current_status = scene['projectile'].__dict__['_projectile_flight'].status
        again = ledger.last_observation(scene['projectile'].id)
        self.assertIs(again, evidence)
        self.assertEqual(again.boundary, 6)
        self.assertEqual(again.position, scene['boundary6'].target(scene['projectile'].id).position)
        self.assertEqual(scene['boundary7'].target(scene['projectile'].id).projectile_state.status, 'landed')
        self.assertEqual(ledger.last_observation(scene['projectile'].id), evidence)
        self.assertEqual(scene['projectile'].get_position(), current_position)
        self.assertEqual(scene['projectile'].__dict__['_projectile_flight'].status, current_status)
        self.assertEqual(len(enc._atomic_interval_history), receipt_count)

    def test_ledger_rejects_invalid_owner_and_mutable_or_unsupported_status(self):
        ledger = ObjectObservationLedger('observer')
        with self.assertRaises(ValueError):
            ObjectObservationLedger(' ')
        with self.assertRaises(ValueError):
            ObjectObservation('id', 'observer', 'object', 'action', 'encounter', 1, 1,
                             CartesianPosition(0, 0, 0), 'future')
        with self.assertRaises(ValueError):
            ObjectObservation('id', 'observer', 'object', 'action', 'encounter', 1, 1,
                             CartesianPosition(0, 0, 0), [])
        self.assertIsNone(ledger.last_observation('object'))


if __name__ == '__main__':
    unittest.main()
