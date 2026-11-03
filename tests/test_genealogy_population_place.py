"""One explicitly authored Person across reproduction, population, and space."""
from copy import deepcopy
import json
from pathlib import Path
import random
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import atomic_publication
from activities import RunAction
from atomic_publication import PublicationFailure, RNGCursor
from activities import SpotAction
from encounter import Encounter
from group_member_realization import (
    AdultMemberGeometryDescriptor,
    AdultMemberRequest,
    GroupMemberCandidateRejected,
    StaleGroupMemberCandidate,
    prepare_adult_member_candidate,
    validate_adult_member_candidate,
)
from library import Library
from reproduction_being_bridge import (
    ReproductionBeingBridgeError,
    materialize_reproductive_offspring,
)
from reproduction_group import ReproductionGroupProposal, prepare_reproduction_group
from spatial.state import CartesianPosition
from spatial.geometry import Sphere
from spatial.occlusion import VisualOcclusion
from statistical_group import StatisticalGroup
from universe import Universe


CONFIG = json.loads((ROOT / "examples" / "nomadic_group.json").read_text())


def make_world(*, suffix="main", publish_genealogy=True, authored_offspring_id=None,
               independent_observer=False, rng_seed=774):
    config = deepcopy(CONFIG)
    # The adopted fixture seed and Group key produce a stable 11-person
    # committed composition (the key participates in the fixture's RNG).
    group_id = "counted-member-group"
    config["group_id"] = group_id
    config["motion"].update(position=[12, 18, 0], velocity=[0, 0, 0],
                            acceleration=[0, 0, 0])
    world = Universe("Genealogy, population, place", library=Library(
        config_dir=str(ROOT / "src" / "config")))
    group = StatisticalGroup("Population", group_id, config, config["seed"])
    group.set_position(CartesianPosition(12, 18, 0))
    if independent_observer:
        group.set_geometry(Sphere(max(group.footprint_radius, 0.5)))
        group.set_visual_occlusion(VisualOcclusion(0.0))
    counts = group.counts()
    member_id = f"{group.id}/0/adults/0"
    if publish_genealogy:
        candidate = prepare_reproduction_group(ReproductionGroupProposal(
            "family-C", ("Parent-A", "Parent-B"),
            (authored_offspring_id or member_id,),
            "explicit scenario genealogy for C",
        ))
        world.publish_reproduction_group(candidate, request_key="family-C-authored",
                                         expected_revision=0)
    world.add_object(group)
    observer_id = world.make_being("Human", "World observer")
    observer = world.get_object_by_id(observer_id)
    observer.set_position(CartesianPosition(12, 14, 0))
    observer_two = None
    if independent_observer:
        observer.set_geometry(Sphere(0.5))
        observer_two_id = world.make_being("Human", "Independent Spotter")
        observer_two = world.get_object_by_id(observer_two_id)
        # This is an explicit starting location in the scenario, not knowledge
        # obtained from parentage or aggregate population evidence.
        observer_two.set_position(CartesianPosition(12, 44, 0))
        observer_two.set_geometry(Sphere(0.5))
    encounter = Encounter(world, 15, 0, initiated=True,
                          id=f"genealogy-population-{suffix}")
    world.add_event(encounter)
    encounter.add_being(observer_id)
    if observer_two is not None:
        encounter.add_being(observer_two.id)
    encounter.add_object(group.id)
    rng = RNGCursor(random.Random(rng_seed).getstate())
    encounter.enable_transactional_progression(quiescent=True, rng_owner=rng)
    action = RunAction(world, observer_id, 0, 1, 1, experience=2,
                       id=f"observer-run-{suffix}")
    encounter.schedule_choice((action,))
    result = (world, encounter, group, observer, rng, counts, member_id)
    return (*result, observer_two) if independent_observer else result


def linked_request(group, member_id, *, key="bind-C", boundary=1, geometry=None):
    return AdultMemberRequest(
        group.id, 0, "adults", 0, boundary, name="C",
        reproductive_person_id=member_id, reproduction_request_key=key,
        geometry=geometry,
    )


