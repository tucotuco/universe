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
from being import BeingInstance
from encounter import Encounter
from interval_staging import StaleInterval, validate_interval_candidate
from native_throw_arena import (build_native_scene, build_projection,
                                PROJECTILE_WEIGHT_LB, RELEASE_BOUNDARY)
from spatial.state import CartesianPosition
from throwing import ProjectileFlight, ProjectileBoundaryState


class NativeThrowTests(unittest.TestCase):
    def test_inspection_accepts_committed_weapon_projectile_release_transition(self):
        world, enc, actor, _projectile, _rng, original = build_native_scene(seed=816)
        enc._choice_book.undo(enc._choice_book.for_action(original.id).id)
        definition = world.library.being_dictionary.get_object_definition('Human')
        target = BeingInstance(definition, 'Helpless Target', id='throw-demo/fatal-target')
        target.current.hit_points = 0
        target.set_position(CartesianPosition(0.5, 0.0, 0.0))
        world.add_object(target);enc.add_being(target.id)
        enc.mark_aware(actor.id, target.id)
        weapon_id = world.make_weapon_for_being(actor.id, 'Dagger', 'Coup Dagger')
        actor.set_body_part_holds_object('right hand', weapon_id)
        enc.add_object(weapon_id)
        action = ThrowAction(world, actor.id, weapon_id, enc.time,
            heavy_load_reference_lb=100.0, elevation_degrees=45,
            target_id=target.id, coup_de_grace=True,
            id='throw-demo/fatal-release-inspection')
        enc.schedule_choice((action,))
        enc.step(RELEASE_BOUNDARY)

        committed = enc.inspect_committed(RELEASE_BOUNDARY)
        self.assertEqual(committed.action(action.id).facts.outcome, 'released')
        projectile_state = committed.target(weapon_id).projectile_state
        self.assertEqual(projectile_state.status, 'in_flight')
        self.assertEqual(projectile_state.source_action_id, action.id)
        self.assertEqual(projectile_state.source_effect_identity[2], action.id)

    def test_held_four_second_dagger_throw_uses_native_range_damage_profile(self):
        world, enc, actor, _projectile, rng, original = build_native_scene()
        book = enc.__dict__['_choice_book']
        book.undo(book.for_action(original.id).id)
        target_definition = world.library.being_dictionary.get_object_definition('Human')
        target = BeingInstance(target_definition, 'Target', id='throw-demo/dagger-target')
        target.set_position(CartesianPosition(8.0, 0.0, 0.0))
        world.add_object(target);enc.add_being(target.id)
        weapon_id = world.make_weapon_for_being(actor.id, 'Dagger', 'Thrown Dagger')
        enc.add_object(weapon_id)
        actor.set_body_part_holds_object('right hand', weapon_id)
        dagger = world.get_object_by_id(weapon_id)
        action = ThrowAction(world, actor.id, weapon_id, enc.time,
            heavy_load_reference_lb=100.0, elevation_degrees=45,
            target_id=target.id, id='throw-demo/dagger-action')
        enc.schedule_choice((action,));enc.step(4)
        self.assertEqual(action.resolution.outcome, 'released')
        self.assertNotIn(weapon_id, actor.weapons)
        self.assertNotIn(weapon_id, actor.possessions)
        self.assertNotIn(weapon_id, actor.current.body_parts.values())
        self.assertEqual(dagger.__dict__['_projectile_flight'].damage_potential,
                         dagger.current.attacks['R']['d'])
        initial_target_hp = target.current.hit_points
        for _ in range(4):
            if dagger.__dict__['_projectile_flight'].impact_outcome is not None:
                break
            enc.step(1)
        flight = dagger.__dict__['_projectile_flight']
        self.assertIn(flight.impact_outcome, ('hit','miss','fatal','target_moved'))
        if flight.impact_outcome == 'hit':
            self.assertLess(target.current.hit_points, initial_target_hp)

    def test_thrown_coup_de_grace_auto_criticals_helpless_target_with_fortitude_consequence(self):
        world, enc, actor, _projectile, rng, original = build_native_scene(seed=816)
        book = enc.__dict__['_choice_book']
        book.undo(book.for_action(original.id).id)
        definition = world.library.being_dictionary.get_object_definition('Human')
        target = BeingInstance(definition, 'Helpless Target', id='throw-demo/helpless-target')
        target.set_position(CartesianPosition(0.5, 0.0, 0.0))
        target.current.hit_points = 0
        world.add_object(target);enc.add_being(target.id)
        enc.mark_aware(actor.id, target.id)
        weapon_id = world.make_weapon_for_being(actor.id, 'Dagger', 'Coup Dagger')
        actor.set_body_part_holds_object('right hand', weapon_id)
        enc.add_object(weapon_id)
        weapon = world.get_object_by_id(weapon_id)
        target.set_position(CartesianPosition(2.0, 0.0, 0.0))
        out_of_range = ThrowAction(world, actor.id, weapon_id, enc.time,
            heavy_load_reference_lb=100.0, elevation_degrees=45,
            target_id=target.id, coup_de_grace=True,
            id='throw-demo/ranged-coup-too-far')
        with self.assertRaisesRegex(ValueError, 'within one yard'):
            out_of_range.prepare_schedule(enc)
        target.set_position(CartesianPosition(0.5, 0.0, 0.0))
        action = ThrowAction(world, actor.id, weapon_id, enc.time,
            heavy_load_reference_lb=100.0, elevation_degrees=45,
            target_id=target.id, coup_de_grace=True,
            id='throw-demo/ranged-coup')
        enc.schedule_choice((action,))
        enc.step(4)
        flight = weapon.__dict__['_projectile_flight']
        self.assertTrue(flight.coup_de_grace)
        self.assertLessEqual(math.hypot(actor.get_position().x-target.get_position().x,
                                        actor.get_position().y-target.get_position().y), 0.9144)
        for _ in range(4):
            if weapon.__dict__['_projectile_flight'].impact_outcome is not None:
                break
            enc.step(1)
        flight = weapon.__dict__['_projectile_flight']
        self.assertIn(flight.impact_outcome, ('hit', 'fatal'))
        self.assertLess(target.current.hit_points, 0)
        effects = atomic_publication.target_effects_from(target, action.id)
        critical_damage = [row.effect.amount for row in effects
            if row.effect.__class__.__name__ == 'DamageEffect'
            and row.effect.target_id == target.id
            and row.effect.component == 'critical_bypass']
        self.assertEqual(len(critical_damage), 1)

    def test_thrown_weapon_hit_applies_common_snapshot_shield_and_armor_effects(self):
        world, enc, actor, _projectile, rng, original = build_native_scene(seed=116)
        book = enc.__dict__['_choice_book']
        book.undo(book.for_action(original.id).id)
        definition = world.library.being_dictionary.get_object_definition('Human')
        target = BeingInstance(definition, 'Armored Target', id='throw-demo/armored-target')
        target.set_position(CartesianPosition(8.0, 0.0, 0.0))
        world.add_object(target);enc.add_being(target.id)
        armor_id = world.make_armor_for_being(target.id, 'Leather armor', 'Target Armor')
        shield_id = world.make_weapon_for_being(target.id, 'Small shield', 'Target Shield')
        world.arm_being(target.id, shield_id, 'shield hand')
        enc.add_object(armor_id);enc.add_object(shield_id)
        dagger_id = world.make_weapon_for_being(actor.id, 'Dagger', 'Thrown Dagger')
        actor.set_body_part_holds_object('right hand', dagger_id)
        enc.add_object(dagger_id)
        action = ThrowAction(world, actor.id, dagger_id, enc.time,
            heavy_load_reference_lb=100.0, elevation_degrees=45,
            target_id=target.id, id='throw-demo/protected-hit')
        enc.schedule_choice((action,))
        rng.state = random.Random(116).getstate()
        enc.step(4)
        for _ in range(4):
            if world.get_object_by_id(dagger_id).__dict__['_projectile_flight'].impact_outcome is not None:
                break
            enc.step(1)
        flight = world.get_object_by_id(dagger_id).__dict__['_projectile_flight']
        self.assertEqual(flight.impact_outcome, 'hit')
        shield_effects = atomic_publication.target_effects_from(
            world.get_object_by_id(shield_id), action.id)
        armor_effects = atomic_publication.target_effects_from(
            world.get_object_by_id(armor_id), action.id)
        shield_protection = [row.effect for row in shield_effects
            if row.effect.__class__.__name__ == 'ProtectionEffect'
            and row.effect.layer == 'shield']
        self.assertEqual(len(shield_protection), 1)
        protection = shield_protection[0]
        self.assertTrue(protection.intercepted)
        shield = world.get_object_by_id(shield_id)
        shield_size = int(shield.get_weapon_size())
        self.assertEqual(protection.passed,
                         protection.incoming - shield_size)
        self.assertTrue(any(row.effect.__class__.__name__ == 'ProtectionEffect'
            and row.effect.layer == 'armor' for row in armor_effects))
        durability = [row.effect.amount for row in shield_effects
            if row.effect.__class__.__name__ == 'DamageEffect'
            and row.effect.component == 'shield']
        self.assertEqual((protection.incoming, protection.passed, durability),
                         (3, 1, [1]))
        armor_protection = next(row.effect for row in armor_effects
            if row.effect.__class__.__name__ == 'ProtectionEffect'
            and row.effect.layer == 'armor')
        self.assertEqual((armor_protection.incoming, armor_protection.passed), (1, 0))
        self.assertEqual(durability,
            [max(0, protection.incoming - shield_size)])

    def test_targeted_throw_aims_at_explicit_being_point_without_body_geometry(self):
        world, enc, actor, projectile, _rng, original = build_native_scene()
        book = object.__getattribute__(enc, '__dict__')['_choice_book']
        book.undo(book.for_action(original.id).id)
        definition = world.library.being_dictionary.get_object_definition('Human')
        target = BeingInstance(definition, 'Target', id='throw-demo/target')
        target.set_position(CartesianPosition(8.0, 0.0, 0.0))
        self.assertIsNone(target.geometry)
        world.add_object(target)
        enc.add_being(target.id)
        action = ThrowAction(world, actor.id, projectile.id, enc.time,
            heavy_load_reference_lb=100.0,
            elevation_degrees=45, target_id=target.id,
            landing_elevation_m=0.0, id='throw-demo/targeted-action')
        enc.schedule_choice((action,))
        enc.step(RELEASE_BOUNDARY)
        flight = projectile.__dict__['_projectile_flight']
        self.assertEqual(flight.target_id, target.id)
        self.assertAlmostEqual(flight.landing_position.x, target.get_position().x)
        self.assertAlmostEqual(flight.landing_position.y, target.get_position().y)
        self.assertEqual(flight.landing_position.z, target.get_position().z)
        self.assertEqual(action.resolution.outcome, 'released')

    def test_target_movement_before_arrival_prevents_a_retroactive_attack_roll(self):
        world, enc, actor, projectile, rng, original = build_native_scene()
        book = object.__getattribute__(enc, '__dict__')['_choice_book']
        book.undo(book.for_action(original.id).id)
        definition = world.library.being_dictionary.get_object_definition('Human')
        target = BeingInstance(definition, 'Target', id='throw-demo/moving-target')
        target.set_position(CartesianPosition(8.0, 0.0, 0.0))
        world.add_object(target)
        enc.add_being(target.id)
        action = ThrowAction(world, actor.id, projectile.id, enc.time,
            heavy_load_reference_lb=100.0, elevation_degrees=45,
            target_id=target.id, id='throw-demo/moving-target-action')
        enc.schedule_choice((action,))
        enc.step(RELEASE_BOUNDARY)
        flight = projectile.__dict__['_projectile_flight']
        target.set_position(CartesianPosition(9.0, 0.0, 0.0))
        target_hp = target.current.hit_points
        rng_before = rng.state
        enc.step(4)
        resolved = projectile.__dict__['_projectile_flight']
        state = projectile.__dict__['_atomic_projectile_history'][-1]
        self.assertEqual(resolved.impact_outcome, 'target_moved')
        self.assertEqual(resolved.status, 'landed')
        self.assertEqual(state.position, flight.landing_position)
        self.assertEqual(target.current.hit_points, target_hp)
        self.assertEqual(state.impact_damage, 0)
        self.assertEqual(rng.state, rng_before)

    def test_simultaneous_targeted_arrivals_are_order_independent_and_stack_damage(self):
        results = []
        for reverse in (False, True):
            world, enc, actor, _initial_projectile, rng, original = build_native_scene(seed=422)
            book = object.__getattribute__(enc, '__dict__')['_choice_book']
            book.undo(book.for_action(original.id).id)
            definition = world.library.being_dictionary.get_object_definition('Human')
            target = BeingInstance(definition, 'Target', id='throw-demo/shared-target')
            target.set_position(CartesianPosition(8.0, 0.0, 0.0))
            second_actor = BeingInstance(definition, 'Second Thrower',
                id='throw-demo/second-thrower')
            second_actor.set_position(CartesianPosition(16.0, 0.0, 0.0))
            world.add_object(target);world.add_object(second_actor)
            enc.add_being(target.id);enc.add_being(second_actor.id)
            first_id = world.make_object_for_being(actor.id, 'Rock', 'First Rock')
            second_id = world.make_object_for_being(second_actor.id, 'Rock', 'Second Rock')
            enc.add_object(first_id);enc.add_object(second_id)
            first = ThrowAction(world, actor.id, first_id, enc.time,
                heavy_load_reference_lb=100.0, elevation_degrees=45,
                target_id=target.id, id='throw-demo/first')
            second = ThrowAction(world, second_actor.id, second_id, enc.time,
                heavy_load_reference_lb=100.0, elevation_degrees=45,
                target_id=target.id, id='throw-demo/second')
            actions = (second, first) if reverse else (first, second)
            enc.schedule_choice(actions)
            # Give the first impact a natural 20 in both declaration orders.
            # This exercises a real hit while still leaving the second
            # projectile's result to common-snapshot simultaneous resolution.
            rng.state = random.Random(116).getstate()
            enc.step(4)
            hp_before_impact = target.current.hit_points
            enc.step(4)
            flights = [world.get_object_by_id(key).__dict__['_projectile_flight']
                       for key in (first_id, second_id)]
            damages = [world.get_object_by_id(key).__dict__[
                '_atomic_projectile_history'][-1].impact_damage
                for key in (first_id, second_id)]
            self.assertTrue(all(flight.impact_outcome in ('hit', 'miss', 'fatal')
                                for flight in flights))
            self.assertTrue(any(flight.impact_outcome == 'hit' for flight in flights))
            self.assertEqual(hp_before_impact-target.current.hit_points, sum(damages))
            results.append((tuple(flight.impact_outcome for flight in flights),
                tuple(damages), target.current.hit_points, rng.state))
        self.assertEqual(results[0], results[1])

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
        # Keep the original native position object so restoring it doesn't
        # create a second identity change in the interval read fence.
        before=projectile.spatial_state.position
        projectile.spatial_state.position=CartesianPosition(before.x+0.25,before.y,before.z)
        with self.assertRaises(StaleInterval):
            validate_interval_candidate(enc,candidate,rng_owner=rng)
        projectile.spatial_state.position=before
        # A candidate stays stale once an authoritative dependency was
        # replaced, even if an equal position is later restored.
        with self.assertRaises(StaleInterval):
            validate_interval_candidate(enc,candidate,rng_owner=rng)


if __name__ == '__main__':
    unittest.main()
