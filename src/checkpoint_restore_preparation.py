"""Private, quarantine-only trusted-local restore preparation (5D2C12C3).

The host must make its local-checkpoint trust decision outside checkpoint
bytes, then deliberately request an opaque process-local approval here. This
is a policy/API boundary, not cryptographic authentication or a Python sandbox.
"""
from dataclasses import dataclass
from itertools import count
from threading import Lock
from weakref import WeakKeyDictionary

from checkpoint_binding import (BINDING_SCHEMA, QuarantinedRunIdentityBinding,
    _NATIVE_BINDINGS)
from checkpoint_identity_reservations import (
    IdentityReservationRejected, HistoricalIdentityReservationPlan,
    plan_historical_identity_reservations, _validate_plan)
from frozen_practice import (ImportedPracticePrefix, ImportedPracticeRejected,
    freeze_imported_run_practice)


class RestorePreparationRejected(ValueError):
    """Input or host authorization is outside the supported preparation case."""


@dataclass(frozen=True)
class QuarantinedImportedHistoryProvenance:
    schema: str
    label: str
    practice_prefix: ImportedPracticePrefix


@dataclass(frozen=True)
class QuarantinedRestorePreparationView:
    schema: str
    binding_view: object
    imported_history: QuarantinedImportedHistoryProvenance
    choice_counter_floor: int
    minimum_next_draft_suffix: int
    source_counter_exact: bool
    identity_plan_digest: str
    quarantined: bool = True


@dataclass(frozen=True, eq=False)
class QuarantinedTrustedLocalRestore:
    """Detached public view; its native graph is retained in a private store."""
    schema: str
    view: QuarantinedRestorePreparationView
    quarantined: bool = True


class _HostLocalApproval:
    __slots__ = ('__weakref__',)


_HOST_APPROVALS = WeakKeyDictionary()  # opaque approval -> exact binding identity
_PREPARED_RESTORES = WeakKeyDictionary()  # view handle -> private native graph/plan
_CONTEXT_REVISION_LOCK = Lock()
_CONTEXT_REVISIONS = count(1)
_MOVEMENT_IMPORT_AUTHORITY = object()
_QUARANTINED_MOVEMENT_IMPORTS = WeakKeyDictionary()
_MOVEMENT_CONTINUATION_APPROVALS = WeakKeyDictionary()


@dataclass(frozen=True, eq=False)
class QuarantinedMovementNativeInspection:
    """Detached result of inspecting an imported boundary-1 native graph."""
    schema: str
    binding: object
    receipt_fingerprint: str
    inspection: object
    native_beings: tuple
    observer_evidence: tuple
    continuation_refusal: str
    quarantined: bool = True


@dataclass(frozen=True)
class TrustedMovementContinuationInspection:
    """Detached boundary-2 result of one explicitly trusted restored movement."""
    schema: str
    movement_plan: object
    inspection: object
    native_beings: tuple
    observer_evidence: tuple
    rng_state: tuple
    quarantined_after_step: bool


@dataclass(frozen=True)
class _PrivateMovementNativeInspection:
    native: object
    receipt: object
    fingerprint: str


class _HostMovementContinuationApproval:
    """Process-local host decision bound to one import and exact accepted plan."""
    __slots__ = ('__weakref__',)


@dataclass(frozen=True)
class _PrivatePreparedRestore:
    binding: object
    native: object
    identity_plan: HistoricalIdentityReservationPlan
    context_revision: int


