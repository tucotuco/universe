"""5C3A gated programmatic native progression; legacy default remains intact."""
from pathlib import Path
import itertools
import math
import random
import sys
import tempfile
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import patch,Mock
import uuid

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import test_interval_staging as fixtures
import test_atomic_publication as publication_fixtures
import test_action_settlement as combat_fixtures
from transactional_progression import TransactionalProgressionError
from atomic_publication import (RNGCursor,PublicationFailure,RollbackIntegrityFailure,
    PublicationOwnershipError,publication_boundary,publish_interval_candidate,target_interval_history)
from action import Action
from activities import RunAction,SpotAction
from encounter import Encounter
from field_observation import BeliefLedger
from history_conversation import AskAboutPastAction
from group_observation import ObserveGroupAction
from melee_combat import MeleeStrike
from melee_defense import MeleeDefense
from action_evaluation import _ProvisionalRandom,RandomDraw,UnsupportedEvaluation
from interval_staging import StaleInterval
from realization import Fact,ImpossibleRealization
from spatial.state import CartesianPosition
from spatial.frame import LocalFrame
from physiology_registry import PhysiologyRegistry,PhysiologyDefinition


class TestTransactionalProgression(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.TestIntervalStaging();self.f.setUp()
        self.world,self.enc=self.f.world,self.f.enc
        self.a,self.b,self.c=self.f.a,self.f.b,self.f.c
        self.rng=RNGCursor(random.Random(141).getstate())

    def enable(self,**kwargs):
        return self.enc.enable_transactional_progression(quiescent=True,rng_owner=kwargs.pop('rng_owner',self.rng),**kwargs)

    def raw(self):return publication_fixtures.raw_graph(self.world,self.enc)

    def test_dead_weak_mode_binding_does_not_poison_reused_legacy_encounter_id(self):
        from transactional_progression import _BINDINGS,mode_of
        key=id(self.enc);marker=object();previous=_BINDINGS.get(key,marker)
        _BINDINGS[key]=SimpleNamespace(encounter=lambda:None)
        try:
            self.assertEqual(mode_of(self.enc),'legacy')
            self.assertNotIn(key,_BINDINGS)
        finally:
            if previous is marker:_BINDINGS.pop(key,None)
            else:_BINDINGS[key]=previous

    def test_legacy_is_default_and_still_calls_native_resolver(self):
        action=self.f.spot();self.enc.schedule_action(action)
        self.assertEqual(self.enc.progression_mode,'legacy')
        original=SpotAction.resolve;seen=[]
        def resolve(action,dc):seen.append(action.id);return original(action,dc)
        with patch.object(SpotAction,'resolve',resolve):self.enc.step(6)
        self.assertEqual(seen,[action.id]);self.assertFalse(self.enc.__dict__.get('_atomic_interval_history'))

    def test_explicit_mode_is_visible_and_irreversible(self):
        descriptor=self.enable();self.assertEqual(self.enc.progression_mode,'transactional')
        self.assertEqual(descriptor.rng_role,'caller_cursor')
        before=self.raw()
        with self.assertRaises(ValueError):self.enable()
        with self.assertRaises(AttributeError):self.enc.progression_mode='legacy'
        self.assertEqual(self.raw(),before)

    def test_quiescent_contract_is_required(self):
        before=self.raw()
        with self.assertRaises(PublicationOwnershipError):self.enc.enable_transactional_progression()
        self.assertEqual(self.enc.progression_mode,'legacy');self.assertEqual(self.raw(),before)

    def test_already_progressed_or_fractional_legacy_graph_cannot_enable(self):
        for duration in (.25,1):
            f=fixtures.TestIntervalStaging();f.setUp();f.enc.step(duration)
            before=publication_fixtures.raw_graph(f.world,f.enc)
            with self.assertRaises(ValueError):f.enc.enable_transactional_progression(quiescent=True)
            self.assertEqual(publication_fixtures.raw_graph(f.world,f.enc),before)

    def test_legacy_direct_resolution_attempt_cannot_be_disguised_as_fresh_graph(self):
        action=self.f.spot();self.enc.schedule_action(action);action.resolve(10)
        self.assertIsNone(action.resolution)  # Legacy direct resolver does not install the result.
        before=self.raw()
        with self.assertRaisesRegex(ValueError,'legacy'):self.enable()
        self.assertEqual(self.raw(),before);self.assertEqual(self.enc.progression_mode,'legacy')

    def test_faulted_and_unsupported_initial_graphs_reject_pre_mode(self):
        self.enc.boundary_fault={'error':'legacy'};before=self.raw()
        with self.assertRaises(ValueError):self.enable()
        self.assertEqual(self.raw(),before);self.assertEqual(self.enc.progression_mode,'legacy')
        self.enc.boundary_fault=None
        delay=Action(self.world,0,None,'delay',self.a.id,self.b.id,None);self.enc.schedule_action(delay)
        before=self.raw()
        with self.assertRaises(UnsupportedEvaluation):self.enable()
        self.assertEqual(self.raw(),before);self.assertEqual(self.enc.progression_mode,'legacy')

    def test_existing_c2_published_graph_cannot_be_retroactively_selected(self):
        candidate=self.enc.prepare_interval_candidate(1)
        with publication_boundary(self.enc,quiescent=True) as owner:publish_interval_candidate(self.enc,candidate,ownership=owner)
        before=self.raw()
        with self.assertRaises(ValueError):self.enable()
        self.assertEqual(self.raw(),before)

    def test_tactical_and_ai_owned_graphs_cannot_select_native_mode(self):
        from tactical_duel import TacticalDuel
        from ai_duel import AgentDuel
        for kind in (TacticalDuel,AgentDuel):
            game=kind(seed=21);before=publication_fixtures.raw_graph(game.world,game.encounter);rng=random.getstate()
            with self.assertRaisesRegex(ValueError,'facade'):game.encounter.enable_transactional_progression(quiescent=True)
            self.assertEqual(publication_fixtures.raw_graph(game.world,game.encounter),before)
            self.assertEqual(random.getstate(),rng)

    def test_missing_or_changed_mode_binding_never_falls_back(self):
        self.enable();saved=self.enc.__dict__.pop('_transactional_mode')
        before=self.raw()
        with self.assertRaisesRegex(ValueError,'binding'):self.enc.step(1)
        self.assertEqual(self.raw(),before)
        self.enc.__dict__['_transactional_mode']=saved
        self.enc.step(1);self.assertEqual(self.enc.time,1)

    def test_single_step_matches_direct_c2_candidate_exactly(self):
        self.enable();action=self.f.spot(roll=None);self.enc.schedule_action(action)
        self.enc.step(5)
        candidate=self.enc.prepare_interval_candidate(6,rng_owner=self.rng)
        result=self.enc.step(1)
        self.assertEqual(result.completed_action_ids,tuple(candidate.supported_candidate.boundary.actions))
        self.assertEqual(action.resolution,candidate.supported_candidate.boundary.actions[action.id])
        self.assertEqual(target_interval_history(self.a)[-1].state,candidate.supported_candidate.target(self.a.id))
        self.assertEqual(self.rng.state,candidate.provisional_rng.after)
        self.assertEqual(self.enc._atomic_interval_history[-1].action_ids,result.completed_action_ids)

    def test_no_legacy_dispatch_or_resolver_is_called_by_step(self):
        self.enable();action=self.f.spot();self.enc.schedule_action(action)
        # Instance callbacks are intentionally refused, so watch the approved
        # native implementation without replacing its class contract.
        with patch('transactional_progression.guard_legacy_action',side_effect=AssertionError('legacy callback')):
            self.enc.step(6)
        self.assertEqual(action.resolution.outcome,'success');self.assertEqual(self.enc.time,6)

    def test_each_boundary_has_one_owned_native_stage_and_publish(self):
        self.enable()
        import atomic_publication,transactional_progression
        original=atomic_publication.publish_interval_candidate;seen=[]
        def publish(enc,candidate,**kw):
            self.assertIsNotNone(atomic_publication._ACTIVE);self.assertTrue(enc.universe._schedule_lock._is_owned())
            seen.append((enc.time,candidate.boundary));return original(enc,candidate,**kw)
        with patch('atomic_publication.publish_interval_candidate',publish):self.enc.step(3)
        self.assertEqual(seen,[(0,1),(1,2),(2,3)])
        self.assertIsNone(atomic_publication._ACTIVE);self.assertEqual(len(self.enc.fatigue_frame_history),3)

    def test_fractional_starts_and_later_member_publish_whole_choice(self):
        self.enable();one=RunAction(self.world,self.a.id,.2,1,1,experience=7);two=RunAction(self.world,self.c.id,.7,1,1)
        view=self.enc.schedule_choice((one,two));self.assertEqual(view.state,'accepted');self.assertEqual(self.enc.pending_action_list,[])
        self.enc.step(1,velocities={self.a.id:(10,0,0),self.c.id:(10,0,0)})
        self.assertEqual(one.start_position,CartesianPosition(2,0,0));self.assertEqual(two.start_position,CartesianPosition(11,0,0))
        self.assertIs(self.world.event_history[one.id],one);self.assertIs(self.world.event_history[two.id],two)
        self.assertIsNone(one.resolution);self.assertEqual(self.enc.get_choice(view.id).state,'executing')
        self.enc.step(1,velocities={self.a.id:(10,0,0),self.c.id:(10,0,0)})
        self.assertEqual(one.resolution.outcome,'success');self.assertEqual(self.a.skill_experience['run'],7)

    def test_origin_partial_interval_ends_at_integer_without_boundary_zero(self):
        # Fresh independent world avoids the intentionally refused shared-owner case.
        from universe import Universe
        from library import Library
        world=Universe('Partial',library=Library(config_dir=str(Path(__file__).resolve().parents[1]/'src/config')))
        being=world.get_object_by_id(world.make_being('Human','P'));being.set_position(CartesianPosition(0,0,0))
        enc=Encounter(world,10,.25,initiated=True);enc.add_being(being.id);world.add_event(enc)
        enc.enable_transactional_progression(quiescent=True)
        enc.step(.75,velocities={being.id:(4,0,0)})
        self.assertEqual(enc.time,1);self.assertEqual(being.get_position(),CartesianPosition(3,0,0))
        self.assertEqual(enc.fatigue_frame_history[0]['start'],.25);self.assertEqual(enc.last_processed_boundary,1)

    def test_fractional_only_and_long_tail_requests_refuse_before_any_commit(self):
        self.enable();before=self.raw();rng=self.rng.state
        for duration in (.25,1.5,2.75):
            with self.subTest(duration=duration),self.assertRaisesRegex(ValueError,'integer'):self.enc.step(duration,velocities={self.a.id:(1,0,0)})
            self.assertEqual(self.raw(),before);self.assertEqual(self.rng.state,rng)

    def test_invalid_duration_inputs_do_not_invoke_numeric_callbacks(self):
        self.enable()
        class Unsafe:
            def __float__(self):raise AssertionError('unsafe conversion')
        before=self.raw()
        for duration in (True,0,-1,float('nan'),float('inf'),'1',Unsafe()):
            with self.subTest(duration=type(duration).__name__),self.assertRaises(ValueError):self.enc.step(duration)
            self.assertEqual(self.raw(),before)

    def test_invalid_motion_or_end_limit_refuses_whole_long_request(self):
        self.enc.end_time=2;self.enable();before=self.raw()
        for kwargs in ({'duration':3},{'duration':2,'velocities':{self.a.id:(float('inf'),0,0)}},
                       {'duration':2,'velocities':{'missing':(1,0,0)}},{'duration':2,'velocity_frame':'unknown'}):
            with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):self.enc.step(**kwargs)
            self.assertEqual(self.raw(),before)

    def test_native_local_velocity_is_normalized_once_for_the_long_step(self):
        self.enc.set_local_frame(LocalFrame(CartesianPosition(0,0,0),(0,1,0),(-1,0,0),(0,0,1)));self.enable()
        self.enc.step(2,velocities={self.a.id:(3,0,0)},velocity_frame='local')
        self.assertEqual(self.a.get_position(),CartesianPosition(0,6,0))

    def test_exact_nominal_end_and_nextafter_stay_in_their_respective_batches(self):
        self.enable();one=self.f.spot();start=.25
        two=SpotAction(self.world,self.c.id,self.b.id,start,die_roll=20);self.enc.schedule_choice((one,two))
        self.enc.step(6);self.assertIsNotNone(one.resolution);self.assertIsNone(two.resolution)
        self.enc.step(1);self.assertIsNotNone(two.resolution)
        self.assertEqual(two._atomic_lifecycle.nominal_end,6.25);self.assertEqual(two._atomic_lifecycle.boundary,7)

    def test_mixed_group_history_spot_run_complete_route_and_distinct_beliefs(self):
        group=self.f.f.f.group();history=self.f.f.f.history();la,lb=BeliefLedger(self.a.id),BeliefLedger(self.b.id);accounts=[]
        self.enable();one,two=self.f.f.observe(self.a,group,ledger=la),self.f.f.observe(self.b,group,ledger=lb)
        ask=AskAboutPastAction(self.world,self.c.id,self.a.id,0,episode_time=0,topic='lessons',generate=self.f.f.f.recipe(history),received_accounts=accounts)
        run=RunAction(self.world,self.c.id,0,6,1,experience=7);spot=self.f.spot()
        ask.end_time=6
        self.enc.schedule_choice((one,two,ask,run,spot));result=self.enc.step(6,velocities={self.c.id:(1,0,0)})
        self.assertEqual(set(result.completed_action_ids),{x.id for x in (one,two,ask,run,spot)})
        self.assertEqual(group._composition_reality.revision,1);self.assertNotEqual(la.evidence[0].reported_position,lb.evidence[0].reported_position)
        self.assertEqual(len(accounts),1);self.assertEqual(self.a.skill_experience.get('spot',0),12);self.assertEqual(self.c.skill_experience['run'],7)
        self.assertEqual(len(self.a.skill_use_history[-1].exercises),1)
        self.assertFalse(hasattr(one.resolution,'hp_before'));self.assertEqual(len(target_interval_history(self.a)),6)

    def test_combined_practice_validates_history_against_full_same_boundary_transition(self):
        skills=self.world.get_skill_dictionary();self.a.set_skill_level(skills,'run',1)
        self.a.record_skill_use(skills,'run',1230,action_id='prior',time=-2)
        history=self.a.begin_personal_history(earliest=-10,known_through=10,nondeclining_skills=('run',));self.enable()
        one=RunAction(self.world,self.a.id,0,6,.5,experience=10)
        two=RunAction(self.world,self.a.id,0,6,.5,experience=12);spot=self.f.spot()
        ask=self.f.f.f.ask(self.c,history,self.f.f.f.recipe(history,rank=2,extra=(Fact(history.skill_key(6,'run'),3),)))
        ask.end_time=6
        self.enc.schedule_choice((one,two,spot,ask));self.enc.step(6,velocities={self.a.id:(1,0,0)})
        self.assertEqual(self.a.get_skill_level('run'),3);self.assertEqual(self.a.skill_experience['run'],1252)
        self.assertEqual(history.reality.inspect(history.skill_key(6,'run')).value,3)
        self.assertEqual(self.a.skill_use_history[-1].level_before,2)

    def test_unfavorable_and_cancelled_outcomes_commit_without_fault(self):
        self.enable();action=self.f.spot(roll=1);run=RunAction(self.world,self.c.id,0,2,1)
        self.enc.schedule_choice((action,run));self.enc.step(1);self.enc.cancel_action(run.id,reason='stop')
        self.enc.step(5)
        self.assertEqual(action.resolution.outcome,'failure');self.assertEqual(run.resolution.outcome,'interrupted')
        self.assertIsNone(self.enc.boundary_fault);self.assertIn(run.id,self.enc.cancelled_action_list)

    def test_unsupported_new_actions_and_callbacks_reject_without_registration(self):
        self.enable()
        class Unsafe(SpotAction):
            def resolve(self,dc):raise AssertionError('legacy extension')
        action=Unsafe(self.world,self.a.id,self.b.id,0)
        before=self.raw()
        with self.assertRaises(UnsupportedEvaluation):self.enc.schedule_action(action)
        self.assertEqual(self.raw(),before)
        action=self.f.spot();callback=Mock(side_effect=AssertionError('completion'));action.on_completed=callback
        with self.assertRaises(UnsupportedEvaluation):self.enc.schedule_choice((action,))
        callback.assert_not_called();self.assertEqual(self.raw(),before)

    def test_unknown_future_family_prevents_any_prefix_commit(self):
        delay=Action(self.world,3,None,'delay',self.a.id,self.b.id,None);self.enc.schedule_action(delay);before=self.raw()
        with self.assertRaises(UnsupportedEvaluation):self.enable()
        self.assertEqual(self.raw(),before)

    def test_injected_unsafe_callback_after_acceptance_blocks_step_prewrite(self):
        self.enable();action=self.f.spot();self.enc.schedule_action(action);callback=Mock(side_effect=AssertionError('unsafe'))
        action.on_completed=callback;before=self.raw()
        with self.assertRaises(UnsupportedEvaluation):self.enc.step(2,velocities={self.a.id:(1,0,0)})
        self.assertEqual(self.raw(),before);self.assertIsNone(self.enc.boundary_fault);callback.assert_not_called()

    def test_shared_cross_encounter_participants_and_custom_environment_refuse(self):
        other=Encounter(self.world,10,0,initiated=True);other.add_being(self.a.id);self.world.add_event(other)
        before=self.raw()
        with self.assertRaises(UnsupportedEvaluation):self.enable()
        self.assertEqual(self.raw(),before)

    def test_unsafe_narrative_and_interpreter_never_execute(self):
        history=self.f.f.f.history();self.enable();unsafe=Mock(side_effect=AssertionError('generator'))
        ask=AskAboutPastAction(self.world,self.c.id,self.a.id,0,episode_time=0,topic='lessons',generate=unsafe)
        before=self.raw()
        with self.assertRaises(UnsupportedEvaluation):self.enc.schedule_action(ask)
        self.assertEqual(self.raw(),before);unsafe.assert_not_called()

    def test_direct_legacy_resolve_damage_and_completion_cannot_bypass(self):
        self.enable();action=self.f.spot();self.enc.schedule_action(action);before=self.raw();rng=random.getstate()
        for operation in (lambda:action.resolve(10),lambda:self.enc.resolve_actions(1),lambda:self.enc.publish_choice(self.enc.choice_for_action(action.id)),
                          lambda:self.enc._choice_book.publish_due(0)):
            with self.subTest(operation=operation),self.assertRaises(ValueError):operation()
            self.assertEqual(self.raw(),before);self.assertEqual(random.getstate(),rng)
        unscheduled=Action(self.world,0,None,'thrust',self.a.id,self.b.id,None)
        with self.assertRaises(ValueError):unscheduled.do_fatal_hit()
        self.assertEqual(self.raw(),before)

    def test_group_and_testimony_completion_hooks_are_explicitly_refused(self):
        group=self.f.f.f.group();history=self.f.f.f.history();self.enable()
        observe=self.f.f.observe(self.a,group,ledger=BeliefLedger(self.a.id));ask=self.f.f.f.ask(self.c,history)
        self.enc.schedule_choice((observe,ask));before=self.raw()
        for action in (observe,ask):
            with self.assertRaises(ValueError):action.on_completed(self.enc)
        self.assertEqual(self.raw(),before)

    def test_run_and_native_ai_planning_refuse_before_callbacks_or_rng(self):
        self.enable();before=self.raw();rng=random.getstate()
        callback=Mock(side_effect=AssertionError('policy'))
        # Instance override is unsupported, but run must refuse even before it.
        self.enc.choose_movement=callback
        with self.assertRaisesRegex(ValueError,'run'):self.enc.run()
        del self.enc.choose_movement
        for operation in (self.enc.choose_fight_actions,self.enc.choose_actions,self.enc.generate,self.enc.move):
            with self.assertRaises(ValueError):operation()
        callback.assert_not_called();self.assertEqual(self.raw(),before);self.assertEqual(random.getstate(),rng)
        self.assertIsNone(self.enc.boundary_fault)

    def test_facade_ui_and_replay_consumers_fail_before_policy_or_rng(self):
        from tactical_duel import TacticalDuel
        from ai_duel import AgentDuel
        self.enable();before=self.raw()
        for kind in (TacticalDuel,AgentDuel):
            game=kind(seed=14);game.encounter=self.enc
            if kind is AgentDuel:game.policy=Mock(side_effect=AssertionError('policy'))
            for operation in (lambda:game.choose('wait'),game.state,game.to_session,game.timeline,game._observe,game._foe_choice):
                state=random.getstate()
                with self.assertRaises(ValueError):operation()
                self.assertEqual(random.getstate(),state);self.assertEqual(self.raw(),before)
            if kind is AgentDuel:game.policy.decide.assert_not_called()

    def test_serialization_and_restore_refuse_even_before_first_commit(self):
        self.enable()
        with tempfile.TemporaryDirectory() as directory:
            dest=Path(directory)/'existing.json';dest.write_text('preserve')
            for _ in range(2):
                with self.assertRaises(ValueError):self.world.save_to_file(str(dest))
                with self.assertRaises(ValueError):self.world.load_from_file(str(dest))
                self.assertEqual(dest.read_text(),'preserve')
                for operation in (self.world.to_json,self.enc.to_json,lambda:self.enc.assert_checkpoint_exportable(replay=True)):
                    with self.assertRaises(ValueError):operation()
                self.enc.step(1)

    def test_inactive_preview_never_creates_an_alternate_authoritative_tail(self):
        self.enable();before=self.raw();candidate=self.enc.prepare_interval_candidate(1,rng_owner=self.rng)
        self.assertFalse(candidate.ready_for_publication);self.assertEqual(self.raw(),before)
        with self.assertRaises(ValueError):self.enc.step(.5)
        self.assertEqual(self.raw(),before)

    def test_module_and_native_random_rng_are_owned_and_adopted_in_step(self):
        outside=random.getstate()
        try:
            self.enable(rng_owner=None);action=self.f.spot(roll=None);self.enc.schedule_action(action)
            candidate=self.enc.prepare_interval_candidate(1);self.enc.step(1)
            self.assertEqual(random.getstate(),candidate.provisional_rng.after)
        finally:random.setstate(outside)
        f=fixtures.TestIntervalStaging();f.setUp();rng=random.Random(28);f.enc.enable_transactional_progression(quiescent=True,rng_owner=rng)
        action=f.spot(roll=None);f.enc.schedule_action(action);candidate=f.enc.prepare_interval_candidate(1,rng_owner=rng)
        outside=random.getstate();f.enc.step(1)
        self.assertEqual(rng.getstate(),candidate.provisional_rng.after);self.assertEqual(random.getstate(),outside)

    def test_facade_and_opaque_rng_owner_are_not_implicitly_supported(self):
        from tactical_duel import TacticalDuel
        owner=TacticalDuel(seed=3);before=self.raw()
        with self.assertRaises(ValueError):self.enable(rng_owner=owner)
        class Unsafe:
            def getstate(self):raise AssertionError('opaque RNG')
        with self.assertRaises(TypeError):self.enable(rng_owner=Unsafe())
        self.assertEqual(self.raw(),before)

    def test_physio_frame_cadence_is_read_only_across_long_step(self):
        registry=PhysiologyRegistry((PhysiologyDefinition('human@1',model='human-r4'),))
        for being in (self.a,self.b,self.c):being.physiology_id='human@1'
        self.enc.set_physiology_registry(registry);self.a.set_physical_fatigue(.7,.8);qb=self.a.physical_fatigue
        self.enable();self.enc.step(3,velocities={self.a.id:(1,0,0)})
        self.assertIs(self.a.physical_fatigue,qb);self.assertEqual(len(self.enc.fatigue_frame_history),3)
        self.assertEqual([frame['time'] for frame in self.enc.fatigue_frame_history],[1,2,3])
        self.assertEqual(self.enc.last_fatigue_frame.view(self.a.id).q,.7)

    def test_later_publication_failure_keeps_prior_second_and_explicit_step_retry(self):
        self.enable();action=RunAction(self.world,self.a.id,0,3,1,experience=7);self.enc.schedule_action(action)
        import atomic_publication
        original=atomic_publication.publish_interval_candidate;checkpoint=[]
        def publish(enc,candidate,**kwargs):
            if candidate.boundary==2:
                checkpoint.append(self.raw());kwargs['_fail_after']='rng'
            return original(enc,candidate,**kwargs)
        with patch('atomic_publication.publish_interval_candidate',publish):
            with self.assertRaises(PublicationFailure) as caught:self.enc.step(3,velocities={self.a.id:(1,0,0)})
        self.assertFalse(caught.exception.rollback_errors);self.assertEqual(self.enc.time,1);self.assertEqual(self.raw(),checkpoint[0])
        self.assertEqual(self.a.get_position(),CartesianPosition(1,0,0));self.assertIsNone(action.resolution)
        for operation in (lambda:self.enc.step(1),self.enc.run,self.enc.assert_checkpoint_exportable):
            with self.assertRaises(ValueError):operation()
        self.enc.recover_transactional_progression(caught.exception.recovery_token)
        self.enc.step(2,velocities={self.a.id:(1,0,0)})
        self.assertEqual(self.enc.time,3);self.assertEqual(action.resolution.outcome,'success')
        self.assertEqual(len(self.enc._atomic_interval_history),3)

    def test_stale_injected_candidate_refuses_before_publisher_writes(self):
        self.enable();import atomic_publication
        original=atomic_publication.publish_interval_candidate
        def stale(enc,candidate,**kwargs):
            enc.universe._schedule_revision+=1  # Models an unsupported external writer.
            return original(enc,candidate,**kwargs)
        before=self.a.get_position()
        with patch('atomic_publication.publish_interval_candidate',stale):
            with self.assertRaises(StaleInterval):self.enc.step(1,velocities={self.a.id:(1,0,0)})
        self.assertEqual(self.enc.time,0);self.assertIs(self.a.get_position(),before);self.assertIsNone(self.enc.boundary_fault)

    def test_reentrant_step_and_planning_are_rejected_under_routed_ownership(self):
        self.enable();import atomic_publication
        original=atomic_publication.publish_interval_candidate;seen=[]
        def publish(enc,candidate,**kwargs):
            with self.assertRaises(ValueError):enc.step(1)
            before=self.raw()
            with self.assertRaises(ValueError):enc.schedule_action(self.f.spot())
            self.assertEqual(self.raw(),before);seen.append(True)
            return original(enc,candidate,**kwargs)
        with patch('atomic_publication.publish_interval_candidate',publish):self.enc.step(1)
        self.assertEqual(seen,[True])

    @patch('atomic_publication._EMERGENCIES',{})
    def test_rollback_integrity_emergency_propagates_through_step_without_reset(self):
        self.enable();import atomic_publication
        original=atomic_publication.publish_interval_candidate
        def broken(enc,candidate,**kwargs):return original(enc,candidate,_fail_after='movement',_rollback_fail_at=0,**kwargs)
        with patch('atomic_publication.publish_interval_candidate',broken):
            with self.assertRaises(RollbackIntegrityFailure) as caught:self.enc.step(1,velocities={self.a.id:(1,0,0)})
        self.assertTrue(caught.exception.rollback_errors)
        with self.assertRaises(PublicationOwnershipError):self.enc.step(1)
        with self.assertRaises(PublicationOwnershipError):self.enc.recover_transactional_progression(caught.exception.recovery_token)

    def test_coordinated_writer_cannot_enter_between_stage_and_publish(self):
        from atomic_publication import coordinated_access
        self.enable();import atomic_publication
        original=atomic_publication.publish_interval_candidate;attempt=threading.Event();done=threading.Event();threads=[]
        def publish(enc,candidate,**kwargs):
            def writer():
                attempt.set()
                with coordinated_access(self.world):self.a.current.hit_points-=1
                done.set()
            t=threading.Thread(target=writer);threads.append(t);t.start();self.assertTrue(attempt.wait(1));self.assertFalse(done.wait(.05))
            return original(enc,candidate,**kwargs)
        with patch('atomic_publication.publish_interval_candidate',publish):self.enc.step(1)
        for thread in threads:thread.join(2);self.assertFalse(thread.is_alive())
        self.assertTrue(done.is_set());self.assertEqual(self.enc.time,1)

    def test_inverted_lock_order_is_refused_by_step(self):
        self.enable();before=self.raw()
        with self.world._schedule_lock:
            with self.assertRaises(PublicationOwnershipError):self.enc.step(1)
        self.assertEqual(self.raw(),before)

    def test_native_preparation_override_is_rejected_before_callback(self):
        self.enable();action=self.f.spot();before=self.raw();unsafe=Mock(side_effect=AssertionError('unsafe native preparer'))
        with patch.object(SpotAction,'prepare_schedule',unsafe):
            with self.assertRaises(UnsupportedEvaluation):self.enc.schedule_action(action)
        unsafe.assert_not_called();self.assertEqual(self.raw(),before)

    def test_existing_start_metadata_can_be_selected_without_legacy_effects(self):
        action=self.f.spot();self.enc.schedule_action(action)
        self.assertTrue(action._activity_started);self.assertIsNone(action.resolution)
        self.enable();self.enc.step(6)
        self.assertEqual(action.resolution.outcome,'success');self.assertNotIn('spot',self.a.skill_experience)

    def test_prepared_native_choices_remain_undoable_before_first_owned_start(self):
        self.enable();action=RunAction(self.world,self.a.id,0,1,1)
        view=self.enc.schedule_choice((action,));self.assertEqual(view.state,'accepted')
        self.assertIsNone(self.world.get_event_by_id(action.id));self.enc.undo_choice(view)
        self.enc.step(1);self.assertEqual(self.enc.finished_action_list,[]);self.assertIsNone(action.resolution)

    def test_custom_environment_after_selection_is_not_invoked(self):
        self.enable();unsafe=Mock(side_effect=AssertionError('environment'));self.enc.update_environment=unsafe
        before=self.raw()
        with self.assertRaises(UnsupportedEvaluation):self.enc.step(1,velocities={self.a.id:(1,0,0)})
        self.assertEqual(self.raw(),before);unsafe.assert_not_called()

    def test_invalid_native_interpretation_refuses_without_prefix_effects(self):
        group=self.f.f.f.group();self.enable();action=self.f.f.observe(self.a,group)
        self.enc.schedule_action(action)
        self.a.current.skills.skills.pop('spot')
        before=self.raw()
        with self.assertRaisesRegex(UnsupportedEvaluation,'interpreter'):self.enc.step(1)
        self.assertEqual(self.raw(),before);self.assertIsNone(group._counts);self.assertIsNone(self.enc.boundary_fault)


    def test_mode_selection_validates_contracts_without_sampling_or_action_evaluation(self):
        group=self.f.f.f.group();action=self.f.f.observe(self.a,group);self.enc.schedule_action(action)
        with patch('observer_proposals.build_supported_candidate',side_effect=AssertionError('early evaluation')):
            with patch('statistical_group.composition_rng',side_effect=AssertionError('early reality')):
                self.enable()
        self.assertIsNone(group._counts);self.assertIsNone(action.resolution)
        self.enc.step(1);self.assertEqual(action.resolution.outcome,'success')


    def test_selected_mode_cannot_bypass_step_with_direct_c2_publication(self):
        self.enable();candidate=self.enc.prepare_interval_candidate(1,rng_owner=self.rng);before=self.raw()
        with publication_boundary(self.enc,quiescent=True) as ownership:
            with self.assertRaisesRegex(ValueError,'step route'):
                publish_interval_candidate(self.enc,candidate,ownership=ownership,rng_owner=self.rng)
        self.assertEqual(self.raw(),before);self.assertIsNone(self.enc.boundary_fault)
        self.enc.step(1);self.assertEqual(self.enc.time,1)

    def test_competing_manual_publisher_cannot_advance_between_routed_seconds(self):
        from contextlib import contextmanager
        import atomic_publication
        self.enable();original=atomic_publication.publication_boundary
        ready=threading.Event();done=threading.Event();errors=[]
        def writer():
            ready.wait(2)
            try:
                with original(self.enc,quiescent=True) as ownership:
                    candidate=self.enc.prepare_interval_candidate(2,rng_owner=self.rng)
                    publish_interval_candidate(self.enc,candidate,ownership=ownership,rng_owner=self.rng)
            except Exception as exc:errors.append(exc)
            finally:done.set()
        thread=threading.Thread(target=writer);thread.start()
        @contextmanager
        def boundary(enc,**kwargs):
            with original(enc,**kwargs) as ownership:yield ownership
            if enc is self.enc and enc.time==1:
                ready.set();self.assertTrue(done.wait(2));self.assertEqual(enc.time,1)
        with patch('atomic_publication.publication_boundary',boundary):self.enc.step(2)
        thread.join(2);self.assertFalse(thread.is_alive());self.assertEqual(len(errors),1)
        self.assertIsInstance(errors[0],TransactionalProgressionError)
        self.assertEqual([r.boundary for r in self.enc._atomic_interval_history],[1,2])


    def test_unsafe_external_recipients_refuse_before_acceptance_or_callbacks(self):
        history=self.f.f.f.history();group=self.f.f.f.group();self.enable()
        class UnsafeAccounts(list):
            def __iter__(self):raise AssertionError('unsafe recipient iterator')
        ask=AskAboutPastAction(self.world,self.c.id,self.a.id,0,episode_time=0,topic='lessons',
            generate=self.f.f.f.recipe(history),received_accounts=UnsafeAccounts())
        before=self.raw()
        with self.assertRaises(UnsupportedEvaluation):self.enc.schedule_action(ask)
        self.assertEqual(self.raw(),before)
        class UnsafeBelief(BeliefLedger):
            def learn(self,*args,**kwargs):raise AssertionError('unsafe belief')
        observe=self.f.f.observe(self.a,group,ledger=UnsafeBelief(self.a.id))
        with self.assertRaises(UnsupportedEvaluation):self.enc.schedule_action(observe)
        self.assertEqual(self.raw(),before)


    def test_concurrent_selectors_revalidate_irreversibility_under_ownership(self):
        from contextlib import contextmanager
        import atomic_publication
        original=atomic_publication.publication_boundary;barrier=threading.Barrier(2);results=[]
        @contextmanager
        def synchronized(enc,**kwargs):
            barrier.wait(timeout=2)
            with original(enc,**kwargs) as ownership:yield ownership
        def select():
            try:results.append(self.enc.enable_transactional_progression(quiescent=True,rng_owner=self.rng))
            except Exception as exc:results.append(exc)
        with patch('atomic_publication.publication_boundary',synchronized):
            threads=[threading.Thread(target=select) for _ in range(2)]
            for thread in threads:thread.start()
            for thread in threads:thread.join(3);self.assertFalse(thread.is_alive())
        self.assertEqual(sum(isinstance(x,TransactionalProgressionError) for x in results),1)
        self.assertEqual(self.enc.progression_mode,'transactional');self.enc.step(1)



