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


@dataclass(frozen=True)
class _PrivatePreparedRestore:
    binding: object
    native: object
    identity_plan: HistoricalIdentityReservationPlan
    context_revision: int


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
