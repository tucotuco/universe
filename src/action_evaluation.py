"""Inactive native Action evaluation boundary (Universe 4 Increment 4).

Capture only at a caller-owned post-movement/pre-action integer fence. Nothing
here advances time, dispatches live resolvers, publishes effects, or commits RNG.
Exact native adapters are deliberate: this is not a Python extension sandbox.
"""
from dataclasses import dataclass, field, fields, replace
import math
import random
from types import MappingProxyType

from action_calculations import (attack_hits, saving_throw, hit_outcome,
    armor_impact, shield_impact, damage_path, check_succeeds, run_outcome,
    defense_succeeds, melee_path_status)
from utils import experience_level, saving_throw_experience_modifier
from spatial.state import CartesianPosition, SpatialState
from spatial.geometry import Sphere, AxisAlignedBox
from spatial.occlusion import VisualOcclusion
from spatial.visibility import trace_sightline, trace_physical_path


class UnsupportedEvaluation(TypeError):
    """No reviewed pure adapter; no extension callback has been invoked."""


class EvaluationIntegrityError(ValueError):
    """Contradictory/corrupt native data, distinct from a gameplay outcome."""


def _timing_adjustment(strategy):
    value = strategy.get('timing', 0)
    if type(value) not in (int, float) or value < 0 or not math.isfinite(value):
        raise EvaluationIntegrityError('invalid native timing strategy')
    return math.floor((-1 + math.sqrt(1 + 8 * value)) / 2)


def freeze(value):
    """Detach data without deepcopy/reduce/serialization extension callbacks."""
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise EvaluationIntegrityError('non-finite evaluation data')
        return value
    if type(value) in (list, tuple):
        return tuple(freeze(x) for x in value)
    if type(value) in (set, frozenset):
        return frozenset(freeze(x) for x in value)
    if type(value) in (dict, MappingProxyType):
        return MappingProxyType({freeze(k): freeze(v) for k, v in value.items()})
    raise UnsupportedEvaluation('opaque nested evaluation data')


def native_data(value, classes):
    if type(value) not in classes:
        raise UnsupportedEvaluation('unreviewed native read adapter')
    data = object.__getattribute__(value, '__dict__')
    if any(callable(x) for x in data.values()):
        raise UnsupportedEvaluation('instance callback override requires a reviewed adapter')
    return data


def position(value):
    if value is None:
        return None
    data = native_data(value, (CartesianPosition,))
    return CartesianPosition(*(freeze(data[k]) for k in ('x', 'y', 'z')))


@dataclass(frozen=True)
class EntityView:
    id: str
    category: str
    hp: float
    obj_type: str
    position: CartesianPosition | None
    geometry: object
    visual_occlusion: object
    data: object
    physical_path_role: str = 'physical_entity'

    def get_position(self):
        return self.position

    def segment_intersection(self, start, end):
        return None if self.geometry is None or self.position is None else self.geometry.segment_interval(start, end, self.position)


@dataclass(frozen=True)
class ActionView:
    id: str
    family: str
    actor_id: str
    target_id: str | None
    instrument_id: str | None
    start: float
    nominal_end: float
    boundary: int
    priority: int
    order: int
    lifecycle: str
    data: object


@dataclass(frozen=True)
class EvaluationSnapshot:
    encounter_id: str
    boundary: int
    difficulty: float
    entities: object
    participant_ids: tuple
    actions: object
    awareness: object
    fatigue: object
    physiology: object
    rng_state: tuple
    schema: str = 'native-action-proposals-v1-inactive'
    practice_inputs: object = None
    objective_inputs: object = None
    omitted_objective_action_ids: tuple = ()
    imported_practice_dependency: object = None
    encounter_map: object = None
    physical_grips: tuple = ()
    grapple_controls: tuple = ()
    object_grips: tuple = ()
    moving_ids: tuple = ()
    motion_velocities_m_s: object = field(default_factory=lambda: MappingProxyType({}))
    pole_weapon_names: frozenset = frozenset()

    def entity(self, identity):
        try:
            return self.entities[identity]
        except KeyError as exc:
            raise EvaluationIntegrityError('unknown Object identity') from exc

    def distance(self, first, second):
        if first not in self.participant_ids or second not in self.participant_ids:
            return None
        a, b = self.entity(first).position, self.entity(second).position
        return None if a is None or b is None else math.dist(a.as_tuple(), b.as_tuple())

    def path(self, first, second):
        distance = self.distance(first, second)
        if distance is None or distance == 0:
            return None
        return trace_sightline(self.entity(first).position, self.entity(second).position,
            ((key, self.entity(key)) for key in self.participant_ids), exclude_ids=(first, second))

    def physical_path(self, first, second):
        distance = self.distance(first, second)
        if distance is None or distance == 0:
            return None
        return trace_physical_path(self.entity(first).position, self.entity(second).position,
            ((key, entity) for key in self.participant_ids
             for entity in (self.entity(key),)
             if entity.data.get('parent_container_id') is None),
            exclude_ids=(first, second))

    def melee_status(self, action):
        from arena_hex_map import layout_from_encounter_map
        from action_calculations import melee_hex_path_status
        layout = layout_from_encounter_map(self.encounter_map)
        if layout is not None:
            source = self.entity(action.actor_id).position
            target = self.entity(action.target_id).position
            return melee_hex_path_status(source, target, action.data['reach'],
                self.physical_path(action.actor_id, action.target_id), layout,
                self.entity(action.actor_id).data.get('hex_facing'))
        distance = self.distance(action.actor_id, action.target_id)
        path = self.physical_path(action.actor_id, action.target_id) if distance is not None and 0 < distance <= action.data['reach'] else None
        return melee_path_status(distance, action.data['reach'], path)