def _import_quarantined_movement_boundary(decoded):
    """Restore and inspect only the authentic initial Arena movement boundary.

    This restoration-owner path rebuilds native Target records and process-local
    anchors from the closed checkpoint graph. It never publishes an interval or
    enables executable progression; its only scheduling mode permits inspection.
    """
    from checkpoint_binding import (_materialize_quarantined_movement_native,
        bind_quarantined_movement_boundary)
    from atomic_publication import (PublishedInterval, _register_quarantined_movement_import,
        _unregister_quarantined_movement_import)
    from encounter_inspection import fingerprint, inspect_encounter
    from transactional_progression import (
        _bind_quarantined_movement_inspection,
        _unbind_quarantined_movement_inspection,
        TransactionalProgressionError, is_quarantined, mode_of,
        step_transactionally)

    try:
        native = _materialize_quarantined_movement_native(decoded)
    except (TypeError, ValueError) as exc:
        raise RestorePreparationRejected(f'movement native reconstruction refused: {exc}') from exc
    encounter = native.encounter
    beings = dict(native.beings)
    targets = dict(native.targets)
    target_anchors = {}
    for target_id in encounter.being_list:
        being = beings[target_id]
        storage = being.__dict__.get('_atomic_target_history')
        if type(storage) is not list or len(storage) != 1 or storage[0] is not targets[target_id]:
            raise RestorePreparationRejected('native Target record ownership changed during staging')
        record = storage[0]
        target_anchors[target_id] = (
            id(being), id(being.current), id(being.spatial_state), id(storage),
            id(record), fingerprint(record))
    from dataclasses import replace
    from types import MappingProxyType
    from encounter_inspection import CommittedBoundaryRecord
    source_meta = native.source_inspection
    if type(source_meta) is not CommittedBoundaryRecord:
        raise RestorePreparationRejected('source committed inspection record is unsupported')
    imported_meta = replace(source_meta,
        target_anchors=MappingProxyType(dict(target_anchors)),
        action_anchors=MappingProxyType({}))
    source_receipt_fields = dict(native.source_receipt_fields)
    try:
        receipt = PublishedInterval(
            source_receipt_fields['encounter_id'], source_receipt_fields['boundary'],
            source_receipt_fields['action_ids'], source_receipt_fields['effect_ids'],
            source_receipt_fields['rng_state'], source_receipt_fields['notification_intents'],
            source_receipt_fields['committed'], imported_meta)
    except (KeyError, TypeError, ValueError) as exc:
        raise RestorePreparationRejected(f'stored movement receipt is incomplete: {exc}') from exc
    if (receipt.encounter_id != encounter.id or receipt.boundary != 1
            or receipt.rng_state != native.rng_owner.state or receipt.action_ids
            or receipt.effect_ids or receipt.notification_intents or not receipt.committed):
        raise RestorePreparationRejected('stored receipt differs from the authentic movement-only interval')

    registered = False
    bound_mode = False
    try:
        encounter.__dict__['_atomic_interval_history'] = [receipt]
        _register_quarantined_movement_import(encounter, receipt, native.rng_owner,
            authority=_MOVEMENT_IMPORT_AUTHORITY)
        registered = True
        _bind_quarantined_movement_inspection(encounter, native.rng_owner, receipt,
            authority=_MOVEMENT_IMPORT_AUTHORITY)
        bound_mode = True
        if not is_quarantined(encounter) or mode_of(encounter) != 'quarantined_inspection':
            raise RestorePreparationRejected('imported native Encounter lost inspection quarantine')
        inspection = inspect_encounter(encounter)
        if (inspection.boundary != 1 or inspection.latest_boundary != 1
                or set(inspection.targets) != set(encounter.being_list)
                or len(inspection.timeline) != 1
                or inspection.timeline[0].action_ids
                or inspection.timeline[0].effect_ids
                or any(len(inspection.histories[being_id]) != 1
                       for being_id in encounter.being_list)):
            raise RestorePreparationRejected('native inspector disagrees with imported boundary')
        before = (encounter.time, encounter.last_processed_boundary,
            tuple((being_id, tuple(beings[being_id].get_position().as_tuple()),
                   tuple(beings[being_id]._atomic_target_history))
                  for being_id in sorted(beings)),
            native.rng_owner.state, tuple(encounter._atomic_interval_history))
        try:
            step_transactionally(encounter, 1, None, None)
        except TransactionalProgressionError as exc:
            refusal = str(exc)
        else:
            raise RestorePreparationRejected('quarantined imported Encounter unexpectedly advanced')
        after = (encounter.time, encounter.last_processed_boundary,
            tuple((being_id, tuple(beings[being_id].get_position().as_tuple()),
                   tuple(beings[being_id]._atomic_target_history))
                  for being_id in sorted(beings)),
            native.rng_owner.state, tuple(encounter._atomic_interval_history))
        if after != before:
            raise RestorePreparationRejected('quarantined progression refusal changed imported state')
        from checkpoint_reconstruction import _projection
        from checkpoint_arena_perception import encode_arena_perception_ledger
        native_being_rows = []
        observer_rows = []
        for being_id in sorted(beings):
            being = beings[being_id]
            position = being.get_position()
            native_being_rows.append((being_id,
                None if position is None else tuple(position.as_tuple()),
                being.get_posture(), being.hex_facing,
                _projection(being.original), _projection(being.current),
                tuple(sorted(encounter.awareness[being_id]))))
            encoded = encode_arena_perception_ledger(
                being._arena_perception_ledger, observer=being,
                encounter=encounter,
                registry=native.universe.object_registry.object_instances)
            observer_rows.append((being_id, encoded))
        handle = QuarantinedMovementNativeInspection(
            'universe.quarantined-movement-native-inspection/1',
            bind_quarantined_movement_boundary(decoded),
            fingerprint(receipt), inspection, tuple(native_being_rows),
            tuple(observer_rows), refusal, True)
        _QUARANTINED_MOVEMENT_IMPORTS[handle] = _PrivateMovementNativeInspection(
            native, receipt, fingerprint(receipt))
        return handle
    except BaseException as exc:
        if bound_mode:
            _unbind_quarantined_movement_inspection(encounter,
                authority=_MOVEMENT_IMPORT_AUTHORITY)
        if registered:
            _unregister_quarantined_movement_import(encounter, receipt,
                authority=_MOVEMENT_IMPORT_AUTHORITY)
        encounter.__dict__.pop('_atomic_interval_history', None)
        for being in beings.values():
            being.__dict__['_atomic_target_history'] = []
        if isinstance(exc, RestorePreparationRejected):
            raise
        raise RestorePreparationRejected(f'quarantined movement receipt import refused: {exc}') from exc


