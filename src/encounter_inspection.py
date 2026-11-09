"""Committed native display projections, never commands, replay or observer policy.

Reads require the same quiescent/coordinated closure as publication. Frozen
receipt metadata supplies historical context; HP/practice remain Target-owned.
No resolver, random generator, ledger realization or completion hook is called.
"""
from dataclasses import dataclass, fields, is_dataclass
from types import MappingProxyType
import importlib

from action_evaluation import (DamageEffect, FatalEffect, ProjectileReleaseEffect, PickupEffect, ReadyWeaponEffect, freeze, native_data,
                               EvaluationIntegrityError, UnsupportedEvaluation)
from spatial.state import CartesianPosition


class InspectionRejected(EvaluationIntegrityError):
    pass


def _require(value, message):
    if not value:
        raise InspectionRejected(message)


@dataclass(frozen=True)
class CommittedBoundaryRecord:
    start: float
    end: int
    entities: object
    target_anchors: object
    actions: object
    action_anchors: object
    effects: object
    objective: object
    objective_use: tuple
    recipients: object
    starts: tuple
    participants: tuple
    schedule: object
    projectile_states: object


@dataclass(frozen=True)
class EntityInspection:
    category: str
    obj_type: str
    name: str | None
    position: object
    pre_action: object


@dataclass(frozen=True)
class ActionInspection:
    declaration: object
    facts: object
    effects: tuple
    damage_by_target: object
    fatal_targets: tuple
    lifecycle: object
    # HP and resulting skill ranks deliberately have no Action fields.

    @property
    def resolved_boundary(self):
        return self.lifecycle.boundary

    @property
    def defenses(self):
        return self.facts.defenses


@dataclass(frozen=True)
class TargetInspection:
    boundary: int
    state: object
    position: object
    properties: object
    damage_by_action: object
    fatal_floor_reduction: float
    practice_history: tuple
    projectile_state: object = None


@dataclass(frozen=True)
class BoundaryInspection:
    encounter_id: str
    boundary: int
    start: float
    action_ids: tuple
    effect_ids: tuple
    start_fences: tuple


@dataclass(frozen=True)
class ObjectiveFactInspection:
    key: object
    value: object
    established_before: bool
    revision: int
    origins: tuple
    requesting_action_ids: tuple
    supporting_keys: tuple
    consumed_by: tuple


@dataclass(frozen=True)
class ObjectiveInspection:
    subject_id: str
    ledger_identity: int
    revision: int
    facts: object
    counts: object


@dataclass(frozen=True)
class EncounterInspection:
    encounter_id: str
    boundary: int
    latest_boundary: int
    actions: object
    targets: object
    histories: object
    timeline: tuple
    effects: object
    objective: object
    objective_use: tuple
    recipients: object
    participants: tuple
    schedule: object
    schema: str = 'native-committed-inspection-v1'
    audience: str = 'omniscient inspection; not observer-filtered policy or replay'

    def action(self, action_id):
        _require(type(action_id) is str and action_id in self.actions, 'unknown/uncommitted/foreign Action')
        return self.actions[action_id]

    def target(self, target_id):
        _require(type(target_id) is str and target_id in self.targets, 'unknown/foreign Target')
        return self.targets[target_id]

    def target_history(self, target_id):
        self.target(target_id)
        return self.histories[target_id]


# Exact approved frozen native data classes. Opaque dataclasses, subclasses,
# callbacks and objects with extra attributes never pass this closed copier.
_ALLOWED = None


def _expected_body_parts(meta, target_id, initial):
    expected = dict(initial)
    for row in meta.effects.values():
        effect = row.effect
        if type(effect) is ReadyWeaponEffect and effect.target_id == target_id:
            expected[effect.hand] = effect.object_id
    return expected


