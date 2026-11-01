"""Trusted-local checkpoint preparation remains private and quarantined."""
from dataclasses import FrozenInstanceError, replace
import json
from pathlib import Path
import random
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tests'))

import atomic_publication
from checkpoint_binding import (_NATIVE_BINDINGS, bind_quarantined_run_boundary)
from checkpoint_identity_reservations import (
    IdentityReservationRejected, plan_historical_identity_reservations)
from checkpoint_projection import project_quarantined_run_boundary
from checkpoint_restore_preparation import (
    RestorePreparationRejected, _HOST_APPROVALS, _PREPARED_RESTORES,
    _host_authorize_trusted_local_restore, _preflight_preparation,
    _prepare_trusted_local_restore)
from checkpoint_wire import decode_run_spot_wire
from frozen_practice import freeze_imported_run_practice
from test_checkpoint_projection import committed_run_wire
from transactional_progression import TransactionalProgressionError, is_quarantined


def binding_from_wire(wire=None):
    if wire is None:
        wire, _batch = committed_run_wire()
    decoded = decode_run_spot_wire(wire)
    projection = project_quarantined_run_boundary(decoded)
    return wire, bind_quarantined_run_boundary(decoded, projection)


class TestQuarantinedRestorePreparation(unittest.TestCase):
    def setUp(self):
        _wire, self.binding = binding_from_wire()
        self.private = _NATIVE_BINDINGS[self.binding]
        self.book = self.private.encounter._choice_book

    def _snapshot(self):
        world, encounter = self.private.universe, self.private.encounter
        return {
            'counter': self.book._counter,
            'drafts': self.book._drafts,
            'choices': self.book._choices,
            'tokens': self.book._tokens,
            'reservations': self.book._reservations,
            'registered': self.book._registered,
            'states': self.book._states,
            'revision': world._schedule_revision,
            'events': world.event_history,
            'event_items': tuple(world.event_history.items()),
            'registry': world.object_registry.object_instances,
            'registry_items': tuple(world.object_registry.object_instances.items()),
            'pending': encounter.pending_action_list,
            'finished': encounter.finished_action_list,
            'cancelled': encounter.cancelled_action_list,
            'rng': self.private.rng_owner.state,
            'module_rng': random.getstate(),
            'receipts': dict(atomic_publication._COMMITTED_RECEIPTS),
            'practice': tuple((being.id, tuple(being.skill_use_history),
                dict(being.skill_experience), dict(being.current.skills.skills),
                dict(being._skill_practice_baselines),
                tuple(being.__dict__.get('_atomic_target_history', ())))
                for _being_id, being in self.private.beings),
            'atomic_history': encounter.__dict__.get('_atomic_interval_history'),
            'container_ids': tuple(id(value) for value in (
                self.book._drafts, self.book._closed_drafts, self.book._tokens,
                self.book._choices, self.book._reservations, self.book._registered,
                self.book._states, world.event_history,
                world.object_registry.object_instances, encounter.pending_action_list,
                encounter.finished_action_list, encounter.cancelled_action_list,
                world._choice_books)),
        }

    def test_host_approved_preparation_combines_same_graph_and_only_sets_floor(self):
        before = self._snapshot()
        approval = _host_authorize_trusted_local_restore(self.binding)
        prepared = _prepare_trusted_local_restore(self.binding, approval)
        after = self._snapshot()

        self.assertTrue(prepared.quarantined)
        self.assertEqual(prepared.view.schema,
                         'universe.quarantined-trusted-local-restore-preparation/1')
        self.assertEqual(prepared.view.binding_view, self.binding.view)
        provenance = prepared.view.imported_history
        self.assertEqual(provenance.label,
            'host-authorized imported checkpoint history; not native receipt history')
        prefix = provenance.practice_prefix
        plan = _PREPARED_RESTORES[prepared].identity_plan
        self.assertEqual((prefix.universe_id, prefix.encounter_id, prefix.choice_id,
                          prefix.target_id, prefix.action_ids),
                         (plan.universe_id, plan.encounter_id, plan.historical_choice_ids[0],
                          self.binding.historical.batch_practice[0].target_id,
                          plan.historical_action_ids))
        self.assertEqual(prefix.content_digest, freeze_imported_run_practice(
            self.binding.historical).content_digest)
        self.assertEqual(prefix.action_ids, self.binding.historical.action_identity_ids)
        self.assertEqual(len(prefix.action_ids), 1)
        self.assertEqual(len(self.binding.historical.being_identity_ids), 2)
        self.assertEqual(set(self.binding.historical.being_identity_ids),
                         set(self.binding.historical.target_identity_ids))
        self.assertEqual(self.binding.view.actions[0].family, 'native.run-action/1')
        self.assertFalse(hasattr(self.binding.view.actions[0], 'observed_id'))
        self.assertEqual(prepared.view.identity_plan_digest, plan.content_digest)
        self.assertEqual(prepared.view.choice_counter_floor, plan.choice_book_counter_floor)
        self.assertEqual(prepared.view.minimum_next_draft_suffix,
                         plan.minimum_next_draft_suffix)
        self.assertFalse(prepared.view.source_counter_exact)
        self.assertEqual(prepared.view.binding_view.native_encounter.next_boundary, 2)
        self.assertEqual(prepared.view.binding_view.native_encounter.time, 1)
        self.assertEqual(prefix.uses[0].experience, 4)
        target_practice = next(row for row in after['practice'] if row[0] == prefix.target_id)
        self.assertEqual(target_practice[2]['run'], 4)
        self.assertEqual(target_practice[3].get('run', 0), 0)
        native_actions = dict(self.private.actions)
        self.assertEqual(tuple(native_actions), prefix.action_ids)
        self.assertIsNone(native_actions[prefix.action_ids[0]].target_id)
        self.assertIsNone(native_actions[prefix.action_ids[0]].displacement)

        self.assertEqual(after['counter'], plan.choice_book_counter_floor)
        for key in ('drafts', 'choices', 'tokens', 'reservations', 'registered', 'states',
                    'revision', 'events', 'event_items', 'registry', 'registry_items',
                    'pending', 'finished', 'cancelled', 'rng', 'module_rng', 'receipts',
                    'practice', 'atomic_history'):
            self.assertEqual(after[key], before[key], key)
        self.assertEqual(after['events'], self.private.universe.event_history)
        self.assertEqual(after['registry'], self.private.universe.object_registry.object_instances)
        self.assertIsNone(after['atomic_history'])
        self.assertTrue(is_quarantined(self.private.universe))
        self.assertTrue(is_quarantined(self.private.encounter))
        self.assertTrue(all(is_quarantined(value) for _key, value in self.private.actions))
        for forbidden in ('universe', 'encounter', 'native', 'rng_owner', 'identity_plan'):
            self.assertFalse(hasattr(prepared, forbidden), forbidden)
        with self.assertRaises(FrozenInstanceError):
            prepared.view.choice_counter_floor = 0
        with self.assertRaises(TransactionalProgressionError):
            self.private.encounter.step(1)
        with self.assertRaises(TransactionalProgressionError):
            self.book.propose(())
        with self.assertRaises(TransactionalProgressionError):
            dict(self.private.actions)[prefix.action_ids[0]].resolve(10)
        with self.assertRaises(TransactionalProgressionError):
            self.private.encounter.enable_transactional_progression(
                quiescent=True, rng_owner=self.private.rng_owner)
        with self.assertRaises(RestorePreparationRejected):
            _prepare_trusted_local_restore(self.binding, approval)

    def test_missing_checkpoint_or_forged_host_authority_refuses_without_mutation(self):
        before = self._snapshot()
        for supplied in (None, True, 'trusted=true', {'trusted': True},
                         self.binding.view.rng_state):
            with self.subTest(supplied=supplied):
                with self.assertRaises(RestorePreparationRejected):
                    _prepare_trusted_local_restore(self.binding, supplied)
        self.assertEqual(self._snapshot(), before)
        self.assertFalse(_HOST_APPROVALS)
        with self.assertRaises(RestorePreparationRejected):
            _host_authorize_trusted_local_restore(object())

    def test_prefix_plan_and_counter_invariant_failures_are_atomic(self):
        before = self._snapshot()
        contexts_before = set(_PREPARED_RESTORES)
        approval = _host_authorize_trusted_local_restore(self.binding)
        prefix = freeze_imported_run_practice(self.binding.historical)
        plan = plan_historical_identity_reservations(self.binding.historical)
        with self.assertRaises(RestorePreparationRejected):
            _preflight_preparation(self.binding, self.private,
                imported_prefix=replace(prefix, content_digest='0' * 64))
        with self.assertRaises(RestorePreparationRejected):
            _preflight_preparation(self.binding, self.private,
                identity_plan=replace(plan,
                    choice_book_counter_floor=plan.choice_book_counter_floor + 1))
        wrong_owner_batch = replace(self.binding.historical.batch_practice[0],
                                    target_id='foreign-run-target')
        wrong_sidecar = replace(self.binding.historical,
                                 batch_practice=(wrong_owner_batch,))
        foreign_binding = replace(self.binding, historical=wrong_sidecar)
        with self.assertRaises(RestorePreparationRejected):
            _preflight_preparation(foreign_binding, self.private)
        self.assertEqual(self._snapshot(), before)

        # The helper refuses any unexpected existing allocator state rather
        # than lowering/replacing it. Restore test fixture state afterward.
        self.book._counter = plan.choice_book_counter_floor + 1
        with self.assertRaises(IdentityReservationRejected):
            from checkpoint_identity_reservations import _initialize_quarantined_choice_counter_floor
            _initialize_quarantined_choice_counter_floor(self.book, plan)
        self.book._counter = 0
        self.assertEqual(self._snapshot(), before)
        self.assertEqual(set(_PREPARED_RESTORES), contexts_before)
        self.assertIs(_HOST_APPROVALS[approval], self.binding)

    def test_publication_fault_rolls_back_only_private_counter_without_alias_replacement(self):
        before = self._snapshot()
        contexts_before = set(_PREPARED_RESTORES)
        approval = _host_authorize_trusted_local_restore(self.binding)
        from checkpoint_identity_reservations import _initialize_quarantined_choice_counter_floor

        def mutate_then_fail(book, plan):
            _initialize_quarantined_choice_counter_floor(book, plan)
            raise RuntimeError('injected context publication failure')

        with patch('checkpoint_identity_reservations._initialize_quarantined_choice_counter_floor',
                   side_effect=mutate_then_fail):
            with self.assertRaisesRegex(RuntimeError, 'injected'):
                _prepare_trusted_local_restore(self.binding, approval)
        after = self._snapshot()
        self.assertEqual(after, before)
        self.assertEqual(set(_PREPARED_RESTORES), contexts_before)
        self.assertIs(_HOST_APPROVALS[approval], self.binding)

    def test_separate_process_decode_bind_authorize_and_prepare(self):
        wire, _batch = committed_run_wire()
        source_projection = project_quarantined_run_boundary(decode_run_spot_wire(wire))
        expected_choice = source_projection.committed_choices[0][0]
        expected_actions = tuple(row.action_id for row in source_projection.actions)
        script = r'''
import json,random,sys
sys.path.insert(0,sys.argv[1])
from checkpoint_wire import decode_run_spot_wire
from checkpoint_projection import project_quarantined_run_boundary
from checkpoint_binding import bind_quarantined_run_boundary,_NATIVE_BINDINGS
from checkpoint_restore_preparation import (_host_authorize_trusted_local_restore,
 _prepare_trusted_local_restore,_PREPARED_RESTORES)
from atomic_publication import _COMMITTED_RECEIPTS
module_rng=random.getstate(); receipts=dict(_COMMITTED_RECEIPTS)
d=decode_run_spot_wire(sys.stdin.buffer.read())
p=project_quarantined_run_boundary(d); b=bind_quarantined_run_boundary(d,p)
approval=_host_authorize_trusted_local_restore(b)
r=_prepare_trusted_local_restore(b,approval); n=_NATIVE_BINDINGS[b]
assert random.getstate()==module_rng and dict(_COMMITTED_RECEIPTS)==receipts
assert r.quarantined and r.view.imported_history.practice_prefix.boundary==1
assert n.encounter._choice_book._counter==r.view.choice_counter_floor
assert not n.encounter._choice_book._choices and not n.encounter.finished_action_list
assert r.view.binding_view.encounter_id==r.view.imported_history.practice_prefix.encounter_id
print(json.dumps({'choice':r.view.imported_history.practice_prefix.choice_id,
 'actions':r.view.imported_history.practice_prefix.action_ids,
 'target':r.view.imported_history.practice_prefix.target_id,
 'floor':r.view.choice_counter_floor,'next':r.view.minimum_next_draft_suffix,
 'exact':r.view.source_counter_exact,'quarantined':r.quarantined}))
'''
        run = subprocess.run([sys.executable, '-c', script, str(ROOT / 'src')],
            input=wire, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            check=True, cwd=str(ROOT))
        result = json.loads(run.stdout)
        self.assertEqual(result['choice'], expected_choice)
        self.assertEqual(tuple(result['actions']), expected_actions)
        self.assertEqual(result['floor'] + 1, result['next'])
        self.assertFalse(result['exact'])
        self.assertTrue(result['quarantined'])


if __name__ == '__main__':
    unittest.main()
