"""Nomadic-group experiment: uncertain reality, fallible evidence, belief, motion.

Run from the repository root: python examples/nomadic_group_experiment.py
No geography, terrain, true optics, Agent choices, or combat are simulated.
"""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from encounter import Encounter
from field_observation import BeliefLedger, FieldObserver
from library import Library
from spatial.state import CartesianPosition
from statistical_group import StatisticalGroup
from universe import Universe


def run_scenario(config=None):
    if config is None:
        config = json.loads((Path(__file__).with_name("nomadic_group.json")).read_text())

    world = Universe("Nomadic group experiment", library=Library(
        config_dir=str(ROOT / "src" / "config")))
    group = StatisticalGroup(config["group_name"], config["group_id"],
                             config, seed=config["seed"])
    world.add_object(group)
    alpha_id = world.make_being("Human", "Scout Alpha")
    beta_id = world.make_being("Human", "Scout Beta")
    alpha = world.get_object_by_id(alpha_id)
    beta = world.get_object_by_id(beta_id)
    alpha.set_position(CartesianPosition(0, -650, 0))
    beta.set_position(CartesianPosition(250, -275, 0))

    encounter = Encounter(world, difficulty_class=10, start_time=0)
    for scout_id in (alpha_id, beta_id):
        encounter.add_being(scout_id)
    encounter.add_object(group.id)
    observer = FieldObserver(**config["observation"])
    beliefs = {alpha_id: BeliefLedger(alpha_id), beta_id: BeliefLedger(beta_id)}

    # At t=0, composition is statistical and nobody has been materialized.
    initially_unrealized = (group._counts is None, group.materialized_count)
    first = observer.observe(encounter, alpha_id, group, "alpha-t0",
                             count_bias={"dogs": 2}, position_error=(12, -10, 0))
    assert first is not None
    beliefs[alpha_id].learn(first)
    assert encounter.decide_to_act(alpha_id, group.id, "continue observing") is not None

    # Propagate physical state (constant acceleration), alongside Encounter time.
    group.advance(100)
    encounter.step(duration=100)
    assert group.time == encounter.time

    # The same Scout observes again; a persistent classification bias can survive.
    second = observer.observe(encounter, alpha_id, group, "alpha-t100",
                              count_bias={"dogs": 3}, position_error=(4, -3, 0))
    third = observer.observe(encounter, beta_id, group, "beta-t100",
                             count_bias={"dogs": -1}, position_error=(-3, 2, 0))
    assert second is not None and third is not None
    beliefs[alpha_id].learn(second)
    beliefs[beta_id].learn(third)
    alpha_velocity_estimate = beliefs[alpha_id].estimated_velocity(group.id)
    alpha_prediction = beliefs[alpha_id].predict_position(group.id, 160)

    # Communication shares evidence, not reality; a discrepancy becomes a lead.
    shared_a = beliefs[alpha_id].share_from(beliefs[beta_id])
    shared_b = beliefs[beta_id].share_from(beliefs[alpha_id])
    targets = beliefs[alpha_id].discrepancies(group.id)

    # The group's actual acceleration and limits constrain its future position.
    reachable = group.reachable_at(time=160)
    counts = group.counts()
    one_household = group.household(0)
    first_category = next(k for k, value in one_household.items() if value > 0)
    member = group.member(0, first_category, 0)

    return {
        "world": world, "encounter": encounter, "group": group,
        "scouts": (alpha, beta), "beliefs": beliefs,
        "observations": (first, second, third),
        "initially_unrealized": initially_unrealized,
        "shared": (shared_a, shared_b), "conflicts": targets,
        "counts": counts, "selected_member": member,
        "selected_member_position": group.member_position(member),
        "estimated_velocity": alpha_velocity_estimate,
        "alpha_prediction": alpha_prediction,
        "reachable": reachable,
    }


if __name__ == "__main__":
    result = run_scenario()
    group = result["group"]
    print("Initially unresolved counts / members:", result["initially_unrealized"])
    print("True counts (realized without individual members):", result["counts"])
    for observation in result["observations"]:
        print(f"{observation.id}, t={observation.time:g}, {observation.mode}:",
              {key: report.interval for key, report in observation.reports.items()})
    print("Scout Alpha inferred velocity (m/s):", result["estimated_velocity"])
    print("Scout Alpha predicted center at t=160:", result["alpha_prediction"])
    print("Evidence shared (new unique observations):", result["shared"])
    print("Unresolved conflicting reports:", result["conflicts"])
    print("Members materialized:", group.materialized_count,
          "out of", result["counts"]["humans"] + result["counts"]["livestock"] + result["counts"]["dogs"])
    print("Selected member:", result["selected_member"].id)
    print("Conservative center reachability at t=160:", result["reachable"])
