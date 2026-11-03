"""One explicitly authored Person across genealogy, population, and place.

Run from the repository root with:
    python examples/individual_across_genealogy_population_place.py

The population assignment is an explicit scenario/world fact: C is authored
to be the pre-existing stable slot ``Group/0/adults/0``. Reproduction does not
infer that assignment. The existing transactional Encounter publisher creates
one native Being with that identity and publishes population and genealogy
binding together. It does not create observer knowledge.
"""
from copy import deepcopy
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from activities import RunAction
from atomic_publication import RNGCursor
from encounter import Encounter
from group_member_realization import AdultMemberRequest, prepare_adult_member_candidate
from library import Library
from reproduction_being_bridge import materialize_reproductive_offspring
from reproduction_group import ReproductionGroupProposal, prepare_reproduction_group
from spatial import CartesianPosition
from statistical_group import StatisticalGroup
from universe import Universe


def main():
    config = deepcopy(json.loads((ROOT / "examples" / "nomadic_group.json").read_text()))
    # The existing fixture's seed and Group identity yield its committed 11 humans.
    group_id = "counted-member-group"
    config["group_id"] = group_id
    config["motion"].update(position=[12, 18, 0], velocity=[0, 0, 0],
                            acceleration=[0, 0, 0])
    world = Universe("Genealogy-population-place demonstration", library=Library(
        config_dir=str(ROOT / "src" / "config")))
    group = StatisticalGroup("Counted population", group_id, config, config["seed"])
    group.set_position(CartesianPosition(12, 18, 0))
    counts_before = group.counts()
    materialized_before = group.materialized_count
    child_id = f"{group.id}/0/adults/0"
    population_before = group.aggregate_state()

    # This is an explicit independent cross-domain identity assertion. The
    # parentage record does not assert or infer residence/group membership.
    genealogy_candidate = prepare_reproduction_group(ReproductionGroupProposal(
        "family-C", ("Parent-A", "Parent-B"), (child_id,),
        "scenario-authored parentage and population-member identity for C",
    ))
    genealogy = world.publish_reproduction_group(
        genealogy_candidate, request_key="family-C-authored", expected_revision=0)
    world.add_object(group)

    observer_id = world.make_being("Human", "World observer")
    observer = world.get_object_by_id(observer_id)
    observer.set_position(CartesianPosition(12, 14, 0))
    encounter = Encounter(world, 15, 0, initiated=True,
                          id="genealogy-population-place-encounter")
    world.add_event(encounter)
    encounter.add_being(observer.id)
    encounter.add_object(group.id)
    rng = RNGCursor(random.Random(774).getstate())
    encounter.enable_transactional_progression(quiescent=True, rng_owner=rng)
    encounter.schedule_choice((RunAction(world, observer.id, 0, 1, 1,
                                         experience=2,
                                         id="world-observer-run"),))

    request = AdultMemberRequest(
        group.id, 0, "adults", 0, 1, name="C",
        reproductive_person_id=child_id,
        reproduction_request_key="bind-C-to-counted-member",
    )
    candidate = prepare_adult_member_candidate(encounter, group, request)
    if child_id in world.object_registry.object_instances:
        raise AssertionError("C existed as a native Object before publication")
    encounter.step(1, adult_member_candidate=candidate)

    being = world.get_object_by_id(child_id)
    if (being is None or being.id != child_id
            or group._realized_beings.get(child_id) is not being
            or world._reproduction_group_registry._native_beings_by_person_id.get(child_id) is not being):
        raise AssertionError("genealogy, Group, and native Being identities diverged")
    if group.counts() != counts_before or group.current_counts() != counts_before:
        raise AssertionError("realization changed the existing population count")
    if encounter.aware_beings(observer.id):
        raise AssertionError("world realization unexpectedly granted observer Awareness")

    # Retry through the existing native binding API; the exact key is a
    # read-only replay and returns the one already-published Being.
    replay = materialize_reproductive_offspring(
        world, child_id, being_definition=world.get_being_definition("Human"),
        name="C", request_key="bind-C-to-counted-member",
        expected_revision=world._reproduction_group_registry.revision)
    if replay is not being:
        raise AssertionError("identical binding retry did not return the published Being")
    from reproduction_being_bridge import ReproductionBeingBridgeError
    conflict_refused = False
    try:
        materialize_reproductive_offspring(
            world, child_id, being_definition=world.get_being_definition("Human"),
            name="C with conflicting authored name",
            request_key="bind-C-to-counted-member",
            expected_revision=world._reproduction_group_registry.revision)
    except ReproductionBeingBridgeError:
        conflict_refused = True
    if not conflict_refused:
        raise AssertionError("conflicting reuse of the binding request key was accepted")

    population_after = group.aggregate_state()
    receipt = encounter._atomic_interval_history[-1]
    output = {
        "individual": child_id,
        "identity_matches": {
            "reproductive_offspring": child_id in genealogy.offspring_ids,
            "counted_group_slot": child_id in group._realized_beings,
            "object_registry": world.get_object_by_id(child_id) is being,
            "reproduction_native_binding": world._reproduction_group_registry
                ._native_beings_by_person_id.get(child_id) is being,
            "encounter_participant": encounter.being_list.count(child_id) == 1,
        },
        "population": {
            "total_before": counts_before["humans"],
            "total_after": group.counts()["humans"],
            "adult_realized_before": population_before["categories"]["adults"]["realized"],
            "adult_unresolved_before": population_before["categories"]["adults"]["unresolved"],
            "adult_committed": population_after["categories"]["adults"]["committed"],
            "adult_realized": population_after["categories"]["adults"]["realized"],
            "adult_unresolved": population_after["categories"]["adults"]["unresolved"],
            "materialized_members_before": materialized_before,
            "materialized_members_after": group.materialized_count,
        },
        "place": {
            "group_position": group.get_position().as_tuple(),
            "being_position": being.get_position().as_tuple(),
            "native_spatial_state": type(being.spatial_state).__name__,
        },
        "idempotent_retry_returns_same_object": replay is being,
        "conflicting_retry_refused": conflict_refused,
        "automatic_awareness": encounter.aware_beings(observer.id),
        "encounter_boundary_receipt": receipt.boundary,
        "reproduction_revision_unchanged_by_binding": (
            world._reproduction_group_registry.revision == genealogy.revision),
    }
    if not all(output["identity_matches"].values()):
        raise AssertionError("identity conservation failed")
    if output["population"]["total_before"] != output["population"]["total_after"]:
        raise AssertionError("population was double-counted")
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
