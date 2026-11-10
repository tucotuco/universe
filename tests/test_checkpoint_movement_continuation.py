import base64
import hashlib
import json
import os
import subprocess
import sys
import unittest
from dataclasses import replace

from arena_browser_session import GeneratedArenaSession
from arena_movement_plan_checkpoint import capture_accepted_plan, decode
from checkpoint_envelope import assemble_native_run_spot_envelope
from checkpoint_wire import encode_run_spot_envelope


_CHILD = r'''
import base64, hashlib, json, sys
assert 'npcgen' not in sys.modules
from checkpoint_wire import decode_run_spot_wire
from arena_movement_plan_checkpoint import decode as decode_plan
from checkpoint_restore_preparation import (
  _import_quarantined_movement_boundary,
  _host_authorize_movement_continuation,
  _QUARANTINED_MOVEMENT_IMPORTS,
  _trusted_continue_imported_movement_boundary)
wire=json.loads(sys.stdin.buffer.read().decode('utf-8'))
decoded=decode_run_spot_wire(base64.b64decode(wire['checkpoint'],validate=True))
plan=decode_plan(base64.b64decode(wire['movement_plan'],validate=True))
imported=_import_quarantined_movement_boundary(decoded)
approval=_host_authorize_movement_continuation(imported,plan)
result=_trusted_continue_imported_movement_boundary(imported,plan,approval=approval)
private=_QUARANTINED_MOVEMENT_IMPORTS[imported]
encounter=private.native.encounter
before_followup=(encounter.time,tuple(encounter._atomic_interval_history),
  private.native.rng_owner.state)
try:
  encounter.step(1)
  followup='unexpectedly-advanced'
except Exception as exc:
  followup=str(exc)
after_followup=(encounter.time,tuple(encounter._atomic_interval_history),
  private.native.rng_owner.state)
assert after_followup==before_followup
digest=lambda value: hashlib.sha256(repr(value).encode()).hexdigest()
inspection=result.inspection
rows=[(row[0], row[1], row[2], row[3], digest(row[4]), digest(row[5]),
       row[6], row[7], row[8]) for row in result.native_beings]
observers=[(row[0],digest(row[1])) for row in result.observer_evidence]
print(json.dumps({
  'schema':result.schema, 'plan':digest(plan),
  'encounter':inspection.encounter_id, 'boundary':inspection.boundary,
  'latest':inspection.latest_boundary, 'participants':sorted(inspection.participants),
  'timeline':[[row.boundary,list(row.action_ids),list(row.effect_ids)]
              for row in inspection.timeline],
  'beings':rows, 'observers':observers,
  'activation':[[imported.binding.sidecar.movement_activation[3],
    imported.binding.sidecar.movement_activation[0], imported.binding.encounter_id,
    imported.binding.sidecar.movement_activation[1],
    imported.binding.sidecar.movement_activation[2]]],
  'rng':digest(result.rng_state), 'choices':0,
  'pending':[], 'finished':[], 'cancelled':[],
  'quarantined':result.quarantined_after_step,
  'followup_refusal':followup,
  'receipt_count':len(inspection.timeline)
}))
'''

