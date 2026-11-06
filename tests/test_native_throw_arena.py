"""U-THROW-004 exact native release and per-boundary projectile state."""
import math
from pathlib import Path
import random
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'examples'))

import atomic_publication
from action import Action
from activities import ThrowAction
from atomic_publication import PublicationFailure
from encounter import Encounter
from interval_staging import StaleInterval, validate_interval_candidate
from native_throw_arena import (build_native_scene, build_projection,
                                PROJECTILE_WEIGHT_LB, RELEASE_BOUNDARY)
from spatial.state import CartesianPosition
from throwing import ProjectileFlight, ProjectileBoundaryState


class NativeThrowTests(unittest.TestCase):
    def test_native_release_and_each_integer_flight_boundary(self):
        world, enc, actor, projectile, rng, action = build_native_scene()
        initial_rng = rng.state
        authored_position = projectile.get_position()
        self.assertEqual(enc.active_reservations[0].object_id, projectile.id)
        self.assertIsNone(projectile.__dict__.get('_projectile_flight'))
        enc.step(3)
        self.assertEqual(projectile.get_position(), authored_position)
        self.assertIsNone(action.resolution)
        enc.step(1)
        speed, projection = build_projection()
        flight = projectile.__dict__['_projectile_flight']
        self.assertIs(type(flight), ProjectileFlight)
        self.assertEqual(action.resolution.outcome, 'released')
        self.assertEqual(projectile.get_position(), projection.release_position)
        self.assertAlmostEqual(math.dist(flight.velocity_m_s, (0, 0, 0)), speed * 0.9144)
        self.assertAlmostEqual(flight.impact_time, 4 + projection.flight_time_s)
        self.assertNotIn(projectile.id, actor.possessions)
        self.assertEqual(projectile.current.hit_points, 1)
        self.assertEqual(projectile.current.weight, PROJECTILE_WEIGHT_LB)
        self.assertEqual(actor.skill_use_history, [])
        self.assertEqual(rng.state, initial_rng)
        release_receipt = enc.__dict__['_atomic_interval_history'][-1]
        self.assertEqual(release_receipt.boundary, 4)
        release_rows = atomic_publication.target_effects_from(projectile, action.id)
        self.assertEqual(len([row for row in release_rows if row.effect.__class__.__name__ == 'ProjectileReleaseEffect']), 1)
        release_identity = next(row.identity for row in release_rows
            if row.effect.__class__.__name__ == 'ProjectileReleaseEffect')
        committed = atomic_publication._COMMITTED_RECEIPTS[id(release_receipt)]
        self.assertIs(committed[0](), release_receipt)
        self.assertIs(committed[1](), enc)
        self.assertTrue(release_receipt.committed)
        positions = [projectile.get_position()]
        previous_states = list(projectile.__dict__['_atomic_projectile_history'])
        for boundary in (5, 6, 7):
            enc.step(1)
            receipt = enc.__dict__['_atomic_interval_history'][-1]
            self.assertEqual(receipt.boundary, boundary)
            state = projectile.__dict__['_atomic_projectile_history'][-1]
            self.assertIs(type(state), ProjectileBoundaryState)
            self.assertEqual(state.source_effect_identity,
                             (release_identity.encounter_id, release_identity.boundary,
                              release_identity.source_action_id, release_identity.channel,
                              release_identity.slot))
            self.assertEqual(state.impact_time, flight.impact_time)
            if boundary < 7:
                self.assertEqual(state.status, 'in_flight')
                self.assertEqual(projectile.__dict__['_projectile_flight'].status, 'in_flight')
                expected = projection.position_at(boundary - 4)
            else:
                self.assertEqual(state.status, 'landed')
                self.assertEqual(projectile.__dict__['_projectile_flight'].status, 'landed')
                self.assertEqual(state.impact_time, flight.impact_time)
                self.assertEqual(state.boundary, 7)
                expected = projection.landing_position
            self.assertAlmostEqual(projectile.get_position().x, expected.x)
            self.assertAlmostEqual(projectile.get_position().y, expected.y)
            self.assertAlmostEqual(projectile.get_position().z, expected.z)
            positions.append(projectile.get_position())
            previous_states.append(state)
        self.assertEqual(projectile.get_position(), projection.landing_position)
        self.assertEqual(enc.time, 7)
        self.assertEqual(len(enc.__dict__['_atomic_interval_history']), 7)
        inspection = enc.inspect_committed(7)
        for boundary, expected_status in ((4,'in_flight'),(5,'in_flight'),
                                          (6,'in_flight'),(7,'landed')):
            inspected = enc.inspect_committed(boundary).target(projectile.id)
            self.assertEqual(inspected.projectile_state.status, expected_status)
            self.assertEqual(inspected.position, previous_states[boundary-4].position)
        self.assertEqual(rng.state, initial_rng)
        self.assertEqual(tuple(projectile.__dict__['_atomic_projectile_history']), tuple(previous_states))
        for prior, expected in zip(positions, previous_states):
            self.assertEqual(prior, expected.position)
        landed = projectile.get_position()
        committed_flight_history = tuple(projectile.__dict__['_atomic_projectile_history'])
        enc.step(1)
        self.assertEqual(projectile.get_position(), landed)
        self.assertEqual(tuple(projectile.__dict__['_atomic_projectile_history']), committed_flight_history)

    def test_repeat_scene_has_identical_boundaries_effects_positions_and_rng(self):
        outputs = []
        for _ in range(2):
            _, enc, _, projectile, rng, action = build_native_scene(seed=913)
            before = rng.state
            for _ in range(7): enc.step(1)
            outputs.append((action.resolution.outcome,
                tuple((s.boundary, s.position.as_tuple(), s.status, s.impact_time,
                       s.source_effect_identity)
                      for s in projectile.__dict__['_atomic_projectile_history']),
                tuple(enc.__dict__['_atomic_interval_history'][-1].effect_ids), rng.state))
            self.assertEqual(rng.state, before)
        self.assertEqual(outputs[0], outputs[1])

    def test_overlapping_reservation_invalid_parameters_and_generic_base_refusal(self):
        world, enc, actor, projectile, rng, action = build_native_scene()
        competing = ThrowAction(world, actor.id, projectile.id, 0,
            heavy_load_reference_lb=100, elevation_degrees=45,
            id='throw-demo/competing')
        validation = enc.validate_choice(enc.propose_choice((competing,)))
        self.assertFalse(validation.valid)
        self.assertTrue(any('actively reserved' in d.reason for d in validation.diagnostics))
        self.assertNotIn(competing.id, world.event_history)
        projectile.current.weight = 51.0  # Above Strength 10's adopted 50 lb absolute limit.
        with self.assertRaisesRegex(ValueError, 'weight bracket'):
            action.prepare_schedule(enc)
        projectile.current.weight = PROJECTILE_WEIGHT_LB
        with self.assertRaises(ValueError):
            ThrowAction(world, actor.id, projectile.id, 0,
                heavy_load_reference_lb=100, elevation_degrees=float('nan'))
        generic = Action(world, 0, 4, 'throw', actor.id, None, projectile.id,
                         id='throw-demo/generic')
        rejected = enc.validate_choice(enc.propose_choice((generic,)))
        self.assertFalse(rejected.valid)
        self.assertTrue(any('unsupported transactional base Action activity' in d.reason
                            for d in rejected.diagnostics))

    def test_release_failure_rolls_back_and_deterministic_retry_commits(self):
        world, enc, actor, projectile, rng, action = build_native_scene()
        before_rng = rng.state
        original = atomic_publication.publish_interval_candidate
        def fail_after_target(encounter, candidate, **kwargs):
            if candidate.boundary == 4: kwargs['_fail_after'] = 'targets'
            return original(encounter, candidate, **kwargs)
        with patch('atomic_publication.publish_interval_candidate', fail_after_target):
            with self.assertRaises(PublicationFailure) as caught:
                enc.step(4)
        self.assertFalse(caught.exception.rollback_errors)
        self.assertEqual(enc.time, 3)
        self.assertEqual(projectile.get_position(), CartesianPosition(0, 0, 0))
        self.assertIn(projectile.id, actor.possessions)
        self.assertNotIn('_projectile_flight', projectile.__dict__)
        self.assertIsNone(action.resolution)
        self.assertEqual(enc.__dict__['_atomic_interval_history'][-1].boundary, 3)
        self.assertEqual(rng.state, before_rng)
        enc.recover_transactional_progression(caught.exception.recovery_token)
        enc.step(1)
        self.assertEqual(action.resolution.outcome, 'released')
        self.assertEqual(enc.last_processed_boundary, 4)

    def test_flight_boundary_failure_preserves_last_committed_state_and_retry(self):
        _, enc, _, projectile, rng, action = build_native_scene()
        enc.step(4)
        before_position = projectile.get_position()
        before_flight = projectile.__dict__['_projectile_flight']
        before_history = tuple(projectile.__dict__['_atomic_projectile_history'])
        before_receipts = tuple(enc.__dict__['_atomic_interval_history'])
        before_receipt_ids = set(atomic_publication._COMMITTED_RECEIPTS)
        original = atomic_publication.publish_interval_candidate
        def fail_after_movement(encounter, candidate, **kwargs):
            if candidate.boundary == 5: kwargs['_fail_after'] = 'movement'
            return original(encounter, candidate, **kwargs)
        with patch('atomic_publication.publish_interval_candidate', fail_after_movement):
            with self.assertRaises(PublicationFailure) as caught: enc.step(1)
        self.assertEqual(enc.time, 4)
        self.assertEqual(projectile.get_position(), before_position)
        self.assertIs(projectile.__dict__['_projectile_flight'], before_flight)
        self.assertEqual(tuple(projectile.__dict__['_atomic_projectile_history']), before_history)
        self.assertEqual(tuple(enc.__dict__['_atomic_interval_history']), before_receipts)
        self.assertEqual(set(atomic_publication._COMMITTED_RECEIPTS), before_receipt_ids)
        enc.recover_transactional_progression(caught.exception.recovery_token)
        enc.step(1)
        self.assertGreater(projectile.get_position().x, before_position.x)
        self.assertEqual(enc.last_processed_boundary, 5)

    def test_release_uses_the_common_post_movement_boundary_position(self):
        _, enc, actor, projectile, _, action = build_native_scene()
        enc.step(4, velocities={actor.id: (1.0, 0.0, 0.0)})
        self.assertEqual(actor.get_position(), CartesianPosition(4.0, 0.0, 0.0))
        self.assertEqual(projectile.get_position(),
                         CartesianPosition(4.0, 0.0, 69.0 * 0.0254))
        self.assertEqual(action.resolution.outcome, 'released')

    def test_in_flight_candidate_refuses_stale_object_position(self):
        _, enc, _, projectile, rng, _ = build_native_scene()
        enc.step(4)
        candidate=enc.prepare_interval_candidate(5,rng_owner=rng)
        before=projectile.get_position()
        projectile.spatial_state.position=CartesianPosition(before.x+0.25,before.y,before.z)
        with self.assertRaises(StaleInterval):
            validate_interval_candidate(enc,candidate,rng_owner=rng)
        projectile.spatial_state.position=before
        validate_interval_candidate(enc,candidate,rng_owner=rng)


if __name__ == '__main__':
    unittest.main()
