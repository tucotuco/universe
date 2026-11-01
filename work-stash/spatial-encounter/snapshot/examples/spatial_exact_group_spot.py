"""Two observers obtain exact visible aggregate evidence through native Spot.

Run with ``python examples/spatial_exact_group_spot.py``. The fixture premise
declares every member of this statistical Group visible. The engine validates
the ordinary Spot path but does not model member-level visibility. Evidence
contains only an aggregate count: no Group center or species categories.
"""
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from activities import SpotAction
from atomic_publication import RNGCursor
from encounter import Encounter
from field_inquiry import InquiryPolicy
from field_observation import BeliefLedger
from library import Library
from spatial import CartesianPosition, Sphere
from statistical_group import StatisticalGroup
from universe import Universe


def run_scenario():
    config = json.loads((ROOT / 'examples' / 'nomadic_group.json').read_text())
    config['group_id'] = 'fully-visible-statistical-group'
    config['motion'].update(position=[0, 0, 0], velocity=[0, 0, 0], acceleration=[0, 0, 0])
    world = Universe('Exact visible Group Spot',
        library=Library(config_dir=str(ROOT / 'src' / 'config')))
    ids = [world.make_being('Human', label) for label in ('Observer one', 'Observer two')]
    observers = [world.get_object_by_id(key) for key in ids]
    observers[0].set_position(CartesianPosition(0, -20, 0))
    observers[1].set_position(CartesianPosition(20, -20, 0))
    for observer in observers:
        observer.set_geometry(Sphere(.5))
    group = StatisticalGroup('Fully visible training group', config['group_id'],
                             config, config['seed'])
    group.set_geometry(Sphere(5))
    world.add_object(group)
    encounter = Encounter(world, difficulty_class=15, start_time=0, initiated=True,
                          name='Exact Group Observation')
    world.add_event(encounter)
    for observer in observers:
        encounter.add_being(observer.id)
    encounter.add_object(group.id)
    ledgers = [BeliefLedger(observer.id) for observer in observers]
    rng = RNGCursor(random.Random(5102).getstate())
    encounter.enable_transactional_progression(quiescent=True, rng_owner=rng)
    actions = [SpotAction(world, observer.id, group.id, 0, die_roll=20,
        id=f'exact-visible-spot-{index + 1}', ledger=ledger,
        group_fully_visible=True)
        for index, (observer, ledger) in enumerate(zip(observers, ledgers))]
    for action in actions:
        encounter.schedule_choice((action,))
    encounter.step(6)
    inspection = encounter.inspect_committed()
    inquiries = [InquiryPolicy(relative_uncertainty_threshold=.5).propose(
        ledger, group.id, encounter.time) for ledger in ledgers]
    return world, encounter, observers, group, ledgers, actions, inspection, inquiries, rng


def demo_data():
    _, encounter, observers, group, ledgers, actions, inspection, inquiries, rng = run_scenario()
    return {
        'presentation': 'omniscient developer demonstration, not an Agent interface',
        'visibility_premise': 'the fixture declares the whole Group visible before either Action; member-level visibility is not engine-modeled',
        'encounter': {'time': encounter.time, 'committed_boundaries': tuple(row.boundary for row in inspection.timeline)},
        'group_reality_developer_view': dict(group.counts()),
        'materialized_members': group.materialized_count,
        'observations': tuple({
            'action_id': action.id,
            'boundary': inspection.action(action.id).resolved_boundary,
            # Being and evidence IDs are generated process-local identities;
            # the reproducible comparison reports roles and causal Actions.
            'target_group_id': evidence.group_id,
            'outcome': inspection.action(action.id).facts.outcome,
            'visible_count': evidence.reports['visible_count'].estimate,
            'uncertainty': evidence.reports['visible_count'].uncertainty,
            'reported_position': evidence.reported_position,
            'species_categories_disclosed': tuple(sorted(set(evidence.reports) - {'visible_count'})),
            'owner_has_evidence': evidence.id in {item.id for item in ledgers[index].evidence},
            'other_observer_has_evidence': evidence.id in {item.id for item in ledgers[1-index].evidence},
            'inquiry_policy_result': inquiries[index],
        } for index, (action, evidence) in enumerate(zip(actions, (ledger.evidence[0] for ledger in ledgers)))),
        'spot_experience': tuple(observer.get_skill_experience('spot') for observer in observers),
        'rng_state_version': rng.state[0],
        'scope_note': 'No uncertainty-driven follow-up is selected; the previous noisy Group inquiry branch is intentionally absent.',
    }


if __name__ == '__main__':
    print(json.dumps(demo_data(), indent=2, sort_keys=True))
