import ast
from dataclasses import replace
import os
from pathlib import Path
import random
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "examples"))
sys.path.insert(0, str(ROOT / "src"))

from arena_browser_session import GeneratedArenaSession
from arena_hex_map import HexAddress
from checkpoint_adapters import NativeInventory
from checkpoint_arena_perception import (
    ArenaPerceptionCheckpointRejected, decode_arena_perception_ledger,
    encode_arena_perception_ledger, encode_detached_arena_perception_ledger,
)
from checkpoint_inventory import (CheckpointRejected, capture_checkpoint_candidate,
                                  validate_checkpoint_candidate)
from test_arena_ground_pickup import fixture as ground_fixture, move_player_to


def _bindings(candidate, observer):
    encounter = candidate.encounter
    return (tuple(sorted(encounter.entity_ids())),
            tuple(sorted(encounter.awareness[observer.id])))


def _decode(candidate, observer, data):
    entity_ids, visible_ids = _bindings(candidate, observer)
    return decode_arena_perception_ledger(data, observer_id=observer.id,
        entity_ids=entity_ids, visible_entity_ids=visible_ids,
        boundary=candidate.encounter.last_processed_boundary,
        time=candidate.encounter.time)


def _native_encoding(candidate, observer):
    return encode_arena_perception_ledger(observer._arena_perception_ledger,
        observer=observer, encounter=candidate.encounter,
        registry=candidate.universe.object_registry.object_instances)


