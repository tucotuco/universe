"""Inactive complete supported-family observer/lifecycle proposals (5B3).

No world mutation, callbacks, delivery, publication, or persistence. Native
calculations are shared; evidence reads never expose objective truth to belief.
"""
from dataclasses import dataclass, field, fields, replace
import inspect
import math
from types import MappingProxyType

from action_evaluation import (ActionProposal, AwarenessEffect, PracticeEffect,
    EffectIdentity, IdentifiedEffect, UnsupportedEvaluation, EvaluationIntegrityError,
    native_data, freeze, bind_evaluation_result, evaluate_snapshot)
from action_choice import ChoiceBook
from action_settlement import reconcile_boundary
from group_observation import (ObserveGroupAction, SampledGroupObservation,
    observation_rng, group_check, sample_group_evidence)
from field_interpretation import FieldInterpreter, FieldInterpretation, interpret_field
from field_observation import (BeliefLedger, FieldObservation, CountReport, BeliefRevision,
    EvidenceReassessment, InquiryProposal, InquiryRecord, belief_revisions)
from history_conversation import AskAboutPastAction, HeardAccount
from spatial.state import CartesianPosition
from location_observation import (BeingLocationObservation, LastSeenLocation,
    LocationEvidenceLedger)
from object_observation import ObjectObservation, ObjectObservationLedger
from objective_reality import (ObjectiveContext, capture_objective_context,
    evaluate_native_companion, build_objective_candidate, revalidate_complete_objective)

_NATIVE_HOOKS = {ObserveGroupAction: ObserveGroupAction.on_completed,
                 AskAboutPastAction: AskAboutPastAction.on_completed}
_NATIVE_BELIEF_LEARN = BeliefLedger.learn
_NATIVE_BELIEF_COUNT = BeliefLedger.count_estimate
_NATIVE_BELIEF_DISCREPANCIES = BeliefLedger.discrepancies
_NATIVE_LOCATION_LAST_SEEN = LocationEvidenceLedger.last_seen_location
_NATIVE_OBJECT_LAST = ObjectObservationLedger.last_observation
_NATIVE_SAMPLE = SampledGroupObservation.sample
_NATIVE_INTERPRET = FieldInterpreter.interpret
from action import Action
from activities import RunAction, SpotAction, ThrowAction, PickUpAction, ReadyWeaponAction
from melee_combat import MeleeStrike
from melee_defense import MeleeDefense
_NATIVE_RESOLVERS = {cls:cls.resolve for cls in (Action,RunAction,SpotAction,ThrowAction,PickUpAction,ReadyWeaponAction,MeleeStrike,MeleeDefense,ObserveGroupAction,AskAboutPastAction)}
_RECORDS = (FieldObservation, CountReport, FieldInterpretation, BeliefRevision,
    EvidenceReassessment, InquiryProposal, InquiryRecord, HeardAccount, CartesianPosition,
    BeingLocationObservation, LastSeenLocation, ObjectObservation)


def _check(test, reason):
    if not test:
        raise EvaluationIntegrityError(reason)


def frozen_value(value):
    if value is None or type(value) in (str, int, float, bool):
        return freeze(value)
    if type(value) in (tuple, list):
        return tuple(frozen_value(v) for v in value)
    if type(value) in (dict, MappingProxyType):
        return MappingProxyType({freeze(k): frozen_value(v) for k, v in value.items()})
    if type(value) in _RECORDS:
        data = native_data(value, (type(value),))
        return type(value)(**{f.name: frozen_value(data[f.name]) for f in fields(value)})
    raise UnsupportedEvaluation('opaque evidence/account value requires a reviewed adapter')


@dataclass(frozen=True)
class RecipientIdentity:
    role: str
    object_identity: int


@dataclass(frozen=True)
class FrozenBelief:
    identity: RecipientIdentity
    observer_id: str
    evidence: object
    interpretations: object
    current_readings: object
    belief_history: tuple
    auxiliary: object


@dataclass(frozen=True)
class FrozenAccounts:
    identity: RecipientIdentity
    accounts: tuple


@dataclass(frozen=True)
class FrozenLocationEvidence:
    identity: RecipientIdentity
    observer_id: str
    observations: object


@dataclass(frozen=True)
class FrozenObjectEvidence:
    identity: RecipientIdentity
    observer_id: str
    observations: object


@dataclass(frozen=True)
class ObserverActionInputs:
    action_id: str
    observer_config: object = None
    interpreter_config: object = None
    seed: int | None = None
    random_key: str | None = None
    focus: str | None = None
    policy: object = None
    belief_recipient: RecipientIdentity | None = None
    account_recipient: RecipientIdentity | None = None
    location_recipient: RecipientIdentity | None = None
    object_recipient: RecipientIdentity | None = None
    substituted_claim: str | None = None


@dataclass(frozen=True)
class FrozenLifecycle:
    action_id: str
    choice_id: str
    choice_action_state: str
    resources: tuple
    canceled_at: float | None
    cancellation_reason: str | None


@dataclass(frozen=True)
class FrozenObserverInputs:
    snapshot: object = field(repr=False, compare=False)
    actions: object
    recipients: object
    lifecycle: object
    pending: tuple
    finished: tuple
    cancelled: tuple
    choice_revision: int


@dataclass(frozen=True)
class ObservationEffect:
    source_action_id: str
    target_id: str
    observation_id: str


@dataclass(frozen=True)
class InterpretationEffect:
    source_action_id: str
    target_id: str
    observation_id: str


