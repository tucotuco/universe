"""One host-authorized boundary-2 native Run continuation demonstration (5E1J6).

This is deliberately not a loader or a general resume API. It accepts only the
existing private C3 handle, issued C4 dependency and C5 frozen-read proof, then
admits one explicit native RunAction and advances exactly one boundary.
"""
from dataclasses import dataclass
import math

from checkpoint_restore_dependencies import (
    RestoreDependencyRejected, ProspectiveBoundary2IdentityPreflight,
    _PREPARED_RESTORES,
    _capture_prepared_boundary2_frozen_read,
    _make_prepared_continuation_context,
)
from checkpoint_restore_preparation import QuarantinedTrustedLocalRestore


class ContinuationRejected(ValueError):
    """The bounded trusted-local continuation was refused or fault-stopped."""


@dataclass(frozen=True)
class Boundary2ContinuationEvidence:
    schema: str
    imported_history: object
    encounter_id: str
    boundary: int
    choice_id: str
    action_id: str
    published_interval: object
    action_proposal: object
    target_interval_record: object
    target_experience: object
    target_run_rank: object
    target_position: tuple
    awareness: tuple
    final_rng_state: tuple
    quarantined_after_commit: bool
    imported_receipt_registered: bool


def _restore_book_snapshot(book):
    return (book._counter, book.encounter.universe._schedule_revision,
        dict(book._drafts), set(book._closed_drafts), dict(book._tokens),
        dict(book._choices), book._reservations, dict(book._registered),
        dict(book._states))


def _restore_book_in_place(book, snapshot):
    (book._counter, book.encounter.universe._schedule_revision,
     drafts, closed, tokens, choices, reservations, registered, states) = snapshot
    for storage, values in ((book._drafts, drafts), (book._tokens, tokens),
                            (book._choices, choices), (book._registered, registered),
                            (book._states, states)):
        storage.clear(); storage.update(values)
    book._closed_drafts.clear(); book._closed_drafts.update(closed)
    book._reservations = reservations


def _restore_mode(encounter, restore_context):
    import transactional_progression as progression
    binding = progression._BINDINGS.get(id(encounter))
    if binding is not None and binding.encounter() is encounter:
        if binding.restore_context is not restore_context:
            raise ContinuationRejected('mode binding changed during activation rollback')
        progression._BINDINGS.pop(id(encounter), None)
    data = object.__getattribute__(encounter, '__dict__')
    data.pop('_transactional_mode', None)


