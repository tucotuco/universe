"""Opt-in in-memory atomic publication/recovery. No default dispatch activation.

Supported isolation requires an explicit quiescent authority lease: every other
reader/writer of the closure uses coordinated_access or is stopped by its owner.
Uncooperative raw Python access is outside this contract, never made thread-safe
by the scheduling lock. No native completion/mutation callbacks execute here.
"""
from contextlib import contextmanager
from dataclasses import dataclass, replace
import itertools
import random
import threading
import weakref
from types import MappingProxyType

from action_evaluation import UnsupportedEvaluation, EvaluationIntegrityError, freeze
from interval_staging import (IntervalCandidate, AuthorityReference, _ISSUED_CANDIDATES,
    validate_interval_candidate, _read_set, _rng_input, _native_lock, _preflight, _semantic, _validate_closure, _digest, _guard_methods)
from action_choice import declaration
from action_evaluation import ProjectileReleaseEffect
from throwing import ProjectileFlight, ProjectileBoundaryState
from encounter import Encounter
from experience import BatchSkillUse
from realization import RealityLedger, CommittedFact
from observer_proposals import (BeliefProjection, AccountsProjection,
                                LocationEvidenceProjection, ObjectEvidenceProjection,
                                _capture_object_evidence)
from statistical_group import StatisticalGroup
from object import ObjectInstance
from spatial.state import CartesianPosition
from encounter_fatigue_bridge import FrozenFatigueFrame, FrozenFatigueView
from physiology_registry import ResolvedPhysiology
from universe_physical_fatigue_r4 import Profile


PHASES = ('movement','registrations','targets','practice','reality','observers',
          'lifecycle','endpoint_starts','frames_clock','adult_registry',
          'adult_group_member','adult_group_realized','adult_group_motion',
          'adult_encounter_participant','adult_reproduction_binding',
          'adult_reproduction_request','rng','consistency','mark_committed')
_GATE = threading.RLock()  # Stable lock order: process gate, then world schedule lock.
_ACTIVE = None
_PUBLISHING = False
_FAULTS = {}
_EMERGENCIES = {}  # No automatic reset: shared RNG/recipient authority may be tainted.
_COMMITTED_RECEIPTS = {}  # Process-local successful issuance; never a replay format.
_COUNTER = itertools.count(1)
_MODULE_GETSTATE, _MODULE_SETSTATE = random.getstate, random.setstate


class PublicationOwnershipError(RuntimeError):
    pass


class PublicationRejected(ValueError):
    """Pre-write caller/candidate/adapter refusal; no fault is latched."""


class PublicationFailure(RuntimeError):
    """Application failed and stopped; inspect rollback/restoration and token."""
    def __init__(self, original, phase, recovery_token, rollback_errors=()):
        self.original = original
        self.phase = phase
        self.recovery_token = recovery_token
        self.rollback_errors = tuple(rollback_errors)
        super().__init__(f'Interval publication failed at {phase}: {original}; '
            + ('ROLLBACK INTEGRITY FAILURE: '+repr(self.rollback_errors) if rollback_errors else 'checkpoint restored; explicit recovery required'))


class RollbackIntegrityFailure(PublicationFailure):
    """Emergency: automatic recovery is prohibited; external repair is required."""


@dataclass
class RNGCursor:
    """Explicit caller-owned, coordinated native RNG cursor; never serialized."""
    state: tuple


@dataclass(eq=False,frozen=True)
class _AuthorityLease:
    encounter: object
    thread: int


@dataclass(frozen=True)
class TargetIntervalRecord:
    encounter_id: str
    boundary: int
    state: object  # TargetCandidate: resulting state is Target-owned.


@dataclass(frozen=True)
class ObjectiveCommitProvenance:
    encounter_id: str
    boundary: int
    key: object
    revision: int
    origins: tuple
    requesters: tuple
    consumers: tuple


@dataclass(frozen=True)
class PublishedInterval:
    encounter_id: str
    boundary: int
    action_ids: tuple
    effect_ids: tuple
    rng_state: tuple
    notification_intents: tuple
    committed: bool = True
    inspection: object = None  # Frozen display provenance; Target state stays Target-owned.


@dataclass
class _FailureState:
    encounter: object  # weakref
    candidate: object
    diagnostic: dict
    token: str
    restored: bool


def _emergency(world):
    value = _EMERGENCIES.get(id(world))
    return value is not None and value[0]() is world


def _ordered_lock(world):
    lock=_native_lock(world)
    # Reject the inverted entry before waiting for the process gate; otherwise
    # another owner holding that gate could be waiting for this schedule lock.
    if lock._is_owned() and not _GATE._is_owned():
        raise PublicationOwnershipError('lock order requires publication/coordinated gate before schedule lock')
    return lock


