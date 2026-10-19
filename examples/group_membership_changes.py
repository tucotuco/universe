"""Independent Group departure and joining, separated by time outside any Group.

Run from the repository root: python examples/group_membership_changes.py
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
    config_a = deepcopy(base)
    config_b = deepcopy(base)
    config_a.update(group_id='western-caravan', group_name='Western caravan')
    config_b.update(group_id='eastern-caravan', group_name='Eastern caravan', seed=base['seed'] + 1)
    config_b['motion']['position'][0] += 100
    world = Universe('Independent membership example', library=Library(config_dir=str(ROOT / 'src/config')))
    a = StatisticalGroup('Western', config_a['group_id'], config_a, config_a['seed'])
    b = StatisticalGroup('Eastern', config_b['group_id'], config_b, config_b['seed'])
    world.add_object(a)
    world.add_object(b)
    being = a.realize_being(world, 0, 'adults', 0, name='Traveler')
    being.set_skill_level(world.get_skill_dictionary(), 'spot', 5)
    base_counts = (a.counts(), b.counts())

    a.advance(1)
    b.advance(1)
    left = a.leave_being(world, being, time=1)
    alone_counts = (a.current_counts(), b.current_counts())
    assert not a.has_realized_member(being) and not b.has_realized_member(being)

    # During the gap, independent Entity state and history can still change.
    # A later membership has no influence on identity or skill state.
    being.set_skill_level(world.get_skill_dictionary(), 'spot', 6)
    a.advance(4)
    b.advance(4)
    joined = b.join_being(world, being, time=5)
    joined_counts = (a.current_counts(), b.current_counts())
    assert a.realize_being(world, 0, 'adults', 0) is being
    return dict(world=world, western=a, eastern=b, being=being,
                baseline=base_counts, alone_counts=alone_counts,
                joined_counts=joined_counts, leave=left, join=joined)


if __name__ == '__main__':
    result = run_experiment()
    print('Formation adults, west/east:', *(c['adults'] for c in result['baseline']))
    print('During independent interval:', *(c['adults'] for c in result['alone_counts']))
    print('After joining eastern:', *(c['adults'] for c in result['joined_counts']))
    print('Member history:', result['leave'].to_dict(), result['join'].to_dict())
    print('Spotting retained:', result['being'].get_skill_level('spot'))