def capture_snapshot(encounter, boundary, *, rng_state=None, _objective=False, _stage=None,
                     _restore_context=None, _decision_preflight=False):
    """Freeze the current state at an explicit, non-dispatching evaluation fence.

    Caller must first advance physical state to this boundary without resolving
    Actions. This inactive API never supplies that transaction coordinator.
    """
    from action import Action
    from activities import RunAction, SpotAction
    from melee_combat import MeleeStrike
    from melee_defense import MeleeDefense
    from encounter import Encounter
    from universe import Universe
    from being import BeingInstance, BeingDefinition
    from object import ObjectInstance, ObjectDefinition
    from weapon import WeaponInstance, WeaponDefinition
    from armor import ArmorInstance, ArmorDefinition
    from skill import Skills
    from states import States
    from abilities import Abilities
    from strategy import Strategy
    from exertion import Exertion
    from physical_fatigue import PhysicalFatigueState
    from encounter_fatigue_bridge import FrozenFatigueFrame
    from physiology_registry import PhysiologyRegistry
    from statistical_group import StatisticalGroup
    ed = native_data(encounter, (Encounter,))
    if _stage is not None:
        from interval_staging import _StagedReadFence
        if type(_stage) is not _StagedReadFence or _stage.encounter_identity != id(encounter) or _stage.boundary != boundary:
            raise EvaluationIntegrityError('invalid private interval read fence')
        ed = dict(ed, time=boundary, pending_action_list=_stage.pending_ids)
    elif _decision_preflight:
        if (type(_decision_preflight) is not bool or not _decision_preflight
                or ed['active_boundary'] is not None
                or ed['time'] != ed['last_processed_boundary']
                or boundary != ed['last_processed_boundary'] + 1):
            raise EvaluationIntegrityError('invalid next-boundary decision preflight')
        ed = dict(ed, time=boundary)
    if (type(boundary) is not int or boundary < 1 or ed['time'] != boundary
            or ed['_dispatching'] or ed.get('boundary_fault') is not None
            or ed['last_processed_boundary'] >= boundary):
        raise EvaluationIntegrityError('capture requires a current positive integer pre-action fence')
    world = ed['universe']
    native_data(world, (Universe,))
    # Native registry lookup only; no Action getter/universe lookup escapes.
    from object import ObjectRegistry
    from library import Library
    from weapon import WeaponDictionary
    wd = native_data(world, (Universe,))
    if _stage is not None:
        wd = dict(wd, event_history=_stage.events)
    registry = native_data(wd['object_registry'], (ObjectRegistry,))
    objects = registry['object_instances']
    if type(objects) is not dict or type(wd['event_history']) not in ((dict,) if _stage is None else (dict, MappingProxyType)):
        raise UnsupportedEvaluation('opaque registry mapping')
    weapon_dictionary = native_data(native_data(wd['library'], (Library,))['weapon_dictionary'], (WeaponDictionary,))
    if type(weapon_dictionary['objects']) is not dict:
        raise UnsupportedEvaluation('opaque weapon definitions')
    weapon_names = frozenset(freeze(tuple(weapon_dictionary['objects'])))
    shield_names = freeze(weapon_dictionary['object_categories']).get('Shields', ())
    participants = tuple(dict.fromkeys(freeze(ed['being_list']) + freeze(ed['non_being_object_list'])))
    actions = {}
    from activities import ThrowAction, PickUpAction, ReadyWeaponAction, ReadyPreparationAction, DelayAction
    families = {Action: 'combat', MeleeStrike: 'melee', MeleeDefense: 'defense',
                RunAction: 'run', SpotAction: 'spot', ThrowAction: 'throw',
                PickUpAction: 'pickup', ReadyWeaponAction: 'ready_weapon',
                ReadyPreparationAction: 'ready_preparation', DelayAction: 'delay'}
    objective_actions = {}
    if _objective:
        from group_observation import ObserveGroupAction
        from history_conversation import AskAboutPastAction
        from statistical_group import StatisticalGroup
        from objective_reality import objective_action_data
        families.update({ObserveGroupAction: 'observe_group', AskAboutPastAction: 'history_request'})
    pending_ids = freeze(ed['pending_action_list'])
    ids = tuple(dict.fromkeys(pending_ids + freeze(ed['cancelled_action_list'])))
    for order, aid in enumerate(ids):
        action = wd['event_history'].get(aid)
        if type(action) not in families:
            raise UnsupportedEvaluation('Action family requires a pure adapter (Reality/evidence staging deferred)')
        action_data = object.__getattribute__(action, '__dict__')
        target = objects.get(action_data.get('target_id'))
        spot_group = (_objective and type(action) is SpotAction
                      and type(target) is StatisticalGroup
                      and action_data.get('group_fully_visible') is True)
        if _objective and (type(action) in (ObserveGroupAction, AskAboutPastAction) or spot_group):
            ad, objective = objective_action_data(action)
            objective_actions[aid] = objective
        else:
            ad = native_data(action, tuple(families))
        if _stage is not None:
            ad = dict(ad, **_stage.initialization.get(aid, {}))
        if type(ad['id']) is not str or ad['id'] != aid:
            raise EvaluationIntegrityError('Action identity mismatch')
        if ad['event_type'] not in (('swing', 'thrust', 'touch', 'feint', 'coup de grace', 'strike object', 'break weapon', 'disarm', 'grab', 'grab object', 'wrest', 'hold', 'break hold', 'release grip', 'grapple', 'grapple escape', 'takedown','reverse','pin','trip','bull rush','overrun','end-run', 'parry', 'dodge', 'block', 'yield', 'run', 'spot', 'throw', 'pick up', 'ready weapon', 'ready object', 'delay') + (('observe_group', 'ask_about_past') if _objective else ())):
            raise UnsupportedEvaluation('unsupported base Action activity')
        if aid in ed['cancelled_action_list'] and ad.get('_atomic_acknowledged_boundary') is not None:
            ack = ad['_atomic_acknowledged_boundary']
            from observer_proposals import LifecycleEffect
            from atomic_publication import PublishedInterval
            life, outcome = ad.get('_atomic_lifecycle'), ad.get('resolution')
            deadline = ad['end_time']
            history = ed.get('_atomic_interval_history', ())
            if (type(ack) is not int or ack < 1 or ack > ed['last_processed_boundary']
                    or type(deadline) not in (int,float) or not math.isfinite(deadline) or math.ceil(deadline) != ack
                    or type(life) is not LifecycleEffect or life.action_id != aid or life.source_action_id != aid
                    or life.boundary != ack or life.status != 'cancelled'
                    or type(outcome) is not ActionProposal or outcome.action_id != aid or outcome.outcome != 'interrupted'
                    or type(history) is not list or not any(type(record) is PublishedInterval and record.committed
                        and record.boundary == ack and aid in record.action_ids for record in history)):
                raise EvaluationIntegrityError('invalid or unbacked committed cancellation acknowledgement')
            continue
        if any(ad.get(k) is not None for k in ('resolution', 'combat_result', 'result')):
            raise EvaluationIntegrityError('Action already has a successful live result')
        book = object.__getattribute__(encounter, '__dict__').get('_choice_book')
        paused = bool(book is not None and book.is_paused(aid))
        # A newly started Action's interval initialization is authoritative
        # inside this detached common-boundary snapshot. The live ChoiceBook
        # deadline is not published until interval commit and can still show
        # the constructor's placeholder deadline (notably for timed Yield).
        staged_start = (_stage is not None and aid in _stage.initialization
                        and 'end_time' in _stage.initialization[aid])
        end = (ad['end_time'] if book is None or staged_start
               else book.effective_end(action))
        if type(end) not in (int, float) or not math.isfinite(end):
            raise EvaluationIntegrityError('invalid Action deadline')
        cancelled = aid in ed['cancelled_action_list']
        if not cancelled and not paused and math.ceil(end) < boundary:
            raise EvaluationIntegrityError('stale pending Action')
        strategy = freeze(native_data(ad['strategy'], (Strategy,)))
        family = ('end_run' if type(action) is Action and ad['event_type']=='end-run' else
                  'ready_preparation' if type(action) is Action and ad['event_type']=='ready object' else
                  'delay' if type(action) is Action and ad['event_type']=='delay' else
                  'disarm' if type(action) is Action and ad['event_type']=='disarm' else
                  'object_strike' if type(action) is Action and ad['event_type'] in ('strike object','break weapon') else
                  'grappling' if type(action) is Action and ad['event_type'] in ('grab','grab object','wrest','hold','break hold','release grip','grapple','grapple escape','takedown','reverse','pin','trip','bull rush','overrun') else
                  'melee' if type(action) is Action and ad['event_type'] in ('feint', 'coup de grace')
                  else families[type(action)])
        multiple_action_priority = None
        book = object.__getattribute__(encounter, '__dict__').get('_choice_book')
        if book is not None:
            for record in book._choices.values():
                for member in record.members:
                    if member.action.id == aid:
                        multiple_action_priority = member.priority_penalty
                        break
                if multiple_action_priority is not None:
                    break
        selected = {'event_type': ad['event_type'], 'strategy': strategy}
        if multiple_action_priority is not None:
            selected['multiple_action_priority'] = multiple_action_priority
        for key in ('reach','motion','feint_motion','feint_source_action_id','coup_motion','object_motion','break_motion','break_weapon_id','disarm_weapon_id','disarm_motion','ready_motion','readying_seconds','kind','target_action_id','ready_at','threat_at_schedule',
                    'minimum_distance','practice_experience','max_distance','spotting_conditions','declared_roll','episode_time','topic','experience_policy','canceled_at','cancellation_reason','parry_motion','prepared_defense_action_id','strategy_pool','grab_hand','touch_action_id','touch_willing','grip_id','grapple_id','grapple_position','trip_source_action_id','trip_defender_ability','trip_size_categories','holder_id','holder_hand','object_grip_id','charge','charge_continuation_source_id','bull_rush_target_willing','end_run_exit_position','end_run_movement_conditions','end_run_occupant_willing','end_run_rate','end_run_origin_position','end_run_target_position','end_run_origin_cell','end_run_target_cell','end_run_phase_result'):
            if key in ad:
                selected[key] = (position(ad[key]) if key in (
                    'end_run_exit_position','end_run_origin_position',
                    'end_run_target_position') else freeze(ad[key]))
        if ('bull_rush_target_willing' in selected
                and (ad['event_type'] != 'bull rush'
                     or type(selected['bull_rush_target_willing']) is not bool)):
            raise EvaluationIntegrityError('Bull Rush willingness must be an explicit native boolean scenario fact')
        if type(action) is Action and ad['event_type'] == 'grab':
            from physical_contact import successful_touch
            selected['contact_verified'] = successful_touch(encounter,ad.get('touch_action_id'),
                ad.get('actor_id'),ad.get('target_id'))
        if type(action) is Action and ad['event_type'] == 'trip':
            from physical_contact import trip_contact_kind
            selected['trip_contact_kind'] = trip_contact_kind(encounter,
                ad.get('trip_source_action_id'),ad.get('actor_id'),ad.get('target_id'))
        prepared_id = ad.get('prepared_defense_action_id')
        if prepared_id is not None:
            source = wd['event_history'].get(prepared_id)
            if type(source) is not MeleeDefense:
                raise EvaluationIntegrityError('retained defense source is not a native MeleeDefense Action')
            source_data = native_data(source, (MeleeDefense,))
            source_resolution = source_data.get('resolution')
            if (source_data['id'] not in ed['finished_action_list']
                    or type(source_resolution) is not ActionProposal
                    or source_resolution.outcome != 'ready'
                    or source_data.get('target_action_id') is not None
                    or source_data.get('actor_id') != ad.get('actor_id')
                    or source_data.get('kind') != ad.get('kind')
                    or type(source_data.get('ready_at')) not in (int, float)
                    or source_data['ready_at'] > boundary):
                raise EvaluationIntegrityError('retained defense source is not ready for this boundary')
            if any(type(other) is MeleeDefense and
                   object.__getattribute__(other, '__dict__').get('prepared_defense_action_id') == prepared_id
                   for other_id, other in wd['event_history'].items() if other_id != aid):
                raise EvaluationIntegrityError('one retained defense cannot be committed more than once')
            selected['prepared_defense'] = freeze({
                'id': source_data['id'], 'kind': source_data['kind'],
                'actor_id': source_data['actor_id'],
                'instrument_id': source_data.get('instrument_id'),
                'ready_at': source_data['ready_at'],
                'strategy': native_data(source_data['strategy'], (Strategy,)),
                'parry_motion': source_data.get('parry_motion'),
                'strategy_pool': source_data.get('strategy_pool'),
            })
        if type(action) is SpotAction:
            selected['group_fully_visible'] = freeze(ad['group_fully_visible'])
        if type(action) is RunAction:
            selected['start_position'] = position(ad['start_position'])
            selected['started'] = ad.get('_activity_started', False)
        if type(action) is Action and ad.get('event_type') in ('bull rush','overrun'):
            source_id = ad.get('charge_continuation_source_id')
            if source_id is not None:
                from melee_combat import MeleeStrike
                source = wd['event_history'].get(source_id)
                source_data = native_data(source, (MeleeStrike, Action)) if type(source) in (MeleeStrike, Action) else None
                resolution = None if source_data is None else source_data.get('resolution')
                common = (source_data is not None
                    and source_data.get('actor_id') == ad.get('actor_id')
                    and source_data.get('target_id') == ad.get('target_id')
                    and source_data.get('end_time') == ad.get('start_time')
                    and type(resolution) is ActionProposal)
                if (type(source) is MeleeStrike and common
                        and source_data.get('charge') is True
                        and resolution.outcome in ('normal','critical')):
                    selected['charge_continuation'] = True
                elif (ad.get('event_type') == 'overrun' and type(source) is Action
                        and common and source_data.get('event_type') == 'bull rush'
                        and resolution.outcome in ('success','success_pending_displacement')):
                    selected['bull_rush_continuation'] = True
                elif (ad.get('event_type') == 'bull rush' and type(source) is Action
                        and common and source_data.get('event_type') == 'bull rush'
                        and resolution.outcome == 'success_pending_displacement'):
                    selected['bull_rush_continuation'] = True
                else:
                    raise EvaluationIntegrityError('continuation lacks its immediately successful Charge or Bull Rush receipt')
        if type(action) is MeleeDefense and action.kind == 'yield':
            selected['start_position'] = position(ad.get('start_position'))
            selected['target_position'] = position(ad.get('target_position'))
        if type(action) is ThrowAction:
            for key in ('heavy_load_reference_lb','elevation_degrees','azimuth_degrees','landing_elevation_m'):
                selected[key] = freeze(ad[key])
        if type(action) is PickUpAction:
            selected['map_width_cells'] = freeze(ad['map_width_cells'])
            selected['map_height_cells'] = freeze(ad['map_height_cells'])
        if type(action) is ReadyWeaponAction:
            selected['hand'] = freeze(ad['hand'])
        if type(action) is ReadyPreparationAction:
            selected['ready_motion'] = freeze(ad['ready_motion'])
            selected['readying_seconds'] = freeze(ad['readying_seconds'])
        if not cancelled:
            # Reuse Increment 3 ownership and declaration validation, after the
            # exact-type/callback preflight above. No scheduling hook executes.
            from encounter import BoundaryInvariantError
            try:
                if _stage is None:
                    encounter._choice_book.assert_registered(action)
                elif aid not in _stage.registered or _stage.events[aid] is not action:
                    raise EvaluationIntegrityError('unregistered staged Action')
            except BoundaryInvariantError as exc:
                raise EvaluationIntegrityError(str(exc)) from exc
        # Position is an immutable native value; no arbitrary object survives.
        if type(action) is Action and ad['event_type'] == 'feint':
            if (ad.get('feint_motion') not in ('swing', 'thrust')
                    or ad.get('instrument_id') is None
                    or type(ad.get('reach')) not in (int, float)
                    or not math.isfinite(ad['reach']) or ad['reach'] <= 0):
                raise EvaluationIntegrityError('native Feint declaration is incomplete')
        if type(action) is Action and ad['event_type'] == 'coup de grace':
            if (ad.get('coup_motion') not in ('swing', 'thrust')
                    or ad.get('instrument_id') is None
                    or type(ad.get('reach')) not in (int, float)
                    or not math.isfinite(ad['reach']) or ad['reach'] <= 0):
                raise EvaluationIntegrityError('native Coup de grace declaration is incomplete')
        feint_source = ad.get('feint_source_action_id')
        if type(action) is MeleeStrike and feint_source is not None:
            source = wd['event_history'].get(feint_source)
            if (type(source) is not Action or source.event_type != 'feint'
                    or source.actor_id != ad.get('actor_id')
                    or source.target_id != ad.get('target_id')
                    or source.id not in ed['finished_action_list']
                    or type(source.resolution) is not ActionProposal
                    or source.resolution.outcome != 'success'):
                raise EvaluationIntegrityError('MeleeStrike references an ineligible Feint result')
        actions[aid] = ActionView(aid, family, freeze(ad['actor_id']),
            freeze(ad['target_id']), freeze(ad['instrument_id']), freeze(ad['start_time']),
            end, math.ceil(end), -1 if type(action) is MeleeDefense else 0, order,
            'cancelled' if cancelled else ('paused' if paused else 'pending'), MappingProxyType(selected))
    object_classes = (BeingInstance, ObjectInstance, WeaponInstance, ArmorInstance,
                      StatisticalGroup)
    entities = {}
    wanted = set(participants)
    for a in actions.values():
        wanted.update(x for x in (a.actor_id, a.target_id, a.instrument_id) if x is not None)
    # Pull represented Being inventory and container contents into the same
    # pre-action snapshot used by the interval movement and Action phases.
    inventory_roots = set()
    for key in tuple(wanted):
        if key not in objects:
            raise EvaluationIntegrityError('unknown Object identity')
        obj = objects[key]
        od = native_data(obj, object_classes)
        if type(obj) is BeingInstance:
            current = native_data(od['current'], (BeingDefinition,))
            inventory = (tuple(freeze(od.get('possessions', ())))
                + tuple(freeze(od.get('weapons', ())))
                + tuple(x for x in freeze(current['body_parts']).values() if x is not None)
                + (() if current['armor_id'] is None else (freeze(current['armor_id']),)))
            wanted.update(inventory)
            inventory_roots.update(inventory)
    while inventory_roots:
        parent_id = inventory_roots.pop()
        for child_id, child in objects.items():
            child_data = native_data(child, object_classes)
            if child_data.get('parent_container_id') == parent_id and child_id not in wanted:
                wanted.add(child_id)
                inventory_roots.add(child_id)
    # Complete transitive type preflight before reading any held item metadata.
    for key in wanted:
        if key not in objects:
            raise EvaluationIntegrityError('unknown transitive Object identity')
        item = native_data(objects[key], object_classes)
        current_data = native_data(item['current'], (BeingDefinition, ObjectDefinition, WeaponDefinition, ArmorDefinition))
        if type(current_data['obj_type']) is not str:
            raise EvaluationIntegrityError('Object type must be a native name')
    object_types = {key: object.__getattribute__(
        object.__getattribute__(objects[key], '__dict__')['current'], '__dict__')['obj_type']
        for key in wanted}
    for key in sorted(wanted):
        if key not in objects:
            raise EvaluationIntegrityError('unknown Object identity')
        obj = objects[key]
        od = native_data(obj, object_classes)
        if od['id'] != key:
            raise EvaluationIntegrityError('Object identity mismatch')
        cd = native_data(od['current'], (BeingDefinition, ObjectDefinition, WeaponDefinition, ArmorDefinition))
        spatial = od['spatial_state']
        pos = None if spatial is None else position(native_data(spatial, (SpatialState,))['position'])
        if _stage is not None and key in _stage.positions:
            pos = _stage.positions[key]
        shape = od['geometry']
        if shape is not None:
            gd = native_data(shape, (Sphere, AxisAlignedBox))
            shape = type(shape)(**freeze(gd))
        optics = od['visual_occlusion']
        if optics is not None:
            optics = VisualOcclusion(**freeze(native_data(optics, (VisualOcclusion,))))
        data = {'hardness': freeze(cd['hardness']), 'weight': freeze(cd.get('weight')),
                'parent_container_id': freeze(od.get('parent_container_id')),
                'discovery_dc': freeze(cd.get('discovery_dc')),
                'name': freeze(od.get('name'))}
        category = 'object'
        if type(obj) is BeingInstance:
            category = 'being'
            skills = native_data(cd['skills'], (Skills,))
            abilities = freeze(native_data(cd['abilities'], (Abilities,))['abilities'])
            data.update(skills=freeze(skills['skills']), weapon_skills=freeze(skills['weapon_skills']),
                race=freeze(cd.get('race')),
                abilities=abilities, states=freeze(native_data(cd['states'], (States,))['states']),
                posture=freeze(obj.get_posture()),
                size_category=freeze(object.__getattribute__(obj, '__dict__').get('size_category')),
                experience=freeze(cd['experience']), armor_id=freeze(cd['armor_id']),
                height=freeze(cd.get('height')), length=freeze(cd.get('length')),
                body_parts=freeze(cd['body_parts']), strategy=freeze(native_data(od['strategy'], (Strategy,))),
                fatigue_level=freeze(od['fatigue_level']),
                exertion=freeze(native_data(od['exertion'], (Exertion,))),
                fatigue_adjustments=freeze(od['exertion'].fatigue_levels))
            armor_penalty = 0
            armor_id = cd.get('armor_id')
            if armor_id is not None:
                armor_obj = objects.get(armor_id)
                if type(armor_obj) is not ArmorInstance:
                    raise EvaluationIntegrityError('Grapple armor identity is not native armor')
                armor_current = native_data(armor_obj.current, (ArmorDefinition,))
                armor_penalty = armor_current['armor_check_penalty']
            data['armor_check_penalty'] = freeze(armor_penalty)
            data['free_hands'] = tuple(slot for slot, held in cd['body_parts'].items()
                if slot in ('left hand','right hand') and held is None)
            facing = (_stage.facings[key] if _stage is not None and key in _stage.facings
                      else od.get('hex_facing'))
            data['hex_facing'] = freeze(facing)
            data['possessions'] = freeze(od.get('possessions', ()))
            data['weapons'] = freeze(od.get('weapons', ()))
            # Preserve category membership and insertion order, including RNG choice.
            shields = shield_names
            data['held'] = tuple(v for v in data['body_parts'].values() if v is not None and
                v in objects and object_types[v] in weapon_names)
            data['shields'] = tuple(v for v in data['body_parts'].values() if v is not None and
                v in objects and object_types[v] in shields)
            freeze(native_data(od['physical_fatigue'], (PhysicalFatigueState,)))
            freeze(od['physiology_id'])
        elif type(obj) is WeaponInstance:
            category = 'weapon'
            from weapon import (NATIVE_DRAW_LOCATION_TAG, DRAWABLE_WORN_SHEATH,
                                native_ready_preparation)
            tags = cd.get('tags')
            if type(tags) is not dict:
                raise EvaluationIntegrityError('Weapon tags must be a native dictionary')
            location = tags.get(NATIVE_DRAW_LOCATION_TAG)
            if location is not None and (type(location) is not dict
                    or set(location) != {'kind', 'owner_id'}
                    or location.get('kind') != DRAWABLE_WORN_SHEATH
                    or type(location.get('owner_id')) is not str
                    or not location['owner_id']):
                raise EvaluationIntegrityError('native Weapon draw-location record is malformed')
            data.update(attacks=freeze(cd['attacks']), size=freeze(cd['weapon_size']),
                        original_type=freeze(native_data(od['original'], (WeaponDefinition,))['obj_type']),
                        draw_location=freeze(location),
                        ready_preparation=freeze(native_ready_preparation(obj)))
        elif type(obj) is ArmorInstance:
            category = 'armor'
            data['defenses'] = freeze(cd['defenses'])
        elif type(obj) is ObjectInstance:
            # The native Object Spot adapter may report only whether this
            # Object's already modeled point-mass flight is active at the
            # boundary. Position is captured through the common staged frame
            # above; no release cause or future trajectory is exposed here.
            data['projectile_status'] = None
            flight = object.__getattribute__(obj, '__dict__').get('_projectile_flight')
            if flight is not None:
                from throwing import ProjectileFlight
                if type(flight) is not ProjectileFlight:
                    raise UnsupportedEvaluation('unreviewed Object flight descriptor in Spot snapshot')
                data['projectile_status'] = (
                    'landed' if flight.impact_time <= boundary else 'in_flight')
        spatial_role = ('aggregate_extent' if type(obj) is StatisticalGroup
                        else 'physical_entity')
        entities[key] = EntityView(key, category, freeze(cd['hit_points']), freeze(cd['obj_type']),
                                   pos, shape, optics, MappingProxyType(data), spatial_role)
    # Reuse the existing Q/B/profile equations; detach the resulting frame too.
    physiology_registry = ed['_physiology_registry']
    if physiology_registry is not None:
        registry_data = native_data(physiology_registry, (PhysiologyRegistry,))
        from physiology_registry import PhysiologyDefinition
        if type(registry_data['_definitions']) is not dict:
            raise UnsupportedEvaluation('opaque physiology definitions')
        for definition in registry_data['_definitions'].values():
            freeze(native_data(definition, (PhysiologyDefinition,)))
    frame = FrozenFatigueFrame((objects[x] for x in ed['being_list']), registry=physiology_registry)
    profiles = {}
    if physiology_registry is not None:
        for key in ed['being_list']:
            profiles[key] = {}
            for mode in ('ordinary', 'running'):
                resolved = frame.physiology(key, mode=mode)
                profiles[key][mode] = {f.name: (freeze({p.name: getattr(resolved.profile, p.name) for p in fields(resolved.profile)})
                    if f.name == 'profile' else freeze(getattr(resolved, f.name))) for f in fields(resolved)}
    from frozen_practice import capture_practice_inputs
    imported_dependency = None
    if _restore_context is None:
        practice_inputs = capture_practice_inputs(world, objects, entities)
    else:
        from checkpoint_restore_dependencies import _PreparedContinuationContext
        from frozen_practice import (_capture_prepared_practice_inputs,
            _validate_imported_prefix)
        if type(_restore_context) is not _PreparedContinuationContext:
            raise EvaluationIntegrityError('unsupported trusted-local practice context')
        _validate_imported_prefix(_restore_context.imported_prefix)
        imported_dependency = _restore_context.evaluation_binding()
        practice_ids = tuple(key for key, view in entities.items()
                             if view.category == 'being')
        practice_inputs = _capture_prepared_practice_inputs(world, objects,
            practice_ids, _restore_context.imported_prefix)
    objective_inputs = None
    if _objective:
        from objective_reality import capture_objective_inputs
        objective_inputs = capture_objective_inputs(objects, objective_actions, participants)
    from physical_contact import active_contact_state, active_object_grip_state
    grips, controls = active_contact_state(encounter)
    object_grips=active_object_grip_state(encounter)
    object_grip_hands={(row[2],row[4]) for row in object_grips}
    for key in tuple(entities):
        entity = entities[key]
        if entity.category != 'being':
            continue
        occupied = tuple(row[3] for row in grips if row[1] == key and row[3] is not None)
        if occupied:
            data = dict(entity.data)
            data['free_hands'] = tuple(hand for hand in data.get('free_hands', ())
                                       if hand not in occupied)
            entities[key] = replace(entity, data=MappingProxyType(data))
    for key,entity in tuple(entities.items()):
        if entity.category=='being' and any(owner_id==key for owner_id,_hand in object_grip_hands):
            data=dict(entity.data)
            data['free_hands']=tuple(hand for hand in data.get('free_hands',())
                if (key,hand) not in object_grip_hands)
            entities[key]=replace(entity,data=MappingProxyType(data))
    moving_ids = set()
    if _stage is not None:
        for key, position_value in _stage.positions.items():
            if key not in objects or type(objects[key]) is not BeingInstance:
                continue
            spatial = object.__getattribute__(objects[key], '__dict__').get('spatial_state')
            prior_position = None if spatial is None else spatial.position
            if position_value != prior_position:
                moving_ids.add(key)
    for row in actions.values():
        if (row.lifecycle == 'pending'
                and row.start <= boundary <= row.nominal_end
                and (row.family == 'run' or row.data.get('event_type')
                     in ('trip', 'takedown', 'reverse', 'pin'))):
            moving_ids.add(row.actor_id)
            if row.data.get('event_type') in ('trip', 'takedown', 'reverse', 'pin'):
                moving_ids.add(row.target_id)
    snapshot = EvaluationSnapshot(ed['id'], boundary, freeze(ed['difficulty_class']),
        MappingProxyType(entities), participants, MappingProxyType(actions), freeze(ed['awareness']),
        freeze(frame.to_dict()), freeze(profiles), freeze(random.getstate() if rng_state is None else rng_state),
        practice_inputs=practice_inputs, objective_inputs=objective_inputs,
        imported_practice_dependency=imported_dependency,
        encounter_map=freeze(ed.get('map')), physical_grips=grips,
        grapple_controls=controls, object_grips=object_grips,
        moving_ids=tuple(sorted(moving_ids)),
        motion_velocities_m_s=MappingProxyType({} if _stage is None else
            {key: freeze(value) for key,value in _stage.motion_velocities_m_s.items()}),
        pole_weapon_names=frozenset(
            tuple(weapon_dictionary['object_categories'].get('Spears', ()))
            + tuple(weapon_dictionary['object_categories'].get('Lances', ()))))
    # Validate identities/defense graph before any provisional draw.
    for a in actions.values():
        if a.family in ('combat', 'melee') and snapshot.entity(a.target_id).category != 'being':
            raise UnsupportedEvaluation('non-Being combat target lacks a native saving-throw contract')
        if (a.family == 'object_strike' and a.data['event_type'] == 'strike object'
                and snapshot.entity(a.target_id).category == 'being'):
            raise EvaluationIntegrityError('Strike an object requires an Object target')
        if (a.family == 'object_strike' and a.data['event_type'] == 'break weapon'
                and snapshot.entity(a.target_id).category != 'being'):
            raise EvaluationIntegrityError('Break weapon requires its aware Being opponent')
        if snapshot.entity(a.actor_id).category != 'being':
            raise EvaluationIntegrityError('Action actor must be a Being')
        for key in (a.target_id, a.instrument_id):
            if key is not None:
                snapshot.entity(key)
        if (a.family == 'defense' and a.data['target_action_id'] is not None
                and a.data['target_action_id'] not in actions):
            raise EvaluationIntegrityError('missing designated strike')
    return snapshot


