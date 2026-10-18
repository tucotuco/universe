"""Demonstrate latent, conditional formation attributes and fixed cohort quotas.

This is an experiment in generation consistency, not a demographic or causal
model of real pastoral groups. Run from root:
    python examples/correlated_group_attributes.py
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
    config = deepcopy(json.loads((ROOT / 'examples/nomadic_group.json').read_text()))
    config.update(json.loads((ROOT / 'examples/nomadic_group_correlations.json').read_text()))
    world = Universe('Correlated formation experiment',
                     library=Library(config_dir=str(ROOT / 'src/config')))
    group = StatisticalGroup(config['group_name'], config['group_id'], config, config['seed'])
    world.add_object(group)
    keys = [(household, 'adults', index)
            for household in range(group.household_count)
            for index in range(group.household(household)['adults'])]
    assigned = group._adult_formation_assignments('trained_spotter')
    key_for_id = lambda key: f'{group.id}/{key[0]}/adults/{key[2]}'
    trained = next(key for key in keys if key_for_id(key) in assigned)
    other = next(key for key in keys if key_for_id(key) not in assigned)

    before = group.committed_formation_attributes(*trained)
    role = group.formation_attribute(*trained, 'role')
    after_role = group.committed_formation_attributes(*trained)
    experience = group.formation_attribute(*trained, 'years_in_role')
    other_details = {name: group.formation_attribute(*other, name)
                     for name in ('age_band', 'role', 'years_in_role')}
    being = group.realize_being(world, *trained)
    return {
        'group': group, 'trained': trained, 'other': other,
        'before': before, 'after_role': after_role, 'role': role,
        'years_in_role': experience, 'other_details': other_details,
        'being': being, 'quota': group.formation_trait_state('trained_spotter'),
    }


if __name__ == '__main__':
    result = run_experiment()
    group = result['group']
    print('Group composition:', group.counts())
    print('Attributes before query:', result['before'])
    print('After querying role (parent resolved):', result['after_role'])
    print('After querying years in role:', group.committed_formation_attributes(*result['trained']))
    print('Untrained member:', result['other_details'])
    print('Fully realized Beings:', group.realized_being_count)
    print('Known original spotter quota:', result['quota'])