@contextmanager
def publication_boundary(encounter, *, quiescent=False):
    """Explicit exclusive authority contract, not a claim about raw Python.

    The owner asserts unmanaged readers/writers, legacy facades, physical updates
    and RNG users are stopped. Cooperating concurrent users must bracket their
    entire native access in coordinated_access, which blocks on this same gate.
    All recipients (including external lists) and the RNG owner are included.
    """
    global _ACTIVE
    if quiescent is not True:
        raise PublicationOwnershipError('publication requires explicit quiescent/coordinated authority')
    if type(encounter) is not Encounter:raise PublicationOwnershipError('native Encounter ownership required')
    world = object.__getattribute__(encounter,'__dict__')['universe']
    lock=_ordered_lock(world)
    with _GATE:
        if _ACTIVE is not None:
            raise PublicationOwnershipError('nested/reentrant publication ownership')
        if _EMERGENCIES:
            raise PublicationOwnershipError('Controlled publication process blocked by rollback integrity emergency')
        if _native_lock(world) is not lock:raise PublicationOwnershipError('schedule lock identity changed')
        with lock:
            lease = _AuthorityLease(encounter, threading.get_ident())
            _ACTIVE = lease
            try: yield lease
            finally:
                _ACTIVE = None


@contextmanager
def coordinated_access(world):
    """Bracket ALL native reads/writes by a cooperating external participant.

    This does not retrofit arbitrary Python getters/setters with locking.
    Reentrant access during application is refused, not exposed midway.
    """
    lock=_ordered_lock(world)
    with _GATE:
        if _ACTIVE is not None and (_PUBLISHING or object.__getattribute__(_ACTIVE.encounter,'__dict__')['universe'] is not world):
            raise PublicationOwnershipError('intermediate or cross-world reentrant native access')
        if _EMERGENCIES:raise PublicationOwnershipError('controlled access blocked by rollback integrity emergency')
        if _native_lock(world) is not lock:raise PublicationOwnershipError('schedule lock identity changed')
        with lock:yield


def _owned(encounter, ownership):
    if _EMERGENCIES:raise PublicationOwnershipError('rollback integrity emergency requires out-of-band repair; no controlled recovery')
    if (type(ownership) is not _AuthorityLease or ownership is not _ACTIVE
            or ownership.thread != threading.get_ident() or ownership.encounter is not encounter
            or _PUBLISHING):
        raise PublicationOwnershipError('current same-thread exclusive publication lease required')


def target_interval_history(target):
    return tuple(object.__getattribute__(target,'__dict__').get('_atomic_target_history',()))


def target_effects_from(target, action_id):
    return tuple(row for batch in target_interval_history(target) for row in batch.state.incoming
                 if row.identity.source_action_id == action_id)


def _materialize(value):
    """Native JSON fact/frame data only; no serializers or custom deepcopy."""
    if type(value) is MappingProxyType:return {k:_materialize(v) for k,v in value.items()}
    if type(value) is tuple:return [_materialize(v) for v in value]
    if value is None or type(value) in (str,int,float,bool):return value
    raise UnsupportedEvaluation('non-native mutable fact/frame publication value')


@dataclass
class _AttributeWrite:
    storage: dict
    key: str
    after: object
    existed: bool
    before: object
    before_order: tuple

    def apply(self):dict.__setitem__(self.storage,self.key,self.after)
    def undo(self):
        if self.existed:dict.__setitem__(self.storage,self.key,self.before)
        else:dict.pop(self.storage,self.key,None)
        # A partly failed write may have removed its key. Restore its original
        # insertion position too, retaining other entries until their inverses.
        if tuple(key for key in self.storage if key in self.before_order)!=tuple(key for key in self.before_order if key in self.storage):
            current=dict(self.storage)
            ordered={key:current[key] for key in self.before_order if key in current}
            ordered.update((key,value) for key,value in current.items() if key not in ordered)
            dict.clear(self.storage);dict.update(self.storage,ordered)
    def verify(self):return self.key in self.storage and self.storage[self.key] is self.after


@dataclass
class _ContentsWrite:
    storage: object
    after: object
    before: object

    def _put(self,value):
        if type(self.storage) is dict:dict.clear(self.storage);dict.update(self.storage,value)
        elif type(self.storage) is list:list.__setitem__(self.storage,slice(None),value)
        else:set.clear(self.storage);set.update(self.storage,value)
    def apply(self):self._put(self.after)
    def undo(self):self._put(self.before)
    def verify(self):
        if type(self.storage) is dict:
            return tuple(self.storage)==tuple(self.after) and all(self.storage[key] is value for key,value in self.after.items())
        if type(self.storage) is list:
            return len(self.storage)==len(self.after) and all(a is b for a,b in zip(self.storage,self.after))
        return self.storage==self.after


@dataclass
class _RNGWrite:
    role: str
    owner: object
    before: tuple
    after: tuple

    def _put(self,state):
        if self.role=='module':_MODULE_SETSTATE(state)
        elif self.role=='native_random':random.Random.setstate(self.owner,state)
        else:object.__getattribute__(self.owner,'__dict__')['state' if self.role=='caller_cursor' else '_rng_state']=state
    def apply(self):self._put(self.after)
    def undo(self):self._put(self.before)
    def verify(self):
        actual = (_MODULE_GETSTATE() if self.role=='module' else random.Random.getstate(self.owner)
            if self.role=='native_random' else object.__getattribute__(self.owner,'__dict__')['state' if self.role=='caller_cursor' else '_rng_state'])
        return actual==self.after


