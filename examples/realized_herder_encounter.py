"""One statistical group member becomes a persistent Being inside an Encounter.

Run from repository root: python examples/realized_herder_encounter.py
"""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from activities import RunAction
from encounter import Encounter
from library import Library
from spatial.state import CartesianPosition
from statistical_group import StatisticalGroup
from universe import Universe


def run_scenario():
    configuration = json.loads((ROOT / "examples" / "nomadic_group.json").read_text())
    world = Universe("Group-to-Being realization", library=Library(config_dir=str(ROOT / "src" / "config")))
    group = StatisticalGroup(configuration["group_name"], configuration["group_id"],
                             configuration, configuration["seed"])
    world.add_object(group)
    counts_before = group.counts()
    scout_id = world.make_being("Human", "Approaching scout")
    scout = world.get_object_by_id(scout_id)
    scout.set_position(CartesianPosition(0, -100, 0))

    herder = group.realize_being(world, 0, "adults", 0, name="Herder")
    member = group.member(0, "adults", 0)
    encounter = Encounter(world, difficulty_class=10, start_time=0)
    encounter.add_being(scout_id)
    encounter.add_being(herder.id)
    encounter.add_object(group.id)
    encounter.perceive_within(scout_id, 1000)
    encounter.decide_to_act(scout_id, group.id, "approach nomadic party")

    action = RunAction(world, herder.id, start_time=0, duration=1,
                       minimum_distance=2, experience=250)
    encounter.schedule_action(action)
    result = encounter.step(1, velocities={herder.id: (0, 3, 0)})
    # Repeat realization should preserve the same mutable Being and experience.
    herder_again = group.realize_being(world, 0, "adults", 0, name="Herder")
    return dict(world=world, group=group, counts_before=counts_before,
                herder=herder, herder_again=herder_again, scout=scout,
                member=member, encounter=encounter, action=action, step=result)


if __name__ == "__main__":
    result = run_scenario()
    group = result["group"]
    herder = result["herder"]
    print("Group composition:", result["counts_before"])
    print("Identity:", herder.id)
    print("Registered as Being:", result["world"].get_object_by_id(herder.id) is herder)
    print("Repeat realization returns same Being:", herder is result["herder_again"])
    print("Action result:", result["action"].resolution.outcome)
    print("Run skill:", herder.get_skill_level("run"))
    print("Run experience:", herder.get_skill_experience("run"))
    print("Realized full Beings / total group members:",
          group.realized_being_count, "/",
          sum(result["counts_before"][category] for category in group.CATEGORIES))
    print("Aggregate composition unchanged:", group.counts() == result["counts_before"])
