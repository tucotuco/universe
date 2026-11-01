"""Inactive boundary-2 read dependency and identity preflight."""
from dataclasses import FrozenInstanceError, replace
import json
from pathlib import Path
import random
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tests'))

import atomic_publication
import checkpoint_restore_dependencies as dependencies
from checkpoint_binding import _NATIVE_BINDINGS, bind_quarantined_run_boundary
from checkpoint_projection import project_quarantined_run_boundary
from checkpoint_restore_preparation import (
    _host_authorize_trusted_local_restore, _prepare_trusted_local_restore)
from checkpoint_restore_dependencies import (
    RestoreDependencyRejected, create_prepared_boundary2_read_dependency,
    preflight_boundary2_identity_ids,
    _capture_prepared_boundary2_frozen_read,
    _validate_prepared_boundary2_frozen_read)
from checkpoint_wire import decode_run_spot_wire
from test_checkpoint_projection import committed_run_wire
from transactional_progression import TransactionalProgressionError


def prepared_fixture(wire=None):
    if wire is None:
        wire, _batch = committed_run_wire()
    decoded = decode_run_spot_wire(wire)
    projection = project_quarantined_run_boundary(decoded)
    binding = bind_quarantined_run_boundary(decoded, projection)
    approval = _host_authorize_trusted_local_restore(binding)
    prepared = _prepare_trusted_local_restore(binding, approval)
    return wire, binding, prepared


