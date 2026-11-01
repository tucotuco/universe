"""Bounded trusted-local Run boundary-2 continuation (5E1J6)."""
import base64
from collections.abc import Mapping
from dataclasses import fields, is_dataclass
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tests'))

import atomic_publication
from checkpoint_binding import _NATIVE_BINDINGS, bind_quarantined_run_boundary
from checkpoint_projection import project_quarantined_run_boundary
from checkpoint_restore_continuation import (
    ContinuationRejected, _continue_one_run_boundary2)
from checkpoint_restore_dependencies import (
    RestoreDependencyRejected, create_prepared_boundary2_read_dependency,
    preflight_boundary2_identity_ids)
from checkpoint_restore_preparation import (
    _PREPARED_RESTORES, _host_authorize_trusted_local_restore,
    _prepare_trusted_local_restore)
from checkpoint_wire import decode_run_spot_wire
from test_checkpoint_projection import committed_run_wire
from test_checkpoint_reconstruction import build_source
from transactional_progression import (
    TransactionalProgressionError, is_quarantined)


def _prepared(wire):
    decoded = decode_run_spot_wire(wire)
    projection = project_quarantined_run_boundary(decoded)
    binding = bind_quarantined_run_boundary(decoded, projection)
    approval = _host_authorize_trusted_local_restore(binding)
    return _prepare_trusted_local_restore(binding, approval)


def _stable(value):
    """Closed value comparison that treats numerically equal int/float as equal."""
    if is_dataclass(value):
        return (type(value).__name__, tuple((field.name, _stable(getattr(value, field.name)))
                                             for field in fields(value)))
    if isinstance(value, Mapping):
        return tuple((key, _stable(value[key])) for key in sorted(value))
    if type(value) in (tuple, list):
        return tuple(_stable(item) for item in value)
    if type(value) in (str, int, float, bool, type(None)):
        return value
    raise TypeError(f'unsupported comparison value {type(value).__name__}')


def _preflight(prepared, dependency, action_id='c6-boundary2-run'):
    private = _PREPARED_RESTORES[prepared]
    encounter = private.native.encounter
    prefix = prepared.view.imported_history.practice_prefix
    choice_id = (f'{encounter.id}/draft/'
                 f'{prepared.view.minimum_next_draft_suffix}')
    return preflight_boundary2_identity_ids(prepared, dependency,
        encounter_id=encounter.id, practice_target_id=prefix.target_id,
        choice_id=choice_id, action_ids=(action_id,), boundary=2)


def _summary(evidence, choice_state, *, choice_counter, action_displacement,
             participant_state, historical_provenance, native_history_boundaries,
             native_practice_times, new_receipt_issued):
    target = evidence.target_interval_record
    practice = target.state.practice_state
    use = target.state.practice_state.exercises[-1]
    return {
        'boundary': evidence.boundary,
        'choice_id': evidence.choice_id,
        'choice_state': choice_state,
        'action_id': evidence.action_id,
        'action_displacement': action_displacement,
        'action_proposal': _stable(evidence.action_proposal),
        'receipt_action_ids': evidence.published_interval.action_ids,
        'effect_ids': _stable(evidence.published_interval.effect_ids),
        'target_hp': target.state.projected_hp,
        'target_position': evidence.target_position,
        'target_experience': evidence.target_experience,
        'target_run_rank': evidence.target_run_rank,
        'participant_state': participant_state,
        'historical_provenance': historical_provenance,
        'native_history_boundaries': native_history_boundaries,
        'native_practice_times': native_practice_times,
        'choice_counter': choice_counter,
        'new_receipt_issued': new_receipt_issued,
        'awareness': evidence.awareness,
        'batch_exercise': _stable(use),
        'practice_transition': _stable(practice.transitions[-1]),
        'practice_exercise_count': len(practice.exercises),
        'final_rng_state': repr(evidence.final_rng_state),
        'quarantined': evidence.quarantined_after_commit,
        'imported_receipt_registered': evidence.imported_receipt_registered,
    }


