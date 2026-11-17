from __future__ import annotations

import copy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "examples"))

import encounter_delta_headless
import native_persistence_scale
from native_history import (NativeHistoryRejected, capture, decode, encode,
                            append_committed, events_at, state_at, validate,
                            NativeHistoryRecorder, write, rng_state_at, upgrade,
                            NativeHistoryQuery, entity_context_at, LEGACY_SCHEMA, PREVIOUS_SCHEMA,
                            QUIET_SPAN_SCHEMA, ENTITY_CONTEXT_SCHEMA, SCHEMA, SAME_RNG, _seal,
                            fatigue_context_at,
                            _plain, _expand_rows, _target_candidates)


class NativeHistoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.demo = encounter_delta_headless.build_demo(until=4)
        cls.log = capture(cls.demo["encounter"])
        cls.wire = encode(cls.log)

    def test_native_inspection_boundaries_round_trip_as_atomic_history(self):
        log = decode(self.wire)
        self.assertTrue(validate(log))
        self.assertEqual(log["latest_boundary"], 4)
        self.assertEqual([row["boundary"] for row in log["boundaries"]], [1, 2, 3, 4])
        self.assertEqual(events_at(log, 2)["action_ids"], [])
        self.assertEqual(len(events_at(log, 3)["action_ids"]), 1)
        action_row = next(iter(events_at(log, 3)["actions"].values()))
        self.assertEqual(action_row["$record"], "encounter_inspection.ActionInspection")
        self.assertEqual(len(events_at(log, 4)["action_ids"]), 2)
        self.assertEqual(len(events_at(log, 4)["effect_ids"]), 6)
        self.assertEqual(state_at(log, 4)["boundary"], 4)
        for boundary in range(1, 5):
            expected = _target_candidates(self.demo["encounter"]).get(boundary, {})
            self.assertEqual(state_at(log, boundary)["entities"], _plain(expected))
            receipt = next(row for row in self.demo["encounter"]._atomic_interval_history
                           if row.boundary == boundary)
            self.assertEqual(entity_context_at(log, boundary),
                             _plain(receipt.inspection.entities))
            self.assertEqual(events_at(log, boundary)["action_ids"], list(receipt.action_ids))

    def test_scale_verifier_checks_action_and_quiet_span_receipts(self):
        demo = encounter_delta_headless.build_demo(until=4)
        encounter = demo["encounter"]
        encounter.step(8)
        log = native_persistence_scale._verify_history_boundaries(encounter)
        self.assertEqual(log["latest_boundary"], 12)
        self.assertEqual(sum(row.get("to_boundary", row.get("boundary", 0))
                             - row.get("from_boundary", row.get("boundary", 0)) + 1
                             for row in log["boundaries"]), 12)
        class MismatchedReader:
            def __init__(self, _log):
                pass

            def state_at(self, boundary):
                return {"boundary": boundary + 1}

            def events_at(self, _boundary):
                return {}

            def entity_context_at(self, _boundary):
                return None

            def rng_state_at(self, _boundary):
                return None

        with patch("native_persistence_scale.NativeHistoryQuery", MismatchedReader):
            with self.assertRaisesRegex(RuntimeError, "receipt at 1"):
                native_persistence_scale._verify_history_boundaries(encounter)

    def test_validated_query_session_matches_single_queries_and_detaches_input(self):
        source = copy.deepcopy(self.log)
        reader = NativeHistoryQuery(source)
        for boundary in range(1, self.log['latest_boundary'] + 1):
            self.assertEqual(reader.state_at(boundary), state_at(self.log, boundary))
            self.assertEqual(reader.events_at(boundary), events_at(self.log, boundary))
            self.assertEqual(reader.rng_state_at(boundary), rng_state_at(self.log, boundary))
            self.assertEqual(reader.entity_context_at(boundary),
                             entity_context_at(self.log, boundary))
            self.assertEqual(reader.fatigue_context_at(boundary),
                             fatigue_context_at(self.log, boundary))
        expected = reader.state_at(4)
        source['initial']['encounter_id'] = 'mutated-after-validation'
        self.assertEqual(reader.state_at(4), expected)

    def test_changes_are_presence_aware_and_reconstruct_each_native_target_boundary(self):
        for boundary, delta in enumerate(self.log["boundaries"], 1):
            state = state_at(self.log, boundary)
            self.assertEqual(state["boundary"], boundary)
            expected = _target_candidates(self.demo["encounter"]).get(boundary, {})
            # Native history contains exact typed target read records. The
            # initial entity state is separate and only changes by committed deltas.
            self.assertEqual(set(state["entities"]), set(expected))
            self.assertTrue(all(row["before"] is True or row["before"] is False
                                for row in delta["changes"]))

    def test_unchanged_rng_cursor_is_referenced_and_legacy_history_upgrades(self):
        log = decode(self.wire)
        self.assertEqual(log['schema'], SCHEMA)
        previous = None
        for boundary, row in enumerate(log['boundaries'], 1):
            current = rng_state_at(log, boundary)
            if current == previous:
                self.assertEqual(row['rng_after'], SAME_RNG)
            else:
                self.assertNotEqual(row['rng_after'], SAME_RNG)
            previous = current

        legacy = {key: copy.deepcopy(value) for key, value in log.items()
                  if key not in ('sha256', 'entity_context')}
        legacy['schema'] = LEGACY_SCHEMA
        previous = None
        for row in legacy['boundaries']:
            if row['rng_after'] == SAME_RNG:
                row['rng_after'] = previous
            previous = row['rng_after']
        legacy = _seal({key: value for key, value in legacy.items()
                        if key != 'sha256'})
        self.assertTrue(validate(legacy))
        upgraded_legacy = upgrade(legacy)
        self.assertEqual(encode(upgraded_legacy),
                         encode(__import__('native_history')._without_entity_context(log)))
        self.assertIsNone(entity_context_at(upgraded_legacy, 4))
        self.assertIsNone(fatigue_context_at(upgraded_legacy, 4))

        old_context = __import__('native_history')._without_fatigue_context(log)
        old_context_body = {key: copy.deepcopy(value) for key, value in old_context.items()
                            if key != 'sha256'}
        old_context_body['schema'] = ENTITY_CONTEXT_SCHEMA
        old_context_body['entity_context'].pop('fatigue_available')
        old_context = _seal(old_context_body)
        self.assertTrue(validate(old_context))
        upgraded_context = upgrade(old_context)
        self.assertEqual(upgraded_context['schema'], SCHEMA)
        self.assertFalse(upgraded_context['entity_context']['fatigue_available'])
        self.assertIsNone(fatigue_context_at(upgraded_context, 4))
        self.assertEqual(entity_context_at(upgraded_context, 4),
                         entity_context_at(old_context, 4))

        previous_schema = {key: copy.deepcopy(value) for key, value in log.items()
                           if key not in ('sha256', 'entity_context')}
        previous_schema['schema'] = PREVIOUS_SCHEMA
        previous = None
        for row in previous_schema['boundaries']:
            if row['rng_after'] == SAME_RNG:
                row['rng_after'] = previous
            previous = row['rng_after']
        previous_schema = _seal({key: value for key, value in previous_schema.items()
                                  if key != 'sha256'})
        self.assertTrue(validate(previous_schema))
        self.assertEqual(encode(upgrade(previous_schema)),
                         encode(__import__('native_history')._without_entity_context(log)))

        quiet_schema = {key: copy.deepcopy(value) for key, value in log.items()
                        if key not in ('sha256', 'entity_context')}
        quiet_schema['schema'] = QUIET_SPAN_SCHEMA
        quiet_schema = _seal(quiet_schema)
        self.assertEqual(encode(upgrade(quiet_schema)),
                         encode(__import__('native_history')._without_entity_context(log)))

        corrupt = copy.deepcopy(log)
        corrupt['boundaries'][0]['rng_after'] = dict(SAME_RNG)
        with self.assertRaisesRegex(NativeHistoryRejected, 'RNG reference'):
            validate(_seal({key: value for key, value in corrupt.items()
                            if key != 'sha256'}))

    def test_fatigue_history_is_versioned_and_strictly_validated(self):
        reader = NativeHistoryQuery(self.log)
        for boundary in range(1, self.log['latest_boundary'] + 1):
            state = reader.fatigue_context_at(boundary)
            self.assertIsNotNone(state)
            self.assertEqual(set(state), set(self.demo['encounter'].being_list))
            for row in state.values():
                fatigue = row['physical_fatigue']
                self.assertEqual(set(fatigue), {'b', 'check_modifier', 'physiology_id', 'q'})
                self.assertEqual(row['physiology'], {})

        corrupt = copy.deepcopy(self.log)
        pre_action = corrupt['entity_context']['initial'][
            self.demo['encounter'].being_list[0]]['fields']['pre_action']
        pre_action.pop('physical_fatigue')
        with self.assertRaisesRegex(NativeHistoryRejected, 'fatigue/physiology'):
            validate(_seal({key: value for key, value in corrupt.items()
                            if key != 'sha256'}))

    def test_consecutive_empty_boundaries_use_lossless_quiet_span(self):
        demo = encounter_delta_headless.build_demo(until=4)
        encounter = demo['encounter']
        encounter.step(8)
        log = capture(encounter)
        spans = [row for row in log['boundaries'] if row.get('kind') == 'quiet_span']
        self.assertTrue(spans)
        query = NativeHistoryQuery(log)
        self.assertEqual(len(query._segments), len(log['boundaries']))
        self.assertLess(len(query._segments), log['latest_boundary'])
        expanded = dict(log)
        expanded['boundaries'] = _expand_rows(log)
        self.assertGreater(len(encode(_seal({key: value for key, value in expanded.items()
                                             if key != 'sha256'}))), len(encode(log)))
        self.assertLess(len(log['boundaries']), log['latest_boundary'])
        self.assertTrue(validate(decode(encode(log))))
        previous_schema = {key: copy.deepcopy(value) for key, value in log.items()
                           if key not in ('sha256', 'entity_context')}
        previous_schema['schema'] = PREVIOUS_SCHEMA
        previous_schema['boundaries'] = _expand_rows(log)
        for row in previous_schema['boundaries']:
            row['rng_after'] = rng_state_at(log, row['boundary'])
        previous_schema = _seal({key: value for key, value in previous_schema.items()
                                  if key != 'sha256'})
        self.assertTrue(validate(previous_schema))
        self.assertEqual(encode(upgrade(previous_schema)),
                         encode(__import__('native_history')._without_entity_context(log)))
        quiet_span_schema = {key: copy.deepcopy(value) for key, value in log.items()
                             if key not in ('sha256', 'entity_context')}
        quiet_span_schema['schema'] = QUIET_SPAN_SCHEMA
        quiet_span_schema = _seal(quiet_span_schema)
        self.assertTrue(validate(quiet_span_schema))
        self.assertEqual(encode(upgrade(quiet_span_schema)),
                         encode(__import__('native_history')._without_entity_context(log)))
        encounter.inspect_committed()
        receipts = {row.boundary: row for row in encounter._atomic_interval_history}
        for boundary in range(1, encounter.last_processed_boundary + 1):
            expected = _target_candidates(encounter).get(boundary, {})
            state = state_at(log, boundary)
            self.assertEqual(state['entities'], _plain(expected))
            self.assertEqual(state['time'], receipts[boundary].inspection.end)
            self.assertEqual(events_at(log, boundary)['action_ids'],
                             list(receipts[boundary].action_ids))
            self.assertEqual(rng_state_at(log, boundary), _plain(receipts[boundary].rng_state))

        span = copy.deepcopy(spans[0])
        bad_body = {key: value for key, value in log.items() if key != 'sha256'}
        bad_body['boundaries'][log['boundaries'].index(spans[0])] = span
        span['increments'][0]['path'] = ['entities', 'missing', 'fields', 'hit_points']
        with self.assertRaises(NativeHistoryRejected):
            validate(_seal(bad_body))

    def test_append_after_quiet_span_preserves_expanded_boundary_semantics(self):
        demo = encounter_delta_headless.build_demo(until=4)
        encounter = demo['encounter']
        encounter.step(8)
        log = capture(encounter)
        self.assertTrue(any(row.get('kind') == 'quiet_span'
                            for row in log['boundaries']))
        encounter.step(1)
        quiet_appended = append_committed(log, encounter)
        self.assertEqual(quiet_appended['latest_boundary'], log['latest_boundary'] + 1)
        self.assertTrue(any(row.get('kind') == 'quiet_span'
                            and row['to_boundary'] == quiet_appended['latest_boundary']
                            for row in quiet_appended['boundaries']))
        from activities import DelayAction
        action = DelayAction(encounter, encounter.being_list[1], defense=0,
                             start_time=encounter.time, id='append-after-quiet-span')
        encounter.schedule_action(action)
        encounter.step(1)
        appended = append_committed(quiet_appended, encounter)
        self.assertEqual(appended['latest_boundary'], encounter.last_processed_boundary)
        self.assertEqual(events_at(appended, appended['latest_boundary'])['action_ids'],
                         [action.id])
        receipts = {row.boundary: row for row in encounter._atomic_interval_history}
        for boundary in range(1, encounter.last_processed_boundary + 1):
            self.assertEqual(state_at(appended, boundary)['boundary'], boundary)
            self.assertEqual(entity_context_at(appended, boundary),
                             _plain(receipts[boundary].inspection.entities))
        self.assertTrue(validate(decode(encode(appended))))

    def test_wire_omits_process_pointer_anchors(self):
        forbidden = {"object_identity", "ledger_identity", "target_anchors", "action_anchors"}
        stack = [self.log]
        while stack:
            value = stack.pop()
            if type(value) is dict:
                self.assertTrue(forbidden.isdisjoint(value))
                stack.extend(value.values())
            elif type(value) is list:
                stack.extend(value)

    def test_capture_is_read_only_and_does_not_import_arena_application(self):
        import sys
        from encounter_inspection import fingerprint
        encounter = self.demo["encounter"]
        before = tuple((id(row), fingerprint(row))
                       for row in encounter._atomic_interval_history)
        rng_before = self.demo["rng_owner"].state
        recaptured = capture(encounter)
        after = tuple((id(row), fingerprint(row))
                      for row in encounter._atomic_interval_history)
        self.assertEqual(before, after)
        self.assertEqual(rng_before, self.demo["rng_owner"].state)
        self.assertEqual(encode(recaptured), self.wire)
        for module in ("arena_browser_session", "arena_persistence",
                       "arena_native_snapshot", "arena_server", "npcgen"):
            self.assertNotIn(module, sys.modules)

    def test_corrupt_digest_preimage_duplicate_actions_and_reordering_refuse(self):
        corrupted = copy.deepcopy(self.log)
        corrupted["boundaries"][0]["events"]["action_ids"].append("foreign")
        with self.assertRaises(NativeHistoryRejected):
            validate(corrupted)
        bad_preimage = copy.deepcopy(self.log)
        change = next(row for row in bad_preimage["boundaries"][0]["changes"]
                      if row["before"] is True)
        change["before_value"] = "incorrect"
        # Re-seal the envelope to exercise semantic preimage validation.
        import hashlib
        import json
        unsigned = dict(bad_preimage)
        unsigned.pop("sha256")
        unsigned["sha256"] = hashlib.sha256(json.dumps(
            unsigned, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("ascii")).hexdigest()
        with self.assertRaises(NativeHistoryRejected):
            validate(unsigned)
        bad_entity_context = copy.deepcopy(self.log)
        self.assertTrue(bad_entity_context['entity_context']['changes'])
        bad_entity_context['entity_context']['changes'][0]['state_sha256'] = '0' * 64
        with self.assertRaisesRegex(NativeHistoryRejected, 'EntityInspection state digest'):
            validate(_seal({key: value for key, value in bad_entity_context.items()
                            if key != 'sha256'}))
        reordered = copy.deepcopy(self.log)
        reordered["boundaries"][0], reordered["boundaries"][1] = (
            reordered["boundaries"][1], reordered["boundaries"][0])
        with self.assertRaises(NativeHistoryRejected):
            validate(reordered)

    def test_standalone_write_does_not_overwrite_existing_artifact(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.json"
            write(self.log, path)
            before = path.read_bytes()
            with self.assertRaises(NativeHistoryRejected):
                write(self.log, path)
            self.assertEqual(path.read_bytes(), before)

    def test_interrupted_standalone_write_cleans_temp_and_allows_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'history.json'
            with patch('native_history.os.link', side_effect=OSError('injected prepublish fault')):
                with self.assertRaisesRegex(NativeHistoryRejected, 'before publication'):
                    write(self.log, path)
            self.assertFalse(path.exists())
            self.assertEqual(list(Path(directory).iterdir()), [])
            write(self.log, path)
            self.assertEqual(decode(path.read_bytes()), self.log)

    def test_append_accepts_only_the_next_authenticated_native_commit(self):
        demo = encounter_delta_headless.build_demo(until=4)
        encounter = demo["encounter"]
        log = capture(encounter)
        from activities import DelayAction
        action = DelayAction(encounter, encounter.being_list[1], defense=0,
                             start_time=4, id="append-delay")
        encounter.schedule_action(action)
        encounter.step(1)

        appended = append_committed(log, encounter)
        self.assertEqual(log["latest_boundary"], 4)  # immutable input
        self.assertEqual(appended["latest_boundary"], 5)
        self.assertEqual(events_at(appended, 5)["action_ids"], ["append-delay"])
        self.assertEqual(state_at(appended, 5)["boundary"], 5)
        self.assertTrue(validate(decode(encode(appended))))
        with self.assertRaisesRegex(NativeHistoryRejected, "no next committed"):
            append_committed(appended, encounter)

    def test_rolled_back_publication_has_no_appendable_history_receipt(self):
        demo = encounter_delta_headless.build_demo(until=4)
        encounter = demo["encounter"]
        recorder = NativeHistoryRecorder.attach(encounter)
        log = recorder.export()
        from activities import DelayAction
        action = DelayAction(encounter, encounter.being_list[1], defense=0,
                             start_time=4, id="rolled-back-delay")
        encounter.schedule_action(action)
        import atomic_publication
        publish = atomic_publication.publish_interval_candidate

        def fail_after_commit_marker(*args, **kwargs):
            kwargs["_fail_after"] = "mark_committed"
            return publish(*args, **kwargs)

        with patch.object(atomic_publication, "publish_interval_candidate",
                          fail_after_commit_marker):
            with self.assertRaises(atomic_publication.PublicationFailure):
                encounter.step(1)
        self.assertEqual(encounter.time, 4)
        self.assertEqual(recorder.latest_boundary, 4)
        self.assertIsNone(recorder.failure)
        self.assertEqual(log["latest_boundary"], 4)
        with self.assertRaisesRegex(NativeHistoryRejected,
                                    "no next committed boundary"):
            append_committed(log, encounter)

    def test_attached_recorder_appends_only_after_native_commit_returns(self):
        demo = encounter_delta_headless.build_demo(until=4)
        encounter = demo["encounter"]
        recorder = NativeHistoryRecorder.attach(encounter)
        from activities import DelayAction
        action = DelayAction(encounter, encounter.being_list[1], defense=0,
                             start_time=4, id="automatic-history-delay")
        encounter.schedule_action(action)
        encounter.step(1)
        log = recorder.export()
        self.assertEqual(recorder.latest_boundary, 5)
        self.assertEqual(events_at(log, 5)["action_ids"], [action.id])
        self.assertEqual(log, capture(encounter))

    def test_two_observers_keep_distinct_group_evidence_in_native_history(self):
        # This is a current native observation Action, not a fabricated
        # evidence row. The independently owned ledgers must remain separate
        # in the historical read model at the committed boundary.
        import test_encounter_inspection as fixtures
        from field_observation import BeliefLedger

        fixture = fixtures.InspectionFixture()
        fixture.setUp()
        group = fixture.f.f.f.group()
        fixture.enable()
        first_ledger = BeliefLedger(fixture.a.id)
        second_ledger = BeliefLedger(fixture.b.id)
        first = fixture.f.f.observe(fixture.a, group, ledger=first_ledger)
        second = fixture.f.f.observe(fixture.b, group, ledger=second_ledger)
        fixture.enc.schedule_choice((first, second))
        fixture.enc.step(1)

        log = decode(encode(capture(fixture.enc)))
        boundary = state_at(log, 1)
        evidence = {row["owner_id"]: row["projection"]
                    for row in boundary["recipients"]
                    if row["role"] == "in_world_belief_ledger"}
        self.assertEqual(set(evidence), {fixture.a.id, fixture.b.id})
        self.assertIn(first.id, events_at(log, 1)["action_ids"])
        self.assertIn(second.id, events_at(log, 1)["action_ids"])
        self.assertNotEqual(evidence[fixture.a.id], evidence[fixture.b.id])
        self.assertEqual(evidence[fixture.a.id]["observer_id"], fixture.a.id)
        self.assertEqual(evidence[fixture.b.id]["observer_id"], fixture.b.id)
        self.assertTrue(validate(log))


if __name__ == "__main__":
    unittest.main()