_BOUNDARY_TWO_CHILD = r'''
import base64, json, sys
assert 'npcgen' not in sys.modules
from checkpoint_wire import decode_run_spot_wire
from arena_movement_plan_checkpoint import decode as decode_plan
from checkpoint_restore_preparation import (
  _import_quarantined_movement_boundary, _host_authorize_movement_continuation,
  _trusted_continue_imported_movement_boundary, _capture_trusted_movement_checkpoint,
  RestorePreparationRejected)
from unittest.mock import patch
import checkpoint_envelope
wire=json.loads(sys.stdin.buffer.read().decode('utf-8'))
decoded=decode_run_spot_wire(base64.b64decode(wire['checkpoint'],validate=True))
plan=decode_plan(base64.b64decode(wire['movement_plan'],validate=True))
handle=_import_quarantined_movement_boundary(decoded)
approval=_host_authorize_movement_continuation(handle,plan)
result=_trusted_continue_imported_movement_boundary(handle,plan,approval=approval)
assert result.inspection.boundary == 2 and result.quarantined_after_step
private=_import_handle=__import__('checkpoint_restore_preparation')._QUARANTINED_MOVEMENT_IMPORTS[handle]
encounter=private.native.encounter
snapshot=(encounter.time,tuple(encounter._atomic_interval_history),private.native.rng_owner.state,
  tuple((key,being.get_position().as_tuple(),tuple(being._atomic_target_history),
    being.__dict__.get('_checkpoint_quarantined')) for key,being in private.native.beings),
  encounter.__dict__.get('_checkpoint_quarantined'),
  private.native.universe.__dict__.get('_checkpoint_quarantined'))
with patch.object(checkpoint_envelope,'assemble_native_run_spot_envelope',
    side_effect=RuntimeError('injected capture failure')):
  try:
    _capture_trusted_movement_checkpoint(handle)
  except RestorePreparationRejected:
    pass
  else:
    raise AssertionError('injected checkpoint capture unexpectedly succeeded')
after=(encounter.time,tuple(encounter._atomic_interval_history),private.native.rng_owner.state,
  tuple((key,being.get_position().as_tuple(),tuple(being._atomic_target_history),
    being.__dict__.get('_checkpoint_quarantined')) for key,being in private.native.beings),
  encounter.__dict__.get('_checkpoint_quarantined'),
  private.native.universe.__dict__.get('_checkpoint_quarantined'))
assert after==snapshot
checkpoint, next_plan=_capture_trusted_movement_checkpoint(handle)
print(json.dumps({'checkpoint':base64.b64encode(checkpoint).decode(),
  'movement_plan':base64.b64encode(next_plan).decode()},sort_keys=True,separators=(',',':')))
'''

_BOUNDARY_THREE_CHILD = r'''
import base64, hashlib, json, sys
assert 'npcgen' not in sys.modules
from checkpoint_wire import decode_run_spot_wire
from arena_movement_plan_checkpoint import decode as decode_plan
from checkpoint_restore_preparation import (
  _import_quarantined_movement_boundary, _host_authorize_movement_continuation,
  _trusted_continue_imported_movement_boundary, _QUARANTINED_MOVEMENT_IMPORTS)
from checkpoint_reconstruction import _projection
from checkpoint_arena_perception import encode_arena_perception_ledger
from encounter_inspection import fingerprint
wire=json.loads(sys.stdin.buffer.read().decode('utf-8'))
decoded=decode_run_spot_wire(base64.b64decode(wire['checkpoint'],validate=True))
plan=decode_plan(base64.b64decode(wire['movement_plan'],validate=True))
handle=_import_quarantined_movement_boundary(decoded)
approval=_host_authorize_movement_continuation(handle,plan)
result=_trusted_continue_imported_movement_boundary(handle,plan,approval=approval)
private=_QUARANTINED_MOVEMENT_IMPORTS[handle]
encounter=private.native.encounter
registry=private.native.universe.object_registry.object_instances
digest=lambda value: hashlib.sha256(repr(value).encode()).hexdigest()
beings=[]; observers=[]
for being_id, being in sorted(private.native.beings):
  position=being.get_position()
  beings.append((being_id,tuple(position.as_tuple()),being.get_posture(),being.hex_facing,
    digest(_projection(being.original)),digest(_projection(being.current)),
    tuple(sorted(encounter.awareness[being_id])),
    tuple(row.boundary for row in being._atomic_target_history),
    tuple(fingerprint(row) for row in being._atomic_target_history)))
  observers.append((being_id,digest(encode_arena_perception_ledger(
    being._arena_perception_ledger,observer=being,encounter=encounter,registry=registry))))
print(json.dumps({'boundary':result.inspection.boundary,'latest':result.inspection.latest_boundary,
  'plan':digest(plan),
  'encounter':result.inspection.encounter_id,'participants':sorted(result.inspection.participants),
  'timeline':[[r.boundary,list(r.action_ids),list(r.effect_ids)] for r in result.inspection.timeline],
  'beings':beings,'observers':observers,'rng':digest(result.rng_state),
  'choices':encounter._choice_book._counter,'pending':list(encounter.pending_action_list),
  'finished':list(encounter.finished_action_list),'cancelled':list(encounter.cancelled_action_list),
  'activation':[[encounter.arena_movement_activation.activation_kind,
    encounter.arena_movement_activation.actor_id,encounter.arena_movement_activation.encounter_id,
    encounter.arena_movement_activation.movement_decision_id,
    encounter.arena_movement_activation.time]],
  'quarantined':result.quarantined_after_step,'receipt_count':len(result.inspection.timeline)},
  sort_keys=True,separators=(',',':')))
'''


