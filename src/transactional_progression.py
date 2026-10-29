"""Explicit native Encounter mode/dispatch gate (5C3A).

This module owns no simulation timeline or result reducer. Each routed second
uses the existing committed cursor, 5C1 staging and 5C2 publication unchanged.
Control bindings are process-local and never an authoritative save format.
"""
from dataclasses import dataclass
import math
import threading
import weakref


class TransactionalProgressionError(ValueError):
    pass


@dataclass(frozen=True)
class ProgressionMode:
    name: str
    encounter_identity: int
    rng_role: str
    rng_owner_identity: int
    authority_contract: str = 'quiescent_or_coordinated_native_access'


@dataclass(frozen=True)
class _Binding:
    encounter: object  # weakref
    mode: ProgressionMode
    rng_owner: object
    running: object  # nonblocking control lock, outside the checkpoint graph


_BINDINGS = {}
_FACADES = {}
_LEGACY_USED = {}
_ROUTED_OWNERSHIP = {}


def mode_of(encounter):
    data=object.__getattribute__(encounter,'__dict__')
    binding=_BINDINGS.get(id(encounter));declared=data.get('_transactional_mode')
    if binding is None and declared is None:return 'legacy'
    if (binding is None or binding.encounter() is not encounter or declared is not binding.mode
            or type(declared) is not ProgressionMode or declared.encounter_identity!=id(encounter)):
        raise TransactionalProgressionError('missing/changed native transactional mode binding; no legacy fallback')
    return 'transactional'


def guard_legacy_encounter(encounter, operation='legacy consumer'):
    if mode_of(encounter)=='transactional':
        raise TransactionalProgressionError(operation+' is unavailable on a transactional Encounter; native step() only (5C3A)')


def register_legacy_facade(encounter,facade):
    key=id(encounter)
    _FACADES[key]=(weakref.ref(encounter),weakref.ref(facade))


def _owned_ids(encounter,world_data):
    ed=object.__getattribute__(encounter,'__dict__')
    ids=set(ed['being_list']+ed['non_being_object_list'])
    registry=object.__getattribute__(world_data['object_registry'],'__dict__')['object_instances']
    for key in tuple(ids):
        item=registry.get(key)
        if item is None:continue
        current=object.__getattribute__(object.__getattribute__(item,'__dict__')['current'],'__dict__')
        ids.update(value for value in current.get('body_parts',{}).values() if value is not None)
        if current.get('armor_id') is not None:ids.add(current['armor_id'])
    return ids


def guard_legacy_action(action, *, effect=False):
    """Block reviewed direct legacy mutators for a selected native authority.

    Record legacy execution attempts associated with an existing Encounter, so
    an unrecorded direct resolver cannot later be mistaken for a fresh graph.
    Pure preparation/geometry/roll calculations are not intercepted.
    """
    if not _BINDINGS and not effect:return
    ad=object.__getattribute__(action,'__dict__');world=ad.get('universe')
    if world is None:return
    wd=object.__getattribute__(world,'__dict__')
    for book in wd.get('_choice_books',()):
        enc=object.__getattribute__(book,'__dict__')['encounter']
        ed=object.__getattribute__(enc,'__dict__')
        related=(ad.get('encounter') is enc or ad.get('_encounter') is enc
            or ad.get('parent_event_id')==ed['id']
            or any(ad.get(key) in _owned_ids(enc,wd) for key in ('actor_id','target_id','instrument_id') if ad.get(key) is not None))
        if not related:continue
        if mode_of(enc)=='transactional':
            raise TransactionalProgressionError('direct legacy Action resolution/completion/damage/export is forbidden on transactional authority')
        if effect:
            key=id(enc)
            _LEGACY_USED[key]=weakref.ref(enc,lambda ref,key=key:_LEGACY_USED.pop(key,None))


def validate_publication_entry(encounter,ownership):
    if mode_of(encounter)=='transactional' and _ROUTED_OWNERSHIP.get(id(encounter)) is not ownership:
        raise TransactionalProgressionError('selected transactional Encounters publish only through their native step route')


def planning_entry(encounter):
    if mode_of(encounter)=='transactional' and _BINDINGS[id(encounter)].running.locked():
        raise TransactionalProgressionError('choice/cancellation editing is allowed only between transactional step calls')


