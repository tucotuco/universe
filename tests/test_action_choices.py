"""Increment 3: native planning, reservations and bounded publication only."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json
from pathlib import Path
import random
import sys
import tempfile
from threading import Barrier
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from action import Action
from action_choice import ChoiceMember, ChoiceRejected
from activities import RunAction, SpotAction
from ai_duel import AgentDuel
from encounter import Encounter, BoundaryInvariantError
from event import Event
from history_conversation import AskAboutPastAction
from library import Library
from melee_combat import MeleeStrike
from melee_defense import MeleeDefense
from scheduling import PreparedSchedule, UnsupportedScheduleExtension
from realization import Fact
from spatial.state import CartesianPosition
from strategy import Strategy
from tactical_duel import TacticalDuel
from universe import Universe


class TestActionChoices(unittest.TestCase):
    def setUp(self):
        self.world = Universe('Choices', library=Library(config_dir=str(ROOT / 'src/config')))
        self.a = self.world.get_object_by_id(self.world.make_being('Human', 'A'))
        self.b = self.world.get_object_by_id(self.world.make_being('Human', 'B'))
        self.a.set_position(CartesianPosition(0, 0, 0))
        self.b.set_position(CartesianPosition(1.5, 0, 0))
        self.w1 = self.world.make_weapon_for_being(self.a.id, 'Dagger', 'First knife')
        self.w2 = self.world.make_weapon_for_being(self.a.id, 'Dagger', 'Second knife')
        self.w3 = self.world.make_weapon_for_being(self.b.id, 'Dagger', 'Other knife')
        self.world.arm_being(self.a.id, self.w1, 'right hand')
        self.world.arm_being(self.a.id, self.w2, 'left hand')
        self.world.arm_being(self.b.id, self.w3, 'right hand')
        self.enc = Encounter(self.world, 10, 0, initiated=True)
        self.enc.add_being(self.a.id)
        self.enc.add_being(self.b.id)
        self.enc.mark_aware(self.a.id, self.b.id)
        self.enc.mark_aware(self.b.id, self.a.id)
        self.world.add_event(self.enc)

    def action(self, weapon=None, start=0, end=1, actor=None, target=None):
        actor, target = actor or self.a, target or self.b
        action = Action(self.world, start, None, 'thrust' if weapon else 'inspect',
                        actor.id, target.id, weapon)
        action.end_time = end
        action.resolve = lambda dc: None  # Instrument the native timeline without new combat rules.
        return action

    def strike(self, weapon=None, actor=None, target=None):
        return MeleeStrike(self.enc, (actor or self.a).id, (target or self.b).id,
                           weapon or self.w1, motion='thrust', reach=2)

    def accept(self, actions):
        draft = self.enc.propose_choice(actions)
        validation = self.enc.validate_choice(draft)
        self.assertTrue(validation.valid, validation.diagnostics)
        return self.enc.accept_valid_choice(validation)

    def unchanged(self, operation, exception=None):
        before, rng = self.world.to_json(), random.getstate()
        reservations = self.enc.active_reservations
        if exception:
            with self.assertRaises(exception):
                operation()
        else:
            result = operation()
        self.assertEqual(self.world.to_json(), before)
        self.assertEqual(random.getstate(), rng)
        self.assertEqual(self.enc.active_reservations, reservations)
        if not exception:
            return result

    def test_invalid_complete_set_edit_validate_accept_loop_has_no_subset_effects(self):
        good, bad = self.action(self.w1, end=2), self.action(self.w2, end=.5)
        before, rng = self.world.to_json(), random.getstate()
        draft = self.enc.propose_choice({'good': good, 'bad': bad})
        invalid = self.enc.validate_choice(draft)
        self.assertFalse(invalid.valid)
        self.assertTrue(any(d.member == 'bad' and 'one second' in d.reason for d in invalid.diagnostics))
        self.unchanged(lambda: self.enc.accept_valid_choice(invalid), ChoiceRejected)
        self.assertEqual(self.world.to_json(), before)
        self.assertEqual(random.getstate(), rng)
        self.assertIsNone(good.parent_event_id)
        self.assertIsNone(self.world.get_event_by_id(good.id))
        replacement = self.action(self.w2, end=2)
        edited = self.enc.edit_choice(draft, {'good': good, 'corrected': replacement})
        token = self.enc.validate_choice(edited)
        choice = self.enc.accept_valid_choice(token)
        self.assertEqual(choice.state, 'accepted')
        self.assertEqual(len(self.enc.active_reservations), 2)
        self.assertEqual(self.enc.pending_action_list, [])

    def test_acceptance_reserves_without_registration_binding_history_or_rng(self):
        one, two = self.action(self.w1, start=1.5, end=2.7), self.action(self.w2, start=3, end=4)
        rng = random.getstate()
        choice = self.accept({'first': one, 'later': two})
        self.assertEqual(choice.action_ids, (one.id, two.id))
        self.assertEqual(self.enc.pending_action_list, [])
        self.assertEqual(self.enc.finished_action_list, [])
        self.assertEqual(self.enc.cancelled_action_list, [])
        self.assertTrue(all(self.world.get_event_by_id(a.id) is None and a.parent_event_id is None
                            for a in (one, two)))
        self.assertEqual([(r.start, r.boundary) for r in self.enc.active_reservations], [(1.5, 3), (3, 4)])
        self.assertEqual(random.getstate(), rng)

    def test_complete_group_publishes_once_before_any_member_starts(self):
        early = self.action(self.w1, start=1.5, end=2.7)
        later = self.action(self.w2, start=3, end=4)
        choice = self.accept({'later': later, 'early': early})
        self.enc.step(1.25)
        self.assertIsNone(self.world.get_event_by_id(early.id))
        book = self.enc._choice_book
        original = book._start_due
        observed = []
        def start(now, action_ids=None):
            if action_ids:
                observed.append(tuple(self.world.get_event_by_id(aid) is not None for aid in action_ids))
                self.assertTrue(all(aid in self.enc.pending_action_list for aid in action_ids))
            return original(now, action_ids)
        with patch.object(book, '_start_due', side_effect=start):
            self.enc.step(.25)
        self.assertEqual(observed, [(True, True)])
        self.assertEqual(self.enc.pending_action_list, [later.id, early.id])
        self.assertEqual(self.enc.choice_state['actions'][later.id], 'registered')
        self.assertEqual(self.enc.choice_state['actions'][early.id], 'executing')
        self.assertEqual(self.enc.get_choice(choice.id).state, 'executing')
        self.enc.step(2.5)
        self.assertEqual(self.enc.finished_action_list, [early.id, later.id])
        self.assertEqual(self.enc.get_choice(choice.id).state, 'finished')
        self.assertEqual(self.enc.active_reservations, ())

    def test_current_start_has_explicit_fence_and_no_undo_after_publication(self):
        action = self.action(self.w1)
        choice = self.accept([action])
        self.assertEqual(self.enc.time, 0)
        self.assertFalse(hasattr(action, '_activity_started'))
        published = self.enc.publish_choice(choice)
        self.assertEqual(published.state, 'executing')
        self.assertTrue(action._activity_started)
        self.assertEqual(self.enc.time, 0)
        self.unchanged(lambda: self.enc.undo_choice(published), ChoiceRejected)
        self.unchanged(lambda: self.enc.publish_choice(published), ChoiceRejected)

    def test_future_group_run_start_sample_excludes_earlier_movement(self):
        first = self.action(self.w1, start=1, end=2)
        run = RunAction(self.world, self.a.id, 2, 1, minimum_distance=2)
        self.accept({'first': first, 'run': run})
        self.enc.step(1, velocities={self.a.id: (1, 0, 0)})
        self.assertIsNone(run.start_position)
        self.enc.step(2, velocities={self.a.id: (1, 0, 0)})
        self.assertEqual(run.start_position.x, 2)
        self.assertEqual(run.displacement, 1)
        self.assertEqual(run.resolution.outcome, 'partial')

    def test_edit_invalidates_old_validation_and_action_mutation_is_detected(self):
        action = self.action(self.w1, start=1, end=2)
        draft = self.enc.propose_choice([action])
        token = self.enc.validate_choice(draft)
        edited = self.enc.edit_choice(draft, [self.action(self.w2, start=1, end=2)])
        self.unchanged(lambda: self.enc.accept_valid_choice(token), ChoiceRejected)
        token2 = self.enc.validate_choice(edited)
        edited.members[0].action.end_time = 3
        self.unchanged(lambda: self.enc.accept_valid_choice(token2), ChoiceRejected)

    def test_forged_validation_copy_is_not_authorization(self):
        token = self.enc.validate_choice(self.enc.propose_choice([self.action(self.w1)]))
        self.unchanged(lambda: self.enc.accept_valid_choice(replace(token)), ChoiceRejected)

    def test_acceptance_rechecks_native_prerequisites_even_without_revision_change(self):
        attack = self.strike()
        draft = self.enc.propose_choice([attack])
        token = self.enc.validate_choice(draft)
        self.a.get_body_parts()['right hand'] = None
        self.unchanged(lambda: self.enc.accept_valid_choice(token), ChoiceRejected)
        self.assertIsNone(self.world.get_event_by_id(attack.id))

    def test_internal_and_existing_conflicts_report_actions_choices_and_intervals(self):
        first, second = self.action(self.w1, start=0, end=2), self.action(self.w1, start=1, end=3.2)
        token = self.unchanged(lambda: self.enc.validate_choice(self.enc.propose_choice([first, second])))
        conflict = next(d for d in token.diagnostics if d.code == 'active_object_conflict')
        self.assertEqual(conflict.object_id, self.w1)
        self.assertEqual(conflict.interval, (1, 4))
        self.assertEqual(conflict.conflicting_interval, (0, 2))
        self.assertEqual(conflict.conflicting_action, first.id)
        accepted = self.accept([first])
        other = self.enc.validate_choice(self.enc.propose_choice([second]))
        conflict = next(d for d in other.diagnostics if d.code == 'active_object_conflict')
        self.assertEqual(conflict.conflicting_choice, accepted.id)

    def test_overlapping_real_attack_and_parry_same_weapon_refused(self):
        incoming = self.strike(self.w3, self.b, self.a)
        self.enc.schedule_action(incoming)
        own = self.strike(self.w1)
        defense = MeleeDefense(self.enc, self.a.id, self.b.id, kind='parry', parry_motion='swing',
                               target_action_id=incoming.id, weapon_id=self.w1)
        token = self.unchanged(lambda: self.enc.validate_choice(self.enc.propose_choice([own, defense])))
        self.assertFalse(token.valid)
        self.assertTrue(any(d.object_id == self.w1 for d in token.diagnostics))
        self.assertEqual(defense.end_time, 0)

    def test_one_retained_dodge_cannot_be_assigned_twice_in_one_choice(self):
        preparation = MeleeDefense(self.enc, self.a.id, kind='dodge',
            strategy=Strategy(defense=0, timing=0))
        self.enc.schedule_action(preparation)
        self.enc.step(2)
        self.assertEqual(preparation.resolution.outcome, 'ready')
        incoming = self.strike(self.w3, self.b, self.a)
        self.enc.schedule_action(incoming)
        first = MeleeDefense(self.enc, self.a.id, self.b.id, kind='dodge',
            target_action_id=incoming.id,
            prepared_defense_action_id=preparation.id)
        second = MeleeDefense(self.enc, self.a.id, self.b.id, kind='dodge',
            target_action_id=incoming.id,
            prepared_defense_action_id=preparation.id)
        token = self.enc.validate_choice(self.enc.propose_choice([first, second]))
        self.assertFalse(token.valid)
        self.assertTrue(any('already been committed' in diagnostic.reason
                            or 'more than once in a Choice' in diagnostic.reason
                            for diagnostic in token.diagnostics))

    def test_independent_instruments_and_movement_do_not_reserve_the_being(self):
        one, two = self.strike(self.w1), self.strike(self.w2)
        choice = self.accept([one, two])
        self.assertEqual({r.object_id for r in self.enc.active_reservations}, {self.w1, self.w2})
        self.enc.publish_choice(choice)
        self.enc.step(.5, velocities={self.a.id: (.5, 0, 0)})
        self.assertEqual(self.a.get_position().x, .25)
        self.assertNotIn(self.a.id, {r.object_id for r in self.enc.active_reservations})

    def test_passive_armor_and_shield_multiple_impacts_create_no_use_conflict(self):
        armor_id = self.world.make_armor_for_being(self.b.id, 'Leather armor', 'Vest')
        self.world.armor_being(self.b.id, armor_id)
        shield_id = self.world.make_weapon_for_being(self.b.id, 'Buckler', 'Shield')
        self.world.arm_being(self.b.id, shield_id, 'left hand')
        one, two = self.strike(self.w1), self.strike(self.w2)
        choice = self.accept([one, two])
        self.assertEqual({r.object_id for r in self.enc.active_reservations}, {self.w1, self.w2})
        self.enc.publish_choice(choice)
        shield = self.world.get_object_by_id(shield_id)
        before = shield.hit_points()
        with patch('action.roll_dice', side_effect=[17, 4, 1, 17, 4, 1]):
            self.enc.step(4)
        self.assertEqual(shield.hit_points(), before - 8)

    def test_unarmed_spot_and_dodge_do_not_acquire_held_weapon_reservations(self):
        incoming = self.strike(self.w3, self.b, self.a)
        self.enc.schedule_action(incoming)
        dodge = MeleeDefense(self.enc, self.a.id, self.b.id, kind='dodge', target_action_id=incoming.id)
        spot = SpotAction(self.world, self.a.id, self.b.id, 0)
        choice = self.accept([dodge, spot])
        self.assertFalse(any(r.choice_id == choice.id for r in self.enc.active_reservations))

    def test_multiple_active_objects_are_checked_by_the_same_validator(self):
        # A reviewed native packet fixture exercises the multi-Object schema;
        # it does not install an arbitrary executable extension or a new rule.
        first = self.action(self.w1, start=1, end=3)
        second = self.action(self.w2, start=1, end=3)
        original = PreparedSchedule.from_action
        def packet(action, **kwargs):
            result = original(action, **kwargs)
            return replace(result, active_object_ids=(self.w1, self.w2)) if action is first else result
        with patch('scheduling.PreparedSchedule.from_action', side_effect=packet):
            token = self.enc.validate_choice(self.enc.propose_choice([first, second]))
        self.assertFalse(token.valid)
        self.assertTrue(any(d.object_id == self.w2 for d in token.diagnostics))

    def test_whole_undo_releases_every_reservation_without_execution_trace(self):
        one, two = self.action(self.w1, start=1, end=2), self.action(self.w2, start=2, end=3)
        before = self.world.to_json()
        choice = self.accept([one, two])
        self.enc.undo_choice(choice)
        self.assertEqual(self.world.to_json(), before)
        self.assertEqual(self.enc.active_reservations, ())
        self.assertEqual(self.enc.cancelled_action_list, [])
        self.assertTrue(all(a.parent_event_id is None for a in (one, two)))

    def test_current_instant_selection_can_be_undone_only_before_its_start_fence(self):
        choice = self.accept([self.action(self.w1)])
        self.enc.undo_choice(choice)  # No simulated time or member activity has begun.
        next_choice = self.accept([self.action(self.w1)])
        self.enc.step(.25)
        self.assertEqual(self.enc.get_choice(next_choice.id).state, 'executing')
        self.unchanged(lambda: self.enc.undo_choice(next_choice.id), ChoiceRejected)

    def test_valid_replacement_reuses_old_resources_in_one_versioned_swap(self):
        old_action = self.action(self.w1, start=2, end=4)
        old = self.accept([old_action])
        new_action = self.action(self.w1, start=2, end=3)
        draft = self.enc.propose_choice([new_action])
        token = self.enc.validate_choice(draft, replacing=old)
        self.assertTrue(token.valid, token.diagnostics)
        replacement = self.enc.replace_choice(old, token)
        self.assertEqual((replacement.id, replacement.version), (old.id, 2))
        self.assertEqual([r.action_id for r in self.enc.active_reservations], [new_action.id])
        self.assertIsNone(self.world.get_event_by_id(old_action.id))
        self.assertIsNone(old_action.parent_event_id)
        self.unchanged(lambda: self.enc.undo_choice(old), ChoiceRejected)

    def test_invalid_and_stale_replacements_preserve_original_and_its_reservations(self):
        old = self.accept([self.action(self.w1, start=2, end=4)])
        invalid = self.enc.validate_choice(self.enc.propose_choice([self.action(self.w1, start=2, end=2.5)]), replacing=old)
        self.unchanged(lambda: self.enc.replace_choice(old, invalid), ChoiceRejected)
        draft = self.enc.propose_choice([self.action(self.w1, start=2, end=3)])
        stale = self.enc.validate_choice(draft, replacing=old)
        self.accept([self.action(self.w2, start=1, end=2)])
        self.unchanged(lambda: self.enc.replace_choice(old, stale), ChoiceRejected)
        self.assertEqual(self.enc.get_choice(old.id), old)

    def test_competing_acceptance_and_concurrent_calls_cannot_double_allocate(self):
        tokens = [self.enc.validate_choice(self.enc.propose_choice([self.action(self.w1, start=2, end=4)]))
                  for _ in range(2)]
        barrier = Barrier(2)
        def attempt(token):
            barrier.wait()
            try:
                return self.enc.accept_valid_choice(token).state
            except ChoiceRejected:
                return 'rejected'
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, tokens))
        self.assertEqual(sorted(results), ['accepted', 'rejected'])
        self.assertEqual(len(self.enc.active_reservations), 1)

    def test_competitor_cannot_observe_transient_release_during_replacement(self):
        old = self.accept([self.action(self.w1, start=2, end=4)])
        token = self.enc.validate_choice(self.enc.propose_choice([self.action(self.w1, start=2, end=3)]), replacing=old)
        competitor = self.enc.validate_choice(self.enc.propose_choice([self.action(self.w1, start=2, end=3)]))
        self.assertFalse(competitor.valid)
        self.enc.replace_choice(old, token)
        self.unchanged(lambda: self.enc.accept_valid_choice(competitor), ChoiceRejected)
        self.assertEqual(len(self.enc.active_reservations), 1)

    def test_same_set_defense_local_key_resolves_without_early_registration(self):
        attack = self.strike(self.w3, self.b, self.a)
        defense = MeleeDefense(self.enc, self.a.id, self.b.id, kind='parry', parry_motion='swing',
                               target_action_id='incoming', weapon_id=self.w1)
        draft = self.enc.propose_choice([ChoiceMember('defense', defense, 'incoming'),
                                         ChoiceMember('incoming', attack)])
        validation = self.enc.validate_choice(draft)
        self.assertTrue(validation.valid, validation.diagnostics)
        self.assertEqual((defense.target_action_id, defense.end_time), ('incoming', 0))
        self.assertIsNone(self.world.get_event_by_id(attack.id))
        choice = self.enc.accept_valid_choice(validation)
        self.enc.publish_choice(choice)
        self.assertEqual(defense.target_action_id, attack.id)
        self.assertEqual(defense.end_time, attack.end_time)
        self.assertEqual(self.enc.pending_action_list, [defense.id, attack.id])
        with patch('melee_defense.roll_dice', side_effect=[20, 1]):
            self.enc.step(4)
        self.assertEqual(attack.defended_by, defense.id)
        self.assertEqual(self.a.get_skill_experience('Dagger'), 10)
        self.assertEqual(self.b.get_skill_experience('Dagger'), 10)

    def test_invalid_same_set_reference_is_editable_without_partial_registration(self):
        defense = MeleeDefense(self.enc, self.a.id, self.b.id, kind='parry', parry_motion='swing',
                               target_action_id='missing', weapon_id=self.w1)
        draft = self.enc.propose_choice([ChoiceMember('defense', defense, 'missing')])
        token = self.unchanged(lambda: self.enc.validate_choice(draft))
        self.assertFalse(token.valid)
        self.assertIn('reference', token.diagnostics[0].reason)
        attack = self.strike(self.w3, self.b, self.a)
        edited = self.enc.edit_choice(draft, [ChoiceMember('defense', defense, 'incoming'),
                                              ChoiceMember('incoming', attack)])
        self.assertTrue(self.enc.validate_choice(edited).valid)

    def test_opaque_nested_mutating_preparation_is_never_executed(self):
        calls = []
        unsafe = self.action()
        def hook(enc):
            calls.append(1)
            random.random()
            self.a.set_hit_points(0)
            enc.schedule_action(self.action(self.w1))
        unsafe.on_schedule = hook
        draft = self.enc.propose_choice([self.action(self.w2), unsafe])
        token = self.unchanged(lambda: self.enc.validate_choice(draft))
        self.assertFalse(token.valid)
        self.unchanged(lambda: self.enc.accept_valid_choice(token), ChoiceRejected)
        self.assertEqual(calls, [])

    def test_single_adapter_prepares_once_and_cannot_bypass_reservations(self):
        action = self.strike()
        with patch.object(self.enc, 'prepare_action', wraps=self.enc.prepare_action) as prepare:
            self.enc.schedule_action(action)
        self.assertEqual(prepare.call_count, 1)
        self.unchanged(lambda: self.enc.schedule_action(self.strike()), ChoiceRejected)

    def test_publication_collision_validates_all_ids_before_writing_any_member(self):
        one, two = self.action(self.w1), self.action(self.w2)
        choice = self.accept([one, two])
        collision = Event(self.world, 0, 1, id=two.id)
        self.world.add_event(collision)
        self.unchanged(lambda: self.enc.publish_choice(choice), ValueError)
        self.assertIsNone(self.world.get_event_by_id(one.id))
        self.assertIsNone(one.parent_event_id)
        self.assertEqual(self.enc.get_choice(choice.id).state, 'accepted')

    def test_bounded_publication_failure_restores_registries_parents_and_references(self):
        one, two = self.action(self.w1), self.action(self.w2)
        choice = self.accept([one, two])
        history, pending = self.world.event_history, self.enc.pending_action_list
        original = self.enc._choice_book._publish_updates
        def failed(record):
            original(record)
            raise RuntimeError('injected native metadata failure')
        with patch.object(self.enc._choice_book, '_publish_updates', side_effect=failed):
            self.unchanged(lambda: self.enc.publish_choice(choice), RuntimeError)
        self.assertIs(self.world.event_history, history)
        self.assertIs(self.enc.pending_action_list, pending)
        self.assertTrue(all(a.parent_event_id is None for a in (one, two)))
        self.enc.publish_choice(choice)
        self.assertEqual(pending, [one.id, two.id])

    def test_failed_single_replacement_publication_restores_old_interruption_state(self):
        old, new = self.action(self.w1), self.action(self.w1)
        self.enc.schedule_action(old)
        with patch.object(self.enc._choice_book, '_publish_updates', side_effect=RuntimeError('publication failed')):
            self.unchanged(lambda: self.enc.schedule_action(new, interrupt_action_id=old.id), RuntimeError)
        self.assertNotIn('canceled_at', old.__dict__)
        self.assertEqual(self.enc.pending_action_list, [old.id])

    def test_endpoint_handoff_waits_for_settlement_even_after_first_action_finishes(self):
        rejected = []
        first = self.action(self.w1, end=2)
        def completion(enc):
            handoff = self.action(self.w1, start=2, end=3)
            with self.assertRaisesRegex(ChoiceRejected, 'settlement'):
                enc.schedule_action(handoff)
            rejected.append(handoff.id)
        first.on_completed = completion
        self.enc.schedule_action(first)
        self.enc.step(2)
        self.assertEqual(len(rejected), 1)
        self.assertEqual(self.enc.active_reservations, ())
        next_action = self.action(self.w1, start=2, end=3)
        self.enc.schedule_action(next_action)
        self.assertIn(next_action.id, self.enc.pending_action_list)

    def test_future_endpoint_choice_publishes_after_old_boundary_settles(self):
        first = self.action(self.w1, end=2)
        self.enc.schedule_action(first)
        future = self.action(self.w1, start=2, end=3)
        choice = self.accept([future])
        first.on_completed = lambda enc: self.assertIsNone(self.world.get_event_by_id(future.id))
        self.enc.step(2)
        self.assertEqual(self.enc.get_choice(choice.id).state, 'executing')
        self.assertIs(self.world.get_event_by_id(future.id), future)

    def test_published_cancellation_is_not_choice_undo_and_releases_future_use(self):
        first = self.action(self.w1, end=3)
        self.enc.schedule_action(first)
        self.enc.step(.5)
        self.enc.cancel_action(first.id)
        self.assertEqual(self.enc.cancelled_action_list, [first.id])
        self.assertIs(self.world.get_event_by_id(first.id), first)
        self.assertEqual(self.enc.active_reservations, ())
        self.enc.schedule_action(self.action(self.w1, start=.5, end=1.5))

    def test_cancel_later_registered_member_keeps_group_undo_closed(self):
        one, two = self.action(self.w1), self.action(self.w2, start=2, end=3)
        choice = self.accept([one, two])
        self.enc.publish_choice(choice)
        self.enc.cancel_action(two.id)
        self.unchanged(lambda: self.enc.undo_choice(choice.id), ChoiceRejected)
        self.assertIn(two.id, self.enc.cancelled_action_list)

    def test_accepted_action_edit_rejects_progression_preflight_without_fault(self):
        action = self.action(self.w1, start=1, end=2)
        choice = self.accept([action])
        action.end_time = 3
        self.unchanged(lambda: self.enc.step(velocities={self.a.id: (1, 0, 0)}), ChoiceRejected)
        self.assertIsNone(self.enc.boundary_fault)
        self.enc.undo_choice(choice)

    def test_published_instrument_unavailability_remains_a_gameplay_outcome(self):
        attack = self.strike()
        self.enc.schedule_action(attack)
        self.world.object_registry.object_instances.pop(self.w1)
        self.enc.step(4)
        self.assertEqual(attack.resolution.outcome, 'weapon_unavailable')
        self.assertIsNone(self.enc.boundary_fault)

    def test_future_started_run_can_report_unplaced_without_planning_rollback(self):
        first = self.action(start=1, end=2)
        run = RunAction(self.world, self.a.id, 2, 1, minimum_distance=1)
        self.accept([first, run])
        self.enc.step(1)
        self.a.set_spatial_state(None)
        self.enc.step(2)
        self.assertEqual(run.resolution.outcome, 'unplaced')
        self.assertIsNone(self.enc.boundary_fault)

    def test_raw_registration_and_queue_append_cannot_bypass_native_publication(self):
        action = self.action(self.w1)
        with self.assertRaisesRegex(ValueError, 'choice publication'):
            self.world.add_event(action)
        action.parent_event_id = self.enc.id
        self.world.event_history[action.id] = action  # Deliberate corruption.
        self.enc.pending_action_list.append(action.id)
        self.unchanged(lambda: self.enc.step(), BoundaryInvariantError)

    def test_facades_and_legacy_ai_obey_competing_native_reservations(self):
        game = TacticalDuel(17)
        planned = MeleeStrike(game.encounter, game.player.id, game.foe.id,
                              game.player_weapon, motion='thrust', reach=game.REACH)
        draft = game.encounter.propose_choice([planned])
        game.encounter.accept_valid_choice(game.encounter.validate_choice(draft))
        previous_time = game.encounter.time
        with self.assertRaises(ChoiceRejected):
            game._attack(game.player, game.foe, game.player_weapon, 'thrust')
        self.assertEqual(game.encounter.time, previous_time)
        self.assertEqual(game.encounter.pending_action_list, [])
        ai = AgentDuel(17, policy=Mock())
        own = MeleeStrike(ai.encounter, ai.foe.id, ai.player.id, ai.foe_weapon,
                          motion='swing', reach=ai.REACH)
        record = ai.encounter.propose_choice([own])
        ai.encounter.accept_valid_choice(ai.encounter.validate_choice(record))
        with self.assertRaises(ChoiceRejected):
            ai._attack(ai.foe, ai.player, ai.foe_weapon, 'swing')
        reserved = self.accept([self.action(self.w1, start=2, end=4)])
        with patch.object(self.a, 'choose_melee_action', return_value='thrust at being'), \
             patch.object(self.b, 'is_dead', return_value=True), \
             patch.object(self.a, 'choose_weapon', return_value=self.w1), \
             patch.object(self.enc, 'choose_target_being', return_value=self.b.id):
            with self.assertRaises(ChoiceRejected):
                self.enc.choose_fight_actions()
        self.assertEqual(self.enc.get_choice(reserved.id).state, 'accepted')

    def test_live_choice_exports_refuse_without_truncation_and_summary_is_versionable(self):
        choice = self.accept([self.action(self.w1, start=1, end=2)])
        summary = json.loads(self.world.to_json())['event_history'][self.enc.id]['choice_state']
        self.assertEqual(summary['version'], 1)
        self.assertEqual(summary['choices'][0]['id'], choice.id)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'checkpoint.json'
            path.write_text('preserve')
            with self.assertRaisesRegex(ChoiceRejected, 'coherent restore'):
                self.world.save_to_file(path)
            self.assertEqual(path.read_text(), 'preserve')
        game = TacticalDuel(17)
        action = Action(game.world, 1, None, 'inspect', game.player.id, game.foe.id, None)
        action.end_time = 2
        draft = game.encounter.propose_choice([action])
        game.encounter.accept_valid_choice(game.encounter.validate_choice(draft))
        with self.assertRaisesRegex(ChoiceRejected, 'coherent restore'):
            game.to_session()

    def test_invalid_keys_duplicate_members_and_empty_sets_return_diagnostics(self):
        action = self.action(self.w1)
        for members in ([], [ChoiceMember('x', action), ChoiceMember('x', self.action())],
                        [ChoiceMember('x', action), ChoiceMember('y', action)],
                        [ChoiceMember([], action)]):
            with self.subTest(members=members):
                token = self.unchanged(lambda: self.enc.validate_choice(self.enc.propose_choice(members)))
                self.assertFalse(token.valid)

    def test_live_object_reservations_are_shared_across_native_encounters(self):
        other = Encounter(self.world, 10, 0, initiated=True)
        other.add_being(self.a.id)
        other.add_being(self.b.id)
        first = self.accept([self.action(self.w1, start=1, end=3)])
        candidate = self.action(self.w1, start=2, end=4)
        token = other.validate_choice(other.propose_choice([candidate]))
        self.assertFalse(token.valid)
        conflict = next(d for d in token.diagnostics if d.object_id == self.w1)
        self.assertEqual(conflict.conflicting_choice, first.id)
        with self.assertRaises(ChoiceRejected):
            other.accept_valid_choice(token)
        self.assertEqual(other.pending_action_list, [])

    def test_foreign_boundary_must_settle_before_global_object_handoff(self):
        other = Encounter(self.world, 10, 2, initiated=True)
        other.add_being(self.a.id)
        other.add_being(self.b.id)
        first = self.action(self.w1, end=2)
        def during_boundary(enc):
            candidate = self.action(self.w1, start=2, end=3)
            token = other.validate_choice(other.propose_choice([candidate]))
            self.assertFalse(token.valid)
            self.assertTrue(any(d.code == 'active_object_conflict' for d in token.diagnostics))
        first.on_completed = during_boundary
        self.enc.schedule_action(first)
        self.enc.step(2)
        other.schedule_action(self.action(self.w1, start=2, end=3))
        self.assertEqual(len(other.active_reservations), 1)

    def test_unregistered_context_live_choice_cannot_be_dropped_by_world_export(self):
        other = Encounter(self.world, 10, 0, initiated=True)
        other.add_being(self.a.id)
        other.add_being(self.b.id)
        draft = other.propose_choice([self.action(self.w1, start=1, end=2)])
        other.accept_valid_choice(other.validate_choice(draft))
        self.assertIsNone(self.world.get_event_by_id(other.id))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'checkpoint.json'
            with self.assertRaises(ChoiceRejected):
                self.world.save_to_file(path)
            self.assertFalse(path.exists())

    def test_ordinary_event_import_cannot_overwrite_live_choice_commitments(self):
        self.accept([self.action(self.w1, start=1, end=2)])
        ordinary = Universe('Ordinary', library=self.world.library)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'ordinary.json'
            ordinary.save_to_file(path)
            self.unchanged(lambda: self.world.load_from_file(path), ChoiceRejected)

    def test_rejected_legacy_ai_complete_set_has_no_partial_registration_or_rng(self):
        self.accept([self.action(self.w1, start=2, end=4)])
        with patch.object(self.a, 'choose_melee_action', new=lambda universe: 'thrust at being'), \
             patch.object(self.b, 'is_dead', new=lambda: True), \
             patch.object(self.a, 'choose_weapon', new=lambda held: self.w1), \
             patch.object(self.enc, 'choose_target_being', new=lambda actor: self.b.id):
            self.unchanged(self.enc.run, ChoiceRejected)
        self.assertIsNone(self.enc.boundary_fault)

    def test_valid_legacy_ai_multiple_actors_publish_one_complete_native_set(self):
        observed = []
        original = self.enc._choice_book._publish_updates
        def publish(record):
            observed.append(record.view.action_ids)
            self.assertEqual(len(record.members), 2)
            self.assertTrue(all(self.world.get_event_by_id(aid) is None for aid in record.view.action_ids))
            return original(record)
        with patch.object(self.a, 'choose_melee_action', return_value='thrust at being'), \
             patch.object(self.b, 'choose_melee_action', return_value='thrust at being'), \
             patch.object(self.a, 'choose_weapon', return_value=self.w1), \
             patch.object(self.b, 'choose_weapon', return_value=self.w3), \
             patch.object(self.enc, 'choose_target_being', side_effect=lambda aid:
                          self.b.id if aid == self.a.id else self.a.id), \
             patch.object(self.enc._choice_book, '_publish_updates', side_effect=publish):
            self.enc.choose_fight_actions()
        self.assertEqual(len(observed), 1)
        self.assertEqual(tuple(self.enc.pending_action_list), observed[0])

    def test_active_cancellation_holds_endpoint_until_settlement(self):
        victim = self.action(self.w1, end=4)
        self.enc.schedule_action(victim)
        trigger = self.action(end=1)
        def callback(enc):
            enc.cancel_action(victim.id)
            with self.assertRaises(ChoiceRejected):
                enc.schedule_action(self.action(self.w1, start=1, end=2))
        trigger.on_completed = callback
        self.enc.schedule_action(trigger)
        self.enc.step(1)
        self.enc.schedule_action(self.action(self.w1, start=1, end=2))
        self.assertEqual(len(self.enc.active_reservations), 1)

    def test_raw_event_identity_swap_cannot_reuse_a_published_action_id(self):
        original = self.action(self.w1)
        self.enc.schedule_action(original)
        forged = self.action(self.w1)
        forged.id, forged.parent_event_id = original.id, self.enc.id
        self.world.event_history[original.id] = forged
        self.unchanged(lambda: self.enc.step(), BoundaryInvariantError)

    def test_single_future_adapter_choice_is_discoverable_for_whole_undo(self):
        action = self.action(self.w1, start=1, end=2)
        self.enc.schedule_action(action)
        choice = self.enc.choice_for_action(action.id)
        self.assertEqual(choice.state, 'accepted')
        self.enc.undo_choice(choice)
        self.assertIsNone(self.enc.choice_for_action(action.id))
        self.assertEqual(self.enc.cancelled_action_list, [])

    def test_cross_context_future_handoff_cannot_start_before_prior_settlement(self):
        first = self.action(self.w1, end=2)
        self.enc.schedule_action(first)
        other = Encounter(self.world, 10, 2, initiated=True)
        other.add_being(self.a.id)
        other.add_being(self.b.id)
        action = self.action(self.w1, start=2, end=3)
        draft = other.propose_choice([action])
        choice = other.accept_valid_choice(other.validate_choice(draft))
        self.unchanged(lambda: other.publish_choice(choice), ChoiceRejected)
        self.assertIsNone(self.world.get_event_by_id(action.id))
        self.enc.step(2)
        other.publish_choice(choice)
        self.assertIs(self.world.get_event_by_id(action.id), action)

    def test_opaque_id_values_and_strategy_getters_do_not_execute_during_validation(self):
        calls = []
        class Opaque:
            def __hash__(self):
                calls.append('hash')
                random.random()
                return 1
            @property
            def attack(self):
                calls.append('strategy')
                random.random()
                return 0
        for field in ('actor_id', 'strategy'):
            action = self.action()
            setattr(action, field, Opaque())
            draft = self.enc.propose_choice([action])
            token = self.unchanged(lambda: self.enc.validate_choice(draft))
            self.assertFalse(token.valid)
        self.assertEqual(calls, [])

    def test_action_payload_restore_rejects_before_mutating_a_fresh_destination(self):
        action = self.action()
        payload = json.loads(self.world.to_json())
        payload['event_history'].pop(self.enc.id)
        payload['event_history'][action.id] = {'type': 'Action', 'id': action.id}
        destination = Universe('Unchanged', library=self.world.library)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'unsupported.json'
            path.write_text(json.dumps(payload))
            before = destination.to_json()
            with self.assertRaisesRegex(ValueError, 'Action checkpoint restoration is unsupported'):
                destination.load_from_file(path)
            self.assertEqual(destination.to_json(), before)

    def test_schedule_choice_rejects_invalid_complete_set_without_subset_registration(self):
        one, two = self.action(self.w1), self.action(self.w2, end=.5)
        self.unchanged(lambda: self.enc.schedule_choice([one, two]), ChoiceRejected)
        self.assertTrue(all(self.world.get_event_by_id(a.id) is None and a.parent_event_id is None
                            for a in (one, two)))

    def test_schedule_choice_publication_failure_restores_whole_set(self):
        one, two = self.action(self.w1), self.action(self.w2)
        original = self.enc._choice_book._publish_updates
        def fail(record):
            original(record)
            raise RuntimeError('native metadata failure')
        with patch.object(self.enc._choice_book, '_publish_updates', side_effect=fail):
            self.unchanged(lambda: self.enc.schedule_choice([one, two]), RuntimeError)
        self.assertIsNone(one.parent_event_id)
        self.assertIsNone(two.parent_event_id)

    def test_registered_later_start_pauses_safely_for_foreign_resource_handoff(self):
        self.enc.schedule_action(self.action(self.w1, end=3))
        other = Encounter(self.world, 10, 2, initiated=True)
        other.add_being(self.a.id)
        other.add_being(self.b.id)
        early = self.action(start=2, end=3)
        later = self.action(self.w1, start=4, end=5)
        draft = other.propose_choice([early, later])
        choice = other.accept_valid_choice(other.validate_choice(draft))
        other.publish_choice(choice)
        with self.assertRaisesRegex(ChoiceRejected, 'prior boundary'):
            other.step(2)
        self.assertEqual((other.time, other.last_processed_boundary), (4, 4))
        self.assertIsNone(other.boundary_fault)
        self.assertFalse(hasattr(later, '_activity_started'))
        self.enc.step(3)
        other.step(1)
        self.assertEqual(other.finished_action_list, [early.id, later.id])

    def test_started_run_becoming_unplaced_is_a_legitimate_outcome(self):
        run = RunAction(self.world, self.a.id, 0, 1, minimum_distance=1)
        self.enc.schedule_action(run)
        self.a.set_spatial_state(None)
        self.enc.step(1)
        self.assertEqual(run.resolution.outcome, 'unplaced')
        self.assertIsNone(self.enc.boundary_fault)
        self.assertEqual(self.a.get_skill_experience('run'), 0)

    def test_distinct_valid_parries_keep_both_designated_practice_records(self):
        incoming = self.strike(self.w3, self.b, self.a)
        self.enc.schedule_action(incoming)
        defenses = [MeleeDefense(self.enc, self.a.id, self.b.id, kind='parry', parry_motion='swing',
                     target_action_id=incoming.id, weapon_id=weapon) for weapon in (self.w1, self.w2)]
        self.enc.schedule_choice(defenses)
        with patch('melee_defense.roll_dice', side_effect=[20, 1, 20, 1]):
            self.enc.step(4)
        self.assertTrue(all(d.defended_action_ids == (incoming.id,) for d in defenses))
        self.assertEqual(self.a.get_skill_experience('Dagger'), 20)
        self.assertEqual(self.b.get_skill_experience('Dagger'), 10)

    def test_shared_receipt_list_changes_are_effects_not_action_declaration_edits(self):
        history = self.b.begin_personal_history(earliest=0, known_through=0)
        accounts = []
        def generate(owner, view):
            return (Fact(owner.episode_key(0, 'past'), {'description': 'A memory'}, 'test'),)
        inquiries = [AskAboutPastAction(self.world, self.a.id, self.b.id, 0,
            episode_time=0, topic='past', generate=generate, received_accounts=accounts) for _ in range(2)]
        self.enc.schedule_choice(inquiries)
        self.enc.step(1)
        self.assertEqual([account.action_id for account in accounts], [a.id for a in inquiries])
        self.assertEqual(len(history.reality.view().all_facts()), 1)
        self.assertIsNone(self.enc.boundary_fault)

    def test_accepted_delay_preserves_existing_actor_occupancy_exception(self):
        delay = self.action()
        delay.event_type = 'delay'
        self.accept([delay])
        self.assertFalse(self.enc.is_being_occupied(self.a.id))
        self.assertEqual(self.enc.active_reservations, ())


if __name__ == '__main__':
    unittest.main()