def detached(value):
    global _ALLOWED
    if _ALLOWED is None:
        # Deliberately named data adapters, not all dataclasses in a namespace.
        catalog = {
            'action_evaluation': 'ActionProposal ActionView AwarenessEffect DamageEffect DefenseEffect EffectIdentity FatalEffect IdentifiedEffect PickupEffect ReadyWeaponEffect PracticeEffect ProtectionEffect ProjectileReleaseEffect',
            'action_settlement': 'TargetCandidate',
            'frozen_practice': 'CandidatePracticeUse CandidateSkillTransition PracticeProjection',
            'observer_proposals': 'ObservationEffect InterpretationEffect BeliefAcquisitionEffect LocationObservationEffect ObjectObservationEffect TestimonyEffect AccountDeliveryEffect ActionOutcomeEffect LifecycleEffect ReservationReleaseEffect PostCommitNotificationIntent ObserverProjection BeliefProjection AccountsProjection LocationEvidenceProjection ObjectEvidenceProjection FrozenLocationEvidence FrozenObjectEvidence RecipientIdentity ObjectiveUse',
            'location_observation': 'BeingLocationObservation LastSeenLocation',
            'object_observation': 'ObjectObservation',
            'objective_reality': 'ObjectiveFact SubjectRealityCandidate',
            'experience': 'SkillUse BatchSkillUse',
            'realization': 'FactKey',
            'field_observation': 'FieldObservation CountReport BeliefRevision EvidenceReassessment InquiryProposal InquiryRecord',
            'field_interpretation': 'FieldInterpretation',
            'history_conversation': 'HeardAccount',
            'interval_staging': 'AuthorityReference StartFence RegistrationIntent QueueProjection',
            'atomic_publication': 'TargetIntervalRecord PublishedInterval',
            'action_choice': 'Reservation',
            'throwing': 'ProjectileFlight ProjectileBoundaryState',
            'spatial.state': 'CartesianPosition',
            'encounter_inspection': 'CommittedBoundaryRecord EntityInspection ActionInspection TargetInspection BoundaryInspection ObjectiveFactInspection ObjectiveInspection EncounterInspection',
        }
        allowed = set()
        for name, names in catalog.items():
            namespace = vars(importlib.import_module(name))
            for cls_name in names.split():
                cls = namespace[cls_name]
                _require(type(cls) is type and cls.__module__ == name and is_dataclass(cls)
                    and cls.__dataclass_params__.frozen, 'inspection adapter class changed')
                allowed.add(cls)
        _ALLOWED = frozenset(allowed)
    if value is None or type(value) in (str, int, float, bool):
        return freeze(value)
    if type(value) in (tuple, list):
        return tuple(detached(v) for v in value)
    if type(value) in (frozenset, set):
        return frozenset(detached(v) for v in value)
    if type(value) in (dict, MappingProxyType):
        return MappingProxyType({detached(k): detached(v) for k, v in value.items()})
    if type(value) not in _ALLOWED:
        raise UnsupportedEvaluation('unreviewed committed inspection payload')
    data = native_data(value, (type(value),))
    names = tuple(f.name for f in fields(type(value)))
    _require(set(data) == set(names), 'damaged committed record fields')
    # Only closed data is copied. No dataclass constructor/extension hook runs.
    result = object.__new__(type(value))
    for name in names:
        object.__setattr__(result, name, detached(data[name]))
    return result


def fingerprint(value):
    from interval_staging import _digest, _semantic
    return _digest(_semantic(detached(value)))