def validate_action_contract(encounter,action,*,_force=False):
    """Closed declaration checks before native preparation or publication."""
    if not _force and mode_of(encounter)!='transactional':return
    from interval_staging import _guard_methods
    _guard_methods()
    import inspect
    from action import Action
    from activities import RunAction,SpotAction
    from melee_combat import MeleeStrike
    from melee_defense import MeleeDefense
    from group_observation import ObserveGroupAction
    from history_conversation import AskAboutPastAction
    from observer_proposals import _NATIVE_RESOLVERS,_NATIVE_HOOKS,_capture_belief,frozen_value
    from objective_reality import objective_action_data
    from action_evaluation import UnsupportedEvaluation
    if type(action) not in (Action,RunAction,SpotAction,MeleeStrike,MeleeDefense,ObserveGroupAction,AskAboutPastAction):
        raise UnsupportedEvaluation('transactional progression requires a reviewed exact native Action family')
    data=object.__getattribute__(action,'__dict__')
    if (inspect.getattr_static(type(action),'resolve') is not _NATIVE_RESOLVERS[type(action)]
            or 'on_completed' in data or inspect.getattr_static(type(action),'on_completed',None) is not _NATIVE_HOOKS.get(type(action))
            or any(callable(value) for key,value in data.items() if key!='generate')):
        raise UnsupportedEvaluation('transactional Action callback/override requires a reviewed proposal adapter')
    if type(action) is Action and data['event_type'] not in ('swing','thrust'):
        raise UnsupportedEvaluation('unsupported transactional base Action activity')
    if type(action) in (ObserveGroupAction,AskAboutPastAction):objective_action_data(action)
    if type(action) is ObserveGroupAction and data['ledger'] is not None:
        _capture_belief(data['ledger'],data['actor_id'])
    if type(action) is AskAboutPastAction and data['received_accounts'] is not None:
        from history_conversation import HeardAccount
        accounts=data['received_accounts']
        if type(accounts) is not list or any(type(item) is not HeardAccount for item in accounts):
            raise UnsupportedEvaluation('transactional testimony requires a native in-world account list')
        frozen_value(accounts)


def validate_choice_actions(encounter,actions):
    if mode_of(encounter)!='transactional':return
    from action_choice import ChoiceMember
    if type(actions) not in (tuple,list,dict):
        raise TransactionalProgressionError('transactional choices require native list/tuple/dict declarations')
    for member in (actions.values() if type(actions) is dict else actions):
        validate_action_contract(encounter,member.action if type(member) is ChoiceMember else member)


def _all_declarations(encounter,boundary,rng_owner):
    """Reuse native capture for static coverage, including unpublished futures.

    This is declaration validation only: no endpoint evaluation or speculative
    future interval is created. Actual movement/start/effect evaluation remains
    exclusively in prepare_interval_candidate at its real next checkpoint.
    """
    from interval_staging import _preflight,_rng_input,_StagedReadFence
    from observer_proposals import capture_observer_context
    from action_choice import declaration
    ed,wd,objects,book=_preflight(encounter,boundary)
    _,_,rng=_rng_input(encounter,None,rng_owner)
    pending=list(ed['pending_action_list']);events=dict(wd['event_history'])
    registered=dict(book._registered);states=dict(book._states);initial={}
    for record in book._choices.values():
        for member,packet in zip(record.members,record.prepared):
            validate_action_contract(encounter,member.action,_force=True)
            if record.view.state!='accepted':continue
            aid=packet.action_id;events[aid]=member.action;pending.append(aid)
            initial[aid]={key:value for key,value in packet.initialization if key!='start_position'}
            initial[aid].update(end_time=packet.end_time,parent_event_id=encounter.id)
            registered[aid]=(record.view.id,packet,declaration(member.action));states[aid]='registered'
    fence=_StagedReadFence(id(encounter),boundary,tuple(pending),events,initial,registered,states,{})
    return capture_observer_context(encounter,boundary,rng_state=rng,_stage=fence)