def _host_authorize_movement_continuation(import_handle, movement_plan):
    """Record the host's out-of-band trust decision for this exact plan/import."""
    from arena_movement_plan_checkpoint import (
        ArenaMovementPlanCheckpoint, MovementPlanRejected, encode, decode)
    if (_QUARANTINED_MOVEMENT_IMPORTS.get(import_handle) is None
            or type(movement_plan) is not ArenaMovementPlanCheckpoint):
        raise RestorePreparationRejected('host approval requires an exact imported graph and closed plan')
    try:
        movement_plan = decode(encode(movement_plan))
    except (MovementPlanRejected, TypeError, ValueError) as exc:
        raise RestorePreparationRejected(f'host-approved movement plan is invalid: {exc}') from exc
    approval = _HostMovementContinuationApproval()
    _MOVEMENT_CONTINUATION_APPROVALS[approval] = (import_handle, movement_plan)
    return approval


def _trusted_continue_imported_movement_boundary(import_handle, movement_plan, *, approval):
    """Advance one validated imported Arena movement boundary under host trust.

    This is intentionally a one-boundary restoration-owner operation. The
    source plan must be separately captured from the accepted live session;
    checkpoint bytes cannot manufacture host trust or a new movement Choice.
    """
    from arena_movement_plan_checkpoint import (
        ArenaMovementPlanCheckpoint, MovementPlanRejected, SCHEMA, encode, decode)
    from arena_hex_map import ArenaHexLayout, HexAddress
    from spatial.state import CartesianPosition
    from movement_intent import MovementIntent, MovementRateConditions
    from checkpoint_adapters import _movement_activation_state, CheckpointRejected
    from encounter_inspection import inspect_encounter, fingerprint
    from transactional_progression import (
        TransactionalProgressionError, _trusted_imported_movement_scope,
        _bind_trusted_imported_movement_progression, is_quarantined)
    from being import BeingInstance

    private = _QUARANTINED_MOVEMENT_IMPORTS.get(import_handle)
    approved = _MOVEMENT_CONTINUATION_APPROVALS.get(approval)
    if (private is None or type(movement_plan) is not ArenaMovementPlanCheckpoint
            or movement_plan.schema != SCHEMA or approved is None
            or approved[0] is not import_handle):
        raise RestorePreparationRejected('trusted movement requires host approval for this exact imported graph and plan')
    try:
        movement_plan = decode(encode(movement_plan))
    except (MovementPlanRejected, TypeError, ValueError) as exc:
        raise RestorePreparationRejected(f'accepted movement plan failed strict validation: {exc}') from exc
    if movement_plan != approved[1]:
        raise RestorePreparationRejected('accepted movement plan differs from the host-approved plan')
    native = private.native
    encounter = native.encounter
    universe = native.universe
    beings = dict(native.beings)
    plan = movement_plan
    try:
        activation = _movement_activation_state(encounter)
    except (TypeError, ValueError, CheckpointRejected) as exc:
        raise RestorePreparationRejected(f'imported native movement state is invalid: {exc}') from exc
    if (not is_quarantined(universe) or not is_quarantined(encounter)
            or not all(is_quarantined(being) for being in beings.values())
            or encounter.progression_mode != 'quarantined_inspection'
            or plan.universe_id != universe.id or plan.encounter_id != encounter.id
            or plan.actor_id != activation.actor_id
            or plan.decision_id != activation.movement_decision_id
            or plan.accepted_at != activation.time or plan.checkpoint_boundary != 1
            or activation.activation_kind != 'first_player_movement'
            or tuple(encounter.being_list) != tuple(private.native.encounter.being_list)
            or set(universe.object_registry.object_instances) != set(encounter.being_list)
            or set(beings) != set(encounter.being_list)):
        raise RestorePreparationRejected('trusted plan/Encounter/participant activation binding is inconsistent')
    if (type(plan.layout) is not tuple or len(plan.layout) != 2
            or any(type(value) is not int or value < 1 for value in plan.layout)):
        raise RestorePreparationRejected('movement-plan layout is invalid')
    try:
        layout = ArenaHexLayout.rectangle(*plan.layout)
        address = HexAddress(*plan.cell)
        destination = CartesianPosition(*plan.destination)
        expected_destination = layout.center_position(address, z=destination.z)
    except (TypeError, ValueError) as exc:
        raise RestorePreparationRejected(f'movement-plan destination cannot be reconstructed: {exc}') from exc
    if destination != expected_destination:
        raise RestorePreparationRejected('accepted movement destination is not the recorded native hex center')
    actor = beings.get(plan.actor_id)
    if (type(actor) is not BeingInstance or universe.get_object_by_id(actor.id) is not actor
            or actor.get_position() is None or actor.get_position() == destination
            or type(actor.current.hit_points) not in (int, float) or actor.current.hit_points <= 0
            or actor.is_helpless()):
        raise RestorePreparationRejected('movement actor is missing, unable, or already at destination')
    if (type(encounter.pending_action_list) is not list or encounter.pending_action_list
            or encounter.finished_action_list or encounter.cancelled_action_list
            or encounter._choice_book._counter != 0 or encounter._choice_book._choices
            or encounter._choice_book._drafts or encounter._choice_book._registered
            or encounter._choice_book._reservations or encounter._choice_book._tokens
            or encounter._choice_book._states or encounter._choice_book._closed_drafts
            or universe.__dict__.get('_choice_books') != [encounter._choice_book]
            or universe.__dict__.get('_schedule_revision') != 0
            or set(universe.event_history) != {'0', encounter.id}
            or any(being.original is being.current for being in beings.values())):
        raise RestorePreparationRejected('supported continuation requires the authentic empty Action/Choice state')
    try:
        before_inspection = inspect_encounter(encounter)
    except Exception as exc:
        raise RestorePreparationRejected(f'imported boundary failed native inspection: {exc}') from exc
    if (before_inspection.boundary != 1 or before_inspection.latest_boundary != 1
            or set(before_inspection.targets) != set(encounter.being_list)
            or len(before_inspection.timeline) != 1
            or before_inspection.timeline[0].action_ids
            or before_inspection.timeline[0].effect_ids
            or len(encounter._atomic_interval_history) != 1
            or encounter._atomic_interval_history[0] is not private.receipt):
        raise RestorePreparationRejected('imported native receipt chain is outside boundary-1 movement scope')
    if (type(plan.world_premise) is not tuple or len(plan.world_premise) != 6
            or plan.world_premise != ('Plains', 'Road', 1.0, 1.0, True, False)):
        raise RestorePreparationRejected('movement plan premise differs from supported generated Arena world')
    conditions = MovementRateConditions(terrain_multiplier=plan.world_premise[2],
        hampered_multiplier=plan.world_premise[3], direction=None,
        concurrent_demanding_action=False)
    next_boundary = encounter.last_processed_boundary + 1
    intent = MovementIntent(plan.actor_id, destination, plan.rate,
        f'{plan.decision_id}:boundary:{next_boundary}', next_boundary,
        facing_policy=plan.facing_policy)
    from transactional_progression import _BINDINGS
    binding = _BINDINGS.get(id(encounter))
    if (binding is None or binding.encounter() is not encounter
            or binding.mode.name != 'quarantined_inspection'
            or binding.rng_owner is not native.rng_owner):
        raise RestorePreparationRejected('imported inspection binding or exclusive RNG owner changed')
    if _MOVEMENT_CONTINUATION_APPROVALS.pop(approval, None) != approved:
        raise RestorePreparationRejected('host movement approval is stale or already consumed')
    old_receipts = tuple(encounter._atomic_interval_history)
    old_rng = native.rng_owner.state
    old_position = actor.get_position()
    context = None
    try:
        with _trusted_imported_movement_scope(encounter, import_handle,
                authority=_MOVEMENT_IMPORT_AUTHORITY) as context:
            _bind_trusted_imported_movement_progression(encounter, import_handle,
                native.rng_owner, private.receipt, context,
                authority=_MOVEMENT_IMPORT_AUTHORITY)
            encounter.step(1, movement_intent=intent, movement_conditions=conditions)
        after = inspect_encounter(encounter)
        if (after.boundary != 2 or after.latest_boundary != 2
                or tuple(record.boundary for record in encounter._atomic_interval_history) != (1, 2)
                or len(after.timeline) != 2
                or any(row.action_ids or row.effect_ids for row in after.timeline)
                or any(len(after.histories[being_id]) != 2 for being_id in encounter.being_list)):
            raise RestorePreparationRejected('native continuation did not produce an inspected boundary 2')
    except BaseException as exc:
        if encounter.time == 1 and tuple(encounter._atomic_interval_history) == old_receipts:
            native.rng_owner.state = old_rng
            if actor.get_position() != old_position:
                raise RestorePreparationRejected('failed native publication did not restore movement state') from exc
            from transactional_progression import _restore_quarantined_movement_inspection
            try:
                _restore_quarantined_movement_inspection(encounter,
                    import_handle, private.receipt,
                    authority=_MOVEMENT_IMPORT_AUTHORITY)
            except TransactionalProgressionError:
                pass
        if isinstance(exc, RestorePreparationRejected):
            raise
        raise RestorePreparationRejected(f'trusted native movement continuation failed: {exc}') from exc
    from checkpoint_reconstruction import _projection
    from checkpoint_arena_perception import encode_arena_perception_ledger
    native_rows = []
    observer_rows = []
    registry = universe.object_registry.object_instances
    for being_id in sorted(beings):
        being = beings[being_id]
        position = being.get_position()
        native_rows.append((being_id, tuple(position.as_tuple()), being.get_posture(),
            being.hex_facing, _projection(being.original), _projection(being.current),
            tuple(sorted(encounter.awareness[being_id])),
            tuple(record.boundary for record in after.histories[being_id]),
            tuple(fingerprint(record) for record in being._atomic_target_history)))
        observer_rows.append((being_id, encode_arena_perception_ledger(
            being._arena_perception_ledger, observer=being, encounter=encounter,
            registry=registry)))
    return TrustedMovementContinuationInspection(
        'universe.trusted-movement-continuation-inspection/1', plan, after,
        tuple(native_rows), tuple(observer_rows), native.rng_owner.state,
        is_quarantined(encounter))


