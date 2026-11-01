"""Inactive read-dependency and identity preflight for prospective boundary 2.

This is not an IntervalCandidate and has no scheduling, evaluation, publication,
or progression entry point. Its digests detect stale local inputs; they are not
checkpoint authentication.
"""
from dataclasses import dataclass
import hashlib
import json
from types import MappingProxyType
from weakref import WeakKeyDictionary

from checkpoint_restore_preparation import (
    QuarantinedTrustedLocalRestore, RestorePreparationRejected,
    _PREPARED_RESTORES, _preflight_preparation)
from checkpoint_identity_reservations import (
    IdentityReservationRejected, validate_future_identity_ids)
from frozen_practice import ImportedPracticeRejected


class RestoreDependencyRejected(ValueError):
    """Prepared state, dependency token, or proposed identities are stale/invalid."""


@dataclass(frozen=True, eq=False)
class PreparedBoundary2ReadDependency:
    schema: str
    prepared_context_revision: int
    universe_id: str
    encounter_id: str
    imported_boundary: int
    prospective_boundary: int
    practice_target_id: str
    practice_prefix_schema: str
    practice_prefix_digest: str
    practice_action_ids: tuple
    historical_choice_ids: tuple
    historical_action_ids: tuple
    historical_event_ids: tuple
    choice_counter_floor: int
    minimum_next_draft_suffix: int
    identity_plan_digest: str
    prepared_native_read_digest: str
    dependency_digest: str


@dataclass(frozen=True)
class ProspectiveBoundary2IdentityPreflight:
    schema: str
    dependency_digest: str
    prepared_context_revision: int
    boundary: int
    encounter_id: str
    practice_target_id: str
    choice_id: str
    action_ids: tuple
    accepted: bool


@dataclass(frozen=True)
class PreparedBoundary2FrozenRead:
    """Detached diagnostic capture; not an EvaluationSnapshot or candidate."""
    schema: str
    prepared_context_revision: int
    dependency_digest: str
    imported_prefix_schema: str
    imported_prefix_digest: str
    boundary: int
    encounter_id: str
    practice_target_id: str
    choice_id: str
    action_ids: tuple
    native_read_set_digest: str
    native_read_set: tuple
    practice_inputs: object


@dataclass(frozen=True)
class _PreparedContinuationContext:
    """Private frozen authority binding for the one post-preflight interval."""
    prepared_context_revision: int
    dependency_digest: str
    imported_prefix_schema: str
    imported_prefix_digest: str
    identity_plan_digest: str
    choice_counter_floor: int
    historical_choice_ids: tuple
    historical_action_ids: tuple
    future_choice_id: str
    future_action_ids: tuple
    imported_prefix: object
    frozen_read_digest: str

    def evaluation_binding(self):
        return (self.prepared_context_revision, self.dependency_digest,
                self.imported_prefix_schema, self.imported_prefix_digest,
                self.identity_plan_digest, self.choice_counter_floor, self.historical_choice_ids,
                self.historical_action_ids, self.future_choice_id,
                self.future_action_ids, self.frozen_read_digest)


_ISSUED_DEPENDENCIES = WeakKeyDictionary()  # token -> exact prepared-context handle


def _dependency_data(value):
    return (value.schema, value.prepared_context_revision, value.universe_id,
            value.encounter_id, value.imported_boundary, value.prospective_boundary,
            value.practice_target_id, value.practice_prefix_schema,
            value.practice_prefix_digest, value.practice_action_ids,
            value.historical_choice_ids, value.historical_action_ids,
            value.historical_event_ids, value.choice_counter_floor,
            value.minimum_next_draft_suffix, value.identity_plan_digest,
            value.prepared_native_read_digest)


def _digest(value):
    raw = json.dumps(value, ensure_ascii=True, sort_keys=True,
                     separators=(',', ':'), allow_nan=False)
    return hashlib.sha256(raw.encode('ascii')).hexdigest()


