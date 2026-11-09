"""Inactive Target-owned candidate reconciliation (Universe 4 Increment 5A).

Consumes already-calculated native effects. No combat calculation, world lookup,
publication, callbacks, RNG draws, practice awards, or persistent history writes.
"""
from collections import Counter
from dataclasses import dataclass, field, fields, replace
import math
import random
from types import MappingProxyType
from spatial.state import CartesianPosition

from action_evaluation import (EvaluationSnapshot, EvaluationResult, ActionView,
    EntityView, ActionProposal, DamageEffect, FatalEffect, ProtectionEffect,
    PracticeEffect, AwarenessEffect, DefenseEffect, EffectIdentity, IdentifiedEffect,
    RandomDraw, ProjectileReleaseEffect, PickupEffect, ReadyWeaponEffect, UnsupportedEvaluation,
    EvaluationIntegrityError, freeze, position, pickup_eligibility)


class SettlementIntegrityError(EvaluationIntegrityError):
    """The complete candidate cannot be built from these inconsistent inputs."""


@dataclass(frozen=True)
class TargetCandidate:
    """Only this Target projection owns its proposed HP/state/provenance.

    Practice state/history is projected from frozen native inputs.
    Awareness is an observer's projected directed
    relation; it does not migrate the live Encounter's awareness storage.
    """
    target_id: str
    category: str
    starting_hp: int | float
    projected_hp: int | float
    actual_damage: int | float
    fatal_effect_ids: tuple
    incoming: tuple
    outgoing_effect_ids: tuple
    aware_of: frozenset
    practice_state: object = None
    observer_state: object = None

    def effects_from(self, action_id):
        return tuple(row for row in self.incoming if row.identity.source_action_id == action_id)

    @property
    def practice(self):
        return tuple(row for row in self.incoming if type(row.effect) is PracticeEffect)


@dataclass(frozen=True)
class BoundaryCandidate:
    encounter_id: str
    boundary: int
    targets: object
    actions: object
    effects: object
    trace: tuple
    provisional_rng_state: tuple
    practice_validation: str
    schema: str = 'native-target-candidate-v1-inactive'
    ready_for_publication: bool = False
    source_snapshot: object = field(default=None, repr=False, compare=False)
    evaluation: object = field(default=None, repr=False, compare=False)
    observer_reconciliation_complete: bool = False
    publication_dependencies: tuple = ('5B3_observer_evidence_testimony_and_lifecycle',
        'whole_interval_publication_and_recovery', 'checkpoint_replay_compatibility')

    @property
    def coverage(self):
        if self.evaluation is not None and self.evaluation.observer_context is not None and not self.observer_reconciliation_complete:
            return 'core_effects_only'
        return 'native_fragment' if self.source_snapshot is not None and self.source_snapshot.omitted_objective_action_ids else 'complete_supported_batch'

    def target(self, target_id):
        return self.targets[target_id]

    def effects_of(self, action_id):
        return tuple(row for row in self.effects.values() if row.identity.source_action_id == action_id)


_EFFECTS = (DamageEffect, FatalEffect, ProtectionEffect, PracticeEffect, AwarenessEffect, DefenseEffect, ProjectileReleaseEffect, PickupEffect, ReadyWeaponEffect)
_FAMILIES = frozenset(('combat', 'melee', 'defense', 'run', 'spot', 'throw', 'pickup', 'ready_weapon', 'observe_group', 'history_request'))
_ATTACK_OUTCOMES = frozenset(('normal', 'critical', 'fatal', 'hit self', 'miss', 'spectacular miss', 'drop weapon'))
_OUTCOMES = {
    'observe_group': frozenset(('unplaced', 'out_of_range', 'success', 'failure')),
    'history_request': frozenset(('unplaced', 'out_of_range', 'not_aware', 'heard')),
    'combat': _ATTACK_OUTCOMES | {'weapon_unavailable'},
    'melee': _ATTACK_OUTCOMES | {'unable_to_act', 'target_down', 'weapon_unavailable',
        'unplaced', 'out_of_reach', 'blocked', 'uncertain_path', 'parried', 'dodged'},
    'defense': frozenset(('unable_to_defend', 'no_threat', 'deflected', 'evaded', 'failed')),
    'run': frozenset(('unplaced', 'no_movement', 'success', 'partial')),
    'spot': frozenset(('unplaced', 'unmodeled_target', 'no_clear_path', 'success', 'failure')),
    'throw': frozenset(('unplaced', 'unavailable', 'released')),
    'pickup': frozenset(('unplaced', 'unavailable', 'inaccessible', 'over_capacity',
                         'unknown_weight', 'unknown_capacity', 'unable_to_act',
                         'unsupported_contents', 'contested', 'success')),
    'ready_weapon': frozenset(('unavailable', 'unable_to_act', 'unsupported_weapon',
                               'hand_unavailable', 'already_ready', 'contested', 'success')),
}
_METADATA = {'combat': (), 'melee': ('distance',), 'defense': (), 'run': ('displacement',),
             'spot': ('path_status', 'roll', 'discovery_dc', 'spotting_dc_adjustment',
                      'racial_action_bonus', 'effective_dc', 'observation_id',
                      'objective_key', 'evidence_kind', 'visible_count'),
             'observe_group': ('skill_level_used', 'roll', 'observation_id', 'objective_key'),
             'history_request': ('account_id', 'objective_key', 'newly_constructed'),
             'pickup': (), 'ready_weapon': ()}
