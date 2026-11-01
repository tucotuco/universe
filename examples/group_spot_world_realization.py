"""Group evidence and independent world-requested adult realization.

Run from the repository root with ``python examples/group_spot_world_realization.py``.
The JSON is an omniscient developer trace. The scenario-authored slot request is
independent of the Agent's Group Spot/evidence.
"""
from copy import deepcopy
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from activities import RunAction, SpotAction
from atomic_publication import PublicationFailure, RNGCursor
from attention_intent import accept_spot_attention
from encounter import Encounter
from field_observation import BeliefLedger
from group_member_realization import AdultMemberGeometryDescriptor, AdultMemberRequest
from group_member_realization import prepare_adult_member_candidate
from library import Library
from melee_combat import MeleeStrike
from spatial import CartesianPosition, Sphere, VisualOcclusion
from statistical_group import StatisticalGroup
from universe import Universe


def _spot_from_developer_choice_book(encounter, actor_id, target_id):
    """Omniscient example-only lookup; the Agent-facing result has no IDs."""
    actions = []
    for record in encounter._choice_book._choices.values():
        actions.extend(member.action for member in record.members)
    return next(action for action in actions
                if type(action) is SpotAction and action.actor_id == actor_id
                and action.target_id == target_id)


def _execute(*, inject_realization_fault=False, group_spot_roll=20):
    config = deepcopy(json.loads((ROOT / 'examples' / 'nomadic_group.json').read_text()))
    group_id = 'world-required-counted-group'
    config['group_id'] = group_id
    config['motion'].update(position=[0, 0, 0], velocity=[0, 0, 0],
                            acceleration=[0, 0, 0])
    world = Universe('Group Spot then world-requested realization',
                     library=Library(config_dir=str(ROOT / 'src' / 'config')))
    observer_ids = [world.make_being('Human', name)
                    for name in ('Observer one', 'Observer two')]
    observers = [world.get_object_by_id(identity) for identity in observer_ids]
    observers[0].set_position(CartesianPosition(0, -100, 0))

    # The explicit world-selected adult slot has this deterministic native
    # keyed placement. The scenario puts Observer two nearby; no position or
    # slot data is supplied to the Agent by Group evidence.
    group_slot_position = (-7.636994404253866, -3.162518900629233, 0.0)
    observers[1].set_position(CartesianPosition(
        group_slot_position[0] + .75, group_slot_position[1], group_slot_position[2]))
    for observer in observers:
        observer.set_geometry(Sphere(.5))
    dagger_id = world.make_weapon_for_being(
        observers[1].id, 'Dagger', "Observer two's dagger")
    world.arm_being(observers[1].id, dagger_id, 'right hand')
    observers[1].set_weapon_skill_level(world.get_weapon_dictionary(), 'Dagger', 5)

    group = StatisticalGroup('Counted group', group_id, config, config['seed'])
    group.set_geometry(Sphere(config['motion']['footprint_radius_m']))
    group.set_visual_occlusion(VisualOcclusion(0.0))
    counts_before = group.counts()
    world.add_object(group)

    # This independent objective requirement is authored before the Agent's
    # observation. It is not derived from a Spot, inquiry, or Attention result.
    world_requirement = {
        'reason': 'scenario needs one adult individually embodied as a participant',
        'group_id': group.id,
        'household': 0,
        'category': 'adults',
        'index': 0,
        'publication_boundary': 7,
        'trigger_action_id': None,
    }

    encounter = Encounter(world, difficulty_class=15, start_time=0, initiated=True,
                          id='group-spot-world-realization-encounter',
                          awareness={observers[1].id: {observers[0].id}})
    world.add_event(encounter)
    for observer in observers:
        encounter.add_being(observer.id)
    encounter.add_object(group.id)
    ledgers = [BeliefLedger(observer.id) for observer in observers]
    rng = RNGCursor(random.Random(5302).getstate())
    rng_before = rng.state
    encounter.enable_transactional_progression(quiescent=True, rng_owner=rng)

    group_spot = SpotAction(
        world, observers[1].id, group.id, 0, die_roll=group_spot_roll,
        id='observer-two-spots-group', ledger=ledgers[1], group_fully_visible=True)
    encounter.schedule_choice((group_spot,))
    encounter.step(6)
    group_spot_receipt = encounter._atomic_interval_history[-1]
    group_spot_record = encounter.inspect_committed().action(group_spot.id)
    evidence = ledgers[1].evidence[0] if ledgers[1].evidence else None
    counts_visible = counts_before['humans'] + counts_before['livestock'] + counts_before['dogs']
    if group_spot_roll == 20:
        if evidence is None or group_spot_record.facts.outcome != 'success':
            raise AssertionError('successful Group Spot must publish aggregate evidence')
        if (set(evidence.reports) != {'visible_count'} or evidence.reported_position is not None
                or evidence.position_uncertainty_m is not None
                or evidence.reports['visible_count'].estimate != counts_visible
                or evidence.reports['visible_count'].uncertainty != 0):
            raise AssertionError('Group Spot disclosed more or less than the aggregate count')
    elif evidence is not None or group_spot_record.facts.outcome != 'failure':
        raise AssertionError('failed Group Spot must not publish evidence')
    # The objective scenario request is submitted at the following boundary,
    # regardless of the Agent's Spot outcome. It explicitly names the slot.
    request = AdultMemberRequest(
        world_requirement['group_id'], world_requirement['household'],
        world_requirement['category'], world_requirement['index'],
        world_requirement['publication_boundary'], geometry=AdultMemberGeometryDescriptor(.5))
    candidate = prepare_adult_member_candidate(encounter, group, request)
    member_id = candidate.member_id  # trusted world/developer state only
    awareness_after_group_spot = tuple(
        member_id in encounter.aware_beings(observer.id)
        for observer in observers
    )
    if world_requirement['trigger_action_id'] is not None:
        raise AssertionError('the authored world requirement must not depend on an Agent Action')
    boundary_seven = encounter.prepare_interval_candidate(
        7, rng_owner=rng, adult_member_candidate=candidate)
    if member_id in boundary_seven.pre_action_snapshot.entities:
        raise AssertionError('new adult leaked into the publication boundary snapshot')
    if member_id in encounter.being_list or world.get_object_by_id(member_id) is not None:
        raise AssertionError('candidate Being became authoritative before publication')

    realization_rollback = None
    if inject_realization_fault:
        before_fault = (
            encounter.time, encounter.last_processed_boundary, rng.state,
            group.counts(), group.materialized_count, group.realized_being_count,
            tuple(group._members.items()), tuple(group._realized_beings.items()),
            frozenset(group._motion_attached_native_ids), tuple(encounter.being_list),
            world.get_object_by_id(member_id), tuple(ledgers[1].evidence),
            tuple(encounter.aware_beings(observers[1].id)),
            tuple(id(receipt) for receipt in encounter._atomic_interval_history),
        )
        import atomic_publication
        publish = atomic_publication.publish_interval_candidate

        def fail_after_group_member(owner, interval, **kwargs):
            kwargs['_fail_after'] = 'adult_group_member'
            return publish(owner, interval, **kwargs)

        try:
            from unittest.mock import patch
            with patch('atomic_publication.publish_interval_candidate',
                       side_effect=fail_after_group_member):
                encounter.step(1, adult_member_candidate=candidate)
        except PublicationFailure as error:
            if error.phase != 'adult_group_member' or error.rollback_errors:
                raise
            rollback_token = error.recovery_token
        else:
            raise AssertionError('member publication fault was not injected')
        after_fault = (
            encounter.time, encounter.last_processed_boundary, rng.state,
            group.counts(), group.materialized_count, group.realized_being_count,
            tuple(group._members.items()), tuple(group._realized_beings.items()),
            frozenset(group._motion_attached_native_ids), tuple(encounter.being_list),
            world.get_object_by_id(member_id), tuple(ledgers[1].evidence),
            tuple(encounter.aware_beings(observers[1].id)),
            tuple(id(receipt) for receipt in encounter._atomic_interval_history),
        )
        if before_fault != after_fault:
            raise AssertionError('failed realization leaked Group, observer, RNG, or receipt state')
        if member_id in encounter.aware_beings(observers[1].id):
            raise AssertionError('failed realization disclosed an individual reference')
        encounter.recover_transactional_progression(rollback_token)
        candidate = prepare_adult_member_candidate(encounter, group, request)
        boundary_seven = encounter.prepare_interval_candidate(
            7, rng_owner=rng, adult_member_candidate=candidate)
        realization_rollback = {'phase': 'adult_group_member', 'restored': True}

    encounter.step(1, adult_member_candidate=candidate)
    member = world.get_object_by_id(member_id)
    boundary_seven_receipt = encounter._atomic_interval_history[-1]
    boundary_seven_awareness = tuple(
        member_id in encounter.aware_beings(observer.id) for observer in observers)
    if (member is None or member.id not in encounter.being_list
            or group.counts() != counts_before
            or member_id in boundary_seven.pre_action_snapshot.entities
            or boundary_seven_receipt.action_ids or boundary_seven_receipt.effect_ids
            or member_id in world.event_history):
        raise AssertionError('atomic realization/count/snapshot/identity invariants failed')
    if any(boundary_seven_awareness) or any(
            encounter.is_aware(observer.id, member_id) for observer in observers):
        raise AssertionError('realization must not create observer Awareness')

    # The first fully committed snapshot at n+1 includes the realized Being.
    boundary_eight = encounter.prepare_interval_candidate(8, rng_owner=rng)
    if member_id not in boundary_eight.pre_action_snapshot.entities:
        raise AssertionError('adult is not eligible at the boundary after publication')
    encounter.step(1)
    boundary_eight_receipt = encounter._atomic_interval_history[-1]

    awareness_before_attention = tuple(encounter.aware_beings(observers[1].id))
    if member_id in awareness_before_attention:
        raise AssertionError('Group evidence or realization exposed the individual early')
    attention_result = accept_spot_attention(encounter, observers[1].id)
    if not attention_result.accepted or hasattr(attention_result, 'target_id'):
        raise AssertionError('unique unfamiliar member did not receive identity-free attention acceptance')
    attention_spot = _spot_from_developer_choice_book(
        encounter, observers[1].id, member_id)
    if attention_spot.start_time != 8 or attention_spot.end_time != 14:
        raise AssertionError(f'attention adapter timing was {(attention_spot.start_time, attention_spot.end_time)} at Encounter time {encounter.time}')
    if attention_spot.target_id != member_id:
        raise AssertionError('developer trace target differs from the world-selected member')
    if member_id in encounter.aware_beings(observers[1].id):
        raise AssertionError('Attention binding itself must not create Awareness')
    encounter.step(6)
    attention_receipt = encounter._atomic_interval_history[-1]
    attention_inspection = encounter.inspect_committed()
    attention_record = attention_inspection.action(attention_spot.id)
    awareness_after_attention = tuple(encounter.aware_beings(observers[1].id))
    newly_aware = tuple(identity for identity in awareness_after_attention
                        if identity not in awareness_before_attention)
    if attention_record.facts.outcome != 'success' or newly_aware != (member_id,):
        raise AssertionError('successful attention Spot did not add exactly the observer-owned target')
    if encounter.is_aware(observers[0].id, member_id):
        raise AssertionError('observer one inherited observer two Awareness')

    # The post-Spot Action target comes only from Observer two's own Awareness.
    thrust_target_id = encounter.aware_beings(observers[1].id)[-1]
    if thrust_target_id != member_id:
        raise AssertionError('follow-up target was not sourced from observer-owned Awareness')
    target_hp_before = member.get_hit_points()
    thrust = MeleeStrike(encounter, observers[1].id, thrust_target_id, dagger_id,
                         motion='thrust', reach=2)
    encounter.schedule_choice((thrust,))
    encounter.step(thrust.end_time - encounter.time)
    thrust_receipt = encounter._atomic_interval_history[-1]
    final_inspection = encounter.inspect_committed()
    thrust_record = final_inspection.action(thrust.id)
    if thrust_record.facts.outcome not in ('normal', 'critical', 'fatal'):
        raise AssertionError(f'expected target-directed Thrust to resolve, got {thrust_record.facts.outcome}')
    if group.counts() != counts_before:
        raise AssertionError('combat changed statistical Group composition')

    return {
        'world': world,
        'encounter': encounter,
        'observers': observers,
        'group': group,
        'member': member,
        'world_requirement': world_requirement,
        'counts_before': counts_before,
        'ledgers': ledgers,
        'group_spot': group_spot,
        'group_spot_record': group_spot_record,
        'group_spot_receipt': group_spot_receipt,
        'evidence': evidence,
        'awareness_after_group_spot': awareness_after_group_spot,
        'candidate': candidate,
        'boundary_seven': boundary_seven,
        'boundary_seven_receipt': boundary_seven_receipt,
        'boundary_seven_awareness': boundary_seven_awareness,
        'boundary_eight': boundary_eight,
        'boundary_eight_receipt': boundary_eight_receipt,
        'realization_rollback': realization_rollback,
        'awareness_before_attention': awareness_before_attention,
        'attention_result': attention_result,
        'attention_spot': attention_spot,
        'attention_receipt': attention_receipt,
        'attention_record': attention_record,
        'awareness_after_attention': awareness_after_attention,
        'thrust_target_id': thrust_target_id,
        'target_hp_before': target_hp_before,
        'thrust': thrust,
        'thrust_receipt': thrust_receipt,
        'inspection': final_inspection,
        'rng_before': rng_before,
        'rng': rng,
    }


