"""Inactive native shared truth, independent of observer evidence/publication."""
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
import json
import random
import sys
from types import MappingProxyType
import unittest
from unittest.mock import Mock, patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from action_evaluation import capture_snapshot,evaluate_snapshot,UnsupportedEvaluation,EvaluationIntegrityError
from action_settlement import reconcile_boundary
from activities import SpotAction
from encounter import Encounter
from group_observation import ObserveGroupAction
from history_conversation import AskAboutPastAction
from library import Library
from objective_reality import (EpisodeFacts,capture_objective_context,evaluate_native_companion,
    build_objective_candidate)
from realization import Fact,FactKey,ImpossibleRealization
from spatial.state import CartesianPosition
from spatial.geometry import Sphere
from statistical_group import StatisticalGroup
from universe import Universe


class TestSharedObjectiveReality(unittest.TestCase):
    def setUp(self):
        self.world=Universe('Objective',library=Library(config_dir=str(ROOT/'src/config')))
        self.beings=[self.world.get_object_by_id(self.world.make_being('Human',name)) for name in ('A','B','C')]
        self.a,self.b,self.c=self.beings
        self.enc=Encounter(self.world,10,0,initiated=True)
        for i,being in enumerate(self.beings):
            being.set_position(CartesianPosition(i*2,0,0));being.set_geometry(Sphere(.2));self.enc.add_being(being.id)
        for actor in self.beings:
            for target in self.beings:
                if actor is not target:self.enc.mark_aware(actor.id,target.id)
        self.world.add_event(self.enc)

    def group(self,name='group-one',seed=81):
        config=json.loads((ROOT/'examples/nomadic_group.json').read_text())
        config['motion']['position']=[30,0,0]
        group=StatisticalGroup(name,name,config,seed)
        self.world.add_object(group);self.enc.add_object(group.id)
        return group

    def observe(self,actor,group):
        return ObserveGroupAction(self.world,actor.id,group.id,0,observation={'coarse_range_m':100,'detailed_range_m':50})

    def history(self):
        return self.a.begin_personal_history(earliest=-10,known_through=10,nondeclining_skills=('spot',))

    def recipe(self,h,description='Prior lessons',rank=None,extra=(),time=0,topic='lessons'):
        key=h.episode_key(time,topic)
        value={'description':description}
        facts=[]
        if rank is not None:
            value.update(skill='spot',rank_after=rank);facts.append(Fact(h.skill_key(time,'spot'),rank,'declared_history'))
        return EpisodeFacts((Fact(key,value,'declared_history'),*facts,*extra))

    def ask(self,actor,h,recipe=None,time=0,topic='lessons'):
        return AskAboutPastAction(self.world,actor.id,self.a.id,0,episode_time=time,topic=topic,
            generate=recipe if recipe is not None else self.recipe(h,time=time,topic=topic))

    def context(self,*actions):
        self.enc.schedule_choice(actions);self.enc.time=1
        return capture_objective_context(self.enc,1)

    def raw_state(self):
        seen=set()
        def copy(value):
            if value is None or type(value) in (str,int,float,bool):return value
            if callable(value):return ('callable',id(value))
            if id(value) in seen:return ('ref',id(value))
            seen.add(id(value))
            if type(value) in (dict,MappingProxyType):return tuple((copy(k),copy(v)) for k,v in value.items())
            if type(value) in (tuple,list):return tuple(copy(v) for v in value)
            if type(value) in (set,frozenset):return tuple(sorted((copy(v) for v in value),key=repr))
            try:data=object.__getattribute__(value,'__dict__')
            except AttributeError:return ('opaque',type(value).__name__,id(value))
            return (type(value).__name__,copy(data))
        return copy(self.world)

    def unchanged(self,operation):
        before=self.raw_state();rng=random.getstate();choices=(self.enc.choice_state,self.enc.active_reservations)
        try:return operation()
        finally:
            self.assertEqual(self.raw_state(),before);self.assertEqual(random.getstate(),rng)
            self.assertEqual((self.enc.choice_state,self.enc.active_reservations),choices)

    def build(self,context,companion=None):
        if companion is None:companion=self.unchanged(lambda:evaluate_native_companion(context))
        inputs=repr(context)
        try:return self.unchanged(lambda:build_objective_candidate(context,companion))
        finally:self.assertEqual(repr(context),inputs)

    def test_two_observers_share_one_group_truth_and_all_causal_requests(self):
        group=self.group();one,two=self.observe(self.a,group),self.observe(self.b,group)
        ctx=self.context(one,two);candidate=self.build(ctx);subject=candidate.subject(group.id)
        self.assertEqual(candidate.requests[one.id].requested_key,candidate.requests[two.id].requested_key)
        self.assertTrue(all(f.requesting_action_ids==tuple(sorted((one.id,two.id))) for f in subject.facts.values()))
        self.assertEqual(group._composition_reality.revision,0);self.assertIsNone(group._counts)
        self.assertEqual(len(group._members),0);self.assertEqual(len(group._realized_beings),0)
        self.assertGreater(len(candidate.draws),0)
        self.assertEqual(len(candidate.draws),1+subject.counts['households']*4)

    def test_group_values_and_native_keyed_stream_match_legacy_counts(self):
        group=self.group();ctx=self.context(self.observe(self.a,group));candidate=self.build(ctx)
        clone=StatisticalGroup(group.name,group.id,json.loads(json.dumps(group.config)),group.seed)
        self.assertEqual(dict(candidate.subject(group.id).counts),clone.counts())
        for record in clone._composition_reality.view().all_facts():
            self.assertEqual(candidate.subject(group.id).fact(record.key).value,record.value)

    def test_request_permutation_and_multiplicity_do_not_change_truth(self):
        group=self.group();one,two=self.observe(self.a,group),self.observe(self.b,group)
        ctx=self.context(one,two);expected=self.build(ctx)
        original=ctx.snapshot.objective_inputs
        altered=replace(original,actions=MappingProxyType(dict(reversed(tuple(original.actions.items())))))
        root=replace(ctx.snapshot,objective_inputs=altered)
        # Reordered IDs remain bound to the same complete read set.
        excluded=tuple(altered.actions)
        native=replace(ctx.native_snapshot,omitted_objective_action_ids=excluded)
        result=self.build(replace(ctx,snapshot=root,native_snapshot=native))
        self.assertEqual(result.subjects,expected.subjects);self.assertEqual(result.draws,expected.draws)
        from objective_reality import _group_candidate
        single,draws=_group_candidate(original.groups[group.id],(one.id,))
        self.assertEqual(single.counts,expected.subject(group.id).counts);self.assertEqual(draws,expected.draws)

    def test_distinct_groups_keep_distinct_native_fact_identity(self):
        first,second=self.group('one'),self.group('two')
        ctx=self.context(self.observe(self.a,first),self.observe(self.b,second));candidate=self.build(ctx)
        self.assertEqual(set(candidate.subjects),{'one','two'})
        self.assertTrue(all(key.entity_id=='one' for key in candidate.subject('one').facts))
        self.assertTrue(all(key.entity_id=='two' for key in candidate.subject('two').facts))

    def test_known_group_is_reused_without_sampling_or_cache_changes(self):
        group=self.group();known=group.counts();revision=group._composition_reality.revision
        ctx=self.context(self.observe(self.a,group),self.observe(self.b,group))
        with patch('statistical_group.composition_rng',side_effect=AssertionError('unnecessary RNG')):
            candidate=self.build(ctx)
        self.assertEqual(candidate.subject(group.id).counts,known);self.assertEqual(candidate.draws,())
        self.assertTrue(all(f.established for f in candidate.subject(group.id).facts.values()))
        self.assertEqual(group._composition_reality.revision,revision)

    def test_partial_group_reuses_known_root_and_household(self):
        group=self.group();group.household(0);ctx=self.context(self.observe(self.a,group));candidate=self.build(ctx)
        self.assertFalse(any(d.stream_parts==('household_count',) or d.stream_parts[:2]==('household',0) for d in candidate.draws))
        known=group._composition_reality.view().all_facts()
        for fact in known:self.assertTrue(candidate.subject(group.id).facts[fact.key].established)

    def test_group_cache_disagreement_rejects_instead_of_resampling(self):
        group=self.group();group.counts();group._counts['humans']+=1
        ctx=self.context(self.observe(self.a,group))
        with patch('statistical_group.composition_rng',side_effect=AssertionError('reroll')):
            with self.assertRaises(ImpossibleRealization):self.build(ctx)

    def test_cache_without_supporting_facts_is_rejected(self):
        group=self.group();group._counts={'adults':1,'children':0,'livestock':0,'dogs':0,'humans':1,'households':1}
        ctx=self.context(self.observe(self.a,group))
        with self.assertRaises((ImpossibleRealization,EvaluationIntegrityError)):self.build(ctx)

    def test_detached_group_configuration_and_cache_do_not_alias(self):
        group=self.group();ctx=self.context(self.observe(self.a,group));expected=self.build(ctx)
        group.config['composition']['households_cdf'][:]=[[99,1.0]]
        group.seed=999;group._counts={'invalid':10}
        self.assertEqual(self.build(ctx),expected)
        frozen=ctx.snapshot.objective_inputs.groups[group.id]
        with self.assertRaises(TypeError):frozen.composition['households_cdf'][0][0]=999
        with self.assertRaises(FrozenInstanceError):expected.subject(group.id).base_revision=99
        with self.assertRaises(TypeError):expected.subject(group.id).counts['humans']=0

    def test_two_inquiries_share_episode_and_supporting_facts(self):
        h=self.history();recipe=self.recipe(h,rank=0)
        one,two=self.ask(self.b,h,recipe),self.ask(self.c,h,recipe)
        ctx=self.context(one,two);candidate=self.build(ctx);subject=candidate.subject(self.a.id)
        self.assertEqual(len(subject.facts),2)
        self.assertEqual(candidate.requests[one.id].requested_key,candidate.requests[two.id].requested_key)
        self.assertTrue(all(f.requesting_action_ids==tuple(sorted((one.id,two.id))) for f in subject.facts.values()))
        self.assertEqual(h.reality.revision,0);self.assertEqual(candidate.draws,())

    def test_distinct_episode_keys_remain_distinct(self):
        h=self.history();one=self.ask(self.b,h,topic='first');two=self.ask(self.c,h,topic='second')
        candidate=self.build(self.context(one,two))
        self.assertNotEqual(candidate.requests[one.id].requested_key,candidate.requests[two.id].requested_key)
        self.assertEqual(len(candidate.subject(self.a.id).facts),2)

    def test_known_episode_is_reused_without_regeneration(self):
        h=self.history();recipe=self.recipe(h,'Known')
        h.realize_episode(0,'lessons',lambda view:recipe(h,view));revision=h.reality.revision
        action=self.ask(self.b,h,self.recipe(h,'Ignored native known-key generator'))
        ctx=self.context(action)
        with patch.object(EpisodeFacts,'__call__',side_effect=AssertionError('generator invocation')):
            candidate=self.build(ctx)
        fact=candidate.subject(self.a.id).fact(h.episode_key(0,'lessons'))
        self.assertEqual(fact.value['description'],'Known');self.assertTrue(fact.established)
        self.assertEqual(fact.committed_revision,revision);self.assertEqual(h.reality.revision,revision)

    def test_literal_adapter_matches_native_fact_declaration_semantics(self):
        h=self.history();recipe=self.recipe(h,'Explicit scenario fact',rank=0)
        ctx=self.context(self.ask(self.b,h,recipe));candidate=self.build(ctx)
        found=h.realize_episode(0,'lessons',lambda view:recipe(h,view))
        self.assertEqual(candidate.subject(self.a.id).fact(found.record.key).value,found.record.value)
        for f in h.reality.view().all_facts():self.assertEqual(candidate.subject(self.a.id).fact(f.key).value,f.value)

    def test_conflicting_episode_claims_reject_all_without_winner(self):
        h=self.history();one=self.ask(self.b,h,self.recipe(h,'A'));two=self.ask(self.c,h,self.recipe(h,'B'))
        ctx=self.context(one,two)
        with self.assertRaises(ImpossibleRealization):self.build(ctx)
        self.assertEqual(h.reality.revision,0)

    def test_same_episode_with_conflicting_supporting_rank_rejected(self):
        h=self.history();rankkey=h.skill_key(1,'spot')
        one=self.ask(self.b,h,self.recipe(h,extra=(Fact(rankkey,0),)))
        two=self.ask(self.c,h,self.recipe(h,extra=(Fact(rankkey,1),)))
        ctx=self.context(one,two)
        with self.assertRaises(ImpossibleRealization):self.build(ctx)

    def test_new_claim_cannot_overwrite_established_support(self):
        h=self.history();h.commit_skill_rank(0,'spot',0)
        action=self.ask(self.b,h,self.recipe(h,rank=1));ctx=self.context(action)
        with self.assertRaises(ImpossibleRealization):self.build(ctx)

    def joint_context(self,rank):
        self.a.set_skill_level(self.world.get_skill_dictionary(),'spot',1)
        self.a.record_skill_use(self.world.get_skill_dictionary(),'spot',1235,action_id='prior',time=-2)
        h=self.history()
        recipe=self.recipe(h,rank=2,extra=(Fact(h.skill_key(1,'spot'),rank),))
        actions=(self.ask(self.b,h,recipe),SpotAction(self.world,self.a.id,self.b.id,0,experience=10,die_roll=20),SpotAction(self.world,self.a.id,self.b.id,0,experience=10,die_roll=20))
        return h,self.context(*actions)

    def test_joint_history_support_matches_complete_target_practice_transition(self):
        h,ctx=self.joint_context(3);companion=evaluate_native_companion(ctx);candidate=self.build(ctx,companion)
        projection=companion.target(self.a.id).practice_state
        self.assertEqual(len(projection.exercises),2);self.assertEqual(len(projection.transitions),1)
        self.assertEqual(projection.transitions[0].level_after,3)
        self.assertEqual(candidate.subject(self.a.id).fact(h.skill_key(1,'spot')).value,3)
        self.assertEqual(self.a.get_skill_level('spot'),2)

    def test_coincident_boundary_history_cannot_use_fictitious_intermediate_rank(self):
        _,ctx=self.joint_context(2)
        with self.assertRaises(ImpossibleRealization):self.build(ctx)
        with self.assertRaises(ImpossibleRealization):self.build(ctx)

    def test_scoped_nondecline_is_not_inferred_for_every_skill(self):
        h=self.a.begin_personal_history(earliest=-10,known_through=10,nondeclining_skills=('run',))
        action=self.ask(self.b,h,self.recipe(h,'A nontraining episode'))
        spot=SpotAction(self.world,self.a.id,self.b.id,0,experience=250,die_roll=20)
        ctx=self.context(action,spot);self.build(ctx)
        self.assertEqual(evaluate_native_companion(ctx).target(self.a.id).practice_state.level('spot'),1)

    def test_live_history_skill_and_episode_mutation_does_not_change_frozen_truth(self):
        h,ctx=self.joint_context(3);expected=self.build(ctx)
        self.a.skill_experience['spot']=9999;self.a.current.skills.skills['spot']=99
        h.nondeclining_skills=frozenset();h.reality._records.clear();h.known_through=-1
        self.assertEqual(self.build(ctx),expected)

    def test_native_evaluation_and_settlement_never_claim_full_objective_actions(self):
        group=self.group();ctx=self.context(self.observe(self.a,group))
        with self.assertRaises(UnsupportedEvaluation):evaluate_snapshot(ctx.snapshot)
        companion=evaluate_native_companion(ctx)
        self.assertEqual(companion.coverage,'native_fragment');self.assertFalse(companion.ready_for_publication)
        self.assertFalse(self.build(ctx,companion).ready_for_publication)
        with self.assertRaises(EvaluationIntegrityError):reconcile_boundary(ctx.snapshot,evaluate_snapshot(ctx.native_snapshot))

    def test_foreign_or_modified_companion_is_rejected(self):
        group=self.group();ctx=self.context(self.observe(self.a,group));companion=evaluate_native_companion(ctx)
        with self.assertRaises(EvaluationIntegrityError):self.build(replace(ctx,native_snapshot=replace(ctx.native_snapshot)),companion)
        changed=replace(companion.target(self.a.id),projected_hp=999)
        forged=replace(companion,targets=MappingProxyType({**companion.targets,self.a.id:changed}))
        with self.assertRaises(EvaluationIntegrityError):self.build(ctx,forged)

    def test_opaque_history_generator_is_refused_without_invocation(self):
        h=self.history();unsafe=Mock(side_effect=AssertionError('unsafe'))
        action=AskAboutPastAction(self.world,self.b.id,self.a.id,0,episode_time=0,topic='lessons',generate=unsafe)
        self.enc.schedule_choice((action,));self.enc.time=1
        with self.assertRaises(UnsupportedEvaluation):capture_objective_context(self.enc,1)
        unsafe.assert_not_called()

    def test_custom_group_and_validator_extensions_refused_before_callbacks(self):
        group=self.group();action=self.observe(self.a,group)
        self.enc.schedule_choice((action,));self.enc.time=1
        unsafe=Mock(side_effect=AssertionError('validator callback'))
        group._composition_reality._validators+=(unsafe,)
        with self.assertRaises(UnsupportedEvaluation):capture_objective_context(self.enc,1)
        unsafe.assert_not_called()

    def test_failure_after_group_candidate_leaves_everything_unpublished(self):
        group=self.group();h=self.history()
        ctx=self.context(self.observe(self.a,group),self.ask(self.b,h))
        with patch('objective_reality._history_candidate',side_effect=RuntimeError('after group')):
            with self.assertRaises(RuntimeError):self.build(ctx)
        self.assertEqual(self.build(ctx),self.build(ctx))
        self.assertEqual(group._composition_reality.revision,0);self.assertEqual(h.reality.revision,0)

    def test_no_live_counts_generators_evidence_or_authoritative_rng_are_called(self):
        group=self.group();ctx=self.context(self.observe(self.a,group))
        with patch.object(group,'counts',side_effect=AssertionError('live counts')),patch('group_observation.SampledGroupObservation.sample',side_effect=AssertionError('evidence')),patch('random.random',side_effect=AssertionError('global RNG')),patch('random.randint',side_effect=AssertionError('global RNG')):
            self.build(ctx)

    def test_out_of_range_request_is_not_an_objective_integrity_fault(self):
        group=self.group();group.set_position(CartesianPosition(1000,0,0));action=self.observe(self.a,group)
        candidate=self.build(self.context(action))
        self.assertEqual(candidate.requests[action.id].status,'out_of_range');self.assertEqual(dict(candidate.subjects),{})

    def test_literal_values_and_candidate_episodes_are_deeply_immutable(self):
        h=self.history();value={'description':'Original'};recipe=EpisodeFacts((Fact(h.episode_key(0,'lessons'),value),))
        value['description']='Mutated';action=self.ask(self.b,h,recipe);candidate=self.build(self.context(action))
        fact=candidate.subject(self.a.id).fact(h.episode_key(0,'lessons'))
        self.assertEqual(fact.value['description'],'Original')
        with self.assertRaises(TypeError):fact.value['description']='Changed'
        self.assertFalse(hasattr(candidate,'apply'));self.assertFalse(hasattr(candidate,'save'))
        self.assertFalse(hasattr(action,'objective_state'));self.assertIsNone(action.heard_account)

    def test_live_resolver_does_not_call_the_new_candidate_path(self):
        self.a.set_skill_level(self.world.get_skill_dictionary(),'spot',0)
        group=self.group();action=self.observe(self.a,group)
        self.enc.schedule_choice((action,))
        with patch('objective_reality.build_objective_candidate',side_effect=AssertionError('inactive')):
            self.enc.step(1)
        self.assertIn(action.id,self.enc.finished_action_list)


    def test_known_group_ledger_values_and_cache_are_detached_after_capture(self):
        group=self.group();known=group.counts();ctx=self.context(self.observe(self.a,group))
        expected=self.build(ctx)
        group._counts['humans']=9999
        for record in group._composition_reality._records.values():
            if record.key.attribute=='household':record.value['adults']=9999
        self.assertEqual(self.build(ctx),expected)
        self.assertEqual(expected.subject(group.id).counts,known)

    def test_known_episode_values_are_detached_and_keep_revision_origin(self):
        h=self.history();recipe=self.recipe(h,'Established',rank=0)
        h.realize_episode(0,'lessons',lambda view:recipe(h,view))
        ctx=self.context(self.ask(self.b,h,recipe));expected=self.build(ctx)
        h.reality._records[h.episode_key(0,'lessons')].value['description']='Live edit'
        self.assertEqual(self.build(ctx),expected)
        fact=expected.subject(self.a.id).fact(h.episode_key(0,'lessons'))
        self.assertEqual((fact.committed_revision,fact.origins),(1,('declared_history',)))

    def test_invalid_committed_household_is_rejected_before_sampling(self):
        group=self.group();group.household(0)
        for record in group._composition_reality._records.values():
            if record.key.attribute=='household':record.value['adults']=-1
        action=self.observe(self.a,group);self.enc.schedule_choice((action,));self.enc.time=1
        with patch('statistical_group.composition_rng',side_effect=AssertionError('reroll')):
            with self.assertRaises(ImpossibleRealization):self.unchanged(lambda:capture_objective_context(self.enc,1))

    def test_training_episode_missing_required_rank_is_rejected(self):
        h=self.history();key=h.episode_key(0,'lessons')
        recipe=EpisodeFacts((Fact(key,{'description':'Training','skill':'spot','rank_after':0}),))
        ctx=self.context(self.ask(self.b,h,recipe))
        with self.assertRaises(ImpossibleRealization):self.build(ctx)

    def test_conflicting_duplicate_claim_inside_one_recipe_has_no_precedence(self):
        h=self.history();key=h.episode_key(0,'lessons')
        recipe=EpisodeFacts((Fact(key,{'description':'A'}),Fact(key,{'description':'B'})))
        ctx=self.context(self.ask(self.b,h,recipe))
        with self.assertRaises(ImpossibleRealization):self.build(ctx)

    def test_foreign_subject_fact_is_not_accepted_as_support(self):
        h=self.history();recipe=self.recipe(h,extra=(Fact(FactKey(self.b.id,'skill_rank',0,'spot'),0),))
        ctx=self.context(self.ask(self.b,h,recipe))
        with self.assertRaises(ImpossibleRealization):self.build(ctx)

    def test_custom_literal_generator_subclass_is_not_executed(self):
        h=self.history();called=Mock()
        class Unsafe(EpisodeFacts):
            def __call__(self,*args):called();raise AssertionError('unsafe literal subclass')
        key=h.episode_key(0,'lessons');recipe=Unsafe((Fact(key,{'description':'Literal'}),))
        action=self.ask(self.b,h,recipe);self.enc.schedule_choice((action,));self.enc.time=1
        with self.assertRaises(UnsupportedEvaluation):capture_objective_context(self.enc,1)
        called.assert_not_called()

    def test_custom_group_subclass_is_refused_without_counts_callback(self):
        called=Mock()
        class UnsafeGroup(StatisticalGroup):
            def counts(self):called();raise AssertionError('unsafe group')
        config=json.loads((ROOT/'examples/nomadic_group.json').read_text())
        group=UnsafeGroup('unsafe','unsafe',config,81);self.world.add_object(group);self.enc.add_object(group.id)
        action=self.observe(self.a,group);self.enc.schedule_choice((action,));self.enc.time=1
        with self.assertRaises(UnsupportedEvaluation):capture_objective_context(self.enc,1)
        called.assert_not_called()

    def test_custom_observer_subclass_is_refused_without_evidence_callback(self):
        from group_observation import SampledGroupObservation
        called=Mock()
        class UnsafeObserver(SampledGroupObservation):
            def sample(self,*args):called();raise AssertionError('evidence callback')
        group=self.group()
        action=ObserveGroupAction(self.world,self.a.id,group.id,0,observation=UnsafeObserver(100,50))
        self.enc.schedule_choice((action,));self.enc.time=1
        with self.assertRaises(UnsupportedEvaluation):capture_objective_context(self.enc,1)
        called.assert_not_called()

    def test_custom_action_type_is_refused_before_dynamic_access(self):
        group=self.group();action=self.observe(self.a,group);self.enc.schedule_choice((action,));self.enc.time=1
        class UnsafeAction(ObserveGroupAction):
            def __getattribute__(self,name):raise AssertionError('unsafe Action access')
        unsafe=object.__new__(UnsafeAction)
        object.__getattribute__(unsafe,'__dict__').update(action.__dict__)
        self.world.event_history[action.id]=unsafe
        with self.assertRaises(UnsupportedEvaluation):capture_objective_context(self.enc,1)

    def test_future_objective_actions_do_not_realize_early(self):
        group=self.group();action=ObserveGroupAction(self.world,self.a.id,group.id,0,duration=2,
            observation={'coarse_range_m':100,'detailed_range_m':50})
        ctx=self.context(action);candidate=self.build(ctx)
        self.assertEqual(dict(candidate.requests),{});self.assertEqual(dict(candidate.subjects),{});self.assertEqual(candidate.draws,())
        self.assertEqual(group._composition_reality.revision,0)

    def test_lost_awareness_is_legitimate_inapplicable_history_request(self):
        h=self.history();action=self.ask(self.b,h);self.enc.schedule_choice((action,))
        self.enc.clear_awareness(self.b.id,self.a.id);self.enc.time=1
        ctx=capture_objective_context(self.enc,1);candidate=self.build(ctx)
        self.assertEqual(candidate.requests[action.id].status,'not_aware')
        self.assertEqual(dict(candidate.subjects),{})

    def test_new_facts_have_no_fabricated_committed_revision(self):
        group=self.group();candidate=self.build(self.context(self.observe(self.a,group)))
        self.assertTrue(all(not fact.established and fact.committed_revision is None for fact in candidate.subject(group.id).facts.values()))
        self.assertEqual(candidate.subject(group.id).base_revision,0)


    def test_empty_native_composition_is_supported_without_household_draws(self):
        group=self.group();group.config['composition']['households_cdf']=[[0,1.0]]
        candidate=self.build(self.context(self.observe(self.a,group)))
        self.assertEqual(dict(candidate.subject(group.id).counts),dict(adults=0,children=0,livestock=0,dogs=0,humans=0,households=0))
        self.assertEqual(len(candidate.draws),1)
        self.assertEqual(next(iter(candidate.subject(group.id).facts.values())).supporting_keys,())

    def test_invalid_cached_scalar_type_is_not_equated_with_integer_truth(self):
        group=self.group();group.counts();group._counts['households']=True
        ctx=self.context(self.observe(self.a,group))
        with self.assertRaises(EvaluationIntegrityError):self.build(ctx)
