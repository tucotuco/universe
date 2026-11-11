"""Inactive native whole-interval staging (5C1), with no publication API.

The private read fence overlays reviewed data during existing snapshot capture;
no cloned Encounter, live walker, resolver, callback, or temporary write executes.
Process-local identity/read tokens are dependencies, not a save/replay format.
"""
from dataclasses import dataclass, fields, is_dataclass, replace
import hashlib
import inspect
import math
import random
import weakref
from types import MappingProxyType, MethodType, FunctionType
from _thread import RLock

from action_evaluation import (EvaluationIntegrityError, UnsupportedEvaluation,
    capture_snapshot, freeze, native_data, position)
from observer_proposals import capture_observer_context, build_supported_candidate
from spatial.state import CartesianPosition, SpatialState, integrate_position
from spatial.frame import LocalFrame
from encounter import Encounter
from universe import Universe
from action_choice import ChoiceBook, ChoiceView, ChoiceMember, Reservation, _Accepted, declaration
from scheduling import PreparedSchedule
from action import Action
from activities import RunAction, SpotAction, ThrowAction, PickUpAction, ReadyWeaponAction
from melee_combat import MeleeStrike
from melee_defense import MeleeDefense
from group_observation import ObserveGroupAction, SampledGroupObservation
from history_conversation import AskAboutPastAction
from being import BeingInstance, BeingDefinition
from object import ObjectInstance, ObjectRegistry, ObjectDefinition
from weapon import WeaponInstance, WeaponDefinition
from armor import ArmorInstance, ArmorDefinition
from statistical_group import StatisticalGroup
from physiology_registry import PhysiologyRegistry
from field_interpretation import FieldInterpreter
from field_observation import BeliefLedger
from location_observation import LocationEvidenceLedger
from encounter_fatigue_bridge import FrozenFatigueFrame
from library import Library
from skill import Skills, SkillDictionary
from abilities import Abilities
from states import States
from exertion import Exertion
from throwing import ProjectileFlight, ProjectileBoundaryState


_ISSUED_CANDIDATES = {}  # Process-local native issuance, never serialized.


class IntervalIntegrityError(EvaluationIntegrityError):
    """Invalid committed checkpoint or incomplete interval candidate."""


class StaleInterval(IntervalIntegrityError):
    """The captured authority/dependency identity or content has changed."""


def _require(test, reason):
    if not test:
        raise IntervalIntegrityError(reason)


_ACTIONS = (Action, RunAction, SpotAction, ThrowAction, PickUpAction, ReadyWeaponAction, MeleeStrike, MeleeDefense,
            ObserveGroupAction, AskAboutPastAction)
_OBJECTS = (BeingInstance, ObjectInstance, WeaponInstance, ArmorInstance, StatisticalGroup)
# Pin methods at import, before any user-provided extension is inspected. This
# includes inherited read methods invoked by older native capture adapters.
_CLASSES = (Encounter, Universe, ChoiceBook, ObjectRegistry, *_ACTIONS, *_OBJECTS,
            SpatialState, CartesianPosition, LocalFrame, PhysiologyRegistry,
            FrozenFatigueFrame, SampledGroupObservation, FieldInterpreter, BeliefLedger,
            LocationEvidenceLedger,
            BeingDefinition, ObjectDefinition, WeaponDefinition, ArmorDefinition, Library,
            Skills, SkillDictionary, Abilities, States, Exertion,
            ProjectileFlight, ProjectileBoundaryState, random.Random)
_METHODS = {(cls, name): inspect.getattr_static(cls, name)
            for cls in _CLASSES for name in dir(cls)
            if callable(inspect.getattr_static(cls, name))}
_METHODS.update({(cls,name):inspect.getattr_static(cls,name,None) for cls in _CLASSES
    for name in ('__getattr__','on_schedule','on_completed')})


def _guard_methods():
    for (cls, name), expected in _METHODS.items():
        if inspect.getattr_static(cls, name, None) is not expected:
            raise UnsupportedEvaluation(f'unreviewed {cls.__name__}.{name} interval hook')


@dataclass(frozen=True)
class AuthorityReference:
    role: str
    key: str
    identity: int


@dataclass(frozen=True)
class IntervalCheckpoint:
    encounter: AuthorityReference
    universe: AuthorityReference
    start: float
    last_processed_boundary: int
    schedule_revision: int
    read_set: tuple
    dependency_token: str
    schema: str = 'native-interval-checkpoint-v1-process-local-inactive'


@dataclass(frozen=True)
class MovementSegment:
    start: float
    end: float
    velocities: object
    before: object
    after: object


@dataclass(frozen=True)
class ProjectileMotionUpdate:
    object_id: str
    prior_flight: ProjectileFlight
    next_flight: ProjectileFlight
    state: ProjectileBoundaryState


@dataclass(frozen=True)
class StartFence:
    time: float
    phase: str
    published_choices: tuple
    registered_action_ids: tuple
    started_action_ids: tuple
    metadata: object


@dataclass(frozen=True)
class RegistrationIntent:
    action: AuthorityReference
    choice_id: str
    accepted_packet: AuthorityReference
    metadata: object
    signature_from_final_native_declaration: bool = True


@dataclass(frozen=True)
class QueueProjection:
    pending: tuple
    finished: tuple
    cancelled: tuple
    event_registrations: tuple
    action_states: object
    choice_states: object
    reservations: tuple
    schedule_revision: int


@dataclass(frozen=True)
class ProvisionalRNG:
    role: str
    owner_identity: int | None
    before: tuple
    after: tuple
    core_trace: tuple
    observer_trace: tuple
    objective_trace: tuple
    apply_only_with_interval_commit: bool = True