class _WritePlan:
    def __init__(self):
        self.phases={phase:[] for phase in PHASES}
        self.locations={}
        self.journal=[]
        self.adult_realization=None  # Detached until its explicit publication phases.
        self.adult_reproduction_binding=None

    def _add(self,phase,location,operation,chain=False):
        if location in self.locations and not chain:
            raise UnsupportedEvaluation('aliased/duplicate authoritative write location')
        self.locations[location]=operation;self.phases[phase].append(operation)

    def attr(self,phase,obj,key,value,*,chain=False):
        data=object.__getattribute__(obj,'__dict__')
        if type(data) is not dict:raise UnsupportedEvaluation('unsupported attribute storage')
        location=('attribute',id(data),key)
        prior=self.locations.get(location)
        self._add(phase,location,_AttributeWrite(data,key,value,True if prior is not None else key in data,
            prior.after if prior is not None else data.get(key),tuple(data)),chain=chain)

    def contents(self,phase,storage,value,*,chain=False):
        kind=type(storage)
        if kind not in (dict,list,set):raise UnsupportedEvaluation('unsupported retained container')
        after=kind(value);before=kind(storage)
        location=('contents',id(storage));prior=self.locations.get(location)
        self._add(phase,location,_ContentsWrite(storage,after,kind(prior.after) if prior is not None else before),chain=chain)

    def append(self,phase,obj,key,value):
        data=object.__getattribute__(obj,'__dict__')
        if key not in data:
            storage=[value];self.attr(phase,obj,key,storage)
        else:
            if type(data[key]) is not list:raise UnsupportedEvaluation('unsupported native history storage')
            storage=data[key];self.contents(phase,storage,storage+[value])
        return storage

    def validate_aliases(self):
        full={loc[1] for loc in self.locations if loc[0]=='contents'}
        if any(loc[0]=='attribute' and loc[1] in full for loc in self.locations):
            raise UnsupportedEvaluation('overlapping attribute/container write plan')

    def apply_phase(self,phase):
        for operation in self.phases[phase]:
            # Journal first: even an operation failing partway must be undone.
            self.journal.append(operation);operation.apply()

    def verify(self, *, skip_phase=None):
        skipped={id(op) for op in self.phases.get(skip_phase,())}
        if not all(operation.verify() for operation in (*self.locations.values(),*self.phases['rng']) if id(operation) not in skipped):
            raise EvaluationIntegrityError('post-application write-plan consistency failure')

    def rollback(self,fail_at=None):
        errors=[]
        for index,operation in enumerate(reversed(self.journal)):
            try:
                if fail_at==index:raise RuntimeError('injected inverse-journal failure')
                operation.undo()
            except BaseException as exc:errors.append(f'{type(exc).__name__}: {exc}')
        return errors


def _frame(snapshot):
    """Rebuild only native frame values from the already frozen common reads."""
    frame=object.__new__(FrozenFatigueFrame)
    frame._views=MappingProxyType({key:FrozenFatigueView(key,**dict(value)) for key,value in snapshot.fatigue.items()})
    profiles={}
    for key,modes in snapshot.physiology.items():
        profiles[key]=MappingProxyType({mode:ResolvedPhysiology(Profile(**dict(row['profile'])),
            row['identifier'],tuple(row['lineage']),row['version_hash'],row['mode']) for mode,row in modes.items()})
    frame._profiles=MappingProxyType(profiles)
    return frame


def _resolve_metadata(encounter,metadata):
    result={}
    for key,value in metadata.items():
        if type(value) is AuthorityReference:
            if value.role!='encounter' or value.identity!=id(encounter) or value.key!=encounter.id:
                raise PublicationRejected('unresolved metadata authority reference')
            value=encounter
        result[key]=value
    return result


def _recipient_handles(encounter,candidate):
    handles={}
    sources=[encounter.universe.event_history[aid] for aid in candidate.pre_action_snapshot.actions if aid in encounter.universe.event_history]
    sources += [m.action for r in encounter._choice_book._choices.values() for m in r.members]
    for action in sources:
        data=object.__getattribute__(action,'__dict__')
        if data.get('ledger') is not None:handles[('in_world_belief_ledger',id(data['ledger']))]=data['ledger']
        if data.get('received_accounts') is not None:handles[('in_world_received_accounts',id(data['received_accounts']))]=data['received_accounts']
        if data.get('location_ledger') is not None:handles[('observer_location_evidence',id(data['location_ledger']))]=data['location_ledger']
        if data.get('object_ledger') is not None:handles[('observer_object_evidence',id(data['object_ledger']))]=data['object_ledger']
    return {identity:handles[(identity.role,identity.object_identity)] for identity in candidate.supported_candidate.recipients}


def _preserve_known(existing,projected):
    if type(existing) is not dict or not set(existing).issubset(projected):
        raise UnsupportedEvaluation('native acquisition cannot remove existing recipient records')
    result={}
    for key,value in projected.items():
        if key in existing:
            if existing[key]!=value:raise UnsupportedEvaluation('unsupported replacement of established recipient record')
            value=existing[key]
        result[key]=value
    return result


def _append_projection(existing,projected):
    if type(existing) is not list or tuple(existing)!=tuple(projected[:len(existing)]):
        raise UnsupportedEvaluation('native recipient history must retain its existing prefix')
    return list(existing)+list(projected[len(existing):])


