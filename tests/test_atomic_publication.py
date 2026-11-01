"""Explicit 5C2 publication, retained identities, full rollback and isolation."""
from dataclasses import replace
from pathlib import Path
import math
import random
import sys
import tempfile
import threading
from types import MappingProxyType
import unittest
from unittest.mock import patch,Mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import test_interval_staging as intervals
import test_action_settlement as combat
from atomic_publication import (PHASES, publication_boundary, coordinated_access,
    publish_interval_candidate, recover_interval_publication, PublicationFailure,
    RollbackIntegrityFailure, PublicationRejected, PublicationOwnershipError,
    RNGCursor, target_interval_history, target_effects_from)
from interval_staging import StaleInterval
from action_evaluation import _ProvisionalRandom,RandomDraw,UnsupportedEvaluation
from activities import RunAction,SpotAction
from field_observation import BeliefLedger
from history_conversation import AskAboutPastAction
from experience import BatchSkillUse,SkillUse
from melee_combat import MeleeStrike
from melee_defense import MeleeDefense
from realization import Fact
from strategy import Strategy
from spatial.state import CartesianPosition


def raw_graph(world,encounter):
    """All reachable native data and identities; fault-control latch is separate."""
    seen=set()
    def copy(value):
        if value is None or type(value) in (str,int,float,bool):return (type(value).__name__,value)
        if callable(value):return ('callable',id(value))
        identity=id(value)
        if identity in seen:return ('ref',identity)
        seen.add(identity)
        if type(value) in (dict,MappingProxyType):
            return ('mapping',identity,tuple((copy(k),copy(None if identity==id(encounter.__dict__) and k=='boundary_fault' else v)) for k,v in value.items()))
        if type(value) in (tuple,list):return (type(value).__name__,identity,tuple(copy(v) for v in value))
        if type(value) in (set,frozenset):return (type(value).__name__,identity,tuple(sorted((copy(v) for v in value),key=repr)))
        try:data=object.__getattribute__(value,'__dict__')
        except AttributeError:return ('opaque',type(value).__name__,identity)
        return (type(value).__name__,identity,copy(data))
    return copy(world)