@dataclass(frozen=True)
class IntervalCandidate:
    encounter_id: str
    boundary: int
    start_checkpoint: IntervalCheckpoint
    movement: tuple
    start_fences: tuple
    pre_action_snapshot: object
    supported_candidate: object
    provisional_rng: ProvisionalRNG
    proposed_authoritative_changes: object
    coverage: str = 'complete_supported_interval'
    ready_for_publication: bool = False
    remaining_dependencies: tuple = ('5C2_identity_preserving_atomic_publication_and_recovery',
        '5C3_activation_consumers_checkpoint_replay_compatibility')
    integrity_token: str = ''
    # A typed non-Action world-state operation; never part of Action coverage.
    adult_member_candidate: object = None
    projectile_updates: tuple = ()


@dataclass(frozen=True)
class _StagedReadFence:
    """Transient capture input. Live references never survive into the candidate."""
    encounter_identity: int
    boundary: int
    pending_ids: tuple
    events: object
    initialization: object
    registered: object
    states: object
    positions: object
    facings: object


def _digest(value):
    return hashlib.sha256(repr(value).encode()).hexdigest()


def _semantic(value):
    """Check/digest detached native proposal data, including hidden source views."""
    if value is None or type(value) in (str, int, float, bool):
        return value
    if type(value) is tuple:
        return tuple(_semantic(v) for v in value)
    if type(value) is MappingProxyType:
        return tuple((_semantic(k), _semantic(v)) for k, v in value.items())
    if type(value) in (set, frozenset):
        return tuple(sorted((_semantic(v) for v in value), key=repr))
    if is_dataclass(value) and type(value).__dataclass_params__.frozen:
        return (type(value).__module__, type(value).__name__, tuple((f.name, _semantic(getattr(value, f.name)))
            for f in fields(value) if not (type(value) is IntervalCandidate and f.name == 'integrity_token')))
    raise UnsupportedEvaluation('opaque or mutable value escaped interval staging')


def _read_set(encounter):
    """Bounded native graph read token: identities, aliasing, values, revisions.

    Encounter/Universe backreferences are terminal; the selected authoritative
    roots below, not arbitrary unrelated Universe state, define the read set.
    Native opaque leaves (locks/functions) are tracked by identity, never called.
    """
    ed = object.__getattribute__(encounter, '__dict__'); world = ed['universe']
    wd = object.__getattribute__(world, '__dict__'); book = ed['_choice_book']
    objects = object.__getattribute__(wd['object_registry'], '__dict__')['object_instances']
    # All registered Object identities protect registry alias/rebinding, while
    # content traversal covers only participants, holdings and Action references.
    keys = set(ed['being_list'] + ed['non_being_object_list'])
    events = {}
    for aid in ed['pending_action_list'] + ed['cancelled_action_list'] + ed['finished_action_list']:
        if aid in wd['event_history']:
            events[aid] = wd['event_history'][aid]
    for record in book._choices.values():
        for member in record.members:
            events[member.action.id] = member.action
    for action in events.values():
        data = object.__getattribute__(action, '__dict__')
        keys.update(v for k in ('actor_id', 'target_id', 'instrument_id') if (v := data.get(k)) is not None)
    for key in tuple(keys):
        if key not in objects:
            continue
        data = object.__getattribute__(objects[key], '__dict__')
        if type(objects[key]) is BeingInstance:
            current = object.__getattribute__(data['current'], '__dict__')
            keys.update(x for x in current['body_parts'].values() if x is not None)
            if current['armor_id'] is not None: keys.add(current['armor_id'])
    roots = (
        ('encounter', {k:v for k,v in ed.items() if k not in ('universe','_choice_book')}),
        ('choice_book', {k:v for k,v in book.__dict__.items() if k not in ('encounter','lock')}),
        ('world_identity', id(world)), ('world_registry', id(wd['object_registry'])),
        ('object_registry', (id(objects),tuple((k,id(v)) for k,v in objects.items()))),
        ('event_registry', (id(wd['event_history']), tuple((k,id(v)) for k,v in wd['event_history'].items()))),
        ('objects', {key:objects[key] for key in sorted(keys) if key in objects}),
        ('events', events), ('library', wd['library']),
        ('schedule', (wd['_schedule_revision'],id(wd['_schedule_lock']),id(wd['_choice_books']),
            tuple((id(b),id(b.encounter),b.encounter.time,b.encounter.last_processed_boundary,
                   b._reservations,tuple(b._states.items()),tuple((cid,r.view) for cid,r in b._choices.items()))
                  for b in wd['_choice_books']))))
    seen = set()
    terminals = {id(encounter), id(world), id(book)}
    def walk(value):
        if value is None or type(value) in (str, int, float, bool):return value
        identity = id(value)
        if identity in terminals:return ('authority_ref', type(value).__name__, identity)
        if type(value) in (FunctionType, MethodType):
            return ('callable', id(value.__func__),id(value.__self__)) if type(value) is MethodType else ('callable',identity)
        if identity in seen:return ('alias', identity)
        seen.add(identity)
        if type(value) in (dict, MappingProxyType):return ('mapping',identity,tuple((walk(k),walk(v)) for k,v in value.items()))
        if type(value) in (list, tuple):return (type(value).__name__,identity,tuple(walk(v) for v in value))
        if type(value) in (set, frozenset):return (type(value).__name__,identity,tuple(sorted((walk(v) for v in value),key=repr)))
        # Native data graph, never an arbitrary property/serializer/deepcopy.
        cls = type(value)
        if cls.__module__ in _DATA_MODULES:
            try: data = object.__getattribute__(value, '__dict__')
            except AttributeError: return ('native_leaf', cls.__name__, identity)
            return ('native',cls.__module__,cls.__name__,identity,walk(data))
        return ('opaque_identity',cls.__module__,cls.__name__,identity)
    # The synthetic root maps have fresh identities on each capture; discard
    # their container identities while retaining actual authority descendants.
    result = []
    for name, value in roots:
        if name in ('encounter','choice_book','objects','events'):
            token = tuple((key,walk(item)) for key,item in value.items())
        elif name == 'library':
            token = walk(value)
        elif name == 'schedule':
            token = _semantic(value)
        else:
            token = value
        result.append((name,token))
    result.append(('native_class_constants',tuple((cls.__module__,cls.__name__,key,walk(value))
        for cls in _CLASSES for key,value in vars(cls).items() if not key.startswith('__')
        and type(value) in (str,int,float,bool,tuple,list,dict,set,frozenset))))
    return tuple(result)


