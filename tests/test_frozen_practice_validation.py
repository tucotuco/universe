"""Inactive common-boundary practice, using established facts only."""
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
import random
from types import MappingProxyType
import sys
import unittest
from unittest.mock import Mock, patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from action_evaluation import (capture_snapshot,evaluate_snapshot,UnsupportedEvaluation,
    bind_evaluation_result,PracticeEffect,_ProvisionalRandom)
from action_settlement import reconcile_boundary,SettlementIntegrityError
from activities import RunAction,RunAction
from encounter import Encounter
from experience import SkillUse,level_from_practice
from frozen_practice import PracticeValidationError,validate_history_constraints
from library import Library
from melee_combat import MeleeStrike
from realization import Fact,FactKey,ImpossibleRealization
from spatial.state import CartesianPosition
from spatial.geometry import Sphere
from universe import Universe


class TestFrozenPracticeValidation(unittest.TestCase):
    def setUp(self):
        self.world=Universe('Practice',library=Library(config_dir=str(ROOT/'src/config')))
        self.skills=self.world.get_skill_dictionary()
        self.a=self.world.get_object_by_id(self.world.make_being('Human','A'))
        self.b=self.world.get_object_by_id(self.world.make_being('Human','B'))
        for actor,x in ((self.a,0),(self.b,1.5)):
            actor.set_position(CartesianPosition(x,0,0));actor.set_geometry(Sphere(.2));actor.set_hit_points(100)
        self.enc=Encounter(self.world,10,0,initiated=True)
        self.enc.add_being(self.a.id);self.enc.add_being(self.b.id)
        self.enc.mark_aware(self.a.id,self.b.id);self.enc.mark_aware(self.b.id,self.a.id)
        self.world.add_event(self.enc)

    def practice_action(self,xp=10,actor=None,target=None,duration=1,roll=20,minimum_distance=1.5):
        return RunAction(self.world,(actor or self.a).id,0,duration,minimum_distance,experience=xp)

    def _move_all(self):
        for actor in (self.a,self.b):
            pos=actor.get_position();actor.set_position(CartesianPosition(pos.x+1,pos.y,pos.z))

    def move_and_capture(self,boundary=1):
        self._move_all();self.enc.time=boundary
        return capture_snapshot(self.enc,boundary)

    def snapshot(self,*actions):
        self.enc.schedule_choice(actions)
        moved=set()
        for action in actions:
            actor=self.world.get_object_by_id(action.actor_id)
            if actor.id not in moved:
                pos=actor.get_position();actor.set_position(CartesianPosition(pos.x+1,pos.y,pos.z));moved.add(actor.id)
        self.enc.time=max(__import__('math').ceil(a.end_time) for a in actions)
        return capture_snapshot(self.enc,int(self.enc.time))

    def state(self):
        # Inspect raw state, including cycles, without calling live serialization
        # or historical methods (legacy Universe JSON cannot encode history).
        seen=set()
        def copy(value):
            if value is None or type(value) in (str,int,float,bool):return value
            if callable(value):return ('callable',id(value))
            if id(value) in seen:return ('reference',id(value))
            seen.add(id(value))
            if type(value) in (dict,MappingProxyType):return tuple((copy(k),copy(v)) for k,v in value.items())
            if type(value) in (list,tuple):return tuple(copy(v) for v in value)
            if type(value) in (set,frozenset):return tuple(sorted((copy(v) for v in value),key=repr))
            try:data=object.__getattribute__(value,'__dict__')
            except AttributeError:return ('opaque',type(value).__name__,id(value))
            return (type(value).__name__,copy(data))
        return copy(self.world)

    def unchanged(self,operation):
        state=self.state();rng=random.getstate();choices=(self.enc.choice_state,self.enc.active_reservations)
        try:return operation()
        finally:
            self.assertEqual(self.state(),state);self.assertEqual(random.getstate(),rng)
            self.assertEqual((self.enc.choice_state,self.enc.active_reservations),choices)

    def build(self,snapshot,result=None):
        if result is None:result=evaluate_snapshot(snapshot)
        before=(repr(snapshot),repr(result))
        try:return self.unchanged(lambda:reconcile_boundary(snapshot,result))
        finally:self.assertEqual((repr(snapshot),repr(result)),before)

    def prior_run(self):
        self.a.set_skill_level(self.skills,'run',1)
        self.a.record_skill_use(self.skills,'run',1235,action_id='prior',time=-2,outcome='success')
        self.assertEqual(self.a.get_skill_level('run'),2)

    def history(self,skills=('run',)):
        return self.a.begin_personal_history(earliest=-10,known_through=10,nondeclining_skills=skills)

    def test_combined_threshold_uses_native_curve_and_common_rank(self):
        self.prior_run();one,two=self.practice_action(),self.practice_action();s=self.snapshot(one,two);r=evaluate_snapshot(s)
        c=self.build(s,r);p=c.target(self.a.id).practice_state
        self.assertEqual(level_from_practice(1,1245),2)
        self.assertEqual(level_from_practice(1,1255),3)
        self.assertEqual(p.level('run'),3);self.assertEqual(p.skill_experience['run'],1255)
        self.assertEqual(len(p.exercises),2);self.assertEqual(len(p.transitions),1)
        self.assertEqual((p.transitions[0].level_before,p.transitions[0].level_after),(2,3))
        self.assertEqual([dict(a.metadata)['displacement'] for a in r.proposals],[1,1])
        self.assertEqual([e.action_id for e in p.exercises],[one.id,two.id]);self.assertEqual(p.prior_uses,s.practice_inputs.beings[self.a.id].prior_uses)
        self.assertEqual(self.a.get_skill_level('run'),2)

    def test_single_award_does_not_cross_combined_threshold(self):
        self.prior_run();s=self.snapshot(self.practice_action());p=self.build(s).target(self.a.id).practice_state
        self.assertEqual(p.level('run'),2);self.assertEqual(p.skill_experience['run'],1245)

    def test_permutation_and_retry_do_not_change_progression(self):
        self.prior_run();s=self.snapshot(self.practice_action(),self.practice_action());r=evaluate_snapshot(s);expected=self.build(s,r)
        shuffled=replace(r,proposals=tuple(reversed(r.proposals)),identified_effects=tuple(reversed(r.identified_effects)))
        self.assertEqual(self.build(s,shuffled),expected);self.assertEqual(self.build(s,r),expected)

    def test_practice_is_owned_by_each_being_without_cross_awards(self):
        run=RunAction(self.world,self.a.id,0,1,1,experience=250)
        runs=(self.practice_action(250),self.practice_action(250,actor=self.b,target=self.a))
        self.enc.schedule_choice((run,*runs));self._move_all();s=self.move_and_capture(1);c=self.build(s)
        self.assertEqual(c.target(self.a.id).practice_state.level('run'),1)
        self.assertEqual(c.target(self.b.id).practice_state.level('run'),1)
        self.assertEqual(c.target(self.a.id).practice_state.skill_experience['run'],500)
        self.assertEqual(c.target(self.b.id).practice_state.skill_experience['run'],250)

    def test_nonprogressive_keeps_xp_and_history_without_rank_gain(self):
        one,two=self.practice_action(300),self.practice_action(300)
        self.enc.schedule_choice((one,two));self.skills.skills['run']['is_progressive']=False;s=self.move_and_capture(1);p=self.build(s).target(self.a.id).practice_state
        self.assertEqual(p.level('run'),0);self.assertEqual(p.skill_experience['run'],600)
        self.assertEqual(len(p.exercises),2);self.assertEqual(p.transitions[0].level_after,0)

    def test_ordinary_untrained_is_eligible(self):
        s=self.snapshot(self.practice_action(250));p=self.build(s).target(self.a.id).practice_state
        self.assertEqual(p.level('run'),1)

    def test_extraordinary_untrained_refused_before_any_award(self):
        action=self.practice_action(250);self.enc.schedule_choice((action,));self.skills.skills['run']['is_ordinary']=False;s=self.move_and_capture(1)
        with self.assertRaisesRegex(PracticeValidationError,'pre-batch training'):self.build(s)

    def test_extraordinary_trained_uses_same_native_progression(self):
        self.a.set_skill_level(self.skills,'run',1)
        action=self.practice_action(500);self.enc.schedule_choice((action,));self.skills.skills['run']['is_ordinary']=False;s=self.move_and_capture(1)
        self.assertEqual(self.build(s).target(self.a.id).practice_state.level('run'),2)

    def test_zero_xp_and_failed_action_both_retain_attributable_uses(self):
        one,two=self.practice_action(0),self.practice_action(0,minimum_distance=.5)
        s=self.snapshot(one,two);p=self.build(s).target(self.a.id).practice_state
        self.assertEqual([u.outcome for u in p.exercises],['partial','success'])
        self.assertEqual([u.experience for u in p.exercises],[0,0]);self.assertEqual(len(p.exercises),2)
        self.assertEqual(p.baselines['run'],0);self.assertEqual(p.skill_experience['run'],0)

    def test_weapon_practice_does_not_propagate_to_categories(self):
        ids=[self.world.make_weapon_for_being(self.a.id,'Dagger',name) for name in ('One','Two')]
        for wid,part in zip(ids,('right hand','left hand')):self.world.arm_being(self.a.id,wid,part)
        self.a.current.skills.weapon_skills['Dagger']=0
        self.a.record_skill_use(self.skills,'Dagger',230,action_id='prior-weapon',time=-2)
        self.a.current.skills.weapon_skills['Simple weapons']=4
        strikes=tuple(MeleeStrike(self.enc,self.a.id,self.b.id,wid,motion='thrust',reach=2) for wid in ids)
        s=self.snapshot(*strikes);p=self.build(s).target(self.a.id).practice_state
        self.assertEqual(p.weapon_levels['Dagger'],1);self.assertEqual(p.weapon_levels['Simple weapons'],4)
        self.assertNotIn('Dagger',p.ordinary_levels)

    def test_prior_action_skill_use_prevents_double_award(self):
        action=self.practice_action();self.a.record_skill_use(self.skills,'run',0,action_id=action.id,time=-1)
        s=self.snapshot(action)
        with self.assertRaisesRegex(PracticeValidationError,'already recorded'):self.build(s)

    def test_duplicate_effects_and_alternative_ids_are_refused(self):
        s=self.snapshot(self.practice_action());r=evaluate_snapshot(s)
        row=next(e for e in r.identified_effects if type(e.effect) is PracticeEffect)
        for added in (row,replace(row,identity=replace(row.identity,slot=99))):
            with self.assertRaises(SettlementIntegrityError):self.build(s,replace(r,identified_effects=r.identified_effects+(added,)))

    def test_valid_established_rank_and_training_episode_are_not_realized_again(self):
        self.prior_run();h=self.history();key=h.episode_key(0,'training')
        h.reality.commit((Fact(key,{'description':'Prior lessons','skill':'run','rank_after':2}),Fact(h.skill_key(0,'run'),2)))
        s=self.snapshot(self.practice_action(),self.practice_action());revision=h.reality.revision
        with patch.object(h.reality,'commit',side_effect=AssertionError('must not realize')):
            c=self.build(s)
        self.assertEqual(c.target(self.a.id).practice_state.level('run'),3)
        self.assertEqual(h.reality.revision,revision)

    def test_established_earlier_high_rank_rejects_future_low_use(self):
        h=self.history();h.commit_skill_rank(0,'run',2)
        s=self.snapshot(self.practice_action())
        with self.assertRaisesRegex(ImpossibleRealization,'pre-action rank'):self.build(s)

    def test_rank_at_boundary_describes_common_post_batch_state(self):
        self.prior_run();h=self.history();h.commit_skill_rank(1,'run',2)
        s=self.snapshot(self.practice_action(),self.practice_action())
        with self.assertRaisesRegex(ImpossibleRealization,'skill gain'):self.build(s)

    def test_boundary_rank_equal_to_combined_after_is_valid(self):
        self.prior_run();h=self.history();h.commit_skill_rank(1,'run',3)
        s=self.snapshot(self.practice_action(),self.practice_action());p=self.build(s).target(self.a.id).practice_state
        self.assertEqual(p.transitions[0].time,1);self.assertEqual(p.transitions[0].level_after,3)
        self.assertEqual(len(p.exercises),2)
        self.assertTrue(all(not hasattr(e,'level_after') for e in p.exercises))

    def test_fractional_nominal_times_are_provenance_not_sequential_rank_precedence(self):
        self.prior_run();h=self.history();h.commit_skill_rank(1.5,'run',2)
        s=self.snapshot(self.practice_action(duration=1.2),self.practice_action(duration=1.8));p=self.build(s).target(self.a.id).practice_state
        self.assertEqual(p.transitions[0].time,2)
        self.assertEqual([use.nominal_end for use in p.exercises],[1.2,1.8])
        self.assertEqual([use.resolved_at for use in p.exercises],[2,2])
        self.assertEqual(p.transitions[0].level_after,3)

    def test_constraints_apply_only_to_explicit_nondeclining_skills(self):
        h=self.history(('run',));h.commit_skill_rank(0,'run',0)
        s=self.snapshot(self.practice_action(250))
        self.assertEqual(self.build(s).target(self.a.id).practice_state.level('run'),1)

    def test_undated_prior_use_retains_native_temporal_meaning(self):
        self.a.set_skill_level(self.skills,'run',1)
        prior=self.a.record_skill_use(self.skills,'run',0,time=None,action_id='undated')
        h=self.history();h.commit_skill_rank(-1,'run',0)
        s=self.snapshot(self.practice_action(0));p=self.build(s).target(self.a.id).practice_state
        self.assertIsNone(p.prior_uses[0].time);self.assertEqual(p.prior_uses[0],prior)

    def test_live_definition_xp_rank_history_and_fact_changes_do_not_alias(self):
        self.prior_run();h=self.history();h.commit_skill_rank(0,'run',2)
        s=self.snapshot(self.practice_action(),self.practice_action());expected=self.build(s)
        self.skills.skills['run']['is_progressive']=False
        self.a.current.skills.skills['run']=99;self.a.skill_experience['run']=9999
        self.a._skill_practice_baselines['run']=98;self.a.skill_use_history.clear()
        h.reality._records.clear();h.reality._revision=0
        self.assertEqual(self.build(s),expected)

    def test_nested_history_episode_and_definitions_are_immutable(self):
        h=self.history();key=h.episode_key(0,'trip')
        h.reality.commit((Fact(key,{'description':'A trip'}),))
        s=self.snapshot(self.practice_action(0));inputs=s.practice_inputs;being=inputs.beings[self.a.id]
        with self.assertRaises(TypeError):inputs.definitions['run']['is_ordinary']=False
        with self.assertRaises(TypeError):being.skill_experience['run']=100
        with self.assertRaises(TypeError):being.history.records[0].value['description']='changed'
        with self.assertRaises(FrozenInstanceError):being.history.records[0].key.time=99
        with self.assertRaises(FrozenInstanceError):self.build(s).target(self.a.id).practice_state.transitions[0].level_after=99
        h.reality._records[key].value['description']='Live edit'
        self.assertEqual(being.history.records[0].value['description'],'A trip')

    def test_custom_history_validator_is_rejected_without_invocation(self):
        h=self.history();unsafe=Mock(side_effect=AssertionError('unsafe validator'))
        h.reality._validators+=(unsafe,)
        self.enc.schedule_choice((self.practice_action(),));self.enc.time=1
        with self.assertRaises(UnsupportedEvaluation):capture_snapshot(self.enc,1)
        unsafe.assert_not_called()

    def test_custom_skill_dictionary_and_opaque_definition_refused_without_callbacks(self):
        action=self.practice_action();self.enc.schedule_choice((action,));self.enc.time=1
        class Opaque:
            def __bool__(self):raise AssertionError('opaque definition')
        self.skills.skills['run']['is_ordinary']=Opaque()
        with self.assertRaises(UnsupportedEvaluation):capture_snapshot(self.enc,1)

    def test_opaque_prior_skill_use_refused_without_callback(self):
        self.enc.schedule_choice((self.practice_action(),));self.enc.time=1
        class Opaque:
            def __getattribute__(self,name):raise AssertionError('unsafe use')
        self.a.skill_use_history.append(Opaque())
        with self.assertRaises(UnsupportedEvaluation):capture_snapshot(self.enc,1)

    def test_inconsistent_ledger_revision_or_identity_is_rejected(self):
        h=self.history();h.commit_skill_rank(0,'run',0)
        self.enc.schedule_choice((self.practice_action(),));self.enc.time=1;h.reality._revision=2
        with self.assertRaises(PracticeValidationError):capture_snapshot(self.enc,1)

    def test_failure_after_a_practice_projection_has_no_partial_result(self):
        s=self.snapshot(self.practice_action(250),self.practice_action(250,actor=self.b,target=self.a));r=evaluate_snapshot(s);expected=self.build(s,r)
        from frozen_practice import project_practice
        calls=[]
        def fail(*args):
            calls.append(args[1])
            if len(calls)==2:raise RuntimeError('injected practice fault')
            return project_practice(*args)
        with patch('frozen_practice.project_practice',fail):
            with self.assertRaises(RuntimeError):self.build(s,r)
        self.assertEqual(self.build(s,r),expected)

    def test_no_mutable_callbacks_or_rng_are_used_in_reconciliation(self):
        s=self.snapshot(self.practice_action());r=evaluate_snapshot(s)
        with patch.object(self.a,'record_skill_use',side_effect=AssertionError('live award')),patch.object(self.skills,'get_skill_definition',side_effect=AssertionError('live dictionary')),patch.object(_ProvisionalRandom,'roll',side_effect=AssertionError('random')):
            self.build(s,r)

    def test_single_use_matches_native_progression_and_history(self):
        self.prior_run();s=self.snapshot(self.practice_action(20));p=self.build(s).target(self.a.id).practice_state
        live=self.a.record_skill_use(self.skills,'run',20,action_id='comparison',time=1,outcome='success')
        self.assertEqual((p.transitions[0].level_before,p.transitions[0].level_after),(live.level_before,live.level_after))
        self.assertEqual(p.skill_experience['run'],self.a.get_skill_experience('run'))

    def test_native_and_frozen_history_rules_agree_without_new_facts(self):
        self.a.set_skill_level(self.skills,'run',2)
        self.a.record_skill_use(self.skills,'run',0,time=-2,action_id='prior')
        h=self.history();h.commit_skill_rank(0,'run',2)
        s=self.snapshot(self.practice_action(0));f=s.practice_inputs.beings[self.a.id].history
        for use in (SkillUse('run',0,2,2,'valid',1,'miss'),SkillUse('run',0,1,1,'invalid',1,'miss')):
            try:h.validate_future_skill_use(use);native=True
            except ImpossibleRealization:native=False
            try:validate_history_constraints(self.a.id,f.earliest,f.known_through,f.nondeclining_skills,f.records,s.practice_inputs.beings[self.a.id].prior_uses+(use,));frozen=True
            except ImpossibleRealization:frozen=False
            self.assertEqual(native,frozen)

    def test_practice_readiness_is_explicit_but_publication_is_still_disabled(self):
        s=self.snapshot(self.practice_action());c=self.build(s)
        self.assertEqual(c.practice_validation,'validated');self.assertFalse(c.ready_for_publication)
        self.assertFalse(hasattr(c,'apply'))
        for action in c.actions.values():self.assertFalse(hasattr(action,'skill_state'))


    def test_unknown_skill_definition_is_refused_without_inference(self):
        action=self.practice_action();self.enc.schedule_choice((action,));del self.skills.skills['run'];s=self.move_and_capture(1)
        with self.assertRaisesRegex(PracticeValidationError,'unknown practiced skill'):self.build(s)

    def test_negative_bool_or_noninteger_prior_experience_refused_at_capture(self):
        self.enc.schedule_choice((self.practice_action(),));self.enc.time=1
        for invalid in (-1,True,1.5):
            self.a.skill_experience['run']=invalid
            with self.assertRaises(PracticeValidationError):capture_snapshot(self.enc,1)

    def test_opaque_current_rank_does_not_run_numeric_callbacks(self):
        self.enc.schedule_choice((self.practice_action(),));self.enc.time=1
        class Opaque:
            def __float__(self):raise AssertionError('unsafe numeric conversion')
        self.a.current.skills.skills['run']=Opaque()
        with self.assertRaises(UnsupportedEvaluation):capture_snapshot(self.enc,1)

    def test_subclassed_skill_dictionary_is_refused_before_lookup(self):
        from skill import SkillDictionary
        class UnsafeDictionary(SkillDictionary):
            def get_skill_definition(self,name):raise AssertionError('unsafe lookup')
        self.enc.schedule_choice((self.practice_action(),));self.enc.time=1
        self.world.library.skill_dictionary=UnsafeDictionary()
        with self.assertRaises(UnsupportedEvaluation):capture_snapshot(self.enc,1)

    def test_inquiry_window_and_committed_episode_constraints_are_checked(self):
        h=self.history();key=h.episode_key(0,'trip');h.reality.commit((Fact(key,{'description':'Trip'}),))
        self.enc.schedule_choice((self.practice_action(),));self.enc.time=1
        h.known_through=-1
        with self.assertRaises(ImpossibleRealization):capture_snapshot(self.enc,1)

    def test_fact_commit_order_and_identity_are_preserved(self):
        h=self.history();h.commit_skill_rank(-1,'run',0);h.commit_skill_rank(0,'run',0)
        s=self.snapshot(self.practice_action(0));f=s.practice_inputs.beings[self.a.id].history
        self.assertEqual([r.revision for r in f.records],[1,2])
        self.assertEqual([r.key.time for r in f.records],[-1,0])
        self.assertEqual(f.ledger_identity,id(h.reality));self.assertEqual(f.revision,2)
        self.assertFalse(hasattr(f,'commit'));self.assertFalse(hasattr(f,'being'))

    def test_inconsistent_registration_of_common_skill_reads_is_refused(self):
        from types import MappingProxyType
        s=self.snapshot(self.practice_action());entity=s.entities[self.a.id]
        changed=replace(entity,data=MappingProxyType({**entity.data,'skills':MappingProxyType({'run':99})}))
        s=replace(s,entities=MappingProxyType({**s.entities,self.a.id:changed}))
        with self.assertRaisesRegex(PracticeValidationError,'common evaluation reads'):self.build(s)

    def test_no_effect_does_not_manufacture_practice_from_skill_prerequisites(self):
        run=RunAction(self.world,self.a.id,0,1,1,experience=250)
        self.enc.schedule_choice((run,));self.enc.time=1
        s=capture_snapshot(self.enc,1);c=self.build(s);p=c.target(self.a.id).practice_state
        self.assertEqual(p.exercises,());self.assertEqual(p.transitions,())
        self.assertEqual(dict(p.skill_experience),{})
        self.assertEqual(c.practice_validation,'no_practice')
        self.assertTrue(c.publication_dependencies);self.assertFalse(c.ready_for_publication)

    def test_zero_xp_prior_duplicate_is_retained_and_rejected(self):
        action=self.practice_action(0)
        prior=SkillUse('run',0,0,0,action.id,0,'failure')
        self.a.skill_use_history.append(prior)
        s=self.snapshot(action)
        self.assertEqual(s.practice_inputs.beings[self.a.id].prior_uses[0].experience,0)
        with self.assertRaises(PracticeValidationError):self.build(s)

    def test_same_boundary_never_emits_sequential_legacy_skill_use_ranks(self):
        self.prior_run();s=self.snapshot(self.practice_action(),self.practice_action());p=self.build(s).target(self.a.id).practice_state
        self.assertEqual(len(p.prior_uses),1)
        self.assertEqual(len(p.exercises),2)
        self.assertEqual(len(p.transitions),1)
        transition=p.transitions[0]
        self.assertEqual((transition.level_before,transition.level_after),(2,3))
        self.assertEqual(set(transition.effect_ids),{use.effect_identity for use in p.exercises})
        self.assertTrue(all(not hasattr(use,'level_before') for use in p.exercises))


    def test_new_use_may_follow_historical_inquiry_window_without_extending_it(self):
        self.a.set_skill_level(self.skills,'run',1)
        h=self.a.begin_personal_history(earliest=-10,known_through=0,nondeclining_skills=('run',))
        h.commit_skill_rank(0,'run',1)
        s=self.snapshot(self.practice_action(500));p=self.build(s).target(self.a.id).practice_state
        self.assertEqual(p.level('run'),2)
        self.assertEqual(s.practice_inputs.beings[self.a.id].history.known_through,0)
        self.assertEqual(h.known_through,0);self.assertEqual(h.reality.revision,1)