def _make_plan(encounter,candidate,rng_owner):
    """All inverse values and final values exist before the first write."""
    plan=_WritePlan();world=encounter.universe;book=encounter._choice_book
    objects=world.object_registry.object_instances;changes=candidate.proposed_authoritative_changes
    supported=candidate.supported_candidate;queues=changes['queues'];snapshot=candidate.pre_action_snapshot
    if candidate.adult_member_candidate is not None:
        from group_member_realization import (
            _construct_detached_adult, validate_adult_member_candidate,
        )
        operation=candidate.adult_member_candidate
        group=world.get_object_by_id(operation.request.group_id)
        try:
            validate_adult_member_candidate(encounter,group,operation)
            being,proposed_member=_construct_detached_adult(operation,encounter,group)
        except (ValueError,TypeError,KeyError,AttributeError) as exc:
            raise PublicationRejected('adult-member candidate failed publisher preflight') from exc
        slot=(operation.request.household,'adults',operation.request.index)
        member=group._members.get(slot)
        if member is None:member=proposed_member
        elif member!=proposed_member:raise PublicationRejected('GroupMember identity/placement mismatch')
        if (being.id in objects or being.id in encounter.being_list
                or being.id in encounter.non_being_object_list):
            raise PublicationRejected('adult-member identity collision before publication')
        plan.adult_realization=(operation,group,being,member,slot)
        if operation.request.reproductive_person_id is not None:
            from reproduction_being_bridge import (
                _NativeBeingBindingRecord, _definition_signature,
            )
            reproduction=world._reproduction_group_registry
            if (operation.reproduction_registry_identity!=id(reproduction)
                    or operation.reproduction_registry_revision!=reproduction._revision
                    or operation.reproduction_group_id
                    != reproduction._canonical_group_id_unlocked(
                        reproduction._group_id_by_offspring.get(operation.member_id, ''))):
                raise PublicationRejected('ReproductionGroup binding dependencies changed')
            definition_signature=_definition_signature(being.original)
            normalized=(being.id,being.name,definition_signature)
            request_key=operation.request.reproduction_request_key
            if (operation.member_id not in reproduction._person_id_reservations
                    or reproduction._group_id_by_offspring.get(operation.member_id) is None
                    or operation.member_id in reproduction._native_beings_by_person_id
                    or request_key in reproduction._native_being_requests
                    or request_key in reproduction._requests
                    or request_key in reproduction._generation_requests
                    or request_key in reproduction._progressive_requests):
                raise PublicationRejected('explicit offspring binding is no longer available')
            binding_record=_NativeBeingBindingRecord(
                request_key,operation.member_id,normalized,being)
            plan.adult_reproduction_binding=(reproduction,binding_record)
    events=dict(world.event_history)
    for record in book._choices.values():
        for member in record.members:
            if member.action.id in changes['action_metadata']:events[member.action.id]=member.action
    for key,pos in changes['positions'].items():
        if pos is not None and objects[key].spatial_state.position!=pos:
            plan.attr('movement',objects[key].spatial_state,'position',pos)
    for update in candidate.projectile_updates:
        obj=objects.get(update.object_id)
        if (obj is None or type(update.prior_flight) is not ProjectileFlight
                or object.__getattribute__(obj,'__dict__').get('_projectile_flight') is not update.prior_flight
                or type(update.next_flight) is not ProjectileFlight
                or type(update.state) is not ProjectileBoundaryState):
            raise PublicationRejected('projectile flight dependency changed')
        plan.attr('movement',obj,'_projectile_flight',update.next_flight)
        plan.append('movement',obj,'_atomic_projectile_history',update.state)
    for row in supported.boundary.effects.values():
        effect=row.effect
        if type(effect) is not ProjectileReleaseEffect:continue
        obj=objects.get(effect.target_id);source=events.get(effect.source_action_id)
        if (obj is None or type(obj) is not ObjectInstance or source is None
                or object.__getattribute__(obj,'__dict__').get('_projectile_flight') is not None
                or obj.spatial_state is None):
            raise PublicationRejected('projectile release target is unavailable or already in flight')
        actor=objects.get(source.actor_id)
        if actor is None or effect.target_id not in actor.possessions:
            raise PublicationRejected('projectile release no longer owns its Object')
        plan.contents('targets',actor.possessions,[key for key in actor.possessions if key!=effect.target_id])
        identity=(row.identity.encounter_id,row.identity.boundary,row.identity.source_action_id,
                  row.identity.channel,row.identity.slot)
        release_position=CartesianPosition(*effect.release_position)
        landing_position=CartesianPosition(*effect.landing_position)
        flight=ProjectileFlight(effect.source_action_id,effect.release_time,effect.impact_time,
            release_position,landing_position,effect.velocity_m_s,
            effect.landing_elevation_m,identity)
        state=ProjectileBoundaryState(effect.source_action_id,candidate.boundary,
            release_position,'in_flight',effect.impact_time,identity)
        plan.attr('targets',obj.spatial_state,'position',release_position,chain=True)
        plan.attr('targets',obj,'_projectile_flight',flight)
        plan.append('targets',obj,'_atomic_projectile_history',state)
    initial={aid:_resolve_metadata(encounter,data) for aid,data in changes['action_metadata'].items()}
    endpoint_new={aid for fence in candidate.start_fences if fence.phase=='after_settlement' for aid in fence.registered_action_ids}
    endpoint_started={aid for fence in candidate.start_fences if fence.phase=='after_settlement' for aid in fence.started_action_ids}
    endpoint_choices={cid for fence in candidate.start_fences if fence.phase=='after_settlement' for cid in fence.published_choices}
    registrations=dict(book._registered)
    for intent in queues.event_registrations:
        action=events[intent.action.key]
        if id(action)!=intent.action.identity:raise PublicationRejected('Action publication identity mismatch')
        record=book._choices[intent.choice_id]
        packet=next(p for p in record.prepared if p.action_id==action.id)
        if id(packet)!=intent.accepted_packet.identity:raise PublicationRejected('accepted packet identity mismatch')
        registrations[action.id]=(intent.choice_id,packet,declaration(action,_initialization=initial[action.id]))
    early_events={aid:action for aid,action in events.items() if aid not in endpoint_new}
    early_registered={aid:row for aid,row in registrations.items() if aid not in endpoint_new}
    plan.contents('registrations',world.event_history,early_events)
    plan.contents('registrations',book._registered,early_registered)
    if endpoint_new:
        plan.contents('endpoint_starts',world.event_history,events,chain=True)
        plan.contents('endpoint_starts',book._registered,registrations,chain=True)
    for aid,data in initial.items():
        for key,value in data.items():
            late=aid in endpoint_new or (aid in endpoint_started and key in ('_activity_started','start_position','threat_at_schedule'))
            plan.attr('endpoint_starts' if late else 'registrations',events[aid],key,value)
    target_anchors={}
    from encounter_inspection import prepare_record, fingerprint
    for key,target in supported.boundary.targets.items():
        obj=objects[key]
        if obj.current.hit_points!=target.projected_hp:plan.attr('targets',obj.current,'hit_points',target.projected_hp)
        record=TargetIntervalRecord(encounter.id,candidate.boundary,target)
        storage=plan.append('targets',obj,'_atomic_target_history',record)
        target_anchors[key]=(id(obj),id(obj.current),id(obj.spatial_state),id(storage),id(record),fingerprint(record))
        practice=target.practice_state
        if practice is not None:
            plan.contents('practice',obj.current.skills.skills,practice.ordinary_levels)
            plan.contents('practice',obj.current.skills.weapon_skills,practice.weapon_levels)
            plan.contents('practice',obj.skill_experience,practice.skill_experience)
            plan.contents('practice',obj._skill_practice_baselines,practice.baselines)
            history=list(obj.skill_use_history)
            for transition in practice.transitions:
                uses=tuple(x for x in practice.exercises if x.skill_name==transition.skill_name)
                history.append(BatchSkillUse(key,transition.skill_name,sum(x.experience for x in uses),
                    transition.level_before,transition.level_after,transition.time,uses))
            plan.contents('practice',obj.skill_use_history,history)
    for key,state in supported.objective.subjects.items():
        subject=objects[key]
        ledger=subject._composition_reality if type(subject) is StatisticalGroup else subject.personal_history.reality
        if type(ledger) is not RealityLedger or id(ledger)!=state.ledger_identity:raise PublicationRejected('objective ledger identity mismatch')
        records=dict(ledger._records);new=[f for f in state.facts.values() if not f.established]
        revision=ledger._revision+(1 if new else 0)
        for fact in new:
            if fact.key in records:raise PublicationRejected('objective fact unexpectedly established')
            records[fact.key]=CommittedFact(fact.key,_materialize(fact.value),fact.origins[0],revision)
        if new:
            plan.contents('reality',ledger._records,records);plan.attr('reality',ledger,'_revision',revision)
        use={row.key:row for row in supported.objective_use if row.subject_id==key}
        provenance=list(ledger.__dict__.get('_atomic_provenance',[]))
        for fact in state.facts.values():
            consumers=use[fact.key].consumed_by if fact.key in use else ()
            if consumers:provenance.append(ObjectiveCommitProvenance(encounter.id,candidate.boundary,fact.key,
                records[fact.key].revision,fact.origins,fact.requesting_action_ids,consumers))
        if provenance!=ledger.__dict__.get('_atomic_provenance',[]):
            if '_atomic_provenance' not in ledger.__dict__:plan.attr('reality',ledger,'_atomic_provenance',provenance)
            else:plan.contents('reality',ledger._atomic_provenance,provenance)
        if state.counts is not None:
            if subject._counts is None:plan.attr('reality',subject,'_counts',dict(state.counts))
            elif dict(subject._counts)!=dict(state.counts):raise PublicationRejected('established group cache disagrees')
    handles=_recipient_handles(encounter,candidate)
    for identity,projection in supported.recipients.items():
        handle=handles[identity]
        if type(projection) is BeliefProjection:
            plan.contents('observers',handle._evidence,_preserve_known(handle._evidence,projection.evidence))
            plan.contents('observers',handle._interpretations,_preserve_known(handle._interpretations,projection.interpretations))
            plan.contents('observers',handle._current_reassessments,_preserve_known(handle._current_reassessments,projection.current_readings))
            plan.contents('observers',handle._belief_history,_append_projection(handle._belief_history,projection.belief_history))
            # Auxiliary arrays remain native and unchanged by acquisition.
        elif type(projection) is AccountsProjection:plan.contents('observers',handle,_append_projection(handle,projection.accounts))
        elif type(projection) is LocationEvidenceProjection:
            from location_observation import LocationEvidenceLedger
            if (type(handle) is not LocationEvidenceLedger
                    or handle.observer_id != projection.observer_id
                    or identity.role != 'observer_location_evidence'):
                raise UnsupportedEvaluation('location recipient identity/owner mismatch')
            plan.contents('observers',handle._observations,
                          _preserve_known(handle._observations,projection.observations))
        elif type(projection) is ObjectEvidenceProjection:
            from object_observation import ObjectObservationLedger
            if (type(handle) is not ObjectObservationLedger
                    or handle.observer_id != projection.observer_id
                    or identity.role != 'observer_object_evidence'):
                raise UnsupportedEvaluation('Object evidence recipient identity/owner mismatch')
            plan.contents('observers',handle._observations,
                          _preserve_known(handle._observations,projection.observations))
        else:raise UnsupportedEvaluation('unsupported authoritative recipient publication')
    for key,target in supported.boundary.targets.items():
        if target.category!='being':continue
        if key in encounter.awareness:plan.contents('observers',encounter.awareness[key],target.aware_of)

    new_awareness={key:set(target.aware_of) for key,target in supported.boundary.targets.items()
        if target.category=='being' and key not in encounter.awareness}
    for key,value in new_awareness.items():
        data=encounter.awareness
        plan._add('observers',('attribute',id(data),key),_AttributeWrite(data,key,value,False,None,tuple(data)))
    for aid,proposal in supported.boundary.actions.items():
        action=events[aid]
        plan.attr('lifecycle',action,'resolution',proposal)
        plan.attr('lifecycle',action,'_atomic_effect_ids',tuple(row.identity for row in supported.effects.values() if row.identity.source_action_id==aid))
        plan.attr('lifecycle',action,'_atomic_lifecycle',supported.lifecycle[aid])
        if snapshot.actions[aid].lifecycle=='cancelled':plan.attr('lifecycle',action,'_atomic_acknowledged_boundary',candidate.boundary)
    plan.contents('lifecycle',encounter.pending_action_list,tuple(aid for aid in queues.pending if aid not in endpoint_new))
    if endpoint_new:plan.contents('endpoint_starts',encounter.pending_action_list,queues.pending,chain=True)
    plan.contents('lifecycle',encounter.finished_action_list,queues.finished)
    plan.contents('lifecycle',encounter.cancelled_action_list,queues.cancelled)
    interim_states={aid:('registered' if aid in endpoint_started else state) for aid,state in queues.action_states.items() if aid not in endpoint_new}
    final_choices={cid:(record if record.view.state==queues.choice_states[cid] else
        replace(record,view=replace(record.view,state=queues.choice_states[cid]))) for cid,record in book._choices.items()}
    interim_choices={cid:(record if cid in endpoint_choices else final_choices[cid]) for cid,record in book._choices.items()}
    plan.contents('lifecycle',book._states,interim_states)
    plan.contents('lifecycle',book._choices,interim_choices)
    if endpoint_started or endpoint_new:
        plan.contents('endpoint_starts',book._states,queues.action_states,chain=True)
        plan.contents('endpoint_starts',book._choices,final_choices,chain=True)
    plan.attr('lifecycle',book,'_reservations',queues.reservations)
    plan.attr('lifecycle',world,'_schedule_revision',queues.schedule_revision-len(endpoint_choices))
    if endpoint_choices:plan.attr('endpoint_starts',world,'_schedule_revision',queues.schedule_revision,chain=True)
    plan.attr('frames_clock',encounter,'last_fatigue_frame',_frame(snapshot))
    plan.contents('frames_clock',encounter.fatigue_frame_history,
        encounter.fatigue_frame_history+[_materialize(changes['fatigue_history'][-1])])
    for name,value in changes['clock'].items():
        plan.attr('frames_clock',encounter,{'coordinator_time':'_coordinator_time','interval_start':'_interval_start'}.get(name,name),value)
    if plan.adult_realization is not None:
        operation,group,being,member,slot=plan.adult_realization
        registry_after=dict(objects);registry_after[operation.member_id]=being
        plan.contents('adult_registry',objects,registry_after)
        if slot not in group._members:
            members_after=dict(group._members);members_after[slot]=member
            plan.contents('adult_group_member',group._members,members_after)
        realized_after=dict(group._realized_beings);realized_after[operation.member_id]=being
        plan.contents('adult_group_realized',group._realized_beings,realized_after)
        motion_after=set(group._motion_attached_native_ids);motion_after.add(operation.member_id)
        plan.contents('adult_group_motion',group._motion_attached_native_ids,motion_after)
        participants_after=list(encounter.being_list);participants_after.append(operation.member_id)
        plan.contents('adult_encounter_participant',encounter.being_list,participants_after)
    if plan.adult_reproduction_binding is not None:
        reproduction,binding_record=plan.adult_reproduction_binding
        bindings_after=dict(reproduction._native_beings_by_person_id)
        bindings_after[binding_record.person_id]=binding_record.being
        plan.contents('adult_reproduction_binding',
                      reproduction._native_beings_by_person_id,bindings_after)
        requests_after=dict(reproduction._native_being_requests)
        requests_after[binding_record.request_key]=binding_record
        plan.contents('adult_reproduction_request',
                      reproduction._native_being_requests,requests_after)
    receipt=PublishedInterval(encounter.id,candidate.boundary,tuple(supported.boundary.actions),tuple(supported.effects),
        candidate.provisional_rng.after,supported.notification_intents,inspection=prepare_record(encounter,candidate,target_anchors,events))
    plan.append('mark_committed',encounter,'_atomic_interval_history',receipt)
    role=candidate.provisional_rng.role
    if role=='caller_state':raise UnsupportedEvaluation('immutable caller RNG state has no owned write location; restage with RNGCursor')
    if random.getstate is not _MODULE_GETSTATE or random.setstate is not _MODULE_SETSTATE:
        raise UnsupportedEvaluation('unreviewed module RNG override')
    plan.phases['rng'].append(_RNGWrite(role,rng_owner,candidate.provisional_rng.before,candidate.provisional_rng.after))
    plan.validate_aliases()
    return plan,receipt