class TestPreparedBoundary2Dependencies(unittest.TestCase):
    def setUp(self):
        self.wire, self.binding, self.prepared = prepared_fixture()
        self.private = _NATIVE_BINDINGS[self.binding]
        self.native = dependencies._PREPARED_RESTORES[self.prepared]
        self.encounter = self.private.encounter
        self.book = self.encounter._choice_book
        self.prefix = self.prepared.view.imported_history.practice_prefix
        self.dependency = create_prepared_boundary2_read_dependency(self.prepared)
        self.next_choice = (f'{self.encounter.id}/draft/'
                            f'{self.prepared.view.minimum_next_draft_suffix}')

    def _snapshot(self):
        world, encounter, book = self.private.universe, self.encounter, self.book
        return (
            encounter.time, encounter.last_processed_boundary,
            encounter._coordinator_time, encounter._interval_start,
            encounter.active_boundary, encounter.boundary_fault,
            tuple(encounter.being_list), tuple(encounter.pending_action_list),
            tuple(encounter.finished_action_list), tuple(encounter.cancelled_action_list),
            encounter.awareness.copy(), book._counter, world._schedule_revision,
            tuple(book._drafts.items()), tuple(book._closed_drafts), tuple(book._tokens.items()),
            tuple(book._choices.items()), tuple(book._reservations),
            tuple(book._registered.items()), tuple(book._states.items()),
            tuple(world.event_history.items()), tuple(world.object_registry.object_instances.items()),
            self.private.rng_owner.state, random.getstate(),
            dict(atomic_publication._COMMITTED_RECEIPTS),
            tuple((being_id, tuple(being.skill_use_history),
                tuple(being.__dict__.get('_atomic_target_history', ())),
                dict(being.skill_experience), dict(being.current.skills.skills),
                dict(being._skill_practice_baselines))
                for being_id, being in self.private.beings),
            tuple(id(value) for value in (
                world.event_history, world.object_registry.object_instances,
                world._choice_books, encounter.being_list,
                encounter.pending_action_list, encounter.finished_action_list,
                encounter.cancelled_action_list, book._drafts, book._closed_drafts,
                book._tokens, book._choices, book._reservations,
                book._registered, book._states)))

    def _preflight(self, **overrides):
        args = dict(encounter_id=self.encounter.id,
            practice_target_id=self.prefix.target_id, choice_id=self.next_choice,
            action_ids=('prospective-run-a', 'prospective-run-b'), boundary=2)
        args.update(overrides)
        return preflight_boundary2_identity_ids(self.prepared, self.dependency, **args)

    def test_positive_dependency_and_future_id_preflight_are_detached_and_inert(self):
        before = self._snapshot()
        interval_staging = __import__('interval_staging')
        frozen_practice = __import__('frozen_practice')
        with patch.object(interval_staging, '_read_set',
                          side_effect=AssertionError('must not call live read set')), \
             patch.object(frozen_practice, 'capture_practice_inputs',
                          side_effect=AssertionError('must not wire live practice capture')):
            checked = self._preflight()
        after = self._snapshot()
        self.assertTrue(checked.accepted)
        self.assertEqual((checked.boundary, checked.encounter_id,
                          checked.practice_target_id, checked.choice_id, checked.action_ids),
                         (2, self.encounter.id, self.prefix.target_id, self.next_choice,
                          ('prospective-run-a', 'prospective-run-b')))
        self.assertEqual(self.dependency.imported_boundary, 1)
        self.assertEqual(self.dependency.prospective_boundary, 2)
        self.assertEqual(self.dependency.practice_prefix_digest, self.prefix.content_digest)
        self.assertEqual(self.dependency.practice_action_ids, self.prefix.action_ids)
        self.assertEqual(self.dependency.historical_choice_ids,
                         (self.binding.historical.choice_id,))
        self.assertEqual(self.dependency.historical_action_ids,
                         self.binding.historical.action_identity_ids)
        self.assertEqual(self.dependency.choice_counter_floor,
                         self.prepared.view.choice_counter_floor)
        self.assertEqual(self.dependency.minimum_next_draft_suffix,
                         self.prepared.view.minimum_next_draft_suffix)
        self.assertEqual(self.dependency.prepared_context_revision,
                         self.native.context_revision)
        self.assertEqual(self.dependency.identity_plan_digest,
                         self.prepared.view.identity_plan_digest)
        with self.assertRaises(FrozenInstanceError):
            self.dependency.practice_prefix_digest = 'changed'
        self.assertEqual(after, before)
        self.assertEqual(self.book._counter, self.prepared.view.choice_counter_floor)
        self.assertEqual(self.prefix.uses[0].experience, 4)
        self.assertEqual(len(self.prefix.uses), 1)
        target = dict(self.private.beings)[self.prefix.target_id]
        self.assertEqual(target.skill_experience['run'], 4)
        self.assertEqual(target.current.skills.skills.get('run', 0), 0)
        from action_evaluation import EffectIdentity
        from experience import BatchSkillUse
        from frozen_practice import CandidatePracticeUse, merge_imported_practice_uses
        later_cause = CandidatePracticeUse(
            EffectIdentity(self.encounter.id, 2, 'later-native-action', 'effect', 0),
            'run', 1, 'later-native-action', 2.25, 2, 'success')
        later_use = BatchSkillUse(self.prefix.target_id, 'run', 1, 0, 0, 2,
                                  (later_cause,))
        merged = merge_imported_practice_uses(
            self.prefix, self.prefix.target_id, (later_use,))
        self.assertEqual(len(merged), 2)
        self.assertEqual(tuple(row.action_id for row in merged[0].exercises),
                         self.prefix.action_ids)
        self.assertEqual(tuple(row.action_id for row in merged[1].exercises),
                         ('later-native-action',))
        self.assertTrue(self.prepared.quarantined)
        with self.assertRaises(TransactionalProgressionError):
            self.encounter.step(1)

    def test_stale_forged_cross_context_and_mismatched_root_dependencies_refuse(self):
        before = self._snapshot()
        forged = replace(self.dependency, practice_prefix_digest='0' * 64)
        forged = replace(forged, dependency_digest=dependencies._digest(
            dependencies._dependency_data(forged)))
        with self.assertRaises(RestoreDependencyRejected):
            self._preflight_dependency(forged)
        stale_revision = replace(self.dependency,
            prepared_context_revision=self.dependency.prepared_context_revision + 1)
        with self.assertRaises(RestoreDependencyRejected):
            self._preflight_dependency(stale_revision)

        _wire, _binding, other = prepared_fixture()
        with self.assertRaises(RestoreDependencyRejected):
            preflight_boundary2_identity_ids(other, self.dependency,
                encounter_id=other.view.binding_view.encounter_id,
                practice_target_id=other.view.imported_history.practice_prefix.target_id,
                choice_id=(f"{other.view.binding_view.encounter_id}/draft/"
                           f"{other.view.minimum_next_draft_suffix}"),
                action_ids=('other-action',))

        with self.assertRaises(RestoreDependencyRejected):
            self._preflight(encounter_id='foreign-encounter')
        with self.assertRaises(RestoreDependencyRejected):
            self._preflight(practice_target_id='foreign-target')
        with self.assertRaises(RestoreDependencyRejected):
            self._preflight(boundary=1)
        with self.assertRaises(RestoreDependencyRejected):
            self._preflight(boundary=3)
        self.assertEqual(self._snapshot(), before)

    def _frozen_read(self):
        check = self._preflight()
        import action_evaluation, interval_staging
        with patch.object(interval_staging, 'prepare_interval_candidate',
                          side_effect=AssertionError('must not stage an interval')), \
             patch.object(action_evaluation, 'evaluate_snapshot',
                          side_effect=AssertionError('must not evaluate Actions')), \
             patch.object(atomic_publication, 'publish_interval_candidate',
                          side_effect=AssertionError('must not publish')):
            return check, _capture_prepared_boundary2_frozen_read(
                self.prepared, self.dependency, check)

    def test_native_frozen_read_reuses_real_readset_and_practice_capture_inertly(self):
        before = self._snapshot()
        check, captured = self._frozen_read()
        after = self._snapshot()
        from frozen_practice import BatchSkillUse, FrozenBeingPractice
        target = captured.practice_inputs.beings[self.prefix.target_id]
        self.assertIs(type(target), FrozenBeingPractice)
        self.assertEqual((captured.schema, captured.boundary, captured.encounter_id,
                          captured.practice_target_id, captured.choice_id, captured.action_ids),
                         ('universe.prepared-boundary2-frozen-read/1', 2,
                          self.encounter.id, self.prefix.target_id, check.choice_id,
                          check.action_ids))
        self.assertEqual(captured.imported_prefix_digest, self.prefix.content_digest)
        self.assertEqual(captured.imported_prefix_schema, self.prefix.schema)
        batches = tuple(use for use in target.prior_uses if type(use) is BatchSkillUse)
        self.assertEqual(batches, self.prefix.uses)
        self.assertEqual(len(batches), 1)
        self.assertEqual(tuple(row.action_id for row in batches[0].exercises),
                         self.prefix.action_ids)
        self.assertEqual(tuple(row.effect_identity for row in batches[0].exercises),
                         tuple(row.effect_identity for row in self.prefix.uses[0].exercises))
        self.assertEqual((target.skill_experience['run'], target.ordinary_levels.get('run', 0)),
                         (4, 0))
        self.assertEqual(len(captured.practice_inputs.beings), 2)
        self.assertTrue(captured.native_read_set_digest)
        self.assertEqual(captured.native_read_set,
                         __import__('interval_staging')._read_set(self.encounter))
        self.assertEqual(after, before)
        from transactional_progression import is_quarantined
        self.assertTrue(self.prepared.quarantined and is_quarantined(self.encounter))
        self.assertEqual(self.encounter.pending_action_list, [])
        self.assertEqual(self.book._choices, {})
        self.assertEqual(self.book._registered, {})
        self.assertTrue(_validate_prepared_boundary2_frozen_read(
            self.prepared, self.dependency, check, captured))

        # Public diagnostic data is recursively detached: only primitives,
        # immutable containers, and frozen value records may escape.
        from dataclasses import fields, is_dataclass
        from types import MappingProxyType
        def assert_detached(value):
            if value is None or type(value) in (str, int, float, bool):
                return
            if type(value) in (tuple, frozenset):
                for item in value:
                    assert_detached(item)
                return
            if type(value) is MappingProxyType:
                for key, item in value.items():
                    assert_detached(key); assert_detached(item)
                return
            if is_dataclass(value):
                self.assertTrue(type(value).__dataclass_params__.frozen)
                for field in fields(value):
                    assert_detached(getattr(value, field.name))
                return
            self.fail(f'mutable/native handle escaped: {type(value)!r}')
        assert_detached(captured)

    def test_frozen_read_matches_ordinary_frozen_practice_except_imported_prefix(self):
        _check, captured = self._frozen_read()
        from action_evaluation import native_data, freeze
        from being import BeingInstance, BeingDefinition
        from skill import Skills
        from types import SimpleNamespace
        objects = self.private.universe.object_registry.object_instances
        ordinary_views = {}
        for key in self.encounter.being_list:
            data = native_data(objects[key], (BeingInstance,))
            current = native_data(data['current'], (BeingDefinition,))
            skills = native_data(current['skills'], (Skills,))
            ordinary_views[key] = SimpleNamespace(category='being', data={
                'skills': freeze(skills['skills']),
                'weapon_skills': freeze(skills['weapon_skills'])})
        from frozen_practice import capture_practice_inputs
        ordinary = capture_practice_inputs(self.private.universe, objects, ordinary_views)
        self.assertEqual(captured.practice_inputs.definitions, ordinary.definitions)
        for key, baseline in ordinary.beings.items():
            imported = captured.practice_inputs.beings[key]
            self.assertEqual((imported.ordinary_levels, imported.weapon_levels,
                              imported.baselines, imported.skill_experience,
                              imported.history),
                             (baseline.ordinary_levels, baseline.weapon_levels,
                              baseline.baselines, baseline.skill_experience,
                              baseline.history))
            self.assertEqual(imported.prior_uses,
                self.prefix.uses if key == self.prefix.target_id else baseline.prior_uses)

    def test_frozen_read_rejects_stale_snapshot_and_edited_preflight(self):
        check, captured = self._frozen_read()
        target = dict(self.private.beings)[self.prefix.target_id]
        original = target.skill_experience['run']
        target.skill_experience['run'] = original + 1
        try:
            with self.assertRaises(RestoreDependencyRejected):
                _validate_prepared_boundary2_frozen_read(
                    self.prepared, self.dependency, check, captured)
        finally:
            target.skill_experience['run'] = original
        # Empty future choices remain invalid; this bridge does not execute them.
        bad = replace(check, action_ids=())
        with self.assertRaises(RestoreDependencyRejected):
            _capture_prepared_boundary2_frozen_read(self.prepared, self.dependency, bad)
        forged = replace(self.dependency, practice_prefix_digest='0' * 64)
        with self.assertRaises(RestoreDependencyRejected):
            _capture_prepared_boundary2_frozen_read(self.prepared, forged, check)
        rng = self.private.rng_owner
        original_state = rng.state
        rng.state = random.Random(77).getstate()
        try:
            with self.assertRaises(RestoreDependencyRejected):
                _validate_prepared_boundary2_frozen_read(
                    self.prepared, self.dependency, check, captured)
        finally:
            rng.state = original_state

    def _preflight_dependency(self, dependency):
        return preflight_boundary2_identity_ids(self.prepared, dependency,
            encounter_id=self.encounter.id,
            practice_target_id=self.prefix.target_id,
            choice_id=self.next_choice,
            action_ids=('prospective-run-a', 'prospective-run-b'), boundary=2)

    def test_duplicate_historical_and_live_namespace_collisions_refuse(self):
        before = self._snapshot()
        cases = (
            {'choice_id': self.binding.historical.choice_id},
            {'action_ids': (self.prefix.action_ids[0],)},
            {'action_ids': ('duplicate', 'duplicate')},
            {'action_ids': ('0',)},
            {'action_ids': (self.encounter.id,)},
        )
        for changes in cases:
            with self.subTest(changes=changes), self.assertRaises(RestoreDependencyRejected):
                self._preflight(**changes)
        self.assertEqual(self._snapshot(), before)

    def test_native_prefix_rng_or_counter_drift_invalidates_dependency(self):
        before = self._snapshot()
        target = dict(self.private.beings)[self.prefix.target_id]
        original_xp = target.skill_experience['run']
        target.skill_experience['run'] = original_xp + 1
        try:
            with self.assertRaises(RestoreDependencyRejected):
                self._preflight()
        finally:
            target.skill_experience['run'] = original_xp

        action = dict(self.private.actions)[self.prefix.action_ids[0]]
        original_minimum = action.minimum_distance
        action.minimum_distance = original_minimum + 0.125
        try:
            with self.assertRaises(RestoreDependencyRejected):
                self._preflight()
        finally:
            action.minimum_distance = original_minimum

        original_counter = self.book._counter
        self.book._counter = original_counter + 1
        try:
            with self.assertRaises(RestoreDependencyRejected):
                self._preflight()
        finally:
            self.book._counter = original_counter
        self.assertEqual(self._snapshot(), before)

    def test_separate_process_wire_to_prepared_dependency_and_identity_preflight(self):
        source_projection = project_quarantined_run_boundary(decode_run_spot_wire(self.wire))
        expected_choice = (f"{source_projection.encounter_id}/draft/"
                           f"{int(source_projection.committed_choices[0][0].rsplit('/', 1)[1]) + 1}")
        script = r'''
import json,random,sys
sys.path.insert(0,sys.argv[1])
from checkpoint_wire import decode_run_spot_wire
from checkpoint_projection import project_quarantined_run_boundary
from checkpoint_binding import bind_quarantined_run_boundary
from checkpoint_restore_preparation import (_host_authorize_trusted_local_restore,
 _prepare_trusted_local_restore)
from checkpoint_restore_dependencies import (create_prepared_boundary2_read_dependency,
 preflight_boundary2_identity_ids, _capture_prepared_boundary2_frozen_read)
from atomic_publication import _COMMITTED_RECEIPTS
module_rng=random.getstate(); receipts=dict(_COMMITTED_RECEIPTS)
d=decode_run_spot_wire(sys.stdin.buffer.read()); p=project_quarantined_run_boundary(d)
b=bind_quarantined_run_boundary(d,p)
r=_prepare_trusted_local_restore(b,_host_authorize_trusted_local_restore(b))
dep=create_prepared_boundary2_read_dependency(r)
prefix=r.view.imported_history.practice_prefix
choice=f'{dep.encounter_id}/draft/{dep.minimum_next_draft_suffix}'
check=preflight_boundary2_identity_ids(r,dep,encounter_id=dep.encounter_id,
 practice_target_id=dep.practice_target_id,choice_id=choice,
 action_ids=('new-run-a','new-run-b'))
frozen=_capture_prepared_boundary2_frozen_read(r,dep,check)
practice=frozen.practice_inputs.beings[prefix.target_id]
assert len(practice.prior_uses)==1 and practice.prior_uses[0]==prefix.uses[0]
assert practice.skill_experience['run']==4 and practice.ordinary_levels.get('run',0)==0
assert random.getstate()==module_rng and dict(_COMMITTED_RECEIPTS)==receipts
print(json.dumps({'encounter':dep.encounter_id,'target':dep.practice_target_id,
 'prefix':dep.practice_prefix_digest,'revision':dep.prepared_context_revision,
 'boundary':check.boundary,'choice':check.choice_id,
 'actions':check.action_ids,'counter':dep.choice_counter_floor,
 'imported_uses':len(practice.prior_uses),'readset':frozen.native_read_set_digest,
 'quarantined':r.quarantined}))
'''
        run = subprocess.run([sys.executable, '-c', script, str(ROOT / 'src')],
            input=self.wire, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            check=True, cwd=str(ROOT))
        result = json.loads(run.stdout)
        self.assertEqual(result['encounter'], self.dependency.encounter_id)
        self.assertEqual(result['target'], self.prefix.target_id)
        self.assertEqual(result['boundary'], 2)
        self.assertEqual(result['choice'], expected_choice)
        self.assertEqual(result['imported_uses'], 1)
        self.assertTrue(result['readset'])
        self.assertTrue(result['quarantined'])


if __name__ == '__main__':
    unittest.main()
