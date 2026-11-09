"""Explicit native Encounter mode/dispatch gate (5C3A).

This module owns no simulation timeline or result reducer. Each routed second
uses the existing committed cursor, 5C1 staging and 5C2 publication unchanged.
Control bindings are process-local and never an authoritative save format.
"""
from dataclasses import dataclass
import math
import threading
import weakref
from contextlib import contextmanager


class TransactionalProgressionError(ValueError):
    pass


def assert_not_quarantined(encounter, operation='gameplay operation'):
    data = object.__getattribute__(encounter, '__dict__')
    world = data.get('universe')
    active = _ACTIVE_RESTORED_EXECUTION
    if (active is not None and active[0]() is encounter
            and active[1] == threading.get_ident()):
        return
    if is_quarantined(encounter) or (world is not None and is_quarantined(world)):
        raise TransactionalProgressionError(operation + ' is forbidden on a quarantined checkpoint reconstruction')


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
    restore_context: object = None


_BINDINGS = {}
_FACADES = {}
_LEGACY_USED = {}
_ROUTED_OWNERSHIP = {}
_QUARANTINED = weakref.WeakSet()
_ACTIVE_RESTORED_EXECUTION = None


@contextmanager
def _trusted_local_execution_scope(encounter, context):
    """Private one-call scope; quarantine markers stay intact outside/inside it."""
    global _ACTIVE_RESTORED_EXECUTION
    from checkpoint_restore_dependencies import _PreparedContinuationContext
    if (type(context) is not _PreparedContinuationContext
            or mode_of(encounter) != 'legacy' or not is_quarantined(encounter)):
        raise TransactionalProgressionError('exact quarantined prepared continuation is required')
    if _ACTIVE_RESTORED_EXECUTION is not None:
        raise TransactionalProgressionError('nested trusted-local continuation is forbidden')
    _ACTIVE_RESTORED_EXECUTION = (weakref.ref(encounter), threading.get_ident(), context)
    try:
        yield
    finally:
        _ACTIVE_RESTORED_EXECUTION = None


def _enable_prepared_transactional_progression(encounter, rng_owner, restore_context):
    """Bind only the reviewed, quarantined time-1 Run continuation context."""
    from encounter import Encounter
    from interval_staging import _rng_input
    active = _ACTIVE_RESTORED_EXECUTION
    if (type(encounter) is not Encounter or active is None
            or active[0]() is not encounter or active[1] != threading.get_ident()
            or active[2] is not restore_context):
        raise TransactionalProgressionError('trusted-local activation scope is not current')
    if mode_of(encounter) != 'legacy':
        raise TransactionalProgressionError('restored native progression is already configured')
    ed = object.__getattribute__(encounter, '__dict__')
    facade = _FACADES.get(id(encounter)); used = _LEGACY_USED.get(id(encounter))
    if (encounter.start_time != 0 or encounter.time != 1
            or encounter.last_processed_boundary != 1
            or encounter._coordinator_time != 1 or encounter._interval_start != 1
            or encounter.finished_action_list or encounter.cancelled_action_list
            or encounter.fatigue_frame_history or ed.get('_atomic_interval_history')
            or ed.get('pending_action_list') or (used is not None and used() is encounter)
            or (facade is not None and facade[0]() is encounter and facade[1]() is not None)):
        raise TransactionalProgressionError('prepared checkpoint is outside the exact fresh boundary-1 continuation state')
    role, identity, _ = _rng_input(encounter, None, rng_owner)
    if role != 'caller_cursor':
        raise TransactionalProgressionError('trusted-local continuation requires its exclusive private RNG cursor')
    if encounter._choice_book._counter != restore_context.choice_counter_floor:
        raise TransactionalProgressionError('ChoiceBook counter differs from imported identity floor')
    _all_declarations(encounter, 2, rng_owner)
    descriptor = ProgressionMode('transactional', id(encounter), role, identity)
    key = id(encounter)
    binding = _Binding(weakref.ref(encounter,
        lambda ref: _BINDINGS.pop(key, None)), descriptor, rng_owner,
        threading.Lock(), restore_context)
    _BINDINGS[key] = binding
    try:
        ed['_transactional_mode'] = descriptor
    except BaseException:
        _BINDINGS.pop(key, None)
        raise
    return descriptor