def prepare_record(encounter, candidate, anchors, events):
    """Pure additional receipt provenance, constructed before any live write."""
    snap = candidate.pre_action_snapshot
    supported = candidate.supported_candidate
    entities = {}
    objects = encounter.universe.object_registry.object_instances
    for key, entity in snap.entities.items():
        obj = objects[key]
        label = object.__getattribute__(obj, '__dict__').get('name')
        entities[key] = EntityInspection(entity.category, entity.obj_type, label if type(label) is str else None,
                         entity.position, entity.data)
    actions = {aid: (snap.actions[aid], proposal) for aid, proposal in supported.boundary.actions.items()}
    projectile_states={}
    from action_evaluation import ProjectileReleaseEffect
    from throwing import ProjectileBoundaryState
    for identity, row in supported.boundary.effects.items():
        effect=row.effect
        if type(effect) is ProjectileReleaseEffect:
            source_identity=(identity.encounter_id,identity.boundary,identity.source_action_id,
                             identity.channel,identity.slot)
            projectile_states[effect.target_id]=ProjectileBoundaryState(effect.source_action_id,
                candidate.boundary,CartesianPosition(*effect.release_position),'in_flight',
                effect.impact_time,source_identity)
    for update in candidate.projectile_updates:
        projectile_states[update.object_id]=update.state
    return detached(CommittedBoundaryRecord(candidate.start_checkpoint.start, candidate.boundary,
        entities, anchors, actions, {aid: id(events[aid]) for aid in actions},
        supported.effects, supported.objective.subjects, supported.objective_use,
        supported.recipients, candidate.start_fences, snap.participant_ids,
        candidate.proposed_authoritative_changes['queues'], projectile_states))


def _idle(encounter):
    import atomic_publication as publication
    from transactional_progression import mode_of, _BINDINGS
    _require(mode_of(encounter) == 'transactional', 'inspection requires explicitly selected transactional mode')
    _require(not publication._ACTIVE and not publication._PUBLISHING,
             'inspection unavailable during publication ownership')
    _require(not _BINDINGS[id(encounter)].running.locked(), 'inspection unavailable during progression')
    fault=publication._FAULTS.get(id(encounter))
    _require(encounter.__dict__.get('boundary_fault') is None
        and (fault is None or fault.encounter() is not encounter),
             'faulted/incomplete interval cannot be inspected as final')