def demo_data():
    state = _execute()
    encounter, group, member = state['encounter'], state['group'], state['member']
    observers = state['observers']
    evidence = state['evidence']
    inspection = state['inspection']
    return {
        'presentation': 'omniscient developer chronology; not an Agent view or realization receipt',
        'independent_world_requirement': {
            'reason': state['world_requirement']['reason'],
            'group_id': state['world_requirement']['group_id'],
            'slot': (state['world_requirement']['household'],
                     state['world_requirement']['category'],
                     state['world_requirement']['index']),
            'independent_of_group_spot': True,
            'trigger_action_id': state['world_requirement']['trigger_action_id'],
        },
        'chronology': {
            'boundary_6_group_spot': {
                'outcome': state['group_spot_record'].facts.outcome,
                'evidence_kind': None if evidence is None else evidence.mode,
                'aggregate_visible_count': None if evidence is None else
                    evidence.reports['visible_count'].estimate,
                'aggregate_uncertainty': None if evidence is None else
                    evidence.reports['visible_count'].uncertainty,
                'reported_position': None if evidence is None else evidence.reported_position,
                'member_identity_in_evidence': False if evidence is None else
                    member.id in repr(evidence),
                'observer_two_aware_of_group': encounter.is_aware(observers[1].id, group.id),
                'observer_one_evidence_count': len(state['ledgers'][0].evidence),
                'member_identity_in_awareness': state['awareness_after_group_spot'],
            },
            'boundary_7_world_realization': {
                'candidate_absent_from_boundary_snapshot': member.id not in
                    state['boundary_seven'].pre_action_snapshot.entities,
                'committed_registry_identity': state['world'].get_object_by_id(member.id) is member,
                'encounter_participant_after_commit': member.id in encounter.being_list,
                'group_counts_conserved': group.counts() == state['counts_before'],
                'first_eligible_boundary': state['candidate'].first_eligible_boundary,
                'boundary_receipt_action_ids': state['boundary_seven_receipt'].action_ids,
                'boundary_receipt_effect_ids': state['boundary_seven_receipt'].effect_ids,
                'dedicated_realization_action_or_receipt': False,
                'awareness_after_realization': state['boundary_seven_awareness'],
                'rollback_retry': state['realization_rollback'],
            },
            'boundary_8_eligibility': {
                'member_in_snapshot': member.id in state['boundary_eight'].pre_action_snapshot.entities,
                'receipt_action_ids': state['boundary_eight_receipt'].action_ids,
            },
            'boundary_14_attention_spot': {
                'agent_facing_acceptance': {
                    'accepted': state['attention_result'].accepted,
                    'status': state['attention_result'].status,
                    'target_id_disclosed': False,
                },
                'duration_seconds': state['attention_spot'].end_time - state['attention_spot'].start_time,
                'outcome': state['attention_record'].facts.outcome,
                'roll': dict(state['attention_record'].facts.metadata)['roll'],
                'aware_beings_before': state['awareness_before_attention'],
                'aware_beings_after': state['awareness_after_attention'],
                'observer_one_aware_of_member': encounter.is_aware(observers[0].id, member.id),
                'observer_two_aware_of_member': encounter.is_aware(observers[1].id, member.id),
                'receipt_action_ids': state['attention_receipt'].action_ids,
            },
            'boundary_18_thrust': {
                'actor_id': state['thrust'].actor_id,
                'target_id': state['thrust'].target_id,
                'target_source': 'Encounter.aware_beings(observer_two.id) after committed Spot',
                'outcome': inspection.action(state['thrust'].id).facts.outcome,
                'target_hp_before': state['target_hp_before'],
                'target_hp_after': member.get_hit_points(),
                'target_owned_run_experience': member.get_skill_experience('run'),
                'attacker_dagger_experience': observers[1].get_skill_experience('Dagger'),
                'receipt_action_ids': state['thrust_receipt'].action_ids,
            },
        },
        'final': {
            'encounter_time': encounter.time,
            'group_counts': group.counts(),
            'spot_experience_awarded': tuple(observer.get_skill_experience('spot')
                                             for observer in observers),
            'rng_matches_thrust_receipt': state['rng'].state == state['thrust_receipt'].rng_state,
        },
    }


if __name__ == '__main__':
    print(json.dumps(demo_data(), indent=2, sort_keys=True))