def _validate_restored_candidate_context(encounter, candidate):
    """Bind an issued interval to the exact private imported-prefix context."""
    binding = _BINDINGS.get(id(encounter))
    if binding is None or binding.encounter() is not encounter:
        if candidate.pre_action_snapshot.imported_practice_dependency is None:
            return True
        raise TransactionalProgressionError('candidate imported practice lacks a current native mode binding')
    context = binding.restore_context
    snapshot = candidate.pre_action_snapshot
    if context is None:
        if snapshot.imported_practice_dependency is not None:
            raise TransactionalProgressionError('unbound imported-practice dependency in interval')
        return True
    from checkpoint_restore_dependencies import _PreparedContinuationContext
    from frozen_practice import BatchSkillUse, _validate_imported_prefix
    if type(context) is not _PreparedContinuationContext:
        raise TransactionalProgressionError('unsupported private restored continuation binding')
    _validate_imported_prefix(context.imported_prefix)
    if (snapshot.imported_practice_dependency != context.evaluation_binding()
            or snapshot.boundary != 2 or candidate.boundary != 2
            or snapshot.encounter_id != encounter.id):
        raise TransactionalProgressionError('candidate differs from its trusted-local boundary-2 dependency')
    if (set(candidate.supported_candidate.boundary.actions) != set(context.future_action_ids)
            or any(snapshot.actions[aid].family != 'run' for aid in context.future_action_ids)):
        raise TransactionalProgressionError('candidate does not cover the admitted Run Action set')
    choices = encounter._choice_book._choices
    record = choices.get(context.future_choice_id)
    if (record is None or tuple(record.view.action_ids) != context.future_action_ids
            or record.view.state not in ('accepted', 'executing')):
        raise TransactionalProgressionError('admitted native Choice changed before candidate validation')
    prior = snapshot.practice_inputs.beings[context.imported_prefix.target_id].prior_uses
    imported = tuple(use for use in prior if type(use) is BatchSkillUse
        and use.being_id == context.imported_prefix.target_id
        and tuple(row.action_id for row in use.exercises) == context.imported_prefix.action_ids)
    if imported != context.imported_prefix.uses or len(imported) != 1:
        raise TransactionalProgressionError('imported Target practice is missing or duplicated')
    return True


def quarantine_reconstruction(encounter):
    """Register an inactive reconstruction in process-local entry-point guards."""
    world = object.__getattribute__(encounter, '__dict__').get('universe')
    _QUARANTINED.add(encounter)
    if world is not None:
        _QUARANTINED.add(world)
    object.__getattribute__(encounter, '__dict__')['_checkpoint_quarantined'] = True
    if world is not None:
        object.__getattribute__(world, '__dict__')['_checkpoint_quarantined'] = True


def quarantine_reconstructed_graph(universe, objects):
    """Mark private identity-only native objects as quarantined roots.

    This records process-local quarantine state; it does not make native Python
    objects immutable. Safety for this adapter comes from retaining these
    references privately and exposing only detached value views.
    """
    roots = (universe,) + tuple(objects)
    for value in roots:
        data = object.__getattribute__(value, '__dict__')
        _QUARANTINED.add(value)
        data['_checkpoint_quarantined'] = True


def is_quarantined(value):
    return value in _QUARANTINED or object.__getattribute__(value, '__dict__').get('_checkpoint_quarantined') is True


def mode_of(encounter):
    data=object.__getattribute__(encounter,'__dict__')
    binding=_BINDINGS.get(id(encounter));declared=data.get('_transactional_mode')
    # A dead weak binding can outlive its Encounter until cyclic GC runs. If
    # CPython later reuses that object ID for a fresh legacy Encounter, retire
    # only the dead map entry; live or explicitly marked bindings still fail
    # closed below.
    if binding is not None and binding.encounter() is None and declared is None:
        if _BINDINGS.get(id(encounter)) is binding:
            _BINDINGS.pop(id(encounter),None)
        binding=None
    if binding is None and declared is None:return 'legacy'
    if (binding is None or binding.encounter() is not encounter or declared is not binding.mode
            or type(declared) is not ProgressionMode or declared.encounter_identity!=id(encounter)):
        raise TransactionalProgressionError('missing/changed native transactional mode binding; no legacy fallback')
    return 'transactional'


def guard_legacy_encounter(encounter, operation='legacy consumer'):
    assert_not_quarantined(encounter, operation)
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
    ad=object.__getattribute__(action,'__dict__');world=ad.get('universe')
    if ad.get('_checkpoint_quarantined') is True:
        raise TransactionalProgressionError('Action resolution/completion is forbidden on a quarantined reconstruction')
    if not _BINDINGS and not effect:return
    if world is None:return
    wd=object.__getattribute__(world,'__dict__')
    for book in wd.get('_choice_books',()):
        enc=object.__getattribute__(book,'__dict__')['encounter']
        assert_not_quarantined(enc, 'Action resolution/completion')
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
    assert_not_quarantined(encounter, 'interval publication')
    if mode_of(encounter)=='transactional' and _ROUTED_OWNERSHIP.get(id(encounter)) is not ownership:
        raise TransactionalProgressionError('selected transactional Encounters publish only through their native step route')


