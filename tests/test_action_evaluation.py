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
from activities import RunAction, SpotAction
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
        self.enc.schedule_choice(actions)

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