def _native_read_digest(prepared, private, prefix, plan):
    """Fingerprint the source-reviewed Run graph without exposing native refs.

    Prepared Beings are compared with the immutable binding view. The one
    historical RunAction is checked against its detached declaration and
    identity/effect links before its legitimate Run fields enter the digest.
    Process-local alias/container identities remain private to this digest.
    """
    from checkpoint_binding import _being_state_snapshot, _data_number
    from activities import RunAction
    binding, native = private.binding, private.native
    world, encounter = native.universe, native.encounter
    book = encounter._choice_book
    beings = dict(native.beings)
    targets = {row.target_id: row for row in binding.historical.projection.targets}
    bound_views = {row.logical_id: row for row in binding.view.beings}
    being_states = []
    for being_id in sorted(beings):
        being = beings[being_id]
        state = _being_state_snapshot(being, targets[being_id])
        if state != bound_views[being_id].state:
            raise RestoreDependencyRejected('prepared Being state differs from its immutable binding view')
        being_states.append((being_id, id(being), state,
            tuple(being.skill_use_history),
            tuple(being.__dict__.get('_atomic_target_history', ()))))
    event_rows = tuple((key, id(value)) for key, value in world.event_history.items())
    object_rows = tuple((key, id(value))
                        for key, value in world.object_registry.object_instances.items())
    projected_actions = {row.action_id: row
                         for row in binding.historical.projection.actions}
    action_views = {row.logical_id: row for row in binding.view.actions}
    if (len(native.actions) != 1 or len(projected_actions) != 1
            or set(dict(native.actions)) != set(projected_actions)
            or set(action_views) != set(projected_actions)):
        raise RestoreDependencyRejected('prepared graph must contain its one projected RunAction')
    action_rows = []
    for action_id, action in native.actions:
        projected = projected_actions[action_id]
        action_view = action_views[action_id]
        declaration = dict(projected.declaration)
        try:
            parameters = dict(declaration['parameters'])
            expected_start_position = tuple(_data_number(value, 'Run start position')
                for value in parameters['start_position'][1])
            expected_strategy = tuple((key, _data_number(value, 'Run strategy'))
                for key, value in declaration['strategy'])
            actual_strategy = tuple((key, getattr(action.strategy, key))
                for key, _value in expected_strategy)
            actual_start_position = tuple(action.start_position.as_tuple())
        except (AttributeError, IndexError, KeyError, TypeError, ValueError) as exc:
            raise RestoreDependencyRejected('prepared RunAction declaration is malformed') from exc
        if (type(action) is not RunAction or action.id != action_id
                or action.universe is not world or action.event_type != 'run'
                or action.actor_id != projected.actor_id
                or projected.actor_id not in beings or action.target_id is not None
                or action.instrument_id is not None
                or action.parent_event_id != encounter.id
                or action.start_time != _data_number(projected.start, 'Run start')
                or action.end_time != _data_number(projected.end, 'Run end')
                or action.minimum_distance != _data_number(
                    parameters['minimum_distance'], 'Run minimum distance')
                or action.practice_experience != _data_number(
                    parameters['practice_experience'], 'Run practice experience')
                or actual_start_position != expected_start_position
                or actual_strategy != expected_strategy
                or action.displacement is not None or action.resolution is not None
                or not getattr(action, '_checkpoint_quarantined', False)
                or action_view.choice_id != binding.historical.choice_id
                or action_view.family != 'native.run-action/1'
                or action_view.actor_id != projected.actor_id
                or action_view.start != projected.start or action_view.end != projected.end
                or binding.historical.action_effect_links !=
                    ((action_id, projected.effect_ids),)):
            raise RestoreDependencyRejected('prepared native RunAction differs from its validated source')
        action_rows.append((action_id, id(action), type(action).__module__,
            type(action).__qualname__, action.actor_id, action.target_id,
            action.instrument_id, action.start_time, action.end_time,
            action.parent_event_id, action.minimum_distance,
            action.practice_experience, actual_start_position, actual_strategy,
            action.displacement, action.resolution,
            bool(getattr(action, '_checkpoint_quarantined', False)),
            action_view.choice_id, action_view.family, projected.effect_ids))
    action_rows = tuple(action_rows)
    awareness_rows = tuple((key, tuple(sorted(value)))
                           for key, value in sorted(encounter.awareness.items()))
    container_ids = tuple(id(value) for value in (
        world.event_history, world.object_registry.object_instances,
        world._schedule_lock, world._choice_books, encounter.being_list,
        encounter.pending_action_list, encounter.finished_action_list,
        encounter.cancelled_action_list, book._drafts, book._closed_drafts,
        book._tokens, book._choices, book._reservations, book._registered,
        book._states))
    payload = (
        'universe.prepared-boundary2-native-run-read/1',
        private.context_revision, id(prepared), id(binding), id(world),
        id(encounter), id(native.rng_owner), prefix.to_data(), plan.content_digest,
        world.id, encounter.id, encounter.start_time, encounter.time,
        encounter.last_processed_boundary, encounter._coordinator_time,
        encounter._interval_start, encounter.active_boundary, encounter.boundary_fault,
        tuple(encounter.being_list), tuple(encounter.pending_action_list),
        tuple(encounter.finished_action_list), tuple(encounter.cancelled_action_list),
        awareness_rows, binding.historical.choice_id,
        binding.historical.being_identity_ids,
        binding.historical.target_identity_ids,
        binding.historical.action_effect_links,
        book._counter,
        world._schedule_revision, event_rows, object_rows, action_rows,
        tuple(being_states), native.rng_owner.state, container_ids)
    return _digest(payload)