def _host_authorize_trusted_local_restore(binding):
    """Mint an out-of-band capability after the host's explicit trust choice.

    This underscore-private call is intended for host-owned code only. The
    checkpoint cannot encode or mint the returned process-local capability.
    Calling it is the host's policy decision; this module cannot verify why the
    host trusts its local input.
    """
    if type(binding) is not QuarantinedRunIdentityBinding or binding not in _NATIVE_BINDINGS:
        raise RestorePreparationRejected('host approval requires the exact private Run binding')
    approval = _HostLocalApproval()
    _HOST_APPROVALS[approval] = binding
    return approval


def _preflight_preparation(binding, native, *, imported_prefix=None, identity_plan=None,
                           counter_floor_applied=False):
    """Validate the complete bounded graph without writing any native state."""
    from action import Action
    from activities import RunAction
    from atomic_publication import RNGCursor
    from checkpoint_binding import _PrivateNativeBinding
    from event import Event
    from transactional_progression import is_quarantined, mode_of

    if type(binding) is not QuarantinedRunIdentityBinding or binding.schema != BINDING_SCHEMA:
        raise RestorePreparationRejected('quarantined native Run binding/1 required')
    if (not binding.quarantined or type(native) is not _PrivateNativeBinding
            or _NATIVE_BINDINGS.get(binding) is not native):
        raise RestorePreparationRejected('private quarantined native graph is missing')
    sidecar = binding.historical
    try:
        computed_prefix = freeze_imported_run_practice(sidecar)
        computed_plan = plan_historical_identity_reservations(sidecar)
    except (ImportedPracticeRejected, IdentityReservationRejected, TypeError, ValueError) as exc:
        raise RestorePreparationRejected(f'historical prefix or identity plan refused: {exc}') from exc
    if imported_prefix is not None and imported_prefix != computed_prefix:
        raise RestorePreparationRejected('supplied imported-practice prefix disagrees with sidecar')
    if identity_plan is not None and identity_plan != computed_plan:
        raise RestorePreparationRejected('supplied identity plan disagrees with sidecar')
    _validate_plan(computed_plan)

    world, encounter, rng_owner = native.universe, native.encounter, native.rng_owner
    beings = dict(native.beings)
    actions = dict(native.actions)
    view = binding.view
    if (view.universe_id != computed_prefix.universe_id
            or view.encounter_id != computed_prefix.encounter_id
            or view.boundary != 1 or view.start != ('integer', '0')
            or view.choice_id != computed_prefix.choice_id
            or tuple(row.logical_id for row in view.actions) != computed_prefix.action_ids
            or tuple(sorted(beings)) != tuple(sorted(sidecar.being_identity_ids))
            or tuple(sorted(actions)) != tuple(sorted(computed_prefix.action_ids))):
        raise RestorePreparationRejected('binding view and imported identity references diverge')
    if (computed_plan.universe_id != computed_prefix.universe_id
            or computed_plan.encounter_id != computed_prefix.encounter_id
            or computed_plan.historical_choice_ids != (computed_prefix.choice_id,)
            or computed_plan.historical_action_ids != computed_prefix.action_ids
            or computed_prefix.target_id not in computed_plan.target_object_ids
            or any(('effect-id', row.effect_identity.encounter_id,
                    row.effect_identity.boundary, row.effect_identity.source_action_id,
                    row.effect_identity.channel, row.effect_identity.slot)
                   not in computed_plan.causal_effect_ids
                   for row in computed_prefix.uses[0].exercises)):
        raise RestorePreparationRejected('practice prefix and identity reservations diverge')
    if (type(world.id) is not str or world.id != view.universe_id
            or type(encounter.id) is not str or encounter.id != view.encounter_id
            or encounter.universe is not world
            or encounter.start_time != 0 or encounter.time != 1
            or encounter.last_processed_boundary != 1
            or encounter._coordinator_time != 1 or encounter._interval_start != 1
            or encounter.active_boundary is not None or encounter.boundary_fault is not None
            or encounter._advancing or encounter._running or encounter._dispatching
            or encounter._boundary_context is not None):
        raise RestorePreparationRejected('private Encounter clock or coordinator is inconsistent')
    if not all(is_quarantined(value) for value in (world, encounter, *beings.values(), *actions.values())):
        raise RestorePreparationRejected('every native object must remain quarantined')
    try:
        if mode_of(encounter) != 'legacy':
            raise RestorePreparationRejected('transactional mode must not be enabled during preparation')
    except Exception as exc:
        if isinstance(exc, RestorePreparationRejected):
            raise
        raise RestorePreparationRejected('Encounter mode binding is inconsistent') from exc

    if set(world.event_history) != {'0', encounter.id}:
        raise RestorePreparationRejected('native Event registry must contain only root and Encounter Events')
    if not isinstance(world.event_history['0'], Event) or world.event_history[encounter.id] is not encounter:
        raise RestorePreparationRejected('native root Event identities are inconsistent')
    if set(world.object_registry.object_instances) != set(sidecar.being_identity_ids):
        raise RestorePreparationRejected('native Being Object registry differs from imported history')
    if set(encounter.being_list) != set(sidecar.being_identity_ids) or len(encounter.being_list) != 2:
            raise RestorePreparationRejected('Encounter participants differ from imported history')
    if (tuple(sorted(sidecar.being_identity_ids)) != tuple(sorted(sidecar.target_identity_ids))
            or len(sidecar.being_identity_ids) != 2
            or len(sidecar.action_identity_ids) != 1):
        raise RestorePreparationRejected('Run sidecar participants, Targets, or Action coverage is incomplete')
    if world._choice_books != [encounter._choice_book]:
        raise RestorePreparationRejected('private Encounter ChoiceBook ownership is inconsistent')
    book = encounter._choice_book
    expected_counter = (computed_plan.choice_book_counter_floor if counter_floor_applied else 0)
    if (book.encounter is not encounter or book.lock is not world._schedule_lock
            or book._counter != expected_counter or book._drafts or book._closed_drafts or book._tokens
            or book._choices or book._reservations or book._registered or book._states
            or world._schedule_revision != 0):
        raise RestorePreparationRejected('private ChoiceBook counter floor or empty scheduling state is inconsistent')
    if (encounter.pending_action_list or encounter.finished_action_list
            or encounter.cancelled_action_list or encounter.non_being_object_list
            or encounter.fatigue_frame_history or encounter.__dict__.get('_atomic_interval_history')):
        raise RestorePreparationRejected('live Action, receipt, or interval history must remain empty')
    if any(action_id in world.event_history for action_id in computed_plan.historical_action_ids):
        raise RestorePreparationRejected('historical Action Event ID collides with native registry')
    from checkpoint_binding import _data_number
    projected_actions = {row.action_id: row for row in sidecar.projection.actions}
    if set(actions) != set(projected_actions) or len(projected_actions) != 1:
        raise RestorePreparationRejected('historical Run Action identity coverage is incomplete')
    for action_id, action in actions.items():
        projected = projected_actions.get(action_id)
        if (type(action) is not RunAction or not isinstance(action, Action)
                or projected is None or action.id != action_id
                or action.universe is not world or action.parent_event_id != encounter.id
                or action.actor_id != projected.actor_id
                or projected.actor_id not in beings or action.target_id is not None
                or action.start_time != _data_number(projected.start, 'Run Action start')
                or action.end_time != _data_number(projected.end, 'Run Action end')
                or getattr(action, '_encounter', None) is not None
                or action.resolution is not None or action.displacement is not None):
            raise RestorePreparationRejected('historical Action identity shell is inconsistent')
    if type(rng_owner) is not RNGCursor or type(rng_owner.state) is not tuple:
        raise RestorePreparationRejected('exclusive private RNG cursor is unsupported')
    if (rng_owner.state != view.rng_state
            or rng_owner.state != view.native_encounter.rng_state
            or not view.native_encounter.quarantined
            or view.native_encounter.next_boundary != 2
            or view.native_encounter.pending_action_ids
            or view.native_encounter.finished_action_ids
            or view.native_encounter.cancelled_action_ids
            or view.native_encounter.choice_count
            or view.native_encounter.reservation_count):
        raise RestorePreparationRejected('RNG state or detached Encounter view is inconsistent')
    for being_id, being in beings.items():
        if (being.id != being_id or world.object_registry.object_instances.get(being_id) is not being
                or not hasattr(being, 'skill_use_history') or being.skill_use_history
                or being.__dict__.get('_atomic_target_history')):
            raise RestorePreparationRejected('Being identity or empty native history invariant failed')
    batch = computed_prefix.uses[0]
    target = beings.get(computed_prefix.target_id)
    target_projection = next((row for row in sidecar.projection.targets
                              if row.target_id == computed_prefix.target_id), None)
    if target is None or target_projection is None or len(target_projection.practice_transitions) != 1:
        raise RestorePreparationRejected('Target-owned practice transition is missing')
    transition = target_projection.practice_transitions[0]
    try:
        experience_after = int(transition.experience_after[1])
        level_after = int(transition.level_after[1])
    except (IndexError, TypeError, ValueError) as exc:
        raise RestorePreparationRejected('Target-owned practice endpoint is malformed') from exc
    if (batch.being_id != target.id or batch.time != 1
            or batch.skill_name != 'run'
            or tuple(row.action_id for row in batch.exercises) != computed_prefix.action_ids
            or target.skill_experience.get('run', 0) != experience_after
            or target.current.skills.skills.get('run', 0) != level_after):
        raise RestorePreparationRejected('imported practice and materialized Target state disagree')
    return computed_prefix, computed_plan, book


