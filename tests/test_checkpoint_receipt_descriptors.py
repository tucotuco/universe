"""Inactive 5D2C2 portable descriptors; no receipt reissuance or restore."""
from dataclasses import replace
from pathlib import Path
import random
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'tests'))

from activities import RunAction,SpotAction
from atomic_publication import RNGCursor
from checkpoint_receipts import (DESCRIPTOR_SCHEMA,ReceiptDescriptorRejected,
    describe_committed_receipt_chain,plan_receipt_rebinding,validate_receipt_descriptor)


def walk(value):
    yield value
    if type(value) is tuple:
        for item in value:yield from walk(item)


class ReceiptFixture(unittest.TestCase):
    def setUp(self):
        from test_interval_staging import TestIntervalStaging
        self.f=TestIntervalStaging();self.f.setUp()
        self.world,self.enc=self.f.world,self.f.enc
        self.rng=RNGCursor(random.Random(734).getstate())
        self.enc.enable_transactional_progression(quiescent=True,rng_owner=self.rng)

    def capture(self):
        return describe_committed_receipt_chain(self.world,self.enc,quiescent=True,
            rng_scope='exclusive_encounter')

    def one_boundary(self):
        first=RunAction(self.world,self.f.a.id,0,1,.5,experience=3)
        self.enc.schedule_choice((first,));self.enc.step(1)
        return first

    def two_boundaries_with_future(self):
        first=RunAction(self.world,self.f.a.id,0,1,.5,experience=3)
        second=RunAction(self.world,self.f.a.id,0,1,.5,experience=4)
        self.enc.schedule_choice((first,second));self.enc.step(1,velocities={self.f.a.id:(1,0,0)})
        runner=RunAction(self.world,self.f.a.id,1,1,1,experience=7)
        self.enc.schedule_choice((runner,));self.enc.step(1)
        future=SpotAction(self.world,self.f.c.id,self.f.b.id,3.25)
        self.enc.schedule_choice((future,))
        return first,second,runner,future