def _validate_live_latest(encounter, targets, meta, objectives, recipients, action_ids):
    """Reject unfenced drift; never substitute current state for historical data."""
    objects = encounter.universe.object_registry.object_instances
    from observer_proposals import (BeliefProjection, AccountsProjection,
        LocationEvidenceProjection, ObjectEvidenceProjection, _capture_belief,
        _capture_location_evidence, _capture_object_evidence)
    from field_observation import BeliefLedger
    from realization import RealityLedger, CommittedFact, FactKey
    from statistical_group import StatisticalGroup
    from being import BeingDefinition
    from object import ObjectDefinition
    from armor import ArmorDefinition
    from weapon import WeaponDefinition
    from spatial.state import SpatialState
    from skill import Skills
    from states import States
    from abilities import Abilities
    for key, target in targets.items():
        obj = objects[key]
        current=native_data(obj.current,(BeingDefinition,ObjectDefinition,ArmorDefinition,WeaponDefinition))
        if obj.spatial_state is not None:native_data(obj.spatial_state,(SpatialState,))
        _require(detached(current['hit_points']) == target.projected_hp, 'unreceipted Target HP change')
        picked_up = any(type(row.effect) is PickupEffect and row.effect.object_id == key
                        for row in meta.effects.values())
        expected_position=(None if picked_up else
                           meta.projectile_states[key].position if key in meta.projectile_states
                           else meta.entities[key].position)
        _require(detached(None if obj.spatial_state is None else obj.spatial_state.position) == expected_position, 'unreceipted position change')
        for row in meta.effects.values():
            if type(row.effect) is PickupEffect and row.effect.object_id == key:
                actor=objects.get(row.effect.target_id)
                _require(actor is not None and key in actor.possessions
                    and obj.parent_container_id==actor.id and obj.spatial_state is None,
                    'unreceipted Pick up custody transfer')
        if key in meta.projectile_states:
            _require(obj.__dict__.get('_atomic_projectile_history',())[-1] == meta.projectile_states[key],
                     'unreceipted projectile boundary state')
        properties=meta.entities[key].pre_action
        _require(detached(current['hardness']) == properties['hardness'], 'unreceipted protection change')
        if target.category == 'being':
            states=native_data(current['states'],(States,))
            abilities=native_data(current['abilities'],(Abilities,))
            _require(detached(states['states']) == properties['states']
                and detached(abilities['abilities']) == properties['abilities']
                and detached(current['body_parts']) == _expected_body_parts(meta, key, properties['body_parts'])
                and detached(current['armor_id']) == properties['armor_id']
                and detached(current['experience']) == properties['experience'], 'unreceipted participant state change')
        practice = target.practice_state
        if practice is not None:
            native_data(obj.current.skills,(Skills,))
            _require(detached(obj.skill_use_history) == _practice_history(practice), 'unreceipted skill-use history')
            _require(detached(obj.current.skills.skills) == practice.ordinary_levels
                and detached(obj.current.skills.weapon_skills) == practice.weapon_levels
                and detached(obj.skill_experience) == practice.skill_experience
                and detached(obj._skill_practice_baselines) == practice.baselines,
                'unreceipted practice change')
        if target.category == 'being':
            _require(frozenset(encounter.awareness.get(key, ())) == target.aware_of, 'unreceipted awareness change')
    for key, subject in objectives.items():
        obj = objects[key]
        ledger = obj._composition_reality if type(obj) is StatisticalGroup else obj.personal_history.reality
        data = native_data(ledger, (RealityLedger,))
        _require(id(ledger) == subject.ledger_identity, 'objective ledger identity changed')
        _require(type(data['_records']) is dict and all(type(k) is FactKey for k in data['_records']),
                 'unreviewed objective record storage')
        for existing_key in data['_records']:
            detached(existing_key)
        _require(set(data['_records']) == set(subject.facts), 'unreceipted objective fact set')
        if type(obj) is StatisticalGroup and subject.counts is not None:
            _require(detached(obj._counts) == subject.counts, 'unreceipted objective count cache')
        # All candidate facts, including reused facts, must still be canonical.
        revision = subject.base_revision + int(any(not f.established for f in subject.facts.values()))
        _require(data['_revision'] == revision, 'unreceipted objective revision')
        for key, fact in subject.facts.items():
            row = data['_records'].get(key)
            _require(type(row) is CommittedFact, 'unreviewed committed objective fact')
            rd=native_data(row,(CommittedFact,))
            expected_revision=fact.committed_revision if fact.established else revision
            _require(detached(rd['key']) == fact.key and detached(rd['value']) == fact.value
                and type(rd['revision']) is int and rd['revision'] == expected_revision
                and type(rd['origin']) is str and rd['origin'] == fact.origins[0], 'objective fact changed')
    handles = {}
    # Candidate projections retain identities for recipients of accepted
    # future Actions too. Such a recipient can be unchanged at this committed
    # boundary, so its owning Action may not yet occur in action_ids. Resolve
    # the identity against the native registered event table without invoking
    # any Action callback.
    event_history = object.__getattribute__(encounter.universe, '__dict__')['event_history']
    for action in event_history.values():
        data = object.__getattribute__(action, '__dict__')
        for field in ('ledger', 'received_accounts', 'location_ledger', 'object_ledger'):
            if data.get(field) is not None:
                handles[id(data[field])] = data[field]
    for identity, projection in recipients.items():
        handle = handles.get(identity.object_identity)
        _require(handle is not None, 'recipient identity lost')
        if type(projection) is BeliefProjection:
            native_data(handle, (BeliefLedger,))
            actual = _capture_belief(handle, projection.observer_id)
            _require(detached(actual.evidence) == projection.evidence
                and detached(actual.interpretations) == projection.interpretations
                and detached(actual.current_readings) == projection.current_readings
                and detached(actual.belief_history) == projection.belief_history
                and detached(actual.auxiliary) == projection.auxiliary, 'unreceipted Belief change')
        elif type(projection) is AccountsProjection:
            _require(type(handle) is list and detached(handle) == projection.accounts, 'unreceipted account change')
        elif type(projection) is LocationEvidenceProjection:
            from location_observation import LocationEvidenceLedger
            _require(type(handle) is LocationEvidenceLedger
                and handle.observer_id == projection.observer_id,
                'location evidence recipient identity/owner changed')
            actual = _capture_location_evidence(handle, projection.observer_id)
            _require(detached(actual.observations) == projection.observations,
                     'unreceipted observer location evidence change')
        elif type(projection) is ObjectEvidenceProjection:
            from object_observation import ObjectObservationLedger
            _require(type(handle) is ObjectObservationLedger
                and handle.observer_id == projection.observer_id,
                'Object evidence recipient identity/owner changed')
            actual = _capture_object_evidence(handle, projection.observer_id)
            _require(detached(actual.observations) == projection.observations,
                     'unreceipted observer Object evidence change')
        else:
            raise UnsupportedEvaluation('unreviewed inspection recipient')


