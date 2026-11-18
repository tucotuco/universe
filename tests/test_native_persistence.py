from __future__ import annotations

import base64
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "examples"))
sys.path.insert(0, str(ROOT / "tests"))

import encounter_delta_headless
import native_history
import native_persistence
import test_encounter_inspection as inspection_fixtures
import test_action_evaluation as action_fixtures
from native_history import NativeHistoryRecorder
from activities import DelayAction, RunAction
from atomic_publication import RNGCursor
from encounter import Encounter
from library import Library
from melee_combat import MeleeStrike
from spatial.geometry import Sphere
from spatial.state import CartesianPosition
from strategy import Strategy
from universe import Universe
from native_persistence import (NativeSaveRejected, export_save, load_path,
                                load_save, load_legacy_arena_save, write_save)
from checkpoint_adapters import RecipientBinding
from reproduction_group import (ReproductionGroupElaborationProposal,
                                ReproductionGroupProposal,
                                prepare_reproduction_group)
from being import BeingDefinition
from reproduction_being_bridge import materialize_reproductive_offspring
from history_conversation import AskAboutPastAction
from activities import SpotAction
from location_observation import LocationEvidenceLedger
from object_observation import ObjectObservationLedger
from statistical_group import GroupMember, MembershipChange, StatisticalGroup


def _previous_entity_compact_graph(encounter):
    """Build the pinned `/2` Entity writer used by legacy-history fixtures."""
    import base64
    import native_graph_snapshot
    from checkpoint_inventory import capture_checkpoint_candidate
    from native_graph_snapshot import encode as encode_graph

    candidate = capture_checkpoint_candidate(
        encounter.universe, encounter, quiescent=True,
        rng_scope="exclusive_encounter", native_adapters=True,
        full_native=True, compact_native_target_history=True,
        compact_native_entity_context=True,
        rng_owner=native_persistence._native_rng_owner(encounter))
    graph = json.loads(encode_graph(candidate.envelope, native=True))
    compatibility = (
        native_graph_snapshot._LEGACY_NATIVE_GRAPH_V2_ENTITY_COMPATIBILITY)
    graph["compatibility"] = compatibility
    inventory = native_graph_snapshot._expand_compact_inventory(
        native_graph_snapshot._tuples(graph["inventory"]), native=True)
    graph["inventory"] = native_graph_snapshot._compact_inventory(
        (compatibility, inventory[1]), native=True)
    unsigned = {key: value for key, value in graph.items() if key != "sha256"}
    graph["sha256"] = hashlib.sha256(
        native_graph_snapshot._canonical(unsigned)).hexdigest()
    return base64.b64encode(
        native_graph_snapshot._canonical(graph)).decode("ascii")


def _legacy_history_shape(value):
    value.pop("receipt_facts_complete", None)
    value.pop("observer_knowledge", None)
    value.get("initial", {}).pop("initial_schedule_available", None)
    value.get("initial", {}).pop("initial_entities_available", None)
    for row in value.get("boundaries", ()):
        row.pop("notification_intents", None)
        row.pop("disarm_landings", None)
        row.pop("receipt_facts_available", None)
        for change in row.get("changes", ()):
            if change.get("path") == ["recipients"] and change.get("after"):
                for recipient in change.get("value", ()):
                    recipient.pop("binding_id", None)
    return value


def _legacy_initial_entity_anchor(value, encounter):
    """Model pre-/11 history whose initial projection was the first receipt."""
    body = copy.deepcopy({key: item for key, item in value.items()
                          if key != "sha256"})
    initial_entities = native_history._plain(
        encounter._atomic_interval_history[0].inspection.entities)
    old_state = native_history._initial_state(body["initial"])
    committed_states = []
    for row in native_history._expand_rows(body):
        old_state = native_history._apply(old_state, row["changes"])
        for recipient in old_state.get("recipients", ()):
            recipient.pop("binding_id", None)
        committed_states.append(old_state)
    body["initial"]["entities"] = initial_entities
    body["initial"]["initial_entities_available"] = False
    prior = native_history._initial_state(body["initial"])
    rows = []
    for original, state in zip(native_history._expand_rows(value), committed_states):
        row = dict(original)
        row["changes"] = native_history._diff(prior, state)
        row["state_sha256"] = hashlib.sha256(
            native_history._canonical(state)).hexdigest()
        rows.append(row)
        prior = state
    body["boundaries"] = native_history._compact_quiet_rows(rows)
    context = body.get("entity_context")
    if type(context) is dict and context.get("available") is True:
        first_boundary = encounter._atomic_interval_history[0].boundary
        strip_fatigue = context.get("fatigue_available") is False

        def legacy_context(entities):
            result = copy.deepcopy(entities)
            if strip_fatigue:
                for entity in result.values():
                    pre_action = entity.get("fields", {}).get("pre_action", {})
                    pre_action.pop("physical_fatigue", None)
                    pre_action.pop("physiology", None)
            return result

        context_initial = legacy_context(initial_entities)
        context["initial"] = context_initial
        prior_context = context_initial
        changes = []
        for receipt in encounter._atomic_interval_history[1:]:
            boundary = receipt.boundary
            current = legacy_context(native_history._plain(
                receipt.inspection.entities))
            delta = native_history._diff(prior_context, current)
            if delta:
                changes.append({"boundary": boundary,
                    "changes": delta,
                    "state_sha256": hashlib.sha256(
                        native_history._canonical(current)).hexdigest()})
            prior_context = current
        context["changes"] = changes
    return body