# Modules containing the reviewed data-only graph (not a callback allowlist).
_DATA_MODULES = frozenset(('being','object','weapon','armor','action','activities','melee_combat',
    'melee_defense','group_observation','history_conversation','personal_history','realization',
    'statistical_group','field_observation','field_interpretation','objective_reality','action_choice',
    'transactional_progression','encounter_inspection','atomic_publication','action_evaluation','action_settlement','frozen_practice','scheduling','spatial.state','spatial.geometry','spatial.occlusion','spatial.frame','strategy',
    'location_observation','arena_perception',
    'skill','states','abilities','exertion','physical_fatigue','physiology_registry','library',
    'ability','experience','condition','encounter','standard_fatigue_check','encounter_fatigue_bridge'))


def _rng_input(encounter, rng_state, rng_owner):
    if rng_owner is None:
        role, identity = ('module', id(random)) if rng_state is None else ('caller_state', None)
        state = random.getstate() if rng_state is None else freeze(rng_state)
    elif type(rng_owner) is random.Random:
        if set(vars(rng_owner)) - {'gauss_next'}:
            raise UnsupportedEvaluation('custom RNG instance attributes require a reviewed owner')
        role, identity, state = 'native_random', id(rng_owner), rng_owner.getstate()
    else:
        from atomic_publication import RNGCursor
        if type(rng_owner) is RNGCursor:
            state = freeze(native_data(rng_owner,(RNGCursor,))['state'])
            if rng_state is not None:_require(state==freeze(rng_state), 'explicit RNG state disagrees with caller cursor')
            try:random.Random(0).setstate(state)
            except (TypeError,ValueError) as exc:raise IntervalIntegrityError('invalid caller RNG cursor') from exc
            return 'caller_cursor',id(rng_owner),state
        from tactical_duel import TacticalDuel
        from ai_duel import AgentDuel
        if type(rng_owner) not in (TacticalDuel, AgentDuel):
            raise UnsupportedEvaluation('unsupported provisional RNG owner')
        data = object.__getattribute__(rng_owner, '__dict__')
        _require(data.get('encounter') is encounter, 'facade RNG belongs to another Encounter')
        role, identity, state = 'native_facade', id(rng_owner), freeze(data['_rng_state'])
    if rng_owner is not None and rng_state is not None:
        _require(state == freeze(rng_state), 'explicit RNG state disagrees with owner')
    try: random.Random(0).setstate(state)
    except (TypeError,ValueError) as exc: raise IntervalIntegrityError('invalid provisional RNG state') from exc
    return role, identity, freeze(state)


