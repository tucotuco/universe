"""Native Spot evidence of an Object's committed airborne state and location.

Run from the repository root with:
    PYTHONDONTWRITEBYTECODE=1 python examples/native_throw_spot.py

The printed World/Encounter inspection is explicitly GM ground truth. Evidence
is separately read from each Spotter's own ObjectObservationLedger.
"""
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / 'src', ROOT / 'examples'):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from activities import SpotAction
from being import BeingInstance
from native_throw_concurrent_run import build_concurrent_scene
from object_observation import ObjectObservationLedger
from spatial import CartesianPosition, Sphere, VisualOcclusion
from throwing import project_drag_free_trajectory, release_velocity_yd_s


SPOTTER_ID = 'throw-demo/spotter'
SECOND_OBSERVER_ID = 'throw-demo/second-observer'
SPOTTER_ACTION_ID = 'throw-demo/spotter-object-spot'
SECOND_SPOT_ACTION_ID = 'throw-demo/second-observer-object-spot'
SPOTTER_POSITION_M = (0.0, -20.0, 0.0)
SECOND_OBSERVER_POSITION_M = (0.0, -30.0, 0.0)


def build_spot_scene(seed=5):
    world, encounter, thrower, runner, projectile, rng, throw, run = build_concurrent_scene(seed)
    # Explicitly authored fixture geometry and default Entity discovery DC make
    # the existing geometric Spot gate testable. Dimensions are not inferred
    # from the Object definition or Being stature.
    runner.set_geometry(Sphere(0.25))
    projectile.set_geometry(Sphere(0.10))
    projectile.set_visual_occlusion(VisualOcclusion(0.0))
    projectile.current.discovery_dc = 15

    spotter = BeingInstance(world.library.being_dictionary.get_object_definition('Human'),
                            'Spotter', id=SPOTTER_ID)
    spotter.set_position(CartesianPosition(*SPOTTER_POSITION_M))
    spotter.set_geometry(Sphere(0.25))
    second = BeingInstance(world.library.being_dictionary.get_object_definition('Human'),
                           'Second Observer', id=SECOND_OBSERVER_ID)
    second.set_position(CartesianPosition(*SECOND_OBSERVER_POSITION_M))
    second.set_geometry(Sphere(0.25))
    world.add_object(spotter)
    world.add_object(second)
    encounter.add_being(spotter.id)
    encounter.add_being(second.id)

    spotter_evidence = ObjectObservationLedger(spotter.id)
    second_evidence = ObjectObservationLedger(second.id)
    spot = SpotAction(world, spotter.id, projectile.id, 0, object_ledger=spotter_evidence,
                      id=SPOTTER_ACTION_ID)
    second_spot = SpotAction(world, second.id, projectile.id, 0, object_ledger=second_evidence,
                             id=SECOND_SPOT_ACTION_ID)
    # Seed 5 yields ordered native rolls 20 and 9. The first passes the target's
    # explicit DC 15; the second fails. These are ordinary single Spot checks.
    encounter.schedule_choice((spot,))
    encounter.schedule_choice((second_spot,))
    return {
        'world': world, 'encounter': encounter, 'thrower': thrower,
        'runner': runner, 'projectile': projectile, 'rng': rng,
        'throw': throw, 'run': run, 'spotter': spotter, 'second': second,
        'spot': spot, 'second_spot': second_spot,
        'spotter_evidence': spotter_evidence, 'second_evidence': second_evidence,
    }