@dataclass(frozen=True)
class BeliefAcquisitionEffect:
    source_action_id: str
    target_id: str
    recipient: RecipientIdentity
    observation_id: str
    acquired: bool


@dataclass(frozen=True)
class LocationObservationEffect:
    source_action_id: str
    target_id: str
    recipient: RecipientIdentity
    observation: BeingLocationObservation


@dataclass(frozen=True)
class ObjectObservationEffect:
    source_action_id: str
    target_id: str
    recipient: RecipientIdentity
    observation: ObjectObservation


@dataclass(frozen=True)
class TestimonyEffect:
    source_action_id: str
    target_id: str
    account_id: str


@dataclass(frozen=True)
class AccountDeliveryEffect:
    source_action_id: str
    target_id: str
    recipient: RecipientIdentity
    account_id: str


@dataclass(frozen=True)
class ActionOutcomeEffect:
    source_action_id: str
    action_id: str
    outcome: str


@dataclass(frozen=True)
class LifecycleEffect:
    source_action_id: str
    action_id: str
    status: str
    from_queue: str
    to_queue: str
    choice_id: str
    previous_choice_action_state: str
    nominal_end: float
    boundary: int
    canceled_at: float | None
    cancellation_reason: str | None


@dataclass(frozen=True)
class ReservationReleaseEffect:
    source_action_id: str
    action_id: str
    choice_id: str
    object_id: str
    not_before_boundary: int
    after_settlement: bool = True


@dataclass(frozen=True)
class PostCommitNotificationIntent:
    source_action_id: str
    action_id: str
    topic: str = 'action_outcome_available'
    after_commit: bool = True


@dataclass(frozen=True)
class ObserverProjection:
    observer_id: str
    observations: object
    interpretations: object
    heard_accounts: object
    belief_recipient_ids: tuple


@dataclass(frozen=True)
class BeliefProjection:
    identity: RecipientIdentity
    observer_id: str
    evidence: object
    interpretations: object
    current_readings: object
    belief_history: tuple
    auxiliary: object


@dataclass(frozen=True)
class AccountsProjection:
    identity: RecipientIdentity
    accounts: tuple
    delivery_effect_ids: tuple


@dataclass(frozen=True)
class LocationEvidenceProjection:
    identity: RecipientIdentity
    observer_id: str
    observations: object
    effect_ids: tuple


@dataclass(frozen=True)
class ObjectEvidenceProjection:
    identity: RecipientIdentity
    observer_id: str
    observations: object
    effect_ids: tuple


@dataclass(frozen=True)
class ObjectiveUse:
    subject_id: str
    key: object
    requested_by: tuple
    consumed_by: tuple
    constructed: bool
    eligible_new_fact: bool


@dataclass(frozen=True)
class ObserverRandomTrace:
    action_id: str
    stage: str
    starting_state: tuple
    ending_state: tuple
    roll: int | None = None


@dataclass(frozen=True)
class SupportedBoundaryCandidate:
    boundary: object
    objective: object
    effects: object
    recipients: object
    lifecycle: object
    objective_use: tuple
    observer_trace: tuple
    notification_intents: tuple
    context: object = field(repr=False, compare=False)
    coverage: str = 'complete_supported_due_set'
    ready_for_publication: bool = False
    missing_dependencies: tuple = ('5C_whole_interval_movement_clock_rng_staging_and_atomic_publication_recovery',
        'D7_target_history_checkpoint_replay_and_consumer_compatibility')

    def target(self, identity):
        return self.boundary.target(identity)


def _capture_belief(ledger, observer_id):
    data = native_data(ledger, (BeliefLedger,))
    if (inspect.getattr_static(type(ledger),'learn') is not _NATIVE_BELIEF_LEARN
            or inspect.getattr_static(type(ledger),'count_estimate') is not _NATIVE_BELIEF_COUNT
            or inspect.getattr_static(type(ledger),'discrepancies') is not _NATIVE_BELIEF_DISCREPANCIES):
        raise UnsupportedEvaluation('custom Belief calculation requires a reviewed pure adapter')
    _check(data['observer_id'] == observer_id, 'Belief ledger belongs to a different observer')
    if any(type(data[k]) is not dict for k in ('_evidence','_interpretations','_current_reassessments')) or any(type(data[k]) is not list for k in ('_belief_history','_reassessments','communication_log','_inquiry_history')):
        raise UnsupportedEvaluation('unreviewed Belief storage container')
    evidence = frozen_value(data['_evidence']); interpretations = frozen_value(data['_interpretations'])
    current = frozen_value(data['_current_reassessments'])
    for key, value in evidence.items():
        _check(type(key) is str and type(value) is FieldObservation and key == value.id, 'invalid existing evidence identity')
    for readings in (interpretations, current):
        for key, value in readings.items():
            _check(key in evidence and type(value) is FieldInterpretation
                and value.observation_id == key and value.observer_id == evidence[key].observer_id, 'invalid existing interpretation')
    auxiliary = frozen_value({k: data[k] for k in (
        '_reassessments','communication_log','_inquiry_history')})
    return FrozenBelief(RecipientIdentity('in_world_belief_ledger', id(ledger)), observer_id, evidence,
        interpretations, current, frozen_value(data['_belief_history']), auxiliary)


