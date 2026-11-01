"""Increment 1 target behavior; no boundary, reservation, or damage changes."""
from dataclasses import FrozenInstanceError, replace
import json
import math
from pathlib import Path
import random
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from action import Action
from activities import RunAction, SpotAction
from encounter import Encounter
from event import Event
from group_observation import ObserveGroupAction
from history_conversation import AskAboutPastAction
from library import Library
from melee_combat import MeleeStrike
from melee_defense import MeleeDefense
from scheduling import PreparedSchedule, UnsupportedScheduleExtension
from spatial.state import CartesianPosition
from statistical_group import StatisticalGroup
from tactical_duel import TacticalDuel
from universe import Universe


class TestSchedulePreparation(unittest.TestCase):
    def setUp(self):
        self.world = Universe('Preparation', library=Library(config_dir=str(ROOT / 'src/config')))
        self.a = self.world.get_object_by_id(self.world.make_being('Human', 'A'))
        self.b = self.world.get_object_by_id(self.world.make_being('Human', 'B'))
        self.a.set_position(CartesianPosition(0, 0, 0))
        self.b.set_position(CartesianPosition(1, 0, 0))
        self.blade = self.world.make_weapon_for_being(self.a.id, 'Dagger', 'Blade')
        self.world.arm_being(self.a.id, self.blade, 'right hand')
        self.enc = Encounter(self.world, 10, 0, initiated=True)
        self.enc.add_being(self.a.id)
        self.enc.add_being(self.b.id)
        self.enc.mark_aware(self.a.id, self.b.id)
        self.enc.mark_aware(self.b.id, self.a.id)
        self.world.add_event(self.enc)

    def action(self, end=1):
        action = Action(self.world, 0, None, 'inspect', self.a.id, self.b.id, None)
        action.end_time = end
        return action

    def unchanged_attempt(self, action, operation, exception=None, snapshot=None):
        snapshot = snapshot or self.world.to_json
        before_world = snapshot()
        before_action = dict(action.__dict__)
        before_rng = random.getstate()
        if exception:
            with self.assertRaises(exception):
                operation()
        else:
            result = operation()
        self.assertEqual(snapshot(), before_world)
        self.assertEqual(action.__dict__, before_action)
        self.assertEqual(random.getstate(), before_rng)
        if not exception:
            return result

    def test_start_zero_duration_one_and_fractional_durations(self):
        for duration in (1, 1.25, 2.5):
            with self.subTest(duration=duration):
                action = self.action(duration)
                self.assertEqual(self.enc.schedule_action(action), action.id)
                self.assertEqual((action.start_time, action.end_time), (0, duration))
                self.assertEqual(action.parent_event_id, self.enc.id)
                self.assertIs(self.world.get_event_by_id(action.id), action)

    def test_finalized_duration_and_start_rejection_has_no_effects(self):
        for start, end in [(0, 0), (0, .99), (0, -1), (-1, 1),
                           (0, math.inf), (0, math.nan), (0, None),
                           (math.inf, 2), (math.nan, 2), (True, 2), (0, False)]:
            with self.subTest(start=start, end=end):
                action = self.action(end)
                action.start_time = start
                self.unchanged_attempt(action, lambda: self.enc.schedule_action(action), ValueError)

    def test_prepared_packet_is_frozen_and_preparation_does_not_register(self):
        action = self.action()
        prepared = self.unchanged_attempt(action, lambda: self.enc.prepare_action(action))
        self.assertIsInstance(prepared, PreparedSchedule)
        with self.assertRaises(FrozenInstanceError):
            prepared.end_time = 0
        self.assertIsNone(action.parent_event_id)
        self.assertIsNone(self.world.get_event_by_id(action.id))

    def test_run_initial_position_is_staged_until_valid_publication(self):
        action = RunAction(self.world, self.a.id, 0, 1.25, minimum_distance=1)
        prepared = self.unchanged_attempt(action, lambda: self.enc.prepare_action(action))
        self.assertEqual(dict(prepared.initialization)['start_position'], self.a.get_position())
        self.assertIsNone(action.start_position)
        self.enc.schedule_action(action)
        self.assertEqual(action.start_position, self.a.get_position())

    def test_failed_short_run_does_not_publish_start_binding(self):
        action = RunAction(self.world, self.a.id, 0, .5, minimum_distance=1)
        self.unchanged_attempt(action, lambda: self.enc.schedule_action(action), ValueError)

    def test_spot_binding_is_staged(self):
        action = SpotAction(self.world, self.a.id, self.b.id, 0)
        self.unchanged_attempt(action, lambda: self.enc.prepare_action(action))
        self.assertIsNone(action._encounter)
        self.enc.schedule_action(action)
        self.assertIs(action._encounter, self.enc)

    def test_defense_placeholder_prepares_positive_final_timing_without_mutation(self):
        attack = MeleeStrike(self.enc, self.a.id, self.b.id, self.blade,
                             motion='thrust', reach=2)
        self.enc.schedule_action(attack)
        defense = MeleeDefense(self.enc, self.b.id, self.a.id, kind='dodge',
                               target_action_id=attack.id)
        self.assertEqual(defense.end_time, 0)
        prepared = self.unchanged_attempt(defense, lambda: self.enc.prepare_action(defense))
        self.assertEqual(prepared.end_time, 4)
        self.assertEqual(dict(prepared.initialization)['ready_at'], 2)
        self.assertIsNone(defense.ready_at)
        self.enc.schedule_action(defense)
        self.assertEqual((defense.ready_at, defense.end_time), (2, 4))

    def test_invalid_final_defense_deadline_leaves_readiness_and_threat_unset(self):
        attack = MeleeStrike(self.enc, self.a.id, self.b.id, self.blade,
                             motion='thrust', reach=2)
        self.enc.schedule_action(attack)
        self.enc.end_time = 3
        defense = MeleeDefense(self.enc, self.b.id, self.a.id, kind='dodge',
                               target_action_id=attack.id)
        self.unchanged_attempt(defense, lambda: self.enc.schedule_action(defense), ValueError)
        self.assertEqual((defense.end_time, defense.ready_at, defense.threat_at_schedule),
                         (0, None, ()))

    def test_group_preparation_does_not_realize_composition_or_learn_evidence(self):
        config = json.loads((ROOT / 'examples/nomadic_group.json').read_text())
        group = StatisticalGroup('Group', 'group-preparation', config, config['seed'])
        self.world.add_object(group)
        self.enc.add_object(group.id)
        action = ObserveGroupAction(self.world, self.a.id, group.id, 0,
            observation={'coarse_range_m': 100, 'detailed_range_m': 10})
        self.unchanged_attempt(action, lambda: self.enc.prepare_action(action))
        self.assertIsNone(group._counts)
        self.assertEqual(group._composition_reality.revision, 0)
        self.assertIsNone(action._encounter)

    def test_history_preparation_never_calls_generator_or_delivers_accounts(self):
        history = self.b.begin_personal_history(earliest=0, known_through=0)
        calls, accounts = [], []
        action = AskAboutPastAction(self.world, self.a.id, self.b.id, 0,
            episode_time=0, topic='past', generate=lambda h, v: calls.append(1),
            received_accounts=accounts)
        # The legacy Universe serializer cannot traverse PersonalHistory's
        # back-reference. Inspect its authoritative ledger directly instead.
        self.unchanged_attempt(action, lambda: self.enc.prepare_action(action),
            snapshot=lambda: (self.enc.to_json(), history.to_jsonable(),
                              self.a.get_hit_points(), self.b.get_hit_points()))
        self.assertEqual((history.reality.revision, calls, accounts), (0, [], []))
        self.assertIsNone(action._encounter)

    def test_parent_target_instrument_and_collision_rejection_preserves_action(self):
        for field, value in [('parent_event_id', 'other'), ('target_id', 'missing'),
                             ('actor_id', 'missing'), ('instrument_id', 'missing')]:
            action = self.action()
            setattr(action, field, value)
            self.unchanged_attempt(action, lambda: self.enc.schedule_action(action), ValueError)
        action = self.action()
        other = Event(self.world, 0, 1, id=action.id)
        self.world.add_event(other)
        self.unchanged_attempt(action, lambda: self.enc.schedule_action(action), ValueError)

    def test_post_preparation_candidate_is_validated_before_initialization(self):
        action = self.action()
        base = PreparedSchedule.from_action(action)
        for packet in [replace(base, end_time=.5), replace(base, end_time=math.inf),
                       replace(base, parent_event_id='other'),
                       replace(base, instrument_id='missing'),
                       replace(base, active_object_ids=('missing',)),
                       replace(base, initialization=(('parent_event_id', 'other'),))]:
            with self.subTest(packet=packet):
                with patch('scheduling.PreparedSchedule.from_action', return_value=packet):
                    self.unchanged_attempt(action, lambda: self.enc.schedule_action(action), ValueError)

    def test_custom_mutating_hook_is_rejected_before_rng_actor_or_nested_effects(self):
        action, nested = self.action(), self.action()
        calls, accounts = [], []
        def unsafe(encounter):
            calls.append(1)
            accounts.append('leaked')
            random.random()
            self.a.set_hit_points(0)
            encounter.schedule_action(nested)
        action.on_schedule = unsafe
        self.unchanged_attempt(action, lambda: self.enc.schedule_action(action), UnsupportedScheduleExtension)
        self.assertEqual((calls, accounts), ([], []))
        self.assertIsNone(self.world.get_event_by_id(nested.id))

    def test_named_prepare_callback_is_not_trusted_just_because_of_its_name(self):
        calls = []
        class Unsafe(Action):
            def prepare_schedule(self, encounter):
                calls.append(1)
                random.random()
                return PreparedSchedule.from_action(self)
        action = Unsafe(self.world, 0, None, 'inspect', self.a.id, self.b.id, None)
        self.unchanged_attempt(action, lambda: self.enc.schedule_action(action), UnsupportedScheduleExtension)
        self.assertEqual(calls, [])

    def test_specialized_helper_override_is_rejected_before_invocation(self):
        action = MeleeStrike(self.enc, self.a.id, self.b.id, self.blade,
                             motion='thrust', reach=2)
        calls = []
        action.damage_potential = lambda: calls.append(1)
        self.unchanged_attempt(action, lambda: self.enc.schedule_action(action), UnsupportedScheduleExtension)
        self.assertEqual(calls, [])

    def test_resolver_only_subclass_can_inherit_safe_base_scheduling(self):
        class SafeScheduling(Action):
            def resolve(self, difficulty_class):
                return None
        action = SafeScheduling(self.world, 0, None, 'inspect', self.a.id, self.b.id, None)
        self.enc.schedule_action(action)
        self.assertIn(action.id, self.enc.pending_action_list)

    def test_custom_dictionary_descriptor_is_rejected_before_execution(self):
        calls = []
        class UnsafeDictionary(Action):
            @property
            def __dict__(self):
                calls.append(1)
                random.random()
                return {}
        action = UnsafeDictionary(self.world, 0, None, 'inspect', self.a.id, self.b.id, None)
        before_world, before_rng = self.world.to_json(), random.getstate()
        with self.assertRaises(UnsupportedScheduleExtension):
            self.enc.schedule_action(action)
        self.assertEqual(calls, [])
        self.assertEqual(random.getstate(), before_rng)
        self.assertEqual(self.world.to_json(), before_world)

    def test_ordinary_universe_origin_event_is_preserved_but_encounter_extension_refused(self):
        origin = self.world.get_event_by_id('0')
        self.assertEqual(origin.start_time, 0)
        event = Event(self.world, 0, 0)
        calls = []
        event.actor_id = self.a.id
        event.resolve = lambda dc: calls.append(1)
        event.on_schedule = lambda encounter: calls.append(2)
        with self.assertRaises(UnsupportedScheduleExtension):
            self.enc.schedule_action(event)
        self.assertEqual(calls, [])
        self.world.add_event(event)  # Ordinary Universe Event semantics unchanged.
        self.assertIs(self.world.get_event_by_id(event.id), event)

    def test_invalid_replacement_does_not_cancel_existing_activity(self):
        previous = self.action()
        self.enc.schedule_action(previous)
        invalid = self.action(.5)
        self.unchanged_attempt(invalid, lambda: self.enc.schedule_action(
            invalid, interrupt_action_id=previous.id), ValueError)
        self.assertEqual(self.enc.pending_action_list, [previous.id])
        self.assertEqual(self.enc.cancelled_action_list, [])

    def test_valid_replacement_preserves_interruption_provenance(self):
        previous, replacement = self.action(), self.action(2)
        self.enc.schedule_action(previous)
        self.enc.schedule_action(replacement, interrupt_action_id=previous.id)
        self.assertEqual(self.enc.pending_action_list, [replacement.id])
        self.assertEqual(self.enc.cancelled_action_list, [previous.id])
        self.assertEqual(previous.canceled_at, 0)
        self.assertIs(self.world.get_event_by_id(previous.id), previous)

    def test_tactical_attack_prepares_once_and_failed_reaction_preserves_attack(self):
        duel = TacticalDuel(17)
        with patch.object(duel.encounter, 'prepare_action', wraps=duel.encounter.prepare_action) as prepare:
            duel._attack(duel.player, duel.foe, duel.player_weapon, 'thrust')
        self.assertEqual(prepare.call_count, 1)
        previous = duel._pending(duel.player)
        # No perceived incoming attack at this initial instant.
        with self.assertRaises(ValueError):
            duel._react('parry')
        self.assertIs(duel._pending(duel.player), previous)

    def test_legacy_ai_uses_the_same_supported_registration_path(self):
        with patch.object(self.a, 'choose_melee_action', return_value='thrust at being'), \
             patch.object(self.b, 'is_dead', return_value=True), \
             patch.object(self.enc, 'choose_target_being', return_value=self.b.id), \
             patch.object(self.enc, 'schedule_action', wraps=self.enc.schedule_action) as schedule:
            self.enc.choose_fight_actions()
        self.assertEqual(schedule.call_count, 1)
        action = schedule.call_args.args[0]
        self.assertIs(self.world.get_event_by_id(action.id), action)
        self.assertEqual(action.parent_event_id, self.enc.id)


if __name__ == '__main__':
    unittest.main()