_METADATA['throw'] = ('release_speed_yd_s', 'impact_time')


def _require(condition, reason):
    if not condition:
        raise SettlementIntegrityError(reason)


def _identity(value):
    _require(type(value) is str and bool(value), 'expected nonempty native identity')
    return value


def _number(value, *, nonnegative=False):
    _require(type(value) in (int, float), 'expected native numeric state/contribution')
    _require(type(value) is int or math.isfinite(value), 'non-finite state/contribution')
    _require(not nonnegative or value >= 0, 'negative damage or magnitude is not a supported effect')
    return value


def _tuple(value):
    _require(type(value) is tuple, 'expected immutable native tuple')
    return value


def _mapping(value):
    _require(type(value) in (dict, MappingProxyType), 'opaque lookup is unsupported')
    return value


def _effect(effect):
    if type(effect) not in _EFFECTS:
        raise UnsupportedEvaluation('effect family requires a reviewed candidate adapter')
    # Reconstruct primitive fields; no mutable producer alias or opaque callback.
    values = {f.name: freeze(getattr(effect, f.name)) for f in fields(effect)}
    _identity(values['source_action_id'])
    _identity(values['strike_id'] if type(effect) is DefenseEffect else values['target_id'])
    if type(effect) is PickupEffect:
        _identity(values['object_id'])
    if type(effect) is ReadyWeaponEffect:
        _identity(values['object_id'])
        _require(values['hand'] in ('left hand', 'right hand'), 'unsupported native Ready weapon hand')
    for key in ('component', 'layer', 'skill', 'observed_id', 'basis', 'kind'):
        if key in values:
            _identity(values[key])
    for key in ('amount', 'incoming', 'passed', 'distance', 'max_distance'):
        if key in values:
            if key == 'max_distance' and values[key] is None and type(effect) is AwarenessEffect:
                continue
            _number(values[key], nonnegative=True)
    if 'experience' in values:
        _require(type(values['experience']) is int and values['experience'] >= 0, 'invalid practice award')
    for key in ('eligible', 'success', 'intercepted'):
        if key in values:
            _require(type(values[key]) is bool, 'invalid effect boolean')
    return type(effect)(**values)


def _signature(effect):
    return (type(effect).__name__, tuple(getattr(effect, f.name) for f in fields(effect)))


def _copy_actions(snapshot):
    actions = {}
    for key, view in _mapping(snapshot.actions).items():
        _identity(key)
        _require(type(view) is ActionView, 'invalid frozen Action type')
        _require(_identity(view.id) == key, 'invalid frozen Action identity')
        if type(view.family) is not str or view.family not in _FAMILIES:
            raise UnsupportedEvaluation('unsupported snapshot Action family; no partial fallback')
        _identity(view.actor_id)
        if view.target_id is not None:
            _identity(view.target_id)
        if view.instrument_id is not None:
            _identity(view.instrument_id)
        _number(view.start); _number(view.nominal_end)
        _require(type(view.boundary) is int and view.boundary == math.ceil(view.nominal_end), 'invalid Action boundary')
        _require(type(view.order) is int and view.order >= 0 and type(view.priority) is int, 'invalid native Action order')
        _identity(view.lifecycle)
        _require(view.lifecycle in ('pending', 'cancelled'), 'unsupported Action lifecycle')
        _require(view.lifecycle == 'cancelled' or view.boundary >= snapshot.boundary, 'stale pending Action')
        data = {_identity(k): (position(v) if k == 'start_position' else freeze(v)) for k, v in _mapping(view.data).items()}
        actions[key] = replace(view, data=MappingProxyType(data))
    _require(len({a.order for a in actions.values()}) == len(actions), 'ambiguous scheduling order')
    return actions