def _prepare_trusted_local_restore(binding, host_approval):
    """Prepare one host-approved local checkpoint, but retain quarantine.

    No scheduling, stepping, receipt issuance, native history installation,
    practice capture integration or progression binding occurs here.
    """
    if type(host_approval) is not _HostLocalApproval or _HOST_APPROVALS.get(host_approval) is not binding:
        raise RestorePreparationRejected('a current out-of-band host-local approval is required')
    try:
        native = _NATIVE_BINDINGS.get(binding)
    except TypeError as exc:
        raise RestorePreparationRejected('exact private native binding is required') from exc
    if native is None:
        raise RestorePreparationRejected('private native graph is unavailable')
    book = native.encounter._choice_book
    # Lock the isolated scheduler across the complete read-set check and final
    # scalar initialization. No live queues or history are published.
    with book.lock:
        prefix, plan, checked_book = _preflight_preparation(binding, native)
        if checked_book is not book:
            raise RestorePreparationRejected('ChoiceBook changed during restore preparation')
        provenance = QuarantinedImportedHistoryProvenance(
            'universe.host-authorized-imported-history/1',
            'host-authorized imported checkpoint history; not native receipt history', prefix)
        with _CONTEXT_REVISION_LOCK:
            context_revision = next(_CONTEXT_REVISIONS)
        view = QuarantinedRestorePreparationView(
            'universe.quarantined-trusted-local-restore-preparation/1',
            binding.view, provenance, plan.choice_book_counter_floor,
            plan.minimum_next_draft_suffix, plan.source_counter_exact,
            plan.content_digest, True)
        result = QuarantinedTrustedLocalRestore(view.schema, view, True)
        original_counter = book._counter
        try:
            from checkpoint_identity_reservations import _initialize_quarantined_choice_counter_floor
            _initialize_quarantined_choice_counter_floor(book, plan)
            _PREPARED_RESTORES[result] = _PrivatePreparedRestore(
                binding, native, plan, context_revision)
            _HOST_APPROVALS.pop(host_approval, None)
        except BaseException as exc:
            book._counter = original_counter
            _PREPARED_RESTORES.pop(result, None)
            if isinstance(exc, IdentityReservationRejected):
                raise RestorePreparationRejected(f'ChoiceBook counter reservation refused: {exc}') from exc
            raise
    return result