def _preflight(encounter, boundary):
    _guard_methods()
    ed = native_data(encounter, (Encounter,)); wd = native_data(ed['universe'], (Universe,))
    _require(ed['initiated'], 'interval requires an initiated Encounter')
    _require(not any(ed[k] for k in ('_advancing','_dispatching','_running')) and ed['active_boundary'] is None
        and ed['boundary_fault'] is None and ed['_boundary_context'] is None
        and ed['_active_fatigue_frame'] is None, 'active, faulted or reentrant interval checkpoint')
    _require(type(boundary) is int and boundary > 0 and boundary == ed['last_processed_boundary']+1,
        'interval must end at exactly the next positive integer boundary')
    now = ed['time']
    _require(type(now) in (int,float) and math.isfinite(now) and now >= 0
        and ed['_coordinator_time'] == now and ed['_interval_start'] == now
        and ed['last_processed_boundary'] == math.floor(now)
        and (now == ed['start_time'] or now == ed['last_processed_boundary']) and now < boundary,
        'fractional tail or inconsistent committed checkpoint')
    _require(ed['end_time'] is None or boundary <= ed['end_time'], 'interval exceeds Encounter end')
    _require(type(wd['event_history']) is dict and wd['event_history'].get(ed['id']) in (None,encounter),
        'Encounter registry identity mismatch')
    if ed['map'] is not None and type(ed['map']) is not dict:
        raise UnsupportedEvaluation('unreviewed environment/map contract')
    if ed['map'] is not None:freeze(ed['map'])
    registry = native_data(wd['object_registry'], (ObjectRegistry,))['object_instances']
    _require(type(registry) is dict, 'unsupported Object registry')
    for key in ('being_list','non_being_object_list','pending_action_list','finished_action_list','cancelled_action_list'):
        _require(type(ed[key]) is list and all(type(x) is str for x in ed[key]) and len(ed[key]) == len(set(ed[key])), 'duplicate/opaque checkpoint membership')
    participants = ed['being_list']+ed['non_being_object_list']
    _require(len(participants)==len(set(participants)), 'aliased participant roles')
    for key in participants:
        obj = registry.get(key)
        data = native_data(obj, _OBJECTS)
        _require(data['id'] == key and sum(v is obj for v in registry.values()) == 1, 'aliased Object registry identity')
        _require((type(obj) is BeingInstance) == (key in ed['being_list']), 'invalid participant role')
    book = ed['_choice_book']; native_data(book,(ChoiceBook,))
    _require(book.encounter is encounter and book.lock is wd['_schedule_lock']
        and type(wd['_choice_books']) is list and wd['_choice_books'].count(book)==1, 'choice ownership/index mismatch')
    for other in wd['_choice_books']:
        native_data(other,(ChoiceBook,)); native_data(other.encounter,(Encounter,))
        _require(type(other._choices) is dict and type(other._registered) is dict and type(other._states) is dict
            and type(other._reservations) is tuple and all(type(r) is Reservation for r in other._reservations), 'opaque choice/reservation stores')
        _require(all(type(r) is _Accepted and type(r.view) is ChoiceView and type(r.members) is tuple
            and all(type(m) is ChoiceMember and type(m.key) is str for m in r.members) for r in other._choices.values()), 'unreviewed choice records')
        _require(other.encounter.universe is ed['universe'] and other.lock is wd['_schedule_lock'], 'foreign choice-book owner')
        if other is not book and set(participants).intersection(other.encounter.being_list+other.encounter.non_being_object_list):
            raise UnsupportedEvaluation('shared cross-Encounter physical/recipient ownership requires a world coordinator')
    _require(set(book._states)==set(book._registered), 'choice state/registration index mismatch')
    for queue,state in (('pending_action_list',('registered','executing')),('finished_action_list',('finished',)),
                        ('cancelled_action_list',('cancelled',))):
        _require(set(ed[queue])=={aid for aid,value in book._states.items() if value in state},
            'Action queue/choice lifecycle mismatch')
        for aid in ed[queue]:
            action=wd['event_history'].get(aid)
            if type(action) not in _ACTIONS:raise UnsupportedEvaluation('missing or unsupported lifecycle Action reference')
            data=object.__getattribute__(action,'__dict__')
            _require(data['id']==aid and data['parent_event_id']==ed['id'], 'lifecycle Action registry/owner mismatch')
    _require(not set(ed['finished_action_list']).intersection(ed['cancelled_action_list']), 'conflicting terminal lifecycle')
    # Family/type preflight precedes native schedule validation or any getters.
    action_refs = [wd['event_history'].get(aid) for aid in ed['pending_action_list']+ed['cancelled_action_list']]
    action_refs += [m.action for record in book._choices.values() for m in record.members]
    for action in action_refs:
        if type(action) not in _ACTIONS:raise UnsupportedEvaluation('unsupported whole-interval Action family')
        data = object.__getattribute__(action, '__dict__')
        if inspect.getattr_static(type(action),'on_schedule',None) is not None:
            raise UnsupportedEvaluation('unreviewed scheduling hook')
        if 'on_completed' in data:
            raise UnsupportedEvaluation('unreviewed completion metadata')
        if type(action) in (ObserveGroupAction,AskAboutPastAction) or (
                type(action) is SpotAction and data.get('group_fully_visible') is True):
            from objective_reality import objective_action_data
            objective_action_data(action)
        if any(callable(v) for k,v in data.items() if k != 'generate'):
            raise UnsupportedEvaluation('unreviewed Action callback before interval capture')
        _require(data['universe'] is ed['universe'], 'Action belongs to another Universe')
        if data.get('encounter',encounter) is not encounter or data.get('_encounter',encounter) not in (None,encounter):
            raise IntervalIntegrityError('Action Encounter reference mismatch')
    # Reviewed native assertions are read-only and validate declarations/packets.
    encounter._pending_schedule()
    reservations = tuple(r for b in wd['_choice_books'] for r in b._reservations)
    for index,r in enumerate(reservations):
        _require(r.object_id in registry and r.start < r.boundary, 'invalid active-Object reservation')
        for old in reservations[:index]:
            _require(not (r.object_id==old.object_id and max(r.start,old.start)<min(r.boundary,old.boundary)),
                'overlapping or duplicate active-Object reservations')
    for cid, record in book._choices.items():
        _require(record.view.id==cid and record.view.action_ids==tuple(m.action.id for m in record.members)
            and len(record.prepared)==len(record.members)==len(record.signatures)
            and record.view.first_start==min(p.start_time for p in record.prepared), 'choice packet/membership mismatch')
        for member,packet in zip(record.members,record.prepared):
            _require(type(packet) is PreparedSchedule and packet.action_id==member.action.id, 'invalid prepared packet')
            state = 'accepted' if record.view.state=='accepted' else book._states.get(packet.action_id)
            if state in ('accepted','registered','executing'):
                expected = {(cid,packet.action_id,key,packet.start_time,math.ceil(packet.end_time)) for key in packet.active_object_ids}
                actual = {(r.choice_id,r.action_id,r.object_id,r.start,r.boundary) for r in book._reservations if r.action_id==packet.action_id}
                _require(actual==expected, 'missing or changed active-Object reservation')
            if state in ('registered','executing'):
                known=book._registered.get(packet.action_id)
                _require(known is not None and known[0]==cid and known[1] is packet
                    and packet.start_time==member.action.start_time and packet.end_time==member.action.end_time, 'changed registered packet ownership')
            if state == 'registered':
                _require(packet.start_time >= now, 'missed Action start fence')
            if state == 'executing':
                _require(packet.start_time <= now and getattr(member.action,'_activity_started',False), 'invalid executing Action start')
    return ed,wd,registry,book