class TestPortableCommittedReceipts(ReceiptFixture):
    def test_one_boundary_is_portable_and_authenticated_without_advancing_rng(self):
        self.one_boundary();before=self.rng.state
        descriptor=self.capture()
        self.assertEqual(descriptor.schema,DESCRIPTOR_SCHEMA)
        self.assertEqual(tuple(row.boundary for row in descriptor.receipts),(1,))
        self.assertEqual(descriptor,self.capture())
        self.assertEqual(self.rng.state,before)
        data=descriptor.to_data()
        self.assertTrue(all(x is None or type(x) in (str,int,bool,tuple) for x in walk(data)))
        self.assertNotIn('target_anchors',tuple(walk(data)))
        self.assertNotIn('action_anchors',tuple(walk(data)))

    def test_two_boundaries_preserve_batch_practice_future_choice_and_rebinding_obligations(self):
        first,second,runner,future=self.two_boundaries_with_future()
        descriptor=self.capture()
        self.assertEqual([row.boundary for row in descriptor.receipts],[1,2])
        self.assertEqual(len(descriptor.accepted_future_choices),1)
        self.assertIn(future.id,descriptor.accepted_future_choices[0].action_ids)
        data=descriptor.to_data()
        self.assertIn('practice.batch-use/1',tuple(walk(data)))
        self.assertIn(first.id,tuple(walk(data)));self.assertIn(second.id,tuple(walk(data)))
        plan=plan_receipt_rebinding(descriptor)
        self.assertEqual(plan.boundaries,(1,2))
        self.assertIn(future.id,plan.action_ids or plan.entity_ids)
        self.assertIn(self.f.b.id,plan.entity_ids)
        self.assertIn('authenticate-and-register-fresh-receipts-only-after-complete-validation',plan.steps)
        self.assertTrue(validate_receipt_descriptor(descriptor))
        self.assertEqual(self.enc.time,2)
        self.assertTrue(any(record.view.state=='accepted' and future.id in record.view.action_ids
                            for record in self.enc._choice_book._choices.values()))

    def test_missing_out_of_order_and_duplicate_live_receipts_refuse(self):
        self.two_boundaries_with_future()
        history=self.enc.__dict__['_atomic_interval_history'];original=list(history)
        try:
            history[:] = []
            with self.assertRaises(ReceiptDescriptorRejected):self.capture()
            history[:] = list(reversed(original))
            with self.assertRaises(ReceiptDescriptorRejected):self.capture()
            history[:] = original+[original[-1]]
            with self.assertRaises(ReceiptDescriptorRejected):self.capture()
        finally:history[:]=original

    def test_forged_issuance_and_stale_target_storage_refuse(self):
        self.one_boundary()
        import atomic_publication
        receipt=self.enc.__dict__['_atomic_interval_history'][0]
        issued=atomic_publication._COMMITTED_RECEIPTS.pop(id(receipt))
        try:
            with self.assertRaises(ReceiptDescriptorRejected):self.capture()
        finally:atomic_publication._COMMITTED_RECEIPTS[id(receipt)]=issued
        storage=self.f.a.__dict__['_atomic_target_history']
        self.f.a.__dict__['_atomic_target_history']=list(storage)
        try:
            with self.assertRaises(ReceiptDescriptorRejected):self.capture()
        finally:self.f.a.__dict__['_atomic_target_history']=storage

    def test_ambiguous_rng_scope_and_shared_cursor_refuse(self):
        self.one_boundary()
        with self.assertRaisesRegex(ReceiptDescriptorRejected,'exclusive_encounter'):
            describe_committed_receipt_chain(self.world,self.enc,quiescent=True)
        import transactional_progression
        with patch.dict(transactional_progression._BINDINGS,{object():SimpleNamespace(rng_owner=self.rng)}):
            with self.assertRaisesRegex(ReceiptDescriptorRejected,'shared'):
                self.capture()

    def test_descriptor_closed_fields_versions_links_and_target_history(self):
        self.two_boundaries_with_future();descriptor=self.capture();row=descriptor.receipts[0]
        with self.assertRaisesRegex(ReceiptDescriptorRejected,'version'):
            validate_receipt_descriptor(replace(descriptor,schema='universe.committed-native-receipt-chain/99'))
        action=replace(row.actions[0],adapter='native.unknown/1')
        with self.assertRaisesRegex(ReceiptDescriptorRejected,'Action adapter'):
            validate_receipt_descriptor(replace(descriptor,receipts=(replace(row,actions=(action,)+row.actions[1:]),descriptor.receipts[1])))
        with self.assertRaisesRegex(ReceiptDescriptorRejected,'Target-owned'):
            validate_receipt_descriptor(replace(descriptor,receipts=(replace(row,targets=()),descriptor.receipts[1])))
        effect_id,payload=row.effects[0]
        with self.assertRaisesRegex(ReceiptDescriptorRejected,'effect version'):
            validate_receipt_descriptor(replace(descriptor,receipts=(replace(row,effects=( (effect_id,('effect.unknown/1',payload[1])),)+row.effects[1:]),descriptor.receipts[1])))
        action=row.actions[0]
        with self.assertRaisesRegex(ReceiptDescriptorRejected,'coverage'):
            validate_receipt_descriptor(replace(descriptor,receipts=(replace(row,actions=(replace(action,effect_ids=action.effect_ids[:-1]),)+row.actions[1:]),descriptor.receipts[1])))
        payload_fields=tuple((key,('string','missing-action') if key=='source_action_id' else value)
                             for key,value in payload[1])
        broken_effect=(effect_id,(payload[0],payload_fields))
        with self.assertRaisesRegex(ReceiptDescriptorRejected,'source Action link'):
            validate_receipt_descriptor(replace(descriptor,receipts=(replace(row,effects=(broken_effect,)+row.effects[1:]),descriptor.receipts[1])))
        forged=object.__new__(type(descriptor))
        for name,value in descriptor.__dict__.items():object.__setattr__(forged,name,value)
        object.__setattr__(forged,'unreviewed_handle',object())
        with self.assertRaisesRegex(ReceiptDescriptorRejected,'unknown .* fields'):
            validate_receipt_descriptor(forged)

    def test_checkpoint_readiness_and_existing_receipt_refusal_stay_false(self):
        self.two_boundaries_with_future()
        from checkpoint_inventory import capture_checkpoint_candidate,validate_checkpoint_candidate
        candidate=capture_checkpoint_candidate(self.world,self.enc,quiescent=True,
            rng_scope='exclusive_encounter',native_adapters=True)
        result=validate_checkpoint_candidate(self.world,self.enc,candidate,quiescent=True)
        self.assertFalse(candidate.closure_validated);self.assertFalse(candidate.portable_schema_defined);self.assertFalse(candidate.restore_verified)
        self.assertFalse(result.restore_verified)
        self.assertIn('receipt_rebinding_required',{row.code for row in result.diagnostics})


if __name__=='__main__':unittest.main()
