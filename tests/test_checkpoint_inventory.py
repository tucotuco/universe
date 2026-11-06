"""5D1 inactive partial inventory: data capture is not checkpoint completeness."""
from dataclasses import replace
import hashlib
from pathlib import Path
import random
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src')]
import test_encounter_inspection as fixtures
import checkpoint_inventory
from checkpoint_inventory import (capture_checkpoint_candidate as capture,
    validate_checkpoint_candidate as validate,CheckpointRejected)
from atomic_publication import publication_boundary,PublicationOwnershipError
from activities import RunAction
from encounter import Encounter
from field_observation import BeliefLedger
from history_conversation import AskAboutPastAction
from melee_defense import MeleeDefense


def strings(value):
    if type(value)is str:yield value
    elif type(value)is tuple:
        for item in value:yield from strings(item)


def tags(candidate):
    return {node[1] for node in candidate.envelope[1][2][1]}


class TestCheckpointInventory(fixtures.InspectionFixture):
    def capture(self,**kwargs):
        return capture(self.world,self.enc,quiescent=True,rng_scope='exclusive_encounter',**kwargs)

    def assert_inventory(self,candidate,valid=True):
        self.assertEqual(validate(self.world,self.enc,candidate,quiescent=True).inventory_validated,valid)
        self.assertFalse(candidate.closure_validated);self.assertFalse(candidate.portable_schema_defined)
        self.assertFalse(candidate.restore_verified)
        self.assertIn('semantic_closure_adapter_incomplete',{d.code for d in candidate.diagnostics})
        with self.assertRaises(CheckpointRejected):validate(self.world,self.enc,candidate,quiescent=True).require_complete()

    def test_compatibility_reads_exact_canonical_historical_input(self):
        path=checkpoint_inventory._AUTHORITATIVE_DECISIONS_PATH
        original=Path.read_bytes
        payload=original(path)
        expected='65539e8eef0e4a56601f0811ca2c1d262c696fbc7372d17335510f73e749ee44'
        self.assertEqual(len(payload),14791)
        self.assertEqual(hashlib.sha256(payload).hexdigest(),expected)

        def historical_digest(compatibility):
            return next(row[1] for row in compatibility
                        if type(row)is tuple and row and row[0]=='authoritative-decisions')

        self.assertEqual(historical_digest(checkpoint_inventory._compatibility()),expected)

        missing_reads=[]
        def missing(path_arg):
            missing_reads.append(path_arg)
            if path_arg==path:raise FileNotFoundError(str(path_arg))
            return original(path_arg)
        with patch.object(Path,'read_bytes',missing):
            with self.assertRaises(FileNotFoundError):checkpoint_inventory._compatibility()
        self.assertIn(path,missing_reads)

        tampered_reads=[]
        def tampered(path_arg):
            tampered_reads.append(path_arg)
            if path_arg==path:return original(path_arg)+b'altered'
            return original(path_arg)
        with patch.object(Path,'read_bytes',tampered):
            altered_digest=historical_digest(checkpoint_inventory._compatibility())
        self.assertIn(path,tampered_reads)
        self.assertNotEqual(altered_digest,expected)

    def test_initial_native_world_inventory_is_coherent_but_explicitly_incomplete(self):
        self.enable();before=self.raw();candidate=self.capture();self.assert_inventory(candidate)
        self.assertEqual(self.raw(),before)
        self.assertIn('universe.Universe',tags(candidate));self.assertIn('being.BeingInstance',tags(candidate))
        self.assertIn('physical_fatigue.PhysicalFatigueState',tags(candidate))

    def test_initial_fractional_start_and_zero_time_choices_are_preserved(self):
        f=fixtures.fixtures.TestIntervalStaging();f.setUp()
        fractional=Encounter(f.world,10,.25,initiated=True)
        # An isolated World is necessary: cross-Encounter inventory is refused.
        f.world._choice_books.remove(f.enc._choice_book);f.world.event_history.pop(f.enc.id)
        f.world.add_event(fractional);fractional.add_being(f.a.id)
        fractional.enable_transactional_progression(quiescent=True,rng_owner=fractional_rng())
        action=RunAction(f.world,f.a.id,.25,1,1);fractional.schedule_action(action)
        c=capture(f.world,fractional,quiescent=True,rng_scope='exclusive_encounter')
        self.assertIn(float(.25).hex(),tuple(strings(c.envelope)))
        self.assertTrue(validate(f.world,fractional,c,quiescent=True).inventory_validated)

    def test_unstarted_whole_choice_and_reservations_are_not_lost(self):
        self.enable();one,two=self.f.spot(start=2),RunAction(self.world,self.c.id,3,1,1)
        view=self.enc.schedule_choice((one,two));c=self.capture();self.assert_inventory(c)
        self.assertIn('action_choice._Accepted',tags(c));self.assertIn('scheduling.PreparedSchedule',tags(c))
        for key in (view.id,one.id,two.id):self.assertIn(key,tuple(strings(c.envelope)))
        self.assertFalse(self.enc.pending_action_list)

    def test_current_planning_changes_stale_old_candidate_after_commit(self):
        self.commit();old=self.capture();action=self.f.spot(start=3);self.enc.schedule_action(action)
        with self.assertRaisesRegex(CheckpointRejected,'stale'):validate(self.world,self.enc,old,quiescent=True)
        new=self.capture();self.assert_inventory(new);self.assertNotEqual(new.content_digest,old.content_digest)

    def test_future_published_member_and_start_samples_are_included(self):
        self.enable();one=RunAction(self.world,self.a.id,.25,1,1);two=self.f.spot(self.c,start=3)
        self.enc.schedule_choice((one,two));self.enc.step(1,velocities={self.a.id:(2,0,0)})
        c=self.capture();self.assert_inventory(c)
        self.assertIn('start_position',tuple(strings(c.envelope)))
        self.assertIn('atomic_publication.PublishedInterval',tags(c));self.assertIn(two.id,tuple(strings(c.envelope)))
        self.assertIn('receipt_rebinding_required',{d.code for d in c.diagnostics})

    def test_multiple_boundaries_and_cancelled_lifecycle_are_captured(self):
        self.enable();action=RunAction(self.world,self.a.id,.25,1,.5,experience=3);self.enc.schedule_action(action);self.enc.step(1)
        self.enc.cancel_action(action.id);self.enc.step(1);c=self.capture();self.assert_inventory(c)
        self.assertIn('observer_proposals.LifecycleEffect',tags(c));self.assertIn('cancelled',tuple(strings(c.envelope)))
        self.assertIn('atomic_publication.TargetIntervalRecord',tags(c))

    def test_objective_subjective_and_external_recipients_explicitly_refuse_completeness(self):
        group=self.f.f.f.group();history=self.f.f.f.history();la,lb=BeliefLedger(self.a.id),BeliefLedger(self.b.id);accounts=[]
        self.enable();one,two=self.f.f.observe(self.a,group,ledger=la),self.f.f.observe(self.b,group,ledger=lb)
        ask=AskAboutPastAction(self.world,self.c.id,self.a.id,0,episode_time=0,topic='lessons',
            generate=self.f.f.f.recipe(history),received_accounts=accounts)
        self.enc.schedule_choice((one,two,ask));self.enc.step(1);before=self.raw();c=self.capture();self.assert_inventory(c,valid=False)
        self.assertEqual(before,self.raw())
        codes={d.code for d in c.diagnostics}
        self.assertTrue({'unbound_external_recipient','unbound_recipient_identity','validator_rehydration_required','conditional_attribute_adapter_missing'}<=codes)
        for tag in ('field_observation.BeliefLedger','realization.CommittedFact','history_conversation.HeardAccount','personal_history.PersonalHistory'):
            self.assertIn(tag,tags(c))
        # Process addresses from observer/Reality snapshots must not survive.
        values=set(strings(c.envelope))
        for obj in (la,lb,accounts,group._composition_reality,history.reality):self.assertNotIn(str(id(obj)),values)

    def test_changed_recipient_and_definitions_make_inventory_stale(self):
        group=self.f.f.f.group();ledger=BeliefLedger(self.a.id);self.enable()
        action=self.f.f.observe(self.a,group,ledger=ledger);self.enc.schedule_action(action);self.enc.step(1)
        c=self.capture();record=ledger._evidence.pop(action.id)
        with self.assertRaises((ValueError,TypeError)):validate(self.world,self.enc,c,quiescent=True)
        ledger._evidence[action.id]=record;c=self.capture()
        self.a.current.hardness+=1
        with self.assertRaises((ValueError,TypeError)):validate(self.world,self.enc,c,quiescent=True)

    def test_deterministic_address_free_projection_has_no_handles(self):
        self.enable();c=self.capture();d=self.capture();self.assertEqual(c.envelope,d.envelope)
        self.assertEqual(c.content_digest,d.content_digest);self.assertEqual(c.diagnostics,d.diagnostics)
        for obj in (self.world,self.enc,self.enc._choice_book,self.world._schedule_lock,self.rng):
            self.assertNotIn(str(id(obj)),set(strings(c.envelope)))
        def closed(v):
            self.assertIn(type(v),(tuple,str,int,bool,type(None)))
            if type(v)is tuple:
                for item in v:closed(item)
        closed(c.envelope)

    def test_copies_and_modified_candidates_are_not_issued(self):
        self.enable();c=self.capture()
        for changed in (replace(c),replace(c,closure_validated=True)):
            with self.assertRaises(CheckpointRejected):validate(self.world,self.enc,changed,quiescent=True)
        object.__setattr__(c,'envelope',('forged',))
        with self.assertRaises(CheckpointRejected):validate(self.world,self.enc,c,quiescent=True)

    def test_root_and_quiescent_ownership_are_required(self):
        self.enable();before=self.raw()
        with self.assertRaises(CheckpointRejected):capture(self.world,self.enc)
        c=self.capture();other=fixtures.InspectionFixture();other.setUp();other.enable()
        with self.assertRaises(CheckpointRejected):validate(other.world,other.enc,c,quiescent=True)
        with self.assertRaises(CheckpointRejected):capture(other.world,self.enc,quiescent=True)
        self.assertEqual(before,self.raw())

    def test_active_fault_emergency_and_lock_order_refuse(self):
        self.enable();before=self.raw()
        with publication_boundary(self.enc,quiescent=True):
            with self.assertRaises(ValueError):self.capture()
        with self.world._schedule_lock:
            with self.assertRaises(PublicationOwnershipError):self.capture()
        with patch('atomic_publication._EMERGENCIES',{1:object()}):
            with self.assertRaises(PublicationOwnershipError):self.capture()
        self.enc.boundary_fault={'error':'fault'}
        with self.assertRaises(ValueError):self.capture()
        self.enc.boundary_fault=None;self.assertEqual(before,self.raw())

    def test_rng_role_state_and_declared_scope_are_distinct(self):
        self.enable();c=self.capture();self.assertIn('caller_cursor',tuple(strings(c.envelope)))
        no_scope=capture(self.world,self.enc,quiescent=True)
        self.assertIn('rng_authority_scope_unbound',{d.code for d in no_scope.diagnostics})
        self.rng.state=random.Random(9).getstate()
        with self.assertRaisesRegex(CheckpointRejected,'stale'):validate(self.world,self.enc,c,quiescent=True)

    def test_module_rng_is_not_silently_assumed_private(self):
        self.enc.enable_transactional_progression(quiescent=True)
        c=capture(self.world,self.enc,quiescent=True)
        self.assertIn('module',tuple(strings(c.envelope)))
        self.assertIn('rng_authority_scope_unbound',{d.code for d in c.diagnostics})
        with self.assertRaises(CheckpointRejected):self.capture()

    def test_unsupported_generator_never_runs(self):
        history=self.f.f.f.history();self.enable();seen=[]
        action=AskAboutPastAction(self.world,self.c.id,self.a.id,0,episode_time=0,topic='lessons',
            generate=self.f.f.f.recipe(history))
        self.enc.schedule_action(action)
        action.generate=lambda *args:seen.append('called')
        with self.assertRaises((ValueError,TypeError)):self.capture()
        self.assertEqual(seen,[])

    def test_unknown_extension_data_is_diagnosed_without_repr(self):
        self.enable();seen=[]
        class Opaque:
            def __repr__(self):seen.append('repr');raise AssertionError
            def __str__(self):seen.append('str');raise AssertionError
        self.a.extra=Opaque();c=self.capture()
        self.assertIn('unsupported_native_value',{d.code for d in c.diagnostics});self.assertFalse(c.closure_validated)
        self.assertFalse(validate(self.world,self.enc,c,quiescent=True).inventory_validated)
        self.assertEqual(seen,[])

    def test_bad_registry_and_missing_receipt_refuse(self):
        self.commit();record=self.enc._atomic_interval_history.pop()
        with self.assertRaises((ValueError,TypeError)):self.capture()
        self.enc._atomic_interval_history.append(record)
        self.world.object_registry.object_instances['duplicate']=self.a
        with self.assertRaises((ValueError,TypeError)):self.capture()

    def test_edited_accepted_declaration_and_missing_reservation_refuse(self):
        f=fixtures.TestCombatInspection();f.setUp();strike=f.f.attack(melee=True)
        f.enc.schedule_action(strike);f.enc._choice_book._reservations=()
        with self.assertRaises((ValueError,TypeError)):capture(f.world,f.enc,quiescent=True,rng_scope='exclusive_encounter')
        self.enable();spot=self.f.spot(start=2);self.enc.schedule_action(spot);spot.end_time+=1
        with self.assertRaises((ValueError,TypeError)):self.capture()

    def test_source_compatibility_and_unrelated_world_objects_are_stale_dependencies(self):
        self.enable();c=self.capture()
        with patch('checkpoint_inventory._compatibility',return_value=('changed-version',)):
            with self.assertRaisesRegex(CheckpointRejected,'stale'):validate(self.world,self.enc,c,quiescent=True)
        extra=self.world.get_object_by_id(self.world.make_object('Rock','Outside encounter'))
        c=self.capture();extra.current.hit_points+=1
        with self.assertRaisesRegex(CheckpointRejected,'stale'):validate(self.world,self.enc,c,quiescent=True)

    def test_simultaneous_skill_exercises_remain_one_target_batch_record(self):
        self.a.record_skill_use(self.world.get_skill_dictionary(),'run',1240,action_id='prior',time=-2)
        self.enable();one,two=(RunAction(self.world,self.a.id,0,1,.5,experience=3),
                              RunAction(self.world,self.a.id,0,1,.5,experience=4))
        self.enc.schedule_choice((one,two));self.enc.step(1,velocities={self.a.id:(1,0,0)})
        c=self.capture();self.assert_inventory(c)
        self.assertIn('experience.BatchSkillUse',tags(c));self.assertIn('frozen_practice.CandidatePracticeUse',tags(c))
        self.assertEqual(len(self.a.skill_use_history[-1].exercises),2)
        self.assertFalse(hasattr(one.resolution,'level_after'))

    def test_equal_contents_new_container_identity_is_stale(self):
        self.enable();c=self.capture();self.a.skill_experience=dict(self.a.skill_experience)
        with self.assertRaisesRegex(CheckpointRejected,'stale'):validate(self.world,self.enc,c,quiescent=True)

    def test_source_change_during_capture_fails_without_live_writes(self):
        self.enable();before=self.raw()
        import checkpoint_inventory
        original=checkpoint_inventory._compatibility
        calls=[]
        def changed():
            calls.append(1)
            return original() if len(calls)==1 else ('different-source',)
        with patch('checkpoint_inventory._compatibility',changed):
            with self.assertRaisesRegex(CheckpointRejected,'changed during read'):self.capture()
        self.assertEqual(before,self.raw())

    def test_capture_uses_no_action_evaluation_or_realization(self):
        self.enable();before=self.raw()
        with (patch('action_evaluation.evaluate_snapshot',side_effect=AssertionError('evaluate')),
              patch('observer_proposals.build_supported_candidate',side_effect=AssertionError('candidate effects')),
              patch('group_observation.sample_group_evidence',side_effect=AssertionError('sample'))):
            c=self.capture();self.assert_inventory(c)
        self.assertEqual(before,self.raw())

    def test_custom_action_and_custom_history_validator_refuse_without_calling(self):
        self.enable();seen=[];action=self.f.spot(start=2)
        self.enc.schedule_action(action)
        from activities import SpotAction
        class Custom(SpotAction):
            def resolve(self,*args):seen.append('resolve')
        action.__class__=Custom
        with self.assertRaises((ValueError,TypeError)):self.capture()
        self.assertEqual(seen,[])
        action.__class__=SpotAction
        history=self.f.f.f.history();history.reality._validators=(lambda *args:seen.append('validator'),)
        with self.assertRaises((ValueError,TypeError)):self.capture()
        self.assertEqual(seen,[])

    def test_qb_and_profile_definitions_are_inventory_inputs_not_settlement(self):
        from physical_fatigue import PhysicalFatigueState
        from physiology_registry import PhysiologyRegistry,PhysiologyDefinition
        self.a.physical_fatigue=PhysicalFatigueState(.75,.5)
        self.enc.set_physiology_registry(PhysiologyRegistry((PhysiologyDefinition('human@1',model='human-r4'),)))
        self.a.physiology_id='human@1';self.b.physiology_id='human@1';self.c.physiology_id='human@1'
        self.enable();before=self.raw();c=self.capture();self.assert_inventory(c)
        self.assertIn('physiology_registry.PhysiologyDefinition',tags(c));self.assertIn(float(.75).hex(),tuple(strings(c.envelope)))
        self.assertEqual(before,self.raw());self.assertEqual(self.a.physical_fatigue.q,.75)

    def test_existing_exports_and_run_remain_refused(self):
        self.enable();c=self.capture();before=self.raw()
        for operation in (lambda:self.world.to_json(),lambda:self.enc.to_json(),lambda:self.enc.run(),
                          lambda:self.world.load_from_file('never-open-this.json')):
            with self.assertRaises((ValueError,TypeError)):operation()
        self.assertEqual(before,self.raw());self.assert_inventory(c)

    def test_terminal_and_multi_encounter_scopes_are_explicitly_refused(self):
        self.enable();self.enc.end_time=1;self.enc.step(1)
        with self.assertRaisesRegex(CheckpointRejected,'terminal'):self.capture()
        self.enc.end_time=None
        Encounter(self.world,10,0,initiated=True)
        with self.assertRaisesRegex(CheckpointRejected,'multi-Encounter'):self.capture()