def _practice_history(practice):
    if practice is None:
        return ()
    from experience import BatchSkillUse
    return detached(tuple(practice.prior_uses) + tuple(
        BatchSkillUse(practice.being_id, transition.skill_name,
            sum(use.experience for use in practice.exercises if use.skill_name == transition.skill_name),
            transition.level_before, transition.level_after, transition.time,
            tuple(use for use in practice.exercises if use.skill_name == transition.skill_name))
        for transition in practice.transitions))


def _objective_views(subjects, uses):
    result={}
    for key, subject in subjects.items():
        revision=subject.base_revision + int(any(not fact.established for fact in subject.facts.values()))
        facts={}
        for fact_key, fact in subject.facts.items():
            consumers=tuple(dict.fromkeys(aid for row in uses if row.subject_id == key and row.key == fact_key for aid in row.consumed_by))
            facts[fact_key]=ObjectiveFactInspection(fact.key,fact.value,fact.established,
                fact.committed_revision if fact.established else revision,
                fact.origins,tuple(dict.fromkeys(aid for row in uses if row.subject_id == key and row.key == fact_key for aid in row.requested_by))
                or fact.requesting_action_ids,fact.supporting_keys,consumers)
        result[key]=ObjectiveInspection(key,subject.ledger_identity,revision,MappingProxyType(facts),subject.counts)
    return MappingProxyType(result)


