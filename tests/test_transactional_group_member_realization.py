"""Atomic opt-in publication of one already-counted adult Group member."""
from copy import deepcopy
import json
from pathlib import Path
import random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src")]

from activities import RunAction
import atomic_publication
from atomic_publication import PHASES, PublicationFailure, RNGCursor
from encounter import Encounter
from field_observation import BeliefLedger
from group_member_realization import (
    AdultMemberGeometryDescriptor,
    AdultMemberRequest,
    GroupMemberCandidateRejected,
    StaleGroupMemberCandidate,
    _construct_detached_adult,
    prepare_adult_member_candidate,
    validate_adult_member_candidate,
)
from library import Library
from spatial.state import CartesianPosition
from statistical_group import StatisticalGroup
from universe import Universe


CONFIG = json.loads((ROOT / "examples" / "nomadic_group.json").read_text())
REALIZATION_PHASES = (
    "adult_registry",
    "adult_group_member",
    "adult_group_realized",
    "adult_group_motion",
    "adult_encounter_participant",
    "rng",
    "consistency",
    "mark_committed",
)


def make_context(suffix="main", *, include_actor=True, transactional=True):
    config = deepcopy(CONFIG)
    config["group_id"] = "counted-member-group"
    config["motion"].update(position=[0, 0, 0], velocity=[0, 0, 0],
                            acceleration=[0, 0, 0])
    world = Universe("Transactional adult realization",
                     library=Library(config_dir=str(ROOT / "src" / "config")))
    observer_id = world.make_being("Human", f"Observer {suffix}")
    observer = world.get_object_by_id(observer_id)
    observer.set_position(CartesianPosition(0, -20, 0))
    group = StatisticalGroup("Counted group", config["group_id"], config,
                             config["seed"])
    counts = group.counts()
    if suffix == "main":
        assert counts["humans"] == 11
    world.add_object(group)
    encounter = Encounter(world, 15, 0, initiated=True,
                          id=f"adult-realization-{suffix}")
    world.add_event(encounter)
    encounter.add_being(observer.id)
    encounter.add_object(group.id)
    ledger = BeliefLedger(observer.id)
    rng = RNGCursor(random.Random(4510).getstate())
    if transactional:
        encounter.enable_transactional_progression(quiescent=True, rng_owner=rng)
    actor_run = None
    if include_actor:
        actor_run = RunAction(world, observer.id, 0, 1, 1, experience=3,
                              id=f"observer-run-{suffix}")
        encounter.schedule_choice((actor_run,))
    return world, encounter, group, observer, ledger, rng, counts, actor_run


def request_for(group, boundary=1, *, household=0, index=0, geometry=None):
    return AdultMemberRequest(group.id, household, "adults", index, boundary,
                              geometry=geometry)


def full_boundary(encounter, rng, boundary, *, velocities=None, realization=None):
    return encounter.prepare_interval_candidate(
        boundary, velocities=velocities, rng_owner=rng,
        adult_member_candidate=realization)


def member_state(world, encounter, group, rng, member_id, action=None):
    return {
        "registry_container": id(world.object_registry.object_instances),
        "registry": tuple((key, id(value))
                          for key, value in world.object_registry.object_instances.items()),
        "members_container": id(group._members),
        "members": tuple(group._members.items()),
        "realized_container": id(group._realized_beings),
        "realized": tuple((key, id(value)) for key, value in group._realized_beings.items()),
        "motion_container": id(group._motion_attached_native_ids),
        "motion": frozenset(group._motion_attached_native_ids),
        "participants_container": id(encounter.being_list),
        "participants": tuple(encounter.being_list),
        "awareness_container": id(encounter.awareness),
        "awareness": tuple((key, frozenset(value))
                           for key, value in encounter.awareness.items()),
        "events_container": id(world.event_history),
        "events": tuple((key, id(value)) for key, value in world.event_history.items()),
        "queues": (id(encounter.pending_action_list), tuple(encounter.pending_action_list),
                   id(encounter.finished_action_list), tuple(encounter.finished_action_list),
                   id(encounter.cancelled_action_list), tuple(encounter.cancelled_action_list)),
        "choice_book": (tuple((key, id(value)) for key, value
                              in encounter._choice_book._choices.items()),
                        tuple(encounter._choice_book._states.items()),
                        tuple(encounter._choice_book._registered.items()),
                        tuple(encounter._choice_book._reservations),
                        world._schedule_revision),
        "committed_receipt_keys": frozenset(
            key for key, row in atomic_publication._COMMITTED_RECEIPTS.items()
            if row[1]() is encounter),
        "interval_history": tuple(getattr(encounter, "_atomic_interval_history", ())),
        "counts": group.counts(),
        "reality": (group._composition_reality.revision,
                    group._composition_reality.view().all_facts()),
        "time": (encounter.time, encounter.last_processed_boundary,
                 encounter.active_boundary, encounter.boundary_fault),
        "rng": rng.state,
        "member_present": world.get_object_by_id(member_id) is not None,
        "member_geometry": (None if world.get_object_by_id(member_id) is None
                            else world.get_object_by_id(member_id).geometry),
        "action_resolution": None if action is None else action.resolution,
    }