def _capture_location_evidence(ledger, observer_id):
    if type(ledger) is not LocationEvidenceLedger or ledger.observer_id != observer_id:
        raise UnsupportedEvaluation('location evidence recipient must belong to the observing Being')
    if inspect.getattr_static(type(ledger), 'last_seen_location', None) is not _NATIVE_LOCATION_LAST_SEEN:
        raise UnsupportedEvaluation('unreviewed location evidence query override')
    data = native_data(ledger, (LocationEvidenceLedger,))
    if type(data.get('_observations')) is not dict:
        raise UnsupportedEvaluation('unreviewed location evidence storage')
    observations = frozen_value(data['_observations'])
    for key, value in observations.items():
        _check(type(key) is str and type(value) is BeingLocationObservation
               and key == value.id and value.observer_id == observer_id,
               'invalid or foreign existing location evidence')
    identity = RecipientIdentity('observer_location_evidence', id(ledger))
    return FrozenLocationEvidence(identity, observer_id, observations)


def _capture_object_evidence(ledger, observer_id):
    if type(ledger) is not ObjectObservationLedger or ledger.observer_id != observer_id:
        raise UnsupportedEvaluation('Object evidence recipient must belong to the observing Being')
    if inspect.getattr_static(type(ledger), 'last_observation', None) is not _NATIVE_OBJECT_LAST:
        raise UnsupportedEvaluation('unreviewed Object evidence query override')
    data = native_data(ledger, (ObjectObservationLedger,))
    if type(data.get('_observations')) is not dict:
        raise UnsupportedEvaluation('unreviewed Object evidence storage')
    observations = frozen_value(data['_observations'])
    for key, value in observations.items():
        _check(type(key) is str and type(value) is ObjectObservation
               and key == value.id and value.observer_id == observer_id,
               'invalid or foreign existing Object evidence')
    identity = RecipientIdentity('observer_object_evidence', id(ledger))
    return FrozenObjectEvidence(identity, observer_id, observations)


def capture_observer_context(encounter, boundary, *, rng_state=None, _stage=None,
                             _restore_context=None):
    """Read-only extension of 5B2 capture; callback and recipient adapters are closed."""
    context = capture_objective_context(encounter, boundary, rng_state=rng_state,
        _stage=_stage,_restore_context=_restore_context)
    ed = object.__getattribute__(encounter, '__dict__')
    world = object.__getattribute__(ed['universe'], '__dict__')
    book = native_data(ed['_choice_book'], (ChoiceBook,))
    if _stage is not None:
        ed = dict(ed, pending_action_list=_stage.pending_ids)
        world = dict(world, event_history=_stage.events)
        book = dict(book, _registered=_stage.registered, _states=_stage.states)
    actions, recipients, lifecycle = {}, {}, {}
    for aid, view in context.snapshot.actions.items():
        action = world['event_history'][aid]
        data = object.__getattribute__(action, '__dict__')
        if _stage is not None:
            data = dict(data, **_stage.initialization.get(aid, {}))
        # Never invoke completion callbacks to discover whether they are safe.
        if inspect.getattr_static(type(action),'resolve',None) is not _NATIVE_RESOLVERS.get(type(action)):
            raise UnsupportedEvaluation('unreviewed resolver override requires an explicit staging adapter')
        expected = _NATIVE_HOOKS.get(type(action))
        if 'on_completed' in data or inspect.getattr_static(type(action), 'on_completed', None) is not expected:
            raise UnsupportedEvaluation('unreviewed on_completed callback cannot bypass staging')
        known = book['_registered'].get(aid)
        _check(known is not None, 'lifecycle Action bypassed whole-choice registration')
        packet = known[1]
        resources = tuple((r.object_id, r.boundary) for r in book['_reservations'] if r.action_id == aid)
        canceled_at, reason = data.get('canceled_at'), data.get('cancellation_reason')
        if view.lifecycle == 'cancelled':
            _check(type(canceled_at) in (int,float) and math.isfinite(canceled_at) and canceled_at <= boundary
                and type(reason) is str, 'unsupported cancellation metadata')
        lifecycle[aid] = FrozenLifecycle(aid, known[0], book['_states'][aid], resources, canceled_at, reason)
        if view.family == 'observe_group':
            if (inspect.getattr_static(type(data['observer']),'sample',None) is not _NATIVE_SAMPLE
                    or inspect.getattr_static(type(data['interpreter']),'interpret',None) is not _NATIVE_INTERPRET):
                raise UnsupportedEvaluation('unreviewed observer/interpreter calculation override')
            sensor = freeze(native_data(data['observer'], (SampledGroupObservation,)))
            interpreter = freeze(native_data(data['interpreter'], (FieldInterpreter,)))
            seed, key = data['seed'], data['random_key']
            _check(type(seed) is int and type(key) is str and bool(key), 'invalid observer RNG declaration')
            policy = freeze(data['experience_policy'])
            _check(set(policy) == {'success','failure'} and all(type(v) is int and v >= 0 for v in policy.values()), 'invalid observation practice policy')
            recipient = None
            if data['ledger'] is not None:
                frozen = _capture_belief(data['ledger'], view.actor_id)
                recipient = frozen.identity; recipients[recipient] = frozen
            actions[aid] = ObserverActionInputs(aid, sensor, interpreter, seed, key, data['focus_category'], policy, recipient)
        elif view.family == 'spot':
            from activities import SpotAction
            from statistical_group import StatisticalGroup
            from object import ObjectInstance
            registry = object.__getattribute__(ed['universe'], '__dict__')['object_registry'].object_instances
            target = registry.get(view.target_id)
            if type(action) is not SpotAction:
                raise UnsupportedEvaluation('unreviewed native Spot Action contract')
            if data.get('object_ledger') is not None:
                if (type(data.get('object_ledger')) is not ObjectObservationLedger
                        or type(target) is not ObjectInstance
                        or view.target_id not in context.snapshot.participant_ids
                        or context.snapshot.entity(view.target_id).category != 'object'
                        or data.get('location_ledger') is not None
                        or data.get('ledger') is not None
                        or data.get('group_fully_visible') is True):
                    raise UnsupportedEvaluation('Object evidence requires one participating native ObjectInstance and its owner ledger')
                frozen = _capture_object_evidence(data['object_ledger'], view.actor_id)
                recipients[frozen.identity] = frozen
                actions[aid] = ObserverActionInputs(aid, object_recipient=frozen.identity)
            elif data.get('location_ledger') is not None:
                if (type(target) is StatisticalGroup
                        or view.target_id not in context.snapshot.participant_ids
                        or context.snapshot.entity(view.target_id).category != 'being'):
                    raise UnsupportedEvaluation('location evidence is supported only for a participating Being target')
                frozen = _capture_location_evidence(data['location_ledger'], view.actor_id)
                recipients[frozen.identity] = frozen
                actions[aid] = ObserverActionInputs(aid, location_recipient=frozen.identity)
            elif aid in context.snapshot.objective_inputs.actions:
                if (type(target) is not StatisticalGroup
                        or data.get('group_fully_visible') is not True or data.get('ledger') is None):
                    raise UnsupportedEvaluation('exact Group evidence requires the declared native Spot/visibility/ledger contract')
                frozen = _capture_belief(data['ledger'], view.actor_id)
                recipients[frozen.identity] = frozen
                actions[aid] = ObserverActionInputs(aid, belief_recipient=frozen.identity)
        elif view.family == 'history_request':
            recipient = None; values = data['received_accounts']
            if values is not None:
                if type(values) is not list:
                    raise UnsupportedEvaluation('received_accounts must be a reviewed in-world native list')
                _check(all(type(a) is HeardAccount for a in values), 'opaque in-world account contents')
                recipient = RecipientIdentity('in_world_received_accounts', id(values))
                recipients[recipient] = FrozenAccounts(recipient, frozen_value(values))
            claim = data['substituted_claim']
            _check(claim is None or type(claim) is str and bool(claim.strip()), 'unsupported claim')
            actions[aid] = ObserverActionInputs(aid, account_recipient=recipient, substituted_claim=claim)
    inputs = FrozenObserverInputs(context.snapshot, MappingProxyType(actions), MappingProxyType(recipients),
        MappingProxyType(lifecycle), tuple(ed['pending_action_list']), tuple(ed['finished_action_list']),
        tuple(ed['cancelled_action_list']), world['_schedule_revision'])
    return replace(context, observer_inputs=inputs)