def _digest(value):
    return hashlib.sha256(repr(value).encode()).hexdigest()


class NativeMovementContinuationTests(unittest.TestCase):
    def _source_at_boundary_one(self):
        session = GeneratedArenaSession(root_seed_factory=lambda: 20261120)
        session.generate({'starting_experience': '10000',
                          'width_cells': '5', 'height_cells': '5'})
        candidate = session.active_candidate
        player = candidate.participants[0].native.being
        self.assertGreater(player.current.hit_points, 0)
        destination = candidate.arena_map.layout.address_for_index(0)
        session.choose_destination({'column': destination.column,
            'row': destination.row, 'rate': 'walk', 'facing_policy': 'turn'})
        accepted = session._movement_plan
        self.assertIsNotNone(accepted)
        session.advance_one_second()
        self.assertEqual(candidate.encounter.time, 1)
        self.assertIsNotNone(session._movement_plan,
            'fixture destination must remain in progress after boundary 1')
        self.assertNotEqual(player.get_position(), accepted.destination)
        plan_wire = capture_accepted_plan(session)
        saved_plan = decode(plan_wire)
        self.assertEqual((saved_plan.decision_id, saved_plan.destination,
            saved_plan.cell, saved_plan.rate, saved_plan.facing_policy),
            (accepted.decision_id,
             (accepted.destination.x, accepted.destination.y, accepted.destination.z),
             (accepted.address.column, accepted.address.row), accepted.rate,
             accepted.facing_policy))
        envelope = assemble_native_run_spot_envelope(candidate.universe,
            candidate.encounter, quiescent=True, rng_scope='exclusive_encounter')
        return session, envelope, plan_wire

    @staticmethod
    def _source_state(session, plan_wire):
        from checkpoint_reconstruction import _projection
        from checkpoint_arena_perception import encode_arena_perception_ledger
        from encounter_inspection import inspect_encounter, fingerprint
        candidate = session.active_candidate
        encounter = candidate.encounter
        inspection = inspect_encounter(encounter)
        beings = []
        observers = []
        registry = candidate.universe.object_registry.object_instances
        for participant in candidate.participants:
            being = participant.native.being
            position = being.get_position()
            beings.append((being.id, tuple(position.as_tuple()), being.get_posture(),
                being.hex_facing, _digest(_projection(being.original)),
                _digest(_projection(being.current)),
                tuple(sorted(encounter.awareness[being.id])),
                tuple(row.boundary for row in inspection.histories[being.id]),
                tuple(fingerprint(row) for row in being._atomic_target_history)))
            ledger = encode_arena_perception_ledger(being._arena_perception_ledger,
                observer=being, encounter=encounter, registry=registry)
            observers.append((being.id, _digest(ledger)))
        return {
            'schema': 'universe.trusted-movement-continuation-inspection/1',
            'plan': _digest(decode(plan_wire)),
            'encounter': inspection.encounter_id,
            'boundary': inspection.boundary,
            'latest': inspection.latest_boundary,
            'participants': sorted(inspection.participants),
            'timeline': [[row.boundary, list(row.action_ids), list(row.effect_ids)]
                         for row in inspection.timeline],
            'beings': json.loads(json.dumps(sorted(beings))),
            'observers': json.loads(json.dumps(sorted(observers))),
            'activation': [[encounter.arena_movement_activation.activation_kind,
                encounter.arena_movement_activation.actor_id,
                encounter.arena_movement_activation.encounter_id,
                encounter.arena_movement_activation.movement_decision_id,
                encounter.arena_movement_activation.time]],
            'rng': _digest(session._rng_cursor.state),
            'choices': encounter._choice_book._counter,
            'pending': list(encounter.pending_action_list),
            'finished': list(encounter.finished_action_list),
            'cancelled': list(encounter.cancelled_action_list),
            'quarantined': False,
            'receipt_count': len(inspection.timeline),
        }

    def test_fresh_process_boundary_one_continues_to_matching_boundary_two(self):
        session, envelope, plan_wire = self._source_at_boundary_one()
        candidate = session.active_candidate
        activation = candidate.encounter.arena_movement_activation
        self.assertEqual(session._movement_plan.decision_id,
                         activation.movement_decision_id)
        session.advance_one_second()
        expected = self._source_state(session, plan_wire)
        self.assertEqual(expected['boundary'], 2)
        self.assertEqual(expected['receipt_count'], 2)
        self.assertEqual(expected['pending'], [])
        self.assertEqual(expected['finished'], [])
        self.assertEqual(expected['cancelled'], [])

        payload = json.dumps({
            'checkpoint': base64.b64encode(encode_run_spot_envelope(envelope)).decode(),
            'movement_plan': base64.b64encode(plan_wire).decode(),
        }, sort_keys=True, separators=(',', ':')).encode()
        process = subprocess.run([sys.executable, '-c', _CHILD], input=payload,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=os.getcwd(),
            env={**os.environ, 'PYTHONPATH': os.pathsep.join((
                os.path.abspath('src'), os.path.abspath('tests'),
                os.environ.get('PYTHONPATH', '')))}, check=False, timeout=120)
        self.assertEqual(process.returncode, 0, process.stderr.decode(errors='replace'))
        actual = json.loads(process.stdout)
        self.assertEqual(actual['schema'], expected['schema'])
        self.assertEqual(actual['plan'], expected['plan'])
        for key in ('encounter', 'boundary', 'latest', 'participants', 'timeline',
                    'beings', 'observers', 'activation', 'rng', 'choices',
                    'pending', 'finished', 'cancelled', 'receipt_count'):
            self.assertEqual(actual[key], expected[key], key)
        self.assertEqual(actual['boundary'], 2)
        self.assertEqual(actual['timeline'], [[1, [], []], [2, [], []]])
        self.assertTrue(actual['quarantined'])
        self.assertIn('quarantined', actual['followup_refusal'].lower())
        self.assertFalse(expected['quarantined'])

    def test_three_process_repeatable_boundary_two_checkpoint_and_boundary_three(self):
        session, envelope, plan_wire = self._source_at_boundary_one()
        candidate = session.active_candidate
        session.advance_one_second()
        session.advance_one_second()
        expected = self._source_state(session, plan_wire)
        self.assertEqual(expected['boundary'], 3)
        plan2 = replace(decode(plan_wire), checkpoint_boundary=2)
        expected['plan'] = _digest(plan2)
        env = {**os.environ, 'PYTHONPATH': os.pathsep.join((
            os.path.abspath('src'), os.path.abspath('tests'), os.environ.get('PYTHONPATH', '')))}
        source_payload = json.dumps({'checkpoint':base64.b64encode(
            encode_run_spot_envelope(envelope)).decode(),
            'movement_plan':base64.b64encode(plan_wire).decode()},
            sort_keys=True,separators=(',',':')).encode()
        process_b = subprocess.run([sys.executable, '-c', _BOUNDARY_TWO_CHILD],
            input=source_payload, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            cwd=os.getcwd(), env=env, check=False, timeout=180)
        self.assertEqual(process_b.returncode, 0, process_b.stderr.decode(errors='replace'))
        checkpoint_two = json.loads(process_b.stdout)
        plan_two = decode(base64.b64decode(checkpoint_two['movement_plan']))
        self.assertEqual(plan_two.checkpoint_boundary, 2)
        process_c = subprocess.run([sys.executable, '-c', _BOUNDARY_THREE_CHILD],
            input=json.dumps(checkpoint_two,sort_keys=True,separators=(',',':')).encode(),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=os.getcwd(), env=env,
            check=False, timeout=180)
        self.assertEqual(process_c.returncode, 0, process_c.stderr.decode(errors='replace'))
        actual = json.loads(process_c.stdout)
        self.assertEqual(actual['boundary'], 3)
        for key in ('encounter','boundary','latest','participants','timeline','beings',
                    'observers','rng','choices','pending','finished','cancelled',
                    'activation','receipt_count','plan'):
            self.assertEqual(actual[key], expected[key], key)
        self.assertEqual(actual['timeline'], [[1,[],[]],[2,[],[]],[3,[],[]]])
        self.assertTrue(actual['quarantined'])

    def test_boundary_two_projection_rejects_forged_receipt_target_and_interval_order(self):
        from dataclasses import replace as dc_replace
        from checkpoint_projection import project_quarantined_movement_boundary
        from checkpoint_wire import decode_run_spot_wire
        session, _envelope, _plan_wire = self._source_at_boundary_one()
        session.advance_one_second()
        candidate = session.active_candidate
        envelope = assemble_native_run_spot_envelope(candidate.universe,
            candidate.encounter, quiescent=True, rng_scope='exclusive_encounter')
        decoded = decode_run_spot_wire(encode_run_spot_envelope(envelope))
        data = decoded.envelope_data
        project_quarantined_movement_boundary(decoded)

        chain = list(data[8])
        receipts = list(chain[4])
        forged_receipt = list(receipts[1]); forged_receipt[1] = 3
        receipts[1] = tuple(forged_receipt); chain[4] = tuple(receipts)
        bad_receipt_data = list(data); bad_receipt_data[8] = tuple(chain)
        with self.assertRaises(ValueError):
            project_quarantined_movement_boundary(dc_replace(decoded,
                envelope_data=tuple(bad_receipt_data)))

        chain = list(data[8]); receipts = list(chain[4]); second = list(receipts[1])
        targets = list(second[4]); target = list(targets[0]); target[0] = 'forged-target'
        targets[0] = tuple(target); second[4] = tuple(targets)
        receipts[1] = tuple(second); chain[4] = tuple(receipts)
        bad_target_data = list(data); bad_target_data[8] = tuple(chain)
        with self.assertRaises(ValueError):
            project_quarantined_movement_boundary(dc_replace(decoded,
                envelope_data=tuple(bad_target_data)))

        chain = list(data[8]); receipts = list(chain[4]); second = list(receipts[1])
        second[6] = ('random-state', ('forged-cursor',))
        receipts[1] = tuple(second); chain[4] = tuple(receipts)
        bad_rng_data = list(data); bad_rng_data[8] = tuple(chain)
        with self.assertRaises(ValueError):
            project_quarantined_movement_boundary(dc_replace(decoded,
                envelope_data=tuple(bad_rng_data)))

        bad_order_data = list(data); bad_order_data[4] = (1, 1)
        with self.assertRaises(ValueError):
            project_quarantined_movement_boundary(dc_replace(decoded,
                envelope_data=tuple(bad_order_data)))

    def test_mismatched_plan_is_refused_without_admitting_or_mutating_import(self):
        session, envelope, plan_wire = self._source_at_boundary_one()
        from checkpoint_restore_preparation import (
            RestorePreparationRejected, _import_quarantined_movement_boundary,
            _host_authorize_movement_continuation,
            _trusted_continue_imported_movement_boundary,
            _QUARANTINED_MOVEMENT_IMPORTS)
        from checkpoint_wire import decode_run_spot_wire
        from atomic_publication import _COMMITTED_RECEIPTS
        decoded = decode_run_spot_wire(encode_run_spot_envelope(envelope))
        imported = _import_quarantined_movement_boundary(decoded)
        native = _QUARANTINED_MOVEMENT_IMPORTS[imported].native
        encounter = native.encounter
        being_map = dict(native.beings)
        before = (encounter.time, encounter.last_processed_boundary,
            tuple(encounter._atomic_interval_history), native.rng_owner.state,
            tuple((key, being.get_position().as_tuple(),
                   tuple(being._atomic_target_history))
                  for key, being in sorted(being_map.items())))
        receipts = set(_COMMITTED_RECEIPTS)
        plan = decode(plan_wire)
        approval = _host_authorize_movement_continuation(imported, plan)
        forged = replace(plan, actor_id='unrelated-player-id')
        with self.assertRaises(RestorePreparationRejected):
            _trusted_continue_imported_movement_boundary(imported, forged,
                approval=approval)
        after = (encounter.time, encounter.last_processed_boundary,
            tuple(encounter._atomic_interval_history), native.rng_owner.state,
            tuple((key, being.get_position().as_tuple(),
                   tuple(being._atomic_target_history))
                  for key, being in sorted(being_map.items())))
        self.assertEqual(after, before)
        self.assertEqual(set(_COMMITTED_RECEIPTS), receipts)
        self.assertEqual(encounter.progression_mode, 'quarantined_inspection')
        self.assertTrue(session.active_candidate.encounter.time == 1)

    def test_failed_native_step_restores_quarantined_inspection_binding(self):
        from unittest.mock import patch
        from checkpoint_restore_preparation import (
            RestorePreparationRejected, _import_quarantined_movement_boundary,
            _host_authorize_movement_continuation,
            _trusted_continue_imported_movement_boundary,
            _QUARANTINED_MOVEMENT_IMPORTS)
        from checkpoint_wire import decode_run_spot_wire
        from atomic_publication import _COMMITTED_RECEIPTS
        from encounter import Encounter

        session, envelope, plan_wire = self._source_at_boundary_one()
        decoded = decode_run_spot_wire(encode_run_spot_envelope(envelope))
        imported = _import_quarantined_movement_boundary(decoded)
        native = _QUARANTINED_MOVEMENT_IMPORTS[imported].native
        encounter = native.encounter
        before = (encounter.time, encounter.last_processed_boundary,
            tuple(encounter._atomic_interval_history), native.rng_owner.state,
            tuple((key, being.get_position().as_tuple(),
                   tuple(being._atomic_target_history))
                  for key, being in native.beings))
        receipts = set(_COMMITTED_RECEIPTS)
        plan = decode(plan_wire)
        approval = _host_authorize_movement_continuation(imported, plan)
        with patch.object(Encounter, 'step', side_effect=RuntimeError('injected step failure')):
            with self.assertRaises(RestorePreparationRejected):
                _trusted_continue_imported_movement_boundary(imported, plan,
                    approval=approval)
        after = (encounter.time, encounter.last_processed_boundary,
            tuple(encounter._atomic_interval_history), native.rng_owner.state,
            tuple((key, being.get_position().as_tuple(),
                   tuple(being._atomic_target_history))
                  for key, being in native.beings))
        self.assertEqual(after, before)
        self.assertEqual(set(_COMMITTED_RECEIPTS), receipts)
        self.assertEqual(encounter.progression_mode, 'quarantined_inspection')
        self.assertTrue(encounter.__dict__['_checkpoint_quarantined'])
        self.assertTrue(session.active_candidate.encounter.time == 1)


if __name__ == '__main__':
    unittest.main()
