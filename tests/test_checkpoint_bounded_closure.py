"""5D2B: prove the smallest meaningful native checkpoint remains blocked."""
from pathlib import Path
import random
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'tests'))
import test_interval_staging as interval_fixtures
from atomic_publication import RNGCursor
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

    def candidate(self):
        return capture_checkpoint_candidate(self.world,self.enc,quiescent=True,
            rng_scope='exclusive_encounter',native_adapters=True)

    def test_initial_native_universe_has_no_field_level_closure_proof(self):
        candidate=self.candidate();result=validate_checkpoint_candidate(self.world,self.enc,candidate,quiescent=True)
        self.assertTrue(result.inventory_validated)
        self.assertFalse(result.closure_validated)
        self.assertFalse(result.portable_schema_defined)
        self.assertFalse(result.restore_verified)
        self.assertIn('semantic_closure_adapter_incomplete',{d.code for d in result.diagnostics})

    def test_committed_batch_and_future_choice_use_portable_choice_descriptor(self):
        first=self.f.spot(actor=self.f.a,start=.25)
        simultaneous=self.f.spot(actor=self.f.a,start=.25)
        self.enc.schedule_choice((first,simultaneous))
        self.enc.step(2)
        inspection=self.enc.inspect_committed()
        from experience import BatchSkillUse
        self.assertTrue(any(type(use) is BatchSkillUse for use in self.f.a.skill_use_history))
        future=self.f.spot(actor=self.f.a,start=4.25)
        choice=self.enc.schedule_choice((future,))
        self.assertEqual(self.enc.get_choice(choice.id).state,'accepted')
        candidate=self.candidate();result=validate_checkpoint_candidate(self.world,self.enc,candidate,quiescent=True)
        codes={item.code for item in result.diagnostics}
        self.assertTrue({'semantic_closure_adapter_incomplete','receipt_rebinding_required'}<=codes)
        self.assertNotIn('native_signature_rebuild_required',codes)
        self.assertIn('universe.accepted-action-choice/1',tuple(strings(candidate.envelope)))
        self.assertFalse(result.closure_validated);self.assertFalse(result.portable_schema_defined);self.assertFalse(result.restore_verified)
        self.assertEqual(self.enc.time,2)
        self.assertEqual(self.enc.get_choice(choice.id).state,'accepted')
        self.assertIn(future.id,self.enc.get_choice(choice.id).action_ids)


if __name__=='__main__':unittest.main()
