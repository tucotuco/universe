"""Move one realized adult between Groups without rebuilding that individual's past.

Run from the Universe repository root:
    python examples/group_membership_transfer.py

The scenario is a membership experiment, not a social or travel simulator.
"""
from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from library import Library
from statistical_group import StatisticalGroup
from universe import Universe


def run_experiment():
    base = json.loads((ROOT / 'examples/nomadic_group.json').read_text())
    correlation = json.loads((ROOT / 'examples/nomadic_group_correlations.json').read_text())
    source_spec = deepcopy(base)
    source_spec.update(correlation)
    source_spec['group_id'], source_spec['group_name'] = 'western-caravan', 'Western caravan'
    destination_spec = deepcopy(base)
    destination_spec['group_id'], destination_spec['group_name'] = 'eastern-caravan', 'Eastern caravan'
    destination_spec['seed'] = base['seed'] + 1
    destination_spec['motion']['position'] = [v + 50 for v in base['motion']['position']]

    world = Universe('Transfer experiment', library=Library(config_dir=str(ROOT / 'src/config')))
    western = StatisticalGroup(source_spec['group_name'], source_spec['group_id'],
                               source_spec, source_spec['seed'])
    eastern = StatisticalGroup(destination_spec['group_name'], destination_spec['group_id'],
                               destination_spec, destination_spec['seed'])
    world.add_object(western)
    world.add_object(eastern)

    key = (0, 'adults', 0)
    role = western.formation_attribute(*key, 'role')
    herder = western.realize_being(world, *key, name='Traveler')
    herder.set_skill_level(world.get_skill_dictionary(), 'spot', 6)
    original_position = herder.get_position()
    original_identity = herder.id
    baseline = (western.counts(), eastern.counts())
    departure = western.transfer_being_to(world, herder, eastern, time=0)
    after_departure = (western.current_counts(), eastern.current_counts())
    known_in_east = eastern.known_skill_state('spot')['known'][herder.id]['level']

    # Advance both group clocks before a second transfer at time 1. Membership
    # itself does not relocate or couple the traveler to the destination's motion.
    western.advance(1)
    eastern.advance(1)
    arrival_home = eastern.transfer_being_to(world, herder, western, time=1)
    after_return = (western.current_counts(), eastern.current_counts())
    assert herder.id == original_identity and herder.get_position() == original_position
    assert western.realize_being(world, *key) is herder

    return {
        'world': world, 'western': western, 'eastern': eastern,
        'herder': herder, 'role': role, 'baseline': baseline,
        'departure': departure, 'return': arrival_home,
        'after_departure': after_departure, 'after_return': after_return,
        'known_spot_in_east': known_in_east,
    }


if __name__ == '__main__':
    r = run_experiment()
    print('Original group composition (west/east adults):',
          *(g['adults'] for g in r['baseline']))
    print('After transfer, current adults (west/east):',
          *(g['adults'] for g in r['after_departure']))
    print('Eastern known arrival Spotting level:', r['known_spot_in_east'])
    print('After return, current adults (west/east):',
          *(g['adults'] for g in r['after_return']))
    print('Formation role remains in original Group:', r['role'])
    print('Transfers in western history:',
          [e.to_dict() for e in r['western'].membership_history])
    print('Same Being retained:',
          r['world'].get_object_by_id(r['herder'].id) is r['herder'])
