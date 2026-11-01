"""Pure inactive identity reservation for the bounded imported Run history."""
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
import random
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tests'))

import atomic_publication
from checkpoint_binding import _NATIVE_BINDINGS, bind_quarantined_run_boundary
from checkpoint_identity_reservations import (HistoricalIdentityReservationPlan,
    IdentityReservationRejected, plan_historical_identity_reservations,
    validate_future_identity_ids)
from checkpoint_projection import project_quarantined_run_boundary
from checkpoint_wire import decode_run_spot_wire
from test_checkpoint_projection import committed_run_wire


def bound_fixture():
    wire, _batch = committed_run_wire()
    decoded = decode_run_spot_wire(wire)
    projection = project_quarantined_run_boundary(decoded)
    return bind_quarantined_run_boundary(decoded, projection)


class TestCheckpointIdentityReservations(unittest.TestCase):
    def setUp(self):
        self.binding = bound_fixture()
        self.sidecar = self.binding.historical
        self.private = _NATIVE_BINDINGS[self.binding]

    def test_closed_run_plan_records_actual_namespaces_and_counter_floor(self):
        book = self.private.encounter._choice_book
        before = (book._counter, dict(book._choices), dict(book._registered),
                  tuple(self.private.universe.event_history),
                  tuple(self.private.encounter.pending_action_list),
                  self.private.rng_owner.state, random.getstate(),
                  dict(atomic_publication._COMMITTED_RECEIPTS))
        plan = plan_historical_identity_reservations(self.sidecar)
        self.assertIs(type(plan), HistoricalIdentityReservationPlan)
        self.assertEqual(plan.historical_choice_ids, (self.sidecar.choice_id,))
        self.assertEqual(plan.historical_action_ids, self.sidecar.action_identity_ids)
        self.assertEqual(len(plan.historical_action_ids), 1)
        self.assertEqual(plan.event_namespace_ids,
                         ('0', self.sidecar.projection.encounter_id,
                          self.sidecar.action_identity_ids[0]))
        self.assertEqual(plan.target_object_ids, self.sidecar.target_identity_ids)
        self.assertEqual(len(plan.target_object_ids), 2)
        self.assertEqual(plan.causal_effect_ids,
                         tuple(row.identity for row in self.sidecar.projection.effects))
        suffix = int(self.sidecar.choice_id.rsplit('/', 1)[1])
        self.assertEqual(plan.choice_book_counter_floor, suffix)
        self.assertEqual(plan.minimum_next_draft_suffix, suffix + 1)
        self.assertFalse(plan.source_counter_exact)
        self.assertIn('not persisted', plan.source_counter_note)
        with self.assertRaises(FrozenInstanceError):
            plan.choice_book_counter_floor = 0
        after = (book._counter, dict(book._choices), dict(book._registered),
                 tuple(self.private.universe.event_history),
                 tuple(self.private.encounter.pending_action_list),
                 self.private.rng_owner.state, random.getstate(),
                 dict(atomic_publication._COMMITTED_RECEIPTS))
        self.assertEqual(after, before)

    def test_future_identity_check_reserves_one_action_and_rejects_collisions(self):
        plan = plan_historical_identity_reservations(self.sidecar)
        next_suffix = plan.minimum_next_draft_suffix
        choice_id = f'{plan.encounter_id}/draft/{next_suffix}'
        checked = validate_future_identity_ids(plan, choice_id, ('future-run-action',))
        self.assertTrue(checked.accepted)
        self.assertEqual(checked.action_ids, ('future-run-action',))
        bad_sets = (
            (self.sidecar.choice_id, ('new-run',)),
            (f'{plan.encounter_id}/draft/{plan.choice_book_counter_floor}', ('new-run',)),
            (choice_id, (plan.historical_action_ids[0],)),
            (choice_id, ('same', 'same')),
            (choice_id, ('',)),
        )
        for candidate_choice, action_ids in bad_sets:
            with self.subTest(choice_id=candidate_choice, action_ids=action_ids):
                with self.assertRaises(IdentityReservationRejected):
                    validate_future_identity_ids(plan, candidate_choice, action_ids)
        with self.assertRaises(IdentityReservationRejected):
            validate_future_identity_ids(plan, choice_id, ('future-run-action',),
                                         existing_event_ids=('future-run-action',))
        with self.assertRaises(IdentityReservationRejected):
            validate_future_identity_ids(plan, choice_id, ('future-run-action',),
                                         existing_choice_ids=(choice_id,))

    def test_foreign_choice_membership_duplicate_action_and_wrong_owner_refuse(self):
        original, projection = self.sidecar, self.sidecar.projection
        foreign = 'foreign-encounter/draft/2'
        changed_choice = (foreign, *projection.committed_choices[0][1:])
        malformed = replace(original, choice_id=foreign,
            projection=replace(projection, committed_choices=(changed_choice,)))
        with self.assertRaises(IdentityReservationRejected):
            plan_historical_identity_reservations(malformed)
        malformed_suffix = 'not-the-generated-shape'
        changed_choice = (malformed_suffix, *projection.committed_choices[0][1:])
        with self.assertRaises(IdentityReservationRejected):
            plan_historical_identity_reservations(replace(original,
                choice_id=malformed_suffix,
                projection=replace(projection, committed_choices=(changed_choice,))))
        with self.assertRaises(IdentityReservationRejected):
            plan_historical_identity_reservations(replace(original,
                action_identity_ids=(original.action_identity_ids[0],
                                     original.action_identity_ids[0])))
        row = projection.committed_choices[0]
        wrong_membership = (row[0], row[1], row[2], ('invented-run-action',))
        with self.assertRaises(IdentityReservationRejected):
            plan_historical_identity_reservations(replace(original,
                projection=replace(projection, committed_choices=(wrong_membership,))))
        wrong_batch = replace(original.batch_practice[0], target_id='foreign-target')
        with self.assertRaises(IdentityReservationRejected):
            plan_historical_identity_reservations(replace(original,
                batch_practice=(wrong_batch,)))

    def test_plan_is_detached_and_rejects_edits_and_unsupported_history(self):
        plan = plan_historical_identity_reservations(self.sidecar)
        with self.assertRaises(IdentityReservationRejected):
            validate_future_identity_ids(replace(plan, choice_book_counter_floor=0),
                f'{plan.encounter_id}/draft/2', ('new-run-action',))
        unsupported = replace(self.sidecar,
            projection=replace(self.sidecar.projection, boundary=2))
        with self.assertRaises(IdentityReservationRejected):
            plan_historical_identity_reservations(unsupported)
        self.assertEqual(self.private.encounter._choice_book._counter, 0)
        self.assertFalse(self.private.encounter._choice_book._choices)
        self.assertFalse(self.private.encounter._choice_book._registered)
        self.assertEqual(set(self.private.universe.event_history),
                         {'0', plan.encounter_id})
        self.assertTrue(set(plan.historical_action_ids).isdisjoint(
            self.private.universe.event_history))

    def test_wire_projection_binding_and_plan_work_in_separate_process(self):
        wire, _batch = committed_run_wire()
        projection = project_quarantined_run_boundary(decode_run_spot_wire(wire))
        expected_choice = projection.committed_choices[0][0]
        expected_actions = tuple(row.action_id for row in projection.actions)
        script = r'''
import json,sys
sys.path.insert(0,sys.argv[1]); sys.path.insert(0,sys.argv[2])
from checkpoint_wire import decode_run_spot_wire
from checkpoint_projection import project_quarantined_run_boundary
from checkpoint_binding import bind_quarantined_run_boundary,_NATIVE_BINDINGS
from checkpoint_identity_reservations import plan_historical_identity_reservations
d=decode_run_spot_wire(sys.stdin.buffer.read()); p=project_quarantined_run_boundary(d)
b=bind_quarantined_run_boundary(d,p)
r=plan_historical_identity_reservations(b.historical)
private=_NATIVE_BINDINGS[b]
assert private.encounter._choice_book._counter == 0
assert not private.encounter._choice_book._choices
assert set(r.historical_action_ids).isdisjoint(private.universe.event_history)
assert len(r.historical_action_ids)==1 and len(r.target_object_ids)==2
print(json.dumps({'choice':r.historical_choice_ids[0],
 'actions':r.historical_action_ids,'targets':r.target_object_ids,
 'floor':r.choice_book_counter_floor,'next':r.minimum_next_draft_suffix,
 'exact':r.source_counter_exact}))
'''
        run = subprocess.run([sys.executable, '-c', script, str(ROOT / 'src'),
            str(ROOT / 'tests')], input=wire, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, check=True, cwd=str(ROOT))
        import json
        result = json.loads(run.stdout)
        self.assertEqual(result['choice'], expected_choice)
        self.assertEqual(tuple(result['actions']), expected_actions)
        self.assertEqual(len(result['targets']), 2)
        self.assertEqual(result['next'], result['floor'] + 1)
        self.assertFalse(result['exact'])


if __name__ == '__main__':
    unittest.main()