def _copy_proposal(proposal, actions, entities):
    if type(proposal) is not ActionProposal:
        raise UnsupportedEvaluation('opaque Action proposal')
    _identity(proposal.action_id); _identity(proposal.actor_id)
    _require(proposal.action_id in actions, 'unknown source Action')
    action = actions[proposal.action_id]
    _require(proposal.actor_id == action.actor_id, 'proposal actor does not match declaration')
    _require(type(proposal.outcome) is str, 'opaque outcome')
    allowed = {'interrupted'} if action.lifecycle == 'cancelled' else _OUTCOMES[action.family]
    _require(proposal.outcome in allowed, 'outcome contradicts native Action family/lifecycle')
    targets = tuple(_identity(k) for k in _tuple(proposal.target_ids))
    _require(len(set(targets)) == len(targets) and all(k in entities for k in targets), 'invalid affected Target reference')
    metadata = freeze(_tuple(proposal.metadata))
    _require(all(type(pair) is tuple and len(pair) == 2 and type(pair[0]) is str for pair in metadata), 'invalid outcome metadata')
    names = tuple(pair[0] for pair in metadata)
    _require(len(set(names)) == len(names) and set(names).issubset(_METADATA[action.family]), 'unsupported metadata (no Target HP on Actions)')
    effects = tuple(_effect(e) for e in _tuple(proposal.effects))
    defenses = tuple(_effect(d) for d in _tuple(proposal.defenses))
    _require(all(type(d) is DefenseEffect for d in defenses), 'non-defense dependency')
    _require(not any(type(e) is DefenseEffect for e in effects), 'defenses must use dependency channel')
    if action.lifecycle == 'cancelled':
        _require(not effects and not defenses, 'interrupted Action may not propose active effects')
    expected_targets = set(() if action.target_id is None else (action.target_id,))
    if action.family in ('combat', 'melee', 'throw'):
        expected_targets.update(e.target_id for e in effects)
    if action.family == 'pickup':
        expected_targets.update(e.target_id for e in effects)
    if action.family == 'ready_weapon':
        expected_targets.update(e.target_id for e in effects)
    _require(set(targets) == expected_targets, 'affected Target references do not match causal records')
    return ActionProposal(proposal.action_id, proposal.actor_id, tuple(sorted(targets)),
                          proposal.outcome, effects, defenses, tuple(sorted(metadata)))


