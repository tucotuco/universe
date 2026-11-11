"""Assignment 03: LEGACY-CURRENT-BEHAVIOR, not adopted simulation rules.

These tests expose migration points. Zero clamps, early fractional dispatch,
and sequential leaks are intentionally superseded by Class A T5/F2/H2 v2.
Probe Actions record native dispatch behavior; they implement no combat model.
Assignment 04 supersedes only scheduling defects below; resolution and damage
characterizations remain pending their separately authorized increments.
"""
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from action import Action
from activities import RunAction, SpotAction
from encounter import Encounter, BoundaryInvariantError
from event import Event
from experience import ActionResolution, SkillExercise
from group_observation import ObserveGroupAction
from history_conversation import AskAboutPastAction
from library import Library
from melee_combat import MeleeStrike
from melee_defense import MeleeDefense
from spatial.state import CartesianPosition
from universe import Universe


class ProbeAction(Action):
    def __init__(self, encounter, actor_id, target_id, *, start=0, end=1,
                 instrument=None, resolve=None, schedule=None, completed=None):
        super().__init__(encounter.universe, start, None, 'inspect', actor_id,
                         target_id, instrument)
        self.end_time = end
        self.calls = 0
        self.resolve_callback = resolve
        self.schedule_callback = schedule
        if schedule is not None:
            self.on_schedule = lambda encounter: schedule(self, encounter)
        self.completed_callback = completed

    def resolve(self, difficulty_class):
        self.calls += 1
        if self.resolve_callback:
            return self.resolve_callback()

    def on_completed(self, encounter):
        if self.completed_callback:
            self.completed_callback(encounter)


class LegacyEncounterFixture(unittest.TestCase):
    def setUp(self):
        self.world = Universe('Legacy characterization',
                             library=Library(config_dir=str(ROOT / 'src/config')))
        self.a = self.world.get_object_by_id(self.world.make_being('Human', 'A'))
        self.b = self.world.get_object_by_id(self.world.make_being('Human', 'B'))
        self.a.set_position(CartesianPosition(0, 0, 0))
        self.b.set_position(CartesianPosition(1.5, 0, 0))
        self.blade = self.world.make_weapon_for_being(self.a.id, 'Dagger', 'Knife')
        self.world.arm_being(self.a.id, self.blade, 'right hand')
        self.enc = Encounter(self.world, 10, 0)
        self.enc.add_being(self.a.id)
        self.enc.add_being(self.b.id)
        self.enc.mark_aware(self.a.id, self.b.id)
        self.enc.mark_aware(self.b.id, self.a.id)
        self.enc.initiated = True

    def probe(self, **kwargs):
        return ProbeAction(self.enc, self.a.id, self.b.id, **kwargs)

    def strike(self, end=2):
        action = MeleeStrike(self.enc, self.a.id, self.b.id, self.blade,
                             motion='thrust', reach=2)
        action.end_time = end
        return action