class TestTrustedLocalBoundary2Continuation(unittest.TestCase):
    def test_separate_process_resume_matches_uninterrupted_native_execution(self):
        """Fresh-process Run continuation matches an independent uninterrupted trace."""
        source_script = r'''
import base64, json, random, sys
sys.path.insert(0,sys.argv[1]); sys.path.insert(0,sys.argv[2])
from test_checkpoint_reconstruction import build_source
from test_checkpoint_restore_continuation import _stable
from activities import RunAction
from checkpoint_envelope import assemble_native_run_spot_envelope
from checkpoint_wire import encode_run_spot_envelope, decode_run_spot_wire
from checkpoint_projection import project_quarantined_run_boundary
from frozen_practice import freeze_imported_run_practice
import atomic_publication
world,enc,cursor,_envelope,_actions=build_source()
actor,participant=(world.get_object_by_id(i) for i in enc.being_list)
actor.skill_experience.pop('spot',None); actor.current.skills.skills.pop('spot',None)
initial_rng=repr(cursor.state)
first=RunAction(world,actor.id,0,1,.5,experience=4)
enc.schedule_choice((first,))
enc.step(1,velocities={actor.id:(1.0,0.0,0.0)})
wire=encode_run_spot_envelope(assemble_native_run_spot_envelope(
    world,enc,quiescent=True,rng_scope='exclusive_encounter'))
before=wire
projection=project_quarantined_run_boundary(decode_run_spot_wire(wire))
prefix=freeze_imported_run_practice(projection)
aid='c6-boundary2-run'
action=RunAction(world,actor.id,1,1,.1,experience=5,id=aid)
choice=enc.schedule_choice((action,))
enc.step(1,velocities={actor.id:(.25,0,0)})
assert repr(cursor.state)==initial_rng, 'Run-only uninterrupted path must not consume RNG'
history=enc.__dict__['_atomic_interval_history']
receipt=history[-1]
target=next(row for row in actor.__dict__['_atomic_target_history'] if row.boundary==2)
proposal=receipt.inspection.actions[aid][1]
practice=target.state.practice_state
use=practice.exercises[-1]
issued=atomic_publication._COMMITTED_RECEIPTS.get(id(receipt))
assert len(history)==2 and tuple(row.boundary for row in history)==(1,2)
assert issued is not None and issued[0]() is receipt and issued[1]() is enc
assert actor.skill_use_history[0].time==1 and actor.skill_use_history[1].time==2
participants=[]
for bid in sorted(enc.being_list):
    being=world.get_object_by_id(bid)
    participants.append((bid,tuple(being.get_position().as_tuple()),being.current.hit_points,
        dict(being.skill_experience),dict(being.current.skills.skills),
        (being.physical_fatigue.q,being.physical_fatigue.b),
        tuple(sorted(enc.awareness.get(bid,())))))
out={
 'wire':base64.b64encode(wire).decode('ascii'),
 'wire_sha256':__import__('hashlib').sha256(wire).hexdigest(),
 'continuation':{
            'boundary':receipt.boundary,'choice_id':choice.id,
 'choice_state':enc._choice_book.view(choice.id).state,'action_id':aid,
 'action_displacement':dict(proposal.metadata)['displacement'],
 'action_proposal':_stable(proposal),'receipt_action_ids':receipt.action_ids,
 'effect_ids':_stable(receipt.effect_ids),'target_hp':target.state.projected_hp,
 'target_position':tuple(actor.get_position().as_tuple()),
 'target_experience':dict(actor.skill_experience),
 'target_run_rank':actor.current.skills.skills.get('run',0),
 'awareness':tuple(sorted(enc.awareness.get(actor.id,()))),
 'batch_exercise':_stable(use),'practice_transition':_stable(practice.transitions[-1]),
 'practice_exercise_count':len(practice.exercises),
 'final_rng_state':repr(cursor.state),
 'participant_state':_stable(tuple(participants)),
 'historical_provenance':(prefix.schema,prefix.content_digest,prefix.encounter_id,
   prefix.choice_id,prefix.boundary,prefix.target_id,prefix.action_ids,
   _stable(prefix.uses[0]),
   tuple(row.identity for row in projection.effects)),
 'native_history_boundaries':tuple(row.boundary for row in history),
 'native_practice_times':tuple(row.time for row in actor.skill_use_history),
 'choice_counter':enc._choice_book._counter,
 'new_receipt_issued':issued[0]() is receipt}}
assert wire==before
print(json.dumps(out,separators=(',',':')))
'''
        source = subprocess.run([sys.executable, '-c', source_script,
            str(ROOT / 'src'), str(ROOT / 'tests')], cwd=ROOT,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        self.assertEqual(source.returncode, 0,
            source.stderr.decode('utf-8', errors='replace'))
        expected = json.loads(source.stdout)
        wire = base64.b64decode(expected.pop('wire'))
        self.assertEqual(hashlib.sha256(wire).hexdigest(), expected.pop('wire_sha256'))
        resume_script = r'''
import hashlib,json,sys
sys.path.insert(0,sys.argv[1]);sys.path.insert(0,sys.argv[2])
from checkpoint_wire import decode_run_spot_wire
from checkpoint_projection import project_quarantined_run_boundary
from checkpoint_binding import bind_quarantined_run_boundary
from frozen_practice import freeze_imported_run_practice
from checkpoint_restore_preparation import (_host_authorize_trusted_local_restore,
    _prepare_trusted_local_restore)
from checkpoint_restore_dependencies import (create_prepared_boundary2_read_dependency,
    preflight_boundary2_identity_ids)
from checkpoint_restore_continuation import _continue_one_run_boundary2
from checkpoint_restore_preparation import _PREPARED_RESTORES
from transactional_progression import is_quarantined
wire=sys.stdin.buffer.read(); before=hashlib.sha256(wire).hexdigest()
decoded=decode_run_spot_wire(wire); projection=project_quarantined_run_boundary(decoded)
binding=bind_quarantined_run_boundary(decoded,projection)
prepared=_prepare_trusted_local_restore(binding,_host_authorize_trusted_local_restore(binding))
dependency=create_prepared_boundary2_read_dependency(prepared)
private=_PREPARED_RESTORES[prepared]; enc=private.native.encounter
initial_rng=repr(private.native.rng_owner.state)
prefix=prepared.view.imported_history.practice_prefix
aid='c6-boundary2-run'
choice=f'{enc.id}/draft/{prepared.view.minimum_next_draft_suffix}'
preflight=preflight_boundary2_identity_ids(prepared,dependency,
 encounter_id=enc.id,practice_target_id=prefix.target_id,choice_id=choice,
 action_ids=(aid,),boundary=2)
evidence=_continue_one_run_boundary2(prepared,dependency,preflight,action_id=aid)
assert repr(private.native.rng_owner.state)==initial_rng, 'Run-only resumed path must not consume RNG'
book=enc._choice_book
state=book.view(evidence.choice_id).state
action=enc.universe.get_event_by_id(aid)
receipt=evidence.published_interval
issued=__import__('atomic_publication')._COMMITTED_RECEIPTS.get(id(receipt))
actor=enc.get_being(prefix.target_id)
participants=[]
for bid in sorted(enc.being_list):
 being=enc.get_being(bid)
 participants.append((bid,tuple(being.get_position().as_tuple()),being.current.hit_points,
  dict(being.skill_experience),dict(being.current.skills.skills),
  (being.physical_fatigue.q,being.physical_fatigue.b),
  tuple(sorted(enc.awareness.get(bid,())))))
historical=prepared.view.imported_history
history=enc.__dict__['_atomic_interval_history']
native_target_history=actor.__dict__.get('_atomic_target_history',())
provenance=(historical.practice_prefix.schema,historical.practice_prefix.content_digest,
 historical.practice_prefix.encounter_id,historical.practice_prefix.choice_id,
 historical.practice_prefix.boundary,historical.practice_prefix.target_id,
 historical.practice_prefix.action_ids,
 __import__('test_checkpoint_restore_continuation')._stable(
  historical.practice_prefix.uses[0]),
 tuple(row.identity for row in binding.historical.projection.effects))
assert hashlib.sha256(wire).hexdigest()==before
assert evidence.imported_history is prepared.view.imported_history
assert not evidence.imported_receipt_registered
assert evidence.quarantined_after_commit and is_quarantined(enc)
assert len(history)==1 and history[0].boundary==2
assert history[0] is evidence.published_interval
assert issued is not None and issued[0]() is receipt and issued[1]() is enc
assert evidence.action_id in evidence.published_interval.action_ids
assert enc._choice_book._counter==prepared.view.choice_counter_floor+1
assert book._states[aid]=='finished' and aid in book._registered
assert enc.universe.event_history[aid] is action
assert action.target_id is None and action.displacement is None
assert enc.time==2 and enc.last_processed_boundary==2
assert actor.skill_experience.get('run')==9
assert actor.current.skills.skills.get('run',0)==evidence.target_run_rank
assert [row.time for row in actor.skill_use_history]==[2]
assert [row.boundary for row in native_target_history]==[2]
assert dict(evidence.action_proposal.metadata)['displacement']==.25
try: enc.inspect_committed()
except Exception: pass
else: raise AssertionError('suffix-only native history must not masquerade as complete history')
try: enc.step(1)
except Exception: pass
else: raise AssertionError('quarantine must remain closed outside the private operation')
from checkpoint_restore_continuation import Boundary2ContinuationEvidence
from test_checkpoint_restore_continuation import _summary,_stable
participants=tuple(sorted((bid,tuple(enc.get_being(bid).get_position().as_tuple()),
 enc.get_being(bid).current.hit_points,dict(enc.get_being(bid).skill_experience),
 dict(enc.get_being(bid).current.skills.skills),
 (enc.get_being(bid).physical_fatigue.q,enc.get_being(bid).physical_fatigue.b),
 tuple(sorted(enc.awareness.get(bid,())))) for bid in enc.being_list))
summary=_summary(evidence,state,choice_counter=book._counter,
 action_displacement=dict(evidence.action_proposal.metadata)['displacement'],
 participant_state=_stable(participants),historical_provenance=provenance,
 native_history_boundaries=tuple(row.boundary for row in history),
 native_practice_times=tuple(row.time for row in actor.skill_use_history),
 new_receipt_issued=issued[0]() is receipt)
print(json.dumps(summary,separators=(',',':')))
'''
        resumed = subprocess.run([sys.executable, '-c', resume_script,
            str(ROOT / 'src'), str(ROOT / 'tests')], input=wire,
            cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        self.assertEqual(resumed.returncode, 0,
            resumed.stderr.decode('utf-8', errors='replace'))
        actual = json.loads(resumed.stdout)
        uninterrupted = expected['continuation']
        self.assertEqual(uninterrupted['native_history_boundaries'], [1, 2])
        self.assertEqual(uninterrupted['native_practice_times'], [1, 2])
        resumed_expected = {key: value for key, value in uninterrupted.items()
            if key not in ('native_history_boundaries', 'native_practice_times')}
        resumed_expected.update(
            quarantined=True,
            imported_receipt_registered=False,
            native_history_boundaries=[2],
            native_practice_times=[2],
        )
        self.assertEqual(actual, resumed_expected)

    def test_invalid_authorization_and_mismatched_preflight_refuse_without_mutation(self):
        wire, _ = committed_run_wire()
        prepared = _prepared(wire)
        private = _PREPARED_RESTORES[prepared]
        encounter = private.native.encounter
        dependency = create_prepared_boundary2_read_dependency(prepared)
        preflight = _preflight(prepared, dependency)
        before = (encounter.time, private.native.rng_owner.state,
            encounter._choice_book._counter, tuple(encounter._choice_book._choices),
            tuple(encounter.pending_action_list), tuple(encounter.__dict__.get('_atomic_interval_history', ())))
        with self.assertRaisesRegex(ContinuationRejected, 'host-authorized'):
            _continue_one_run_boundary2(object(), dependency, preflight,
                                         action_id='c6-boundary2-run')
        with self.assertRaises(ContinuationRejected):
            _continue_one_run_boundary2(prepared, dependency, object(),
                                         action_id='c6-boundary2-run')
        after = (encounter.time, private.native.rng_owner.state,
            encounter._choice_book._counter, tuple(encounter._choice_book._choices),
            tuple(encounter.pending_action_list), tuple(encounter.__dict__.get('_atomic_interval_history', ())))
        self.assertEqual(after, before)
        self.assertTrue(is_quarantined(encounter))

    def test_fault_after_practice_rolls_back_and_requires_no_history_rewrite(self):
        wire, _ = committed_run_wire()
        prepared = _prepared(wire)
        private = _PREPARED_RESTORES[prepared]
        encounter, world, cursor = (private.native.encounter,
            private.native.universe, private.native.rng_owner)
        dependency = create_prepared_boundary2_read_dependency(prepared)
        preflight = _preflight(prepared, dependency)
        book = encounter._choice_book
        before = (encounter.time, encounter.last_processed_boundary,
            encounter._coordinator_time, encounter._interval_start,
            cursor.state, book._counter, world._schedule_revision,
            tuple(world.event_history.items()), tuple(book._choices.items()),
            tuple(book._reservations), tuple(encounter.pending_action_list),
            tuple(encounter.finished_action_list),
            tuple((b.id, tuple(b.skill_use_history), tuple(b.__dict__.get('_atomic_target_history', ())),
                   dict(b.skill_experience), dict(b.current.skills.skills))
                  for _key, b in private.native.beings),
            tuple(id(value) for value in (world.event_history, book._choices,
                book._reservations, encounter.pending_action_list, encounter.finished_action_list)))
        original = atomic_publication.publish_interval_candidate
        def fail_after_practice(*args, **kwargs):
            kwargs['_fail_after'] = 'practice'
            return original(*args, **kwargs)
        with patch.object(atomic_publication, 'publish_interval_candidate', fail_after_practice):
            with self.assertRaises(ContinuationRejected):
                _continue_one_run_boundary2(prepared, dependency, preflight,
                                             action_id='c6-boundary2-run')
        after = (encounter.time, encounter.last_processed_boundary,
            encounter._coordinator_time, encounter._interval_start,
            cursor.state, book._counter, world._schedule_revision,
            tuple(world.event_history.items()), tuple(book._choices.items()),
            tuple(book._reservations), tuple(encounter.pending_action_list),
            tuple(encounter.finished_action_list),
            tuple((b.id, tuple(b.skill_use_history), tuple(b.__dict__.get('_atomic_target_history', ())),
                   dict(b.skill_experience), dict(b.current.skills.skills))
                  for _key, b in private.native.beings),
            tuple(id(value) for value in (world.event_history, book._choices,
                book._reservations, encounter.pending_action_list, encounter.finished_action_list)))
        self.assertEqual(after, before)
        self.assertEqual(encounter.boundary_fault, None)
        self.assertEqual(encounter.progression_mode, 'legacy')
        self.assertTrue(is_quarantined(encounter))
        self.assertEqual(atomic_publication._EMERGENCIES.get(id(world)), None)

    def test_candidate_construction_failure_discards_private_choice_and_mode(self):
        wire, _ = committed_run_wire()
        prepared = _prepared(wire)
        private = _PREPARED_RESTORES[prepared]
        encounter, world, cursor = (private.native.encounter,
            private.native.universe, private.native.rng_owner)
        dependency = create_prepared_boundary2_read_dependency(prepared)
        preflight = _preflight(prepared, dependency)
        book = encounter._choice_book
        before = (encounter.time, encounter.last_processed_boundary,
            cursor.state, book._counter, world._schedule_revision,
            tuple(world.event_history.items()), tuple(book._choices.items()),
            tuple(book._reservations), tuple(book._registered.items()),
            tuple(book._states.items()), tuple(encounter.pending_action_list),
            tuple(encounter.finished_action_list))
        import interval_staging
        with patch.object(interval_staging, 'build_supported_candidate',
                          side_effect=RuntimeError('injected candidate construction fault')):
            with self.assertRaises(ContinuationRejected):
                _continue_one_run_boundary2(prepared, dependency, preflight,
                                             action_id='c6-boundary2-run')
        after = (encounter.time, encounter.last_processed_boundary,
            cursor.state, book._counter, world._schedule_revision,
            tuple(world.event_history.items()), tuple(book._choices.items()),
            tuple(book._reservations), tuple(book._registered.items()),
            tuple(book._states.items()), tuple(encounter.pending_action_list),
            tuple(encounter.finished_action_list))
        self.assertEqual(after, before)
        self.assertEqual(encounter.progression_mode, 'legacy')
        self.assertEqual(encounter.boundary_fault, None)
        self.assertTrue(is_quarantined(encounter))

    def test_ordinary_transactional_enable_still_refuses_restored_time(self):
        wire, _ = committed_run_wire()
        prepared = _prepared(wire)
        encounter = _PREPARED_RESTORES[prepared].native.encounter
        with self.assertRaises(TransactionalProgressionError):
            encounter.enable_transactional_progression(quiescent=True,
                rng_owner=_PREPARED_RESTORES[prepared].native.rng_owner)
        self.assertEqual(encounter.progression_mode, 'legacy')


if __name__ == '__main__':
    unittest.main()