def _motion(positions, velocities, frame, velocity_frame, duration):
    if velocity_frame not in ('global','local'):raise ValueError('invalid velocity frame')
    if velocity_frame == 'local' and frame is None:raise ValueError('local movement requires a LocalFrame')
    if frame is not None:native_data(frame,(LocalFrame,))
    velocities = {} if velocities is None else velocities
    if type(velocities) is not dict:raise UnsupportedEvaluation('movement requires a native velocity dict')
    result = {}
    for key,vector in velocities.items():
        _require(key in positions and positions[key] is not None, 'moving Object must be a positioned participant')
        if type(vector) not in (tuple,list) or len(vector)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) for v in vector):
            raise ValueError('velocity requires three finite native numeric components')
        value = tuple(float(v) for v in vector)
        if velocity_frame == 'local': value = frame.vector_to_global(value)
        integrate_position(positions[key],value,duration)  # Native full-displacement preflight.
        result[key] = value
    return MappingProxyType(result)


def _data_metadata(updates, encounter):
    return MappingProxyType({aid:MappingProxyType({key:(AuthorityReference('encounter',encounter.id,id(encounter))
        if key=='_encounter' else value) for key,value in data.items()}) for aid,data in updates.items()})


def _stage_start_fence(encounter, boundary, time, phase, positions, pending, events, initialization,
                       registered, states, choice_states, records, rng_state):
    """Native publish_due/_start_due metadata as data, never native callbacks."""
    published, added, started = [],[],[]
    for cid,record in records.items():
        if choice_states[cid] == 'accepted' and record.view.first_start == time:
            # Complete choice is visible before any member is sampled/started.
            published.append(cid); choice_states[cid]='executing'
            for member,packet in zip(record.members,record.prepared):
                aid = packet.action_id
                _require(aid not in pending and (aid not in events or events[aid] is member.action), 'duplicate staged publication')
                events[aid]=member.action; pending.append(aid); added.append(aid)
                initialization[aid] = {k:v for k,v in packet.initialization if k!='start_position'}
                initialization[aid].update(end_time=packet.end_time,parent_event_id=encounter.id)
                registered[aid]=(cid,packet,declaration(member.action)); states[aid]='registered'
    # Read geometry with all newly published dependencies present. No Action
    # result/effects are evaluated here; defense start samples are geometric.
    updates = {}
    for aid,(cid,packet,_) in registered.items():
        if states[aid]!='registered' or packet.start_time!=time:continue
        for book in encounter.universe._choice_books:
            for old in book._reservations:
                if old.choice_id!=cid and old.object_id in packet.active_object_ids and old.boundary<=time:
                    _require(book.encounter.last_processed_boundary>=old.boundary or
                        (book is encounter._choice_book and phase=='after_settlement' and old.boundary==boundary),
                        'Object handoff requires preceding boundary settlement')
        action=events[aid]; data={'_activity_started':True}
        if type(action) is RunAction:data['start_position']=positions[action.actor_id]
        if type(action) is MeleeDefense:
            fence=_StagedReadFence(id(encounter),boundary,tuple(pending),events,initialization,registered,states,positions,{})
            snap=capture_snapshot(encounter,boundary,rng_state=rng_state,_objective=True,_stage=fence)
            strike=snap.actions.get(initialization.get(aid,{}).get('target_action_id',action.target_action_id))
            if strike is not None:data['threat_at_schedule']=((strike.id,snap.melee_status(strike)[0]=='in_reach'),)
            if action.kind=='yield':
                data['start_position']=positions.get(action.actor_id)
                data['target_position']=positions.get(action.target_id)
        updates[aid]=data
    for aid,data in updates.items():
        initialization.setdefault(aid,{}).update(data); states[aid]='executing'; started.append(aid)
    metadata={aid:dict(initialization[aid]) for aid in set(added+started)}
    return StartFence(time,phase,tuple(published),tuple(added),tuple(started),_data_metadata(metadata,encounter))


