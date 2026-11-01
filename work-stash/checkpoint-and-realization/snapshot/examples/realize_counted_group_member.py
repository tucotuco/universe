"""Resolve one already-counted adult, then use it in a native Encounter.

Run with ``python examples/realize_counted_group_member.py``. The developer
view shows objective identity and state; Spot evidence remains observer-owned
and contains only the exact aggregate count authorized by the scenario.
Member realization happens before Encounter construction. Runtime member
realization is not part of the transactional publisher.
"""
from copy import deepcopy
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from activities import RunAction, SpotAction
from atomic_publication import RNGCursor
from encounter import Encounter
from field_observation import BeliefLedger
from library import Library
from spatial import CartesianPosition, Sphere
from statistical_group import StatisticalGroup
from universe import Universe


def prepare_scenario():
    config = json.loads((ROOT / 'examples' / 'nomadic_group.json').read_text())
    config = deepcopy(config)
    config['group_id'] = 'counted-member-group'
    config['motion'].update(position=[0, 0, 0], velocity=[0, 0, 0],
                           acceleration=[0, 0, 0])
    world = Universe('Counted Group Member',
        library=Library(config_dir=str(ROOT / 'src' / 'config')))
    observer_ids = [world.make_being('Human', name)
                    for name in ('Observer one', 'Observer two')]
    observers = [world.get_object_by_id(identity) for identity in observer_ids]
    observers[0].set_position(CartesianPosition(0, -20, 0))
    observers[1].set_position(CartesianPosition(20, -20, 0))
    for observer in observers:
        observer.set_geometry(Sphere(.5))
    group = StatisticalGroup('Counted group', config['group_id'], config,
                             config['seed'])
    group.set_geometry(Sphere(5))
    world.add_object(group)

    # Commit the existing aggregate before selecting a slot. The member is a
    # realization of this composition, not an arrival or additional member.
    formation_counts = group.counts()
    member = group.realize_being(world, 0, 'adults', 0)
    # Supply the same simple body geometry the Spot fixture uses for other
    # Beings, so the native sightline adapter need not refuse an unmodeled
    # Encounter participant.
    member.set_geometry(Sphere(.5))
    repeated_member = group.realize_being(world, 0, 'adults', 0)
    if repeated_member is not member:
        raise AssertionError('same Group slot did not retain its Being identity')
    counts_after_realization = group.counts()
    if counts_after_realization != formation_counts:
        raise AssertionError('member realization changed the Group formation count')

    encounter = Encounter(world, difficulty_class=15, start_time=0,
                          initiated=True, name='Counted member interaction')
    world.add_event(encounter)
    for observer in observers:
        encounter.add_being(observer.id)
    encounter.add_being(member.id)
    encounter.add_object(group.id)
    ledgers = [BeliefLedger(observer.id) for observer in observers]
    rng = RNGCursor(random.Random(5302).getstate())
    encounter.enable_transactional_progression(quiescent=True, rng_owner=rng)
    spot = SpotAction(world, observers[0].id, group.id, 0, die_roll=20,
        id='counted-member-spot-1', ledger=ledgers[0],
        group_fully_visible=True)
    encounter.schedule_choice((spot,))
    spots = (spot,)
    return (world, encounter, observers, group, member, ledgers, spots, rng,
            formation_counts)


def run_scenario():
    (world, encounter, observers, group, member, ledgers, spots, rng,
     formation_counts) = prepare_scenario()
    rng_before = rng.state
    encounter.step(6)
    spot_inspection = encounter.inspect_committed()

    # The realized Being is an ordinary native Encounter participant and can
    # perform an existing Action. This does not change Group membership/count.
    run = RunAction(world, member.id, 6, 1, 1, experience=7,
                    id='counted-member-run')
    encounter.schedule_choice((run,))
    encounter.step(1, velocities={member.id: (2, 0, 0)})
    inspection = encounter.inspect_committed()
    observation = ledgers[0].evidence[0]
    member_id = member.id
    observation_payload = repr(observation)
    return {
        'presentation': 'omniscient developer inspection, not an Agent interface',
        'realization_timing': 'initial configuration, before Encounter construction',
        'member': {
            'logical_id': member_id,
            'group_member': group.has_realized_member(member),
            'formation_slot': (0, 'adults', 0),
            'position': member.get_position().as_tuple(),
            'beings_realized': group.realized_being_count,
            'unresolved_adult_slots': group.known_skill_state('spot')['unresolved_adults'],
        },
        'group_counts_unchanged': formation_counts == group.counts(),
        'observer_one': {
            'exact_visible_aggregate_count': observation.reports['visible_count'].estimate,
            'uncertainty': observation.reports['visible_count'].uncertainty,
            'member_identity_in_evidence': member_id in observation_payload,
            'spot_action_boundary': spot_inspection.action(spots[0].id).resolved_boundary,
        },
        'observer_two_received_evidence': bool(ledgers[1].evidence),
        'native_run': {
            'outcome': inspection.action(run.id).facts.outcome,
            'displacement_m': dict(inspection.action(run.id).facts.metadata)['displacement'],
            'target_owned_run_experience': member.get_skill_experience('run'),
        },
        'rng_unchanged': rng.state == rng_before,
        'encounter_time': encounter.time,
        'group_counts': group.counts(),
        'member_registry_identity_preserved': world.get_object_by_id(member_id) is member,
        'spot_experience': tuple(observer.get_skill_experience('spot')
                                 for observer in observers),
    }


if __name__ == '__main__':
    print(json.dumps(run_scenario(), indent=2, sort_keys=True))
