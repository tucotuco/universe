"""U-THROW-004 native transactional Throw and committed flight chronology.

Run: PYTHONDONTWRITEBYTECODE=1 python examples/native_throw_arena.py
"""
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / 'src') not in sys.path:
    sys.path.insert(0, str(ROOT / 'src'))

from abilities import Abilities
from activities import ThrowAction
from atomic_publication import RNGCursor
from being import BeingInstance
from encounter import Encounter
from library import Library
from object import ObjectDefinition, ObjectInstance
from spatial.geometry import Sphere
from spatial.state import CartesianPosition
from throwing import project_drag_free_trajectory, release_velocity_yd_s
from universe import Universe


STRENGTH = 10
THROW_LEVEL = 1
PROJECTILE_WEIGHT_LB = 1.0
HEAVY_LOAD_REFERENCE_LB = 100.0
BODY_HEIGHT_IN = 69.0
AZIMUTH_DEG = 0.0
ELEVATION_DEG = 45.0
RELEASE_BOUNDARY = 4


def build_native_scene(seed=141):
    world = Universe('U-THROW-004 native fixture',
                     library=Library(config_dir=str(ROOT / 'src/config')))
    definition = world.library.being_dictionary.get_object_definition('Human')
    definition.height = BODY_HEIGHT_IN
    definition.abilities.set_ability('STR', STRENGTH)
    actor = BeingInstance(definition, 'Thrower', id='throw-demo/thrower')
    actor.current.height = BODY_HEIGHT_IN
    actor.current.abilities.set_ability('STR', STRENGTH)
    actor.set_skill_level(world.library.skill_dictionary, 'throw', THROW_LEVEL)
    actor.set_position(CartesianPosition(0.0, 0.0, 0.0))
    actor.set_geometry(Sphere(0.25))
    world.add_object(actor)
    projectile = ObjectInstance(
        ObjectDefinition('stone', 1.0, 1.0, 1.0, PROJECTILE_WEIGHT_LB,
                         0.0, 0.0, 1.0),
        'One-pound stone', id='throw-demo/projectile',
        spatial_state=None)
    # This is its authored pre-throw point, distinct from the t=4 body-height
    # handoff point that the native release publisher installs.
    projectile.set_position(CartesianPosition(0.0, 0.0, 0.0))
    actor.add_possession(projectile.id)
    world.add_object(projectile)
    encounter = Encounter(world, 15, 0, end_time=None, initiated=True,
                          name='Native Throw fixture', id='throw-demo/encounter')
    world.add_event(encounter)
    encounter.add_being(actor.id)
    encounter.add_object(projectile.id)
    rng = RNGCursor(random.Random(seed).getstate())
    encounter.enable_transactional_progression(quiescent=True, rng_owner=rng)
    action = ThrowAction(world, actor.id, projectile.id, 0.0,
        heavy_load_reference_lb=HEAVY_LOAD_REFERENCE_LB,
        elevation_degrees=ELEVATION_DEG, azimuth_degrees=AZIMUTH_DEG,
        landing_elevation_m=0.0, id='throw-demo/action')
    encounter.schedule_choice((action,))
    return world, encounter, actor, projectile, rng, action


def build_projection():
    speed = release_velocity_yd_s(strength=STRENGTH,
        throw_skill_level=THROW_LEVEL, projectile_weight_lb=PROJECTILE_WEIGHT_LB,
        heavy_load_reference_lb=HEAVY_LOAD_REFERENCE_LB, height_inches=BODY_HEIGHT_IN)
    release = CartesianPosition(0.0, 0.0, BODY_HEIGHT_IN * 0.0254)
    trajectory = project_drag_free_trajectory(release_velocity_yd_s=speed,
        release_position=release, landing_elevation_m=0.0,
        elevation_degrees=ELEVATION_DEG, azimuth_degrees=AZIMUTH_DEG)
    return speed, trajectory


def run_native_throw():
    world, encounter, actor, projectile, rng, action = build_native_scene()
    initial_rng = rng.state
    authored_position = projectile.get_position()
    rows = []
    for duration in (4, 1, 1, 1):
        encounter.step(duration)
        receipt = encounter.__dict__['_atomic_interval_history'][-1]
        flight = projectile.__dict__.get('_projectile_flight')
        rows.append((encounter.last_processed_boundary, action.resolution,
            projectile.get_position(), None if flight is None else flight.status,
            receipt, flight))
    assert authored_position == CartesianPosition(0.0, 0.0, 0.0)
    assert action.resolution.outcome == 'released'
    assert rng.state == initial_rng
    return world, encounter, actor, projectile, rng, action, rows


def main():
    speed, trajectory = build_projection()
    world, encounter, actor, projectile, rng, action, rows = run_native_throw()
    print('U-THROW-004 — native transactional Throw and authoritative flight')
    print('Source inputs: Strength 10; Throw 1; 69 in body height; one-pound Object;')
    print('4 s preparation; 45° elevation; 0° azimuth; flat z=0 landing plane; g=10 m/s².')
    print('The pure projection below is analytical reference; the table is committed native state.')
    print(f'Pure projection: release={speed:.9f} yd/s ({speed*0.9144:.9f} m/s); '
          f'airtime={trajectory.flight_time_s:.9f} s; impact t={4+trajectory.flight_time_s:.9f} s; '
          f'landing={trajectory.landing_position.as_tuple()} m ({trajectory.horizontal_range_yd:.9f} yd).')
    print('boundary | Action | committed position (m) | range (yd) | state | receipt/effect | fractional impact')
    for boundary, proposal, position, status, receipt, flight in rows:
        effect = ('release=' + str(flight.source_effect_identity)
                  if flight is not None else ','.join(str(identity) for identity in receipt.effect_ids) or 'none')
        action_status = proposal.outcome if boundary == RELEASE_BOUNDARY and proposal else 'no Action due'
        impact = '—' if flight is None else f'{flight.impact_time:.9f} s'
        horizontal_range = (position.x**2 + position.y**2) ** 0.5 / 0.9144
        print(f'{boundary:>8} | {action_status:>14} | '
              f'{position.as_tuple()} | {horizontal_range:.6f} | {status or "held":>9} | '
              f'{receipt.boundary}:{effect} | {impact}')
    print(f'Object identity preserved: {world.get_object_by_id(projectile.id) is projectile}; '
          f'released from actor possessions: {projectile.id not in actor.possessions}.')
    print(f'Native receipts: {len(encounter.__dict__["_atomic_interval_history"])}; '
          f'authoritative RNG unchanged (Throw has no roll/practice).')


if __name__ == '__main__':
    main()