def _validate_effect(effect, proposal, action, actions, entities, participants, snapshot):
    _require(effect.source_action_id == action.id, 'effect source contradicts owner Action')
    actor = entities[action.actor_id]
    if type(effect) is DefenseEffect:
        _identity(effect.strike_id)
        _require(action.family == 'defense' and effect.strike_id == action.data['target_action_id'], 'invalid designated defense source')
        _require(effect.strike_id in actions, 'missing designated strike')
        strike = actions[effect.strike_id]
        _require(strike.family == 'melee' and strike.actor_id == action.target_id
            and strike.target_id == action.actor_id and strike.nominal_end == action.nominal_end,
            'contradictory designated defense relationship')
        _require(effect.kind == action.data['kind'] and effect.kind in ('parry', 'dodge'), 'invalid defense kind')
        _require(type(effect.eligible) is bool and type(effect.success) is bool and (effect.eligible or not effect.success), 'invalid defense eligibility/success')
        expected = ('deflected' if effect.kind == 'parry' else 'evaded') if effect.success else 'failed' if effect.eligible else None
        _require(proposal.outcome == expected if expected is not None else proposal.outcome in ('no_threat', 'unable_to_defend'), 'defense outcome contradicts dependency')
        if effect.eligible:
            _require(strike.lifecycle == 'pending', 'eligible defense designates interrupted strike')
        return action.actor_id, ('defense', action.id, effect.strike_id)
    _identity(effect.target_id)
    _require(effect.target_id in entities, 'unknown effect recipient')
    recipient = entities[effect.target_id]
    if type(effect) is PickupEffect:
        _identity(effect.object_id)
        _require(action.family == 'pickup' and proposal.outcome == 'success'
                 and effect.target_id == action.actor_id
                 and effect.object_id == action.target_id
                 and recipient.category == 'being'
                 and entities[effect.object_id].category in ('object', 'weapon', 'armor'),
                 'Pick up effect does not transfer its declared Object to its actor')
        return effect.target_id, ('pickup', action.id, effect.object_id)
    if type(effect) is ReadyWeaponEffect:
        _identity(effect.object_id)
        _require(action.family == 'ready_weapon' and proposal.outcome == 'success'
                 and effect.target_id == action.actor_id and effect.object_id == action.target_id
                 and effect.hand == action.data.get('hand') and recipient.category == 'being'
                 and entities[effect.object_id].category == 'weapon',
                 'Ready weapon effect does not match its declared actor, Weapon, and hand')
        from action_evaluation import ready_weapon_eligibility
        _require(ready_weapon_eligibility(snapshot, action) is None,
                 'Ready weapon effect is ineligible in the common snapshot')
        return effect.target_id, ('ready_weapon', action.id, effect.object_id, effect.hand)
    if type(effect) is ProjectileReleaseEffect:
        _require(action.family == 'throw' and proposal.outcome == 'released'
                 and action.instrument_id == effect.target_id and recipient.category == 'object',
                 'projectile release must target its declared Object instrument')
        _require(effect.release_time == action.boundary and effect.impact_time > effect.release_time
                 and action.nominal_end-action.start==4,
                 'invalid projectile release chronology')
        _require(type(effect.release_position) is tuple and len(effect.release_position)==3
                 and type(effect.landing_position) is tuple and len(effect.landing_position)==3
                 and type(effect.velocity_m_s) is tuple and len(effect.velocity_m_s) == 3,
                 'invalid projectile trajectory proposal')
        for value in effect.release_position+effect.landing_position: _number(value)
        _number(effect.landing_elevation_m)
        for value in effect.velocity_m_s: _number(value)
        if actor.position is None or effect.target_id not in actor.data.get('possessions', ()):
            raise SettlementIntegrityError('Throw Object is not a positioned available possession')
        _require(actor.data.get('abilities',{}).get('STR')==10
            and type(recipient.data.get('weight')) in (int,float)
            and 0 < recipient.data['weight'] <= 3.3,
            'unsupported Throw strength/weight bracket')
        from throwing import release_velocity_yd_s, project_drag_free_trajectory
        height=actor.data.get('height')
        speed=release_velocity_yd_s(strength=actor.data['abilities']['STR'],
            throw_skill_level=actor.data['skills'].get('throw',0),
            projectile_weight_lb=recipient.data['weight'],
            heavy_load_reference_lb=action.data['heavy_load_reference_lb'],height_inches=height)
        projected=project_drag_free_trajectory(release_velocity_yd_s=speed,
            release_position=CartesianPosition(actor.position.x,actor.position.y,
                actor.position.z+height*0.0254),
            landing_elevation_m=action.data['landing_elevation_m'],
            elevation_degrees=action.data['elevation_degrees'],
            azimuth_degrees=action.data['azimuth_degrees'])
        expected_time=action.boundary+projected.flight_time_s
        _require(effect.release_position==projected.release_position.as_tuple()
            and effect.velocity_m_s==projected.velocity_m_s
            and effect.landing_position==projected.landing_position.as_tuple()
            and math.isclose(effect.impact_time,expected_time,rel_tol=1e-13,abs_tol=1e-13),
            'projectile release contradicts the adopted frozen launch calculation')
        return effect.target_id, ('projectile_release', action.id, effect.target_id)
    if type(effect) in (DamageEffect, FatalEffect, ProtectionEffect):
        _require(action.family in ('combat', 'melee') and proposal.outcome in ('normal', 'critical', 'hit self', 'fatal'), 'damage/protection on an inapplicable Action')
        body_id = action.actor_id if proposal.outcome == 'hit self' else action.target_id
        body = entities[body_id]
        if type(effect) is FatalEffect:
            _require(proposal.outcome == 'fatal' and recipient.category == 'being' and effect.target_id == action.target_id, 'unsupported or contradictory fatal recipient')
            return effect.target_id, ('fatal', action.id, effect.target_id)
        if type(effect) is DamageEffect:
            _number(effect.amount, nonnegative=True)
            _require(effect.component in ('body', 'critical_bypass', 'shield', 'armor'), 'unsupported damage component')
            layer = effect.component
            if layer in ('body', 'critical_bypass'):
                _require(effect.target_id == body_id, 'body/self-hit recipient contradicts Action')
                if layer == 'critical_bypass':
                    _require(proposal.outcome in ('critical', 'fatal'), 'critical bypass on noncritical Action')
            elif layer == 'armor':
                _require(recipient.category == 'armor' and body.data.get('armor_id') == effect.target_id, 'armor recipient is not snapshot protection')
            else:
                _require(recipient.category == 'weapon' and effect.target_id in body.data.get('shields', ()), 'shield recipient is not snapshot protection')
            return effect.target_id, ('damage', action.id, effect.target_id, layer)
        _require(effect.layer in ('shield', 'armor') and type(effect.intercepted) is bool, 'invalid protection contribution')
        _number(effect.incoming, nonnegative=True); _number(effect.passed, nonnegative=True)
        _require(effect.passed <= effect.incoming, 'protection invents damage')
        if effect.layer == 'armor':
            _require(recipient.category == 'armor' and body.data.get('armor_id') == effect.target_id and effect.intercepted, 'invalid armor protection recipient')
        else:
            _require(recipient.category == 'weapon' and effect.target_id in body.data.get('shields', ()), 'invalid shield protection recipient')
        return effect.target_id, ('protection', action.id, effect.target_id, effect.layer)
    _require(effect.target_id == action.actor_id and actor.category == 'being', 'practice/awareness must belong to actor')
    if type(effect) is PracticeEffect:
        _identity(effect.skill)
        _require(type(effect.experience) is int and effect.experience >= 0, 'invalid practice award')
        _require(action.family != 'combat', 'base Action has no native practice adapter')
        if action.family == 'run':
            _require(effect.skill == 'run' and proposal.outcome in ('partial', 'success'), 'invalid Run practice')
        elif action.family == 'observe_group':
            _require(effect.skill == 'spot', 'invalid Group observation practice')
            _require(proposal.outcome in ('success', 'failure'), 'ineligible observation practice')
        elif action.family == 'defense':
            _require(proposal.outcome in ('deflected', 'evaded', 'failed'), 'ineligible defense practice')
            skill = entities[action.instrument_id].data['original_type'] if action.data['kind'] == 'parry' else 'tumble'
            _require(effect.skill == skill, 'invalid defense practice skill')
        else:
            _require(proposal.outcome in _ATTACK_OUTCOMES | {'parried', 'dodged'}, 'inapplicable strike practice')
            _require(effect.skill == entities[action.instrument_id].data['original_type'], 'invalid strike practice skill')
        return effect.target_id, ('practice', action.id, effect.target_id, effect.skill)
    _require(type(effect) is AwarenessEffect and ((action.family in ('spot', 'observe_group') and proposal.outcome == 'success')
        or (action.family == 'history_request' and proposal.outcome == 'heard')), 'unsupported awareness effect')
    _identity(effect.observed_id)
    _require(effect.observed_id == action.target_id and effect.observed_id in participants
        and effect.target_id in participants and effect.observed_id != effect.target_id, 'invalid awareness reference')
    _number(effect.distance, nonnegative=True)
    basis = {'spot':'spot_check_geometric_path', 'observe_group':'sampled_group_observation', 'history_request':'heard_account_range_scaffold'}[action.family]
    if action.family == 'spot':
        _require(effect.max_distance is None and effect.basis == basis,
                 'Spot has no adopted fixed distance threshold')
    else:
        _number(effect.max_distance, nonnegative=True)
        _require(effect.max_distance > 0 and effect.distance <= effect.max_distance and effect.basis == basis, 'invalid awareness evidence')
    return effect.target_id, ('awareness', action.id, effect.target_id, effect.observed_id, effect.basis)