class TestLegacyTimeline(LegacyEncounterFixture):
    def test_increment1_registered_zero_duration_action_is_rejected(self):
        action = self.probe(end=0)
        with self.assertRaisesRegex(ValueError, 'at least one second'):
            self.enc.schedule_action(action)
        self.assertIsNone(self.world.get_event_by_id(action.id))
        self.assertEqual(action.calls, 0)


    def test_legacy_schedule_duration_matrix(self):
        for duration, valid in [(-1, False), (0, False), (.25, False),
                                (1, True), (1.25, True), (2, True),
                                (math.nan, False), (math.inf, False),
                                (-math.inf, False)]:
            with self.subTest(duration=duration):
                action = self.probe(end=duration)
                if valid:
                    self.enc.schedule_action(action)
                    self.assertIn(action.id, self.enc.pending_action_list)
                else:
                    with self.assertRaises(ValueError):
                        self.enc.schedule_action(action)
                    self.assertIsNone(self.world.get_event_by_id(action.id))

    def test_legacy_builtin_duration_constructors_allow_positive_subsecond(self):
        factories = [
            lambda d: RunAction(self.world, self.a.id, 0, d, minimum_distance=1),
            lambda d: ObserveGroupAction(self.world, self.a.id, self.b.id, 0,
                duration=d, observation={'coarse_range_m': 20, 'detailed_range_m': 10}),
            lambda d: AskAboutPastAction(self.world, self.a.id, self.b.id, 0,
                duration=d, episode_time=0, topic='test', generate=lambda h, v: ()),
        ]
        for factory in factories:
            for duration in [-1, 0, .25, 1, 1.25, math.nan, math.inf]:
                with self.subTest(factory=factory, duration=duration):
                    if math.isfinite(duration) and duration > 0:
                        self.assertEqual(factory(duration).end_time, duration)
                    else:
                        with self.assertRaises(ValueError):
                            factory(duration)

    def test_deliberate_spot_duration_is_exactly_six_seconds(self):
        self.assertEqual(SpotAction(self.world, self.a.id, self.b.id, 0).end_time, 6)
        for duration in (-1, 0, .25, 1, 1.25, math.nan, math.inf):
            with self.subTest(duration=duration), self.assertRaises(ValueError):
                SpotAction(self.world, self.a.id, self.b.id, 0, duration=duration)

    def test_legacy_base_action_ignores_supplied_end_and_defaults_to_one_second(self):
        action = Action(self.world, 0, 0, 'inspect', self.a.id, self.b.id, None)
        self.assertEqual(action.end_time, 1)

    def test_legacy_defense_constructor_placeholder_finalizes_on_schedule(self):
        attack = MeleeStrike(self.enc, self.a.id, self.b.id, self.blade,
                             motion='thrust', reach=2)
        self.enc.schedule_action(attack)
        defense = MeleeDefense(self.enc, self.b.id, self.a.id, kind='dodge',
                               target_action_id=attack.id)
        self.assertEqual((defense.start_time, defense.end_time), (0, 0))
        self.enc.schedule_action(defense)
        self.assertEqual(defense.ready_at, 2)
        self.assertEqual(defense.end_time, attack.end_time)
        self.assertGreaterEqual(defense.end_time - defense.start_time, 1)

    def test_increment1_opaque_deadline_hook_is_rejected_without_invocation(self):
        action = self.probe(schedule=lambda a, e: setattr(a, 'end_time', 0))
        with self.assertRaises(TypeError):
            self.enc.schedule_action(action)
        self.assertEqual(action.end_time, 1)
        self.assertIsNone(self.world.get_event_by_id(action.id))


    def test_increment2_fractional_deadline_waits_for_integer_boundary(self):
        action = self.probe(end=1.2)
        self.enc.schedule_action(action)
        self.assertEqual(self.enc.step(1.2).completed_action_ids, ())
        self.assertEqual(self.enc.time, 1.2)
        self.assertEqual(self.enc.step(.8).completed_action_ids, (action.id,))
        self.assertEqual(action.end_time, 1.2)


    def test_legacy_fractional_deadlines_in_one_second_observe_sequential_effects(self):
        seen = []
        first = self.probe(end=1.2, resolve=lambda: self.b.set_hit_points(3))
        second = self.probe(end=1.8, resolve=lambda: seen.append(self.b.get_hit_points()))
        self.enc.schedule_action(first)
        self.enc.schedule_action(second)
        self.enc.step(2)
        self.assertEqual(seen, [3])

    def test_legacy_exact_and_immediately_after_integer_deadline(self):
        exact = self.probe(end=1)
        beyond = self.probe(end=math.nextafter(1, math.inf))
        self.enc.schedule_action(exact)
        self.enc.schedule_action(beyond)
        self.assertEqual(self.enc.step(1).completed_action_ids, (exact.id,))
        self.assertEqual(self.enc.step(.5).completed_action_ids, ())
        self.assertEqual(self.enc.step(.5).completed_action_ids, (beyond.id,))

    def test_increment2_long_step_samples_each_boundary(self):
        seen = []
        first = self.probe(end=1, resolve=lambda: seen.append(self.a.get_position().x))
        second = self.probe(end=2, resolve=lambda: seen.append(self.a.get_position().x))
        self.enc.schedule_action(first)
        self.enc.schedule_action(second)
        self.enc.step(2, velocities={self.a.id: (1, 0, 0)})
        self.assertEqual(seen, [1, 2])

    def test_legacy_successive_steps_sample_each_endpoint(self):
        seen = []
        for end in (1, 2):
            self.enc.schedule_action(self.probe(end=end,
                resolve=lambda: seen.append(self.a.get_position().x)))
        for _ in range(2):
            self.enc.step(1, velocities={self.a.id: (1, 0, 0)})
        self.assertEqual(seen, [1, 2])

    def test_increment2_direct_future_and_repeated_dispatch_are_rejected(self):
        action = self.probe(end=1)
        self.enc.schedule_action(action)
        for _ in range(2):
            with self.assertRaises(BoundaryInvariantError):
                self.enc.resolve_actions(as_of=20)
        self.assertEqual((self.enc.time, action.calls), (0, 0))


    def test_increment2_corrupt_pending_state_stops_before_dispatch(self):
        stale = self.probe(end=1)
        null = self.probe(end=2)
        self.enc.schedule_action(stale)
        self.enc.schedule_action(null)
        null.end_time = None
        self.enc.pending_action_list.append('missing-event')
        with self.assertRaises(BoundaryInvariantError):
            self.enc.step()
        self.assertEqual(stale.calls, 0)
        self.assertEqual(self.enc.time, 0)


    def test_increment2_nonfinite_dispatch_cutoff_is_rejected(self):
        action = self.probe()
        self.enc.schedule_action(action)
        for cutoff in (math.nan, math.inf):
            with self.assertRaises(BoundaryInvariantError):
                self.enc.resolve_actions(as_of=cutoff)
        self.assertEqual(action.calls, 0)


    def test_increment2_run_dispatches_first_at_one(self):
        one = self.probe(end=1)
        self.enc.schedule_action(one)
        with patch.object(self.enc, 'choose_fight_actions'), \
             patch.object(self.enc, 'keep_going', return_value=False):
            self.enc.run()
        self.assertEqual((one.calls, self.enc.time, self.enc.last_processed_boundary), (1, 1, 1))