def prepare_native_spot(*, suffix, seed, resolve=True):
    """Publish realization, then schedule an ordinary six-second native Spot."""
    world, encounter, group, observer, rng, counts, child_id, spotter = make_world(
        suffix=suffix, independent_observer=True, rng_seed=seed)
    candidate = prepare_adult_member_candidate(
        encounter, group, linked_request(group, child_id,
            geometry=AdultMemberGeometryDescriptor(sphere_radius=0.5)))
    genealogy_before = world.reproduction_group_snapshot()
    encounter.step(1, adult_member_candidate=candidate)
    being = world.get_object_by_id(child_id)
    spot = SpotAction(world, spotter.id, child_id, encounter.time,
                      id=f"population-linked-spot-{suffix}")
    encounter.schedule_choice((spot,))
    before = {
        "spotter": tuple(encounter.aware_beings(spotter.id)),
        "other_observer": tuple(encounter.aware_beings(observer.id)),
        "position": being.get_position(),
        "counts": group.counts(),
        "genealogy": world.reproduction_group_snapshot(),
        "rng": rng.state,
        "history": spotter.personal_history,
    }
    encounter.step(5)
    assert encounter.time == 6
    assert spot.id in encounter.pending_action_list
    assert tuple(encounter.aware_beings(spotter.id)) == before["spotter"]
    inspection = None
    if resolve:
        encounter.step(1)
        inspection = encounter.inspect_committed(7)
    return (world, encounter, group, observer, spotter, being, spot, inspection,
            before, counts, genealogy_before, rng)


