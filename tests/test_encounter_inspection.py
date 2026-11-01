"""5C3B one committed read schema, causal damage and strict consumer barriers."""
from dataclasses import FrozenInstanceError, replace, dataclass
from pathlib import Path
import math
import random
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import test_interval_staging as fixtures
import test_atomic_publication as publication_fixtures
import test_action_settlement as combat_fixtures
from encounter_inspection import inspect_encounter, InspectionRejected, detached
from action_evaluation import UnsupportedEvaluation, _ProvisionalRandom, RandomDraw, DamageEffect, ProtectionEffect
from atomic_publication import RNGCursor, publication_boundary, PublicationOwnershipError, PublicationFailure
from activities import RunAction
from field_observation import BeliefLedger
from history_conversation import AskAboutPastAction
from melee_defense import MeleeDefense
from tactical_duel import TacticalDuel
from ai_duel import AgentDuel


class InspectionFixture(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.TestIntervalStaging(); self.f.setUp()
        self.enc, self.world = self.f.enc, self.f.world
        self.a, self.b, self.c = self.f.a, self.f.b, self.f.c
        self.rng = RNGCursor(random.Random(343).getstate())

    def enable(self):
        self.enc.enable_transactional_progression(quiescent=True, rng_owner=self.rng)

    def raw(self):
        return publication_fixtures.raw_graph(self.world, self.enc), self.rng.state, random.getstate()

    def commit(self):
        self.enable(); action = RunAction(self.world,self.a.id,0,1,.5,experience=1)
        self.enc.schedule_action(action); self.enc.step(1,velocities={self.a.id:(1,0,0)})
        return action


class TestCommittedInspection(InspectionFixture):
    def test_native_read_is_detached_complete_and_does_not_draw_or_mutate(self):
        action = self.commit(); before = self.raw()
        with patch.object(random, 'randint', side_effect=AssertionError('random read')):
            view = self.enc.inspect_committed()
        self.assertEqual(before, self.raw())
        self.assertEqual(view.action(action.id).facts, action.resolution)
        self.assertIsNot(view.action(action.id).facts, action.resolution)
        self.assertEqual(view.boundary, 1); self.assertEqual(view.timeline[0].boundary, 1)
        self.assertEqual(set(view.effects), set(self.enc._atomic_interval_history[0].effect_ids))
        self.assertEqual(view.target(self.a.id).state.projected_hp, self.a.get_hit_points())
        self.assertEqual(view.target_history(self.a.id), (view.target(self.a.id),))
        with self.assertRaises(TypeError): view.actions[action.id] = None
        with self.assertRaises(FrozenInstanceError): view.boundary = 3
        with self.assertRaises(TypeError): view.target(self.a.id).state.practice_state.skill_experience['spot'] = 0

    def test_historical_positions_and_practice_remain_boundary_owned(self):
        self.enable(); one = RunAction(self.world,self.a.id,0,1,.5,experience=1); self.enc.schedule_action(one)
        self.enc.step(1, velocities={self.a.id:(1,0,0)})
        first = self.enc.inspect_committed()
        two = RunAction(self.world,self.a.id,1,1,.5,experience=1); self.enc.schedule_action(two)
        self.enc.step(1, velocities={self.a.id:(1,0,0)})
        old = self.enc.inspect_committed(1); latest = self.enc.inspect_committed()
        self.assertEqual(old.targets, first.targets); self.assertEqual(old.actions, first.actions)
        self.assertEqual(old.latest_boundary, 2); self.assertNotEqual(old.target(self.a.id).position, latest.target(self.a.id).position)
        self.assertEqual(len(latest.target_history(self.a.id)), 2)
        self.assertEqual(tuple(x.boundary for x in latest.timeline), (1,2))
        self.assertEqual(latest.action(one.id).declaration.boundary, 1)
        with self.assertRaises(InspectionRejected): old.action(two.id)

    def test_empty_boundaries_and_integer_selection(self):
        self.enable(); self.enc.step(3)
        view = self.enc.inspect_committed(2)
        self.assertEqual(view.actions, {}); self.assertEqual(view.boundary,2)
        for value in (0,4,1.0,True):
            with self.subTest(value=value), self.assertRaises(InspectionRejected): self.enc.inspect_committed(value)

    def test_legacy_uncommitted_and_foreign_identifiers_refuse(self):
        before = self.raw()
        with self.assertRaises(InspectionRejected): self.enc.inspect_committed()
        self.assertEqual(before,self.raw()); self.enable()
        with self.assertRaises(InspectionRejected): self.enc.inspect_committed()
        self.enc.step(1); view=self.enc.inspect_committed()
        for op in (lambda:view.action('foreign'),lambda:view.target('foreign'),lambda:view.target_history('foreign')):
            with self.assertRaises(InspectionRejected): op()

    def test_receipt_must_be_native_issued_and_owned(self):
        self.commit(); receipt=self.enc._atomic_interval_history[0]
        self.assertEqual(self.enc.inspect_committed(receipt=receipt).boundary,1)
        for forged in (replace(receipt),replace(receipt,committed=False),replace(receipt,encounter_id='other')):
            before=self.raw()
            with self.assertRaises(InspectionRejected): self.enc.inspect_committed(receipt=forged)
            self.assertEqual(before,self.raw())
        with self.assertRaises(InspectionRejected): self.enc.inspect_committed(2,receipt=receipt)
        self.enc._atomic_interval_history[0]=replace(receipt)
        with self.assertRaises(InspectionRejected): self.enc.inspect_committed()

    def test_receipt_tampering_is_detected(self):
        self.commit(); receipt=self.enc._atomic_interval_history[0]
        object.__setattr__(receipt,'effect_ids',())
        before=self.raw()
        with self.assertRaises(InspectionRejected): self.enc.inspect_committed()
        self.assertEqual(before,self.raw())

    def test_target_history_container_and_record_identity_are_verified(self):
        self.commit(); storage=self.a._atomic_target_history
        self.a._atomic_target_history=list(storage)
        with self.assertRaisesRegex(InspectionRejected,'history identity'): self.enc.inspect_committed()
        self.a._atomic_target_history=storage; storage[0]=replace(storage[0])
        with self.assertRaisesRegex(InspectionRejected,'history/provenance'): self.enc.inspect_committed()

    def test_live_drift_and_action_resolution_are_not_silently_used(self):
        action=self.commit(); hp=self.a.current.hit_points; self.a.current.hit_points+=1
        with self.assertRaisesRegex(InspectionRejected,'HP change'): self.enc.inspect_committed()
        self.a.current.hit_points=hp; action.resolution=replace(action.resolution,outcome='invented')
        with self.assertRaisesRegex(InspectionRejected,'result changed'): self.enc.inspect_committed()

    def test_opaque_payload_does_not_call_extension_hooks(self):
        seen=[]
        @dataclass(frozen=True)
        class Opaque:
            value:int=1
            def __repr__(self): seen.append('repr'); raise AssertionError
        with self.assertRaises(UnsupportedEvaluation): detached(Opaque())
        self.assertEqual(seen,[])

    def test_busy_ownership_progression_fault_and_emergency_refuse(self):
        self.commit(); before=self.raw()
        with publication_boundary(self.enc,quiescent=True):
            with self.assertRaisesRegex(InspectionRejected,'ownership'): self.enc.inspect_committed()
        from transactional_progression import _BINDINGS
        binding=_BINDINGS[id(self.enc)]; binding.running.acquire()
        try:
            with self.assertRaisesRegex(InspectionRejected,'progression'): self.enc.inspect_committed()
        finally:binding.running.release()
        self.assertEqual(before,self.raw())
        self.enc.boundary_fault={'error':'fault'}
        with self.assertRaisesRegex(InspectionRejected,'faulted'): self.enc.inspect_committed()
        self.enc.boundary_fault=None
        with patch('atomic_publication._EMERGENCIES',{1:object()}):
            with self.assertRaises(PublicationOwnershipError): self.enc.inspect_committed()

    def test_facade_read_adapters_share_schema_without_converting_ownership(self):
        self.commit(); before=self.raw(); expected=self.enc.inspect_committed()
        self.assertEqual(TacticalDuel.inspect_encounter(self.enc),expected)
        self.assertEqual(AgentDuel.inspect_encounter(self.enc),expected)
        self.assertEqual(before,self.raw())
        game=TacticalDuel(seed=17); game.encounter=self.enc
        with self.assertRaises(ValueError): game.state()
        with self.assertRaises(ValueError): game.choose('wait')
        with self.assertRaises(ValueError): self.enc.run()
        self.assertEqual(before,self.raw())

    def test_shared_objective_distinct_observers_beliefs_and_history_accounts(self):
        group=self.f.f.f.group(); history=self.f.f.f.history()
        la,lb=BeliefLedger(self.a.id),BeliefLedger(self.b.id); accounts=[]
        self.enable()
        one,two=self.f.f.observe(self.a,group,ledger=la),self.f.f.observe(self.b,group,ledger=lb)
        ask=AskAboutPastAction(self.world,self.c.id,self.a.id,0,episode_time=0,topic='lessons',
            generate=self.f.f.f.recipe(history),received_accounts=accounts)
        self.enc.schedule_choice((one,two,ask)); self.enc.step(1)
        before=self.raw(); view=self.enc.inspect_committed(); self.assertEqual(before,self.raw())
        truth=view.objective[group.id]
        self.assertEqual(len(truth.facts),4)
        self.assertTrue(all(not f.established_before for f in truth.facts.values()))
        self.assertTrue(all(set(u.consumed_by)=={one.id,two.id} for u in view.objective_use if u.subject_id==group.id))
        a=view.target(self.a.id).state.observer_state; b=view.target(self.b.id).state.observer_state
        self.assertNotEqual(a.observations[one.id].reported_position,b.observations[two.id].reported_position)
        self.assertEqual(len(view.recipients),3); self.assertEqual(len(accounts),1)
        self.assertTrue(view.target(self.c.id).state.observer_state.heard_accounts)
        self.enc.step(1); self.assertEqual(self.enc.inspect_committed(1).recipients,view.recipients)

    def test_reused_objective_facts_are_labeled_established(self):
        group=self.f.f.f.group(); group.counts(); self.enable()
        action=self.f.f.observe(self.a,group); self.enc.schedule_action(action); self.enc.step(1)
        view=self.enc.inspect_committed()
        self.assertTrue(all(f.established_before for f in view.objective[group.id].facts.values()))

    def test_practice_two_exercises_one_target_transition(self):
        self.a.record_skill_use(self.world.get_skill_dictionary(),'run',1240,action_id='prior',time=-2)
        self.enable(); one,two=(RunAction(self.world,self.a.id,0,1,.5,experience=3),
                              RunAction(self.world,self.a.id,0,1,.5,experience=4))
        self.enc.schedule_choice((one,two)); self.enc.step(1,velocities={self.a.id:(1,0,0)}); view=self.enc.inspect_committed()
        practice=view.target(self.a.id).state.practice_state
        self.assertEqual(len(practice.exercises),2); self.assertEqual(len(practice.transitions),1)
        self.assertEqual({e.action_id for e in practice.exercises},{one.id,two.id})
        self.assertFalse(hasattr(view.action(one.id),'level_after'))

    def test_fractional_timing_and_cancelled_action_remain_readable(self):
        self.enable(); one=RunAction(self.world,self.a.id,.25,1,.5,experience=1); self.enc.schedule_action(one)
        self.enc.step(1); self.assertIsNone(one.resolution)
        self.enc.cancel_action(one.id); self.enc.step(1)
        view=self.enc.inspect_committed(); action=view.action(one.id)
        self.assertEqual(action.declaration.start,.25); self.assertEqual(action.declaration.nominal_end,1.25)
        self.assertEqual(action.lifecycle.status,'cancelled'); self.assertEqual(action.facts.outcome,'interrupted')
        self.assertEqual(action.damage_by_target,{})


    def test_read_from_every_publication_phase_refuses_without_mutation(self):
        from atomic_publication import _WritePlan, PHASES
        self.enable(); self.enc.schedule_action(RunAction(self.world,self.a.id,0,1,.5,experience=1))
        apply = _WritePlan.apply_phase; seen=[]
        def inspect_phase(plan, phase):
            apply(plan, phase); before=self.raw()
            with self.assertRaises(InspectionRejected): self.enc.inspect_committed()
            self.assertEqual(before,self.raw());seen.append(phase)
        with patch.object(_WritePlan,'apply_phase',inspect_phase): self.enc.step(1)
        self.assertEqual(tuple(seen),PHASES)
        self.assertEqual(self.enc.inspect_committed().boundary,1)

    def test_failed_second_commit_preserves_first_and_recovers_deterministically(self):
        import atomic_publication
        self.commit(); receipt=self.enc._atomic_interval_history[0]
        before=self.raw(); publish=atomic_publication.publish_interval_candidate
        def fail(*args,**kw): return publish(*args,**kw,_fail_after='mark_committed')
        with patch('atomic_publication.publish_interval_candidate',fail):
            with self.assertRaises(PublicationFailure) as caught:self.enc.step(1)
        self.assertEqual(before,self.raw());self.assertIs(self.enc._atomic_interval_history[0],receipt)
        self.assertEqual(len(self.enc._atomic_interval_history),1)
        with self.assertRaises(InspectionRejected): self.enc.inspect_committed(1)
        self.enc.recover_transactional_progression(caught.exception.recovery_token)
        old=self.enc.inspect_committed(1); self.enc.step(1)
        self.assertEqual(old.targets,self.enc.inspect_committed(1).targets)
        self.assertEqual(self.enc.inspect_committed().boundary,2)

    def test_coordinated_read_waits_for_complete_external_access(self):
        import threading
        from atomic_publication import coordinated_access
        self.commit();entered=threading.Event();done=threading.Event();results=[]
        def read():
            entered.set()
            try:results.append(self.enc.inspect_committed())
            except BaseException as exc:results.append(exc)
            finally:done.set()
        with coordinated_access(self.world):
            thread=threading.Thread(target=read);thread.start()
            self.assertTrue(entered.wait(5));self.assertFalse(done.wait(.03))
        self.assertTrue(done.wait(5));thread.join(5)
        self.assertEqual(results[0].boundary,1)

    def test_inverted_schedule_lock_and_foreign_owner_refuse(self):
        self.commit();before=self.raw()
        with self.world._schedule_lock:
            with self.assertRaises(PublicationOwnershipError):self.enc.inspect_committed()
        event=self.world.event_history.pop(self.enc.id)
        with self.assertRaisesRegex(InspectionRejected,'ownership'):self.enc.inspect_committed()
        self.world.event_history[event.id]=event
        # Registry order is caller-mutated here; the reader itself remains pure.
        self.assertEqual(self.enc.inspect_committed().boundary,1)

    def test_changed_evidence_and_skill_use_history_refuse(self):
        group=self.f.f.f.group();ledger=BeliefLedger(self.a.id);self.enable()
        action=self.f.f.observe(self.a,group,ledger=ledger)
        self.enc.schedule_action(action);self.enc.step(1)
        old=self.enc.inspect_committed();record=ledger._evidence.pop(action.id)
        with self.assertRaises(ValueError):self.enc.inspect_committed()
        ledger._evidence[action.id]=record
        self.assertEqual(self.enc.inspect_committed(),old)
        self.a.skill_use_history.clear()
        with self.assertRaisesRegex(InspectionRejected,'skill-use history'):self.enc.inspect_committed()

    def test_pending_fractional_run_status_and_no_movement_outcome(self):
        self.enable();run=RunAction(self.world,self.a.id,.25,1,1)
        self.enc.schedule_action(run);self.enc.step(1);view=self.enc.inspect_committed()
        self.assertIn(run.id,view.schedule.pending)
        with self.assertRaises(InspectionRejected):view.action(run.id)
        self.enc.step(1);completed=self.enc.inspect_committed().action(run.id)
        self.assertEqual(completed.facts.outcome,'no_movement')
        self.assertEqual((completed.declaration.start,completed.declaration.nominal_end),(.25,1.25))

    def test_historical_belief_does_not_use_later_evidence(self):
        group=self.f.f.f.group();ledger=BeliefLedger(self.a.id);self.enable()
        first=self.f.f.observe(self.a,group,ledger=ledger)
        self.enc.schedule_action(first);self.enc.step(1);old=self.enc.inspect_committed()
        second=self.f.f.observe(self.a,group,ledger=ledger)
        second.start_time=1;second.end_time+=1
        self.enc.schedule_action(second);self.enc.step(1)
        self.assertEqual(self.enc.inspect_committed(1).recipients,old.recipients)
        projection=next(iter(self.enc.inspect_committed().recipients.values()))
        self.assertEqual(len(projection.evidence),2)
        self.assertEqual(len(next(iter(old.recipients.values())).evidence),1)
        self.assertTrue(all(f.established_before and f.revision==1 for f in self.enc.inspect_committed().objective[group.id].facts.values()))

    def test_missing_old_receipt_and_unreceipted_history_are_rejected(self):
        self.commit();self.enc.step(1);first=self.enc._atomic_interval_history.pop(0)
        with self.assertRaisesRegex(InspectionRejected,'initial'):self.enc.inspect_committed()
        self.enc._atomic_interval_history.insert(0,first)
        row=self.a._atomic_target_history[-1]
        self.a._atomic_target_history.append(replace(row,boundary=42))
        with self.assertRaisesRegex(InspectionRejected,'unreceipted Target history'):self.enc.inspect_committed()

    def test_action_declaration_and_unsupported_family_cannot_be_hidden(self):
        action=self.commit();old=action.actor_id;action.actor_id=self.b.id
        with self.assertRaisesRegex(InspectionRejected,'declaration'):self.enc.inspect_committed()
        action.actor_id=old
        from activities import SpotAction
        class CustomSpot(SpotAction):
            def resolve(self,*args):raise AssertionError('resolver called')
        action.__class__=CustomSpot
        with self.assertRaises(UnsupportedEvaluation):self.enc.inspect_committed()

    def test_native_reference_replacement_is_detected_before_display(self):
        self.commit();obj=self.world.object_registry.object_instances.pop(self.a.id)
        with self.assertRaises((ValueError,TypeError)):self.enc.inspect_committed()
        self.world.object_registry.object_instances[obj.id]=obj
        import copy
        current=obj.current;obj.current=copy.copy(current)
        with self.assertRaisesRegex(InspectionRejected,'identity'):self.enc.inspect_committed()
        obj.current=current
        self.assertEqual(self.enc.inspect_committed().boundary,1)

    def test_unsafe_objective_storage_is_refused_without_callbacks(self):
        group=self.f.f.f.group();self.enable();action=self.f.f.observe(self.a,group)
        self.enc.schedule_action(action);self.enc.step(1);seen=[]
        class Unsafe(dict):
            def get(self,*args):seen.append('get');raise AssertionError('unsafe get')
        group._composition_reality._records=Unsafe(group._composition_reality._records)
        with self.assertRaises(InspectionRejected):self.enc.inspect_committed()
        self.assertEqual(seen,[])

    def test_opaque_history_identity_is_rejected_without_equality(self):
        self.commit();seen=[]
        class Unsafe:
            def __eq__(self,other):seen.append('eq');raise AssertionError('unsafe equality')
        row=self.a._atomic_target_history[0]
        object.__setattr__(row,'encounter_id',Unsafe())
        with self.assertRaises(UnsupportedEvaluation):self.enc.inspect_committed()
        self.assertEqual(seen,[])

    def test_reused_process_identity_does_not_inherit_foreign_fault(self):
        import weakref
        from atomic_publication import _FailureState
        self.commit();other=fixtures.TestIntervalStaging();other.setUp()
        foreign=_FailureState(weakref.ref(other.enc),None,{},'other-fault',True)
        with patch('atomic_publication._FAULTS',{id(self.enc):foreign}):
            self.assertEqual(self.enc.inspect_committed().boundary,1)
        own=_FailureState(weakref.ref(self.enc),None,{},'own-fault',True)
        with patch('atomic_publication._FAULTS',{id(self.enc):own}):
            with self.assertRaises(InspectionRejected):self.enc.inspect_committed()

    def test_objective_fact_provenance_and_cache_are_verified(self):
        group=self.f.f.f.group();self.enable();action=self.f.f.observe(self.a,group)
        self.enc.schedule_action(action);self.enc.step(1)
        ledger=group._composition_reality;key=next(iter(ledger._records));original=ledger._records[key]
        for changed in (replace(original,origin='forged'),replace(original,revision=99)):
            ledger._records[key]=changed
            with self.assertRaisesRegex(InspectionRejected,'objective fact changed'):self.enc.inspect_committed()
        ledger._records[key]=original;old=dict(group._counts);group._counts['humans']+=1
        with self.assertRaisesRegex(InspectionRejected,'count cache'):self.enc.inspect_committed()
        group._counts.clear();group._counts.update(old)
        self.assertEqual(self.enc.inspect_committed().boundary,1)

    def test_future_accepted_choice_does_not_rewrite_committed_schedule(self):
        self.commit();old=self.enc.inspect_committed()
        self.enc.schedule_choice((self.f.spot(start=2),))
        self.assertEqual(self.enc.inspect_committed(),old)

    def test_unsafe_observer_hooks_and_legacy_exports_remain_refused(self):
        action=self.commit();before=self.raw()
        for operation in (lambda:action.resolve(10),lambda:self.enc.resolve_actions(),
                          lambda:self.enc.to_json(),lambda:self.world.to_json()):
            with self.assertRaises((ValueError,TypeError)):operation()
            self.assertEqual(before,self.raw())

    def test_observation_reads_do_not_sample_realize_or_learn(self):
        group=self.f.f.f.group();ledger=BeliefLedger(self.a.id);self.enable()
        action=self.f.f.observe(self.a,group,ledger=ledger)
        self.enc.schedule_action(action);self.enc.step(1)
        # Patch free sampling/evaluation/realization entry points, rather than
        # supported class methods (which deliberately trigger adapter refusal).
        with (patch('observer_proposals.build_supported_candidate',side_effect=AssertionError('evaluate')),
              patch('group_observation.sample_group_evidence',side_effect=AssertionError('sample'))):
            before=self.raw();view=self.enc.inspect_committed();self.assertEqual(before,self.raw())
        self.assertTrue(view.target(self.a.id).state.observer_state.observations)


class TestCombatInspection(unittest.TestCase):
    def setUp(self):
        self.f=combat_fixtures.TestActionSettlement();self.f.setUp()
        self.enc,self.world,self.a,self.b=self.f.enc,self.f.world,self.f.a,self.f.b
        self.enc.enable_transactional_progression(quiescent=True,rng_owner=RNGCursor(random.Random(4).getstate()))

    def resolve(self,actions,rolls):
        self.enc.schedule_choice(actions); values=iter(rolls)
        def roll(rng,dice):
            value=next(values);rng.trace.append(RandomDraw(rng.action_id,dice,int(dice[2:].split('+')[0]),value));return value
        with patch.object(_ProvisionalRandom,'roll',roll):self.enc.step(max(math.ceil(a.end_time) for a in actions))
        return self.enc.inspect_committed()

    def test_h12_damage8_and7_are_causal_not_hp_differences(self):
        self.b.current.hit_points=12
        one,two=self.f.attack(extra=4),self.f.attack(self.f.w2,extra=3)
        view=self.resolve((one,two),(15,4,15,4)); target=view.target(self.b.id)
        self.assertEqual(target.state.projected_hp,-3);self.assertEqual(target.state.actual_damage,15)
        self.assertEqual(sum(view.action(one.id).damage_by_target[self.b.id].values()),8)
        self.assertEqual(sum(view.action(two.id).damage_by_target[self.b.id].values()),7)
        self.assertEqual(sum(target.damage_by_action[one.id].values()),8)
        self.assertFalse(any('hp' in name for name in vars(view.action(one.id))))
        old=self.enc.inspect_committed(); self.enc.step(1)
        self.assertEqual(self.enc.inspect_committed(old.boundary).target(self.b.id),target)

    def test_earlier_hp_is_not_replaced_by_current_hp_after_later_damage(self):
        one=self.f.attack();first=self.resolve((one,),(15,4));boundary=self.enc.time
        two=self.f.attack();two.start_time=boundary;two.end_time+=boundary
        self.enc.schedule_action(two);values=iter((15,4))
        def roll(rng,dice):
            value=next(values);rng.trace.append(RandomDraw(rng.action_id,dice,int(dice[2:].split('+')[0]),value));return value
        with patch.object(_ProvisionalRandom,'roll',roll):self.enc.step(math.ceil(two.end_time)-boundary)
        old=self.enc.inspect_committed(first.boundary);latest=self.enc.inspect_committed()
        self.assertEqual(old.target(self.b.id).state.projected_hp,96)
        self.assertEqual(latest.target(self.b.id).state.projected_hp,92)
        self.assertEqual(old.targets,first.targets)

    def test_unavailable_instrument_is_a_committed_no_damage_outcome(self):
        strike=self.f.attack(melee=True);self.enc.schedule_action(strike)
        self.a.current.body_parts['right hand']=None
        self.enc.step(math.ceil(strike.end_time));view=self.enc.inspect_committed()
        self.assertEqual(view.action(strike.id).facts.outcome,'weapon_unavailable')
        self.assertEqual(view.action(strike.id).damage_by_target,{})

    def test_multiple_fatals_floor_is_separate_from_damage(self):
        one,two=self.f.attack(),self.f.attack(self.f.w2)
        view=self.resolve((one,two),(20,20,1,20,20,1)); t=view.target(self.b.id)
        self.assertEqual(t.state.projected_hp,-10);self.assertEqual(t.state.actual_damage,0)
        self.assertEqual(t.fatal_floor_reduction,110);self.assertEqual(len(t.state.fatal_effect_ids),2)
        self.assertEqual(view.action(one.id).damage_by_target,{})
        self.assertEqual(view.action(one.id).fatal_targets,(self.b.id,))

    def test_fatal_and_actual_damage_stay_separate(self):
        one,two=self.f.attack(),self.f.attack(self.f.w2)
        view=self.resolve((one,two),(20,20,1,15,4));t=view.target(self.b.id)
        self.assertEqual((t.state.projected_hp,t.state.actual_damage,t.fatal_floor_reduction),(-14,4,110))
        self.assertEqual(sum(view.action(two.id).damage_by_target[self.b.id].values()),4)

    def test_negative_hp_fatal_has_no_extra_floor_damage(self):
        self.b.current.hit_points=-15
        one=self.f.attack();view=self.resolve((one,),(20,20,1))
        self.assertEqual(view.target(self.b.id).fatal_floor_reduction,0)
        self.assertEqual(view.target(self.b.id).state.projected_hp,-15)

    def test_multiple_defenses_have_every_outcome_practice_and_association(self):
        strike=self.f.attack(melee=True)
        one=MeleeDefense(self.enc,self.b.id,self.a.id,kind='dodge',target_action_id=strike.id)
        two=MeleeDefense(self.enc,self.b.id,self.a.id,kind='dodge',target_action_id=strike.id)
        view=self.resolve((strike,one,two),(20,1,1,20))
        defenses=view.action(strike.id).defenses
        self.assertEqual(len(defenses),2);self.assertEqual({d.success for d in defenses},{False,True})
        self.assertEqual({d.source_action_id for d in defenses},{one.id,two.id})
        self.assertEqual(view.action(strike.id).damage_by_target,{})
        self.assertEqual(len(view.target(self.b.id).state.practice_state.exercises),2)

    def test_armor_negative_and_protection_not_double_counted(self):
        aid=self.world.make_armor_for_being(self.b.id,'Leather armor','Armor');self.world.armor_being(self.b.id,aid)
        self.world.get_object_by_id(aid).current.hit_points=1
        one,two=self.f.attack(extra=10),self.f.attack(self.f.w2,extra=10)
        view=self.resolve((one,two),(15,4,15,4));target=view.target(aid)
        self.assertLess(target.state.projected_hp,0)
        self.assertTrue(any(type(r.effect) is ProtectionEffect for r in target.state.incoming))
        self.assertEqual(target.state.actual_damage,sum(sum(c.values()) for c in target.damage_by_action.values()))

    def test_shield_can_be_negative_and_has_separate_causal_damage(self):
        sid=self.world.make_weapon_for_being(self.b.id,'Small shield','Shield');self.world.arm_being(self.b.id,sid,'shield hand')
        self.world.get_object_by_id(sid).current.hit_points=1
        one,two=self.f.attack(),self.f.attack(self.f.w2)
        view=self.resolve((one,two),(15,4,1,15,4,1));t=view.target(sid)
        self.assertEqual(t.state.projected_hp,-7);self.assertEqual(t.state.actual_damage,8)
        self.assertEqual(sum(view.action(one.id).damage_by_target[sid].values()),4)

    def test_ordinary_miss_and_unavailable_instrument(self):
        one=self.f.attack();view=self.resolve((one,),(2,))
        self.assertEqual(view.action(one.id).damage_by_target,{})
        self.assertEqual(view.action(one.id).facts.outcome,'miss')

    def test_handoff_release_is_committed_but_next_result_is_not_invented(self):
        old=self.f.attack(melee=True);boundary=math.ceil(old.end_time)
        new=self.f.attack(melee=True);new.start_time=boundary;new.end_time+=boundary
        view=self.resolve((old,new),(15,4,15,4))
        from observer_proposals import ReservationReleaseEffect
        self.assertTrue(any(type(row.effect) is ReservationReleaseEffect for row in view.action(old.id).effects))
        self.assertEqual(view.action(new.id).declaration.start,boundary)


if __name__=='__main__':unittest.main()