def planning_entry(encounter):
    assert_not_quarantined(encounter, 'choice/cancellation planning')
    if mode_of(encounter)=='transactional' and _BINDINGS[id(encounter)].running.locked():
        raise TransactionalProgressionError('choice/cancellation editing is allowed only between transactional step calls')


def validate_action_contract(encounter,action,*,_force=False):
    """Closed declaration checks before native preparation or publication."""
    from activities import SpotAction, PickUpAction, ReadyWeaponAction
    if type(action) is SpotAction:
        if (type(action.start_time) not in (int, float)
                or type(action.end_time) not in (int, float)
                or not math.isfinite(action.start_time) or not math.isfinite(action.end_time)
                or action.end_time - action.start_time != 6):
            raise TransactionalProgressionError('deliberate Spot must retain its six-second duration')
        from discovery import SpottingConditions
        try:
            SpottingConditions(action.spotting_conditions)
        except (TypeError, ValueError) as exc:
            raise TransactionalProgressionError(str(exc)) from exc
    if type(action) is PickUpAction:
        if (type(action.start_time) not in (int, float)
                or type(action.end_time) not in (int, float)
                or not math.isfinite(action.start_time) or not math.isfinite(action.end_time)
                or action.event_type != 'pick up'
                or action.end_time - action.start_time != 1
                or type(action.map_width_cells) is not int
                or type(action.map_height_cells) is not int
                or action.map_width_cells < 5 or action.map_height_cells < 5
                or action.map_width_cells * action.map_height_cells > 1_000_000):
            raise TransactionalProgressionError('Pick up must retain the approved one-second Arena declaration')
    if type(action) is ReadyWeaponAction:
        if (type(action.start_time) not in (int, float)
                or type(action.end_time) not in (int, float)
                or not math.isfinite(action.start_time) or not math.isfinite(action.end_time)
                or action.event_type != 'ready weapon'
                or action.end_time - action.start_time != 1
                or action.hand not in ReadyWeaponAction.HANDS):
            raise TransactionalProgressionError('Ready weapon must retain the approved one-second hand declaration')
    if not _force and mode_of(encounter)!='transactional':return
    from interval_staging import _guard_methods
    _guard_methods()
    import inspect
    from action import Action
    from activities import RunAction,SpotAction,PickUpAction,ReadyWeaponAction
    from activities import ThrowAction
    from melee_combat import MeleeStrike
    from melee_defense import MeleeDefense
    from group_observation import ObserveGroupAction
    from history_conversation import AskAboutPastAction
    from observer_proposals import _NATIVE_RESOLVERS,_NATIVE_HOOKS,_capture_belief,frozen_value
    from objective_reality import objective_action_data
    from action_evaluation import UnsupportedEvaluation
    if type(action) not in (Action,RunAction,SpotAction,ThrowAction,PickUpAction,ReadyWeaponAction,MeleeStrike,MeleeDefense,ObserveGroupAction,AskAboutPastAction):
        raise UnsupportedEvaluation('transactional progression requires a reviewed exact native Action family')
    data=object.__getattribute__(action,'__dict__')
    if (inspect.getattr_static(type(action),'resolve') is not _NATIVE_RESOLVERS[type(action)]
            or 'on_completed' in data or inspect.getattr_static(type(action),'on_completed',None) is not _NATIVE_HOOKS.get(type(action))
            or any(callable(value) for key,value in data.items() if key!='generate')):
        raise UnsupportedEvaluation('transactional Action callback/override requires a reviewed proposal adapter')
    if type(action) is Action and data['event_type'] not in ('swing','thrust'):
        raise UnsupportedEvaluation('unsupported transactional base Action activity')
    if type(action) is ThrowAction:
        if (data.get('event_type') != 'throw' or data.get('target_id') is not None
                or type(data.get('instrument_id')) is not str
                or data.get('end_time') - data.get('start_time') != 4
                or any(type(data.get(key)) not in (int,float) or not math.isfinite(data[key])
                       for key in ('heavy_load_reference_lb','elevation_degrees','azimuth_degrees','landing_elevation_m'))):
            raise TransactionalProgressionError('invalid reviewed Throw declaration')
    if type(action) in (ObserveGroupAction,AskAboutPastAction) or (
            type(action) is SpotAction and data.get('group_fully_visible') is True):
        objective_action_data(action)
    if type(action) is SpotAction and data.get('group_fully_visible') is True:
        _capture_belief(data['ledger'],data['actor_id'])
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
    fence=_StagedReadFence(id(encounter),boundary,tuple(pending),events,initial,registered,states,{}, {})
    return capture_observer_context(encounter,boundary,rng_state=rng,_stage=fence)


