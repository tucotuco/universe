"""Deterministic vertical slice: movement, occlusion, spotting, and learning.

Run from the repository root:

    python examples/integrated_encounter.py

All 3D coordinates are provisional encounter space in metres. They do not
represent terrain generated from a planetary world. Dice and XP are fixed to
make the causal sequence testable; they are not a general learning policy.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from activities import RunAction, SpotAction
from encounter import Encounter
from library import Library
from spatial import AxisAlignedBox, CartesianPosition, Sphere, VisualOcclusion
from universe import Universe


def run_scenario():
    """Run the same four-second scenario used by the integration tests.

    A scout has already noticed a companion and decides to search an area.
    An opaque wall initially hides a cache. The scout changes position,
    clearing the *geometric* sightline. A first skill check fails; the
    recorded practice raises spotting proficiency, so the same roll on the
    next attempt succeeds and produces directed awareness of the cache.
    """
    world = Universe("Integrated Encounter", library=Library(
        config_dir=str(ROOT / "src" / "config")))
    scout_id = world.make_being("Human", "Scout")
    companion_id = world.make_being("Human", "Companion")
    cache_id = world.make_object("Brick", "Cache")
    wall_id = world.make_object("Brick", "Opaque wall")

    scout = world.get_object_by_id(scout_id)
    companion = world.get_object_by_id(companion_id)
    cache = world.get_object_by_id(cache_id)
    wall = world.get_object_by_id(wall_id)

    scout.set_position(CartesianPosition(0, 0, 0))
    companion.set_position(CartesianPosition(0, -5, 0))
    companion.set_geometry(Sphere(.5))
    cache.set_position(CartesianPosition(10, 0, 0))
    cache.set_geometry(Sphere(.5))
    wall.set_position(CartesianPosition(5, 0, 0))
    wall.set_geometry(AxisAlignedBox(1, 2, 2))
    wall.set_visual_occlusion(VisualOcclusion(1))

    encounter = Encounter(world, difficulty_class=11, start_time=0)
    for being_id in (scout_id, companion_id):
        encounter.add_being(being_id)
    for object_id in (cache_id, wall_id):
        encounter.add_object(object_id)

    # Bootstrap awareness of a companion, not the concealed cache.
    encounter.mark_aware(scout_id, companion_id)
    initiation = encounter.decide_to_act(scout_id, companion_id, "search nearby")
    assert initiation is not None

    def snapshot(stage):
        return {
            "stage": stage,
            "time": encounter.time,
            "position": scout.get_position().as_tuple(),
            "sightline": encounter.line_of_sight(scout_id, cache_id).status,
            "cache_aware": encounter.is_aware(scout_id, cache_id),
            "run_level": scout.get_skill_level("run") or 0,
            "spot_level": scout.get_skill_level("spot") or 0,
            "run_xp": scout.get_skill_experience("run"),
            "spot_xp": scout.get_skill_experience("spot"),
        }

    states = [snapshot("initial")]

    run = RunAction(world, scout_id, encounter.time, duration=2,
                    minimum_distance=2.5, experience=250)
    encounter.schedule_action(run)
    obstructed_spot = SpotAction(world, scout_id, cache_id, encounter.time,
                                 duration=1, max_distance=15, die_roll=20,
                                 experience=0)
    encounter.schedule_action(obstructed_spot)

    # After one second, the wall still intersects the sightline, even
    # with a natural 20. Both actions are resolved on the Encounter timeline.
    steps = [encounter.step(duration=1, velocities={scout_id: (0, 1.5, 0)})]
    states.append(snapshot("still_occluded"))

    # Two seconds of motion clear the wall and complete the RunAction.
    steps.append(encounter.step(duration=1, velocities={scout_id: (0, 1.5, 0)}))
    states.append(snapshot("clear_path"))

    # Geometry is now clear, but the scout still does not know about the
    # cache until a SpotAction succeeds. Skill 0 + roll 10 < difficulty 11.
    first_spot = SpotAction(world, scout_id, cache_id, encounter.time,
                            duration=1, max_distance=15, die_roll=10,
                            experience=250)
    encounter.schedule_action(first_spot)
    steps.append(encounter.step(duration=1))
    states.append(snapshot("failed_check_learned"))

    # The *same* roll now succeeds after practice advanced the skill.
    second_spot = SpotAction(world, scout_id, cache_id, encounter.time,
                             duration=1, max_distance=15, die_roll=10,
                             experience=0)
    encounter.schedule_action(second_spot)
    steps.append(encounter.step(duration=1))
    states.append(snapshot("aware_of_cache"))

    return {
        "world": world,
        "encounter": encounter,
        "scout": scout,
        "companion": companion,
        "ids": {"scout": scout_id, "companion": companion_id,
                "cache": cache_id, "wall": wall_id},
        "actions": {"run": run, "obstructed_spot": obstructed_spot,
                    "first_spot": first_spot, "second_spot": second_spot},
        "steps": steps,
        "states": states,
    }


if __name__ == "__main__":
    scenario = run_scenario()
    for state in scenario["states"]:
        print("t={time:.0f} | {stage:<21} | sightline={sightline:<7} "
              "| aware={cache_aware} | run={run_level} ({run_xp} XP) "
              "| spot={spot_level} ({spot_xp} XP)".format(**state))
    print("Action outcomes:", {name: action.resolution.outcome
                               for name, action in scenario["actions"].items()})
    print("Personal skill history:", [
        (entry.skill_name, entry.time, entry.outcome, entry.experience,
         entry.level_before, entry.level_after)
        for entry in scenario["scout"].skill_use_history
    ])