class TestCombatCheckpointInventory(unittest.TestCase):
    def setUp(self):self.f=fixtures.TestCombatInspection();self.f.setUp()
    def capture(self):return capture(self.f.world,self.f.enc,quiescent=True,rng_scope='exclusive_encounter')

    def test_negative_hp_and_batch_practice_remain_target_owned(self):
        f=self.f;f.b.current.hit_points=12;one,two=f.f.attack(extra=4),f.f.attack(f.f.w2,extra=3)
        f.resolve((one,two),(15,4,15,4));c=self.capture()
        self.assertTrue(validate(f.world,f.enc,c,quiescent=True).inventory_validated)
        self.assertIn('action_settlement.TargetCandidate',tags(c))
        self.assertIn('-3',tuple(strings(c.envelope)));self.assertFalse(c.closure_validated)
        self.assertFalse(any('hp_before' in name for name in vars(one.resolution)))

    def test_fatal_flags_and_defense_associations_are_not_simplified(self):
        f=self.f;one,two=f.f.attack(),f.f.attack(f.f.w2);f.resolve((one,two),(20,20,1,20,20,1))
        c=self.capture();self.assertIn('action_evaluation.FatalEffect',tags(c))
        self.assertEqual(f.b.current.hit_points,-10)
        f=fixtures.TestCombatInspection();f.setUp();strike=f.f.attack(melee=True)
        d1=MeleeDefense(f.enc,f.b.id,f.a.id,kind='dodge',target_action_id=strike.id)
        d2=MeleeDefense(f.enc,f.b.id,f.a.id,kind='dodge',target_action_id=strike.id)
        f.resolve((strike,d1,d2),(20,1,1,20));c=capture(f.world,f.enc,quiescent=True,rng_scope='exclusive_encounter')
        self.assertIn('action_evaluation.DefenseEffect',tags(c));self.assertIn(d1.id,tuple(strings(c.envelope)));self.assertIn(d2.id,tuple(strings(c.envelope)))


def fractional_rng():
    from atomic_publication import RNGCursor
    return RNGCursor(random.Random(3).getstate())


if __name__=='__main__':unittest.main()