def _validate_complete_outcome(proposal, action, entities):
    """Validate required typed contributions, without redoing any calculation."""
    effects = proposal.effects
    pickups = [e for e in effects if type(e) is PickupEffect]
    _require(len(pickups) == int(action.family == 'pickup' and proposal.outcome == 'success'),
             'missing/extra native Pick up custody effect')
    ready = [e for e in effects if type(e) is ReadyWeaponEffect]
    _require(len(ready) == int(action.family == 'ready_weapon' and proposal.outcome == 'success'),
             'missing/extra native Ready weapon equipment effect')
    releases = [e for e in effects if type(e) is ProjectileReleaseEffect]
    _require(len(releases) == int(action.family == 'throw' and proposal.outcome == 'released'),
             'missing/extra projectile release contribution')
    practice = [e for e in effects if type(e) is PracticeEffect]
    expected_practice = None
    if action.lifecycle == 'pending':
        if action.family == 'melee' and proposal.outcome in _ATTACK_OUTCOMES | {'parried', 'dodged'}:
            expected_practice = (entities[action.instrument_id].data['original_type'], 10)
        elif action.family == 'defense' and proposal.defenses[0].eligible:
            skill = entities[action.instrument_id].data['original_type'] if action.data['kind'] == 'parry' else 'tumble'
            expected_practice = (skill, 10)
        elif action.family == 'observe_group' and proposal.outcome in ('success', 'failure'):
            expected_practice = ('spot', action.data['experience_policy'][proposal.outcome])
        elif action.family == 'run' and proposal.outcome in ('success', 'partial'):
            expected_practice = ('run', action.data['practice_experience'])
    _require(len(practice) == (0 if expected_practice is None else 1), 'missing/extra qualifying practice proposal')
    if expected_practice is not None:
        _require((practice[0].skill, practice[0].experience) == expected_practice, 'practice differs from declared native award')
    awareness = [e for e in effects if type(e) is AwarenessEffect]
    _require(len(awareness) == int((action.family in ('spot', 'observe_group') and proposal.outcome == 'success')
        or (action.family == 'history_request' and proposal.outcome == 'heard')), 'missing/extra Spot awareness')
    damage = [e for e in effects if type(e) is DamageEffect]
    fatals = [e for e in effects if type(e) is FatalEffect]
    _require(len(fatals) == int(proposal.outcome == 'fatal'), 'missing/extra fatal effect')
    if action.family in ('combat', 'melee') and proposal.outcome in ('normal', 'critical', 'hit self'):
        _require(sum(e.component == 'body' for e in damage) == 1, 'missing body contribution')
        _require(sum(e.component == 'critical_bypass' for e in damage) == int(proposal.outcome == 'critical'), 'missing/extra critical bypass')
        body_id = action.actor_id if proposal.outcome == 'hit self' else action.target_id
        body = entities[body_id]
        shields = [e for e in effects if type(e) is ProtectionEffect and e.layer == 'shield']
        armor = [e for e in effects if type(e) is ProtectionEffect and e.layer == 'armor']
        _require(len(shields) == int(bool(body.data.get('shields', ()))) and len(armor) == int(body.data.get('armor_id') is not None), 'missing/extra native protection contribution')
        actual_body = next(e.amount for e in damage if e.component == 'body')
        if armor:
            _require(armor[0].passed == actual_body, 'armor through-damage contradicts body contribution')
            if shields:
                _require(shields[0].passed == armor[0].incoming, 'shield/armor chain contradicts proposals')
        elif shields:
            _require(shields[0].passed == actual_body, 'shield through-damage contradicts body contribution')
    for protection in (e for e in effects if type(e) is ProtectionEffect):
        impacts = [e for e in damage if e.target_id == protection.target_id and e.component == protection.layer]
        _require(len(impacts) == int(protection.intercepted), 'missing/extra actual protection impact')
        if protection.layer == 'shield':
            if protection.intercepted:
                _require(impacts[0].amount == protection.incoming, 'shield impact contradicts incoming damage')
            else:
                _require(protection.passed == protection.incoming, 'unintercepted shield changes damage')
    for impact in (e for e in damage if e.component in ('armor', 'shield')):
        _require(any(type(e) is ProtectionEffect and e.target_id == impact.target_id and e.layer == impact.component for e in effects), 'equipment damage lacks protection provenance')

