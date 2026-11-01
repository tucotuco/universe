"""Strict detached wire-format tests for bounded Run/Spot envelopes."""
import random
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tests'))

import test_interval_staging as interval_fixtures
from activities import RunAction
from atomic_publication import RNGCursor
from checkpoint_envelope import (
    assemble_native_run_spot_envelope,
    validate_native_run_spot_envelope,
)
from checkpoint_wire import (
    WIRE_SCHEMA,
    WireRejected,
    decode_run_spot_wire,
    encode_detached_run_spot_data,
    encode_run_spot_envelope,
    reencode_decoded_run_spot_wire,
)


def has(value, needle):
    if value == needle:
        return True
    if type(value) is tuple:
        return any(has(item, needle) for item in value)
    return False


def reseal(data):
    items = list(data)
    raw = json.dumps(tuple(items[:-1]), ensure_ascii=True,
                     separators=(',', ':')).encode('ascii')
    items[-1] = hashlib.sha256(raw).hexdigest()
    return tuple(items)


def replace_first(value, predicate, replacement, changed=None):
    if changed is None:
        changed = [False]
    if type(value) is tuple:
        if not changed[0] and predicate(value):
            changed[0] = True
            return replacement
        return tuple(replace_first(item, predicate, replacement, changed) for item in value)
    return value