class TestTransactionalLongStep(unittest.TestCase):
    def fixture(self):
        counter=itertools.count(1)
        with patch('identifiable.uuid.uuid4',side_effect=lambda:uuid.UUID(int=next(counter))):
            f=fixtures.TestIntervalStaging();f.setUp();rng=RNGCursor(random.Random(18).getstate())
            f.enc.enable_transactional_progression(quiescent=True,rng_owner=rng)
            one=RunAction(f.world,f.a.id,.2,1,1,experience=7)
            spot=SpotAction(f.world,f.a.id,f.b.id,0,die_roll=None)
            later=SpotAction(f.world,f.c.id,f.b.id,1,die_roll=None)
            run=RunAction(f.world,f.c.id,2,1,1,experience=5)
            f.enc.schedule_choice((one,spot,later,run))
        return f,rng

    def state(self,f,rng):
        return (f.enc.time,f.enc.choice_state,tuple(f.enc.finished_action_list),f.enc.fatigue_frame_history,
            [(being.get_position(),being.get_hit_points(),being.skill_experience,being.skill_use_history,target_interval_history(being)) for being in (f.a,f.b,f.c)],
            [(aid,a.resolution,getattr(a,'start_position',None)) for aid,a in f.world.event_history.items() if isinstance(a,Action)],rng.state)

    def test_long_step_equals_individual_chronological_seconds(self):
        one,rng1=self.fixture();two,rng2=self.fixture();motion={one.a.id:(1,0,0),one.c.id:(.5,0,0)}
        one.enc.step(3,velocities=motion)
        for _ in range(3):two.enc.step(1,velocities=motion)
        self.assertEqual(self.state(one,rng1),self.state(two,rng2))
        self.assertEqual([r.boundary for r in one.enc._atomic_interval_history],[1,2,3])

    def test_second_boundary_reads_previously_committed_movement_not_final_long_endpoint(self):
        f,rng=self.fixture();f.enc.step(3,velocities={f.a.id:(1,0,0)})
        positions=[record.state for record in target_interval_history(f.a)]
        self.assertEqual([entry.boundary for entry in f.enc._atomic_interval_history],[1,2,3])
        run=next(action for action in f.world.event_history.values() if type(action) is RunAction and action.actor_id==f.a.id)
        self.assertAlmostEqual(dict(run.resolution.metadata)['displacement'],1.8)
        self.assertEqual(run.start_position,CartesianPosition(.2,0,0));self.assertEqual(f.a.get_position(),CartesianPosition(3,0,0))