class GenealogyPopulationPlaceTests(unittest.TestCase):
    def test_native_spot_discovers_linked_being_without_leaking_genealogy_or_counts(self):
        (world, encounter, group, observer, spotter, being, spot, inspection,
         before, counts, genealogy_before, _) = prepare_native_spot(
            suffix="spot-success", seed=5302)
        self.assertEqual(before["spotter"], ())
        self.assertEqual(before["other_observer"], ())
        self.assertEqual(encounter.time, 7)
        self.assertEqual((spot.start_time, spot.end_time), (1, 7))
        self.assertIn(spot.id, inspection.actions)
        record = inspection.action(spot.id)
        self.assertEqual(record.resolved_boundary, 7)
        self.assertEqual(record.facts.outcome, "success")
        metadata = dict(record.facts.metadata)
        self.assertEqual((metadata["roll"], metadata["discovery_dc"],
                          metadata["effective_dc"]), (18, 15, 15))
        self.assertEqual(tuple(encounter.aware_beings(spotter.id)), (being.id,))
        self.assertEqual(tuple(encounter.aware_beings(observer.id)), ())
        # Current Being Spot publishes Awareness only. It has no Group-count,
        # parentage, kinship, evidence, Belief, or Spot-practice consequence.
        effect_names = [type(row.effect).__name__ for row in record.effects]
        self.assertEqual(effect_names.count("AwarenessEffect"), 1)
        self.assertFalse(set(effect_names) & {
            "ObservationEffect", "BeliefAcquisitionEffect", "PracticeEffect"})
        self.assertNotIn(group.id, encounter.aware_beings(spotter.id))
        self.assertNotIn("Parent-A", encounter.aware_beings(spotter.id))
        self.assertNotIn("Parent-B", encounter.aware_beings(spotter.id))
        self.assertEqual(spotter.get_skill_experience("spot"), 0)
        self.assertIsNone(spotter.personal_history)
        self.assertIs(being, world.get_object_by_id(being.id))
        self.assertEqual(being.get_position(), before["position"])
        self.assertEqual(group.counts(), counts)
        self.assertEqual(group.realized_being_count, 1)
        self.assertEqual(world.reproduction_group_snapshot(), genealogy_before)
        self.assertEqual(inspection.timeline[-1].boundary, 7)
        self.assertIn(spot.id, inspection.timeline[-1].action_ids)

    def test_failed_native_spot_does_not_publish_awareness_or_skill_practice(self):
        (world, encounter, group, observer, spotter, being, spot, inspection,
         before, counts, genealogy_before, _) = prepare_native_spot(
            suffix="spot-failure", seed=5303)
        record = inspection.action(spot.id)
        self.assertEqual(record.facts.outcome, "failure")
        failure_effect_names = {type(row.effect).__name__ for row in record.effects}
        self.assertFalse(failure_effect_names & {
            "AwarenessEffect", "ObservationEffect", "BeliefAcquisitionEffect", "PracticeEffect"})
        self.assertEqual(tuple(encounter.aware_beings(spotter.id)), before["spotter"])
        self.assertEqual(tuple(encounter.aware_beings(observer.id)), before["other_observer"])
        self.assertEqual(spotter.get_skill_experience("spot"), 0)
        self.assertEqual(group.counts(), counts)
        self.assertEqual(world.reproduction_group_snapshot(), genealogy_before)
        self.assertEqual(being.get_position(), before["position"])

    def test_spot_publication_fault_rolls_back_awareness_rng_then_seeded_retry_commits(self):
        (world, encounter, group, observer, spotter, being, spot, _,
         before, counts, genealogy_before, rng) = prepare_native_spot(
            suffix="spot-rollback", seed=5302, resolve=False)
        rng_before = rng.state
        receipts_before = tuple(encounter._atomic_interval_history)
        publisher = atomic_publication.publish_interval_candidate

        def fail_after_observer_writes(owner, candidate, **kwargs):
            return publisher(owner, candidate, _fail_after="observers", **kwargs)

        with patch.object(atomic_publication, "publish_interval_candidate",
                          fail_after_observer_writes):
            with self.assertRaises(PublicationFailure) as caught:
                encounter.step(1)
        self.assertEqual(caught.exception.phase, "observers")
        self.assertFalse(caught.exception.rollback_errors)
        self.assertEqual(encounter.time, 6)
        self.assertEqual(rng.state, rng_before)
        self.assertEqual(tuple(encounter._atomic_interval_history), receipts_before)
        self.assertEqual(tuple(encounter.aware_beings(spotter.id)), before["spotter"])
        self.assertEqual(tuple(encounter.aware_beings(observer.id)), before["other_observer"])
        self.assertIn(spot.id, encounter.pending_action_list)

        encounter.recover_transactional_progression(caught.exception.recovery_token)
        encounter.step(1)
        record = encounter.inspect_committed(7).action(spot.id)
        self.assertEqual(record.facts.outcome, "success")
        self.assertEqual(dict(record.facts.metadata)["roll"], 18)
        self.assertEqual(tuple(encounter.aware_beings(spotter.id)), (being.id,))
        self.assertEqual(tuple(encounter.aware_beings(observer.id)), ())
        self.assertEqual(group.counts(), counts)
        self.assertEqual(world.reproduction_group_snapshot(), genealogy_before)

    def test_one_authored_identity_is_genealogy_counted_member_and_spatial_being(self):
        world, encounter, group, observer, rng, counts_before, child_id = make_world()
        reproduction = world._reproduction_group_registry
        genealogy_before = world.reproduction_group_snapshot()
        population_before = group.aggregate_state()
        rng_before = rng.state
        awareness_before = tuple(encounter.aware_beings(observer.id))
        observer_history_before = observer.personal_history
        self.assertEqual(counts_before["humans"], 11)
        self.assertEqual(group.materialized_count, 0)
        self.assertEqual(population_before["categories"]["adults"]["unresolved"],
                         counts_before["adults"])
        self.assertEqual(genealogy_before.known_parents(child_id), ("Parent-A", "Parent-B"))

        request = linked_request(group, child_id)
        candidate = prepare_adult_member_candidate(encounter, group, request)
        self.assertEqual(candidate.member_id, child_id)
        self.assertNotIn(child_id, world.object_registry.object_instances)
        encounter.step(1, adult_member_candidate=candidate)

        being = world.get_object_by_id(child_id)
        self.assertIsNotNone(being)
        self.assertEqual(being.id, child_id)
        self.assertIs(group._realized_beings[child_id], being)
        self.assertIs(reproduction._native_beings_by_person_id[child_id], being)
        self.assertEqual(encounter.being_list.count(child_id), 1)
        self.assertEqual(being.get_position(), candidate.initial_position)
        self.assertNotEqual(being.get_position(), group.get_position())
        self.assertEqual(group.counts(), counts_before)
        self.assertEqual(group.current_counts(), counts_before)
        self.assertEqual(group.materialized_count, 1)
        self.assertEqual(group.realized_being_count, 1)
        aggregate = group.aggregate_state()
        self.assertEqual(aggregate["categories"]["adults"]["committed"], counts_before["adults"])
        self.assertEqual(aggregate["categories"]["adults"]["realized"], 1)
        self.assertEqual(aggregate["categories"]["adults"]["unresolved"], counts_before["adults"] - 1)
        self.assertEqual(encounter.aware_beings(observer.id), [])
        self.assertEqual(tuple(encounter.aware_beings(observer.id)), awareness_before)
        self.assertNotIn(child_id, encounter.aware_beings(observer.id))
        self.assertIs(observer.personal_history, observer_history_before)
        self.assertEqual(rng.state, rng_before)
        self.assertEqual(world.reproduction_group_snapshot().known_parents(child_id),
                         genealogy_before.known_parents(child_id))
        self.assertEqual(world.reproduction_group_snapshot(), genealogy_before)
        self.assertEqual(reproduction._revision, genealogy_before.revision)
        reproduction._assert_consistent()

        # The bridge's exact retry is a no-write read in an Encounter world.
        retry_before = (
            id(world.object_registry.object_instances),
            tuple((key, id(value)) for key, value in world.object_registry.object_instances.items()),
            id(group._members), tuple(group._members.items()),
            id(group._realized_beings), tuple((key, id(value)) for key, value in group._realized_beings.items()),
            id(encounter.being_list), tuple(encounter.being_list),
            id(reproduction._native_beings_by_person_id),
            tuple((key, id(value)) for key, value in reproduction._native_beings_by_person_id.items()),
            id(reproduction._native_being_requests),
            tuple((key, id(value)) for key, value in reproduction._native_being_requests.items()),
            reproduction.revision, rng.state,
        )
        replay = materialize_reproductive_offspring(
            world, child_id, being_definition=world.get_being_definition("Human"),
            name="C", request_key="bind-C", expected_revision=reproduction.revision)
        self.assertIs(replay, being)
        self.assertEqual(retry_before, (
            id(world.object_registry.object_instances),
            tuple((key, id(value)) for key, value in world.object_registry.object_instances.items()),
            id(group._members), tuple(group._members.items()),
            id(group._realized_beings), tuple((key, id(value)) for key, value in group._realized_beings.items()),
            id(encounter.being_list), tuple(encounter.being_list),
            id(reproduction._native_beings_by_person_id),
            tuple((key, id(value)) for key, value in reproduction._native_beings_by_person_id.items()),
            id(reproduction._native_being_requests),
            tuple((key, id(value)) for key, value in reproduction._native_being_requests.items()),
            reproduction.revision, rng.state,
        ))
        self.assertEqual(group.counts(), counts_before)
        self.assertEqual(group.realized_being_count, 1)
        with self.assertRaisesRegex(ReproductionBeingBridgeError, "different Being properties"):
            materialize_reproductive_offspring(
                world, child_id, being_definition=world.get_being_definition("Human"),
                name="C altered", request_key="bind-C", expected_revision=reproduction.revision)

    def test_association_requires_explicit_matching_established_offspring_and_clean_slot(self):
        world, encounter, group, _, _, _, child_id = make_world(
            suffix="unestablished", authored_offspring_id="different-logical-child")
        with self.assertRaisesRegex(GroupMemberCandidateRejected, "not an established offspring"):
            prepare_adult_member_candidate(encounter, group, linked_request(group, child_id))
        with self.assertRaisesRegex(GroupMemberCandidateRejected, "must equal"):
            prepare_adult_member_candidate(encounter, group, AdultMemberRequest(
                group.id, 0, "adults", 0, 1, reproductive_person_id="some-other-person",
                reproduction_request_key="bind-conflict"))
        linked_world, linked_encounter, linked_group, _, _, _, _ = make_world(
            suffix="implicit")
        with self.assertRaisesRegex(GroupMemberCandidateRejected,
                                    "explicit matching offspring association"):
            prepare_adult_member_candidate(linked_encounter, linked_group,
                AdultMemberRequest(linked_group.id, 0, "adults", 0, 1, name="C"))
        with self.assertRaisesRegex(GroupMemberCandidateRejected, "supplied together"):
            prepare_adult_member_candidate(encounter, group, AdultMemberRequest(
                group.id, 0, "adults", 0, 1, reproductive_person_id=child_id))

        world, encounter, group, _, _, _, child_id = make_world(suffix="stale")
        stale = prepare_adult_member_candidate(encounter, group, linked_request(group, child_id))
        from dataclasses import replace
        with self.assertRaises(StaleGroupMemberCandidate):
            validate_adult_member_candidate(encounter, group,
                replace(stale, reproduction_registry_revision=stale.reproduction_registry_revision + 1))

    def test_candidate_refuses_preexisting_object_collision_without_mutation(self):
        from object import ObjectDefinition, ObjectInstance
        world, encounter, group, _, _, _, child_id = make_world()
        conflict = ObjectInstance(ObjectDefinition("marker", 0, 0, 0, 0, 0, 0, 0),
                                  "Conflict", id=child_id)
        world.add_object(conflict)
        with self.assertRaisesRegex(GroupMemberCandidateRejected, "collides"):
            prepare_adult_member_candidate(encounter, group, linked_request(group, child_id))
        self.assertIs(world.get_object_by_id(child_id), conflict)
        self.assertNotIn(child_id, group._realized_beings)
        self.assertNotIn(child_id, world._reproduction_group_registry._native_beings_by_person_id)

    def test_faults_after_both_reproduction_binding_writes_and_consistency_restore_everything(self):
        phases = ("adult_registry", "adult_group_member", "adult_group_realized",
                  "adult_group_motion", "adult_encounter_participant",
                  "adult_reproduction_binding", "adult_reproduction_request",
                  "rng", "consistency")
        publisher = atomic_publication.publish_interval_candidate
        for phase in phases:
            with self.subTest(phase=phase):
                world, encounter, group, observer, rng, counts, child_id = make_world(suffix=phase)
                reproduction = world._reproduction_group_registry
                candidate = prepare_adult_member_candidate(
                    encounter, group, linked_request(group, child_id))
                object_map = world.object_registry.object_instances
                group_members = group._members
                group_realized = group._realized_beings
                group_motion = group._motion_attached_native_ids
                participants = encounter.being_list
                bindings = reproduction._native_beings_by_person_id
                requests = reproduction._native_being_requests
                before_objects = dict(object_map)
                before_reproduction = (dict(bindings), dict(requests))
                before_rng = rng.state

                def inject(enc, interval, **kwargs):
                    return publisher(enc, interval, _fail_after=phase, **kwargs)

                with patch.object(atomic_publication, "publish_interval_candidate", inject):
                    with self.assertRaises(PublicationFailure) as caught:
                        encounter.step(1, adult_member_candidate=candidate)
                self.assertEqual(caught.exception.phase, phase)
                self.assertFalse(caught.exception.rollback_errors)
                self.assertIs(world.object_registry.object_instances, object_map)
                self.assertIs(group._members, group_members)
                self.assertIs(group._realized_beings, group_realized)
                self.assertIs(group._motion_attached_native_ids, group_motion)
                self.assertIs(encounter.being_list, participants)
                self.assertIs(reproduction._native_beings_by_person_id, bindings)
                self.assertIs(reproduction._native_being_requests, requests)
                self.assertEqual(dict(object_map), before_objects)
                self.assertEqual((dict(bindings), dict(requests)), before_reproduction)
                self.assertEqual(rng.state, before_rng)
                self.assertEqual(group.counts(), counts)
                self.assertEqual(encounter.aware_beings(observer.id), [])
                encounter.recover_transactional_progression(caught.exception.recovery_token)

                fresh = prepare_adult_member_candidate(encounter, group,
                    linked_request(group, child_id))
                encounter.step(1, adult_member_candidate=fresh)
                being = world.get_object_by_id(child_id)
                self.assertIs(reproduction._native_beings_by_person_id[child_id], being)
                self.assertEqual(group.counts(), counts)
                self.assertEqual(group.realized_being_count, 1)

    def test_unlinked_reproduction_checkpoint_refusal_remains_in_force(self):
        world, encounter, group, _, _, _, child_id = make_world()
        candidate = prepare_adult_member_candidate(encounter, group, linked_request(group, child_id))
        encounter.step(1, adult_member_candidate=candidate)
        with self.assertRaisesRegex(ValueError, "no-Encounter only"):
            from reproduction_checkpoint import encode_reproduction_checkpoint
            encode_reproduction_checkpoint(world)


if __name__ == "__main__":
    unittest.main()