class TestTransactionalAdultRealization(unittest.TestCase):
    def test_publication_then_next_boundary_action_and_count_conservation(self):
        world, encounter, group, observer, ledger, rng, counts, observer_run = make_context()
        request = request_for(group)
        realization = prepare_adult_member_candidate(encounter, group, request)
        rng_before = rng.state
        views_before = (ledger.evidence, ledger.belief_history,
                       tuple(ledger._interpretations.items()))
        initial_registry = world.object_registry.object_instances
        initial_members = group._members
        initial_realized = group._realized_beings
        initial_motion = group._motion_attached_native_ids
        initial_participants = encounter.being_list

        first = full_boundary(encounter, rng, 1, velocities={observer.id: (2, 0, 0)},
                              realization=realization)
        self.assertNotIn(realization.member_id, first.pre_action_snapshot.entities)
        self.assertNotIn(realization.member_id, first.pre_action_snapshot.actions)
        self.assertNotIn(realization.member_id,
                         (observer_run.actor_id, observer_run.target_id,
                          observer_run.instrument_id))
        step_one = encounter.step(1, velocities={observer.id: (2, 0, 0)},
                                  adult_member_candidate=realization)
        receipt = encounter._atomic_interval_history[-1]

        being = world.get_object_by_id(realization.member_id)
        slot = (request.household, "adults", request.index)
        self.assertIsNotNone(being)
        self.assertIs(group._realized_beings[realization.member_id], being)
        self.assertEqual(group._members[slot].id, realization.member_id)
        self.assertEqual(group._members[slot].offset, realization.member_offset)
        self.assertIn(realization.member_id, group._motion_attached_native_ids)
        self.assertEqual(encounter.being_list.count(realization.member_id), 1)
        self.assertEqual(group.counts(), counts)
        self.assertIsNone(being.geometry)
        self.assertEqual(encounter.time, 1)
        self.assertEqual(receipt.action_ids, (observer_run.id,))
        self.assertEqual(step_one.completed_action_ids, (observer_run.id,))
        self.assertNotIn(realization.member_id, receipt.action_ids)
        self.assertNotIn(realization.member_id, receipt.effect_ids)
        self.assertNotIn(realization.member_id, world.event_history)
        self.assertIs(world.object_registry.object_instances, initial_registry)
        self.assertIs(group._members, initial_members)
        self.assertIs(group._realized_beings, initial_realized)
        self.assertIs(group._motion_attached_native_ids, initial_motion)
        self.assertIs(encounter.being_list, initial_participants)
        self.assertEqual((ledger.evidence, ledger.belief_history,
                          tuple(ledger._interpretations.items())), views_before)
        self.assertEqual(rng.state, rng_before)

        # Registration is accepted only after boundary 1. The next snapshot can
        # include the Being; its one-second RunAction then completes at boundary 2.
        run = RunAction(world, being.id, 1, 1, 1, experience=7,
                        id="realized-adult-run")
        encounter.schedule_choice((run,))
        second = full_boundary(encounter, rng, 2,
                               velocities={being.id: (2, 0, 0)})
        self.assertIn(being.id, second.pre_action_snapshot.entities)
        self.assertIn(run.id, second.pre_action_snapshot.actions)
        encounter.step(1, velocities={being.id: (2, 0, 0)})
        later_receipt = encounter._atomic_interval_history[-1]
        self.assertIn(run.id, later_receipt.action_ids)
        self.assertEqual(run.resolution.outcome, "success")
        self.assertEqual(being.get_skill_experience("run"), 7)
        self.assertEqual(group.counts(), counts)
        self.assertEqual(rng.state, rng_before)
        with self.assertRaises(GroupMemberCandidateRejected):
            prepare_adult_member_candidate(encounter, group, request_for(group, 3))

    def test_detached_construction_has_no_registration_rng_or_uuid_side_effect(self):
        from unittest.mock import patch
        import identifiable

        world, encounter, group, observer, ledger, rng, counts, _ = make_context("detached")
        candidate = prepare_adult_member_candidate(encounter, group,
            request_for(group, 1))
        before = member_state(world, encounter, group, rng, candidate.member_id)
        read_before = __import__("interval_staging")._read_set(encounter)
        global_rng = random.getstate()
        with patch.object(identifiable.uuid, "uuid4",
                          side_effect=AssertionError("stable ID must not draw UUID")):
            being, member = _construct_detached_adult(candidate, encounter, group)
        self.assertEqual(being.id, candidate.member_id)
        self.assertEqual(being.get_position(), candidate.initial_position)
        self.assertEqual(member.id, candidate.member_id)
        self.assertIsNone(world.get_object_by_id(candidate.member_id))
        self.assertEqual(member_state(world, encounter, group, rng, candidate.member_id), before)
        self.assertEqual(__import__("interval_staging")._read_set(encounter), read_before)
        self.assertEqual(random.getstate(), global_rng)
        self.assertEqual(rng.state, before["rng"])
        self.assertEqual(group.counts(), counts)
        self.assertFalse(ledger.evidence)

    def test_explicit_sphere_descriptor_is_immutable_pure_and_constructed_detached(self):
        from dataclasses import FrozenInstanceError
        from spatial import Sphere

        world, encounter, group, observer, ledger, rng, counts, _ = make_context("geometry")
        descriptor = AdultMemberGeometryDescriptor(sphere_radius=0.5)
        request = request_for(group, 1, geometry=descriptor)
        before = member_state(world, encounter, group, rng,
                              f"{group.id}/0/adults/0")
        read_before = __import__("interval_staging")._read_set(encounter)
        global_rng_before = random.getstate()
        candidate = prepare_adult_member_candidate(encounter, group, request)
        self.assertEqual(candidate.geometry, descriptor)
        self.assertIs(candidate.request.geometry, descriptor)
        self.assertIsNone(world.get_object_by_id(candidate.member_id))
        self.assertEqual(member_state(world, encounter, group, rng,
                                      candidate.member_id), before)
        self.assertEqual(__import__("interval_staging")._read_set(encounter), read_before)
        self.assertEqual(random.getstate(), global_rng_before)
        self.assertEqual(group.counts(), counts)
        with self.assertRaises(FrozenInstanceError):
            descriptor.sphere_radius = 3.0
        with self.assertRaises(FrozenInstanceError):
            candidate.geometry = None

        being, member = _construct_detached_adult(candidate, encounter, group)
        self.assertEqual(being.geometry, Sphere(0.5))
        self.assertEqual(member.id, candidate.member_id)
        self.assertIsNone(world.get_object_by_id(candidate.member_id))
        self.assertEqual(member_state(world, encounter, group, rng,
                                      candidate.member_id), before)

    def test_invalid_and_altered_geometry_descriptors_fail_closed(self):
        from dataclasses import replace
        from spatial import Sphere

        for invalid in (0, -0.1, float("nan"), float("inf"), True, "0.5"):
            with self.subTest(invalid=invalid):
                with self.assertRaises((TypeError, ValueError)):
                    AdultMemberGeometryDescriptor(invalid)

        world, encounter, group, observer, ledger, rng, counts, _ = make_context(
            "geometry-invalid")
        with self.assertRaises(GroupMemberCandidateRejected):
            prepare_adult_member_candidate(encounter, group,
                request_for(group, 1, geometry=Sphere(0.5)))
        candidate = prepare_adult_member_candidate(encounter, group,
            request_for(group, 1, geometry=AdultMemberGeometryDescriptor(0.5)))
        forged = replace(candidate, geometry=AdultMemberGeometryDescriptor(0.75))
        with self.assertRaises(StaleGroupMemberCandidate):
            validate_adult_member_candidate(encounter, group, forged)
        forged_request = replace(candidate.request,
                                 geometry=AdultMemberGeometryDescriptor(0.75))
        forged_both = replace(candidate, request=forged_request,
                              geometry=forged_request.geometry)
        with self.assertRaises(StaleGroupMemberCandidate):
            validate_adult_member_candidate(encounter, group, forged_both)
        group.set_position(CartesianPosition(3, 0, 0))
        with self.assertRaises(StaleGroupMemberCandidate):
            validate_adult_member_candidate(encounter, group, candidate)
        self.assertIsNone(world.get_object_by_id(candidate.member_id))
        self.assertEqual(group.counts(), counts)

    def test_stale_foreign_and_invalid_candidates_refuse_before_publication(self):
        world, encounter, group, observer, ledger, rng, counts, _ = make_context("stale")
        candidate = prepare_adult_member_candidate(encounter, group,
            request_for(group, 1))
        altered = type(candidate)(**{**candidate.__dict__, "display_name": "forged"})
        before = member_state(world, encounter, group, rng, candidate.member_id)
        with self.assertRaises(StaleGroupMemberCandidate):
            full_boundary(encounter, rng, 1, realization=altered)
        self.assertEqual(member_state(world, encounter, group, rng, candidate.member_id), before)

        other_world, other_encounter, other_group, *_ = make_context("foreign", include_actor=False)
        other_candidate = prepare_adult_member_candidate(other_encounter, other_group,
            request_for(other_group, 1))
        with self.assertRaises((StaleGroupMemberCandidate, ValueError)):
            full_boundary(encounter, rng, 1, realization=other_candidate)

        with self.assertRaises((GroupMemberCandidateRejected, ValueError)):
            prepare_adult_member_candidate(encounter, group,
                request_for(group, 2))
        group.set_position(CartesianPosition(3, 0, 0))
        with self.assertRaises(StaleGroupMemberCandidate):
            validate_adult_member_candidate(encounter, group, candidate)
        self.assertEqual(group.counts(), counts)

    def test_changed_registry_definition_and_duplicate_operation_fail_closed(self):
        from object import ObjectDefinition, ObjectInstance

        world, encounter, group, observer, ledger, rng, _, _ = make_context("revision")
        candidate = prepare_adult_member_candidate(encounter, group,
            request_for(group, 1))
        unrelated = ObjectInstance(ObjectDefinition("unrelated", 0, 0, 0, 0, 0, 0, 0),
                                   name="Unrelated", id="unrelated-after-capture")
        world.add_object(unrelated)
        before = member_state(world, encounter, group, rng, candidate.member_id)
        with self.assertRaises(ValueError):
            encounter.step(1, adult_member_candidate=candidate)
        self.assertEqual(member_state(world, encounter, group, rng, candidate.member_id), before)
        self.assertIsNone(encounter.boundary_fault)

        world, encounter, group, observer, ledger, rng, _, _ = make_context("definition")
        candidate = prepare_adult_member_candidate(encounter, group,
            request_for(group, 1))
        definition = world.get_being_definition("Human")
        old_hp = definition.hit_points
        definition.hit_points = old_hp + 1
        before = member_state(world, encounter, group, rng, candidate.member_id)
        with self.assertRaises(ValueError):
            encounter.step(1, adult_member_candidate=candidate)
        self.assertEqual(member_state(world, encounter, group, rng, candidate.member_id), before)
        self.assertIsNone(encounter.boundary_fault)
        definition.hit_points = old_hp

        world, encounter, group, observer, ledger, rng, _, _ = make_context("duplicate")
        candidate = prepare_adult_member_candidate(encounter, group,
            request_for(group, 1))
        before = member_state(world, encounter, group, rng, candidate.member_id)
        with self.assertRaises(ValueError):
            encounter.step(1, adult_member_candidate=(candidate, candidate))
        self.assertEqual(member_state(world, encounter, group, rng, candidate.member_id), before)
        self.assertIsNone(encounter.boundary_fault)

    def test_legacy_encounter_refuses_realization_without_fallback(self):
        world, encounter, group, observer, ledger, rng, _, _ = make_context(
            "legacy", transactional=False)
        before = member_state(world, encounter, group, rng,
                              f"{group.id}/0/adults/0")
        with self.assertRaises(GroupMemberCandidateRejected):
            prepare_adult_member_candidate(encounter, group, request_for(group, 1))
        # Even a candidate from a supported transactional peer cannot route
        # this operation through legacy Encounter.step().
        other_world, other_encounter, other_group, *_ = make_context(
            "legacy-peer", include_actor=False)
        foreign = prepare_adult_member_candidate(other_encounter, other_group,
            request_for(other_group, 1))
        with self.assertRaises(ValueError):
            encounter.step(1, adult_member_candidate=foreign)
        self.assertEqual(member_state(world, encounter, group, rng,
                                      foreign.member_id), before)

    def test_slot_cache_and_registry_collisions_refuse(self):
        from object import ObjectDefinition, ObjectInstance
        from statistical_group import GroupMember

        world, encounter, group, observer, ledger, rng, _, _ = make_context("collision")
        slot = (0, "adults", 0)
        member_id = f"{group.id}/0/adults/0"
        world.add_object(ObjectInstance(ObjectDefinition("collision", 0, 0, 0, 0, 0, 0, 0),
                                        name="Collision", id=member_id))
        with self.assertRaisesRegex(GroupMemberCandidateRejected, "collides"):
            prepare_adult_member_candidate(encounter, group, request_for(group, 1))
        world.object_registry.object_instances.pop(member_id)
        group._members[slot] = GroupMember(member_id, 0, "adults", 0, (1.0, 2.0, 0.0))
        with self.assertRaisesRegex(GroupMemberCandidateRejected, "cached GroupMember"):
            prepare_adult_member_candidate(encounter, group, request_for(group, 1))

    def test_fault_after_each_realization_write_and_consistency_rolls_back_then_retries(self):
        self.assertTrue(set(REALIZATION_PHASES).issubset(PHASES))
        for phase in REALIZATION_PHASES:
            with self.subTest(phase=phase):
                world, encounter, group, observer, ledger, rng, counts, action = make_context(
                    f"fault-{phase}")
                candidate = prepare_adult_member_candidate(encounter, group,
                    request_for(group, 1,
                        geometry=AdultMemberGeometryDescriptor(sphere_radius=0.5)))
                interval = full_boundary(encounter, rng, 1,
                    velocities={observer.id: (2, 0, 0)}, realization=candidate)
                self.assertNotIn(candidate.member_id, interval.pre_action_snapshot.entities)
                before = member_state(world, encounter, group, rng, candidate.member_id, action)
                objects_ref = world.object_registry.object_instances
                members_ref = group._members
                realized_ref = group._realized_beings
                motion_ref = group._motion_attached_native_ids
                participants_ref = encounter.being_list
                events_ref = world.event_history
                publisher=atomic_publication.publish_interval_candidate
                def injected(enc, interval_candidate, **kwargs):
                    return publisher(enc, interval_candidate,
                                     _fail_after=phase, **kwargs)
                from unittest.mock import patch
                with patch.object(atomic_publication, "publish_interval_candidate", injected):
                    with self.assertRaises(PublicationFailure) as caught:
                        encounter.step(1, velocities={observer.id: (2, 0, 0)},
                                       adult_member_candidate=candidate)
                    self.assertEqual(caught.exception.phase, phase)
                    self.assertFalse(caught.exception.rollback_errors)
                    after = member_state(world, encounter, group, rng, candidate.member_id, action)
                    # Fault latch diagnostics are intentionally external to the
                    # restored checkpoint; the member and every transaction
                    # application write must be absent.
                    before["time"] = (*before["time"][:3], encounter.boundary_fault)
                    self.assertEqual(after, before)
                    self.assertIs(world.object_registry.object_instances, objects_ref)
                    self.assertIs(group._members, members_ref)
                    self.assertIs(group._realized_beings, realized_ref)
                    self.assertIs(group._motion_attached_native_ids, motion_ref)
                    self.assertIs(encounter.being_list, participants_ref)
                    self.assertIs(world.event_history, events_ref)
                    self.assertIsNone(action.resolution)
                    self.assertFalse(ledger.evidence)
                    encounter.recover_transactional_progression(
                        caught.exception.recovery_token)
                fresh = prepare_adult_member_candidate(encounter, group,
                    request_for(group, 1,
                        geometry=AdultMemberGeometryDescriptor(sphere_radius=0.5)))
                encounter.step(1, velocities={observer.id: (2, 0, 0)},
                               adult_member_candidate=fresh)
                published = world.get_object_by_id(candidate.member_id)
                self.assertIs(published, group._realized_beings[candidate.member_id])
                self.assertEqual(published.geometry.radius, 0.5)
                self.assertEqual(group.counts(), counts)


if __name__ == "__main__":
    unittest.main()
