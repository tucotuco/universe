"""U-THROW-005 integration: native Run and autonomous flight share a boundary."""
from pathlib import Path
import random
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'examples'))

import atomic_publication
from activities import RunAction, ThrowAction
from atomic_publication import (PublicationFailure, target_effects_from,
                                target_interval_history)
from being import BeingInstance
from encounter import Encounter
from library import Library
from native_throw_arena import build_projection
from native_throw_concurrent_run import build_concurrent_scene
from spatial.state import CartesianPosition
from universe import Universe


class ConcurrentThrowRunTests(unittest.TestCase):
    def test_run_and_flight_commit_together_then_land_at_boundary_7(self):
        world, enc, thrower, runner, projectile, rng, throw, run = build_concurrent_scene()
        rng_before = rng.state
        thrower_start = thrower.get_position()
        runner_start = runner.get_position()
        _, projection = build_projection()

        enc.step(4)
        self.assertEqual(enc.last_processed_boundary, 4)
        self.assertEqual(throw.resolution.outcome, 'released')
        self.assertEqual(run.resolution, None)
        self.assertEqual(runner.get_position(), runner_start)
        receipt_4 = enc._atomic_interval_history[-1]
        self.assertEqual(receipt_4.boundary, 4)
        release_state = enc.inspect_committed(4).target(projectile.id)
        release_position = release_state.position
        release_flight = release_state.projectile_state
        release_history = tuple(projectile.__dict__['_atomic_projectile_history'])
        receipt_history = tuple(enc._atomic_interval_history)

        # Multiple read-only views are snapshots only: they do not move the
        # projectile, change the Action, advance RNG, or issue receipts.
        for _ in range(2):
            again = enc.inspect_committed(4).target(projectile.id)
            self.assertEqual(again.position, release_position)
            self.assertEqual(again.projectile_state, release_flight)
        self.assertEqual(projectile.get_position(), release_position)
        self.assertEqual(tuple(projectile.__dict__['_atomic_projectile_history']), release_history)
        self.assertEqual(tuple(enc._atomic_interval_history), receipt_history)
        self.assertEqual(rng.state, rng_before)

        enc.step(1, velocities={runner.id: (1.25, 0.0, 0.0)})
        self.assertEqual(enc.last_processed_boundary, 5)
        receipt_5 = enc._atomic_interval_history[-1]
        self.assertEqual(receipt_5.boundary, 5)
        self.assertEqual(receipt_5.action_ids, (run.id,))
        self.assertIn(run.id, enc.finished_action_list)
        self.assertEqual(run.resolution.outcome, 'success')
        self.assertEqual(enc.inspect_committed(5).action(run.id).facts.outcome, 'success')
        self.assertEqual(enc.inspect_committed(5).target(runner.id).position,
                         CartesianPosition(101.25, 0.0, 0.0))
        flight_5 = enc.inspect_committed(5).target(projectile.id)
        self.assertEqual(flight_5.position, projection.position_at(1.0))
        self.assertEqual(flight_5.projectile_state.status, 'in_flight')
        self.assertEqual(flight_5.projectile_state.source_action_id, throw.id)
        self.assertEqual(flight_5.projectile_state.source_effect_identity,
                         release_flight.source_effect_identity)
        self.assertEqual({item.source_action_id for item in receipt_5.effect_ids}, {run.id})
        self.assertEqual({item.channel for item in receipt_5.effect_ids}, {'effect', 'lifecycle'})
        run_practice = [item.effect for item in enc.inspect_committed(5).action(run.id).effects
                        if item.effect.__class__.__name__ == 'PracticeEffect']
        self.assertEqual(len(run_practice), 1)
        self.assertEqual(run_practice[0].target_id, runner.id)
        self.assertEqual(run_practice[0].experience, 6)
        self.assertEqual(runner.get_skill_experience('run'), 6)
        runner_run_contributions = target_effects_from(runner, run.id)
        self.assertEqual(len(runner_run_contributions), 1)
        self.assertEqual(runner_run_contributions[0].identity.boundary, 5)
        self.assertEqual(runner_run_contributions[0].effect, run_practice[0])
        self.assertEqual(thrower.get_position(), thrower_start)
        self.assertEqual(rng.state, rng_before)

        prior_4 = enc.inspect_committed(4).target(projectile.id)
        expected = {6: (projection.position_at(2.0), 'in_flight'),
                    7: (projection.landing_position, 'landed')}
        for boundary, (position, status) in expected.items():
            enc.step(1)
            inspection = enc.inspect_committed(boundary)
            projectile_view = inspection.target(projectile.id)
            runner_view = inspection.target(runner.id)
            self.assertEqual(projectile_view.position, position)
            self.assertEqual(projectile_view.projectile_state.status, status)
            self.assertEqual(projectile_view.projectile_state.impact_time,
                             release_flight.impact_time)
            self.assertEqual(runner_view.position, CartesianPosition(101.25, 0.0, 0.0))
            self.assertEqual(thrower.get_position(), thrower_start)
        self.assertEqual(enc.inspect_committed(7).target(projectile.id).projectile_state.impact_time,
                         6.337306187730018)
        self.assertEqual(prior_4.position, release_position)
        self.assertEqual(prior_4.projectile_state, release_flight)
        self.assertEqual(rng.state, rng_before)

    def test_joint_run_and_flight_publication_rollback_then_retry(self):
        _, enc, thrower, runner, projectile, rng, throw, run = build_concurrent_scene(seed=781)
        enc.step(4)
        before = (
            enc.time, enc.last_processed_boundary, projectile.get_position(),
            projectile.__dict__['_projectile_flight'],
            tuple(projectile.__dict__['_atomic_projectile_history']),
            runner.get_position(), runner.get_skill_experience('run'),
            tuple(runner.skill_use_history), tuple(target_interval_history(runner)),
            tuple(target_interval_history(projectile)), run.resolution,
            tuple(enc.pending_action_list), tuple(enc.finished_action_list),
            tuple(enc._atomic_interval_history), rng.state,
            set(atomic_publication._COMMITTED_RECEIPTS), throw.resolution,
            thrower.get_position(),
        )
        publisher = atomic_publication.publish_interval_candidate

        def inject_after_targets(owner, candidate, **kwargs):
            if candidate.boundary == 5:
                kwargs['_fail_after'] = 'targets'
            return publisher(owner, candidate, **kwargs)

        with patch.object(atomic_publication, 'publish_interval_candidate', inject_after_targets):
            with self.assertRaises(PublicationFailure) as caught:
                enc.step(1, velocities={runner.id: (1.25, 0.0, 0.0)})
        self.assertEqual(caught.exception.phase, 'targets')
        self.assertFalse(caught.exception.rollback_errors)
        after = (
            enc.time, enc.last_processed_boundary, projectile.get_position(),
            projectile.__dict__['_projectile_flight'],
            tuple(projectile.__dict__['_atomic_projectile_history']),
            runner.get_position(), runner.get_skill_experience('run'),
            tuple(runner.skill_use_history), tuple(target_interval_history(runner)),
            tuple(target_interval_history(projectile)), run.resolution,
            tuple(enc.pending_action_list), tuple(enc.finished_action_list),
            tuple(enc._atomic_interval_history), rng.state,
            set(atomic_publication._COMMITTED_RECEIPTS), throw.resolution,
            thrower.get_position(),
        )
        self.assertEqual(after, before)

        enc.recover_transactional_progression(caught.exception.recovery_token)
        enc.step(1, velocities={runner.id: (1.25, 0.0, 0.0)})
        committed = enc._atomic_interval_history[-1]
        self.assertEqual(committed.boundary, 5)
        self.assertEqual(committed.action_ids, (run.id,))
        self.assertEqual(run.resolution.outcome, 'success')
        self.assertEqual(runner.get_position(), CartesianPosition(101.25, 0.0, 0.0))
        self.assertEqual(enc.inspect_committed(5).target(projectile.id).position,
                         build_projection()[1].position_at(1.0))
        self.assertEqual(rng.state, before[14])

    def test_deterministic_repeat_and_throw_reservation_remains_exclusive(self):
        outputs = []
        for _ in range(2):
            world, enc, _, runner, projectile, rng, throw, run = build_concurrent_scene(seed=229)
            initial_rng = rng.state
            competing = ThrowAction(world, throw.actor_id, projectile.id, 1,
                heavy_load_reference_lb=100.0, elevation_degrees=45.0,
                id='throw-demo/competing-object-use')
            invalid = enc.validate_choice(enc.propose_choice((competing,)))
            self.assertFalse(invalid.valid)
            self.assertNotIn(competing.id, world.event_history)
            enc.step(4)
            enc.step(1, velocities={runner.id: (1.25, 0.0, 0.0)})
            enc.step(1)
            enc.step(1)
            self.assertEqual(rng.state, initial_rng)
            outputs.append((
                throw.resolution.outcome,
                run.resolution.outcome,
                tuple((boundary, enc.inspect_committed(boundary).target(projectile.id).position,
                       enc.inspect_committed(boundary).target(projectile.id).projectile_state.status)
                      for boundary in (4, 5, 6, 7)),
                runner.get_position(), runner.get_skill_experience('run'),
                tuple((receipt.boundary, receipt.action_ids, receipt.effect_ids)
                      for receipt in enc._atomic_interval_history[-4:]),
                rng.state,
            ))
        self.assertEqual(outputs[0], outputs[1])

    def test_ordinary_encounter_run_without_throw_remains_available(self):
        world = Universe('ordinary Run compatibility',
                         library=Library(config_dir=str(ROOT / 'src' / 'config')))
        definition = world.library.being_dictionary.get_object_definition('Human')
        runner = BeingInstance(definition, 'Ordinary Runner', id='ordinary/runner')
        runner.set_position(CartesianPosition(0.0, 0.0, 0.0))
        world.add_object(runner)
        encounter = Encounter(world, 10, 0, initiated=True, id='ordinary/no-throw')
        world.add_event(encounter)
        encounter.add_being(runner.id)
        action = RunAction(world, runner.id, 0, 1, 0.5, experience=2,
                           id='ordinary/run')
        encounter.schedule_action(action)
        encounter.step(1, velocities={runner.id: (1.0, 0.0, 0.0)})
        self.assertEqual(runner.get_position(), CartesianPosition(1.0, 0.0, 0.0))
        self.assertEqual(action.resolution.outcome, 'success')
        self.assertEqual(runner.get_skill_experience('run'), 2)
        self.assertFalse(encounter.__dict__.get('_projectile_flight_registry'))


if __name__ == '__main__':
    unittest.main()