def _validate_closure(candidate):
    _require(type(candidate) is IntervalCandidate and candidate.coverage=='complete_supported_interval'
        and candidate.ready_for_publication is False, 'invalid interval completeness/readiness')
    snapshot=candidate.pre_action_snapshot; supported=candidate.supported_candidate
    _require(supported.coverage=='complete_supported_due_set' and not supported.ready_for_publication
        and supported.boundary.source_snapshot is snapshot and supported.boundary.coverage=='complete_supported_batch'
        and supported.boundary.observer_reconciliation_complete, 'incomplete supported interval Action coverage')
    due={aid for aid,a in snapshot.actions.items() if a.boundary==candidate.boundary}
    _require(set(supported.boundary.actions)==due and set(supported.lifecycle)==due, 'missing interval due Action')
    changes=candidate.proposed_authoritative_changes
    _require(set(changes)=={'clock','positions','facings','environment','fatigue_history','targets','objective','recipients',
        'lifecycle','action_metadata','queues','rng'}, 'incomplete authoritative recipient inventory')
    _require(changes['targets'] is supported.boundary.targets and changes['objective'] is supported.objective
        and changes['recipients'] is supported.recipients and changes['lifecycle'] is supported.lifecycle,
        'disconnected authoritative effect projection')
    _require(changes['clock']['time']==candidate.boundary and snapshot.boundary==candidate.boundary
        and snapshot.encounter_id==candidate.encounter_id, 'wrong interval boundary/Encounter')
    queues=changes['queues']
    _require(len(queues.pending)==len(set(queues.pending)) and not set(queues.pending).intersection(queues.finished),
        'inconsistent proposed queues')
    _require(all(r.boundary>candidate.boundary for r in queues.reservations), 'early or missing resource release')
    _require(candidate.provisional_rng.after==supported.boundary.provisional_rng_state, 'RNG projection mismatch')
    _require(type(candidate.projectile_updates) is tuple
        and len({u.object_id for u in candidate.projectile_updates})==len(candidate.projectile_updates),
        'invalid projectile boundary update set')
    for update in candidate.projectile_updates:
        _require(type(update) is ProjectileMotionUpdate and type(update.prior_flight) is ProjectileFlight
            and type(update.next_flight) is ProjectileFlight and type(update.state) is ProjectileBoundaryState
            and update.state.boundary==candidate.boundary
            and update.state.source_action_id==update.prior_flight.source_action_id
            and update.state.source_effect_identity==update.prior_flight.source_effect_identity
            and update.state.position==candidate.proposed_authoritative_changes['positions'].get(update.object_id)
            and update.state.status==update.next_flight.status
            and update.next_flight.source_action_id==update.prior_flight.source_action_id
            and update.next_flight.source_effect_identity==update.prior_flight.source_effect_identity
            and update.next_flight.release_time==update.prior_flight.release_time
            and update.next_flight.impact_time==update.prior_flight.impact_time
            and update.next_flight.release_position==update.prior_flight.release_position
            and update.next_flight.landing_position==update.prior_flight.landing_position
            and update.next_flight.velocity_m_s==update.prior_flight.velocity_m_s
            and (update.state.status=='landed')==(update.prior_flight.impact_time<=candidate.boundary)
            and (update.next_flight.landing_recorded_at==float(candidate.boundary)
                 if update.state.status=='landed' else update.next_flight.landing_recorded_at is None),
            'inconsistent projectile boundary projection')
    operation=candidate.adult_member_candidate
    if operation is not None:
        from group_member_realization import AdultMemberCandidate
        _require(type(operation) is AdultMemberCandidate
            and operation.request.publication_boundary==candidate.boundary
            and operation.first_eligible_boundary==candidate.boundary+1
            and operation.encounter_id==candidate.encounter_id
            and operation.encounter_identity==candidate.start_checkpoint.encounter.identity
            and operation.universe_identity==candidate.start_checkpoint.universe.identity
            and operation.read_dependencies==candidate.start_checkpoint.read_set,
            'invalid or stale adult-member system operation')
        _require(operation.request.group_id in snapshot.entities
            and operation.member_id not in snapshot.entities
            and all(operation.member_id not in (getattr(action,'actor_id',None),
                getattr(action,'target_id',None),getattr(action,'instrument_id',None))
                for action in snapshot.actions.values()),
            'adult realization would cross the current shared snapshot boundary')


def _native_lock(world):
    data=native_data(world,(Universe,))
    if type(data['_schedule_lock']) is not RLock:
        raise UnsupportedEvaluation('unreviewed scheduling lock/context callback')
    return data['_schedule_lock']


