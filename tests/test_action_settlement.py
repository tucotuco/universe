"""Increment 5A: inactive native Target-owned reduction, never publication."""
from dataclasses import fields, FrozenInstanceError, replace
from itertools import permutations
from pathlib import Path
import math
import random
import sys
from types import MappingProxyType
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from action import Action
from action_evaluation import (ActionProposal, DamageEffect, FatalEffect, ProtectionEffect,
    PracticeEffect, AwarenessEffect, DefenseEffect, EffectIdentity, IdentifiedEffect,
    bind_evaluation_result, capture_snapshot, evaluate_snapshot, UnsupportedEvaluation,
    _ProvisionalRandom, RandomDraw)
from action_settlement import reconcile_boundary, SettlementIntegrityError
from activities import RunAction, SpotAction
from encounter import Encounter
from library import Library
from melee_combat import MeleeStrike
from melee_defense import MeleeDefense
from spatial.state import CartesianPosition
from spatial.geometry import Sphere
from strategy import Strategy
from universe import Universe


class TestActionSettlement(unittest.TestCase):
    def setUp(self):
        self.world = Universe('Candidate', library=Library(config_dir=str(ROOT / 'src/config')))
        self.a = self.world.get_object_by_id(self.world.make_being('Human', 'A'))
        self.b = self.world.get_object_by_id(self.world.make_being('Human', 'B'))
        self.a.set_position(CartesianPosition(0, 0, 0)); self.b.set_position(CartesianPosition(1.5, 0, 0))
        for being in (self.a, self.b):
            being.set_geometry(Sphere(.25)); being.set_hit_points(100)
        self.w1 = self.world.make_weapon_for_being(self.a.id, 'Dagger', 'Knife A')
        self.w2 = self.world.make_weapon_for_being(self.a.id, 'Dagger', 'Knife A2')
        self.w3 = self.world.make_weapon_for_being(self.b.id, 'Dagger', 'Knife B')
        for being, wid, part in [(self.a,self.w1,'right hand'),(self.a,self.w2,'left hand'),(self.b,self.w3,'right hand')]:
            self.world.arm_being(being.id,wid,part)
        self.enc=Encounter(self.world,10,0,initiated=True)
        self.enc.add_being(self.a.id);self.enc.add_being(self.b.id)
        self.enc.mark_aware(self.a.id,self.b.id);self.enc.mark_aware(self.b.id,self.a.id)
        self.world.add_event(self.enc)

    def attack(self, weapon=None, extra=0, melee=False):
        if melee:
            return MeleeStrike(self.enc,self.a.id,self.b.id,weapon or self.w1,motion='thrust',reach=2,strategy=Strategy(extra_damage=extra))
        return Action(self.world,0,None,'thrust',self.a.id,self.b.id,weapon or self.w1,strategy=Strategy(extra_damage=extra))

    def snapshot(self,*actions):
        if actions:self.enc.schedule_choice(actions)
        boundary=max((math.ceil(self.world.get_event_by_id(k).end_time) for k in self.enc.pending_action_list),default=1)
        # Test fixture supplies the inactive caller-owned pre-action fence.
        self.enc.time=boundary
        return capture_snapshot(self.enc,boundary)

    def evaluate(self,snapshot,rolls):
        values=iter(rolls)
        def roll(ctx,dice):
            v=next(values);ctx.trace.append(RandomDraw(ctx.action_id,dice,int(dice[2:].split('+')[0]),v));return v
        with patch.object(_ProvisionalRandom,'roll',roll):return evaluate_snapshot(snapshot)

    def unchanged(self,operation):
        before=self.world.to_json();rng=random.getstate();choices=(self.enc.choice_state,self.enc.active_reservations)
        try:return operation()
        finally:
            self.assertEqual(self.world.to_json(),before);self.assertEqual(random.getstate(),rng)
            self.assertEqual((self.enc.choice_state,self.enc.active_reservations),choices)

    def build(self,snapshot,result):
        frozen_inputs=(repr(snapshot),repr(result))
        try:return self.unchanged(lambda:reconcile_boundary(snapshot,result))
        finally:self.assertEqual((repr(snapshot),repr(result)),frozen_inputs)

    def rebind(self,snapshot,result,proposals):
        return bind_evaluation_result(snapshot,tuple(proposals),result.trace,result.provisional_rng_state)

    def test_additive_body_damage_projects_below_zero(self):
        self.b.set_hit_points(12)
        one,two=self.attack(extra=4),self.attack(self.w2,extra=3)
        s=self.snapshot(one,two);result=self.evaluate(s,[15,4,15,4]);c=self.build(s,result);target=c.target(self.b.id)
        self.assertEqual((target.starting_hp,target.actual_damage,target.projected_hp),(12,15,-3))
        self.assertEqual([row.effect.amount for row in target.incoming],[8,7])
        self.assertEqual([row.identity.source_action_id for row in target.incoming],[one.id,two.id])
        self.assertEqual(self.b.hit_points(),12)
        self.assertEqual(c.effects_of(one.id),target.effects_from(one.id))
        self.assertEqual(c.target(self.a.id).outgoing_effect_ids,tuple(row.identity for row in c.effects.values()))

    def test_armor_impacts_project_negative_without_degrading_protection(self):
        armor=self.world.get_object_by_id(self.world.make_armor_for_being(self.b.id,'Leather armor','Leather'))
        armor.current.hit_points=6
        s=self.snapshot(self.attack(),self.attack(self.w2));result=self.evaluate(s,[15,4,15,4]);c=self.build(s,result)
        self.assertEqual(c.target(armor.id).projected_hp,-2)
        self.assertEqual(c.target(armor.id).actual_damage,8)
        self.assertEqual(c.target(self.b.id).projected_hp,94)
        self.assertEqual(armor.hit_points(),6)
        self.assertEqual([r.effect.passed for r in c.target(armor.id).incoming if type(r.effect) is ProtectionEffect],[3,3])

    def test_passive_shield_impacts_accumulate_below_zero(self):
        shield_id=self.world.make_weapon_for_being(self.b.id,'Small shield','Shield')
        self.world.arm_being(self.b.id,shield_id,'shield hand')
        shield=self.world.get_object_by_id(shield_id);shield.current.hit_points=6
        s=self.snapshot(self.attack(),self.attack(self.w2));result=self.evaluate(s,[15,4,1,15,4,1]);c=self.build(s,result)
        self.assertEqual(c.target(shield_id).projected_hp,-2)
        self.assertEqual([r.effect.amount for r in c.target(shield_id).incoming if type(r.effect) is DamageEffect],[4,4])
        self.assertEqual(c.target(self.b.id).projected_hp,100-2*(4-int(shield.get_weapon_size())) )
        self.assertNotIn(shield_id,{r.object_id for r in self.enc.active_reservations})

    def test_negative_hp_real_damage_cannot_heal(self):
        self.b.set_hit_points(-12)
        s=self.snapshot(self.attack(extra=2));r=self.evaluate(s,[15,4])
        self.assertEqual(self.build(s,r).target(self.b.id).projected_hp,-18)

    def test_fatal_flags_nonstacking_without_damage(self):
        self.b.set_hit_points(20)
        s=self.snapshot(self.attack(),self.attack(self.w2));r=self.evaluate(s,[20,20,1,20,20,1]);t=self.build(s,r).target(self.b.id)
        self.assertEqual(t.projected_hp,-10);self.assertEqual(t.actual_damage,0);self.assertEqual(len(t.fatal_effect_ids),2)
        self.assertTrue(all(type(row.effect) is FatalEffect for row in t.incoming))

    def test_fatal_and_independent_real_damage(self):
        self.b.set_hit_points(20)
        s=self.snapshot(self.attack(),self.attack(self.w2,extra=2));r=self.evaluate(s,[20,20,1,15,4]);t=self.build(s,r).target(self.b.id)
        self.assertEqual((t.projected_hp,t.actual_damage),(-16,6))

    def test_negative_hp_fatal_alone_and_fatal_plus_real_damage(self):
        self.b.set_hit_points(-12)
        s=self.snapshot(self.attack());r=self.evaluate(s,[20,20,1])
        self.assertEqual(self.build(s,r).target(self.b.id).projected_hp,-12)
        p=r.proposals[0]
        # Explicit composed typed-effect fixture: native fatal itself rolls no damage.
        extra=DamageEffect(p.action_id,self.b.id,6,'body')
        combined=self.rebind(s,r,(replace(p,effects=p.effects+(extra,)),))
        self.assertEqual(self.build(s,combined).target(self.b.id).projected_hp,-18)
        self.assertEqual(self.build(s,combined).target(self.b.id).actual_damage,6)

    def test_one_fatal_source_with_explicit_actual_damage_counts_once(self):
        self.b.set_hit_points(20)
        s=self.snapshot(self.attack());r=self.evaluate(s,[20,20,1]);p=r.proposals[0]
        r=self.rebind(s,r,(replace(p,effects=p.effects+(DamageEffect(p.action_id,self.b.id,6,'body'),)),))
        c=self.build(s,r)
        self.assertEqual(c.target(self.b.id).projected_hp,-16)
        self.assertEqual(len(c.effects_of(p.action_id)),2)

    def test_critical_and_self_hit_keep_distinct_recipients_and_components(self):
        one,two=self.attack(),self.attack(self.w2)
        s=self.snapshot(one,two);r=self.evaluate(s,[20,15,4,3,1,1,2]);c=self.build(s,r)
        self.assertEqual(c.target(self.b.id).projected_hp,93)
        self.assertEqual(c.target(self.a.id).projected_hp,98)
        self.assertEqual({e.effect.component for e in c.target(self.b.id).incoming},{'body','critical_bypass'})
        self.assertEqual({e.identity.source_action_id for e in c.target(self.a.id).incoming},{two.id})

    def test_results_have_no_target_hp_snapshots(self):
        s=self.snapshot(self.attack());r=self.evaluate(s,[15,4]);c=self.build(s,r)
        for p in c.actions.values():
            self.assertFalse(any('hp' in f.name for f in fields(p)))
            for e in p.effects:self.assertFalse(any('hp' in f.name for f in fields(e)))
        self.assertEqual(c.target(self.b.id).projected_hp,96)
        self.assertFalse(hasattr(c,'projected_hp'))

    def test_permutations_preserve_candidate_and_causal_identities(self):
        s=self.snapshot(self.attack(),self.attack(self.w2));r=self.evaluate(s,[15,4,20,15,3,2]);expected=self.build(s,r)
        for proposed in permutations(r.proposals):
            for effects in permutations(r.identified_effects):
                shuffled=replace(r,proposals=proposed,identified_effects=effects)
                self.assertEqual(self.build(s,shuffled),expected)
        reversed_inner=tuple(replace(p,effects=tuple(reversed(p.effects))) for p in reversed(r.proposals))
        self.assertEqual(self.build(s,replace(r,proposals=reversed_inner)),expected)

    def test_float_aggregation_is_order_independent(self):
        s=self.snapshot(self.attack(),self.attack(self.w2));r=self.evaluate(s,[15,4,15,4])
        ps=tuple(replace(p,effects=(replace(p.effects[0],amount=v),)) for p,v in zip(r.proposals,(.1,.2)))
        r=self.rebind(s,r,ps);expected=self.build(s,r)
        self.assertEqual(expected.target(self.b.id).actual_damage,math.fsum((.1,.2)))
        self.assertEqual(self.build(s,replace(r,identified_effects=tuple(reversed(r.identified_effects)))),expected)

    def test_frozen_candidate_and_detached_records(self):
        s=self.snapshot(self.attack());r=self.evaluate(s,[15,4]);c=self.build(s,r);t=c.target(self.b.id)
        with self.assertRaises(FrozenInstanceError):t.projected_hp=0
        with self.assertRaises(TypeError):c.targets[self.b.id]=None
        with self.assertRaises(TypeError):c.effects[t.incoming[0].identity]=None
        with self.assertRaises(FrozenInstanceError):t.incoming[0].effect.amount=0
        self.assertIsNot(t.incoming[0].effect,r.proposals[0].effects[0])
        self.b.set_hit_points(1)
        self.assertEqual(t.projected_hp,96)
        self.assertFalse(c.ready_for_publication)
        self.assertFalse(hasattr(c,'apply'))

    def test_duplicate_effect_identity_rejected_without_partial_candidate(self):
        s=self.snapshot(self.attack());r=self.evaluate(s,[15,4]);r=replace(r,identified_effects=r.identified_effects*2)
        with self.assertRaisesRegex(SettlementIntegrityError,'duplicate effect identity'):self.build(s,r)

    def test_same_contribution_under_different_id_is_rejected(self):
        s=self.snapshot(self.attack());r=self.evaluate(s,[15,4]);row=r.identified_effects[0]
        duplicate=replace(row,identity=replace(row.identity,slot=1))
        p=replace(r.proposals[0],effects=r.proposals[0].effects*2)
        r=replace(r,proposals=(p,),identified_effects=(row,duplicate))
        with self.assertRaisesRegex(SettlementIntegrityError,'duplicate causal'):self.build(s,r)

    def test_contradictory_effect_recipient_rejected(self):
        s=self.snapshot(self.attack());r=self.evaluate(s,[15,4]);row=r.identified_effects[0]
        r=replace(r,identified_effects=(replace(row,effect=replace(row.effect,target_id=self.a.id)),))
        with self.assertRaises(SettlementIntegrityError):self.build(s,r)

    def test_unknown_recipient_and_source_refused(self):
        s=self.snapshot(self.attack());r=self.evaluate(s,[15,4]);row=r.identified_effects[0]
        for effect in [replace(row.effect,target_id='missing'),replace(row.effect,source_action_id='missing')]:
            with self.assertRaises(SettlementIntegrityError):self.build(s,replace(r,identified_effects=(replace(row,effect=effect),)))

    def test_wrong_boundary_encounter_and_snapshot_refused(self):
        s=self.snapshot(self.attack());r=self.evaluate(s,[15,4]);row=r.identified_effects[0]
        for key in [replace(row.identity,boundary=s.boundary+1),replace(row.identity,encounter_id='foreign')]:
            with self.assertRaises(SettlementIntegrityError):self.build(s,replace(r,identified_effects=(replace(row,identity=key),)))
        with self.assertRaises(SettlementIntegrityError):self.build(replace(s),r)

    def test_complete_batch_required_and_no_duplicate_action(self):
        s=self.snapshot(self.attack(),self.attack(self.w2));r=self.evaluate(s,[15,4,15,4])
        subset=evaluate_snapshot(s,(r.proposals[0].action_id,))
        with self.assertRaises(SettlementIntegrityError):self.build(s,subset)
        with self.assertRaises(SettlementIntegrityError):self.build(s,replace(r,proposals=r.proposals*2))

    def test_missing_or_mismatched_effect_envelope_refused(self):
        s=self.snapshot(self.attack());r=self.evaluate(s,[15,4]);row=r.identified_effects[0]
        for broken in [replace(r,identified_effects=()),replace(r,identified_effects=(replace(row,effect=replace(row.effect,amount=3)),))]:
            with self.assertRaises(SettlementIntegrityError):self.build(s,broken)

    def test_invalid_damage_numbers_refused(self):
        s=self.snapshot(self.attack());r=self.evaluate(s,[15,4]);p=r.proposals[0]
        for amount in (-1,float('nan'),float('inf'),True):
            changed=replace(p,effects=(replace(p.effects[0],amount=amount),))
            with self.assertRaises((SettlementIntegrityError,ValueError)):self.build(s,self.rebind(s,r,(changed,)))

    def test_opaque_effect_rejected_without_callback(self):
        s=self.snapshot(self.attack());r=self.evaluate(s,[15,4]);called=Mock()
        class Opaque:
            def __getattribute__(self,name):called();raise AssertionError('unsafe')
        p=replace(r.proposals[0],effects=(Opaque(),))
        with self.assertRaises(UnsupportedEvaluation):self.build(s,self.rebind(s,r,(p,)))
        called.assert_not_called()

    def test_unsupported_snapshot_family_refuses_without_fallback(self):
        s=self.snapshot(self.attack());r=self.evaluate(s,[15,4]);aid=r.proposals[0].action_id
        future=replace(s.actions[aid],family='observe_group',boundary=s.boundary+1,nominal_end=s.boundary+1)
        bad=replace(s,actions=MappingProxyType({**s.actions,'future':replace(future,id='future',order=1)}))
        r=self.rebind(bad,r,r.proposals)
        with self.assertRaises(UnsupportedEvaluation):self.build(bad,r)

    def test_failed_target_projection_discards_local_work_and_retry_is_identical(self):
        s=self.snapshot(self.attack(),self.attack(self.w2));r=self.evaluate(s,[15,4,15,4]);expected=self.build(s,r)
        from action_settlement import _project_hp
        called=[]
        def fail(start,rows):
            called.append(1)
            if len(called)==2:raise RuntimeError('injected projection fault')
            return _project_hp(start,rows)
        with patch('action_settlement._project_hp',fail):
            with self.assertRaises(RuntimeError):self.build(s,r)
        self.assertEqual(self.build(s,r),expected)

    def test_reconciliation_never_draws_or_evaluates_again(self):
        s=self.snapshot(self.attack());r=self.evaluate(s,[15,4])
        with patch('action_evaluation.evaluate_snapshot',side_effect=AssertionError('reroll')), patch.object(_ProvisionalRandom,'roll',side_effect=AssertionError('draw')), patch('random.randint',side_effect=AssertionError('authoritative draw')):
            self.build(s,r)

    def test_two_defenses_keep_every_outcome_and_practice_once(self):
        other=self.world.make_weapon_for_being(self.b.id,'Dagger','Other parry')
        self.world.arm_being(self.b.id,other,'left hand')
        strike=self.attack(melee=True)
        one=MeleeDefense(self.enc,self.b.id,self.a.id,kind='parry',target_action_id=strike.id,weapon_id=self.w3)
        two=MeleeDefense(self.enc,self.b.id,self.a.id,kind='parry',target_action_id=strike.id,weapon_id=other)
        s=self.snapshot(strike,one,two);r=self.evaluate(s,[1,20,20,1]);c=self.build(s,r)
        self.assertEqual(c.target(self.b.id).projected_hp,100)
        self.assertEqual(len(c.target(self.b.id).practice),2)
        owned=[row for row in c.target(self.b.id).incoming if type(row.effect) is DefenseEffect]
        self.assertEqual([row.effect.success for row in owned],[False,True])
        self.assertEqual(len(c.actions[strike.id].defenses),2)
        self.assertEqual(c.practice_validation,'validated')
        self.assertEqual(len({r.identity for r in owned}),2)

    def test_missing_or_contradictory_defense_dependency_refused(self):
        strike=self.attack(melee=True)
        defense=MeleeDefense(self.enc,self.b.id,self.a.id,kind='dodge',target_action_id=strike.id)
        s=self.snapshot(strike,defense);r=self.evaluate(s,[20,1]);ps=r.proposals
        for deps in [(),(replace(ps[1].defenses[0],success=False),)]:
            broken=replace(ps[1],defenses=deps)
            with self.assertRaises(SettlementIntegrityError):self.build(s,replace(r,proposals=(ps[0],broken)))

    def test_successful_defense_cannot_coexist_with_damage(self):
        strike=self.attack(melee=True)
        defense=MeleeDefense(self.enc,self.b.id,self.a.id,kind='dodge',target_action_id=strike.id)
        s=self.snapshot(strike,defense);r=self.evaluate(s,[20,1]);dp,sp=r.proposals
        sp=replace(sp,outcome='normal',effects=sp.effects+(DamageEffect(strike.id,self.b.id,3,'body'),))
        with self.assertRaises(SettlementIntegrityError):self.build(s,self.rebind(s,r,(dp,sp)))

    def test_missing_qualifying_practice_is_not_silently_accepted(self):
        s=self.snapshot(self.attack(melee=True));r=self.evaluate(s,[15,4]);p=r.proposals[0]
        p=replace(p,effects=tuple(e for e in p.effects if type(e) is not PracticeEffect),target_ids=(self.b.id,))
        with self.assertRaisesRegex(SettlementIntegrityError,'practice'):self.build(s,self.rebind(s,r,(p,)))

    def test_run_practice_staged_without_moving_or_projecting_skills(self):
        run=RunAction(self.world,self.a.id,0,2,3,experience=4)
        self.enc.schedule_choice((run,));self.a.set_position(CartesianPosition(2,0,0))
        s=self.snapshot();r=evaluate_snapshot(s);c=self.build(s,r)
        self.assertEqual(c.actions[run.id].outcome,'partial')
        self.assertEqual(c.target(self.a.id).practice[0].effect.experience,4)
        self.assertFalse(hasattr(c.target(self.a.id),'skills'))
        self.assertEqual(self.a.get_position().x,2)
        self.assertEqual(c.target(self.a.id).projected_hp,100)

    def test_spot_awareness_union_retains_individual_causes_without_practice(self):
        one=SpotAction(self.world,self.a.id,self.b.id,0,die_roll=20)
        two=SpotAction(self.world,self.a.id,self.b.id,0,die_roll=20)
        self.enc.clear_awareness(self.a.id,self.b.id)
        s=self.snapshot(one,two);r=evaluate_snapshot(s);c=self.build(s,r);t=c.target(self.a.id)
        self.assertEqual(t.aware_of,frozenset((self.b.id,)))
        self.assertEqual(len(t.practice),0)
        self.assertEqual(len([e for e in t.incoming if type(e.effect) is AwarenessEffect]),2)
        self.assertFalse(self.enc.is_aware(self.a.id,self.b.id))

    def test_cancelled_and_empty_boundary_remain_representable(self):
        action=self.attack();self.enc.schedule_choice((action,));self.enc.cancel_action(action.id)
        self.enc.time=math.ceil(action.end_time)
        s=capture_snapshot(self.enc,int(self.enc.time));c=self.build(s,evaluate_snapshot(s))
        self.assertEqual(c.actions[action.id].outcome,'interrupted');self.assertEqual(len(c.effects),0)
        empty=replace(s,actions=MappingProxyType({}));r=evaluate_snapshot(empty)
        self.assertEqual(len(self.build(empty,r).actions),0)

    def test_target_hp_metadata_cannot_be_smuggled_into_action(self):
        s=self.snapshot(self.attack());r=self.evaluate(s,[15,4]);p=replace(r.proposals[0],metadata=(('hp_after',96),))
        with self.assertRaises(SettlementIntegrityError):self.build(s,self.rebind(s,r,(p,)))

    def test_nonbeing_fatal_target_remains_unsupported(self):
        s=self.snapshot(self.attack());r=self.evaluate(s,[20,20,1]);p=r.proposals[0];row=r.identified_effects[0]
        changed=replace(row.effect,target_id=self.w1)
        p=replace(p,effects=(changed,),target_ids=(self.b.id,self.w1))
        with self.assertRaises(SettlementIntegrityError):self.build(s,self.rebind(s,r,(p,)))

    def test_live_resolver_stays_sequential_and_clamped(self):
        self.b.set_hit_points(12)
        one,two=self.attack(extra=4),self.attack(self.w2,extra=3)
        self.enc.schedule_choice((one,two))
        with patch('action_settlement.reconcile_boundary',side_effect=AssertionError('must remain inactive')), patch('action.roll_dice',side_effect=[15,4,15,4]):
            self.enc.step(4)
        self.assertEqual(self.b.hit_points(),0)
        self.assertEqual(self.enc.finished_action_list,[one.id,two.id])


    def test_multiple_fatal_flags_and_real_damage_do_not_stack(self):
        self.b.set_hit_points(20)
        s=self.snapshot(self.attack(),self.attack(self.w2));r=self.evaluate(s,[20,20,1,20,20,1])
        first,second=r.proposals
        first=replace(first,effects=first.effects+(DamageEffect(first.action_id,self.b.id,6,'body'),))
        c=self.build(s,self.rebind(s,r,(first,second)))
        self.assertEqual((c.target(self.b.id).projected_hp,c.target(self.b.id).actual_damage),(-16,6))
        self.assertEqual(len(c.target(self.b.id).fatal_effect_ids),2)

    def test_already_negative_equipment_takes_real_damage(self):
        shield_id=self.world.make_weapon_for_being(self.b.id,'Small shield','Shield')
        self.world.arm_being(self.b.id,shield_id,'shield hand')
        self.world.get_object_by_id(shield_id).current.hit_points=-12
        s=self.snapshot(self.attack(extra=2));r=self.evaluate(s,[15,4,1])
        self.assertEqual(self.build(s,r).target(shield_id).projected_hp,-18)

    def test_float_overflow_rejects_whole_candidate(self):
        s=self.snapshot(self.attack(),self.attack(self.w2));r=self.evaluate(s,[15,4,15,4])
        ps=tuple(replace(p,effects=(replace(p.effects[0],amount=1e308),)) for p in r.proposals)
        with self.assertRaises(SettlementIntegrityError):self.build(s,self.rebind(s,r,ps))

    def test_integer_aggregation_does_not_round_large_hp(self):
        self.b.current.hit_points=10**100
        s=self.snapshot(self.attack());r=self.evaluate(s,[15,4])
        self.assertEqual(self.build(s,r).target(self.b.id).projected_hp,10**100-4)

    def test_missing_protection_contribution_is_rejected(self):
        self.world.make_armor_for_being(self.b.id,'Leather armor','Leather')
        s=self.snapshot(self.attack());r=self.evaluate(s,[15,4]);p=r.proposals[0]
        p=replace(p,effects=tuple(e for e in p.effects if not(type(e) is ProtectionEffect or (type(e) is DamageEffect and e.component=='armor'))),target_ids=(self.b.id,))
        with self.assertRaisesRegex(SettlementIntegrityError,'protection'):self.build(s,self.rebind(s,r,(p,)))

    def test_invalid_provisional_context_refuses_without_live_rng_change(self):
        s=self.snapshot(self.attack());r=self.evaluate(s,[15,4])
        with self.assertRaises(SettlementIntegrityError):self.build(s,replace(r,provisional_rng_state=(0,(),None)))
        bad=replace(r.trace[0],action_id='foreign')
        with self.assertRaises(SettlementIntegrityError):self.build(s,replace(r,trace=(bad,)))

    def test_defense_mirrors_are_references_not_duplicate_charges(self):
        strike=self.attack(melee=True)
        defense=MeleeDefense(self.enc,self.b.id,self.a.id,kind='dodge',target_action_id=strike.id)
        s=self.snapshot(strike,defense);r=self.evaluate(s,[20,1]);c=self.build(s,r)
        self.assertEqual(sum(type(row.effect) is DefenseEffect for row in c.effects.values()),1)
        self.assertEqual(sum(type(d) is DefenseEffect for p in c.actions.values() for d in p.defenses),2)
        row=next(row for row in r.identified_effects if type(row.effect) is DefenseEffect)
        with self.assertRaises(SettlementIntegrityError):self.build(s,replace(r,identified_effects=r.identified_effects+(row,)))

    def test_spot_failure_has_no_practice_or_awareness(self):
        spot=SpotAction(self.world,self.a.id,self.b.id,0,die_roll=1)
        self.enc.clear_awareness(self.a.id,self.b.id)
        s=self.snapshot(spot);r=evaluate_snapshot(s);t=self.build(s,r).target(self.a.id)
        self.assertEqual(len(t.practice),0);self.assertEqual(t.aware_of,frozenset())

    def test_ordinary_miss_and_unavailable_weapon_are_outcomes(self):
        action=self.attack();s=self.snapshot(action);r=self.evaluate(s,[2])
        self.assertEqual(self.build(s,r).actions[action.id].outcome,'miss')
        action=replace(s.actions[action.id],instrument_id=None)
        modified=replace(s,actions=MappingProxyType({action.id:action}))
        self.assertEqual(self.build(modified,evaluate_snapshot(modified)).actions[action.id].outcome,'weapon_unavailable')

    def test_opaque_identity_cannot_execute_equality_callback(self):
        s=self.snapshot(self.attack());r=self.evaluate(s,[15,4]);row=r.identified_effects[0]
        class Opaque:
            def __eq__(self,other):raise AssertionError('unsafe equality')
        changed=replace(row,identity=replace(row.identity,channel=Opaque()))
        with self.assertRaises(SettlementIntegrityError):self.build(s,replace(r,identified_effects=(changed,)))

    def test_reality_inquiry_families_continue_to_refuse(self):
        from history_conversation import AskAboutPastAction
        generate=Mock(side_effect=AssertionError('unsafe history realization'))
        inquiry=AskAboutPastAction(self.world,self.a.id,self.b.id,0,episode_time=-1,topic='birth',generate=generate)
        self.world.event_history[inquiry.id]=inquiry;self.enc.pending_action_list.append(inquiry.id);self.enc.time=1
        with self.assertRaises(UnsupportedEvaluation):capture_snapshot(self.enc,1)
        generate.assert_not_called()
