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
import test_encounter_inspection as inspection_fixtures


def _legacy_shape(body):
    """Strip fields introduced by history `/7` when constructing old fixtures."""
    body.pop("receipt_facts_complete", None)
    body.pop("observer_knowledge", None)
    for row in body.get("boundaries", ()):
        row.pop("notification_intents", None)
        row.pop("disarm_landings", None)
        row.pop("receipt_facts_available", None)
        if row.get("kind") == "quiet_span":
            row.pop("receipt_facts_available", None)
    return body
from native_history import (NativeHistoryRejected, capture, decode, encode,
                            append_committed, events_at, state_at, validate,
                            NativeHistoryRecorder, write, rng_state_at, upgrade,
                            NativeHistoryQuery, entity_context_at, LEGACY_SCHEMA, PREVIOUS_SCHEMA,
                            QUIET_SPAN_SCHEMA, ENTITY_CONTEXT_SCHEMA, FATIGUE_CONTEXT_SCHEMA,
                            INITIAL_RNG_SCHEMA, SCHEMA, SAME_RNG, _seal,
                            fatigue_context_at, committed_actions_at, observer_facts_at,
                            entity_at, entity_history_at, objective_at,
                            objective_use_at, schedule_at, action_state_at,
                            choice_state_at, _plain, _expand_rows, _target_candidates)


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
        query = NativeHistoryQuery(log)
        target_rows = {}
        for boundary in range(1, 5):
            expected = _target_candidates(self.demo["encounter"]).get(boundary, {})
            self.assertEqual(state_at(log, boundary)["entities"], _plain(expected))
            target_rows[boundary] = expected
            for target_id, candidate in expected.items():
                self.assertEqual(query.target_at(target_id, boundary), _plain(candidate))
            receipt = next(row for row in self.demo["encounter"]._atomic_interval_history
                           if row.boundary == boundary)
            self.assertEqual(entity_context_at(log, boundary),
                             _plain(receipt.inspection.entities))
            self.assertEqual(events_at(log, boundary)["action_ids"], list(receipt.action_ids))
            self.assertEqual(NativeHistoryQuery(log).notification_intents_at(boundary),
                             _plain(receipt.notification_intents))
        for target_id in target_rows[1]:
            expected_history = [
                {"boundary": boundary, "state": _plain(rows[target_id])}
                for boundary, rows in target_rows.items() if target_id in rows]
            self.assertEqual(query.target_history_at(target_id), expected_history)

    def test_per_entity_inspection_history_matches_each_native_receipt(self):
        query = NativeHistoryQuery(self.log)
        entity_ids = set(self.log["entity_context"]["initial"])
        for boundary in range(self.log["latest_boundary"] + 1):
            actual = query.entity_context_at(boundary)
            receipts = self.demo["encounter"]._atomic_interval_history
            expected = _plain(receipts[max(0, boundary - 1)].inspection.entities)
            self.assertEqual(actual, expected)
            self.assertEqual(set(actual), entity_ids)
            for entity_id in entity_ids:
                self.assertEqual(query.entity_at(entity_id, boundary), actual[entity_id])
                self.assertEqual(entity_at(self.log, entity_id, boundary), actual[entity_id])
        entity_id = sorted(entity_ids)[0]
        expected_history = [
            {"boundary": boundary, "entity": query.entity_at(entity_id, boundary)}
            for boundary in range(self.log["latest_boundary"] + 1)]
        self.assertEqual(query.entity_history_at(entity_id), expected_history)
        self.assertEqual(entity_history_at(self.log, entity_id), expected_history)
        detached = query.entity_at(entity_id, 0)
        detached.clear()
        self.assertTrue(query.entity_at(entity_id, 0))
        self.assertIsNone(query.entity_at("unregistered-entity", 0))

    def test_legacy_entity_history_is_unavailable_not_inferred(self):
        legacy = _legacy_shape({key: copy.deepcopy(value) for key, value in self.log.items()
                                if key not in ("sha256", "entity_context")})
        legacy["schema"] = LEGACY_SCHEMA
        legacy["initial"].pop("rng_before_first_commit")
        previous = None
        for row in legacy["boundaries"]:
            if row["rng_after"] == SAME_RNG:
                row["rng_after"] = (rng_state_at(self.log, row["boundary"])
                                    if previous is None else previous)
            previous = row["rng_after"]
        legacy = _seal({key: value for key, value in legacy.items() if key != "sha256"})
        legacy = upgrade(legacy)
        query = NativeHistoryQuery(legacy)
        identity = next(iter(self.log["entity_context"]["initial"]))
        self.assertIsNone(query.entity_at(identity, 0))
        self.assertIsNone(query.entity_history_at(identity))

    def test_objective_fact_and_use_queries_match_committed_group_observation(self):
        fixture = inspection_fixtures.InspectionFixture()
        fixture.setUp()
        group = fixture.f.f.f.group()
        fixture.enable()
        from field_observation import BeliefLedger
        observation = fixture.f.f.observe(
            fixture.a, group, ledger=BeliefLedger(fixture.a.id))
        fixture.enc.schedule_choice((observation,))
        fixture.enc.step(1)
        log = capture(fixture.enc)
        query = NativeHistoryQuery(log)
        self.assertEqual(query.objective_at(0), {})
        self.assertEqual(query.objective_use_at(0), {"$tuple": []})
        receipt = fixture.enc._atomic_interval_history[0]
        self.assertEqual(query.objective_at(1), _plain(receipt.inspection.objective))
        self.assertEqual(objective_at(log, 1), _plain(receipt.inspection.objective))
        self.assertEqual(query.objective_use_at(1), _plain(receipt.inspection.objective_use))
        self.assertEqual(objective_use_at(log, 1), _plain(receipt.inspection.objective_use))
        self.assertTrue(query.objective_at(1))
        self.assertTrue(query.objective_use_at(1))
        detached = query.objective_at(1)
        detached.clear()
        self.assertTrue(query.objective_at(1))

    def test_schedule_query_preserves_finished_and_future_accepted_choice_states(self):
        fixture = inspection_fixtures.InspectionFixture()
        fixture.setUp()
        fixture.enable()
        from activities import DelayAction, RunAction
        first = RunAction(fixture.world, fixture.a.id, 0, 1, .5, experience=1)
        second = DelayAction(fixture.enc, fixture.b.id, defense=0, start_time=0)
        future = RunAction(fixture.world, fixture.c.id, 3, 1, .5, experience=1)
        for action in (first, second, future):
            fixture.enc.schedule_action(action)
        fixture.enc.step(1)
        log = capture(fixture.enc)
        query = NativeHistoryQuery(log)
        expected = _plain(fixture.enc._atomic_interval_history[0].inspection.schedule)
        self.assertEqual(query.schedule_at(1), expected)
        self.assertEqual(schedule_at(log, 1), expected)
        fields_value = expected["fields"]
        self.assertEqual(query.action_state_at(first.id, 1), "finished")
        self.assertEqual(query.action_state_at(second.id, 1), "finished")
        self.assertIsNone(query.action_state_at(future.id, 1))
        accepted = [identity for identity, state in fields_value["choice_states"].items()
                    if state == "accepted"]
        self.assertTrue(accepted)
        self.assertEqual(query.choice_state_at(accepted[0], 1), "accepted")
        self.assertEqual(choice_state_at(log, accepted[0], 1), "accepted")
        self.assertIsNone(query.choice_state_at("unregistered-choice", 1))

    def test_committed_action_effect_read_model_matches_inspection_at_each_boundary(self):
        log = decode(self.wire)
        query = NativeHistoryQuery(log)
        actual_by_boundary = {}
        for boundary in range(log["latest_boundary"] + 1):
            actual = committed_actions_at(log, boundary)
            actual_by_boundary[boundary] = actual
            self.assertEqual(query.committed_actions_at(boundary), actual)
            if boundary == 0:
                self.assertEqual(actual["action_ids"], [])
                self.assertEqual(actual["effect_ids"], [])
                self.assertEqual(actual["actions"], {})
                self.assertEqual(actual["effects"], {})
                continue
            inspection = self.demo["encounter"].inspect_committed(boundary)
            self.assertEqual(actual["actions"], _plain(inspection.actions))
            for action_id in inspection.actions:
                self.assertEqual(query.committed_action_at(action_id, boundary),
                                 _plain(inspection.actions[action_id]))
            self.assertEqual(actual["effects"], _plain(inspection.effects))
            self.assertEqual(actual["action_ids"],
                             [identity for row in inspection.timeline
                              for identity in row.action_ids])
            self.assertEqual(actual["effect_ids"],
                             [_plain(identity) for row in inspection.timeline
                              for identity in row.effect_ids])
        # Out-of-order queries reset the bounded fold and remain exact.
        for boundary in reversed(range(log["latest_boundary"] + 1)):
            self.assertEqual(query.committed_actions_at(boundary),
                             actual_by_boundary[boundary])
        detached = query.committed_actions_at(log["latest_boundary"])
        detached["actions"].clear()
        self.assertTrue(query.committed_actions_at(log["latest_boundary"])["actions"])

    def test_initial_native_state_and_entity_facts_are_queryable_at_boundary_zero(self):
        expected_state = {
            "encounter_id": self.log["initial"]["encounter_id"],
            "universe_id": self.log["initial"]["universe_id"],
            "start": self.log["initial"]["start"],
            "entities": self.log["initial"]["entities"],
            "participants": self.log["initial"]["participants"],
            "initial_schedule": self.log["initial"]["initial_schedule"],
            "boundary": None,
            "time": self.log["initial"]["start"],
            "schedule": self.log["initial"]["initial_schedule"],
            "objective": {},
            "objective_use": {"$tuple": []},
            "recipients": {},
            "projectile_states": {},
        }
        expected_events = {"action_ids": [], "effect_ids": [], "actions": {},
                           "effects": {}, "starts": {"$tuple": []},
                           "participants": self.log["initial"]["participants"]}
        query = NativeHistoryQuery(self.log)
        self.assertEqual(state_at(self.log, 0), expected_state)
        self.assertEqual(query.state_at(0), expected_state)
        self.assertEqual(entity_context_at(self.log, 0),
                         self.log["entity_context"]["initial"])
        self.assertEqual(query.entity_context_at(0),
                         self.log["entity_context"]["initial"])
        self.assertEqual(fatigue_context_at(self.log, 0),
                         query.fatigue_context_at(0))
        self.assertEqual(events_at(self.log, 0), expected_events)
        self.assertEqual(query.events_at(0), expected_events)
        self.assertEqual(rng_state_at(self.log, 0),
                         self.log["initial"]["rng_before_first_commit"])
        self.assertEqual(query.rng_state_at(0), rng_state_at(self.log, 0))
        self.assertEqual(query.observer_knowledge_at(0), {})
        source = copy.deepcopy(self.log)
        detached_state = state_at(source, 0)
        detached_events = events_at(source, 0)
        detached_state["entities"].clear()
        detached_events["participants"]["$tuple"].clear()
        self.assertTrue(source["initial"]["entities"])
        self.assertTrue(source["initial"]["participants"]["$tuple"])

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

            def committed_actions_at(self, _boundary):
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
        previous = rng_state_at(log, 0)
        for boundary, row in enumerate(log['boundaries'], 1):
            current = rng_state_at(log, boundary)
            if current == previous:
                self.assertEqual(row['rng_after'], SAME_RNG)
            else:
                self.assertNotEqual(row['rng_after'], SAME_RNG)
            previous = current

        legacy = _legacy_shape({key: copy.deepcopy(value) for key, value in log.items()
                  if key not in ('sha256', 'entity_context')})
        legacy['schema'] = LEGACY_SCHEMA
        legacy['initial'].pop('rng_before_first_commit')
        previous = None
        for row in legacy['boundaries']:
            if row['rng_after'] == SAME_RNG:
                row['rng_after'] = (rng_state_at(log, row['boundary'])
                                    if previous is None else previous)
            previous = row['rng_after']
        legacy = _seal({key: value for key, value in legacy.items()
                        if key != 'sha256'})
        self.assertTrue(validate(legacy))
        upgraded_legacy = upgrade(legacy)
        self.assertEqual(encode(upgraded_legacy),
                         encode(__import__('native_history')._without_entity_context(log)))
        self.assertIsNone(entity_context_at(upgraded_legacy, 4))
        self.assertIsNone(fatigue_context_at(upgraded_legacy, 4))
        self.assertIsNone(NativeHistoryQuery(upgraded_legacy).observer_knowledge_at(4))

        old_context = __import__('native_history')._without_fatigue_context(log)
        old_context_body = _legacy_shape({key: copy.deepcopy(value) for key, value in old_context.items()
                            if key != 'sha256'})
        old_context_body['schema'] = ENTITY_CONTEXT_SCHEMA
        old_context_body['entity_context'].pop('fatigue_available')
        old_context_body['initial'].pop('rng_before_first_commit')
        old_context = _seal(old_context_body)
        self.assertTrue(validate(old_context))
        upgraded_context = upgrade(old_context)
        self.assertEqual(upgraded_context['schema'], SCHEMA)
        self.assertFalse(upgraded_context['entity_context']['fatigue_available'])
        self.assertIsNone(fatigue_context_at(upgraded_context, 4))
        self.assertEqual(entity_context_at(upgraded_context, 4),
                         entity_context_at(old_context, 4))

        fatigue_schema = _legacy_shape({key: copy.deepcopy(value) for key, value in log.items()
                          if key != 'sha256'})
        fatigue_schema['schema'] = FATIGUE_CONTEXT_SCHEMA
        fatigue_schema['initial'].pop('rng_before_first_commit')
        fatigue_schema['boundaries'] = _expand_rows(log)
        _legacy_shape({"boundaries": fatigue_schema['boundaries']})
        for index, row in enumerate(fatigue_schema['boundaries']):
            actual = rng_state_at(log, row['boundary'])
            row['rng_after'] = (actual if index == 0 else
                                SAME_RNG if actual == rng_state_at(log, index)
                                else actual)
        fatigue_schema = _seal(fatigue_schema)
        self.assertTrue(validate(fatigue_schema))
        self.assertIsNone(upgrade(fatigue_schema)['initial']['rng_before_first_commit'])

        prior_fatigue = __import__('native_history')._without_initial_rng(log)
        prior_fatigue_body = _legacy_shape({key: copy.deepcopy(value)
                              for key, value in prior_fatigue.items()
                              if key != 'sha256'})
        prior_fatigue_body['schema'] = FATIGUE_CONTEXT_SCHEMA
        prior_fatigue_body['initial'].pop('rng_before_first_commit')
        prior_fatigue = _seal(prior_fatigue_body)
        self.assertTrue(validate(prior_fatigue))
        upgraded_fatigue = upgrade(prior_fatigue)
        self.assertIsNone(upgraded_fatigue['initial']['rng_before_first_commit'])
        with self.assertRaisesRegex(NativeHistoryRejected,
                                    'initial RNG cursor is not recorded'):
            rng_state_at(upgraded_fatigue, 0)
        for boundary in range(1, log['latest_boundary'] + 1):
            self.assertEqual(state_at(upgraded_fatigue, boundary),
                             state_at(log, boundary))
            self.assertEqual(events_at(upgraded_fatigue, boundary),
                             events_at(log, boundary))

        previous_schema = _legacy_shape({key: copy.deepcopy(value) for key, value in log.items()
                           if key not in ('sha256', 'entity_context')})
        previous_schema['schema'] = PREVIOUS_SCHEMA
        previous_schema['initial'].pop('rng_before_first_commit')
        previous = None
        for row in previous_schema['boundaries']:
            if row['rng_after'] == SAME_RNG:
                row['rng_after'] = (rng_state_at(log, row['boundary'])
                                    if previous is None else previous)
            previous = row['rng_after']
        previous_schema = _seal({key: value for key, value in previous_schema.items()
                                  if key != 'sha256'})
        self.assertTrue(validate(previous_schema))
        self.assertEqual(encode(upgrade(previous_schema)),
                         encode(__import__('native_history')._without_entity_context(log)))

        quiet_schema = _legacy_shape({key: copy.deepcopy(value) for key, value in log.items()
                        if key not in ('sha256', 'entity_context')})
        quiet_schema['schema'] = QUIET_SPAN_SCHEMA
        quiet_schema['initial'].pop('rng_before_first_commit')
        quiet_schema['boundaries'] = _expand_rows(log)
        _legacy_shape({"boundaries": quiet_schema['boundaries']})
        for index, row in enumerate(quiet_schema['boundaries']):
            actual = rng_state_at(log, row['boundary'])
            row['rng_after'] = (actual if index == 0 else
                                SAME_RNG if actual == rng_state_at(log, index)
                                else actual)
        quiet_schema['boundaries'] = __import__('native_history')._compact_quiet_rows(
            quiet_schema['boundaries'])
        quiet_schema = _seal(quiet_schema)
        self.assertEqual(encode(upgrade(quiet_schema)),
                         encode(__import__('native_history')._without_entity_context(log)))

        corrupt = copy.deepcopy(log)
        corrupt['initial']['rng_before_first_commit'] = None
        corrupt['boundaries'][0]['rng_after'] = dict(SAME_RNG)
        with self.assertRaisesRegex(NativeHistoryRejected, 'RNG reference'):
            validate(_seal({key: value for key, value in corrupt.items()
                            if key != 'sha256'}))

        corrupt_origin = copy.deepcopy(log)
        corrupt_origin['initial']['rng_before_first_commit']['$tuple'][0] = 99
        with self.assertRaisesRegex(NativeHistoryRejected, 'RNG cursor is invalid'):
            validate(_seal({key: value for key, value in corrupt_origin.items()
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
        previous_schema = _legacy_shape({key: copy.deepcopy(value) for key, value in log.items()
                           if key not in ('sha256', 'entity_context')})
        previous_schema['schema'] = PREVIOUS_SCHEMA
        previous_schema['initial'].pop('rng_before_first_commit')
        previous_schema['boundaries'] = _expand_rows(log)
        _legacy_shape({"boundaries": previous_schema['boundaries']})
        for row in previous_schema['boundaries']:
            row['rng_after'] = rng_state_at(log, row['boundary'])
        previous_schema = _seal({key: value for key, value in previous_schema.items()
                                  if key != 'sha256'})
        self.assertTrue(validate(previous_schema))
        self.assertEqual(encode(upgrade(previous_schema)),
                         encode(__import__('native_history')._without_entity_context(log)))
        quiet_span_schema = _legacy_shape({key: copy.deepcopy(value) for key, value in log.items()
                             if key not in ('sha256', 'entity_context')})
        quiet_span_schema['schema'] = QUIET_SPAN_SCHEMA
        quiet_span_schema['initial'].pop('rng_before_first_commit')
        quiet_span_schema['boundaries'] = _expand_rows(log)
        _legacy_shape({"boundaries": quiet_span_schema['boundaries']})
        for index, row in enumerate(quiet_span_schema['boundaries']):
            actual = rng_state_at(log, row['boundary'])
            row['rng_after'] = (actual if index == 0 else
                                SAME_RNG if actual == rng_state_at(log, index)
                                else actual)
        quiet_span_schema['boundaries'] = __import__('native_history')._compact_quiet_rows(
            quiet_span_schema['boundaries'])
        _legacy_shape({"boundaries": quiet_span_schema['boundaries']})
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

    def test_schema_six_upgrade_preserves_rng_and_marks_receipt_facts_unavailable(self):
        log = capture(encounter_delta_headless.build_demo(until=4)["encounter"])
        body = {key: copy.deepcopy(value) for key, value in log.items()
                if key != "sha256"}
        body.pop("receipt_facts_complete")
        body.pop("observer_knowledge")
        body["schema"] = INITIAL_RNG_SCHEMA
        for row in body["boundaries"]:
            row.pop("notification_intents", None)
            row.pop("disarm_landings", None)
            row.pop("receipt_facts_available", None)
        legacy_six = _seal(body)
        self.assertTrue(validate(legacy_six))
        upgraded = upgrade(legacy_six)
        self.assertEqual(upgraded["schema"], SCHEMA)
        self.assertEqual(upgraded["initial"]["rng_before_first_commit"],
                         log["initial"]["rng_before_first_commit"])
        self.assertEqual(rng_state_at(upgraded, 0), rng_state_at(log, 0))
        self.assertFalse(upgraded["receipt_facts_complete"])
        self.assertIsNone(NativeHistoryQuery(upgraded).receipt_facts_at(4))

    def test_appending_after_schema_six_keeps_known_and_unknown_receipts_distinct(self):
        from activities import DelayAction
        encounter = encounter_delta_headless.build_demo(until=4)["encounter"]
        current = capture(encounter)
        body = {key: copy.deepcopy(value) for key, value in current.items()
                if key != "sha256"}
        body.pop("receipt_facts_complete")
        body.pop("observer_knowledge")
        body["schema"] = INITIAL_RNG_SCHEMA
        for row in body["boundaries"]:
            row.pop("notification_intents", None)
            row.pop("disarm_landings", None)
            row.pop("receipt_facts_available", None)
        upgraded = upgrade(_seal(body))
        actor = encounter.being_list[1]
        encounter.schedule_action(DelayAction(
            encounter, actor, defense=0, start_time=encounter.time,
            id="history-v6-followup-delay"))
        encounter.step(1)
        appended = append_committed(upgraded, encounter)
        query = NativeHistoryQuery(appended)
        self.assertIsNone(query.receipt_facts_at(4))
        self.assertEqual(query.receipt_facts_at(5), {
            "notification_intents": {"$tuple": []},
            "disarm_landings": {"$tuple": []}})
        self.assertFalse(appended["receipt_facts_complete"])

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
        first_only = observer_facts_at(log, 1, fixture.a.id)
        second_only = observer_facts_at(log, 1, fixture.b.id)
        self.assertEqual([row["owner_id"] for row in first_only], [fixture.a.id])
        self.assertEqual([row["owner_id"] for row in second_only], [fixture.b.id])
        self.assertEqual(first_only[0]["projection"], evidence[fixture.a.id])
        self.assertEqual(second_only[0]["projection"], evidence[fixture.b.id])
        self.assertEqual(observer_facts_at(log, 1, "unknown-observer"), [])
        self.assertTrue(validate(log))


if __name__ == "__main__":
    unittest.main()