def _committed_consistency(encounter,candidate,plan):
    _validate_closure(candidate)
    if candidate.integrity_token!=_digest(_semantic(candidate)):
        raise EvaluationIntegrityError('candidate seal changed during publication')
    plan.verify(skip_phase='mark_committed')
    encounter._pending_schedule()
    from frozen_practice import capture_practice_inputs
    from objective_reality import _frozen_group
    from observer_proposals import _capture_belief
    objects=encounter.universe.object_registry.object_instances
    views={}
    for key,view in candidate.pre_action_snapshot.entities.items():
        if view.category=='being':
            skills=objects[key].current.skills
            view=replace(view,data=MappingProxyType(dict(view.data,skills=freeze(skills.skills),weapon_skills=freeze(skills.weapon_skills))))
        views[key]=view
    capture_practice_inputs(encounter.universe,objects,views)
    for key in candidate.supported_candidate.objective.subjects:
        if type(objects[key]) is StatisticalGroup:_frozen_group(objects[key])
    for identity,handle in _recipient_handles(encounter,candidate).items():
        if identity.role=='in_world_belief_ledger':_capture_belief(handle,handle.observer_id)
        elif identity.role=='observer_location_evidence':
            from observer_proposals import _capture_location_evidence
            _capture_location_evidence(handle,handle.observer_id)
        elif identity.role=='observer_object_evidence':
            _capture_object_evidence(handle,handle.observer_id)
    for update in candidate.projectile_updates:
        obj=objects[update.object_id]
        if (obj.spatial_state.position!=update.state.position
                or obj.__dict__.get('_projectile_flight') is not update.next_flight
                or obj.__dict__.get('_atomic_projectile_history',())[-1] is not update.state):
            raise PublicationRejected('projectile boundary post-write consistency failed')
    for row in candidate.supported_candidate.boundary.effects.values():
        effect=row.effect
        if type(effect) is ProjectileReleaseEffect:
            obj=objects[effect.target_id]
            actor=objects[candidate.supported_candidate.boundary.actions[effect.source_action_id].actor_id]
            if (obj.spatial_state.position!=CartesianPosition(*effect.release_position)
                    or obj.__dict__.get('_projectile_flight') is None
                    or obj.__dict__.get('_projectile_flight').source_action_id!=effect.source_action_id
                    or effect.target_id in actor.possessions):
                raise PublicationRejected('projectile release post-write consistency failed: '
                    f'position={obj.spatial_state.position!r}, flight={obj.__dict__.get("_projectile_flight")!r}, '
                    f'possessed={effect.target_id in actor.possessions}')
    if candidate.adult_member_candidate is not None:
        operation,group,being,member,slot=plan.adult_realization
        objects=encounter.universe.object_registry.object_instances
        if (objects.get(operation.member_id) is not being
                or group._realized_beings.get(operation.member_id) is not being
                or group._members.get(slot)!=member
                or operation.member_id not in group._motion_attached_native_ids
                or encounter.being_list.count(operation.member_id)!=1
                or operation.member_id in encounter.non_being_object_list
                or operation.member_id in encounter.awareness
                or group.__dict__.get('_counts')!=dict(operation.formation_counts)
                or operation.member_id in candidate.pre_action_snapshot.entities
                or operation.first_eligible_boundary!=candidate.boundary+1):
            raise PublicationRejected('adult-member realization post-write consistency failed')
        if operation.request.reproductive_person_id is not None:
            reproduction=encounter.universe._reproduction_group_registry
            from reproduction_being_bridge import _definition_signature
            request_key=operation.request.reproduction_request_key
            record=reproduction._native_being_requests.get(request_key)
            if (reproduction._native_beings_by_person_id.get(operation.member_id) is not being
                    or record is None or record.being is not being
                    or record.person_id!=operation.member_id
                    or record.request_key!=request_key
                    or record.normalized_request!=(being.id,being.name,
                                                   _definition_signature(being.original))):
                raise PublicationRejected('native reproductive identity post-write consistency failed')
            reproduction._assert_consistent()