def _project_hp(starting, rows):
    damage = [row.effect.amount for row in rows if type(row.effect) is DamageEffect]
    # Exact integers remain exact; fsum gives deterministic, accurate float sums.
    try:
        total = sum(damage) if all(type(x) is int for x in damage) else math.fsum(damage)
        fatal_ids = tuple(row.identity for row in rows if type(row.effect) is FatalEffect)
        hp = (min(starting, -10) if fatal_ids else starting) - total
    except (OverflowError, ValueError) as exc:
        raise SettlementIntegrityError('unrepresentable candidate damage total') from exc
    _number(total, nonnegative=True); _number(hp)
    return total, hp, fatal_ids


def reconcile_boundary(snapshot, result):
    """Validate one complete supported evaluation, return a detached candidate.

    Effect IDs are allocated by evaluation, not by reducer enumeration. Mirrored
    defense dependencies must agree with their owning proposal; no reroll or
    recalculation is used to hide contradictions. Failure returns no candidate.
    """
    _require(type(snapshot) is EvaluationSnapshot and type(result) is EvaluationResult, 'native snapshot/result required')
    _require(result.snapshot is snapshot, 'evaluation belongs to a different frozen read boundary')
    _identity(snapshot.encounter_id)
    _require(type(snapshot.boundary) is int and snapshot.boundary > 0, 'invalid candidate boundary')
    _require(type(snapshot.schema) is str and snapshot.schema == 'native-action-proposals-v1-inactive', 'unsupported snapshot schema')
    if any(a.family in ('observe_group', 'history_request') for a in snapshot.actions.values()):
        if result.observer_context is None:
            raise UnsupportedEvaluation('complete observer/lifecycle context is required; no partial fallback')
        from observer_proposals import validate_complete_context
        validate_complete_context(result.observer_context)
        _require(result.observer_context.snapshot is snapshot, 'observer result has different snapshot')
    actions = _copy_actions(snapshot)
    participants = frozenset(_identity(k) for k in _tuple(snapshot.participant_ids))
    entities = {}
    for key, entity in _mapping(snapshot.entities).items():
        _identity(key)
        _require(type(entity) is EntityView, 'invalid Target type')
        _require(_identity(entity.id) == key, 'invalid Target identity')
        _identity(entity.category)
        _require(entity.category in ('being', 'object', 'armor', 'weapon'), 'unsupported Target category')
        _number(entity.hp)
        entities[key] = replace(entity, data=freeze(entity.data))
    _require(participants.issubset(entities), 'unknown participating Target')
    for action in actions.values():
        _require(action.actor_id in participants and entities[action.actor_id].category == 'being', 'unknown/non-Being actor')
        for key in (action.target_id, action.instrument_id):
            _require(key is None or key in entities, 'unknown Action reference')
        if action.family in ('combat', 'melee'):
            _require(action.target_id is not None and entities[action.target_id].category == 'being', 'non-Being combat adapter remains unsupported')
    due = {key for key, action in actions.items() if action.boundary == snapshot.boundary}
    _require(all(actions[key].start < snapshot.boundary for key in due), 'due Action has not started')
    proposals = {}
    for raw in _tuple(result.proposals):
        p = _copy_proposal(raw, actions, entities)
        _require(p.action_id not in proposals, 'duplicate Action proposal')
        proposals[p.action_id] = p
    _require(set(proposals) == due, 'complete eligible boundary required; missing/extra Action proposals')
    order = lambda aid: (actions[aid].priority, actions[aid].order, aid)
    owned = {}
    for aid, p in proposals.items():
        action = actions[aid]
        if action.family == 'defense' and action.lifecycle == 'pending':
            _require(len(p.defenses) == 1 and p.defenses[0].source_action_id == aid, 'missing owned defense result')
        elif action.family not in ('melee', 'combat'):
            _require(not p.defenses, 'unexpected defense dependency')
        owned[(aid, 'effect')] = p.effects
        owned[(aid, 'defense')] = tuple(d for d in p.defenses if d.source_action_id == aid)
    rows, seen_semantics = {}, set()
    for raw in _tuple(result.identified_effects):
        _require(type(raw) is IdentifiedEffect and type(raw.identity) is EffectIdentity, 'invalid effect envelope')
        key = raw.identity
        _identity(key.encounter_id); _identity(key.source_action_id); _identity(key.channel)
        _require(type(key.boundary) is int and key.encounter_id == snapshot.encounter_id and key.boundary == snapshot.boundary, 'effect from wrong boundary/Encounter')
        _require(key.source_action_id in due and key.channel in ('effect', 'defense') and type(key.slot) is int and key.slot >= 0, 'invalid source/channel/slot')
        _require(key not in rows, 'duplicate effect identity')
        effect = _effect(raw.effect)
        _require((type(effect) is DefenseEffect) == (key.channel == 'defense'), 'effect channel mismatch')
        owner = key.source_action_id
        recipient, semantic = _validate_effect(effect, proposals[owner], actions[owner], actions, entities, participants, snapshot)
        _require(semantic not in seen_semantics, 'duplicate causal contribution under different identities')
        seen_semantics.add(semantic)
        rows[key] = (IdentifiedEffect(EffectIdentity(key.encounter_id, key.boundary, owner, key.channel, key.slot), effect), recipient)
    for (aid, channel), expected in owned.items():
        actual = [row for key, (row, _) in rows.items() if key.source_action_id == aid and key.channel == channel]
        _require({row.identity.slot for row in actual} == set(range(len(expected))), 'missing/extra effect identity slots')
        _require(Counter(_signature(row.effect) for row in actual) == Counter(_signature(e) for e in expected), 'identified effects contradict Action proposal')
    for aid, proposal in proposals.items():
        _validate_complete_outcome(proposal, actions[aid], entities)
    eligible_pickups = {}
    for aid in due:
        action = actions[aid]
        if action.family != 'pickup' or action.lifecycle != 'pending':
            continue
        status = pickup_eligibility(snapshot, action)
        if status is None:
            eligible_pickups.setdefault(action.target_id, []).append(aid)
    for aid in due:
        action = actions[aid]
        if action.family != 'pickup' or action.lifecycle != 'pending':
            continue
        status = pickup_eligibility(snapshot, action)
        expected = (status if status is not None else
                    'contested' if len(eligible_pickups[action.target_id]) > 1 else 'success')
        _require(proposals[aid].outcome == expected,
                 'Pick up outcome contradicts same-snapshot eligibility/contention')
    from action_evaluation import ready_weapon_eligibility
    ready_claims = {}
    for aid in due:
        action = actions[aid]
        if action.family == 'ready_weapon' and action.lifecycle == 'pending':
            status = ready_weapon_eligibility(snapshot, action)
            if status is None:
                ready_claims.setdefault((action.actor_id, action.data['hand']), []).append(aid)
                ready_claims.setdefault(('weapon', action.target_id), []).append(aid)
    for aid in due:
        action = actions[aid]
        if action.family != 'ready_weapon' or action.lifecycle != 'pending':
            continue
        status = ready_weapon_eligibility(snapshot, action)
        expected = (status if status is not None else
                    'contested' if any(len(ready_claims[key]) > 1 for key in (
                        (action.actor_id, action.data['hand']), ('weapon', action.target_id)))
                    else 'success')
        _require(proposals[aid].outcome == expected,
                 'Ready weapon outcome contradicts same-snapshot eligibility/contention')
    # Defense references are not applied twice. Check all due owning outcomes,
    # including failures, against the explicit strike dependencies.
    for aid, p in proposals.items():
        if actions[aid].family not in ('combat', 'melee'):
            continue
        expected = [d for pid, owner in proposals.items() if actions[pid].family == 'defense'
            and actions[pid].lifecycle == 'pending' for d in owner.defenses if d.strike_id == aid]
        _require(Counter(_signature(d) for d in p.defenses) == Counter(_signature(d) for d in expected), 'missing/contradictory designated defense dependency')
        successes = [d for d in expected if d.eligible and d.success]
        if successes:
            _require(p.outcome not in _ATTACK_OUTCOMES and not any(type(e) in (DamageEffect, FatalEffect, ProtectionEffect) for e in p.effects), 'successful defense conflicts with attack effects')
        if p.outcome in ('parried', 'dodged'):
            kind = 'parry' if p.outcome == 'parried' else 'dodge'
            _require(any(d.kind == kind for d in successes), 'defended outcome lacks successful dependency')
    # Canonical presentation order never establishes effect precedence.
    sorted_rows = sorted(rows.values(), key=lambda pair: (order(pair[0].identity.source_action_id), pair[0].identity.channel, pair[0].identity.slot))
    incoming = {key: [] for key in entities}
    outgoing = {key: [] for key in entities}
    awareness = {key: set() for key in entities}
    for observer, targets in _mapping(snapshot.awareness).items():
        _identity(observer)
        _require(observer in participants and entities[observer].category == 'being', 'invalid awareness owner')
        for target in freeze(targets):
            _identity(target)
            _require(target in participants and target != observer, 'invalid snapshot awareness reference')
            awareness[observer].add(target)
    for row, recipient in sorted_rows:
        incoming[recipient].append(row)
        outgoing[actions[row.identity.source_action_id].actor_id].append(row.identity)
        if type(row.effect) is AwarenessEffect:
            awareness[recipient].add(row.effect.observed_id)
    from frozen_practice import project_practice
    targets = {}
    for key in sorted(entities):
        entity = entities[key]
        total, hp, fatals = _project_hp(entity.hp, incoming[key])
        targets[key] = TargetCandidate(key, entity.category, entity.hp, hp, total, fatals,
            tuple(incoming[key]), tuple(outgoing[key]), frozenset(awareness[key]),
            project_practice(snapshot, key, incoming[key], actions, proposals) if entity.category == 'being' else None)
    # Validate/copy the carried provisional context; no simulation draws occur.
    trace = []
    for draw in _tuple(result.trace):
        _require(type(draw) is RandomDraw, 'opaque RNG trace')
        values = {f.name: freeze(getattr(draw, f.name)) for f in fields(draw)}
        _identity(values['action_id'])
        _require(values['action_id'] in due and type(values['purpose']) is str and type(values['sides']) is int and values['sides'] > 0 and type(values['value']) is int, 'invalid provisional trace identity')
        value = values['value']
        _require(0 <= value < values['sides'] if values['purpose'] == 'shield_choice_index' else 1 <= value <= values['sides'], 'provisional draw outside declared range')
        trace.append(RandomDraw(**values))
    rng_state = freeze(_tuple(result.provisional_rng_state))
    try:
        random.Random(0).setstate(rng_state)  # Structural validation only; no draws.
    except (ValueError, TypeError, OverflowError) as exc:
        raise SettlementIntegrityError('invalid provisional RNG state') from exc
    has_practice = any(type(row.effect) is PracticeEffect for row, _ in sorted_rows)
    # Canonicalize Action descriptions too, so producer enumeration order does
    # not alter an otherwise identical candidate or its provenance presentation.
    for aid, proposal in tuple(proposals.items()):
        effects = tuple(row.effect for row, _ in sorted_rows if row.identity.source_action_id == aid and row.identity.channel == 'effect')
        defenses = tuple(sorted(proposal.defenses, key=lambda d: order(d.source_action_id)))
        proposals[aid] = replace(proposal, effects=effects, defenses=defenses)
    return BoundaryCandidate(snapshot.encounter_id, snapshot.boundary, MappingProxyType(targets),
        MappingProxyType({aid: proposals[aid] for aid in sorted(proposals, key=order)}),
        MappingProxyType({row.identity: row for row, _ in sorted_rows}), tuple(trace), rng_state,
        'validated' if has_practice else 'no_practice', source_snapshot=snapshot, evaluation=result,
        publication_dependencies=(('5B3_observer_and_lifecycle_reconciliation','5C_whole_interval_staging_publication_and_recovery','D7_checkpoint_replay_compatibility')
            if result.observer_context is not None else ('5B3_observer_evidence_testimony_and_lifecycle',
                'whole_interval_publication_and_recovery','checkpoint_replay_compatibility')))
