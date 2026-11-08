"""Quarantine-only native identity binding for the closed Run projection."""
from dataclasses import FrozenInstanceError, fields, is_dataclass, replace
import json
import random
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tests'))

from checkpoint_binding import (IdentityBindingRejected,
    QuarantinedRunIdentityBinding, _NATIVE_BINDINGS,
    _native_state_value, bind_quarantined_run_boundary)
from checkpoint_projection import project_quarantined_run_boundary
from checkpoint_wire import (DecodedRunSpotWire, decode_run_spot_wire,
    encode_run_spot_envelope)
from frozen_practice import freeze_imported_run_practice
from test_checkpoint_projection import committed_run_wire


def _assert_immutable_tree(test, value):
    if is_dataclass(value):
        test.assertTrue(type(value).__dataclass_params__.frozen)
        for field in fields(value):
            _assert_immutable_tree(test, getattr(value, field.name))
    elif type(value) is tuple:
        for item in value:
            _assert_immutable_tree(test, item)
    else:
        test.assertIn(type(value), (type(None), str, bool, int, float))


def _receipt_registry_snapshot():
    """Keep weak references, not their targets, while recording registry rows."""
    from atomic_publication import _COMMITTED_RECEIPTS
    return {key: (row[0], row[1], row[2])
            for key, row in tuple(_COMMITTED_RECEIPTS.items())}


def _assert_binding_receipt_isolation(test, before, binding_result):
    """Authenticate registry deltas and reject any receipt owned by this bind.

    The registry is process-wide: valid publisher commits from other Encounters
    can coexist with a quarantined binding. Preserve the unchanged rows, verify
    any new/replaced row against its actual Encounter history and fingerprint,
    and require the newly reconstructed Encounter itself to have no receipt.
    """
    import atomic_publication
    from checkpoint_binding import _NATIVE_BINDINGS
    from encounter_inspection import fingerprint

    encounter = _NATIVE_BINDINGS[binding_result].encounter
    test.assertEqual(tuple(encounter.__dict__.get('_atomic_interval_history', ())), ())
    after = _receipt_registry_snapshot()

    # Existing live rows are neither replaced nor altered by binding.
    for key, (receipt_ref, encounter_ref, digest) in before.items():
        receipt, owner = receipt_ref(), encounter_ref()
        if receipt is None or owner is None:
            continue  # weak-reference cleanup is the documented registry lifetime
        test.assertIn(key, after)
        current_receipt_ref, current_encounter_ref, current_digest = after[key]
        test.assertIs(current_receipt_ref(), receipt)
        test.assertIs(current_encounter_ref(), owner)
        test.assertEqual(current_digest, digest)
        test.assertEqual(fingerprint(receipt), digest)

    # Every changed/new row must be a live, fingerprint-authenticated publisher
    # receipt retained by its owning Encounter. None may belong to this bind.
    for key, (receipt_ref, encounter_ref, digest) in after.items():
        old = before.get(key)
        unchanged = (old is not None and old[0] is receipt_ref
                     and old[1] is encounter_ref and old[2] == digest)
        if unchanged:
            continue
        receipt, owner = receipt_ref(), encounter_ref()
        test.assertIsNotNone(receipt, 'new receipt registry row is already dead')
        test.assertIsNotNone(owner, 'new receipt registry owner is already dead')
        test.assertEqual(key, id(receipt))
        test.assertIsNot(owner, encounter,
                         'quarantined binding registered a receipt for its Encounter')
        history = owner.__dict__.get('_atomic_interval_history', ())
        test.assertTrue(any(row is receipt for row in history),
                        'registry row is not retained by its owning Encounter history')
        test.assertEqual(fingerprint(receipt), digest,
                         'registry row does not authenticate its committed receipt')
    test.assertFalse(any(row[1]() is encounter
                         for row in atomic_publication._COMMITTED_RECEIPTS.values()))


