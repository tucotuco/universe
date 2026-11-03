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

from activities import RunAction, SpotAction
from atomic_publication import RNGCursor
from encounter import Encounter
from group_member_realization import AdultMemberRequest, prepare_adult_member_candidate
from group_member_realization import AdultMemberGeometryDescriptor
from library import Library
from reproduction_being_bridge import materialize_reproductive_offspring
from reproduction_group import ReproductionGroupProposal, prepare_reproduction_group
from spatial import CartesianPosition
from spatial import Sphere, VisualOcclusion
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
    # The aggregate's explicit transparent envelope prevents the geometric
    # path tracer from treating the unmodeled Group shape as unknown opacity.
    group.set_geometry(Sphere(max(group.footprint_radius, 0.5)))
    group.set_visual_occlusion(VisualOcclusion(0.0))
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
    genealogy_before_encounter = world.reproduction_group_snapshot()
    world.add_object(group)

    observer_id = world.make_being("Human", "World observer")
    observer = world.get_object_by_id(observer_id)
    observer.set_position(CartesianPosition(12, 14, 0))
    observer.set_geometry(Sphere(0.5))
    spotter_id = world.make_being("Human", "Independent Spotter")
    spotter = world.get_object_by_id(spotter_id)
    # This authored location puts the observer near C's deterministic Group
    # slot placement. It is not knowledge acquired from genealogy or counts.
    spotter.set_position(CartesianPosition(12, 44, 0))
    spotter.set_geometry(Sphere(0.5))
    encounter = Encounter(world, 15, 0, initiated=True,
                          id="genealogy-population-place-encounter")
    world.add_event(encounter)
    encounter.add_being(observer.id)
    encounter.add_being(spotter.id)
    encounter.add_object(group.id)
    # The seeded native RNG supplies a reproducible Spot check (18 against
    # the Being's default DC 15); the Action does not carry an authored roll.
    rng = RNGCursor(random.Random(5302).getstate())
    encounter.enable_transactional_progression(quiescent=True, rng_owner=rng)
    encounter.schedule_choice((RunAction(world, observer.id, 0, 1, 1,
                                         experience=2,
                                         id="world-observer-run"),))

    request = AdultMemberRequest(
        group.id, 0, "adults", 0, 1, name="C",
        reproductive_person_id=child_id,
        reproduction_request_key="bind-C-to-counted-member",
        geometry=AdultMemberGeometryDescriptor(sphere_radius=0.5),
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

    # The second Being submits a genuine, target-directed native Spot through
    # the same transactional scheduler and publisher. Its target is supplied
    # by this developer-authored scenario; this does not implement category-
    # directed discovery of an unknown individual.
    awareness_before_spot = {
        observer.id: tuple(encounter.aware_beings(observer.id)),
        spotter.id: tuple(encounter.aware_beings(spotter.id)),
    }
    if any(child_id in known for known in awareness_before_spot.values()):
        raise AssertionError("realization or genealogy exposed C before Spot")
    personal_history_before_spot = spotter.personal_history
    spot = SpotAction(world, spotter.id, child_id, encounter.time,
                      id="spot-counted-genealogy-person")
    encounter.schedule_choice((spot,))
    if (spot.start_time, spot.end_time) != (1, 7):
        raise AssertionError("deliberate Spot must span the six seconds 1 through 7")
    encounter.step(5)
    if (encounter.time != 6 or spot.id not in encounter.pending_action_list
            or tuple(encounter.aware_beings(spotter.id)) != awareness_before_spot[spotter.id]):
        raise AssertionError("Spot changed observer state before its resolution boundary")
    encounter.step(1)
    spot_record = encounter.inspect_committed(7).action(spot.id)
    effects = tuple(row.effect for row in spot_record.effects)
    if spot_record.facts.outcome != "success":
        raise AssertionError(f"seeded native Spot failed: {spot_record.facts.outcome}")
    metadata = dict(spot_record.facts.metadata)
    if (metadata.get("roll"), metadata.get("discovery_dc"), metadata.get("effective_dc")) != (18, 15, 15):
        raise AssertionError("Spot did not use the expected seeded check and target DC")
    if (tuple(encounter.aware_beings(spotter.id)) != (child_id,)
            or tuple(encounter.aware_beings(observer.id)) != awareness_before_spot[observer.id]):
        raise AssertionError("Spot Awareness was not isolated to its observing Being")
    effect_names = {type(effect).__name__ for effect in effects}
    if sum(type(effect).__name__ == "AwarenessEffect" for effect in effects) != 1:
        raise AssertionError("successful Being Spot must publish one Awareness effect")
    if effect_names & {"ObservationEffect", "BeliefAcquisitionEffect", "PracticeEffect"}:
        raise AssertionError("Being Spot must not create evidence, Belief, or skill practice")
    if spotter.personal_history is not personal_history_before_spot:
        raise AssertionError("Spot unexpectedly changed personal history")
    if spotter.get_skill_experience("spot") != 0:
        raise AssertionError("revision-60 Spot must not award Spot experience")
    if (group.counts() != counts_before or being.get_position() != candidate.initial_position
            or world.reproduction_group_snapshot() != genealogy_before_encounter):
        raise AssertionError("perception changed population, place, or genealogy")

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
        "spot": {
            "action_id": spot.id,
            "start": spot.start_time,
            "end": spot.end_time,
            "resolved_boundary": spot_record.resolved_boundary,
            "outcome": spot_record.facts.outcome,
            "roll": metadata["roll"],
            "target_discovery_dc": metadata["discovery_dc"],
            "effective_dc": metadata["effective_dc"],
            "effects": [type(effect).__name__ for effect in effects],
            "spot_experience": spotter.get_skill_experience("spot"),
        },
        "observer_knowledge": {
            "before": {key: list(value) for key, value in awareness_before_spot.items()},
            "after": {
                observer.id: encounter.aware_beings(observer.id),
                spotter.id: encounter.aware_beings(spotter.id),
            },
            "group_count_evidence_created": False,
            "genealogy_exposed_by_spot": False,
        },
        "encounter_boundary_receipts": [row.boundary for row in encounter._atomic_interval_history],
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
