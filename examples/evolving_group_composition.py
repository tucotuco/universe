"""Original cohort quotas versus evolving resident composition.

Run from repository root: python examples/evolving_group_composition.py
Formation trait assignments are private truth used by this controlled test,
not observations available to Scouts or the public simulation layer.
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


def make_world():
    baseline = json.loads((ROOT / 'examples/nomadic_group.json').read_text())
    correlations = json.loads((ROOT / 'examples/nomadic_group_correlations.json').read_text())
    world = Universe('Evolving statistical composition',
                     library=Library(config_dir=str(ROOT / 'src/config')))
    groups = []
    for i, title in enumerate(('Western caravan', 'Eastern caravan')):
        config = deepcopy(baseline)
        config.update(deepcopy(correlations))
        config.update(group_id=f'caravan-{i}', group_name=title, seed=8101 + i)
        config['motion']['position'][0] += 100 * i
        group = StatisticalGroup(title, config['group_id'], config, config['seed'])
        world.add_object(group)
        groups.append(group)
    return world, groups


def trained_key(group):
    qualified = group._adult_formation_assignments('trained_spotter')
    for household in range(group.household_count):
        for index in range(group.household(household)['adults']):
            if f'{group.id}/{household}/adults/{index}' in qualified:
                return household, 'adults', index
    raise AssertionError('expected at least one trained member')


def run_experiment():
    world, (west, east) = make_world()
    baseline = [g.current_formation_trait_state('trained_spotter') for g in (west, east)]
    travelers = [g.realize_being(world, *trained_key(g)) for g in (west, east)]
    after_realization = [g.current_formation_trait_state('trained_spotter') for g in (west, east)]

    for group in (west, east):
        group.advance(1)
    west_leave = west.leave_being(world, travelers[0])
    east_leave = east.leave_being(world, travelers[1])
    after_departure = [g.current_formation_trait_state('trained_spotter') for g in (west, east)]

    for group in (west, east):
        group.advance(1)
    # These are separate joins; there is no atomic transfer primitive.
    west_join = west.join_being(world, travelers[1])
    east_join = east.join_being(world, travelers[0])
    after_joins = [g.current_formation_trait_state('trained_spotter') for g in (west, east)]

    # Current ability changes independently of each Group's original cohort.
    travelers[1].set_skill_level(world.get_skill_dictionary(), 'spot', 7)
    after_learning = west.current_formation_trait_state('trained_spotter')
    known_spot = west.known_skill_state('spot')

    # Sample an attribute of a STILL UNREALIZED native of the west Group.
    native_key = next((h, 'adults', n) for h in range(west.household_count)
                      for n in range(west.household(h)['adults'])
                      if (h, 'adults', n) != trained_key(west))
    original_unresolved = west.realized_being_count
    role = west.formation_attribute(*native_key, 'role')
    assert west.realized_being_count == original_unresolved
    return dict(world=world, west=west, east=east, travelers=travelers,
                baseline=baseline, after_realization=after_realization,
                after_departure=after_departure, after_joins=after_joins,
                after_learning=after_learning, known_spot=known_spot,
                unresolved_member_role=role,
                changes=(west_leave, east_leave, west_join, east_join))


if __name__ == '__main__':
    result = run_experiment()
    for phase in ('baseline', 'after_realization', 'after_departure', 'after_joins'):
        states = result[phase]
        print(phase + ':')
        for label, state in zip(('west', 'east'), states):
            cohort = state['resident_original_cohort']
            print(f"  {label}: adults={state['current_adults']}, "
                  f"resident_original_trained={cohort['realized_qualified'] + cohort['unresolved_qualified']}, "
                  f"unresolved_trained={cohort['unresolved_qualified']}, "
                  f"arrivals={state['arrivals']['adults']}")
    print('Current spot level of west newcomer:',
          result['known_spot']['known'][result['travelers'][1].id]['level'])
    print('Original quotas unchanged:',
          [g.formation_trait_state('trained_spotter')['committed_qualified']
           for g in (result['west'], result['east'])])
    print('Role resolved without realizing another Being:', result['unresolved_member_role'])