def run_native_throw_spot(seed=5):
    scene = build_spot_scene(seed)
    enc, rng = scene['encounter'], scene['rng']
    initial_rng = rng.state
    enc.step(4)
    boundary4 = enc.inspect_committed(4)
    assert scene['spotter_evidence'].observations == ()
    assert not enc.is_aware(scene['spotter'].id, scene['projectile'].id)
    enc.step(1, velocities={scene['runner'].id: (1.25, 0.0, 0.0)})
    boundary5 = enc.inspect_committed(5)
    assert boundary5.action(scene['run'].id).facts.outcome == 'success'
    assert scene['spotter_evidence'].observations == ()

    # Staging proves the evidence proposal reads the candidate's common
    # post-movement/pre-action boundary-6 snapshot, without publishing it.
    candidate = enc.prepare_interval_candidate(6, rng_owner=rng)
    frozen_projectile = candidate.pre_action_snapshot.entity(scene['projectile'].id)
    assert frozen_projectile.position == candidate.projectile_updates[0].state.position
    proposal_rows = candidate.supported_candidate.boundary.effects.values()
    proposed_evidence = [row.effect.observation for row in proposal_rows
                         if row.effect.__class__.__name__ == 'ObjectObservationEffect']
    assert len(proposed_evidence) == 1
    assert proposed_evidence[0].position == frozen_projectile.position
    assert proposed_evidence[0].projectile_status == 'in_flight'
    assert scene['spotter_evidence'].observations == ()
    assert rng.state == initial_rng

    enc.step(1)
    boundary6 = enc.inspect_committed(6)
    evidence = scene['spotter_evidence'].last_observation(scene['projectile'].id)
    assert evidence is not None and evidence.boundary == 6
    assert evidence.position == boundary6.target(scene['projectile'].id).position
    assert evidence.projectile_status == boundary6.target(scene['projectile'].id).projectile_state.status == 'in_flight'
    assert scene['spot'].resolution.outcome == 'success'
    assert scene['second_spot'].resolution.outcome == 'failure'
    assert enc.is_aware(scene['spotter'].id, scene['projectile'].id)
    assert not enc.is_aware(scene['second'].id, scene['projectile'].id)
    assert not enc.is_aware(scene['runner'].id, scene['projectile'].id)
    assert scene['second_evidence'].observations == ()
    assert not scene['spotter'].get_skill_experience('spot')
    assert not scene['second'].get_skill_experience('spot')

    # Exactly two native 1d20 checks; Throw and Run do not consume RNG.
    expected_rng = random.Random(seed)
    rolls = (expected_rng.randint(1, 20), expected_rng.randint(1, 20))
    assert rolls == (20, 9)
    assert rng.state == expected_rng.getstate()
    receipt6 = enc._atomic_interval_history[-1]
    assert receipt6.boundary == 6
    assert receipt6.action_ids == (scene['spot'].id, scene['second_spot'].id)
    observed_rows = [row for row in boundary6.action(scene['spot'].id).effects
                     if row.effect.__class__.__name__ == 'ObjectObservationEffect']
    assert len(observed_rows) == 1 and observed_rows[0].effect.observation == evidence

    # This is a separate omniscient developer view of later objective Reality.
    enc.step(1)
    boundary7 = enc.inspect_committed(7)
    grounded = boundary7.target(scene['projectile'].id)
    assert grounded.projectile_state.status == 'landed'
    assert evidence.projectile_status == 'in_flight'
    assert evidence.position == boundary6.target(scene['projectile'].id).position
    return {**scene, 'initial_rng': initial_rng, 'rolls': rolls,
            'boundary4': boundary4, 'boundary5': boundary5,
            'boundary6': boundary6, 'boundary7': boundary7,
            'evidence': evidence}


def main():
    scene = run_native_throw_spot()
    print('U-THROW-006 — ordinary native Spot of an airborne Object')
    print('GM/developer ground truth is separated from each observer-owned evidence ledger.')
    for boundary in (4, 5, 6, 7):
        inspection = scene[f'boundary{boundary}']
        projectile = inspection.target(scene['projectile'].id)
        runner = inspection.target(scene['runner'].id)
        status = projectile.projectile_state.status
        print(f'GM boundary {boundary}: Object={projectile.position.as_tuple()} m; '
              f'state={status}; Runner={runner.position.as_tuple()} m; '
              f'receipt actions={inspection.timeline[-1].action_ids}.')
    evidence = scene['evidence']
    print(f"Spotter evidence: Object={evidence.object_id}; position={evidence.position.as_tuple()} m; "
          f"motion={evidence.projectile_status}; boundary/time={evidence.boundary}/{evidence.time}; "
          f"source Action={evidence.source_action_id}.")
    print(f"Spot outcomes: {scene['spot'].resolution.outcome} (roll {scene['rolls'][0]}) / "
          f"{scene['second_spot'].resolution.outcome} (roll {scene['rolls'][1]}). "
          f"Only Spotter is aware; no Spot XP; total native receipts="
          f"{len(scene['encounter']._atomic_interval_history)}.")


if __name__ == '__main__':
    main()