def _capture_dependency(prepared):
    if type(prepared) is not QuarantinedTrustedLocalRestore:
        raise RestoreDependencyRejected('exact quarantined prepared-context handle required')
    try:
        private = _PREPARED_RESTORES.get(prepared)
    except TypeError as exc:
        raise RestoreDependencyRejected('unknown prepared-context handle') from exc
    if private is None:
        raise RestoreDependencyRejected('prepared context is stale or no longer privately bound')
    if (type(private.context_revision) is not int or private.context_revision < 1
            or not prepared.quarantined or not prepared.view.quarantined):
        raise RestoreDependencyRejected('prepared-context revision or quarantine marker changed')
    try:
        prefix, plan, book = _preflight_preparation(
            private.binding, private.native, counter_floor_applied=True)
    except (RestorePreparationRejected, ImportedPracticeRejected,
            IdentityReservationRejected, TypeError, ValueError) as exc:
        raise RestoreDependencyRejected(f'prepared native read is stale or inconsistent: {exc}') from exc
    if (plan != private.identity_plan
            or prefix != prepared.view.imported_history.practice_prefix
            or prefix.content_digest != prepared.view.imported_history.practice_prefix.content_digest
            or plan.content_digest != prepared.view.identity_plan_digest
            or book._counter != prepared.view.choice_counter_floor):
        raise RestoreDependencyRejected('prepared prefix, reservation plan, or counter revision changed')
    read_digest = _native_read_digest(prepared, private, prefix, plan)
    return (private, prefix, plan, book, read_digest)


def _build_dependency(prepared, captured):
    private, prefix, plan, _book, read_digest = captured
    revision = private.context_revision
    fields = (
        'universe.prepared-boundary2-read-dependency/1', revision,
        prefix.universe_id, prefix.encounter_id, prefix.boundary, prefix.boundary + 1,
        prefix.target_id, prefix.schema, prefix.content_digest, prefix.action_ids,
        plan.historical_choice_ids, plan.historical_action_ids,
        plan.event_namespace_ids, plan.choice_book_counter_floor,
        plan.minimum_next_draft_suffix, plan.content_digest, read_digest)
    digest = _digest(fields)
    return PreparedBoundary2ReadDependency(*fields, digest)


def create_prepared_boundary2_read_dependency(prepared):
    """Issue an immutable, nonexecuting dependency for this prepared context."""
    captured = _capture_dependency(prepared)
    dependency = _build_dependency(prepared, captured)
    _ISSUED_DEPENDENCIES[dependency] = prepared
    return dependency


def _validate_issued_dependency(prepared, dependency):
    if (type(dependency) is not PreparedBoundary2ReadDependency
            or _ISSUED_DEPENDENCIES.get(dependency) is not prepared):
        raise RestoreDependencyRejected('dependency was not issued for this exact prepared context')
    fields = _dependency_data(dependency)
    if (dependency.schema != 'universe.prepared-boundary2-read-dependency/1'
            or dependency.dependency_digest != _digest(fields)):
        raise RestoreDependencyRejected('dependency digest is invalid or edited')
    captured = _capture_dependency(prepared)
    current = _build_dependency(prepared, captured)
    if (_dependency_data(current) != _dependency_data(dependency)
            or current.dependency_digest != dependency.dependency_digest):
        raise RestoreDependencyRejected('prepared boundary-2 dependency is stale')
    return captured


