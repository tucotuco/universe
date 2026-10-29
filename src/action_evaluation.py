"""Inactive native Action evaluation boundary (Universe 4 Increment 4).

Capture only at a caller-owned post-movement/pre-action integer fence. Nothing
here advances time, dispatches live resolvers, publishes effects, or commits RNG.
Exact native adapters are deliberate: this is not a Python extension sandbox.
"""
from dataclasses import dataclass, field, fields
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
from spatial.visibility import trace_sightline


class UnsupportedEvaluation(TypeError):
    """No reviewed pure adapter; no extension callback has been invoked."""


class EvaluationIntegrityError(ValueError):
    """Contradictory/corrupt native data, distinct from a gameplay outcome."""


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

    def melee_status(self, action):
        distance = self.distance(action.actor_id, action.target_id)
        path = self.path(action.actor_id, action.target_id) if distance is not None and 0 < distance <= action.data['reach'] else None
        return melee_path_status(distance, action.data['reach'], path)


def capture_snapshot(encounter, boundary, *, rng_state=None, _objective=False, _stage=None):
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
    ed = native_data(encounter, (Encounter,))
    if _stage is not None:
        from interval_staging import _StagedReadFence
        if type(_stage) is not _StagedReadFence or _stage.encounter_identity != id(encounter) or _stage.boundary != boundary:
            raise EvaluationIntegrityError('invalid private interval read fence')
        ed = dict(ed, time=boundary, pending_action_list=_stage.pending_ids)
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
    families = {Action: 'combat', MeleeStrike: 'melee', MeleeDefense: 'defense',
                RunAction: 'run', SpotAction: 'spot'}
    objective_actions = {}
    if _objective:
        from group_observation import ObserveGroupAction
        from history_conversation import AskAboutPastAction
        from objective_reality import objective_action_data
        families.update({ObserveGroupAction: 'observe_group', AskAboutPastAction: 'history_request'})
    pending_ids = freeze(ed['pending_action_list'])
    ids = tuple(dict.fromkeys(pending_ids + freeze(ed['cancelled_action_list'])))
    for order, aid in enumerate(ids):
        action = wd['event_history'].get(aid)
        if type(action) not in families:
            raise UnsupportedEvaluation('Action family requires a pure adapter (Reality/evidence staging deferred)')
        if _objective and type(action) in (ObserveGroupAction, AskAboutPastAction):
            ad, objective = objective_action_data(action)
            objective_actions[aid] = objective
        else:
            ad = native_data(action, tuple(families))
        if _stage is not None:
            ad = dict(ad, **_stage.initialization.get(aid, {}))
        if type(ad['id']) is not str or ad['id'] != aid:
            raise EvaluationIntegrityError('Action identity mismatch')
        if ad['event_type'] not in (('swing', 'thrust', 'parry', 'dodge', 'run', 'spot') + (('observe_group', 'ask_about_past') if _objective else ())):
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
        end = ad['end_time']
        if type(end) not in (int, float) or not math.isfinite(end):
            raise EvaluationIntegrityError('invalid Action deadline')
        cancelled = aid in ed['cancelled_action_list']
        if not cancelled and math.ceil(end) < boundary:
            raise EvaluationIntegrityError('stale pending Action')
        strategy = freeze(native_data(ad['strategy'], (Strategy,)))
        selected = {'event_type': ad['event_type'], 'strategy': strategy}
        for key in ('reach','kind','target_action_id','ready_at','threat_at_schedule',
                    'minimum_distance','practice_experience','max_distance','declared_roll','episode_time','topic','experience_policy','canceled_at','cancellation_reason'):
            if key in ad:
                selected[key] = freeze(ad[key])
        if type(action) is RunAction:
            selected['start_position'] = position(ad['start_position'])
            selected['started'] = ad.get('_activity_started', False)
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
        actions[aid] = ActionView(aid, families[type(action)], freeze(ad['actor_id']),
            freeze(ad['target_id']), freeze(ad['instrument_id']), freeze(ad['start_time']),
            end, math.ceil(end), -1 if type(action) is MeleeDefense else 0, order,
            'cancelled' if cancelled else 'pending', MappingProxyType(selected))
    object_classes = (BeingInstance, ObjectInstance, WeaponInstance, ArmorInstance)
    if _objective:
        from statistical_group import StatisticalGroup
        object_classes += (StatisticalGroup,)
    entities = {}
    wanted = set(participants)
    for a in actions.values():
        wanted.update(x for x in (a.actor_id, a.target_id, a.instrument_id) if x is not None)
    # Pull transitive body holdings and armor with IDs intact, before evaluating.
    for key in tuple(wanted):
        if key not in objects:
            raise EvaluationIntegrityError('unknown Object identity')
        obj = objects[key]
        od = native_data(obj, object_classes)
        if type(obj) is BeingInstance:
            current = native_data(od['current'], (BeingDefinition,))
            wanted.update(x for x in freeze(current['body_parts']).values() if x is not None)
            if current['armor_id'] is not None:
                wanted.add(freeze(current['armor_id']))
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
        data = {'hardness': freeze(cd['hardness'])}
        category = 'object'
        if type(obj) is BeingInstance:
            category = 'being'
            skills = native_data(cd['skills'], (Skills,))
            abilities = freeze(native_data(cd['abilities'], (Abilities,))['abilities'])
            data.update(skills=freeze(skills['skills']), weapon_skills=freeze(skills['weapon_skills']),
                abilities=abilities, states=freeze(native_data(cd['states'], (States,))['states']),
                experience=freeze(cd['experience']), armor_id=freeze(cd['armor_id']),
                body_parts=freeze(cd['body_parts']), strategy=freeze(native_data(od['strategy'], (Strategy,))),
                fatigue_level=freeze(od['fatigue_level']),
                exertion=freeze(native_data(od['exertion'], (Exertion,))),
                fatigue_adjustments=freeze(od['exertion'].fatigue_levels))
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
            data.update(attacks=freeze(cd['attacks']), size=freeze(cd['weapon_size']),
                        original_type=freeze(native_data(od['original'], (WeaponDefinition,))['obj_type']))
        elif type(obj) is ArmorInstance:
            category = 'armor'
            data['defenses'] = freeze(cd['defenses'])
        entities[key] = EntityView(key, category, freeze(cd['hit_points']), freeze(cd['obj_type']),
                                   pos, shape, optics, MappingProxyType(data))
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
    practice_inputs = capture_practice_inputs(world, objects, entities)
    objective_inputs = None
    if _objective:
        from objective_reality import capture_objective_inputs
        objective_inputs = capture_objective_inputs(objects, objective_actions, participants)
    snapshot = EvaluationSnapshot(ed['id'], boundary, freeze(ed['difficulty_class']),
        MappingProxyType(entities), participants, MappingProxyType(actions), freeze(ed['awareness']),
        freeze(frame.to_dict()), freeze(profiles), freeze(random.getstate() if rng_state is None else rng_state),
        practice_inputs=practice_inputs, objective_inputs=objective_inputs)
    # Validate identities/defense graph before any provisional draw.
    for a in actions.values():
        if a.family in ('combat', 'melee') and snapshot.entity(a.target_id).category != 'being':
            raise UnsupportedEvaluation('non-Being combat target lacks a native saving-throw contract')
        if snapshot.entity(a.actor_id).category != 'being':
            raise EvaluationIntegrityError('Action actor must be a Being')
        for key in (a.target_id, a.instrument_id):
            if key is not None:
                snapshot.entity(key)
        if a.family == 'defense' and a.data['target_action_id'] not in actions:
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
    max_distance: float
    basis: str = 'spot_check_geometric_path'