def enable_transactional_progression(encounter, *, quiescent=False, rng_owner=None):
    from encounter import Encounter
    from atomic_publication import publication_boundary
    from interval_staging import _rng_input
    if type(encounter) is not Encounter:raise TransactionalProgressionError('native Encounter required')
    if mode_of(encounter)!='legacy':raise TransactionalProgressionError('transactional mode is irreversible and cannot be reconfigured')
    with publication_boundary(encounter,quiescent=quiescent):
        if mode_of(encounter)!='legacy':
            raise TransactionalProgressionError('transactional selection already completed; mode cannot be reconfigured')
        ed=object.__getattribute__(encounter,'__dict__')
        facade=_FACADES.get(id(encounter));used=_LEGACY_USED.get(id(encounter))
        if (ed['time']!=ed['start_time'] or ed['fatigue_frame_history'] or ed['finished_action_list'] or ed['cancelled_action_list']
                or ed.get('_atomic_interval_history') or (used is not None and used() is encounter)
                or (facade is not None and facade[0]() is encounter and facade[1]() is not None)):
            raise TransactionalProgressionError('select native programmatic mode before any legacy progression/resolution, incompatible history or facade ownership')
        role,identity,_=_rng_input(encounter,None,rng_owner)
        if role not in ('module','native_random','caller_cursor'):
            raise TransactionalProgressionError('facade RNG ownership is outside native programmatic progression (5C3B)')
        _all_declarations(encounter,ed['last_processed_boundary']+1,rng_owner)
        # Dynamic outcomes/facts/practice depend on the requested movement.
        # Evaluate them only at the actual staged boundary, never at selection.
        descriptor=ProgressionMode('transactional',id(encounter),role,identity)
        key=id(encounter)
        binding=_Binding(weakref.ref(encounter,lambda ref:_BINDINGS.pop(key,None)),descriptor,rng_owner,threading.Lock())
        _BINDINGS[key]=binding
        try:ed['_transactional_mode']=descriptor
        except BaseException:
            _BINDINGS.pop(key,None);raise
        return descriptor


def step_transactionally(encounter,duration,velocities,velocity_frame):
    from atomic_publication import publication_boundary,publish_interval_candidate
    from interval_staging import _motion
    from encounter import EncounterStep
    if mode_of(encounter)!='transactional':raise TransactionalProgressionError('explicit transactional selection required')
    binding=_BINDINGS[id(encounter)]
    if not binding.running.acquire(blocking=False):raise TransactionalProgressionError('reentrant/concurrent transactional progression')
    try:
        # Native real inputs only; opaque numeric conversion is not an adapter.
        if type(duration) not in (int,float) or not math.isfinite(duration) or duration<=0:
            raise TransactionalProgressionError('transactional duration must be finite and positive')
        start=encounter.time;end=start+duration
        if not math.isfinite(end) or end<=start or end!=math.floor(end):
            raise TransactionalProgressionError('transactional step must end at an exact integer boundary; fractional tails are unsupported')
        if encounter.end_time is not None and end>encounter.end_time:
            raise TransactionalProgressionError('transactional step exceeds Encounter end')
        completed=[];motion=None
        while encounter.time<end:
            with publication_boundary(encounter,quiescent=True) as ownership:
                # Reentrant entry checks are private control state, not timeline
                # flags; 5C1/5C2 see an actual committed native checkpoint.
                boundary=encounter.last_processed_boundary+1
                context=_all_declarations(encounter,boundary,binding.rng_owner)
                if motion is None:
                    positions={key:context.snapshot.entities[key].position for key in context.snapshot.participant_ids}
                    motion=dict(_motion(positions,velocities,encounter.local_frame,velocity_frame,end-start))
                # The same scope covers validation, staging and publication.
                if mode_of(encounter)!='transactional':raise TransactionalProgressionError('mode changed')
                _ROUTED_OWNERSHIP[id(encounter)]=ownership
                try:
                    candidate=encounter.prepare_interval_candidate(boundary,velocities=motion,rng_owner=binding.rng_owner)
                    receipt=publish_interval_candidate(encounter,candidate,ownership=ownership,rng_owner=binding.rng_owner)
                    completed.extend(receipt.action_ids)
                finally:_ROUTED_OWNERSHIP.pop(id(encounter),None)
        return EncounterStep(start,end,tuple(motion),tuple(completed))
    finally:binding.running.release()


def recover_transactional_progression(encounter,token):
    from atomic_publication import publication_boundary,recover_interval_publication
    if mode_of(encounter)!='transactional':raise TransactionalProgressionError('explicit transactional selection required')
    binding=_BINDINGS[id(encounter)]
    if not binding.running.acquire(blocking=False):raise TransactionalProgressionError('cannot recover during active progression')
    try:
        with publication_boundary(encounter,quiescent=True) as ownership:
            return recover_interval_publication(encounter,token,ownership=ownership,rng_owner=binding.rng_owner)
    finally:binding.running.release()
