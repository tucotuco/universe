import hashlib
import json
import os
import subprocess
import sys
import unittest
from dataclasses import replace

from arena_browser_session import GeneratedArenaSession
from checkpoint_binding import (IdentityBindingRejected,
    bind_quarantined_movement_boundary)
from checkpoint_envelope import assemble_native_run_spot_envelope
from checkpoint_projection import project_quarantined_movement_boundary
from checkpoint_wire import (DecodedRunSpotWire, WireRejected,
    decode_run_spot_wire, encode_detached_run_spot_data,
    encode_run_spot_envelope)


_FRESH_PROCESS = r'''
import hashlib, json, sys
assert 'npcgen' not in sys.modules
from checkpoint_wire import decode_run_spot_wire
from checkpoint_binding import bind_quarantined_movement_boundary
decoded = decode_run_spot_wire(sys.stdin.buffer.read())
bound = bind_quarantined_movement_boundary(decoded)
sidecar = bound.sidecar
digest = lambda value: hashlib.sha256(repr(value).encode()).hexdigest()
print(json.dumps({
  'schema': bound.schema,
  'universe': bound.universe_id,
  'encounter': bound.encounter_id,
  'boundary': bound.boundary,
  'participants': sidecar.participant_identity_ids,
  'definitions': [(row[0], digest(row[1]), digest(row[2]))
                  for row in sidecar.participant_definition_values],
  'activation': sidecar.movement_activation,
  'targets': sidecar.target_record_identity_ids,
  'observers': [(row[0], row[1], row[2], len(row[3]), digest(row[4]))
                for row in sidecar.observer_evidence],
  'rng': digest(sidecar.rng_state),
  'actions': sidecar.action_ids,
  'choices': sidecar.choice_ids,
  'effects': sidecar.effect_ids,
  'quarantined': bound.quarantined
}))
'''


def _digest(value):
    return hashlib.sha256(repr(value).encode()).hexdigest()