def inspect_encounter(encounter, boundary=None, *, receipt=None):
    """Detached omniscient display of successful commits, under native read ownership.

    Boundary defaults to the latest commit. Action lookup includes earlier
    committed Actions; Target/history lookup ends at the selected boundary.
    This API does not accept a live Action/Target object or an imported receipt.
    """
    from encounter import Encounter
    from universe import Universe
    import atomic_publication as publication
    from interval_staging import _guard_methods, _OBJECTS, _ACTIONS
    from action_evaluation import ActionProposal
    from observer_proposals import (LifecycleEffect, LocationObservationEffect,
                                    LocationEvidenceProjection, ObjectObservationEffect,
                                    ObjectEvidenceProjection)
    if type(encounter) is not Encounter:
        raise UnsupportedEvaluation('native Encounter inspection required')
    world=object.__getattribute__(encounter,'__dict__')['universe']
    if type(world) is not Universe:
        raise UnsupportedEvaluation('native Universe inspection required')
    # Only root routing/control checks precede the gate. Registry/history/Target
    # traversal happens entirely inside coordinated ownership.
    _idle(encounter)
    with publication.coordinated_access(world):
        _idle(encounter)
        _guard_methods()
        native_data(encounter,(Encounter,))
        wd=native_data(world,(Universe,))
        _require(encounter.universe is world, 'Encounter world changed')
        from object import ObjectRegistry
        registry=native_data(wd['object_registry'],(ObjectRegistry,))
        _require(type(registry['object_instances']) is dict and type(wd['event_history']) is dict,
                 'unreviewed registry storage')
        _require(all(type(key) is str for key in registry['object_instances'])
            and all(type(key) is str for key in wd['event_history']), 'unreviewed registry keys')
        _require(type(encounter.id) is str and wd['event_history'].get(encounter.id) is encounter,
                 'Encounter ownership identity changed')
        _require(encounter.active_boundary is None and not encounter._dispatching
            and not encounter._advancing and not encounter._running, 'active/inconsistent native progression')
        from action_choice import ChoiceBook
        from transactional_progression import validate_action_contract
        book=native_data(encounter._choice_book,(ChoiceBook,))
        _require(type(book['_choices']) is dict, 'unreviewed choice storage')
        for choice in book['_choices'].values():
            from action_choice import _Accepted
            _require(type(choice) is _Accepted, 'unreviewed accepted choice')
            from action_choice import ChoiceMember
            _require(type(choice.members) is tuple, 'unreviewed accepted members')
            for member in choice.members:
                _require(type(member) is ChoiceMember, 'unreviewed choice member')
                validate_action_contract(encounter, member.action)
        for field in ('pending_action_list','finished_action_list','cancelled_action_list'):
            rows=encounter.__dict__[field]
            _require(type(rows) is list and all(type(aid) is str for aid in rows), 'unreviewed Action queue')
            for aid in rows:
                validate_action_contract(encounter,wd['event_history'].get(aid))
        for field in ('time','_coordinator_time','last_processed_boundary','start_time'):
            freeze(encounter.__dict__[field])
        encounter._pending_schedule()
        history = encounter.__dict__.get('_atomic_interval_history')
        _require(type(history) is list and bool(history), 'no committed transactional boundary')
        # Authenticate and detach before reading any user-corruptible nested
        # fields or comparing identities. No opaque equality/repr hooks run.
        copies=[]
        for row in history:
            _require(type(row) is publication.PublishedInterval, 'unreviewed receipt')
            issued=publication._COMMITTED_RECEIPTS.get(id(row))
            _require(issued is not None and issued[0]() is row and issued[1]() is encounter,
                     'forged/uncommitted receipt')
            copied=detached(row)
            _require(fingerprint(copied) == issued[2], 'committed receipt altered')
            copies.append(copied)
        authorized_pickup_ids={row.effect.object_id
            for copied in copies for row in copied.inspection.effects.values()
            if type(row.effect) is PickupEffect}
        if boundary is not None:
            _require(type(boundary) is int, 'integer committed boundary required')
        if receipt is not None:
            _require(type(receipt) is publication.PublishedInterval and any(r is receipt for r in history),
                     'foreign/uncommitted receipt')
            _require(boundary is None or boundary == receipt.boundary, 'receipt/boundary mismatch')
            boundary = receipt.boundary
        boundary = history[-1].boundary if boundary is None else boundary
        _require(any(r.boundary == boundary for r in history), 'unknown/uncommitted boundary')
        _require(history[-1].boundary == encounter.last_processed_boundary == encounter.time,
                 'incomplete committed cursor')
        objects = world.object_registry.object_instances
        actions = {}; effects = {}; histories = {}; timeline = []
        latest_targets = {}; objectives = {}; recipients = {}; selected_objectives = {}; selected_recipients = {}
        selected_use = []; selected_meta = None
        previous = None
        import math
        _require(copies[0].boundary == math.floor(encounter.start_time)+1
            and copies[0].inspection.start == encounter.start_time, 'missing initial committed receipt')
        all_action_ids=[]
        target_storage={}
        projectile_effects=set()
        for live_receipt, record in zip(history,copies):
            meta = record.inspection
            _require(record.committed and record.encounter_id == encounter.id
                and type(meta) is CommittedBoundaryRecord and meta.end == record.boundary
                and (previous is None or (record.boundary == previous + 1 and meta.start == previous)), 'inconsistent committed receipt sequence')
            previous = record.boundary
            _require(tuple(meta.actions) == record.action_ids and tuple(meta.effects) == record.effect_ids,
                     'incomplete committed coverage')
            for eid, row in meta.effects.items():
                _require(eid == row.identity and eid.encounter_id == encounter.id
                    and eid.boundary == record.boundary and eid.source_action_id in meta.actions,
                    'foreign effect provenance')
                if type(row.effect) is LocationObservationEffect:
                    declaration, facts = meta.actions[eid.source_action_id]
                    evidence = row.effect.observation
                    projection = meta.recipients.get(row.effect.recipient)
                    _require(row.effect.target_id == declaration.actor_id
                        and row.effect.source_action_id == declaration.id
                        and declaration.family == 'spot'
                        and evidence.id == declaration.id
                        and evidence.observer_id == declaration.actor_id
                        and evidence.being_id == declaration.target_id
                        and evidence.source_action_id == declaration.id
                        and evidence.encounter_id == encounter.id
                        and evidence.boundary == record.boundary
                        and evidence.time == declaration.nominal_end
                        and evidence.position == meta.entities[declaration.target_id].position
                        and facts.outcome == 'success'
                        and type(projection) is LocationEvidenceProjection
                        and projection.observer_id == declaration.actor_id
                        and projection.observations.get(evidence.id) == evidence,
                        'location observation does not match its successful Spot receipt')
                if type(row.effect) is ObjectObservationEffect:
                    declaration, facts = meta.actions[eid.source_action_id]
                    evidence = row.effect.observation
                    projection = meta.recipients.get(row.effect.recipient)
                    properties = meta.entities[declaration.target_id].pre_action
                    _require(row.effect.target_id == declaration.actor_id
                        and row.effect.source_action_id == declaration.id
                        and declaration.family == 'spot'
                        and evidence.id == declaration.id
                        and evidence.observer_id == declaration.actor_id
                        and evidence.object_id == declaration.target_id
                        and evidence.source_action_id == declaration.id
                        and evidence.encounter_id == encounter.id
                        and evidence.boundary == record.boundary
                        and evidence.time == declaration.nominal_end
                        and evidence.position == meta.entities[declaration.target_id].position
                        and evidence.projectile_status == properties.get('projectile_status')
                        and facts.outcome == 'success'
                        and type(projection) is ObjectEvidenceProjection
                        and projection.observer_id == declaration.actor_id
                        and projection.observations.get(evidence.id) == evidence,
                        'Object observation does not match its successful Spot receipt')
                if type(row.effect) is ProjectileReleaseEffect:
                    projectile_effects.add((eid.encounter_id,eid.boundary,eid.source_action_id,
                                            eid.channel,eid.slot))
            _require(type(meta.projectile_states) in (dict,MappingProxyType),
                     'unreviewed committed projectile state map')
            from throwing import ProjectileBoundaryState
            for object_id, state in meta.projectile_states.items():
                source=state.source_effect_identity if type(state) is ProjectileBoundaryState else None
                _require(type(object_id) is str and object_id in meta.target_anchors
                    and type(state) is ProjectileBoundaryState and state.boundary==record.boundary
                    and state.source_action_id==source[2] and source in projectile_effects
                    and state.status in ('in_flight','landed'),
                    'invalid or uncaused committed projectile state')
                _require(type(state.impact_time) in (int,float)
                    and (state.status=='landed') == (state.impact_time<=record.boundary),
                    'projectile landing chronology is inconsistent')
            batch_targets = {}
            for key, anchor in meta.target_anchors.items():
                obj = objects.get(key)
                native_data(obj, _OBJECTS)
                spatial_identity_ok=(id(obj.spatial_state)==anchor[2]
                    or (key in authorized_pickup_ids and obj.spatial_state is None))
                _require(detached(obj.id) == key and id(obj) == anchor[0] and id(obj.current) == anchor[1]
                    and spatial_identity_ok, 'Target identity changed')
                storage = obj.__dict__.get('_atomic_target_history')
                _require(type(storage) is list and id(storage) == anchor[3], 'Target history identity changed')
                target_storage[key]=storage
                _require(all(type(r) is publication.TargetIntervalRecord for r in storage), 'unreviewed Target history entry')
                validated=tuple(detached(r) for r in storage)
                owned = [r for r, value in zip(storage,validated)
                         if value.encounter_id == encounter.id and value.boundary == record.boundary]
                _require(len(owned) == 1 and id(owned[0]) == anchor[4]
                    and fingerprint(owned[0]) == anchor[5], 'Target history/provenance changed')
                state = detached(owned[0].state)
                _require(state.target_id == key, 'foreign Target state')
                batch_targets[key] = state
                _require(all(row.identity in meta.effects and row == meta.effects[row.identity] for row in state.incoming)
                    and all(eid in meta.effects for eid in state.outgoing_effect_ids), 'incomplete Target effect coverage')
                if record.boundary <= boundary:
                    by_action = {}
                    for row in state.incoming:
                        if type(row.effect) is DamageEffect:
                            components = by_action.setdefault(row.identity.source_action_id, {})
                            component = row.effect.component
                            components[component] = components.get(component, 0) + row.effect.amount
                    entity = meta.entities[key]
                    projectile_state=meta.projectile_states.get(key)
                    position=projectile_state.position if projectile_state is not None else entity.position
                    view = TargetInspection(record.boundary, state, position, entity,
                        freeze(by_action), state.starting_hp - min(state.starting_hp, -10) if state.fatal_effect_ids else 0,
                        _practice_history(state.practice_state), projectile_state)
                    histories.setdefault(key, []).append(view)
            latest_targets = batch_targets
            objectives.update(meta.objective); recipients.update(meta.recipients)
            for aid, (declaration, facts) in meta.actions.items():
                all_action_ids.append(aid)
                action = world.event_history.get(aid)
                from group_observation import ObserveGroupAction
                from history_conversation import AskAboutPastAction
                if type(action) in (ObserveGroupAction, AskAboutPastAction):
                    from objective_reality import objective_action_data
                    data, _ = objective_action_data(action)
                else:
                    data = native_data(action, _ACTIONS)
                _require(id(action) == meta.action_anchors[aid] and detached(data['id']) == aid
                    and type(data.get('resolution')) is ActionProposal and detached(data['resolution']) == facts,
                    'Action identity/result changed')
                _require(detached(tuple(data.get(field) for field in ('actor_id','target_id','instrument_id','start_time','end_time','parent_event_id')))
                    == (declaration.actor_id,declaration.target_id,declaration.instrument_id,declaration.start,declaration.nominal_end,encounter.id),
                    'Action declaration/provenance changed')
                own = tuple(row for row in meta.effects.values() if row.identity.source_action_id == aid)
                _require(tuple(data.get('_atomic_effect_ids', ())) == tuple(row.identity for row in own), 'Action effect coverage changed')
                life = tuple(row.effect for row in own if type(row.effect) is LifecycleEffect)
                _require(len(life) == 1 and detached(data.get('_atomic_lifecycle')) == life[0], 'Action lifecycle changed')
                if record.boundary <= boundary:
                    damage = {}
                    for row in own:
                        if type(row.effect) is DamageEffect:
                            e = row.effect
                            components = damage.setdefault(e.target_id, {})
                            components[e.component] = components.get(e.component, 0) + e.amount
                    actions[aid] = ActionInspection(declaration, facts, own, freeze(damage),
                        tuple(row.effect.target_id for row in own if type(row.effect) is FatalEffect), life[0])
            if record.boundary <= boundary:
                effects.update(meta.effects)
                selected_objectives.update(meta.objective); selected_recipients.update(meta.recipients)
                selected_use.extend(meta.objective_use)
                timeline.append(BoundaryInspection(encounter.id,record.boundary,meta.start,record.action_ids,record.effect_ids,meta.starts))
                selected_meta = meta
        for key, storage in target_storage.items():
            own_records=[row for row in storage if type(row) is publication.TargetIntervalRecord
                         and row.encounter_id == encounter.id]
            expected=[row.boundary for row in copies if key in row.inspection.target_anchors]
            _require([row.boundary for row in own_records] == expected, 'unreceipted Target history entry')
        _validate_live_latest(encounter, latest_targets, copies[-1].inspection, objectives, recipients, all_action_ids)
        return detached(EncounterInspection(encounter.id, boundary, history[-1].boundary, actions,
            {key: rows[-1] for key, rows in histories.items()}, {key: tuple(rows) for key, rows in histories.items()},
            tuple(timeline), effects, _objective_views(selected_objectives,selected_use), tuple(selected_use), selected_recipients,
            selected_meta.participants,selected_meta.schedule))
