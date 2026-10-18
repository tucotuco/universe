"""Demonstrate realized Being consequences reflected in statistical group views.

Run from repository root: python examples/group_aggregate_consequences.py
The scripted health transition is an integration fixture, NOT combat physics.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from action import Action
from activities import RunAction
from encounter import Encounter
from experience import ActionResolution
from realized_herder_encounter import run_scenario


class ScriptedHealthChange(Action):
    """Test/demo event: apply a stated health outcome with explicit provenance."""

    def __init__(self, universe, actor_id, time, hit_points):
        super().__init__(universe, time, None, 'scripted_health_change',
                         actor_id, actor_id, None)
        self.end_time = time + 1
        self.hit_points_result = hit_points

    def resolve(self, difficulty_class):
        self.get_target().set_hit_points(self.hit_points_result)
        return ActionResolution('health_changed')


def run_scenario_with_consequences():
    result = run_scenario()
    group, herder, encounter = result['group'], result['herder'], result['encounter']
    initial = result['counts_before']
    practiced = group.known_skill_state('run')
    before = group.aggregate_state()

    incapacitating = ScriptedHealthChange(result['world'], herder.id,
                                          encounter.time, 0)
    encounter.schedule_action(incapacitating)
    encounter.step(1)
    incapacitated = group.aggregate_state()

    fatal = ScriptedHealthChange(result['world'], herder.id,
                                encounter.time, -10)
    encounter.schedule_action(fatal)
    encounter.step(1)
    deceased = group.aggregate_state()
    assert group.counts() == initial
    return dict(result, practiced=practiced, before=before,
                incapacitated=incapacitated, deceased=deceased,
                health_actions=(incapacitating, fatal))


if __name__ == '__main__':
    states = run_scenario_with_consequences()
    print('Committed composition:', states['before']['composition'])
    print('Herder run capability:', states['practiced']['known'])
    for label in ('before', 'incapacitated', 'deceased'):
        print(f'{label} adult status:', states[label]['categories']['adults'])
    print('Recorded Encounter health action IDs:',
          [event.id for event in states['health_actions']])