class NativePersistenceTests(unittest.TestCase):
    def test_native_recipient_binding_descriptor_rejects_malformed_identity(self):
        from native_graph_snapshot import (
            ArenaNativeSnapshotRejected,
            _validate_host_binding_descriptors,
        )

        row = ('native', 'ledger', 'in_world_belief_ledger',
               ('observer',),
               ('reference', ('host-recipient',
                              ('universe', 'native-world', 'native', 'ledger'))),
               'g' * 64)
        with self.assertRaisesRegex(
                ArenaNativeSnapshotRejected,
                'native host binding identity is malformed'):
            _validate_host_binding_descriptors(
                ((row,),), require_binding_ids=True)

    def test_native_recipient_binding_descriptor_rejects_identity_collisions(self):
        from native_graph_snapshot import (
            ArenaNativeSnapshotRejected,
            _validate_host_binding_descriptors,
        )

        def row(name, reference, binding_id):
            return ('native', name, 'in_world_belief_ledger', ('observer',),
                    ('reference', ('host-recipient', *reference)), binding_id)

        first = ('universe', 'native-world', 'native', 'ledger-a')
        second = ('universe', 'native-world', 'native', 'ledger-b')
        binding = 'a' * 64
        with self.assertRaisesRegex(
                ArenaNativeSnapshotRejected,
                'identity aliases distinct recipient references'):
            _validate_host_binding_descriptors(
                ((row('ledger-a', first, binding),
                  row('ledger-b', second, binding),),),
                require_binding_ids=True)
        with self.assertRaisesRegex(
                ArenaNativeSnapshotRejected,
                'reference has conflicting binding identities'):
            _validate_host_binding_descriptors(
                ((row('ledger-a', first, binding),
                  row('ledger-b', first, 'b' * 64),),),
                require_binding_ids=True)

    def _assert_recipient_history_matches_receipts(self, encounter):
        """Check detached recipient history against every authoritative cut."""
        log = native_history.capture(encounter)
        query = native_history.NativeHistoryQuery(log)
        self.assertEqual(query.state_at(0)["recipients"], {})
        self.assertEqual(query.observer_facts_at(0, encounter.being_list[0]), [])
        for boundary in range(1, log["latest_boundary"] + 1):
            receipt_view = encounter.inspect_committed(boundary)
            expected = native_history._stable_recipients(
                receipt_view.recipients, encounter)
            self.assertEqual(query.state_at(boundary)["recipients"], expected,
                             f"recipient projection at boundary {boundary}")
            owners = set(encounter.being_list)
            owners.update(row["owner_id"] for row in expected
                          if row["owner_id"] is not None)
            for owner_id in owners:
                self.assertEqual(query.observer_facts_at(boundary, owner_id),
                    [row for row in expected if row["owner_id"] == owner_id])

    def _combat_encounter(self):
        world = Universe("native-combat", library=Library(config_dir=str(ROOT / "src/config")))
        attacker = world.get_object_by_id(world.make_being("Human", "Attacker"))
        defender = world.get_object_by_id(world.make_being("Human", "Defender"))
        attacker.set_position(CartesianPosition(0, 0, 0))
        defender.set_position(CartesianPosition(1.5, 0, 0))
        for being in (attacker, defender):
            being.set_geometry(Sphere(.25))
            being.set_hit_points(100)
        weapon_id = world.make_weapon_for_being(attacker.id, "Dagger", "Native dagger")
        world.arm_being(attacker.id, weapon_id, "right hand")
        encounter = Encounter(world, 10, 0, initiated=True)
        encounter.add_being(attacker.id)
        encounter.add_being(defender.id)
        encounter.mark_aware(attacker.id, defender.id)
        encounter.mark_aware(defender.id, attacker.id)
        world.add_event(encounter)
        rng = RNGCursor(__import__("random").Random(9).getstate())
        encounter.enable_transactional_progression(quiescent=True, rng_owner=rng)
        return world, encounter, rng, attacker, defender, weapon_id

    def test_native_save_preserves_initial_rng_history_anchor(self):
        _world, encounter, rng, *_ = self._combat_encounter()
        origin = rng.state
        encounter.step(1)
        wire = export_save(encounter)
        restored_world, restored_encounter, restored_rng = load_save(wire)
        self.assertEqual(restored_rng.state, rng.state)
        self.assertEqual(restored_encounter.__dict__["_native_rng_origin_state"], origin)
        log = native_history.current_recording(restored_encounter)
        self.assertIsNotNone(log)
        self.assertEqual(native_history.rng_state_at(log, 0), native_history._plain(origin))
        self.assertIs(restored_world.event_history[restored_encounter.id], restored_encounter)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "initial-rng-native-save.json"
            path.write_bytes(wire)
            child = r'''import json,sys
import native_history
from native_persistence import load_path
world,encounter,rng=load_path(sys.argv[1])
log=native_history.current_recording(encounter)
print(json.dumps({'encounter':encounter.id,
 'initial_rng':native_history.rng_state_at(log,0),
 'current_rng':native_history._plain(rng.state)},sort_keys=True))'''
            result = subprocess.run(
                [sys.executable, "-B", "-c", child, str(path)], cwd=ROOT,
                env={**__import__("os").environ,
                     "PYTHONPATH": f"{ROOT / 'src'}:{ROOT / 'examples'}"},
                text=True, capture_output=True, check=False, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        child_state = json.loads(result.stdout)
        self.assertEqual(child_state["encounter"], encounter.id)
        self.assertEqual(child_state["initial_rng"], native_history._plain(origin))
        self.assertEqual(child_state["current_rng"], native_history._plain(rng.state))

    def test_generated_v12_arena_save_migrates_to_canonical_native_save(self):
        """A current legacy /12 Arena artifact can enter native Save/Load losslessly."""
        from arena_browser_session import GeneratedArenaSession

        session = GeneratedArenaSession(root_seed_factory=lambda: 20261116)
        session.generate({"starting_experience": "10000", "width_cells": "5",
                          "height_cells": "5"})
        session.choose_run()
        session.advance_one_second()
        legacy_wire = session.save_encounter_bytes()
        world, encounter, rng = load_legacy_arena_save(legacy_wire)
        self.assertIs(world.event_history[encounter.id], encounter)
        self.assertIsNotNone(encounter.arena_activation)
        activation = encounter.arena_activation.to_dict()
        awareness = {key: tuple(sorted(value))
                     for key, value in sorted(encounter.awareness.items())}
        ledgers = {being_id: world.get_object_by_id(being_id)._arena_perception_ledger
                   for being_id in encounter.being_list}
        history_log = native_history.capture(encounter)
        history_query = native_history.NativeHistoryQuery(history_log)
        for being_id, ledger in ledgers.items():
            for boundary in range(encounter.last_processed_boundary + 1):
                expected = {}
                for row in ledger._history:
                    if row.visibility_boundary <= boundary:
                        expected[row.entity_id] = native_history._plain(row)
                self.assertEqual(history_query.observer_knowledge_at(
                    boundary, being_id), expected)
        self.assertEqual(history_query.observer_knowledge_at(
            encounter.last_processed_boundary, "not-an-observer"), {})
        corrupt_history = json.loads(json.dumps(history_log))
        owner_id = next(iter(corrupt_history["observer_knowledge"]["initial"]))
        entity_id = next(iter(corrupt_history["observer_knowledge"]["initial"][owner_id]))
        corrupt_history["observer_knowledge"]["initial"][owner_id][entity_id][
            "fields"]["observer_id"] = "forged-observer"
        with self.assertRaisesRegex(native_history.NativeHistoryRejected,
                                    "observer evidence owner"):
            native_history.validate(native_history._seal(
                {key: value for key, value in corrupt_history.items()
                 if key != "sha256"}))
        native_wire = export_save(encounter)
        restored_world, restored_encounter, restored_rng = load_save(native_wire)
        self.assertEqual(export_save(restored_encounter), native_wire)
        self.assertEqual(restored_world.id, world.id)
        self.assertEqual(restored_encounter.id, encounter.id)
        self.assertEqual(restored_encounter.arena_activation.to_dict(), activation)
        self.assertEqual({key: tuple(sorted(value)) for key, value in
                          sorted(restored_encounter.awareness.items())}, awareness)
        self.assertEqual(restored_rng.state, rng.state)
        for being_id, ledger in ledgers.items():
            restored = restored_world.get_object_by_id(being_id)._arena_perception_ledger
            self.assertIsNotNone(restored)
            self.assertEqual(restored.observer_id, ledger.observer_id)
            self.assertEqual(restored._history, ledger._history)
        restored_log = native_history.current_recording(restored_encounter)
        restored_query = native_history.NativeHistoryQuery(restored_log)
        for being_id, ledger in ledgers.items():
            for boundary in range(restored_encounter.last_processed_boundary + 1):
                expected = {}
                for row in ledger._history:
                    if row.visibility_boundary <= boundary:
                        expected[row.entity_id] = native_history._plain(row)
                self.assertEqual(restored_query.observer_knowledge_at(
                    boundary, being_id), expected)

        # A valid /7 native history has no explicit schedule-availability
        # marker or passive observer timeline. Its scheduler projection came
        # from the first receipt, so it is not exposed as boundary-zero state.
        legacy_payload = json.loads(native_wire)
        legacy_history = {key: value for key, value in legacy_payload["history"].items()
                          if key != "sha256"}
        legacy_history.pop("observer_knowledge")
        legacy_history["initial"].pop("initial_schedule_available")
        legacy_history["initial"].pop("initial_entities_available")
        legacy_history["schema"] = native_history.RECEIPT_FACT_SCHEMA
        legacy_payload["history"] = native_history._seal(legacy_history)
        legacy_unsigned = {key: value for key, value in legacy_payload.items()
                           if key != "sha256"}
        legacy_payload["sha256"] = hashlib.sha256(
            native_persistence._canonical(legacy_unsigned)).hexdigest()
        legacy_wire = native_persistence._canonical(legacy_payload)
        migrated_world, migrated_encounter, _migrated_rng = load_save(legacy_wire)
        self.assertIs(migrated_world.event_history[migrated_encounter.id],
                      migrated_encounter)
        migrated_log = native_history.current_recording(migrated_encounter)
        migrated_query = native_history.NativeHistoryQuery(migrated_log)
        self.assertFalse(migrated_log['initial']['initial_schedule_available'])
        self.assertIsNone(migrated_query.schedule_at(0))
        for boundary in range(1, encounter.last_processed_boundary + 1):
            self.assertEqual(migrated_query.schedule_at(boundary),
                             restored_query.schedule_at(boundary))
        migrated_wire = export_save(migrated_encounter)
        self.assertEqual(export_save(load_save(migrated_wire)[1]), migrated_wire)

    def test_arena_observer_knowledge_appends_only_committed_evidence_changes(self):
        from arena_browser_session import GeneratedArenaSession

        session = GeneratedArenaSession(root_seed_factory=lambda: 20261116)
        session.generate({"starting_experience": "10000", "width_cells": "5",
                          "height_cells": "5"})
        session.choose_run()
        encounter = session._active.encounter
        # Attach before the first commit, then let the ordinary native
        # publisher create boundary evidence and append it on the next turn.
        export_save(encounter)
        session.advance_one_second()
        actor_id = encounter.being_list[0]
        encounter.schedule_action(DelayAction(
            encounter, actor_id, defense=0, start_time=encounter.time,
            id="arena-observer-history-second-boundary"))
        encounter.step(1)
        log = native_history.current_recording(encounter)
        self.assertEqual(log["schema"], native_history.SCHEMA)
        reader = native_history.NativeHistoryQuery(log)
        for boundary in range(encounter.last_processed_boundary + 1):
            for observer_id in encounter.being_list:
                expected = {}
                ledger = encounter.get_being(observer_id)._arena_perception_ledger
                for evidence in ledger._history:
                    if evidence.visibility_boundary <= boundary:
                        expected[evidence.entity_id] = native_history._plain(evidence)
                self.assertEqual(reader.observer_knowledge_at(
                    boundary, observer_id), expected)

    def test_legacy_v10_v11_pristine_arena_migrate_and_start_natively(self):
        """Accepted pristine legacy files migrate without inventing an Action."""
        import os
        from activities import DelayAction

        script = r'''import hashlib,json,sys
import native_history
from activities import DelayAction
from atomic_publication import RNGCursor
from native_persistence import load_save,export_save
wire=open(sys.argv[1],'rb').read();version=sys.argv[2]
world,enc,rng=load_save(wire)
assert enc.progression_mode=='transactional'
assert export_save(enc)==wire
actor_id=enc.being_list[0]
action_id='legacy-migration-first-delay-'+version
action=DelayAction(enc,actor_id,0,enc.time,id=action_id)
wrong_rng=RNGCursor(rng.state)
try:
 enc.activate_arena_for_player_action(actor_id,action,rng_owner=wrong_rng)
 raise AssertionError('foreign RNG owner was accepted')
except RuntimeError as error:
 assert 'RNG owner differs' in str(error)
assert not enc.initiated and enc.arena_activation is None
assert action_id not in world.event_history and not enc.pending_action_list
_,activation=enc.activate_arena_for_player_action(actor_id,action,rng_owner=rng)
enc.step(1);receipt=enc.inspect_committed(1).action(action.id)
print(json.dumps({'world_id':world.id,'encounter_id':enc.id,
 'being_ids':list(enc.being_list),'time':enc.time,'boundary':enc.last_processed_boundary,
 'activation':activation.to_dict(),'action_id':action.id,
 'outcome':receipt.facts.outcome,'position':world.get_object_by_id(actor_id).get_position().as_tuple(),
 'hp':world.get_object_by_id(actor_id).get_hit_points(),'rng':rng.state,
 'history':hashlib.sha256(native_history.encode(native_history.capture(enc))).hexdigest(),
 'observers':sorted((key,tuple(sorted(value))) for key,value in enc.awareness.items()),
 'arena_imports':sorted(set(sys.modules)&{'arena_browser_session','arena_server','npcgen'})},sort_keys=True))'''
        for version, filename in (
                ('v10', 'legacy-per-scale-010-v10.uarena'),
                ('v11', 'legacy-per-scale-011-v11.uarena')):
            with self.subTest(version=version), tempfile.TemporaryDirectory() as directory:
                legacy_wire = (ROOT / 'tests/fixtures/arena' / filename).read_bytes()
                control_world, control_encounter, control_rng = load_legacy_arena_save(legacy_wire)
                control_encounter.enable_transactional_progression(
                    quiescent=True, rng_owner=control_rng)
                native_wire = export_save(control_encounter)
                control_actor = control_encounter.being_list[0]
                action_id = 'legacy-migration-first-delay-' + version
                control_action = DelayAction(control_encounter, control_actor, 0,
                                             control_encounter.time, id=action_id)
                _, control_activation = control_encounter.activate_arena_for_player_action(
                    control_actor, control_action, rng_owner=control_rng)
                control_encounter.step(1)
                control_receipt = control_encounter.inspect_committed(1).action(action_id)
                expected = {
                    'world_id': control_world.id,
                    'encounter_id': control_encounter.id,
                    'being_ids': list(control_encounter.being_list),
                    'time': control_encounter.time,
                    'boundary': control_encounter.last_processed_boundary,
                    'activation': control_activation.to_dict(),
                    'action_id': action_id,
                    'outcome': control_receipt.facts.outcome,
                    'position': control_world.get_object_by_id(control_actor).get_position().as_tuple(),
                    'hp': control_world.get_object_by_id(control_actor).get_hit_points(),
                    'rng': control_rng.state,
                    'history': hashlib.sha256(native_history.encode(
                        native_history.capture(control_encounter))).hexdigest(),
                    'observers': sorted((key, tuple(sorted(value)))
                                        for key, value in control_encounter.awareness.items()),
                    'arena_imports': [],
                }
                source = Path(directory) / f'{version}.native.json'
                source.write_bytes(native_wire)
                result = subprocess.run(
                    [sys.executable, '-B', '-c', script, str(source), version],
                    cwd=directory,
                    env={**os.environ,
                         'PYTHONPATH': f'{ROOT / "src"}:{ROOT / "examples"}'},
                    text=True, capture_output=True, check=False, timeout=60)
                self.assertEqual(result.returncode, 0, result.stderr)
                restored = json.loads(result.stdout)
                self.assertEqual(restored, json.loads(json.dumps(expected)))

    def test_legacy_arena_v10_v11_v12_read_through_native_graph_api(self):
        """The native consumer can strictly coexist with all accepted old Saves."""
        from arena_browser_session import GeneratedArenaSession

        current = GeneratedArenaSession(root_seed_factory=lambda: 20261116)
        current.generate({"starting_experience": "10000", "width_cells": "5",
                         "height_cells": "5"})
        current.choose_run()
        current.advance_one_second()
        candidate = current.active_candidate
        run_action = next(action for action in candidate.universe.event_history.values()
                          if type(action).__name__ == "RunAction")
        actor_id = run_action.actor_id
        continuation = (candidate.encounter, candidate.universe, current._rng_cursor,
                        actor_id, run_action.id)
        cases = [
            ("v10", (ROOT / "tests/fixtures/arena/legacy-per-scale-010-v10.uarena").read_bytes(), None),
            ("v11", (ROOT / "tests/fixtures/arena/legacy-per-scale-011-v11.uarena").read_bytes(), None),
            ("v12", current.save_encounter_bytes(), continuation),
        ]
        script = r'''import json,sys
import hashlib
import native_history
from native_persistence import load_legacy_arena_save
world,enc,rng=load_legacy_arena_save(open(sys.argv[1],'rb').read())
assert world.event_history.get(enc.id) is enc
assert enc.universe is world
continued=False
if len(sys.argv)==4:
 actor=world.get_object_by_id(sys.argv[2]); action=world.get_event_by_id(sys.argv[3])
 assert actor.id==action.actor_id and action.resolution is not None
 enc.step(1)
 continued=True
assert not (set(__import__('sys').modules) & {
 'arena_browser_session','arena_server','npcgen'})
if continued:
 assert native_history.NativeHistoryQuery(native_history.capture(enc)).schedule_at(0) is None
print(json.dumps({'universe':world.id,'encounter':enc.id,
 'boundary':enc.last_processed_boundary,'time':enc.time,
 'registry':len(world.object_registry.object_instances),'continued':continued,
 'action_outcome':None if not continued else action.resolution.outcome,
 'actor_position':None if not continued else actor.get_position().as_tuple(),
 'rng':None if not continued else rng.state},sort_keys=True))'''
        import os
        for label, wire, control in cases:
            with self.subTest(version=label), tempfile.TemporaryDirectory() as directory:
                source = Path(directory) / f"{label}.uarena"
                source.write_bytes(wire)
                arguments = [sys.executable, "-B", "-c", script, str(source)]
                expected = None
                if control is not None:
                    control_encounter, control_world, control_rng, control_actor, control_action = control
                    control_encounter.step(1)
                    expected = {
                        "universe": control_world.id,
                        "encounter": control_encounter.id,
                        "boundary": control_encounter.last_processed_boundary,
                        "time": control_encounter.time,
                        "registry": len(control_world.object_registry.object_instances),
                        "continued": True,
                        "action_outcome": control_world.get_event_by_id(control_action).resolution.outcome,
                        "actor_position": control_world.get_object_by_id(control_actor).get_position().as_tuple(),
                        "rng": control_rng.state,
                    }
                    arguments.extend((control_actor, control_action))
                result = subprocess.run(
                    arguments, cwd=ROOT,
                    env={**os.environ,
                         "PYTHONPATH": f"{ROOT / 'src'}:{ROOT / 'examples'}"},
                    text=True, capture_output=True, check=False, timeout=60)
                self.assertEqual(result.returncode, 0, result.stderr)
                restored = json.loads(result.stdout)
                self.assertTrue(restored["universe"])
                self.assertTrue(restored["encounter"])
                self.assertGreater(restored["registry"], 0)
                if expected is None:
                    self.assertFalse(restored["continued"])
                else:
                    self.assertEqual(restored, json.loads(json.dumps(expected)))

    def test_fresh_process_restores_pending_action_and_continues_natively(self):
        demo = encounter_delta_headless.build_demo(until=4)
        encounter = demo["encounter"]
        actor_id = encounter.being_list[1]
        recorder = NativeHistoryRecorder.attach(encounter)
        action = DelayAction(encounter, actor_id, defense=0, start_time=4,
                             id="native-save-pending-delay")
        encounter.schedule_action(action)
        with patch.object(native_history, "capture",
                          side_effect=AssertionError("recorder history was recaptured")):
            save = export_save(encounter)
        before_ids = {
            "world": encounter.universe.id,
            "encounter": encounter.id,
            "beings": sorted(encounter.universe.object_registry.object_instances),
            "actions": sorted(encounter.universe.event_history),
        }

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "native-save.json"
            self.assertEqual(write_save(encounter, path), len(save))
            saved_bytes = path.read_bytes()
            self.assertEqual(saved_bytes, save)
            with self.assertRaisesRegex(NativeSaveRejected, "already exists"):
                write_save(encounter, path)
            self.assertEqual(path.read_bytes(), saved_bytes)
            encounter.step(1)
            self.assertEqual(recorder.latest_boundary, 5)
            expected = {
                "time": encounter.time,
                "rng": demo["rng_owner"].state,
                "hp": [encounter.get_being(identity).get_hit_points()
                       for identity in encounter.being_list],
                "history": hashlib.sha256(native_history.encode(
                    native_history.capture(encounter))).hexdigest(),
                "receipt_actions": list(encounter._atomic_interval_history[-1].action_ids),
            }
            child = r'''import hashlib,json,sys
import native_history
from native_persistence import load_path
world,encounter,rng=load_path(sys.argv[1])
assert encounter.id == 'headless-encounter' and encounter.time == 4
assert any(row['state'] == 'accepted' and row['action_ids'] == ['native-save-pending-delay']
 for row in encounter._choice_book.summary()['choices'])
encounter.step(1)
print(json.dumps({'world':world.id,'encounter':encounter.id,'time':encounter.time,
 'rng':rng.state,'hp':[encounter.get_being(i).get_hit_points() for i in encounter.being_list],
 'history':hashlib.sha256(native_history.encode(native_history.capture(encounter))).hexdigest(),
 'receipt_actions':list(encounter._atomic_interval_history[-1].action_ids),
 'arena_app_imports':sorted(set(sys.modules)&{'arena_browser_session','arena_server','npcgen'})},sort_keys=True))'''
            result = subprocess.run(
                [sys.executable, "-B", "-c", child, str(path)], cwd=directory,
                env={**__import__("os").environ,
                     "PYTHONPATH": f"{ROOT / 'src'}:{ROOT / 'examples'}"},
                text=True, capture_output=True, check=False, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        restored = json.loads(result.stdout)
        self.assertEqual(restored["world"], before_ids["world"])
        self.assertEqual(restored["encounter"], before_ids["encounter"])
        self.assertEqual(restored["time"], expected["time"])
        self.assertEqual(restored["rng"], json.loads(json.dumps(expected["rng"])))
        self.assertEqual(restored["hp"], expected["hp"])
        self.assertEqual(restored["history"], expected["history"])
        self.assertEqual(restored["receipt_actions"], expected["receipt_actions"])
        self.assertEqual(restored["arena_app_imports"], [])

    def test_generated_arena_first_choice_native_save_round_trips_and_continues(self):
        from arena_browser_session import GeneratedArenaSession
        session = GeneratedArenaSession(root_seed_factory=lambda: 20261116)
        session.generate({"starting_experience": "10000", "width_cells": "5",
                          "height_cells": "5"})
        session.choose_run()
        candidate = session.active_candidate
        encounter, world = candidate.encounter, candidate.universe
        activation = encounter.arena_activation
        self.assertIsNotNone(activation)
        action = world.get_event_by_id(
            encounter._choice_book._choices[activation.choice_id].view.action_ids[0])
        self.assertIs(type(action), RunAction)
        save = export_save(encounter)

        encounter.step(1)
        receipt = encounter.inspect_committed(1).action(action.id)
        expected = {
            "world_id": world.id,
            "encounter_id": encounter.id,
            "activation": activation.to_dict(),
            "action_id": action.id,
            "outcome": receipt.facts.outcome,
            "actor_id": action.actor_id,
            "position": world.get_object_by_id(action.actor_id).get_position().as_tuple(),
            "rng": session._rng_cursor.state,
            "history": hashlib.sha256(native_history.encode(
                native_history.capture(encounter))).hexdigest(),
        }
        child = r'''import hashlib,json,sys
from native_persistence import load_save
import native_history
world,enc,rng=load_save(open(sys.argv[1],'rb').read())
actor_id,action_id,choice_id=sys.argv[2:]
activation=enc.arena_activation
assert activation is not None and activation.actor_id==actor_id
assert activation.choice_id==choice_id and activation.encounter_id==enc.id
assert enc.choice_for_action(action_id).state in ('accepted','executing')
enc.step(1);receipt=enc.inspect_committed(1).action(action_id)
print(json.dumps({'world_id':world.id,'encounter_id':enc.id,
 'activation':activation.to_dict(),'action_id':action_id,
 'outcome':receipt.facts.outcome,'actor_id':actor_id,
 'position':world.get_object_by_id(actor_id).get_position().as_tuple(),
 'rng':rng.state,'history':hashlib.sha256(native_history.encode(
  native_history.capture(enc))).hexdigest(),
 'arena_app_imports':sorted(set(sys.modules)&{'arena_browser_session','arena_server','npcgen'})},sort_keys=True))'''
        import os
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "arena-native-initial.json"
            path.write_bytes(save)
            result = subprocess.run(
                [sys.executable, "-B", "-c", child, str(path), action.actor_id,
                 action.id, activation.choice_id], cwd=directory,
                env={**os.environ,
                     "PYTHONPATH": f"{ROOT / 'src'}:{ROOT / 'examples'}"},
                text=True, capture_output=True, check=False, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        restored = json.loads(result.stdout)
        self.assertEqual(restored.pop("arena_app_imports"), [])
        self.assertEqual(restored, json.loads(json.dumps(expected)))

    def test_projectile_shield_interception_continues_after_native_fresh_process_load(self):
        """A saved in-flight projectile retains its later native shield result."""
        import random
        from being import BeingInstance
        from activities import ThrowAction
        from native_throw_arena import build_native_scene

        world, encounter, actor, _stone, rng, original = build_native_scene(seed=116)
        encounter._choice_book.undo(encounter._choice_book.for_action(original.id).id)
        definition = world.library.being_dictionary.get_object_definition("Human")
        target = BeingInstance(definition, "Native Shielded Target",
                              id="native-persist/shielded-target")
        target.set_position(CartesianPosition(8.0, 0.0, 0.0))
        world.add_object(target)
        encounter.add_being(target.id)
        armor_id = world.make_armor_for_being(target.id, "Leather armor",
                                              "Native target armor")
        encounter.add_object(armor_id)
        shield_id = world.make_weapon_for_being(target.id, "Small shield",
                                               "Native target shield")
        world.arm_being(target.id, shield_id, "shield hand")
        encounter.add_object(shield_id)
        weapon_id = world.make_weapon_for_being(actor.id, "Dagger",
                                                "Native thrown Dagger")
        world.arm_being(actor.id, weapon_id, "right hand")
        encounter.add_object(weapon_id)
        projectile = world.get_object_by_id(weapon_id)
        action = ThrowAction(world, actor.id, projectile.id, encounter.time,
            heavy_load_reference_lb=100.0, elevation_degrees=45,
            target_id=target.id, id="native-persist/shielded-throw")
        encounter.schedule_choice((action,))
        rng.state = random.Random(116).getstate()
        encounter.step(4)
        self.assertEqual(action.resolution.outcome, "released")
        self.assertIsNone(projectile.__dict__["_projectile_flight"].impact_outcome)
        original_projectile_history = projectile.__dict__["_atomic_projectile_history"]
        self.assertTrue(original_projectile_history)
        prior_history = native_history.capture(encounter)
        projectile.__dict__["_atomic_projectile_history"] = []
        with self.assertRaises(NativeSaveRejected):
            export_save(encounter)
        projectile.__dict__["_atomic_projectile_history"] = original_projectile_history
        self.assertEqual(native_history.capture(encounter), prior_history)
        wire = export_save(encounter)
        from native_graph_snapshot import decode as decode_graph
        graph = decode_graph(base64.b64decode(
            json.loads(wire)["graph_b64"], validate=True), native=True)
        inventory = graph[1]
        nodes = next(row[1] for row in inventory if row[0] == "nodes")
        projectile_content = next(content for _ref, tag, content in nodes
                                  if tag in ("weapon.WeaponInstance",
                                             "object.ObjectInstance")
                                  and dict(content).get("id")
                                      == ("string", projectile.id))
        history_ref = dict(projectile_content)["_atomic_projectile_history"][1]
        self.assertEqual(next(content for ref, tag, content in nodes
                              if ref == history_ref and tag == "list"), ())
        markers = next(row[1:] for row in inventory
                       if row[0] == "native-adapters")
        self.assertIn("projectile-interval-history/1", markers)

        def run_to_impact(enc, world, cursor):
            from atomic_publication import target_effects_from
            thrown = world.get_object_by_id(projectile.id)
            victim = world.get_object_by_id(target.id)
            shield = world.get_object_by_id(shield_id)
            armor = world.get_object_by_id(armor_id)
            initial_armor_hp = armor.hit_points()
            for _ in range(5):
                if thrown.__dict__["_projectile_flight"].impact_outcome is not None:
                    break
                enc.step(1)
            history_query = native_history.NativeHistoryQuery(
                native_history.capture(enc))
            for entity in (thrown, shield, armor, victim):
                for record in getattr(entity, "_atomic_target_history", ()):
                    if record.encounter_id == enc.id:
                        self.assertEqual(history_query.target_at(
                            entity.id, record.boundary),
                            native_history._plain(record.state))
            effects = [row.effect for row in target_effects_from(shield, action.id)]
            protection = next(effect for effect in effects
                              if type(effect).__name__ == "ProtectionEffect"
                              and effect.layer == "shield")
            durability = [effect.amount for effect in effects
                          if type(effect).__name__ == "DamageEffect"
                          and effect.component == "shield"]
            armor_effects = [row.effect for row in target_effects_from(armor, action.id)]
            armor_protection = next(effect for effect in armor_effects
                if type(effect).__name__ == "ProtectionEffect" and effect.layer == "armor")
            armor_durability = [effect.amount for effect in armor_effects
                if type(effect).__name__ == "DamageEffect" and effect.component == "armor"]
            return {"time": enc.time,
                    "outcome": thrown.__dict__["_projectile_flight"].impact_outcome,
                    "hp": victim.get_hit_points(), "shield_hp": shield.hit_points(),
                    "armor_hp": armor.hit_points(),
                    "initial_armor_hp": initial_armor_hp,
                    "intercepted": protection.intercepted,
                    "incoming": protection.incoming, "passed": protection.passed,
                    "durability": durability,
                    "armor_protection": [armor_protection.incoming,
                        armor_protection.passed, armor_protection.intercepted],
                    "armor_durability": armor_durability,
                    "rng": cursor.state,
                    "history": hashlib.sha256(native_history.encode(
                        native_history.capture(enc))).hexdigest()}

        expected = run_to_impact(encounter, world, rng)
        history_log = native_history.capture(encounter)
        history_query = native_history.NativeHistoryQuery(history_log)
        receipt_by_boundary = {
            receipt.boundary: receipt
            for receipt in encounter._atomic_interval_history}
        for boundary in range(encounter.last_processed_boundary + 1):
            receipt = receipt_by_boundary.get(boundary)
            states = ({} if receipt is None else
                      receipt.inspection.projectile_states)
            recorded = states.get(projectile.id)
            self.assertEqual(
                history_query.projectile_state_at(projectile.id, boundary),
                None if recorded is None else native_history._plain(recorded))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "native-shielded-projectile.json"
            path.write_bytes(wire)
            child = r'''import hashlib,json,sys
import native_history
from atomic_publication import target_effects_from
from native_persistence import load_path
world,enc,rng=load_path(sys.argv[1])
thrown=world.get_object_by_id(sys.argv[2]); victim=world.get_object_by_id(sys.argv[3])
shield=world.get_object_by_id(sys.argv[4]);armor=world.get_object_by_id(sys.argv[5])
initial_armor_hp=armor.hit_points()
for _ in range(5):
 if thrown.__dict__['_projectile_flight'].impact_outcome is not None: break
 enc.step(1)
history_query=native_history.NativeHistoryQuery(native_history.capture(enc))
for entity in (thrown,shield,armor,victim):
 for record in getattr(entity,'_atomic_target_history',()):
  if record.encounter_id==enc.id:
   assert history_query.target_at(entity.id,record.boundary)==native_history._plain(record.state)
effects=[row.effect for row in target_effects_from(shield,sys.argv[6])]
protection=next(effect for effect in effects if type(effect).__name__=='ProtectionEffect' and effect.layer=='shield')
durability=[effect.amount for effect in effects if type(effect).__name__=='DamageEffect' and effect.component=='shield']
armor_effects=[row.effect for row in target_effects_from(armor,sys.argv[6])]
armor_protection=next(effect for effect in armor_effects if type(effect).__name__=='ProtectionEffect' and effect.layer=='armor')
armor_durability=[effect.amount for effect in armor_effects if type(effect).__name__=='DamageEffect' and effect.component=='armor']
print(json.dumps({'time':enc.time,
 'outcome':thrown.__dict__['_projectile_flight'].impact_outcome,
 'hp':victim.get_hit_points(),'shield_hp':shield.hit_points(),'armor_hp':armor.hit_points(),
 'initial_armor_hp':initial_armor_hp,
 'intercepted':protection.intercepted,'incoming':protection.incoming,
 'passed':protection.passed,'durability':durability,
 'armor_protection':[armor_protection.incoming,armor_protection.passed,armor_protection.intercepted],
 'armor_durability':armor_durability,'rng':rng.state,
 'history':hashlib.sha256(native_history.encode(native_history.capture(enc))).hexdigest()},sort_keys=True))'''
            import os
            result = subprocess.run(
                [sys.executable, "-B", "-c", child, str(path), projectile.id,
                 target.id, shield_id, armor_id, action.id], cwd=ROOT,
                env={**os.environ,
                     "PYTHONPATH": f"{ROOT / 'src'}:{ROOT / 'examples'}"},
                text=True, capture_output=True, check=False, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), json.loads(json.dumps(expected)))
        self.assertEqual(expected["outcome"], "hit")
        self.assertTrue(expected["intercepted"])
        self.assertEqual(len(expected["armor_protection"]), 3)
        self.assertEqual(expected["armor_protection"], [1, 0, True])
        self.assertEqual(expected["armor_durability"], [1])
        self.assertEqual(expected["armor_hp"], expected["initial_armor_hp"] - 1)

    def test_native_file_write_recovers_across_pre_and_post_link_faults(self):
        """A failed publication leaves either no file or a valid complete Save."""
        demo = encounter_delta_headless.build_demo(until=4)
        encounter = demo["encounter"]
        with tempfile.TemporaryDirectory() as directory:
            before_path = Path(directory) / "pre-link.json"
            with patch.object(native_persistence.os, "link",
                              side_effect=OSError("injected link failure")):
                with self.assertRaisesRegex(NativeSaveRejected,
                                            "before publication"):
                    write_save(encounter, before_path)
            self.assertFalse(before_path.exists())
            self.assertEqual(sorted(path.name for path in Path(directory).iterdir()), [])

            expected_wire = export_save(encounter)
            self.assertEqual(write_save(encounter, before_path), len(expected_wire))
            self.assertEqual(before_path.read_bytes(), expected_wire)
            loaded_world, loaded_encounter, _loaded_rng = load_path(before_path)
            self.assertIs(loaded_world.event_history[loaded_encounter.id], loaded_encounter)

            after_path = Path(directory) / "post-link.json"
            original_fsync = native_persistence.os.fsync
            calls = []

            def fail_directory_sync(fd):
                calls.append(fd)
                if len(calls) == 2:
                    raise OSError("injected directory fsync failure")
                return original_fsync(fd)

            with patch.object(native_persistence.os, "fsync",
                              side_effect=fail_directory_sync):
                with self.assertRaisesRegex(NativeSaveRejected,
                                            "after atomic publication"):
                    write_save(encounter, after_path)
            self.assertEqual(len(calls), 2)
            self.assertTrue(after_path.exists())
            self.assertEqual(after_path.read_bytes(), expected_wire)
            self.assertEqual(sorted(path.name for path in Path(directory).iterdir()),
                             ["post-link.json", "pre-link.json"])
            post_world, post_encounter, _post_rng = load_path(after_path)
            self.assertIs(post_world.event_history[post_encounter.id], post_encounter)

    def test_native_save_stores_target_facts_once_and_rebuilds_history(self):
        """TargetIntervalRecord history lives in the fact stream, not graph twice."""
        import base64
        from native_graph_snapshot import decode as decode_graph
        from native_graph_snapshot import encode as encode_graph
        from checkpoint_inventory import capture_checkpoint_candidate
        from being import BeingInstance

        encounter = encounter_delta_headless.build_demo(until=4)["encounter"]
        # A registered but inactive Being has no Target intervals. Compaction
        # must preserve the distinction between an absent field and an empty
        # one so a canonical second Save remains byte-for-byte identical.
        definition = encounter.universe.library.being_dictionary.get_object_definition("Human")
        inactive = BeingInstance(definition, "Inactive registered Being",
                                 id="native-persist/inactive-being")
        encounter.universe.add_object(inactive)
        self.assertNotIn("_atomic_target_history", inactive.__dict__)
        original_candidate = capture_checkpoint_candidate(
            encounter.universe, encounter, quiescent=True,
            rng_scope="exclusive_encounter", native_adapters=True,
            full_native=True, rng_owner=native_persistence._native_rng_owner(encounter))
        original_graph_bytes = len(encode_graph(original_candidate.envelope, native=True))
        expected = {}
        for identity, entity in encounter.universe.object_registry.object_instances.items():
            rows = [row for row in getattr(entity, "_atomic_target_history", ())
                    if row.encounter_id == encounter.id]
            if rows:
                expected[identity] = [native_history._plain(row) for row in rows]

        wire = export_save(encounter)
        save = json.loads(wire)
        graph_wire = base64.b64decode(save["graph_b64"], validate=True)
        self.assertLess(len(graph_wire), original_graph_bytes)
        inventory = decode_graph(graph_wire, native=True)
        nodes = next(row[1] for row in inventory[1] if row[0] == "nodes")
        self.assertFalse(any(tag == "atomic_publication.TargetIntervalRecord"
                             for _reference, tag, _content in nodes))

        world, restored, _rng = load_save(wire)
        actual = {}
        for identity, entity in world.object_registry.object_instances.items():
            rows = [row for row in getattr(entity, "_atomic_target_history", ())
                    if row.encounter_id == restored.id]
            if rows:
                actual[identity] = [native_history._plain(row) for row in rows]
        self.assertEqual(actual, expected)
        restored_inactive = world.get_object_by_id(inactive.id)
        self.assertNotIn("_atomic_target_history", restored_inactive.__dict__)
        query = native_history.NativeHistoryQuery(
            native_history.capture(restored))
        for boundary in range(1, restored.last_processed_boundary + 1):
            self.assertEqual(query.boundary_facts_at(boundary)["target_states"],
                native_history._plain(native_history._target_candidates(restored).get(
                    boundary, {})))
        self.assertEqual(export_save(restored), wire)

    def test_native_save_stores_entity_context_once_and_rebuilds_receipts(self):
        """Committed EntityInspection maps are reconstructed from typed history."""
        import base64
        from native_graph_snapshot import decode as decode_graph
        from native_graph_snapshot import encode as encode_graph
        from checkpoint_inventory import capture_checkpoint_candidate

        encounter = encounter_delta_headless.build_demo(until=4)["encounter"]
        original_candidate = capture_checkpoint_candidate(
            encounter.universe, encounter, quiescent=True,
            rng_scope="exclusive_encounter", native_adapters=True,
            full_native=True, compact_native_target_history=True,
            rng_owner=native_persistence._native_rng_owner(encounter))
        original_graph_bytes = len(encode_graph(original_candidate.envelope, native=True))
        expected = {
            row.boundary: native_history._plain(row.inspection.entities)
            for row in encounter._atomic_interval_history
        }

        wire = export_save(encounter)
        save = json.loads(wire)
        graph_wire = base64.b64decode(save["graph_b64"], validate=True)
        self.assertLess(len(graph_wire), original_graph_bytes)
        inventory = decode_graph(graph_wire, native=True)
        nodes = next(row[1] for row in inventory[1] if row[0] == "nodes")
        self.assertFalse(any(tag == "encounter_inspection.EntityInspection"
                             for _reference, tag, _content in nodes))
        self.assertFalse(any(tag in ("encounter_inspection.CommittedBoundaryRecord",
                                     "atomic_publication.PublishedInterval")
                             for _reference, tag, _content in nodes))
        markers = next(row[1:] for row in inventory[1]
                       if row[0] == "native-adapters")
        self.assertIn("committed-boundary-history/1", markers)

        world, restored, _rng = load_save(wire)
        actual = {
            row.boundary: native_history._plain(row.inspection.entities)
            for row in restored._atomic_interval_history
        }
        self.assertEqual(actual, expected)
        query = native_history.NativeHistoryQuery(native_history.capture(restored))
        for boundary, entity_context in expected.items():
            self.assertEqual(query.boundary_facts_at(boundary)["entity_context"],
                             entity_context)
        self.assertIs(world.event_history[restored.id], restored)
        self.assertEqual(export_save(restored), wire)

    def test_native_save_rebuilds_committed_inspection_facts_from_history(self):
        """Stable receipt projections are stored once and reconstructed exactly."""
        import base64
        from native_graph_snapshot import decode as decode_graph
        from native_graph_snapshot import encode as encode_graph
        from checkpoint_inventory import capture_checkpoint_candidate

        encounter = encounter_delta_headless.build_demo(until=4)["encounter"]
        target_entity_candidate = capture_checkpoint_candidate(
            encounter.universe, encounter, quiescent=True,
            rng_scope="exclusive_encounter", native_adapters=True,
            full_native=True, compact_native_target_history=True,
            compact_native_entity_context=True,
            rng_owner=native_persistence._native_rng_owner(encounter))
        graph_before_receipt_facts = len(encode_graph(
            target_entity_candidate.envelope, native=True))
        fields = ("actions", "effects", "objective", "objective_use", "starts",
                  "participants", "schedule", "projectile_states")
        expected = {
            receipt.boundary: {
                name: native_history._plain(getattr(receipt.inspection, name))
                for name in fields
            }
            for receipt in encounter._atomic_interval_history
        }
        expected_publication = {
            receipt.boundary: {
                name: native_history._plain(getattr(receipt, name))
                for name in ("action_ids", "effect_ids", "rng_state",
                             "notification_intents")
            }
            for receipt in encounter._atomic_interval_history
        }

        wire = export_save(encounter)
        save = json.loads(wire)
        graph_wire = base64.b64decode(save["graph_b64"], validate=True)
        self.assertLess(len(graph_wire), graph_before_receipt_facts)
        inventory = decode_graph(graph_wire, native=True)
        marker = next(row[1:] for row in inventory[1]
                      if row[0] == "native-adapters")
        self.assertIn("committed-receipt-facts/1", marker)
        self.assertIn("published-interval-facts/1", marker)
        self.assertIn("disarm-landing-facts/1", marker)

        world, restored, _rng = load_save(wire)
        actual = {
            receipt.boundary: {
                name: native_history._plain(getattr(receipt.inspection, name))
                for name in fields
            }
            for receipt in restored._atomic_interval_history
        }
        actual_publication = {
            receipt.boundary: {
                name: native_history._plain(getattr(receipt, name))
                for name in ("action_ids", "effect_ids", "rng_state",
                             "notification_intents")
            }
            for receipt in restored._atomic_interval_history
        }
        self.assertEqual(actual, expected)
        self.assertEqual(actual_publication, expected_publication)
        self.assertIs(world.event_history[restored.id], restored)
        self.assertEqual(export_save(restored), wire)

    def test_native_save_rebuilds_choicebook_indexes_in_fresh_process(self):
        """ChoiceBook lookup caches compact while accepted work still resumes."""
        import os
        from native_graph_snapshot import decode as decode_graph

        encounter = encounter_delta_headless.build_demo(until=4)["encounter"]
        future = DelayAction(encounter, encounter.being_list[0], defense=0,
                             start_time=6, id="compact-choice-future-delay")
        encounter.schedule_action(future)
        before = encounter._choice_book.summary()
        state_before = native_history.capture(encounter)
        action_id = next(iter(encounter._choice_book._states))
        prior_status = encounter._choice_book._states[action_id]
        encounter._choice_book._states[action_id] = "cancelled"
        with self.assertRaises(NativeSaveRejected):
            export_save(encounter)
        encounter._choice_book._states[action_id] = prior_status
        self.assertIsNone(native_history.current_recording(encounter))
        self.assertEqual(native_history.capture(encounter), state_before)

        wire = export_save(encounter)
        payload = json.loads(wire)
        inventory = decode_graph(base64.b64decode(
            payload["graph_b64"], validate=True), native=True)
        nodes = next(row[1] for row in inventory[1] if row[0] == "nodes")
        book_content = next(content for _ref, tag, content in nodes
                            if tag == "action_choice.ChoiceBook")
        fields = dict(book_content)
        self.assertEqual(fields["_registered"], ("registration-index", ()))
        states_ref = fields["_states"][1]
        self.assertEqual(next(content for ref, tag, content in nodes
                              if ref == states_ref and tag == "ordered-map"), ())
        markers = next(row[1:] for row in inventory[1]
                       if row[0] == "native-adapters")
        self.assertIn("choice-book-indexes/1", markers)

        def outcome(encounter, rng):
            history = native_history.capture(encounter)
            return {"time": encounter.time,
                    "choicebook": encounter._choice_book.summary(),
                    "events": sorted(encounter.universe.event_history),
                    "rng": native_history._plain(rng.state),
                    "history": hashlib.sha256(
                        native_history.encode(history)).hexdigest(),
                    "state": native_history.state_at(
                        history, history["latest_boundary"])}

        while encounter.time < 7:
            encounter.step(1)
        expected = outcome(encounter,
                           native_persistence._native_rng_owner(encounter))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "compact-choice-book.json"
            path.write_bytes(wire)
            child = r'''import hashlib,json,sys
import native_history
from native_persistence import load_path
world,encounter,rng=load_path(sys.argv[1])
while encounter.time < 7:
    encounter.step(1)
history=native_history.capture(encounter)
print(json.dumps({'time':encounter.time,
 'choicebook':encounter._choice_book.summary(),
 'events':sorted(world.event_history),
 'rng':native_history._plain(rng.state),
 'history':hashlib.sha256(native_history.encode(history)).hexdigest(),
 'state':native_history.state_at(history,history['latest_boundary'])},sort_keys=True))'''
            restored = subprocess.run(
                [sys.executable, "-B", "-c", child, str(path)], cwd=ROOT,
                env={**os.environ,
                     "PYTHONPATH": f"{ROOT / 'src'}:{ROOT / 'examples'}"},
                text=True, capture_output=True, check=False, timeout=60)
        self.assertEqual(restored.returncode, 0, restored.stderr)
        self.assertEqual(json.loads(restored.stdout),
                         json.loads(json.dumps(expected)))

    def test_compacted_entity_context_rejects_altered_source_receipt(self):
        """Omitted context remains covered by authenticated receipt integrity."""
        from checkpoint_inventory import (capture_checkpoint_candidate,
                                          validate_checkpoint_candidate)
        from encounter_inspection import InspectionRejected

        encounter = encounter_delta_headless.build_demo(until=2)["encounter"]
        candidate = capture_checkpoint_candidate(
            encounter.universe, encounter, quiescent=True,
            rng_scope="exclusive_encounter", native_adapters=True,
            full_native=True, compact_native_target_history=True,
            compact_native_entity_context=True,
            rng_owner=native_persistence._native_rng_owner(encounter))
        receipt = encounter._atomic_interval_history[-1]
        from types import MappingProxyType
        object.__setattr__(receipt.inspection, "entities", MappingProxyType({}))
        with self.assertRaises(InspectionRejected):
            validate_checkpoint_candidate(encounter.universe, encounter, candidate,
                                          quiescent=True)

    def test_compacted_receipt_facts_reject_altered_source_projection(self):
        """A compact graph candidate remains sealed to its receipt source."""
        from checkpoint_inventory import (CheckpointRejected,
                                          capture_checkpoint_candidate,
                                          validate_checkpoint_candidate)
        from encounter_inspection import InspectionRejected

        encounter = encounter_delta_headless.build_demo(until=2)["encounter"]
        candidate = capture_checkpoint_candidate(
            encounter.universe, encounter, quiescent=True,
            rng_scope="exclusive_encounter", native_adapters=True,
            full_native=True, compact_native_target_history=True,
            compact_native_entity_context=True,
            compact_native_receipt_facts=True,
            rng_owner=native_persistence._native_rng_owner(encounter))
        receipt = encounter._atomic_interval_history[-1]
        from types import MappingProxyType
        object.__setattr__(receipt.inspection, "actions", MappingProxyType({}))
        with self.assertRaises((CheckpointRejected, InspectionRejected)):
            validate_checkpoint_candidate(encounter.universe, encounter,
                                          candidate, quiescent=True)

    def test_compacted_publication_facts_reject_altered_source_receipt(self):
        """Compact Action/Event identity rows remain sealed to their receipt."""
        from checkpoint_inventory import (CheckpointRejected,
                                          capture_checkpoint_candidate,
                                          validate_checkpoint_candidate)
        from encounter_inspection import InspectionRejected

        encounter = encounter_delta_headless.build_demo(until=2)["encounter"]
        candidate = capture_checkpoint_candidate(
            encounter.universe, encounter, quiescent=True,
            rng_scope="exclusive_encounter", native_adapters=True,
            full_native=True, compact_native_target_history=True,
            compact_native_entity_context=True,
            compact_native_receipt_facts=True,
            compact_native_publication_facts=True,
            rng_owner=native_persistence._native_rng_owner(encounter))
        receipt = encounter._atomic_interval_history[-1]
        object.__setattr__(receipt, "action_ids", ("forged-action-id",))
        with self.assertRaises((CheckpointRejected, InspectionRejected)):
            validate_checkpoint_candidate(encounter.universe, encounter,
                                          candidate, quiescent=True)

    def test_uncompacted_native_graph_v1_from_last_writer_migrates_strictly(self):
        """The immediately previous accepted /1 graph rewrites to compact /2."""
        import base64
        import native_graph_snapshot
        from checkpoint_inventory import capture_checkpoint_candidate
        from native_graph_snapshot import encode as encode_graph

        encounter = encounter_delta_headless.build_demo(until=4)["encounter"]
        current_wire = export_save(encounter)
        candidate = capture_checkpoint_candidate(
            encounter.universe, encounter, quiescent=True,
            rng_scope="exclusive_encounter", native_adapters=True,
            full_native=True, rng_owner=native_persistence._native_rng_owner(encounter))
        self.assertEqual(candidate.diagnostics, ())
        old_graph_data = json.loads(encode_graph(candidate.envelope, native=True))
        old_graph_data["schema"] = native_graph_snapshot._LEGACY_NATIVE_SCHEMA_V1
        old_compatibility = (
            native_graph_snapshot._LEGACY_NATIVE_GRAPH_V1_BFC_COMPATIBILITY)
        old_graph_data["compatibility"] = old_compatibility
        current_inventory = native_graph_snapshot._expand_compact_inventory(
            native_graph_snapshot._tuples(old_graph_data["inventory"]), native=True)
        old_inventory = (old_compatibility, current_inventory[1])
        old_graph_data["inventory"] = native_graph_snapshot._compact_inventory(
            old_inventory, native=True)
        unsigned_graph = {key: value for key, value in old_graph_data.items()
                          if key != "sha256"}
        old_graph_data["sha256"] = hashlib.sha256(
            native_graph_snapshot._canonical(unsigned_graph)).hexdigest()
        old_graph = native_graph_snapshot._canonical(old_graph_data)

        old_save = json.loads(current_wire)
        old_save["graph_b64"] = base64.b64encode(old_graph).decode("ascii")
        unsigned_save = {key: value for key, value in old_save.items()
                         if key != "sha256"}
        old_save["sha256"] = hashlib.sha256(
            native_persistence._canonical(unsigned_save)).hexdigest()
        restored_world, restored, _rng = load_save(
            native_persistence._canonical(old_save))
        self.assertIs(restored_world.event_history[restored.id], restored)
        self.assertEqual(export_save(restored), current_wire)

    def test_target_compact_native_graph_v2_from_previous_writer_migrates(self):
        """The immediately prior compact graph migrates to current graph facts."""
        import base64
        import native_graph_snapshot
        from checkpoint_inventory import capture_checkpoint_candidate
        from native_graph_snapshot import encode as encode_graph

        encounter = encounter_delta_headless.build_demo(until=4)["encounter"]
        current_wire = export_save(encounter)
        candidate = capture_checkpoint_candidate(
            encounter.universe, encounter, quiescent=True,
            rng_scope="exclusive_encounter", native_adapters=True,
            full_native=True, compact_native_target_history=True,
            rng_owner=native_persistence._native_rng_owner(encounter))
        prior_graph = json.loads(encode_graph(candidate.envelope, native=True))
        legacy_compatibility = (
            native_graph_snapshot._LEGACY_NATIVE_GRAPH_V2_TARGET_COMPATIBILITY)
        prior_graph["compatibility"] = legacy_compatibility
        old_inventory = native_graph_snapshot._expand_compact_inventory(
            native_graph_snapshot._tuples(prior_graph["inventory"]), native=True)
        old_inventory = (legacy_compatibility, old_inventory[1])
        prior_graph["inventory"] = native_graph_snapshot._compact_inventory(
            old_inventory, native=True)
        unsigned_graph = {key: value for key, value in prior_graph.items()
                          if key != "sha256"}
        prior_graph["sha256"] = hashlib.sha256(
            native_graph_snapshot._canonical(unsigned_graph)).hexdigest()

        prior_save = json.loads(current_wire)
        prior_save["graph_b64"] = base64.b64encode(
            native_graph_snapshot._canonical(prior_graph)).decode("ascii")
        unsigned_save = {key: value for key, value in prior_save.items()
                         if key != "sha256"}
        prior_save["sha256"] = hashlib.sha256(
            native_persistence._canonical(unsigned_save)).hexdigest()
        restored_world, restored, _rng = load_save(
            native_persistence._canonical(prior_save))
        self.assertIs(restored_world.event_history[restored.id], restored)
        self.assertEqual(export_save(restored), current_wire)

    def test_entity_compact_native_graph_v2_from_previous_writer_migrates(self):
        """The last Target+Entity graph writer remains a strict migration input."""
        import base64
        import native_graph_snapshot
        from checkpoint_inventory import capture_checkpoint_candidate
        from native_graph_snapshot import encode as encode_graph

        encounter = encounter_delta_headless.build_demo(until=4)["encounter"]
        current_wire = export_save(encounter)
        candidate = capture_checkpoint_candidate(
            encounter.universe, encounter, quiescent=True,
            rng_scope="exclusive_encounter", native_adapters=True,
            full_native=True, compact_native_target_history=True,
            compact_native_entity_context=True,
            rng_owner=native_persistence._native_rng_owner(encounter))
        prior_graph = json.loads(encode_graph(candidate.envelope, native=True))
        legacy_compatibility = (
            native_graph_snapshot._LEGACY_NATIVE_GRAPH_V2_ENTITY_COMPATIBILITY)
        prior_graph["compatibility"] = legacy_compatibility
        old_inventory = native_graph_snapshot._expand_compact_inventory(
            native_graph_snapshot._tuples(prior_graph["inventory"]), native=True)
        prior_graph["inventory"] = native_graph_snapshot._compact_inventory(
            (legacy_compatibility, old_inventory[1]), native=True)
        unsigned_graph = {key: value for key, value in prior_graph.items()
                          if key != "sha256"}
        prior_graph["sha256"] = hashlib.sha256(
            native_graph_snapshot._canonical(unsigned_graph)).hexdigest()

        prior_save = json.loads(current_wire)
        prior_save["graph_b64"] = base64.b64encode(
            native_graph_snapshot._canonical(prior_graph)).decode("ascii")
        unsigned_save = {key: value for key, value in prior_save.items()
                         if key != "sha256"}
        prior_save["sha256"] = hashlib.sha256(
            native_persistence._canonical(unsigned_save)).hexdigest()
        restored_world, restored, _rng = load_save(
            native_persistence._canonical(prior_save))
        self.assertIs(restored_world.event_history[restored.id], restored)
        self.assertEqual(export_save(restored), current_wire)

    def test_receipt_fact_compact_native_graph_v2_from_previous_writer_migrates(self):
        """The last receipt-fact `/2` writer remains a strict migration input."""
        import base64
        import native_graph_snapshot
        from checkpoint_inventory import capture_checkpoint_candidate
        from native_graph_snapshot import encode as encode_graph

        encounter = encounter_delta_headless.build_demo(until=4)["encounter"]
        current_wire = export_save(encounter)
        candidate = capture_checkpoint_candidate(
            encounter.universe, encounter, quiescent=True,
            rng_scope="exclusive_encounter", native_adapters=True,
            full_native=True, compact_native_target_history=True,
            compact_native_entity_context=True,
            compact_native_receipt_facts=True,
            rng_owner=native_persistence._native_rng_owner(encounter))
        prior_graph = json.loads(encode_graph(candidate.envelope, native=True))
        legacy_compatibility = (
            native_graph_snapshot._LEGACY_NATIVE_GRAPH_V2_RECEIPT_FACTS_COMPATIBILITY)
        prior_graph["compatibility"] = legacy_compatibility
        old_inventory = native_graph_snapshot._expand_compact_inventory(
            native_graph_snapshot._tuples(prior_graph["inventory"]), native=True)
        prior_graph["inventory"] = native_graph_snapshot._compact_inventory(
            (legacy_compatibility, old_inventory[1]), native=True)
        unsigned_graph = {key: value for key, value in prior_graph.items()
                          if key != "sha256"}
        prior_graph["sha256"] = hashlib.sha256(
            native_graph_snapshot._canonical(unsigned_graph)).hexdigest()

        prior_save = json.loads(current_wire)
        prior_save["graph_b64"] = base64.b64encode(
            native_graph_snapshot._canonical(prior_graph)).decode("ascii")
        unsigned_save = {key: value for key, value in prior_save.items()
                         if key != "sha256"}
        prior_save["sha256"] = hashlib.sha256(
            native_persistence._canonical(unsigned_save)).hexdigest()
        restored_world, restored, _rng = load_save(
            native_persistence._canonical(prior_save))
        self.assertIs(restored_world.event_history[restored.id], restored)
        self.assertEqual(export_save(restored), current_wire)

    def test_missed_projectile_continues_with_native_unresolved_destination(self):
        """A miss preserves its adopted direction and unresolved landing in Load."""
        import random
        from being import BeingInstance
        from activities import ThrowAction
        from native_throw_arena import build_native_scene

        world, encounter, actor, projectile, rng, original = build_native_scene()
        encounter._choice_book.undo(encounter._choice_book.for_action(original.id).id)
        definition = world.library.being_dictionary.get_object_definition("Human")
        target = BeingInstance(definition, "Native Miss Target",
                              id="native-persist/miss-target")
        target.set_position(CartesianPosition(8.0, 0.0, 0.0))
        world.add_object(target)
        encounter.add_being(target.id)
        encounter.mark_aware(actor.id, target.id)
        action = ThrowAction(world, actor.id, projectile.id, encounter.time,
            heavy_load_reference_lb=100.0, elevation_degrees=45,
            target_id=target.id, id="native-persist/missed-throw")
        encounter.schedule_choice((action,))
        rng.state = random.Random(0).getstate()
        encounter.step(4)
        self.assertEqual(action.resolution.outcome, "released")
        self.assertIsNone(projectile.__dict__["_projectile_flight"].impact_outcome)
        original_projectile_history = projectile.__dict__["_atomic_projectile_history"]
        self.assertTrue(original_projectile_history)
        prior_history = native_history.capture(encounter)
        projectile.__dict__["_atomic_projectile_history"] = []
        with self.assertRaises(NativeSaveRejected):
            export_save(encounter)
        projectile.__dict__["_atomic_projectile_history"] = original_projectile_history
        self.assertEqual(native_history.capture(encounter), prior_history)
        wire = export_save(encounter)

        def continue_to_miss(enc, saved_world, cursor):
            thrown = saved_world.get_object_by_id(projectile.id)
            victim = saved_world.get_object_by_id(target.id)
            for _ in range(6):
                if thrown.__dict__["_projectile_flight"].impact_outcome is not None:
                    break
                enc.step(1)
            flight = thrown.__dict__["_projectile_flight"]
            state = thrown.__dict__["_atomic_projectile_history"][-1]
            log = native_history.capture(enc)
            query = native_history.NativeHistoryQuery(log)
            for boundary in range(enc.last_processed_boundary + 1):
                receipt = next((row for row in enc._atomic_interval_history
                                if row.boundary == boundary), None)
                recorded = (None if receipt is None else
                            receipt.inspection.projectile_states.get(thrown.id))
                self.assertEqual(query.projectile_state_at(thrown.id, boundary),
                    None if recorded is None else native_history._plain(recorded))
            return {
                "time": enc.time,
                "outcome": flight.impact_outcome,
                "status": flight.status,
                "miss_direction": flight.miss_direction,
                "position": thrown.get_position().as_tuple(),
                "landing_position": flight.landing_position.as_tuple(),
                "impact_damage": state.impact_damage,
                "state_status": state.status,
                "state_direction": state.miss_direction,
                "target_hp": victim.get_hit_points(),
                "rng": cursor.state,
                "history": hashlib.sha256(native_history.encode(log)).hexdigest(),
            }

        expected = continue_to_miss(encounter, world, rng)
        self.assertEqual(expected["outcome"], "miss")
        self.assertIn(expected["miss_direction"], range(1, 9))
        self.assertEqual(expected["state_status"], "miss_unresolved")
        self.assertEqual(expected["state_direction"], expected["miss_direction"])
        self.assertEqual(expected["impact_damage"], 0)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "native-missed-projectile.json"
            path.write_bytes(wire)
            child = r'''import hashlib,json,sys
import native_history
from native_persistence import load_path,export_save
saved_wire=open(sys.argv[1],'rb').read()
world,enc,rng=load_path(sys.argv[1])
assert export_save(enc)==saved_wire
thrown=world.get_object_by_id(sys.argv[2]); victim=world.get_object_by_id(sys.argv[3])
for _ in range(6):
 if thrown.__dict__['_projectile_flight'].impact_outcome is not None: break
 enc.step(1)
flight=thrown.__dict__['_projectile_flight']
state=thrown.__dict__['_atomic_projectile_history'][-1]
log=native_history.capture(enc); query=native_history.NativeHistoryQuery(log)
for boundary in range(enc.last_processed_boundary+1):
 receipt=next((row for row in enc._atomic_interval_history
  if row.boundary==boundary),None)
 recorded=None if receipt is None else receipt.inspection.projectile_states.get(thrown.id)
 assert query.projectile_state_at(thrown.id,boundary)==(None if recorded is None
  else native_history._plain(recorded))
print(json.dumps({'time':enc.time,'outcome':flight.impact_outcome,
 'status':flight.status,'miss_direction':flight.miss_direction,
 'position':thrown.get_position().as_tuple(),
 'landing_position':flight.landing_position.as_tuple(),
 'impact_damage':state.impact_damage,'state_status':state.status,
 'state_direction':state.miss_direction,'target_hp':victim.get_hit_points(),
 'rng':rng.state,'history':hashlib.sha256(native_history.encode(log)).hexdigest()},
 sort_keys=True))'''
            result = subprocess.run(
                [sys.executable, "-B", "-c", child, str(path), projectile.id, target.id],
                cwd=directory,
                env={**__import__("os").environ,
                     "PYTHONPATH": f"{ROOT / 'src'}:{ROOT / 'examples'}"},
                text=True, capture_output=True, check=False, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), json.loads(json.dumps(expected)))

    def test_target_movement_during_projectile_flight_restores_natively(self):
        """Ordinary native movement before impact remains a target-moved result."""
        from being import BeingInstance
        from activities import ThrowAction
        from native_throw_arena import build_native_scene

        world, encounter, actor, projectile, rng, original = build_native_scene()
        encounter._choice_book.undo(encounter._choice_book.for_action(original.id).id)
        definition = world.library.being_dictionary.get_object_definition("Human")
        target = BeingInstance(definition, "Moving Native Target",
                              id="native-persist/moving-target")
        target.set_position(CartesianPosition(8.0, 0.0, 0.0))
        world.add_object(target)
        encounter.add_being(target.id)
        encounter.mark_aware(actor.id, target.id)
        action = ThrowAction(world, actor.id, projectile.id, encounter.time,
            heavy_load_reference_lb=100.0, elevation_degrees=45,
            target_id=target.id, id="native-persist/moving-target-throw")
        encounter.schedule_choice((action,))
        encounter.step(4)
        self.assertEqual(action.resolution.outcome, "released")
        self.assertGreater(projectile.__dict__["_projectile_flight"].impact_time, 7)
        self.assertLess(projectile.__dict__["_projectile_flight"].impact_time, 8)
        wire = export_save(encounter)

        def continue_movement_and_impact(enc, saved_world, cursor):
            victim = saved_world.get_object_by_id(target.id)
            thrown = saved_world.get_object_by_id(projectile.id)
            initial_hp = victim.get_hit_points()
            enc.step(3, velocities={victim.id: (0.0, 0.2, 0.0)})
            enc.step(1)
            flight = thrown.__dict__["_projectile_flight"]
            state = thrown.__dict__["_atomic_projectile_history"][-1]
            log = native_history.capture(enc)
            query = native_history.NativeHistoryQuery(log)
            for boundary in range(enc.last_processed_boundary + 1):
                receipt = next((row for row in enc._atomic_interval_history
                                if row.boundary == boundary), None)
                recorded = (None if receipt is None else
                            receipt.inspection.projectile_states.get(thrown.id))
                self.assertEqual(query.projectile_state_at(thrown.id, boundary),
                    None if recorded is None else native_history._plain(recorded))
            return {
                "time": enc.time,
                "outcome": flight.impact_outcome,
                "status": flight.status,
                "target_position": victim.get_position().as_tuple(),
                "target_hp": victim.get_hit_points(),
                "initial_target_hp": initial_hp,
                "projectile_position": thrown.get_position().as_tuple(),
                "impact_damage": state.impact_damage,
                "state_status": state.status,
                "rng": cursor.state,
                "history": hashlib.sha256(native_history.encode(log)).hexdigest(),
            }

        expected = continue_movement_and_impact(encounter, world, rng)
        self.assertEqual(expected["outcome"], "target_moved")
        self.assertEqual(expected["status"], "landed")
        self.assertEqual(expected["target_position"], (8.0, 0.6, 0.0))
        self.assertEqual(expected["target_hp"], expected["initial_target_hp"])
        self.assertEqual(expected["impact_damage"], 0)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "native-moving-projectile-target.json"
            path.write_bytes(wire)
            child = r'''import hashlib,json,sys
import native_history
from native_persistence import load_path
world,enc,rng=load_path(sys.argv[1])
victim=world.get_object_by_id(sys.argv[2]); thrown=world.get_object_by_id(sys.argv[3])
initial_hp=victim.get_hit_points()
enc.step(3,velocities={victim.id:(0.0,0.2,0.0)})
enc.step(1)
flight=thrown.__dict__['_projectile_flight']
state=thrown.__dict__['_atomic_projectile_history'][-1]
log=native_history.capture(enc);query=native_history.NativeHistoryQuery(log)
for boundary in range(enc.last_processed_boundary+1):
 receipt=next((row for row in enc._atomic_interval_history
  if row.boundary==boundary),None)
 recorded=None if receipt is None else receipt.inspection.projectile_states.get(thrown.id)
 assert query.projectile_state_at(thrown.id,boundary)==(None if recorded is None
  else native_history._plain(recorded))
print(json.dumps({'time':enc.time,'outcome':flight.impact_outcome,
 'status':flight.status,'target_position':victim.get_position().as_tuple(),
 'target_hp':victim.get_hit_points(),'initial_target_hp':initial_hp,
 'projectile_position':thrown.get_position().as_tuple(),
 'impact_damage':state.impact_damage,'state_status':state.status,
 'rng':rng.state,'history':hashlib.sha256(native_history.encode(log)).hexdigest()},
 sort_keys=True))'''
            result = subprocess.run(
                [sys.executable, "-B", "-c", child, str(path), target.id, projectile.id],
                cwd=directory,
                env={**__import__("os").environ,
                     "PYTHONPATH": f"{ROOT / 'src'}:{ROOT / 'examples'}"},
                text=True, capture_output=True, check=False, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), json.loads(json.dumps(expected)))

    def test_thrown_coup_de_grace_restores_critical_consequences(self):
        """A held Dagger's release, flight and native coup consequences survive Load."""
        from being import BeingInstance
        from activities import ThrowAction
        from atomic_publication import target_effects_from
        from native_throw_arena import build_native_scene

        world, encounter, actor, _projectile, rng, original = build_native_scene(seed=816)
        encounter._choice_book.undo(encounter._choice_book.for_action(original.id).id)
        definition = world.library.being_dictionary.get_object_definition("Human")
        target = BeingInstance(definition, "Helpless Target",
                              id="native-persist/fatal-throw-target")
        target.current.hit_points = 0
        target.set_position(CartesianPosition(0.5, 0.0, 0.0))
        world.add_object(target)
        encounter.add_being(target.id)
        encounter.mark_aware(actor.id, target.id)
        weapon_id = world.make_weapon_for_being(actor.id, "Dagger", "Coup Dagger")
        actor.set_body_part_holds_object("right hand", weapon_id)
        encounter.add_object(weapon_id)
        action = ThrowAction(world, actor.id, weapon_id, encounter.time,
            heavy_load_reference_lb=100.0, elevation_degrees=45,
            target_id=target.id, coup_de_grace=True,
            id="native-persist/fatal-throw")
        encounter.schedule_choice((action,))
        encounter.step(4)
        self.assertEqual(action.resolution.outcome, "released")
        self.assertEqual(encounter.inspect_committed(4).target(weapon_id)
                         .projectile_state.status, "in_flight")
        wire = export_save(encounter)

        def continue_to_impact(enc, saved_world, cursor):
            victim = saved_world.get_object_by_id(target.id)
            dagger = saved_world.get_object_by_id(weapon_id)
            enc.step(4)
            flight = dagger.__dict__["_projectile_flight"]
            action_view = enc.inspect_committed(8).action(action.id)
            effects = [row.effect for row in target_effects_from(victim, action.id)]
            critical = [effect.amount for effect in effects
                        if type(effect).__name__ == "DamageEffect"
                        and effect.component == "critical_bypass"]
            body = [effect.amount for effect in effects
                    if type(effect).__name__ == "DamageEffect"
                    and effect.component == "body"]
            log = native_history.capture(enc)
            return {
                "time": enc.time,
                "outcome": flight.impact_outcome,
                "status": flight.status,
                "hp": victim.get_hit_points(),
                "damage_components": [body, critical],
                "action_outcome": action_view.facts.outcome,
                "source_effect_identity": flight.source_effect_identity,
                "rng": cursor.state,
                "history": hashlib.sha256(native_history.encode(log)).hexdigest(),
            }

        expected = continue_to_impact(encounter, world, rng)
        self.assertEqual(expected["outcome"], "hit")
        self.assertEqual(expected["status"], "landed")
        self.assertLess(expected["hp"], 0)
        self.assertEqual(expected["damage_components"], [[2], [1]])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "native-thrown-coup-save.json"
            path.write_bytes(wire)
            child = r'''import hashlib,json,sys
import native_history
from atomic_publication import target_effects_from
from native_persistence import load_path
world,enc,rng=load_path(sys.argv[1])
victim=world.get_object_by_id(sys.argv[2]);dagger=world.get_object_by_id(sys.argv[3])
action=world.get_event_by_id(sys.argv[4]);enc.step(4)
flight=dagger.__dict__['_projectile_flight']
action_view=enc.inspect_committed(8).action(action.id)
effects=[row.effect for row in target_effects_from(victim,action.id)]
critical=[effect.amount for effect in effects if type(effect).__name__=='DamageEffect'
 and effect.component=='critical_bypass']
body=[effect.amount for effect in effects if type(effect).__name__=='DamageEffect'
 and effect.component=='body']
log=native_history.capture(enc)
print(json.dumps({'time':enc.time,'outcome':flight.impact_outcome,
 'status':flight.status,'hp':victim.get_hit_points(),
 'damage_components':[body,critical],'action_outcome':action_view.facts.outcome,
 'source_effect_identity':flight.source_effect_identity,'rng':rng.state,
 'history':hashlib.sha256(native_history.encode(log)).hexdigest()},sort_keys=True))'''
            result = subprocess.run(
                [sys.executable, "-B", "-c", child, str(path), target.id, weapon_id,
                 action.id], cwd=directory,
                env={**__import__("os").environ,
                     "PYTHONPATH": f"{ROOT / 'src'}:{ROOT / 'examples'}"},
                text=True, capture_output=True, check=False, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), json.loads(json.dumps(expected)))

    def test_thrown_coup_de_grace_fatal_outcome_restores_with_causal_damage(self):
        """The fatal Fortitude branch keeps ordered damage and death causality."""
        import random
        from being import BeingInstance
        from activities import ThrowAction
        from atomic_publication import target_effects_from
        from native_throw_arena import build_native_scene

        world, encounter, actor, _stone, rng, original = build_native_scene(seed=0)
        encounter._choice_book.undo(encounter._choice_book.for_action(original.id).id)
        target = BeingInstance(world.library.being_dictionary.get_object_definition("Human"),
                               "Fatal Coup target", id="native-persist/fatal-coup-target")
        target.current.hit_points = 0
        target.set_position(CartesianPosition(0.5, 0.0, 0.0))
        world.add_object(target)
        encounter.add_being(target.id)
        encounter.mark_aware(actor.id, target.id)
        weapon_id = world.make_weapon_for_being(actor.id, "Dagger", "Fatal Coup Dagger")
        actor.set_body_part_holds_object("right hand", weapon_id)
        encounter.add_object(weapon_id)
        action = ThrowAction(world, actor.id, weapon_id, encounter.time,
            heavy_load_reference_lb=100.0, elevation_degrees=45,
            target_id=target.id, coup_de_grace=True,
            id="native-persist/fatal-throw-coup")
        encounter.schedule_choice((action,))
        rng.state = random.Random(0).getstate()
        encounter.step(4)
        self.assertEqual(action.resolution.outcome, "released")
        wire = export_save(encounter)

        def continue_to_fatal(enc, saved_world, cursor):
            victim = saved_world.get_object_by_id(target.id)
            dagger = saved_world.get_object_by_id(weapon_id)
            enc.step(4)
            flight = dagger.__dict__["_projectile_flight"]
            action_view = enc.inspect_committed(8).action(action.id)
            effects = [row.effect for row in target_effects_from(victim, action.id)]
            fatal_effects = [effect for effect in effects
                if type(effect).__name__ == "FatalEffect"]
            damage = [[effect.component, effect.amount] for effect in effects
                if type(effect).__name__ == "DamageEffect"]
            history = native_history.capture(enc)
            query = native_history.NativeHistoryQuery(history)
            for boundary in range(enc.last_processed_boundary + 1):
                receipt = next((row for row in enc._atomic_interval_history
                                if row.boundary == boundary), None)
                recorded = (None if receipt is None else
                            receipt.inspection.projectile_states.get(weapon_id))
                self.assertEqual(query.projectile_state_at(weapon_id, boundary),
                    None if recorded is None else native_history._plain(recorded))
            return {
                "time": enc.time,
                "flight_outcome": flight.impact_outcome,
                "flight_status": flight.status,
                "action_outcome": action_view.facts.outcome,
                "target_hp": victim.get_hit_points(),
                "damage": damage,
                "fatal_effects": [effect.target_id for effect in fatal_effects],
                "fatal_effect_identity": [native_history._plain(row.identity)
                    for row in target_effects_from(victim, action.id)
                    if type(row.effect).__name__ == "FatalEffect"],
                "rng": cursor.state,
                "history": hashlib.sha256(native_history.encode(history)).hexdigest(),
            }

        expected = continue_to_fatal(encounter, world, rng)
        self.assertEqual(expected["flight_outcome"], "fatal")
        self.assertEqual(expected["flight_status"], "landed")
        self.assertEqual(expected["action_outcome"], "released")
        self.assertEqual(expected["fatal_effects"], [target.id])
        self.assertEqual(expected["damage"], [["body", 4], ["critical_bypass", 4]])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "native-fatal-throw-coup.json"
            path.write_bytes(wire)
            child = r'''import hashlib,json,sys
import native_history
from atomic_publication import target_effects_from
from native_persistence import load_path
world,enc,rng=load_path(sys.argv[1])
victim=world.get_object_by_id(sys.argv[2]);dagger=world.get_object_by_id(sys.argv[3])
action=world.get_event_by_id(sys.argv[4]);enc.step(4)
flight=dagger.__dict__['_projectile_flight'];action_view=enc.inspect_committed(8).action(action.id)
effects=[row.effect for row in target_effects_from(victim,action.id)]
fatal=[effect for effect in effects if type(effect).__name__=='FatalEffect']
damage=[[effect.component,effect.amount] for effect in effects if type(effect).__name__=='DamageEffect']
history=native_history.capture(enc);query=native_history.NativeHistoryQuery(history)
for boundary in range(enc.last_processed_boundary+1):
 receipt=next((row for row in enc._atomic_interval_history if row.boundary==boundary),None)
 recorded=None if receipt is None else receipt.inspection.projectile_states.get(dagger.id)
 assert query.projectile_state_at(dagger.id,boundary)==(None if recorded is None
  else native_history._plain(recorded))
print(json.dumps({'time':enc.time,'flight_outcome':flight.impact_outcome,
 'flight_status':flight.status,'action_outcome':action_view.facts.outcome,
 'target_hp':victim.get_hit_points(),'damage':damage,
 'fatal_effects':[effect.target_id for effect in fatal],
 'fatal_effect_identity':[native_history._plain(row.identity)
  for row in target_effects_from(victim,action.id) if type(row.effect).__name__=='FatalEffect'],
 'rng':rng.state,'history':hashlib.sha256(native_history.encode(history)).hexdigest()},sort_keys=True))'''
            result = subprocess.run(
                [sys.executable, "-B", "-c", child, str(path), target.id,
                 weapon_id, action.id], cwd=directory,
                env={**__import__("os").environ,
                     "PYTHONPATH": f"{ROOT / 'src'}:{ROOT / 'examples'}"},
                text=True, capture_output=True, check=False, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), json.loads(json.dumps(expected)))

    def test_pending_targeted_throw_choice_restores_before_release_and_impact(self):
        """Initial-state Load resumes the accepted held-Weapon Throw declaration."""
        import random
        from being import BeingInstance
        from activities import ThrowAction
        from native_throw_arena import build_native_scene

        world, encounter, actor, _stone, rng, original = build_native_scene(seed=116)
        encounter._choice_book.undo(encounter._choice_book.for_action(original.id).id)
        target = BeingInstance(world.library.being_dictionary.get_object_definition("Human"),
                               "Pending Throw target", id="native-persist/pending-throw-target")
        target.set_position(CartesianPosition(8.0, 0.0, 0.0))
        world.add_object(target)
        encounter.add_being(target.id)
        encounter.mark_aware(actor.id, target.id)
        weapon_id = world.make_weapon_for_being(actor.id, "Dagger", "Pending Throw Dagger")
        world.arm_being(actor.id, weapon_id, "right hand")
        encounter.add_object(weapon_id)
        action = ThrowAction(world, actor.id, weapon_id, encounter.time,
            heavy_load_reference_lb=100.0, elevation_degrees=45,
            target_id=target.id, id="native-persist/pending-throw")
        encounter.schedule_choice((action,))
        rng.state = random.Random(116).getstate()
        wire = export_save(encounter)
        self.assertEqual(json.loads(wire)["history"], None)

        def finish(enc, saved_world, cursor):
            victim = saved_world.get_object_by_id(target.id)
            thrown = saved_world.get_object_by_id(weapon_id)
            event = action
            enc.step(8)
            flight = thrown.__dict__["_projectile_flight"]
            log = native_history.capture(enc)
            query = native_history.NativeHistoryQuery(log)
            for boundary in range(1, enc.last_processed_boundary + 1):
                inspection = enc.inspect_committed(boundary)
                committed = query.committed_actions_at(boundary)
                self.assertEqual(committed["actions"], native_history._plain(inspection.actions))
                self.assertEqual(committed["effects"], native_history._plain(inspection.effects))
                self.assertEqual(query.timeline_at(boundary),
                                 native_history._plain(inspection.timeline))
            return {
                "time": enc.time,
                "action_id": event.id,
                "action_outcome": event.resolution.outcome,
                "flight_outcome": flight.impact_outcome,
                "flight_status": flight.status,
                "target_hp": victim.get_hit_points(),
                "weapon_position": thrown.get_position().as_tuple(),
                "rng": cursor.state,
                "history": hashlib.sha256(native_history.encode(log)).hexdigest(),
            }

        expected = finish(encounter, world, rng)
        self.assertEqual(expected["action_outcome"], "released")
        self.assertEqual(expected["flight_outcome"], "hit")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "native-pending-throw.json"
            path.write_bytes(wire)
            child = r'''import hashlib,json,sys
import native_history
from native_persistence import load_path
world,enc,rng=load_path(sys.argv[1])
victim=world.get_object_by_id(sys.argv[2]);thrown=world.get_object_by_id(sys.argv[3])
choice=enc.choice_for_action(sys.argv[4])
event=next(member.action for member in enc._choice_book._choices[choice.id].members
 if member.action.id==sys.argv[4])
assert choice.state=='accepted' and event.resolution is None
enc.step(8);flight=thrown.__dict__['_projectile_flight']
log=native_history.capture(enc);query=native_history.NativeHistoryQuery(log)
for boundary in range(1,enc.last_processed_boundary+1):
 inspection=enc.inspect_committed(boundary);committed=query.committed_actions_at(boundary)
 assert committed['actions']==native_history._plain(inspection.actions)
 assert committed['effects']==native_history._plain(inspection.effects)
 assert query.timeline_at(boundary)==native_history._plain(inspection.timeline)
print(json.dumps({'time':enc.time,'action_id':event.id,
 'action_outcome':event.resolution.outcome,'flight_outcome':flight.impact_outcome,
 'flight_status':flight.status,'target_hp':victim.get_hit_points(),
 'weapon_position':thrown.get_position().as_tuple(),'rng':rng.state,
 'history':hashlib.sha256(native_history.encode(log)).hexdigest()},sort_keys=True))'''
            result = subprocess.run(
                [sys.executable, "-B", "-c", child, str(path), target.id,
                 weapon_id, action.id], cwd=directory,
                env={**__import__("os").environ,
                     "PYTHONPATH": f"{ROOT / 'src'}:{ROOT / 'examples'}"},
                text=True, capture_output=True, check=False, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), json.loads(json.dumps(expected)))

    def test_simultaneous_projectile_arrivals_restore_as_one_native_boundary(self):
        """A saved in-flight batch keeps both causal arrivals in one atomic cut."""
        import random
        from being import BeingInstance
        from activities import ThrowAction
        from native_throw_arena import build_native_scene

        world, encounter, first_actor, first_projectile, rng, original = \
            build_native_scene(seed=422)
        encounter._choice_book.undo(encounter._choice_book.for_action(original.id).id)
        definition = world.library.being_dictionary.get_object_definition("Human")
        target = BeingInstance(definition, "Shared target",
                               id="native-persist/simultaneous-projectile-target")
        target.set_position(CartesianPosition(8.0, 0.0, 0.0))
        second_actor = BeingInstance(definition, "Second thrower",
                                     id="native-persist/second-thrower")
        second_actor.set_position(CartesianPosition(16.0, 0.0, 0.0))
        world.add_object(target)
        world.add_object(second_actor)
        encounter.add_being(target.id)
        encounter.add_being(second_actor.id)
        second_projectile_id = world.make_object_for_being(
            second_actor.id, "Rock", "Second projectile")
        encounter.add_object(second_projectile_id)
        first = ThrowAction(world, first_actor.id, first_projectile.id,
            encounter.time, heavy_load_reference_lb=100.0, elevation_degrees=45,
            target_id=target.id, id="native-persist/simultaneous-first-throw")
        second = ThrowAction(world, second_actor.id, second_projectile_id,
            encounter.time, heavy_load_reference_lb=100.0, elevation_degrees=45,
            target_id=target.id, id="native-persist/simultaneous-second-throw")
        encounter.schedule_choice((first, second))
        # The established seed gives this represented target one native hit
        # while both projectiles resolve from the same integer-boundary cut.
        rng.state = random.Random(116).getstate()
        encounter.step(4)
        self.assertTrue(all(world.get_object_by_id(object_id).__dict__.get(
            "_projectile_flight") is not None
            for object_id in (first_projectile.id, second_projectile_id)))
        wire = export_save(encounter)

        def continue_batch(enc, saved_world, cursor):
            victim = saved_world.get_object_by_id(target.id)
            enc.step(3)
            flights = [saved_world.get_object_by_id(object_id).__dict__["_projectile_flight"]
                       for object_id in (first_projectile.id, second_projectile_id)]
            log = native_history.capture(enc)
            query = native_history.NativeHistoryQuery(log)
            for boundary in range(1, enc.last_processed_boundary + 1):
                receipt = enc.inspect_committed(boundary)
                committed = query.committed_actions_at(boundary)
                self.assertEqual(committed["actions"], native_history._plain(receipt.actions))
                self.assertEqual(committed["effects"], native_history._plain(receipt.effects))
                self.assertEqual(query.timeline_at(boundary),
                                 native_history._plain(receipt.timeline))
            impact = next(row for row in enc._atomic_interval_history
                          if row.boundary == 7)
            impact_states = [saved_world.get_object_by_id(object_id).__dict__[
                "_atomic_projectile_history"][-1]
                for object_id in (first_projectile.id, second_projectile_id)]
            return {
                "time": enc.time,
                "last_boundary": enc.last_processed_boundary,
                "outcomes": [flight.impact_outcome for flight in flights],
                "damages": [state.impact_damage for state in impact_states],
                "target_hp": victim.get_hit_points(),
                "impact_actions": [row.action_id for row in impact.inspection.actions],
                "impact_projectiles": sorted(impact.inspection.projectile_states),
                "impact_effects": [native_history._plain(row)
                                    for row in impact.inspection.effects],
                "rng": native_history._plain(cursor.state),
                "history": hashlib.sha256(native_history.encode(log)).hexdigest(),
            }

        expected = continue_batch(encounter, world, rng)
        self.assertIn("hit", expected["outcomes"])
        self.assertEqual(len(expected["impact_projectiles"]), 2)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "native-simultaneous-projectiles.json"
            path.write_bytes(wire)
            child = r'''import hashlib,json,sys
import native_history
from native_persistence import load_path
world,enc,rng=load_path(sys.argv[1]);target=world.get_object_by_id(sys.argv[2])
objects=json.loads(sys.argv[3]);enc.step(3)
flights=[world.get_object_by_id(key).__dict__['_projectile_flight'] for key in objects]
log=native_history.capture(enc);query=native_history.NativeHistoryQuery(log)
for boundary in range(1,enc.last_processed_boundary+1):
 receipt=enc.inspect_committed(boundary);committed=query.committed_actions_at(boundary)
 assert committed['actions']==native_history._plain(receipt.actions)
 assert committed['effects']==native_history._plain(receipt.effects)
 assert query.timeline_at(boundary)==native_history._plain(receipt.timeline)
impact=next(row for row in enc._atomic_interval_history if row.boundary==7)
states=[world.get_object_by_id(key).__dict__['_atomic_projectile_history'][-1]
 for key in objects]
print(json.dumps({'time':enc.time,'last_boundary':enc.last_processed_boundary,
 'outcomes':[flight.impact_outcome for flight in flights],
 'damages':[state.impact_damage for state in states],
 'target_hp':target.get_hit_points(),
 'impact_actions':[row.action_id for row in impact.inspection.actions],
 'impact_projectiles':sorted(impact.inspection.projectile_states),
 'impact_effects':[native_history._plain(row) for row in impact.inspection.effects],
 'rng':native_history._plain(rng.state),
 'history':hashlib.sha256(native_history.encode(log)).hexdigest()},sort_keys=True))'''
            result = subprocess.run(
                [sys.executable, "-B", "-c", child, str(path), target.id,
                 json.dumps([first_projectile.id, second_projectile_id])], cwd=directory,
                env={**__import__("os").environ,
                     "PYTHONPATH": f"{ROOT / 'src'}:{ROOT / 'examples'}"},
                text=True, capture_output=True, check=False, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), json.loads(json.dumps(expected)))

    def test_strict_outer_integrity_and_duplicate_keys_are_rejected(self):
        demo = encounter_delta_headless.build_demo(until=4)
        wire = export_save(demo["encounter"])
        value = json.loads(wire)
        value["history"]["latest_boundary"] = 3
        tampered = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
        with self.assertRaisesRegex(NativeSaveRejected, "integrity"):
            load_save(tampered)

        # Recompute both public digests after corrupting a valid property
        # preimage. Integrity hashes are not a substitute for causal checks.
        value = json.loads(wire)
        history = value["history"]
        delta = next(change for row in history["boundaries"]
                     if row.get("kind") != "quiet_span"
                     for change in row["changes"]
                     if change.get("before") is True and "before_value" in change)
        delta["before_value"] = {"forged": "but rehashed"}
        history.pop("sha256")
        history["sha256"] = hashlib.sha256(
            native_persistence._canonical(history)).hexdigest()
        value.pop("sha256")
        value["sha256"] = hashlib.sha256(
            native_persistence._canonical(value)).hexdigest()
        rehashed = native_persistence._canonical(value)
        with self.assertRaisesRegex(NativeSaveRejected, "preimage"):
            load_save(rehashed)
        with self.assertRaisesRegex(NativeSaveRejected, "duplicate"):
            load_save(b'{"schema":"a","schema":"b"}')

    def test_rejected_first_export_does_not_attach_history_recorder(self):
        demo = encounter_delta_headless.build_demo(until=4)
        encounter = demo['encounter']
        self.assertFalse(native_history.has_recorder(encounter))
        with patch('native_persistence.MAX_BYTES', 1):
            with self.assertRaisesRegex(NativeSaveRejected, 'portable size limit'):
                export_save(encounter)
        self.assertFalse(native_history.has_recorder(encounter))
        accepted = export_save(encounter)
        self.assertTrue(native_history.has_recorder(encounter))
        self.assertEqual(load_save(accepted)[1].id, encounter.id)

    def test_native_melee_damage_history_and_fresh_process_continuation(self):
        world, encounter, rng, attacker, defender, weapon_id = self._combat_encounter()
        first = MeleeStrike(encounter, attacker.id, defender.id, weapon_id,
                            motion="thrust", reach=2, strategy=Strategy())
        encounter.schedule_action(first)
        encounter.step(4)
        facts = encounter.inspect_committed(4).action(first.id).facts
        self.assertEqual(facts.outcome, "normal")
        self.assertLess(defender.get_hit_points(), 100)

        recorder = NativeHistoryRecorder.attach(encounter)
        second = MeleeStrike(encounter, attacker.id, defender.id, weapon_id,
                             motion="thrust", reach=2, strategy=Strategy())
        encounter.schedule_action(second)
        save = export_save(encounter)
        encounter.step(4)
        self.assertEqual(recorder.latest_boundary, 8)
        expected = {
            "time": encounter.time,
            "rng": json.loads(json.dumps(rng.state)),
            "hp": [attacker.get_hit_points(), defender.get_hit_points()],
            "history": hashlib.sha256(native_history.encode(
                native_history.capture(encounter))).hexdigest(),
            "actions": list(encounter._atomic_interval_history[-1].action_ids),
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "native-combat-save.json"
            path.write_bytes(save)
            child = r'''import hashlib,json,sys
import native_history
from native_persistence import load_path
world,encounter,rng=load_path(sys.argv[1])
encounter.step(4)
print(json.dumps({'time':encounter.time,'rng':rng.state,
 'hp':[encounter.get_being(i).get_hit_points() for i in encounter.being_list],
 'history':hashlib.sha256(native_history.encode(native_history.capture(encounter))).hexdigest(),
 'actions':list(encounter._atomic_interval_history[-1].action_ids)},sort_keys=True))'''
            result = subprocess.run(
                [sys.executable, "-B", "-c", child, str(path)], cwd=ROOT,
                env={**__import__("os").environ,
                     "PYTHONPATH": f"{ROOT / 'src'}:{ROOT / 'examples'}"},
                text=True, capture_output=True, check=False, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), expected)

    def test_running_action_history_and_pending_continuation_in_fresh_process(self):
        """A real movement Action survives a mid-run native Save without replay."""
        world, encounter, rng, actor, _defender, _weapon_id = self._combat_encounter()
        from native_graph_snapshot import decode as decode_graph
        from physiology_registry import PhysiologyRegistry, PhysiologyDefinition
        registry = PhysiologyRegistry((PhysiologyDefinition(
            "native-human@1", model="human-r4"),))
        encounter.set_physiology_registry(registry)
        for being_id in encounter.being_list:
            encounter.get_being(being_id).set_physiology_id("native-human@1")
        actor.set_physical_fatigue(.7, .8)
        actor.exertion.set_activity_level("run")
        actor.exertion.set_load_level("heavy")
        actor.exertion.set_fatigue_level(1)
        actor.exertion.set_accumulated_exertion(17)
        action = RunAction(world, actor.id, encounter.time, 2, .75, 250,
                           id="native-run-pending-continuation")
        encounter.schedule_action(action)
        encounter.step(1, velocities={actor.id: (.5, 0, 0)})
        self.assertEqual(encounter.time, 1)
        self.assertEqual(actor.get_position(), CartesianPosition(.5, 0, 0))
        self.assertEqual(action.start_position, CartesianPosition(0, 0, 0))
        self.assertIsNone(action.resolution)
        saved_fatigue_view = encounter.last_fatigue_frame.view(actor.id).to_dict()
        saved_physiology_versions = {
            mode: encounter.last_fatigue_frame.physiology(actor.id, mode=mode).version_hash
            for mode in ("ordinary", "running")}

        wire = export_save(encounter)
        graph = decode_graph(base64.b64decode(
            json.loads(wire)["graph_b64"], validate=True), native=True)
        inventory = graph[1]
        nodes = next(row[1] for row in inventory if row[0] == "nodes")
        saved_encounter = next(content for _ref, tag, content in nodes
                               if tag == "encounter.Encounter")
        fatigue_ref = dict(saved_encounter)["fatigue_frame_history"][1]
        self.assertEqual(next(content for ref, tag, content in nodes
                              if ref == fatigue_ref and tag == "list"), ())
        markers = next(row[1:] for row in inventory
                       if row[0] == "native-adapters")
        self.assertIn("fatigue-frame-history/1", markers)
        query = native_history.NativeHistoryQuery(
            native_history.current_recording(encounter))
        for boundary, expected_x in ((1, .5),):
            position = query.entity_context_at(boundary)[actor.id]["fields"]["position"]["fields"]
            self.assertEqual(float.fromhex(position["x"]["$number"]), expected_x)
            fatigue = query.fatigue_context_at(boundary)[actor.id]
            self.assertEqual(float.fromhex(
                fatigue["physical_fatigue"]["q"]["$number"]), .7)
            self.assertEqual(fatigue["physiology"]["ordinary"]["version_hash"],
                             saved_physiology_versions["ordinary"])

        encounter.step(1, velocities={actor.id: (.5, 0, 0)})
        self.assertEqual(actor.get_position(), CartesianPosition(1, 0, 0))
        self.assertEqual(actor.get_skill_experience("run"), 250)
        self.assertEqual(actor.get_skill_level("run"), 1)
        run_commit = encounter.inspect_committed(boundary=2).action(action.id)
        self.assertEqual(run_commit.facts.outcome, "success")
        self.assertEqual(encounter._atomic_interval_history[-1].action_ids,
                         (action.id,))
        practice_effects = [row.effect for row in run_commit.effects
                            if type(row.effect).__name__ == "PracticeEffect"]
        self.assertEqual(len(practice_effects), 1)
        self.assertEqual(practice_effects[0].source_action_id, action.id)
        run_result = {
            "outcome": run_commit.facts.outcome,
            "practice_effect_sources": [row.source_action_id for row in practice_effects],
            "receipt_action_ids": list(encounter._atomic_interval_history[-1].action_ids),
        }
        encounter.step(1)
        expected = {
            "time": encounter.time,
            "position": actor.get_position().as_tuple(),
            "experience": actor.get_skill_experience("run"),
            "skill_uses": [{"skill": row.skill_name, "experience": row.experience,
                            "level_before": row.level_before,
                            "level_after": row.level_after, "time": row.time,
                            "exercise_experience": [use.experience for use in row.exercises]}
                           for row in actor.skill_use_history],
            "run_result": run_result,
            "receipt_action_ids": list(encounter._atomic_interval_history[-1].action_ids),
            "physical_fatigue": actor.get_physical_fatigue().to_dict(actor.physiology_id),
            "fatigue_view": encounter.last_fatigue_frame.view(actor.id).to_dict(),
            "physiology_version": encounter.last_fatigue_frame.physiology(
                actor.id).version_hash,
            "fatigue_frame_history": encounter.fatigue_frame_history,
            "exertion": json.loads(actor.exertion.to_json()),
            "rng": json.loads(json.dumps(rng.state)),
            "history": hashlib.sha256(native_history.encode(
                native_history.capture(encounter))).hexdigest(),
        }
        query = native_history.NativeHistoryQuery(
            native_history.current_recording(encounter))
        versions = {}
        for boundary in (1, 2, 3):
            context = query.entity_context_at(boundary)[actor.id]["fields"]
            position = context["position"]["fields"]
            self.assertEqual(float.fromhex(position["x"]["$number"]), .5 if boundary == 1 else 1.0)
            exertion = context["pre_action"]["exertion"]
            self.assertEqual(exertion["accumulated_exertion"], 17)
            self.assertEqual(exertion["activity_level"], "run")
            fatigue = query.fatigue_context_at(boundary)[actor.id]
            self.assertEqual(float.fromhex(
                fatigue["physical_fatigue"]["q"]["$number"]), .7)
            versions[boundary] = fatigue["physiology"]["running"]["version_hash"]
        self.assertEqual(versions[1], versions[2])
        self.assertNotEqual(versions[2], versions[3])

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "native-run-pending-save.json"
            path.write_bytes(wire)
            child = r'''import hashlib,json,sys
import native_history
from action_evaluation import PracticeEffect
from native_persistence import load_path
world,encounter,rng=load_path(sys.argv[1])
action=world.event_history['native-run-pending-continuation']
actor=world.get_object_by_id(action.actor_id)
assert actor.physiology_id == 'native-human@1'
assert encounter.last_fatigue_frame.view(actor.id).to_dict() == json.loads(sys.argv[2])
saved_versions=json.loads(sys.argv[3])
assert {mode:encounter.last_fatigue_frame.physiology(actor.id,mode=mode).version_hash
 for mode in ('ordinary','running')} == saved_versions
assert encounter.time == 1 and action.start_position.as_tuple() == (0.0,0.0,0.0)
assert action.resolution is None and actor.get_position().as_tuple() == (.5,0.0,0.0)
encounter.step(1,velocities={actor.id:(.5,0,0)})
committed=encounter.inspect_committed(boundary=2).action(action.id)
facts=committed.facts
practice=[row.effect for row in committed.effects if type(row.effect) is PracticeEffect]
run_result={'outcome':facts.outcome,
 'practice_effect_sources':[row.source_action_id for row in practice],
 'receipt_action_ids':list(encounter._atomic_interval_history[-1].action_ids)}
encounter.step(1)
print(json.dumps({'time':encounter.time,'position':actor.get_position().as_tuple(),
 'experience':actor.get_skill_experience('run'),
 'skill_uses':[{'skill':row.skill_name,'experience':row.experience,
  'level_before':row.level_before,'level_after':row.level_after,'time':row.time,
  'exercise_experience':[use.experience for use in row.exercises]}
  for row in actor.skill_use_history],
 'run_result':run_result,
 'receipt_action_ids':list(encounter._atomic_interval_history[-1].action_ids),
 'physical_fatigue':actor.get_physical_fatigue().to_dict(actor.physiology_id),
 'fatigue_view':encounter.last_fatigue_frame.view(actor.id).to_dict(),
 'physiology_version':encounter.last_fatigue_frame.physiology(actor.id).version_hash,
 'fatigue_frame_history':encounter.fatigue_frame_history,
 'exertion':json.loads(actor.exertion.to_json()),
 'rng':rng.state,
 'history':hashlib.sha256(native_history.encode(native_history.capture(encounter))).hexdigest()},
 sort_keys=True))'''
            import os
            result = subprocess.run(
                [sys.executable, "-B", "-c", child, str(path),
                 json.dumps(saved_fatigue_view), json.dumps(saved_physiology_versions)], cwd=directory,
                env={**os.environ,
                     "PYTHONPATH": f"{ROOT / 'src'}:{ROOT / 'examples'}"},
                text=True, capture_output=True, check=False, timeout=45)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout),
                         json.loads(json.dumps(expected)))

    def test_statistical_group_is_supported_and_unbound_observers_fail_closed(self):
        group_fixture = inspection_fixtures.InspectionFixture()
        group_fixture.setUp()
        group_fixture.f.f.f.group()
        group_fixture.commit()
        before = group_fixture.raw()
        group_save = export_save(group_fixture.enc)
        restored_world, restored_encounter, _ = load_save(group_save)
        self.assertEqual(restored_encounter.id, group_fixture.enc.id)
        self.assertIn("group-one", restored_world.object_registry.object_instances)
        self.assertEqual(group_fixture.raw(), before)

        observer_fixture = inspection_fixtures.InspectionFixture()
        observer_fixture.setUp()
        group = observer_fixture.f.f.f.group()
        history = observer_fixture.f.f.f.history()
        from field_observation import BeliefLedger
        from history_conversation import AskAboutPastAction
        observer_fixture.enable()
        first = observer_fixture.f.f.observe(observer_fixture.a, group,
            ledger=BeliefLedger(observer_fixture.a.id))
        second = observer_fixture.f.f.observe(observer_fixture.b, group,
            ledger=BeliefLedger(observer_fixture.b.id))
        accounts = []
        ask = AskAboutPastAction(observer_fixture.world, observer_fixture.c.id,
            observer_fixture.a.id, 0, episode_time=0, topic="lessons",
            generate=observer_fixture.f.f.f.recipe(history),
            received_accounts=accounts)
        observer_fixture.enc.schedule_choice((first, second, ask))
        observer_fixture.enc.step(1)
        before = observer_fixture.raw()
        with self.assertRaisesRegex(NativeSaveRejected,
                                    "missing durable committed recipient binding") as refused:
            export_save(observer_fixture.enc)
        self.assertEqual(observer_fixture.raw(), before)

    def test_native_stun_condition_and_interrupted_action_resume_in_fresh_process(self):
        fixture = action_fixtures.TestActionEvaluation()
        fixture.setUp()
        fixture.b.set_position(CartesianPosition(.2, 0, 0))
        skills = fixture.world.get_skill_dictionary()
        fixture.a.set_skill_level(skills, "unarmed combat", 5)
        fixture.a.set_skill_level(skills, "stun", 2)
        fixture.a.current.tags["universe.stun_categories"] = {"humanoid": 2}
        fixture.b.current.tags["universe.stun_category"] = "humanoid"
        rng = RNGCursor(__import__("random").Random(6).getstate())
        fixture.enc.enable_transactional_progression(quiescent=True, rng_owner=rng)
        from activities import declare_stun
        stun = declare_stun(fixture.world, fixture.enc, fixture.a.id,
                            fixture.b.id, region="Arm", motion="thrust")
        later = MeleeStrike(fixture.enc, fixture.b.id, fixture.a.id, fixture.w3,
                            motion="swing", reach=2)
        self.assertGreater(later.end_time, stun.end_time)
        fixture.enc.schedule_action(stun)
        fixture.enc.schedule_action(later)
        fixture.enc.step(stun.end_time)
        self.assertEqual(fixture.enc.inspect_committed().action(stun.id).facts.outcome,
                         "stunned")
        self.assertEqual(fixture.b.current.states.states["stunned_until"], 10)
        self.assertIn(later.id, fixture.enc.cancelled_action_list)
        save = export_save(fixture.enc)
        fixture.enc.step(8)
        expected = {
            "time": fixture.enc.time,
            "rng": json.loads(json.dumps(rng.state)),
            "hp": [fixture.a.get_hit_points(), fixture.b.get_hit_points()],
            "stunned_until": fixture.b.current.states.states["stunned_until"],
            "cancelled": list(fixture.enc.cancelled_action_list),
            "history": hashlib.sha256(native_history.encode(
                native_history.capture(fixture.enc))).hexdigest(),
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "native-stun-save.json"
            path.write_bytes(save)
            child = r'''import hashlib,json,sys
import native_history
from native_persistence import load_path
world,encounter,rng=load_path(sys.argv[1])
encounter.step(8)
print(json.dumps({'time':encounter.time,'rng':rng.state,
 'hp':[encounter.get_being(i).get_hit_points() for i in encounter.being_list],
 'stunned_until':encounter.get_being(encounter.being_list[1]).current.states.states['stunned_until'],
 'cancelled':list(encounter.cancelled_action_list),
 'history':hashlib.sha256(native_history.encode(native_history.capture(encounter))).hexdigest()},sort_keys=True))'''
            result = subprocess.run(
                [sys.executable, "-B", "-c", child, str(path)], cwd=ROOT,
                env={**__import__("os").environ,
                     "PYTHONPATH": f"{ROOT / 'src'}:{ROOT / 'examples'}"},
                text=True, capture_output=True, check=False, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), expected)

    def test_native_local_frame_movement_resumes_in_fresh_process(self):
        fixture=inspection_fixtures.InspectionFixture();fixture.setUp()
        from spatial.frame import LocalFrame
        frame=LocalFrame(CartesianPosition(10,-4,20),(0,1,0),(-1,0,0),(0,0,1))
        fixture.enc.set_local_frame(frame)
        fixture.enable()
        initial_position=fixture.a.get_position()
        first=RunAction(fixture.world,fixture.a.id,0,1,.5,experience=1,
            id='native-local-frame-run-0')
        fixture.enc.schedule_action(first)
        fixture.enc.step(1,velocities={fixture.a.id:(1,0,0)},velocity_frame='local')
        self.assertEqual(frame.vector_to_global((1,0,0)),(0.0,1.0,0.0))
        self.assertEqual(fixture.a.get_position(),CartesianPosition(
            initial_position.x,initial_position.y+1,initial_position.z))
        wire=export_save(fixture.enc)
        continuation=RunAction(fixture.world,fixture.a.id,1,1,.5,experience=1,
            id='native-local-frame-run-1')
        fixture.enc.schedule_action(continuation)
        fixture.enc.step(1,velocities={fixture.a.id:(0,1,0)},velocity_frame='local')
        expected={'encounter_id':fixture.enc.id,'time':fixture.enc.time,
            'frame':fixture.enc.local_frame.to_dict(),
            'global_position':fixture.a.get_position().as_tuple(),
            'local_position':fixture.enc.entity_local_position(fixture.a.id).as_tuple(),
            'rng':fixture.rng.state,
            'history':hashlib.sha256(native_history.encode(
                native_history.capture(fixture.enc))).hexdigest(),
            'actions':list(fixture.enc._atomic_interval_history[-1].action_ids)}
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'native-local-frame.json';path.write_bytes(wire)
            child=r'''import hashlib,json,sys
import native_history
from activities import RunAction
from native_persistence import load_path
world,enc,rng=load_path(sys.argv[1])
frame=enc.local_frame
assert frame is not None
assert enc.entity_local_position(enc.being_list[0]).as_tuple()==frame.to_local(
 world.get_object_by_id(enc.being_list[0]).get_position()).as_tuple()
action=RunAction(world,enc.being_list[0],enc.time,1,.5,experience=1,
 id='native-local-frame-run-1')
enc.schedule_action(action)
enc.step(1,velocities={enc.being_list[0]:(0,1,0)},velocity_frame='local')
print(json.dumps({'encounter_id':enc.id,'time':enc.time,'frame':frame.to_dict(),
 'global_position':world.get_object_by_id(enc.being_list[0]).get_position().as_tuple(),
 'local_position':enc.entity_local_position(enc.being_list[0]).as_tuple(),
 'rng':rng.state,
 'history':hashlib.sha256(native_history.encode(native_history.capture(enc))).hexdigest(),
 'actions':[entry.action_ids for entry in enc._atomic_interval_history[-1:]][0]},sort_keys=True))'''
            import os
            result=subprocess.run([sys.executable,'-B','-c',child,str(path)],cwd=ROOT,
                env={**os.environ,'PYTHONPATH':f'{ROOT / "src"}:{ROOT / "examples"}'},
                text=True,capture_output=True,check=False,timeout=45)
        self.assertEqual(result.returncode,0,result.stderr)
        actual=json.loads(result.stdout)
        self.assertEqual(actual,json.loads(json.dumps(expected)))

    def test_native_spatial_primitives_round_trip_and_continue(self):
        world,encounter,rng,actor,target,_weapon_id=self._combat_encounter()
        from spatial.geometry import AxisAlignedBox
        from spatial.occlusion import VisualOcclusion
        actor.set_geometry(Sphere(.37))
        target.set_geometry(AxisAlignedBox(1.25,2.5,3.75))
        target.set_visual_occlusion(VisualOcclusion(.375))
        encounter.step(1)
        wire=export_save(encounter)
        continuation=DelayAction(encounter,actor.id,defense=0,start_time=encounter.time,
            id='native-spatial-primitives-continuation')
        encounter.schedule_action(continuation);encounter.step(1)
        expected={'encounter_id':encounter.id,'time':encounter.time,
            'geometries':[actor.geometry.to_dict(),target.geometry.to_dict()],
            'occlusion':target.visual_occlusion.opacity,
            'positions':[actor.get_position().as_tuple(),target.get_position().as_tuple()],
            'rng':rng.state,
            'history':hashlib.sha256(native_history.encode(
                native_history.capture(encounter))).hexdigest(),
            'actions':list(encounter._atomic_interval_history[-1].action_ids)}
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'native-spatial-primitives.json';path.write_bytes(wire)
            child=r'''import hashlib,json,sys
import native_history
from activities import DelayAction
from native_persistence import load_path
world,encounter,rng=load_path(sys.argv[1])
actor=encounter.get_being(encounter.being_list[0])
target=encounter.get_being(encounter.being_list[1])
assert type(actor.geometry).__name__=='Sphere'
assert type(target.geometry).__name__=='AxisAlignedBox'
assert target.visual_occlusion.opacity==.375
action=DelayAction(encounter,actor.id,defense=0,start_time=encounter.time,
 id='native-spatial-primitives-continuation')
encounter.schedule_action(action);encounter.step(1)
print(json.dumps({'encounter_id':encounter.id,'time':encounter.time,
 'geometries':[actor.geometry.to_dict(),target.geometry.to_dict()],
 'occlusion':target.visual_occlusion.opacity,
 'positions':[actor.get_position().as_tuple(),target.get_position().as_tuple()],
 'rng':rng.state,
 'history':hashlib.sha256(native_history.encode(
  native_history.capture(encounter))).hexdigest(),
 'actions':list(encounter._atomic_interval_history[-1].action_ids)},sort_keys=True))'''
            import os
            result=subprocess.run([sys.executable,'-B','-c',child,str(path)],cwd=ROOT,
                env={**os.environ,'PYTHONPATH':f'{ROOT / "src"}:{ROOT / "examples"}'},
                text=True,capture_output=True,check=False,timeout=45)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout),json.loads(json.dumps(expected)))

    def test_native_being_abilities_states_speed_and_posture_restore(self):
        world,encounter,rng,actor,_target,_weapon_id=self._combat_encounter()
        from states import StatesList
        state_list=StatesList();state_list.load_states(str(ROOT/'src/config/states.tsv'))
        actor.set_ability('STR',13);actor.set_ability('FIT',9)
        actor.set_max_speed('ambulate',5)
        actor.set_state(state_list,'prone',True)
        actor.set_posture('lying')
        encounter.step(1)
        history_query=native_history.NativeHistoryQuery(
            native_history.capture(encounter))
        for boundary in (0,1):
            historical=history_query.entity_at(actor.id,boundary)['fields']['pre_action']
            self.assertEqual(historical['abilities']['STR'],13)
            self.assertEqual(historical['abilities']['FIT'],9)
            self.assertTrue(historical['states']['prone'])
            self.assertEqual(historical['posture'],'lying')
        wire=export_save(encounter)
        continuation=DelayAction(encounter,actor.id,defense=0,start_time=encounter.time,
            id='native-being-fields-continuation')
        encounter.schedule_action(continuation);encounter.step(1)
        def projection(being):
            return {'abilities':dict(being.get_abilities()),'states':being.get_states(),
                'posture':being.get_posture(),'ambulate':being.sprint()}
        expected={'encounter_id':encounter.id,'time':encounter.time,
            'being':projection(actor),'rng':rng.state,
            'history':hashlib.sha256(native_history.encode(
                native_history.capture(encounter))).hexdigest(),
            'actions':list(encounter._atomic_interval_history[-1].action_ids)}
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'native-being-fields.json';path.write_bytes(wire)
            child=r'''import hashlib,json,sys
import native_history
from activities import DelayAction
from native_persistence import load_path
world,encounter,rng=load_path(sys.argv[1])
actor=encounter.get_being(encounter.being_list[0])
assert actor.STR()==13 and actor.FIT()==9
assert actor.get_state('prone') is True and actor.get_posture()=='lying'
assert actor.sprint()==5
action=DelayAction(encounter,actor.id,defense=0,start_time=encounter.time,
 id='native-being-fields-continuation')
encounter.schedule_action(action);encounter.step(1)
print(json.dumps({'encounter_id':encounter.id,'time':encounter.time,
 'being':{'abilities':dict(actor.get_abilities()),'states':actor.get_states(),
  'posture':actor.get_posture(),'ambulate':actor.sprint()},'rng':rng.state,
 'history':hashlib.sha256(native_history.encode(
  native_history.capture(encounter))).hexdigest(),
 'actions':list(encounter._atomic_interval_history[-1].action_ids)},sort_keys=True))'''
            import os
            result=subprocess.run([sys.executable,'-B','-c',child,str(path)],cwd=ROOT,
                env={**os.environ,'PYTHONPATH':f'{ROOT / "src"}:{ROOT / "examples"}'},
                text=True,capture_output=True,check=False,timeout=45)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout),json.loads(json.dumps(expected)))

    def test_native_save_preserves_registered_nonparticipants_in_fresh_process(self):
        world,encounter,rng,actor,_target,_weapon_id=self._combat_encounter()
        outsider_id=world.make_being('Human','Registered nonparticipant')
        outsider=world.get_object_by_id(outsider_id)
        outsider.set_position(CartesianPosition(8,9,1))
        outsider.set_hit_points(23)
        outsider.set_ability('INT',14)
        scenery_id=world.make_object('Linen pillow','Uninvolved scenery')
        scenery=world.get_object_by_id(scenery_id)
        scenery.set_position(CartesianPosition(-4,2,0))
        self.assertNotIn(outsider_id,encounter.being_list)
        self.assertNotIn(scenery_id,encounter.non_being_object_list)
        encounter.step(1)
        wire=export_save(encounter)
        continuation=DelayAction(encounter,actor.id,defense=0,start_time=encounter.time,
            id='native-nonparticipant-continuation')
        encounter.schedule_action(continuation);encounter.step(1)
        expected={'world_id':world.id,'encounter_id':encounter.id,'time':encounter.time,
            'participants':list(encounter.being_list),'outsider':{
                'id':outsider.id,'position':outsider.get_position().as_tuple(),
                'hp':outsider.get_hit_points(),'intelligence':outsider.INT(),
                'definition':outsider.original.obj_type},
            'scenery':{'id':scenery.id,'position':scenery.get_position().as_tuple(),
                'definition':scenery.original.obj_type},
            'rng':rng.state,'history':hashlib.sha256(native_history.encode(
                native_history.capture(encounter))).hexdigest(),
            'actions':list(encounter._atomic_interval_history[-1].action_ids)}
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'native-nonparticipants.json';path.write_bytes(wire)
            child=r'''import hashlib,json,sys
import native_history
from activities import DelayAction
from native_persistence import load_path
world,encounter,rng=load_path(sys.argv[1])
outsider=world.get_object_by_id(sys.argv[2]);scenery=world.get_object_by_id(sys.argv[3])
actor=encounter.get_being(encounter.being_list[0])
assert outsider.id not in encounter.being_list
assert scenery.id not in encounter.non_being_object_list
assert outsider.original is world.library.get_being_definition('Human')
assert scenery.original is world.library.get_object_definition('Linen pillow')
action=DelayAction(encounter,actor.id,defense=0,start_time=encounter.time,
 id='native-nonparticipant-continuation')
encounter.schedule_action(action);encounter.step(1)
print(json.dumps({'world_id':world.id,'encounter_id':encounter.id,
 'time':encounter.time,'participants':list(encounter.being_list),
 'outsider':{'id':outsider.id,'position':outsider.get_position().as_tuple(),
  'hp':outsider.get_hit_points(),'intelligence':outsider.INT(),
  'definition':outsider.original.obj_type},
 'scenery':{'id':scenery.id,'position':scenery.get_position().as_tuple(),
  'definition':scenery.original.obj_type},'rng':rng.state,
 'history':hashlib.sha256(native_history.encode(
  native_history.capture(encounter))).hexdigest(),
 'actions':list(encounter._atomic_interval_history[-1].action_ids)},sort_keys=True))'''
            import os
            result=subprocess.run([sys.executable,'-B','-c',child,str(path),
                outsider_id,scenery_id],cwd=ROOT,
                env={**os.environ,'PYTHONPATH':f'{ROOT / "src"}:{ROOT / "examples"}'},
                text=True,capture_output=True,check=False,timeout=45)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout),json.loads(json.dumps(expected)))

    def test_statistical_group_facts_and_keyed_realization_resume_in_fresh_process(self):
        fixture = inspection_fixtures.InspectionFixture()
        fixture.setUp()
        group_config = json.loads((ROOT / "examples/nomadic_group.json").read_text())
        group_config["formation_traits"] = {
            "adults": {"trained_spotter": {"count": 0, "initial_skills": {}}}}
        group_config["formation_attributes"] = {
            "adults": {"voice": {"given": "trained_spotter", "conditional_cdfs": {
                "true": [["formal", 1]], "false": [["casual", 1]]}}}}
        group = StatisticalGroup("Native group", "group-one", group_config,
                                 group_config["seed"])
        fixture.world.add_object(group)
        expected_count = group.household_count
        expected_household = group.household(0)
        group.counts()
        first_adult = next((household, index)
            for household in range(group.household_count)
            for index in range(group.household(household)["adults"]))
        realized_member = group.realize_being(
            fixture.world, first_adult[0], 'adults', first_adult[1])
        unrealized_members = tuple(
            group.member(0, category, 0)
            for category in ('children', 'livestock', 'dogs'))
        expected_voice = group.formation_attribute(first_adult[0], "adults",
            first_adult[1], "voice")
        fixture.enable()
        first = DelayAction(fixture.enc, fixture.a.id, defense=0,
                            start_time=0, id="native-group-delay")
        fixture.enc.schedule_action(first)
        fixture.enc.step(1)
        group.join_being(fixture.world, fixture.a, time=0)
        group.advance(1)
        group.leave_being(fixture.world, fixture.a, time=1)
        group.advance(2)
        group.join_being(fixture.world, fixture.a, time=3)
        expected_membership = {str(time): group.state_at(time)
                               for time in (0, 0.5, 1, 2, 3)}
        original_membership = group.membership_history[1]
        group.membership_history[1] = MembershipChange(
            1, fixture.a.id, "adults", "foreign-group", "leave")
        with self.assertRaises(NativeSaveRejected):
            export_save(fixture.enc)
        group.membership_history[1] = original_membership
        group._departed_member_ids.add(realized_member.id)
        with self.assertRaises(NativeSaveRejected):
            export_save(fixture.enc)
        group._departed_member_ids.remove(realized_member.id)
        attached = set(group._motion_attached_native_ids)
        group._motion_attached_native_ids.remove(realized_member.id)
        with self.assertRaises(NativeSaveRejected):
            export_save(fixture.enc)
        group._motion_attached_native_ids = attached
        incoming = group._incoming_beings.pop(fixture.a.id)
        with self.assertRaises(NativeSaveRejected):
            export_save(fixture.enc)
        group._incoming_beings[fixture.a.id] = incoming
        member_key = (first_adult[0], "adults", first_adult[1])
        original_group_member = group._members[member_key]
        group._members[member_key] = GroupMember(
            "forged-group-member-id", original_group_member.household,
            original_group_member.category, original_group_member.index,
            original_group_member.offset)
        with self.assertRaises(NativeSaveRejected):
            export_save(fixture.enc)
        group._members[member_key] = original_group_member
        group._members[member_key] = GroupMember(
            original_group_member.id, original_group_member.household,
            original_group_member.category, original_group_member.index,
            (original_group_member.offset[0] + 0.01,
             original_group_member.offset[1], original_group_member.offset[2]))
        with self.assertRaises(NativeSaveRejected):
            export_save(fixture.enc)
        group._members[member_key] = original_group_member
        wire = export_save(fixture.enc)
        group.advance(1)
        expected_group_continuation = {
            "time": group.time,
            "position": group.get_position().as_tuple(),
            "velocity": group.velocity,
            "state": group.state_at(3.5),
            "member_position": fixture.a.get_position().as_tuple(),
            "realized_member_id": realized_member.id,
            "realized_member_position": realized_member.get_position().as_tuple(),
            "unrealized_members": [[member.id, member.category,
                member.offset, group.member_position(member).as_tuple()]
                for member in unrealized_members],
        }

        continuation_id = "native-group-continuation-delay"
        next_action = DelayAction(fixture.enc, fixture.a.id, defense=0,
                                  start_time=1, id=continuation_id)
        fixture.enc.schedule_action(next_action)
        fixture.enc.step(1)
        expected = {
            "world": fixture.world.id, "encounter": fixture.enc.id,
            "time": fixture.enc.time, "rng": fixture.rng.state,
            "group_id": group.id, "count": group.household_count,
            "household": group.household(0),
            "membership": expected_membership,
            "group_continuation": expected_group_continuation,
            "formation_attribute": expected_voice,
            "history": hashlib.sha256(native_history.encode(
                native_history.capture(fixture.enc))).hexdigest(),
            "actions": list(fixture.enc._atomic_interval_history[-1].action_ids),
        }
        self.assertEqual(expected["count"], expected_count)
        self.assertEqual(expected["household"], expected_household)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "native-group-save.json"
            path.write_bytes(wire)
            child = r'''import hashlib,json,sys
import native_history
from activities import DelayAction
from native_persistence import export_save, load_path
world,enc,rng=load_path(sys.argv[1])
assert export_save(enc)==open(sys.argv[1],'rb').read()
group=world.object_registry.object_instances['group-one']
realized_member=world.get_object_by_id(sys.argv[7])
assert group._realized_beings[realized_member.id] is realized_member
unrealized_members=[group._members[(0,category,0)]
 for category in ('children','livestock','dogs')]
assert all(world.get_object_by_id(member.id) is None for member in unrealized_members)
membership={str(time):group.state_at(time) for time in (0,0.5,1,2,3)}
assert [row.action for row in group.membership_history]==['join','leave','join']
assert [row.time for row in group.membership_history]==[0.0,1.0,3.0]
group.advance(1)
group_continuation={'time':group.time,'position':group.get_position().as_tuple(),
 'velocity':group.velocity,'state':group.state_at(3.5),
 'member_position':world.object_registry.object_instances[
  group.membership_history[0].being_id].get_position().as_tuple(),
 'realized_member_id':realized_member.id,
 'realized_member_position':realized_member.get_position().as_tuple(),
 'unrealized_members':[[member.id,member.category,member.offset,
  group.member_position(member).as_tuple()] for member in unrealized_members]}
assert group.household_count == int(sys.argv[2])
assert group.household(0) == json.loads(sys.argv[3])
household,index=int(sys.argv[4]),int(sys.argv[5])
assert group.committed_formation_attributes(household,'adults',index)['voice']==sys.argv[6]
action=DelayAction(enc,enc.being_list[0],defense=0,start_time=enc.time,
 id='native-group-continuation-delay')
enc.schedule_action(action)
enc.step(1)
print(json.dumps({'world':world.id,'encounter':enc.id,'time':enc.time,
 'rng':rng.state,'group_id':group.id,'count':group.household_count,
 'household':group.household(0),'membership':membership,
 'group_continuation':group_continuation,
 'formation_attribute':group.committed_formation_attributes(household,'adults',index)['voice'],
 'history':hashlib.sha256(native_history.encode(native_history.capture(enc))).hexdigest(),
 'actions':list(enc._atomic_interval_history[-1].action_ids),
 'arena_imports':sorted(set(sys.modules)&{'arena_browser_session','arena_native_snapshot',
  'arena_persistence','arena_server','npcgen'})},sort_keys=True))'''
            import os
            result = subprocess.run(
                [sys.executable, "-B", "-c", child, str(path),
                 str(expected_count), json.dumps(expected_household),
                 str(first_adult[0]), str(first_adult[1]), expected_voice,
                 realized_member.id],
                cwd=ROOT, env={**os.environ,
                    "PYTHONPATH": f"{ROOT / 'src'}:{ROOT / 'examples'}"},
                text=True, capture_output=True, check=False, timeout=45)
        self.assertEqual(result.returncode, 0, result.stderr)
        actual = json.loads(result.stdout)
        self.assertEqual(actual.pop("arena_imports"), [])
        self.assertEqual(actual, json.loads(json.dumps(expected)))

    def test_observer_owned_group_evidence_round_trips_without_identity_leakage(self):
        fixture = inspection_fixtures.InspectionFixture()
        fixture.setUp()
        group = fixture.f.f.f.group()
        fixture.enable()
        from field_observation import BeliefLedger
        first_ledger = BeliefLedger(fixture.a.id)
        second_ledger = BeliefLedger(fixture.b.id)
        first = fixture.f.f.observe(fixture.a, group, ledger=first_ledger)
        second = fixture.f.f.observe(fixture.b, group, ledger=second_ledger)
        fixture.enc.schedule_choice((first, second))
        fixture.enc.step(1)
        bindings = (
            RecipientBinding(fixture.world, "native", "belief-a",
                "in_world_belief_ledger", (fixture.a.id,), first_ledger),
            RecipientBinding(fixture.world, "native", "belief-b",
                "in_world_belief_ledger", (fixture.b.id,), second_ledger),
        )
        wire = export_save(fixture.enc, recipient_bindings=bindings)

        continuation = DelayAction(fixture.enc, fixture.a.id, defense=0,
                                   start_time=1, id="native-observer-continuation")
        fixture.enc.schedule_action(continuation)
        fixture.enc.step(1)
        expected = {
            "time": fixture.enc.time,
            "rng": fixture.rng.state,
            "history": hashlib.sha256(native_history.encode(
                native_history.capture(fixture.enc))).hexdigest(),
            "actions": list(fixture.enc._atomic_interval_history[-1].action_ids),
            "saved_actions": sorted((first.id, second.id)),
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "native-observer-save.json"
            path.write_bytes(wire)
            child = r'''import hashlib,json,sys
import native_history
from activities import DelayAction
from native_persistence import load_path
world,enc,rng=load_path(sys.argv[1])
actions=[event for event in world.event_history.values()
 if type(event).__name__=='ObserveGroupAction']
ledgers={event.actor_id:event.ledger for event in actions}
assert set(ledgers)==set(enc.being_list[:2])
assert all(ledger.observer_id==owner and ledger.evidence for owner,ledger in ledgers.items())
action=DelayAction(enc,enc.being_list[0],defense=0,start_time=enc.time,
 id='native-observer-continuation')
enc.schedule_action(action)
enc.step(1)
print(json.dumps({'time':enc.time,'rng':rng.state,
 'history':hashlib.sha256(native_history.encode(native_history.capture(enc))).hexdigest(),
 'actions':list(enc._atomic_interval_history[-1].action_ids),
 'saved_actions':sorted(event.id for event in actions)},sort_keys=True))'''
            import os
            result = subprocess.run(
                [sys.executable, "-B", "-c", child, str(path)],
                cwd=ROOT, env={**os.environ,
                    "PYTHONPATH": f"{ROOT / 'src'}:{ROOT / 'examples'}"},
                text=True, capture_output=True, check=False, timeout=45)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), json.loads(json.dumps(expected)))


    def test_personal_history_facts_and_validator_resume_in_fresh_process(self):
        fixture = inspection_fixtures.InspectionFixture()
        fixture.setUp()
        from personal_history import PersonalHistory
        from realization import Fact
        history = PersonalHistory(fixture.a, earliest=-10, known_through=0,
                                  nondeclining_skills=('run',))
        fixture.a.personal_history = history
        history.commit_skill_rank(-5, 'run', 1, origin='native-history-fixture')
        key = history.episode_key(-1, "earlier-training")
        history.realize_episode(-1, "earlier-training", lambda _view: (
            Fact(key, {"description": "practiced earlier", "skill": "run",
                       "rank_after": 2}, 'native-history-fixture'),
            Fact(history.skill_key(-1, 'run'), 2, 'native-history-fixture')))
        fixture.enable()
        first = DelayAction(fixture.enc, fixture.a.id, defense=0,
                            start_time=0, id="native-personal-history-delay")
        fixture.enc.schedule_action(first)
        fixture.enc.step(1)
        wire = export_save(fixture.enc)
        self.assertEqual(history.inspect_episode(-1, "earlier-training").value,
                         {"description": "practiced earlier", "skill": "run",
                          "rank_after": 2})
        self.assertEqual(len(history.facts_at(-1)), 2)
        self.assertEqual(history.reality.inspect(history.skill_key(-5, 'run')).value, 1)
        self.assertEqual(len(history.facts_at(-5)), 1)

        continuation = DelayAction(fixture.enc, fixture.a.id, defense=0,
                                   start_time=1, id="native-history-continuation")
        fixture.enc.schedule_action(continuation)
        fixture.enc.step(1)
        live_history = fixture.a.personal_history
        history_digest = hashlib.sha256(json.dumps(
            live_history.to_jsonable(), sort_keys=True, separators=(",", ":"),
            allow_nan=False).encode()).hexdigest()
        expected = {
            "time": fixture.enc.time,
            "rng": json.loads(json.dumps(fixture.rng.state)),
            "history_digest": history_digest,
            "native_history": hashlib.sha256(native_history.encode(
                native_history.capture(fixture.enc))).hexdigest(),
            "actions": list(fixture.enc._atomic_interval_history[-1].action_ids),
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "native-personal-history-save.json"
            path.write_bytes(wire)
            child = r'''import hashlib,json,sys
import native_history
from activities import DelayAction
from native_persistence import load_path
world,enc,rng=load_path(sys.argv[1])
being=world.get_object_by_id(enc.being_list[0])
history=being.personal_history
history._validate(history.reality.view())
assert history.inspect_episode(-1,'earlier-training').value=={
 'description':'practiced earlier','skill':'run','rank_after':2}
assert len(history.facts_at(-1))==2
assert history.reality.inspect(history.skill_key(-5,'run')).value==1
assert len(history.facts_at(-5))==1
assert history.reality.revision==2
action=DelayAction(enc,being.id,defense=0,start_time=enc.time,
 id='native-history-continuation')
enc.schedule_action(action)
enc.step(1)
print(json.dumps({'time':enc.time,'rng':rng.state,
 'history_digest':hashlib.sha256(json.dumps(history.to_jsonable(),sort_keys=True,
  separators=(',',':'),allow_nan=False).encode()).hexdigest(),
 'native_history':hashlib.sha256(native_history.encode(native_history.capture(enc))).hexdigest(),
 'actions':list(enc._atomic_interval_history[-1].action_ids)},sort_keys=True))'''
            import os
            result = subprocess.run(
                [sys.executable, "-B", "-c", child, str(path)], cwd=ROOT,
                env={**os.environ,
                     "PYTHONPATH": f"{ROOT / 'src'}:{ROOT / 'examples'}"},
                text=True, capture_output=True, check=False, timeout=45)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), expected)

    def test_logical_reproduction_registry_resumes_with_native_encounter(self):
        world = Universe('native-reproduction', library=Library(
            config_dir=str(ROOT / 'src/config')))
        world.publish_reproduction_group(prepare_reproduction_group(
            ReproductionGroupProposal('RG-NATIVE', ('P1', 'P2'), ('C1',),
                                      'native-save:test')),
            request_key='native-create', expected_revision=0)
        snapshot = world.reproduction_group_snapshot()
        self.assertEqual(snapshot.revision, 1)
        self.assertEqual(world.get_reproduction_group('RG-NATIVE').offspring_ids, ('C1',))
        from encounter import Encounter
        ids = [world.make_being('Human', name) for name in ('Native A', 'Native B')]
        encounter = Encounter(world, 10, 0, initiated=True, id='native-reproduction-encounter')
        for identity in ids:
            encounter.add_being(identity)
        world.add_event(encounter)
        rng = RNGCursor(__import__('random').Random(91).getstate())
        encounter.enable_transactional_progression(quiescent=True, rng_owner=rng)
        initial = DelayAction(encounter, ids[0], defense=0, start_time=0,
                              id='native-reproduction-initial')
        encounter.schedule_action(initial)
        encounter.step(1)
        wire = export_save(encounter)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'native-reproduction-save.json'
            path.write_bytes(wire)
            child = r'''import hashlib,json,sys
from activities import DelayAction
from native_persistence import load_path
world,enc,rng=load_path(sys.argv[1])
snapshot=world.reproduction_group_snapshot()
group=world.get_reproduction_group('RG-NATIVE')
assert group.parent_ids == ('P1','P2') and group.offspring_ids == ('C1',)
action=DelayAction(enc,enc.being_list[0],defense=0,start_time=enc.time,
 id='native-reproduction-continuation')
enc.schedule_action(action)
enc.step(1)
print(json.dumps({'revision':world.reproduction_group_snapshot().revision,
 'group_id':group.group_id,'parents':group.parent_ids,'offspring':group.offspring_ids,
 'time':enc.time,'rng':rng.state},sort_keys=True))'''
            import os
            result = subprocess.run(
                [sys.executable, '-B', '-c', child, str(path)], cwd=ROOT,
                env={**os.environ,
                     'PYTHONPATH': f'{ROOT / "src"}:{ROOT / "examples"}'},
                text=True, capture_output=True, check=False, timeout=45)
        self.assertEqual(result.returncode, 0, result.stderr)
        restored = json.loads(result.stdout)
        self.assertEqual(restored['revision'], snapshot.revision)
        self.assertEqual(restored['group_id'], 'RG-NATIVE')
        self.assertEqual(restored['parents'], ['P1', 'P2'])
        self.assertEqual(restored['offspring'], ['C1'])
        self.assertEqual(restored['time'], 2)

    def test_native_save_restores_and_continues_multiple_encounters(self):
        import os
        import random

        world = Universe('native-multiple-encounters', library=Library(
            config_dir=str(ROOT / 'src/config')))
        identities = [world.make_being('Human', f'Native Encounter {index}')
                      for index in range(2)]
        companion = Encounter(world, 10, 0, initiated=True,
                              id='native-multi-pristine-companion')
        companion.add_being(identities[1])
        world.add_event(companion)
        companion_rng = RNGCursor(random.Random(701).getstate())
        companion.enable_transactional_progression(
            quiescent=True, rng_owner=companion_rng)
        # The selected Encounter is deliberately not the first Encounter in
        # event-history order; the portable root role must remain unambiguous.
        selected = Encounter(world, 10, 0, initiated=True,
                             id='native-multi-selected')
        selected.add_being(identities[0])
        world.add_event(selected)
        selected_rng = RNGCursor(random.Random(700).getstate())
        selected.enable_transactional_progression(
            quiescent=True, rng_owner=selected_rng)
        initial = DelayAction(selected, identities[0], defense=0, start_time=0,
                              id='native-multi-selected-initial')
        selected.schedule_action(initial)
        selected.step(1)
        wire = export_save(selected)

        companion_rng_state = companion_rng.state

        def continue_both(native_world, first, second, first_rng,
                          second_rng_state):
            selected_next = DelayAction(
                first, identities[0], defense=0, start_time=first.time,
                id='native-multi-selected-next')
            first.schedule_action(selected_next)
            first.step(1)
            second_rng = native_persistence.rng_owner_for(second)
            if second_rng.state != second_rng_state:
                raise AssertionError('restored companion RNG cursor differs')
            companion_next = DelayAction(
                second, identities[1], defense=0, start_time=second.time,
                id='native-multi-companion-next')
            second.schedule_action(companion_next)
            second.step(1)
            return {
                'encounters': sorted(
                    event.id for event in native_world.event_history.values()
                    if type(event) is Encounter),
                'books': len(native_world._choice_books),
                'times': [first.time, second.time],
                'results': [selected_next.resolution.outcome,
                            companion_next.resolution.outcome],
                'rng': [first_rng.state, second_rng.state],
                'histories': [
                    hashlib.sha256(native_history.encode(
                        native_history.capture(first))).hexdigest(),
                    hashlib.sha256(native_history.encode(
                        native_history.capture(second))).hexdigest(),
                ],
            }

        expected = continue_both(world, selected, companion, selected_rng,
                                 companion_rng_state)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'native-multiple-encounters.json'
            path.write_bytes(wire)
            child = r'''import hashlib,json,sys
from activities import DelayAction
from encounter import Encounter
from native_persistence import load_path,rng_owner_for
import native_history
world,selected,selected_rng=load_path(sys.argv[1])
encounters={event.id:event for event in world.event_history.values()
 if type(event) is Encounter}
assert set(encounters)=={'native-multi-selected','native-multi-pristine-companion'}
companion=encounters['native-multi-pristine-companion']
assert len(world._choice_books)==2
assert all(book.lock is world._schedule_lock for book in world._choice_books)
first=DelayAction(selected,sys.argv[2],defense=0,start_time=selected.time,
 id='native-multi-selected-next')
selected.schedule_action(first);selected.step(1)
second_rng=rng_owner_for(companion)
second=DelayAction(companion,sys.argv[3],defense=0,start_time=companion.time,
 id='native-multi-companion-next')
companion.schedule_action(second);companion.step(1)
print(json.dumps({'encounters':sorted(encounters),'books':len(world._choice_books),
 'times':[selected.time,companion.time],
 'results':[first.resolution.outcome,second.resolution.outcome],
 'rng':[selected_rng.state,second_rng.state],
 'histories':[hashlib.sha256(native_history.encode(native_history.capture(enc))).hexdigest()
  for enc in (selected,companion)]},sort_keys=True))'''
            result = subprocess.run(
                [sys.executable, '-B', '-c', child, str(path),
                 identities[0], identities[1]], cwd=ROOT,
                env={**os.environ,
                     'PYTHONPATH': f'{ROOT / "src"}:{ROOT / "examples"}'},
                text=True, capture_output=True, check=False, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout),
                         json.loads(json.dumps(expected)))

        # Save again after both Encounter streams have progressed. A new OS
        # process must resume each independent cursor/history, not just the
        # selected root.
        continued_save = export_save(selected)
        tampered = json.loads(continued_save)
        tampered['encounters'].append(dict(tampered['encounters'][0]))
        tampered.pop('sha256')
        tampered['sha256'] = hashlib.sha256(
            native_persistence._canonical(tampered)).hexdigest()
        with self.assertRaisesRegex(NativeSaveRejected, 'identities are duplicated'):
            load_save(native_persistence._canonical(tampered))
        tampered = json.loads(continued_save)
        companion_row = next(row for row in tampered['encounters']
                             if row['encounter_id'] == companion.id)
        companion_row['rng_state'] = native_persistence._rng_json(
            random.Random(702).getstate())
        tampered.pop('sha256')
        tampered['sha256'] = hashlib.sha256(
            native_persistence._canonical(tampered)).hexdigest()
        with self.assertRaises(NativeSaveRejected):
            load_save(native_persistence._canonical(tampered))
        selected_second = DelayAction(
            selected, identities[0], defense=0, start_time=selected.time,
            id='native-multi-selected-second')
        companion_second = DelayAction(
            companion, identities[1], defense=0, start_time=companion.time,
            id='native-multi-companion-second')
        selected.schedule_action(selected_second)
        companion.schedule_action(companion_second)
        selected.step(1)
        companion.step(1)
        expected_second = {
            'times': [selected.time, companion.time],
            'results': [selected_second.resolution.outcome,
                        companion_second.resolution.outcome],
            'rng': [selected_rng.state, companion_rng.state],
            'histories': [hashlib.sha256(native_history.encode(
                native_history.capture(saved))).hexdigest()
                for saved in (selected, companion)],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'native-multiple-progressed.json'
            path.write_bytes(continued_save)
            child = r'''import hashlib,json,sys
from activities import DelayAction
from encounter import Encounter
from native_persistence import load_path,rng_owner_for,export_save
import native_history
world,selected,selected_rng=load_path(sys.argv[1])
assert export_save(selected)==open(sys.argv[1],'rb').read()
by_id={event.id:event for event in world.event_history.values()
 if type(event) is Encounter}
companion=by_id['native-multi-pristine-companion']
first=DelayAction(selected,selected.being_list[0],defense=0,
 start_time=selected.time,id='native-multi-selected-second')
second=DelayAction(companion,companion.being_list[0],defense=0,
 start_time=companion.time,id='native-multi-companion-second')
selected.schedule_action(first);companion.schedule_action(second)
selected.step(1);companion.step(1)
print(json.dumps({'times':[selected.time,companion.time],
 'results':[first.resolution.outcome,second.resolution.outcome],
 'rng':[selected_rng.state,rng_owner_for(companion).state],
 'histories':[hashlib.sha256(native_history.encode(native_history.capture(enc))).hexdigest()
  for enc in (selected,companion)]},sort_keys=True))'''
            result = subprocess.run(
                [sys.executable, '-B', '-c', child, str(path)], cwd=ROOT,
                env={**os.environ,
                     'PYTHONPATH': f'{ROOT / "src"}:{ROOT / "examples"}'},
                text=True, capture_output=True, check=False, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout),
                         json.loads(json.dumps(expected_second)))

    def test_native_save_restores_recipient_bindings_for_multiple_encounters(self):
        import os
        import random
        from object import ObjectDefinition, ObjectInstance
        from object_observation import ObjectObservationLedger
        from spatial.geometry import Sphere
        from spatial.occlusion import VisualOcclusion

        world = Universe('native-multi-recipients', library=Library(
            config_dir=str(ROOT / 'src/config')))
        encounters = []
        bindings = []
        for index, seed in ((0, 11), (1, 12)):
            actor_id = world.make_being('Human', f'Multi observer {index}')
            actor = world.get_object_by_id(actor_id)
            actor.set_position(CartesianPosition(0, index * 5, 0))
            actor.set_geometry(Sphere(.25))
            object_id = f'native-multi-observer-object-{index}'
            target = ObjectInstance(
                ObjectDefinition(f'Multi target {index}', 1, 1, .2, .2,
                                 1, 0, 0),
                f'Multi target {index}', id=object_id)
            world.add_object(target)
            target.set_position(CartesianPosition(1.5, index * 5, 0))
            target.set_geometry(Sphere(.1))
            target.set_visual_occlusion(VisualOcclusion(0))
            target.current.discovery_dc = 15
            encounter = Encounter(world, 10, 0, initiated=True,
                                  id=f'native-multi-observer-encounter-{index}')
            encounter.add_being(actor_id)
            encounter.add_object(object_id)
            world.add_event(encounter)
            rng = RNGCursor(random.Random(seed).getstate())
            encounter.enable_transactional_progression(
                quiescent=True, rng_owner=rng)
            ledger = ObjectObservationLedger(actor_id)
            action = SpotAction(world, actor_id, object_id, 0,
                                object_ledger=ledger,
                                id=f'native-multi-observer-spot-{index}')
            encounter.schedule_action(action)
            encounters.append((encounter, actor, target, rng, action, ledger))
            bindings.append(RecipientBinding(
                world, 'native-multi-observer', f'ledger-{index}',
                'observer_object_evidence', (actor_id,), ledger))

        # The selected Encounter is deliberately second in registry order.
        companion, selected = encounters
        selected[0].step(1)
        wire = export_save(selected[0], recipient_bindings=tuple(bindings))

        def finish(encounter):
            while encounter.time < 6:
                encounter.step(1)

        for encounter, *_ in encounters:
            finish(encounter)

        def projection():
            return {
                'times': [row[0].time for row in encounters],
                'outcomes': [row[4].resolution.outcome for row in encounters],
                'rng': [row[3].state for row in encounters],
                'evidence': [[ob.id, ob.observer_id, ob.object_id,
                              ob.source_action_id, ob.encounter_id, ob.boundary,
                              ob.time, list(ob.position.as_tuple()), ob.basis]
                             for row in encounters for ob in row[5].observations],
                'histories': [hashlib.sha256(native_history.encode(
                    native_history.capture(row[0]))).hexdigest()
                    for row in encounters],
            }

        expected = projection()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'native-multi-observers.json'
            path.write_bytes(wire)
            child = r'''import hashlib,json,sys
import native_history
from encounter import Encounter
from native_persistence import load_path,rng_owner_for
world,selected,selected_rng=load_path(sys.argv[1])
encounters={event.id:event for event in world.event_history.values()
 if type(event) is Encounter}
assert len(encounters)==2
actions=[next(member.action for choice in enc._choice_book._choices.values()
 for member in choice.members) for enc in encounters.values()]
rows=[]
for enc,action in zip(encounters.values(),actions):
 while enc.time < 6:
  enc.step(1)
 rows.append((enc,action,rng_owner_for(enc)))
evidence=[[ob.id,ob.observer_id,ob.object_id,ob.source_action_id,
 ob.encounter_id,ob.boundary,ob.time,list(ob.position.as_tuple()),ob.basis]
 for _enc,action,_rng in rows for ob in action.object_ledger.observations]
assert all(all(ob.observer_id==action.actor_id
 for ob in action.object_ledger.observations) for _enc,action,_rng in rows)
print(json.dumps({'times':[row[0].time for row in rows],
 'outcomes':[row[1].resolution.outcome for row in rows],
 'rng':[row[2].state for row in rows],'evidence':evidence,
 'histories':[hashlib.sha256(native_history.encode(
  native_history.capture(row[0]))).hexdigest() for row in rows]},sort_keys=True))'''
            result = subprocess.run(
                [sys.executable, '-B', '-c', child, str(path)], cwd=ROOT,
                env={**os.environ,
                     'PYTHONPATH': f'{ROOT / "src"}:{ROOT / "examples"}'},
                text=True, capture_output=True, check=False, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout),
                         json.loads(json.dumps(expected)))

    def test_native_save_restores_location_ledgers_across_multiple_encounters(self):
        import os
        import random
        from spatial.geometry import Sphere

        world=Universe('native-multi-location-recipients',library=Library(
            config_dir=str(ROOT/'src/config')))
        rows=[];bindings=[]
        for index,seed in ((0,31),(1,32)):
            observer_id=world.make_being('Human',f'Location observer {index}')
            target_id=world.make_being('Human',f'Location target {index}')
            observer=world.get_object_by_id(observer_id);target=world.get_object_by_id(target_id)
            observer.set_position(CartesianPosition(0,index*5,0))
            target.set_position(CartesianPosition(1.5,index*5,0))
            observer.set_geometry(Sphere(.25));target.set_geometry(Sphere(.25))
            encounter=Encounter(world,10,0,initiated=True,
                id=f'native-multi-location-encounter-{index}')
            encounter.add_being(observer_id);encounter.add_being(target_id)
            encounter.mark_aware(observer_id,target_id);encounter.mark_aware(target_id,observer_id)
            world.add_event(encounter)
            rng=RNGCursor(random.Random(seed).getstate())
            encounter.enable_transactional_progression(quiescent=True,rng_owner=rng)
            ledger=LocationEvidenceLedger(observer_id)
            action=SpotAction(world,observer_id,target_id,0,die_roll=20,
                location_ledger=ledger,id=f'native-multi-location-spot-{index}')
            encounter.schedule_action(action);encounter.step(1)
            rows.append((encounter,observer,target,rng,action,ledger))
            bindings.append(RecipientBinding(world,'native-multi-location',f'ledger-{index}',
                'observer_location_evidence',(observer_id,),ledger))
        selected=rows[1][0]
        wire=export_save(selected,recipient_bindings=tuple(bindings))

        def projection():
            return {'times':[row[0].time for row in rows],
                'outcomes':[row[4].resolution.outcome for row in rows],
                'rng':[row[3].state for row in rows],
                'observations':[[ob.id,ob.observer_id,ob.being_id,ob.source_action_id,
                    ob.encounter_id,ob.boundary,ob.time,list(ob.position.as_tuple()),ob.basis]
                    for row in rows for ob in row[5].observations],
                'histories':[hashlib.sha256(native_history.encode(
                    native_history.capture(row[0]))).hexdigest() for row in rows]}

        for encounter,*_ in rows:
            while encounter.time<6:encounter.step(1)
        expected=projection()
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'native-multi-location-save.json';path.write_bytes(wire)
            child=r'''import hashlib,json,sys
import native_history
from encounter import Encounter
from native_persistence import load_path,rng_owner_for
world,selected,selected_rng=load_path(sys.argv[1])
encounters={event.id:event for event in world.event_history.values() if type(event)is Encounter}
assert len(encounters)==2
rows=[]
for index in range(2):
 enc=encounters[f'native-multi-location-encounter-{index}']
 action=world.get_event_by_id(f'native-multi-location-spot-{index}')
 assert action.location_ledger.observer_id==action.actor_id
 while enc.time<6:enc.step(1)
 rows.append((enc,action,rng_owner_for(enc)))
observations=[[ob.id,ob.observer_id,ob.being_id,ob.source_action_id,ob.encounter_id,
 ob.boundary,ob.time,list(ob.position.as_tuple()),ob.basis]
 for _enc,action,_rng in rows for ob in action.location_ledger.observations]
assert all(all(ob.observer_id==action.actor_id
 for ob in action.location_ledger.observations) for _enc,action,_rng in rows)
print(json.dumps({'times':[row[0].time for row in rows],
 'outcomes':[row[1].resolution.outcome for row in rows],
 'rng':[row[2].state for row in rows],'observations':observations,
 'histories':[hashlib.sha256(native_history.encode(native_history.capture(row[0]))).hexdigest()
 for row in rows]},sort_keys=True))'''
            result=subprocess.run([sys.executable,'-B','-c',child,str(path)],cwd=ROOT,
                env={**os.environ,'PYTHONPATH':f'{ROOT / "src"}:{ROOT / "examples"}'},
                text=True,capture_output=True,check=False,timeout=60)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout),json.loads(json.dumps(expected)))

    def test_native_save_restores_distinct_group_beliefs_across_encounters(self):
        import os
        import random
        from field_observation import BeliefLedger
        from group_observation import ObserveGroupAction

        world=Universe('native-multi-group-beliefs',library=Library(
            config_dir=str(ROOT/'src/config')))
        rows=[];bindings=[]
        skills=world.get_skill_dictionary()
        for index,seed in ((0,41),(1,42)):
            config=json.loads((ROOT/'examples/nomadic_group.json').read_text())
            config['motion']['position']=[1.5,index*5,0]
            group=StatisticalGroup(f'Objective Group {index}',
                f'native-group-{index}',config,81)
            world.add_object(group)
            actor_id=world.make_being('Human',f'Group observer {index}')
            actor=world.get_object_by_id(actor_id)
            actor.set_position(CartesianPosition(0,index*5,0))
            actor.set_geometry(Sphere(.25))
            actor.set_skill_level(skills,'spot',10)
            encounter=Encounter(world,10,0,initiated=True,
                id=f'native-multi-group-encounter-{index}')
            encounter.add_being(actor_id);encounter.add_object(group.id)
            world.add_event(encounter)
            rng=RNGCursor(random.Random(seed).getstate())
            encounter.enable_transactional_progression(quiescent=True,rng_owner=rng)
            ledger=BeliefLedger(actor_id)
            action=ObserveGroupAction(world,actor_id,group.id,0,seed=seed,
                random_key=f'belief-observer-{index}',
                observation={'coarse_range_m':100,'detailed_range_m':50},
                ledger=ledger)
            encounter.schedule_action(action);encounter.step(1)
            rows.append((encounter,actor,group,rng,action,ledger))
            bindings.append(RecipientBinding(world,'native-multi-group',f'belief-{index}',
                'in_world_belief_ledger',(actor_id,),ledger))
        self.assertTrue(all(row[4].resolution.outcome=='success' for row in rows))
        wire=export_save(rows[1][0],recipient_bindings=tuple(bindings))

        def project_observation(observation):
            return [observation.id,observation.observer_id,observation.group_id,
                observation.time,
                None if observation.reported_position is None else list(observation.reported_position.as_tuple()),
                sorted((name,value.estimate,value.uncertainty)
                    for name,value in observation.reports.items()),
                observation.mode,sorted(observation.dubious_candidates.items()),
                observation.focus_category]

        def project_interpretation(value):
            return [value.observation_id,value.observer_id,value.skill_name,
                value.skill_level,sorted((name,report.estimate,report.uncertainty)
                    for name,report in value.reports.items()),
                sorted(value.rejected_candidates.items())]

        def project_provenance(ledger):
            return [[entry.encounter_id,entry.boundary,entry.key.entity_id,
                entry.key.attribute,entry.key.detail,entry.key.time,entry.revision,
                list(entry.origins),list(entry.requesters),list(entry.consumers)]
                for entry in ledger._atomic_provenance]

        def project():
            return {'times':[row[0].time for row in rows],
                'outcomes':[row[4].resolution.outcome for row in rows],
                'samplers':[json.loads(json.dumps(row[4].observer.__dict__)) for row in rows],
                'interpreters':[json.loads(json.dumps(row[4].interpreter.__dict__)) for row in rows],
                'evidence':[[project_observation(ob) for ob in row[5].evidence] for row in rows],
                'interpretations':[[[key,project_interpretation(value)] for key,value in sorted(
                    row[5]._interpretations.items())] for row in rows],
                'belief_history':[[[item.group_id,item.category,item.estimate,
                    list(item.evidence_ids),item.trigger,item.time,item.disputed,
                    item.trigger_observation_id] for item in row[5].belief_history] for row in rows],
                'rng':[row[3].state for row in rows],
                'facts':[row[2]._composition_reality.to_jsonable() for row in rows],
                'objective_provenance':[project_provenance(row[2]._composition_reality)
                    for row in rows],
                'objective_history':[[native_history.NativeHistoryQuery(
                    native_history.capture(row[0])).objective_at(boundary)
                    for boundary in (0,1,2)] for row in rows],
                'objective_use_history':[[native_history.NativeHistoryQuery(
                    native_history.capture(row[0])).objective_use_at(boundary)
                    for boundary in (0,1,2)] for row in rows],
                'observer_history':[[native_history.NativeHistoryQuery(
                    native_history.capture(row[0])).observer_facts_at(boundary,
                    row[1].id) for boundary in (0,1,2)] for row in rows],
                'histories':[hashlib.sha256(native_history.encode(
                    native_history.capture(row[0]))).hexdigest() for row in rows]}

        for encounter,*_ in rows:
            encounter.schedule_action(DelayAction(encounter,encounter.being_list[0],
                defense=0,start_time=encounter.time,id=f'{encounter.id}-continuation'))
            encounter.step(1)
        expected=project()
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'native-multi-group-beliefs.json';path.write_bytes(wire)
            child=r'''import hashlib,json,sys
from encounter import Encounter
from activities import DelayAction
import native_history
from native_persistence import load_path,rng_owner_for
def interpretation(value):
 return [value.observation_id,value.observer_id,value.skill_name,value.skill_level,
  sorted((name,report.estimate,report.uncertainty) for name,report in value.reports.items()),
  sorted(value.rejected_candidates.items())]
def provenance(ledger):
 return [[entry.encounter_id,entry.boundary,entry.key.entity_id,
  entry.key.attribute,entry.key.detail,entry.key.time,entry.revision,
  list(entry.origins),list(entry.requesters),list(entry.consumers)]
  for entry in ledger._atomic_provenance]
world,selected,selected_rng=load_path(sys.argv[1])
encounters={event.id:event for event in world.event_history.values() if type(event)is Encounter}
assert len(encounters)==2
rows=[]
for index in range(2):
 enc=encounters[f'native-multi-group-encounter-{index}']
 action=world.get_event_by_id(sys.argv[index+2])
 group=world.get_object_by_id(f'native-group-{index}')
 ledger=action.ledger
 assert ledger.observer_id==action.actor_id
 assert len(ledger.evidence)==1 and len(ledger.inquiry_history)==0
 assert ledger.interpretation_for(ledger.evidence[0].id) is not None
 assert interpretation(ledger.current_interpretation_for(ledger.evidence[0].id))==interpretation(ledger.interpretation_for(ledger.evidence[0].id))
 assert action.interpreter.skill_name=='spot' and action.interpreter.expert_level==5
 assert action.observer.coarse_range_m==100 and action.observer.detailed_range_m==50
 actor=world.get_object_by_id(action.actor_id)
 enc.schedule_action(DelayAction(enc,actor.id,defense=0,start_time=enc.time,
  id=f'{enc.id}-continuation'))
 enc.step(1);rows.append((enc,action,ledger,rng_owner_for(enc),group))
def obs(o):
 return [o.id,o.observer_id,o.group_id,o.time,
  None if o.reported_position is None else list(o.reported_position.as_tuple()),
  sorted((name,value.estimate,value.uncertainty) for name,value in o.reports.items()),
  o.mode,sorted(o.dubious_candidates.items()),o.focus_category]
def interpretation(value):
 return [value.observation_id,value.observer_id,value.skill_name,value.skill_level,
  sorted((name,report.estimate,report.uncertainty) for name,report in value.reports.items()),
  sorted(value.rejected_candidates.items())]
print(json.dumps({'times':[r[0].time for r in rows],
 'outcomes':[r[1].resolution.outcome for r in rows],
 'samplers':[r[1].observer.__dict__ for r in rows],
 'interpreters':[r[1].interpreter.__dict__ for r in rows],
 'evidence':[[obs(o) for o in r[2].evidence] for r in rows],
 'interpretations':[[[key,interpretation(value)] for key,value in sorted(
  r[2]._interpretations.items())] for r in rows],
 'belief_history':[[[i.group_id,i.category,i.estimate,list(i.evidence_ids),i.trigger,
  i.time,i.disputed,i.trigger_observation_id] for i in r[2].belief_history] for r in rows],
 'rng':[r[3].state for r in rows],
 'facts':[r[4]._composition_reality.to_jsonable() for r in rows],
 'objective_provenance':[provenance(r[4]._composition_reality) for r in rows],
 'objective_history':[[native_history.NativeHistoryQuery(
  native_history.capture(r[0])).objective_at(boundary)
  for boundary in (0,1,2)] for r in rows],
 'objective_use_history':[[native_history.NativeHistoryQuery(
  native_history.capture(r[0])).objective_use_at(boundary)
  for boundary in (0,1,2)] for r in rows],
 'observer_history':[[native_history.NativeHistoryQuery(
  native_history.capture(r[0])).observer_facts_at(boundary,r[1].actor_id)
  for boundary in (0,1,2)] for r in rows],
 'histories':[hashlib.sha256(native_history.encode(native_history.capture(r[0]))).hexdigest()
  for r in rows]},sort_keys=True))'''
            result=subprocess.run([sys.executable,'-B','-c',child,str(path),
                rows[0][4].id,rows[1][4].id],cwd=ROOT,
                env={**os.environ,'PYTHONPATH':f'{ROOT / "src"}:{ROOT / "examples"}'},
                text=True,capture_output=True,check=False,timeout=60)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout),json.loads(json.dumps(expected)))

    def test_native_save_distinguishes_same_owner_belief_ledgers(self):
        """Two native ledgers owned by one Being retain distinct stable IDs."""
        import os
        import random
        from field_observation import BeliefLedger
        from group_observation import ObserveGroupAction

        world = Universe('native-same-owner-beliefs', library=Library(
            config_dir=str(ROOT / 'src/config')))
        actor_id = world.make_being('Human', 'Repeated observer')
        actor = world.get_object_by_id(actor_id)
        actor.set_position(CartesianPosition(0, 0, 0))
        actor.set_geometry(Sphere(.25))
        actor.set_skill_level(world.get_skill_dictionary(), 'spot', 10)
        groups = []
        for index, y in enumerate((0, 4)):
            config = json.loads((ROOT / 'examples/nomadic_group.json').read_text())
            config['motion']['position'] = [1.5, y, 0]
            group = StatisticalGroup(f'Repeated owner group {index}',
                f'native-same-owner-group-{index}', config, 81)
            world.add_object(group)
            groups.append(group)
        encounter = Encounter(world, 10, 0, initiated=True,
            id='native-same-owner-belief-encounter')
        encounter.add_being(actor_id)
        for group in groups:
            encounter.add_object(group.id)
        world.add_event(encounter)
        rng = RNGCursor(random.Random(41).getstate())
        encounter.enable_transactional_progression(quiescent=True, rng_owner=rng)
        ledgers = (BeliefLedger(actor_id), BeliefLedger(actor_id))
        actions = tuple(ObserveGroupAction(world, actor_id, group.id, index,
            seed=41 + index, random_key=f'same-owner-belief-{index}',
            observation={'coarse_range_m': 100, 'detailed_range_m': 50},
            ledger=ledgers[index]) for index, group in enumerate(groups))
        encounter.schedule_action(actions[0])
        encounter.step(1)
        encounter.schedule_action(actions[1])
        encounter.step(1)
        self.assertEqual([action.resolution.outcome for action in actions],
                         ['success', 'success'])
        query = native_history.NativeHistoryQuery(native_history.capture(encounter))
        for boundary in (1, 2):
            expected_rows = native_history._stable_recipients(
                encounter.inspect_committed(boundary).recipients, encounter)
            self.assertEqual(query.state_at(boundary)['recipients'], expected_rows)
        final_rows = query.state_at(2)['recipients']
        self.assertEqual(len(final_rows), 2)
        self.assertEqual({row['owner_id'] for row in final_rows}, {actor_id})
        self.assertEqual(len({row['binding_id'] for row in final_rows}), 2)
        from native_history import _recipient_binding_id
        first_binding_id = _recipient_binding_id(
            world, 'in_world_belief_ledger', id(ledgers[0]))
        later_alias = ObserveGroupAction(
            world, actor_id, groups[0].id, 8, seed=41,
            observation={'coarse_range_m': 100, 'detailed_range_m': 50},
            random_key='same-owner-later-ledger-alias', ledger=ledgers[0])
        later_alias.id = '000-native-same-owner-later-alias'
        encounter.schedule_action(later_alias)
        self.assertEqual(_recipient_binding_id(
            world, 'in_world_belief_ledger', id(ledgers[0])),
            first_binding_id,
            'a later Action must not re-key an already recorded recipient')
        bindings = tuple(RecipientBinding(world, 'same-owner', f'belief-{index}',
            'in_world_belief_ledger', (actor_id,), ledger)
            for index, ledger in enumerate(ledgers))
        wire = export_save(encounter, recipient_bindings=bindings)
        action_ids = [action.id for action in actions]
        # The preceding descriptor version did not include the pinned origin.
        # Its strict reader recovers that origin from the saved Action refs,
        # including when a later earlier-sorting declaration reuses a ledger.
        import native_graph_snapshot
        legacy_payload = json.loads(wire)
        legacy_inventory = native_graph_snapshot.decode(
            base64.b64decode(legacy_payload['graph_b64']), native=True)
        compatibility, inventory_body = legacy_inventory
        legacy_sections = []
        for section in inventory_body[1:]:
            if section[0] == 'native-adapters':
                markers = tuple('observer-recipient-facts/1'
                    if marker == 'observer-recipient-facts/2' else marker
                    for marker in section[1:])
                section = (section[0], *markers)
            elif section[0] == 'host-bindings':
                section = (section[0], tuple(row[:6] for row in section[1]))
            legacy_sections.append(section)
        legacy_inventory = (compatibility,
                            (inventory_body[0], *legacy_sections))
        legacy_payload['graph_b64'] = base64.b64encode(
            native_graph_snapshot.encode(legacy_inventory, native=True)
        ).decode('ascii')
        legacy_unsigned = {key: value for key, value in legacy_payload.items()
                           if key != 'sha256'}
        legacy_payload['sha256'] = hashlib.sha256(
            native_persistence._canonical(legacy_unsigned)).hexdigest()
        migrated_world, migrated_encounter, _migrated_rng = load_save(
            native_persistence._canonical(legacy_payload))
        migrated_actions = [migrated_world.get_event_by_id(identity)
                            for identity in action_ids]
        self.assertIsNot(migrated_actions[0].ledger, migrated_actions[1].ledger)
        self.assertEqual(migrated_encounter.id, encounter.id)
        # Re-seal the container after substituting a well-formed, unique but
        # false stable identity. Strict graph decode must derive it again from
        # the saved Action references instead of trusting the descriptor.
        payload = json.loads(wire)
        inventory = native_graph_snapshot.decode(
            base64.b64decode(payload['graph_b64']), native=True)
        compatibility, inventory_body = inventory
        sections = []
        for section in inventory_body[1:]:
            if section[0] == 'host-bindings':
                descriptors = list(section[1])
                descriptor = descriptors[0]
                descriptors[0] = (*descriptor[:5], 'f' * 64, descriptor[6])
                section = (section[0], tuple(descriptors))
            sections.append(section)
        forged_inventory = (compatibility,
                            (inventory_body[0], *sections))
        payload['graph_b64'] = base64.b64encode(
            native_graph_snapshot.encode(forged_inventory, native=True)
        ).decode('ascii')
        unsigned = {key: value for key, value in payload.items()
                    if key != 'sha256'}
        payload['sha256'] = hashlib.sha256(
            native_persistence._canonical(unsigned)).hexdigest()
        with self.assertRaisesRegex(
                NativeSaveRejected,
                'Action references'):
            load_save(native_persistence._canonical(payload))
        encounter.schedule_action(DelayAction(encounter, actor_id, defense=0,
            start_time=2, id='native-same-owner-continuation'))
        encounter.step(1)
        expected = {
            'time': encounter.time,
            'rng': rng.state,
            'action_ids': action_ids,
            'evidence': [[row.id for row in ledger.evidence] for ledger in ledgers],
            'history': hashlib.sha256(native_history.encode(
                native_history.capture(encounter))).hexdigest(),
        }
        child = r'''import hashlib,json,sys
from activities import DelayAction
import native_history
from native_persistence import load_path,rng_owner_for
world,enc,_rng=load_path(sys.argv[1])
actions=[world.get_event_by_id(identity) for identity in sys.argv[2:4]]
ledgers=[action.ledger for action in actions]
assert len(ledgers[0].evidence)==1 and len(ledgers[1].evidence)==1
assert ledgers[0] is not ledgers[1]
assert [action.resolution.outcome for action in actions]==['success','success']
enc.schedule_action(DelayAction(enc,enc.being_list[0],defense=0,start_time=2,
 id='native-same-owner-continuation'));enc.step(1)
print(json.dumps({'time':enc.time,'rng':rng_owner_for(enc).state,
 'action_ids':[action.id for action in actions],
 'evidence':[[row.id for row in ledger.evidence] for ledger in ledgers],
 'history':hashlib.sha256(native_history.encode(
  native_history.capture(enc))).hexdigest()},sort_keys=True))'''
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'same-owner-beliefs.json'
            path.write_bytes(wire)
            result = subprocess.run([sys.executable, '-B', '-c', child,
                str(path), *action_ids], cwd=directory, env={**os.environ,
                'PYTHONPATH': f'{ROOT / "src"}:{ROOT / "examples"}'},
                text=True, capture_output=True, check=False, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout),
                         json.loads(json.dumps(expected)))

    def test_native_save_restores_listener_accounts_across_encounters(self):
        import os
        import random
        from personal_history import PersonalHistory
        from realization import Fact
        from objective_reality import EpisodeFacts

        world=Universe('native-multi-listener-accounts',library=Library(
            config_dir=str(ROOT/'src/config')))
        rows=[];bindings=[]
        for index,seed in ((0,51),(1,52)):
            listener_id=world.make_being('Human',f'Listener {index}')
            speaker_id=world.make_being('Human',f'Speaker {index}')
            listener=world.get_object_by_id(listener_id);speaker=world.get_object_by_id(speaker_id)
            listener.set_position(CartesianPosition(0,index*5,0))
            speaker.set_position(CartesianPosition(1.5,index*5,0))
            encounter=Encounter(world,10,0,initiated=True,
                id=f'native-multi-accounts-encounter-{index}')
            encounter.add_being(listener_id);encounter.add_being(speaker_id)
            encounter.mark_aware(listener_id,speaker_id)
            world.add_event(encounter)
            rng=RNGCursor(random.Random(seed).getstate())
            encounter.enable_transactional_progression(quiescent=True,rng_owner=rng)
            topic=f'account-{index}'
            speaker.personal_history=PersonalHistory(speaker,earliest=-10,
                known_through=0,nondeclining_skills=())
            key=speaker.personal_history.episode_key(-1,topic)
            description=f'native testimony {index}'
            facts=EpisodeFacts((Fact(key,{'description':description},origin='declared-testimony'),))
            accounts=[]
            action=AskAboutPastAction(world,listener_id,speaker_id,0,
                episode_time=-1,topic=topic,generate=facts,
                duration=1,received_accounts=accounts)
            encounter.schedule_action(action);encounter.step(1)
            self.assertEqual(action.resolution.outcome,'heard')
            self.assertEqual(len(accounts),1)
            rows.append((encounter,listener,speaker,rng,action,accounts))
            bindings.append(RecipientBinding(world,'native-multi-accounts',
                f'accounts-{index}','in_world_received_accounts',(listener_id,),accounts))
        wire=export_save(rows[1][0],recipient_bindings=tuple(bindings))
        import base64
        from native_graph_snapshot import decode as decode_graph
        graph = decode_graph(base64.b64decode(
            json.loads(wire)["graph_b64"], validate=True), native=True)
        nodes = next(row[1] for row in graph[1] if row[0] == "nodes")
        tags = [tag for _reference, tag, _content in nodes]
        self.assertNotIn("action_settlement.TargetIntervalRecord", tags)
        self.assertNotIn("encounter_inspection.EntityInspection", tags)
        self.assertNotIn("encounter_inspection.CommittedBoundaryRecord", tags)
        self.assertNotIn("atomic_publication.PublishedInterval", tags)
        self.assertNotIn("observer_proposals.BeliefProjection", tags)
        self.assertNotIn("observer_proposals.AccountsProjection", tags)
        self.assertNotIn("observer_proposals.LocationEvidenceProjection", tags)
        self.assertNotIn("observer_proposals.ObjectEvidenceProjection", tags)
        markers = next(row[1:] for row in graph[1]
                       if row[0] == "native-adapters")
        self.assertIn("committed-receipt-facts/1", markers)
        self.assertIn("observer-recipient-facts/2", markers)
        self.assertIn("published-interval-facts/1", markers)
        self.assertIn("committed-boundary-history/1", markers)
        for encounter,*_ in rows:
            encounter.schedule_action(DelayAction(encounter,encounter.being_list[0],
                defense=0,start_time=encounter.time,id=f'{encounter.id}-continuation'))
            encounter.step(1)
        expected={'times':[row[0].time for row in rows],
            'outcomes':[row[4].resolution.outcome for row in rows],
            'accounts':[row[5][0].to_dict() for row in rows],
            'declared_facts':[[[fact.key.entity_id,fact.key.attribute,fact.key.detail,
                fact.key.time,dict(fact.value),fact.origin] for fact in row[4].generate.facts]
                for row in rows],
            'facts':[row[2].personal_history.to_jsonable() for row in rows],
            'objective_history':[[native_history.NativeHistoryQuery(
                native_history.capture(row[0])).objective_at(boundary)
                for boundary in (0,1,2)] for row in rows],
            'objective_use_history':[[native_history.NativeHistoryQuery(
                native_history.capture(row[0])).objective_use_at(boundary)
                for boundary in (0,1,2)] for row in rows],
            'rng':[row[3].state for row in rows],
            'histories':[hashlib.sha256(native_history.encode(
                native_history.capture(row[0]))).hexdigest() for row in rows]}
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'native-multi-listener-accounts.json';path.write_bytes(wire)
            child=r'''import hashlib,json,sys
from encounter import Encounter
from activities import DelayAction
import native_history
from objective_reality import EpisodeFacts,DeclaredObjectiveFact
from native_persistence import load_path,rng_owner_for
world,selected,selected_rng=load_path(sys.argv[1])
encounters={event.id:event for event in world.event_history.values() if type(event)is Encounter}
assert len(encounters)==2;rows=[]
for index in range(2):
 enc=encounters[f'native-multi-accounts-encounter-{index}']
 action=world.get_event_by_id(sys.argv[index+2])
 assert action.resolution.outcome=='heard' and len(action.received_accounts)==1
 assert type(action.generate)is EpisodeFacts
 assert all(type(fact)is DeclaredObjectiveFact for fact in action.generate.facts)
 speaker=world.get_object_by_id(action.target_id)
 enc.schedule_action(DelayAction(enc,action.actor_id,defense=0,start_time=enc.time,
  id=f'{enc.id}-continuation'))
 enc.step(1);rows.append((enc,action,speaker,rng_owner_for(enc)))
print(json.dumps({'times':[r[0].time for r in rows],
 'outcomes':[r[1].resolution.outcome for r in rows],
 'accounts':[r[1].received_accounts[0].to_dict() for r in rows],
 'declared_facts':[[[fact.key.entity_id,fact.key.attribute,fact.key.detail,
  fact.key.time,dict(fact.value),fact.origin] for fact in r[1].generate.facts]
  for r in rows],
 'facts':[r[2].personal_history.to_jsonable() for r in rows],
 'objective_history':[[native_history.NativeHistoryQuery(
  native_history.capture(r[0])).objective_at(boundary)
  for boundary in (0,1,2)] for r in rows],
 'objective_use_history':[[native_history.NativeHistoryQuery(
  native_history.capture(r[0])).objective_use_at(boundary)
  for boundary in (0,1,2)] for r in rows],
 'rng':[r[3].state for r in rows],
 'histories':[hashlib.sha256(native_history.encode(native_history.capture(r[0]))).hexdigest()
  for r in rows]},sort_keys=True))'''
            result=subprocess.run([sys.executable,'-B','-c',child,str(path),
                rows[0][4].id,rows[1][4].id],cwd=ROOT,
                env={**os.environ,'PYTHONPATH':f'{ROOT / "src"}:{ROOT / "examples"}'},
                text=True,capture_output=True,check=False,timeout=60)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout),json.loads(json.dumps(expected)))

    def test_native_save_combines_object_and_location_recipients(self):
        """A /2 Save restores heterogeneous owner bindings in one graph."""
        import os
        import random
        from object import ObjectDefinition, ObjectInstance
        from object_observation import ObjectObservationLedger
        from spatial.occlusion import VisualOcclusion

        world = Universe('native-mixed-observer-recipients', library=Library(
            config_dir=str(ROOT / 'src/config')))
        rows = []
        bindings = []
        for index, role, seed in ((0, 'object', 71), (1, 'location', 72)):
            observer_id = world.make_being('Human', f'Mixed observer {index}')
            observer = world.get_object_by_id(observer_id)
            observer.set_position(CartesianPosition(0, index * 5, 0))
            observer.set_geometry(Sphere(.25))
            if role == 'object':
                target_id = f'native-mixed-target-{index}'
                target = ObjectInstance(
                    ObjectDefinition(f'Mixed object {index}', 1, 1, .2, .2,
                                     1, 0, 0), f'Mixed object {index}',
                    id=target_id)
                world.add_object(target)
                target.set_position(CartesianPosition(1.5, index * 5, 0))
                target.set_geometry(Sphere(.1))
                target.set_visual_occlusion(VisualOcclusion(0))
                target.current.discovery_dc = 15
                ledger = ObjectObservationLedger(observer_id)
                action = SpotAction(world, observer_id, target_id, 0,
                                    object_ledger=ledger,
                                    id=f'native-mixed-action-{index}')
                binding_role = 'observer_object_evidence'
            else:
                target_id = world.make_being('Human', f'Mixed target {index}')
                target = world.get_object_by_id(target_id)
                target.set_position(CartesianPosition(1.5, index * 5, 0))
                target.set_geometry(Sphere(.25))
                ledger = LocationEvidenceLedger(observer_id)
                action = SpotAction(world, observer_id, target_id, 0,
                                    die_roll=20, location_ledger=ledger,
                                    id=f'native-mixed-action-{index}')
                binding_role = 'observer_location_evidence'
            encounter = Encounter(world, 10, 0, initiated=True,
                                  id=f'native-mixed-encounter-{index}')
            encounter.add_being(observer_id)
            if role == 'object':
                encounter.add_object(target_id)
            else:
                encounter.add_being(target_id)
                encounter.mark_aware(observer_id, target_id)
                encounter.mark_aware(target_id, observer_id)
            world.add_event(encounter)
            rng = RNGCursor(random.Random(seed).getstate())
            encounter.enable_transactional_progression(quiescent=True,
                                                       rng_owner=rng)
            encounter.schedule_action(action)
            encounter.step(1)
            rows.append((encounter, rng, action, ledger))
            bindings.append(RecipientBinding(
                world, 'native-mixed-recipients', f'ledger-{index}',
                binding_role, (observer_id,), ledger))

        listener_id = world.make_being('Human', 'Mixed listener')
        speaker_id = world.make_being('Human', 'Mixed speaker')
        listener = world.get_object_by_id(listener_id)
        speaker = world.get_object_by_id(speaker_id)
        listener.set_position(CartesianPosition(0, 10, 0))
        speaker.set_position(CartesianPosition(1.5, 10, 0))
        encounter = Encounter(world, 10, 0, initiated=True,
                              id='native-mixed-encounter-2')
        encounter.add_being(listener_id)
        encounter.add_being(speaker_id)
        encounter.mark_aware(listener_id, speaker_id)
        world.add_event(encounter)
        rng = RNGCursor(random.Random(73).getstate())
        encounter.enable_transactional_progression(quiescent=True,
                                                   rng_owner=rng)
        from personal_history import PersonalHistory
        from realization import Fact
        from objective_reality import EpisodeFacts
        speaker.personal_history = PersonalHistory(
            speaker, earliest=-10, known_through=0, nondeclining_skills=())
        key = speaker.personal_history.episode_key(-1, 'mixed-testimony')
        facts = EpisodeFacts((Fact(
            key, {'description': 'mixed testimony'},
            origin='declared-testimony'),))
        accounts = []
        action = AskAboutPastAction(
            world, listener_id, speaker_id, 0, episode_time=-1,
            topic='mixed-testimony', generate=facts, duration=1,
            received_accounts=accounts)
        encounter.schedule_action(action)
        encounter.step(1)
        self.assertEqual(action.resolution.outcome, 'heard')
        rows.append((encounter, rng, action, accounts))
        bindings.append(RecipientBinding(
            world, 'native-mixed-recipients', 'listener-accounts',
            'in_world_received_accounts', (listener_id,), accounts))

        wire = export_save(rows[1][0], recipient_bindings=tuple(bindings))
        for encounter, *_ in rows:
            while encounter.time < 6:
                encounter.step(1)

        def expected_projection():
            output = []
            for row in rows:
                encounter, rng, action, recipient = row[:4]
                self._assert_recipient_history_matches_receipts(encounter)
                if type(recipient) is list:
                    observations = recipient[0].to_dict()
                    target = encounter.universe.get_object_by_id(action.target_id)
                    facts = target.personal_history.to_jsonable()
                else:
                    observations = [[value.id, value.observer_id,
                        getattr(value, 'object_id', None),
                        getattr(value, 'being_id', None), value.source_action_id,
                        value.encounter_id, value.boundary, value.time,
                        list(value.position.as_tuple()), value.basis]
                        for value in recipient.observations]
                    facts = native_history.NativeHistoryQuery(
                        native_history.capture(encounter)).observer_facts_at(
                            encounter.last_processed_boundary, action.actor_id)
                query = native_history.NativeHistoryQuery(
                    native_history.capture(encounter))
                historical_facts = [
                    query.observer_facts_at(boundary, action.actor_id)
                    for boundary in (0, 1, 6)]
                if action is rows[2][2]:
                    # Emulate the prior /9 writer, which retained only each
                    # boundary's touched recipient rows and had no listener
                    # owner field. The strict upgrade must recover ownership
                    # from recorded HeardAccount facts and carry state forward.
                    def legacy_recipients(value, _encounter):
                        output = []
                        for identity, projection in value.items():
                            role = object.__getattribute__(identity, "__dict__")["role"]
                            data = dict(object.__getattribute__(projection, "__dict__"))
                            data.pop("identity", None)
                            data.pop("listener_ids", None)
                            owner = data.get("observer_id") or data.get("listener_id")
                            output.append({"role": role, "owner_id": owner,
                                           "projection": native_history._plain(data)})
                        return sorted(output, key=lambda item:
                            (item["role"], item["owner_id"] or ""))
                    with patch("native_history._stable_recipients", legacy_recipients), \
                            patch("native_history._merge_recipient_rows",
                                  side_effect=lambda _old, touched: touched):
                        old_log = native_history.capture(encounter)
                    old_log = _legacy_initial_entity_anchor(old_log, encounter)
                    unsigned = {key: value for key, value in old_log.items()
                                if key != "sha256"}
                    unsigned["schema"] = native_history.RECIPIENT_HISTORY_SCHEMA
                    unsigned["initial"].pop("initial_entities_available")
                    old_log = native_history._seal(unsigned)
                    upgraded = native_history.upgrade(old_log)
                    upgraded_query = native_history.NativeHistoryQuery(upgraded)
                    self.assertTrue(upgraded["initial"]["initial_schedule_available"])
                    for boundary in range(encounter.last_processed_boundary + 1):
                        self.assertEqual(
                            native_history._without_recipient_binding_ids(
                                upgraded_query.observer_facts_at(
                                    boundary, action.actor_id)),
                            native_history._without_recipient_binding_ids(
                                query.observer_facts_at(
                                    boundary, action.actor_id)))
                    corrupted = native_history.decode(native_history.encode(upgraded))
                    expanded = native_history._expand_rows(corrupted)
                    state = native_history._initial_state(corrupted["initial"])
                    for row_value in expanded:
                        state = upgraded_query.state_at(row_value["boundary"])
                        if state["recipients"]:
                            state["recipients"][0]["owner_id"] = "forged-listener"
                            state["recipients"][0]["projection"]["listener_id"] = "forged-listener"
                        row_value["changes"] = native_history._diff(
                            native_history._initial_state(corrupted["initial"])
                            if row_value["boundary"] == 1 else previous_corrupt_state,
                            state)
                        row_value["state_sha256"] = hashlib.sha256(
                            native_history._canonical(state)).hexdigest()
                        previous_corrupt_state = state
                    unsigned = {key: value for key, value in corrupted.items()
                                if key not in ("sha256", "boundaries")}
                    unsigned["boundaries"] = expanded
                    with self.assertRaisesRegex(
                            native_history.NativeHistoryRejected,
                            "native recipient owner or projection is malformed"):
                        native_history.validate(native_history._seal(unsigned))
                output.append([encounter.time, action.resolution.outcome,
                    observations, facts, historical_facts, rng.state,
                    hashlib.sha256(native_history.encode(
                        native_history.capture(encounter))).hexdigest()])
            return output

        expected = expected_projection()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'native-mixed-recipients.json'
            path.write_bytes(wire)
            child = r'''import hashlib,json,sys
import native_history
from activities import DelayAction
from encounter import Encounter
from native_persistence import load_path,rng_owner_for
world,selected,_rng=load_path(sys.argv[1])
encounters={event.id:event for event in world.event_history.values()
 if type(event) is Encounter}
output=[]
for index in range(3):
 enc=encounters[f'native-mixed-encounter-{index}']
 action=world.get_event_by_id(sys.argv[index+2])
 ledger=(action.object_ledger if index==0 else action.location_ledger) if index<2 else action.received_accounts
 while enc.time<6: enc.step(1)
 # Every native owner-filtered historical projection matches the receipts
 # after restoration, at each cut rather than only the selected 0/1/6 cuts.
 log=native_history.capture(enc)
 query=native_history.NativeHistoryQuery(log)
 assert query.state_at(0)['recipients']=={}
 for boundary in range(1,log['latest_boundary']+1):
  expected=native_history._stable_recipients(
   enc.inspect_committed(boundary).recipients,enc)
  assert query.state_at(boundary)['recipients']==expected
  owners=set(enc.being_list)|{row['owner_id'] for row in expected
   if row['owner_id'] is not None}
  for owner in owners:
   assert query.observer_facts_at(boundary,owner)==[row for row in expected
    if row['owner_id']==owner]
 if index<2:
  observations=[[o.id,o.observer_id,getattr(o,'object_id',None),
   getattr(o,'being_id',None),o.source_action_id,o.encounter_id,o.boundary,
   o.time,list(o.position.as_tuple()),o.basis] for o in ledger.observations]
  facts=native_history.NativeHistoryQuery(native_history.capture(enc)).observer_facts_at(
   enc.last_processed_boundary,action.actor_id)
 else:
  observations=ledger[0].to_dict()
  facts=world.get_object_by_id(action.target_id).personal_history.to_jsonable()
 query=native_history.NativeHistoryQuery(native_history.capture(enc))
 historical_facts=[query.observer_facts_at(boundary,action.actor_id)
  for boundary in (0,1,6)]
 output.append([enc.time,action.resolution.outcome,observations,facts,historical_facts,
  rng_owner_for(enc).state,hashlib.sha256(native_history.encode(
   native_history.capture(enc))).hexdigest()])
print(json.dumps(output,sort_keys=True))'''
            result = subprocess.run(
                [sys.executable, '-B', '-c', child, str(path),
                 *(row[2].id for row in rows)], cwd=ROOT,
                env={**os.environ,
                     'PYTHONPATH': f'{ROOT / "src"}:{ROOT / "examples"}'},
                text=True, capture_output=True, check=False, timeout=90)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout),
                         json.loads(json.dumps(expected)))

    def test_native_save_is_self_contained_for_shared_library_definitions(self):
        """Fresh Load uses the bundled Library, not files from its old path."""
        import os
        from native_scenario import NativeScenarioBuilder

        builder = NativeScenarioBuilder(
            'native-portable-definitions',
            Library(config_dir=str(ROOT / 'src/config')),
            seed=74, encounter_id='native-portable-definitions-encounter')
        actor = builder.add_being('Human', 'Portable-definition Being')
        weapon = builder.make_weapon(
            actor.id, 'Dagger', 'Portable-definition Dagger',
            hand='right hand', participant=True)
        armor_id = builder.world.make_armor_for_being(
            actor.id, 'Gauntlet', 'Portable-definition armor')
        scenery_id = builder.world.make_object(
            'Linen pillow', 'Portable-definition Object')
        builder.encounter.add_object(scenery_id)
        armor = builder.world.get_object_by_id(armor_id)
        scenery = builder.world.get_object_by_id(scenery_id)
        action_definition = builder.world.library.get_action_definition(
            'break weapon (armed)')
        skill_definition = builder.world.library.get_skill_definition(
            'unarmed combat')
        builder.enable()
        pending = DelayAction(builder.encounter, actor.id, defense=0,
                              start_time=builder.encounter.time,
                              id='native-portable-definitions-delay')
        builder.schedule(pending)
        wire = export_save(builder.encounter)

        self.assertIs(actor.original,
                      builder.world.library.get_being_definition('Human'))
        self.assertIs(weapon.original,
                      builder.world.library.get_weapon_definition('Dagger'))
        self.assertIs(armor.original,
                      builder.world.library.get_armor_definition('Gauntlet'))
        self.assertIs(scenery.original,
                      builder.world.library.get_object_definition('Linen pillow'))
        self.assertIsNotNone(action_definition)
        self.assertIsNotNone(skill_definition)
        self.assertIs(builder.world.get_skill_definition('unarmed combat'),
                      skill_definition)
        builder.step(1)
        expected = {
            'changed_nodes': [],
            'shared_actor_definition': True,
            'shared_weapon_definition': True,
            'shared_armor_definition': True,
            'shared_object_definition': True,
            'shared_action_definition': True,
            'shared_skill_definition': True,
            'time': builder.encounter.time,
            'outcome': pending.resolution.outcome,
            'action_id': pending.id,
            'rng': builder.rng.state,
            'history': hashlib.sha256(native_history.encode(
                native_history.capture(builder.encounter))).hexdigest(),
        }
        child = r'''import hashlib,json,sys
import base64
import native_history
from native_persistence import load_path,rng_owner_for,export_save
from native_graph_snapshot import decode as decode_graph
# The restored graph must contain definitions without consulting source config.
import builtins,io
from pathlib import Path
config_root=Path(sys.argv[2]).resolve()
original_open=builtins.open;original_io_open=io.open
def guarded_open(path,*args,**kwargs):
 try: selected=Path(path).resolve()
 except (TypeError,ValueError): selected=None
 if selected==config_root or (selected is not None and config_root in selected.parents):
  raise AssertionError('native Load consulted an external Library definition file')
 return original_open(path,*args,**kwargs)
def guarded_io_open(path,*args,**kwargs):
 try: selected=Path(path).resolve()
 except (TypeError,ValueError): selected=None
 if selected==config_root or (selected is not None and config_root in selected.parents):
  raise AssertionError('native Load consulted an external Library definition file')
 return original_io_open(path,*args,**kwargs)
builtins.open=guarded_open;io.open=guarded_io_open
world,enc,rng=load_path(sys.argv[1])
actor=world.get_object_by_id(sys.argv[3]);weapon=world.get_object_by_id(sys.argv[4])
armor=world.get_object_by_id(sys.argv[6]);scenery=world.get_object_by_id(sys.argv[7])
action_definition=world.library.get_action_definition('break weapon (armed)')
skill_definition=world.library.get_skill_definition('unarmed combat')
assert actor.original is world.library.get_being_definition('Human')
assert weapon.original is world.library.get_weapon_definition('Dagger')
assert armor.original is world.library.get_armor_definition('Gauntlet')
assert scenery.original is world.library.get_object_definition('Linen pillow')
assert action_definition is world.library.action_dictionary.get_action_definition('break weapon (armed)')
assert skill_definition is world.library.get_skill_definition('unarmed combat')
assert skill_definition is world.library.skill_dictionary.get_skill_definition('unarmed combat')
assert skill_definition is world.get_skill_definition('unarmed combat')
original_save=open(sys.argv[1],'rb').read()
resaved=export_save(enc)
original_value=json.loads(original_save);resaved_value=json.loads(resaved)
def graph_nodes(value):
 envelope=decode_graph(base64.b64decode(value['graph_b64']),native=True)
 rows=next(section[1] for section in envelope[1][1:] if section[0]=='nodes')
 return {row[0]:row[1:] for row in rows}
before=graph_nodes(original_value);after=graph_nodes(resaved_value)
changed_nodes=[[repr(ref), before.get(ref,(None,None))[0],
 after.get(ref,(None,None))[0]] for ref in
 sorted(set(before)|set(after),key=repr) if before.get(ref)!=after.get(ref)]
choice=enc.choice_for_action(sys.argv[5])
action=next(member.action for member in enc._choice_book._choices[choice.id].members
 if member.action.id==sys.argv[5])
assert choice.state=='accepted'
enc.step(1)
print(json.dumps({'changed_nodes':changed_nodes,
 'shared_actor_definition':actor.original is world.library.get_being_definition('Human'),
 'shared_weapon_definition':weapon.original is world.library.get_weapon_definition('Dagger'),
 'shared_armor_definition':armor.original is world.library.get_armor_definition('Gauntlet'),
 'shared_object_definition':scenery.original is world.library.get_object_definition('Linen pillow'),
 'shared_action_definition':action_definition is world.library.action_dictionary.get_action_definition('break weapon (armed)'),
 'shared_skill_definition':skill_definition is world.library.get_skill_definition('unarmed combat'),
 'time':enc.time,'outcome':action.resolution.outcome,'action_id':action.id,
 'rng':rng_owner_for(enc).state,
 'history':hashlib.sha256(native_history.encode(native_history.capture(enc))).hexdigest()},
 sort_keys=True))'''
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'native-self-contained-definitions.json'
            path.write_bytes(wire)
            result = subprocess.run(
                [sys.executable, '-B', '-c', child, str(path),
                 str(ROOT / 'src/config'), actor.id, weapon.id, pending.id,
                 armor.id, scenery.id], cwd=directory,
                env={**os.environ,
                     'PYTHONPATH': f'{ROOT / "src"}:{ROOT / "examples"}'},
                text=True, capture_output=True, check=False, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout),
                         json.loads(json.dumps(expected)))

    def test_logical_reproduction_native_being_binding_restores_by_object_identity(self):
        world = Universe('native-reproduction-binding', library=Library(
            config_dir=str(ROOT / 'src/config')))
        world.publish_reproduction_group(prepare_reproduction_group(
            ReproductionGroupProposal('RG-BINDING', ('P1', 'P2'), ('C1',),
                                      'native-save:binding')),
            request_key='native-binding-create', expected_revision=0)
        world.publish_reproduction_group(prepare_reproduction_group(
            ReproductionGroupProposal('RG-BINDING-ALIAS', ('P1',), ('C2',),
                                      'native-save:alias', parents_complete=False)),
            request_key='native-binding-alias-create', expected_revision=1)
        world.resolve_reproduction_group_elaboration(
            ReproductionGroupElaborationProposal(
                'RG-BINDING-ALIAS', ('P1',), ('P2',), True),
            request_key='native-binding-alias-complete', expected_revision=2)
        reproduction_revision = world.reproduction_group_snapshot().revision
        definition = BeingDefinition(
            obj_type='Native reproduction fixture', length=1.8, weight=70,
            hit_points=12, hit_dice='1d8', alignment='Neutral',
            armor_class=10, challenge_rating=0)
        being = materialize_reproductive_offspring(
            world, 'C1', being_definition=definition, name='Child',
            request_key='native-binding-materialize',
            expected_revision=reproduction_revision)
        from encounter import Encounter
        encounter = Encounter(world, 10, 0, initiated=True,
                              id='native-reproduction-binding-encounter')
        encounter.add_being(being.id)
        world.add_event(encounter)
        rng = RNGCursor(__import__('random').Random(92).getstate())
        encounter.enable_transactional_progression(quiescent=True, rng_owner=rng)
        initial = DelayAction(encounter, being.id, defense=0, start_time=0,
                              id='native-reproduction-binding-initial')
        encounter.schedule_action(initial)
        encounter.step(1)
        wire = export_save(encounter)
        continued = DelayAction(encounter, being.id, defense=0, start_time=1,
                                id='native-reproduction-binding-continuation')
        encounter.schedule_action(continued)
        encounter.step(1)
        expected = {
            'being_id': being.id,
            'name': being.name,
            'request': 'native-binding-materialize',
            'revision': world.reproduction_group_snapshot().revision,
            'time': encounter.time,
            'rng': rng.state,
            'outcome': continued.resolution.outcome,
            'history': hashlib.sha256(native_history.encode(
                native_history.capture(encounter))).hexdigest(),
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'native-reproduction-binding-save.json'
            path.write_bytes(wire)
            child = r'''import hashlib,json,sys
import native_history
from activities import DelayAction
from being import BeingDefinition
from native_persistence import export_save,load_path
world,enc,rng=load_path(sys.argv[1])
assert enc.id=='native-reproduction-binding-encounter'
assert export_save(enc)==open(sys.argv[1],'rb').read()
registry=world._reproduction_group_registry
being=world.get_object_by_id('C1')
record=registry._native_being_requests['native-binding-materialize']
assert registry._native_beings_by_person_id['C1'] is being
assert record.being is being and record.person_id == 'C1'
assert world.canonical_reproduction_group_id('RG-BINDING-ALIAS')=='RG-BINDING'
assert world.get_reproduction_group('RG-BINDING-ALIAS') is world.get_reproduction_group('RG-BINDING')
assert world.get_reproduction_group('RG-BINDING').offspring_ids == ('C1','C2')
definition=BeingDefinition(obj_type='Native reproduction fixture',length=1.8,
 weight=70,hit_points=12,hit_dice='1d8',alignment='Neutral',
 armor_class=10,challenge_rating=0)
from reproduction_being_bridge import materialize_reproductive_offspring
assert materialize_reproductive_offspring(world,'C1',being_definition=definition,
 name='Child',request_key='native-binding-materialize',
 expected_revision=3) is being
action=DelayAction(enc,being.id,defense=0,start_time=enc.time,
 id='native-reproduction-binding-continuation')
enc.schedule_action(action)
enc.step(1)
print(json.dumps({'being_id':being.id,'name':being.name,'request':record.request_key,
 'revision':world.reproduction_group_snapshot().revision,
 'time':enc.time,'rng':rng.state,'outcome':action.resolution.outcome,
 'history':hashlib.sha256(native_history.encode(native_history.capture(enc))).hexdigest()},sort_keys=True))'''
            import os
            result = subprocess.run(
                [sys.executable, '-B', '-c', child, str(path)], cwd=ROOT,
                env={**os.environ,
                     'PYTHONPATH': f'{ROOT / "src"}:{ROOT / "examples"}'},
                text=True, capture_output=True, check=False, timeout=45)
        self.assertEqual(result.returncode, 0, result.stderr)
        restored = json.loads(result.stdout)
        self.assertEqual(restored['being_id'], 'C1')
        self.assertEqual(restored['name'], 'Child')
        self.assertEqual(restored['request'], 'native-binding-materialize')
        self.assertEqual(restored, json.loads(json.dumps(expected)))

    def test_progressive_reproduction_history_restores_and_continues_in_fresh_process(self):
        import os
        import random
        from reproduction_generation import (
            ProgressiveReproductionRequest,
            TestOnlyIntervalReproductionProfile,
        )

        world = Universe('native-progressive-reproduction', library=Library(
            config_dir=str(ROOT / 'src/config')))
        profile = TestOnlyIntervalReproductionProfile(
            'native-persistence-progressive', '1', ((2, 1),))
        for target, key, revision in (
                (1, 'native-progressive-first', 0),
                (2, 'native-progressive-second', 1)):
            world.resolve_progressive_reproduction(
                ProgressiveReproductionRequest(('P1', 'P2'), 73, target, profile),
                request_key=key, expected_revision=revision)

        actor_id = world.make_being('Human', 'Progressive history runner')
        actor = world.get_object_by_id(actor_id)
        encounter = Encounter(world, 10, 0, initiated=True,
                              id='native-progressive-encounter')
        encounter.add_being(actor_id)
        world.add_event(encounter)
        rng = RNGCursor(random.Random(444).getstate())
        encounter.enable_transactional_progression(quiescent=True, rng_owner=rng)
        first = DelayAction(encounter, actor_id, defense=0, start_time=0,
                            id='native-progressive-initial')
        encounter.schedule_action(first)
        encounter.step(1)
        wire = export_save(encounter)

        def registry_projection(registry_world):
            snapshot = registry_world.reproduction_group_snapshot()
            history = snapshot.progressive_histories[0]
            group = next(row for row in snapshot.groups if row.group_id == history.group_id)
            return {
                'revision': snapshot.revision,
                'history': [list(history.parent_ids), history.world_seed,
                    history.profile_id, history.profile_version, history.profile_schema,
                    [list(row) for row in history.weighted_counts_per_period],
                    history.algorithm, history.scope_digest, history.through_period,
                    history.group_id,
                    [[row.period, row.count, list(row.offspring_ids)]
                     for row in history.periods], history.revision,
                    history.parent_global_history_complete],
                'group': [group.group_id, list(group.parent_ids),
                    list(group.offspring_ids), group.source_reference,
                    group.revision, group.parents_complete],
                'request_keys': list(snapshot.progressive_request_keys),
                'scope': [[list(parents), scope]
                          for parents, scope in snapshot.progressive_parent_set_scopes],
            }

        continued = DelayAction(encounter, actor_id, defense=0, start_time=1,
                                id='native-progressive-continuation')
        encounter.schedule_action(continued)
        encounter.step(1)
        expected = {
            'registry': registry_projection(world),
            'time': encounter.time,
            'outcome': continued.resolution.outcome,
            'rng': rng.state,
            'history': hashlib.sha256(native_history.encode(
                native_history.capture(encounter))).hexdigest(),
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'native-progressive-reproduction.json'
            path.write_bytes(wire)
            child = r'''import hashlib,json,sys
import native_history
from activities import DelayAction
from native_persistence import export_save,load_path
world,enc,rng=load_path(sys.argv[1])
assert enc.id=='native-progressive-encounter'
assert export_save(enc)==open(sys.argv[1],'rb').read()
snapshot=world.reproduction_group_snapshot();history=snapshot.progressive_histories[0]
group=next(row for row in snapshot.groups if row.group_id==history.group_id)
registry={'revision':snapshot.revision,
 'history':[list(history.parent_ids),history.world_seed,history.profile_id,
  history.profile_version,history.profile_schema,
  [list(row) for row in history.weighted_counts_per_period],history.algorithm,
  history.scope_digest,history.through_period,history.group_id,
  [[row.period,row.count,list(row.offspring_ids)] for row in history.periods],
  history.revision,history.parent_global_history_complete],
 'group':[group.group_id,list(group.parent_ids),list(group.offspring_ids),
  group.source_reference,group.revision,group.parents_complete],
 'request_keys':list(snapshot.progressive_request_keys),
 'scope':[[list(parents),scope] for parents,scope in snapshot.progressive_parent_set_scopes]}
action=DelayAction(enc,enc.being_list[0],defense=0,start_time=enc.time,
 id='native-progressive-continuation')
enc.schedule_action(action);enc.step(1)
print(json.dumps({'registry':registry,'time':enc.time,
 'outcome':action.resolution.outcome,'rng':rng.state,
 'history':hashlib.sha256(native_history.encode(native_history.capture(enc))).hexdigest()},
 sort_keys=True))'''
            result = subprocess.run(
                [sys.executable, '-B', '-c', child, str(path)], cwd=directory,
                env={**os.environ,
                     'PYTHONPATH': f'{ROOT / "src"}:{ROOT / "examples"}'},
                text=True, capture_output=True, check=False, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout),
                         json.loads(json.dumps(expected)))

    def test_statistical_reproduction_outcomes_resume_with_positive_and_zero_results(self):
        import os
        import random
        from dataclasses import asdict
        from reproduction_generation import (
            StatisticalReproductionRequest,
            TestOnlyOffspringCountDistribution,
            prepare_statistical_reproduction,
        )

        world = Universe('native-statistical-reproduction', library=Library(
            config_dir=str(ROOT / 'src/config')))
        distribution = TestOnlyOffspringCountDistribution(
            'native-persistence-counts', '1', ((0, 1), (1, 2), (2, 3)))
        for parents, seed, request_key in (
                (('P-A', 'P-B'), 5, 'native-generation-positive'),
                (('P-ZERO',), 2, 'native-generation-zero')):
            request = StatisticalReproductionRequest(
                parents, seed, 8, (1, 3, 5, 8), distribution)
            candidate = prepare_statistical_reproduction(world, request)
            world.publish_statistical_reproduction(
                candidate, request_key=request_key,
                expected_revision=candidate.base_revision)

        actor_id = world.make_being('Human', 'Statistical history runner')
        encounter = Encounter(world, 10, 0, initiated=True,
                              id='native-statistical-reproduction-encounter')
        encounter.add_being(actor_id)
        world.add_event(encounter)
        rng = RNGCursor(random.Random(445).getstate())
        encounter.enable_transactional_progression(quiescent=True, rng_owner=rng)
        first = DelayAction(encounter, actor_id, defense=0, start_time=0,
                            id='native-statistical-reproduction-initial')
        encounter.schedule_action(first)
        encounter.step(1)
        wire = export_save(encounter)

        def registry_projection(registry_world):
            snapshot = registry_world.reproduction_group_snapshot()
            outcomes = []
            for row in snapshot.generation_outcomes:
                value = asdict(row)
                value.pop('world_identity')
                outcomes.append(value)
            groups = []
            for row in snapshot.groups:
                value = asdict(row)
                value.pop('world_identity')
                groups.append(value)
            return {
                'revision': snapshot.revision,
                'outcomes': outcomes,
                'groups': groups,
                'parent_scopes': [[list(parents), scope]
                                  for parents, scope in snapshot.generation_parent_set_scopes],
                'origin_ticks': [list(row) for row in snapshot.offspring_origin_ticks],
                'request_keys': list(snapshot.request_keys),
            }

        positive = world.reproduction_group_snapshot().generation_outcomes[0]
        zero = world.reproduction_group_snapshot().generation_outcomes[1]
        self.assertEqual(positive.count, 2)
        self.assertIsNotNone(positive.group_id)
        self.assertEqual(zero.count, 0)
        self.assertIsNone(zero.group_id)
        self.assertEqual(zero.offspring_ids, ())
        continued = DelayAction(encounter, actor_id, defense=0, start_time=1,
                                id='native-statistical-reproduction-continuation')
        encounter.schedule_action(continued)
        encounter.step(1)
        expected = {
            'registry': registry_projection(world),
            'time': encounter.time,
            'outcome': continued.resolution.outcome,
            'rng': rng.state,
            'history': hashlib.sha256(native_history.encode(
                native_history.capture(encounter))).hexdigest(),
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'native-statistical-reproduction.json'
            path.write_bytes(wire)
            child = r'''import hashlib,json,sys
from dataclasses import asdict
import native_history
from activities import DelayAction
from native_persistence import export_save,load_path
world,enc,rng=load_path(sys.argv[1])
assert enc.id=='native-statistical-reproduction-encounter'
assert export_save(enc)==open(sys.argv[1],'rb').read()
snapshot=world.reproduction_group_snapshot()
outcomes=[]
for row in snapshot.generation_outcomes:
 value=asdict(row);value.pop('world_identity');outcomes.append(value)
groups=[]
for row in snapshot.groups:
 value=asdict(row);value.pop('world_identity');groups.append(value)
registry={'revision':snapshot.revision,'outcomes':outcomes,'groups':groups,
 'parent_scopes':[[list(parents),scope] for parents,scope in snapshot.generation_parent_set_scopes],
 'origin_ticks':[list(row) for row in snapshot.offspring_origin_ticks],
 'request_keys':list(snapshot.request_keys)}
assert outcomes[0]['count']==2 and outcomes[0]['group_id'] is not None
assert outcomes[1]['count']==0 and outcomes[1]['group_id'] is None
assert outcomes[1]['offspring_ids']==()
action=DelayAction(enc,enc.being_list[0],defense=0,start_time=enc.time,
 id='native-statistical-reproduction-continuation')
enc.schedule_action(action);enc.step(1)
print(json.dumps({'registry':registry,'time':enc.time,
 'outcome':action.resolution.outcome,'rng':rng.state,
 'history':hashlib.sha256(native_history.encode(native_history.capture(enc))).hexdigest()},
 sort_keys=True))'''
            result = subprocess.run(
                [sys.executable, '-B', '-c', child, str(path)], cwd=directory,
                env={**os.environ,
                     'PYTHONPATH': f'{ROOT / "src"}:{ROOT / "examples"}'},
                text=True, capture_output=True, check=False, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout),
                         json.loads(json.dumps(expected)))

    def test_completed_ask_about_past_and_listener_accounts_resume_with_binding(self):
        world, encounter, rng, listener, speaker, _weapon_id = self._combat_encounter()
        from personal_history import PersonalHistory
        from realization import Fact
        from objective_reality import EpisodeFacts
        speaker.personal_history = PersonalHistory(
            speaker, earliest=-10, known_through=0, nondeclining_skills=())
        accounts = []
        key = speaker.personal_history.episode_key(-1, 'native-test')
        inquiry = AskAboutPastAction(
            world, listener.id, speaker.id, 0, episode_time=-1,
            topic='native-test', duration=1,
            generate=EpisodeFacts((Fact(
                key, {'description': 'practiced a native test'},
                origin='native-test'),)),
            received_accounts=accounts)
        encounter.schedule_action(inquiry)
        encounter.step(1)
        self.assertEqual(len(accounts), 1)
        self.assertEqual(accounts[0].words, 'practiced a native test')
        binding = RecipientBinding(
            world, 'history', 'listener-accounts', 'in_world_received_accounts',
            (listener.id,), accounts)
        boundary_binding_id = native_history.NativeHistoryQuery(
            native_history.capture(encounter)).state_at(1)['recipients'][0]['binding_id']
        from native_history import _recipient_binding_id
        self.assertEqual(boundary_binding_id, _recipient_binding_id(
            world, 'in_world_received_accounts', id(accounts)))
        wire = export_save(encounter, recipient_bindings=(binding,))
        # Present a valid prior /9 native Save: its receipt stores only the
        # touched recipient row and has no explicit row owner. The recorded
        # HeardAccount itself is sufficient to recover this listener.
        document = json.loads(wire)
        legacy_history = {key: value for key, value in document['history'].items()
                          if key != 'sha256'}
        legacy_history = _legacy_initial_entity_anchor(legacy_history, encounter)
        legacy_history['schema'] = native_history.RECIPIENT_HISTORY_SCHEMA
        legacy_history['initial'].pop('initial_entities_available')
        history_state = native_history._initial_state(legacy_history['initial'])
        for history_row in legacy_history['boundaries']:
            for change in history_row['changes']:
                if change['path'] != ['recipients'] or not change['after']:
                    continue
                for recipient in change['value']:
                    if recipient['role'] == 'in_world_received_accounts':
                        recipient['owner_id'] = None
                        recipient['projection'].pop('listener_id', None)
            history_state = native_history._apply(history_state, history_row['changes'])
            history_row['state_sha256'] = hashlib.sha256(
                native_history._canonical(history_state)).hexdigest()
        document['history'] = native_history._seal(legacy_history)
        unsigned_document = {key: value for key, value in document.items()
                             if key != 'sha256'}
        document['sha256'] = hashlib.sha256(
            native_persistence._canonical(unsigned_document)).hexdigest()
        wire = native_persistence._canonical(document)
        next_action = DelayAction(encounter, listener.id, defense=0,
                                  start_time=1, id='native-inquiry-continuation')
        encounter.schedule_action(next_action)
        encounter.step(1)
        original_query = native_history.NativeHistoryQuery(
            native_history.capture(encounter))
        history = {"boundaries": [
            {"state": original_query.state_at(boundary),
             "events": original_query.events_at(boundary),
             "context": original_query.entity_context_at(boundary)}
            for boundary in range(1, encounter.last_processed_boundary + 1)]}
        expected = {'time': encounter.time, 'rng': rng.state,
                    'history': history,
                    'account': accounts[0].to_dict()}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'native-ask-about-past-save.json'
            path.write_bytes(wire)
            child = r'''import hashlib,json,sys
import native_history
from activities import DelayAction
from native_persistence import load_path
world,enc,rng=load_path(sys.argv[1])
inquiry=next(a for a in world.event_history.values()
 if type(a).__name__=='AskAboutPastAction')
assert inquiry.generate is not None and len(inquiry.received_accounts)==1
query=native_history.NativeHistoryQuery(native_history.current_recording(enc))
facts=query.observer_facts_at(1,inquiry.actor_id)
assert len(facts)==1 and facts[0]['owner_id']==inquiry.actor_id
assert facts[0]['projection']['accounts']['$tuple'][0]['fields']['listener_id']==inquiry.actor_id
account=inquiry.received_accounts[0].to_dict()
action=DelayAction(enc,enc.being_list[0],defense=0,start_time=enc.time,
 id='native-inquiry-continuation')
enc.schedule_action(action)
enc.step(1)
log=native_history.current_recording(enc); q=native_history.NativeHistoryQuery(log)
history={'boundaries':[{'state':q.state_at(boundary),
 'events':q.events_at(boundary),'context':q.entity_context_at(boundary)}
 for boundary in range(1,enc.last_processed_boundary+1)]}
print(json.dumps({'time':enc.time,'rng':rng.state,
 'history':history,'initial_entities_available':log['initial']['initial_entities_available'],
 'account':account},sort_keys=True))'''
            import os
            result = subprocess.run(
                [sys.executable, '-B', '-c', child, str(path)], cwd=ROOT,
                env={**os.environ,
                     'PYTHONPATH': f'{ROOT / "src"}:{ROOT / "examples"}'},
                text=True, capture_output=True, check=False, timeout=45)
        self.assertEqual(result.returncode, 0, result.stderr)
        actual = json.loads(result.stdout)
        self.assertFalse(actual['initial_entities_available'])
        self.assertEqual(actual['time'], expected['time'])
        self.assertEqual(actual['rng'], json.loads(json.dumps(expected['rng'])))
        self.assertEqual(actual['history'], expected['history'])
        self.assertEqual(actual['account'], expected['account'])

    def test_shared_testimony_binding_restores_listener_aliases_without_cross_exposure(self):
        world, encounter, rng, first_listener, speaker, _weapon_id = self._combat_encounter()
        second_id = world.make_being('Human', 'Second Listener')
        second_listener = world.get_object_by_id(second_id)
        second_listener.set_position(CartesianPosition(-1.5, 0, 0))
        second_listener.set_geometry(Sphere(.25))
        second_listener.set_hit_points(100)
        encounter.add_being(second_listener.id)
        encounter.mark_aware(second_listener.id, speaker.id)
        from personal_history import PersonalHistory
        from realization import Fact
        from objective_reality import EpisodeFacts
        speaker.personal_history = PersonalHistory(
            speaker, earliest=-10, known_through=0, nondeclining_skills=())
        accounts = []
        first_key = speaker.personal_history.episode_key(-1, 'shared-native-first')
        second_key = speaker.personal_history.episode_key(-2, 'shared-native-second')
        first = AskAboutPastAction(world, first_listener.id, speaker.id, 0,
            episode_time=-1, topic='shared-native-first', received_accounts=accounts,
            generate=EpisodeFacts((Fact(first_key, {'description': 'first account'},
                                        origin='shared-native-test'),)))
        second = AskAboutPastAction(world, second_listener.id, speaker.id, 0,
            episode_time=-2, topic='shared-native-second', received_accounts=accounts,
            generate=EpisodeFacts((Fact(second_key, {'description': 'second account'},
                                        origin='shared-native-test'),)))
        encounter.schedule_choice((first, second))
        encounter.step(1)
        self.assertEqual((first.resolution.outcome, second.resolution.outcome),
                         ('heard', 'heard'))
        binding = RecipientBinding(world, 'history', 'shared-native-listeners',
            'in_world_received_accounts', (first_listener.id, second_listener.id), accounts)
        wire = export_save(encounter, recipient_bindings=(binding,))
        query = native_history.NativeHistoryQuery(native_history.capture(encounter))
        left = query.observer_facts_at(1, first_listener.id)
        right = query.observer_facts_at(1, second_listener.id)
        self.assertEqual(len(left), 1)
        self.assertEqual(len(right), 1)
        self.assertNotEqual(left, right)
        encounter.step(1)
        expected_digest = hashlib.sha256(native_history.encode(
            native_history.capture(encounter))).hexdigest()
        expected_rng = rng.state
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'native-shared-testimony-save.json'
            path.write_bytes(wire)
            child = r'''import hashlib,json,sys
import native_history
from native_persistence import load_path
world,enc,rng=load_path(sys.argv[1])
actions=[a for a in world.event_history.values()
 if type(a).__name__=='AskAboutPastAction']
assert len(actions)==2 and actions[0].received_accounts is actions[1].received_accounts
assert len(actions[0].received_accounts)==2
query=native_history.NativeHistoryQuery(native_history.current_recording(enc))
first=actions[0].actor_id; second=actions[1].actor_id
left=query.observer_facts_at(1,first); right=query.observer_facts_at(1,second)
assert len(left)==len(right)==1 and left!=right
assert left[0]['owner_id']==first and right[0]['owner_id']==second
enc.step(1)
query=native_history.NativeHistoryQuery(native_history.current_recording(enc))
assert query.observer_facts_at(2,first)==left
assert query.observer_facts_at(2,second)==right
print(json.dumps({'time':enc.time,'rng':rng.state,
 'history':hashlib.sha256(native_history.encode(native_history.capture(enc))).hexdigest()},sort_keys=True))'''
            import os
            result = subprocess.run([sys.executable, '-B', '-c', child, str(path)],
                cwd=ROOT, env={**os.environ,
                    'PYTHONPATH': f'{ROOT / "src"}:{ROOT / "examples"}'},
                text=True, capture_output=True, check=False, timeout=45)
        self.assertEqual(result.returncode, 0, result.stderr)
        actual = json.loads(result.stdout)
        self.assertEqual(actual['time'], encounter.time)
        self.assertEqual(actual['rng'], json.loads(json.dumps(expected_rng)))
        self.assertEqual(actual['history'], expected_digest)

    def test_spot_location_evidence_restores_with_owner_and_provenance(self):
        world, encounter, rng, observer, target, _weapon_id = self._combat_encounter()
        ledger = LocationEvidenceLedger(observer.id)
        spot = SpotAction(world, observer.id, target.id, 0, die_roll=20,
                          location_ledger=ledger, id='native-location-spot')
        encounter.schedule_action(spot)
        encounter.step(6)
        self.assertEqual(len(ledger.observations), 1)
        binding = RecipientBinding(
            world, 'perception', 'observer-location', 'observer_location_evidence',
            (observer.id,), ledger)
        wire = export_save(encounter, recipient_bindings=(binding,))
        continuation = DelayAction(encounter, observer.id, defense=0,
                                   start_time=6, id='native-location-continuation')
        encounter.schedule_action(continuation)
        encounter.step(1)
        row = ledger.observations[0]
        last_seen=ledger.last_seen_location(target.id)
        expected = {
            'time': encounter.time, 'rng': rng.state,
            'history': hashlib.sha256(native_history.encode(
                native_history.capture(encounter))).hexdigest(),
            'observation': [row.id, row.observer_id, row.being_id,
                            row.source_action_id, row.encounter_id, row.boundary,
                            row.time, list(row.position.as_tuple()), row.basis],
            'last_seen': [last_seen.observer_id,last_seen.being_id,
                          list(last_seen.position.as_tuple()),last_seen.observed_at,
                          last_seen.boundary,last_seen.source_action_id,
                          last_seen.observation_id],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'native-location-evidence-save.json'
            path.write_bytes(wire)
            child = r'''import hashlib,json,sys
import native_history
from activities import DelayAction
from native_persistence import load_path
world,enc,rng=load_path(sys.argv[1])
spot=world.get_event_by_id('native-location-spot')
ledger=spot.location_ledger
row=ledger.observations[0]
assert ledger.observer_id == spot.actor_id
assert row.source_action_id == spot.id and row.being_id == spot.target_id
last=ledger.last_seen_location(row.being_id)
assert last.observer_id==spot.actor_id and last.observation_id==row.id
action=DelayAction(enc,spot.actor_id,defense=0,start_time=enc.time,
 id='native-location-continuation')
enc.schedule_action(action)
enc.step(1)
print(json.dumps({'time':enc.time,'rng':rng.state,
 'history':hashlib.sha256(native_history.encode(native_history.capture(enc))).hexdigest(),
 'observation':[row.id,row.observer_id,row.being_id,row.source_action_id,
 row.encounter_id,row.boundary,row.time,list(row.position.as_tuple()),row.basis],
 'last_seen':[last.observer_id,last.being_id,list(last.position.as_tuple()),
 last.observed_at,last.boundary,last.source_action_id,last.observation_id]},sort_keys=True))'''
            import os
            result = subprocess.run(
                [sys.executable, '-B', '-c', child, str(path)], cwd=ROOT,
                env={**os.environ,
                     'PYTHONPATH': f'{ROOT / "src"}:{ROOT / "examples"}'},
                text=True, capture_output=True, check=False, timeout=45)
        self.assertEqual(result.returncode, 0, result.stderr)
        actual = json.loads(result.stdout)
        self.assertEqual(actual['time'], expected['time'])
        self.assertEqual(actual['rng'], json.loads(json.dumps(expected['rng'])))
        self.assertEqual(actual['history'], expected['history'])
        self.assertEqual(actual['observation'], expected['observation'])

    def test_object_spot_ledgers_restore_distinct_evidence_and_projectile_continuation(self):
        from native_throw_spot import build_spot_scene
        scene = build_spot_scene(seed=5)
        world, encounter, rng = scene['world'], scene['encounter'], scene['rng']
        encounter.step(6)
        self.assertEqual(len(scene['spotter_evidence'].observations), 1)
        self.assertEqual(scene['second_evidence'].observations, ())
        bindings = tuple(RecipientBinding(
            world, 'object-evidence', name, 'observer_object_evidence',
            (ledger.observer_id,), ledger)
            for name, ledger in (('spotter', scene['spotter_evidence']),
                                 ('second', scene['second_evidence'])))
        wire = export_save(encounter, recipient_bindings=bindings)
        encounter.step(1)
        observation = scene['spotter_evidence'].observations[0]
        expected = {
            'time': encounter.time, 'rng': rng.state,
            'history': hashlib.sha256(native_history.encode(
                native_history.capture(encounter))).hexdigest(),
            'observation': [observation.id, observation.observer_id,
                            observation.object_id, observation.source_action_id,
                            observation.encounter_id, observation.boundary,
                            observation.time, list(observation.position.as_tuple()),
                            observation.projectile_status, observation.basis],
            'flight': scene['projectile'].__dict__['_projectile_flight'].status,
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'native-object-observation-save.json'
            path.write_bytes(wire)
            child = r'''import hashlib,json,sys
import native_history
from native_persistence import load_path
world,enc,rng=load_path(sys.argv[1])
spot=world.get_event_by_id('throw-demo/spotter-object-spot')
second=world.get_event_by_id('throw-demo/second-observer-object-spot')
assert len(spot.object_ledger.observations)==1
assert second.object_ledger.observations==()
observation=spot.object_ledger.observations[0]
enc.step(1)
projectile=world.get_object_by_id(observation.object_id)
flight=projectile.__dict__['_projectile_flight'].status
print(json.dumps({'time':enc.time,'rng':rng.state,
 'history':hashlib.sha256(native_history.encode(native_history.capture(enc))).hexdigest(),
 'observation':[observation.id,observation.observer_id,observation.object_id,
 observation.source_action_id,observation.encounter_id,observation.boundary,
 observation.time,list(observation.position.as_tuple()),
 observation.projectile_status,observation.basis], 'flight':flight},sort_keys=True))'''
            import os
            result = subprocess.run(
                [sys.executable, '-B', '-c', child, str(path)], cwd=ROOT,
                env={**os.environ,
                     'PYTHONPATH': f'{ROOT / "src"}:{ROOT / "examples"}'},
                text=True, capture_output=True, check=False, timeout=45)
        self.assertEqual(result.returncode, 0, result.stderr)
        actual = json.loads(result.stdout)
        self.assertEqual(actual['time'], expected['time'])
        self.assertEqual(actual['rng'], json.loads(json.dumps(expected['rng'])))
        self.assertEqual(actual['history'], expected['history'])
        self.assertEqual(actual['observation'], expected['observation'])
        self.assertEqual(actual['flight'], expected['flight'])

    def test_native_search_success_and_listen_failure_resume_with_exact_history(self):
        world, encounter, rng, observer, target, _weapon_id = self._combat_encounter()
        target.current.tags['arena_search_accessible'] = True
        target.current.tags['arena_audible'] = True
        search = SpotAction(world, observer.id, target.id, 0, die_roll=20,
                            sense='search', id='native-search-success')
        encounter.schedule_action(search)
        encounter.step(6)
        self.assertEqual(search.resolution.outcome, 'success')
        self.assertTrue(encounter.is_aware(observer.id, target.id))
        listen = SpotAction(world, observer.id, target.id, 6, die_roll=1,
                            sense='listen', id='native-listen-failure')
        encounter.schedule_action(listen)
        wire = export_save(encounter)
        self.assertEqual(native_history.current_recording(encounter)['latest_boundary'], 6)
        encounter.step(6)
        self.assertEqual(native_history.current_recording(encounter)['latest_boundary'], 12)
        expected = {
            'time': encounter.time, 'rng': rng.state,
            'history': hashlib.sha256(native_history.encode(
                native_history.capture(encounter))).hexdigest(),
            'outcomes': [search.resolution.outcome, listen.resolution.outcome],
            'awareness': encounter.is_aware(observer.id, target.id),
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'native-search-listen-save.json'
            path.write_bytes(wire)
            child = r'''import hashlib,json,sys
import native_history
from native_persistence import load_path,export_save
from native_history import current_recording
world,enc,rng=load_path(sys.argv[1])
assert export_save(enc)==open(sys.argv[1],'rb').read()
search=world.get_event_by_id('native-search-success')
choice=next(row for row in enc._choice_book._choices.values()
 if row.view.action_ids==('native-listen-failure',))
listen=choice.members[0].action
assert search.resolution.outcome=='success'
assert listen.resolution is None
enc.step(6)
recorded=current_recording(enc)
assert recorded['latest_boundary']==enc.last_processed_boundary
resaved=json.loads(export_save(enc))
assert resaved['history']==recorded
print(json.dumps({'time':enc.time,'rng':rng.state,
 'history':hashlib.sha256(native_history.encode(native_history.capture(enc))).hexdigest(),
 'outcomes':[search.resolution.outcome,listen.resolution.outcome],
 'awareness':enc.is_aware(search.actor_id,search.target_id)},sort_keys=True))'''
            import os
            result = subprocess.run(
                [sys.executable, '-B', '-c', child, str(path)], cwd=ROOT,
                env={**os.environ,
                     'PYTHONPATH': f'{ROOT / "src"}:{ROOT / "examples"}'},
                text=True, capture_output=True, check=False, timeout=45)
        self.assertEqual(result.returncode, 0, result.stderr)
        actual = json.loads(result.stdout)
        self.assertEqual(actual['time'], expected['time'])
        self.assertEqual(actual['rng'], json.loads(json.dumps(expected['rng'])))
        self.assertEqual(actual['history'], expected['history'])
        self.assertEqual(actual['outcomes'], expected['outcomes'])
        self.assertEqual(actual['awareness'], expected['awareness'])

    def test_simultaneous_native_melee_batch_restores_causal_effects_and_continues(self):
        from melee_combat import MeleeStrike, effective_melee_reach_meters
        world, encounter, rng, first, second, first_weapon_id = self._combat_encounter()
        victim_id = world.make_being('Human', 'Native Batch Victim')
        victim = world.get_object_by_id(victim_id)
        victim.set_position(CartesianPosition(.4, 0, 0))
        victim.set_geometry(Sphere(.25))
        victim.set_hit_points(100)
        encounter.add_being(victim_id)
        encounter.mark_aware(first.id, victim_id)
        encounter.mark_aware(second.id, victim_id)
        second_weapon_id = world.make_weapon_for_being(second.id, 'Dagger',
                                                       'Native Batch Dagger')
        world.arm_being(second.id, second_weapon_id, 'right hand')
        first.current.skills.weapon_skills['Dagger'] = 3
        second.current.skills.weapon_skills['Dagger'] = 3
        first_reach = effective_melee_reach_meters(
            first.current, world.get_object_by_id(first_weapon_id).current)
        second_reach = effective_melee_reach_meters(
            second.current, world.get_object_by_id(second_weapon_id).current)
        strikes = (
            MeleeStrike(encounter, first.id, victim_id, first_weapon_id,
                        motion='thrust', reach=max(2.0, first_reach)),
            MeleeStrike(encounter, second.id, victim_id, second_weapon_id,
                        motion='thrust', reach=max(2.0, second_reach)),
        )
        encounter.schedule_choice(strikes)
        encounter.step(max(action.end_time for action in strikes))
        receipt = next(row for row in reversed(encounter._atomic_interval_history)
                       if len(row.action_ids) == 2)
        self.assertEqual(len(receipt.action_ids), 2)
        self.assertTrue(receipt.effect_ids)
        self.assertLess(victim.get_hit_points(), 100)
        wire = export_save(encounter)
        encounter.schedule_action(DelayAction(
            encounter, first.id, defense=0, start_time=encounter.time,
            id='native-batch-continuation'))
        encounter.step(1)
        expected = {
            'time': encounter.time, 'rng': rng.state,
            'hp': victim.get_hit_points(),
            'history': hashlib.sha256(native_history.encode(
                native_history.capture(encounter))).hexdigest(),
            'actions': list(receipt.action_ids),
            'effects': [str(identity) for identity in receipt.effect_ids],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'native-simultaneous-melee-save.json'
            path.write_bytes(wire)
            child = r'''import hashlib,json,sys
import native_history
from activities import DelayAction
from native_persistence import load_path
world,enc,rng=load_path(sys.argv[1])
victim=world.get_object_by_id(sys.argv[2])
receipt=next(row for row in reversed(enc._atomic_interval_history)
 if len(row.action_ids)==2)
assert len(receipt.action_ids)==2
assert victim.get_hit_points()<100
actor=world.get_event_by_id(receipt.action_ids[0]).actor_id
enc.schedule_action(DelayAction(enc,actor,defense=0,
 start_time=enc.time,id='native-batch-continuation'))
enc.step(1)
print(json.dumps({'time':enc.time,'rng':rng.state,'hp':victim.get_hit_points(),
 'history':hashlib.sha256(native_history.encode(native_history.capture(enc))).hexdigest(),
 'actions':list(receipt.action_ids),
 'effects':[str(identity) for identity in receipt.effect_ids]},sort_keys=True))'''
            import os
            result = subprocess.run(
                [sys.executable, '-B', '-c', child, str(path), victim_id], cwd=ROOT,
                env={**os.environ,
                     'PYTHONPATH': f'{ROOT / "src"}:{ROOT / "examples"}'},
                text=True, capture_output=True, check=False, timeout=45)
        self.assertEqual(result.returncode, 0, result.stderr)
        actual = json.loads(result.stdout)
        self.assertEqual(actual['time'], expected['time'])
        self.assertEqual(actual['rng'], json.loads(json.dumps(expected['rng'])))
        self.assertEqual(actual['hp'], expected['hp'])
        self.assertEqual(actual['history'], expected['history'])
        self.assertEqual(actual['actions'], expected['actions'])
        self.assertEqual(actual['effects'], expected['effects'])

    def test_simultaneous_three_being_wrest_coholding_restores_and_continues(self):
        """Native Save retains one Object identity shared by concurrent holders."""
        from action import Action
        from physical_contact import shared_object_holders
        from native_scenario import NativeScenarioBuilder
        from action_evaluation import _ProvisionalRandom, RandomDraw
        from unittest.mock import patch
        builder = NativeScenarioBuilder(
            'Native simultaneous co-holding',
            Library(config_dir=str(ROOT / 'src/config')), seed=17)
        actor = builder.add_being('Human', 'First challenger',
            position=(0, 0, 0), radius=.1, hit_points=100)
        holder = builder.add_being('Human', 'Object holder',
            position=(.3, 0, 0), radius=.1, hit_points=100)
        third = builder.add_being('Human', 'Second challenger',
            position=(.3, .3, 0), radius=.1, hit_points=100)
        world, encounter = builder.world, builder.encounter
        for being in (actor, holder, third):
            being.size_category = 'medium'
            being.set_posture('standing')
            for other in (actor, holder, third):
                if other.id != being.id:
                    encounter.mark_aware(being.id, other.id)
        obj = builder.make_weapon(holder.id, 'Dagger', 'One shared Dagger')
        object_id = obj.id
        builder.arm(holder.id, object_id, 'right hand')
        obj.parent_container_id = holder.id
        builder.add_object(object_id)
        builder.mark_aware(actor.id, object_id)
        builder.mark_aware(holder.id, object_id)
        builder.mark_aware(third.id, object_id)
        builder.enable()

        def scripted_step(rolls):
            values = iter(rolls)
            def scripted(context, dice):
                value = next(values)
                context.trace.append(RandomDraw(
                    context.action_id, dice, int(dice[2:].split('+')[0]), value))
                return value
            with patch.object(_ProvisionalRandom, 'roll', scripted):
                encounter.step(1)

        actor.current.abilities.abilities['STR'] = 30
        third.current.abilities.abilities['STR'] = 30
        holder.current.abilities.abilities['STR'] = 3

        grabs = []
        for challenger in (actor, third):
            grab = Action(world, 0, 1, 'grab object', challenger.id,
                          object_id, None)
            grab.holder_id = holder.id
            grab.holder_hand = 'right hand'
            grab.grab_hand = 'left hand'
            grabs.append(grab)
        encounter.schedule_choice(tuple(grabs))
        scripted_step([20, 20])
        grips = __import__('physical_contact').active_object_grip_state(encounter)
        grip_by_actor = {row[2]: row for row in grips}
        wrests = []
        for challenger in (actor, third):
            wrest = Action(world, 2, 3, 'wrest', challenger.id,
                           object_id, None)
            wrest.holder_id = holder.id
            wrest.holder_hand = 'right hand'
            wrest.grab_hand = 'left hand'
            wrest.object_grip_id = grip_by_actor[challenger.id][1]
            wrests.append(wrest)
        encounter.schedule_choice(tuple(wrests))
        encounter.step(1)  # Activate the simultaneous contests at their common fence.
        scripted_step([6, 6, 6, 1, 1, 1, 6, 6, 6, 1, 1, 1])
        self.assertEqual([row.resolution.outcome for row in wrests],
                         ['success', 'success'])
        self.assertEqual(set(shared_object_holders(encounter, object_id)),
                         {(actor.id, 'left hand'), (third.id, 'left hand')})

        wire = export_save(encounter)
        actor_id, third_id = actor.id, third.id
        from transactional_progression import _BINDINGS
        rng_owner = _BINDINGS[id(encounter)].rng_owner
        def rng_digest(owner):
            return hashlib.sha256(json.dumps(owner.state).encode()).hexdigest()
        delay_id = 'native-coholding-continuation'
        encounter.schedule_action(DelayAction(
            encounter, actor_id, defense=0, start_time=encounter.time,
            id=delay_id))
        encounter.step(1)
        expected = {
            'time': encounter.time,
            'rng': rng_digest(rng_owner),
            'history': hashlib.sha256(native_history.encode(
                native_history.capture(encounter))).hexdigest(),
            'holders': [[identity, 'left hand']
                        for identity in sorted((actor_id, third_id))],
            'action_ids': sorted(row.id for row in wrests),
            'object_id': object_id,
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'native-coholding.json'
            path.write_bytes(wire)
            child = r'''import hashlib,json,sys
import native_history
from activities import DelayAction
from native_persistence import load_path
from physical_contact import shared_object_holders
def rng_digest(rng): return hashlib.sha256(json.dumps(rng.state).encode()).hexdigest()
world,enc,rng=load_path(sys.argv[1])
oid,actor,third,delay=sys.argv[2:]
holders=[list(row) for row in shared_object_holders(enc,oid)]
assert holders==[[identity,'left hand'] for identity in sorted((actor,third))]
obj=world.get_object_by_id(oid)
assert obj.id==oid and obj.parent_container_id==min(actor,third)
assert sum(world.get_object_by_id(x).current.body_parts.get('left hand')==oid
 for x in enc.being_list)==2
actions=[world.get_event_by_id(x) for x in enc.finished_action_list
 if getattr(world.get_event_by_id(x),'event_type',None)=='wrest']
assert len(actions)==2 and all(row.resolution.outcome=='success' for row in actions)
enc.schedule_action(DelayAction(enc,actor,defense=0,start_time=enc.time,id=delay))
enc.step(1)
print(json.dumps({'time':enc.time,'rng':rng_digest(rng),
 'history':hashlib.sha256(native_history.encode(native_history.capture(enc))).hexdigest(),
 'holders':holders,'action_ids':sorted(row.id for row in actions),'object_id':obj.id},sort_keys=True))'''
            import os
            result = subprocess.run(
                [sys.executable, '-B', '-c', child, str(path), object_id,
                 actor_id, third_id, delay_id], cwd=ROOT,
                env={**os.environ, 'PYTHONPATH': f'{ROOT / "src"}:{ROOT / "examples"}'},
                text=True, capture_output=True, check=False, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), expected)

    def test_pending_disarm_landing_choice_restores_and_commits_same_weapon(self):
        """A post-roll landing Choice remains actionable after native restore."""
        from action import Action
        from action_evaluation import _ProvisionalRandom, RandomDraw
        from arena_hex_map import ArenaHexLayout, HexAddress, encounter_map_descriptor
        from atomic_publication import disarm_landing_options, choose_disarm_landing
        from melee_combat import effective_melee_reach_meters
        from native_scenario import NativeScenarioBuilder
        from unittest.mock import patch
        builder = NativeScenarioBuilder(
            'Native Disarm landing continuation',
            Library(config_dir=str(ROOT / 'src/config')), seed=41)
        attacker = builder.add_being('Human', 'Disarmer', radius=.25,
            hit_points=100)
        defender = builder.add_being('Human', 'Weapon holder', radius=.25,
            hit_points=100)
        world, encounter = builder.world, builder.encounter
        layout = ArenaHexLayout.rectangle(10, 10)
        encounter.map = encounter_map_descriptor(layout)
        source = layout.center_position(HexAddress(5, 5))
        target = layout.center_position(HexAddress(6, 5))
        attacker.set_position(source)
        defender.set_position(target)
        from hex_facing import nearest_facing
        attacker.set_hex_facing(nearest_facing(
            (target.x-source.x, target.y-source.y, 0.0)))
        defender.set_hex_facing(6)
        for being in (attacker, defender):
            being.set_posture('standing')
            being.size_category = 'medium'
        builder.mark_aware(attacker.id, defender.id)
        builder.mark_aware(defender.id, attacker.id)
        instrument = builder.make_weapon(attacker.id, 'Dagger', 'Disarming Dagger')
        target_weapon = builder.make_weapon(defender.id, 'Dagger', 'Target Dagger')
        builder.arm(attacker.id, instrument.id, 'right hand')
        builder.arm(defender.id, target_weapon.id, 'right hand')
        attacker.current.skills.weapon_skills['Dagger'] = 2
        builder.enable()
        action = Action(world, 0, 1, 'disarm', attacker.id, defender.id,
                        instrument.id)
        action.disarm_weapon_id = target_weapon.id
        action.disarm_motion = 'thrust'
        action.reach = effective_melee_reach_meters(
            attacker.current, instrument.current)
        action.end_time = instrument.Tt()
        builder.schedule(action)
        values = iter((20, 1))
        def scripted(context, dice):
            value = next(values)
            context.trace.append(RandomDraw(context.action_id, dice,
                int(dice[2:].split('+')[0]), value))
            return value
        with patch.object(_ProvisionalRandom, 'roll', scripted):
            encounter.step(action.end_time)
        self.assertEqual(action.resolution.outcome, 'landing_choice_pending')
        self.assertTrue(disarm_landing_options(encounter, target_weapon.id))
        wire = export_save(encounter)
        actor_id, object_id, action_id = attacker.id, target_weapon.id, action.id
        saved_options = disarm_landing_options(encounter, object_id)
        chosen = saved_options[0]
        choose_disarm_landing(encounter, object_id, chosen.column, chosen.row)
        chosen_receipt = encounter._disarm_landing_receipts[-1]
        choice_history = native_history.current_recording(encounter)
        self.assertEqual(
            native_history.NativeHistoryQuery(choice_history).disarm_landings_at(
                chosen_receipt.boundary),
            native_history._plain((chosen_receipt,)))
        post_choice_wire = export_save(encounter)
        _choice_world, post_choice_restore, post_choice_rng = load_save(
            post_choice_wire)
        self.assertEqual(
            native_history._plain(post_choice_restore._disarm_landing_receipts),
            native_history._plain(encounter._disarm_landing_receipts))
        self.assertEqual(export_save(post_choice_restore), post_choice_wire)
        encounter.schedule_action(DelayAction(
            encounter, actor_id, defense=0, start_time=encounter.time,
            id='native-disarm-landing-continuation'))
        encounter.step(1)
        committed_history = native_history.capture(encounter)
        landing_receipt = encounter._disarm_landing_receipts[-1]
        self.assertEqual(
            native_history.NativeHistoryQuery(committed_history).disarm_landings_at(
                landing_receipt.boundary),
            native_history._plain((landing_receipt,)))
        committed_wire = export_save(encounter)
        committed_body = json.loads(committed_wire)
        saved_facts = native_history.NativeHistoryQuery(
            committed_body["history"]).disarm_landings_at(
                landing_receipt.boundary)
        self.assertEqual(saved_facts, native_history._plain((landing_receipt,)))
        from native_graph_snapshot import decode as decode_graph
        committed_graph = decode_graph(
            base64.b64decode(committed_body["graph_b64"],
                             validate=True), native=True)
        committed_marker = next(row[1:] for row in committed_graph[1]
                                if row[0] == "native-adapters")
        self.assertIn("disarm-landing-facts/1", committed_marker)
        restored_world, restored, restored_rng = load_save(committed_wire)
        self.assertIs(restored_world.event_history[restored.id], restored)
        self.assertEqual(
            native_history._plain(restored._disarm_landing_receipts),
            native_history._plain(encounter._disarm_landing_receipts))
        self.assertEqual(restored_rng.state, builder.rng.state)
        self.assertEqual(export_save(restored), committed_wire)
        continuation_id = 'native-disarm-landing-continuation'
        post_choice_restore.schedule_action(DelayAction(
            post_choice_restore, actor_id, defense=0,
            start_time=post_choice_restore.time, id=continuation_id))
        post_choice_restore.step(1)
        self.assertEqual(post_choice_rng.state, builder.rng.state)
        self.assertEqual(native_history.encode(native_history.capture(
            post_choice_restore)), native_history.encode(committed_history))
        from native_history import NativeHistoryRejected, _seal
        corrupted = json.loads(json.dumps(committed_history))
        landing_row = next(row for row in corrupted["boundaries"]
                           if row.get("boundary") == landing_receipt.boundary)
        landing_row["disarm_landings"]["$tuple"][0]["fields"]["actor_id"] = "missing-being"
        corrupted = _seal({key: value for key, value in corrupted.items()
                           if key != "sha256"})
        with self.assertRaisesRegex(NativeHistoryRejected, "dangling Entity reference"):
            native_history.validate(corrupted)
        expected = {
            'time': encounter.time,
            'rng': hashlib.sha256(json.dumps(builder.rng.state).encode()).hexdigest(),
            'history': hashlib.sha256(native_history.encode(committed_history)).hexdigest(),
            'object_id': object_id,
            'position': list(world.get_object_by_id(object_id).get_position().as_tuple()),
            'parent': world.get_object_by_id(object_id).parent_container_id,
            'holder_hand': defender.current.body_parts.get('right hand'),
            'action_id': action_id,
            'outcome': action.resolution.outcome,
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'native-disarm-pending.json'
            path.write_bytes(wire)
            child = r'''import hashlib,json,sys
import native_history
from activities import DelayAction
from atomic_publication import disarm_landing_options,choose_disarm_landing
from native_persistence import load_path
world,enc,rng=load_path(sys.argv[1])
object_id,actor_id,action_id=sys.argv[2:]
action=world.get_event_by_id(action_id)
assert action.resolution.outcome=='landing_choice_pending'
weapon=world.get_object_by_id(object_id)
from weapon import native_pending_disarm_landing
assert native_pending_disarm_landing(weapon) is not None
options=disarm_landing_options(enc,object_id)
assert options
cell=options[0]
choose_disarm_landing(enc,object_id,cell.column,cell.row)
enc.schedule_action(DelayAction(enc,actor_id,defense=0,start_time=enc.time,
 id='native-disarm-landing-continuation'))
enc.step(1)
holder=world.get_object_by_id(action.target_id)
print(json.dumps({'time':enc.time,
 'rng':hashlib.sha256(json.dumps(rng.state).encode()).hexdigest(),
 'history':hashlib.sha256(native_history.encode(native_history.capture(enc))).hexdigest(),
 'object_id':weapon.id,'position':weapon.get_position().as_tuple(),
 'parent':weapon.parent_container_id,
 'holder_hand':holder.current.body_parts.get('right hand'),
 'action_id':action.id,'outcome':action.resolution.outcome},sort_keys=True))'''
            import os
            result = subprocess.run(
                [sys.executable, '-B', '-c', child, str(path), object_id,
                 actor_id, action_id], cwd=ROOT,
                env={**os.environ, 'PYTHONPATH': f'{ROOT / "src"}:{ROOT / "examples"}'},
                text=True, capture_output=True, check=False, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), expected)

    def test_multiple_action_choice_and_simultaneous_touch_resume_from_initial_save(self):
        """An initial Save restores accepted composition and its first commits."""
        from action_choice import ChoiceMember
        from action import Action
        from native_scenario import NativeScenarioBuilder
        builder = NativeScenarioBuilder(
            'Native multiple-Action persistence',
            Library(config_dir=str(ROOT / 'src/config')), end_time=1, seed=53)
        actor = builder.add_being('Human', 'Composing Being',
            position=(0, 0, 0), radius=.2, hit_points=100)
        first_target = builder.add_being('Human', 'First Search target',
            position=(.3, 0, 0), radius=.2, hit_points=100)
        second_target = builder.add_being('Human', 'Second Search target',
            position=(0, .3, 0), radius=.2, hit_points=100)
        for target in (first_target, second_target):
            builder.mark_aware(actor.id, target.id)
        actor.set_skill_level(builder.world.get_skill_dictionary(), 'multi-action', 1)
        builder.enable()
        actions = []
        for identity, target in (('first', first_target), ('second', second_target)):
            action = Action(builder.world, 0, 1, 'touch', actor.id, target.id, None,
                            id=f'native-multi-touch-{identity}')
            action.touch_willing = True
            actions.append(action)
        actions = tuple(actions)
        builder.schedule_choice((
            ChoiceMember('first', actions[0], priority_penalty=0),
            ChoiceMember('second', actions[1], priority_penalty=3),
        ))
        choice = builder.encounter.choice_for_action(actions[0].id)
        initial_schedule = native_history.capture_initial_schedule(builder.encounter)
        self.assertEqual(choice.state, 'accepted')
        choice_record = builder.encounter._choice_book._choices[choice.id]
        self.assertEqual(tuple(row.priority_penalty for row in choice_record.members), (0, 3))
        self.assertFalse(native_history.has_recorder(builder.encounter))
        with patch('native_persistence.MAX_BYTES', 1):
            with self.assertRaisesRegex(NativeSaveRejected, 'portable size limit'):
                export_save(builder.encounter)
        self.assertFalse(native_history.has_recorder(builder.encounter))
        wire = export_save(builder.encounter)
        self.assertIsNone(native_history.current_recording(builder.encounter))
        builder.step(1)
        rows = builder.encounter._atomic_interval_history
        first_receipt = next(row for row in rows if row.boundary == 1)
        self.assertEqual(set(first_receipt.action_ids), {row.id for row in actions})
        expected = {
            'time': builder.encounter.time,
            'rng': hashlib.sha256(json.dumps(builder.rng.state).encode()).hexdigest(),
            'history': hashlib.sha256(native_history.encode(
                native_history.capture(builder.encounter))).hexdigest(),
            'choice_id': choice.id,
            'action_ids': [row.id for row in actions],
            'outcomes': [row.resolution.outcome for row in actions],
            'priority_penalties': [0, 3],
            'receipt_action_ids': list(first_receipt.action_ids),
            'initial_schedule': initial_schedule,
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'native-multiple-action.json'
            path.write_bytes(wire)
            child = r'''import hashlib,json,sys
import native_history
from native_persistence import load_path
world,enc,rng=load_path(sys.argv[1])
assert not (set(sys.modules)&{'arena_browser_session','arena_server','npcgen'})
choice_id,first_id,second_id=sys.argv[2:]
choice=enc.get_choice(choice_id)
assert choice.state=='accepted'
record=enc._choice_book._choices[choice_id]
assert [member.action.id for member in record.members]==[first_id,second_id]
assert [member.priority_penalty for member in record.members]==[0,3]
enc.step(1)
rows=enc._atomic_interval_history
first_receipt=next(row for row in rows if row.boundary==1)
assert set(first_receipt.action_ids)=={first_id,second_id}
actions=[world.get_event_by_id(identity) for identity in (first_id,second_id)]
initial_schedule=native_history.NativeHistoryQuery(
 native_history.current_recording(enc)).schedule_at(0)
print(json.dumps({'time':enc.time,
 'rng':hashlib.sha256(json.dumps(rng.state).encode()).hexdigest(),
 'history':hashlib.sha256(native_history.encode(native_history.capture(enc))).hexdigest(),
 'choice_id':choice.id,'action_ids':[row.id for row in actions],
 'outcomes':[row.resolution.outcome for row in actions],
 'priority_penalties':[member.priority_penalty for member in record.members],
 'receipt_action_ids':list(first_receipt.action_ids),
 'initial_schedule':initial_schedule},sort_keys=True))'''
            import os
            result = subprocess.run(
                [sys.executable, '-B', '-c', child, str(path), choice.id,
                 actions[0].id, actions[1].id], cwd=ROOT,
                env={**os.environ, 'PYTHONPATH': f'{ROOT / "src"}:{ROOT / "examples"}'},
                text=True, capture_output=True, check=False, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), expected)

    def test_repeating_multiple_action_successor_choice_resumes_natively(self):
        """The immutable next cycle survives Load and resolves as declared."""
        from action_choice import ChoiceMember
        from action import Action
        from native_scenario import NativeScenarioBuilder
        builder = NativeScenarioBuilder(
            'Native repeated Multiple-action cycle',
            Library(config_dir=str(ROOT / 'src/config')), end_time=3, seed=61)
        actor = builder.add_being('Human', 'Repeated actor',
            position=(0, 0, 0), radius=.2, hit_points=100)
        targets = (
            builder.add_being('Human', 'First target',
                position=(.3, 0, 0), radius=.2, hit_points=100),
            builder.add_being('Human', 'Second target',
                position=(0, .3, 0), radius=.2, hit_points=100),
        )
        for target in targets:
            builder.mark_aware(actor.id, target.id)
        actor.set_skill_level(builder.world.get_skill_dictionary(), 'multi-action', 1)
        builder.enable()
        first_cycle = []
        for key, target in zip(('first', 'second'), targets):
            action = Action(builder.world, 0, 1, 'touch', actor.id, target.id, None,
                            id=f'native-repeat-{key}')
            action.touch_willing = True
            first_cycle.append(action)
        builder.schedule_choice((
            ChoiceMember('first', first_cycle[0], priority_penalty=0),
            ChoiceMember('second', first_cycle[1], priority_penalty=3),
        ))
        builder.step(1)
        active = [record for record in builder.encounter._choice_book._choices.values()
                  if record.view.state == 'accepted']
        self.assertEqual(len(active), 1)
        successor = active[0]
        self.assertEqual(tuple(member.priority_penalty for member in successor.members), (0, 3))
        successor_action_ids = [member.action.id for member in successor.members]
        self.assertTrue(set(successor_action_ids).isdisjoint(
            {action.id for action in first_cycle}))
        wire = export_save(builder.encounter)
        builder.step(1)

        def state(world, encounter, rng):
            rows = sorted(encounter._choice_book.summary()['choices'],
                          key=lambda row: row['id'])
            action_ids = sorted(identity for identity in world.event_history
                                if getattr(world.get_event_by_id(identity),
                                           'event_type', None) == 'touch')
            return {
                'time': encounter.time,
                'rng': hashlib.sha256(json.dumps(rng.state).encode()).hexdigest(),
                'history': hashlib.sha256(native_history.encode(
                    native_history.capture(encounter))).hexdigest(),
                'choices': rows,
                'successor_actions': successor_action_ids,
                'touch_actions': action_ids,
                'outcomes': [world.get_event_by_id(identity).resolution.outcome
                             for identity in action_ids],
            }
        expected = state(builder.world, builder.encounter, builder.rng)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'native-repeat-choice.json'
            path.write_bytes(wire)
            child = r'''import hashlib,json,sys
import native_history
from native_persistence import load_path
world,enc,rng=load_path(sys.argv[1])
successor_id,*action_ids=sys.argv[2:]
choice=enc._choice_book._choices[successor_id]
assert choice.view.state=='accepted'
assert [member.action.id for member in choice.members]==action_ids
assert [member.priority_penalty for member in choice.members]==[0,3]
enc.step(1)
rows=sorted(enc._choice_book.summary()['choices'],key=lambda row:row['id'])
touch_ids=sorted(identity for identity in world.event_history
 if getattr(world.get_event_by_id(identity),'event_type',None)=='touch')
print(json.dumps({'time':enc.time,
 'rng':hashlib.sha256(json.dumps(rng.state).encode()).hexdigest(),
 'history':hashlib.sha256(native_history.encode(native_history.capture(enc))).hexdigest(),
 'choices':rows,'successor_actions':action_ids,'touch_actions':touch_ids,
 'outcomes':[world.get_event_by_id(identity).resolution.outcome
  for identity in touch_ids]},sort_keys=True))'''
            import os
            result = subprocess.run(
                [sys.executable, '-B', '-c', child, str(path), successor.view.id,
                 *successor_action_ids], cwd=ROOT,
                env={**os.environ, 'PYTHONPATH': f'{ROOT / "src"}:{ROOT / "examples"}'},
                text=True, capture_output=True, check=False, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        actual = json.loads(result.stdout)
        for key, value in expected.items():
            with self.subTest(field=key):
                self.assertEqual(actual[key], value)

    def test_native_history_v10_save_migrates_without_inventing_initial_entities(self):
        """Pre-/11 Saves keep their first-receipt anchor and continue natively."""
        from native_history import PUBLICATION_FACT_SCHEMA, NativeHistoryQuery, _seal
        from native_persistence import _canonical
        demo = encounter_delta_headless.build_demo(until=4)
        original = demo['encounter']
        body = json.loads(export_save(original))
        legacy = _legacy_initial_entity_anchor(
            {key: value for key, value in body['history'].items()
             if key != 'sha256'}, original)
        legacy['schema'] = PUBLICATION_FACT_SCHEMA
        legacy['initial'].pop('initial_entities_available')
        body['history'] = _seal(legacy)
        unsigned = {key: value for key, value in body.items() if key != 'sha256'}
        body['sha256'] = hashlib.sha256(_canonical(unsigned)).hexdigest()
        wire = _canonical(body)

        action_id = 'native-history-v10-migrated-delay'
        original.schedule_action(DelayAction(
            original, original.being_list[1], defense=0, start_time=4,
            id=action_id))
        original.step(1)
        original_query = NativeHistoryQuery(native_history.capture(original))
        expected = {
            'time': original.time,
            'rng': demo['rng_owner'].state,
            'boundaries': [original_query.boundary_facts_at(boundary)
                for boundary in range(1, original.last_processed_boundary + 1)],
        }

        child = r'''import json,sys
from activities import DelayAction
from native_history import NativeHistoryQuery,current_recording
from native_persistence import export_save,load_path,load_save
world,enc,rng=load_path(sys.argv[1]); log=current_recording(enc)
assert log['schema']=='universe.native-encounter-history/12'
assert log['initial']['initial_entities_available'] is False
query=NativeHistoryQuery(log)
assert query.state_at(0)['entities'] is None
assert query.entity_context_at(0) is None
enc.schedule_action(DelayAction(enc,enc.being_list[1],defense=0,
 start_time=4,id='native-history-v10-migrated-delay'))
enc.step(1); log=current_recording(enc); query=NativeHistoryQuery(log)
wire=export_save(enc)
assert export_save(load_save(wire)[1])==wire
print(json.dumps({'time':enc.time,'rng':rng.state,'boundaries':[
 query.boundary_facts_at(boundary) for boundary in
 range(1,enc.last_processed_boundary+1)]},sort_keys=True))'''
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'native-history-v10-save.json'
            path.write_bytes(wire)
            result = subprocess.run(
                [sys.executable, '-B', '-c', child, str(path)], cwd=directory,
                env={**__import__('os').environ,
                     'PYTHONPATH': f'{ROOT / "src"}:{ROOT / "examples"}'},
                text=True, capture_output=True, check=False, timeout=45)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), json.loads(json.dumps(expected)))

    def test_native_history_v1_save_upgrades_and_resumes_commit_recording(self):
        import base64
        from checkpoint_inventory import capture_checkpoint_candidate
        from native_graph_snapshot import encode as encode_graph
        from native_history import LEGACY_SCHEMA, SAME_RNG, _seal
        from native_persistence import _canonical
        demo = encounter_delta_headless.build_demo(until=4)
        original = demo['encounter']
        wire = export_save(original)
        body = json.loads(wire)
        # Legacy histories did not compact EntityInspection into a separate
        # fact family, so keep the corresponding legacy graph projection too.
        legacy_candidate = capture_checkpoint_candidate(
            original.universe, original, quiescent=True,
            rng_scope='exclusive_encounter', native_adapters=True,
            full_native=True,
            rng_owner=native_persistence._native_rng_owner(original))
        body['graph_b64'] = base64.b64encode(encode_graph(
            legacy_candidate.envelope, native=True)).decode('ascii')
        boundary_rngs = {row['boundary']: native_history.rng_state_at(
            body['history'], row.get('to_boundary', row.get('boundary')))
            for row in native_history._expand_rows(body['history'])}
        legacy = _legacy_history_shape({key: value for key, value in body['history'].items()
                  if key not in ('sha256', 'entity_context')})
        legacy = _legacy_initial_entity_anchor(legacy, original)
        legacy['schema'] = LEGACY_SCHEMA
        legacy['initial'].pop('initial_entities_available')
        legacy['initial'].pop('rng_before_first_commit')
        previous = None
        for row in legacy['boundaries']:
            if row['rng_after'] == SAME_RNG:
                row['rng_after'] = (boundary_rngs[row['boundary']]
                                    if previous is None else previous)
            previous = row['rng_after']
        body['history'] = _seal({key: value for key, value in legacy.items()
                                 if key != 'sha256'})
        unsigned = {key: value for key, value in body.items() if key != 'sha256'}
        body['sha256'] = hashlib.sha256(_canonical(unsigned)).hexdigest()
        migrated_world, migrated, _ = load_save(_canonical(body))
        self.assertEqual(migrated.id, original.id)
        self.assertEqual(native_history.current_recording(migrated)['schema'],
                         native_history.SCHEMA)
        action_id = 'native-history-v1-migrated-delay'
        actor_id = original.being_list[1]
        for encounter in (original, migrated):
            encounter.schedule_action(DelayAction(
                encounter, actor_id, defense=0, start_time=4, id=action_id))
            encounter.step(1)
        original_query = native_history.NativeHistoryQuery(
            native_history.capture(original))
        migrated_query = native_history.NativeHistoryQuery(
            native_history.capture(migrated))
        self.assertIsNone(migrated_query.schedule_at(0))
        self.assertIsNone(migrated_query.state_at(0)['schedule'])
        for boundary in range(1, original.last_processed_boundary + 1):
            self.assertEqual(migrated_query.schedule_at(boundary),
                             original_query.schedule_at(boundary))
            self.assertEqual(migrated_query.events_at(boundary),
                             original_query.events_at(boundary))
        migrated_wire = export_save(migrated)
        self.assertEqual(export_save(load_save(migrated_wire)[1]), migrated_wire)

    def test_native_history_v4_save_migrates_without_fabricating_then_rebinds_current_context(self):
        import base64
        from checkpoint_inventory import capture_checkpoint_candidate
        from native_graph_snapshot import encode as encode_graph
        from native_history import ENTITY_CONTEXT_SCHEMA, _seal
        from native_persistence import _canonical
        demo = encounter_delta_headless.build_demo(until=4)
        original = demo["encounter"]
        body = json.loads(export_save(original))
        legacy_candidate = capture_checkpoint_candidate(
            original.universe, original, quiescent=True,
            rng_scope="exclusive_encounter", native_adapters=True,
            full_native=True,
            rng_owner=native_persistence._native_rng_owner(original))
        body["graph_b64"] = base64.b64encode(encode_graph(
            legacy_candidate.envelope, native=True)).decode("ascii")
        history = native_history._without_fatigue_context(body["history"])
        legacy = _legacy_history_shape({key: value for key, value in history.items()
                                        if key != "sha256"})
        legacy = _legacy_initial_entity_anchor(legacy, original)
        legacy["schema"] = ENTITY_CONTEXT_SCHEMA
        legacy["initial"].pop("initial_entities_available")
        legacy["entity_context"].pop("fatigue_available")
        legacy["initial"].pop("rng_before_first_commit")
        body["history"] = _seal(legacy)
        unsigned = {key: item for key, item in body.items() if key != "sha256"}
        body["sha256"] = hashlib.sha256(_canonical(unsigned)).hexdigest()
        legacy_wire = _canonical(body)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "native-history-v4-save.json"
            path.write_bytes(legacy_wire)
            child = r'''import hashlib,json,sys
import native_history
from activities import DelayAction
from native_persistence import load_path
world,enc,rng=load_path(sys.argv[1])
log=native_history.current_recording(enc)
assert log['schema'] == native_history.SCHEMA
query=native_history.NativeHistoryQuery(log)
assert query.fatigue_context_at(4) is not None
assert query.schedule_at(0) is None
action=DelayAction(enc,enc.being_list[1],defense=0,start_time=4,
 id='native-history-v4-migrated-delay')
enc.schedule_action(action)
enc.step(1)
query=native_history.NativeHistoryQuery(native_history.current_recording(enc))
print(json.dumps({'time':enc.time,'rng':rng.state,
 'schedules':[query.schedule_at(boundary) for boundary in
  range(1,query._latest+1)],
 'actions':list(enc._atomic_interval_history[-1].action_ids)},sort_keys=True))'''
            result = subprocess.run(
                [sys.executable, "-B", "-c", child, str(path)], cwd=directory,
                env={**__import__("os").environ,
                     "PYTHONPATH": f"{ROOT / 'src'}:{ROOT / 'examples'}"},
                text=True, capture_output=True, check=False, timeout=45)

        action = DelayAction(original, original.being_list[1], defense=0,
                             start_time=4, id="native-history-v4-migrated-delay")
        original.schedule_action(action)
        original.step(1)
        expected = {
            "time": original.time,
            "rng": demo["rng_owner"].state,
            "schedules":[native_history.NativeHistoryQuery(
                native_history.capture(original)).schedule_at(boundary)
                for boundary in range(1,original.last_processed_boundary+1)],
            "actions": list(original._atomic_interval_history[-1].action_ids),
        }
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), json.loads(json.dumps(expected)))

    def test_native_history_v5_save_upgrades_without_inventing_origin_then_rebinds_graph(self):
        from native_history import FATIGUE_CONTEXT_SCHEMA, _seal
        from native_persistence import _canonical
        demo = encounter_delta_headless.build_demo(until=4)
        original = demo["encounter"]
        body = json.loads(export_save(original))
        prior = native_history._without_initial_rng(body["history"])
        legacy = _legacy_history_shape({key: value for key, value in prior.items()
                                       if key != "sha256"})
        legacy = _legacy_initial_entity_anchor(legacy, original)
        legacy["schema"] = FATIGUE_CONTEXT_SCHEMA
        legacy["initial"].pop("initial_entities_available")
        legacy["initial"].pop("rng_before_first_commit")
        body["history"] = _seal(legacy)
        body["graph_b64"] = _previous_entity_compact_graph(original)
        unsigned = {key: value for key, value in body.items() if key != "sha256"}
        body["sha256"] = hashlib.sha256(_canonical(unsigned)).hexdigest()

        restored_world, restored, restored_rng = load_save(_canonical(body))
        self.assertEqual(restored.id, original.id)
        self.assertEqual(restored_rng.state, demo["rng_owner"].state)
        current = native_history.current_recording(restored)
        self.assertEqual(current["schema"], native_history.SCHEMA)
        self.assertEqual(current["initial"]["rng_before_first_commit"],
                         native_history._plain(demo["rng_owner"].state))
        self.assertEqual(restored_world.event_history[restored.id], restored)

    def test_native_history_v6_save_preserves_origin_and_rebinds_graph_receipts(self):
        from native_history import INITIAL_RNG_SCHEMA, _seal
        from native_persistence import _canonical
        demo = encounter_delta_headless.build_demo(until=4)
        body = json.loads(export_save(demo["encounter"]))
        history = {key: item for key, item in body["history"].items()
                   if key != "sha256"}
        history = _legacy_initial_entity_anchor(history, demo["encounter"])
        history.pop("receipt_facts_complete")
        history.pop("observer_knowledge")
        history["initial"].pop("initial_schedule_available")
        history["initial"].pop("initial_entities_available")
        history["schema"] = INITIAL_RNG_SCHEMA
        for row in history["boundaries"]:
            row.pop("notification_intents", None)
            row.pop("disarm_landings", None)
            row.pop("receipt_facts_available", None)
        body["history"] = _seal(history)
        body["graph_b64"] = _previous_entity_compact_graph(demo["encounter"])
        unsigned = {key: item for key, item in body.items() if key != "sha256"}
        body["sha256"] = hashlib.sha256(_canonical(unsigned)).hexdigest()

        world, restored, rng = load_save(_canonical(body))
        current = native_history.current_recording(restored)
        self.assertEqual(current["schema"], native_history.SCHEMA)
        self.assertEqual(current["initial"]["rng_before_first_commit"],
                         body["history"]["initial"]["rng_before_first_commit"])
        self.assertTrue(current["receipt_facts_complete"])
        self.assertTrue(native_history.NativeHistoryQuery(current).receipt_facts_at(4))
        self.assertEqual(restored.id, demo["encounter"].id)
        self.assertIs(world.event_history[restored.id], restored)
        self.assertEqual(rng.state, demo["rng_owner"].state)


if __name__ == "__main__":
    unittest.main()