class TestAtomicPublication(unittest.TestCase):
    def setUp(self):
        self.f=intervals.TestIntervalStaging();self.f.setUp()
        self.world,self.enc=self.f.world,self.f.enc
        self.a,self.b,self.c=self.f.a,self.f.b,self.f.c

    def build(self,boundary=1,**kwargs):return self.enc.prepare_interval_candidate(boundary,**kwargs)

    def advance_before(self,boundary):
        """Publish intervening integer boundaries without skipping native intervals."""
        while self.enc.last_processed_boundary < boundary - 1:
            next_boundary=self.enc.last_processed_boundary+1
            self.publish(self.build(next_boundary))

    def publish(self,candidate,**kwargs):
        with publication_boundary(self.enc,quiescent=True) as owner:
            return publish_interval_candidate(self.enc,candidate,ownership=owner,**kwargs)

    def mixed(self):
        group=self.f.f.f.group();history=self.f.f.f.history();accounts=[]
        la,lb=BeliefLedger(self.a.id),BeliefLedger(self.b.id)
        one,two=self.f.f.observe(self.a,group,ledger=la),self.f.f.observe(self.b,group,ledger=lb)
        ask=AskAboutPastAction(self.world,self.c.id,self.a.id,0,episode_time=0,topic='lessons',generate=self.f.f.f.recipe(history),received_accounts=accounts)
        spot=self.f.spot();run=RunAction(self.world,self.c.id,0,1,1,experience=7)
        self.enc.schedule_choice((one,two,ask,spot,run))
        # Also exercise unpublished whole-choice registration and fractional starts.
        future=RunAction(self.world,self.b.id,.2,1,1)
        later=SpotAction(self.world,self.c.id,self.b.id,.7,duration=6,die_roll=20)
        self.enc.schedule_choice((future,later))
        return self.build(velocities={self.c.id:(1,0,0),self.b.id:(.5,0,0)}),group,history,la,lb,accounts,(one,two,ask,spot,run,future,later)

    def test_success_advances_once_preserves_references_and_next_interval(self):
        action=self.f.spot();self.enc.schedule_action(action)
        self.advance_before(6)
        refs=(self.a,self.a.current,self.a.current.skills,self.a.current.skills.skills,self.a.skill_experience,
            self.a.skill_use_history,self.world.event_history,self.enc.pending_action_list,self.enc.finished_action_list,
            self.enc._choice_book,self.enc._choice_book._registered,self.enc._choice_book._states,self.enc._choice_book._choices,
            self.enc.awareness,self.enc.awareness[self.a.id],self.enc.fatigue_frame_history)
        candidate=self.build(6);receipt=self.publish(candidate)
        self.assertTrue(receipt.committed);self.assertEqual(receipt.boundary,6)
        self.assertEqual(self.enc.time,6);self.assertEqual(self.enc.last_processed_boundary,6)
        self.assertEqual(action.resolution,candidate.supported_candidate.boundary.actions[action.id])
        self.assertNotIn('spot',self.a.skill_experience)
        self.assertEqual(refs,(self.a,self.a.current,self.a.current.skills,self.a.current.skills.skills,self.a.skill_experience,
            self.a.skill_use_history,self.world.event_history,self.enc.pending_action_list,self.enc.finished_action_list,
            self.enc._choice_book,self.enc._choice_book._registered,self.enc._choice_book._states,self.enc._choice_book._choices,
            self.enc.awareness,self.enc.awareness[self.a.id],self.enc.fatigue_frame_history))
        for ref,now in zip(refs,(self.a,self.a.current,self.a.current.skills,self.a.current.skills.skills,self.a.skill_experience,
            self.a.skill_use_history,self.world.event_history,self.enc.pending_action_list,self.enc.finished_action_list,
            self.enc._choice_book,self.enc._choice_book._registered,self.enc._choice_book._states,self.enc._choice_book._choices,
            self.enc.awareness,self.enc.awareness[self.a.id],self.enc.fatigue_frame_history)):self.assertIs(ref,now)
        with self.assertRaises(PublicationRejected):self.publish(candidate)
        self.publish(self.build(7));self.assertEqual(self.enc.time,7)

    def test_mixed_publication_commits_exact_candidate_and_shared_reality(self):
        candidate,group,history,la,lb,accounts,actions=self.mixed()
        refs=(group._composition_reality,group._composition_reality._records,history,history.reality,history.reality._records,
            la,la._evidence,la._interpretations,la._belief_history,lb._evidence,accounts)
        self.publish(candidate);supported=candidate.supported_candidate
        self.assertEqual(group.counts(),dict(supported.objective.subject(group.id).counts))
        self.assertEqual(group._composition_reality.revision,1)
        self.assertEqual({r.revision for r in group._composition_reality._records.values()},{1})
        self.assertEqual(len(accounts),1);self.assertEqual(len(la.evidence),1);self.assertEqual(len(lb.evidence),1)
        self.assertNotEqual(la.evidence[0].reported_position,lb.evidence[0].reported_position)
        # Only provisional Group observations contribute Spot practice here.
        self.assertEqual(self.a.skill_experience['spot'],12);self.assertEqual(self.c.skill_experience['run'],7)
        self.assertEqual(self.c.get_position(),candidate.pre_action_snapshot.entity(self.c.id).position)
        self.assertEqual(self.enc.finished_action_list,list(supported.boundary.actions))
        self.assertEqual(self.enc.pending_action_list,list(candidate.proposed_authoritative_changes['queues'].pending))
        now=(group._composition_reality,group._composition_reality._records,history,history.reality,history.reality._records,
            la,la._evidence,la._interpretations,la._belief_history,lb._evidence,accounts)
        for old,new in zip(refs,now):self.assertIs(old,new)
        self.assertTrue(all(p.consumers for p in group._composition_reality._atomic_provenance))
        self.assertTrue(self.build(2).coverage=='complete_supported_interval')

    def test_fractional_whole_choice_actual_start_and_endpoint_registration(self):
        one=RunAction(self.world,self.a.id,.2,1,1);two=RunAction(self.world,self.c.id,.7,1,1)
        view=self.enc.schedule_choice((one,two));endpoint=RunAction(self.world,self.b.id,1,1,1);self.enc.schedule_action(endpoint)
        candidate=self.build(velocities={self.a.id:(10,0,0),self.c.id:(10,0,0)})
        self.publish(candidate)
        self.assertEqual(one.start_position,CartesianPosition(2,0,0));self.assertEqual(two.start_position,CartesianPosition(11,0,0))
        self.assertTrue(one._activity_started);self.assertTrue(two._activity_started);self.assertTrue(endpoint._activity_started)
        self.assertEqual(self.enc.get_choice(view.id).state,'executing');self.assertIsNone(endpoint.resolution)
        self.assertIs(self.world.event_history[one.id],one);self.assertIn(endpoint.id,self.enc.pending_action_list)
        self.assertEqual(self.enc._choice_book._registered[one.id][2],__import__('action_choice').declaration(one))
        self.publish(self.build(2));self.assertIsNotNone(one.resolution)

    def test_exact_boundary_and_fractional_spot_end_resolve_at_their_boundaries(self):
        one=self.f.spot();two=SpotAction(self.world,self.c.id,self.b.id,.25,die_roll=20);self.enc.schedule_choice((one,two))
        self.advance_before(6)
        self.publish(self.build(6));self.assertIsNotNone(one.resolution);self.assertIsNone(two.resolution)
        self.publish(self.build(7));self.assertIsNotNone(two.resolution)

    def test_practice_is_one_batch_transition_with_both_sources_and_history_query(self):
        skills=self.world.get_skill_dictionary();self.a.set_skill_level(skills,'run',1)
        self.a.record_skill_use(skills,'run',1230,action_id='prior',time=-2)
        h=self.a.begin_personal_history(earliest=-10,known_through=10,nondeclining_skills=('run',))
        ask=self.f.f.f.ask(self.c,h,self.f.f.f.recipe(h,rank=2,extra=(Fact(h.skill_key(1,'run'),3),)))
        one=RunAction(self.world,self.a.id,0,1,.5,experience=10)
        two=RunAction(self.world,self.a.id,0,1,.5,experience=12)
        spot=self.f.spot();self.enc.schedule_choice((one,two,spot,ask));before=self.a.skill_use_history
        candidate=self.build(velocities={self.a.id:(1,0,0)});self.publish(candidate)
        self.assertIs(self.a.skill_use_history,before);self.assertEqual(len(before),2)
        batch=before[-1];self.assertIs(type(batch),BatchSkillUse)
        self.assertEqual((batch.level_before,batch.level_after,batch.experience),(2,3,22))
        self.assertEqual({x.action_id for x in batch.exercises},{one.id,two.id})
        self.assertIsNone(batch.action_id);self.assertEqual(h.reality.inspect(h.skill_key(1,'run')).value,3)
        self.assertEqual(self.a.get_skill_level('run'),3)
        self.assertEqual(self.a.skill_experience['run'],1252)
        self.assertTrue(self.build(2).coverage=='complete_supported_interval')
        with self.assertRaises(ValueError):self.a.record_skill_use(skills,'run',1,action_id=one.id,time=2)
        with self.assertRaises(ValueError):h.commit_skill_rank(1,'run',2)

    def test_unfavorable_outcome_and_cancelled_acknowledgement_commit(self):
        fail=self.f.spot(roll=1);cancelled=RunAction(self.world,self.c.id,0,1,1)
        self.enc.schedule_choice((fail,cancelled));self.enc.cancel_action(cancelled.id,reason='stopped')
        self.publish(self.build())
        self.assertIsNone(fail.resolution);self.assertEqual(cancelled.resolution.outcome,'interrupted')
        self.assertEqual(self.enc.cancelled_action_list,[cancelled.id]);self.assertNotIn(cancelled.id,self.enc.finished_action_list)
        self.advance_before(6)
        self.publish(self.build(6));self.assertEqual(fail.resolution.outcome,'failure')
        self.assertEqual(cancelled._atomic_acknowledged_boundary,1)

    def test_failed_observation_does_not_commit_unused_objective_facts(self):
        group=self.f.f.f.group();action=self.f.f.observe(self.a,group,roll=1);self.enc.schedule_action(action)
        self.publish(self.build());self.assertIsNone(group._counts);self.assertEqual(group._composition_reality.revision,0)
        self.assertEqual(self.a.skill_experience['spot'],18)

    def test_known_objective_records_and_cache_keep_identity_and_revision(self):
        group=self.f.f.f.group();group.counts();ledger=group._composition_reality;records=dict(ledger._records);cache=group._counts;revision=ledger.revision
        action=self.f.f.observe(self.a,group);self.enc.schedule_action(action);self.publish(self.build())
        self.assertEqual(ledger.revision,revision);self.assertIs(group._counts,cache)
        for key,record in records.items():self.assertIs(ledger._records[key],record)

    def test_all_equal_claim_origins_and_requesters_are_retained(self):
        history=self.f.f.f.history();recipe=self.f.f.f.recipe(history)
        other=type(recipe)(tuple(Fact(x.key,x.value,'another_source') for x in recipe.facts))
        one=self.f.f.f.ask(self.b,history,recipe);two=self.f.f.f.ask(self.c,history,other)
        self.enc.schedule_choice((one,two));self.publish(self.build())
        self.assertEqual(history.reality.revision,1)
        provenance=history.reality._atomic_provenance[-1]
        self.assertEqual(set(provenance.origins),{'declared_history','another_source'})
        self.assertEqual(set(provenance.requesters),{one.id,two.id})

    def test_prior_physical_frame_and_qb_remain_unchanged(self):
        self.enc.step(1);old=self.enc.last_fatigue_frame;history=self.enc.fatigue_frame_history;qb=self.a.physical_fatigue
        candidate=self.build(2);self.publish(candidate)
        self.assertIs(self.enc.fatigue_frame_history,history);self.assertEqual(len(history),2)
        self.assertIsNot(self.enc.last_fatigue_frame,old);self.assertEqual(old.to_dict(),self.enc.last_fatigue_frame.to_dict())
        self.assertIs(self.a.physical_fatigue,qb)

    def test_no_publication_without_explicit_ownership(self):
        candidate=self.build();before=raw_graph(self.world,self.enc)
        with self.assertRaises(PublicationOwnershipError):publish_interval_candidate(self.enc,candidate)
        with self.assertRaises(PublicationOwnershipError):
            with publication_boundary(self.enc):pass
        self.assertEqual(raw_graph(self.world,self.enc),before);self.assertIsNone(self.enc.boundary_fault)

    def test_forged_or_copied_candidate_rejected_before_writes(self):
        candidate=self.build();before=raw_graph(self.world,self.enc)
        with self.assertRaises(PublicationRejected):self.publish(replace(candidate))
        self.assertEqual(raw_graph(self.world,self.enc),before);self.assertIsNone(self.enc.boundary_fault)

    def test_altered_issued_candidate_seal_rejected_without_fault(self):
        candidate=self.build();object.__setattr__(candidate,'coverage','partial')
        before=raw_graph(self.world,self.enc)
        with self.assertRaises(ValueError):self.publish(candidate)
        self.assertEqual(raw_graph(self.world,self.enc),before);self.assertIsNone(self.enc.boundary_fault)

    def test_target_recipient_choice_and_rng_staleness_are_prewrite_refusals(self):
        candidate,*_=self.mixed();self.a.current.hit_points-=1;before=raw_graph(self.world,self.enc)
        with self.assertRaises(StaleInterval):self.publish(candidate)
        self.assertEqual(raw_graph(self.world,self.enc),before);self.assertIsNone(self.enc.boundary_fault)
        candidate=self.build();self.world._schedule_revision+=1
        with self.assertRaises(StaleInterval):self.publish(candidate)

    def test_recipient_content_mutation_after_staging_is_rejected(self):
        candidate,_,_,la,_,_,_=self.mixed();la.communication_log.append(('external','change'))
        before=raw_graph(self.world,self.enc)
        with self.assertRaises(StaleInterval):self.publish(candidate)
        self.assertEqual(raw_graph(self.world,self.enc),before)

    def test_divergent_rng_is_rejected_before_writes(self):
        rng=random.Random(8);candidate=self.build(rng_owner=rng);rng.random();before=raw_graph(self.world,self.enc)
        with self.assertRaises(StaleInterval):self.publish(candidate,rng_owner=rng)
        self.assertEqual(raw_graph(self.world,self.enc),before)

    def test_immutable_caller_state_refuses_but_explicit_cursor_commits(self):
        action=self.f.spot(roll=None);self.enc.schedule_action(action);state=random.Random(9).getstate()
        self.advance_before(6)
        candidate=self.build(6,rng_state=state);before=raw_graph(self.world,self.enc)
        with self.assertRaises(UnsupportedEvaluation):self.publish(candidate,rng_state=state)
        self.assertEqual(raw_graph(self.world,self.enc),before);self.assertIsNone(self.enc.boundary_fault)
        cursor=RNGCursor(state);candidate=self.build(6,rng_owner=cursor);self.publish(candidate,rng_owner=cursor)
        self.assertEqual(cursor.state,candidate.provisional_rng.after);self.assertNotEqual(cursor.state,state)

    def test_module_and_native_random_commit_proposed_cursor(self):
        saved=random.getstate()
        try:
            action=self.f.spot(roll=None);self.enc.schedule_action(action)
            self.advance_before(6)
            candidate=self.build(6)
            self.publish(candidate);self.assertEqual(random.getstate(),candidate.provisional_rng.after)
            other=TestAtomicPublication();other.setUp();rng=random.Random(42)
            action=SpotAction(other.world,other.c.id,other.b.id,0,die_roll=None)
            other.enc.schedule_action(action)
            other.advance_before(6)
            candidate=other.build(6,rng_owner=rng);outside=random.getstate();other.publish(candidate,rng_owner=rng)
            self.assertEqual(rng.getstate(),candidate.provisional_rng.after);self.assertEqual(random.getstate(),outside)
        finally:random.setstate(saved)

    def test_direct_native_facade_root_and_rng_publish_without_consumer_activation(self):
        from tactical_duel import TacticalDuel
        duel=TacticalDuel(seed=14);before=random.getstate()
        candidate=duel.encounter.prepare_interval_candidate(1,rng_owner=duel)
        with publication_boundary(duel.encounter,quiescent=True) as owner:
            publish_interval_candidate(duel.encounter,candidate,ownership=owner,rng_owner=duel)
        self.assertEqual(duel._rng_state,candidate.provisional_rng.after);self.assertEqual(random.getstate(),before)
        self.assertEqual(duel.commands,[])

    def test_coordinated_reader_blocks_until_committed_interval_visible(self):
        action=self.f.spot();self.enc.schedule_action(action)
        self.advance_before(6)
        candidate=self.build(6)
        attempted=threading.Event();done=threading.Event();observed=[]
        def reader():
            attempted.set()
            with coordinated_access(self.world):observed.append((self.enc.time,action.resolution.outcome,len(self.a.skill_use_history)))
            done.set()
        with publication_boundary(self.enc,quiescent=True) as owner:
            thread=threading.Thread(target=reader);thread.start();self.assertTrue(attempted.wait(1))
            self.assertFalse(done.wait(.05))
            publish_interval_candidate(self.enc,candidate,ownership=owner)
            self.assertFalse(done.is_set())
        thread.join(2);self.assertFalse(thread.is_alive());self.assertEqual(observed,[(6,'success',0)])

    def test_competing_coordinated_writer_before_acquisition_makes_candidate_stale(self):
        candidate=self.build()
        def writer():
            with coordinated_access(self.world):self.a.current.hit_points-=1
        thread=threading.Thread(target=writer);thread.start();thread.join(2)
        with self.assertRaises(StaleInterval):self.publish(candidate)
        self.assertIsNone(self.enc.boundary_fault)

    def test_lease_wrong_thread_nested_ownership_and_reentry_are_refused(self):
        candidate=self.build();errors=[]
        with publication_boundary(self.enc,quiescent=True) as owner:
            with self.assertRaises(PublicationOwnershipError):
                with publication_boundary(self.enc,quiescent=True):pass
            def attempt():
                try:publish_interval_candidate(self.enc,candidate,ownership=owner)
                except Exception as exc:errors.append(exc)
            thread=threading.Thread(target=attempt);thread.start();thread.join(2)
            self.assertEqual(len(errors),1);self.assertIsInstance(errors[0],PublicationOwnershipError)
        with self.assertRaises(PublicationOwnershipError):publish_interval_candidate(self.enc,candidate,ownership=owner)

    def test_callback_override_and_unsupported_due_family_refused_without_execution(self):
        action=self.f.spot();self.enc.schedule_action(action);unsafe=Mock(side_effect=AssertionError('unsafe'))
        self.advance_before(6)
        action.on_completed=unsafe
        with self.assertRaises(UnsupportedEvaluation):self.build(6)
        unsafe.assert_not_called();self.assertEqual(self.enc.time,5)

    def test_aliased_recipient_and_practice_write_locations_fail_before_writes(self):
        one=self.f.spot();self.enc.schedule_action(one)
        self.advance_before(6)
        # Existing staging can read these equal containers; publisher must not
        # install independent meanings into one retained mutable mapping.
        self.a._skill_practice_baselines=self.a.skill_experience
        candidate=self.build(6);before=raw_graph(self.world,self.enc)
        with self.assertRaises(UnsupportedEvaluation):self.publish(candidate)
        self.assertEqual(raw_graph(self.world,self.enc),before);self.assertIsNone(self.enc.boundary_fault)

    def test_optin_checkpoint_persistence_is_explicitly_refused(self):
        self.publish(self.build())
        with self.assertRaises(ValueError):self.enc.assert_checkpoint_exportable()
        with self.assertRaises(ValueError):self.world.to_json()
        with self.assertRaises(ValueError):self.enc.to_json()
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):self.world.save_to_file(str(Path(directory)/'world.json'))
            self.assertFalse((Path(directory)/'world.json').exists())

    def test_live_dispatch_and_legacy_consumers_do_not_use_publisher(self):
        action=self.f.spot();self.enc.schedule_action(action)
        with patch('atomic_publication.publish_interval_candidate',side_effect=AssertionError('inactive')):
            self.enc.step(6)
        self.assertIsNotNone(action.resolution);self.assertNotIn('spot',self.a.skill_experience)
        self.assertFalse(self.enc.__dict__.get('_atomic_interval_history'))

    def test_failure_after_prior_committed_second_restores_only_current_interval(self):
        self.publish(self.build());action=RunAction(self.world,self.a.id,1,1,1,experience=5);self.enc.schedule_action(action)
        candidate=self.build(2,velocities={self.a.id:(2,0,0)});before=raw_graph(self.world,self.enc)
        with publication_boundary(self.enc,quiescent=True) as owner:
            with self.assertRaises(PublicationFailure) as caught:publish_interval_candidate(self.enc,candidate,ownership=owner,_fail_after='frames_clock')
            self.assertFalse(caught.exception.rollback_errors);self.assertEqual(raw_graph(self.world,self.enc),before)
            self.assertEqual(self.enc.time,1);self.assertEqual(len(self.enc._atomic_interval_history),1)
            recover_interval_publication(self.enc,caught.exception.recovery_token,ownership=owner)
            retry=self.build(2,velocities={self.a.id:(2,0,0)})
            self.assertEqual(retry,candidate);publish_interval_candidate(self.enc,retry,ownership=owner)
        self.assertEqual(self.enc.time,2);self.assertEqual(len(self.enc._atomic_interval_history),2)

    def test_failed_publication_blocks_legacy_progress_save_and_requires_fresh_candidate(self):
        candidate=self.build()
        with publication_boundary(self.enc,quiescent=True) as owner:
            with self.assertRaises(PublicationFailure) as caught:publish_interval_candidate(self.enc,candidate,ownership=owner,_fail_after='rng')
            for operation in (lambda:self.enc.step(1),self.enc.run,self.enc.assert_checkpoint_exportable,self.build):
                with self.assertRaises(ValueError):operation()
            with self.assertRaises(PublicationRejected):recover_interval_publication(self.enc,'wrong',ownership=owner)
            recover_interval_publication(self.enc,caught.exception.recovery_token,ownership=owner)
            with self.assertRaises(PublicationRejected):publish_interval_candidate(self.enc,candidate,ownership=owner)
            publish_interval_candidate(self.enc,self.build(),ownership=owner)
        self.assertEqual(self.enc.time,1)

    def test_recovery_refuses_if_restored_checkpoint_was_edited(self):
        candidate=self.build()
        with publication_boundary(self.enc,quiescent=True) as owner:
            with self.assertRaises(PublicationFailure) as caught:publish_interval_candidate(self.enc,candidate,ownership=owner,_fail_after='targets')
            original=self.a.current.hit_points;self.a.current.hit_points-=1
            with self.assertRaises(PublicationRejected):recover_interval_publication(self.enc,caught.exception.recovery_token,ownership=owner)
            self.a.current.hit_points=original
            recover_interval_publication(self.enc,caught.exception.recovery_token,ownership=owner)

    @patch('atomic_publication._EMERGENCIES',{})  # Isolated sabotage; no production reset API.
    def test_rollback_integrity_failure_is_emergency_and_has_both_faults(self):
        candidate=self.build(velocities={self.a.id:(2,0,0)})
        with publication_boundary(self.enc,quiescent=True) as owner:
            with self.assertRaises(RollbackIntegrityFailure) as caught:
                publish_interval_candidate(self.enc,candidate,ownership=owner,_fail_after='movement',_rollback_fail_at=0)
            self.assertIn('injected publication failure',str(caught.exception.original))
            self.assertTrue(caught.exception.rollback_errors);self.assertEqual(self.enc.boundary_fault['rollback'],'failed')
            with self.assertRaises(PublicationOwnershipError):recover_interval_publication(self.enc,caught.exception.recovery_token,ownership=owner)
        with self.assertRaises(PublicationOwnershipError):
            with publication_boundary(self.enc,quiescent=True):pass
        with self.assertRaises(ValueError):self.enc.step(1)
        other=intervals.TestIntervalStaging();other.setUp()
        with self.assertRaises(PublicationOwnershipError):
            with publication_boundary(other.enc,quiescent=True):pass

    def test_nontrivial_rng_rollback_for_module_random_and_caller_cursor(self):
        outside=random.getstate()
        try:
            for role in ('module','random','cursor'):
                with self.subTest(role=role):
                    fixture=intervals.TestIntervalStaging();fixture.setUp();enc=fixture.enc
                    action=fixture.spot(roll=None);enc.schedule_action(action)
                    owner=None if role=='module' else random.Random(31) if role=='random' else RNGCursor(random.Random(31).getstate())
                    for boundary in range(1,6):
                        prior=enc.prepare_interval_candidate(boundary,rng_owner=owner)
                        with publication_boundary(enc,quiescent=True) as lease:
                            publish_interval_candidate(enc,prior,ownership=lease,rng_owner=owner)
                    candidate=enc.prepare_interval_candidate(6,rng_owner=owner)
                    self.assertNotEqual(candidate.provisional_rng.before,candidate.provisional_rng.after)
                    before=raw_graph(fixture.world,enc)
                    with publication_boundary(enc,quiescent=True) as lease:
                        with self.assertRaises(PublicationFailure) as caught:
                            publish_interval_candidate(enc,candidate,ownership=lease,rng_owner=owner,_fail_after='rng')
                        actual=random.getstate() if role=='module' else owner.getstate() if role=='random' else owner.state
                        self.assertEqual(actual,candidate.provisional_rng.before)
                        self.assertEqual(raw_graph(fixture.world,enc),before)
                        recover_interval_publication(enc,caught.exception.recovery_token,ownership=lease,rng_owner=owner)
                        retry=enc.prepare_interval_candidate(6,rng_owner=owner)
                        self.assertEqual(candidate,retry)
                        publish_interval_candidate(enc,retry,ownership=lease,rng_owner=owner)
        finally:random.setstate(outside)

    def test_partial_native_container_write_failure_is_journaled_before_write(self):
        from atomic_publication import _ContentsWrite
        candidate,*_=self.mixed();before=raw_graph(self.world,self.enc)
        original=_ContentsWrite.apply
        def broken(operation):
            if operation.storage is self.world.event_history:
                dict.clear(operation.storage)
                raise RuntimeError('partial native dict write')
            original(operation)
        with publication_boundary(self.enc,quiescent=True) as owner:
            with patch.object(_ContentsWrite,'apply',broken):
                with self.assertRaises(PublicationFailure) as caught:publish_interval_candidate(self.enc,candidate,ownership=owner)
            self.assertFalse(caught.exception.rollback_errors)
            self.assertIn('partial native dict',str(caught.exception.original))
            self.assertEqual(raw_graph(self.world,self.enc),before)
            recover_interval_publication(self.enc,caught.exception.recovery_token,ownership=owner)

    def test_intermediate_coordinated_access_and_reentrant_publish_are_refused(self):
        from atomic_publication import _WritePlan
        candidate=self.build();original=_WritePlan.apply_phase;attempts=[]
        with publication_boundary(self.enc,quiescent=True) as owner:
            def phase(plan,name):
                original(plan,name)
                if name=='frames_clock':
                    with self.assertRaises(PublicationOwnershipError):
                        with coordinated_access(self.world):attempts.append('observed partial state')
                    with self.assertRaises(PublicationOwnershipError):publish_interval_candidate(self.enc,candidate,ownership=owner)
            with patch.object(_WritePlan,'apply_phase',phase):publish_interval_candidate(self.enc,candidate,ownership=owner)
        self.assertEqual(attempts,[])

    def test_ending_boundary_can_publish_without_requiring_a_future_interval(self):
        self.enc.end_time=1;self.publish(self.build());self.assertEqual(self.enc.time,1)
        with self.assertRaises(ValueError):self.build(2)

    def test_cancelled_action_and_multiple_awards_can_be_captured_in_later_interval(self):
        first=RunAction(self.world,self.a.id,0,1,.5,experience=10)
        self.enc.schedule_action(first);self.publish(self.build(velocities={self.a.id:(1,0,0)}))
        second=RunAction(self.world,self.a.id,1,1,.5,experience=10)
        self.enc.schedule_action(second);self.publish(self.build(2,velocities={self.a.id:(1,0,0)}))
        self.assertEqual(self.a.skill_experience['run'],20)
        self.assertEqual([x.time for x in self.a.skill_use_history],[1,2])
        self.assertTrue(self.build(3).coverage=='complete_supported_interval')

    def test_candidate_integrity_is_checked_again_after_application(self):
        from atomic_publication import _WritePlan
        candidate=self.build();before=raw_graph(self.world,self.enc);original=_WritePlan.apply_phase
        def tamper(plan,name):
            original(plan,name)
            if name=='rng':object.__setattr__(candidate,'coverage','fragment')
        with publication_boundary(self.enc,quiescent=True) as owner:
            with patch.object(_WritePlan,'apply_phase',tamper):
                with self.assertRaises(PublicationFailure) as caught:publish_interval_candidate(self.enc,candidate,ownership=owner)
            self.assertFalse(caught.exception.rollback_errors)
            self.assertEqual(raw_graph(self.world,self.enc),before)
            recover_interval_publication(self.enc,caught.exception.recovery_token,ownership=owner)
            publish_interval_candidate(self.enc,self.build(),ownership=owner)

    def test_shared_account_container_retains_old_entries_and_appends_each_source_once(self):
        history=self.f.f.f.history();accounts=[]
        one=AskAboutPastAction(self.world,self.b.id,self.a.id,0,episode_time=0,topic='lessons',generate=self.f.f.f.recipe(history),received_accounts=accounts)
        two=AskAboutPastAction(self.world,self.c.id,self.a.id,0,episode_time=0,topic='lessons',generate=self.f.f.f.recipe(history),received_accounts=accounts)
        self.enc.schedule_choice((one,two));self.publish(self.build())
        self.assertEqual([x.action_id for x in accounts],[one.id,two.id])
        old=tuple(accounts);third=AskAboutPastAction(self.world,self.b.id,self.a.id,1,episode_time=0,topic='lessons',generate=self.f.f.f.recipe(history),received_accounts=accounts)
        self.enc.schedule_action(third);self.publish(self.build(2))
        self.assertEqual(len(accounts),3)
        for before,after in zip(old,accounts):self.assertIs(before,after)
        self.assertEqual(history.reality.revision,1)

    def test_existing_evidence_interpretation_and_belief_revision_objects_are_retained(self):
        from group_observation import ObserveGroupAction,observation_rng
        group=self.f.f.f.group();ledger=BeliefLedger(self.a.id)
        one=self.f.f.observe(self.a,group,ledger=ledger);self.enc.schedule_action(one);self.publish(self.build())
        evidence=ledger._evidence[one.id];reading=ledger._interpretations[one.id];revision=ledger._belief_history[0]
        seed=next(n for n in range(10000) if observation_rng(n,'second',group.id,1,'d20').randint(1,20)==20)
        two=ObserveGroupAction(self.world,self.a.id,group.id,1,seed=seed,random_key='second',ledger=ledger,
            observation={'coarse_range_m':100,'detailed_range_m':50})
        self.enc.schedule_action(two);self.publish(self.build(2))
        self.assertIs(ledger._evidence[one.id],evidence);self.assertIs(ledger._interpretations[one.id],reading)
        self.assertIs(ledger._belief_history[0],revision);self.assertEqual(len(ledger.evidence),2)

    @patch('atomic_publication._EMERGENCIES',{})  # Keep emergency fixture out of other tests.
    def test_inverse_journal_runner_failure_also_latches_emergency(self):
        from atomic_publication import _WritePlan
        candidate=self.build(velocities={self.a.id:(1,0,0)})
        with publication_boundary(self.enc,quiescent=True) as owner:
            with patch.object(_WritePlan,'rollback',side_effect=RuntimeError('journal runner broke')):
                with self.assertRaises(RollbackIntegrityFailure) as caught:
                    publish_interval_candidate(self.enc,candidate,ownership=owner,_fail_after='movement')
            self.assertTrue(any('journal runner broke' in x for x in caught.exception.rollback_errors))
            self.assertEqual(self.enc.boundary_fault['rollback'],'failed')
            with self.assertRaises(PublicationOwnershipError):recover_interval_publication(self.enc,caught.exception.recovery_token,ownership=owner)

    def test_missing_none_valued_start_metadata_is_not_a_successful_publication(self):
        from atomic_publication import _AttributeWrite
        action=RunAction(self.world,self.a.id,.2,1,1);self.enc.schedule_action(action)
        self.a.spatial_state=None
        candidate=self.build();before=raw_graph(self.world,self.enc);original=_AttributeWrite.apply
        def drop_none(operation):
            original(operation)
            if operation.storage is action.__dict__ and operation.key=='start_position':
                self.assertIsNone(operation.after);del operation.storage['start_position']
        with publication_boundary(self.enc,quiescent=True) as owner:
            with patch.object(_AttributeWrite,'apply',drop_none):
                with self.assertRaises(PublicationFailure) as caught:publish_interval_candidate(self.enc,candidate,ownership=owner)
            self.assertFalse(caught.exception.rollback_errors);self.assertEqual(raw_graph(self.world,self.enc),before)
            recover_interval_publication(self.enc,caught.exception.recovery_token,ownership=owner)

    def test_published_physiology_frame_retains_common_prepractice_profile_and_qb(self):
        from physiology_registry import PhysiologyRegistry,PhysiologyDefinition
        registry=PhysiologyRegistry((PhysiologyDefinition('human@1',model='human-r4'),))
        for being in (self.a,self.b,self.c):being.physiology_id='human@1'
        self.enc.set_physiology_registry(registry);self.a.set_physical_fatigue(.7,.8)
        self.a.set_skill_level(self.world.get_skill_dictionary(),'run',0)
        action=RunAction(self.world,self.a.id,0,1,1,experience=300);self.enc.schedule_action(action)
        qb=self.a.physical_fatigue;definitions=registry._definitions
        candidate=self.build(velocities={self.a.id:(2,0,0)});self.publish(candidate)
        self.assertIs(self.a.physical_fatigue,qb);self.assertIs(registry._definitions,definitions)
        self.assertEqual(self.a.get_skill_level('run'),1)
        profile=self.enc.last_fatigue_frame.physiology(self.a.id,mode='running')
        self.assertEqual(profile.version_hash,candidate.pre_action_snapshot.physiology[self.a.id]['running']['version_hash'])
        self.assertEqual(self.enc.last_fatigue_frame.to_dict(),dict(candidate.pre_action_snapshot.fatigue))

    def test_inverted_schedule_lock_entry_is_refused_before_waiting_for_gate(self):
        with self.world._schedule_lock:
            with self.assertRaises(PublicationOwnershipError):
                with publication_boundary(self.enc,quiescent=True):pass
            with self.assertRaises(PublicationOwnershipError):
                with coordinated_access(self.world):pass
        with coordinated_access(self.world):
            with coordinated_access(self.world):self.assertEqual(self.enc.time,0)

    def test_unbacked_cancellation_ack_cannot_hide_a_due_action(self):
        action=RunAction(self.world,self.a.id,0,2,1);self.enc.schedule_action(action);self.enc.cancel_action(action.id)
        self.enc.step(1);action._atomic_acknowledged_boundary=1
        before=raw_graph(self.world,self.enc)
        with self.assertRaisesRegex(ValueError,'unbacked'):self.build(2)
        self.assertEqual(raw_graph(self.world,self.enc),before);self.assertIsNone(self.enc.boundary_fault)

    def _fault_phase(self,phase):
        saved=random.getstate()
        try:
            candidate,group,history,la,lb,accounts,actions=self.mixed()
            before=raw_graph(self.world,self.enc);rng=random.getstate()
            with publication_boundary(self.enc,quiescent=True) as owner:
                with self.assertRaises(PublicationFailure) as caught:
                    publish_interval_candidate(self.enc,candidate,ownership=owner,_fail_after=phase)
                fault=caught.exception
                self.assertFalse(fault.rollback_errors,str(fault));self.assertEqual(fault.phase,phase)
                self.assertEqual(raw_graph(self.world,self.enc),before);self.assertEqual(random.getstate(),rng)
                self.assertEqual(self.enc.last_processed_boundary,0);self.assertEqual(accounts,[])
                self.assertIsNone(group._counts);self.assertEqual(history.reality.revision,0)
                recover_interval_publication(self.enc,fault.recovery_token,ownership=owner)
                retry=self.build(velocities={self.c.id:(1,0,0),self.b.id:(.5,0,0)})
                self.assertEqual(retry,candidate)
                publish_interval_candidate(self.enc,retry,ownership=owner)
            self.assertEqual(self.enc.time,1);self.assertEqual(len(accounts),1)
        finally:random.setstate(saved)


