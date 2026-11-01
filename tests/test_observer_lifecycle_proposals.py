"""5B3: complete supported-family proposals remain entirely inactive."""
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
import random
import sys
from types import MappingProxyType
import unittest
from unittest.mock import Mock, patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import test_shared_objective_reality as fixtures
from observer_proposals import (capture_observer_context, build_supported_candidate,
    ObservationEffect, InterpretationEffect, BeliefAcquisitionEffect, AccountDeliveryEffect,
    ReservationReleaseEffect, PostCommitNotificationIntent, observation_rng)
from action_evaluation import UnsupportedEvaluation, EvaluationIntegrityError, PracticeEffect
from activities import SpotAction, RunAction
from group_observation import ObserveGroupAction, SampledGroupObservation
from field_interpretation import FieldInterpreter
from field_observation import BeliefLedger
from history_conversation import AskAboutPastAction
from objective_reality import EpisodeFacts
from realization import Fact, ImpossibleRealization
from spatial.state import CartesianPosition
from melee_combat import MeleeStrike
from melee_defense import MeleeDefense


class TestObserverLifecycleProposals(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.TestSharedObjectiveReality();self.f.setUp()
        self.world,self.enc=self.f.world,self.f.enc
        self.a,self.b,self.c=self.f.a,self.f.b,self.f.c
        for actor in self.f.beings:actor.set_skill_level(self.world.get_skill_dictionary(),'spot',0)

    def observe(self,actor,group,roll=20,ledger=None,xp=None,start=0):
        key=actor.name
        seed=next(s for s in range(10000) if observation_rng(s,key,group.id,start,'d20').randint(1,20)==roll)
        return ObserveGroupAction(self.world,actor.id,group.id,start,seed=seed,random_key=key,
            observation={'coarse_range_m':100,'detailed_range_m':50},ledger=ledger,experience=xp)

    def context(self,*actions):
        self.enc.schedule_choice(actions);self.enc.time=max(__import__('math').ceil(a.end_time) for a in actions)
        # RunAction measures displacement produced while its interval is live.
        for action in actions:
            if isinstance(action,RunAction):
                actor=self.world.get_object_by_id(action.actor_id);pos=actor.get_position()
                actor.set_position(CartesianPosition(pos.x+1,pos.y,pos.z))
        return capture_observer_context(self.enc,int(self.enc.time))

    def build(self,context,**kwargs):
        before=repr(context)
        try:return self.f.unchanged(lambda:build_supported_candidate(context,**kwargs))
        finally:self.assertEqual(repr(context),before)

    def test_two_observers_one_truth_distinct_evidence_belief_and_practice(self):
        group=self.f.group();la,lb=BeliefLedger(self.a.id),BeliefLedger(self.b.id)
        one,two=self.observe(self.a,group,ledger=la),self.observe(self.b,group,ledger=lb)
        ctx=self.context(one,two);candidate=self.build(ctx)
        self.assertEqual(candidate.coverage,'complete_supported_due_set')
        self.assertIs(candidate.objective.companion,candidate.boundary)
        self.assertIs(candidate.effects,candidate.boundary.effects)
        self.assertEqual(set(candidate.boundary.actions),{one.id,two.id})
        first=candidate.target(self.a.id).observer_state.observations[one.id]
        second=candidate.target(self.b.id).observer_state.observations[two.id]
        self.assertNotEqual(first.reported_position,second.reported_position)
        self.assertEqual(len(candidate.objective.subject(group.id).facts),4)
        self.assertTrue(all(set(u.consumed_by)=={one.id,two.id} for u in candidate.objective_use))
        self.assertEqual(candidate.target(self.a.id).practice_state.skill_experience['spot'],12)
        self.assertEqual(len(candidate.recipients),2)
        self.assertEqual(la.evidence,());self.assertEqual(lb.evidence,())
        self.assertIsNone(group._counts)
        self.assertFalse(candidate.ready_for_publication);self.assertFalse(candidate.boundary.ready_for_publication)

    def test_known_truth_has_no_objective_draws_but_observer_noise_remains(self):
        group=self.f.group();group.counts();one,two=self.observe(self.a,group),self.observe(self.b,group)
        candidate=self.build(self.context(one,two))
        self.assertEqual(candidate.objective.draws,())
        self.assertEqual(len([t for t in candidate.observer_trace if t.stage=='evidence']),2)
        self.assertTrue(all(not u.eligible_new_fact for u in candidate.objective_use))

    def test_sampling_interpretation_and_keyed_rng_match_native_single_action(self):
        group=self.f.group();action=self.observe(self.a,group)
        candidate=self.build(self.context(action))
        observation=candidate.target(self.a.id).observer_state.observations[action.id]
        interpretation=candidate.target(self.a.id).observer_state.interpretations[action.id]
        action.resolve(10)  # Independent live comparison after pure nonmutation check.
        self.assertEqual(observation,action.field_observation)
        self.assertEqual(interpretation,action.field_interpretation)
        traces=[t for t in candidate.observer_trace if t.stage=='d20']
        self.assertEqual(traces[0].roll,action.roll)

    def test_failed_roll_needs_no_truth_and_only_native_failure_practice(self):
        group=self.f.group();action=self.observe(self.a,group,roll=1)
        ctx=self.context(action)
        with patch('statistical_group.composition_rng',side_effect=AssertionError('unused truth')):
            candidate=self.build(ctx)
        self.assertEqual(candidate.boundary.actions[action.id].outcome,'failure')
        self.assertEqual(dict(candidate.objective.subjects),{})
        self.assertEqual(candidate.target(self.a.id).practice_state.skill_experience['spot'],18)
        self.assertEqual(dict(candidate.target(self.a.id).observer_state.observations),{})
        self.assertTrue(all(not u.constructed and not u.eligible_new_fact for u in candidate.objective_use))

    def test_one_success_retains_truth_even_when_another_observer_fails(self):
        group=self.f.group();one,two=self.observe(self.a,group),self.observe(self.b,group,roll=1)
        c=self.build(self.context(one,two))
        self.assertTrue(all(set(u.requested_by)=={one.id,two.id} and u.consumed_by==(one.id,) and u.eligible_new_fact for u in c.objective_use))
        self.assertEqual(c.target(self.b.id).practice_state.skill_experience['spot'],18)

    def test_out_of_range_and_unplaced_have_no_evidence_or_awards(self):
        group=self.f.group();one,two=self.observe(self.a,group),self.observe(self.b,group)
        self.enc.schedule_choice((one,two));group.set_position(CartesianPosition(1000,0,0));self.b.spatial_state=None;self.enc.time=1
        c=self.build(capture_observer_context(self.enc,1))
        self.assertEqual([c.boundary.actions[a.id].outcome for a in (one,two)],['out_of_range','unplaced'])
        self.assertEqual(c.target(self.a.id).practice_state.exercises,())
        self.assertEqual(c.target(self.b.id).practice_state.exercises,())

    def test_group_observation_does_not_invent_awareness_prerequisite(self):
        group=self.f.group();action=self.observe(self.a,group)
        self.assertFalse(self.enc.is_aware(self.a.id,group.id))
        c=self.build(self.context(action));self.assertEqual(c.boundary.actions[action.id].outcome,'success')
        self.assertIn(group.id,c.target(self.a.id).aware_of)
        self.assertFalse(self.enc.is_aware(self.a.id,group.id))

    def test_two_heard_accounts_share_objective_episode_but_not_payload_ownership(self):
        h=self.f.history();recipe=self.f.recipe(h,'Real description',rank=0);accounts=[]
        one=AskAboutPastAction(self.world,self.b.id,self.a.id,0,episode_time=0,topic='lessons',generate=recipe,received_accounts=accounts)
        two=AskAboutPastAction(self.world,self.c.id,self.a.id,0,episode_time=0,topic='lessons',generate=recipe,
            received_accounts=accounts,substituted_claim='Inaccurate spoken claim')
        candidate=self.build(self.context(one,two))
        self.assertEqual(len(candidate.objective.subject(self.a.id).facts),2)
        self.assertEqual(candidate.target(self.b.id).observer_state.heard_accounts[one.id].words,'Real description')
        self.assertEqual(candidate.target(self.c.id).observer_state.heard_accounts[two.id].words,'Inaccurate spoken claim')
        self.assertEqual(len(candidate.recipients),1)
        projection=next(iter(candidate.recipients.values()))
        self.assertEqual([a.action_id for a in projection.accounts],[one.id,two.id])
        self.assertEqual(projection.identity.role,'in_world_received_accounts')
        self.assertEqual(accounts,[]);self.assertIsNone(one.heard_account);self.assertIsNone(two.newly_realized)
        self.assertFalse(any(type(r.effect) is BeliefAcquisitionEffect for r in candidate.effects.values()))

    def test_history_unaware_is_normal_and_does_not_construct_truth(self):
        h=self.f.history();action=self.f.ask(self.b,h)
        self.enc.schedule_choice((action,));self.enc.clear_awareness(self.b.id,self.a.id);self.enc.time=1
        c=self.build(capture_observer_context(self.enc,1))
        self.assertEqual(c.boundary.actions[action.id].outcome,'not_aware')
        self.assertEqual(dict(c.objective.subjects),{})
        self.assertEqual(dict(c.target(self.b.id).observer_state.heard_accounts),{})

    def test_mixed_native_spot_observation_history_has_complete_coverage(self):
        group=self.f.group();h=self.f.history();observe=self.observe(self.a,group,start=5)
        ask=AskAboutPastAction(self.world,self.b.id,self.a.id,5,episode_time=0,
            topic='lessons',generate=self.f.recipe(h))
        spot=SpotAction(self.world,self.c.id,self.a.id,0,die_roll=1)
        candidate=self.build(self.context(observe,ask,spot))
        self.assertEqual(set(candidate.boundary.actions),{observe.id,ask.id,spot.id})
        self.assertEqual(candidate.boundary.coverage,'complete_supported_batch')
        self.assertEqual(set(candidate.lifecycle),set(candidate.boundary.actions))
        self.assertEqual(candidate.boundary.practice_validation,'validated')
        self.assertEqual(len(candidate.effects),len(set(candidate.effects)))

    def joint(self,rank):
        self.f.group()  # Keep the mixed scenario's objective world available.
        self.a.set_skill_level(self.world.get_skill_dictionary(),'run',1)
        self.a.record_skill_use(self.world.get_skill_dictionary(),'run',1490,action_id='prior',time=-2)
        h=self.a.begin_personal_history(earliest=-10,known_through=10,
                                        nondeclining_skills=('run',))
        from objective_reality import EpisodeFacts
        recipe=EpisodeFacts((
            Fact(h.episode_key(0,'lessons'),
                 {'description':'Prior lessons','skill':'run','rank_after':3},
                 'declared_history'),
            Fact(h.skill_key(0,'run'),3,'declared_history'),
            Fact(h.skill_key(6,'run'),rank,'declared_history'),
        ))
        spot=SpotAction(self.world,self.a.id,self.b.id,0,die_roll=1)
        run=RunAction(self.world,self.a.id,0,6,.5,experience=12)
        ask=AskAboutPastAction(self.world,self.c.id,self.a.id,0,episode_time=0,
            topic='lessons',generate=recipe,duration=6)
        return None,h,self.context(spot,run,ask),run

    def test_legitimate_run_award_changes_combined_transition_and_history_acceptability(self):
        _,h,ctx,action=self.joint(3);candidate=self.build(ctx)
        p=candidate.target(self.a.id).practice_state
        self.assertEqual(p.skill_experience['run'],1502)
        self.assertEqual(len(p.transitions),1);self.assertEqual(p.transitions[0].level_after,3)
        self.assertEqual([use.experience for use in p.exercises],[12])
        self.assertEqual(candidate.objective.subject(self.a.id).fact(h.skill_key(6,'run')).value,3)

    def test_incompatible_rank_rejected_after_all_actual_awards_without_reroll(self):
        _,_,ctx,_=self.joint(2)
        with self.assertRaises(ImpossibleRealization):self.build(ctx)
        with self.assertRaises(ImpossibleRealization):self.build(ctx)

    def test_no_interpretation_xp_is_invented_and_nonprogressive_retains_history(self):
        group=self.f.group();action=self.observe(self.a,group,xp={'success':300,'failure':0})
        self.enc.schedule_choice((action,));self.world.get_skill_dictionary().skills['spot']['is_progressive']=False;self.enc.time=1
        candidate=self.build(capture_observer_context(self.enc,1))
        p=candidate.target(self.a.id).practice_state
        self.assertEqual(len(p.exercises),1);self.assertEqual(p.skill_experience['spot'],300);self.assertEqual(p.level('spot'),0)

    def test_zero_experience_failure_still_records_one_native_attempt(self):
        group=self.f.group();action=self.observe(self.a,group,roll=1,xp={'success':0,'failure':0})
        p=self.build(self.context(action)).target(self.a.id).practice_state
        self.assertEqual(len(p.exercises),1);self.assertEqual(p.exercises[0].experience,0)

    def test_belief_projection_matches_native_learn_without_live_write(self):
        group=self.f.group();ledger=BeliefLedger(self.a.id)
        action=self.observe(self.a,group,ledger=ledger);c=self.build(self.context(action))
        observer=c.target(self.a.id).observer_state
        reference=BeliefLedger(self.a.id)
        reference.learn(observer.observations[action.id],interpretation=observer.interpretations[action.id])
        belief=next(iter(c.recipients.values()))
        self.assertEqual(belief.belief_history,reference.belief_history)
        self.assertEqual(dict(belief.evidence),reference._evidence)
        self.assertEqual(ledger.evidence,())

    def test_shared_ledger_multiple_actions_keeps_native_acquisition_order(self):
        group=self.f.group();ledger=BeliefLedger(self.a.id)
        one,two=self.observe(self.a,group,ledger=ledger),self.observe(self.a,group,ledger=ledger)
        c=self.build(self.context(one,two));view=next(iter(c.recipients.values()));reference=BeliefLedger(self.a.id)
        obs=c.target(self.a.id).observer_state
        for action in (one,two):reference.learn(obs.observations[action.id],interpretation=obs.interpretations[action.id])
        self.assertEqual(view.belief_history,reference.belief_history)
        self.assertEqual(len(view.evidence),2);self.assertEqual(len(c.recipients),1)

    def test_duplicate_known_evidence_is_idempotent_but_not_a_second_revision(self):
        group=self.f.group();ledger=BeliefLedger(self.a.id);action=self.observe(self.a,group,ledger=ledger)
        ctx=self.context(action);first=self.build(ctx);obs=first.target(self.a.id).observer_state
        ledger.learn(obs.observations[action.id],interpretation=obs.interpretations[action.id])
        second=self.build(capture_observer_context(self.enc,1))
        effects=[r.effect for r in second.effects.values() if type(r.effect) is BeliefAcquisitionEffect]
        self.assertEqual([e.acquired for e in effects],[False])
        self.assertEqual(next(iter(second.recipients.values())).belief_history,ledger.belief_history)

    def test_completion_and_reservation_intents_do_not_change_world(self):
        wid=self.world.make_weapon_for_being(self.a.id,'Dagger','Knife');self.world.arm_being(self.a.id,wid,'right hand')
        strike=MeleeStrike(self.enc,self.a.id,self.b.id,wid,motion='thrust',reach=3)
        ctx=self.context(strike);before=self.enc.active_reservations;c=self.build(ctx,notify=True)
        life=c.lifecycle[strike.id]
        self.assertEqual((life.from_queue,life.to_queue,life.status),('pending','finished','finished'))
        releases=[r.effect for r in c.effects.values() if type(r.effect) is ReservationReleaseEffect]
        self.assertEqual([r.object_id for r in releases],[wid]);self.assertTrue(releases[0].after_settlement)
        self.assertEqual(self.enc.active_reservations,before);self.assertIsNone(strike.combat_result)
        self.assertTrue(all(type(r.effect) is PostCommitNotificationIntent and r.effect.after_commit for r in c.notification_intents))
        self.assertIn(strike.id,self.enc.pending_action_list)

    def test_cancelled_observer_has_interrupted_outcome_and_no_awards_or_truth(self):
        group=self.f.group();action=self.observe(self.a,group)
        self.enc.schedule_choice((action,));self.enc.cancel_action(action.id,reason='early termination');self.enc.time=1
        c=self.build(capture_observer_context(self.enc,1))
        self.assertEqual(c.boundary.actions[action.id].outcome,'interrupted')
        self.assertEqual((c.lifecycle[action.id].from_queue,c.lifecycle[action.id].to_queue),('cancelled','cancelled'))
        self.assertEqual(c.target(self.a.id).practice_state.exercises,());self.assertEqual(dict(c.objective.subjects),{})

    def test_custom_completion_callback_is_refused_before_invocation(self):
        group=self.f.group();action=self.observe(self.a,group);self.enc.schedule_choice((action,));self.enc.time=1
        unsafe=Mock(side_effect=AssertionError('completion'))
        with patch.object(ObserveGroupAction,'on_completed',unsafe):
            with self.assertRaises(UnsupportedEvaluation):capture_observer_context(self.enc,1)
        unsafe.assert_not_called()

    def test_instance_completion_callback_is_refused_before_invocation(self):
        run=RunAction(self.world,self.a.id,0,1,1);self.enc.schedule_choice((run,));self.enc.time=1
        run.on_completed=Mock(side_effect=AssertionError('hook'))
        with self.assertRaises(UnsupportedEvaluation):capture_observer_context(self.enc,1)
        run.on_completed.assert_not_called()

    def test_unsafe_account_container_is_refused_before_append(self):
        h=self.f.history();action=self.f.ask(self.b,h);self.enc.schedule_choice((action,));self.enc.time=1
        class Unsafe(list):
            def append(self,value):raise AssertionError('append')
        # Native signature must still match; use container before scheduling instead.
        other=AskAboutPastAction(self.world,self.c.id,self.a.id,0,episode_time=0,topic='lessons',generate=self.f.recipe(h),received_accounts=Unsafe())
        self.enc.time=0;self.enc.schedule_choice((other,));self.enc.time=1
        with self.assertRaises(UnsupportedEvaluation):capture_observer_context(self.enc,1)

    def test_missing_interpreter_rank_is_explicit_refusal_not_a_new_training_rule(self):
        group=self.f.group();self.a.current.skills.skills.pop('spot',None)
        ctx=self.context(self.observe(self.a,group))
        with self.assertRaisesRegex(UnsupportedEvaluation,'explicit nonnegative integer rank'):self.build(ctx)

    def test_frozen_recipients_sensor_policy_and_claim_do_not_alias_live_edits(self):
        group=self.f.group();ledger=BeliefLedger(self.a.id);action=self.observe(self.a,group,ledger=ledger)
        ctx=self.context(action);expected=self.build(ctx)
        action.observer.count_sigmas['detailed']['dogs']=9999;action.experience_policy['success']=999
        ledger._evidence.clear();self.a.set_skill_level(self.world.get_skill_dictionary(),'spot',99)
        self.assertEqual(self.build(ctx),expected)
        with self.assertRaises(TypeError):expected.target(self.a.id).observer_state.observations[action.id].reports['dogs']=None
        with self.assertRaises(FrozenInstanceError):next(iter(expected.recipients.values())).observer_id='other'

    def test_late_failure_returns_nothing_and_retry_is_identical(self):
        group=self.f.group();ctx=self.context(self.observe(self.a,group));expected=self.build(ctx)
        with patch('observer_proposals._validate_effect_rows',side_effect=RuntimeError('late failure')):
            with self.assertRaises(RuntimeError):self.build(ctx)
        self.assertEqual(self.build(ctx),expected)

    def test_duplicate_effect_injection_and_foreign_boundary_are_rejected(self):
        group=self.f.group();ctx=self.context(self.observe(self.a,group))
        from observer_proposals import _append_effect
        def duplicate(rows,*args):
            _append_effect(rows,*args);rows.append(rows[-1])
        with patch('observer_proposals._append_effect',duplicate):
            with self.assertRaises(EvaluationIntegrityError):self.build(ctx)
        with self.assertRaises(EvaluationIntegrityError):self.build(replace(ctx,snapshot=replace(ctx.snapshot,boundary=2)))

    def test_no_live_mutator_or_delivery_callback_is_used(self):
        group=self.f.group();ledger=BeliefLedger(self.a.id);ctx=self.context(self.observe(self.a,group,ledger=ledger))
        with patch.object(group,'counts',side_effect=AssertionError('live counts')),patch.object(ledger,'learn',side_effect=AssertionError('live belief')),patch.object(self.a,'record_skill_use',side_effect=AssertionError('award')),patch('group_observation.SampledGroupObservation.sample',side_effect=AssertionError('live sampler')):
            self.build(ctx,notify=True)

    def test_live_step_stays_legacy_and_does_not_activate_builder(self):
        group=self.f.group();action=self.observe(self.a,group);self.enc.schedule_choice((action,))
        with patch('observer_proposals.build_supported_candidate',side_effect=AssertionError('inactive')):
            self.enc.step(1)
        self.assertIn(action.id,self.enc.finished_action_list)


    def test_different_interpreter_skill_is_read_but_not_awarded_extra_xp(self):
        group=self.f.group();self.a.set_skill_level(self.world.get_skill_dictionary(),'run',4)
        action=self.observe(self.a,group);action.interpreter=FieldInterpreter('run',5)
        c=self.build(self.context(action));state=c.target(self.a.id)
        self.assertEqual(state.observer_state.interpretations[action.id].skill_level,4)
        self.assertEqual([u.skill_name for u in state.practice_state.exercises],['spot'])
        self.assertNotIn('run',state.practice_state.skill_experience)

    def test_observer_evidence_disagreement_is_not_objective_contradiction(self):
        from field_observation import FieldObservation,CountReport
        group=self.f.group();ledger=BeliefLedger(self.a.id)
        prior=FieldObservation('old',self.a.id,group.id,-1,CartesianPosition(30,0,0),1,
            {name:CountReport(1000,0) for name in ('humans','livestock','dogs')},'prior')
        ledger.learn(prior)
        c=self.build(self.context(self.observe(self.a,group,ledger=ledger)))
        belief=next(iter(c.recipients.values()))
        self.assertTrue(any(r.disputed for r in belief.belief_history))
        self.assertEqual(c.objective.subject(group.id).counts['humans'],9)
        self.assertEqual(len(ledger.evidence),1)

    def test_history_out_of_range_and_cancelled_accounts_are_no_effect_outcomes(self):
        h=self.f.history();one,two=self.f.ask(self.b,h),self.f.ask(self.c,h)
        self.enc.schedule_choice((one,two));self.enc.cancel_action(two.id);self.b.set_position(CartesianPosition(100,0,0));self.enc.time=1
        c=self.build(capture_observer_context(self.enc,1))
        self.assertEqual([c.boundary.actions[a.id].outcome for a in (one,two)],['out_of_range','interrupted'])
        self.assertEqual(dict(c.objective.subjects),{})
        self.assertTrue(all(not state.observer_state.heard_accounts for state in c.boundary.targets.values() if state.observer_state))

    def test_independent_in_world_account_lists_keep_independent_delivery_ids(self):
        h=self.f.history();first,second=[],[];recipe=self.f.recipe(h)
        actions=tuple(AskAboutPastAction(self.world,actor.id,self.a.id,0,episode_time=0,topic='lessons',generate=recipe,
            received_accounts=recipient) for actor,recipient in ((self.b,first),(self.c,second)))
        c=self.build(self.context(*actions))
        self.assertEqual(len(c.recipients),2)
        self.assertEqual([len(r.accounts) for r in c.recipients.values()],[1,1])
        deliveries=[r for r in c.effects.values() if type(r.effect) is AccountDeliveryEffect]
        self.assertEqual(len({r.identity for r in deliveries}),2)
        self.assertEqual(first,[]);self.assertEqual(second,[])

    def test_prior_account_duplicates_are_preserved_without_new_dedup_policy(self):
        from history_conversation import HeardAccount
        h=self.f.history();old=HeardAccount('prior',self.b.id,self.a.id,0,-1,'prior','Words')
        accounts=[old,old]
        action=AskAboutPastAction(self.world,self.b.id,self.a.id,0,episode_time=0,topic='lessons',generate=self.f.recipe(h),received_accounts=accounts)
        c=self.build(self.context(action));projection=next(iter(c.recipients.values()))
        self.assertEqual(projection.accounts[:2],(old,old));self.assertEqual(len(projection.accounts),3)
        self.assertEqual(accounts,[old,old])

    def test_conflicting_prior_belief_observation_identity_rejects_whole_candidate(self):
        from field_observation import FieldObservation,CountReport
        group=self.f.group();ledger=BeliefLedger(self.a.id);action=self.observe(self.a,group,ledger=ledger)
        ledger.learn(FieldObservation(action.id,self.a.id,group.id,0,CartesianPosition(30,0,0),1,
            {'dogs':CountReport(999,0)},'incompatible prior'))
        ctx=self.context(action)
        with self.assertRaises(EvaluationIntegrityError):self.build(ctx)

    def test_incomplete_interpretation_effect_is_rejected(self):
        group=self.f.group();ctx=self.context(self.observe(self.a,group))
        from observer_proposals import _append_effect
        def omit(rows,*args):
            if type(args[-1]) is not InterpretationEffect:_append_effect(rows,*args)
        with patch('observer_proposals._append_effect',omit):
            with self.assertRaisesRegex(EvaluationIntegrityError,'interpretation'):self.build(ctx)

    def test_custom_interpreter_and_belief_overrides_refuse_without_callbacks(self):
        group=self.f.group();ledger=BeliefLedger(self.a.id);action=self.observe(self.a,group,ledger=ledger)
        self.enc.schedule_choice((action,));self.enc.time=1
        unsafe=Mock(side_effect=AssertionError('unsafe custom calculation'))
        with patch.object(FieldInterpreter,'interpret',unsafe):
            with self.assertRaises(UnsupportedEvaluation):capture_observer_context(self.enc,1)
        with patch.object(BeliefLedger,'count_estimate',unsafe):
            with self.assertRaises(UnsupportedEvaluation):capture_observer_context(self.enc,1)
        unsafe.assert_not_called()

    def test_post_capture_mutating_hooks_cannot_enter_detached_evaluation(self):
        group=self.f.group();ledger=BeliefLedger(self.a.id);ctx=self.context(self.observe(self.a,group,ledger=ledger))
        unsafe=Mock(side_effect=AssertionError('post-capture callback'))
        with patch.object(ObserveGroupAction,'on_completed',unsafe),patch.object(BeliefLedger,'count_estimate',unsafe):
            self.build(ctx)
        unsafe.assert_not_called()

    def test_unsupported_action_family_is_not_skipped_or_run_live(self):
        from action import Action
        action=Action(self.world,0,None,'delay',self.a.id,self.b.id,None);self.enc.schedule_choice((action,));self.enc.time=1
        with self.assertRaises(UnsupportedEvaluation):capture_observer_context(self.enc,1)

    def test_complete_defense_strike_and_history_practice_reuse_native_dependencies(self):
        wid=self.world.make_weapon_for_being(self.a.id,'Dagger','Knife');self.world.arm_being(self.a.id,wid,'right hand')
        strike=MeleeStrike(self.enc,self.a.id,self.b.id,wid,motion='thrust',reach=3)
        defense=MeleeDefense(self.enc,self.b.id,self.a.id,kind='dodge',target_action_id=strike.id)
        h=self.f.history()
        ask=AskAboutPastAction(self.world,self.c.id,self.a.id,0,episode_time=0,topic='lessons',generate=self.f.recipe(h),duration=strike.end_time)
        ctx=self.context(strike,defense,ask)
        from action_evaluation import _ProvisionalRandom
        with patch.object(_ProvisionalRandom,'roll',side_effect=[20,1]):c=self.build(ctx)
        self.assertEqual(c.boundary.actions[strike.id].outcome,'dodged')
        self.assertEqual(c.boundary.actions[defense.id].outcome,'evaded')
        self.assertEqual(c.boundary.actions[ask.id].outcome,'heard')
        self.assertEqual(c.target(self.a.id).practice_state.skill_experience['Dagger'],10)
        self.assertEqual(c.target(self.b.id).practice_state.skill_experience['tumble'],10)
        self.assertIsNone(strike.defended_by)

    def test_unused_truth_is_not_constructed_to_validate_irrelevant_cache(self):
        group=self.f.group();group._counts={'invalid':True}
        action=self.observe(self.a,group,roll=1)
        c=self.build(self.context(action))
        self.assertEqual(c.boundary.actions[action.id].outcome,'failure')
        self.assertEqual(dict(c.objective.subjects),{})

    def test_objective_claim_conflicts_still_reject_complete_candidate(self):
        h=self.f.history();one=self.f.ask(self.b,h,self.f.recipe(h,'A'));two=self.f.ask(self.c,h,self.f.recipe(h,'B'))
        ctx=self.context(one,two)
        with self.assertRaises(ImpossibleRealization):self.build(ctx)

    def test_notification_intents_are_optional_after_commit_only(self):
        group=self.f.group();ctx=self.context(self.observe(self.a,group));plain=self.build(ctx);notified=self.build(ctx,notify=True)
        self.assertEqual(plain.notification_intents,())
        self.assertEqual(len(notified.notification_intents),1)
        self.assertTrue(notified.notification_intents[0].effect.after_commit)
        self.assertEqual(plain.objective.subjects,notified.objective.subjects)


    def test_low_level_core_reconciliation_cannot_claim_observer_completion(self):
        from action_settlement import reconcile_boundary
        group=self.f.group();c=self.build(self.context(self.observe(self.a,group)))
        replay=reconcile_boundary(c.context.snapshot,c.boundary.evaluation)
        self.assertEqual(replay.coverage,'core_effects_only')
        self.assertFalse(replay.observer_reconciliation_complete)
        self.assertTrue(any('5B3' in name for name in replay.publication_dependencies))
        self.assertTrue(c.boundary.observer_reconciliation_complete)
        self.assertEqual(c.boundary.coverage,'complete_supported_batch')
        self.assertFalse(c.boundary.ready_for_publication)

    def test_reordering_and_adding_observers_does_not_change_shared_truth_or_noise(self):
        group=self.f.group();one,two=self.observe(self.a,group),self.observe(self.b,group)
        first=self.build(self.context(one,two))
        first_reports=first.target(self.a.id).observer_state.observations[one.id].reports
        first_position=first.target(self.a.id).observer_state.observations[one.id].reported_position
        truth=first.objective.subject(group.id).counts
        self.setUp()
        group=self.f.group();one,two=self.observe(self.a,group),self.observe(self.b,group)
        second=self.build(self.context(two,one))
        self.assertEqual(second.objective.subject(group.id).counts,truth)
        self.assertEqual(second.target(self.a.id).observer_state.observations[one.id].reports,first_reports)
        self.assertEqual(second.target(self.a.id).observer_state.observations[one.id].reported_position,first_position)
        self.setUp()
        group=self.f.group();one=self.observe(self.a,group)
        single=self.build(self.context(one))
        self.assertEqual(single.objective.subject(group.id).counts,truth)
        self.assertEqual(single.target(self.a.id).observer_state.observations[one.id].reports,first_reports)