class TestTransactionalCombat(unittest.TestCase):
    def setUp(self):
        self.f=combat_fixtures.TestActionSettlement();self.f.setUp()
        self.enc,self.world,self.a,self.b=self.f.enc,self.f.world,self.f.a,self.f.b
        self.enc.enable_transactional_progression(quiescent=True,rng_owner=RNGCursor(random.Random(4).getstate()))

    def step_rolls(self,duration,rolls):
        values=iter(rolls)
        def roll(rng,dice):
            value=next(values);rng.trace.append(RandomDraw(rng.action_id,dice,int(dice[2:].split('+')[0]),value));return value
        with patch.object(_ProvisionalRandom,'roll',roll):return self.enc.step(duration)

    def test_simultaneous_negative_hp_and_target_owned_provenance(self):
        self.b.set_hit_points(3);one,two=self.f.attack(self.f.w1),self.f.attack(self.f.w2)
        self.enc.schedule_choice((one,two));self.step_rolls(math.ceil(one.end_time),(15,4,15,4))
        self.assertEqual(self.b.get_hit_points(),-5);self.assertEqual(one.resolution.outcome,'normal')
        self.assertFalse(any('hp_before' in key or 'hp_after' in key for key in vars(one.resolution)))
        self.assertEqual(target_interval_history(self.b)[-1].state.actual_damage,8)

    def test_fatal_effects_do_not_stack(self):
        one,two=self.f.attack(self.f.w1),self.f.attack(self.f.w2);self.enc.schedule_choice((one,two))
        self.step_rolls(math.ceil(one.end_time),(20,20,1,20,20,1));self.assertEqual(self.b.get_hit_points(),-10)
        self.assertEqual(len(target_interval_history(self.b)[-1].state.fatal_effect_ids),2)

    def test_multiple_defenses_and_practice_use_same_route(self):
        strike=self.f.attack(melee=True);one=MeleeDefense(self.enc,self.b.id,self.a.id,kind='dodge',target_action_id=strike.id)
        two=MeleeDefense(self.enc,self.b.id,self.a.id,kind='dodge',target_action_id=strike.id)
        self.enc.schedule_choice((strike,one,two));self.step_rolls(math.ceil(strike.end_time),(20,1,1,20))
        self.assertEqual(strike.resolution.outcome,'dodged');self.assertEqual(len(strike.resolution.defenses),2)
        self.assertEqual(self.b.skill_experience['tumble'],20)

    def test_endpoint_object_handoff_starts_after_previous_settlement(self):
        old=self.f.attack(melee=True);boundary=math.ceil(old.end_time);new=self.f.attack(melee=True)
        new.start_time=boundary;new.end_time+=boundary
        self.enc.schedule_choice((old,new));self.step_rolls(boundary,(15,4))
        self.assertIsNotNone(old.resolution);self.assertTrue(new._activity_started)
        self.assertEqual(tuple(r.action_id for r in self.enc.active_reservations),(new.id,))
        self.assertIsNone(new.resolution);self.step_rolls(math.ceil(new.end_time)-boundary,(15,4))
        self.assertEqual(self.enc.active_reservations,());self.assertIsNotNone(new.resolution)

    def test_defense_fractional_start_uses_actual_geometry(self):
        strike=self.f.attack(melee=True);strike.end_time=3
        defense=MeleeDefense(self.enc,self.b.id,self.a.id,kind='dodge',target_action_id=strike.id);defense.start_time=.5
        self.enc.schedule_choice((strike,defense));self.enc.step(1,velocities={self.b.id:(10,0,0)})
        self.assertEqual(defense.threat_at_schedule,((strike.id,False),));self.assertTrue(defense._activity_started)

    def test_equipment_unavailability_is_normal_committed_outcome(self):
        strike=self.f.attack(melee=True);self.enc.schedule_action(strike)
        self.a.current.body_parts['right hand']=None
        self.enc.step(math.ceil(strike.end_time))
        self.assertEqual(strike.resolution.outcome,'weapon_unavailable');self.assertIsNone(self.enc.boundary_fault)


if __name__=='__main__':unittest.main()
