"""Discover an earlier life episode after the Being has already acted.

Run from the repository root: python examples/historical_being_realization.py
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from being import BeingDefinition, BeingInstance
from library import Library
from realization import Fact, ImpossibleRealization
from universe import Universe


def run_experiment():
    world = Universe('Discoverable world', library=Library(config_dir=str(ROOT/'src/config')))
    being = BeingInstance(BeingDefinition('Human', 6, 170, 10, '2d6',
                                           'Neutral', 10, 1), 'Traveler')
    world.add_object(being)
    being.set_skill_level(world.get_skill_dictionary(), 'run', 2)
    later = being.record_skill_use(world.get_skill_dictionary(), 'run', 0,
                                   action_id='later_journey', time=50)
    life = being.begin_personal_history(earliest=-15, known_through=60,
                                        nondeclining_skills=('run',))
    assert life.inspect_episode(10, 'river_lessons') is None

    def propose(view, rank):
        return (
            Fact(life.episode_key(10, 'river_lessons'), {
                'description': 'Practiced running with an older sibling beside the river',
                'skill': 'run', 'rank_after': rank,
            }, 'retrospective_realization'),
            Fact(life.skill_key(10, 'run'), rank, 'retrospective_realization'),
        )

    try:
        life.realize_episode(10, 'river_lessons', lambda view: propose(view, 3))
    except ImpossibleRealization:
        print('A rank-3 childhood proposal was rejected: later known rank was 2.')

    found = life.realize_episode(10, 'river_lessons', lambda view: propose(view, 1))
    revisited = life.realize_episode(10, 'river_lessons',
                                     lambda view: (_ for _ in ()).throw(AssertionError('resampled')))
    assert found.record == revisited.record and not revisited.newly_realized
    assert later in being.skill_use_history and being.get_skill_level('run') == 2
    print('Committed childhood detail:', found.record.value['description'])
    print('Revisited later:', revisited.record.value['description'])
    print('Existing later skill and objective action remain unchanged.')
    print('No observer Perception or Belief is implied by objective realization.')
    return being


if __name__ == '__main__':
    run_experiment()