class TestLegacyChoiceAndHooks(LegacyEncounterFixture):
    def test_increment3_same_weapon_overlap_is_rejected_across_completion_buckets(self):
        for windows in [((0, 2), (0, 3)), ((0, 1.1), (1.2, 2.3))]:
            with self.subTest(windows=windows):
                actions = [self.probe(start=s, end=e, instrument=self.blade) for s, e in windows]
                for action in actions:
                    action.event_type = 'thrust'  # Explicit native active use.
                self.enc.schedule_action(actions[0])
                with self.assertRaisesRegex(ValueError, 'actively reserved'):
                    self.enc.schedule_action(actions[1])
                self.assertEqual(self.enc.pending_action_list, [actions[0].id])
                self.assertIsNone(self.world.get_event_by_id(actions[1].id))
                self.enc.cancel_action(actions[0].id)


    def test_increment3_real_strikes_cannot_share_one_actively_held_weapon(self):
        first, second = self.strike(), self.strike()
        self.enc.schedule_action(first)
        with self.assertRaisesRegex(ValueError, 'actively reserved'):
            self.enc.schedule_action(second)
        self.assertEqual(self.enc.pending_action_list, [first.id])
        self.assertIsNone(self.world.get_event_by_id(second.id))


    def test_increment3_same_weapon_attack_and_parry_overlap_is_rejected(self):
        other_blade = self.world.make_weapon_for_being(self.b.id, 'Dagger', 'Other knife')
        self.world.arm_being(self.b.id, other_blade, 'right hand')
        own = self.strike(end=4)
        incoming = MeleeStrike(self.enc, self.b.id, self.a.id, other_blade, motion='thrust', reach=2)
        self.enc.schedule_action(own)
        self.enc.schedule_action(incoming)
        defense = MeleeDefense(self.enc, self.a.id, self.b.id, kind='parry', parry_motion='swing',
                               target_action_id=incoming.id, weapon_id=self.blade)
        with self.assertRaisesRegex(ValueError, 'actively reserved'):
            self.enc.schedule_action(defense)
        self.assertEqual(defense.end_time, 0)
        self.assertEqual(self.enc.pending_action_list, [own.id, incoming.id])


    def test_legacy_sequential_group_registration_leaves_first_when_second_fails(self):
        first, second = self.probe(), self.probe(end=-1)
        self.enc.schedule_action(first)
        with self.assertRaises(ValueError):
            self.enc.schedule_action(second)
        self.assertEqual(self.enc.pending_action_list, [first.id])
        self.assertIs(self.world.get_event_by_id(first.id), first)
        self.assertIsNone(self.world.get_event_by_id(second.id))

    def test_increment1_mutating_nested_hook_is_rejected_before_execution(self):
        nested = self.probe(end=2)
        def bad_hook(action, encounter):
            self.a.set_hit_points(4)
            encounter.schedule_action(nested)
            raise ValueError('hook failure')
        action = self.probe(schedule=bad_hook)
        before_hp = self.a.get_hit_points()
        with self.assertRaises(TypeError):
            self.enc.schedule_action(action)
        self.assertEqual(self.a.get_hit_points(), before_hp)
        self.assertIsNone(self.world.get_event_by_id(action.id))
        self.assertIsNone(self.world.get_event_by_id(nested.id))
        self.assertEqual(self.enc.pending_action_list, [])


    def test_increment1_schedule_hook_cannot_register_nested_action(self):
        nested = self.probe(end=1)
        outer = self.probe(schedule=lambda a, e: e.schedule_action(nested))
        with self.assertRaises(TypeError):
            self.enc.schedule_action(outer)
        self.assertEqual(self.enc.pending_action_list, [])
        self.assertIsNone(self.world.get_event_by_id(nested.id))


    def test_increment2_resolve_and_completion_cannot_register_active_boundary(self):
        errors = []
        def attempt():
            action = self.probe(end=1)
            try:
                self.enc.schedule_action(action)
            except BoundaryInvariantError:
                errors.append(action.id)
        outer = self.probe(resolve=attempt, completed=lambda e: attempt())
        self.enc.schedule_action(outer)
        self.assertEqual(self.enc.step().completed_action_ids, (outer.id,))
        self.assertEqual(len(errors), 2)
        self.assertTrue(all(self.world.get_event_by_id(i) is None for i in errors))


    def test_increment1_schedule_hook_refuses_even_during_resolution(self):
        nested = self.probe(end=1)
        proposed = self.probe(end=1, schedule=lambda a, e: e.schedule_action(nested))
        outer = self.probe(resolve=lambda: self.enc.schedule_action(proposed))
        self.enc.schedule_action(outer)
        with self.assertRaises(TypeError):
            self.enc.step()
        self.assertEqual(self.enc.pending_action_list, [outer.id])
        self.assertIsNone(self.world.get_event_by_id(nested.id))
        self.assertIsNone(self.world.get_event_by_id(proposed.id))


    def test_increment2_reentrant_dispatch_does_not_reexecute_action(self):
        action = self.probe()
        action.resolve_callback = lambda: self.enc.resolve_actions(1)
        self.enc.schedule_action(action)
        with self.assertRaises(BoundaryInvariantError):
            self.enc.step()
        self.assertEqual(action.calls, 1)
        self.assertEqual(self.enc.finished_action_list, [])
        self.assertIsNotNone(self.enc.boundary_fault)


    def test_increment1_cancellation_retains_native_start_metadata_and_registration(self):
        action = RunAction(self.world, self.a.id, 0, 1, minimum_distance=1)
        self.enc.schedule_action(action)
        position = action.start_position
        self.enc.cancel_action(action.id)
        self.assertEqual(action.start_position, position)
        self.assertIs(self.world.get_event_by_id(action.id), action)
        self.assertEqual(self.enc.cancelled_action_list, [action.id])
        self.assertIsNone(action.resolution)


    def test_legacy_completion_hook_failure_occurs_after_finished_publication(self):
        def fail(encounter):
            raise ValueError('delivery failed')
        action = self.probe(completed=fail)
        self.enc.schedule_action(action)
        with self.assertRaisesRegex(ValueError, 'delivery failed'):
            self.enc.step()
        self.assertEqual(self.enc.finished_action_list, [action.id])
        self.assertEqual(self.enc.time, 1)
        self.assertIsNotNone(self.enc.boundary_fault)
        with self.assertRaises(BoundaryInvariantError):
            self.enc.step()

    def test_increment2_failure_retains_legacy_effects_but_refuses_retry(self):
        import random
        before_rng = random.getstate()
        self.addCleanup(random.setstate, before_rng)
        def fail():
            self.b.set_hit_points(3)
            random.random()
            raise ValueError('failed after effects')
        action = self.probe(resolve=fail)
        self.enc.schedule_action(action)
        with self.assertRaisesRegex(ValueError, 'failed after effects'):
            self.enc.step(velocities={self.a.id: (1, 0, 0)})
        self.assertEqual(self.a.get_position().x, 1)
        self.assertEqual(self.b.get_hit_points(), 3)
        self.assertEqual(self.enc.time, 1)
        self.assertEqual(self.enc.last_processed_boundary, 0)
        self.assertIn(action.id, self.enc.pending_action_list)
        self.assertEqual(self.enc.fatigue_frame_history, [])
        self.assertIsNone(self.enc._active_fatigue_frame)
        self.assertNotEqual(before_rng, random.getstate())
        after_rng = random.getstate()
        with self.assertRaisesRegex(BoundaryInvariantError, 'faulted'):
            self.enc.step(velocities={self.a.id: (1, 0, 0)})
        self.assertEqual(self.a.get_position().x, 1)
        self.assertEqual(random.getstate(), after_rng)


    def test_legacy_same_second_practice_is_visible_to_later_evaluator(self):
        seen = []
        first = self.probe(resolve=lambda: ActionResolution('failure', (SkillExercise('spot', 250),)))
        second = self.probe(resolve=lambda: seen.append(self.a.get_skill_level('spot')))
        self.enc.schedule_action(first)
        self.enc.schedule_action(second)
        self.enc.step()
        self.assertEqual(seen, [1])

    def test_increment1_opaque_encounter_event_is_rejected(self):
        event = Event(self.world, 0, 1)
        event.actor_id, event.target_id = self.a.id, self.b.id
        calls = []
        event.resolve = lambda dc: calls.append(dc)
        with self.assertRaises(TypeError):
            self.enc.schedule_action(event)
        self.assertIsNone(self.world.get_event_by_id(event.id))
        self.assertEqual(calls, [])


    def test_increment1_missing_instrument_is_rejected_before_publication(self):
        action = self.probe(instrument='missing-instrument')
        with self.assertRaisesRegex(ValueError, 'instrument'):
            self.enc.schedule_action(action)
        self.assertIsNone(self.world.get_event_by_id(action.id))


    def test_legacy_target_disappearance_raises_without_completing_strike(self):
        action = self.strike()
        self.enc.schedule_action(action)
        self.world.object_registry.object_instances.pop(self.b.id)
        with self.assertRaises(BoundaryInvariantError):
            self.enc.step(2)
        self.assertIn(action.id, self.enc.pending_action_list)
        self.assertEqual(self.enc.time, 0)

    def test_legacy_instrument_disappearance_completes_as_weapon_unavailable(self):
        action = self.strike()
        self.enc.schedule_action(action)
        self.world.object_registry.object_instances.pop(self.blade)
        with patch('action.roll_dice') as rolls:
            self.enc.step(2)
        rolls.assert_not_called()
        self.assertIn(action.id, self.enc.finished_action_list)
        self.assertEqual(action.resolution.outcome, 'weapon_unavailable')
        self.assertEqual(action.resolution.skill_exercises, ())

    def test_increment2_canceled_due_action_is_not_resolved_from_stale_work_list(self):
        later = self.probe()
        first = self.probe(completed=lambda e: e.cancel_action(later.id))
        self.enc.schedule_action(first)
        self.enc.schedule_action(later)
        self.assertEqual(self.enc.step().completed_action_ids, (first.id,))
        self.assertEqual(later.calls, 0)
        self.assertIn(later.id, self.enc.cancelled_action_list)
        self.assertNotIn(later.id, self.enc.finished_action_list)