def validate_complete_context(context):
    _check(type(context) is ObjectiveContext and type(context.observer_inputs) is FrozenObserverInputs
        and context.observer_inputs.snapshot is context.snapshot, 'complete observer context missing/different snapshot')
    inputs = context.observer_inputs
    objective_ids = set(context.snapshot.objective_inputs.actions)
    extra = set(inputs.actions) - objective_ids
    _check(set(inputs.lifecycle) == set(context.snapshot.actions)
        and objective_ids.issubset(inputs.actions)
        and all(inputs.actions[key].location_recipient is not None
                or inputs.actions[key].object_recipient is not None
                for key in extra), 'incomplete frozen observer/lifecycle coverage')
    return inputs


def _effect_id(snapshot, action_id, channel, slot):
    return EffectIdentity(snapshot.encounter_id, snapshot.boundary, action_id, channel, slot)


def _append_effect(rows, snapshot, action_id, channel, slot, effect):
    rows.append(IdentifiedEffect(_effect_id(snapshot, action_id, channel, slot), effect))


def _belief_acquire(frozen, observation, interpretation):
    evidence, interpretations = dict(frozen.evidence), dict(frozen.interpretations)
    current = dict(frozen.current_readings)
    if observation.id in evidence:
        if evidence[observation.id] != observation or interpretations.get(observation.id) != interpretation:
            raise EvaluationIntegrityError('observation ID conflicts with existing Belief evidence')
        return frozen, False
    evidence[observation.id] = observation
    if interpretation is not None:
        interpretations[observation.id] = interpretation
    readings = {key: current.get(key, interpretations.get(key)) for key in evidence}
    revisions = belief_revisions(tuple(evidence.values()), readings, observation.group_id,
        'observation', observation.time, observation.id)
    return replace(frozen, evidence=MappingProxyType(evidence), interpretations=MappingProxyType(interpretations),
        belief_history=frozen.belief_history + tuple(revisions)), True