@dataclass(frozen=True)
class DamageEffect:
    source_action_id: str
    target_id: str
    amount: float
    component: str  # body, critical_bypass, shield, armor


@dataclass(frozen=True)
class FatalEffect:
    source_action_id: str
    target_id: str


@dataclass(frozen=True)
class ProtectionEffect:
    source_action_id: str
    target_id: str
    layer: str
    incoming: float
    passed: float
    intercepted: bool


@dataclass(frozen=True)
class PracticeEffect:
    source_action_id: str
    target_id: str
    skill: str
    experience: int


@dataclass(frozen=True)
class AwarenessEffect:
    source_action_id: str
    target_id: str
    observed_id: str
    distance: float
    max_distance: float | None
    basis: str = 'spot_check_geometric_path'


@dataclass(frozen=True)
class DefenseEffect:
    source_action_id: str
    strike_id: str
    kind: str
    eligible: bool
    success: bool


@dataclass(frozen=True)
class ProjectileReleaseEffect:
    source_action_id: str
    target_id: str
    release_time: float
    release_position: tuple
    velocity_m_s: tuple
    impact_time: float
    landing_position: tuple
    landing_elevation_m: float


@dataclass(frozen=True)
class PickupEffect:
    """One same-identity Object custody transfer caused by a PickUpAction."""
    source_action_id: str
    target_id: str  # acquiring Being, as the Target-owned recipient
    object_id: str


@dataclass(frozen=True)
class ReadyWeaponEffect:
    """Draw a carried weapon into an explicitly selected native hand."""
    source_action_id: str
    target_id: str  # acting Being
    object_id: str
    hand: str


@dataclass(frozen=True)
class ReadyPreparationEffect:
    """Persist motion-specific Ready preparation on the native Weapon Object."""
    source_action_id: str
    target_id: str
    object_id: str
    motion: str
    readying_seconds: int
    pole_set: bool = False


@dataclass(frozen=True)
class ReadyConsumptionEffect:
    """Consume prior Ready preparation when an Action uses that Object."""
    source_action_id: str
    target_id: str
    object_id: str
    ready_action_id: str


@dataclass(frozen=True)
class DelayDefenseEffect:
    """Carry the selected defense level into the Being's committed waiting state."""
    source_action_id: str
    target_id: str
    defense: int


@dataclass(frozen=True)
class DropObjectEffect:
    """Release an exact native Object to an explicitly resolved ground point."""
    source_action_id: str
    target_id: str
    owner_id: str
    position: tuple


@dataclass(frozen=True)
class GrappleStateEffect:
    """A Target-owned, receipt-backed physical grip or Grapple-control transition."""
    source_action_id: str
    target_id: str
    actor_id: str
    state_id: str
    kind: str
    operation: str
    hand: str | None
    next_check: int | None
    position: str | None = None


@dataclass(frozen=True)
class PositionEffect:
    """Receipt-backed exact position change from an adopted maneuver result."""
    source_action_id: str
    target_id: str
    position: tuple


@dataclass(frozen=True)
class ObjectGripEffect:
    """Typed, Target-owned receipt for an Object Grip or same-ID Wrest transfer."""
    source_action_id: str
    target_id: str
    actor_id: str
    holder_id: str
    state_id: str
    operation: str
    actor_hand: str
    holder_hand: str


@dataclass(frozen=True)
class ActionProposal:
    action_id: str
    actor_id: str
    target_ids: tuple
    outcome: str
    effects: tuple = ()
    defenses: tuple = ()
    metadata: tuple = ()


@dataclass(frozen=True)
class RandomDraw:
    action_id: str
    purpose: str
    sides: int
    value: int


@dataclass(frozen=True, order=True)
class EffectIdentity:
    """Stable batch/source/channel/slot identity, allocated before reduction."""
    encounter_id: str
    boundary: int
    source_action_id: str
    channel: str
    slot: int


@dataclass(frozen=True)
class IdentifiedEffect:
    identity: EffectIdentity
    effect: object


@dataclass(frozen=True)
class EvaluationResult:
    proposals: tuple
    trace: tuple
    provisional_rng_state: tuple
    # Exact transient frozen read boundary, never a live Encounter reference.
    snapshot: EvaluationSnapshot | None = field(default=None, repr=False, compare=False)
    identified_effects: tuple = ()
    observer_context: object = field(default=None, repr=False, compare=False)


def bind_evaluation_result(snapshot, proposals, trace, provisional_rng_state):
    """Package already-calculated native proposals, without evaluating/reducing.

    This is an internal provenance envelope, not authentication of arbitrary
    Python producers. The candidate reconciler validates complete coverage and
    typed records. Mirrored strike defense dependencies are references, not new
    effects; only the designated defense owns its defense record.
    """
    if type(snapshot) is not EvaluationSnapshot or type(proposals) is not tuple:
        raise EvaluationIntegrityError('native snapshot and proposal tuple required')
    identified = []
    for proposal in proposals:
        if (type(proposal) is not ActionProposal or type(proposal.action_id) is not str
                or type(proposal.effects) is not tuple or type(proposal.defenses) is not tuple):
            raise UnsupportedEvaluation('opaque proposal envelope')
        for slot, effect in enumerate(proposal.effects):
            identified.append(IdentifiedEffect(EffectIdentity(snapshot.encounter_id,
                snapshot.boundary, proposal.action_id, 'effect', slot), effect))
        for slot, effect in enumerate(proposal.defenses):
            if type(effect) is DefenseEffect and type(effect.source_action_id) is not str:
                raise EvaluationIntegrityError('opaque defense source identity')
            if type(effect) is DefenseEffect and effect.source_action_id == proposal.action_id:
                identified.append(IdentifiedEffect(EffectIdentity(snapshot.encounter_id,
                    snapshot.boundary, proposal.action_id, 'defense', slot), effect))
    return EvaluationResult(proposals, trace, provisional_rng_state, snapshot, tuple(identified))


class _ProvisionalRandom:
    def __init__(self, state):
        self.rng = random.Random()
        self.rng.setstate(state)
        self.trace = []
        self.action_id = None

    def roll(self, dice):
        sides = int(dice.removeprefix('1d').split('+')[0])
        value = self.rng.randint(1, sides)
        self.trace.append(RandomDraw(self.action_id, dice, sides, value))
        return value

    def roll_probability(self, probability, purpose):
        if type(probability) not in (int,float) or not 0 <= probability <= 1:
            raise EvaluationIntegrityError('invalid probability for native grip release')
        value = self.rng.getrandbits(53)
        self.trace.append(RandomDraw(self.action_id, purpose, 2**53, value))
        return value < int(probability * (2**53))

    def choose_shield(self, shields):
        if not shields:
            return None
        index = self.rng.choice(range(len(shields)))
        self.trace.append(RandomDraw(self.action_id, 'shield_choice_index', len(shields), index))
        return shields[index]


def _helpless(actor):
    d = actor.data
    return (actor.hp <= 0 or d['fatigue_level'] == 5 or d['states'].get('paralyzed', False)
        or d['states'].get('stunned', False) or any(d['abilities'][k] == 0 for k in ('STR','DEX','CON')))


def _defense(snapshot, action, rng):
    actor = snapshot.entity(action.actor_id)
    kind = action.data['kind']
    if action.data.get('target_action_id') is None:
        if kind not in ('parry', 'dodge') or action.target_id is not None:
            raise EvaluationIntegrityError('only Dodge and Parry can be prepared without a target')
        if action.data.get('ready_at') != action.nominal_end:
            raise EvaluationIntegrityError('target-free defense preparation must end when ready')
        return ActionProposal(action.id, actor.id, (), 'ready')
    attacker = snapshot.entity(action.target_id)
    strike = snapshot.actions[action.data['target_action_id']]
    if kind == 'yield' and strike.family == 'grappling' and strike.data.get('event_type') == 'bull rush':
        if (strike.lifecycle != 'pending' or strike.actor_id != attacker.id
                or strike.target_id != actor.id or strike.nominal_end != action.nominal_end):
            return ActionProposal(action.id, actor.id, (attacker.id,), 'no_threat')
        start, attacker_start = (action.data.get('start_position'),
                                 action.data.get('target_position'))
        current_distance = snapshot.distance(actor.id, attacker.id)
        if (start is None or attacker_start is None or current_distance is None
                or math.dist(actor.position.as_tuple(), attacker.position.as_tuple())
                   <= math.dist(start.as_tuple(), attacker_start.as_tuple())):
            dependency = DefenseEffect(action.id, strike.id, kind, False, False)
            return ActionProposal(action.id, actor.id, (attacker.id,), 'no_space', (),
                                  (dependency,))
        dependency = DefenseEffect(action.id, strike.id, kind, True, True)
        return ActionProposal(action.id, actor.id, (attacker.id,), 'yielded', (),
                              (dependency,))
    prepared = action.data.get('prepared_defense')
    if prepared is not None:
        if (kind not in ('parry', 'dodge') or prepared['kind'] != kind
                or prepared['actor_id'] != actor.id
                or prepared['ready_at'] > strike.nominal_end
                or strike.family != 'melee' or strike.lifecycle != 'pending'
                or strike.actor_id != attacker.id or strike.target_id != actor.id
                or strike.nominal_end != action.nominal_end):
            raise EvaluationIntegrityError('invalid retained-defense assignment')
        if _helpless(actor):
            return ActionProposal(action.id, actor.id, (attacker.id,), 'unable_to_defend')
        if attacker.id not in snapshot.awareness.get(actor.id, ()):
            return ActionProposal(action.id, actor.id, (attacker.id,), 'no_threat')
        if kind == 'parry':
            if prepared['instrument_id'] not in actor.data['held']:
                return ActionProposal(action.id, actor.id, (attacker.id,), 'unable_to_defend')
            parrying_weapon = snapshot.entity(prepared['instrument_id'])
            incoming_weapon = snapshot.entity(strike.instrument_id)
            if (parrying_weapon.data.get('weight') is None
                    or incoming_weapon.data.get('weight') is None
                    or incoming_weapon.data['weight'] > 3 * parrying_weapon.data['weight']
                    or actor.data['weapon_skills'].get(parrying_weapon.data['original_type'], 0) <= 1):
                return ActionProposal(action.id, actor.id, (attacker.id,), 'unable_to_defend')
        if snapshot.melee_status(strike)[0] != 'in_reach':
            return ActionProposal(action.id, actor.id, (attacker.id,), 'no_threat')
        dependency = DefenseEffect(action.id, strike.id, kind, True, False)
        return ActionProposal(action.id, actor.id, (attacker.id,), 'assigned', (), (dependency,))
    eligible = False
    success = False
    effects = ()
    if _helpless(actor) or (kind == 'parry' and action.instrument_id not in actor.data['held']):
        outcome = 'unable_to_defend'
    elif kind == 'block' and action.instrument_id not in actor.data['shields']:
        outcome = 'unable_to_defend'
    elif (strike.family != 'melee' or strike.lifecycle != 'pending' or
          strike.actor_id != attacker.id or strike.target_id != actor.id or
          strike.nominal_end != action.nominal_end):
        outcome = 'no_threat'
    elif action.data['ready_at'] is None or action.data['ready_at'] > strike.nominal_end:
        raise EvaluationIntegrityError('invalid defense readiness')
    else:
        status = snapshot.melee_status(strike)[0]
        eligible = status == 'in_reach' or (kind == 'dodge' and (strike.id, True) in action.data['threat_at_schedule'])
        if not eligible:
            outcome = 'no_threat'
        else:
            if kind == 'yield':
                start, attacker_start = (action.data.get('start_position'),
                                         action.data.get('target_position'))
                current_distance = snapshot.distance(actor.id, attacker.id)
                if (start is None or attacker_start is None or current_distance is None
                        or math.dist(actor.position.as_tuple(), attacker.position.as_tuple())
                           <= math.dist(start.as_tuple(), attacker_start.as_tuple())):
                    dependency = DefenseEffect(action.id, strike.id, kind, False, False)
                    return ActionProposal(action.id, actor.id, (attacker.id,), 'no_space', (),
                                          (dependency,))
                dependency = DefenseEffect(action.id, strike.id, kind, True, True)
                return ActionProposal(action.id, actor.id, (attacker.id,), 'yielded', (),
                                      (dependency,))
            if kind == 'block':
                success = True
                outcome = 'blocked'
                dependency = DefenseEffect(action.id, strike.id, kind, True, True)
                return ActionProposal(action.id, actor.id, (attacker.id,), outcome, (), (dependency,))
            skill = snapshot.entity(action.instrument_id).data['original_type'] if kind == 'parry' else 'tumble'
            rank = (actor.data['weapon_skills'] if kind == 'parry' else actor.data['skills']).get(skill, 0) or 0
            if status != 'in_reach':
                success = True
            else:
                weapon = snapshot.entity(strike.instrument_id)
                attack_rank = attacker.data['weapon_skills'].get(weapon.data['original_type'], 0) or 0
                defense_priority = action.data.get('multiple_action_priority', 0) or 0
                attack_priority = strike.data.get('multiple_action_priority', 0) or 0
                success = defense_succeeds(rng.roll('1d20'), rank,
                    actor.data['strategy']['defense'] - defense_priority,
                    rng.roll('1d20'), attack_rank,
                    attacker.data['strategy']['attack'] - attack_priority)
            outcome = ('deflected' if kind == 'parry' else 'evaded') if success else 'failed'
            effects = (PracticeEffect(action.id, actor.id, skill, 10),)
    dependency = DefenseEffect(action.id, strike.id, kind, eligible, success)
    return ActionProposal(action.id, actor.id, (attacker.id,), outcome, effects, (dependency,))