@dataclass(frozen=True)
class DefenseEffect:
    source_action_id: str
    strike_id: str
    kind: str
    eligible: bool
    success: bool


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
    actor, attacker = snapshot.entity(action.actor_id), snapshot.entity(action.target_id)
    strike = snapshot.actions[action.data['target_action_id']]
    kind = action.data['kind']
    eligible = False
    success = False
    effects = ()
    if _helpless(actor) or (kind == 'parry' and action.instrument_id not in actor.data['held']):
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
            skill = snapshot.entity(action.instrument_id).data['original_type'] if kind == 'parry' else 'tumble'
            rank = (actor.data['weapon_skills'] if kind == 'parry' else actor.data['skills']).get(skill, 0) or 0
            if status != 'in_reach':
                success = True
            else:
                weapon = snapshot.entity(strike.instrument_id)
                attack_rank = attacker.data['weapon_skills'].get(weapon.data['original_type'], 0) or 0
                success = defense_succeeds(rng.roll('1d20'), rank, actor.data['strategy']['defense'],
                    rng.roll('1d20'), attack_rank, attacker.data['strategy']['attack'])
            outcome = ('deflected' if kind == 'parry' else 'evaded') if success else 'failed'
            effects = (PracticeEffect(action.id, actor.id, skill, 10),)
    dependency = DefenseEffect(action.id, strike.id, kind, eligible, success)
    return ActionProposal(action.id, actor.id, (attacker.id,), outcome, effects, (dependency,))


