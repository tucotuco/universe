"""5C1 inactive full-interval closure, native fences and no-live-write safety."""
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
import math
import random
import sys
from types import MappingProxyType
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import test_observer_lifecycle_proposals as observers
from interval_staging import (validate_interval_candidate, IntervalIntegrityError,
    StaleInterval, UnsupportedEvaluation)
from observer_proposals import capture_observer_context, build_supported_candidate
from action_evaluation import EvaluationIntegrityError
from action_choice import Reservation
from activities import RunAction, SpotAction
from action import Action
from encounter import Encounter
from field_observation import BeliefLedger
from history_conversation import AskAboutPastAction
from melee_combat import MeleeStrike
from melee_defense import MeleeDefense
from spatial.state import CartesianPosition
from spatial.frame import LocalFrame
from physiology_registry import PhysiologyRegistry, PhysiologyDefinition
from realization import ImpossibleRealization, Fact


class TestIntervalStaging(unittest.TestCase):
    def setUp(self):
        self.f=observers.TestObserverLifecycleProposals();self.f.setUp()
        self.world,self.enc=self.f.world,self.f.enc
        self.a,self.b,self.c=self.f.a,self.f.b,self.f.c

    def spot(self,actor=None,start=0,duration=1,roll=20,maximum=20):
        return SpotAction(self.world,(actor or self.a).id,self.b.id,start,
            duration=duration,max_distance=maximum,experience=10,die_roll=roll)

    def build(self,boundary=1,**kwargs):
        return self.f.f.unchanged(lambda:self.enc.prepare_interval_candidate(boundary,**kwargs))

    def accept(self,actions):
        return self.enc.accept_valid_choice(self.enc.validate_choice(self.enc.propose_choice(actions)))

    def test_no_movement_matches_direct_5b3_and_does_not_mutate(self):
        action=self.spot();self.enc.schedule_action(action)
        candidate=self.build()
        self.assertEqual(candidate.coverage,'complete_supported_interval');self.assertFalse(candidate.ready_for_publication)
        self.assertTrue(validate_interval_candidate(self.enc,candidate))
        # Native direct 5B3 capture uses the same supplied endpoint, independently.
        self.enc.time=1
        direct=build_supported_candidate(capture_observer_context(self.enc,1,rng_state=candidate.provisional_rng.before))
        self.assertEqual(candidate.supported_candidate.boundary.actions,direct.boundary.actions)
        self.assertEqual(candidate.supported_candidate.boundary.effects,direct.boundary.effects)
        self.assertEqual(candidate.supported_candidate.boundary.targets,direct.boundary.targets)
        self.assertEqual(candidate.provisional_rng.after,direct.boundary.provisional_rng_state)

    def test_empty_interval_has_complete_clock_and_unchanged_physical_frames(self):
        candidate=self.build();changes=candidate.proposed_authoritative_changes
        self.assertEqual(changes['clock']['time'],1);self.assertEqual(candidate.start_checkpoint.start,0)
        self.assertEqual(changes['fatigue_history'][-1]['start'],0)
        self.assertEqual(changes['environment']['fatigue'][self.a.id]['q'],self.a.physical_fatigue.q)
        self.assertEqual(changes['targets'][self.a.id].projected_hp,self.a.get_hit_points())
        self.assertEqual(dict(changes['queues'].action_states),{})
        self.assertEqual(self.enc.fatigue_frame_history,[])

    def test_fractional_first_checkpoint_never_resolves_zero_or_invents_history(self):
        enc=Encounter(self.world,10,.25,initiated=True);self.world.add_event(enc)
        # Separate ownership, no entities shared with the first Encounter.
        candidate=self.f.f.unchanged(lambda:enc.prepare_interval_candidate(1))
        self.assertEqual(candidate.start_checkpoint.start,.25)
        self.assertEqual((candidate.movement[0].start,candidate.movement[0].end),(.25,1))
        with self.assertRaises(IntervalIntegrityError):enc.prepare_interval_candidate(0)

    def test_acceptance_at_zero_is_staged_without_registering_live(self):
        action=RunAction(self.world,self.a.id,0,1,2,experience=5)
        view=self.accept((action,));candidate=self.build(velocities={self.a.id:(3,0,0)})
        fence=candidate.start_fences[0]
        self.assertEqual(fence.published_choices,(view.id,));self.assertEqual(fence.started_action_ids,(action.id,))
        self.assertEqual(candidate.supported_candidate.boundary.actions[action.id].outcome,'success')
        self.assertEqual(self.enc.pending_action_list,[]);self.assertIsNone(action.start_position)
        self.assertIsNone(self.world.get_event_by_id(action.id));self.assertEqual(self.enc.get_choice(view.id).state,'accepted')

    def test_fractional_run_start_samples_true_position_not_construction(self):
        action=RunAction(self.world,self.a.id,.25,1,2)
        self.enc.schedule_action(action)
        candidate=self.build(velocities={self.a.id:(4,0,0)})
        self.assertEqual(candidate.start_fences[0].time,.25)
        view=candidate.pre_action_snapshot.actions[action.id]
        self.assertEqual(view.data['start_position'],CartesianPosition(1,0,0))
        self.assertEqual(candidate.pre_action_snapshot.entity(self.a.id).position,CartesianPosition(4,0,0))
        self.assertNotIn(action.id,candidate.supported_candidate.boundary.actions)
        self.assertIsNone(action.start_position)
        self.assertEqual([(s.start,s.end) for s in candidate.movement],[(0,.25),(.25,1)])

    def test_later_member_registered_whole_choice_then_started_at_fraction(self):
        one=self.spot(start=.2,duration=2);two=RunAction(self.world,self.c.id,.7,1,1)
        view=self.enc.schedule_choice((one,two));candidate=self.build(velocities={self.c.id:(10,0,0)})
        first,last=candidate.start_fences
        self.assertEqual(first.registered_action_ids,(one.id,two.id));self.assertEqual(first.started_action_ids,(one.id,))
        self.assertEqual(last.started_action_ids,(two.id,));self.assertEqual(last.time,.7)
        self.assertEqual(last.metadata[two.id]['start_position'],CartesianPosition(11,0,0))
        self.assertEqual(candidate.proposed_authoritative_changes['queues'].choice_states[view.id],'executing')
        self.assertEqual(self.enc.pending_action_list,[])

    def test_member_beyond_interval_is_registered_but_not_started(self):
        one=self.spot(start=.2,duration=2);two=RunAction(self.world,self.c.id,1.5,1,1)
        self.enc.schedule_choice((one,two));candidate=self.build()
        self.assertEqual(candidate.proposed_authoritative_changes['queues'].action_states[two.id],'registered')
        self.assertFalse(candidate.pre_action_snapshot.actions[two.id].data['started'])
        self.assertIsNone(candidate.pre_action_snapshot.actions[two.id].data['start_position'])

    def test_endpoint_starter_published_only_after_preceding_batch(self):
        old=self.spot();new=RunAction(self.world,self.a.id,1,1,1)
        self.enc.schedule_action(old);view=self.enc.schedule_action(new)
        candidate=self.build(velocities={self.a.id:(2,0,0)})
        self.assertEqual(candidate.start_fences[-1].phase,'after_settlement')
        self.assertEqual(candidate.start_fences[-1].time,1)
        self.assertNotIn(new.id,candidate.pre_action_snapshot.actions)
        self.assertEqual(set(candidate.supported_candidate.boundary.actions),{old.id})
        queues=candidate.proposed_authoritative_changes['queues']
        self.assertIn(new.id,queues.pending);self.assertIn(old.id,queues.finished)
        self.assertEqual(candidate.start_fences[-1].metadata[new.id]['start_position'],CartesianPosition(2,0,0))

    def test_exact_deadline_and_nextafter_belong_to_distinct_boundaries(self):
        one=self.spot();two=self.spot(self.c,duration=math.nextafter(1,math.inf))
        self.enc.schedule_choice((one,two));candidate=self.build()
        self.assertEqual(set(candidate.supported_candidate.boundary.actions),{one.id})
        self.assertIn(two.id,candidate.proposed_authoritative_changes['queues'].pending)
        self.assertEqual(candidate.pre_action_snapshot.actions[two.id].boundary,2)

    def test_all_checks_read_shared_endpoint_not_starting_geometry(self):
        first=self.spot(maximum=3);second=self.spot(self.c,maximum=3)
        self.enc.schedule_choice((first,second));candidate=self.build(velocities={self.b.id:(10,0,0)})
        self.assertEqual({p.outcome for p in candidate.supported_candidate.boundary.actions.values()},{'out_of_range'})
        self.assertEqual(candidate.pre_action_snapshot.entity(self.b.id).position,CartesianPosition(12,0,0))
        self.assertEqual(self.b.get_position(),CartesianPosition(2,0,0))

    def test_movement_into_range_uses_native_success_and_common_rank(self):
        self.b.set_position(CartesianPosition(12,0,0));action=self.spot(maximum=3)
        self.enc.schedule_action(action);candidate=self.build(velocities={self.b.id:(-10,0,0)})
        self.assertEqual(candidate.supported_candidate.boundary.actions[action.id].outcome,'success')
        self.assertEqual(candidate.supported_candidate.target(self.a.id).practice_state.skill_experience['spot'],10)

    def test_local_velocity_uses_native_rigid_frame(self):
        self.enc.set_local_frame(LocalFrame(CartesianPosition(0,0,0),(0,1,0),(-1,0,0),(0,0,1)))
        candidate=self.build(velocities={self.a.id:(3,0,0)},velocity_frame='local')
        self.assertEqual(candidate.pre_action_snapshot.entity(self.a.id).position,CartesianPosition(0,3,0))

    def test_supported_mixed_observers_history_spot_and_run_have_complete_recipients(self):
        group=self.f.f.group();h=self.f.f.history();accounts=[]
        one=self.f.observe(self.a,group,ledger=BeliefLedger(self.a.id));two=self.f.observe(self.b,group,ledger=BeliefLedger(self.b.id))
        ask=AskAboutPastAction(self.world,self.c.id,self.a.id,0,episode_time=0,topic='lessons',generate=self.f.f.recipe(h),received_accounts=accounts)
        spot=self.spot();run=RunAction(self.world,self.c.id,0,1,1,experience=7)
        self.enc.schedule_choice((one,two,ask,spot,run));candidate=self.build(velocities={self.c.id:(1,0,0)})
        supported=candidate.supported_candidate
        self.assertEqual(set(supported.boundary.actions),{a.id for a in (one,two,ask,spot,run)})
        self.assertEqual(len(supported.recipients),3);self.assertEqual(accounts,[])
        self.assertEqual(supported.target(self.c.id).practice_state.skill_experience['run'],7)
        self.assertEqual(supported.target(self.a.id).practice_state.skill_experience['spot'],22)
        self.assertIsNone(group._counts);self.assertTrue(supported.objective.draws)
        self.assertEqual(len(candidate.provisional_rng.observer_trace),4)

    def test_full_combat_defense_and_history_interval_preserves_dependencies(self):
        wid=self.world.make_weapon_for_being(self.a.id,'Dagger','Knife');self.world.arm_being(self.a.id,wid,'right hand')
        strike=MeleeStrike(self.enc,self.a.id,self.b.id,wid,motion='thrust',reach=3)
        defense=MeleeDefense(self.enc,self.b.id,self.a.id,kind='dodge',target_action_id=strike.id)
        h=self.f.f.history();ask=AskAboutPastAction(self.world,self.c.id,self.a.id,0,episode_time=0,topic='lessons',generate=self.f.f.recipe(h),duration=strike.end_time)
        self.enc.schedule_choice((strike,defense,ask))
        boundary=math.ceil(strike.end_time)
        if boundary>1:self.enc.step(boundary-1)
        candidate=self.build(boundary)
        self.assertEqual(set(candidate.supported_candidate.boundary.actions),{strike.id,defense.id,ask.id})
        self.assertFalse(candidate.proposed_authoritative_changes['queues'].reservations)
        self.assertTrue(self.enc.active_reservations)

    def test_run_completion_uses_native_displacement_and_practice(self):
        action=RunAction(self.world,self.a.id,0,1,2,experience=9);self.enc.schedule_action(action)
        candidate=self.build(velocities={self.a.id:(1,0,0)})
        self.assertEqual(candidate.supported_candidate.boundary.actions[action.id].outcome,'partial')
        self.assertEqual(candidate.supported_candidate.target(self.a.id).practice_state.skill_experience['run'],9)
        self.assertIsNone(action.displacement)

    def test_registered_defense_start_resamples_fractional_geometry(self):
        wid=self.world.make_weapon_for_being(self.a.id,'Dagger','Knife');self.world.arm_being(self.a.id,wid,'right hand')
        strike=MeleeStrike(self.enc,self.a.id,self.b.id,wid,motion='thrust',reach=3)
        strike.end_time=3
        defense=MeleeDefense(self.enc,self.b.id,self.a.id,kind='dodge',target_action_id=strike.id)
        defense.start_time=.5
        self.enc.schedule_choice((strike,defense))
        candidate=self.build(velocities={self.b.id:(10,0,0)})
        self.assertEqual(candidate.start_fences[0].time,.5)
        self.assertEqual(candidate.start_fences[0].metadata[defense.id]['threat_at_schedule'],((strike.id,False),))
        self.assertEqual(defense.threat_at_schedule,((strike.id,True),))

    def test_native_physiology_and_qb_are_frozen_without_cost(self):
        registry=PhysiologyRegistry((PhysiologyDefinition('human@1',model='human-r4'),))
        for being in (self.a,self.b,self.c):being.physiology_id='human@1'
        self.a.set_physical_fatigue(.7,.8);self.enc.set_physiology_registry(registry)
        candidate=self.build();frame=candidate.pre_action_snapshot
        self.assertEqual(frame.fatigue[self.a.id]['q'],.7)
        self.assertIn('running',frame.physiology[self.a.id])
        self.assertEqual(self.a.physical_fatigue.q,.7);self.assertIsNone(self.enc.last_fatigue_frame)

    def test_candidate_nested_data_are_detached_and_frozen(self):
        action=self.spot();self.enc.schedule_action(action);candidate=self.build()
        with self.assertRaises(FrozenInstanceError):candidate.boundary=2
        with self.assertRaises(TypeError):candidate.proposed_authoritative_changes['positions'][self.a.id]=None
        before=repr(candidate);self.a.set_position(CartesianPosition(99,0,0))
        self.assertEqual(repr(candidate),before)

    def test_module_rng_is_provisional_and_repeatable(self):
        action=self.spot(roll=None);self.enc.schedule_action(action);before=random.getstate()
        one=self.build();two=self.build()
        self.assertEqual(one,two);self.assertEqual(random.getstate(),before)
        self.assertNotEqual(one.provisional_rng.after,before)
        self.assertEqual(one.provisional_rng.role,'module')

    def test_caller_state_rng_requires_matching_dependency_at_validation(self):
        state=random.Random(51).getstate();self.enc.schedule_action(self.spot(roll=None))
        candidate=self.build(rng_state=state)
        self.assertTrue(validate_interval_candidate(self.enc,candidate,rng_state=state))
        with self.assertRaises(StaleInterval):validate_interval_candidate(self.enc,candidate)

    def test_native_random_owner_is_not_advanced(self):
        rng=random.Random(22);self.enc.schedule_action(self.spot(roll=None));before=rng.getstate()
        candidate=self.build(rng_owner=rng)
        self.assertEqual(rng.getstate(),before);self.assertTrue(validate_interval_candidate(self.enc,candidate,rng_owner=rng))
        rng.random()
        with self.assertRaises(StaleInterval):validate_interval_candidate(self.enc,candidate,rng_owner=rng)

    def test_native_facade_rng_is_not_advanced(self):
        from tactical_duel import TacticalDuel
        duel=TacticalDuel(seed=18);before=duel._rng_state;global_before=random.getstate()
        candidate=duel.encounter.prepare_interval_candidate(1,rng_owner=duel)
        self.assertEqual(duel._rng_state,before);self.assertEqual(random.getstate(),global_before)
        self.assertTrue(validate_interval_candidate(duel.encounter,candidate,rng_owner=duel))
        duel._rng_state=random.Random(19).getstate()
        with self.assertRaises(StaleInterval):validate_interval_candidate(duel.encounter,candidate,rng_owner=duel)

    def test_identity_and_value_mutations_invalidate_dependencies(self):
        self.enc.schedule_action(self.spot());candidate=self.build()
        original=self.a.current.hit_points;self.a.current.hit_points-=1
        with self.assertRaises(StaleInterval):validate_interval_candidate(self.enc,candidate)
        self.a.current.hit_points=original
        self.assertTrue(validate_interval_candidate(self.enc,candidate))
        self.world.object_registry.object_instances[self.a.id]=self.b
        with self.assertRaises(StaleInterval):validate_interval_candidate(self.enc,candidate)

    def test_skill_equipment_and_schedule_revision_changes_are_stale(self):
        candidate=self.build();self.a.set_skill_level(self.world.get_skill_dictionary(),'spot',1)
        with self.assertRaises(StaleInterval):validate_interval_candidate(self.enc,candidate)
        candidate=self.build();self.world._schedule_revision+=1
        with self.assertRaises(StaleInterval):validate_interval_candidate(self.enc,candidate)

    def test_recipient_and_ledger_mutation_are_stale(self):
        group=self.f.f.group();ledger=BeliefLedger(self.a.id);self.enc.schedule_action(self.f.observe(self.a,group,ledger=ledger))
        candidate=self.build();group.counts()
        with self.assertRaises(StaleInterval):validate_interval_candidate(self.enc,candidate)
        candidate=self.build();ledger._belief_history.append('changed')
        with self.assertRaises(StaleInterval):validate_interval_candidate(self.enc,candidate)

    def test_choice_replacement_and_reservation_mutation_are_stale(self):
        action=RunAction(self.world,self.a.id,.5,1,1);self.enc.schedule_action(action);view=self.enc.choice_for_action(action.id);candidate=self.build()
        self.enc.undo_choice(view)
        with self.assertRaises(StaleInterval):validate_interval_candidate(self.enc,candidate)
        candidate=self.build();self.enc._choice_book._reservations=(Reservation('bad','bad',self.a.id,0,1),)
        with self.assertRaises(StaleInterval):validate_interval_candidate(self.enc,candidate)

    def test_wrong_encounter_and_changed_candidate_are_rejected(self):
        candidate=self.build();other=Encounter(self.world,10,0,initiated=True);self.world.add_event(other)
        with self.assertRaises(StaleInterval):validate_interval_candidate(other,candidate)
        with self.assertRaises(IntervalIntegrityError):validate_interval_candidate(self.enc,replace(candidate,coverage='fragment'))
        changed=dict(candidate.proposed_authoritative_changes);changed['positions']=MappingProxyType({})
        with self.assertRaises(IntervalIntegrityError):validate_interval_candidate(self.enc,replace(candidate,proposed_authoritative_changes=MappingProxyType(changed)))

    def test_fractional_tail_and_faulted_or_active_checkpoint_refused(self):
        self.enc.step(.25)
        with self.assertRaises(IntervalIntegrityError):self.build()
        self.enc.step(.75);self.enc.boundary_fault={'error':'injected'}
        with self.assertRaises(IntervalIntegrityError):self.build(2)
        self.enc.boundary_fault=None;self.enc._advancing=True
        with self.assertRaises(IntervalIntegrityError):self.build(2)

    def test_skipped_duplicate_or_noninteger_boundary_refused(self):
        for boundary in (0,2,1.0,True):
            with self.subTest(boundary=boundary),self.assertRaises(IntervalIntegrityError):self.build(boundary)
        self.enc.step(1)
        with self.assertRaises(IntervalIntegrityError):self.build(1)
        self.assertEqual(self.build(2).start_checkpoint.start,1)

    def test_cross_encounter_participant_owner_is_explicit_refusal(self):
        other=Encounter(self.world,10,0,initiated=True);self.world.add_event(other);other.add_being(self.a.id)
        with self.assertRaisesRegex(UnsupportedEvaluation,'cross-Encounter'):self.build()

    def test_unsafe_movement_environment_and_completion_are_never_called(self):
        unsafe=Mock(side_effect=AssertionError('unsafe callback'))
        for target,name in ((self.a,'move'),(self.enc,'update_environment')):
            setattr(target,name,unsafe)
            with self.assertRaises(UnsupportedEvaluation):self.build()
            delattr(target,name)
        action=self.spot();self.enc.schedule_action(action);action.on_completed=unsafe
        with self.assertRaises(UnsupportedEvaluation):self.build()
        unsafe.assert_not_called()

    def test_class_environment_override_refused_before_invocation(self):
        unsafe=Mock(side_effect=AssertionError('environment'))
        with patch.object(Encounter,'update_environment',unsafe):
            with self.assertRaises(UnsupportedEvaluation):self.build()
        unsafe.assert_not_called()

    def test_unsupported_due_family_is_not_silently_skipped(self):
        delay=Action(self.world,0,None,'delay',self.a.id,self.b.id,None);self.enc.schedule_action(delay)
        with self.assertRaises(UnsupportedEvaluation):self.build()

    def test_opaque_narrative_and_recipient_are_refused_before_invocation(self):
        history=self.f.f.history();unsafe=Mock(side_effect=AssertionError('story'))
        action=AskAboutPastAction(self.world,self.b.id,self.a.id,0,episode_time=0,topic='lessons',generate=unsafe)
        self.enc.schedule_action(action)
        with self.assertRaises(UnsupportedEvaluation):self.build()
        unsafe.assert_not_called()

    def test_normal_failed_roll_and_cancelled_action_are_valid_proposals(self):
        action=self.spot(roll=1);other=RunAction(self.world,self.c.id,0,1,1)
        self.enc.schedule_choice((action,other));self.enc.cancel_action(other.id,reason='interrupted')
        candidate=self.build();outcomes=candidate.supported_candidate.boundary.actions
        self.assertEqual(outcomes[action.id].outcome,'failure');self.assertEqual(outcomes[other.id].outcome,'interrupted')
        self.assertEqual(candidate.proposed_authoritative_changes['queues'].cancelled,(other.id,))

    def test_each_late_fault_returns_no_candidate_and_keeps_committed_state(self):
        group=self.f.f.group();action=self.f.observe(self.a,group);self.enc.schedule_action(action)
        # Independent injections cover physical integration, actual start staging,
        # shared realization, complete practice validation, and late closure.
        fault_sites=['interval_staging.integrate_position','interval_staging._stage_start_fence',
            'objective_reality._group_candidate','frozen_practice.project_practice',
            'interval_staging._validate_closure']
        for site in fault_sites:
            with self.subTest(site=site),patch(site,side_effect=RuntimeError('injected')):
                with self.assertRaises(RuntimeError):self.build(velocities={self.a.id:(1,0,0)})
        one=self.build(velocities={self.a.id:(1,0,0)});two=self.build(velocities={self.a.id:(1,0,0)})
        self.assertEqual(one,two);self.assertIsNone(group._counts)

    def test_fault_after_prior_committed_second_preserves_that_checkpoint(self):
        action=self.spot(duration=2);self.enc.schedule_action(action);self.enc.step(1,velocities={self.a.id:(1,0,0)})
        before=self.f.f.raw_state()
        with patch('interval_staging._validate_closure',side_effect=RuntimeError('late')):
            with self.assertRaises(RuntimeError):self.build(2,velocities={self.a.id:(1,0,0)})
        self.assertEqual(self.f.f.raw_state(),before);self.assertEqual(self.enc.last_processed_boundary,1)
        self.assertEqual(self.a.get_position(),CartesianPosition(1,0,0))

    def test_contradictory_history_rejects_interval_without_reroll(self):
        h=self.f.f.history();one=self.f.f.ask(self.b,h,self.f.f.recipe(h,'One'));two=self.f.f.ask(self.c,h,self.f.f.recipe(h,'Two'))
        self.enc.schedule_choice((one,two))
        with self.assertRaises(ImpossibleRealization):self.build()

    def test_live_long_step_remains_legacy_and_does_not_call_interval_builder(self):
        action=self.spot(duration=2);self.enc.schedule_action(action)
        with patch('interval_staging.prepare_interval_candidate',side_effect=AssertionError('inactive')):
            self.enc.step(2.25,velocities={self.a.id:(1,0,0)})
        self.assertEqual(self.enc.last_processed_boundary,2);self.assertIsNotNone(action.resolution)
        with self.assertRaises(ValueError):self.enc.assert_checkpoint_exportable()

    def test_injected_drift_during_capture_is_detected_without_hiding_mutation(self):
        # This models an external writer, not a rollback promise: the adapter
        # detects drift and itself performs no restorative authoritative writes.
        import interval_staging
        original=interval_staging.build_supported_candidate
        def drift(context):
            result=original(context);self.world._schedule_revision+=1;return result
        with patch('interval_staging.build_supported_candidate',side_effect=drift):
            with self.assertRaisesRegex(IntervalIntegrityError,'changed during'):self.enc.prepare_interval_candidate(1)
        self.assertEqual(self.enc.time,0);self.assertEqual(self.enc.last_processed_boundary,0)

    def test_resource_handoff_at_endpoint_waits_until_settlement(self):
        wid=self.world.make_weapon_for_being(self.a.id,'Dagger','Knife');self.world.arm_being(self.a.id,wid,'right hand')
        old=MeleeStrike(self.enc,self.a.id,self.b.id,wid,motion='thrust',reach=3)
        boundary=math.ceil(old.end_time)
        new=MeleeStrike(self.enc,self.a.id,self.b.id,wid,motion='thrust',reach=3)
        new.start_time=boundary;new.end_time+=boundary
        self.enc.schedule_choice((old,new))
        if boundary>1:self.enc.step(boundary-1)
        candidate=self.build(boundary)
        self.assertEqual(candidate.start_fences[-1].phase,'after_settlement')
        self.assertEqual(candidate.start_fences[-1].started_action_ids,(new.id,))
        queues=candidate.proposed_authoritative_changes['queues']
        self.assertEqual(tuple(r.action_id for r in queues.reservations),(new.id,))
        self.assertEqual(len(self.enc.active_reservations),2)
        self.assertEqual(set(candidate.supported_candidate.lifecycle),{old.id})

    def test_tampered_or_competing_reservation_rejects_without_changes(self):
        wid=self.world.make_weapon_for_being(self.a.id,'Dagger','Knife');self.world.arm_being(self.a.id,wid,'right hand')
        action=MeleeStrike(self.enc,self.a.id,self.b.id,wid,motion='thrust',reach=3);self.enc.schedule_action(action)
        self.enc._choice_book._reservations += (Reservation('corrupt','other',wid,0,1),)
        with self.assertRaisesRegex(IntervalIntegrityError,'overlapping'):self.build()
        self.enc._choice_book._reservations=()
        with self.assertRaisesRegex(IntervalIntegrityError,'reservation'):self.build()

    def test_changed_accepted_choice_declaration_refused(self):
        action=RunAction(self.world,self.a.id,.25,1,1);self.enc.schedule_action(action)
        action.end_time+=1
        with self.assertRaises(ValueError):self.build()

    def test_accepted_replacement_stales_old_candidate_without_registering(self):
        action=RunAction(self.world,self.a.id,.25,1,1);self.enc.schedule_action(action)
        old=self.enc.choice_for_action(action.id);candidate=self.build()
        replacement=RunAction(self.world,self.a.id,.5,1,1)
        draft=self.enc.propose_choice((replacement,));validation=self.enc.validate_choice(draft,replacing=old)
        self.enc.replace_choice(old,validation)
        with self.assertRaises(StaleInterval):validate_interval_candidate(self.enc,candidate)
        self.assertEqual(self.enc.pending_action_list,[])
        self.assertTrue(validate_interval_candidate(self.enc,self.build()))

    def test_account_list_and_equipment_identity_changes_are_stale(self):
        history=self.f.f.history();accounts=[]
        action=AskAboutPastAction(self.world,self.b.id,self.a.id,0,episode_time=0,topic='lessons',generate=self.f.f.recipe(history),received_accounts=accounts)
        self.enc.schedule_action(action);candidate=self.build()
        action.received_accounts=[]
        with self.assertRaises(StaleInterval):validate_interval_candidate(self.enc,candidate)
        action.received_accounts=accounts
        self.assertTrue(validate_interval_candidate(self.enc,candidate))
        self.a.current.body_parts['right hand']=self.b.id
        with self.assertRaises(StaleInterval):validate_interval_candidate(self.enc,candidate)

    def test_valid_unavailable_weapon_is_normal_outcome_not_fault(self):
        wid=self.world.make_weapon_for_being(self.a.id,'Dagger','Knife');self.world.arm_being(self.a.id,wid,'right hand')
        action=MeleeStrike(self.enc,self.a.id,self.b.id,wid,motion='thrust',reach=3);self.enc.schedule_action(action)
        boundary=math.ceil(action.end_time)
        if boundary>1:self.enc.step(boundary-1)
        self.a.current.body_parts['right hand']=None
        candidate=self.build(boundary)
        self.assertEqual(candidate.supported_candidate.boundary.actions[action.id].outcome,'weapon_unavailable')
        self.assertIsNone(self.enc.boundary_fault)

    def test_nonbeing_combat_target_remains_explicit_refusal(self):
        wid=self.world.make_weapon_for_being(self.a.id,'Dagger','Knife');self.world.arm_being(self.a.id,wid,'right hand')
        self.enc.add_object(wid)
        action=Action(self.world,0,None,'thrust',self.a.id,wid,wid);self.enc.schedule_action(action)
        with self.assertRaisesRegex(UnsupportedEvaluation,'non-Being'):self.build()

    def test_unsafe_map_or_velocity_container_refused_without_callback(self):
        class Unsafe(dict):
            def items(self):raise AssertionError('unsafe items')
        self.enc.map=Unsafe()
        with self.assertRaises(UnsupportedEvaluation):self.build()
        self.enc.map=None
        with self.assertRaises(UnsupportedEvaluation):self.build(velocities=Unsafe())

    def test_committed_prior_history_is_only_extended_provisionally(self):
        self.enc.step(1);old=tuple(self.enc.fatigue_frame_history);candidate=self.build(2)
        proposed=candidate.proposed_authoritative_changes['fatigue_history']
        self.assertEqual(len(proposed),2);self.assertEqual(proposed[-1]['start'],1)
        self.assertEqual(self.enc.fatigue_frame_history,list(old));self.assertEqual(self.enc.time,1)

    def test_interval_complete_practice_revalidates_new_history_after_group_award(self):
        skills=self.world.get_skill_dictionary();self.a.set_skill_level(skills,'spot',1)
        self.a.record_skill_use(skills,'spot',1230,action_id='prior',time=-1,outcome='practice')
        history=self.f.f.history();group=self.f.f.group()
        observation=self.f.observe(self.a,group);spot=self.spot()
        ask=self.f.f.ask(self.b,history,self.f.f.recipe(history,rank=2,extra=(Fact(history.skill_key(1,'spot'),3),)))
        self.enc.schedule_choice((observation,spot,ask));candidate=self.build()
        self.assertEqual(candidate.supported_candidate.target(self.a.id).practice_state.skill_experience['spot'],1252)
        self.assertEqual(candidate.supported_candidate.target(self.a.id).practice_state.transitions[0].level_after,3)
        self.assertEqual(self.a.get_skill_level('spot'),2)

    def test_time_zero_duration_under_one_is_still_rejected_by_native_schedule(self):
        action=RunAction(self.world,self.a.id,0,.5,1)
        with self.assertRaises(ValueError):self.enc.schedule_action(action)
        self.assertEqual(self.enc.pending_action_list,[])
        self.assertEqual(self.build().supported_candidate.boundary.actions,{})

    def test_missing_terminal_registry_or_inconsistent_lifecycle_is_refused(self):
        action=self.spot();self.enc.schedule_action(action);self.enc.step(1)
        del self.world.event_history[action.id]
        with self.assertRaises(UnsupportedEvaluation):self.build(2)

    def test_aliased_mutable_spatial_or_target_state_is_refused(self):
        old=self.b.spatial_state;self.b.spatial_state=self.a.spatial_state
        with self.assertRaisesRegex(IntervalIntegrityError,'aliased mutable spatial'):self.build()
        self.b.spatial_state=old;self.b.current=self.a.current
        with self.assertRaisesRegex(IntervalIntegrityError,'aliased mutable Target'):self.build()

    def test_custom_scheduling_context_is_refused_before_entering_it(self):
        class UnsafeLock:
            def __enter__(self):raise AssertionError('unsafe lock callback')
            def __exit__(self,*args):raise AssertionError('unsafe lock callback')
        candidate=self.build();self.world._schedule_lock=UnsafeLock()
        with self.assertRaises(UnsupportedEvaluation):self.build()
        with self.assertRaises(StaleInterval):validate_interval_candidate(self.enc,candidate)

    def test_registry_storage_rebinding_is_stale_even_with_same_members(self):
        candidate=self.build();objects=self.world.object_registry.object_instances
        self.world.object_registry.object_instances=dict(objects)
        with self.assertRaises(StaleInterval):validate_interval_candidate(self.enc,candidate)
        self.world.object_registry.object_instances=objects
        self.assertTrue(validate_interval_candidate(self.enc,candidate))
        self.world._choice_books=list(self.world._choice_books)
        with self.assertRaises(StaleInterval):validate_interval_candidate(self.enc,candidate)


if __name__=='__main__':unittest.main()
