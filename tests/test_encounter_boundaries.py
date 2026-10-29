"""Increment 2 targets, plus explicit non-atomic legacy failure limitations."""
import json
import math
from pathlib import Path
import random
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src')]
from action import Action
from ai_duel import AgentDuel
from encounter import Encounter, BoundaryContext, BoundaryInvariantError
from event import Event
from library import Library
from melee_combat import MeleeStrike
from melee_defense import MeleeDefense
from spatial.state import CartesianPosition
from tactical_duel import TacticalDuel
from universe import Universe


class BoundaryProbe(Action):
    """Native timeline instrumentation, not a second combat implementation."""
    def __init__(self, encounter, actor, target, end=1, callback=None, start=None):
        super().__init__(encounter.universe, encounter.time if start is None else start,
                         None, 'inspect', actor.id, target.id, None)
        self.end_time = end
        self.calls = 0
        self.callback = callback

    def resolve(self, difficulty_class):
        self.calls += 1
        if self.callback is not None:
            self.callback()


class TestEncounterBoundaries(unittest.TestCase):
    def setUp(self):
        self.world = Universe('Boundaries', library=Library(config_dir=str(ROOT / 'src/config')))
        self.a = self.world.get_object_by_id(self.world.make_being('Human', 'A'))
        self.b = self.world.get_object_by_id(self.world.make_being('Human', 'B'))
        self.a.set_position(CartesianPosition(0, 0, 0))
        self.b.set_position(CartesianPosition(1.5, 0, 0))
        self.enc = Encounter(self.world, 10, 0, initiated=True)
        self.enc.add_being(self.a.id)
        self.enc.add_being(self.b.id)
        self.enc.mark_aware(self.a.id, self.b.id)
        self.enc.mark_aware(self.b.id, self.a.id)
        self.world.add_event(self.enc)

    def probe(self, end=1, callback=None, start=None):
        return BoundaryProbe(self.enc, self.a, self.b, end, callback, start)

    def unchanged_rejection(self, operation):
        world, rng = self.world.to_json(), random.getstate()
        with self.assertRaises(BoundaryInvariantError):
            operation()
        self.assertEqual(self.world.to_json(), world)
        self.assertEqual(random.getstate(), rng)

    def test_origin_and_first_action_boundary_are_distinct(self):
        origin = self.world.get_event_by_id('0')
        action = self.probe()
        self.enc.schedule_action(action)
        self.assertEqual(origin.start_time, 0)
        self.assertEqual(self.enc.last_processed_boundary, 0)
        self.assertEqual(self.enc.step(.75).completed_action_ids, ())
        self.assertEqual(self.enc.step(.25).completed_action_ids, (action.id,))
        self.assertEqual((self.enc.time, self.enc.last_processed_boundary), (1, 1))

    def test_empty_boundaries_processed_once_and_fragments_do_not_freeze(self):
        self.enc.step(.5)
        self.assertEqual(self.enc.fatigue_frame_history, [])
        self.assertIsNone(self.enc.last_fatigue_frame)
        self.enc.step(.5)
        self.enc.step(2.25)
        self.assertEqual([x['time'] for x in self.enc.fatigue_frame_history], [1, 2, 3])
        self.assertEqual((self.enc.time, self.enc.last_processed_boundary), (3.25, 3))
        self.unchanged_rejection(lambda: self.enc.resolve_actions(3))

    def test_exact_nextafter_and_fractional_nominal_deadlines_share_bucket(self):
        log, actions = [], []
        ends = [1.8, 1.2, 1, math.nextafter(1, math.inf), 2, math.nextafter(2, math.inf)]
        for index, end in enumerate(ends):
            action = self.probe(end, callback=lambda i=index: log.append((i, self.enc.time)))
            self.enc.schedule_action(action)
            actions.append(action)
        self.enc.step(3)
        self.assertEqual(log, [(2, 1), (0, 2), (1, 2), (3, 2), (4, 2), (5, 3)])
        self.assertEqual([a.end_time for a in actions], ends)

    def test_batch_order_is_priority_then_accepted_queue_not_fractional_timestamp(self):
        log = []
        first = self.probe(1.8, lambda: log.append('first'))
        second = self.probe(1.2, lambda: log.append('second'))
        priority = self.probe(1.9, lambda: log.append('priority'))
        priority.resolution_priority = -1
        for action in (first, second, priority):
            self.enc.schedule_action(action)
        self.enc.step(2)
        self.assertEqual(log, ['priority', 'first', 'second'])

    def test_long_constant_velocity_matches_sequential_boundary_samples(self):
        def scenario(long):
            world = Universe('Motion', library=self.world.library)
            actor = world.get_object_by_id(world.make_being('Human', 'Mover'))
            actor.set_position(CartesianPosition(0, 0, 0))
            enc = Encounter(world, 10, 0, initiated=True)
            enc.add_being(actor.id)
            samples = []
            for end in (1, 2, 3):
                enc.schedule_action(BoundaryProbe(enc, actor, actor, end,
                    lambda: samples.append((enc.time, actor.get_position().as_tuple()))))
            for duration in ([3] if long else [1, 1, 1]):
                enc.step(duration, velocities={actor.id: (.25, 2, -1)})
            return samples, enc.fatigue_frame_history, actor.get_position()
        long, short = scenario(True), scenario(False)
        self.assertEqual(long[0], short[0])
        self.assertEqual(long[2], short[2])
        self.assertEqual([(x['start'], x['time']) for x in long[1]], [(0, 1), (1, 2), (2, 3)])

    def test_fractional_fragments_preserve_movement_and_environment_cadence(self):
        log = []
        self.enc.update_environment = lambda: log.append((self.enc.time, self.a.get_position().x))
        for duration in (.25, .75, .125, .875, .25):
            self.enc.step(duration, velocities={self.a.id: (1, 0, 0)})
        self.assertEqual(log, [(1, 1), (2, 2)])
        self.assertEqual(self.a.get_position().x, 2.25)
        self.assertEqual(self.enc.last_processed_boundary, 2)

    def test_run_and_step_share_walker_and_ai_choices_precede_next_boundary(self):
        log = []
        for end in (1, 2):
            self.enc.schedule_action(self.probe(end, lambda: log.append(('action', self.enc.time))))
        with patch.object(self.enc, 'choose_fight_actions',
                          side_effect=lambda: log.append(('choice', self.enc.time))), \
             patch.object(self.enc, 'choose_movement', return_value={self.a.id: (1, 0, 0)}), \
             patch.object(self.enc, 'keep_going', side_effect=[True, False]), \
             patch.object(self.enc, '_advance', wraps=self.enc._advance) as advance:
            self.enc.run()
        self.assertEqual(advance.call_count, 2)
        self.assertEqual(log, [('choice', 0), ('action', 1), ('choice', 1), ('action', 2)])
        self.assertEqual(self.a.get_position().x, 2)
        with patch.object(self.enc, '_advance', wraps=self.enc._advance) as advance:
            self.enc.step()
        self.assertEqual(advance.call_count, 1)
        self.assertEqual(self.enc.last_processed_boundary, 3)

    def test_fractional_encounter_origin_does_not_invent_prior_movement(self):
        enc = Encounter(self.world, 10, .25, initiated=True)
        enc.add_being(self.a.id)
        enc.step(.75, velocities={self.a.id: (1, 0, 0)})
        self.assertEqual(self.a.get_position().x, .75)
        self.assertEqual(enc.fatigue_frame_history[0]['start'], .25)
        self.assertEqual(enc.last_processed_boundary, 1)

    def test_run_honors_fractional_end_without_skipping_or_dispatching_fragments(self):
        self.enc.end_time = 1.5
        with patch.object(self.enc, 'choose_fight_actions'), \
             patch.object(self.enc, 'keep_going', return_value=True):
            self.enc.run()
        self.assertEqual((self.enc.time, self.enc.last_processed_boundary), (1.5, 1))
        self.assertEqual([x['time'] for x in self.enc.fatigue_frame_history], [1])

    def test_run_rejects_corrupt_pending_before_ai_choices(self):
        self.enc.pending_action_list.append('missing')
        with patch.object(self.enc, 'choose_fight_actions') as choose:
            self.unchanged_rejection(self.enc.run)
        choose.assert_not_called()

    def test_run_legacy_stop_hook_uses_existing_being_fatigue_accessor(self):
        # No new stopping rule: retain the native comparison/return behavior.
        with patch.object(self.enc, 'choose_fight_actions'), patch('builtins.print'):
            self.enc.run()
        self.assertEqual((self.enc.time, self.enc.last_processed_boundary), (1, 1))

    def test_direct_dispatch_rejections_are_effect_and_rng_free(self):
        action = self.probe(callback=lambda: random.random())
        self.enc.schedule_action(action)
        for cutoff in (None, 0, -1, .5, 1, 20, math.nan, math.inf, True):
            with self.subTest(cutoff=cutoff):
                self.unchanged_rejection(lambda: self.enc.resolve_actions(cutoff))
        self.assertEqual(action.calls, 0)

    def test_forged_or_consumed_boundary_context_cannot_dispatch(self):
        self.unchanged_rejection(lambda: self.enc.resolve_actions(1,
            _context=BoundaryContext(1, 0)))
        contexts = []
        action = self.probe(callback=lambda: contexts.append(self.enc._boundary_context))
        self.enc.schedule_action(action)
        self.enc.step()
        self.unchanged_rejection(lambda: self.enc.resolve_actions(1, _context=contexts[0]))

    def test_reentrant_step_run_and_dispatch_refuse_before_new_effects(self):
        attempts = []
        def callback():
            for operation in (self.enc.step, self.enc.run,
                    lambda: self.enc.resolve_actions(1, _context=self.enc._boundary_context)):
                with self.assertRaises(BoundaryInvariantError):
                    operation()
                attempts.append(1)
        action = self.probe(callback=callback)
        self.enc.schedule_action(action)
        self.enc.step()
        self.assertEqual((len(attempts), action.calls), (3, 1))
        self.assertIsNone(self.enc.boundary_fault)

    def test_reentrant_run_choice_hook_cannot_start_another_walker(self):
        attempts = []
        def choice():
            with self.assertRaises(BoundaryInvariantError):
                self.enc.step()
            with self.assertRaises(BoundaryInvariantError):
                self.enc.run()
            attempts.append(self.enc.time)
        with patch.object(self.enc, 'choose_fight_actions', side_effect=choice), \
             patch.object(self.enc, 'keep_going', return_value=False):
            self.enc.run()
        self.assertEqual(attempts, [0])
        self.assertEqual(self.enc.last_processed_boundary, 1)

    def test_cursor_and_external_clock_tampering_reject_before_movement(self):
        for cursor in (-1, 1, True, 0.0):
            with self.subTest(cursor=cursor):
                self.enc.last_processed_boundary = cursor
                self.unchanged_rejection(lambda: self.enc.step(velocities={self.a.id: (1, 0, 0)}))
        self.enc.last_processed_boundary = 0
        self.enc.time = .5
        self.unchanged_rejection(self.enc.step)

    def test_null_nonfinite_or_invalid_future_deadline_preflight_is_pure(self):
        action = self.probe(2)
        self.enc.schedule_action(action)
        for value in (None, math.nan, math.inf, 0, .5):
            action.end_time = value
            with self.subTest(value=value):
                self.unchanged_rejection(lambda: self.enc.step(velocities={self.a.id: (1, 0, 0)}))
        self.assertEqual(self.a.get_position().x, 0)
        self.assertIsNone(self.enc.boundary_fault)

    def test_missing_and_duplicate_pending_references_preflight_is_pure(self):
        action = self.probe()
        self.enc.schedule_action(action)
        self.enc.pending_action_list.append(action.id)
        self.unchanged_rejection(self.enc.step)
        self.enc.pending_action_list.pop()
        self.enc.pending_action_list.append('missing')
        self.unchanged_rejection(self.enc.step)
        self.assertEqual(action.calls, 0)

    def test_overdue_action_is_not_executed_late(self):
        self.enc.step()
        stale = self.probe(1, start=0)
        stale.parent_event_id = self.enc.id
        self.world.event_history[stale.id] = stale  # Deliberate corrupt-state injection, not a scheduling API.
        self.enc.pending_action_list.append(stale.id)
        self.unchanged_rejection(self.enc.step)
        self.assertEqual(stale.calls, 0)

    def test_corrupt_registry_target_is_distinct_from_unavailable_instrument(self):
        action = self.probe()
        self.enc.schedule_action(action)
        self.world.object_registry.object_instances.pop(self.b.id)
        self.unchanged_rejection(self.enc.step)
        self.assertEqual(action.calls, 0)

    def test_preflight_rejection_can_be_corrected_without_fault_or_rng_use(self):
        action = self.probe()
        self.enc.schedule_action(action)
        action.end_time = None
        self.unchanged_rejection(self.enc.step)
        action.end_time = 1
        self.assertEqual(self.enc.step().completed_action_ids, (action.id,))
        self.assertIsNone(self.enc.boundary_fault)

    def test_active_and_completed_boundary_scheduling_reject_without_publication(self):
        rejected = []
        def callback():
            candidate = self.probe(1, start=0)
            parent = candidate.parent_event_id
            with self.assertRaises(BoundaryInvariantError):
                self.enc.schedule_action(candidate)
            self.assertEqual(candidate.parent_event_id, parent)
            self.assertIsNone(self.world.get_event_by_id(candidate.id))
            rejected.append(candidate.id)
        action = self.probe(callback=callback)
        self.enc.schedule_action(action)
        self.enc.step()
        candidate = self.probe(1, start=0)
        self.unchanged_rejection(lambda: self.enc.schedule_action(candidate))
        self.assertEqual(len(rejected), 1)

    def test_completion_can_schedule_a_future_boundary_but_not_the_active_one(self):
        future = self.probe(2, start=1)
        action = self.probe()
        action.on_completed = lambda enc: enc.schedule_action(future)
        self.enc.schedule_action(action)
        self.assertEqual(self.enc.step(2).completed_action_ids, (action.id, future.id))

    def test_existing_actor_occupancy_lasts_until_effective_resolution(self):
        action = self.probe(1.2)
        self.enc.schedule_action(action)
        self.enc.step(1.5)
        self.assertTrue(self.enc.is_being_occupied(self.a.id))
        self.enc.step(.5)
        self.assertFalse(self.enc.is_being_occupied(self.a.id))

    def test_fractional_strikes_share_one_eligibility_group(self):
        weapons = []
        for being in (self.a, self.b):
            weapon = self.world.make_weapon_for_being(being.id, 'Dagger', 'Knife')
            self.world.arm_being(being.id, weapon, 'right hand')
            weapons.append(weapon)
        attacks = [MeleeStrike(self.enc, self.a.id, self.b.id, weapons[0], motion='thrust', reach=2),
                   MeleeStrike(self.enc, self.b.id, self.a.id, weapons[1], motion='thrust', reach=2)]
        for action, end in zip(attacks, (1.2, 1.8)):
            action.end_time = end
            self.enc.schedule_action(action)
        self.b.set_hit_points(1)
        with patch('action.roll_dice', side_effect=[17, 2, 17, 2]):
            self.enc.step(2)
        self.assertEqual([a.combat_result.outcome for a in attacks], ['normal', 'normal'])
        self.assertEqual(self.b.get_hit_points(), 0)  # Legacy damage mechanics retained.

    def test_designated_defense_keeps_nominal_time_and_precedence(self):
        weapon = self.world.make_weapon_for_being(self.a.id, 'Dagger', 'Knife')
        self.world.arm_being(self.a.id, weapon, 'right hand')
        attack = MeleeStrike(self.enc, self.a.id, self.b.id, weapon, motion='thrust', reach=2)
        attack.end_time = 3.2
        self.enc.schedule_action(attack)
        defense = MeleeDefense(self.enc, self.b.id, self.a.id, kind='dodge', target_action_id=attack.id)
        self.enc.schedule_action(defense)
        self.assertEqual((defense.ready_at, defense.end_time), (2, 3.2))
        self.assertEqual(self.enc.step(3.2).completed_action_ids, ())
        with patch('melee_defense.roll_dice', side_effect=[20, 1]):
            result = self.enc.step(.8)
        self.assertEqual(result.completed_action_ids, (defense.id, attack.id))
        self.assertEqual(attack.end_time, 3.2)
        self.assertEqual(attack.defended_by, defense.id)

    def test_qb_frame_is_per_boundary_and_remains_write_free(self):
        views = []
        def first():
            views.append(self.enc.fatigue_view(self.a.id).q)
            self.a.set_physical_fatigue(.5, .6)  # Test-only legacy evaluator write.
        one = self.probe(1, first)
        two = self.probe(2, lambda: views.append(self.enc.fatigue_view(self.a.id).q))
        self.enc.schedule_action(one)
        self.enc.schedule_action(two)
        self.enc.step(2.5)
        self.assertEqual(views, [1, .5])
        self.assertEqual([x['views'][self.a.id]['q'] for x in self.enc.fatigue_frame_history], [1, .5])
        self.assertEqual(self.a.get_physical_fatigue().q, .5)
        self.assertIsNone(self.enc._active_fatigue_frame)

    def test_later_boundary_fault_retains_earlier_progress_and_latches_no_retry(self):
        rng = random.getstate()
        self.addCleanup(random.setstate, rng)
        first = self.probe(1, lambda: self.b.set_hit_points(7))
        def fail():
            self.b.set_hit_points(3)
            random.random()
            raise RuntimeError('legacy evaluation failure')
        second = self.probe(2, fail)
        self.enc.schedule_action(first)
        self.enc.schedule_action(second)
        with self.assertRaisesRegex(RuntimeError, 'legacy evaluation failure'):
            self.enc.step(3, velocities={self.a.id: (1, 0, 0)})
        self.assertEqual((self.enc.time, self.enc.last_processed_boundary, self.a.get_position().x), (2, 1, 2))
        self.assertEqual(self.b.get_hit_points(), 3)
        self.assertEqual(self.enc.finished_action_list, [first.id])
        self.assertEqual(self.enc.pending_action_list, [second.id])
        self.assertEqual([x['time'] for x in self.enc.fatigue_frame_history], [1])
        self.assertEqual(self.enc.boundary_fault['boundary'], 2)
        self.assertNotEqual(random.getstate(), rng)
        for operation in (self.enc.step, self.enc.run):
            self.unchanged_rejection(operation)
        self.assertIsNone(self.enc._boundary_context)
        self.assertIsNone(self.enc._active_fatigue_frame)

    def test_environment_failure_does_not_claim_processed_boundary(self):
        action = self.probe()
        self.enc.schedule_action(action)
        with patch.object(self.enc, 'update_environment', side_effect=RuntimeError('environment failed')):
            with self.assertRaisesRegex(RuntimeError, 'environment failed'):
                self.enc.step()
        self.assertIn(action.id, self.enc.finished_action_list)
        self.assertEqual(self.enc.last_processed_boundary, 0)
        self.assertIsNotNone(self.enc.boundary_fault)

    def test_failed_batch_clears_unprocessed_melee_eligibility(self):
        weapon = self.world.make_weapon_for_being(self.a.id, 'Dagger', 'Knife')
        self.world.arm_being(self.a.id, weapon, 'right hand')
        attack = MeleeStrike(self.enc, self.a.id, self.b.id, weapon, motion='thrust', reach=2)
        def fail():
            raise RuntimeError('first evaluator failed')
        failure = self.probe(4, fail)
        failure.resolution_priority = -2
        self.enc.schedule_action(attack)
        self.enc.schedule_action(failure)
        with self.assertRaisesRegex(RuntimeError, 'first evaluator failed'):
            self.enc.step(4)
        self.assertIsNone(attack._simultaneous_eligibility)
        self.assertIsNone(attack.combat_result)

    def test_cursor_serialization_is_diagnostic_and_hides_dispatch_tokens(self):
        self.enc.step(1.5)
        state = json.loads(self.enc.to_json())['boundary_state']
        self.assertEqual((state['time'], state['last_processed'], state['active']), (1.5, 1, None))
        saved = json.loads(self.world.to_json())['event_history'][self.enc.id]
        self.assertEqual(saved['last_processed_boundary'], 1)
        self.assertNotIn('_boundary_context', saved)
        self.assertNotIn('_dispatching', saved)
        state['last_processed'] = 999
        self.assertEqual(self.enc.last_processed_boundary, 1)

    def test_fragment_active_and_faulted_saves_do_not_truncate_files(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'checkpoint.json'
            path.write_text('preserve')
            self.enc.step(.5)
            with self.assertRaises(BoundaryInvariantError):
                self.world.save_to_file(path)
            self.assertEqual(path.read_text(), 'preserve')
            action = self.probe(1.5, start=.5)
            def callback():
                with self.assertRaises(BoundaryInvariantError):
                    self.world.save_to_file(path)
                raise RuntimeError('fault')
            action.callback = callback
            self.enc.schedule_action(action)
            with self.assertRaises(RuntimeError):
                self.enc.step(1.5)
            with self.assertRaises(BoundaryInvariantError):
                self.world.save_to_file(path)
            self.assertEqual(path.read_text(), 'preserve')

    def test_encounter_restore_is_explicitly_unsupported_and_nonmutating(self):
        self.enc.step()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'checkpoint.json'
            self.world.save_to_file(path)
            payload = json.loads(path.read_text())
            payload['event_history'][self.enc.id]['last_processed_boundary'] = 99
            path.write_text(json.dumps(payload))
            before, rng = self.world.to_json(), random.getstate()
            with self.assertRaisesRegex(ValueError, 'checkpoint restoration is unsupported'):
                self.world.load_from_file(path)
            self.assertEqual(self.world.to_json(), before)
            self.assertEqual(random.getstate(), rng)
        with self.assertRaises(BoundaryInvariantError):
            Encounter(self.world, 10, 0, time=1)

    def test_tactical_and_ai_facades_preflight_before_strategy_or_policy(self):
        game = TacticalDuel(17)
        game.encounter.last_processed_boundary = 1
        before, rng = game.world.to_json(), random.getstate()
        with self.assertRaises(BoundaryInvariantError):
            game.choose('guard')
        self.assertEqual(game.world.to_json(), before)
        self.assertEqual(random.getstate(), rng)
        policy = Mock()
        ai = AgentDuel(17, policy=policy)
        ai.encounter.last_processed_boundary = 1
        with self.assertRaises(BoundaryInvariantError):
            ai.choose('wait')
        policy.decide.assert_not_called()

    def test_boundary_beyond_encounter_end_is_rejected_during_preparation(self):
        self.enc.end_time = 1.5
        action = self.probe(1.2)
        with self.assertRaisesRegex(ValueError, 'resolution boundary'):
            self.enc.schedule_action(action)
        self.assertIsNone(self.world.get_event_by_id(action.id))
        self.assertIsNone(action.parent_event_id)


if __name__ == '__main__':
    unittest.main()