class TestCheckpointWire(unittest.TestCase):
    def setUp(self):
        self.f = interval_fixtures.TestIntervalStaging()
        self.f.setUp()
        self.world, self.enc = self.f.world, self.f.enc
        self.cursor = RNGCursor(random.Random(2026).getstate())
        self.enc.enable_transactional_progression(quiescent=True, rng_owner=self.cursor)

    def capture(self):
        return assemble_native_run_spot_envelope(
            self.world, self.enc, quiescent=True, rng_scope='exclusive_encounter')

    def test_initial_envelope_canonical_bytes_round_trip_and_preserve_rng(self):
        envelope = self.capture()
        before_rng = self.cursor.state
        first = encode_run_spot_envelope(envelope)
        second = encode_run_spot_envelope(self.capture())
        self.assertEqual(first, second)
        decoded = decode_run_spot_wire(first)
        self.assertEqual(decoded.schema, WIRE_SCHEMA)
        self.assertEqual(decoded.envelope_data, envelope.to_data())
        self.assertEqual(reencode_decoded_run_spot_wire(decoded), first)
        self.assertEqual(decoded.envelope_data[9], envelope.private_rng)
        self.assertFalse(decoded.envelope_data[13])
        self.assertFalse(decoded.envelope_data[14])
        self.assertFalse(decoded.envelope_data[15])
        self.assertEqual(before_rng, self.cursor.state)
        with self.assertRaises((ValueError, TypeError)):
            validate_native_run_spot_envelope(self.world, self.enc, decoded, quiescent=True)

    def test_one_boundary_fractional_future_choice_and_negative_hp_are_exact(self):
        self.f.a.current.hit_points = -3
        action = RunAction(self.world, self.f.a.id, 0, 1, .5, experience=3)
        self.enc.schedule_choice((action,))
        self.enc.step(1)
        future = self.f.spot(actor=self.f.a, start=2.375)
        self.enc.schedule_choice((future,))
        envelope = self.capture()
        encoded = encode_run_spot_envelope(envelope)
        decoded = decode_run_spot_wire(encoded)
        self.assertEqual(decoded.envelope_data, envelope.to_data())
        self.assertEqual(envelope.boundary_sequence, (1,))
        self.assertTrue(has(decoded.envelope_data, ('binary64', float(2.375).hex())))
        self.assertTrue(has(decoded.envelope_data, ('integer', '-3')))

    def test_two_boundary_committed_native_fixture_survives_separate_process(self):
        first = RunAction(self.world, self.f.a.id, 0, 1, .5, experience=3)
        simultaneous = RunAction(self.world, self.f.a.id, 0, 1, .5, experience=4)
        self.enc.schedule_choice((first, simultaneous))
        self.enc.step(1, velocities={self.f.a.id: (1, 0, 0)})
        run = RunAction(self.world, self.f.a.id, 1, 1, 1, experience=7)
        self.enc.schedule_choice((run,))
        self.enc.step(1)
        future = self.f.spot(actor=self.f.a, start=4.25)
        self.enc.schedule_choice((future,))
        from experience import BatchSkillUse
        self.assertTrue(any(type(row) is BatchSkillUse for row in self.f.a.skill_use_history))
        envelope = self.capture()
        wire = encode_run_spot_envelope(envelope)
        self.assertEqual(envelope.boundary_sequence, (1, 2))
        self.assertTrue(has(envelope.to_data(), ('binary64', float(4.25).hex())))
        script = (
            "import sys; sys.path.insert(0, " + repr(str(ROOT / 'src')) + "); "
            "from checkpoint_wire import decode_run_spot_wire, reencode_decoded_run_spot_wire; "
            "value=decode_run_spot_wire(sys.stdin.buffer.read()); "
            "assert 'checkpoint_envelope' not in sys.modules; "
            "assert 'checkpoint_inventory' not in sys.modules; "
            "sys.stdout.buffer.write(reencode_decoded_run_spot_wire(value))"
        )
        proc = subprocess.run([sys.executable, '-c', script], input=wire,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              check=False, cwd=str(ROOT))
        self.assertEqual(proc.returncode, 0, proc.stderr.decode('utf-8', errors='replace'))
        self.assertEqual(proc.stdout, wire)
        self.assertEqual(decode_run_spot_wire(proc.stdout).envelope_data, envelope.to_data())

    def test_tampering_truncation_versions_duplicate_keys_and_unknown_fields_refuse(self):
        wire = encode_run_spot_envelope(self.capture())
        with self.assertRaises(WireRejected):
            decode_run_spot_wire(wire[:-3])
        modified = bytearray(wire)
        index = modified.find(b'native-run-spot-checkpoint-envelope/1')
        modified[index] = ord('N')
        with self.assertRaises(WireRejected):
            decode_run_spot_wire(bytes(modified))
        with self.assertRaisesRegex(WireRejected, 'duplicate JSON'):
            decode_run_spot_wire(wire[:-1] + b',"schema":"other"}')
        with self.assertRaisesRegex(WireRejected, 'unknown or missing wire'):
            decode_run_spot_wire(wire[:-1] + b',"extra":1}')

    def test_noncanonical_or_malformed_detached_content_refuses(self):
        envelope = self.capture()
        data = list(envelope.to_data())
        data[0] = 'universe.native-run-spot-checkpoint-envelope/999'
        with self.assertRaisesRegex(WireRejected, 'unknown native envelope schema'):
            encode_detached_run_spot_data(reseal(tuple(data)))
        data = list(envelope.to_data())
        data[3] = ('integer', '01')
        with self.assertRaises(WireRejected):
            encode_detached_run_spot_data(reseal(tuple(data)))

    def test_resealed_dangling_entity_duplicate_alias_and_unknown_field_refuse(self):
        future = self.f.spot(actor=self.f.a, start=2.5)
        self.enc.schedule_choice((future,))
        envelope = self.capture()

        data = list(envelope.to_data())
        choices = list(data[7])
        choice = list(choices[0])
        members = list(choice[7])
        member = list(members[0])
        fields = list(member[3])
        actor_field = next(i for i, row in enumerate(fields) if row[0] == 'actor_id')
        fields[actor_field] = ('actor_id', ('entity', 'missing-being'))
        member[3] = tuple(fields)
        members[0] = tuple(member)
        choice[7] = tuple(members)
        choices[0] = tuple(choice)
        data[7] = tuple(choices)
        cert = list(data[6])
        cert_row = next(i for i, row in enumerate(cert[1:], start=1)
                        if row[0] == 'accepted-choice-descriptors')
        cert[cert_row] = ('accepted-choice-descriptors', tuple(choices))
        data[6] = tuple(cert)
        state = list(data[5])
        closure_row = next(i for i, row in enumerate(state)
                           if row[0] == 'bounded-run-spot-closure')
        state[closure_row] = ('bounded-run-spot-closure', tuple(cert))
        data[5] = tuple(state)
        with self.assertRaisesRegex(WireRejected, 'logical entity'):
            encode_detached_run_spot_data(reseal(tuple(data)))

        data = list(envelope.to_data())
        state = list(data[5])
        node_row = next(i for i, row in enumerate(state) if row[0] == 'nodes')
        nodes = list(state[node_row][1])
        nodes[-1] = (nodes[0][0], nodes[-1][1], nodes[-1][2])
        state[node_row] = ('nodes', tuple(nodes))
        data[5] = tuple(state)
        with self.assertRaisesRegex(WireRejected, 'duplicate inventory alias'):
            encode_detached_run_spot_data(reseal(tuple(data)))

        data = list(envelope.to_data())
        state = list(data[5])
        node_row = next(i for i, row in enumerate(state) if row[0] == 'nodes')
        nodes = list(state[node_row][1])
        native_index = next(i for i, node in enumerate(nodes)
                            if node[1] not in ('ordered-map', 'list', 'tuple', 'set', 'frozenset'))
        node = list(nodes[native_index])
        node[2] = node[2] + (('unknown_future_field', ('null',)),)
        nodes[native_index] = tuple(node)
        state[node_row] = ('nodes', tuple(nodes))
        data[5] = tuple(state)
        with self.assertRaisesRegex(WireRejected, 'unknown native field'):
            encode_detached_run_spot_data(reseal(tuple(data)))


if __name__ == '__main__':
    unittest.main()