def prepare_interval_candidate(encounter, next_boundary, *, velocities=None, velocity_frame='global', facing_updates=None,
                               movement_stop_times=None, movement_targets=None,
                               rng_state=None, rng_owner=None, _restore_context=None,
                               adult_member_candidate=None):
    """Read one committed checkpoint; return one inactive, detached interval.

    The schedule lock protects acceptance/publication during capture. Other
    authoritative writes must obey the owning caller's quiescence contract;
    start/end read-set checks detect content/identity drift, not a world lock.
    """
    if type(encounter) is not Encounter:raise UnsupportedEvaluation('native Encounter interval adapter required')
    world=object.__getattribute__(encounter,'__dict__')['universe']
    native_data(world,(Universe,))
    with _native_lock(world):
        ed,wd,objects,book=_preflight(encounter,next_boundary)
        role,owner_identity,before_rng=_rng_input(encounter,rng_state,rng_owner)
        read_set=_read_set(encounter)
        if adult_member_candidate is not None:
            from group_member_realization import (
                AdultMemberCandidate, validate_adult_member_candidate,
            )
            _require(type(adult_member_candidate) is AdultMemberCandidate,
                'unsupported non-Action interval operation')
            _require(_restore_context is None,
                'adult realization cannot be combined with checkpoint continuation')
            _require(adult_member_candidate.request.publication_boundary==next_boundary
                and adult_member_candidate.read_dependencies==read_set,
                'adult-member candidate boundary or read dependency is stale')
            group=world.get_object_by_id(adult_member_candidate.request.group_id)
            validate_adult_member_candidate(encounter,group,adult_member_candidate)
        checkpoint=IntervalCheckpoint(AuthorityReference('encounter',encounter.id,id(encounter)),
            AuthorityReference('universe',world.id,id(world)),ed['time'],ed['last_processed_boundary'],
            wd['_schedule_revision'],read_set,_digest(read_set))
        for key,obj in objects.items():
            if key in ed['being_list']+ed['non_being_object_list']:
                _require(sum(x is obj for x in objects.values())==1, 'aliased authoritative Object')
        positions={key:None if objects[key].spatial_state is None else position(
            native_data(objects[key].spatial_state,(SpatialState,))['position']) for key in ed['being_list']+ed['non_being_object_list']}
        active_flight_ids={key for key in positions
            if type(object.__getattribute__(objects[key],'__dict__').get('_projectile_flight')) is ProjectileFlight
            and object.__getattribute__(objects[key],'__dict__')['_projectile_flight'].status=='in_flight'}
        if velocities is not None and active_flight_ids.intersection(velocities):
            raise UnsupportedEvaluation('in-flight projectile motion is derived from its committed launch state')
        motion=_motion(positions,velocities,ed['local_frame'],velocity_frame,next_boundary-ed['time'])
        movement_stop_times = {} if movement_stop_times is None else dict(movement_stop_times)
        movement_targets = {} if movement_targets is None else dict(movement_targets)
        _require(set(movement_stop_times) == set(movement_targets),
            'movement arrival times and exact destination positions must have matching participants')
        _require(all(key in motion and type(value) in (int, float)
                     and math.isfinite(value) and ed['time'] < value <= next_boundary
                     for key, value in movement_stop_times.items()),
            'movement arrival time must fall inside this committed interval')
        _require(all(key in motion and type(value) is CartesianPosition
                     for key, value in movement_targets.items()),
            'exact movement destinations must be native Cartesian positions')
        facing_updates = {} if facing_updates is None else dict(facing_updates)
        from being import BeingInstance
        from hex_facing import validate_facing
        if any(key not in ed['being_list'] or type(objects[key]) is not BeingInstance
               or key not in motion or not any(motion[key])
               or validate_facing(value) != value for key, value in facing_updates.items()):
            raise UnsupportedEvaluation('facing updates require a moving participant Being and legal native orientation')
        projectile_updates=[]
        for key in tuple(positions):
            flight=object.__getattribute__(objects[key],'__dict__').get('_projectile_flight')
            if flight is None:continue
            _require(type(flight) is ProjectileFlight and flight.status in ('in_flight','landed'),
                'unsupported projectile flight descriptor')
            if flight.status=='landed':continue
            _require(positions[key]==flight.position_at(ed['time']),
                'projectile starting position disagrees with committed flight state')
            landed=flight.impact_time<=next_boundary
            target_position=flight.landing_position if landed else flight.position_at(next_boundary)
            next_flight=replace(flight,status='landed' if landed else 'in_flight',
                landing_recorded_at=float(next_boundary) if landed else None)
            state=ProjectileBoundaryState(flight.source_action_id,next_boundary,target_position,
                next_flight.status,flight.impact_time,
                flight.source_effect_identity)
            positions[key]=target_position
            projectile_updates.append(ProjectileMotionUpdate(key,flight,next_flight,state))
        pending=list(ed['pending_action_list']);events=dict(wd['event_history']);initialization={}
        registered=dict(book._registered);states=dict(book._states)
        choice_states={cid:r.view.state for cid,r in book._choices.items()}; records=book._choices
        fences=[];movement=[];now=ed['time']
        def start(time,phase):
            fence=_stage_start_fence(encounter,next_boundary,time,phase,positions,pending,events,
                initialization,registered,states,choice_states,records,before_rng)
            if fence.published_choices or fence.started_action_ids:fences.append(fence)
        start(now,'before_movement')
        while now<next_boundary:
            times=[r.view.first_start for cid,r in records.items() if choice_states[cid]=='accepted' and r.view.first_start>now]
            times += [packet.start_time for aid,(_,packet,_) in registered.items() if states[aid]=='registered' and packet.start_time>now]
            times += [value for value in movement_stop_times.values() if value > now]
            dest=min([next_boundary]+times)
            segment_motion = {key: vector for key, vector in motion.items()
                              if key not in movement_stop_times or now < movement_stop_times[key]}
            old={key:positions[key] for key in segment_motion}
            new={key:integrate_position(positions[key],vector,dest-now)
                 for key,vector in segment_motion.items()}
            for key, stop_time in movement_stop_times.items():
                if stop_time == dest:
                    new[key] = movement_targets[key]
            positions.update(new)
            movement.append(MovementSegment(now,dest,MappingProxyType(segment_motion),
                                             MappingProxyType(old),MappingProxyType(new)))
            now=dest
            if now<next_boundary:start(now,'before_boundary')
        # The staged final positions become authoritative at this committed
        # native boundary. Keep intermediate integration arithmetic precise,
        # then truncate every persisted Cartesian coordinate toward zero.
        from measured_values import truncate_position
        positions={key:None if value is None else truncate_position(value)
                   for key,value in positions.items()}
        fence=_StagedReadFence(id(encounter),next_boundary,tuple(pending),MappingProxyType(events),
            MappingProxyType(initialization),MappingProxyType(registered),MappingProxyType(states),MappingProxyType(positions),
            MappingProxyType(facing_updates))
        context=capture_observer_context(encounter,next_boundary,rng_state=before_rng,
            _stage=fence,_restore_context=_restore_context)
        if adult_member_candidate is not None:
            _require(adult_member_candidate.member_id not in context.snapshot.entities,
                'new adult must be absent from the common interval snapshot')
            _require(all(adult_member_candidate.member_id not in (
                getattr(action,'actor_id',None),getattr(action,'target_id',None),
                getattr(action,'instrument_id',None))
                for action in context.snapshot.actions.values()),
                'current-boundary Action already references proposed adult')
        if _restore_context is not None:
            from checkpoint_restore_dependencies import _PreparedContinuationContext
            from frozen_practice import _validate_imported_prefix
            if type(_restore_context) is not _PreparedContinuationContext:
                raise EvaluationIntegrityError('unsupported trusted-local practice context')
            _validate_imported_prefix(_restore_context.imported_prefix)
            if (_restore_context.evaluation_binding() !=
                    getattr(context.snapshot, 'imported_practice_dependency', None)):
                raise EvaluationIntegrityError('imported practice dependency differs from activated context')
        # Shared mutable Target storage would require an additional aliasing
        # contract during identity-preserving application. Refuse it now.
        current_owners={}; spatial_owners={}
        for key in context.snapshot.entities:
            obj=objects[key]
            _require(sum(x is obj for x in objects.values())==1, 'aliased transitive Object identity')
            obj_data=object.__getattribute__(obj,'__dict__')
            current=id(obj_data['current'])
            _require(current not in current_owners, 'aliased mutable Target current state')
            current_owners[current]=key
            if key in positions and obj_data['spatial_state'] is not None:
                spatial=id(obj_data['spatial_state'])
                _require(spatial not in spatial_owners, 'aliased mutable spatial state')
                spatial_owners[spatial]=key
        supported=build_supported_candidate(context)
        # Exactly the native settled ordering: finish due Actions, release the
        # old resources, then publish/start choices at the endpoint fence.
        finished=list(ed['finished_action_list']);cancelled=tuple(ed['cancelled_action_list'])
        for aid in supported.boundary.actions:
            if aid in pending:pending.remove(aid);finished.append(aid);states[aid]='finished'
        reservations=tuple(r for r in book._reservations if r.boundary>next_boundary)
        for cid,r in records.items():
            if choice_states[cid]=='executing' and all(states.get(aid) in ('finished','cancelled') for aid in r.view.action_ids):
                choice_states[cid]='finished'
        start(next_boundary,'after_settlement')
        revision=wd['_schedule_revision']+sum(len(f.published_choices) for f in fences)+sum(
            a.lifecycle!='cancelled' for a in context.snapshot.actions.values() if a.boundary==next_boundary)+1
        metadata=_data_metadata(initialization,encounter)
        queues=QueueProjection(tuple(pending),tuple(finished),cancelled,
            tuple(RegistrationIntent(AuthorityReference('event',aid,id(events[aid])),registered[aid][0],
                AuthorityReference('accepted_packet',aid,id(registered[aid][1])),metadata[aid])
                for f in fences for aid in f.registered_action_ids),
            MappingProxyType(states),MappingProxyType(choice_states),reservations,revision)
        provisional=ProvisionalRNG(role,owner_identity,before_rng,supported.boundary.provisional_rng_state,
            supported.boundary.trace,supported.observer_trace,supported.objective.draws)
        history=freeze(ed['fatigue_frame_history'])+(freeze({'start':checkpoint.start,'time':next_boundary,
            'views':context.snapshot.fatigue}),)
        changes=MappingProxyType({'clock':freeze({'time':next_boundary,'coordinator_time':next_boundary,
            'last_processed_boundary':next_boundary,'interval_start':next_boundary,'active_boundary':None}),
            'positions':MappingProxyType(dict(positions)), 'facings':MappingProxyType(facing_updates), 'environment':freeze({'adapter':'native_update_environment_noop',
                'fatigue':context.snapshot.fatigue,'physiology':context.snapshot.physiology}),
            'fatigue_history':history,'targets':supported.boundary.targets,'objective':supported.objective,
            'recipients':supported.recipients,'lifecycle':supported.lifecycle,
            'action_metadata':metadata,'queues':queues,'rng':provisional})
        candidate=IntervalCandidate(encounter.id,next_boundary,checkpoint,tuple(movement),tuple(fences),
            context.snapshot,supported,provisional,changes,
            adult_member_candidate=adult_member_candidate,
            projectile_updates=tuple(projectile_updates))
        _validate_closure(candidate)
        from transactional_progression import _validate_restored_candidate_context
        _validate_restored_candidate_context(encounter,candidate)
        _guard_methods()
        _require(_read_set(encounter)==read_set, 'authoritative dependency changed during interval preparation')
        _require(_rng_input(encounter,rng_state,rng_owner)==(role,owner_identity,before_rng), 'RNG owner changed during preparation')
        issued = replace(candidate,integrity_token=_digest(_semantic(candidate)))
        key = id(issued)
        _ISSUED_CANDIDATES[key] = weakref.ref(issued, lambda ref: _ISSUED_CANDIDATES.pop(key, None))
        return issued