def enable_transactional_progression(encounter, *, quiescent=False, rng_owner=None):
    from encounter import Encounter
    from atomic_publication import publication_boundary
    if type(encounter) is not Encounter:raise TransactionalProgressionError('native Encounter required')
    if mode_of(encounter)!='legacy':raise TransactionalProgressionError('transactional mode is irreversible and cannot be reconfigured')
    with publication_boundary(encounter,quiescent=quiescent):
        return _enable_transactional_progression_owned(encounter, rng_owner=rng_owner)


def _enable_transactional_progression_owned(encounter, *, rng_owner=None):
    """Select transactional mode inside an already-held publication lease."""
    from encounter import Encounter
    from atomic_publication import publication_owned
    from interval_staging import _rng_input
    if type(encounter) is not Encounter or not publication_owned(encounter):
        raise TransactionalProgressionError('transactional selection requires native publication ownership')
    if mode_of(encounter)!='legacy':
        raise TransactionalProgressionError('transactional mode is irreversible and cannot be reconfigured')
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
    descriptor=ProgressionMode('transactional',id(encounter),role,identity)
    key=id(encounter)
    binding=_Binding(weakref.ref(encounter,lambda ref:_BINDINGS.pop(key,None)),descriptor,rng_owner,threading.Lock())
    _BINDINGS[key]=binding
    try:ed['_transactional_mode']=descriptor
    except BaseException:
        _BINDINGS.pop(key,None);raise
    return descriptor


def step_transactionally(encounter,duration,velocities,velocity_frame,*,adult_member_candidate=None,
                        movement_intent=None,movement_conditions=None):
    from atomic_publication import publication_boundary,publish_interval_candidate
    from interval_staging import _motion
    from encounter import EncounterStep
    assert_not_quarantined(encounter, 'Encounter progression')
    if mode_of(encounter)!='transactional':raise TransactionalProgressionError('explicit transactional selection required')
    if movement_intent is None and movement_conditions is not None:
        raise TransactionalProgressionError('movement conditions require a MovementIntent')
    if movement_intent is not None:
        if velocities is not None:
            raise TransactionalProgressionError('MovementIntent and caller-supplied velocities cannot be combined')
        if duration != 1.0:
            raise TransactionalProgressionError('MovementIntent applies to exactly one native second')
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
        completed=[];motion=None;facing_updates=None;movement_stop_times=None;movement_targets=None;movement_decision_ids=[]
        while encounter.time<end:
            with publication_boundary(encounter,quiescent=True) as ownership:
                # Reentrant entry checks are private control state, not timeline
                # flags; 5C1/5C2 see an actual committed native checkpoint.
                boundary=encounter.last_processed_boundary+1
                context=_all_declarations(encounter,boundary,binding.rng_owner)
                if motion is None:
                    positions={key:context.snapshot.entities[key].position for key in context.snapshot.participant_ids}
                    if movement_intent is not None:
                        from movement_intent import prepare_movement_intent
                        prepared=prepare_movement_intent(
                            encounter,movement_intent,movement_conditions,duration=duration,
                            pre_action_snapshot=context.snapshot)
                        motion={movement_intent.actor_id:prepared.velocity_meters_per_second}
                        facing_updates = ({movement_intent.actor_id: prepared.facing_update}
                                          if prepared.facing_update is not None else {})
                        if prepared.arrival_time_seconds is not None:
                            movement_stop_times = {
                                movement_intent.actor_id: start + prepared.arrival_time_seconds}
                            movement_targets = {movement_intent.actor_id: movement_intent.destination}
                        movement_decision_ids.append(movement_intent.decision_id)
                    else:
                        motion=dict(_motion(positions,velocities,encounter.local_frame,velocity_frame,end-start))
                # The same scope covers validation, staging and publication.
                if mode_of(encounter)!='transactional':raise TransactionalProgressionError('mode changed')
                _ROUTED_OWNERSHIP[id(encounter)]=ownership
                try:
                    candidate=encounter.prepare_interval_candidate(boundary,velocities=motion,
                        facing_updates=facing_updates,
                        movement_stop_times=movement_stop_times, movement_targets=movement_targets,
                        rng_owner=binding.rng_owner,_restore_context=binding.restore_context,
                        adult_member_candidate=adult_member_candidate)
                    receipt=publish_interval_candidate(encounter,candidate,ownership=ownership,rng_owner=binding.rng_owner)
                    completed.extend(receipt.action_ids)
                    # One non-Action realization request belongs to exactly
                    # one interval; later boundaries in a long step are normal.
                    adult_member_candidate=None
                finally:_ROUTED_OWNERSHIP.pop(id(encounter),None)
        return EncounterStep(start,end,tuple(motion),tuple(completed),tuple(movement_decision_ids))
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
