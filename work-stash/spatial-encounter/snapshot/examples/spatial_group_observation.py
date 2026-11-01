"""EXPERIMENTAL: one transactional observation of an unresolved Group.

Run with ``python examples/spatial_group_observation.py``. Coordinates describe
a local simulation frame in metres, not a real-world reference system. Group
composition is resolved by the supported objective Reality transaction; the
observer's noisy evidence and Belief remain observer-owned.
"""
from pathlib import Path
import json
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from atomic_publication import RNGCursor
from encounter import Encounter
from field_observation import BeliefLedger
from group_observation import ObserveGroupAction
from library import Library
from spatial import CartesianPosition, ISEAGrid
from statistical_group import StatisticalGroup
from universe import Universe


def _build_scenario(*, observer_position=(0, -200, 1000),
                    other_position=(0, -300, 1000), advance=True):
    config = json.loads((ROOT / 'examples' / 'nomadic_group.json').read_text())
    config['group_id'] = 'spatial-statistical-group'
    config['group_name'] = 'Spatial statistical group'
    config['motion'].update(position=[0, 0, 1000], velocity=[0, 0, 0],
                            acceleration=[0, 0, 0])

    world = Universe('Spatial Group observation',
        library=Library(config_dir=str(ROOT / 'src' / 'config')))
    observer_id = world.make_being('Human', 'Observer')
    other_id = world.make_being('Human', 'Uninformed observer')
    observer = world.get_object_by_id(observer_id)
    other = world.get_object_by_id(other_id)
    observer.set_skill_level(world.get_skill_dictionary(), 'spot', 1)
    other.set_skill_level(world.get_skill_dictionary(), 'spot', 1)
    observer.set_position(CartesianPosition(*observer_position))
    other.set_position(CartesianPosition(*other_position))
    group = StatisticalGroup(config['group_name'], config['group_id'], config,
                             seed=config['seed'])
    world.add_object(group)

    encounter = Encounter(world, difficulty_class=10, start_time=0,
        initiated=True, name='Spatial Group Observation Encounter')
    world.add_event(encounter)
    encounter.add_being(observer_id)
    encounter.add_being(other_id)
    encounter.add_object(group.id)
    observer_beliefs = BeliefLedger(observer_id)
    other_beliefs = BeliefLedger(other_id)

    # The native keyed d20 yields 12 for this declared seed/key/target/start.
    # The existing observation and interpretation algorithms still run normally.
    rng = RNGCursor(random.Random(5102).getstate())
    encounter.enable_transactional_progression(quiescent=True, rng_owner=rng)
    action = ObserveGroupAction(world, observer_id, group.id, 0,
        seed=0, random_key='observer', observation=config['observation'],
        interpretation=config['interpretation'], ledger=observer_beliefs)
    choice = encounter.schedule_choice((action,))
    inspection = None
    if advance:
        encounter.step(1)
        inspection = encounter.inspect_committed()
    return (world, encounter, observer, other, group, observer_beliefs,
            other_beliefs, action, choice, rng, inspection)


def demo_data():
    (_, encounter, observer, other, group, observer_beliefs, other_beliefs,
     action, choice, rng, inspection) = _build_scenario()
    grid = ISEAGrid(radius=1.0)
    group_truth = group.counts()
    evidence = observer_beliefs.evidence[-1]
    interpretation = observer_beliefs.interpretation_for(action.id)
    action_record = inspection.action(action.id)
    target_record = inspection.target(observer.id)
    practice = target_record.practice_history[-1]
    truth = {name: group_truth[name] for name in ('humans', 'livestock', 'dogs')}
    estimates = {name: evidence.reports[name].estimate
                 for name in ('humans', 'livestock', 'dogs')}
    return {
        'coordinate_contract': 'local Cartesian simulation coordinates in metres; not a geographic reference frame',
        'encounter': {
            'id': encounter.id, 'time': encounter.time,
            'committed_boundary': inspection.boundary,
            'member_ids': tuple(encounter.being_list),
            'group_id': group.id,
        },
        'positions': {
            'observer': observer.get_position().as_tuple(),
            'uninformed_observer': other.get_position().as_tuple(),
            'group': group.get_position().as_tuple(),
        },
        'derived_isea_cells': {
            'observer': str(observer.spatial_cell(grid, 5)),
            'uninformed_observer': str(other.spatial_cell(grid, 5)),
            'group': str(group.spatial_cell(grid, 5)),
        },
        'group': {
            'id': group.id,
            'objective_composition': truth,
            'realized_being_count': group.materialized_count,
            'objective_fact_count': len(group._composition_reality.view().all_facts()),
        },
        'observation': {
            'action_id': action.id, 'choice_id': choice.id,
            'actor_id': action_record.declaration.actor_id,
            'target_id': action_record.facts.target_ids[0],
            'outcome': action_record.facts.outcome,
            'observation_id': evidence.id,
            'evidence_observer_id': evidence.observer_id,
            'evidence_group_id': evidence.group_id,
            'evidence_time': evidence.time,
            'evidence_estimates': estimates,
            'evidence_uncertainty': {name: evidence.reports[name].uncertainty
                                     for name in estimates},
            'interpretation_estimates': {name: interpretation.reports[name].estimate
                                         for name in estimates},
            'estimates_differ_from_objective': any(estimates[k] != truth[k] for k in truth),
            'observer_has_belief': bool(observer_beliefs.evidence),
            'belief_revision_count': len(observer_beliefs.belief_history),
            'other_being_has_no_belief': not other_beliefs.evidence,
        },
        'practice': {
            'owner_id': observer.id,
            'experience': observer.get_skill_experience('spot'),
            'history_time': practice.time,
            'exercise_action_id': practice.exercises[0].action_id,
            'exercise_effect_identity': str(practice.exercises[0].effect_identity),
        },
        'rng_state_version': rng.state[0],
    }


if __name__ == '__main__':
    print(json.dumps(demo_data(), indent=2, sort_keys=True))