for _phase in PHASES:
    def _test(self,phase=_phase):self._fault_phase(phase)
    setattr(TestAtomicPublication,'test_fault_restoration_after_'+_phase,_test)


class TestAtomicCombatPublication(unittest.TestCase):
    def setUp(self):
        self.f=combat.TestActionSettlement();self.f.setUp()
        self.world,self.enc,self.a,self.b=self.f.world,self.f.enc,self.f.a,self.f.b

    def stage(self,actions,rolls):
        self.enc.schedule_choice(actions);boundary=max(math.ceil(a.end_time) for a in actions)
        if boundary>1:self.enc.step(boundary-1)
        values=iter(rolls)
        def roll(rng,dice):
            value=next(values);rng.trace.append(RandomDraw(rng.action_id,dice,int(dice[2:].split('+')[0]),value));return value
        with patch.object(_ProvisionalRandom,'roll',roll):return self.enc.prepare_interval_candidate(boundary)

    def publish(self,candidate):
        with publication_boundary(self.enc,quiescent=True) as owner:return publish_interval_candidate(self.enc,candidate,ownership=owner)

    def test_two_strikes_commit_negative_hp_and_target_owned_causal_contributions(self):
        self.b.set_hit_points(3);one=self.f.attack(self.f.w1);two=self.f.attack(self.f.w2)
        candidate=self.stage((one,two),(15,4,15,4));self.publish(candidate)
        self.assertEqual(self.b.get_hit_points(),-5)
        self.assertEqual(len(target_interval_history(self.b)),1)
        self.assertEqual(sum(r.effect.amount for r in target_effects_from(self.b,one.id) if hasattr(r.effect,'amount')),4)
        self.assertFalse(any('hp_before' in name or 'hp_after' in name for name in vars(one.resolution)))
        self.assertEqual(one.resolution.outcome,'normal');self.assertEqual(two.resolution.outcome,'normal')

    def test_multiple_fatal_effects_apply_floor_once_without_invented_damage(self):
        one=self.f.attack(self.f.w1);two=self.f.attack(self.f.w2)
        candidate=self.stage((one,two),(20,20,1,20,20,1));self.publish(candidate)
        self.assertEqual(self.b.get_hit_points(),-10)
        record=target_interval_history(self.b)[-1].state
        self.assertEqual(len(record.fatal_effect_ids),2);self.assertEqual(record.actual_damage,0)

    def test_fatal_and_normal_damage_are_added_to_one_fatal_floor(self):
        one=self.f.attack(self.f.w1);two=self.f.attack(self.f.w2)
        candidate=self.stage((one,two),(20,20,1,15,4));self.publish(candidate)
        self.assertEqual(self.b.get_hit_points(),-14)

    def test_armor_and_shield_damage_commit_below_zero_with_same_protection_snapshot(self):
        armor_id=self.world.make_armor_for_being(self.b.id,'Leather armor','Jacket');self.world.armor_being(self.b.id,armor_id)
        armor=self.world.get_object_by_id(armor_id);armor.current.hit_points=1
        one=self.f.attack(self.f.w1,extra=10);two=self.f.attack(self.f.w2,extra=10)
        candidate=self.stage((one,two),(15,4,15,4));old_current=armor.current;self.publish(candidate)
        self.assertIs(armor.current,old_current);self.assertEqual(armor.current.hit_points,candidate.supported_candidate.target(armor_id).projected_hp)
        self.assertLess(armor.current.hit_points,0);self.assertEqual(len(target_interval_history(armor)[-1].state.incoming),4)

    def test_passive_shield_commits_below_zero_and_retains_original_storage(self):
        sid=self.world.make_weapon_for_being(self.b.id,'Small shield','Shield');self.world.arm_being(self.b.id,sid,'shield hand')
        shield=self.world.get_object_by_id(sid);shield.current.hit_points=1;current=shield.current
        one=self.f.attack(self.f.w1);two=self.f.attack(self.f.w2)
        candidate=self.stage((one,two),(15,4,1,15,4,1));self.publish(candidate)
        self.assertIs(shield.current,current);self.assertEqual(current.hit_points,-7)
        self.assertEqual(target_interval_history(shield)[-1].state.actual_damage,8)

    def test_hp_armor_shield_and_rank_writes_restore_at_late_fault(self):
        saved=random.getstate()
        try:
            aid=self.world.make_armor_for_being(self.b.id,'Leather armor','Armor');armor=self.world.get_object_by_id(aid);armor.current.hit_points=1
            sid=self.world.make_weapon_for_being(self.b.id,'Small shield','Shield');self.world.arm_being(self.b.id,sid,'shield hand')
            shield=self.world.get_object_by_id(sid);shield.current.hit_points=1;self.b.current.hit_points=1
            one=self.f.attack(self.f.w1,extra=10);two=self.f.attack(self.f.w2,extra=10)
            candidate=self.stage((one,two),(15,4,1,15,4,1));before=raw_graph(self.world,self.enc)
            with publication_boundary(self.enc,quiescent=True) as owner:
                with self.assertRaises(PublicationFailure) as caught:
                    publish_interval_candidate(self.enc,candidate,ownership=owner,_fail_after='rng')
                self.assertFalse(caught.exception.rollback_errors);self.assertEqual(raw_graph(self.world,self.enc),before)
                self.assertEqual((self.b.current.hit_points,armor.current.hit_points,shield.current.hit_points),(1,1,1))
                recover_interval_publication(self.enc,caught.exception.recovery_token,ownership=owner)
        finally:random.setstate(saved)

    def test_resource_handoff_metadata_only_starts_after_settlement_phase(self):
        from atomic_publication import _WritePlan
        old=self.f.attack(melee=True);boundary=math.ceil(old.end_time)
        new=self.f.attack(melee=True);new.start_time=boundary;new.end_time+=boundary
        self.enc.schedule_choice((old,new))
        if boundary>1:self.enc.step(boundary-1)
        candidate=self.enc.prepare_interval_candidate(boundary)
        original=_WritePlan.apply_phase;observed=[]
        def inspect_phase(plan,name):
            original(plan,name)
            if name=='lifecycle':
                observed.append((old.id in self.enc.finished_action_list,bool(getattr(new,'_activity_started',False)),tuple(r.action_id for r in self.enc.active_reservations)))
        with patch.object(_WritePlan,'apply_phase',inspect_phase):self.publish(candidate)
        self.assertEqual(observed,[(True,False,(new.id,))]);self.assertTrue(new._activity_started)
        self.assertIn(new.id,self.enc.pending_action_list);self.assertIsNone(new.resolution)

    def test_multiple_defenses_keep_each_outcome_association_and_practice(self):
        strike=self.f.attack(melee=True)
        one=MeleeDefense(self.enc,self.b.id,self.a.id,kind='dodge',target_action_id=strike.id)
        two=MeleeDefense(self.enc,self.b.id,self.a.id,kind='dodge',target_action_id=strike.id)
        candidate=self.stage((strike,one,two),(20,1,1,20));self.publish(candidate)
        self.assertEqual(strike.resolution.outcome,'dodged')
        self.assertEqual(len(strike.resolution.defenses),2)
        self.assertEqual(self.b.skill_experience['tumble'],20)
        self.assertIs(type(self.b.skill_use_history[-1]),BatchSkillUse)
        self.assertEqual(len(self.b.skill_use_history[-1].exercises),2)


if __name__=='__main__':unittest.main()