def preflight_boundary2_identity_ids(prepared, dependency, *, encounter_id,
                                     practice_target_id, choice_id, action_ids,
                                     boundary=2):
    """Read-only validation of proposed IDs; creates no native Action/Choice."""
    captured = _validate_issued_dependency(prepared, dependency)
    private, prefix, plan, book, _read_digest = captured
    if boundary != dependency.prospective_boundary or boundary != 2:
        raise RestoreDependencyRejected('only the prospective integer boundary 2 is supported')
    if encounter_id != dependency.encounter_id or encounter_id != private.native.encounter.id:
        raise RestoreDependencyRejected('prospective Encounter reference does not match prepared context')
    if practice_target_id != dependency.practice_target_id or practice_target_id != prefix.target_id:
        raise RestoreDependencyRejected('historical practice Target reference does not match dependency')
    from checkpoint_identity_reservations import validate_future_identity_ids
    try:
        checked = validate_future_identity_ids(plan, choice_id, action_ids,
            existing_event_ids=tuple(private.native.universe.event_history),
            existing_choice_ids=tuple(book._choices))
    except (IdentityReservationRejected, TypeError, ValueError) as exc:
        raise RestoreDependencyRejected(f'prospective Choice/Action IDs refused: {exc}') from exc
    if not checked.accepted:
        raise RestoreDependencyRejected('prospective identity validation did not accept')
    return ProspectiveBoundary2IdentityPreflight(
        'universe.prospective-boundary2-identity-preflight/1',
        dependency.dependency_digest, dependency.prepared_context_revision,
        boundary, encounter_id, practice_target_id, checked.choice_id,
        checked.action_ids, True)


def _validate_identity_preflight(prepared, dependency, preflight):
    if type(preflight) is not ProspectiveBoundary2IdentityPreflight or not preflight.accepted:
        raise RestoreDependencyRejected('accepted boundary-2 identity preflight is required')
    if (len(preflight.action_ids) not in (1, 2)
            or preflight.dependency_digest != dependency.dependency_digest
            or preflight.prepared_context_revision != dependency.prepared_context_revision):
        raise RestoreDependencyRejected('identity preflight is outside the supported boundary-2 context')
    current = preflight_boundary2_identity_ids(prepared, dependency,
        encounter_id=preflight.encounter_id,
        practice_target_id=preflight.practice_target_id,
        choice_id=preflight.choice_id, action_ids=preflight.action_ids,
        boundary=preflight.boundary)
    if current != preflight:
        raise RestoreDependencyRejected('boundary-2 identity preflight is stale or edited')
    return current


