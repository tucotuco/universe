"""Action-driven nomadic group observation: learned skill, fallible evidence, beliefs.

Run from repo root: python examples/group_observation_encounter.py
This is range-gated proxy sensing, *not* simulated light or terrain vision.
"""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from encounter import Encounter
from field_observation import BeliefLedger
from group_observation import ObserveGroupAction
from library import Library
from spatial.state import CartesianPosition
from statistical_group import StatisticalGroup
from universe import Universe


def run_scenario(config=None, seed=None):
    if config is None:
        config = json.loads((Path(__file__).with_name('nomadic_group.json')).read_text())
    action_settings = config.get('action_observation', {})
    if seed is None:
        seed = action_settings.get('seed', 62)
    world = Universe('Skill-driven field observation', library=Library(
        config_dir=str(ROOT / 'src' / 'config')))
    group = StatisticalGroup(config['group_name'], config['group_id'], config, seed=config['seed'])
    world.add_object(group)
    scouts = {}
    ledgers = {}
    for role in ('son', 'father'):
        properties = config['scouts'][role]
        identifier = world.make_being('Human', properties['name'])
        being = world.get_object_by_id(identifier)
        being.set_skill_level(world.get_skill_dictionary(), 'spot', properties['spot_level'])
        being.set_position(CartesianPosition(*properties['position']))
        scouts[role] = being
        ledgers[role] = BeliefLedger(identifier)

    encounter = Encounter(world, difficulty_class=10, start_time=0)
    for scout in scouts.values():
        encounter.add_being(scout.id)
    encounter.add_object(group.id)
    # Range-only awareness of *group presence* allows a decision to investigate.
    # Its composition is still unrealized; subsequent observation Actions may fail.
    encounter.perceive_within(scouts['son'].id, config['observation']['coarse_range_m'])
    assert encounter.decide_to_act(scouts['son'].id, group.id, 'observe traveling group')
    initially_unrealized = (group._counts is None, group.materialized_count)

    observation_cfg = dict(action_settings.get('sensor', config['observation']))
    interpretation_cfg = dict(config['interpretation'])
    experience_cfg = dict(action_settings.get('experience', {'success': 12, 'failure': 18}))
    actions = []

    def observe(role, time):
        actor = scouts[role]
        action = ObserveGroupAction(
            world, actor.id, group.id, start_time=time,
            seed=seed, random_key=role,
            observation=observation_cfg,
            interpretation=interpretation_cfg,
            experience=experience_cfg, ledger=ledgers[role])
        encounter.schedule_action(action)
        actions.append((role, action))

    # Two perspectives, with an intervening 100-second group movement.
    for role in ('son', 'father'):
        observe(role, 0)
    group.advance(1)
    encounter.step(duration=1)
    group.advance(99)
    encounter.step(duration=99)
    for role in ('son', 'father'):
        observe(role, 100)
    group.advance(1)
    encounter.step(duration=1)

    # Communication transmits original evidence and its source interpretation.
    exchanged = (
        ledgers['son'].share_from(ledgers['father']),
        ledgers['father'].share_from(ledgers['son']),
    )
    discrepancies = ledgers['son'].discrepancies(group.id)
    predicted = ledgers['son'].predict_position(group.id, 160)
    reachable = group.reachable_at(160)
    return {
        'world': world, 'encounter': encounter, 'group': group,
        'scouts': scouts, 'ledgers': ledgers, 'actions': actions,
        'initially_unrealized': initially_unrealized,
        'exchanged': exchanged, 'discrepancies': discrepancies,
        'materialized': group.materialized_count,
        'son_prediction': predicted, 'reachable': reachable,
    }


if __name__ == '__main__':
    result = run_scenario()
    print('Statistical composition initially unresolved:', result['initially_unrealized'])
    print('Counts now committed (no members created):', result['group'].counts())
    for role, action in result['actions']:
        evidence, belief = action.field_observation, action.field_interpretation
        print(f'{role} t={action.end_time:g} | spot rank={action.skill_level_used} | '
              f'roll={action.roll} | outcome={action.resolution.outcome} | '
              f'dog evidence={None if evidence is None else evidence.reports["dogs"].estimate} | '
              f'dog interpretation={None if belief is None else belief.reports["dogs"].estimate}')
    print('Spotting experience:', {role: being.get_skill_experience('spot')
          for role, being in result['scouts'].items()})
    print('Communication new evidence:', result['exchanged'])
    print('Discrepancies:', result['discrepancies'])
    print('Son predicted group position:', result['son_prediction'])
    print('Actual dynamically reachable region:', result['reachable'])
    print('Members materialized:', result['materialized'])