class TestLegacyDamage(LegacyEncounterFixture):
    def test_legacy_ordinary_damage_zero_clamp_and_negative_hp_reset(self):
        self.b.set_hit_points(12)
        self.b.damage(8)
        self.assertEqual(self.b.get_hit_points(), 4)
        self.b.damage(7)
        self.assertEqual(self.b.get_hit_points(), 0)
        self.b.set_hit_points(-12)
        self.b.damage(6)
        self.assertEqual(self.b.get_hit_points(), 0)

    def test_legacy_armor_hp_zero_clamps_but_protection_does_not_degrade(self):
        armor_id = self.world.make_armor_for_being(self.b.id, 'Leather armor', 'Vest')
        armor = self.world.get_object_by_id(armor_id)
        armor.current.hit_points = 6
        weapon = self.world.get_object_by_id(self.blade)
        through = armor.damage_through(4, weapon, 'thrust')
        armor.damage(4)
        armor.damage(4)
        self.assertEqual(armor.hit_points(), 0)
        self.assertEqual(armor.damage_through(4, weapon, 'thrust'), through)

    def test_legacy_multiple_fatals_are_nonadditive_and_do_not_heal_by_themselves(self):
        action = self.strike()
        for initial, expected in [(20, -10), (-10, -10), (-12, -12)]:
            with self.subTest(initial=initial):
                self.b.set_hit_points(initial)
                action.do_fatal_hit()
                action.do_fatal_hit()
                self.assertEqual(self.b.get_hit_points(), expected)

    def test_legacy_fatal_and_ordinary_damage_are_order_dependent(self):
        action = self.strike()
        self.b.set_hit_points(20)
        action.do_fatal_hit()
        self.b.damage(6)
        self.assertEqual(self.b.get_hit_points(), 0)
        self.b.set_hit_points(20)
        self.b.damage(6)
        action.do_fatal_hit()
        self.assertEqual(self.b.get_hit_points(), -10)

    def test_legacy_fatal_path_rolls_defender_save_without_ordinary_damage(self):
        action = self.strike()
        with patch('action.roll_dice', side_effect=[20, 20]) as attack_roll, \
             patch.object(self.b, 'makes_save', return_value=False) as save, \
             patch.object(action, 'damage_potential') as damage:
            Action.resolve(action, 10)
        self.assertEqual(attack_roll.call_count, 2)
        save.assert_called_once_with(self.b.current.abilities.CON, 10)
        damage.assert_not_called()
        self.assertEqual(self.b.get_hit_points(), -10)

    def test_legacy_successful_fatal_save_falls_back_to_critical_damage(self):
        action = self.strike()
        with patch('action.roll_dice', side_effect=[20, 20, 2, 3]) as rolls, \
             patch.object(self.b, 'makes_save', return_value=True):
            Action.resolve(action, 10)
        self.assertEqual(rolls.call_count, 4)
        self.assertEqual(self.b.get_hit_points(), 5)
        self.assertEqual(action.hit_type, 'critical')

    def test_legacy_shared_target_records_sequential_hp_not_shared_final_hp(self):
        armor_id = self.world.make_armor_for_being(self.b.id, 'Leather armor', 'Vest')
        self.world.armor_being(self.b.id, armor_id)
        second_weapon = self.world.make_weapon_for_being(self.a.id, 'Dagger', 'Second knife')
        self.world.arm_being(self.a.id, second_weapon, 'left hand')
        second = MeleeStrike(self.enc, self.a.id, self.b.id, second_weapon, motion='thrust', reach=2)
        second.end_time = 2
        actions = [self.strike(), second]
        for action in actions:
            self.enc.schedule_action(action)
        with patch('action.roll_dice', side_effect=[17, 4, 17, 4]):
            self.enc.step(2)
        records = [a.combat_result for a in actions]
        self.assertEqual([(r.target_hp_before, r.target_hp_after) for r in records],
                         [(10, 7), (7, 4)])
        self.assertEqual([r.target_armor_damage for r in records], [4, 4])
        self.assertEqual(json.loads(actions[0].to_json())['combat_result']['target_hp_after'], 7)

    def test_legacy_drop_weapon_handler_does_not_remove_held_weapon(self):
        action = self.strike()
        before = dict(self.a.armed_with(self.world))
        action.do_drop_weapon()
        self.assertEqual(self.a.armed_with(self.world), before)

    def test_legacy_universe_loader_cannot_reconstruct_saved_probe_actions(self):
        self.world.add_event(self.enc)
        action = self.probe()
        self.enc.schedule_action(action)
        with tempfile.TemporaryDirectory() as folder:
            path = str(Path(folder) / 'world.json')
            with self.assertRaisesRegex(ValueError, 'Live choice commitments'):
                self.world.save_to_file(path)
            self.enc.cancel_action(action.id)
            self.world.save_to_file(path)
            restored = Universe('Restored', library=self.world.library)
            with self.assertRaisesRegex((ValueError, TypeError), 'checkpoint restoration is unsupported'):
                restored.load_from_file(path)


if __name__ == '__main__':
    unittest.main()
