"""Minimal spatial Encounter → deliberate Spot → observer awareness demonstration.

Run from any directory with ``python examples/spatial_spot_encounter.py``.
The positions describe a unit-sphere scenario in the native Cartesian frame;
the ISEA cell is derived indexing context, not a physical coordinate.
"""
from pathlib import Path
import json
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from activities import SpotAction
from action_evaluation import AwarenessEffect
from atomic_publication import RNGCursor
from encounter import Encounter
from library import Library
from spatial import CartesianPosition, ISEAGrid, Sphere
from universe import Universe


def _build_scenario():
    world = Universe('Spatial Spot demonstration',
        library=Library(config_dir=str(ROOT / 'src' / 'config')))
    observer_id = world.make_being('Human', 'Observer')
    observed_id = world.make_being('Human', 'Observed Being')
    observer = world.get_object_by_id(observer_id)
    observed = world.get_object_by_id(observed_id)

    # These are authoritative native Object positions.  The derived ISEA
    # overlay uses the same origin-centred unit-sphere scenario.
    observer.set_position(CartesianPosition.from_lat_lon(0.0, 0.0, 1.0))
    observed.set_position(CartesianPosition.from_lat_lon(0.0, 1.0, 1.0))
    observed.set_geometry(Sphere(0.1))

    encounter = Encounter(world, difficulty_class=11, start_time=0,
        initiated=True, name='Spatial Spot Encounter')
    world.add_event(encounter)
    encounter.add_being(observer_id)
    encounter.add_being(observed_id)

    # The explicit natural 20 makes this demonstration reproducible while
    # retaining the native Spot check and transaction route.
    rng = RNGCursor(random.Random(5101).getstate())
    encounter.enable_transactional_progression(quiescent=True, rng_owner=rng)
    action = SpotAction(world, observer_id, observed_id, start_time=0,
        duration=6, die_roll=20)
    choice = encounter.schedule_choice((action,))
    encounter.step(6)
    inspection = encounter.inspect_committed()
    return world, encounter, observer, observed, action, choice, rng, inspection


def demo_data():
    world, encounter, observer, observed, action, choice, rng, inspection = _build_scenario()
    grid = ISEAGrid(radius=1.0)
    level = 5
    action_record = inspection.action(action.id)
    target_record = inspection.target(observer.id)
    position_rows = {}
    for label, being in (('observer', observer), ('observed', observed)):
        position = being.get_position()
        position_rows[label] = {
            'being_id': being.id,
            'encounter_member': being.id in encounter.being_list,
            'cartesian': position.as_tuple(),
            'angular_from_world_origin': position.angular_coordinate(),
            'isea_trifold_cell': str(being.spatial_cell(grid, level)),
            'isea_level': level,
        }
    facts = action_record.facts
    metadata = dict(facts.metadata)
    awareness = next(row.effect for row in action_record.effects
                     if type(row.effect) is AwarenessEffect)
    return {
        'coordinate_contract': {
            'frame': 'origin-centred unit-sphere scenario coordinates',
            'isea_cell_role': 'derived indexing overlay; continuous position remains authoritative',
        },
        'encounter': {
            'id': encounter.id,
            'name': encounter.name,
            'time': encounter.time,
            'committed_boundary': inspection.boundary,
            'member_ids': tuple(encounter.being_list),
            'event_location_metadata': encounter.location,
        },
        'beings': position_rows,
        'spot': {
            'action_id': action.id,
            'choice_id': choice.id,
            'actor_id': action_record.declaration.actor_id,
            'observed_target_id': facts.target_ids[0],
            'outcome': facts.outcome,
            'distance': awareness.distance,
            'fixed_distance_cap': awareness.max_distance,
            'path_status': metadata['path_status'],
            'roll': metadata['roll'],
            'observer_aware_of_target': encounter.is_aware(observer.id, observed.id),
            'target_aware_of_observer': encounter.is_aware(observed.id, observer.id),
        },
        'practice': {'spot_awards_experience': False,
                     'observer_spot_experience': observer.get_skill_experience('spot'),
                     'target_owned_spot_practice_records': len(target_record.practice_history)},
        'objective_vs_observation': {
            'objective_positions_are_native_being_state': True,
            'spot_changed_objective_reality': False,
            'observer_specific_awareness': encounter.is_aware(observer.id, observed.id),
            'reverse_awareness': encounter.is_aware(observed.id, observer.id),
            'objective_fact_uses': len(inspection.objective_use),
        },
        'rng_state_version': rng.state[0],
    }


if __name__ == '__main__':
    print(json.dumps(demo_data(), indent=2, sort_keys=True))