def _combat(snapshot, action, rng, dependencies):
    actor, target = snapshot.entity(action.actor_id), snapshot.entity(action.target_id)
    weapon = snapshot.entity(action.instrument_id) if action.instrument_id else None
    effects = []
    meta = []
    attempted = False
    outcome = None
    if action.family == 'melee':
        status, distance = snapshot.melee_status(action)
        meta.append(('distance', distance))
        if actor.hp <= 0 or actor.data['fatigue_level'] >= 5:
            outcome = 'unable_to_act'
        elif target.hp <= 0:
            outcome = 'target_down'
        elif action.instrument_id not in actor.data['held']:
            outcome = 'weapon_unavailable'
        elif status != 'in_reach':
            outcome = status
        elif any(d.eligible and d.success for d in dependencies):
            first = next(d for d in dependencies if d.eligible and d.success)
            outcome = 'parried' if first.kind == 'parry' else 'dodged'
            attempted = True
    if outcome is None:
        if weapon is None or weapon.category != 'weapon':
            outcome = 'weapon_unavailable'
        else:
            def hits(roll, dc):
                adjustment = 0
                if action.family == 'melee':
                    adjustment = actor.data['fatigue_adjustments'][actor.data['fatigue_level']]['ability_adjustment']
                    if adjustment is None:
                        return False
                return attack_hits(roll, actor.data['weapon_skills'].get(weapon.obj_type, 0) + actor.data['strategy']['attack'],
                    target.data.get('strategy', {}).get('defense', 0), dc - adjustment)
            def save(being, dc):
                return saving_throw(rng.roll('1d20'), dc,
                    saving_throw_experience_modifier(experience_level(being.data['experience'])))
            outcome = hit_outcome(snapshot.difficulty, rng.roll, hits,
                lambda dc: save(target, dc), lambda dc: save(actor, dc))
            attempted = True
            recipient = actor if outcome == 'hit self' else target
            if outcome == 'fatal':
                effects.append(FatalEffect(action.id, target.id))
            potential = weapon.data['attacks']['S' if action.data['event_type'] == 'swing' else 'T']['d']
            penetration = weapon.data['attacks']['S' if action.data['event_type'] == 'swing' else 'T']['p']
            def shield(damage):
                sid = rng.choose_shield(recipient.data.get('shields', ()))
                if sid is None:
                    return damage
                item = snapshot.entity(sid)
                intercepted, through = shield_impact(damage, item.data['size'], rng.roll('1d10+0'))
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
            damage_path(outcome, potential, action.data['strategy']['extra_damage'], rng.roll, shield, armor, body)
    if attempted and action.family == 'melee':
        effects.append(PracticeEffect(action.id, actor.id, weapon.data['original_type'], 10))
    affected = tuple(dict.fromkeys((target.id,) + tuple(e.target_id for e in effects if hasattr(e, 'target_id'))))
    return ActionProposal(action.id, actor.id, affected, outcome, tuple(effects), tuple(dependencies), tuple(meta))


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
    else:
        target = snapshot.entity(action.target_id)
        distance = snapshot.distance(actor.id, target.id)
        rank = actor.data['skills'].get('spot', 0) or 0
        metadata.append(('skill_level_used', rank))
        if distance is None:
            outcome = 'unplaced'
        elif distance > action.data['max_distance']:
            outcome = 'out_of_range'
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
                outcome = 'success' if check_succeeds(roll, rank, snapshot.difficulty) else 'failure'
                if outcome == 'success':
                    effects.append(AwarenessEffect(action.id, actor.id, target.id, distance, action.data['max_distance']))
        effects.append(PracticeEffect(action.id, actor.id, 'spot', action.data['practice_experience']))
    return ActionProposal(action.id, actor.id, () if action.target_id is None else (action.target_id,),
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
        if a.boundary == snapshot.boundary)
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
    if any(a.family not in ('combat', 'melee', 'defense', 'run', 'spot') for a in selected):
        raise UnsupportedEvaluation('objective-only declarations require their separate inactive context; complete Action effects remain unsupported')
    rng = _ProvisionalRandom(snapshot.rng_state)
    proposals = []
    defense_effects = []
    for action in sorted(selected, key=lambda a: (a.priority, a.order)):
        rng.action_id = action.id
        if action.lifecycle == 'cancelled':
            proposal = ActionProposal(action.id, action.actor_id,
                () if action.target_id is None else (action.target_id,), 'interrupted')
        elif action.family == 'defense':
            proposal = _defense(snapshot, action, rng)
            defense_effects.extend(proposal.defenses)
        elif action.family in ('combat', 'melee'):
            proposal = _combat(snapshot, action, rng, tuple(d for d in defense_effects if d.strike_id == action.id))
        else:
            proposal = _activity(snapshot, action, rng)
        proposals.append(proposal)
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
    if type(action) not in (ObserveGroupAction, AskAboutPastAction):
        raise UnsupportedEvaluation('not a native Reality inquiry')
    # Do not run native_data's callable rejection: history deliberately stores
    # a generator. Read only primitive declaration fields, never the generator.
    data = object.__getattribute__(action, '__dict__')
    key = (('group-composition', freeze(data['target_id'])) if type(action) is ObserveGroupAction
           else ('personal-history', freeze(data['target_id']), freeze(data['episode_time']), freeze(data['topic'])))
    return RealityAdapterRequest(freeze(data['id']), freeze(data['actor_id']),
        freeze(data['target_id']), freeze(data['event_type']), key)