def _capture_prepared_boundary2_frozen_read(prepared, dependency, preflight):
    """Capture the native read-set and frozen practice inputs without staging.

    This composes C4 dependency validation, the real interval read-set walker,
    and the shared frozen-practice copy/validation path. It never calls the
    interval preflight/candidate builder, evaluator, scheduler, or publisher.
    """
    _validate_identity_preflight(prepared, dependency, preflight)
    private, prefix, plan, _book, _read_digest = _validate_issued_dependency(
        prepared, dependency)
    if (preflight.encounter_id != dependency.encounter_id
            or preflight.practice_target_id != prefix.target_id
            or preflight.choice_id in plan.historical_choice_ids
            or set(preflight.action_ids).intersection(plan.historical_action_ids)):
        raise RestoreDependencyRejected('future identities conflict with imported history')
    from interval_staging import _native_lock, _read_set
    from frozen_practice import (_capture_prepared_practice_inputs,
        FrozenBeingPractice, FrozenPracticeInputs, BatchSkillUse)
    native = private.native
    native_beings = dict(native.beings)
    world, encounter = native.universe, native.encounter
    try:
        lock = _native_lock(world)
        with lock:
            # Revalidate while holding the scheduler ownership used by native
            # staging. Other writes remain detectable through the second read.
            _validate_issued_dependency(prepared, dependency)
            before = _read_set(encounter)
            ids = tuple(sorted(native_beings))
            if ids != tuple(sorted(encounter.being_list)):
                raise RestoreDependencyRejected('prepared Beings differ from Encounter participants')
            practice = _capture_prepared_practice_inputs(
                world, world.object_registry.object_instances, ids, prefix)
            after = _read_set(encounter)
            _validate_issued_dependency(prepared, dependency)
            if before != after:
                raise RestoreDependencyRejected('native read-set changed during frozen capture')
    except RestoreDependencyRejected:
        raise
    except Exception as exc:
        raise RestoreDependencyRejected(f'native frozen read capture refused: {exc}') from exc
    if type(practice) is not FrozenPracticeInputs or type(practice.beings) is not MappingProxyType:
        raise RestoreDependencyRejected('native frozen-practice validator returned unsupported data')
    target_practice = practice.beings.get(prefix.target_id)
    if type(target_practice) is not FrozenBeingPractice:
        raise RestoreDependencyRejected('imported Target is absent from frozen practice inputs')
    imported_batches = tuple(use for use in target_practice.prior_uses
                             if type(use) is BatchSkillUse
                             and use.being_id == prefix.target_id
                             and tuple(row.action_id for row in use.exercises) == prefix.action_ids)
    if imported_batches != prefix.uses or len(imported_batches) != 1:
        raise RestoreDependencyRejected('imported Run practice does not appear exactly once')
    from experience import practice_action_ids
    for being_id, frozen in practice.beings.items():
        action_skill_ids = [(aid, use.skill_name)
            for use in frozen.prior_uses for aid in practice_action_ids(use)]
        if len(action_skill_ids) != len(set(action_skill_ids)):
            raise RestoreDependencyRejected('duplicate Action/skill practice in frozen capture')
    if (prefix.target_id not in native_beings
            or target_practice.skill_experience.get('run', 0)
                != native_beings[prefix.target_id].skill_experience.get('run', 0)
            or target_practice.ordinary_levels.get('run', 0)
                != native_beings[prefix.target_id].current.skills.skills.get('run', 0)):
        raise RestoreDependencyRejected('frozen practice capture changed or misread Target state')
    return PreparedBoundary2FrozenRead(
        'universe.prepared-boundary2-frozen-read/1',
        dependency.prepared_context_revision, dependency.dependency_digest,
        prefix.schema, prefix.content_digest, preflight.boundary,
        preflight.encounter_id, prefix.target_id, preflight.choice_id,
        preflight.action_ids, _digest(before), before, practice)


def _validate_prepared_boundary2_frozen_read(prepared, dependency, preflight, captured):
    """Recheck all C4 and native read dependencies against a prior capture."""
    if type(captured) is not PreparedBoundary2FrozenRead:
        raise RestoreDependencyRejected('exact frozen-read capture is required for recheck')
    current = _capture_prepared_boundary2_frozen_read(prepared, dependency, preflight)
    if current != captured:
        raise RestoreDependencyRejected('prepared frozen read or imported practice is stale')
    return True


def _make_prepared_continuation_context(prepared, dependency, preflight, captured):
    """Seal validated C1–C5 inputs for one private activation operation."""
    _validate_identity_preflight(prepared, dependency, preflight)
    _validate_prepared_boundary2_frozen_read(prepared, dependency, preflight, captured)
    private, prefix, plan, _book, _digest_value = _validate_issued_dependency(
        prepared, dependency)
    if (captured.prepared_context_revision != private.context_revision
            or captured.dependency_digest != dependency.dependency_digest
            or captured.imported_prefix_digest != prefix.content_digest
            or captured.imported_prefix_schema != prefix.schema
            or captured.action_ids != preflight.action_ids):
        raise RestoreDependencyRejected('C1–C5 continuation inputs do not describe one context')
    return _PreparedContinuationContext(private.context_revision,
        dependency.dependency_digest, prefix.schema, prefix.content_digest,
        plan.content_digest, plan.choice_book_counter_floor,
        plan.historical_choice_ids, plan.historical_action_ids,
        preflight.choice_id, preflight.action_ids, prefix,
        captured.native_read_set_digest)
