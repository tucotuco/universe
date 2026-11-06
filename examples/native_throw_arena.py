"""U-THROW-003 blocker fixture and pure trajectory projection.

Run from the repository root:
    PYTHONDONTWRITEBYTECODE=1 python examples/native_throw_arena.py

The Encounter admission attempt is expected to refuse. The displayed flight is
only a pure calculation projection; no Action, release, receipt, or landing is
committed to the Encounter.
"""
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / 'src') not in sys.path:
    sys.path.insert(0, str(ROOT / 'src'))

from abilities import Abilities
from action import Action
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


def build_blocked_scene():
    world = Universe('U-THROW-003 blocker fixture',
                     library=Library(config_dir=str(ROOT / 'src/config')))
    definition = world.library.being_dictionary.get_object_definition('Human')
    definition.height = BODY_HEIGHT_IN
    definition.abilities.set_ability('STR', STRENGTH)
    actor = BeingInstance(definition, 'Thrower', id='throw-demo/thrower')
    actor.current.height = BODY_HEIGHT_IN
    actor.current.abilities.set_ability('STR', STRENGTH)
    actor.set_skill_level(world.library.skill_dictionary, 'throw', THROW_LEVEL)
    actor.set_position(CartesianPosition(0.0, 0.0, 0.9))
    actor.set_geometry(Sphere(0.25))
    world.add_object(actor)

    projectile = ObjectInstance(
        ObjectDefinition('stone', 1.0, 1.0, 1.0, PROJECTILE_WEIGHT_LB,
                         0.0, 0.0, 1.0),
        'One-pound stone', id='throw-demo/projectile',
        spatial_state=None,
    )
    projectile.set_position(CartesianPosition(0.0, 0.0, 0.9))
    actor.add_possession(projectile.id)
    world.add_object(projectile)

    encounter = Encounter(world, 15, 0, end_time=None,
                          initiated=True, name='Unobstructed throw fixture',
                          id='throw-demo/encounter')
    world.add_event(encounter)
    encounter.add_being(actor.id)
    encounter.add_object(projectile.id)
    rng = RNGCursor(random.Random(141).getstate())
    encounter.enable_transactional_progression(quiescent=True, rng_owner=rng)

    # The real native Action/Choice admission route is attempted. No Action or
    # Object state is registered or advanced when the closed adapter refuses it.
    action = Action(world, 0.0, None, 'throw', actor.id, None,
                    projectile.id, id='throw-demo/action')
    action.end_time = float(RELEASE_BOUNDARY)
    draft = encounter.propose_choice((action,))
    validation = encounter.validate_choice(draft)
    return world, encounter, actor, projectile, rng, action, validation


def build_projection():
    arm_inches = BODY_HEIGHT_IN * 15.0 / 37.0
    release_speed = release_velocity_yd_s(
        strength=STRENGTH,
        throw_skill_level=THROW_LEVEL,
        projectile_weight_lb=PROJECTILE_WEIGHT_LB,
        heavy_load_reference_lb=HEAVY_LOAD_REFERENCE_LB,
        height_inches=BODY_HEIGHT_IN,
    )
    release_height_m = BODY_HEIGHT_IN * 0.0254
    trajectory = project_drag_free_trajectory(
        release_velocity_yd_s=release_speed,
        release_position=CartesianPosition(0.0, 0.0, release_height_m),
        landing_elevation_m=0.0,
        elevation_degrees=ELEVATION_DEG,
        azimuth_degrees=AZIMUTH_DEG,
    )
    return arm_inches, release_height_m, release_speed, trajectory


def main():
    world, encounter, actor, projectile, rng, action, validation = build_blocked_scene()
    arm_inches, release_height_m, release_speed, trajectory = build_projection()
    print('U-THROW-003 — native Throw integration blocker fixture')
    print('Authored calculation inputs:')
    print(f'  actor={actor.id}; Strength={STRENGTH}; Throw level={THROW_LEVEL}')
    print(f'  actor height={BODY_HEIGHT_IN:.6f} in; reference arm={arm_inches:.9f} in')
    print(f'  Object={projectile.id}; weight={PROJECTILE_WEIGHT_LB:.6f} lb')
    print('  Strength 10 max throwable weight=50 lb; 1 lb is within the 4-second bracket (<=3.3 lb)')
    print('  host fixture seed=141 (no RNG draw occurs; no state transfer is claimed)')
    print(f'  proposed action start=0 s; expected release boundary={RELEASE_BOUNDARY}; azimuth={AZIMUTH_DEG}°, elevation={ELEVATION_DEG}°')
    print(f'  release height={release_height_m:.9f} m above authored flat landing plane z=0 m')
    print('Native transaction admission:')
    for diagnostic in validation.diagnostics:
        print(f'  refused [{diagnostic.code}]: {diagnostic.reason}')
    print(f'  accepted={validation.valid}; pending_actions={encounter.pending_action_list}; reservations={encounter.active_reservations}')
    print(f'  action_registered={world.get_event_by_id(action.id) is action}; receipts_for_this_encounter=0')
    print(f'  projectile_authoritative_position={projectile.get_position().as_tuple()} m (unchanged; no release)')
    print('Pure projected trajectory only (not committed native state):')
    print(f'  release speed={release_speed:.9f} yd/s = {release_speed * 0.9144:.9f} m/s')
    print(f'  flight time={trajectory.flight_time_s:.9f} s after hypothetical release')
    print(f'  landing position={trajectory.landing_position.as_tuple()} m')
    print(f'  horizontal range={trajectory.horizontal_range_yd:.9f} yd ({trajectory.horizontal_range_m:.9f} m)')
    for elapsed in (0.0, 1.0, 2.0, trajectory.flight_time_s):
        if elapsed > trajectory.flight_time_s:
            continue
        point = trajectory.position_at(elapsed)
        print(f'  projected t={elapsed:.9f} s after release: {point.as_tuple()} m')
    print('No Action completion, receipt, practice, committed flight frame, or landing is claimed.')


if __name__ == '__main__':
    main()
