"""5D2B: prove the smallest meaningful native checkpoint remains blocked."""
from pathlib import Path
import random
import sys
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'tests'))
import test_interval_staging as interval_fixtures
from atomic_publication import RNGCursor
from activities import RunAction
from checkpoint_inventory import capture_checkpoint_candidate,validate_checkpoint_candidate


def strings(value):
    if type(value) is str:
        yield value
    elif type(value) is tuple:
        for item in value:
            yield from strings(item)


class TestBoundedClosureBlockers(unittest.TestCase):
    def setUp(self):
        self.f=interval_fixtures.TestIntervalStaging();self.f.setUp();self.world=self.f.world;self.enc=self.f.enc
        self.rng=RNGCursor(random.Random(515).getstate())
        self.enc.enable_transactional_progression(quiescent=True,rng_owner=self.rng)

    def candidate(self,**kwargs):
        return capture_checkpoint_candidate(self.world,self.enc,quiescent=True,
            rng_scope='exclusive_encounter',native_adapters=True,**kwargs)

    def test_initial_native_universe_has_no_field_level_closure_proof(self):
        candidate=self.candidate();result=validate_checkpoint_candidate(self.world,self.enc,candidate,quiescent=True)
        self.assertTrue(result.inventory_validated)
        self.assertIn('bounded_run_spot_closure_verified',{d.code for d in result.diagnostics})
        self.assertIn('native.run-spot-field-closure/4',tuple(strings(candidate.envelope)))
        self.assertFalse(result.closure_validated)
        self.assertFalse(result.portable_schema_defined)
        self.assertFalse(result.restore_verified)
        self.assertIn('semantic_closure_adapter_incomplete',{d.code for d in result.diagnostics})

    def test_committed_batch_and_future_choice_use_portable_choice_descriptor(self):
        first=RunAction(self.world,self.f.a.id,0,1,.5,experience=3)
        simultaneous=RunAction(self.world,self.f.a.id,0,1,.5,experience=4)
        self.enc.schedule_choice((first,simultaneous))
        self.enc.step(1,velocities={self.f.a.id:(1,0,0)})
        inspection=self.enc.inspect_committed()
        from experience import BatchSkillUse
        self.assertTrue(any(type(use) is BatchSkillUse for use in self.f.a.skill_use_history))
        runner=RunAction(self.world,self.f.a.id,1,1,1,experience=7)
        self.enc.schedule_choice((runner,));self.enc.step(1)
        future=self.f.spot(actor=self.f.a,start=4.25)
        choice=self.enc.schedule_choice((future,))
        self.assertEqual(self.enc.get_choice(choice.id).state,'accepted')
        candidate=self.candidate();result=validate_checkpoint_candidate(self.world,self.enc,candidate,quiescent=True)
        codes={item.code for item in result.diagnostics}
        self.assertTrue({'semantic_closure_adapter_incomplete','receipt_rebinding_required'}<=codes)
        self.assertIn('bounded_run_spot_closure_verified',codes)
        self.assertNotIn('native_signature_rebuild_required',codes)
        self.assertIn('universe.accepted-action-choice/1',tuple(strings(candidate.envelope)))
        self.assertFalse(result.closure_validated);self.assertFalse(result.portable_schema_defined);self.assertFalse(result.restore_verified)
        self.assertEqual(self.enc.time,2)
        self.assertEqual(self.enc.get_choice(choice.id).state,'accepted')
        self.assertIn(future.id,self.enc.get_choice(choice.id).action_ids)

    def test_one_boundary_and_optional_spatial_qb_fields_have_closed_descriptor(self):
        from physiology_registry import PhysiologyRegistry,PhysiologyDefinition
        from spatial.geometry import Sphere
        from spatial.occlusion import VisualOcclusion
        for being in (self.f.a,self.f.b,self.f.c):
            being.physiology_id='human@1'
        self.enc.set_physiology_registry(PhysiologyRegistry((
            PhysiologyDefinition('human@1',model='human-r4'),)))
        self.f.a.set_geometry(Sphere(1));self.f.a.set_visual_occlusion(VisualOcclusion(.4))
        self.f.c.__dict__['spatial_state']=None
        action=RunAction(self.world,self.f.a.id,0,1,.5,experience=1)
        self.enc.schedule_choice((action,));self.enc.step(1,velocities={self.f.a.id:(1,0,0)})
        from interval_staging import _read_set
        before=_read_set(self.enc);rng_before=self.rng.state
        candidate=self.candidate()
        codes={d.code for d in candidate.diagnostics}
        self.assertIn('bounded_run_spot_closure_verified',codes)
        self.assertIn('native.run-spot-field-closure/4',tuple(strings(candidate.envelope)))
        self.assertFalse(candidate.closure_validated);self.assertFalse(candidate.portable_schema_defined)
        self.assertEqual(self.enc.time,1)
        self.assertEqual(_read_set(self.enc),before);self.assertEqual(self.rng.state,rng_before)

    def test_run_spot_dictionary_fields_ids_aliases_and_staleness_are_checked(self):
        candidate=self.candidate()
        self.f.a.current.extra_unreviewed='opaque'
        with self.assertRaisesRegex(ValueError,'unknown native fields'):
            self.candidate()
        del self.f.a.current.__dict__['extra_unreviewed']
        self.assertTrue(validate_checkpoint_candidate(self.world,self.enc,candidate,quiescent=True).inventory_validated)

        original=self.f.a.current;self.f.a.__dict__['current']=self.f.b.current
        with self.assertRaises((ValueError,TypeError)):
            self.candidate()
        self.f.a.__dict__['current']=original

        skill_rows=self.world.library.skill_dictionary.skills
        old_skill_rows=tuple(skill_rows.items());skill_rows.pop('run')
        try:
            refused=self.candidate()
            self.assertIn('bounded_run_spot_closure_refused',{d.code for d in refused.diagnostics})
            self.assertNotIn('bounded_run_spot_closure_verified',{d.code for d in refused.diagnostics})
        finally:
            skill_rows.clear();skill_rows.update(old_skill_rows)
        self.assertTrue(validate_checkpoint_candidate(self.world,self.enc,candidate,quiescent=True).inventory_validated)

        self.f.a.original.hit_points+=1
        with self.assertRaisesRegex(ValueError,'stale'):
            validate_checkpoint_candidate(self.world,self.enc,candidate,quiescent=True)

    def test_live_signatures_stay_unchanged_and_unsafe_rng_or_callback_refuses(self):
        action=self.f.spot(actor=self.f.a,start=2)
        choice=self.enc.schedule_choice((action,))
        record=self.enc._choice_book._choices[choice.id]
        signatures=record.signatures
        candidate=self.candidate()
        self.assertIn('bounded_run_spot_closure_verified',{d.code for d in candidate.diagnostics})
        self.assertEqual(record.signatures,signatures)

        from types import SimpleNamespace
        import transactional_progression
        with patch.dict(transactional_progression._BINDINGS,
                {object():SimpleNamespace(encounter=lambda:object(),rng_owner=self.rng)}):
            with self.assertRaisesRegex(ValueError,'shared'):
                self.candidate()

        history=self.f.f.f.history();accounts=[];called=[]
        from history_conversation import AskAboutPastAction
        ask=AskAboutPastAction(self.world,self.f.c.id,self.f.a.id,0,
            episode_time=0,topic='lessons',generate=self.f.f.f.recipe(history),
            received_accounts=accounts)
        self.enc.schedule_choice((ask,))
        ask.generate=lambda *args:called.append('called')
        with self.assertRaises((ValueError,TypeError)):
            self.candidate()
        self.assertEqual(called,[])

    def test_personal_history_reality_is_outside_bounded_run_spot_closure(self):
        self.f.a.begin_personal_history(earliest=-10,known_through=0)
        candidate=self.candidate()
        codes={d.code for d in candidate.diagnostics}
        self.assertIn('bounded_run_spot_closure_refused',codes)
        self.assertNotIn('bounded_run_spot_closure_verified',codes)

    def test_wrong_logical_id_corrupt_definition_and_unsupported_recipients_refuse_local_proof(self):
        from field_observation import BeliefLedger
        candidate=self.candidate()
        entity_id=self.f.a.id;self.f.a.__dict__['id']='wrong-id'
        with self.assertRaises((ValueError,TypeError)):
            self.candidate()
        self.f.a.__dict__['id']=entity_id

        definition_rows=self.world.library.being_dictionary.objects
        old_definition_rows=tuple(definition_rows.items());definition=definition_rows['Human']
        del definition_rows['Human']
        try:
            refused=self.candidate()
            self.assertIn('bounded_run_spot_closure_refused',{d.code for d in refused.diagnostics})
        finally:
            definition_rows.clear();definition_rows.update(old_definition_rows)

        group=self.f.f.f.group();ledger=BeliefLedger(self.f.a.id)
        observe=self.f.f.observe(self.f.a,group,ledger=ledger)
        self.enc.schedule_choice((observe,))
        from checkpoint_adapters import RecipientBinding
        binding=RecipientBinding(self.world,'test','observer-a','in_world_belief_ledger',
                                 (self.f.a.id,),ledger)
        refused=self.candidate(bindings=(binding,))
        self.assertIn('bounded_run_spot_closure_refused',{d.code for d in refused.diagnostics})
        self.assertNotIn('bounded_run_spot_closure_verified',{d.code for d in refused.diagnostics})


if __name__=='__main__':unittest.main()
