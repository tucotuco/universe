"""Focused tests for inactive, quarantined initial Run/Spot reconstruction."""
import json
import random
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from abilities import Abilities
from actiondictionary import ActionDictionary
from armor import ArmorDictionary
from atomic_publication import RNGCursor
from being import BeingDefinition, BeingDictionary
from checkpoint_envelope import assemble_native_run_spot_envelope
from checkpoint_reconstruction import (ReconstructionRejected,
    reconstruct_initial_run_spot, _NATIVE_GRAPHS)
from checkpoint_wire import decode_run_spot_wire, encode_run_spot_envelope
from encounter import Encounter
from library import Library
from object import ObjectDictionary
from physical_fatigue import PhysicalFatigueState
from skill import SkillDictionary
from spatial.geometry import Sphere
from spatial.state import CartesianPosition
from universe import Universe
from weapon import WeaponDictionary


def build_source(*, future=False, arena_activation_enabled=False, initiated=True,
                 facings=None):
    library = Library(load_definitions=False)
    library.action_dictionary = ActionDictionary()
    library.armor_dictionary = ArmorDictionary()
    library.object_dictionary = ObjectDictionary()
    library.weapon_dictionary = WeaponDictionary()
    library.being_dictionary = BeingDictionary()
    library.being_dictionary.objects = {
        name: BeingDefinition(name, 1, 100, 18, '2d8', 'Neutral', 12, 1,
                              abilities=Abilities(strength=12, constitution=14))
        for name in ('Observer', 'Target')
    }
    library.being_dictionary.object_categories = {}
    library.skill_dictionary = SkillDictionary()
    library.skill_dictionary.skills = {
        'run': {'is_ordinary': True, 'is_progressive': True},
        'spot': {'is_ordinary': True, 'is_progressive': True},
    }
    world = Universe('5D2C6 fixture', library)
    observer = world.get_object_by_id(world.make_being('Observer', 'Observer'))
    target = world.get_object_by_id(world.make_being('Target', 'Target'))
    facings = {} if facings is None else facings
    observer.set_hex_facing(facings.get('Observer'))
    target.set_hex_facing(facings.get('Target'))
    observer.set_position(CartesianPosition(0.125, 0, 0))
    target.set_position(CartesianPosition(1.25, 0, 0))
    target.set_geometry(Sphere(0.75))
    observer.physical_fatigue = PhysicalFatigueState(.73, .61)
    observer.skill_experience['spot'] = 17
    observer.current.skills.skills['spot'] = 2
    encounter = Encounter(world, 11, 0, initiated=initiated,
                          arena_activation_enabled=arena_activation_enabled)
    world.add_event(encounter)
    encounter.add_being(observer.id)
    encounter.add_being(target.id)
    cursor = RNGCursor(random.Random(2906).getstate())
    encounter.enable_transactional_progression(quiescent=True, rng_owner=cursor)
    actions = []
    if future:
        from activities import RunAction, SpotAction
        actions.append(RunAction(world, observer.id, 2.375, 1.25, 0.5, experience=3))
        actions.append(SpotAction(world, observer.id, target.id, 4.25, duration=6,
                                  die_roll=14))
        encounter.schedule_choice(tuple(actions))
    envelope = assemble_native_run_spot_envelope(
        world, encounter, quiescent=True, rng_scope='exclusive_encounter')
    return world, encounter, cursor, envelope, actions


def source_wire(future=False, facings=None):
    _, _, _, envelope, _ = build_source(future=future, facings=facings)
    return encode_run_spot_envelope(envelope)