class TestQuarantinedRunIdentityBinding(unittest.TestCase):
    def test_explicit_unknown_and_authored_hex_facing_survive_binding(self):
        from activities import RunAction
        from checkpoint_envelope import assemble_native_run_spot_envelope
        from test_checkpoint_reconstruction import build_source

        world, encounter, _cursor, _, _ = build_source()
        actor, observed = (world.get_object_by_id(identity)
                           for identity in encounter.being_list)
        actor.set_hex_facing(0)
        observed.set_hex_facing(None)
        action = RunAction(world, actor.id, 0, 1, .5, experience=4)
        encounter.schedule_choice((action,))
        encounter.step(1, velocities={actor.id: (1, 0, 0)})
        envelope = assemble_native_run_spot_envelope(
            world, encounter, quiescent=True, rng_scope='exclusive_encounter')
        decoded = decode_run_spot_wire(encode_run_spot_envelope(envelope))
        result = bind_quarantined_run_boundary(decoded)
        private = _NATIVE_BINDINGS[result]
        beings = dict(private.beings)
        self.assertEqual(beings[actor.id].hex_facing, 0)
        self.assertIsNone(beings[observed.id].hex_facing)

    def test_binding_receipt_check_is_scoped_while_unrelated_interval_commits(self):
        wire, _ = committed_run_wire()
        decoded = decode_run_spot_wire(wire)
        projection = project_quarantined_run_boundary(decoded)
        receipt_snapshot = _receipt_registry_snapshot()

        # Deterministically register a genuine receipt for an unrelated
        # Encounter between the snapshot and binding. The former process-global
        # set equality necessarily failed in this valid situation.
        from test_interval_staging import TestIntervalStaging
        fixture = TestIntervalStaging()
        fixture.setUp()
        fixture.enable_native_step()
        unrelated_encounter = fixture.enc
        unrelated_encounter.step(1)
        unrelated_receipt, = unrelated_encounter._atomic_interval_history
        self.assertEqual(unrelated_receipt.action_ids, ())

        result = bind_quarantined_run_boundary(decoded, projection)
        _assert_binding_receipt_isolation(self, receipt_snapshot, result)
        from atomic_publication import _COMMITTED_RECEIPTS
        unrelated_row = _COMMITTED_RECEIPTS[id(unrelated_receipt)]
        self.assertIs(unrelated_row[0](), unrelated_receipt)
        self.assertIs(unrelated_row[1](), unrelated_encounter)
        self.assertNotEqual(set(_COMMITTED_RECEIPTS), set(receipt_snapshot))

    def test_one_run_binding_is_private_and_imported_practice_is_not_replayed(self):
        wire, source_batch = committed_run_wire()
        decoded = decode_run_spot_wire(wire)
        projection = project_quarantined_run_boundary(decoded)
        module_rng = random.getstate()
        receipt_snapshot = _receipt_registry_snapshot()
        from encounter import Encounter
        with patch.object(Encounter, 'step', side_effect=AssertionError('step called')) as step, \
             patch.object(Encounter, '_advance', side_effect=AssertionError('_advance called')) as advance, \
             patch.object(Encounter, 'resolve_actions', side_effect=AssertionError('resolver called')) as resolve:
            result = bind_quarantined_run_boundary(decoded, projection)
        step.assert_not_called()
        advance.assert_not_called()
        resolve.assert_not_called()
        self.assertIs(type(result), QuarantinedRunIdentityBinding)
        self.assertTrue(result.quarantined)
        self.assertEqual(random.getstate(), module_rng)
        _assert_binding_receipt_isolation(self, receipt_snapshot, result)
        for public_name in ('universe', 'encounter', 'rng_owner', 'native', 'native_graph'):
            self.assertFalse(hasattr(result, public_name))
        _assert_immutable_tree(self, result.view)
        _assert_immutable_tree(self, result.historical)

        binding = _NATIVE_BINDINGS[result]
        beings, actions = dict(binding.beings), dict(binding.actions)
        self.assertEqual(len(actions), 1)
        self.assertEqual(set(beings), set(result.historical.being_identity_ids))
        self.assertEqual(set(beings), set(result.historical.target_identity_ids))
        self.assertEqual(len(beings), 2)
        self.assertEqual(len({id(value) for value in beings.values()}), 2)
        self.assertEqual(len({id(value) for value in actions.values()}), 1)
        action_view, = result.view.actions
        action, = actions.values()
        self.assertEqual((action_view.logical_id, action.id), (action.id, action_view.logical_id))
        self.assertEqual(action_view.family, 'native.run-action/1')
        self.assertEqual(action_view.actor_id, action.actor_id)
        self.assertFalse(hasattr(action_view, 'observed_id'))
        self.assertIsNone(action.displacement)
        self.assertIsNone(action.resolution)
        self.assertIsNone(getattr(action, '_encounter', None))
        self.assertNotIn(action.id, binding.universe.event_history)
        self.assertEqual(set(binding.universe.event_history), {'0', projection.encounter_id})
        self.assertFalse(binding.encounter._choice_book._choices)
        self.assertFalse(binding.encounter._choice_book._registered)
        self.assertFalse(binding.encounter._choice_book._states)
        self.assertFalse(binding.encounter._choice_book._reservations)
        self.assertTrue(all(not being.skill_use_history for being in beings.values()))
        self.assertTrue(all(not hasattr(being, '_atomic_target_history') for being in beings.values()))

        self.assertEqual((binding.encounter.start_time, binding.encounter.time,
                          binding.encounter.last_processed_boundary), (0, 1, 1))
        self.assertEqual(result.view.boundary, 1)
        self.assertEqual(result.view.actions[0].start, projection.actions[0].start)
        self.assertEqual(result.view.actions[0].end, projection.actions[0].end)
        self.assertEqual(result.historical.projection.to_data(), projection.to_data())
        self.assertEqual(result.historical.choice_id, projection.committed_choices[0][0])
        self.assertEqual(result.historical.action_identity_ids, (action.id,))
        self.assertEqual(result.historical.action_effect_links,
                         ((action.id, projection.actions[0].effect_ids),))

        targets = {row.target_id: row for row in projection.targets}
        for logical_id, being in beings.items():
            target = targets[logical_id]
            self.assertEqual(being.current.hit_points, int(target.resulting_hp[1]))
            self.assertEqual(tuple(being.get_position().as_tuple()),
                tuple(float.fromhex(value[1]) for value in target.position[1]))
        prefix = freeze_imported_run_practice(result.historical)
        self.assertEqual(prefix.target_id, action.actor_id)
        self.assertEqual(prefix.action_ids, (action.id,))
        self.assertEqual(len(prefix.uses), 1)
        imported = prefix.uses[0]
        self.assertEqual((imported.skill_name, imported.experience, imported.time),
                         ('run', source_batch['experience'], 1))
        self.assertEqual(tuple(row.action_id for row in imported.exercises), (action.id,))
        self.assertEqual(tuple(row.effect_identity.source_action_id
                               for row in imported.exercises), (action.id,))
        actor = beings[action.actor_id]
        self.assertEqual(actor.skill_experience.get('run'), source_batch['experience'])
        self.assertEqual(actor.skill_use_history, [])
        self.assertEqual(binding.rng_owner.state, result.view.rng_state)

        before_view, before_history = result.view, result.historical
        actor.set_hit_points(99)
        action.start_time = 88
        self.assertEqual(result.view, before_view)
        self.assertEqual(result.historical, before_history)
        from transactional_progression import is_quarantined, TransactionalProgressionError
        self.assertTrue(is_quarantined(binding.universe))
        self.assertTrue(is_quarantined(binding.encounter))
        self.assertTrue(all(is_quarantined(value) for value in beings.values()))
        self.assertTrue(is_quarantined(action))
        with self.assertRaises(TransactionalProgressionError):
            action.resolve(10)
        with self.assertRaisesRegex(ValueError, 'Quarantined'):
            binding.universe.add_object(next(iter(beings.values())))
        with self.assertRaises(TransactionalProgressionError):
            binding.encounter.step(1)
        with self.assertRaises(TransactionalProgressionError):
            binding.encounter.run()

    def test_native_encounter_choice_and_target_associations_match_sidecar(self):
        wire, _ = committed_run_wire()
        decoded = decode_run_spot_wire(wire)
        projection = project_quarantined_run_boundary(decoded)
        result = bind_quarantined_run_boundary(decoded, projection)
        private = _NATIVE_BINDINGS[result]
        beings, actions = dict(private.beings), dict(private.actions)
        sidecar = result.historical
        self.assertIs(private.encounter.universe, private.universe)
        self.assertEqual(set(private.encounter.being_list), set(sidecar.being_identity_ids))
        for being_id, being in beings.items():
            self.assertIs(private.universe.get_object_by_id(being_id), being)
            self.assertIs(private.encounter.get_being(being_id), being)
        self.assertEqual(sidecar.choice_id, projection.committed_choices[0][0])
        self.assertEqual(projection.committed_choices[0][3], sidecar.action_identity_ids)
        self.assertEqual(tuple(actions), sidecar.action_identity_ids)
        self.assertEqual(sidecar.target_identity_ids,
                         tuple(row.target_id for row in projection.targets))
        self.assertEqual(sidecar.action_effect_links,
                         tuple((row.action_id, row.effect_ids) for row in projection.actions))
        self.assertEqual(len(sidecar.batch_practice), 1)
        self.assertEqual(sidecar.batch_practice[0].target_id, projection.actions[0].actor_id)
        self.assertEqual(tuple(row.action_id for row in sidecar.batch_practice[0].exercises),
                         sidecar.action_identity_ids)
        self.assertTrue(private.encounter.quarantined if hasattr(private.encounter, 'quarantined')
                        else True)
        _assert_immutable_tree(self, result.view)
        _assert_immutable_tree(self, sidecar)

    def test_separate_process_decode_binding_and_run_practice_preserve_ids(self):
        wire, _ = committed_run_wire()
        projection = project_quarantined_run_boundary(decode_run_spot_wire(wire))
        expected_action = projection.actions[0].action_id
        expected_beings = sorted(row.target_id for row in projection.targets)
        script = r'''
import json,random,sys
sys.path.insert(0,sys.argv[1])
from checkpoint_wire import decode_run_spot_wire
from checkpoint_projection import project_quarantined_run_boundary
from checkpoint_binding import bind_quarantined_run_boundary,_NATIVE_BINDINGS
from frozen_practice import freeze_imported_run_practice
from atomic_publication import _COMMITTED_RECEIPTS
before=random.getstate(); receipts=set(_COMMITTED_RECEIPTS)
d=decode_run_spot_wire(sys.stdin.buffer.read()); p=project_quarantined_run_boundary(d)
r=bind_quarantined_run_boundary(d,p); private=_NATIVE_BINDINGS[r]
prefix=freeze_imported_run_practice(r.historical)
assert random.getstate()==before and set(_COMMITTED_RECEIPTS)==receipts
assert len(private.actions)==1 and len(private.beings)==2
assert not any(hasattr(r,k) for k in ('universe','encounter','rng_owner','native'))
assert private.encounter._choice_book._counter == 0
print(json.dumps({'action':r.historical.action_identity_ids[0],
 'beings':sorted(r.historical.being_identity_ids),'target':prefix.target_id,
 'skill':prefix.uses[0].skill_name,'xp':prefix.uses[0].experience,
 'practice_action':prefix.uses[0].exercises[0].action_id,
 'rng_pure':random.getstate()==before}))
'''
        proc = subprocess.run([sys.executable, '-c', script, str(ROOT / 'src')],
            input=wire, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            cwd=str(ROOT), check=False)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode('utf-8', errors='replace'))
        output = json.loads(proc.stdout)
        self.assertEqual(output['action'], expected_action)
        self.assertEqual(output['practice_action'], expected_action)
        self.assertEqual(output['beings'], expected_beings)
        self.assertEqual(output['target'], projection.actions[0].actor_id)
        self.assertEqual((output['skill'], output['xp']), ('run', 4))
        self.assertTrue(output['rng_pure'])

    def test_tampering_wrong_identity_extra_action_and_unsupported_cases_refuse(self):
        wire, _ = committed_run_wire()
        decoded = decode_run_spot_wire(wire)
        projection = project_quarantined_run_boundary(decoded)
        with self.assertRaisesRegex(IdentityBindingRejected, 'projection'):
            bind_quarantined_run_boundary(decoded, replace(projection, boundary=9))
        tampered_data = list(decoded.envelope_data)
        tampered_data[2] = 'altered-encounter-id'
        tampered = DecodedRunSpotWire(decoded.schema, tuple(tampered_data), decoded.wire_digest)
        with self.assertRaisesRegex(IdentityBindingRejected, '(?i)wire|digest'):
            bind_quarantined_run_boundary(tampered)
        # A duplicate/fabricated second historical Action is outside the one-Run contract.
        duplicate = replace(projection.actions[0], action_id='invented-run-action')
        with self.assertRaises(IdentityBindingRejected):
            bind_quarantined_run_boundary(decoded, replace(projection,
                actions=(projection.actions[0], duplicate)))
        for kwargs in ({'kind': 'two-boundaries'}, {'future': True}):
            unsupported_wire, _ = committed_run_wire(**kwargs)
            with self.subTest(kwargs=kwargs), self.assertRaises(IdentityBindingRejected):
                bind_quarantined_run_boundary(decode_run_spot_wire(unsupported_wire))

    def test_stale_target_practice_and_identity_sidecar_refuse_without_public_result(self):
        wire, _ = committed_run_wire()
        decoded = decode_run_spot_wire(wire)
        projection = project_quarantined_run_boundary(decoded)
        binding = bind_quarantined_run_boundary(decoded, projection)
        published = set(_NATIVE_BINDINGS)
        altered_action = replace(projection.actions[0], effect_ids=())
        with self.assertRaises(IdentityBindingRejected):
            bind_quarantined_run_boundary(decoded, replace(projection, actions=(altered_action,)))
        self.assertEqual(set(_NATIVE_BINDINGS), published)
        altered_target = replace(projection.targets[0], target_id='foreign-being')
        with self.assertRaises(IdentityBindingRejected):
            bind_quarantined_run_boundary(decoded, replace(projection,
                targets=(altered_target, projection.targets[1])))
        self.assertEqual(set(_NATIVE_BINDINGS), published)
        prefix = freeze_imported_run_practice(binding.historical)
        self.assertEqual(prefix.action_ids, binding.historical.action_identity_ids)

    def test_forged_imported_practice_owner_and_experience_refuse(self):
        wire, _ = committed_run_wire()
        result = bind_quarantined_run_boundary(decode_run_spot_wire(wire))
        sidecar = result.historical
        bad_batch = replace(sidecar.batch_practice[0], target_id='wrong-target')
        from dataclasses import replace as dc_replace
        malformed = dc_replace(sidecar, batch_practice=(bad_batch,))
        with self.assertRaises(ValueError):
            freeze_imported_run_practice(malformed)
        bad_projection = replace(sidecar.projection, actions=(
            replace(sidecar.projection.actions[0], outcome='failure'),))
        malformed = dc_replace(sidecar, projection=bad_projection)
        with self.assertRaises(ValueError):
            freeze_imported_run_practice(malformed)

    def test_initial_reconstruction_and_committed_refusal_remain_separate(self):
        from checkpoint_reconstruction import ReconstructionRejected, reconstruct_initial_run_spot
        wire, _ = committed_run_wire()
        with self.assertRaisesRegex(ReconstructionRejected, 'committed boundaries are refused'):
            reconstruct_initial_run_spot(decode_run_spot_wire(wire))

    def _fresh_constructor_plan(self, *, time=1, being_ids=None,
                                awareness=None, rng_state=None, add_book=False,
                                add_event=False):
        from atomic_publication import RNGCursor
        from being import BeingDefinition, BeingDictionary, BeingInstance
        from encounter import _QuarantinedPostBoundaryPlan
        from identifiable import Identifiable
        from library import Library
        from universe import Universe
        library = Library(load_definitions=False, name='factory test')
        dictionary = BeingDictionary()
        definition = BeingDefinition('Factory Test', 1, 1, 10, '1d4', 'N', 10, 1)
        dictionary.objects = {definition.obj_type: definition}
        library.being_dictionary = dictionary
        world = Universe('factory test', library=library)
        registry_ids = ('factory-actor', 'factory-participant')
        ids = tuple(being_ids or registry_ids)
        for logical_id, name in zip(registry_ids, ('Actor', 'Participant')):
            being = BeingInstance(definition, name=name)
            Identifiable.__init__(being, name, id=logical_id)
            world.add_object(being)
        awareness = awareness or tuple((logical_id, ()) for logical_id in ids)
        state = rng_state if rng_state is not None else random.Random(7).getstate()
        plan = _QuarantinedPostBoundaryPlan(world, 'factory-encounter', 0, time, 10,
            'Quarantined test', None, None, None, None, True, ids, awareness, RNGCursor(state))
        if add_book:
            world._choice_books.append(object())
        if add_event:
            from event import Event
            world.add_event(Event(world, 0, name='unsupported', id='unsupported'))
        return world, plan

    def test_ordinary_advanced_constructor_refusal_is_unchanged(self):
        from encounter import BoundaryInvariantError, Encounter
        world, plan = self._fresh_constructor_plan()
        with self.assertRaisesRegex(BoundaryInvariantError,
                'Restoring an advanced Encounter requires an unsupported checkpoint migration'):
            Encounter(world, 10, 0, time=1, id=plan.encounter_id,
                      being_list=list(plan.being_ids))
        self.assertEqual(set(world.event_history), {'0'})
        self.assertEqual(world._choice_books, [])

    def test_private_constructor_rejects_invalid_context_without_partial_registration(self):
        from encounter import BoundaryInvariantError, Encounter
        cases = [
            ('wrong time', {'time': 2}, '0-to-1'),
            ('mismatched participant', {'being_ids': ('factory-actor', 'missing')}, 'registry'),
            ('ambiguous participants', {'being_ids': ('factory-actor', 'factory-actor')}, 'distinct'),
            ('unknown awareness reference', {'awareness': (('factory-actor', ('missing',)),
                                                           ('factory-participant', ()))}, 'awareness'),
            ('invalid RNG', {'rng_state': ('not', 'an', 'rng', 'state')}, 'RNG'),
            ('preexisting choice state', {'add_book': True}, 'scheduling state'),
            ('preexisting event history', {'add_event': True}, 'origin Event'),
        ]
        module_rng_before = random.getstate()
        for label, options, message in cases:
            with self.subTest(label=label):
                world, plan = self._fresh_constructor_plan(**options)
                before_events, before_books = dict(world.event_history), list(world._choice_books)
                with self.assertRaisesRegex(BoundaryInvariantError, message):
                    Encounter._construct_quarantined_post_boundary(plan)
                self.assertEqual(world.event_history, before_events)
                self.assertEqual(world._choice_books, before_books)
                self.assertEqual(world._schedule_revision, 0)
                self.assertEqual(random.getstate(), module_rng_before)


if __name__ == '__main__':
    unittest.main()