def _without_fault(read_set):
    return tuple((name,tuple((key,None if key=='boundary_fault' else value) for key,value in token)
        if name=='encounter' else token) for name,token in read_set)


def publish_interval_candidate(encounter,candidate,*,ownership=None,rng_state=None,rng_owner=None,
                               _fail_after=None,_rollback_fail_at=None):
    """Explicit opt-in, issued-candidate-only, one-interval publication.

    Private fault controls are data-only test points, never callbacks. All
    validation/plan errors before the first application leave no fault latch.
    """
    _owned(encounter,ownership)
    from transactional_progression import validate_publication_entry
    validate_publication_entry(encounter,ownership)
    if _fail_after is not None and (type(_fail_after) is not str or _fail_after not in PHASES):raise PublicationRejected('unknown fault-injection phase')
    if _rollback_fail_at is not None and (type(_rollback_fail_at) is not int or _rollback_fail_at<0):raise PublicationRejected('invalid inverse fault point')
    issued=_ISSUED_CANDIDATES.get(id(candidate))
    if type(candidate) is not IntervalCandidate or issued is None or issued() is not candidate:
        raise PublicationRejected('foreign, consumed or non-issued interval candidate')
    validate_interval_candidate(encounter,candidate,rng_state=rng_state,rng_owner=rng_owner)
    plan,receipt=_make_plan(encounter,candidate,rng_owner)
    from encounter_inspection import fingerprint
    receipt_fingerprint=fingerprint(receipt)
    # Build the complete inverse plan before mutation, then repeat dependencies
    # under the same ownership. No check-then-write window for coordinated users.
    validate_interval_candidate(encounter,candidate,rng_state=rng_state,rng_owner=rng_owner)
    global _PUBLISHING
    _PUBLISHING=True;phase='movement'
    try:
        for phase in PHASES:
            plan.apply_phase(phase)
            if phase=='consistency':
                _committed_consistency(encounter,candidate,plan)
            if phase=='mark_committed':plan.verify()
            if phase==_fail_after:raise RuntimeError('injected publication failure after '+phase)
        _COMMITTED_RECEIPTS[id(receipt)]=(weakref.ref(receipt,lambda ref,key=id(receipt):_COMMITTED_RECEIPTS.pop(key,None)),
            weakref.ref(encounter),receipt_fingerprint)
        _ISSUED_CANDIDATES.pop(id(candidate),None)
        return receipt
    except BaseException as original:
        try:errors=plan.rollback(_rollback_fail_at)
        except BaseException as rollback_failure:errors=[f'inverse journal runner failed: {type(rollback_failure).__name__}: {rollback_failure}']
        try:
            if _read_set(encounter)!=candidate.start_checkpoint.read_set:errors.append('restored authority differs from starting checkpoint')
            if _rng_input(encounter,rng_state,rng_owner)!=(candidate.provisional_rng.role,candidate.provisional_rng.owner_identity,candidate.provisional_rng.before):errors.append('RNG restoration mismatch')
        except BaseException as verification:errors.append(f'rollback verification failed: {verification}')
        token=f'{encounter.id}/publication-fault/{next(_COUNTER)}'
        diagnostic={'kind':'atomic_publication','boundary':candidate.boundary,'last_processed':candidate.start_checkpoint.last_processed_boundary,
            'phase':phase,'error':type(original).__name__,'message':str(original),'rollback':'failed' if errors else 'restored','recovery_token':token}
        encounter.__dict__['boundary_fault']=diagnostic
        _FAULTS[id(encounter)]=_FailureState(weakref.ref(encounter),candidate,dict(diagnostic),token,not errors)
        _ISSUED_CANDIDATES.pop(id(candidate),None)
        if errors:_EMERGENCIES[id(encounter.universe)]=(weakref.ref(encounter.universe),token)
        cls=RollbackIntegrityFailure if errors else PublicationFailure
        raise cls(original,phase,token,errors) from original
    finally:_PUBLISHING=False