def _continue_one_run_boundary2(prepared, dependency, preflight, *,
                                 action_id, velocity=(0.25, 0.0, 0.0)):
    """Privately restore, admit, resolve and publish one Run at boundary 2.

    Host trust is represented by possession of the exact C3 prepared handle;
    checkpoint bytes alone cannot create it. The native graph never escapes.
    """
    if type(prepared) is not QuarantinedTrustedLocalRestore:
        raise ContinuationRejected('exact host-authorized prepared handle required')
    try:
        valid_velocity = (type(velocity) in (tuple, list) and len(velocity) == 3
            and all(type(value) in (int, float) and math.isfinite(value)
                    for value in velocity))
    except OverflowError:
        valid_velocity = False
    if type(action_id) is not str or not action_id.strip() or not valid_velocity:
        raise ContinuationRejected('native Run identity and finite movement vector required')
    try:
        private = _PREPARED_RESTORES.get(prepared)
    except TypeError as exc:
        raise ContinuationRejected('prepared context is not a current local authorization') from exc
    if private is None:
        raise ContinuationRejected('prepared context is stale or foreign')
    native = private.native
    encounter, world = native.encounter, native.universe
    if type(preflight) is not ProspectiveBoundary2IdentityPreflight:
        raise ContinuationRejected('exact issued boundary-2 identity preflight is required')
    native_beings = dict(native.beings)
    book = encounter._choice_book
    prefix = prepared.view.imported_history.practice_prefix
    if (preflight.encounter_id != encounter.id
            or preflight.practice_target_id != prefix.target_id
            or preflight.action_ids != (action_id,)
            or preflight.boundary != 2):
        raise ContinuationRejected('future Run identity preflight does not match this exact operation')

    import atomic_publication as publication
    import transactional_progression as progression
    from activities import RunAction
    from transactional_progression import is_quarantined
    # Match publisher lock order and hold the complete isolated graph while the
    # validated dependency is consumed, the choice is admitted and one step is
    # staged/published. The nested native publisher uses reentrant locks.
    lock = publication._native_lock(world)
    try:
        with publication._GATE:
            if publication._ACTIVE is not None or publication._EMERGENCIES:
                raise ContinuationRejected('native publication authority is busy or fault-blocked')
            with lock:
                frozen_read = _capture_prepared_boundary2_frozen_read(
                    prepared, dependency, preflight)
                context = _make_prepared_continuation_context(
                    prepared, dependency, preflight, frozen_read)
                if not all(is_quarantined(value) for value in
                           (world, encounter, *(being for _key, being in native.beings))):
                    raise ContinuationRejected('native checkpoint quarantine was altered')
                from atomic_publication import RNGCursor
                if type(native.rng_owner) is not RNGCursor:
                    raise ContinuationRejected('exclusive native caller RNG cursor is required')
                if encounter._choice_book._counter != context.choice_counter_floor:
                    raise ContinuationRejected('ChoiceBook counter floor changed')
                actor_id = context.imported_prefix.target_id
                projected = context.imported_prefix
                if (projected.encounter_id != encounter.id
                        or actor_id not in encounter.being_list
                        or len(encounter.being_list) != 2):
                    raise ContinuationRejected('imported Run actor/participant binding is inconsistent')
                book_before = _restore_book_snapshot(book)
                mode_installed = False
                try:
                    with progression._trusted_local_execution_scope(encounter, context):
                        progression._enable_prepared_transactional_progression(
                            encounter, native.rng_owner, context)
                        mode_installed = True
                        action = RunAction(world, actor_id, 1.0,
                            duration=1.0, minimum_distance=0.1,
                            experience=5, id=action_id)
                        choice = encounter.schedule_choice((action,))
                        if (choice.id != context.future_choice_id
                                or choice.action_ids != (action_id,)
                                or book._counter != context.choice_counter_floor + 1):
                            raise ContinuationRejected('native Choice admission disagrees with reserved identities')
                        step = encounter.step(1.0, velocities={actor_id: tuple(velocity)})
                        if step.end_time != 2 or encounter.time != 2 or encounter.last_processed_boundary != 2:
                            raise ContinuationRejected('native coordinator did not commit exactly boundary 2')
                except BaseException as exc:
                    # A publisher fault with verified rollback is explicitly
                    # acknowledged, then the still-unstarted admitted Choice
                    # and its allocator revision are returned to the C5 state.
                    fault = encounter.__dict__.get('boundary_fault')
                    if (fault is not None and fault.get('kind') == 'atomic_publication'
                            and not publication._EMERGENCIES):
                        try:
                            progression.recover_transactional_progression(
                                encounter, fault['recovery_token'])
                        except Exception:
                            raise ContinuationRejected(
                                'native publisher rollback could not be safely acknowledged') from exc
                    if (encounter.time == 1 and not encounter.__dict__.get('_atomic_interval_history')
                            and encounter.boundary_fault is None):
                        _restore_book_in_place(book, book_before)
                        if mode_installed:
                            _restore_mode(encounter, context)
                    raise

                history = encounter.__dict__.get('_atomic_interval_history', ())
                if (len(history) != 1 or history[0].boundary != 2
                        or history[0].encounter_id != encounter.id):
                    raise ContinuationRejected('native publisher did not issue the one boundary-2 receipt')
                receipt = history[0]
                issued = publication._COMMITTED_RECEIPTS.get(id(receipt))
                if (issued is None or issued[0]() is not receipt
                        or issued[1]() is not encounter):
                    raise ContinuationRejected('boundary-2 receipt lacks native publisher issuance')
                if any(row.boundary == 1 for row in history):
                    raise ContinuationRejected('imported boundary 1 was incorrectly installed as native history')
                action_record = receipt.inspection.actions[action_id]
                proposal = action_record[1]
                target_record = next(row for row in
                    object.__getattribute__(native_beings[actor_id], '__dict__')
                        .get('_atomic_target_history', ()) if row.boundary == 2)
                being = native_beings[actor_id]
                imported_registered = any(row.boundary == 1 for row in
                    object.__getattribute__(being, '__dict__').get('_atomic_target_history', ()))
                return Boundary2ContinuationEvidence(
                    'universe.trusted-local-boundary2-continuation/1',
                    prepared.view.imported_history, encounter.id, 2, choice.id,
                    action_id, receipt, proposal, target_record,
                    dict(being.skill_experience), being.current.skills.skills.get('run', 0),
                    tuple(being.get_position().as_tuple()),
                    tuple(sorted(encounter.awareness.get(actor_id, ()))),
                    native.rng_owner.state, is_quarantined(encounter),
                    imported_registered)
    except ContinuationRejected:
        raise
    except (RestoreDependencyRejected, TypeError, ValueError, RuntimeError,
            AttributeError, KeyError) as exc:
        raise ContinuationRejected(f'trusted-local boundary-2 continuation refused: {exc}') from exc