class ArenaPerceptionCheckpointTests(unittest.TestCase):
    def setUp(self):
        self.global_rng = random.getstate()

    def tearDown(self):
        self.assertEqual(random.getstate(), self.global_rng)

    def test_initial_ledgers_round_trip_across_fresh_process_and_native_adapter(self):
        session = GeneratedArenaSession(root_seed_factory=lambda: 20261120)
        session.generate({"starting_experience": "10000",
                          "width_cells": "5", "height_cells": "5"})
        candidate = session.active_candidate
        encounter = candidate.encounter
        before = (encounter.time, encounter.last_processed_boundary,
                  session._rng_cursor.state,
                  tuple((participant.native.being._arena_perception_ledger.observer_id,
                         dict(participant.native.being._arena_perception_ledger._current),
                         list(participant.native.being._arena_perception_ledger._history))
                        for participant in candidate.participants))

        for participant in candidate.participants:
            observer = participant.native.being
            data = _native_encoding(candidate, observer)
            self.assertEqual(data[0], "universe.arena-perception-ledger/1")
            self.assertEqual(len(data[3]), 1)
            decoded = _decode(candidate, observer, data)
            self.assertIsNot(decoded, observer._arena_perception_ledger)
            self.assertEqual(encode_arena_perception_ledger(decoded,
                observer=observer, encounter=encounter,
                registry=candidate.universe.object_registry.object_instances), data)
            self.assertEqual(encode_detached_arena_perception_ledger(decoded,
                observer_id=observer.id, entity_ids=_bindings(candidate, observer)[0],
                visible_entity_ids=_bindings(candidate, observer)[1],
                boundary=encounter.last_processed_boundary, time=encounter.time), data)

            inventory = NativeInventory(candidate.universe, encounter, ())
            inventory.known[id(observer)] = ("object", observer.id)
            inventory._objects_by_identity = {id(observer): observer}
            projected = inventory.field("being.BeingInstance", "_arena_perception_ledger",
                observer._arena_perception_ledger, ("object", observer.id), (), 0)
            self.assertEqual(projected, ("arena-perception-ledger", data))
            self.assertTrue(_pointer_free(projected))
            with self.assertRaisesRegex(CheckpointRejected,
                                        "Arena-enabled Being has no observer-owned perception ledger"):
                inventory.field("being.BeingInstance", "_arena_perception_ledger",
                    None, ("object", observer.id), (), 0)

        observer = candidate.participants[0].native.being
        data = _native_encoding(candidate, observer)
        entity_ids, visible_ids = _bindings(candidate, observer)
        script = """import ast,sys
from checkpoint_arena_perception import decode_arena_perception_ledger, encode_detached_arena_perception_ledger
data,observer,entities,visible,boundary,time=map(ast.literal_eval,sys.argv[1:])
ledger=decode_arena_perception_ledger(data,observer_id=observer,entity_ids=entities,visible_entity_ids=visible,boundary=boundary,time=time)
roundtrip=encode_detached_arena_perception_ledger(ledger,observer_id=observer,entity_ids=entities,visible_entity_ids=visible,boundary=boundary,time=time)
print(repr(roundtrip))
"""
        result = subprocess.run([sys.executable, "-c", script, repr(data),
            repr(observer.id), repr(entity_ids), repr(visible_ids),
            repr(encounter.last_processed_boundary), repr(encounter.time)],
            cwd=ROOT, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            capture_output=True, text=True, check=True)
        self.assertEqual(ast.literal_eval(result.stdout.strip()), data)
        after = (encounter.time, encounter.last_processed_boundary,
                 session._rng_cursor.state,
                 tuple((participant.native.being._arena_perception_ledger.observer_id,
                        dict(participant.native.being._arena_perception_ledger._current),
                        list(participant.native.being._arena_perception_ledger._history))
                       for participant in candidate.participants))
        self.assertEqual(after, before)

    def test_current_position_and_ground_to_carried_history_are_preserved(self):
        session, _, candidate, player, placement, item = ground_fixture(seed=20261107)
        address = HexAddress(placement.column, placement.row)
        move_player_to(session, candidate, player, address)
        opponent = candidate.participants[1].native.being
        opponent_data = _native_encoding(candidate, opponent)
        player_history = [row for row in opponent_data[4]
                          if row[2] == player.id]
        self.assertGreaterEqual(len(player_history), 2)
        self.assertEqual(player_history[-1][6],
                         ("universe.cartesian-position-binary64/1",
                          *(value.hex() for value in player.get_position().as_tuple())))

        visible = next(row for row in session.public_view()["entities"]
                       if row["type"] == "Dagger")
        session.choose_pickup({"handle": visible["handle"]})
        session.advance_one_second()
        for participant in candidate.participants:
            observer = participant.native.being
            data = _native_encoding(candidate, observer)
            item_evidence = [row for row in data[4]
                             if row[2] == item.id]
            self.assertEqual([row[7] for row in item_evidence], ["ground", "carried"])
            decoded = _decode(candidate, observer, data)
            self.assertEqual(encode_arena_perception_ledger(decoded,
                observer=observer, encounter=candidate.encounter,
                registry=candidate.universe.object_registry.object_instances), data)
            self.assertEqual(encode_detached_arena_perception_ledger(decoded,
                observer_id=observer.id, entity_ids=_bindings(candidate, observer)[0],
                visible_entity_ids=_bindings(candidate, observer)[1],
                boundary=candidate.encounter.last_processed_boundary,
                time=candidate.encounter.time), data)

    def test_tampered_or_misbound_ledgers_refuse(self):
        session = GeneratedArenaSession(root_seed_factory=lambda: 20261120)
        session.generate({"starting_experience": "10000",
                          "width_cells": "5", "height_cells": "5"})
        candidate = session.active_candidate
        observer = candidate.participants[0].native.being
        data = _native_encoding(candidate, observer)
        entity_ids, visible_ids = _bindings(candidate, observer)
        args = dict(observer_id=observer.id, entity_ids=entity_ids,
                    visible_entity_ids=visible_ids, boundary=0, time=0.0)

        current_id = data[3][0][0]
        ledger = observer._arena_perception_ledger
        original = ledger._current[current_id]
        ledger._current[current_id] = replace(original, name=original.name + " stale")
        try:
            with self.assertRaisesRegex(ArenaPerceptionCheckpointRejected,
                                        "committed Entity name, custody, or position"):
                _native_encoding(candidate, observer)
        finally:
            ledger._current[current_id] = original

        with self.assertRaisesRegex(ArenaPerceptionCheckpointRejected,
                                    "belongs to another observer"):
            decode_arena_perception_ledger(data, observer_id="foreign", **{
                key: value for key, value in args.items() if key != "observer_id"})

        duplicate_current = (data[3][0], data[3][0])
        with self.assertRaisesRegex(ArenaPerceptionCheckpointRejected, "canonical Entity order|duplicate"):
            decode_arena_perception_ledger((data[0], data[1], data[2], duplicate_current,
                                            data[4]), **args)

        dangling_row = ("missing-entity",
                        (data[3][0][1][0], data[3][0][1][1], "missing-entity",
                         *data[3][0][1][3:]))
        with self.assertRaisesRegex(ArenaPerceptionCheckpointRejected, "absent or self Entity"):
            decode_arena_perception_ledger((data[0], data[1], data[2],
                (dangling_row,), data[4]), **args)

        history = list(data[4])
        row = history[0]
        history[0] = (*row[:8], 1, row[9], row[10])
        with self.assertRaisesRegex(ArenaPerceptionCheckpointRejected,
                                    "beyond the committed boundary"):
            decode_arena_perception_ledger((data[0], data[1], data[2], data[3],
                                            tuple(history)), **args)

        history[0] = (*row[:9], ("binary64", "nan"), row[10])
        with self.assertRaises(ArenaPerceptionCheckpointRejected):
            decode_arena_perception_ledger((data[0], data[1], data[2], data[3],
                                            tuple(history)), **args)

        ledger.unexpected = True
        try:
            with self.assertRaisesRegex(ArenaPerceptionCheckpointRejected,
                                        "unknown or missing fields"):
                _native_encoding(candidate, observer)
        finally:
            del ledger.unexpected
        evidence = ledger.history[0]
        object.__setattr__(evidence, "unexpected", True)
        try:
            with self.assertRaisesRegex(ArenaPerceptionCheckpointRejected,
                                        "unknown or missing fields"):
                _native_encoding(candidate, observer)
        finally:
            object.__delattr__(evidence, "unexpected")

    def test_movement_activation_record_validates_existing_references_without_mutation(self):
        session = GeneratedArenaSession(root_seed_factory=lambda: 20261120)
        session.generate({"starting_experience": "10000",
                          "width_cells": "5", "height_cells": "5"})
        candidate = session.active_candidate
        encounter = candidate.encounter
        player = candidate.participants[0].native.being
        origin = candidate.arena_map.layout.cell_at_position(player.get_position())
        destination = next(a for a in candidate.arena_map.layout.addresses() if a != origin)
        session.choose_destination({"column": destination.column, "row": destination.row,
                                    "rate": "sprint", "facing_policy": "turn"})
        session.advance_one_second()
        original = encounter.arena_movement_activation
        before = (encounter.time, encounter.last_processed_boundary,
            tuple((row.native.being.id, row.native.being.get_position().as_tuple(),
                   row.native.being.get_posture(), row.native.being.hex_facing)
                  for row in candidate.participants), session._movement_plan,
            session._rng_cursor.state, tuple(encounter._choice_book._choices.items()),
            tuple((row.native.being._arena_perception_ledger.observer_id,
                   dict(row.native.being._arena_perception_ledger._current),
                   list(row.native.being._arena_perception_ledger._history))
                  for row in candidate.participants))
        variants = (
            replace(original, encounter_id="foreign-encounter"),
            replace(original, actor_id="foreign-being"),
            replace(original, movement_decision_id=" "),
            replace(original, time=encounter.time),
            replace(original, activation_kind="first_player_choice"),
        )
        try:
            for variant in variants:
                with self.subTest(record=variant):
                    encounter.arena_movement_activation = variant
                    with self.assertRaisesRegex(CheckpointRejected,
                            "Arena movement activation record is inconsistent"):
                        capture_checkpoint_candidate(candidate.universe, encounter,
                            quiescent=True, rng_scope="exclusive_encounter", native_adapters=True)
                    self.assertEqual((encounter.time, encounter.last_processed_boundary,
                        tuple((row.native.being.id, row.native.being.get_position().as_tuple(),
                               row.native.being.get_posture(), row.native.being.hex_facing)
                              for row in candidate.participants), session._movement_plan,
                        session._rng_cursor.state, tuple(encounter._choice_book._choices.items()),
                        tuple((row.native.being._arena_perception_ledger.observer_id,
                               dict(row.native.being._arena_perception_ledger._current),
                               list(row.native.being._arena_perception_ledger._history))
                              for row in candidate.participants)), before)
            encounter.arena_movement_activation = original
            encounter.arena_activation_enabled = False
            with self.assertRaisesRegex(CheckpointRejected,
                    "Arena movement activation phase conflicts"):
                capture_checkpoint_candidate(candidate.universe, encounter,
                    quiescent=True, rng_scope="exclusive_encounter", native_adapters=True)
            encounter.arena_activation_enabled = True
            encounter.arena_movement_activation = None
            with self.assertRaisesRegex(CheckpointRejected,
                    "lacks its movement activation record"):
                capture_checkpoint_candidate(candidate.universe, encounter,
                    quiescent=True, rng_scope="exclusive_encounter", native_adapters=True)
        finally:
            encounter.arena_activation_enabled = True
            encounter.arena_movement_activation = original

    def test_activated_capture_advances_to_receipt_blocker_without_mutation(self):
        session = GeneratedArenaSession(root_seed_factory=lambda: 20261120)
        session.generate({"starting_experience": "10000",
                          "width_cells": "5", "height_cells": "5"})
        candidate = session.active_candidate
        encounter = candidate.encounter
        player = candidate.participants[0].native.being
        start = player.get_position()
        origin = candidate.arena_map.layout.cell_at_position(start)
        destination = next(a for a in candidate.arena_map.layout.addresses() if a != origin)
        session.choose_destination({"column": destination.column,
                                    "row": destination.row,
                                    "rate": "sprint", "facing_policy": "turn"})
        session.advance_one_second()
        book = encounter._choice_book
        def source_state():
            return (encounter.time, encounter.last_processed_boundary,
                 tuple((p.native.being.id, tuple(p.native.being.get_position().as_tuple()),
                        p.native.being.get_posture(), p.native.being.hex_facing)
                       for p in candidate.participants), encounter.initiated,
                 encounter.arena_activation_enabled, encounter.arena_activation,
                 encounter.arena_movement_activation, session._movement_plan,
                 session._rng_cursor.state,
                 (book._counter, tuple(book._choices.items()), tuple(book._states.items()),
                  tuple(encounter.pending_action_list)),
                 tuple((p.native.being._arena_perception_ledger.observer_id,
                         dict(p.native.being._arena_perception_ledger._current),
                         list(p.native.being._arena_perception_ledger._history))
                       for p in candidate.participants))
        before = source_state()
        from checkpoint_arena_perception import encode_arena_perception_ledger
        with patch("checkpoint_arena_perception.encode_arena_perception_ledger",
                   wraps=encode_arena_perception_ledger) as encode_ledger:
            checkpoint = capture_checkpoint_candidate(candidate.universe, encounter,
                quiescent=True, rng_scope="exclusive_encounter", native_adapters=True)
            # Capture and its explicit validation each inspect both observer ledgers.
            self.assertEqual(encode_ledger.call_count, 4)
        validation = validate_checkpoint_candidate(candidate.universe, encounter,
            checkpoint, quiescent=True)
        blocker = next(row.reason for row in checkpoint.diagnostics
                       if row.code == "bounded_run_spot_closure_refused")
        self.assertEqual(blocker,
            "Run/Spot receipt closure refused: missing, duplicate, or unreceipted committed Action")
        self.assertTrue(validation.inventory_validated)
        self.assertFalse(checkpoint.closure_validated)
        self.assertFalse(checkpoint.portable_schema_defined)
        self.assertFalse(checkpoint.restore_verified)
        self.assertEqual(source_state(), before)


def _pointer_free(value):
    if value is None or type(value) in (str, int, float, bool):
        return True
    return type(value) is tuple and all(_pointer_free(item) for item in value)


if __name__ == "__main__":
    unittest.main()