def recover_interval_publication(encounter,recovery_token,*,ownership=None,rng_state=None,rng_owner=None):
    """Acknowledge a restored fault only; never replay or repair a broken graph.

    Correct the code/injection cause first. Recovery checks the exact restored
    checkpoint. Apply any desired input correction AFTER this acknowledgement,
    then stage a fresh candidate explicitly. No automatic retry is performed.
    """
    _owned(encounter,ownership)
    if type(recovery_token) is not str:raise PublicationRejected('native recovery token required')
    fault=_FAULTS.get(id(encounter))
    if fault is None or fault.encounter() is not encounter or recovery_token!=fault.token:
        raise PublicationRejected('unknown or foreign controlled-recovery token')
    if not fault.restored or _emergency(encounter.universe):
        raise PublicationOwnershipError('rollback integrity emergency requires external repair; no automatic recovery')
    if encounter.boundary_fault!=fault.diagnostic:raise PublicationRejected('fault diagnostic was altered')
    candidate=fault.candidate
    if (_without_fault(_read_set(encounter))!=candidate.start_checkpoint.read_set
        or _rng_input(encounter,rng_state,rng_owner)!=(candidate.provisional_rng.role,candidate.provisional_rng.owner_identity,candidate.provisional_rng.before)):
        raise PublicationRejected('restored checkpoint changed; recovery refused')
    _guard_methods()
    encounter.__dict__['boundary_fault']=None
    del _FAULTS[id(encounter)]
    return candidate.start_checkpoint
