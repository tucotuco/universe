"""Compare a fixed formation quota with subsequent Being capability changes.

This is an ontological-refinement experiment; scouts never receive private
trait assignments through their observation/belief interfaces.
Run: python examples/conditional_group_refinement.py
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
    config = deepcopy(json.loads((ROOT / 'examples' / 'nomadic_group.json').read_text()))
    config['formation_traits'] = {
        'adults': {'trained_spotter': {'count': 2, 'initial_skills': {'spot': 4}}}}
    world = Universe('Coherent refinement', library=Library(config_dir=str(ROOT / 'src' / 'config')))
    group = StatisticalGroup(config['group_name'], config['group_id'], config, config['seed'])
    world.add_object(group)
    initial = group.formation_trait_state('trained_spotter')
    adult_keys = [(household, 'adults', index)
                  for household in range(group.household_count)
                  for index in range(group.household(household)['adults'])]
    # The test harness (not an Agent) selects contrasting cases from the
    # private formation allocation, so the small demonstration is informative.
    assigned = group._adult_formation_assignments('trained_spotter')
    def member_id(key):
        return f'{group.id}/{key[0]}/adults/{key[2]}'
    trained = next(key for key in adult_keys if member_id(key) in assigned)
    other = next(key for key in adult_keys if member_id(key) not in assigned)
    first = group.realize_being(world, *trained)
    after_first = group.formation_trait_state('trained_spotter')
    second = group.realize_being(world, *other)
    after_second = group.formation_trait_state('trained_spotter')
    original_levels = (first.get_skill_level('spot') or 0,
                       second.get_skill_level('spot') or 0)
    # A scripted *later* skill gain by a formerly untrained person affects
    # current capability only, not the historical formation-time quota.
    second.set_skill_level(world.get_skill_dictionary(), 'spot', 6)
    after_training = group.formation_trait_state('trained_spotter')
    return dict(group=group, first=first, second=second, initial=initial,
                after_first=after_first, after_second=after_second,
                after_training=after_training, initial_levels=original_levels,
                current=group.known_skill_state('spot'))


if __name__ == '__main__':
    result = run_experiment()
    for label in ('initial', 'after_first', 'after_second', 'after_training'):
        print(f'{label}: {result[label]}')
    print('First two realized initial spot levels:', result['initial_levels'])
    print('Known current spot levels:', result['current'])
    print('Original adult cohort count:', result['group'].counts()['adults'])
    print('Fully realized Beings:', result['group'].realized_being_count)
