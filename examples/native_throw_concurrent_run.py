"""Native projectile flight concurrent with an independent native Run.

Run from the repository root with:
    PYTHONDONTWRITEBYTECODE=1 python examples/native_throw_concurrent_run.py

This is developer inspection of committed world state, not an Agent perception.
The Runner's placement and one-second velocity are authored scenario inputs.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / 'src') not in sys.path:
    sys.path.insert(0, str(ROOT / 'src'))
if str(ROOT / 'examples') not in sys.path:
    sys.path.insert(0, str(ROOT / 'examples'))

from activities import RunAction
from being import BeingInstance
from native_throw_arena import (
    BODY_HEIGHT_IN, RELEASE_BOUNDARY, build_native_scene, build_projection,
)
from spatial.state import CartesianPosition


RUNNER_ID = 'throw-demo/independent-runner'
RUN_ACTION_ID = 'throw-demo/independent-run'
RUNNER_INITIAL_POSITION_M = (100.0, 0.0, 0.0)
RUNNER_BOUNDARY_5_VELOCITY_M_S = (1.25, 0.0, 0.0)
RUN_MINIMUM_DISTANCE_M = 1.0
RUN_EXPERIENCE = 6


def build_concurrent_scene(seed=141):
    """Extend the native Throw fixture with one independently acting Being."""
    world, encounter, thrower, projectile, rng, throw = build_native_scene(seed)
    definition = world.library.being_dictionary.get_object_definition('Human')
    runner = BeingInstance(definition, 'Independent Runner', id=RUNNER_ID)
    runner.set_position(CartesianPosition(*RUNNER_INITIAL_POSITION_M))
    world.add_object(runner)
    encounter.add_being(runner.id)

    # The Run starts only after the Throw's t=4 release fence. Its displacement
    # is supplied as normal Encounter movement over [4, 5], never authored by
    # writing the Being's position directly.
    run = RunAction(world, runner.id, RELEASE_BOUNDARY, 1,
                    RUN_MINIMUM_DISTANCE_M, experience=RUN_EXPERIENCE,
                    id=RUN_ACTION_ID)
    encounter.schedule_choice((run,))
    return world, encounter, thrower, runner, projectile, rng, throw, run


def run_native_throw_with_concurrent_run(seed=141):
    world, encounter, thrower, runner, projectile, rng, throw, run = build_concurrent_scene(seed)
    rng_before = rng.state
    thrower_start = thrower.get_position()
    runner_start = runner.get_position()
    speed, projection = build_projection()
    rows = []

    # One normal chronological advance crosses boundaries 1–4. The Run's
    # accepted choice starts at 4, after the projectile's native release.
    encounter.step(4)
    rows.append((4, encounter.inspect_committed(4), encounter._atomic_interval_history[-1],
                 run.resolution))

    # A read-only inspection must not advance flight or publish a receipt.
    flight_before = projectile.__dict__['_projectile_flight']
    receipts_before = tuple(encounter._atomic_interval_history)
    inspected_4 = encounter.inspect_committed(4).target(projectile.id)
    assert projectile.__dict__['_projectile_flight'] is flight_before
    assert tuple(encounter._atomic_interval_history) == receipts_before
    assert rng.state == rng_before
    assert inspected_4.projectile_state.status == 'in_flight'

    # At boundary 5 the Run's ordinary movement and Action consequences commit
    # in the same transaction as the autonomous projectile update.
    encounter.step(1, velocities={runner.id: RUNNER_BOUNDARY_5_VELOCITY_M_S})
    rows.append((5, encounter.inspect_committed(5), encounter._atomic_interval_history[-1],
                 run.resolution))
    after_5 = encounter.inspect_committed(5)
    assert after_5.action(run.id).facts.outcome == 'success'
    assert after_5.target(runner.id).position == CartesianPosition(101.25, 0.0, 0.0)
    assert after_5.target(projectile.id).position == projection.position_at(1.0)

    for boundary in (6, 7):
        encounter.step(1)
        rows.append((boundary, encounter.inspect_committed(boundary),
                     encounter._atomic_interval_history[-1], run.resolution))

    final = encounter.inspect_committed(7)
    assert throw.resolution.outcome == 'released'
    assert runner.get_position() == CartesianPosition(101.25, 0.0, 0.0)
    assert thrower.get_position() == thrower_start
    assert runner_start == CartesianPosition(*RUNNER_INITIAL_POSITION_M)
    assert final.target(projectile.id).projectile_state.status == 'landed'
    assert final.target(projectile.id).projectile_state.impact_time == 6.337306187730018
    assert final.target(projectile.id).position == projection.landing_position
    assert rng.state == rng_before
    # The earlier detached view remains the actual t=4 state after later commits.
    assert inspected_4.position == CartesianPosition(0.0, 0.0, BODY_HEIGHT_IN * 0.0254)
    assert inspected_4.projectile_state.status == 'in_flight'
    return {
        'world': world, 'encounter': encounter, 'thrower': thrower,
        'runner': runner, 'projectile': projectile, 'rng': rng,
        'throw': throw, 'run': run, 'projection': projection, 'speed': speed,
        'rows': tuple(rows), 'inspected_4': inspected_4,
    }


def _effect_label(effect_identity):
    return (f'{effect_identity.source_action_id}/{effect_identity.channel}/'
            f'{effect_identity.slot}')


def main():
    scene = run_native_throw_with_concurrent_run()
    print('U-THROW-005 — native projectile flight with independent native Run')
    print('Developer inspection of committed state; not an Agent perception.')
    print('Authored: Thrower (69 in), 1 lb Object, Runner starts at (100, 0, 0) m;')
    print('Runner receives 1.25 m/s only over [4, 5]. No Object/Runner role overlap.')
    print(f'Analytical reference only: release={scene["speed"]:.9f} yd/s; '
          f'impact={4 + scene["projection"].flight_time_s:.12f} s; '
          f'landing range={scene["projection"].horizontal_range_yd:.9f} yd.')
    print('boundary | projectile position (m) | range (yd) | status | Runner position (m) | Action | receipt/effects')
    for boundary, inspection, receipt, run_result in scene['rows']:
        projectile_view = inspection.target(scene['projectile'].id)
        runner_view = inspection.target(scene['runner'].id)
        state = projectile_view.projectile_state
        position = projectile_view.position
        range_yd = (position.x ** 2 + position.y ** 2) ** 0.5 / 0.9144
        if boundary == 4:
            result = f'Throw {scene["throw"].resolution.outcome}'
        elif boundary == 5:
            result = f'Run {run_result.outcome}'
        else:
            result = 'no due Action'
        effects = ','.join(_effect_label(item) for item in receipt.effect_ids) or 'none'
        actions = ','.join(receipt.action_ids) or 'none'
        print(f'{boundary:>8} | {position.as_tuple()} | {range_yd:.6f} | '
              f'{state.status} | {runner_view.position.as_tuple()} | {result} | '
              f'receipt {receipt.boundary}; Actions={actions}; effects={effects}')

    t5_receipt = scene['rows'][1][2]
    t5_flight = scene['rows'][1][1].target(scene['projectile'].id).projectile_state
    print(f'Boundary 5 independent results: Run action={scene["run"].id}; '
          f'projectile source Action={t5_flight.source_action_id}; '
          f'projectile release effect={t5_flight.source_effect_identity}.')
    print(f'Boundary 5 receipt includes Run Action: {scene["run"].id in t5_receipt.action_ids}; '
          f'flight history remains projectile-owned; RNG unchanged.')


if __name__ == '__main__':
    main()