def _validate_effect_rows(rows, snapshot, due, recipients, *, inputs, proposals, notify):
    seen = set()
    accepted = (ObservationEffect, InterpretationEffect, BeliefAcquisitionEffect,
        LocationObservationEffect, ObjectObservationEffect, TestimonyEffect,
        AccountDeliveryEffect, ActionOutcomeEffect, LifecycleEffect, ReservationReleaseEffect,
        PostCommitNotificationIntent, AwarenessEffect, PracticeEffect)
    # Core combat effects have already been validated by native reconciliation.
    from action_evaluation import (DamageEffect, FatalEffect, ProtectionEffect,
        DefenseEffect, ProjectileReleaseEffect, PickupEffect, ReadyWeaponEffect)
    accepted += (DamageEffect, FatalEffect, ProtectionEffect, DefenseEffect,
                 ProjectileReleaseEffect, PickupEffect, ReadyWeaponEffect)
    for row in rows:
        _check(type(row) is IdentifiedEffect and type(row.identity) is EffectIdentity, 'invalid staged effect')
        key = row.identity
        _check(key not in seen and key.encounter_id == snapshot.encounter_id and key.boundary == snapshot.boundary
            and key.source_action_id in due, 'duplicate/foreign staged effect identity')
        seen.add(key)
        _check(type(row.effect) in accepted and row.effect.source_action_id == key.source_action_id, 'unsupported/contradictory staged effect')
        if type(row.effect) in (ObservationEffect, InterpretationEffect, BeliefAcquisitionEffect,
                                LocationObservationEffect, ObjectObservationEffect,
                                TestimonyEffect, AccountDeliveryEffect):
            _check(row.effect.target_id == snapshot.actions[key.source_action_id].actor_id, 'observer effect has wrong authoritative recipient')
        if type(row.effect) in (BeliefAcquisitionEffect, LocationObservationEffect,
                                ObjectObservationEffect, AccountDeliveryEffect):
            _check(row.effect.recipient in recipients, 'unknown external authoritative recipient')
        if type(row.effect) is LocationObservationEffect:
            action = snapshot.actions[key.source_action_id]
            evidence = row.effect.observation
            projected = recipients[row.effect.recipient]
            _check(row.effect.recipient.role == 'observer_location_evidence'
                   and type(projected) is LocationEvidenceProjection
                   and projected.identity == row.effect.recipient
                   and projected.observer_id == row.effect.target_id
                   and projected.observations.get(evidence.id) == evidence
                   and evidence.observer_id == row.effect.target_id
                   and evidence.id == action.id
                   and evidence.being_id == action.target_id
                   and evidence.source_action_id == action.id
                   and evidence.encounter_id == snapshot.encounter_id
                   and evidence.boundary == snapshot.boundary
                   and evidence.time == action.nominal_end
                   and evidence.position == snapshot.entity(action.target_id).position
                   and evidence.basis == 'successful_deliberate_spot',
                   'location evidence does not match the common Spot snapshot')
        if type(row.effect) is ObjectObservationEffect:
            action = snapshot.actions[key.source_action_id]
            evidence = row.effect.observation
            projected = recipients[row.effect.recipient]
            entity = snapshot.entity(action.target_id)
            _check(row.effect.recipient.role == 'observer_object_evidence'
                   and type(projected) is ObjectEvidenceProjection
                   and projected.identity == row.effect.recipient
                   and projected.observer_id == row.effect.target_id
                   and projected.observations.get(evidence.id) == evidence
                   and evidence.observer_id == row.effect.target_id
                   and evidence.id == action.id
                   and evidence.object_id == action.target_id
                   and evidence.source_action_id == action.id
                   and evidence.encounter_id == snapshot.encounter_id
                   and evidence.boundary == snapshot.boundary
                   and evidence.time == action.nominal_end
                   and evidence.position == entity.position
                   and evidence.projectile_status == entity.data.get('projectile_status')
                   and evidence.basis == 'successful_deliberate_spot',
                   'Object evidence does not match the common Spot snapshot')
        if type(row.effect) is PostCommitNotificationIntent:
            _check(row.effect.after_commit is True, 'notification must wait for successful commitment')
        if type(row.effect) is ReservationReleaseEffect:
            _check(row.effect.after_settlement is True and row.effect.not_before_boundary == snapshot.boundary, 'resource handoff precedes settlement')
    for aid in due:
        owned = [row.effect for row in rows if row.identity.source_action_id == aid]
        def count(cls):return sum(type(e) is cls for e in owned)
        _check(count(ActionOutcomeEffect) == 1 and count(LifecycleEffect) == 1
            and count(PostCommitNotificationIntent) == int(notify), 'missing/extra lifecycle or notification intent')
        _check(next(e for e in owned if type(e) is ActionOutcomeEffect).outcome == proposals[aid].outcome, 'outcome intent contradicts Action result')
        expected_resources = {resource for resource,_ in inputs.lifecycle[aid].resources}
        released = [e.object_id for e in owned if type(e) is ReservationReleaseEffect]
        _check(len(released) == len(expected_resources) and set(released) == expected_resources, 'missing/duplicate reservation release')
        action = snapshot.actions[aid]; item = inputs.actions.get(aid)
        success = ((action.family == 'observe_group'
                    or action.family == 'spot' and item is not None
                    and item.belief_recipient is not None)
                   and proposals[aid].outcome == 'success')
        heard = action.family == 'history_request' and proposals[aid].outcome == 'heard'
        interpretation_required = action.family == 'observe_group' and success
        _check(count(ObservationEffect) == int(success) and count(InterpretationEffect) == int(interpretation_required)
            and count(TestimonyEffect) == int(heard), 'missing/extra evidence, interpretation or testimony')
        _check(count(BeliefAcquisitionEffect) == int(success and item.belief_recipient is not None)
            and count(AccountDeliveryEffect) == int(heard and item.account_recipient is not None), 'missing/extra authoritative delivery')
        location_success = (action.family == 'spot' and item is not None
                            and item.location_recipient is not None
                            and proposals[aid].outcome == 'success')
        _check(count(LocationObservationEffect) == int(location_success),
               'missing/extra Spot location observation')
        object_success = (action.family == 'spot' and item is not None
                          and item.object_recipient is not None
                          and proposals[aid].outcome == 'success')
        _check(count(ObjectObservationEffect) == int(object_success),
               'missing/extra Spot Object evidence')


