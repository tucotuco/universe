"""Inactive native evaluation contracts; no future damage settlement assertions."""
from dataclasses import FrozenInstanceError, fields, replace
from pathlib import Path
import math
import random
import sys
import unittest
from unittest.mock import patch, Mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from action import Action
from action_choice import ChoiceMember
from action_evaluation import (capture_snapshot, evaluate_snapshot, UnsupportedEvaluation,
    EvaluationIntegrityError, DamageEffect, FatalEffect, PracticeEffect, AwarenessEffect,
    ProtectionEffect, ActionProposal, _ProvisionalRandom, RandomDraw, future_reality_request)
from activities import RunAction, SpotAction, ReadyPreparationAction
from encounter import Encounter
from action_settlement import reconcile_boundary
from library import Library
from melee_combat import MeleeStrike
from melee_defense import MeleeDefense
from strategy import Strategy
from spatial.state import CartesianPosition
from spatial.geometry import Sphere, AxisAlignedBox
from spatial.occlusion import VisualOcclusion
from universe import Universe
from statistical_group import StatisticalGroup


class TestActionEvaluation(unittest.TestCase):
    def setUp(self):
        self.world = Universe('Evaluation', library=Library(config_dir=str(ROOT / 'src/config')))
        self.a = self.world.get_object_by_id(self.world.make_being('Human', 'A'))
        self.b = self.world.get_object_by_id(self.world.make_being('Human', 'B'))
        self.a.set_position(CartesianPosition(0, 0, 0))
        self.b.set_position(CartesianPosition(1.5, 0, 0))
        for actor in (self.a, self.b):
            actor.set_geometry(Sphere(.25))
            actor.set_hit_points(100)
        self.w1 = self.world.make_weapon_for_being(self.a.id, 'Dagger', 'Knife A')
        self.w2 = self.world.make_weapon_for_being(self.a.id, 'Dagger', 'Knife A2')
        self.w3 = self.world.make_weapon_for_being(self.b.id, 'Dagger', 'Knife B')
        self.world.arm_being(self.a.id, self.w1, 'right hand')
        self.world.arm_being(self.a.id, self.w2, 'left hand')
        self.world.arm_being(self.b.id, self.w3, 'right hand')
        self.enc = Encounter(self.world, 10, 0, initiated=True)
        for actor in (self.a, self.b):
            self.enc.add_being(actor.id)
        self.enc.mark_aware(self.a.id, self.b.id)
        self.enc.mark_aware(self.b.id, self.a.id)
        self.world.add_event(self.enc)

    def strike(self, weapon=None):
        return MeleeStrike(self.enc, self.a.id, self.b.id, weapon or self.w1, motion='thrust', reach=2)

    def schedule(self, *actions):
        by_actor = {}
        proposed = {action.id: action for action in actions}
        prepared = {action.id: self.enc.prepare_action(action, _proposed_actions=proposed)
                    for action in actions}
        for action in actions:
            by_actor.setdefault(action.actor_id, []).append(action)
        members = {str(index): ChoiceMember(str(index), action)
                   for index, action in enumerate(actions)}
        penalty_rows = {2: (0, 3), 3: (0, 2, 4), 4: (0, 1, 2, 6)}
        for actor_id, rows in by_actor.items():
            overlapping = [action for action in rows if any(
                other is not action
                and max(prepared[action.id].start_time, prepared[other.id].start_time)
                    < min(prepared[action.id].end_time, prepared[other.id].end_time)
                for other in rows)]
            if not overlapping:
                continue
            actor = self.world.get_object_by_id(actor_id)
            actor.set_skill_level(self.world.get_skill_dictionary(), 'multi-action', 1)
            penalties = penalty_rows.get(len(overlapping))
            if penalties is None:
                raise AssertionError('fixture Multiple-action helper supports two through four overlapping components')
            for action, penalty in zip(overlapping, penalties):
                key = str(actions.index(action))
                members[key] = ChoiceMember(key, action, priority_penalty=penalty)
        self.enc.schedule_choice(tuple(members[str(index)] for index in range(len(actions))))

    def snapshot(self, boundary=None):
        if boundary is None:
            boundary = max(math.ceil(self.world.get_event_by_id(k).end_time) for k in self.enc.pending_action_list)
        # Fixture supplies the post-movement fence; production coordinator stays inactive.
        self.enc.time = boundary
        return capture_snapshot(self.enc, boundary)

    def unchanged(self, operation):
        state, rng = self.world.to_json(), random.getstate()
        choices = (self.enc.choice_state, self.enc.active_reservations)
        try:
            return operation()
        finally:
            self.assertEqual(self.world.to_json(), state)
            self.assertEqual(random.getstate(), rng)
            self.assertEqual((self.enc.choice_state, self.enc.active_reservations), choices)

    def scripted(self, snapshot, values):
        iterator = iter(values)
        def roll(ctx, dice):
            v = next(iterator)
            ctx.trace.append(RandomDraw(ctx.action_id, dice, int(dice[2:].split('+')[0]), v))
            return v
        with patch.object(_ProvisionalRandom, 'roll', roll):
            return self.unchanged(lambda: evaluate_snapshot(snapshot))

    def test_capture_and_evaluation_are_write_free(self):
        action = self.strike(); self.schedule(action)
        self.enc.time = math.ceil(action.end_time)
        snapshot = self.unchanged(lambda: capture_snapshot(self.enc, int(self.enc.time)))
        result = self.unchanged(lambda: evaluate_snapshot(snapshot))
        self.assertEqual(result.proposals[0].action_id, action.id)
        self.assertIsNone(action.combat_result)
        self.assertIsNone(action.hit_type)
        self.assertIsNone(action.defended_by)
        self.assertIsNone(action.resolution)

    def test_two_handed_strike_uses_explicit_free_hand_and_applies_weapon_multiplier(self):
        self.a.size_category = 'medium'
        self.a.current.body_parts['left hand'] = None
        self.b.current.armor_id = None
        action = MeleeStrike(self.enc, self.a.id, self.b.id, self.w1,
                             motion='thrust', reach=2, two_handed=True)
        self.schedule(action)
        snapshot = self.snapshot(math.ceil(action.end_time))
        result = self.scripted(snapshot, [15, 4])
        body_damage = sum(effect.amount for effect in result.proposals[0].effects
                          if type(effect) is DamageEffect
                          and effect.target_id == self.b.id
                          and effect.component == 'body')
        self.assertEqual(body_damage, 6)  # floor(4 * 1.5), native Dagger damage die

    def test_two_handed_strike_refuses_an_occupied_second_hand(self):
        self.a.size_category = 'medium'
        action = MeleeStrike(self.enc, self.a.id, self.b.id, self.w1,
                             motion='thrust', reach=2, two_handed=True)
        with self.assertRaisesRegex(ValueError, 'other hand free or a buckler'):
            self.enc.prepare_action(action)

    def test_shield_bash_uses_equipped_shield_native_motion_and_offhand_penalty(self):
        from weapon import WeaponInstance
        shield_id = self.world.make_weapon('Medium shield', 'Authored bash shield')
        shield = self.world.get_object_by_id(shield_id)
        self.a.possessions.append(shield_id)
        self.a.weapons.append(shield_id)
        shield.parent_container_id = self.a.id
        self.a.current.body_parts['left hand'] = shield_id
        self.a.current.tags['universe.native_dominant_hand'] = 'right hand'
        self.assertIs(type(shield), WeaponInstance)
        action = MeleeStrike(self.enc, self.a.id, self.b.id, shield_id,
                             motion='swing', reach=2, shield_bash=True)
        self.schedule(action)
        snapshot = self.snapshot(math.ceil(action.end_time))
        self.assertTrue(snapshot.actions[action.id].data['shield_bash'])
        self.assertEqual(snapshot.actions[action.id].data['shield_hand'], 'left hand')
        self.assertEqual(snapshot.entity(self.a.id).data['dominant_hand'], 'right hand')
        result = self.scripted(snapshot, [10])
        self.assertEqual(result.proposals[0].outcome, 'miss')  # -3 off-hand Dexterity adjustment

    def test_tower_shield_bash_is_refused_natively(self):
        shield_id = self.world.make_weapon('Tower shield', 'Authored tower shield')
        shield = self.world.get_object_by_id(shield_id)
        self.a.possessions.append(shield_id)
        self.a.weapons.append(shield_id)
        shield.parent_container_id = self.a.id
        self.a.current.body_parts['left hand'] = shield_id
        self.a.current.tags['universe.native_dominant_hand'] = 'right hand'
        action = MeleeStrike(self.enc, self.a.id, self.b.id, shield_id,
                             motion='swing', reach=2, shield_bash=True)
        with self.assertRaisesRegex(ValueError, 'tower shields cannot be used'):
            self.enc.prepare_action(action)

    def test_forearm_buckler_preserves_hand_and_applies_same_hand_attack_penalty(self):
        from weapon import author_forearm_buckler_attachment
        buckler_id = self.world.make_weapon('Buckler', 'Authored forearm buckler')
        buckler = self.world.get_object_by_id(buckler_id)
        self.a.possessions.append(buckler_id)
        self.a.weapons.append(buckler_id)
        buckler.parent_container_id = self.a.id
        author_forearm_buckler_attachment(buckler, self.a.id, 'right')
        self.assertEqual(self.a.current.body_parts['right hand'], self.w1)
        self.assertEqual(self.a.shielded_with(self.world)['right forearm'], buckler_id)
        action = self.strike()
        self.schedule(action)
        snapshot = self.snapshot(math.ceil(action.end_time))
        actor_view = snapshot.entity(self.a.id)
        self.assertEqual(actor_view.data['buckler_arms'], ('right',))
        self.assertIn(buckler_id, actor_view.data['shields'])
        result = self.scripted(snapshot, [10])
        self.assertEqual(result.proposals[0].outcome, 'miss')

    def test_forearm_buckler_can_make_its_native_shield_bash(self):
        from weapon import author_forearm_buckler_attachment
        buckler_id = self.world.make_weapon('Spiked buckler', 'Authored attached bash buckler')
        buckler = self.world.get_object_by_id(buckler_id)
        self.a.possessions.append(buckler_id)
        self.a.weapons.append(buckler_id)
        buckler.parent_container_id = self.a.id
        author_forearm_buckler_attachment(buckler, self.a.id, 'left')
        self.a.current.tags['universe.native_dominant_hand'] = 'right hand'
        action = MeleeStrike(self.enc, self.a.id, self.b.id, buckler_id,
                             motion='swing', reach=2, shield_bash=True)
        self.schedule(action)
        snapshot = self.snapshot(math.ceil(action.end_time))
        self.assertEqual(action.shield_hand, 'left hand')
        self.assertIn(buckler_id, snapshot.entity(self.a.id).data['shields'])
        result = self.scripted(snapshot, [10])
        self.assertEqual(result.proposals[0].outcome, 'miss')

    def test_native_one_second_touch_uses_opposed_attack_totals_without_damage(self):
        self.b.set_position(CartesianPosition(.2, 0, 0))
        self.enc.enable_transactional_progression(quiescent=True)
        action = Action(self.world, 0, 1, 'touch', self.a.id, self.b.id, None)
        action.end_time = 1
        self.enc.schedule_action(action)
        iterator = iter([15, 10])
        def roll(ctx, dice):
            value = next(iterator)
            ctx.trace.append(RandomDraw(ctx.action_id, dice, int(dice[2:].split('+')[0]), value))
            return value
        with patch.object(_ProvisionalRandom, 'roll', roll):
            self.enc.step(1)
        committed = self.enc.inspect_committed(1).action(action.id)
        self.assertEqual((committed.facts.outcome, committed.facts.target_ids),
                         ('touched', (self.b.id,)))
        self.assertFalse(committed.facts.effects)
        self.assertEqual(committed.facts.metadata, (('distance', .2),))

    def test_willing_touch_during_another_action_uses_dex_check_without_multiple_action(self):
        self.b.set_position(CartesianPosition(.2, 0, 0))
        target_id = self.world.make_being('Human', 'Willing recipient')
        target = self.world.get_object_by_id(target_id)
        target.set_position(CartesianPosition(.25, .1, 0))
        target.set_hit_points(100)
        self.enc.add_being(target.id)
        self.enc.mark_aware(self.a.id, target.id)
        self.enc.enable_transactional_progression(quiescent=True)

        other = Action(self.world, 0, 1, 'touch', self.a.id, self.b.id, None)
        willing = Action(self.world, 0, 1, 'touch', self.a.id, target.id, None)
        willing.touch_willing = True
        self.enc.schedule_action(other)
        self.enc.schedule_action(willing)
        self.assertEqual(self.enc.get_being(self.a.id).get_skill_level('multi-action') or 0, 0)

        values = {other.id: iter((15, 1)), willing.id: iter((1, 1, 1))}
        willing_draws = []
        def roll(context, dice):
            value = next(values[context.action_id])
            if context.action_id == willing.id:
                willing_draws.append(dice)
            context.trace.append(RandomDraw(context.action_id, dice,
                int(dice[2:].split('+')[0]), value))
            return value
        with patch.object(_ProvisionalRandom, 'roll', roll):
            self.enc.step(1)
        result = self.enc.inspect_committed(1)
        self.assertEqual(result.action(other.id).facts.outcome, 'touched')
        self.assertEqual(result.action(willing.id).facts.outcome, 'touched')
        self.assertEqual(willing_draws, ['1d6'] * 3)

    def test_willing_touch_uses_four_dice_when_actor_and_recipient_are_moving(self):
        self.a.set_position(CartesianPosition(.2, 0, 0))
        self.b.set_position(CartesianPosition(.25, 0, 0))
        self.enc.enable_transactional_progression(quiescent=True)
        actor_run = RunAction(self.world, self.a.id, 0, 2, 3, experience=0)
        target_run = RunAction(self.world, self.b.id, 0, 2, 3, experience=0)
        willing = Action(self.world, 0, 1, 'touch', self.a.id, self.b.id, None)
        willing.touch_willing = True
        self.enc.schedule_choice((actor_run, target_run, willing))
        values = iter((1, 1, 1, 1))
        willing_draws = []
        def roll(context, dice):
            value = next(values)
            if context.action_id == willing.id:
                willing_draws.append(dice)
            context.trace.append(RandomDraw(context.action_id, dice,
                int(dice[2:].split('+')[0]), value))
            return value
        with patch.object(_ProvisionalRandom, 'roll', roll):
            self.enc.step(1)
        result = self.enc.inspect_committed(1)
        self.assertEqual(result.action(willing.id).facts.outcome, 'touched')
        self.assertEqual(willing_draws, ['1d6'] * 4)

        self.assertEqual(self.enc.time, 1)

    def test_paralysis_precludes_willing_touch_without_a_random_draw(self):
        self.b.set_position(CartesianPosition(.2, 0, 0))
        self.a.current.states.states['paralyzed'] = True
        self.enc.enable_transactional_progression(quiescent=True)
        willing = Action(self.world, 0, 1, 'touch', self.a.id, self.b.id, None)
        willing.touch_willing = True
        self.enc.schedule_action(willing)
        with patch.object(_ProvisionalRandom, 'roll', side_effect=AssertionError('paralyzed actor must not roll')):
            self.enc.step(1)
        result = self.enc.inspect_committed(1)
        self.assertEqual(result.action(willing.id).facts.outcome, 'unable_to_act')

    def test_touch_uses_one_yard_hex_occupancy_without_requiring_facing(self):
        from arena_hex_map import ArenaHexLayout,HexAddress,encounter_map_descriptor
        layout=ArenaHexLayout.rectangle(4,4)
        self.enc.map=encounter_map_descriptor(layout)
        center=layout.center_position(HexAddress(1,1))
        self.a.set_position(CartesianPosition(center.x-.1,center.y,0))
        self.b.set_position(CartesianPosition(center.x+.1,center.y,0))
        self.a.hex_facing=0
        self.enc.enable_transactional_progression(quiescent=True)
        action=Action(self.world,0,1,'touch',self.a.id,self.b.id,None);action.end_time=1
        self.enc.schedule_action(action)
        iterator=iter([15,1])
        def roll(ctx,dice):
            value=next(iterator);ctx.trace.append(RandomDraw(ctx.action_id,dice,
                int(dice[2:].split('+')[0]),value));return value
        with patch.object(_ProvisionalRandom,'roll',roll):self.enc.step(1)
        facts=self.enc.inspect_committed(1).action(action.id).facts
        self.assertEqual(facts.outcome,'touched')
        self.assertAlmostEqual(facts.metadata[0][1],.2)

    def test_native_touch_grab_hold_break_grapple_and_escape_use_separate_receipt_state(self):
        from physical_contact import active_contact_state
        self.a.set_position(CartesianPosition(0,0,0))
        self.b.set_position(CartesianPosition(.2,0,0))
        self.a.current.body_parts['left hand'] = None
        self.a.current.body_parts['right hand'] = None
        self.a.current.skills.skills['improved grapple'] = 3
        self.b.current.skills.skills['improved grapple'] = 0
        self.a.set_posture('standing'); self.b.set_posture('standing')
        self.a.size_category = self.b.size_category = 'medium'
        self.b.current.skills.skills['escape artist'] = 12
        self.b.set_ability('strength',18)
        self.enc.enable_transactional_progression(quiescent=True)

        def resolve(action, duration, rolls):
            action.end_time = action.start_time + duration
            self.enc.schedule_action(action)
            values = iter(rolls)
            maintenance_draw = 0
            def scripted(ctx, dice):
                nonlocal maintenance_draw
                # Automatic maintenance may resolve beside a six-second
                # control Action. Script its opposed roles deterministically
                # without changing the Action under test.
                if ctx.action_id == action.id:
                    value = next(values)
                else:
                    value = 6 if maintenance_draw % 6 < 3 else 1
                    maintenance_draw += 1
                ctx.trace.append(RandomDraw(ctx.action_id,dice,
                    int(dice[2:].split('+')[0]),value))
                return value
            with patch.object(_ProvisionalRandom,'roll',scripted):
                self.enc.step(duration)
            return self.enc.inspect_committed(self.enc.last_processed_boundary).action(action.id)

        touch1 = Action(self.world,0,1,'touch',self.a.id,self.b.id,None)
        self.assertEqual(resolve(touch1,1,[15,1]).facts.outcome,'touched')
        grab1 = Action(self.world,1,2,'grab',self.a.id,self.b.id,None)
        grab1.touch_action_id=touch1.id;grab1.grab_hand='left hand'
        self.assertEqual(resolve(grab1,1,[6,6,6,1,1,1]).facts.outcome,'success')
        self.assertEqual(tuple(row[0] for row in active_contact_state(self.enc)[0]),(grab1.id,))
        self.enc.step(5)  # The individual six-second maintenance boundary is second 8.
        self.assertEqual(self.enc.time,7)
        # The due check is automatic and does not consume an Action. The
        # holder can resolve an ordinary Touch at the same boundary.
        concurrent_touch=Action(self.world,7,8,'touch',self.a.id,self.b.id,None)
        self.enc.schedule_action(concurrent_touch)
        hold_rolls=iter([6,6,6,1,1,1])
        touch_rolls=iter([15,1])
        def hold_roll(ctx,dice):
            if ctx.action_id==concurrent_touch.id:
                value=next(touch_rolls)
            else:
                value=next(hold_rolls)
            ctx.trace.append(RandomDraw(ctx.action_id,dice,
                int(dice[2:].split('+')[0]),value))
            return value
        with patch.object(_ProvisionalRandom,'roll',hold_roll):
            self.enc.step(1)
        hold = next(self.world.get_event_by_id(action_id)
                    for action_id in self.enc.finished_action_list
                    if getattr(self.world.get_event_by_id(action_id),'event_type',None)=='hold')
        self.assertEqual(self.enc.inspect_committed(8).action(concurrent_touch.id).facts.outcome,'touched')
        self.assertEqual(self.enc.inspect_committed(8).action(hold.id).facts.outcome,'success')
        self.assertEqual(active_contact_state(self.enc)[0][0][5],14)
        break_hold = Action(self.world,8,9,'break hold',self.b.id,self.a.id,None)
        break_hold.grip_id=grab1.id
        self.assertEqual(resolve(break_hold,1,[6,6,6,1,1,1]).facts.outcome,'success')
        self.assertEqual(active_contact_state(self.enc)[0],())

        touch2 = Action(self.world,9,10,'touch',self.a.id,self.b.id,None)
        self.assertEqual(resolve(touch2,1,[15,1]).facts.outcome,'touched')
        grab2 = Action(self.world,10,11,'grab',self.a.id,self.b.id,None)
        grab2.touch_action_id=touch2.id;grab2.grab_hand='right hand'
        self.assertEqual(resolve(grab2,1,[6,6,6,1,1,1]).facts.outcome,'success')
        grapple = Action(self.world,11,17,'grapple',self.a.id,self.b.id,None)
        grapple.grip_id=grab2.id
        self.assertEqual(resolve(grapple,6,[6,6,6,1,1,1]).facts.outcome,'success')
        controls = active_contact_state(self.enc)[1]
        self.assertEqual(tuple(row[0] for row in controls),(grapple.id,))
        # The initial Grapple check substitutes for second-17 maintenance of
        # the same prerequisite grip; it neither creates a second grip nor
        # merges physical Hold and control identities.
        self.assertEqual(len(active_contact_state(self.enc)[0]),1)
        takedown = Action(self.world,17,23,'takedown',self.a.id,self.b.id,None)
        takedown.grapple_id=grapple.id; takedown.grapple_position='prone'
        self.assertEqual(resolve(takedown,6,[6,6,6,1,1,1]).facts.outcome,'success')
        self.assertEqual(self.b.get_posture(),'lying')
        self.assertEqual(active_contact_state(self.enc)[1][0][6], 'advantaged_takedown_top')
        pin = Action(self.world,23,29,'pin',self.a.id,self.b.id,None)
        pin.grapple_id=grapple.id; pin.grapple_position='pin_bottom'
        self.assertEqual(resolve(pin,6,[6,6,6,1,1,1]).facts.outcome,'success')
        self.assertEqual(active_contact_state(self.enc)[1][0][6], 'pin_bottom')
        reverse = Action(self.world,29,35,'reverse',self.a.id,self.b.id,None)
        reverse.grapple_id=grapple.id
        self.assertEqual(resolve(reverse,6,[6,6,6,1,1,1]).facts.outcome,'success')
        self.assertEqual(active_contact_state(self.enc)[1][0][6], 'pin_top')
        escape = Action(self.world,35,41,'grapple escape',self.b.id,self.a.id,None)
        escape.grapple_id=grapple.id
        self.assertEqual(resolve(escape,6,[6,6,6,1,1,1]).facts.outcome,'success')
        self.assertEqual(active_contact_state(self.enc)[1][0][6], 'advantaged_takedown_top')
        escape = Action(self.world,41,47,'grapple escape',self.b.id,self.a.id,None)
        escape.grapple_id=grapple.id
        self.assertEqual(resolve(escape,6,[6,6,6,1,1,1]).facts.outcome,'success')
        self.assertEqual(active_contact_state(self.enc)[1][0][6], 'standing')
        escape = Action(self.world,47,53,'grapple escape',self.b.id,self.a.id,None)
        escape.grapple_id=grapple.id
        self.assertEqual(resolve(escape,6,[6,6,6,1,1,1]).facts.outcome,'success')
        self.assertEqual(active_contact_state(self.enc)[1],())
        self.assertEqual(tuple(row[0] for row in active_contact_state(self.enc)[0]),(grab2.id,))

        # A second independent attacker is admitted under the adopted size
        # cap and receives the +2 held-opponent bonus from the first holder.
        c = self.world.get_object_by_id(self.world.make_being('Human','C'))
        c.set_position(CartesianPosition(.4,0,0));c.set_geometry(Sphere(.25))
        c.set_hit_points(100);c.size_category='medium';c.set_posture('standing')
        c.current.skills.skills['improved grapple']=0
        c.set_ability('strength',10);self.b.set_ability('strength',10)
        self.enc.add_being(c.id)
        self.enc.mark_aware(c.id,self.b.id);self.enc.mark_aware(self.b.id,c.id)
        touch3=Action(self.world,53,54,'touch',c.id,self.b.id,None)
        self.assertEqual(resolve(touch3,1,[15,1]).facts.outcome,'touched')
        grab3=Action(self.world,54,55,'grab',c.id,self.b.id,None)
        grab3.touch_action_id=touch3.id;grab3.grab_hand='left hand'
        self.assertEqual(resolve(grab3,1,[1,1,1,1,1,1]).facts.outcome,'success')
        self.assertEqual({row[1] for row in active_contact_state(self.enc)[0]},
                         {self.a.id,c.id})

        # Four medium attackers are the adopted maximum against a medium
        # target; the fifth is refused before drawing any random numbers.
        extra=[]
        for name, start, rolls in (('D',55,[6,6,6,1,1,1]),
                                   ('E',57,[6,6,6,1,1,1])):
            being=self.world.get_object_by_id(self.world.make_being('Human',name))
            being.set_position(CartesianPosition(.5,0,0));being.set_geometry(Sphere(.25))
            being.set_hit_points(100);being.size_category='medium';being.set_posture('standing')
            being.current.skills.skills['improved grapple']=0
            being.set_ability('strength',10);self.enc.add_being(being.id)
            self.enc.mark_aware(being.id,self.b.id);self.enc.mark_aware(self.b.id,being.id)
            touch=Action(self.world,start,start+1,'touch',being.id,self.b.id,None)
            self.assertEqual(resolve(touch,1,[15,1]).facts.outcome,'touched')
            grab=Action(self.world,start+1,start+2,'grab',being.id,self.b.id,None)
            grab.touch_action_id=touch.id;grab.grab_hand='left hand'
            self.assertEqual(resolve(grab,1,rolls).facts.outcome,'success')
            extra.append(being)
        self.assertEqual(len(active_contact_state(self.enc)[0]),4)

        fifth=self.world.get_object_by_id(self.world.make_being('Human','Fifth'))
        fifth.set_position(CartesianPosition(.6,0,0));fifth.set_geometry(Sphere(.25))
        fifth.set_hit_points(100);fifth.size_category='medium';fifth.set_posture('standing')
        fifth.current.skills.skills['improved grapple']=0
        fifth.set_ability('strength',10);self.enc.add_being(fifth.id)
        self.enc.mark_aware(fifth.id,self.b.id);self.enc.mark_aware(self.b.id,fifth.id)
        touch=Action(self.world,59,60,'touch',fifth.id,self.b.id,None)
        self.assertEqual(resolve(touch,1,[15,1]).facts.outcome,'touched')
        overflow=Action(self.world,60,61,'grab',fifth.id,self.b.id,None)
        overflow.touch_action_id=touch.id;overflow.grab_hand='left hand'
        self.assertEqual(resolve(overflow,1,[]).facts.outcome,'capacity_exceeded')
        self.assertEqual(len(active_contact_state(self.enc)[0]),4)

    def test_automatic_hold_maintenance_tie_releases_only_that_grip(self):
        from physical_contact import active_contact_state
        self.a.set_position(CartesianPosition(0,0,0));self.b.set_position(CartesianPosition(.2,0,0))
        for being in (self.a,self.b):
            being.current.skills.skills['improved grapple']=0
            being.set_ability('strength',10)
        self.a.current.body_parts['left hand']=None
        self.a.current.body_parts['right hand']=None
        self.enc.enable_transactional_progression(quiescent=True)
        touch=Action(self.world,0,1,'touch',self.a.id,self.b.id,None)
        self.enc.schedule_action(touch)
        with patch.object(_ProvisionalRandom,'roll',side_effect=[15,1]):
            self.enc.step(1)
        grab=Action(self.world,1,2,'grab',self.a.id,self.b.id,None)
        grab.touch_action_id=touch.id;grab.grab_hand='left hand'
        self.enc.schedule_action(grab)
        with patch.object(_ProvisionalRandom,'roll',side_effect=[6,6,6,1,1,1]):
            self.enc.step(1)
        self.assertEqual(len(active_contact_state(self.enc)[0]),1)
        with patch.object(_ProvisionalRandom,'roll',return_value=2):
            self.enc.step(6)
        self.assertEqual(active_contact_state(self.enc)[0],())
        hold=next(self.world.get_event_by_id(identity) for identity in self.enc.finished_action_list
                  if getattr(self.world.get_event_by_id(identity),'event_type',None)=='hold')
        self.assertEqual(self.enc.inspect_committed(8).action(hold.id).facts.outcome,'failed')

    def test_declared_multiple_grapple_and_break_hold_do_not_interrupt_control(self):
        """Adopted Grapple + Break hold runs as one priority-bearing Action set."""
        from physical_contact import active_contact_state
        self.a.set_position(CartesianPosition(0, 0, 0))
        self.b.set_position(CartesianPosition(.2, 0, 0))
        for being in (self.a, self.b):
            being.current.body_parts["left hand"] = None
            being.current.body_parts["right hand"] = None
            being.current.skills.skills["improved grapple"] = 3
            being.set_ability("strength", 10)
            being.size_category = "medium"
            being.set_posture("standing")
        self.a.set_skill_level(self.world.get_skill_dictionary(), "multi-action", 1)
        self.enc.enable_transactional_progression(quiescent=True)

        touch_a = Action(self.world, 0, 1, "touch", self.a.id, self.b.id, None)
        touch_b = Action(self.world, 0, 1, "touch", self.b.id, self.a.id, None)
        self.enc.schedule_choice((touch_a, touch_b))
        touch_values = {touch_a.id: iter((15, 1)), touch_b.id: iter((15, 1))}
        def touch_roll(ctx, dice):
            value = next(touch_values[ctx.action_id])
            ctx.trace.append(RandomDraw(ctx.action_id, dice,
                int(dice[2:].split("+")[0]), value))
            return value
        with patch.object(_ProvisionalRandom, "roll", touch_roll):
            self.enc.step(1)

        grab_a = Action(self.world, 1, 2, "grab", self.a.id, self.b.id, None)
        grab_a.touch_action_id = touch_a.id; grab_a.grab_hand = "left hand"
        grab_b = Action(self.world, 1, 2, "grab", self.b.id, self.a.id, None)
        grab_b.touch_action_id = touch_b.id; grab_b.grab_hand = "left hand"
        self.enc.schedule_choice((grab_a, grab_b))
        grab_values = {grab_a.id: iter((6, 6, 6, 1, 1, 1)),
                       grab_b.id: iter((6, 6, 6, 1, 1, 1))}
        def grab_roll(ctx, dice):
            value = next(grab_values[ctx.action_id])
            ctx.trace.append(RandomDraw(ctx.action_id, dice,
                int(dice[2:].split("+")[0]), value))
            return value
        with patch.object(_ProvisionalRandom, "roll", grab_roll):
            self.enc.step(1)
        grips = {row[1]: row[0] for row in active_contact_state(self.enc)[0]}
        self.assertEqual(set(grips), {self.a.id, self.b.id})

        grapple = Action(self.world, 2, 8, "grapple", self.a.id, self.b.id, None)
        grapple.end_time = 8; grapple.grip_id = grips[self.a.id]
        break_hold = Action(self.world, 2, 3, "break hold", self.a.id, self.b.id, None)
        break_hold.end_time = 3; break_hold.grip_id = grips[self.b.id]
        choice = self.enc.schedule_choice((
            ChoiceMember("continue-grapple", grapple, priority_penalty=0),
            ChoiceMember("break-hold", break_hold, priority_penalty=3)))
        accepted = self.enc._choice_book._choices[choice.id]
        self.assertEqual(tuple(member.priority_penalty for member in accepted.members), (0, 3))

        break_values = iter((6, 6, 6, 1, 1, 1))
        def break_roll(ctx, dice):
            value = next(break_values)
            ctx.trace.append(RandomDraw(ctx.action_id, dice,
                int(dice[2:].split("+")[0]), value))
            return value
        with patch.object(_ProvisionalRandom, "roll", break_roll):
            self.enc.step(1)
        self.assertEqual(self.enc.inspect_committed(3).action(break_hold.id).facts.outcome, "success")
        self.assertIn(grapple.id, self.enc.pending_action_list)
        self.assertEqual(tuple(row[1:3] for row in active_contact_state(self.enc)[0]),
                         ((self.a.id, self.b.id),))
        self.enc.abort_multiple_action(self.enc._choice_book.view(choice.id))
        self.assertNotIn(grapple.id, self.enc.pending_action_list)
        self.assertIn(grapple.id, self.enc.cancelled_action_list)
        self.assertEqual(len(active_contact_state(self.enc)[1]), 0)

    def test_staggered_automatic_maintenance_keeps_each_grip_independent(self):
        from physical_contact import active_contact_state
        self.a.set_position(CartesianPosition(0,0,0));self.b.set_position(CartesianPosition(.2,0,0))
        for being in (self.a,self.b):
            being.current.skills.skills['improved grapple']=0
            being.set_ability('strength',10)
        self.a.current.body_parts['left hand']=None
        self.a.current.body_parts['right hand']=None
        self.enc.enable_transactional_progression(quiescent=True)

        def resolve(action, rolls):
            self.enc.schedule_action(action)
            values=iter(rolls)
            def scripted(ctx,dice):
                value=next(values)
                ctx.trace.append(RandomDraw(ctx.action_id,dice,
                    int(dice[2:].split('+')[0]),value))
                return value
            with patch.object(_ProvisionalRandom,'roll',scripted):
                self.enc.step(action.end_time-self.enc.time)
            return self.enc.inspect_committed(action.end_time).action(action.id)

        touch1=Action(self.world,0,1,'touch',self.a.id,self.b.id,None)
        self.assertEqual(resolve(touch1,[15,1]).facts.outcome,'touched')
        grip1=Action(self.world,1,2,'grab',self.a.id,self.b.id,None)
        grip1.touch_action_id=touch1.id;grip1.grab_hand='left hand'
        self.assertEqual(resolve(grip1,[6,6,6,1,1,1]).facts.outcome,'success')
        touch2=Action(self.world,2,3,'touch',self.a.id,self.b.id,None)
        self.assertEqual(resolve(touch2,[15,1]).facts.outcome,'touched')
        grip2=Action(self.world,3,4,'grab',self.a.id,self.b.id,None)
        grip2.touch_action_id=touch2.id;grip2.grab_hand='right hand'
        self.assertEqual(resolve(grip2,[6,6,6,1,1,1]).facts.outcome,'success')
        self.assertEqual({row[0] for row in active_contact_state(self.enc)[0]},
                         {grip1.id,grip2.id})

        # The first Grip's check is due at 8. It loses and releases only that
        # hand; the second Grip's independently scheduled check is due at 10.
        with patch.object(_ProvisionalRandom,'roll',side_effect=[1,1,1,6,6,6]):
            self.enc.step(4)
        self.assertEqual({row[0] for row in active_contact_state(self.enc)[0]},
                         {grip2.id})
        first_hold=next(self.world.get_event_by_id(identity)
                        for identity in self.enc.finished_action_list
                        if getattr(self.world.get_event_by_id(identity),'event_type',None)=='hold')
        self.assertEqual(self.enc.inspect_committed(8).action(first_hold.id).facts.outcome,'failed')

        with patch.object(_ProvisionalRandom,'roll',side_effect=[6,6,6,1,1,1]):
            self.enc.step(2)
        self.assertEqual({row[0] for row in active_contact_state(self.enc)[0]},
                         {grip2.id})
        second_hold=next(self.world.get_event_by_id(identity)
                         for identity in self.enc.finished_action_list
                         if getattr(self.world.get_event_by_id(identity),'event_type',None)=='hold'
                         and self.world.get_event_by_id(identity).start_time==9)
        self.assertEqual(self.enc.inspect_committed(10).action(second_hold.id).facts.outcome,'success')

    def test_voluntary_release_releases_only_the_selected_grip_without_rng(self):
        from physical_contact import active_contact_state
        self.a.set_position(CartesianPosition(0,0,0)); self.b.set_position(CartesianPosition(.2,0,0))
        self.a.current.body_parts['left hand'] = None
        self.a.current.body_parts['right hand'] = None
        self.a.current.skills.skills['improved grapple'] = 100
        self.b.current.skills.skills['improved grapple'] = 0
        self.a.set_posture('standing'); self.b.set_posture('standing')
        self.enc.enable_transactional_progression(quiescent=True)

        def resolve(action, duration, rolls=()):
            action.end_time = action.start_time + duration
            self.enc.schedule_action(action)
            values = iter(rolls)
            def scripted(ctx, dice):
                value = next(values)
                ctx.trace.append(RandomDraw(ctx.action_id,dice,
                    int(dice[2:].split('+')[0]),value))
                return value
            with patch.object(_ProvisionalRandom,'roll',scripted):
                self.enc.step(duration)
            return self.enc.inspect_committed(self.enc.last_processed_boundary).action(action.id)

        touch1 = Action(self.world,0,1,'touch',self.a.id,self.b.id,None)
        self.assertEqual(resolve(touch1,1,[15,1]).facts.outcome,'touched')
        grip1 = Action(self.world,1,2,'grab',self.a.id,self.b.id,None)
        grip1.touch_action_id=touch1.id; grip1.grab_hand='left hand'
        self.assertEqual(resolve(grip1,1,[6,6,6,1,1,1]).facts.outcome,'success')
        touch2 = Action(self.world,2,3,'touch',self.a.id,self.b.id,None)
        self.assertEqual(resolve(touch2,1,[15,1]).facts.outcome,'touched')
        grip2 = Action(self.world,3,4,'grab',self.a.id,self.b.id,None)
        grip2.touch_action_id=touch2.id; grip2.grab_hand='right hand'
        self.assertEqual(resolve(grip2,1,[6,6,6,1,1,1]).facts.outcome,'success')

        release = Action(self.world,4,5,'release grip',self.a.id,self.b.id,None)
        release.grip_id=grip1.id
        result = resolve(release,1)
        self.assertEqual(result.facts.outcome,'success')
        self.assertEqual(result.effects[0].effect.operation,'release')
        self.assertEqual(tuple(row[0] for row in active_contact_state(self.enc)[0]),(grip2.id,))

    def test_incompatible_pin_and_escape_reroll_as_one_no_time_conflict_group(self):
        self.a.set_position(CartesianPosition(0,0,0));self.b.set_position(CartesianPosition(.2,0,0))
        self.a.current.body_parts['left hand']=None
        self.a.current.skills.skills['improved grapple']=3
        self.b.current.skills.skills['improved grapple']=3
        self.a.size_category=self.b.size_category='medium'
        self.a.set_posture('standing');self.b.set_posture('standing')
        self.enc.enable_transactional_progression(quiescent=True)
        def commit(action,values):
            self.enc.schedule_action(action)
            supplied=iter(values)
            maintenance_draw=0
            def roll(ctx,dice):
                nonlocal maintenance_draw
                if ctx.action_id==action.id:
                    value=next(supplied)
                else:
                    value=6 if maintenance_draw%6<3 else 1
                    maintenance_draw+=1
                ctx.trace.append(RandomDraw(ctx.action_id,dice,
                    int(dice[2:].split('+')[0]),value))
                return value
            with patch.object(_ProvisionalRandom,'roll',roll):
                self.enc.step(action.end_time-action.start_time)
        touch=Action(self.world,0,1,'touch',self.a.id,self.b.id,None)
        commit(touch,[6,1])
        grip=Action(self.world,1,2,'grab',self.a.id,self.b.id,None)
        grip.touch_action_id=touch.id;grip.grab_hand='left hand'
        commit(grip,[6,6,6,1,1,1])
        grapple=Action(self.world,2,8,'grapple',self.a.id,self.b.id,None)
        grapple.end_time=8;grapple.grip_id=grip.id
        commit(grapple,[6,6,6,1,1,1])
        takedown=Action(self.world,8,14,'takedown',self.a.id,self.b.id,None)
        takedown.end_time=14;takedown.grapple_id=grapple.id;takedown.grapple_position='prone'
        commit(takedown,[6,6,6,1,1,1])

        pin=Action(self.world,14,20,'pin',self.a.id,self.b.id,None)
        pin.end_time=20;pin.grapple_id=grapple.id;pin.grapple_position='pin_top'
        escape=Action(self.world,14,20,'grapple escape',self.b.id,self.a.id,None)
        escape.end_time=20;escape.grapple_id=grapple.id
        self.enc.schedule_action(pin);self.enc.schedule_action(escape)
        self.enc.step(1)
        snapshot=self.snapshot(20)
        rounds={pin.id:[6]*3+[1]*3+[1]*3+[6]*3+[6]*3+[1]*3,
                 escape.id:[6]*3+[1]*3+[1]*3+[6]*3+[1]*3+[6]*3}
        def roll(ctx,dice):
            value=rounds[ctx.action_id].pop(0)
            ctx.trace.append(RandomDraw(ctx.action_id,dice,
                int(dice[2:].split('+')[0]),value))
            return value
        with patch.object(_ProvisionalRandom,'roll',roll):
            result=evaluate_snapshot(snapshot)
        outcomes={row.action_id:row.outcome for row in result.proposals}
        self.assertEqual(outcomes[pin.id],'success')
        self.assertEqual(outcomes[escape.id],'failed')
        self.assertEqual(len(result.trace),36)
        self.assertEqual(rounds,{pin.id:[],escape.id:[]})

    def test_outsider_low_miss_against_pinned_target_hits_pin_holder(self):
        from dataclasses import replace
        holder_id = self.world.make_being('Human', 'Pin holder')
        holder = self.world.get_object_by_id(holder_id)
        holder.set_position(CartesianPosition(1.8, 0, 0))
        holder.set_geometry(Sphere(.25)); holder.set_hit_points(100)
        self.enc.add_being(holder.id)
        self.enc.mark_aware(self.a.id, holder.id)
        self.enc.mark_aware(holder.id, self.a.id)
        self.a.set_position(CartesianPosition(0, 0, 0))
        self.b.set_position(CartesianPosition(1.5, 0, 0))
        self.a.set_posture('standing'); self.b.set_posture('lying')
        attack = MeleeStrike(self.enc, self.a.id, self.b.id, self.w1,
                             motion='thrust', reach=2)
        attack.end_time = 1
        self.enc.schedule_action(attack)
        snapshot = self.snapshot(1)
        snapshot = replace(snapshot, grapple_controls=(
            ('native-pin', holder.id, self.b.id, None, 0, 7, 'pin_top'),))
        result = self.scripted(snapshot, [2, 3])
        proposal = result.proposals[0]
        self.assertEqual(proposal.outcome, 'normal')
        damage = tuple(effect for effect in proposal.effects
                       if type(effect) is DamageEffect and effect.component == 'body')
        self.assertEqual(len(damage), 1)
        self.assertEqual(damage[0].target_id, holder.id)
        self.assertEqual(damage[0].amount, 3)

    def test_third_party_positive_hp_damage_releases_each_physical_grip_transactionally(self):
        from physical_contact import active_contact_state
        from spatial.state import CartesianPosition
        global_rng_state=random.getstate();self.addCleanup(random.setstate,global_rng_state)
        random.seed(7)
        self.a.set_position(CartesianPosition(0,0,0))
        self.b.set_position(CartesianPosition(.5,0,0))
        self.a.current.body_parts['left hand']=None
        self.a.current.body_parts['right hand']=None
        self.a.current.skills.skills['improved grapple']=100
        self.b.current.skills.skills['improved grapple']=0
        third_id=self.world.make_being('Human','Third-party striker')
        third=self.world.get_object_by_id(third_id)
        third.set_position(CartesianPosition(-.5,0,0));third.set_geometry(Sphere(.25));third.set_hit_points(100)
        third_weapon_id=self.world.make_weapon_for_being(third_id,'Dagger','Third-party Dagger')
        self.world.arm_being(third_id,third_weapon_id,'right hand')
        fourth_id=self.world.make_being('Human','Second held target')
        fourth=self.world.get_object_by_id(fourth_id)
        fourth.set_position(CartesianPosition(.5,.5,0));fourth.set_geometry(Sphere(.25));fourth.set_hit_points(100)
        fourth.current.skills.skills['improved grapple']=0
        self.enc.add_being(third_id);self.enc.add_being(fourth_id)
        for other in (self.a,self.b,third,fourth):
            for target in (self.a,self.b,third,fourth):
                if other is not target:self.enc.mark_aware(other.id,target.id)
        self.enc.enable_transactional_progression(quiescent=True)

        def resolve(action,duration,rolls):
            action.end_time=action.start_time+duration;self.enc.schedule_action(action)
            values=iter(rolls)
            def scripted(ctx,dice):
                value=next(values);ctx.trace.append(RandomDraw(ctx.action_id,dice,
                    int(dice[2:].split('+')[0]),value));return value
            with patch.object(_ProvisionalRandom,'roll',scripted):self.enc.step(duration)
            return self.enc.inspect_committed(self.enc.last_processed_boundary).action(action.id)

        touch_b=Action(self.world,0,1,'touch',self.a.id,self.b.id,None)
        self.assertEqual(resolve(touch_b,1,[15,1]).facts.outcome,'touched')
        grab_b=Action(self.world,1,2,'grab',self.a.id,self.b.id,None)
        grab_b.touch_action_id=touch_b.id;grab_b.grab_hand='left hand'
        self.assertEqual(resolve(grab_b,1,[6,6,6,1,1,1]).facts.outcome,'success')
        touch_d=Action(self.world,2,3,'touch',self.a.id,fourth.id,None)
        self.assertEqual(resolve(touch_d,1,[15,1]).facts.outcome,'touched')
        grab_d=Action(self.world,3,4,'grab',self.a.id,fourth.id,None)
        grab_d.touch_action_id=touch_d.id;grab_d.grab_hand='right hand'
        self.assertEqual(resolve(grab_d,1,[6,6,6,1,1,1]).facts.outcome,'success')
        self.assertEqual(len(active_contact_state(self.enc)[0]),2)
        self.a.set_hit_points(4)
        strike=MeleeStrike(self.enc,third.id,self.a.id,third_weapon_id,motion='thrust',reach=2)
        self.assertEqual(resolve(strike,1,[15,4]).facts.outcome,'normal')
        receipt=self.enc.inspect_committed(self.enc.last_processed_boundary).action(strike.id)
        releases=[effect for effect in receipt.facts.effects
                  if type(effect).__name__=='GrappleStateEffect'
                  and effect.operation=='release']
        self.assertEqual({effect.state_id for effect in releases},{grab_b.id,grab_d.id})
        self.assertEqual(len(active_contact_state(self.enc)[0]),0)

    def test_native_trip_uses_touch_identity_contest_and_commits_prone_posture(self):
        self.a.set_position(CartesianPosition(0,0,0)); self.b.set_position(CartesianPosition(.2,0,0))
        self.a.set_posture('standing'); self.b.set_posture('standing')
        self.a.size_category=self.b.size_category='medium'
        self.enc.enable_transactional_progression(quiescent=True)
        touch=Action(self.world,0,1,'touch',self.a.id,self.b.id,None)
        touch.end_time=1; self.enc.schedule_action(touch)
        values=iter([15,1])
        def roll(ctx,dice):
            value=next(values);ctx.trace.append(RandomDraw(ctx.action_id,dice,int(dice.split('d')[1]),value));return value
        with patch.object(_ProvisionalRandom,'roll',roll): self.enc.step(1)
        trip=Action(self.world,1,3,'trip',self.a.id,self.b.id,None)
        trip.trip_source_action_id=touch.id; trip.trip_defender_ability='DEX'; trip.end_time=3
        self.enc.schedule_action(trip)
        values=iter([6,6,6,1,1,1])
        with patch.object(_ProvisionalRandom,'roll',roll): self.enc.step(2)
        self.assertEqual(self.enc.inspect_committed(3).action(trip.id).facts.outcome,'success')
        self.assertEqual(self.b.get_posture(),'lying')

    def test_native_overrun_standing_same_hex_contest_commits_prone_without_displacement(self):
        self.a.set_position(CartesianPosition(0,0,0)); self.b.set_position(CartesianPosition(.2,0,0))
        self.a.set_posture('standing'); self.b.set_posture('standing')
        self.a.set_hex_facing(0)
        self.a.size_category=self.b.size_category='medium'
        self.enc.enable_transactional_progression(quiescent=True)
        overrun=Action(self.world,0,4,'overrun',self.a.id,self.b.id,None)
        self.assertEqual(overrun.end_time,4)
        self.enc.schedule_action(overrun)
        values=iter([6,6,6,1,1,1])
        def roll(ctx,dice):
            value=next(values)
            ctx.trace.append(RandomDraw(ctx.action_id,dice,int(dice.split('d')[1]),value))
            return value
        with patch.object(_ProvisionalRandom,'roll',roll): self.enc.step(4)
        self.assertEqual(self.enc.inspect_committed(4).action(overrun.id).facts.outcome,'success')
        self.assertEqual(self.b.get_posture(),'lying')
        self.assertEqual(self.a.get_position(),CartesianPosition(0,0,0))
        self.assertEqual(self.b.get_position(),CartesianPosition(.2,0,0))

    def test_native_overrun_tie_preserves_standing_posture(self):
        self.a.set_position(CartesianPosition(0,0,0)); self.b.set_position(CartesianPosition(.2,0,0))
        self.a.set_posture('standing'); self.b.set_posture('standing')
        self.a.set_hex_facing(0)
        self.a.size_category=self.b.size_category='medium'
        self.enc.enable_transactional_progression(quiescent=True)
        overrun=Action(self.world,0,4,'overrun',self.a.id,self.b.id,None)
        self.assertEqual(overrun.end_time,4)
        self.enc.schedule_action(overrun)
        values=iter([2,2,2,2,2,2])
        def roll(ctx,dice):
            value=next(values)
            ctx.trace.append(RandomDraw(ctx.action_id,dice,int(dice.split('d')[1]),value))
            return value
        with patch.object(_ProvisionalRandom,'roll',roll): self.enc.step(4)
        self.assertEqual(self.enc.inspect_committed(4).action(overrun.id).facts.outcome,'failed')
        self.assertEqual(self.b.get_posture(),'standing')

    def test_native_overrun_applies_stability_for_explicitly_represented_extra_legs(self):
        self.a.set_position(CartesianPosition(0,0,0)); self.b.set_position(CartesianPosition(.2,0,0))
        self.a.set_posture('standing'); self.b.set_posture('standing')
        self.a.set_hex_facing(0)
        self.a.size_category=self.b.size_category='medium'
        self.a.current.body_parts={name:None for name in
            ('front left leg','front right leg','rear left leg','rear right leg')}
        self.b.current.body_parts={'left leg':None,'right leg':None}
        self.enc.enable_transactional_progression(quiescent=True)
        overrun=Action(self.world,0,4,'overrun',self.a.id,self.b.id,None)
        self.enc.schedule_action(overrun)
        values=iter([2,2,2,2,2,2])
        def roll(ctx,dice):
            value=next(values)
            ctx.trace.append(RandomDraw(ctx.action_id,dice,int(dice.split('d')[1]),value))
            return value
        with patch.object(_ProvisionalRandom,'roll',roll): self.enc.step(4)
        result=self.enc.inspect_committed(4).action(overrun.id)
        self.assertEqual(result.facts.outcome,'success')
        self.assertEqual(self.b.get_posture(),'lying')

    def test_native_overrun_uses_advanced_equipped_shield_bonus(self):
        self.a.set_position(CartesianPosition(0,0,0)); self.b.set_position(CartesianPosition(.2,0,0))
        self.a.set_posture('standing'); self.b.set_posture('standing')
        self.a.set_hex_facing(0)
        self.a.size_category=self.b.size_category='medium'
        shield_id=self.world.make_weapon_for_being(self.a.id,'Small shield','Overrun shield')
        self.world.arm_being(self.a.id,shield_id,'shield hand')
        self.a.set_weapon_skill_level(self.world.get_weapon_dictionary(),'Small shield',2)
        self.enc.enable_transactional_progression(quiescent=True)
        overrun=Action(self.world,0,4,'overrun',self.a.id,self.b.id,shield_id)
        self.enc.schedule_action(overrun)
        values=iter([3,3,3,3,3,4])
        def roll(ctx,dice):
            value=next(values)
            ctx.trace.append(RandomDraw(ctx.action_id,dice,int(dice.split('d')[1]),value))
            return value
        with patch.object(_ProvisionalRandom,'roll',roll): self.enc.step(4)
        self.assertEqual(self.enc.inspect_committed(4).action(overrun.id).facts.outcome,'success')
        self.assertEqual(self.b.get_posture(),'lying')

    def test_native_overrun_and_bull_rush_are_rejected_for_a_bearing_tower_shield(self):
        self.a.set_position(CartesianPosition(0,0,0)); self.b.set_position(CartesianPosition(.2,0,0))
        self.a.set_posture('standing'); self.b.set_posture('standing')
        self.a.set_hex_facing(0)
        self.a.size_category=self.b.size_category='medium'
        shield_id=self.world.make_weapon_for_being(self.a.id,'Tower shield','Tower shield')
        self.world.arm_being(self.a.id,shield_id,'shield hand')
        self.enc.enable_transactional_progression(quiescent=True)
        overrun=Action(self.world,0,4,'overrun',self.a.id,self.b.id,None)
        with self.assertRaisesRegex(ValueError,'tower shield'):
            self.enc.prepare_action(overrun)
        rush=Action(self.world,0,1,'bull rush',self.a.id,self.b.id,None)
        with self.assertRaisesRegex(ValueError,'tower shield'):
            self.enc.prepare_action(rush)
        self.assertEqual(self.enc.pending_action_list,[])

    def test_native_bull_rush_records_success_pending_displacement_without_moving_target(self):
        self.a.set_position(CartesianPosition(0,0,0)); self.b.set_position(CartesianPosition(.2,0,0))
        self.a.set_hex_facing(0)
        self.a.size_category=self.b.size_category='medium'
        self.enc.enable_transactional_progression(quiescent=True)
        rush=Action(self.world,0,1,'bull rush',self.a.id,self.b.id,None)
        self.assertEqual(rush.end_time,1)
        self.enc.schedule_action(rush)
        before=(self.a.get_position(),self.b.get_position())
        values=iter([6,6,6,1,1,1])
        def roll(ctx,dice):
            value=next(values)
            ctx.trace.append(RandomDraw(ctx.action_id,dice,int(dice.split('d')[1]),value))
            return value
        with patch.object(_ProvisionalRandom,'roll',roll): self.enc.step(1)
        result=self.enc.inspect_committed(1).action(rush.id)
        self.assertEqual(result.facts.outcome,'success_pending_displacement')
        self.assertEqual((self.a.get_position(),self.b.get_position()),before)

    def test_explicitly_willing_bull_rush_skips_contest_draws_and_keeps_displacement_bounded(self):
        self.a.set_position(CartesianPosition(0,0,0)); self.b.set_position(CartesianPosition(.2,0,0))
        self.a.set_hex_facing(0)
        self.a.size_category=self.b.size_category='medium'
        self.enc.enable_transactional_progression(quiescent=True)
        rush=Action(self.world,0,1,'bull rush',self.a.id,self.b.id,None)
        rush.bull_rush_target_willing=True
        before=(self.a.get_position(),self.b.get_position())
        self.enc.schedule_action(rush)
        with patch.object(_ProvisionalRandom,'roll',side_effect=AssertionError(
                'an explicitly willing target must not enter the resistance contest')):
            self.enc.step(1)
        result=self.enc.inspect_committed(1).action(rush.id)
        self.assertEqual(result.facts.outcome,'success_pending_displacement')
        self.assertEqual((self.a.get_position(),self.b.get_position()),before)

    def test_native_yield_nullifies_same_boundary_bull_rush(self):
        self.a.set_position(CartesianPosition(0,0,0)); self.b.set_position(CartesianPosition(.8,0,0))
        self.a.set_hex_facing(0)
        self.a.size_category=self.b.size_category='medium'
        self.enc.enable_transactional_progression(quiescent=True)
        rush=Action(self.world,0,1,'bull rush',self.a.id,self.b.id,None)
        defense=MeleeDefense(self.enc,self.b.id,self.a.id,kind='yield',
                             target_action_id=rush.id)
        self.enc.schedule_choice((ChoiceMember('rush',rush),ChoiceMember('yield',defense)))
        self.enc.step(1,velocities={self.b.id:(0,.1,0)})
        result=self.enc.inspect_committed(1)
        self.assertEqual(result.action(defense.id).facts.outcome,'yielded')
        self.assertEqual(result.action(rush.id).facts.outcome,'yielded')
        self.assertGreater(self.b.get_position().y,0)

    def test_native_yield_does_not_nullify_bull_rush_without_opening_distance(self):
        self.a.set_position(CartesianPosition(0,0,0)); self.b.set_position(CartesianPosition(.8,0,0))
        self.a.set_hex_facing(0)
        self.a.size_category=self.b.size_category='medium'
        self.enc.enable_transactional_progression(quiescent=True)
        rush=Action(self.world,0,1,'bull rush',self.a.id,self.b.id,None)
        defense=MeleeDefense(self.enc,self.b.id,self.a.id,kind='yield',
                             target_action_id=rush.id)
        self.enc.schedule_choice((ChoiceMember('rush',rush),ChoiceMember('yield',defense)))
        values=iter([6,6,6,1,1,1])
        def roll(ctx,dice):
            value=next(values)
            ctx.trace.append(RandomDraw(ctx.action_id,dice,int(dice.split('d')[1]),value))
            return value
        with patch.object(_ProvisionalRandom,'roll',roll): self.enc.step(1)
        result=self.enc.inspect_committed(1)
        self.assertEqual(result.action(defense.id).facts.outcome,'no_space')
        self.assertEqual(result.action(rush.id).facts.outcome,'success_pending_displacement')

    def test_prepared_overrun_rechecks_target_position_at_completion_boundary(self):
        self.a.set_position(CartesianPosition(0,0,0)); self.b.set_position(CartesianPosition(.8,0,0))
        self.a.set_posture('standing'); self.b.set_posture('standing')
        self.a.set_hex_facing(0)
        self.a.size_category=self.b.size_category='medium'
        self.enc.enable_transactional_progression(quiescent=True)
        overrun=Action(self.world,0,4,'overrun',self.a.id,self.b.id,None)
        self.enc.schedule_action(overrun)
        self.enc.step(1,velocities={self.b.id:(.2,0,0)})
        moved=self.b.get_position()
        self.assertEqual(moved,CartesianPosition(1.0,0,0))
        self.enc.step(3)
        result=self.enc.inspect_committed(4).action(overrun.id)
        self.assertEqual(result.facts.outcome,'out_of_reach')
        self.assertEqual(self.b.get_position(),moved)

    def test_charge_uses_relative_speed_at_movement_culmination_for_bonus_damage(self):
        self.a.set_position(CartesianPosition(0,0,0)); self.b.set_position(CartesianPosition(13.0,0,0))
        self.a.set_hex_facing(0)
        self.a.set_weapon_skill_level(self.world.get_weapon_dictionary(),'Dagger',100)
        self.enc.enable_transactional_progression(quiescent=True)
        charge=MeleeStrike(self.enc,self.a.id,self.b.id,self.w1,motion='thrust',
                           reach=2.0,strategy=Strategy(timing=3),charge=True)
        self.assertEqual(charge.end_time,2)
        self.enc.schedule_action(charge)
        with patch.object(_ProvisionalRandom,'roll',side_effect=[10,1]):
            self.enc.step(2,velocities={self.a.id:(4.5,0,0),self.b.id:(-1.0,0,0)})
        result=self.enc.inspect_committed(2).action(charge.id)
        self.assertEqual(result.facts.outcome,'normal')
        self.assertEqual(self.b.get_hit_points(),98)

    def test_set_pole_intercepts_charge_and_converts_chargers_scheduled_attack(self):
        self.a.set_position(CartesianPosition(0,0,0)); self.b.set_position(CartesianPosition(7.5,0,0))
        self.a.set_hex_facing(0)
        self.a.set_weapon_skill_level(self.world.get_weapon_dictionary(),'Dagger',0)
        self.b.set_weapon_skill_level(self.world.get_weapon_dictionary(),'Spear',100)
        self.b.strategy=Strategy(defense=10)
        spear_id=self.world.make_weapon_for_being(self.b.id,'Spear','Set pole spear')
        self.enc.add_object(spear_id)
        self.b.possessions.append(spear_id); self.b.weapons.append(spear_id)
        self.b.current.body_parts['left hand']=spear_id
        self.world.get_object_by_id(spear_id).parent_container_id=self.b.id
        self.enc.enable_transactional_progression(quiescent=True)
        adjusted=ReadyPreparationAction(self.enc,self.b.id,spear_id,'set pole',
                                        strategy=Strategy(timing=3))
        self.assertEqual(adjusted.end_time-adjusted.start_time,2)
        ready=ReadyPreparationAction(self.enc,self.b.id,spear_id,'set pole')
        self.assertEqual(ready.end_time-ready.start_time,4)
        self.enc.schedule_action(ready)
        self.enc.step(4)
        from weapon import native_ready_preparation
        spear=self.world.get_object_by_id(spear_id)
        self.assertTrue(native_ready_preparation(spear)['pole_set'])
        charge=MeleeStrike(self.enc,self.a.id,self.b.id,self.w1,motion='thrust',
                           reach=2,strategy=Strategy(timing=3),charge=True)
        self.enc.schedule_action(charge)
        self.enc.step(1,velocities={self.a.id:(4.0,0,0)})
        pole=MeleeStrike(self.enc,self.b.id,self.a.id,spear_id,motion='thrust',reach=10)
        self.assertEqual(pole.end_time,6)
        self.enc.schedule_action(pole)
        def fixed_roll(dice):
            return 10 if dice == '1d20' else 1
        with patch.object(_ProvisionalRandom,'roll',side_effect=fixed_roll):
            self.enc.step(1,velocities={self.a.id:(4.0,0,0)})
        pole_result=self.enc.inspect_committed(6).action(pole.id)
        charge_result=self.enc.inspect_committed(6).action(charge.id)
        self.assertEqual(pole_result.facts.outcome,'normal')
        self.assertNotIn('relative_charge_speed_yd_s',dict(charge_result.facts.metadata),
                         (dict(pole_result.facts.metadata),dict(charge_result.facts.metadata)))
        self.assertEqual(charge_result.facts.outcome,'miss')
        self.assertEqual(self.a.get_hit_points(),98)

    def test_successful_charge_bull_rush_continuation_adds_adopted_contest_bonus(self):
        self.a.set_position(CartesianPosition(0,0,0)); self.b.set_position(CartesianPosition(8.5,0,0))
        self.a.size_category=self.b.size_category='medium'
        self.a.set_hex_facing(0)
        self.a.set_weapon_skill_level(self.world.get_weapon_dictionary(),'Dagger',100)
        self.enc.enable_transactional_progression(quiescent=True)
        charge=MeleeStrike(self.enc,self.a.id,self.b.id,self.w1,motion='thrust',reach=2,
                           strategy=Strategy(timing=3),charge=True)
        self.enc.schedule_action(charge)
        with patch.object(_ProvisionalRandom,'roll',side_effect=lambda dice: 10 if dice=='1d20' else 1):
            self.enc.step(2,velocities={self.a.id:(4.0,0,0)})
        charge_result=self.enc.inspect_committed(2).action(charge.id)
        self.assertEqual(charge_result.facts.outcome,'normal')
        rush=Action(self.world,2,3,'bull rush',self.a.id,self.b.id,None)
        rush.charge_continuation_source_id=charge.id
        self.enc.schedule_action(rush)
        with patch.object(_ProvisionalRandom,'roll',side_effect=(4,4,4,4,4,4)):
            self.enc.step(1)
        result=self.enc.inspect_committed(3).action(rush.id)
        self.assertEqual(result.facts.outcome,'success_pending_displacement')

    def test_successful_bull_rush_overrun_gets_bonus_and_two_seconds_without_inventing_displacement(self):
        self.a.set_position(CartesianPosition(0,0,0)); self.b.set_position(CartesianPosition(.2,0,0))
        self.a.set_hex_facing(0)
        self.a.set_ability('strength',10);self.b.set_ability('strength',10)
        self.a.set_ability('dexterity',10);self.b.set_ability('dexterity',10)
        self.a.set_posture('standing');self.b.set_posture('standing')
        self.a.size_category=self.b.size_category='medium'
        self.enc.enable_transactional_progression(quiescent=True)
        rush=Action(self.world,0,1,'bull rush',self.a.id,self.b.id,None)
        self.enc.schedule_action(rush)
        with patch.object(_ProvisionalRandom,'roll',side_effect=(6,6,6,1,1,1)):
            self.enc.step(1)
        self.assertEqual(self.enc.inspect_committed(1).action(rush.id).facts.outcome,
                         'success_pending_displacement')
        overrun=Action(self.world,1,5,'overrun',self.a.id,self.b.id,None)
        overrun.charge_continuation_source_id=rush.id
        prepared=self.enc.prepare_action(overrun)
        self.assertEqual(prepared.end_time,7)
        self.enc.schedule_action(overrun)
        with patch.object(_ProvisionalRandom,'roll',side_effect=(2,2,2,2,2,2)):
            self.enc.step(6)
        self.assertEqual(self.enc.inspect_committed(7).action(overrun.id).facts.outcome,'success')
        self.assertEqual(self.b.get_posture(),'lying')
        self.assertEqual(self.b.get_position(),CartesianPosition(.2,0,0))

    def test_successful_bull_rush_can_continue_next_second_with_adopted_one_point_bonus(self):
        self.a.set_position(CartesianPosition(0,0,0)); self.b.set_position(CartesianPosition(.2,0,0))
        self.a.set_hex_facing(0)
        self.a.set_ability('strength',10);self.b.set_ability('strength',10)
        self.a.set_posture('standing');self.b.set_posture('standing')
        self.a.size_category=self.b.size_category='medium'
        self.enc.enable_transactional_progression(quiescent=True)
        first=Action(self.world,0,1,'bull rush',self.a.id,self.b.id,None)
        self.enc.schedule_action(first)
        with patch.object(_ProvisionalRandom,'roll',side_effect=(6,6,6,1,1,1)):
            self.enc.step(1)
        self.assertEqual(self.enc.inspect_committed(1).action(first.id).facts.outcome,
                         'success_pending_displacement')
        continued=Action(self.world,1,2,'bull rush',self.a.id,self.b.id,None)
        continued.charge_continuation_source_id=first.id
        self.assertEqual(self.enc.prepare_action(continued).end_time,2)
        self.enc.schedule_action(continued)
        with patch.object(_ProvisionalRandom,'roll',side_effect=(2,2,2,2,2,2)):
            self.enc.step(1)
        self.assertEqual(self.enc.inspect_committed(2).action(continued.id).facts.outcome,
                         'success_pending_displacement')
        self.assertEqual(self.b.get_position(),CartesianPosition(.2,0,0))

    def test_charge_overrun_uses_adopted_time_bonus_and_open_one_hex_landing(self):
        from arena_hex_map import ArenaHexLayout, HexAddress, encounter_map_descriptor
        layout=ArenaHexLayout.rectangle(20,10)
        self.enc.map=encounter_map_descriptor(layout)
        origin=layout.center_position(HexAddress(1,4))
        from hex_facing import facing_vector
        dx,dy=facing_vector(1)
        self.a.set_position(origin)
        self.b.set_position(CartesianPosition(origin.x+8.4*dx,origin.y+8.4*dy,origin.z))
        self.a.set_hex_facing(1)
        self.a.set_ability('strength',10);self.b.set_ability('strength',10)
        self.a.set_ability('dexterity',10);self.b.set_ability('dexterity',10)
        self.a.set_posture('standing');self.b.set_posture('standing')
        self.a.set_weapon_skill_level(self.world.get_weapon_dictionary(),'Dagger',100)
        self.a.size_category=self.b.size_category='medium'
        self.enc.enable_transactional_progression(quiescent=True)
        charge=MeleeStrike(self.enc,self.a.id,self.b.id,self.w1,motion='thrust',reach=2,
                           strategy=Strategy(timing=3),charge=True)
        self.enc.schedule_action(charge)
        with patch.object(_ProvisionalRandom,'roll',side_effect=lambda dice: 10 if dice=='1d20' else 1):
            self.enc.step(2,velocities={self.a.id:(3.8*dx,3.8*dy,0)})
        self.assertEqual(self.enc.inspect_committed(2).action(charge.id).facts.outcome,'normal')
        start_cell=layout.cell_at_position(self.b.get_position())
        neighbors=[address for address in layout.neighbors(start_cell) if layout.contains(address)]
        self.assertTrue(neighbors)
        expected=layout.center_position(max(neighbors,
            key=lambda address: (layout.center_yards(address)[0]*dx
                                 +layout.center_yards(address)[1]*dy)),
            z=self.b.get_position().z)
        from measured_values import truncate_position
        expected=truncate_position(expected)
        overrun=Action(self.world,2,6,'overrun',self.a.id,self.b.id,None)
        overrun.charge_continuation_source_id=charge.id
        self.assertEqual(self.enc.prepare_action(overrun).end_time,8)
        self.enc.schedule_action(overrun)
        with patch.object(_ProvisionalRandom,'roll',side_effect=(6,6,6,6,6,6)):
            self.enc.step(6)
        result=self.enc.inspect_committed(8).action(overrun.id)
        self.assertEqual(result.facts.outcome,'success')
        for actual, wanted in zip(self.b.get_position().as_tuple(),expected.as_tuple()):
            self.assertAlmostEqual(actual,wanted,places=7)
        self.assertEqual(self.b.__dict__.get('_posture'),'lying')

    def test_charge_adds_adopted_two_point_hit_bonus(self):
        self.a.set_position(CartesianPosition(0,0,0)); self.b.set_position(CartesianPosition(8.8,0,0))
        self.a.set_hex_facing(0)
        self.b.strategy = Strategy(defense=5)
        self.enc.enable_transactional_progression(quiescent=True)
        charge=MeleeStrike(self.enc,self.a.id,self.b.id,self.w1,motion='thrust',
                           reach=2.0,strategy=Strategy(timing=3),charge=True)
        self.enc.schedule_action(charge)
        with patch.object(_ProvisionalRandom,'roll',side_effect=[14,1]):
            self.enc.step(2,velocities={self.a.id:(4.0,0,0)})
        result=self.enc.inspect_committed(2).action(charge.id)
        self.assertEqual(result.facts.outcome,'normal')
        self.assertEqual(self.b.get_hit_points(),99)

    def test_charge_below_relative_speed_threshold_fails_without_attack_rolls(self):
        self.a.set_position(CartesianPosition(0,0,0)); self.b.set_position(CartesianPosition(7.4,0,0))
        self.a.set_hex_facing(0)
        self.enc.enable_transactional_progression(quiescent=True)
        charge=MeleeStrike(self.enc,self.a.id,self.b.id,self.w1,motion='thrust',
                           reach=2.0,strategy=Strategy(timing=3),charge=True)
        self.enc.schedule_action(charge)
        self.enc.step(2,velocities={self.a.id:(3.5,0,0)})
        result=self.enc.inspect_committed(2).action(charge.id)
        self.assertEqual(result.facts.outcome,'insufficient_charge_speed')
        self.assertEqual(self.b.get_hit_points(),100)

    def test_charge_declaration_refuses_when_actor_is_already_engaged(self):
        self.a.set_position(CartesianPosition(0,0,0)); self.b.set_position(CartesianPosition(.8,0,0))
        self.a.set_hex_facing(0)
        self.enc.enable_transactional_progression(quiescent=True)
        charge=MeleeStrike(self.enc,self.a.id,self.b.id,self.w1,motion='thrust',
                           reach=2.0,charge=True)
        with self.assertRaisesRegex(ValueError,'disengage from pressing opponents'):
            self.enc.prepare_action(charge)
        self.assertEqual(self.enc.pending_action_list,[])

    def test_native_bull_rush_tie_fails_without_displacement(self):
        self.a.set_position(CartesianPosition(0,0,0)); self.b.set_position(CartesianPosition(.2,0,0))
        self.a.set_hex_facing(0)
        self.a.size_category=self.b.size_category='medium'
        self.enc.enable_transactional_progression(quiescent=True)
        rush=Action(self.world,0,1,'bull rush',self.a.id,self.b.id,None)
        self.enc.schedule_action(rush)
        before=(self.a.get_position(),self.b.get_position())
        values=iter([2,2,2,2,2,2])
        def roll(ctx,dice):
            value=next(values)
            ctx.trace.append(RandomDraw(ctx.action_id,dice,int(dice.split('d')[1]),value))
            return value
        with patch.object(_ProvisionalRandom,'roll',roll): self.enc.step(1)
        self.assertEqual(self.enc.inspect_committed(1).action(rush.id).facts.outcome,'failed')
        self.assertEqual((self.a.get_position(),self.b.get_position()),before)

    def test_native_bull_rush_uses_equipped_advanced_shield_bonus(self):
        self.a.set_position(CartesianPosition(0,0,0)); self.b.set_position(CartesianPosition(.2,0,0))
        self.a.set_hex_facing(0)
        self.a.size_category=self.b.size_category='medium'
        shield_id=self.world.make_weapon_for_being(self.a.id,'Small shield','Bull Rush shield')
        self.world.arm_being(self.a.id,shield_id,'shield hand')
        self.a.set_weapon_skill_level(self.world.get_weapon_dictionary(),'Small shield',2)
        self.enc.enable_transactional_progression(quiescent=True)
        rush=Action(self.world,0,1,'bull rush',self.a.id,self.b.id,shield_id)
        self.enc.schedule_action(rush)
        values=iter([3,3,3,3,4,3])
        def roll(ctx,dice):
            value=next(values)
            ctx.trace.append(RandomDraw(ctx.action_id,dice,int(dice.split('d')[1]),value))
            return value
        with patch.object(_ProvisionalRandom,'roll',roll): self.enc.step(1)
        self.assertEqual(self.enc.inspect_committed(1).action(rush.id).facts.outcome,
                         'success_pending_displacement')

    def test_native_bull_rush_applies_stability_for_explicitly_represented_extra_legs(self):
        self.a.set_position(CartesianPosition(0,0,0)); self.b.set_position(CartesianPosition(.2,0,0))
        self.a.set_hex_facing(0)
        self.a.size_category=self.b.size_category='medium'
        self.a.current.body_parts={name:None for name in
            ('front left leg','front right leg','rear left leg','rear right leg')}
        self.b.current.body_parts={'left leg':None,'right leg':None}
        self.enc.enable_transactional_progression(quiescent=True)
        rush=Action(self.world,0,1,'bull rush',self.a.id,self.b.id,None)
        self.enc.schedule_action(rush)
        values=iter([2,2,2,2,2,2])
        def roll(ctx,dice):
            value=next(values)
            ctx.trace.append(RandomDraw(ctx.action_id,dice,int(dice.split('d')[1]),value))
            return value
        with patch.object(_ProvisionalRandom,'roll',roll): self.enc.step(1)
        result=self.enc.inspect_committed(1).action(rush.id)
        self.assertEqual(result.facts.outcome,'success_pending_displacement')

    def test_native_bull_rush_refuses_target_more_than_one_size_category_larger(self):
        self.a.set_position(CartesianPosition(0,0,0)); self.b.set_position(CartesianPosition(.2,0,0))
        self.a.set_hex_facing(0)
        self.a.size_category='small'; self.b.size_category='large'
        self.enc.enable_transactional_progression(quiescent=True)
        before=(self.enc.time,tuple(self.enc.pending_action_list),random.getstate())
        rush=Action(self.world,0,1,'bull rush',self.a.id,self.b.id,None)
        with self.assertRaisesRegex(ValueError,'more than one size category larger'):
            self.enc.prepare_action(rush)
        self.assertEqual((self.enc.time,tuple(self.enc.pending_action_list),
                          random.getstate()),before)

    def test_multiple_action_priority_penalty_applies_to_bull_rush_contest(self):
        self.a.set_position(CartesianPosition(0,0,0)); self.b.set_position(CartesianPosition(.2,0,0))
        self.a.set_hex_facing(0)
        self.a.size_category=self.b.size_category='medium'
        self.a.current.skills.skills['multi-action']=1
        self.enc.enable_transactional_progression(quiescent=True)
        rush=Action(self.world,0,1,'bull rush',self.a.id,self.b.id,None)
        touch=Action(self.world,0,1,'touch',self.a.id,self.b.id,None)
        touch.end_time=1
        self.enc.schedule_choice((ChoiceMember('rush',rush,priority_penalty=3),
                                  ChoiceMember('touch',touch,priority_penalty=0)))
        values=iter([3,3,3,2,2,2,20,20])
        def roll(ctx,dice):
            value=next(values)
            sides=int(dice.split('d')[1])
            ctx.trace.append(RandomDraw(ctx.action_id,dice,sides,value))
            return value
        with patch.object(_ProvisionalRandom,'roll',roll): self.enc.step(1)
        result=self.enc.inspect_committed(1)
        self.assertEqual(result.action(rush.id).facts.outcome,'failed')

    def test_native_trip_accepts_a_committed_successful_grab_as_contact(self):
        from physical_contact import trip_contact_kind
        self.a.set_position(CartesianPosition(0,0,0)); self.b.set_position(CartesianPosition(.2,0,0))
        self.a.current.body_parts['left hand'] = None
        self.a.current.body_parts['right hand'] = None
        self.a.current.skills.skills['improved grapple'] = 100
        self.b.current.skills.skills['improved grapple'] = 0
        self.a.set_posture('standing'); self.b.set_posture('standing')
        self.a.size_category=self.b.size_category='medium'
        self.enc.enable_transactional_progression(quiescent=True)
        touch=Action(self.world,0,1,'touch',self.a.id,self.b.id,None); touch.end_time=1
        self.enc.schedule_action(touch)
        with patch.object(_ProvisionalRandom,'roll',side_effect=[15,1]): self.enc.step(1)
        grab=Action(self.world,1,2,'grab',self.a.id,self.b.id,None)
        grab.touch_action_id=touch.id; grab.grab_hand='left hand'; grab.end_time=2
        with patch.object(_ProvisionalRandom,'roll',side_effect=[6,6,6,1,1,1]):
            self.enc.schedule_action(grab); self.enc.step(1)
        self.assertEqual(trip_contact_kind(self.enc,grab.id,self.a.id,self.b.id),'grab')
        trip=Action(self.world,2,4,'trip',self.a.id,self.b.id,None)
        trip.trip_source_action_id=grab.id; trip.trip_defender_ability='STR'; trip.end_time=4
        self.enc.schedule_action(trip)
        with patch.object(_ProvisionalRandom,'roll',side_effect=[6,6,6,1,1,1]): self.enc.step(2)
        receipt=self.enc.inspect_committed(4).action(trip.id)
        self.assertEqual(receipt.facts.outcome,'success')
        self.assertEqual(dict(receipt.facts.metadata)['contact_kind'],'grab')
        self.assertEqual(self.b.get_posture(),'lying')

    def test_native_trip_tie_preserves_posture_and_records_contact_source(self):
        self.a.set_position(CartesianPosition(0,0,0)); self.b.set_position(CartesianPosition(.2,0,0))
        self.a.set_posture('standing'); self.b.set_posture('standing')
        self.a.size_category=self.b.size_category='medium'
        self.enc.enable_transactional_progression(quiescent=True)
        touch=Action(self.world,0,1,'touch',self.a.id,self.b.id,None); touch.end_time=1
        self.enc.schedule_action(touch)
        with patch.object(_ProvisionalRandom,'roll',side_effect=[15,1]): self.enc.step(1)
        trip=Action(self.world,1,3,'trip',self.a.id,self.b.id,None)
        trip.trip_source_action_id=touch.id; trip.trip_defender_ability='STR'; trip.end_time=3
        self.enc.schedule_action(trip)
        with patch.object(_ProvisionalRandom,'roll',side_effect=[3,3,3,3,3,3]): self.enc.step(2)
        receipt=self.enc.inspect_committed(3).action(trip.id)
        self.assertEqual(receipt.facts.outcome,'failed')
        self.assertEqual(dict(receipt.facts.metadata)['contact_kind'],'touch')
        self.assertEqual(self.b.get_posture(),'standing')

    def test_native_trip_accepts_a_committed_successful_swing_or_thrust_strike(self):
        from physical_contact import trip_contact_kind
        self.a.set_position(CartesianPosition(0,0,0)); self.b.set_position(CartesianPosition(.2,0,0))
        self.a.set_posture('standing'); self.b.set_posture('standing')
        self.a.size_category=self.b.size_category='medium'
        self.enc.enable_transactional_progression(quiescent=True)
        strike=MeleeStrike(self.enc,self.a.id,self.b.id,self.w1,motion='thrust',reach=2)
        self.enc.schedule_action(strike)
        def hit(ctx,dice):
            value=15 if dice.startswith('1d20') else 1
            ctx.trace.append(RandomDraw(ctx.action_id,dice,int(dice[2:].split('+')[0]),value))
            return value
        with patch.object(_ProvisionalRandom,'roll',hit): self.enc.step(math.ceil(strike.end_time))
        self.assertIn(strike.resolution.outcome,('normal','critical','fatal'))
        self.assertEqual(trip_contact_kind(self.enc,strike.id,self.a.id,self.b.id),'strike')
        start=self.enc.time
        trip=Action(self.world,start,start+2,'trip',self.a.id,self.b.id,None)
        trip.trip_source_action_id=strike.id; trip.trip_defender_ability='STR'; trip.end_time=start+2
        self.enc.schedule_action(trip)
        with patch.object(_ProvisionalRandom,'roll',side_effect=[6,6,6,1,1,1]): self.enc.step(2)
        receipt=self.enc.inspect_committed(int(start+2)).action(trip.id)
        self.assertEqual(receipt.facts.outcome,'success')
        self.assertEqual(dict(receipt.facts.metadata)['contact_kind'],'strike')

    def _run_trip_interruption_scenario(self, same_second):
        from action_evaluation import RandomDraw, _ProvisionalRandom
        self.a.set_position(CartesianPosition(0,0,0)); self.b.set_position(CartesianPosition(.2,0,0))
        self.a.set_posture('standing'); self.b.set_posture('standing')
        self.a.size_category = self.b.size_category = 'medium'
        self.a.current.body_parts['left hand'] = None
        self.a.current.body_parts['right hand'] = None
        self.enc.enable_transactional_progression(quiescent=True)

        touch=Action(self.world,0,1,'touch',self.a.id,self.b.id,None)
        touch.end_time=1; self.enc.schedule_action(touch)
        with patch.object(_ProvisionalRandom,'roll',side_effect=[15,1]):
            self.enc.step(1)
        self.assertEqual(touch.resolution.outcome,'touched')

        strike_strategy=Strategy(timing=1 if same_second else 0)
        attack=MeleeStrike(self.enc,self.b.id,self.a.id,self.w3,
            motion='thrust',reach=2,strategy=strike_strategy)
        self.assertEqual(attack.start_time,1)
        self.assertEqual(attack.end_time,4 if same_second else 5)
        self.enc.schedule_action(attack)
        trip=Action(self.world,2,4,'trip',self.a.id,self.b.id,None)
        trip.trip_source_action_id=touch.id
        trip.trip_defender_ability='STR'
        trip.end_time=4
        self.enc.schedule_action(trip)
        trip_rolls=iter((6,6,6,1,1,1))
        def scripted(ctx,dice):
            value=next(trip_rolls) if ctx.action_id==trip.id else 1
            ctx.trace.append(RandomDraw(ctx.action_id,dice,
                int(dice[2:].split('+')[0]),value))
            return value
        with patch.object(_ProvisionalRandom,'roll',scripted):
            self.enc.step(3)
        self.assertEqual(trip.resolution.outcome,'success')
        if same_second:
            self.assertNotIn(attack.id,self.enc.cancelled_action_list)
            self.assertIn(attack.id,self.enc.finished_action_list)
            self.assertNotEqual(attack.resolution.outcome,'interrupted')
        else:
            self.assertIn(attack.id,self.enc.cancelled_action_list)
            self.assertEqual(attack.canceled_at,4)
            self.assertEqual(attack.cancellation_reason,'successful_trip')
            self.enc.step(1)
            self.assertEqual(attack.resolution.outcome,'interrupted')

    def test_successful_trip_cancels_only_an_attack_scheduled_for_a_later_second(self):
        self._run_trip_interruption_scenario(False)

    def test_successful_trip_preserves_an_attack_due_in_the_same_second(self):
        self._run_trip_interruption_scenario(True)

    def _run_initial_grapple_release_timing_case(self, same_second):
        from action_evaluation import RandomDraw, _ProvisionalRandom
        from physical_contact import active_contact_state
        self.a.set_position(CartesianPosition(0,0,0)); self.b.set_position(CartesianPosition(.2,0,0))
        self.a.current.body_parts['left hand'] = None
        self.a.current.body_parts['right hand'] = None
        self.a.current.skills.skills['improved grapple'] = 100
        self.b.current.skills.skills['improved grapple'] = 0
        self.a.set_posture('standing'); self.b.set_posture('standing')
        self.enc.enable_transactional_progression(quiescent=True)
        touch=Action(self.world,0,1,'touch',self.a.id,self.b.id,None)
        touch.end_time=1; self.enc.schedule_action(touch)
        with patch.object(_ProvisionalRandom,'roll',side_effect=[15,1]):
            self.enc.step(1)
        grab=Action(self.world,1,2,'grab',self.a.id,self.b.id,None)
        grab.touch_action_id=touch.id; grab.grab_hand='left hand'; grab.end_time=2
        with patch.object(_ProvisionalRandom,'roll',side_effect=[6,6,6,1,1,1]):
            self.enc.schedule_action(grab); self.enc.step(1)
        grapple=Action(self.world,2,8,'grapple',self.a.id,self.b.id,None)
        grapple.grip_id=grab.id; grapple.end_time=8
        self.enc.schedule_action(grapple)
        if same_second:
            self.enc.step(5)
            start,end=7,8
        else:
            start,end=3,4
        breaker=Action(self.world,start,end,'break hold',self.b.id,self.a.id,None)
        breaker.grip_id=grab.id; breaker.end_time=end
        self.enc.schedule_action(breaker)
        draws={grapple.id:iter((6,6,6,1,1,1)),breaker.id:iter((6,6,6,1,1,1))}
        def scripted(ctx,dice):
            value=next(draws[ctx.action_id])
            ctx.trace.append(RandomDraw(ctx.action_id,dice,
                int(dice[2:].split('+')[0]),value))
            return value
        with patch.object(_ProvisionalRandom,'roll',scripted):
            self.enc.step(end-self.enc.time)
        self.assertEqual(breaker.resolution.outcome,'success')
        if same_second:
            self.assertNotIn(grapple.id,self.enc.cancelled_action_list)
            self.assertEqual(grapple.resolution.outcome,'success')
            self.assertEqual(active_contact_state(self.enc)[0],())
            self.assertEqual(tuple(row[0] for row in active_contact_state(self.enc)[1]),(grapple.id,))
        else:
            self.assertIn(grapple.id,self.enc.cancelled_action_list)
            self.assertEqual(grapple.canceled_at,4)
            self.assertEqual(active_contact_state(self.enc), ((),()))
            self.assertFalse(self.enc._choice_book.actor_planned_now(self.a.id))

    def test_earlier_last_grip_release_cancels_only_unestablished_initial_grapple(self):
        self._run_initial_grapple_release_timing_case(False)

    def test_same_second_last_grip_release_does_not_retroactively_cancel_grapple(self):
        self._run_initial_grapple_release_timing_case(True)

    def test_failed_initial_grapple_still_atomically_maintains_its_prerequisite_grip(self):
        from physical_contact import active_contact_state
        self.a.set_position(CartesianPosition(0,0,0)); self.b.set_position(CartesianPosition(.2,0,0))
        self.a.current.body_parts['left hand'] = None
        self.a.current.skills.skills['improved grapple'] = 100
        self.b.current.skills.skills['improved grapple'] = 100
        self.a.set_posture('standing'); self.b.set_posture('standing')
        self.enc.enable_transactional_progression(quiescent=True)

        def resolve(action,duration,rolls):
            action.end_time=action.start_time+duration; self.enc.schedule_action(action)
            values=iter(rolls)
            def scripted(ctx,dice):
                value=next(values);ctx.trace.append(RandomDraw(ctx.action_id,dice,
                    int(dice[2:].split('+')[0]),value));return value
            with patch.object(_ProvisionalRandom,'roll',scripted):self.enc.step(duration)
            return self.enc.inspect_committed(self.enc.last_processed_boundary).action(action.id)

        touch=Action(self.world,0,1,'touch',self.a.id,self.b.id,None)
        self.assertEqual(resolve(touch,1,[15,1]).facts.outcome,'touched')
        grab=Action(self.world,1,2,'grab',self.a.id,self.b.id,None)
        grab.touch_action_id=touch.id;grab.grab_hand='left hand'
        self.assertEqual(resolve(grab,1,[6,6,6,1,1,1]).facts.outcome,'success')
        self.a.current.skills.skills['improved grapple'] = 0
        grapple=Action(self.world,2,8,'grapple',self.a.id,self.b.id,None)
        grapple.grip_id=grab.id; grapple.end_time=8
        self.enc.schedule_action(grapple)
        self.enc.step(5)
        values=iter([1,1,1,6,6,6])
        def scripted(ctx,dice):
            value=next(values);ctx.trace.append(RandomDraw(ctx.action_id,dice,
                int(dice[2:].split('+')[0]),value));return value
        with patch.object(_ProvisionalRandom,'roll',scripted):self.enc.step(1)
        result=self.enc.inspect_committed(8).action(grapple.id)
        self.assertEqual(result.facts.outcome,'failed')
        self.assertEqual(len(active_contact_state(self.enc)[1]),0)
        self.assertEqual(active_contact_state(self.enc)[0][0][5],14)

    def test_native_strike_object_applies_hardness_and_publishes_object_hp(self):
        from object import ObjectDefinition, ObjectInstance
        target = ObjectInstance(ObjectDefinition('authored hardwood target', 12, 12, 12,
            20, 1, 2, 6), name='Hardwood test target')
        target.set_position(CartesianPosition(.5, 0, 0))
        self.world.add_object(target)
        self.enc.add_object(target.id)
        self.enc.mark_aware(self.a.id, target.id)
        self.enc.enable_transactional_progression(quiescent=True)
        weapon = self.world.get_object_by_id(self.w1)
        action = Action(self.world, 0, 1, 'strike object', self.a.id, target.id, self.w1)
        action.object_motion = 'thrust'
        from melee_combat import effective_melee_reach_meters
        action.reach = effective_melee_reach_meters(self.a.current, weapon.current)
        action.end_time = max(1, math.ceil(weapon.Tt()))
        self.enc.schedule_action(action)
        # Critical confirmation, then ordinary and critical damage dice.
        iterator = iter([20, 20, 4, 4])
        def roll(ctx, dice):
            value = next(iterator)
            ctx.trace.append(RandomDraw(ctx.action_id, dice,
                int(dice[2:].split('+')[0]), value))
            return value
        with patch.object(_ProvisionalRandom, 'roll', roll):
            self.enc.step(action.end_time)
        receipt = self.enc.inspect_committed(action.end_time).action(action.id)
        self.assertEqual(receipt.facts.outcome, 'critical')
        object_damage = next(effect.amount for effect in receipt.facts.effects
                             if type(effect) is DamageEffect and effect.component == 'object')
        self.assertEqual(object_damage, 6)
        self.assertEqual(target.hit_points(), 0)

    def test_simultaneous_object_strikes_apply_hardness_per_blow_and_sum_atomically(self):
        from object import ObjectDefinition, ObjectInstance
        target=ObjectInstance(ObjectDefinition('test copper plate',12,12,12,20,1,1,20),
                              name='test copper plate')
        target.set_position(CartesianPosition(1.0,0,0));self.world.add_object(target)
        self.enc.add_object(target.id)
        for being in (self.a,self.b):self.enc.mark_aware(being.id,target.id)
        self.enc.enable_transactional_progression(quiescent=True)
        actions=[]
        for actor,weapon_id in ((self.a,self.w1),(self.b,self.w3)):
            weapon=self.world.get_object_by_id(weapon_id)
            action=Action(self.world,0,1,'strike object',actor.id,target.id,weapon_id)
            action.object_motion='thrust'
            from melee_combat import effective_melee_reach_meters
            action.reach=effective_melee_reach_meters(actor.current,weapon.current)
            action.end_time=math.ceil(weapon.Tt());self.enc.schedule_action(action);actions.append(action)
        def roll(ctx,dice):
            value=15 if dice=='1d20' else 3
            ctx.trace.append(RandomDraw(ctx.action_id,dice,int(dice[2:].split('+')[0]),value))
            return value
        with patch.object(_ProvisionalRandom,'roll',roll):self.enc.step(max(math.ceil(a.end_time) for a in actions))
        inspected=self.enc.inspect_committed(max(math.ceil(a.end_time) for a in actions))
        impacts=[effect for action in actions for effect in inspected.action(action.id).effects
                 if type(effect.effect) is DamageEffect and effect.effect.component=='object']
        self.assertEqual([row.effect.amount for row in impacts],[2,2])
        self.assertEqual(target.hit_points(),16)

    def test_native_disarm_releases_same_weapon_into_defender_hex_atomically(self):
        self.a.current.skills.weapon_skills['Dagger']=2
        self.b.set_position(CartesianPosition(.2,0,0))
        self.enc.enable_transactional_progression(quiescent=True)
        weapon=self.world.get_object_by_id(self.w1)
        action=Action(self.world,0,1,'disarm',self.a.id,self.b.id,self.w1)
        action.disarm_weapon_id=self.w3
        action.disarm_motion='thrust'
        from melee_combat import effective_melee_reach_meters
        action.reach=effective_melee_reach_meters(self.a.current,weapon.current)
        action.end_time=weapon.Tt()
        self.enc.schedule_action(action)
        iterator=iter([20,1])
        def roll(ctx,dice):
            value=next(iterator);ctx.trace.append(RandomDraw(ctx.action_id,dice,
                int(dice[2:].split('+')[0]),value));return value
        with patch.object(_ProvisionalRandom,'roll',roll):self.enc.step(action.end_time)
        receipt=self.enc.inspect_committed(action.end_time).action(action.id)
        self.assertEqual(receipt.facts.outcome,'disarmed')
        self.assertEqual(self.b.current.body_parts['right hand'],None)
        self.assertNotIn(self.w3,self.b.weapons)
        dropped=self.world.get_object_by_id(self.w3)
        self.assertIsNone(dropped.parent_container_id)
        self.assertEqual(dropped.get_position(),self.b.get_position())
        self.assertIs(dropped,self.world.get_object_by_id(self.w3))

    def test_native_unarmed_disarm_uses_arm_profile_and_opposed_attack_roll(self):
        self.a.current.skills.skills['unarmed combat']=1
        self.a.current.body_parts['left hand']=None
        self.b.set_position(CartesianPosition(.2,0,0))
        self.enc.enable_transactional_progression(quiescent=True)
        action=Action(self.world,0,1,'disarm',self.a.id,self.b.id,None)
        action.disarm_weapon_id=self.w3
        action.disarm_motion='thrust'
        from melee_combat import reference_arm_length_inches,INCHES_TO_METERS
        action.reach=reference_arm_length_inches(height_inches=self.a.current.height,
            length_inches=self.a.current.length)*INCHES_TO_METERS
        action.end_time=3
        self.enc.schedule_action(action)
        iterator=iter([20,1])
        def roll(ctx,dice):
            value=next(iterator)
            ctx.trace.append(RandomDraw(ctx.action_id,dice,int(dice[2:].split('+')[0]),value))
            return value
        with patch.object(_ProvisionalRandom,'roll',roll):self.enc.step(3)
        receipt=self.enc.inspect_committed(3).action(action.id)
        self.assertEqual(receipt.facts.outcome,'disarmed')
        self.assertIsNone(self.b.current.body_parts['right hand'])
        dropped=self.world.get_object_by_id(self.w3)
        self.assertIsNone(dropped.parent_container_id)
        self.assertEqual(dropped.get_position(),self.b.get_position())

    def test_grappled_disarm_defender_loses_the_five_point_defense_bonus(self):
        from dataclasses import replace
        from types import MappingProxyType
        from action_evaluation import ActionView,_disarm
        self.a.current.skills.skills['unarmed combat']=1
        self.a.current.body_parts['left hand']=None
        self.b.set_position(CartesianPosition(.2,0,0))
        original=self.strike();self.schedule(original)
        snapshot=self.snapshot()
        data=dict(snapshot.actions[original.id].data)
        from melee_combat import reference_arm_length_inches,INCHES_TO_METERS
        data.update(event_type='disarm',disarm_weapon_id=self.w3,
                    disarm_motion='thrust',reach=reference_arm_length_inches(
                        height_inches=self.a.current.height,
                        length_inches=self.a.current.length)*INCHES_TO_METERS)
        action=replace(snapshot.actions[original.id],family='disarm',instrument_id=None,
                       data=MappingProxyType(data))
        snapshot=replace(snapshot,actions=MappingProxyType({action.id:action}),
            grapple_controls=(('control',self.a.id,self.b.id,6,'standing'),))
        class ScriptedRolls:
            values=iter((10,10))
            def roll(self,_dice):return next(self.values)
        result=_disarm(snapshot,action,ScriptedRolls())
        self.assertEqual(result.outcome,'disarmed')
        self.assertEqual(dict(result.metadata)['margin'],1)

    def test_native_break_weapon_uses_pending_attack_motion_and_disables_it_next_boundary(self):
        self.a.set_position(CartesianPosition(0,0,0)); self.b.set_position(CartesianPosition(.2,0,0))
        self.a.current.skills.weapon_skills['Dagger']=2
        self.enc.enable_transactional_progression(quiescent=True)
        from melee_combat import effective_melee_reach_meters
        attacking=self.world.get_object_by_id(self.w1)
        victim=self.world.get_object_by_id(self.w3)
        # Test-authored durability makes the adopted break threshold explicit.
        victim.current.hit_points=1; victim.current.hardness=0
        duration=max(1,math.ceil(attacking.St()))
        follow=MeleeStrike(self.enc,self.b.id,self.a.id,self.w3,motion='thrust',reach=2)
        follow.end_time=duration+1
        self.enc.schedule_action(follow)
        breaker=Action(self.world,0,1,'break weapon',self.a.id,self.b.id,self.w1)
        breaker.break_weapon_id=self.w3; breaker.break_motion='swing'
        breaker.reach=effective_melee_reach_meters(self.a.current,attacking.current)
        breaker.end_time=duration
        self.enc.schedule_action(breaker)
        iterator=iter([15,4,4])
        def roll(ctx,dice):
            value=next(iterator);ctx.trace.append(RandomDraw(ctx.action_id,dice,
                int(dice[2:].split('+')[0]),value));return value
        with patch.object(_ProvisionalRandom,'roll',roll):
            self.enc.step(math.ceil(breaker.end_time))
        receipt=self.enc.inspect_committed(math.ceil(breaker.end_time)).action(breaker.id)
        self.assertEqual(receipt.facts.outcome,'broken')
        self.assertEqual(victim.hit_points(),0)
        # Breaking is committed in an earlier second. The already scheduled
        # attack then resolves normally as unavailable due to its broken weapon.
        self.enc.step(math.ceil(follow.end_time))
        later=self.enc.inspect_committed(math.ceil(follow.end_time)).action(follow.id)
        self.assertEqual(later.facts.outcome,'weapon_unavailable')

    def test_native_armed_feint_is_half_timing_nondamaging_and_bonus_is_one_followup(self):
        self.b.set_position(CartesianPosition(.2, 0, 0))
        self.a.current.skills.weapon_skills['Dagger'] = 2
        self.enc.enable_transactional_progression(quiescent=True)
        weapon = self.world.get_object_by_id(self.w1)
        action = Action(self.world, 0, 1, 'feint', self.a.id, self.b.id, self.w1)
        action.feint_motion = 'thrust'
        from melee_combat import effective_melee_reach_meters
        action.reach = effective_melee_reach_meters(self.a.current, weapon.current)
        duration = math.ceil(weapon.Tt() / 2)
        action.end_time = duration
        self.assertEqual(action.prepare_schedule(self.enc).end_time, duration)
        self.enc.schedule_action(action)
        iterator = iter([20])
        def roll(ctx, dice):
            value = next(iterator)
            ctx.trace.append(RandomDraw(ctx.action_id, dice,
                int(dice[2:].split('+')[0]), value))
            return value
        with patch.object(_ProvisionalRandom, 'roll', roll):
            self.enc.step(duration)
        feint = self.enc.inspect_committed(duration).action(action.id)
        self.assertEqual(feint.facts.outcome, 'success')
        self.assertFalse(feint.facts.effects)
        self.assertEqual(feint.facts.metadata, (('distance', .2),))
        self.enc.difficulty_class = 15
        strike = self.strike()
        strike.feint_source_action_id = action.id
        self.assertEqual(strike.prepare_schedule(self.enc).actor_id, self.a.id)
        self.enc.schedule_action(strike)
        next_duration = math.ceil(strike.end_time) - self.enc.time
        iterator = iter([11, 2])
        with patch.object(_ProvisionalRandom, 'roll', roll):
            self.enc.step(next_duration)
        receipt = self.enc.inspect_committed(math.ceil(strike.end_time)).action(strike.id)
        self.assertEqual(receipt.facts.outcome, 'normal')
        self.assertTrue(any(type(effect).__name__ == 'DamageEffect'
                            for effect in receipt.facts.effects))
        repeated = self.strike()
        repeated.feint_source_action_id = action.id
        with self.assertRaisesRegex(ValueError, 'forfeited or consumed'):
            repeated.prepare_schedule(self.enc)

    def test_armed_feint_requires_advanced_weapon_skill_before_choice_mutation(self):
        self.enc.enable_transactional_progression(quiescent=True)
        weapon = self.world.get_object_by_id(self.w1)
        action = Action(self.world, 0, 1, 'feint', self.a.id, self.b.id, self.w1)
        action.feint_motion = 'thrust'
        from melee_combat import effective_melee_reach_meters
        action.reach = effective_melee_reach_meters(self.a.current, weapon.current)
        action.end_time = math.ceil(weapon.Tt() / 2)
        choices_before = self.enc.choice_state
        history_before = dict(self.world.event_history)
        rng_before = random.getstate()
        with self.assertRaisesRegex(ValueError, 'advanced skill'):
            self.enc.prepare_action(action)
        self.assertEqual(self.enc.choice_state, choices_before)
        self.assertEqual(dict(self.world.event_history), history_before)
        self.assertEqual(random.getstate(), rng_before)

    def test_native_coup_de_grace_automatically_criticals_and_makes_fortitude_save(self):
        from states import StatesList
        self.b.set_position(CartesianPosition(.2, 0, 0))
        states = StatesList()
        states.load_states(str(ROOT / 'src/config/states.tsv'))
        self.b.stun(states)
        self.enc.enable_transactional_progression(quiescent=True)
        weapon = self.world.get_object_by_id(self.w1)
        from melee_combat import effective_melee_reach_meters
        action = Action(self.world, 0, 1, 'coup de grace', self.a.id, self.b.id, self.w1)
        action.coup_motion = 'thrust'
        action.reach = effective_melee_reach_meters(self.a.current, weapon.current)
        action.end_time = weapon.Tt()
        self.enc.schedule_action(action)
        iterator = iter([2, 3, 20])
        def roll(ctx, dice):
            value = next(iterator)
            ctx.trace.append(RandomDraw(ctx.action_id, dice,
                int(dice[2:].split('+')[0]), value))
            return value
        with patch.object(_ProvisionalRandom, 'roll', roll):
            self.enc.step(math.ceil(weapon.Tt()))
        receipt = self.enc.inspect_committed(math.ceil(weapon.Tt())).action(action.id)
        self.assertEqual(receipt.facts.outcome, 'critical')
        self.assertTrue(any(type(effect).__name__ == 'DamageEffect'
                            and effect.component == 'critical_bypass'
                            for effect in receipt.facts.effects))
        self.assertFalse(any(type(effect).__name__ == 'FatalEffect'
                             for effect in receipt.facts.effects))
        fatal = Action(self.world, self.enc.time, self.enc.time + 1,
                       'coup de grace', self.a.id, self.b.id, self.w1)
        fatal.coup_motion = 'thrust'
        fatal.reach = effective_melee_reach_meters(self.a.current, weapon.current)
        fatal.end_time = fatal.start_time + weapon.Tt()
        self.enc.schedule_action(fatal)
        iterator = iter([2, 3, 1])
        with patch.object(_ProvisionalRandom, 'roll', roll):
            self.enc.step(math.ceil(fatal.end_time) - self.enc.time)
        fatal_receipt = self.enc.inspect_committed(math.ceil(fatal.end_time)).action(fatal.id)
        self.assertEqual(fatal_receipt.facts.outcome, 'fatal')
        self.assertTrue(any(type(effect).__name__ == 'FatalEffect'
                            for effect in fatal_receipt.facts.effects))

    def test_coup_and_helpless_targets_already_scheduled_attack_resolve_simultaneously(self):
        from states import StatesList
        self.b.set_position(CartesianPosition(.2,0,0))
        states=StatesList();states.load_states(str(ROOT/'src/config/states.tsv'));self.b.stun(states)
        self.enc.enable_transactional_progression(quiescent=True)
        from melee_combat import effective_melee_reach_meters
        defender_weapon=self.world.get_object_by_id(self.w3)
        incoming=MeleeStrike(self.enc,self.b.id,self.a.id,self.w3,motion='thrust',reach=2)
        self.enc.schedule_action(incoming)
        weapon=self.world.get_object_by_id(self.w1)
        coup=Action(self.world,0,1,'coup de grace',self.a.id,self.b.id,self.w1)
        coup.coup_motion='thrust';coup.reach=effective_melee_reach_meters(self.a.current,weapon.current)
        coup.end_time=weapon.Tt();self.enc.schedule_action(coup)
        def roll(ctx,dice):
            value=(15 if ctx.action_id==incoming.id and dice=='1d20' else
                   2 if dice.startswith('1d') else 1)
            ctx.trace.append(RandomDraw(ctx.action_id,dice,int(dice[2:].split('+')[0]),value))
            return value
        with patch.object(_ProvisionalRandom,'roll',roll):self.enc.step(math.ceil(coup.end_time))
        receipt=self.enc.inspect_committed(math.ceil(coup.end_time))
        self.assertEqual(receipt.action(coup.id).facts.outcome,'fatal')
        self.assertIn(incoming.id,receipt.actions)
        self.assertEqual(receipt.action(incoming.id).facts.outcome,'normal')
        self.assertTrue(any(type(effect).__name__=='FatalEffect'
                            for effect in receipt.action(coup.id).facts.effects))

    def test_nested_views_frozen_and_detached(self):
        self.schedule(self.strike()); s = self.snapshot()
        a = s.entity(self.a.id)
        for mapping, key, value in [(s.entities, self.a.id, None), (a.data['skills'], 'spot', 999),
            (a.data['strategy'], 'attack', 999), (a.data['fatigue_adjustments'][2], 'ability_adjustment', 999),
            (s.fatigue[self.a.id], 'q', 0), (s.awareness, self.a.id, ())]:
            with self.assertRaises(TypeError): mapping[key] = value
        with self.assertRaises(FrozenInstanceError): a.hp = 0
        with self.assertRaises(FrozenInstanceError): a.geometry.radius = 100
        self.a.current.skills.skills['spot'] = 100
        self.a.strategy.attack = 100
        self.a.set_position(CartesianPosition(100, 0, 0))
        self.a.set_physical_fatigue(.1, .1)
        self.assertNotEqual(a.data['skills'].get('spot'), 100)
        self.assertEqual(a.position.x, 0)
        self.assertEqual(s.fatigue[self.a.id]['q'], 1)
        self.assertNotEqual(a.data['strategy']['attack'], 100)
        self.assertFalse(hasattr(a, 'universe'))

    def test_normal_body_contribution_and_d7_ownership(self):
        action = self.strike(); self.schedule(action)
        result = self.scripted(self.snapshot(), [15, 3])
        p = result.proposals[0]
        self.assertEqual(p.outcome, 'normal')
        self.assertIn(DamageEffect(action.id, self.b.id, 3, 'body'), p.effects)
        for record in (p,) + p.effects:
            self.assertFalse(any('hp_before' in f.name or 'hp_after' in f.name for f in fields(record)))
        self.assertIn(self.b.id, p.target_ids)

    def test_critical_extra_die_bypasses_protection(self):
        action = self.strike(); self.schedule(action)
        self.armor(self.b)
        p = self.scripted(self.snapshot(), [20, 15, 4, 3]).proposals[0]
        self.assertEqual(p.outcome, 'critical')
        self.assertIn(DamageEffect(action.id, self.b.id, 3, 'critical_bypass'), p.effects)
        self.assertEqual([x.incoming for x in p.effects if isinstance(x, ProtectionEffect)], [4])
        self.assertIn(DamageEffect(action.id, self.b.id, 3, 'body'), p.effects)
        self.assertTrue(any(isinstance(x, DamageEffect) and x.component == 'armor' and x.amount == 4 for x in p.effects))

    def armor(self, actor):
        aid = self.world.make_armor_for_being(actor.id, 'Leather armor', 'Leather')
        actor.set_armor_id(aid)
        return self.world.get_object_by_id(aid)

    def test_fatal_failed_target_save_has_no_ordinary_damage(self):
        action = self.strike(); self.schedule(action)
        p = self.scripted(self.snapshot(), [20, 20, 1]).proposals[0]
        self.assertEqual(p.outcome, 'fatal')
        self.assertIn(FatalEffect(action.id, self.b.id), p.effects)
        self.assertFalse(any(isinstance(x, DamageEffect) for x in p.effects))

    def test_successful_target_save_reverts_to_critical(self):
        action = self.strike(); self.schedule(action)
        p = self.scripted(self.snapshot(), [20, 20, 20, 4, 2]).proposals[0]
        self.assertEqual(p.outcome, 'critical')
        self.assertFalse(any(isinstance(x, FatalEffect) for x in p.effects))
        self.assertEqual(sum(x.amount for x in p.effects if isinstance(x, DamageEffect)), 6)

    def test_critical_failure_hits_actor_protection(self):
        action = self.strike(); self.schedule(action); armor = self.armor(self.a)
        p = self.scripted(self.snapshot(), [1, 1, 4]).proposals[0]
        self.assertEqual(p.outcome, 'hit self')
        self.assertTrue(any(isinstance(x, DamageEffect) and x.target_id == armor.id for x in p.effects))
        self.assertFalse(any(isinstance(x, DamageEffect) and x.target_id == self.b.id for x in p.effects))

    def test_failed_confirmation_actor_save_and_drop_stub(self):
        action = self.strike(); self.schedule(action); s = self.snapshot()
        self.assertEqual(self.scripted(s, [1, 2, 1]).proposals[0].outcome, 'drop weapon')
        self.assertEqual(self.scripted(s, [1, 2, 20]).proposals[0].outcome, 'spectacular miss')
        self.assertIn(self.w1, self.a.armed_with(self.world).values())

    def test_native_single_action_random_sequences_and_damage_match(self):
        action = self.strike(); self.schedule(action); self.armor(self.b)
        s = self.snapshot()
        # Independent comparisons cover real native RNG including saves/critical paths.
        before_rng = random.getstate()
        try:
            for seed in range(150):
                random.seed(seed); initial = random.getstate()
                snapshot = replace(s, rng_state=initial)
                p = evaluate_snapshot(snapshot).proposals[0]
                self.assertEqual(random.getstate(), initial)
                for entity in (self.a, self.b, self.world.get_object_by_id(self.b.get_armor_id())):
                    entity.current.hit_points = 100
                action.combat_result = None; action.hit_type = None
                action.resolve(self.enc.difficulty_class)
                self.assertEqual(p.outcome, action.hit_type)
                self.assertEqual(evaluate_snapshot(snapshot).provisional_rng_state, random.getstate())
                for entity in (self.a, self.b, self.world.get_object_by_id(self.b.get_armor_id())):
                    if any(isinstance(x, FatalEffect) and x.target_id == entity.id for x in p.effects):
                        self.assertEqual(entity.hit_points(), -10)
                    else:
                        amount = sum(x.amount for x in p.effects if isinstance(x, DamageEffect) and x.target_id == entity.id)
                        self.assertEqual(100 - entity.hit_points(), amount)
        finally:
            random.setstate(before_rng)

    def test_common_snapshot_two_strikes_no_effect_leak(self):
        one, two = self.strike(), self.strike(self.w2); self.schedule(one, two)
        armor = self.armor(self.b); s = self.snapshot()
        result = self.scripted(s, [15, 4, 15, 4])
        first, second = result.proposals
        self.assertEqual([(x.component,x.amount) for x in first.effects if isinstance(x,DamageEffect)],
                         [(x.component,x.amount) for x in second.effects if isinstance(x,DamageEffect)])
        self.assertEqual(self.b.hit_points(), 100)
        self.assertEqual(s.entity(armor.id).hp, armor.hit_points())
        self.assertEqual(evaluate_snapshot(s), evaluate_snapshot(s, (two.id, one.id)))

    def test_declared_multiple_action_priority_is_frozen_with_each_component(self):
        first, second = self.strike(self.w1), self.strike(self.w2)
        self.schedule(first, second)
        snapshot = self.snapshot()
        self.assertEqual(snapshot.actions[first.id].data['multiple_action_priority'], 0)
        self.assertEqual(snapshot.actions[second.id].data['multiple_action_priority'], 3)

    def test_multiple_action_repeats_with_fresh_ids_and_stops_on_abort(self):
        first, second = self.strike(self.w1), self.strike(self.w2)
        self.schedule(first, second)
        self.enc.enable_transactional_progression(quiescent=True)
        self.enc.step(6)
        repeated = [record for record in self.enc._choice_book._choices.values()
                    if record.origin == 'multiple-action-cycle']
        self.assertEqual(len(repeated), 1)
        cycle = repeated[0]
        self.assertEqual(tuple(member.priority_penalty for member in cycle.members), (0, 3))
        self.assertTrue(all(member.action.id not in (first.id, second.id)
                            for member in cycle.members))
        self.assertEqual(cycle.view.first_start,
                         max(first.end_time, second.end_time))
        self.assertEqual(self.enc.get_choice(cycle.view.id).state, 'executing')
        self.enc.cancel_action(cycle.view.action_ids[0])
        self.assertTrue(all(self.enc._choice_book._states[action_id] == 'cancelled'
                            for action_id in cycle.view.action_ids))
        self.enc.step(1)
        self.assertFalse(any(item.origin == 'multiple-action-cycle'
                             and item.view.id != cycle.view.id
                             for item in self.enc._choice_book._choices.values()))

    def test_multiple_designated_defenses_all_retained_no_stacking(self):
        attack = self.strike()
        parry = MeleeDefense(self.enc, self.b.id, self.a.id, kind='parry', parry_motion='swing', target_action_id=attack.id, weapon_id=self.w3)
        dodge = MeleeDefense(self.enc, self.b.id, self.a.id, kind='dodge', target_action_id=attack.id)
        self.schedule(attack, parry, dodge)
        s = self.snapshot()
        result = self.scripted(s, [20, 1, 20, 1])
        strike = next(x for x in result.proposals if x.action_id == attack.id)
        self.assertEqual(len(strike.defenses), 2)
        self.assertTrue(all(d.success for d in strike.defenses))
        self.assertFalse(any(isinstance(x,DamageEffect) for x in strike.effects))
        self.assertEqual(sum(isinstance(e,PracticeEffect) for p in result.proposals for e in p.effects), 3)
        self.assertIsNone(attack.defended_by)
        self.assertFalse(parry.success)
        with self.assertRaises(EvaluationIntegrityError): evaluate_snapshot(s, (attack.id,))

    def test_failed_defense_keeps_practice(self):
        attack = self.strike()
        defense = MeleeDefense(self.enc,self.b.id,self.a.id,kind='dodge',target_action_id=attack.id)
        self.schedule(attack,defense)
        ps = self.scripted(self.snapshot(), [1,20,15,3]).proposals
        self.assertEqual(ps[0].outcome,'failed')
        self.assertTrue(any(isinstance(e,PracticeEffect) for e in ps[0].effects))
        self.assertEqual(ps[1].outcome,'normal')

    def test_geometric_dodge_uses_frozen_start_threat(self):
        attack = self.strike()
        defense = MeleeDefense(self.enc,self.b.id,self.a.id,kind='dodge',target_action_id=attack.id)
        self.schedule(attack,defense)
        self.b.set_position(CartesianPosition(5,0,0))
        s = self.snapshot()
        result = self.unchanged(lambda: evaluate_snapshot(s))
        self.assertEqual(result.proposals[0].outcome,'evaded')
        self.assertEqual(result.proposals[1].outcome,'out_of_reach')
        self.assertEqual(result.trace,())

    def test_out_of_reach_and_unavailable_weapon_are_outcomes(self):
        action=self.strike();self.schedule(action)
        self.b.set_position(CartesianPosition(5,0,0));s=self.snapshot()
        self.assertEqual(evaluate_snapshot(s).proposals[0].outcome,'out_of_reach')
        self.a.body_part_remove_object('right hand')
        self.assertEqual(evaluate_snapshot(self.snapshot()).proposals[0].outcome,'weapon_unavailable')

    def test_cancelled_action_produces_interrupted_without_draws(self):
        action=self.strike();self.schedule(action)
        end=math.ceil(action.end_time);self.enc.cancel_action(action.id)
        s=self.snapshot(end);r=evaluate_snapshot(s)
        self.assertEqual(r.proposals[0].outcome,'interrupted');self.assertEqual(r.trace,())

    def test_run_uses_actual_start_and_proposes_practice(self):
        run=RunAction(self.world,self.a.id,0,2,3,experience=4);self.schedule(run)
        self.a.set_position(CartesianPosition(2,0,0));s=self.snapshot()
        result=self.unchanged(lambda:evaluate_snapshot(s));p=result.proposals[0]
        self.assertEqual(p.outcome,'partial');self.assertIn(('displacement',2),p.metadata)
        self.assertIn(PracticeEffect(run.id,self.a.id,'run',4),p.effects)
        self.assertIsNone(run.displacement)

    def test_run_no_movement_and_unplaced_have_no_practice(self):
        run=RunAction(self.world,self.a.id,0,2,3,experience=4);self.schedule(run)
        self.assertEqual(evaluate_snapshot(self.snapshot()).proposals[0].outcome,'no_movement')
        self.a.spatial_state=None
        p=evaluate_snapshot(self.snapshot()).proposals[0]
        self.assertEqual(p.outcome,'unplaced');self.assertEqual(p.effects,())

    def test_spot_awareness_has_no_practice_or_live_writes(self):
        spot=SpotAction(self.world,self.a.id,self.b.id,0,die_roll=20);self.schedule(spot)
        self.enc.clear_awareness(self.a.id,self.b.id)
        s=self.snapshot();p=self.unchanged(lambda:evaluate_snapshot(s)).proposals[0]
        self.assertEqual(p.outcome,'success')
        self.assertTrue(any(isinstance(x,AwarenessEffect) for x in p.effects))
        self.assertFalse(self.enc.is_aware(self.a.id,self.b.id));self.assertIsNone(spot.roll)

    def test_spot_roll_is_a_plain_difficulty_check_without_practice(self):
        spot=SpotAction(self.world,self.a.id,self.b.id,0,die_roll=1);self.schedule(spot)
        p=evaluate_snapshot(self.snapshot()).proposals[0]
        self.assertEqual(p.outcome,'failure');self.assertEqual(p.effects,())

    def test_spot_blockers_and_geometry_are_detached(self):
        spot=SpotAction(self.world,self.a.id,self.b.id,0,die_roll=20);self.schedule(spot)
        self.a.set_geometry(AxisAlignedBox(.1,.1,.1))
        s=self.snapshot();self.b.geometry=None
        self.assertEqual(evaluate_snapshot(s).proposals[0].outcome,'success')
        self.assertEqual(evaluate_snapshot(self.snapshot()).proposals[0].outcome,'unmodeled_target')

    def test_rng_repeat_and_retry_after_unexpected_failure(self):
        action=self.strike();self.schedule(action);s=self.snapshot()
        expected=evaluate_snapshot(s)
        with patch('action_evaluation.damage_path',side_effect=RuntimeError('injected')):
            with self.assertRaises(RuntimeError):self.unchanged(lambda:evaluate_snapshot(s))
        self.assertEqual(self.unchanged(lambda:evaluate_snapshot(s)),expected)

    def test_unknown_object_identity_fails_before_draw(self):
        action=self.strike();self.schedule(action);self.enc.time=math.ceil(action.end_time)
        action.instrument_id='missing'
        with patch.object(_ProvisionalRandom,'roll',side_effect=AssertionError('unsafe draw')):
            with self.assertRaises((EvaluationIntegrityError,UnsupportedEvaluation)):
                capture_snapshot(self.enc,int(self.enc.time))

    def test_opaque_action_callback_rejected_without_invocation(self):
        action=self.strike();self.schedule(action);action.resolve=Mock(side_effect=AssertionError('unsafe'))
        with self.assertRaises(UnsupportedEvaluation):self.snapshot()
        action.resolve.assert_not_called()

    def test_opaque_nested_strategy_rejected_without_callback(self):
        action=self.strike();self.schedule(action)
        class Opaque:
            def __float__(self):raise AssertionError('unsafe')
        self.a.strategy.attack=Opaque()
        with self.assertRaises(UnsupportedEvaluation):self.snapshot()

    def test_noninteger_fence_refused(self):
        with self.assertRaises(EvaluationIntegrityError):capture_snapshot(self.enc,0)
        self.enc.time=1.5
        with self.assertRaises(EvaluationIntegrityError):capture_snapshot(self.enc,1)

    def test_reality_inquiry_contract_refuses_realization(self):
        from history_conversation import AskAboutPastAction
        generate=Mock(side_effect=AssertionError('unsafe realization'))
        action=AskAboutPastAction(self.world,self.a.id,self.b.id,0,episode_time=-1,topic='birth',generate=generate)
        request=future_reality_request(action)
        self.assertEqual(request.objective_key,('personal-history',self.b.id,-1,'birth'))
        # Deliberate unsupported raw fixture: must refuse before touching history.
        self.world.event_history[action.id]=action;self.enc.pending_action_list.append(action.id)
        self.enc.time=1
        with self.assertRaises(UnsupportedEvaluation):capture_snapshot(self.enc,1)
        generate.assert_not_called()

    def shield(self, actor):
        wid = self.world.make_weapon_for_being(actor.id, 'Small shield', 'Shield')
        self.world.arm_being(actor.id, wid, 'shield hand')
        return self.world.get_object_by_id(wid)

    def test_shield_interception_full_impact_and_armor_followthrough(self):
        action=self.strike();self.schedule(action)
        shield=self.shield(self.b);armor=self.armor(self.b)
        p=self.scripted(self.snapshot(),[15,4,1]).proposals[0]
        impacts=[x for x in p.effects if isinstance(x,ProtectionEffect)]
        self.assertEqual([x.layer for x in impacts],['shield','armor'])
        self.assertEqual(impacts[0].incoming,4)
        self.assertIn(DamageEffect(action.id,shield.id,4,'shield'),p.effects)
        self.assertEqual(impacts[1].incoming,impacts[0].passed)
        self.assertEqual(shield.hit_points(),shield.original.hit_points)

    def test_shield_miss_passes_full_damage(self):
        action=self.strike();self.schedule(action);shield=self.shield(self.b)
        p=self.scripted(self.snapshot(),[15,4,10]).proposals[0]
        self.assertFalse(any(isinstance(x,DamageEffect) and x.target_id==shield.id for x in p.effects))
        self.assertIn(DamageEffect(action.id,self.b.id,4,'body'),p.effects)

    def test_shield_and_critical_rng_match_live(self):
        action=self.strike();self.schedule(action);shield=self.shield(self.b)
        s=self.snapshot();saved=random.getstate()
        try:
            for seed in range(60):
                random.seed(seed);snapshot=replace(s,rng_state=random.getstate())
                expected=evaluate_snapshot(snapshot)
                action.combat_result=None;action.hit_type=None
                self.a.current.hit_points=100;self.b.current.hit_points=100
                shield.current.hit_points=s.entity(shield.id).hp
                action.resolve(self.enc.difficulty_class)
                self.assertEqual(expected.proposals[0].outcome,action.hit_type)
                self.assertEqual(expected.provisional_rng_state,random.getstate())
                amount=sum(x.amount for x in expected.proposals[0].effects if isinstance(x,DamageEffect) and x.target_id==shield.id)
                self.assertEqual(shield.hit_points(),max(0,s.entity(shield.id).hp-amount))
        finally:random.setstate(saved)

    def test_two_shield_impacts_share_snapshot_no_degradation(self):
        one,two=self.strike(),self.strike(self.w2);self.schedule(one,two)
        shield=self.shield(self.b);s=self.snapshot()
        result=self.scripted(s,[15,4,1,15,4,1])
        self.assertEqual([sum(x.amount for x in p.effects if isinstance(x,DamageEffect) and x.target_id==shield.id)
                          for p in result.proposals],[4,4])
        self.assertEqual(shield.hit_points(),s.entity(shield.id).hp)

    def test_native_block_applies_hit_penalty_and_adopted_shield_stopping_bonus(self):
        shield = self.shield(self.b)
        strike = self.strike()
        strike.end_time = 2  # Small shield: two seconds, exactly to impact.
        block = MeleeDefense(self.enc, self.b.id, self.a.id, kind='block',
                             target_action_id='incoming', weapon_id=shield.id)
        draft = self.enc.propose_choice([ChoiceMember('block', block, 'incoming'),
                                         ChoiceMember('incoming', strike)])
        checked = self.enc.validate_choice(draft)
        self.assertTrue(checked.valid, checked.diagnostics)
        choice = self.enc.accept_valid_choice(checked)
        self.enc.publish_choice(choice)
        self.enc.time = 2
        snapshot = capture_snapshot(self.enc, 2)

        # A 13 would hit at the native DC, but the adopted Block -4 makes it miss.
        missed_result = self.scripted(snapshot, [13])
        self.assertEqual(missed_result.proposals[0].outcome, 'blocked')
        self.assertEqual(missed_result.proposals[1].outcome, 'miss')
        reconcile_boundary(snapshot, missed_result)

        # Reset the snapshot's RNG for a higher hit roll; Small shield size 2
        # becomes effective size 3 and stops 2 additional damage.
        hit_result = self.scripted(snapshot, [15, 4, 1])
        self.assertEqual(hit_result.proposals[1].outcome, 'normal')
        reconcile_boundary(snapshot, hit_result)
        impact = next(row for row in hit_result.proposals[1].effects if isinstance(row, ProtectionEffect))
        self.assertEqual((impact.target_id, impact.incoming, impact.passed, impact.intercepted),
                         (shield.id, 4, 0, True))

    def test_revision61_dodge_can_be_prepared_without_an_attack_and_uses_dexterity_pool(self):
        self.b.set_ability('DEX', 14)
        self.b.set_skill_level(self.world.get_skill_dictionary(), 'tumble', 4)
        action = MeleeDefense(self.enc, self.b.id, kind='dodge',
                              strategy=Strategy(defense=5, timing=1))
        packet = self.enc.prepare_action(action)
        self.assertEqual((packet.start_time, packet.end_time), (0, 1))
        self.assertEqual(action.strategy_pool, 6)
        self.enc.schedule_action(action)
        result = self.scripted(self.snapshot(1), [])
        self.assertEqual(result.proposals[0].outcome, 'ready')
        reconcile_boundary(result.snapshot, result)

    def test_revision61_parry_uses_explicit_defender_weapon_motion_timing(self):
        weapon_id = self.world.make_weapon_for_being(self.b.id, 'Longsword', 'Parry timing sword')
        self.world.arm_being(self.b.id, weapon_id, 'right hand')
        self.b.set_weapon_skill_level(self.world.get_weapon_dictionary(), 'Longsword', 2)
        weapon = self.world.get_object_by_id(weapon_id)
        self.assertNotEqual(weapon.St(), weapon.Tt())
        swing = MeleeDefense(self.enc, self.b.id, kind='parry', weapon_id=weapon_id,
                             parry_motion='swing')
        thrust = MeleeDefense(self.enc, self.b.id, kind='parry', weapon_id=weapon_id,
                              parry_motion='thrust')
        self.assertEqual(self.enc.prepare_action(swing).end_time, weapon.St() - 1)
        self.assertEqual(self.enc.prepare_action(thrust).end_time, weapon.Tt() - 1)

    def test_native_block_refuses_wrong_timing_and_unshielded_actor(self):
        shield = self.shield(self.b)
        strike = self.strike()
        strike.end_time = 3
        block = MeleeDefense(self.enc, self.b.id, self.a.id, kind='block',
                             target_action_id='incoming', weapon_id=shield.id)
        draft = self.enc.propose_choice([ChoiceMember('block', block, 'incoming'),
                                         ChoiceMember('incoming', strike)])
        validation = self.enc.validate_choice(draft)
        self.assertFalse(validation.valid)
        self.assertIn('Block must complete its shield-size timing',
                      ' '.join(row.reason for row in validation.diagnostics))
        self.assertEqual(self.enc.pending_action_list, [])

        self.b.current.body_parts['shield hand'] = None
        strike.end_time = 2
        validation = self.enc.validate_choice(self.enc.propose_choice([
            ChoiceMember('block', MeleeDefense(self.enc, self.b.id, self.a.id,
                kind='block', target_action_id='incoming', weapon_id=shield.id), 'incoming'),
            ChoiceMember('incoming', strike)]))
        self.assertFalse(validation.valid)
        self.assertIn('equipped native shield',
                      ' '.join(row.reason for row in validation.diagnostics))
        self.assertEqual(self.enc.pending_action_list, [])

    def test_common_geometry_blocker_is_frozen(self):
        action=self.strike();self.schedule(action)
        # Another positioned Being supplies a modeled physical blocker.
        c=self.world.get_object_by_id(self.world.make_being('Human','C'))
        c.set_position(CartesianPosition(.75,0,0));c.set_geometry(Sphere(.2))
        c.set_visual_occlusion(VisualOcclusion(0));self.enc.add_being(c.id)
        s=self.snapshot();c.set_position(CartesianPosition(5,0,0))
        p=evaluate_snapshot(s).proposals[0]
        self.assertEqual(p.outcome,'blocked')
        self.assertEqual(evaluate_snapshot(s).trace,())
        self.assertEqual(s.path(self.a.id,self.b.id).intersections[0].entity_id,c.id)

    def test_group_envelopes_are_not_physical_blockers_in_frozen_melee(self):
        import json
        from action_evaluation import DamageEffect

        action = self.strike()
        self.schedule(action)
        config = json.loads((ROOT / 'examples' / 'nomadic_group.json').read_text())
        groups = []
        for identity, opacity in (('owning-envelope', 0), ('unrelated-envelope', 1)):
            local = json.loads(json.dumps(config))
            local['group_id'] = identity
            group = StatisticalGroup(identity, identity, local, local['seed'])
            group.set_position(CartesianPosition(.75, 0, 0))
            group.set_geometry(Sphere(.6))
            group.set_visual_occlusion(VisualOcclusion(opacity))
            group.counts()  # Composition is known; no individual is realized.
            self.world.add_object(group)
            self.enc.add_object(group.id)
            groups.append(group)

        self.enc.time = 4
        snapshot = capture_snapshot(self.enc, 4, _objective=True)
        optical = snapshot.path(self.a.id, self.b.id)
        physical = snapshot.physical_path(self.a.id, self.b.id)
        self.assertEqual({row.entity_id for row in optical.intersections},
                         {group.id for group in groups})
        self.assertEqual(optical.status, 'blocked')  # opaque aggregate still occludes Spot.
        self.assertEqual(physical.intersections, ())
        self.assertEqual(physical.unmodeled_entity_ids, ())
        self.assertEqual(snapshot.melee_status(snapshot.actions[action.id]),
                         ('in_reach', 1.5))
        self.assertEqual(action._status(self.enc), ('in_reach', 1.5))
        self.assertEqual([group.materialized_count for group in groups], [0, 0])

        groups[1].set_visual_occlusion(VisualOcclusion(0))
        transparent_snapshot = capture_snapshot(self.enc, 4, _objective=True)
        self.assertEqual(transparent_snapshot.path(self.a.id, self.b.id).status,
                         'clear')
        self.assertEqual(transparent_snapshot.physical_path(self.a.id, self.b.id)
                         .intersections, ())
        self.assertEqual(snapshot.path(self.a.id, self.b.id).status,
                         'blocked')  # Existing frozen optical view is detached.

        values = iter((15, 4))
        def roll(context, dice):
            value = next(values)
            context.trace.append(RandomDraw(context.action_id, dice,
                int(dice[2:].split('+')[0]), value))
            return value
        before_rng = random.getstate()
        with patch.object(_ProvisionalRandom, 'roll', roll):
            result = evaluate_snapshot(snapshot)
        self.assertEqual(random.getstate(), before_rng)
        proposal = result.proposals[0]
        self.assertEqual(proposal.outcome, 'normal')
        self.assertIn(DamageEffect(action.id, self.b.id, 4, 'body'), proposal.effects)
        self.assertTrue(all(group.counts()['humans'] > 0 for group in groups))
        self.assertEqual([group.materialized_count for group in groups], [0, 0])

    def test_unmodeled_group_is_ignored_but_unmodeled_physical_object_stays_uncertain(self):
        import json
        from object import ObjectDefinition, ObjectInstance

        action = self.strike()
        self.schedule(action)
        config = json.loads((ROOT / 'examples' / 'nomadic_group.json').read_text())
        config['group_id'] = 'unmodeled-group'
        group = StatisticalGroup('Unmodeled group', 'unmodeled-group', config,
                                 config['seed'])
        group.set_position(CartesianPosition(.75, 0, 0))
        group.counts()
        self.world.add_object(group)
        self.enc.add_object(group.id)
        self.enc.time = 4
        snapshot = capture_snapshot(self.enc, 4, _objective=True)
        self.assertIn(group.id, snapshot.path(self.a.id, self.b.id).unmodeled_entity_ids)
        self.assertEqual(snapshot.melee_status(snapshot.actions[action.id]),
                         ('in_reach', 1.5))

        obstacle = ObjectInstance(
            ObjectDefinition('unmodeled obstacle', 0, 0, 0, 0, 0, 0, 0),
            name='Unmodeled physical obstacle')
        obstacle.set_position(CartesianPosition(.75, 0, 0))
        self.world.add_object(obstacle)
        self.enc.add_object(obstacle.id)
        physical_snapshot = capture_snapshot(self.enc, 4, _objective=True)
        status = physical_snapshot.melee_status(physical_snapshot.actions[action.id])
        self.assertEqual(status, ('uncertain_path', 1.5))
        self.assertEqual(action._status(self.enc), ('uncertain_path', 1.5))

    def test_defense_metadata_and_equipment_detached(self):
        attack=self.strike()
        defense=MeleeDefense(self.enc,self.b.id,self.a.id,kind='parry',parry_motion='swing',target_action_id=attack.id,weapon_id=self.w3)
        self.schedule(attack,defense);s=self.snapshot()
        defense.target_action_id='corrupted';self.b.body_part_remove_object('right hand')
        self.world.get_object_by_id(self.w3).current.obj_type='corrupted'
        self.assertEqual(s.actions[defense.id].data['target_action_id'],attack.id)
        result=self.scripted(s,[20,1])
        self.assertTrue(result.proposals[0].defenses[0].success)

    def test_legacy_fatigue_adjustment_preserved_without_qb_activation(self):
        action=self.strike();self.schedule(action);self.a.set_fatigue_level(4)
        s=self.snapshot()
        self.assertEqual(self.scripted(s,[11]).proposals[0].outcome,'miss')
        self.a.set_physical_fatigue(.1,.1)
        self.assertEqual(self.scripted(self.snapshot(),[11]).proposals[0].outcome,'miss')

    def test_profile_and_qb_views_reuse_existing_frame(self):
        from physiology_registry import PhysiologyRegistry, PhysiologyDefinition
        from encounter_fatigue_bridge import FrozenFatigueFrame
        registry=PhysiologyRegistry((PhysiologyDefinition('human@1',model='human-r4'),))
        self.enc.set_physiology_registry(registry)
        for actor in (self.a,self.b):actor.set_physiology_id('human@1')
        self.schedule(self.strike());s=self.snapshot()
        frame=FrozenFatigueFrame((self.a,self.b),registry=registry)
        self.assertEqual(dict(s.fatigue[self.a.id]),frame.view(self.a.id).to_dict())
        profile=s.physiology[self.a.id]['ordinary']
        self.assertEqual(profile['version_hash'],frame.physiology(self.a.id).version_hash)
        with self.assertRaises(TypeError):profile['profile']['peak_floor']=999

    def test_base_action_uses_native_combat_without_melee_reach_gate(self):
        action=Action(self.world,0,None,'thrust',self.a.id,self.b.id,self.w1)
        self.schedule(action);self.b.set_position(CartesianPosition(100,0,0))
        p=self.scripted(self.snapshot(),[15,3]).proposals[0]
        self.assertEqual(p.outcome,'normal')
        self.assertFalse(any(isinstance(x,PracticeEffect) for x in p.effects))

    def test_interrupted_defense_is_not_successful_dependency(self):
        attack=self.strike()
        defense=MeleeDefense(self.enc,self.b.id,self.a.id,kind='dodge',target_action_id=attack.id)
        self.schedule(attack,defense);self.enc.cancel_action(defense.id)
        result=self.scripted(self.snapshot(),[15,3])
        self.assertEqual([p.outcome for p in result.proposals],['interrupted','normal'])
        self.assertEqual(result.proposals[1].defenses,())

    def test_unavailable_target_and_actor_are_legitimate_outcomes(self):
        action=self.strike();self.schedule(action);self.b.set_hit_points(0)
        self.assertEqual(evaluate_snapshot(self.snapshot()).proposals[0].outcome,'target_down')
        self.a.set_hit_points(0)
        self.assertEqual(evaluate_snapshot(self.snapshot()).proposals[0].outcome,'unable_to_act')

    def test_unsupported_geometry_refused_before_callback(self):
        action=self.strike();self.schedule(action)
        class UnsafeSphere(Sphere):
            def segment_interval(self,*args):raise AssertionError('unsafe geometry')
        self.b.set_geometry(UnsafeSphere(.2))
        with self.assertRaises(UnsupportedEvaluation):self.snapshot()

    def test_opaque_fatigue_does_not_execute_numeric_callbacks(self):
        action=self.strike();self.schedule(action)
        class Unsafe:
            def __lt__(self,other):raise AssertionError('unsafe fatigue')
            def __float__(self):raise AssertionError('unsafe fatigue')
        object.__setattr__(self.a.physical_fatigue,'q',Unsafe())
        with self.assertRaises(UnsupportedEvaluation):self.snapshot()

    def test_native_encounter_entry_point_does_not_progress(self):
        action=self.strike();self.schedule(action);s=self.snapshot()
        got=self.unchanged(lambda:self.enc.capture_evaluation_snapshot(s.boundary))
        self.assertEqual(got,s)

    def test_group_observation_request_cannot_realize_counts(self):
        from group_observation import ObserveGroupAction
        # Constructor-independent declaration fixture: no group method is read.
        action=object.__new__(ObserveGroupAction)
        action.__dict__.update(id='inquiry',actor_id=self.a.id,target_id='group',event_type='observe_group')
        request=future_reality_request(action)
        self.assertEqual(request.objective_key,('group-composition','group'))
        self.assertTrue(request.requires_shared_candidate)
        self.world.event_history[action.id]=action;self.enc.pending_action_list.append(action.id)
        self.enc.time=1
        with self.assertRaises(UnsupportedEvaluation):capture_snapshot(self.enc,1)


    def test_target_owns_fatal_save_and_actor_owns_reflex_save(self):
        action=self.strike();self.schedule(action)
        self.b.current.experience=40000
        p=self.scripted(self.snapshot(),[20,20,7,3,2]).proposals[0]
        self.assertEqual(p.outcome,'critical')  # Target's experience makes 7 save.
        self.b.current.experience=0;self.a.current.experience=40000
        p=self.scripted(self.snapshot(),[1,2,7]).proposals[0]
        self.assertEqual(p.outcome,'spectacular miss')  # Actor's experience saves.

    def test_two_parries_use_distinct_reserved_weapons_and_keep_all_outcomes(self):
        other=self.world.make_weapon_for_being(self.b.id,'Dagger','Other parry knife')
        self.world.arm_being(self.b.id,other,'left hand')
        attack=self.strike()
        one=MeleeDefense(self.enc,self.b.id,self.a.id,kind='parry',parry_motion='swing',target_action_id=attack.id,weapon_id=self.w3)
        two=MeleeDefense(self.enc,self.b.id,self.a.id,kind='parry',parry_motion='swing',target_action_id=attack.id,weapon_id=other)
        self.schedule(attack,one,two)
        result=self.scripted(self.snapshot(),[1,20,20,1])
        self.assertEqual([p.outcome for p in result.proposals],['failed','deflected','parried'])
        self.assertEqual([d.success for d in result.proposals[-1].defenses],[False,True])
        self.assertEqual({r.object_id for r in self.enc.active_reservations},{self.w1,self.w3,other})
        self.assertIsNone(attack.defended_by)

    def test_finished_boundary_is_not_a_pre_action_snapshot(self):
        self.enc.step(1)
        with self.assertRaises(EvaluationIntegrityError):self.enc.capture_evaluation_snapshot(1)


    def test_live_damage_die_fallback_remains_separate_from_pure_failure(self):
        action=self.strike();self.schedule(action);s=self.snapshot()
        with patch('action.roll_dice',side_effect=ValueError('bad die')), patch('builtins.print'):
            action.do_normal_hit()
        self.assertEqual(self.b.hit_points(),100)
        with patch('action_evaluation._ProvisionalRandom.roll',side_effect=ValueError('bad die')):
            with self.assertRaises(ValueError):self.unchanged(lambda:evaluate_snapshot(s))