def _combat(snapshot, action, rng, dependencies, *, pole_set_charge=False,
            pole_charge_speed=None, charge_intercepted=False):
    actor, target = snapshot.entity(action.actor_id), snapshot.entity(action.target_id)
    weapon = snapshot.entity(action.instrument_id) if action.instrument_id else None
    effects = []
    meta = []
    attempted = False
    outcome = None
    charge_extra_damage = 0
    pinned_controls = tuple(row for row in snapshot.grapple_controls
        if len(row) > 6 and row[6] in ('pin_top', 'pin_bottom'))
    if action.family == 'combat' and action.data['event_type'] == 'touch':
        distance = snapshot.distance(actor.id, target.id)
        willing = action.data.get('touch_willing') is True
        if willing and _helpless(actor):
            return ActionProposal(action.id, actor.id, (target.id,), 'unable_to_act')
        if actor.position is None or target.position is None or distance is None:
            outcome = 'unplaced'
        else:
            from melee_combat import reference_arm_length_inches, INCHES_TO_METERS
            try:
                reach = reference_arm_length_inches(
                    height_inches=actor.data.get('height'),
                    length_inches=actor.data.get('length')) * INCHES_TO_METERS
            except ValueError:
                outcome = 'unsupported_reach'
            if outcome is None:
                from arena_hex_map import layout_from_encounter_map
                layout = layout_from_encounter_map(snapshot.encounter_map)
                if layout is None:
                    if distance > reach: outcome = 'out_of_reach'
                else:
                    from action_calculations import melee_hex_occupancy_path_status
                    status, _ = melee_hex_occupancy_path_status(actor.position, target.position,
                        reach, snapshot.physical_path(actor.id,target.id), layout)
                    if status != 'in_reach': outcome = status
            if outcome is None:
                if willing:
                    other_actions = tuple(row for row in snapshot.actions.values()
                        if row.id != action.id and row.lifecycle == 'pending'
                        and row.start <= snapshot.boundary <= row.nominal_end)
                    actor_busy = any(row.actor_id == actor.id for row in other_actions)
                    moving_ids = set(getattr(snapshot, 'moving_ids', ()))
                    actor_moving = actor.id in moving_ids or any(
                        row.actor_id == actor.id and row.family == 'run' for row in other_actions)
                    target_moving = target.id in moving_ids or any(
                        row.actor_id == target.id and row.family == 'run' for row in other_actions)
                    check = actor_busy or actor_moving or target_moving
                    if not check:
                        outcome = 'touched'
                    else:
                        dice_count = 4 if actor_moving and target_moving else 3
                        dexterity = actor.data['abilities'].get('DEX', 10)
                        total = sum(rng.roll('1d6') for _ in range(dice_count))
                        outcome = 'touched' if total <= dexterity else 'missed'
                else:
                    attack_total = (rng.roll('1d20') + actor.data['strategy']['attack']
                                    - (action.data.get('multiple_action_priority', 0) or 0))
                    defense_total = rng.roll('1d20') + target.data['strategy']['defense']
                    outcome = 'touched' if attack_total > defense_total else 'missed'
        metadata = () if distance is None else (('distance', distance),)
        return ActionProposal(action.id, actor.id, (target.id,), outcome,
            (), (), metadata)
    if action.family == 'melee':
        status, distance = snapshot.melee_status(action)
        meta.append(('distance', distance))
        if pole_set_charge and pole_charge_speed is not None:
            meta.append(('relative_charge_speed_yd_s', pole_charge_speed))
        if action.data.get('charge') is True and not charge_intercepted:
            actor_velocity = snapshot.motion_velocities_m_s.get(actor.id)
            target_velocity = snapshot.motion_velocities_m_s.get(target.id, (0.0, 0.0, 0.0))
            if actor_velocity is None:
                outcome = 'insufficient_charge_speed'
            else:
                relative_speed_yd_s = math.dist(actor_velocity, target_velocity) / 0.9144
                meta.append(('relative_charge_speed_yd_s', relative_speed_yd_s))
                if relative_speed_yd_s < 4.0:
                    outcome = 'insufficient_charge_speed'
                else:
                    charge_extra_damage = math.floor((relative_speed_yd_s - 4.0) / 2.0)
        if outcome is None and any(row[2] == actor.id for row in pinned_controls):
            outcome = 'unable_to_act'
        elif outcome is None and any(row[1] == actor.id and row[2] == target.id
                 for row in pinned_controls):
            outcome = 'grapple_restricted'
        elif outcome is None and (any(actor.id in (row[1], row[2]) for row in snapshot.grapple_controls)
                and not any({actor.id, target.id} == {row[1], row[2]}
                            for row in snapshot.grapple_controls)):
            outcome = 'grapple_restricted'
        elif outcome is None and (actor.hp <= 0 or actor.data['fatigue_level'] >= 5):
            outcome = 'unable_to_act'
        elif outcome is None and target.hp <= 0 and action.data['event_type'] != 'coup de grace':
            outcome = 'target_down'
        elif outcome is None and (action.instrument_id not in actor.data['held'] or weapon is None or weapon.hp <= 0):
            outcome = 'weapon_unavailable'
        elif outcome is None and status != 'in_reach':
            outcome = status
        elif outcome is None and any(d.eligible and d.success and d.kind in ('parry', 'dodge') for d in dependencies):
            first = next(d for d in dependencies if d.eligible and d.success
                         and d.kind in ('parry', 'dodge'))
            outcome = 'parried' if first.kind == 'parry' else 'dodged'
            attempted = True
    if outcome is None:
        if weapon is None or weapon.category != 'weapon':
            outcome = 'weapon_unavailable'
        else:
            def hits(roll, dc):
                adjustment = 0
                target_defense = target.data.get('strategy', {}).get('defense', 0)
                if action.family == 'melee':
                    adjustment = actor.data['fatigue_adjustments'][actor.data['fatigue_level']]['ability_adjustment']
                    if adjustment is None:
                        return False
                    from arena_hex_map import layout_from_encounter_map
                    if layout_from_encounter_map(snapshot.encounter_map) is not None:
                        target_facing = target.data.get('hex_facing')
                        if target_facing is not None:
                            from hex_facing import vector_is_behind
                            source_position, target_position = actor.position, target.position
                            if vector_is_behind(target_facing,
                                (source_position.x - target_position.x,
                                 source_position.y - target_position.y,
                                 source_position.z - target_position.z)):
                                target_defense = 0
                parry_bonus = sum(2 for dependency in dependencies
                    if dependency.kind == 'parry' and dependency.eligible
                    and (dependency.success or snapshot.actions[dependency.source_action_id].data.get('prepared_defense') is not None))
                dodge_dependencies = [dependency for dependency in dependencies
                    if dependency.kind == 'dodge' and dependency.eligible
                    and snapshot.actions[dependency.source_action_id].data.get('prepared_defense') is not None]
                if dodge_dependencies:
                    dodge = snapshot.actions[dodge_dependencies[0].source_action_id].data['prepared_defense']
                    target_defense = (dodge['strategy']['defense']
                                      + (target.data['skills'].get('tumble', 0) or 0) // 4)
                block_penalty = 4 if any(dependency.kind == 'block'
                    and dependency.eligible and dependency.success
                    for dependency in dependencies) else 0
                yield_penalty = sum(1 for dependency in dependencies
                    if dependency.kind == 'yield' and dependency.eligible
                    and dependency.success)
                feint_bonus = 2 if action.data.get('feint_source_action_id') is not None else 0
                pin_bonus = 4 if any(row[2] == target.id for row in pinned_controls) else 0
                priority_penalty = action.data.get('multiple_action_priority', 0) or 0
                return attack_hits(roll - block_penalty - yield_penalty,
                    actor.data['weapon_skills'].get(weapon.obj_type, 0)
                    + actor.data['strategy']['attack'] - priority_penalty
                    + feint_bonus + pin_bonus
                    + (2 if action.data.get('charge') is True and not charge_intercepted else 0)
                    + (2 if pole_set_charge else 0),
                    target_defense + parry_bonus, dc - adjustment)
            if action.family == 'melee' and action.data['event_type'] == 'feint':
                if (actor.data['weapon_skills'].get(weapon.obj_type, 0) or 0) <= 1:
                    outcome = 'weapon_unavailable'
                else:
                    adjustment = actor.data['fatigue_adjustments'][actor.data['fatigue_level']]['ability_adjustment']
                    outcome = ('success' if adjustment is not None
                               and hits(rng.roll('1d20'), snapshot.difficulty) else 'failure')
                return ActionProposal(action.id, actor.id, (target.id,), outcome,
                                      (), tuple(dependencies), (('distance', distance),))
            def save(being, dc):
                return saving_throw(rng.roll('1d20'), dc,
                    saving_throw_experience_modifier(experience_level(being.data['experience'])))
            coup_de_grace = (action.family == 'melee'
                             and action.data['event_type'] == 'coup de grace')
            attack_roll = [None]
            if coup_de_grace:
                if not _helpless(target):
                    return ActionProposal(action.id, actor.id, (target.id,),
                        'ineligible_target', (), tuple(dependencies), (('distance', distance),))
                outcome = 'critical'
            else:
                def combat_roll(dice):
                    value = rng.roll(dice)
                    if attack_roll[0] is None and dice == '1d20':
                        attack_roll[0] = value
                    return value
                outcome = hit_outcome(snapshot.difficulty, combat_roll, hits,
                    lambda dc: save(target, dc), lambda dc: save(actor, dc))
            attempted = True
            redirected_pin = next((row for row in pinned_controls
                if row[2] == target.id and row[1] != actor.id
                and outcome == 'miss' and attack_roll[0] is not None
                and attack_roll[0] <= (2 if row[6] == 'pin_top' else 1)), None)
            if redirected_pin is not None:
                outcome = 'normal'
            recipient = (actor if outcome == 'hit self' else
                         snapshot.entity(redirected_pin[1]) if redirected_pin else target)
            if outcome == 'fatal':
                effects.append(FatalEffect(action.id, target.id))
            potential = weapon.data['attacks']['S' if action.data['event_type'] == 'swing' else 'T']['d']
            penetration = weapon.data['attacks']['S' if action.data['event_type'] == 'swing' else 'T']['p']
            def shield(damage):
                blocks = [d for d in dependencies if d.kind == 'block'
                          and d.eligible and d.success]
                sid = (snapshot.actions[blocks[0].source_action_id].instrument_id
                       if blocks else rng.choose_shield(recipient.data.get('shields', ())))
                if sid is None:
                    return damage
                item = snapshot.entity(sid)
                blocked = bool(blocks)
                shield_size = int(item.data['size']) + (1 if blocked else 0)
                intercepted, through = shield_impact(damage, shield_size, rng.roll('1d10+0'))
                if intercepted and blocked:
                    through = max(0, damage - shield_size - 2)
                effects.append(ProtectionEffect(action.id, sid, 'shield', damage, through, intercepted))
                if intercepted:
                    effects.append(DamageEffect(action.id, sid, damage, 'shield'))
                return through
            def armor(damage):
                aid = recipient.data.get('armor_id')
                if aid is None:
                    return damage
                item = snapshot.entity(aid)
                if item.category != 'armor':
                    raise EvaluationIntegrityError('armor identity is not armor')
                dealt, through = armor_impact(damage, item.data['defenses'], penetration)
                effects.extend((ProtectionEffect(action.id, aid, 'armor', damage, through, True),
                                DamageEffect(action.id, aid, dealt, 'armor')))
                return through
            def body(ordinary, critical):
                effects.append(DamageEffect(action.id, recipient.id, ordinary, 'body'))
                if outcome == 'critical':
                    effects.append(DamageEffect(action.id, recipient.id, critical, 'critical_bypass'))
            if pole_charge_speed is not None:
                pole_extra_damage = math.floor((pole_charge_speed - 4.0) / 2.0)
            else:
                pole_extra_damage = 0
            damage_path(outcome, potential,
                action.data['strategy']['extra_damage']
                + (0 if charge_intercepted else charge_extra_damage) + pole_extra_damage,
                rng.roll, shield, armor, body,
                damage_dice=2 if pole_set_charge else 1)
            if coup_de_grace:
                damage_dealt = sum(effect.amount for effect in effects
                    if type(effect) is DamageEffect and effect.target_id == target.id
                    and effect.component in ('body', 'critical_bypass'))
                if target.hp - damage_dealt > -10:
                    saved = save(target, 10 + damage_dealt)
                    if not saved:
                        outcome = 'fatal'
                        effects.append(FatalEffect(action.id, target.id))
            hp_damage = sum(effect.amount for effect in effects
                if type(effect) is DamageEffect and effect.target_id == recipient.id
                and effect.component in ('body','critical_bypass'))
            if hp_damage > 0 and recipient.hp > 0:
                for grip in snapshot.physical_grips:
                    if grip[1] != recipient.id:
                        continue
                    probability = min(1.0, hp_damage / recipient.hp)
                    purpose = f'grip_release:{grip[0]}:{hp_damage}/{recipient.hp}'
                    if rng.roll_probability(probability,purpose):
                        effects.append(GrappleStateEffect(action.id,grip[2],grip[1],
                            grip[0],'grip','release',grip[3],None))
    if outcome in ('parried','dodged'):
        if attempted and action.family == 'melee':
            effects.append(PracticeEffect(action.id, actor.id, weapon.data['original_type'], 10))
        affected = tuple(dict.fromkeys((target.id,) + tuple(
            effect.target_id for effect in effects if hasattr(effect, 'target_id'))))
        return ActionProposal(action.id, actor.id, affected, outcome, tuple(effects),
                              tuple(dependencies), tuple(meta))
    if attempted and action.family == 'melee':
        effects.append(PracticeEffect(action.id, actor.id, weapon.data['original_type'], 10))
    affected = tuple(dict.fromkeys((target.id,) + tuple(e.target_id for e in effects if hasattr(e, 'target_id'))))
    return ActionProposal(action.id, actor.id, affected, outcome, tuple(effects), tuple(dependencies), tuple(meta))


_GRAPPLE_SIZE_ORDER = ('diminutive', 'tiny', 'small', 'medium', 'large',
                      'huge', 'gargantuan', 'colossal')


def _effective_grapple_size(being):
    category = being.data.get('size_category')
    if category not in _GRAPPLE_SIZE_ORDER:
        return None
    return 2 ** (_GRAPPLE_SIZE_ORDER.index(category) - 1)


def _grapple_attackers(snapshot, target_id):
    return ({row[1] for row in snapshot.physical_grips if row[2] == target_id}
            | {row[1] for row in snapshot.grapple_controls if row[2] == target_id})


def _grapple_capacity_and_bonus(snapshot, actor, target):
    """Return adopted multi-attacker capacity and bonus from this frozen frame."""
    other_ids = _grapple_attackers(snapshot, target.id) - {actor.id}
    declared_ids = {row.actor_id for row in snapshot.actions.values()
                    if row.actor_id != actor.id and row.target_id == target.id
                    and row.boundary == snapshot.boundary
                    and row.data.get('event_type') in ('grab', 'hold', 'grapple')}
    if not other_ids and not declared_ids:
        return True, 0
    target_size = _effective_grapple_size(target)
    capacity_ids = other_ids | declared_ids | {actor.id}
    attacker_sizes = [_effective_grapple_size(snapshot.entity(identity))
                      for identity in capacity_ids]
    if target_size is None or any(size is None for size in attacker_sizes):
        return False, 0
    total = sum(attacker_sizes)
    if total > 4 * target_size:
        return False, 0
    # Revision 34: independent opposed checks, with +2 times the effective
    # sizes of other existing attackers divided by the target's effective size.
    bonus = 2 * sum(_effective_grapple_size(snapshot.entity(identity))
                    for identity in other_ids) / target_size
    return True, bonus


def _grapple_roll(rng, being, *, escape=False, strength_only=False, bonus=0):
    skills = being.data.get('skills', {})
    if strength_only:
        score = being.data['abilities'].get('STR', 10)
        modifier = (score - 10) // 2
    else:
        abilities = being.data['abilities']
        modifier = max((abilities.get('STR', 10) - 10) // 2,
                       (abilities.get('DEX', 10) - 10) // 2)
        improved = next((value for name, value in skills.items()
                         if name.casefold() == 'improved grapple'), 0) or 0
        modifier += improved
        if escape:
            modifier += next((value for name, value in skills.items()
                              if name.casefold() == 'escape artist'), 0) or 0
    modifier -= being.data.get('armor_check_penalty', 0) or 0
    dice = tuple(rng.roll('1d6') for _ in range(3))
    return sum(dice) + modifier + bonus


def _represented_extra_legs(being):
    """Apply the adopted +2 stability modifier from explicit named leg slots."""
    parts = being.data.get('body_parts')
    if type(parts) not in (dict, MappingProxyType):
        return 0
    count = sum(1 for name in parts
                if type(name) is str and name.casefold().strip().endswith(' leg'))
    return 2 if count > 2 else 0


def _charge_overrun_destination(snapshot, action):
    """Resolve only an unambiguous, open one-hex adopted Charge-Overrun landing."""
    from arena_hex_map import HexAddress, layout_from_encounter_map
    from hex_facing import facing_vector
    layout = layout_from_encounter_map(snapshot.encounter_map)
    actor, target = snapshot.entity(action.actor_id), snapshot.entity(action.target_id)
    if (layout is None or actor.position is None or target.position is None
            or target.id in snapshot.moving_ids):
        return None
    source = layout.cell_at_position(target.position)
    facing = actor.data.get('hex_facing')
    if source is None or type(facing) is not int:
        return None
    fx, fy = facing_vector(facing)
    center = layout.center_position(source, z=target.position.z)
    candidates = []
    for address in layout.neighbors(source):
        if not layout.contains(address):
            continue
        position = layout.center_position(address, z=target.position.z)
        dx, dy = position.x-center.x, position.y-center.y
        candidates.append((dx*fx+dy*fy, address, position))
    if not candidates:
        return None
    candidates.sort(key=lambda row: (-row[0], row[1].column, row[1].row))
    if (len(candidates) > 1
            and math.isclose(candidates[0][0], candidates[1][0], rel_tol=0, abs_tol=1e-10)):
        return None
    if candidates[0][0] <= 0:
        return None
    _, destination_cell, destination = candidates[0]
    for identity in snapshot.participant_ids:
        if identity in (actor.id, target.id):
            continue
        entity = snapshot.entity(identity)
        if entity.position is not None and layout.cell_at_position(entity.position) == destination_cell:
            return None
    from spatial.visibility import trace_physical_path
    path = trace_physical_path(target.position, destination,
        ((identity, snapshot.entity(identity)) for identity in snapshot.participant_ids
         if identity != target.id and snapshot.entity(identity).position is not None
         and snapshot.entity(identity).geometry is not None
         and snapshot.entity(identity).data.get('parent_container_id') is None),
        exclude_ids=(target.id,))
    if path.intersections or path.unmodeled_entity_ids:
        return None
    from measured_values import truncate_position
    return truncate_position(destination).as_tuple()


def _grappling(snapshot, action, rng, dependencies=()):
    actor, target = snapshot.entity(action.actor_id), snapshot.entity(action.target_id)
    event_type = action.data['event_type']
    priority_penalty = action.data.get('multiple_action_priority', 0) or 0
    effects = []
    if event_type in ('grab object','wrest'):
        holder=snapshot.entity(action.data['holder_id'])
        if actor.hp<=0 or actor.data['fatigue_level']>=5 or holder.hp<=0:
            return ActionProposal(action.id,actor.id,(target.id,),'unavailable')
        hand=action.data.get('grab_hand');holder_hand=action.data.get('holder_hand')
        if (target.category!='weapon' or target.data.get('parent_container_id')!=holder.id
                or target.id not in holder.data.get('held',())
                or holder.data.get('body_parts',{}).get(holder_hand)!=target.id):
            return ActionProposal(action.id,actor.id,(target.id,),'not_held')
        if event_type=='grab object' and hand not in actor.data.get('free_hands',()):
            return ActionProposal(action.id,actor.id,(target.id,),'hand_unavailable')
        if actor.position is None or holder.position is None:
            return ActionProposal(action.id,actor.id,(target.id,),'unavailable')
        from melee_combat import reference_arm_length_inches
        try:
            reach=reference_arm_length_inches(height_inches=actor.data.get('height'),
                length_inches=actor.data.get('length'),size_category=actor.data.get('size_category'))*0.0254
        except ValueError:
            return ActionProposal(action.id,actor.id,(target.id,),'unavailable')
        path=snapshot.physical_path(actor.id,holder.id)
        from arena_hex_map import layout_from_encounter_map
        layout=layout_from_encounter_map(snapshot.encounter_map)
        if layout is None:
            status,_=melee_path_status(math.dist(actor.position.as_tuple(),holder.position.as_tuple()),reach,path)
        else:
            from action_calculations import melee_hex_occupancy_path_status
            status,_=melee_hex_occupancy_path_status(actor.position,holder.position,reach,path,layout)
        if status!='in_reach':return ActionProposal(action.id,actor.id,(target.id,),status)
        competing=[row for row in snapshot.actions.values() if row.lifecycle=='pending'
            and row.boundary==action.boundary and row.target_id==target.id
            and row.id!=action.id and row.data.get('event_type') in ('grab object','wrest')]
        if any(row.data.get('event_type')!=event_type for row in competing):
            return ActionProposal(action.id,actor.id,(target.id,),'contested')
        losing=[row for row in snapshot.actions.values() if row.lifecycle=='pending'
            and row.boundary==action.boundary and row.data.get('event_type')=='disarm'
            and row.data.get('disarm_weapon_id')==target.id]
        holder_use=[row for row in snapshot.actions.values() if row.lifecycle=='pending'
            and row.boundary==action.boundary and row.id!=action.id
            and row.actor_id==holder.id and row.instrument_id==target.id]
        if losing or holder_use:
            return ActionProposal(action.id,actor.id,(target.id,),'custody_conflict')
        existing=next((row for row in snapshot.object_grips
                       if row[0]==target.id and row[2]==actor.id),None)
        if event_type=='grab object':
            if existing is not None:
                return ActionProposal(action.id,actor.id,(target.id,),'unavailable')
            size_mod={'D':4,'T':2,'S':1,'M':0,'L':-1,'H':-2,'G':-4,'C':-8}.get(target.data.get('size'))
            if size_mod is None:
                return ActionProposal(action.id,actor.id,(target.id,),'unavailable')
            roll=rng.roll('1d20')
            success=attack_hits(roll,actor.data['strategy']['attack']-priority_penalty,
                holder.data['strategy']['defense'],snapshot.difficulty+5+size_mod)
            if not success:
                return ActionProposal(action.id,actor.id,(target.id,),'failed')
            effects.append(ObjectGripEffect(action.id,target.id,actor.id,holder.id,
                action.id,'establish',hand,holder_hand))
            return ActionProposal(action.id,actor.id,(target.id,),'success',tuple(effects))
        grip_id=action.data.get('object_grip_id')
        if (existing is None or existing[2]!=actor.id
                or existing[3]!=holder.id or existing[4]!=hand or existing[5]!=holder_hand
                or existing[1]!=grip_id):
            return ActionProposal(action.id,actor.id,(target.id,),'grip_lost')
        actor_total=(sum(rng.roll('1d6') for _ in range(3))
                     +(actor.data['abilities'].get('STR',10)-10)//2-priority_penalty)
        holder_total=sum(rng.roll('1d6') for _ in range(3))+(holder.data['abilities'].get('STR',10)-10)//2
        if actor_total<=holder_total:
            return ActionProposal(action.id,actor.id,(target.id,),'failed')
        effects.append(ObjectGripEffect(action.id,target.id,actor.id,holder.id,
            grip_id,'transfer',hand,holder_hand))
        return ActionProposal(action.id,actor.id,(target.id,),'success',tuple(effects))
    if event_type in ('grab', 'hold', 'break hold', 'release grip', 'grapple','takedown','reverse','pin','trip','bull rush','overrun'):
        distance = snapshot.distance(actor.id, target.id)
        if actor.position is None or target.position is None or distance is None:
            return ActionProposal(action.id, actor.id, (target.id,), 'unavailable')
        layout = None
        from arena_hex_map import layout_from_encounter_map
        layout = layout_from_encounter_map(snapshot.encounter_map)
        if layout is not None:
            from action_calculations import melee_hex_occupancy_path_status
            status, _ = melee_hex_occupancy_path_status(actor.position,target.position,
                .9144,snapshot.physical_path(actor.id,target.id),layout)
        else:
            status = 'in_reach' if distance <= .9144 else 'out_of_reach'
        if status != 'in_reach':
            return ActionProposal(action.id, actor.id, (target.id,), status)
    if event_type == 'overrun':
        if (actor.data.get('posture') != 'standing'
                or target.data.get('posture') != 'standing'):
            return ActionProposal(action.id, actor.id, (target.id,), 'wrong_position')
        from arena_hex_map import layout_from_encounter_map
        layout = layout_from_encounter_map(snapshot.encounter_map)
        if layout is not None:
            if (layout.cell_at_position(actor.position) is None
                    or layout.cell_at_position(target.position) is None
                    or distance > .9144):
                return ActionProposal(action.id, actor.id, (target.id,), 'wrong_position')
        elif math.dist(actor.position.as_tuple(), target.position.as_tuple()) > .9144:
            return ActionProposal(action.id, actor.id, (target.id,), 'out_of_reach')
        from hex_facing import FacingSector, classify_vector
        facing = actor.data.get('hex_facing')
        if (facing is None or classify_vector(facing,
                (target.position.x-actor.position.x,target.position.y-actor.position.y,
                 target.position.z-actor.position.z)) is not FacingSector.FRONT):
            return ActionProposal(action.id, actor.id, (target.id,), 'not_facing')
        order=('diminutive','tiny','small','medium','large','huge','gargantuan','colossal')
        sizes=(actor.data.get('size_category'),target.data.get('size_category'))
        if any(value not in order for value in sizes):
            return ActionProposal(action.id,actor.id,(target.id,),'size_category_unknown')
        if any(type(snapshot.entity(shield_id).data.get('original_type')) is str
               and 'tower' in snapshot.entity(shield_id).data['original_type'].casefold()
               for shield_id in actor.data.get('shields', ())):
            return ActionProposal(action.id,actor.id,(target.id,),'tower_shield_restricted')
        difference=order.index(sizes[1])-order.index(sizes[0])
        if difference>1:
            return ActionProposal(action.id,actor.id,(target.id,),'size_limit')
        actor_size=actor.data['abilities'].get('STR',10)
        target_size=target.data['abilities'].get('STR',10)
        actor_dex=actor.data['abilities'].get('DEX',10)
        target_dex=target.data['abilities'].get('DEX',10)
        size_modifier=4*(order.index(sizes[0])-order.index(sizes[1]))
        shield_bonus = 0
        if action.instrument_id is not None:
            if action.instrument_id not in actor.data.get('shields', ()):
                return ActionProposal(action.id, actor.id, (target.id,), 'shield_unavailable')
            shield = snapshot.entity(action.instrument_id)
            shield_type = shield.data.get('original_type')
            if type(shield_type) is not str or 'tower' in shield_type.casefold():
                return ActionProposal(action.id, actor.id, (target.id,), 'shield_unavailable')
            shield_rank = actor.data['weapon_skills'].get(shield_type, 0) or 0
            shield_bonus = 2 if shield_rank > 1 else 1
        actor_total=(sum(rng.roll('1d6') for _ in range(3))
                     +(actor_size-10)//2+(actor_dex-10)//2
                     +max(0,size_modifier)+shield_bonus
                     +_represented_extra_legs(actor)-priority_penalty
                     +(1 if (action.data.get('charge_continuation') is True
                             or action.data.get('bull_rush_continuation') is True) else 0))
        target_total=(sum(rng.roll('1d6') for _ in range(3))
                      +(target_size-10)//2+(target_dex-10)//2
                      +max(0,-size_modifier)+_represented_extra_legs(target))
        if actor_total<=target_total:
            return ActionProposal(action.id,actor.id,(target.id,),'failed')
        if action.data.get('charge_continuation') is True:
            destination = _charge_overrun_destination(snapshot, action)
            if destination is None:
                return ActionProposal(action.id,actor.id,(target.id,),
                    'success_pending_displacement')
            effects.append(PositionEffect(action.id,target.id,destination))
        effects.append(GrappleStateEffect(action.id,target.id,actor.id,action.id,
            'posture','set',None,None,'lying'))
        return ActionProposal(action.id,actor.id,(target.id,),'success',tuple(effects))
    if event_type == 'bull rush':
        if any(row.kind == 'yield' and row.eligible and row.success
               and row.strike_id == action.id for row in dependencies):
            return ActionProposal(action.id, actor.id, (target.id,), 'yielded')
        from arena_hex_map import layout_from_encounter_map
        layout = layout_from_encounter_map(snapshot.encounter_map)
        if layout is not None and (layout.cell_at_position(actor.position) is None
                or layout.cell_at_position(target.position) is None):
            return ActionProposal(action.id,actor.id,(target.id,),'wrong_position')
        from hex_facing import FacingSector, classify_vector
        facing = actor.data.get('hex_facing')
        if (facing is None or classify_vector(facing,
                (target.position.x-actor.position.x,target.position.y-actor.position.y,
                 target.position.z-actor.position.z)) is not FacingSector.FRONT):
            return ActionProposal(action.id,actor.id,(target.id,),'not_facing')
        order=('diminutive','tiny','small','medium','large','huge','gargantuan','colossal')
        sizes=(actor.data.get('size_category'),target.data.get('size_category'))
        if any(value not in order for value in sizes):
            return ActionProposal(action.id,actor.id,(target.id,),'size_category_unknown')
        difference=order.index(sizes[0])-order.index(sizes[1])
        if difference < -1:
            return ActionProposal(action.id,actor.id,(target.id,),'size_limit')
        if any(type(snapshot.entity(shield_id).data.get('original_type')) is str
               and 'tower' in snapshot.entity(shield_id).data['original_type'].casefold()
               for shield_id in actor.data.get('shields', ())):
            return ActionProposal(action.id,actor.id,(target.id,),'tower_shield_restricted')
        if action.data.get('bull_rush_target_willing') is True:
            return ActionProposal(action.id,actor.id,(target.id,),
                                  'success_pending_displacement')
        shield_bonus=0
        if action.instrument_id is not None:
            if action.instrument_id not in actor.data.get('shields', ()):
                return ActionProposal(action.id,actor.id,(target.id,),'shield_unavailable')
            shield=snapshot.entity(action.instrument_id)
            shield_type=shield.data.get('original_type')
            if type(shield_type) is not str or 'tower' in shield_type.casefold():
                return ActionProposal(action.id,actor.id,(target.id,),'shield_unavailable')
            shield_rank=actor.data['weapon_skills'].get(shield_type,0) or 0
            shield_bonus=2 if shield_rank>1 else 1
        actor_total=(sum(rng.roll('1d6') for _ in range(3))
                     +(actor.data['abilities'].get('STR',10)-10)//2
                     +4*max(0,difference)+shield_bonus
                     +_represented_extra_legs(actor)-priority_penalty
                     +(2 if action.data.get('charge_continuation') is True else
                       1 if action.data.get('bull_rush_continuation') is True else 0))
        target_total=(sum(rng.roll('1d6') for _ in range(3))
                      +(target.data['abilities'].get('STR',10)-10)//2
                      +4*max(0,-difference)+_represented_extra_legs(target))
        outcome='success_pending_displacement' if actor_total>target_total else 'failed'
        return ActionProposal(action.id,actor.id,(target.id,),outcome)
    if event_type == 'grab':
        source = action.data['touch_action_id']
        if not any(row.id == source and row.actor_id == actor.id and row.target_id == target.id
                   and row.lifecycle == 'pending' and row.data.get('event_type') == 'touch'
                   for row in snapshot.actions.values()):
            # Completed Touch is verified at native scheduling; it is retained
            # in the action declaration as a receipt-backed contact reference.
            if not action.data.get('contact_verified'):
                return ActionProposal(action.id,actor.id,(target.id,),'touched_required')
        if action.data['grab_hand'] not in actor.data.get('free_hands',()):
            return ActionProposal(action.id,actor.id,(target.id,),'unavailable')
        if actor.hp <= 0 or target.hp <= 0 or actor.data['fatigue_level'] >= 5:
            return ActionProposal(action.id,actor.id,(target.id,),'unavailable')
        allowed, bonus = _grapple_capacity_and_bonus(snapshot, actor, target)
        if not allowed:
            return ActionProposal(action.id,actor.id,(target.id,),'capacity_exceeded')
        holder = _grapple_roll(rng,actor,bonus=bonus-priority_penalty)
        pinned = any(row[2] == target.id and len(row) > 6
                     and row[6] in ('pin_top', 'pin_bottom')
                     for row in snapshot.grapple_controls)
        if not pinned and holder <= _grapple_roll(rng,target):
            return ActionProposal(action.id,actor.id,(target.id,),'failed')
        effects.append(GrappleStateEffect(action.id,target.id,actor.id,action.id,
            'grip','establish',action.data['grab_hand'],action.boundary+6))
        return ActionProposal(action.id,actor.id,(target.id,),'success',tuple(effects))
    if event_type == 'hold':
        grip = next((row for row in snapshot.physical_grips if row[0] == action.data['grip_id']
                     and row[1] == actor.id and row[2] == target.id),None)
        if grip is None: return ActionProposal(action.id,actor.id,(target.id,),'unavailable')
        if grip[5] != action.boundary: return ActionProposal(action.id,actor.id,(target.id,),'unavailable')
        allowed, bonus = _grapple_capacity_and_bonus(snapshot, actor, target)
        if not allowed:
            return ActionProposal(action.id,actor.id,(target.id,),'capacity_exceeded')
        if _grapple_roll(rng,actor,bonus=bonus-priority_penalty) <= _grapple_roll(rng,target):
            effects.append(GrappleStateEffect(action.id,target.id,actor.id,grip[0],
                'grip','release',grip[3],None))
            return ActionProposal(action.id,actor.id,(target.id,),'failed',tuple(effects))
        effects.append(GrappleStateEffect(action.id,target.id,actor.id,grip[0],
            'grip','maintain',grip[3],action.boundary+6))
        return ActionProposal(action.id,actor.id,(target.id,),'success',tuple(effects))
    if event_type == 'break hold':
        grip = next((row for row in snapshot.physical_grips if row[0] == action.data['grip_id']
                     and row[1] == target.id and row[2] == actor.id),None)
        if grip is None: return ActionProposal(action.id,actor.id,(target.id,),'unavailable')
        if (_grapple_roll(rng,actor,strength_only=True,bonus=-priority_penalty)
                <= _grapple_roll(rng,target,strength_only=True)):
            return ActionProposal(action.id,actor.id,(target.id,),'failed')
        effects.append(GrappleStateEffect(action.id,actor.id,actor.id,grip[0],
            'grip','release',grip[3],None))
        return ActionProposal(action.id,actor.id,tuple(sorted((target.id,actor.id))),
            'success',tuple(effects))
    if event_type == 'release grip':
        grip = next((row for row in snapshot.physical_grips if row[0] == action.data['grip_id']
                     and row[1] == actor.id and row[2] == target.id),None)
        if grip is None:
            return ActionProposal(action.id,actor.id,(target.id,),'unavailable')
        effects.append(GrappleStateEffect(action.id,target.id,actor.id,grip[0],
            'grip','release',grip[3],None))
        return ActionProposal(action.id,actor.id,(target.id,),'success',tuple(effects))
    if event_type == 'grapple':
        grip = next((row for row in snapshot.physical_grips if row[0] == action.data['grip_id']
                     and row[1] == actor.id and row[2] == target.id),None)
        if grip is None:
            grip = next((row for row in snapshot.physical_grips
                         if row[1] == actor.id and row[2] == target.id),None)
        if grip is None: return ActionProposal(action.id,actor.id,(target.id,),'grip_lost')
        if any(row[1] == actor.id and row[2] == target.id
               for row in snapshot.grapple_controls):
            return ActionProposal(action.id,actor.id,(target.id,),'unavailable')
        if grip[5] != action.boundary:
            return ActionProposal(action.id,actor.id,(target.id,),'grip_lost')
        # Revision 41: the initial Grapple check replaces maintenance of this
        # same prerequisite grip at the coincident six-second boundary.
        effects.append(GrappleStateEffect(action.id,target.id,actor.id,grip[0],
            'grip','maintain',grip[3],action.boundary+6))
        allowed, bonus = _grapple_capacity_and_bonus(snapshot, actor, target)
        if not allowed:
            return ActionProposal(action.id,actor.id,(target.id,),'capacity_exceeded')
        if _grapple_roll(rng,actor,bonus=bonus-priority_penalty) <= _grapple_roll(rng,target):
            return ActionProposal(action.id,actor.id,(target.id,),'failed',tuple(effects))
        effects.append(GrappleStateEffect(action.id,target.id,actor.id,action.id,
            'control','establish',None,action.boundary+6))
        return ActionProposal(action.id,actor.id,(target.id,),'success',tuple(effects))
    if event_type == 'trip':
        contact_kind=action.data.get('trip_contact_kind')
        if contact_kind not in ('touch','grab','strike'):
            return ActionProposal(action.id,actor.id,(target.id,),'touch_required')
        metadata=(('contact_kind',contact_kind),)
        order=('diminutive','tiny','small','medium','large','huge','gargantuan','colossal')
        a_size,t_size=actor.data.get('size_category'),target.data.get('size_category')
        if a_size not in order or t_size not in order:
            return ActionProposal(action.id,actor.id,(target.id,),'size_category_unknown')
        attacker_modifier=(actor.data['abilities'].get('STR',10)-10)//2+4*(order.index(a_size)-order.index(t_size))
        if contact_kind == 'grab':
            attacker_modifier+=2
        defender_ability=action.data.get('trip_defender_ability')
        defender_modifier=(target.data['abilities'].get(defender_ability,10)-10)//2+4*(order.index(t_size)-order.index(a_size))
        attacker=sum(rng.roll('1d6') for _ in range(3))+attacker_modifier-priority_penalty
        defender=sum(rng.roll('1d6') for _ in range(3))+defender_modifier
        if attacker<=defender:
            return ActionProposal(action.id,actor.id,(target.id,),'failed',metadata=metadata)
        effects.append(GrappleStateEffect(action.id,target.id,actor.id,action.id,
            'posture','set',None,None,'lying'))
        return ActionProposal(action.id,actor.id,(target.id,),'success',tuple(effects),metadata=metadata)
    if event_type in ('takedown','reverse','pin'):
        control = next((row for row in snapshot.grapple_controls
                    if row[0] == action.data['grapple_id'] and row[1] == actor.id
                    and row[2] == target.id),None)
    else:
        control = next((row for row in snapshot.grapple_controls
                    if row[0] == action.data['grapple_id'] and row[1] == target.id
                    and row[2] == actor.id),None)
    if control is None: return ActionProposal(action.id,actor.id,(target.id,),'no_control')
    if control[5] != action.boundary: return ActionProposal(action.id,actor.id,(target.id,),'unavailable')
    if event_type in ('takedown','reverse','pin'):
        position=control[6] if len(control)>6 else 'standing'
        if event_type=='takedown':
            if position!='standing':return ActionProposal(action.id,actor.id,(target.id,),'wrong_position')
            goal='advantaged_takedown_top'
        elif event_type=='reverse':
            if position not in ('disadvantaged_takedown_bottom','pin_bottom'):
                return ActionProposal(action.id,actor.id,(target.id,),'wrong_position')
            goal='advantaged_takedown_top' if position=='disadvantaged_takedown_bottom' else 'pin_top'
        else:
            if position!='advantaged_takedown_top':return ActionProposal(action.id,actor.id,(target.id,),'wrong_position')
            goal=action.data['grapple_position']
        if event_type in ('takedown','reverse'):
            order=('diminutive','tiny','small','medium','large','huge','gargantuan','colossal')
            sizes=(actor.data.get('size_category'),target.data.get('size_category'))
            if any(value not in order for value in sizes):
                return ActionProposal(action.id,actor.id,(target.id,),'size_category_unknown')
            if order.index(sizes[1])-order.index(sizes[0])>1:
                return ActionProposal(action.id,actor.id,(target.id,),'size_limit')
        allowed, bonus = _grapple_capacity_and_bonus(snapshot, actor, target)
        if not allowed:
            return ActionProposal(action.id,actor.id,(target.id,),'capacity_exceeded')
        if _grapple_roll(rng,actor,bonus=bonus-priority_penalty)<=_grapple_roll(rng,target):
            return ActionProposal(action.id,actor.id,(target.id,),'failed')
        effects.append(GrappleStateEffect(action.id,target.id,actor.id,control[0],
            'control','transition',None,action.boundary+6,goal))
        if event_type=='takedown':
            effects.append(GrappleStateEffect(action.id,target.id,actor.id,action.id,
                'posture','set',None,None,'lying' if action.data.get('grapple_position')=='prone' else 'kneeling'))
        if event_type=='pin':
            effects.append(GrappleStateEffect(action.id,target.id,actor.id,action.id,
                'posture','set',None,None,'lying'))
        return ActionProposal(action.id,actor.id,(target.id,), 'success',tuple(effects))
    escape = _grapple_roll(rng,actor,escape=True,bonus=-priority_penalty)
    allowed, bonus = _grapple_capacity_and_bonus(snapshot, target, actor)
    if not allowed:
        return ActionProposal(action.id,actor.id,(target.id,),'capacity_exceeded')
    resist = _grapple_roll(rng,target,bonus=bonus)
    if escape > resist:
        position=control[6] if len(control)>6 else 'standing'
        if position == 'pin_top':
            effects.append(GrappleStateEffect(action.id,actor.id,target.id,control[0],
                'control','transition',None,action.boundary+6,'advantaged_takedown_top'))
        elif position == 'pin_bottom':
            effects.append(GrappleStateEffect(action.id,actor.id,target.id,control[0],
                'control','transition',None,action.boundary+6,'disadvantaged_takedown_bottom'))
        elif position == 'advantaged_takedown_top':
            effects.append(GrappleStateEffect(action.id,actor.id,target.id,control[0],
                'control','transition',None,action.boundary+6,'standing'))
        else:
            effects.append(GrappleStateEffect(action.id,actor.id,target.id,control[0],
                'control','release',None,None))
        return ActionProposal(action.id,actor.id,tuple(sorted((actor.id,target.id))),
            'success',tuple(effects))
    effects.append(GrappleStateEffect(action.id,actor.id,target.id,control[0],
        'control','maintain',None,action.boundary+6))
    return ActionProposal(action.id,actor.id,tuple(sorted((actor.id,target.id))),
        'failed',tuple(effects))


def _object_strike(snapshot, action, rng):
    """Resolve the adopted immobile, nonmagical Object branch transactionally."""
    actor, target = snapshot.entity(action.actor_id), snapshot.entity(action.target_id)
    priority_penalty = action.data.get('multiple_action_priority', 0) or 0
    weapon = snapshot.entity(action.instrument_id)
    if action.data['event_type'] == 'break weapon':
        defender = target
        victim_weapon = snapshot.entity(action.data['break_weapon_id'])
        following = [row for row in snapshot.actions.values()
            if row.family == 'melee' and row.actor_id == defender.id
            and row.target_id == actor.id and row.instrument_id == victim_weapon.id
            and row.boundary == action.boundary + 1]
        if len(following) != 1:
            return ActionProposal(action.id,actor.id,(defender.id,),
                'no_prior_second_attack',metadata=())
        distance=snapshot.distance(actor.id,defender.id)
        metadata=() if distance is None else (('distance',distance),)
        if actor.hp<=0 or actor.data['fatigue_level']>=5:
            return ActionProposal(action.id,actor.id,(defender.id,),'unable_to_act',metadata=metadata)
        if (victim_weapon.id not in defender.data['held'] or weapon.id not in actor.data['held']
                or weapon.hp<=0 or victim_weapon.hp<=0):
            return ActionProposal(action.id,actor.id,(defender.id,),'weapon_unavailable',metadata=metadata)
        status,distance=snapshot.melee_status(action)
        if status!='in_reach':
            return ActionProposal(action.id,actor.id,(defender.id,),status,metadata=metadata)
        hardness=victim_weapon.data.get('hardness')
        source_hardness=weapon.data.get('hardness')
        if any(type(x) not in (int,float) or x<0 for x in (hardness,source_hardness)):
            return ActionProposal(action.id,actor.id,(defender.id,),'unsupported_object',metadata=metadata)
        motion='S'; attack_die=weapon.data['attacks'][motion]['d']
        following_motion = following[0].data['event_type']
        defender_die=victim_weapon.data['attacks']['S' if following_motion == 'swing' else 'T']['d']
        skill=actor.data['weapon_skills'].get(weapon.data['original_type'],0)
        adjustment=actor.data['fatigue_adjustments'][actor.data['fatigue_level']]['ability_adjustment']
        if adjustment is None:
            return ActionProposal(action.id,actor.id,(defender.id,),'unable_to_act',metadata=metadata)
        def hits(roll,dc):
            return attack_hits(roll,skill+actor.data['strategy']['attack']-priority_penalty-defender.data['strategy']['attack'],0,dc-adjustment)
        outcome=hit_outcome(snapshot.difficulty,rng.roll,hits,lambda dc:True,lambda dc:True)
        effects=[]
        if outcome in ('normal','critical'):
            own_raw=rng.roll(f'1d{attack_die}')+action.data['strategy']['extra_damage']
            if outcome=='critical':own_raw+=rng.roll(f'1d{attack_die}')
            other_raw=(rng.roll(f'1d{defender_die}')
                       +following[0].data['strategy']['extra_damage'])
            total_raw=own_raw+other_raw
            threshold=hardness+victim_weapon.hp
            breaks=total_raw>=threshold
            victim_loss=victim_weapon.hp if breaks else (total_raw-hardness if total_raw>hardness else 0)
            effects.append(DamageEffect(action.id,victim_weapon.id,victim_loss,'object'))
            own_threshold=source_hardness+weapon.hp
            if breaks and own_threshold< threshold:
                effects.append(DamageEffect(action.id,weapon.id,weapon.hp,'object'))
            outcome='broken' if breaks else 'normal'
        targets=tuple(sorted({defender.id,*(e.target_id for e in effects)}))
        return ActionProposal(action.id,actor.id,targets,outcome,tuple(effects),metadata=metadata)
    distance = snapshot.distance(actor.id, target.id)
    metadata = () if distance is None else (('distance', distance),)
    if actor.hp <= 0 or actor.data['fatigue_level'] >= 5:
        return ActionProposal(action.id, actor.id, (target.id,), 'unable_to_act', metadata=metadata)
    hardness = target.data.get('hardness')
    if type(hardness) not in (int, float) or hardness < 0 or target.hp <= 0:
        return ActionProposal(action.id, actor.id, (target.id,), 'unsupported_object', metadata=metadata)
    # The first native adapter deliberately handles unattended, stationary,
    # non-magical Objects. Attended/magic saving-throw branches need their
    # subject-specific save rules and are rejected before any random draw.
    if target.data.get('parent_container_id') is not None:
        return ActionProposal(action.id, actor.id, (target.id,), 'attended_object', metadata=metadata)
    if weapon.category != 'weapon' or weapon.hp <= 0 or action.instrument_id not in actor.data['held']:
        return ActionProposal(action.id, actor.id, (target.id,), 'weapon_unavailable', metadata=metadata)
    if distance is None or actor.position is None or target.position is None:
        return ActionProposal(action.id, actor.id, (target.id,), 'unplaced')
    if distance > action.data['reach']:
        return ActionProposal(action.id, actor.id, (target.id,), 'out_of_reach', metadata=metadata)
    path = snapshot.physical_path(actor.id, target.id)
    if path is not None and path.intersections:
        return ActionProposal(action.id, actor.id, (target.id,), 'blocked', metadata=metadata)
    if path is not None and path.unmodeled_entity_ids:
        return ActionProposal(action.id, actor.id, (target.id,), 'uncertain_path', metadata=metadata)
    motion = action.data['object_motion']
    attack = weapon.data['attacks']['S' if motion == 'swing' else 'T']['d']
    adjustment = actor.data['fatigue_adjustments'][actor.data['fatigue_level']]['ability_adjustment']
    if adjustment is None:
        return ActionProposal(action.id, actor.id, (target.id,), 'unable_to_act', metadata=metadata)
    skill = actor.data['weapon_skills'].get(weapon.data['original_type'], 0)
    def hits(roll, dc):
        return attack_hits(roll, skill + actor.data['strategy']['attack'] - priority_penalty, 0, dc - adjustment)
    # An immobile unattended object has no independent save; doubled natural
    # 20 uses the ordinary critical confirmation rule against that same DC.
    outcome = hit_outcome(snapshot.difficulty, rng.roll, hits,
                          lambda dc: True, lambda dc: True)
    effects = ()
    if outcome in ('normal', 'critical'):
        potential = attack
        raw = [0]
        def collect(amount, critical): raw[0] += amount + critical
        damage_path(outcome, potential, action.data['strategy']['extra_damage'], rng.roll,
                    lambda amount: amount, lambda amount: amount, collect)
        amount = raw[0] - hardness if raw[0] > hardness else 0
        effects = (DamageEffect(action.id, target.id, amount, 'object'),)
    return ActionProposal(action.id, actor.id, (target.id,), outcome,
                          effects, metadata=metadata)


def _disarm(snapshot, action, rng):
    actor,defender=snapshot.entity(action.actor_id),snapshot.entity(action.target_id)
    attacker_weapon=(snapshot.entity(action.instrument_id)
                     if action.instrument_id is not None else None)
    target_weapon=snapshot.entity(action.data['disarm_weapon_id'])
    distance=snapshot.distance(actor.id,defender.id)
    metadata=[] if distance is None else [('distance',distance)]
    if actor.hp<=0 or actor.data['fatigue_level']>=5:
        return ActionProposal(action.id,actor.id,(defender.id,),'unable_to_act',metadata=tuple(metadata))
    if (target_weapon.hp<=0 or target_weapon.id not in defender.data['held']):
        return ActionProposal(action.id,actor.id,(defender.id,),'weapon_unavailable',metadata=tuple(metadata))
    unarmed = attacker_weapon is None
    if unarmed:
        if ((actor.data['skills'].get('unarmed combat',0) or 0)<=0
                or not any(hand in ('left hand','right hand') and value is None
                           for hand,value in actor.data.get('body_parts',{}).items())):
            return ActionProposal(action.id,actor.id,(defender.id,),'weapon_unavailable',metadata=tuple(metadata))
        from melee_combat import reference_arm_length_inches,INCHES_TO_METERS
        try:
            reach=reference_arm_length_inches(height_inches=actor.data.get('height'),
                length_inches=actor.data.get('length'),size_category=actor.data.get('size_category'))*INCHES_TO_METERS
        except ValueError:
            return ActionProposal(action.id,actor.id,(defender.id,),'unsupported_reach',metadata=tuple(metadata))
        if not math.isclose(action.data.get('reach',-1),reach,rel_tol=1e-12,abs_tol=1e-12):
            raise EvaluationIntegrityError('unarmed Disarm reach differs from native arm dimensions')
    elif attacker_weapon.hp<=0 or action.instrument_id not in actor.data['held']:
        return ActionProposal(action.id,actor.id,(defender.id,),'weapon_unavailable',metadata=tuple(metadata))
    status,distance=snapshot.melee_status(action)
    if status!='in_reach':
        return ActionProposal(action.id,actor.id,(defender.id,),status,metadata=tuple(metadata))
    skill=((actor.data['skills'].get('unarmed combat',0) or 0) if unarmed else
           actor.data['weapon_skills'].get(attacker_weapon.data['original_type'],0))
    if skill <= (0 if unarmed else 1):
        return ActionProposal(action.id,actor.id,(defender.id,),'weapon_unavailable',metadata=tuple(metadata))
    adjustment=actor.data['fatigue_adjustments'][actor.data['fatigue_level']]['ability_adjustment']
    if adjustment is None:
        return ActionProposal(action.id,actor.id,(defender.id,),'unable_to_act',metadata=tuple(metadata))
    priority_penalty=action.data.get('multiple_action_priority',0) or 0
    attacker_total=rng.roll('1d20')+skill+actor.data['strategy']['attack']-priority_penalty-adjustment
    grappled=any(row[2]==defender.id for row in snapshot.grapple_controls)
    defender_total=rng.roll('1d20')+defender.data['strategy']['defense']+(0 if grappled else 5)
    margin=attacker_total-defender_total
    metadata.extend((('margin',margin),('maximum_landing_hexes',max(0,margin//3))))
    if margin<=0:
        return ActionProposal(action.id,actor.id,(defender.id,),'failure',metadata=tuple(metadata))
    if defender.position is None:
        return ActionProposal(action.id,actor.id,(defender.id,),'unplaced',metadata=tuple(metadata[:-1]))
    effect=DropObjectEffect(action.id,target_weapon.id,defender.id,defender.position.as_tuple())
    return ActionProposal(action.id,actor.id,tuple(sorted((defender.id,target_weapon.id))),
        'disarmed',(effect,),metadata=tuple(metadata))


def pickup_eligibility(snapshot, action):
    """Return the r64 ordinary failure code or ``None`` when a pickup is eligible.

    The test is entirely against the common post-movement snapshot. Arena hex
    membership is used only as the adopted coarse access convention; this
    helper does not infer body contact, collision, or reach geometry.
    """
    from arena_hex_map import ArenaHexLayout

    actor, target = snapshot.entity(action.actor_id), snapshot.entity(action.target_id)
    if actor.category != 'being' or target.category not in ('object', 'weapon', 'armor'):
        return 'unavailable'
    if _helpless(actor):
        return 'unable_to_act'
    if actor.position is None or target.position is None:
        return 'unplaced' if target.data.get('parent_container_id') is None else 'unavailable'
    if target.data.get('parent_container_id') is not None:
        return 'unavailable'
    inventory_refs = set()
    for entity in snapshot.entities.values():
        if entity.category != 'being':
            continue
        data = entity.data
        inventory_refs.update(data.get('possessions', ()))
        inventory_refs.update(data.get('weapons', ()))
        inventory_refs.update(value for value in data.get('body_parts', {}).values()
                              if value is not None)
        armor_id = data.get('armor_id')
        if armor_id is not None:
            inventory_refs.add(armor_id)
    if action.target_id in inventory_refs:
        return 'unavailable'
    if any(entity.data.get('parent_container_id') == action.target_id
           for entity in snapshot.entities.values()):
        return 'unsupported_contents'

    try:
        layout = ArenaHexLayout.rectangle(action.data['map_width_cells'],
                                          action.data['map_height_cells'])
        actor_cell = layout.cell_at_position(actor.position)
        object_cell = layout.cell_at_position(target.position)
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        raise UnsupportedEvaluation('Pick up snapshot lacks its reviewed Arena hex convention') from exc
    if actor_cell is None or object_cell is None or actor_cell != object_cell:
        return 'inaccessible'

    weight = target.data.get('weight')
    if (type(weight) not in (int, float) or not math.isfinite(weight) or weight <= 0):
        return 'unknown_weight'
    from movement_intent import _HEAVY_LOAD_UPPER_LB
    abilities, adjustments = actor.data.get('abilities'), actor.data.get('fatigue_adjustments')
    fatigue = actor.data.get('fatigue_level')
    fatigue_row = adjustments.get(fatigue) if hasattr(adjustments, 'get') else None
    adjustment = fatigue_row.get('ability_adjustment') if hasattr(fatigue_row, 'get') else None
    strength = abilities.get('STR') if hasattr(abilities, 'get') else None
    if (type(strength) not in (int, float) or not math.isfinite(strength)
            or type(adjustment) is not int):
        return 'unknown_capacity'
    effective_strength = strength + adjustment
    if type(effective_strength) is not int or effective_strength not in _HEAVY_LOAD_UPPER_LB:
        return 'unknown_capacity'

    inventory = (tuple(actor.data.get('possessions', ()))
                 + tuple(actor.data.get('weapons', ()))
                 + tuple(value for value in actor.data.get('body_parts', {}).values()
                         if value is not None)
                 + (() if actor.data.get('armor_id') is None else (actor.data['armor_id'],)))
    pending = list(dict.fromkeys(inventory))
    visited = set()
    total = 0.0
    while pending:
        object_id = pending.pop()
        if object_id in visited:
            continue
        visited.add(object_id)
        item = snapshot.entity(object_id)
        if item.category in ('being', 'statistical_group'):
            return 'unknown_capacity'
        item_weight = item.data.get('weight')
        if (type(item_weight) not in (int, float) or not math.isfinite(item_weight)
                or item_weight < 0):
            return 'unknown_capacity'
        total += float(item_weight)
        pending.extend(entity.id for entity in snapshot.entities.values()
                       if entity.data.get('parent_container_id') == object_id)
    limit = _HEAVY_LOAD_UPPER_LB[effective_strength]
    if total + float(weight) > limit:
        return 'over_capacity'
    return None


def ready_weapon_eligibility(snapshot, action):
    """Return a bounded initial-readying refusal code from the common snapshot."""
    actor, target = snapshot.entity(action.actor_id), snapshot.entity(action.target_id)
    if actor.category != 'being' or target.category != 'weapon':
        return 'unavailable'
    if _helpless(actor):
        return 'unable_to_act'
    if target.data.get('original_type') != 'Dagger':
        return 'unsupported_weapon'
    if action.data.get('hand') not in ('left hand', 'right hand'):
        return 'hand_unavailable'
    body_parts = actor.data.get('body_parts')
    if type(body_parts) not in (dict, MappingProxyType) or action.data['hand'] not in body_parts:
        return 'hand_unavailable'
    if body_parts[action.data['hand']] is not None:
        return 'hand_unavailable'
    if action.target_id not in actor.data.get('possessions', ()):
        return 'unavailable'
    if target.data.get('parent_container_id') != actor.id or target.position is not None:
        return 'unavailable'
    if (action.target_id == actor.data.get('armor_id')
            or action.target_id in actor.data.get('weapons', ())
            or action.target_id in tuple(body_parts.values())):
        return 'already_ready'
    for entity in snapshot.entities.values():
        if entity.category != 'being' or entity.id == actor.id:
            continue
        data = entity.data
        if (action.target_id in data.get('possessions', ())
                or action.target_id in data.get('weapons', ())
                or action.target_id in tuple(data.get('body_parts', {}).values())
                or action.target_id == data.get('armor_id')):
            return 'unavailable'
    location = target.data.get('draw_location')
    if (type(location) not in (dict, MappingProxyType)
            or location.get('kind') != 'worn_sheath'
            or location.get('owner_id') != actor.id):
        return 'unavailable'
    return None


def ready_preparation_eligibility(snapshot, action):
    """Validate a motion-specific Ready Action against the common snapshot."""
    actor, weapon = snapshot.entity(action.actor_id), snapshot.entity(action.target_id)
    if actor.category != 'being' or weapon.category != 'weapon':
        return 'unavailable'
    if _helpless(actor):
        return 'unable_to_act'
    pole_set = action.data.get('ready_motion') == 'set pole'
    motion = 'thrust' if pole_set else action.data.get('ready_motion')
    attacks = weapon.data.get('attacks', {})
    key = {'swing': 'S', 'thrust': 'T'}.get(motion)
    if key is None or type(attacks) not in (dict, MappingProxyType) or attacks.get(key) is None:
        return 'unsupported_motion'
    if (action.target_id not in actor.data.get('weapons', ())
            or action.target_id not in actor.data.get('held', ())):
        return 'unavailable'
    expected_seconds = max(1, 4 - _timing_adjustment(action.data.get('strategy', {})))
    if pole_set and (weapon.data.get('original_type') not in snapshot.pole_weapon_names
                     or key != 'T' or action.data.get('readying_seconds') != expected_seconds):
        return 'unsupported_pole_set'
    if weapon.data.get('ready_preparation') is not None:
        return 'already_ready'
    if type(action.data.get('readying_seconds')) is not int or action.data['readying_seconds'] < 1:
        return 'unsupported_timing'
    return None


def resolve_end_run_contest(snapshot, action, rng):
    """Resolve the adopted End Run contest from one movement-phase snapshot."""
    actor, target = snapshot.entity(action.actor_id), snapshot.entity(action.target_id)
    data = action.data
    if actor.position is None or target.position is None:
        return ActionProposal(action.id, actor.id, (target.id,), 'unplaced')
    if data.get('end_run_occupant_willing') is True:
        return ActionProposal(action.id, actor.id, (target.id,), 'success')
    actor_dex, target_dex = (actor.data['abilities'].get('DEX'),
                             target.data['abilities'].get('DEX'))
    if type(actor_dex) is not int or type(target_dex) is not int:
        return ActionProposal(action.id, actor.id, (target.id,), 'dexterity_unknown')
    target_facing = target.data.get('hex_facing')
    if type(target_facing) is not int:
        return ActionProposal(action.id, actor.id, (target.id,), 'facing_unknown')
    from hex_facing import vector_is_behind
    behind = vector_is_behind(target_facing,
        (actor.position.x-target.position.x,
         actor.position.y-target.position.y,
         actor.position.z-target.position.z))
    immobilized = (target.data.get('states', {}).get('immobilized') is True
                   or any(len(row) > 6 and row[2] == target.id
                          and row[6] in ('pin_top', 'pin_bottom')
                          for row in snapshot.grapple_controls))
    if behind or immobilized:
        roll = sum(rng.roll('1d6') for _ in range(3))
        outcome = 'success' if roll <= actor_dex else 'failed'
        return ActionProposal(action.id, actor.id, (target.id,), outcome,
            metadata=(('rolls', (roll,)), ('initiator_total', roll),
                      ('occupant_total', actor_dex),
                      ('reason', 'behind_or_immobilized')))
    sizes = ('diminutive','tiny','small','medium','large','huge','gargantuan','colossal')
    actor_size, target_size = (actor.data.get('size_category'),
                               target.data.get('size_category'))
    if actor_size not in sizes or target_size not in sizes:
        return ActionProposal(action.id, actor.id, (target.id,), 'size_unknown')
    size_bonus = 2 * max(0, sizes.index(target_size)-sizes.index(actor_size))
    penalty = data.get('multiple_action_priority', 0) or 0
    if type(penalty) is not int or penalty < 0:
        raise EvaluationIntegrityError('End Run Multiple-action priority penalty is invalid')
    actor_rolls = tuple(rng.roll('1d6') for _ in range(3))
    target_rolls = tuple(rng.roll('1d6') for _ in range(3))
    actor_total = sum(actor_rolls) + (actor_dex-10)//2 + size_bonus - penalty
    target_total = sum(target_rolls) + (target_dex-10)//2
    outcome = 'success' if actor_total > target_total else 'failed'
    return ActionProposal(action.id, actor.id, (target.id,), outcome,
        metadata=(('rolls', actor_rolls+target_rolls),
                  ('initiator_total', actor_total), ('occupant_total', target_total),
                  ('reason', 'opposed_dexterity')))


def _end_run(snapshot, action, rng):
    result = action.data.get('end_run_phase_result')
    if (type(result) is not tuple or len(result) != 2
            or type(result[0]) is not str or type(result[1]) is not tuple):
        raise EvaluationIntegrityError('End Run requires an authoritative movement-phase result')
    outcome, metadata = result
    return ActionProposal(action.id, action.actor_id, (action.target_id,), outcome,
                          metadata=metadata)


def _activity(snapshot, action, rng):
    actor = snapshot.entity(action.actor_id)
    effects = []
    metadata = []
    if action.family == 'run':
        start = action.data['start_position']
        if start is None and not action.data['started']:
            raise EvaluationIntegrityError('Run has no activity start metadata')
        if start is None or actor.position is None:
            outcome = 'unplaced'
        else:
            displacement = math.dist(start.as_tuple(), actor.position.as_tuple())
            outcome = run_outcome(displacement, action.data['minimum_distance'])
            metadata.append(('displacement', displacement))
            if displacement:
                effects.append(PracticeEffect(action.id, actor.id, 'run', action.data['practice_experience']))
    elif action.family == 'throw':
        from throwing import release_velocity_yd_s, project_drag_free_trajectory
        projectile = snapshot.entity(action.instrument_id)
        if actor.position is None or projectile.position is None:
            outcome = 'unplaced'
        elif action.instrument_id not in actor.data.get('possessions', ()):
            outcome = 'unavailable'
        else:
            height = actor.data['height']
            speed = release_velocity_yd_s(strength=actor.data['abilities']['STR'],
                throw_skill_level=actor.data['skills'].get('throw', 0),
                projectile_weight_lb=projectile.data['weight'],
                heavy_load_reference_lb=action.data['heavy_load_reference_lb'],
                height_inches=height)
            release = CartesianPosition(actor.position.x, actor.position.y,
                actor.position.z + height * 0.0254)
            trajectory = project_drag_free_trajectory(release_velocity_yd_s=speed,
                release_position=release, landing_elevation_m=action.data['landing_elevation_m'],
                elevation_degrees=action.data['elevation_degrees'],
                azimuth_degrees=action.data['azimuth_degrees'])
            effects.append(ProjectileReleaseEffect(action.id, projectile.id,
                snapshot.boundary, release.as_tuple(), trajectory.velocity_m_s,
                snapshot.boundary + trajectory.flight_time_s,
                trajectory.landing_position.as_tuple(), action.data['landing_elevation_m']))
            outcome = 'released'
            metadata.extend((('release_speed_yd_s', speed),
                             ('impact_time', snapshot.boundary + trajectory.flight_time_s)))
    else:
        target = snapshot.entity(action.target_id)
        distance = snapshot.distance(actor.id, target.id)
        if distance is None:
            outcome = 'unplaced'
        elif target.geometry is None:
            outcome = 'unmodeled_target'
        else:
            path = snapshot.path(actor.id, target.id)
            metadata.append(('path_status', None if path is None else path.status))
            if path is None or not path.clear:
                outcome = 'no_clear_path'
            else:
                roll = action.data['declared_roll']
                if roll is None:
                    roll = rng.roll('1d20')
                metadata.append(('roll', roll))
                from discovery import SpottingConditions, discovery_dc, racial_discovery_bonus
                conditions = SpottingConditions(action.data['spotting_conditions'])
                base_dc = discovery_dc(target.data['discovery_dc'])
                adjustment = conditions.dc_adjustment
                racial = racial_discovery_bonus(actor.data['race'], 'spot')
                dc = base_dc + adjustment
                metadata.extend((('discovery_dc', base_dc), ('spotting_dc_adjustment', adjustment),
                                 ('racial_action_bonus', racial), ('effective_dc', dc)))
                outcome = 'success' if roll + racial >= dc else 'failure'
                if outcome == 'success':
                    effects.append(AwarenessEffect(action.id, actor.id, target.id, distance, None))
    affected = (() if action.target_id is None else (action.target_id,))
    if action.family == 'throw':
        affected = tuple(dict.fromkeys(affected + tuple(effect.target_id for effect in effects)))
    return ActionProposal(action.id, actor.id, affected,
                          outcome, tuple(effects), metadata=tuple(metadata))


def evaluate_snapshot(snapshot, action_ids=None):
    """Return all-or-nothing proposals/RNG trace; never publish anything.

    Stable native priority then accepted queue order allocates draws. All due
    designated defenses must be included explicitly when requesting a subset.
    Repeating this call allocates from the same frozen initial RNG state.
    """
    if type(snapshot) is not EvaluationSnapshot:
        raise TypeError('expected native EvaluationSnapshot')
    ids = tuple(action_ids) if action_ids is not None else tuple(a.id for a in snapshot.actions.values()
        if a.boundary == snapshot.boundary and a.lifecycle != 'paused')
    if len(set(ids)) != len(ids):
        raise EvaluationIntegrityError('duplicate evaluation identity')
    selected = [snapshot.actions[key] for key in ids]
    for action in selected:
        if action.boundary != snapshot.boundary or action.start >= snapshot.boundary:
            raise EvaluationIntegrityError('Action not due at this evaluation boundary')
        if action.family in ('melee', 'combat'):
            required = {d.id for d in snapshot.actions.values() if d.family == 'defense'
                and d.lifecycle == 'pending' and d.boundary == snapshot.boundary
                and d.data['target_action_id'] == action.id}
            if not required.issubset(ids):
                raise EvaluationIntegrityError('missing explicit designated defense dependency')
    if any(a.family not in ('combat', 'melee', 'object_strike', 'disarm', 'grappling', 'end_run', 'defense', 'run', 'spot', 'throw', 'pickup', 'ready_weapon', 'ready_preparation', 'delay') for a in selected):
        raise UnsupportedEvaluation('objective-only declarations require their separate inactive context; complete Action effects remain unsupported')
    pickup_status = {action.id: pickup_eligibility(snapshot, action)
                     for action in selected if action.lifecycle == 'pending'
                     and action.family == 'pickup'}
    ready_status = {action.id: ready_weapon_eligibility(snapshot, action)
                    for action in selected if action.lifecycle == 'pending'
                    and action.family == 'ready_weapon'}
    preparation_status = {action.id: ready_preparation_eligibility(snapshot, action)
                    for action in selected if action.lifecycle == 'pending'
                    and action.family == 'ready_preparation'}
    pickup_by_object = {}
    for action in selected:
        if (action.lifecycle == 'pending' and action.family == 'pickup'
                and pickup_status[action.id] is None):
            pickup_by_object.setdefault(action.target_id, []).append(action.id)
    ready_claims = {}
    for action in selected:
        if (action.lifecycle == 'pending' and action.family == 'ready_weapon'
                and ready_status[action.id] is None):
            ready_claims.setdefault((action.actor_id, action.data['hand']), []).append(action.id)
            ready_claims.setdefault(('weapon', action.target_id), []).append(action.id)
    preparation_claims = {}
    for action in selected:
        if (action.lifecycle == 'pending' and action.family == 'ready_preparation'
                and preparation_status[action.id] is None):
            preparation_claims.setdefault(action.target_id, []).append(action.id)
    # Revision-14 coupled pole interception. Both attacks use this same
    # frozen snapshot; evaluate a declared prepared-pole attack immediately
    # before its matching charge so the charge's classification is known
    # without publishing either attack's effects first.
    pole_pairs = {}
    pole_charge_pairs = {}
    for charge in selected:
        if (charge.family != 'melee' or charge.lifecycle != 'pending'
                or charge.data.get('charge') is not True):
            continue
        velocity = snapshot.motion_velocities_m_s.get(charge.actor_id)
        target_velocity = snapshot.motion_velocities_m_s.get(charge.target_id, (0.0, 0.0, 0.0))
        if velocity is None:
            continue
        speed = math.dist(velocity, target_velocity) / 0.9144
        if speed < 4.0:
            continue
        for pole in selected:
            if (pole.family != 'melee' or pole.lifecycle != 'pending'
                    or pole.data.get('charge') is True or pole.data.get('event_type') != 'thrust'
                    or pole.actor_id != charge.target_id or pole.target_id != charge.actor_id
                    or pole.instrument_id is None):
                continue
            preparation = snapshot.entity(pole.instrument_id).data.get('ready_preparation')
            if (preparation is None or preparation.get('pole_set') is not True
                    or preparation.get('owner_id') != pole.actor_id
                    or preparation.get('motion') != 'thrust'
                    or preparation.get('completed_at', snapshot.boundary) > pole.start):
                continue
            pole_pairs[pole.id] = (charge.id, speed)
            pole_charge_pairs.setdefault(charge.id, []).append(pole.id)
    rng = _ProvisionalRandom(snapshot.rng_state)
    proposals = []
    defense_effects = []
    ordered = sorted(selected, key=lambda a: (a.priority, a.order))
    # The adopted coupled interaction is declared as one adjudication. Give
    # the set-pole attack the first deterministic draw allocation within its
    # pair even if its declaration followed the charge.
    for pole_id, (charge_id, _speed) in pole_pairs.items():
        pole = next(row for row in ordered if row.id == pole_id)
        charge = next(row for row in ordered if row.id == charge_id)
        if ordered.index(pole) > ordered.index(charge):
            ordered.remove(pole)
            ordered.insert(ordered.index(charge), pole)
    successful_pole_interceptions = set()
    for action in ordered:
        rng.action_id = action.id
        if action.lifecycle == 'cancelled':
            proposal = ActionProposal(action.id, action.actor_id,
                () if action.target_id is None else (action.target_id,), 'interrupted')
        elif action.family == 'defense':
            proposal = _defense(snapshot, action, rng)
            defense_effects.extend(proposal.defenses)
        elif action.family in ('combat', 'melee'):
            pole_pair = pole_pairs.get(action.id)
            intercepted = (action.id in pole_charge_pairs
                and any(pole_id in successful_pole_interceptions
                        for pole_id in pole_charge_pairs[action.id]))
            proposal = _combat(snapshot, action, rng,
                tuple(d for d in defense_effects if d.strike_id == action.id),
                pole_set_charge=pole_pair is not None,
                pole_charge_speed=None if pole_pair is None else pole_pair[1],
                charge_intercepted=intercepted)
            if pole_pair is not None and proposal.outcome in ('normal', 'critical'):
                successful_pole_interceptions.add(action.id)
        elif action.family == 'object_strike':
            proposal = _object_strike(snapshot, action, rng)
        elif action.family == 'disarm':
            proposal = _disarm(snapshot,action,rng)
        elif action.family == 'grappling':
            proposal = _grappling(snapshot,action,rng,
                tuple(d for d in defense_effects if d.strike_id == action.id))
        elif action.family == 'pickup':
            status = pickup_status[action.id]
            if status is not None:
                proposal = ActionProposal(action.id, action.actor_id, (action.target_id,), status)
            elif len(pickup_by_object[action.target_id]) > 1:
                proposal = ActionProposal(action.id, action.actor_id, (action.target_id,), 'contested')
            else:
                effect = PickupEffect(action.id, action.actor_id, action.target_id)
                proposal = ActionProposal(action.id, action.actor_id,
                    tuple(sorted((action.target_id, action.actor_id), key=str)), 'success', (effect,))
        elif action.family == 'ready_weapon':
            status = ready_status[action.id]
            if status is not None:
                proposal = ActionProposal(action.id, action.actor_id, (action.target_id,), status)
            elif any(len(ready_claims[key]) > 1 for key in (
                    (action.actor_id, action.data['hand']), ('weapon', action.target_id))):
                proposal = ActionProposal(action.id, action.actor_id, (action.target_id,), 'contested')
            else:
                effect = ReadyWeaponEffect(action.id, action.actor_id, action.target_id,
                                           action.data['hand'])
                proposal = ActionProposal(action.id, action.actor_id,
                    tuple(sorted((action.target_id, action.actor_id), key=str)), 'success', (effect,))
        elif action.family == 'ready_preparation':
            status = preparation_status[action.id]
            if status is not None:
                proposal = ActionProposal(action.id, action.actor_id, (action.target_id,), status)
            elif len(preparation_claims[action.target_id]) > 1:
                proposal = ActionProposal(action.id, action.actor_id, (action.target_id,), 'contested')
            else:
                effect = ReadyPreparationEffect(action.id, action.actor_id, action.target_id,
                    ('thrust' if action.data['ready_motion'] == 'set pole'
                     else action.data['ready_motion']), action.data['readying_seconds'],
                    action.data['ready_motion'] == 'set pole')
                proposal = ActionProposal(action.id, action.actor_id,
                    tuple(sorted((action.target_id, action.actor_id), key=str)), 'success', (effect,))
        elif action.family == 'end_run':
            proposal = _end_run(snapshot, action, rng)
        elif action.family == 'delay':
            effect = DelayDefenseEffect(action.id, action.actor_id,
                                         action.data['strategy'].get('defense', 0))
            proposal = ActionProposal(action.id, action.actor_id,
                (action.actor_id,), 'success', (effect,))
        else:
            proposal = _activity(snapshot, action, rng)
        if (action.lifecycle == 'pending' and action.instrument_id is not None
                and action.family not in ('ready_preparation', 'ready_weapon', 'delay')):
            instrument = snapshot.entity(action.instrument_id)
            preparation = instrument.data.get('ready_preparation')
            if (instrument.category == 'weapon' and preparation is not None
                    and preparation.get('owner_id') == action.actor_id):
                consume = ReadyConsumptionEffect(action.id, action.actor_id,
                    action.instrument_id, preparation['ready_action_id'])
                proposal = replace(proposal, target_ids=tuple(sorted(set(proposal.target_ids) | {action.actor_id})),
                                   effects=proposal.effects + (consume,))
        proposals.append(proposal)
    # Adopted revision 36–37: separately declared Grapple actions whose
    # successful same-boundary results prescribe incompatible states of the
    # same control are rerolled as one fixed group, without advancing time or
    # changing any eligibility/modifier inputs from this snapshot.
    by_id = {proposal.action_id: proposal for proposal in proposals}
    control_groups = {}
    for proposal in proposals:
        if proposal.outcome != 'success':
            continue
        action = snapshot.actions[proposal.action_id]
        if action.family != 'grappling':
            continue
        for effect in proposal.effects:
            if type(effect) is GrappleStateEffect and effect.kind == 'control' \
                    and effect.operation in ('establish','transition','release'):
                key=(effect.target_id,effect.state_id)
                signature=(effect.actor_id,effect.operation,effect.position,effect.next_check)
                control_groups.setdefault(key,[]).append((action,signature))
    conflict_groups=[]
    for rows in control_groups.values():
        if len(rows)>1 and len({signature for _action,signature in rows})>1:
            conflict_groups.append(tuple(sorted((action for action,_signature in rows),
                key=lambda action:(action.priority,action.order,action.id))))
    for group in conflict_groups:
        while True:
            rerolled=[]
            for action in group:
                rng.action_id=action.id
                rerolled.append(_grappling(snapshot,action,rng))
            successes=[proposal for proposal in rerolled if proposal.outcome=='success']
            signatures=[]
            for proposal in successes:
                for effect in proposal.effects:
                    if type(effect) is GrappleStateEffect and effect.kind=='control' \
                            and effect.operation in ('establish','transition','release'):
                        signatures.append((effect.actor_id,effect.operation,effect.position,effect.next_check))
            compatible=len(set(signatures))<=1
            if (len(group)==2 and len(successes)==1) or (len(group)>=3 and successes and compatible):
                by_id.update((proposal.action_id,proposal) for proposal in rerolled)
                break
    proposals=[by_id[proposal.action_id] for proposal in proposals]
    # Preparation is retained until the defender assigns it. Assignment is
    # fixed before the roll; its result follows the ordinary shared attack
    # result and both records publish in the same atomic boundary.
    by_id = {proposal.action_id: proposal for proposal in proposals}
    for defense_action in selected:
        if (defense_action.family != 'defense'
                or defense_action.lifecycle != 'pending'
                or defense_action.data.get('prepared_defense') is None):
            continue
        defense_proposal = by_id.get(defense_action.id)
        if defense_proposal is None or not defense_proposal.defenses:
            continue
        strike_id = defense_action.data['target_action_id']
        strike_proposal = by_id.get(strike_id)
        if strike_proposal is None:
            raise EvaluationIntegrityError('retained defense assignment lacks its same-boundary attack result')
        source_action = snapshot.actions[strike_id]
        landed = (strike_proposal.outcome in ('normal', 'critical', 'fatal')
                  or (source_action.family == 'melee'
                      and source_action.data.get('event_type') == 'feint'
                      and strike_proposal.outcome == 'success'))
        success = not landed
        outcome = ('deflected' if defense_action.data['kind'] == 'parry' else 'evaded') if success else 'failed'
        effect = replace(defense_proposal.defenses[0], success=success)
        skill = (snapshot.entity(defense_action.instrument_id).data['original_type']
                 if defense_action.data['kind'] == 'parry' else 'tumble')
        practice = PracticeEffect(defense_action.id, defense_action.actor_id, skill, 10)
        by_id[defense_action.id] = replace(defense_proposal,
            outcome=outcome, effects=(practice,), defenses=(effect,))
        attack_effects = tuple(effect if old.source_action_id == defense_action.id else old
                               for old in strike_proposal.defenses)
        by_id[strike_id] = replace(strike_proposal, defenses=attack_effects)
    proposals = [by_id[proposal.action_id] for proposal in proposals]
    return bind_evaluation_result(snapshot, tuple(proposals), tuple(rng.trace), rng.rng.getstate())


@dataclass(frozen=True)
class RealityAdapterRequest:
    """Future adapter boundary: objective candidate plus observer evidence needed.

    A future batch supplies a shared candidate Reality view, established-fact
    constraints and observer-specific frozen capabilities. It must stage facts,
    evidence, interpretation/testimony, practice and notification intents together.
    No generator/counts/history/completion callback is retained or invoked here.
    """
    action_id: str
    observer_id: str
    subject_id: str
    kind: str
    objective_key: tuple
    requires_shared_candidate: bool = True


def future_reality_request(action):
    from group_observation import ObserveGroupAction
    from history_conversation import AskAboutPastAction
    from activities import SpotAction
    if type(action) not in (ObserveGroupAction, AskAboutPastAction, SpotAction):
        raise UnsupportedEvaluation('not a native Reality inquiry')
    if type(action) is SpotAction:
        if object.__getattribute__(action, '__dict__').get('group_fully_visible') is not True:
            raise UnsupportedEvaluation('ordinary Spot does not declare a shared-Reality request')
        from objective_reality import objective_action_data
        objective_action_data(action)  # checked target type, visibility premise, and owner ledger
    # Do not run native_data's callable rejection: history deliberately stores
    # a generator. Read only primitive declaration fields, never the generator.
    data = object.__getattribute__(action, '__dict__')
    key = (('group-composition', freeze(data['target_id'])) if type(action) is ObserveGroupAction
           or type(action) is SpotAction and data.get('group_fully_visible') is True
           else ('personal-history', freeze(data['target_id']), freeze(data['episode_time']), freeze(data['topic'])))
    return RealityAdapterRequest(freeze(data['id']), freeze(data['actor_id']),
        freeze(data['target_id']), freeze(data['event_type']), key)