def build_supported_candidate(context, *, notify=False):
    """One complete supported-family result, still not a world transaction.

    Actual eligibility is determined before objective construction. All observer
    calculations use common pre-action ranks; append-order belief revisions are
    recipient reconciliation, never world-state precedence for Action checks.
    """
    _check(type(notify) is bool, 'notification option must be a Boolean')
    inputs = validate_complete_context(context); snapshot = context.snapshot
    due = {key for key, a in snapshot.actions.items() if a.boundary == snapshot.boundary}
    ordered = sorted((snapshot.actions[k] for k in due), key=lambda a:(a.priority,a.order,a.id))
    core = evaluate_snapshot(context.native_snapshot)
    core_proposals = {p.action_id:p for p in core.proposals}
    outcomes, roll_metadata, active = {}, {}, set()
    trace = []
    for action in ordered:
        if action.id not in inputs.actions:
            continue
        item = inputs.actions[action.id]
        if action.lifecycle == 'cancelled':
            outcomes[action.id] = 'interrupted'; continue
        if action.family == 'spot':
            # Deliberate Spot is an ordinary native discovery Action. Its six
            # second timing, DC, roll and Awareness proposal come from the
            # frozen core evaluator; Group sensor rules are not reused here.
            proposal = core_proposals.get(action.id)
            if proposal is None:
                raise ObserverProposalError('due Spot Action is missing its native proposal')
            outcomes[action.id] = proposal.outcome
            roll = dict(proposal.metadata).get('roll')
            if roll is not None:
                roll_metadata[action.id] = (None, roll)
            if (proposal.outcome == 'success' and action.id in inputs.actions
                    and action.id in snapshot.objective_inputs.actions):
                active.add(action.id)
            continue
        distance = snapshot.distance(action.actor_id,action.target_id)
        limit = (item.observer_config['coarse_range_m']
                 if action.family == 'observe_group' else action.data['max_distance'])
        outcome = 'unplaced' if distance is None else 'out_of_range' if distance > limit else None
        if outcome is None and action.family == 'history_request':
            outcome = 'heard' if action.target_id in snapshot.awareness.get(action.actor_id,()) else 'not_aware'
        if outcome is None:
            level = snapshot.entity(action.actor_id).data['skills'].get('spot') or 0
            rng = observation_rng(item.seed,item.random_key,action.target_id,action.start,'d20')
            start = rng.getstate(); roll = rng.randint(1,20)
            trace.append(ObserverRandomTrace(action.id,'d20',start,rng.getstate(),roll))
            outcome = 'success' if group_check(roll,level,distance,item.observer_config['detailed_range_m'],snapshot.difficulty) else 'failure'
            roll_metadata[action.id] = (level,roll)
        outcomes[action.id] = outcome
        if outcome in ('success','heard'):
            active.add(action.id)
    native_companion = reconcile_boundary(context.native_snapshot, core)
    objective = build_objective_candidate(context,native_companion,active_requests=frozenset(active))
    observers = {key:{'observations':{},'interpretations':{},'accounts':{},'belief_ids':set()}
        for key, e in snapshot.entities.items() if e.category == 'being'}
    recipient_states = dict(inputs.recipients); account_delivery_ids = {}
    location_effect_ids = {}
    rows, lifecycle, notifications = [], {}, []
    object_effect_ids = {}
    for action in ordered:
        aid = action.id; item = inputs.actions.get(aid)
        if item is None:
            proposal = core_proposals[aid]
        else:
            outcome = outcomes[aid]; effects = []; metadata = []
            actor = action.actor_id; target = action.target_id
            if action.family == 'spot':
                proposal = core_proposals[aid]
                if outcome == 'success' and item.location_recipient is not None:
                    from location_observation import BeingLocationObservation
                    location_snapshot = snapshot.entity(target)
                    if location_snapshot.category != 'being' or location_snapshot.position is None:
                        raise UnsupportedEvaluation('successful Spot location evidence requires a modeled Being position')
                    observation = BeingLocationObservation(
                        aid, actor, target, aid, snapshot.encounter_id,
                        snapshot.boundary, action.nominal_end,
                        location_snapshot.position)
                    frozen_observation = frozen_value(observation)
                    frozen_recipient = recipient_states[item.location_recipient]
                    observations = dict(frozen_recipient.observations)
                    existing = observations.get(aid)
                    if existing is not None and existing != frozen_observation:
                        raise EvaluationIntegrityError('location observation ID conflicts with existing evidence')
                    observations[aid] = frozen_observation
                    recipient_states[item.location_recipient] = replace(
                        frozen_recipient, observations=MappingProxyType(observations))
                    _append_effect(rows, snapshot, aid, 'location', 0,
                        LocationObservationEffect(aid, actor, item.location_recipient,
                                                  frozen_observation))
                    location_effect_ids.setdefault(item.location_recipient, []).append(rows[-1].identity)
                if outcome == 'success' and item.object_recipient is not None:
                    location_snapshot = snapshot.entity(target)
                    if location_snapshot.category != 'object' or location_snapshot.position is None:
                        raise UnsupportedEvaluation('successful Object Spot evidence requires a modeled Object position')
                    observation = ObjectObservation(
                        aid, actor, target, aid, snapshot.encounter_id,
                        snapshot.boundary, action.nominal_end,
                        location_snapshot.position,
                        location_snapshot.data.get('projectile_status'))
                    frozen_observation = frozen_value(observation)
                    frozen_recipient = recipient_states[item.object_recipient]
                    observations = dict(frozen_recipient.observations)
                    existing = observations.get(aid)
                    if existing is not None and existing != frozen_observation:
                        raise EvaluationIntegrityError('Object observation ID conflicts with existing evidence')
                    observations[aid] = frozen_observation
                    recipient_states[item.object_recipient] = replace(
                        frozen_recipient, observations=MappingProxyType(observations))
                    _append_effect(rows, snapshot, aid, 'object_observation', 0,
                        ObjectObservationEffect(aid, actor, item.object_recipient,
                                                frozen_observation))
                    object_effect_ids.setdefault(item.object_recipient, []).append(rows[-1].identity)
                if outcome == 'success' and aid in objective.requests:
                    from field_observation import CountReport
                    counts = objective.subject(target).counts
                    visible_total = counts['humans'] + counts['livestock'] + counts['dogs']
                    observed = FieldObservation(aid, actor, target, action.nominal_end,
                        None, None, {'visible_count': CountReport(visible_total, 0)},
                        'exact_visible_aggregate_count', {}, None)
                    observed = frozen_value(observed)
                    observers[actor]['observations'][aid] = observed
                    _append_effect(rows,snapshot,aid,'observer',0,ObservationEffect(aid,actor,aid))
                    if item.belief_recipient is not None:
                        state, acquired = _belief_acquire(
                            recipient_states[item.belief_recipient], observed, None)
                        recipient_states[item.belief_recipient] = state
                        observers[actor]['belief_ids'].add(item.belief_recipient)
                        _append_effect(rows,snapshot,aid,'delivery',0,
                            BeliefAcquisitionEffect(aid,actor,item.belief_recipient,aid,acquired))
                    key = objective.requests[aid].requested_key
                    metadata.extend((('observation_id',aid),
                        ('objective_key',(key.entity_id,key.attribute,key.time,key.detail)),
                        ('evidence_kind','exact_visible_aggregate_count'),
                        ('visible_count',visible_total)))
                    proposal = replace(proposal, metadata=proposal.metadata + tuple(metadata))
            elif action.family == 'observe_group':
                level, roll = roll_metadata.get(aid,(snapshot.entity(actor).data['skills'].get('spot') or 0,None))
                metadata.extend((('skill_level_used',level),('roll',roll)))
                if outcome in ('success','failure'):
                    effects.append(PracticeEffect(aid,actor,'spot',item.policy[outcome]))
                if outcome == 'success':
                    skill = item.interpreter_config['skill_name']
                    interpretation_rank = snapshot.entity(actor).data['skills'].get(skill)
                    if type(interpretation_rank) is not int or interpretation_rank < 0:
                        raise UnsupportedEvaluation('native interpreter requires an explicit nonnegative integer rank; absent/invalid rank is not normalized')
                    rng = observation_rng(item.seed,item.random_key,target,action.start,'evidence'); start = rng.getstate()
                    observed = frozen_value(sample_group_evidence(item.observer_config,objective.subject(target).counts,
                        snapshot.entity(target).position,target,actor,action.nominal_end,
                        snapshot.distance(actor,target),level,aid,rng,item.focus))
                    interpreted = frozen_value(interpret_field(observed,actor,interpretation_rank,skill,item.interpreter_config['expert_level']))
                    trace.append(ObserverRandomTrace(aid,'evidence',start,rng.getstate()))
                    observers[actor]['observations'][aid] = observed; observers[actor]['interpretations'][aid] = interpreted
                    _append_effect(rows,snapshot,aid,'observer',0,ObservationEffect(aid,actor,aid))
                    _append_effect(rows,snapshot,aid,'observer',1,InterpretationEffect(aid,actor,aid))
                    effects.append(AwarenessEffect(aid,actor,target,snapshot.distance(actor,target),item.observer_config['coarse_range_m'],'sampled_group_observation'))
                    key = objective.requests[aid].requested_key
                    metadata.extend((('observation_id',aid),('objective_key',(key.entity_id,key.attribute,key.time,key.detail))))
                    if item.belief_recipient is not None:
                        state, acquired = _belief_acquire(recipient_states[item.belief_recipient],observed,interpreted)
                        recipient_states[item.belief_recipient] = state; observers[actor]['belief_ids'].add(item.belief_recipient)
                        _append_effect(rows,snapshot,aid,'delivery',0,BeliefAcquisitionEffect(aid,actor,item.belief_recipient,aid,acquired))
            elif outcome == 'heard':
                key = objective.requests[aid].requested_key; fact = objective.subject(target).fact(key)
                words = fact.value['description'] if item.substituted_claim is None else item.substituted_claim
                account = HeardAccount(aid,actor,target,action.nominal_end,key.time,key.detail,words)
                observers[actor]['accounts'][aid] = account
                _append_effect(rows,snapshot,aid,'observer',0,TestimonyEffect(aid,actor,aid))
                effects.append(AwarenessEffect(aid,actor,target,snapshot.distance(actor,target),action.data['max_distance'],'heard_account_range_scaffold'))
                metadata.extend((('account_id',aid),('objective_key',(key.entity_id,key.attribute,key.time,key.detail)),('newly_constructed',not fact.established)))
                if item.account_recipient is not None:
                    state = recipient_states[item.account_recipient]
                    recipient_states[item.account_recipient] = replace(state,accounts=state.accounts+(account,))
                    effect = AccountDeliveryEffect(aid,actor,item.account_recipient,aid)
                    _append_effect(rows,snapshot,aid,'delivery',0,effect)
                    account_delivery_ids.setdefault(item.account_recipient,[]).append(rows[-1].identity)
            if action.family != 'spot':
                proposal = ActionProposal(aid,actor,() if target is None else (target,),outcome,tuple(effects),metadata=tuple(metadata))
        core_proposals[aid] = proposal
        life = inputs.lifecycle[aid]
        cancelled = action.lifecycle == 'cancelled'
        status = 'cancelled' if cancelled else 'finished'
        _append_effect(rows,snapshot,aid,'lifecycle',0,ActionOutcomeEffect(aid,aid,proposal.outcome))
        transition = LifecycleEffect(aid,aid,status,'cancelled' if cancelled else 'pending',status,
            life.choice_id,life.choice_action_state,action.nominal_end,snapshot.boundary,life.canceled_at,life.cancellation_reason)
        _append_effect(rows,snapshot,aid,'lifecycle',1,transition); lifecycle[aid] = transition
        for index,(resource,_) in enumerate(life.resources):
            _append_effect(rows,snapshot,aid,'release',index,ReservationReleaseEffect(aid,aid,life.choice_id,resource,snapshot.boundary))
        if notify:
            _append_effect(rows,snapshot,aid,'notification',0,PostCommitNotificationIntent(aid,aid))
            notifications.append(rows[-1])
    result = bind_evaluation_result(snapshot,tuple(core_proposals[a.id] for a in ordered),core.trace,core.provisional_rng_state)
    result = replace(result,observer_context=context)
    boundary = reconcile_boundary(snapshot,result)
    objective = revalidate_complete_objective(objective,boundary)
    targets = {}
    for key, target in boundary.targets.items():
        state = observers.get(key)
        projection = None if state is None else ObserverProjection(key,MappingProxyType(state['observations']),
            MappingProxyType(state['interpretations']),MappingProxyType(state['accounts']),tuple(sorted(state['belief_ids'],key=lambda r:(r.role,r.object_identity))))
        targets[key] = replace(target,observer_state=projection)
    recipients = {}
    for key, state in recipient_states.items():
        if type(state) is FrozenBelief:
            recipients[key] = BeliefProjection(key,state.observer_id,state.evidence,state.interpretations,
                state.current_readings,state.belief_history,state.auxiliary)
        elif type(state) is FrozenLocationEvidence:
            recipients[key] = LocationEvidenceProjection(
                key, state.observer_id, state.observations,
                tuple(location_effect_ids.get(key, ())))
        elif type(state) is FrozenObjectEvidence:
            recipients[key] = ObjectEvidenceProjection(
                key, state.observer_id, state.observations,
                tuple(object_effect_ids.get(key, ())))
        else:
            recipients[key] = AccountsProjection(key,state.accounts,tuple(account_delivery_ids.get(key,())))
    all_rows = tuple(boundary.effects.values())+tuple(rows)
    _validate_effect_rows(all_rows,snapshot,due,recipients,inputs=inputs,proposals=core_proposals,notify=notify)
    _check(set(core_proposals) == due and set(lifecycle) == due, 'incomplete supported-family coverage')
    uses = []
    for subject, state in objective.subjects.items():
        for key, fact in state.facts.items():
            requesters = []; consumers = []
            for aid, request in objective.requests.items():
                if request.subject_id != subject:
                    continue
                related = request.requested_key == key or key in request.supporting_keys
                # Formation root declarations refer to the entire derived composition.
                if snapshot.actions[aid].family == 'observe_group':related = True
                if related:requesters.append(aid)
                if related and aid in active:consumers.append(aid)
            uses.append(ObjectiveUse(subject,key,tuple(sorted(requesters)),tuple(sorted(consumers)),True,
                not fact.established and bool(consumers)))
    # A request with no constructed truth is still explicit in the usage model.
    for aid, request in objective.requests.items():
        if request.subject_id not in objective.subjects:
            uses.append(ObjectiveUse(request.subject_id,request.requested_key,(aid,),(),False,False))
    # One final Target/effect projection is shared by the boundary and objective
    # candidate. Observer records join native incoming/outgoing causal queries.
    for key, target in tuple(targets.items()):
        added_incoming = tuple(row for row in rows if getattr(row.effect,'target_id',None) == key)
        added_outgoing = tuple(row.identity for row in rows
            if snapshot.actions[row.identity.source_action_id].actor_id == key)
        targets[key] = replace(target,incoming=target.incoming+added_incoming,
            outgoing_effect_ids=target.outgoing_effect_ids+added_outgoing)
    effect_map = MappingProxyType({r.identity:r for r in all_rows})
    boundary = replace(boundary,targets=MappingProxyType(targets),effects=effect_map,observer_reconciliation_complete=True,
        publication_dependencies=('5C_whole_interval_staging_publication_and_recovery','D7_checkpoint_replay_compatibility'))
    objective = replace(objective,companion=boundary)
    return SupportedBoundaryCandidate(boundary,objective,effect_map,
        MappingProxyType(recipients),MappingProxyType(lifecycle),tuple(uses),tuple(trace),tuple(notifications),context)