def validate_interval_candidate(encounter, candidate, *, rng_state=None, rng_owner=None):
    """Read-only stale-dependency check for a future 5C2 publisher, not approval.

    No application/commit/rollback is supplied. The same RNG ownership arguments
    used at preparation must be supplied here for caller/facade-owned streams.
    """
    _validate_closure(candidate)
    _require(candidate.integrity_token==_digest(_semantic(candidate)), 'interval candidate integrity mismatch')
    checkpoint=candidate.start_checkpoint
    if id(encounter)!=checkpoint.encounter.identity or encounter.id!=candidate.encounter_id:
        raise StaleInterval('wrong authoritative Encounter identity')
    world=object.__getattribute__(encounter,'__dict__')['universe']
    try: lock=_native_lock(world)
    except (TypeError,KeyError) as exc: raise StaleInterval('changed Universe/lock authority') from exc
    with lock:
        try:
            _preflight(encounter,candidate.boundary)
            if candidate.adult_member_candidate is not None:
                from group_member_realization import validate_adult_member_candidate
                group=world.get_object_by_id(candidate.adult_member_candidate.request.group_id)
                validate_adult_member_candidate(encounter,group,candidate.adult_member_candidate)
            from transactional_progression import _validate_restored_candidate_context
            _validate_restored_candidate_context(encounter,candidate)
            current=_read_set(encounter)
            rng=_rng_input(encounter,rng_state,rng_owner)
        except (ValueError,TypeError,KeyError,AttributeError) as exc:
            raise StaleInterval('invalid or changed interval authority') from exc
        if (current!=checkpoint.read_set or _digest(current)!=checkpoint.dependency_token
            or rng!=(candidate.provisional_rng.role,candidate.provisional_rng.owner_identity,candidate.provisional_rng.before)):
            raise StaleInterval('interval identity/content/revision/RNG dependency changed')
    return True