class TestInitialNativeReconstruction(unittest.TestCase):
    def test_inactive_encounter_and_both_facing_states_round_trip(self):
        source_world, source_encounter, _, envelope, _ = build_source(
            facings={'Observer': 11, 'Target': None})
        decoded = decode_run_spot_wire(encode_run_spot_envelope(envelope))
        result = reconstruct_initial_run_spot(decoded)
        native_world, native_encounter, _ = _NATIVE_GRAPHS[result]
        self.assertFalse(native_encounter.arena_activation_enabled)
        self.assertTrue(native_encounter.initiated)
        self.assertIsNone(native_encounter.arena_activation)
        self.assertEqual(native_world.get_object_by_id(source_encounter.being_list[0]).hex_facing, 11)
        self.assertIsNone(native_world.get_object_by_id(source_encounter.being_list[1]).hex_facing)

    def test_identity_topology_numeric_state_rng_and_quarantine(self):
        source_world, source_encounter, source_rng, envelope, _ = build_source()
        wire = encode_run_spot_envelope(envelope)
        decoded = decode_run_spot_wire(wire)
        module_rng = random.getstate()
        result = reconstruct_initial_run_spot(decoded)
        native_world, native_encounter, native_rng = _NATIVE_GRAPHS[result]
        self.assertTrue(result.quarantined)
        self.assertIsNot(native_world, source_world)
        self.assertIsNot(native_encounter, source_encounter)
        self.assertEqual(result.view.encounter_id, source_encounter.id)
        self.assertEqual(result.logical_ids, tuple(sorted(source_world.object_registry.object_instances)))
        self.assertEqual(set(native_world.object_registry.object_instances),
                         set(source_world.object_registry.object_instances))
        self.assertFalse(hasattr(result, 'universe'))
        self.assertFalse(hasattr(result, 'encounter'))
        self.assertFalse(hasattr(result, 'rng_owner'))
        with self.assertRaises(AttributeError):
            result.view.encounter_time = 9
        self.assertEqual(result.view.being_ids, tuple(source_encounter.being_list))
        self.assertEqual(result.view.encounter_time, source_encounter.time)
        self.assertEqual(result.view.rng_state, source_rng.state)
        self.assertEqual(native_rng.state, source_rng.state)
        view_by_id = {being.logical_id: being for being in result.view.beings}
        for logical_id, source in source_world.object_registry.object_instances.items():
            rebuilt = native_world.get_object_by_id(logical_id)
            self.assertIsNot(rebuilt, source)
            self.assertIs(rebuilt.original,
                          native_world.library.being_dictionary.objects[rebuilt.name])
            self.assertIsNot(rebuilt.current, rebuilt.original)
            self.assertEqual(rebuilt.get_position(), source.get_position())
            self.assertEqual(rebuilt.physical_fatigue, source.physical_fatigue)
            self.assertEqual(rebuilt.skill_experience, source.skill_experience)
            self.assertEqual(rebuilt.current.skills.skills, source.current.skills.skills)
            self.assertIs(native_encounter.get_being(logical_id), rebuilt)
            view = view_by_id[logical_id]
            self.assertEqual(view.position, source.get_position().as_tuple())
            self.assertEqual(view.hit_points, source.get_hit_points())
            self.assertEqual(view.physical_fatigue,
                             (source.physical_fatigue.q, source.physical_fatigue.b))
            self.assertFalse(hasattr(view, 'set_hit_points'))
            self.assertFalse(hasattr(view, 'set_position'))
            self.assertFalse(hasattr(view, 'current'))
            def assert_closed(node):
                if type(node) is tuple:
                    for child in node:
                        assert_closed(child)
                else:
                    self.assertIn(type(node), (type(None), str, bool, int, float))
            assert_closed(view.state)
        self.assertEqual(native_encounter.being_list, source_encounter.being_list)
        self.assertEqual(random.getstate(), module_rng)
        self.assertEqual(source_encounter.time, 0)
        self.assertEqual(native_encounter.pending_action_list, [])

        # Reproduce the old raw-reference exposure using only this test's
        # private fixture access; the detached public view remains unchanged.
        before_view = result.view
        private_being = native_encounter.get_being(native_encounter.being_list[0])
        old_hp = private_being.get_hit_points()
        private_being.set_hit_points(old_hp + 1)
        self.assertEqual(private_being.get_hit_points(), old_hp + 1)
        self.assertEqual(result.view, before_view)
        with self.assertRaises((AttributeError, TypeError)):
            result.view.beings[0].state[0] = ('changed', None)
        with self.assertRaises((AttributeError, TypeError)):
            result.view.beings[0].state += (('changed', None),)

        with self.assertRaisesRegex(ValueError, '(?i)quarantined'):
            native_encounter.step(1)
        with self.assertRaisesRegex(ValueError, '(?i)quarantined'):
            native_encounter.run()
        with self.assertRaisesRegex(ValueError, '(?i)quarantined'):
            native_encounter.schedule_choice(())
        with self.assertRaisesRegex(ValueError, '(?i)quarantined'):
            native_world.to_json()
        native_encounter.__dict__.pop('_checkpoint_quarantined', None)
        native_world.__dict__.pop('_checkpoint_quarantined', None)
        with self.assertRaisesRegex(ValueError, '(?i)quarantined'):
            native_encounter.step(1)

    def test_future_fractional_run_spot_choices_use_fresh_native_registration(self):
        _, source_encounter, source_rng, envelope, source_actions = build_source(future=True)
        module_rng = random.getstate()
        result = reconstruct_initial_run_spot(decode_run_spot_wire(encode_run_spot_envelope(envelope)))
        native_world, native_encounter, native_rng = _NATIVE_GRAPHS[result]
        self.assertEqual(random.getstate(), module_rng)
        self.assertEqual(result.view.rng_state, source_rng.state)
        self.assertEqual(native_rng.state, source_rng.state)
        self.assertEqual(native_encounter.pending_action_list, [])
        self.assertEqual(native_encounter.time, source_encounter.time)
        self.assertEqual(len(native_encounter._choice_book._choices), 1)
        choice_id = next(iter(native_encounter._choice_book._choices))
        record = native_encounter._choice_book._choices[choice_id]
        self.assertEqual(record.view.action_ids, tuple(action.id for action in source_actions))
        rebuilt_actions = tuple(member.action for member in record.members)
        self.assertEqual(tuple(action.start_time for action in rebuilt_actions), (2.375, 4.25))
        self.assertTrue(all(action is not source for action, source in zip(rebuilt_actions, source_actions)))
        self.assertTrue(record.signatures)
        from action_choice import declaration
        self.assertEqual(record.signatures,
                         tuple((member.key, declaration(member.action)) for member in record.members))
        self.assertTrue(all(native_world.get_event_by_id(action.id) is None
                            for action in source_actions))
        from checkpoint_choices import describe_accepted_choice
        self.assertEqual(describe_accepted_choice(native_world, native_encounter,
                         choice_id).to_data(), envelope.accepted_choice_descriptors[0])
        self.assertEqual(tuple(row.logical_id for row in result.view.actions),
                         tuple(action.id for action in source_actions))
        self.assertEqual(tuple(row.start_time for row in result.view.actions),
                         tuple(member[3][3][1] for member in envelope.accepted_choice_descriptors[0][7]))
        self.assertFalse(hasattr(result.view.actions[0], 'resolve'))
        with self.assertRaisesRegex(ValueError, '(?i)quarantined'):
            record.members[0].action.resolve(native_encounter.difficulty_class)

    def test_ordinary_native_mutation_and_legacy_encounter_remain_available(self):
        from spatial.state import CartesianPosition
        world, encounter, _, _, _ = build_source()
        ordinary = world.get_object_by_id(encounter.being_list[0])
        ordinary.set_hit_points(13)
        ordinary.set_position(CartesianPosition(9, 8, 7))
        self.assertEqual(ordinary.get_hit_points(), 13)
        self.assertEqual(ordinary.get_position().as_tuple(), (9.0, 8.0, 7.0))

        legacy_world = Universe('ordinary legacy view test', world.library)
        legacy_encounter = Encounter(legacy_world, 10, 0, initiated=True)
        legacy_world.add_event(legacy_encounter)
        self.assertEqual(legacy_encounter.progression_mode, 'legacy')
        legacy_encounter.step(.25)
        self.assertEqual(legacy_encounter.time, .25)

    def test_separate_process_decode_and_reconstruction_after_source_process_encoding(self):
        wire = source_wire(future=True, facings={'Observer': 2, 'Target': None})
        source_data = decode_run_spot_wire(wire).envelope_data
        source_sections = {row[0]: row[1:] for row in source_data[5][1:]}
        source_nodes = source_sections['nodes'][0]
        expected_ids = sorted(row[0][1] for row in source_nodes
                              if type(row[0]) is tuple and len(row[0]) == 2
                              and row[0][0] == 'object')
        expected_choice_ids = [row[1] for row in source_data[7]]
        expected_action_ids = [member[2] for choice in source_data[7] for member in choice[7]]
        script = r'''
import json,sys
sys.path.insert(0, sys.argv[1])
from checkpoint_wire import decode_run_spot_wire
from checkpoint_reconstruction import reconstruct_initial_run_spot, _NATIVE_GRAPHS
r = reconstruct_initial_run_spot(decode_run_spot_wire(sys.stdin.buffer.read()))
assert r.quarantined and not hasattr(r, 'encounter') and not hasattr(r, 'universe')
world, encounter, _rng = _NATIVE_GRAPHS[r]
v = r.view
print(json.dumps({"encounter": v.encounter_id,
 "beings": sorted(v.being_ids), "time": v.encounter_time,
 "choices": [row[1] for row in v.accepted_choices],
 "actions": [row.logical_id for row in v.actions],
 "positions": {row.logical_id: row.position for row in v.beings},
 "facings": [world.get_object_by_id(identity).hex_facing
             for identity in encounter.being_list],
 "qb": {row.logical_id: row.physical_fatigue for row in v.beings},
 "rng_state_version": v.rng_state[0]}))
'''
        proc = subprocess.run([sys.executable, '-c', script, str(ROOT / 'src')],
            input=wire, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=str(ROOT), check=False)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode('utf-8', errors='replace'))
        output = json.loads(proc.stdout)
        self.assertEqual(output['time'], 0)
        self.assertEqual(output['beings'], expected_ids)
        self.assertEqual(output['choices'], expected_choice_ids)
        self.assertEqual(output['actions'], expected_action_ids)
        self.assertEqual(output['facings'], [2, None])
        self.assertCountEqual([tuple(value) for value in output['positions'].values()],
                              [(0.125, 0.0, 0.0), (1.25, 0.0, 0.0)])
        self.assertIn((.73, .61),
                      tuple(tuple(value) for value in output['qb'].values()))
        self.assertEqual(output['rng_state_version'], 3)

    def test_committed_receipts_compatibility_and_unsupported_catalog_refuse(self):
        from activities import RunAction
        world, encounter, _, _, _ = build_source()
        actor, target = (world.get_object_by_id(i) for i in encounter.being_list)
        encounter.schedule_choice((RunAction(world, actor.id, 0, 1, .5, experience=1),))
        encounter.step(1)
        committed = assemble_native_run_spot_envelope(
            world, encounter, quiescent=True, rng_scope='exclusive_encounter')
        with self.assertRaisesRegex(ReconstructionRejected, 'committed boundaries'):
            reconstruct_initial_run_spot(decode_run_spot_wire(encode_run_spot_envelope(committed)))

        world, encounter, _, _, _ = build_source()
        actor, target = (world.get_object_by_id(i) for i in encounter.being_list)
        encounter.schedule_choice((RunAction(world, actor.id, 0, 1, .5, experience=1),))
        encounter.step(1)
        encounter.schedule_choice((RunAction(world, actor.id, 1, 1, .5, experience=1),))
        encounter.step(1)
        two_boundaries = assemble_native_run_spot_envelope(
            world, encounter, quiescent=True, rng_scope='exclusive_encounter')
        self.assertEqual(two_boundaries.boundary_sequence, (1, 2))
        with self.assertRaisesRegex(ReconstructionRejected, 'committed boundaries'):
            reconstruct_initial_run_spot(
                decode_run_spot_wire(encode_run_spot_envelope(two_boundaries)))

        _, _, _, initial, _ = build_source()
        data = list(initial.to_data())
        compatibility = list(data[3])
        implementation = list(compatibility[2])
        implementation[1] = '0' * 64
        compatibility[2] = tuple(implementation)
        data[3] = tuple(compatibility)
        from checkpoint_envelope import _digest
        data[-1] = _digest(tuple(data[:-1]))
        from checkpoint_wire import encode_detached_run_spot_data
        with self.assertRaisesRegex(ReconstructionRejected, 'compatibility'):
            reconstruct_initial_run_spot(decode_run_spot_wire(encode_detached_run_spot_data(tuple(data))))

        world, encounter, _, _, _ = build_source()
        world.library.weapon_dictionary.objects['alien'] = object()
        with self.assertRaises((ValueError, TypeError), msg='unsafe native definition must refuse'):
            assemble_native_run_spot_envelope(
                world, encounter, quiescent=True, rng_scope='exclusive_encounter')

    def test_one_committed_boundary_is_precisely_refused_in_separate_process(self):
        from activities import RunAction
        world, encounter, _, _, _ = build_source()
        actor, target = (world.get_object_by_id(i) for i in encounter.being_list)
        encounter.schedule_choice((RunAction(world, actor.id, 0, 1, .5, experience=1),))
        encounter.step(1)
        envelope = assemble_native_run_spot_envelope(
            world, encounter, quiescent=True, rng_scope='exclusive_encounter')
        self.assertEqual(envelope.boundary_sequence, (1,))
        wire = encode_run_spot_envelope(envelope)
        script = r'''
import json,sys
sys.path.insert(0, sys.argv[1])
from checkpoint_wire import decode_run_spot_wire
from checkpoint_reconstruction import ReconstructionRejected, reconstruct_initial_run_spot
from atomic_publication import _COMMITTED_RECEIPTS
try:
    reconstruct_initial_run_spot(decode_run_spot_wire(sys.stdin.buffer.read()))
except ReconstructionRejected as exc:
    assert 'reviewed quarantine-only native Action/Target projection' in str(exc), str(exc)
    assert not _COMMITTED_RECEIPTS
    print(json.dumps({'refused': str(exc), 'issued_receipts': len(_COMMITTED_RECEIPTS)}))
else:
    raise AssertionError('one-boundary history unexpectedly reconstructed')
'''
        proc = subprocess.run([sys.executable, '-c', script, str(ROOT / 'src')],
            input=wire, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            cwd=str(ROOT), check=False)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode('utf-8', errors='replace'))
        result = json.loads(proc.stdout)
        self.assertEqual(result['issued_receipts'], 0)
        self.assertIn('process-local issuance', result['refused'])


if __name__ == '__main__':
    unittest.main()