class MovementOnlyIdentityBindingTests(unittest.TestCase):
    def _source(self):
        session = GeneratedArenaSession(root_seed_factory=lambda: 20261120)
        session.generate({'starting_experience': '10000',
                          'width_cells': '5', 'height_cells': '5'})
        candidate = session.active_candidate
        encounter = candidate.encounter
        player = candidate.participants[0].native.being
        origin = candidate.arena_map.layout.cell_at_position(player.get_position())
        destination = next(address for address in candidate.arena_map.layout.addresses()
                           if address != origin)
        session.choose_destination({'column': destination.column,
            'row': destination.row, 'rate': 'sprint', 'facing_policy': 'turn'})
        session.advance_one_second()
        envelope = assemble_native_run_spot_envelope(candidate.universe, encounter,
            quiescent=True, rng_scope='exclusive_encounter')
        decoded = decode_run_spot_wire(encode_run_spot_envelope(envelope))
        return session, envelope, decoded

    def test_fixed_seed_movement_boundary_binds_in_fresh_process(self):
        session, envelope, decoded = self._source()
        candidate = session.active_candidate
        bindings = bind_quarantined_movement_boundary(decoded)
        sidecar = bindings.sidecar
        self.assertTrue(bindings.quarantined)
        self.assertEqual((bindings.encounter_id, bindings.boundary),
                         (candidate.encounter.id, 1))
        self.assertEqual(set(row[0] for row in sidecar.participant_identity_ids),
                         set(row.native.being.id for row in candidate.participants))
        expected_definitions = []
        from checkpoint_reconstruction import _projection
        for being_id, _ref in sidecar.participant_identity_ids:
            being = candidate.universe.get_object_by_id(being_id)
            expected_definitions.append((being_id,
                _digest(_projection(being.original)),
                _digest(_projection(being.current))))
        expected_definitions.sort()
        self.assertEqual(tuple(sorted(row[0] for row in sidecar.target_record_identity_ids)),
                         tuple(sorted(row[0] for row in sidecar.projection.target_records)))
        self.assertEqual(sidecar.action_ids, ())
        self.assertEqual(sidecar.choice_ids, ())
        self.assertEqual(sidecar.effect_ids, ())

        process = subprocess.run([sys.executable, '-c', _FRESH_PROCESS],
            input=encode_run_spot_envelope(envelope), stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, cwd=os.getcwd(), env={**os.environ,
                'PYTHONPATH': os.pathsep.join((os.path.abspath('src'),
                                                os.environ.get('PYTHONPATH', '')))},
            check=False, timeout=120)
        self.assertEqual(process.returncode, 0, process.stderr.decode(errors='replace'))
        child = json.loads(process.stdout)
        self.assertEqual(child['schema'], bindings.schema)
        self.assertEqual(child['universe'], candidate.universe.id)
        self.assertEqual(child['encounter'], candidate.encounter.id)
        self.assertEqual(child['boundary'], 1)
        self.assertEqual(child['activation'], list(sidecar.movement_activation))
        self.assertEqual(child['participants'], json.loads(json.dumps(
            sidecar.participant_identity_ids)))
        self.assertEqual(sorted(child['definitions']), [list(row) for row in expected_definitions])
        self.assertEqual(child['targets'], json.loads(json.dumps(
            sidecar.target_record_identity_ids)))
        self.assertEqual(child['observers'], [
            [row[0], row[1], list(row[2]), len(row[3]), _digest(row[4])]
            for row in sidecar.observer_evidence])
        self.assertEqual(child['rng'], _digest(sidecar.rng_state))
        self.assertEqual(child['actions'], [])
        self.assertEqual(child['choices'], [])
        self.assertEqual(child['effects'], [])
        self.assertTrue(child['quarantined'])
        self.assertEqual(envelope.to_data()[12:16], (True, False, False, False))

    def test_movement_receipt_rejects_corrupted_rows_without_source_mutation(self):
        session, _envelope, decoded = self._source()
        encounter = session.active_candidate.encounter
        before = (encounter.time, encounter.last_processed_boundary,
            encounter._choice_book._counter, tuple(encounter._atomic_interval_history),
            encounter.arena_movement_activation, session._movement_plan,
            tuple((key, tuple(value)) for key, value in encounter.awareness.items()),
            session._rng_cursor.state,
            tuple((participant.native.being.id,
                   tuple(participant.native.being.get_position().as_tuple()))
                  for participant in session.active_candidate.participants))
        data = list(decoded.envelope_data)
        chain = list(data[8])
        row = list(chain[4][0])
        bad_cases = []
        wrong_boundary = list(row); wrong_boundary[1] = 2
        bad_cases.append(('wrong boundary', tuple(wrong_boundary)))
        missing_target = list(row); missing_target[4] = row[4][:-1]
        bad_cases.append(('missing Target', tuple(missing_target)))
        duplicate_target = list(row); duplicate_target[4] = (row[4][0], row[4][0])
        bad_cases.append(('duplicate Target', tuple(duplicate_target)))
        synthetic_action = tuple(row) + (('invented-action',),)
        bad_cases.append(('synthetic Action', synthetic_action))
        changed_target = list(row[4][0])
        changed_target_state = list(changed_target[3])
        changed_fields = list(changed_target_state[1])
        changed_fields[8] = ('aware_of', ('set', ()))
        changed_target_state[1] = tuple(changed_fields)
        changed_target[3] = tuple(changed_target_state)
        mutated_receipt = list(row)
        mutated_receipt[4] = (tuple(changed_target), row[4][1])
        bad_cases.append(('mutated Target state', tuple(mutated_receipt)))
        for label, bad_row in bad_cases:
            changed_chain = list(chain); changed_chain[4] = (bad_row,)
            changed = list(data); changed[8] = tuple(changed_chain)
            forged = replace(decoded, envelope_data=tuple(changed))
            with self.subTest(case=label), self.assertRaises((IdentityBindingRejected, WireRejected)):
                bind_quarantined_movement_boundary(forged)
        changed_choices = list(data); changed_choices[7] = (('invented-choice',),)
        with self.assertRaises((IdentityBindingRejected, WireRejected)):
            bind_quarantined_movement_boundary(replace(decoded,
                envelope_data=tuple(changed_choices)))
        later_chain = list(decoded.envelope_data[8])
        later = list(row); later[1] = 2; later[2] = ('integer', '1')
        later_chain[4] = (tuple(row), tuple(later))
        later_data = list(decoded.envelope_data); later_data[4] = (1, 2)
        later_data[8] = tuple(later_chain)
        with self.assertRaises((IdentityBindingRejected, WireRejected)):
            bind_quarantined_movement_boundary(replace(decoded,
                envelope_data=tuple(later_data)))

        # A native activation-phase mutation must fail before any binding result.
        altered_data = list(decoded.envelope_data)
        inventory = list(altered_data[5])
        nodes_index = next(index for index, section in enumerate(inventory)
                           if section[0] == 'nodes')
        nodes = list(inventory[nodes_index][1])
        encounter_node_index = next(index for index, node in enumerate(nodes)
                                    if node[0] == ('encounter', decoded.envelope_data[2]))
        encounter_node = list(nodes[encounter_node_index])
        encounter_fields = list(encounter_node[2])
        activation_ref = next(value[1] for key, value in encounter_fields
                              if key == 'arena_movement_activation')
        activation_node_index = next(index for index, node in enumerate(nodes)
                                     if node[0] == activation_ref)
        activation_node = list(nodes[activation_node_index])
        activation_fields = list(activation_node[2])
        activation_fields = [(key, ('string', 'wrong-phase') if key == 'activation_kind'
                              else value) for key, value in activation_fields]
        activation_node[2] = tuple(activation_fields)
        nodes[activation_node_index] = tuple(activation_node)
        inventory[nodes_index] = ('nodes', tuple(nodes))
        altered_data[5] = tuple(inventory)
        with self.assertRaises((IdentityBindingRejected, WireRejected)):
            bind_quarantined_movement_boundary(replace(decoded,
                envelope_data=tuple(altered_data)))

        from checkpoint_reconstruction import _Graph, _sections
        graph = _Graph(_sections(decoded.envelope_data[5])['nodes'][0])
        universe_ref = ('universe', decoded.envelope_data[1])
        universe_fields = graph.fields(universe_ref)[1]
        registry = graph.raw_mapping(graph.fields(
            graph.raw_ref(universe_fields['object_registry']))[1]['object_instances'])
        owner_id = decoded.envelope_data[8][4][0][4][0][0]
        being_ref = graph.raw_ref(registry[owner_id])
        history_ref = graph.raw_ref(graph.fields(being_ref)[1]['_atomic_target_history'])
        source_state = decoded.envelope_data[5]
        def mutate_history(replacement):
            state = list(source_state)
            node_section = next(index for index, row in enumerate(state)
                               if row[0] == 'nodes')
            nodes = list(state[node_section][1])
            history_node = next(index for index, node in enumerate(nodes)
                                if node[0] == history_ref)
            row = list(nodes[history_node]); row[2] = replacement
            nodes[history_node] = tuple(row)
            state[node_section] = ('nodes', tuple(nodes))
            changed = list(decoded.envelope_data); changed[5] = tuple(state)
            return replace(decoded, envelope_data=tuple(changed))
        original_history = graph.nodes[history_ref][1]
        for replacement, label in (((), 'missing native Target history'),
                                   ((original_history[0], original_history[0]),
                                    'duplicate native Target history')):
            with self.subTest(case=label), self.assertRaises(IdentityBindingRejected):
                bind_quarantined_movement_boundary(mutate_history(replacement))
        after = (encounter.time, encounter.last_processed_boundary,
            encounter._choice_book._counter, tuple(encounter._atomic_interval_history),
            encounter.arena_movement_activation, session._movement_plan,
            tuple((key, tuple(value)) for key, value in encounter.awareness.items()),
            session._rng_cursor.state,
            tuple((participant.native.being.id,
                   tuple(participant.native.being.get_position().as_tuple()))
                  for participant in session.active_candidate.participants))
        self.assertEqual(after, before)


if __name__ == '__main__':
    unittest.main()
