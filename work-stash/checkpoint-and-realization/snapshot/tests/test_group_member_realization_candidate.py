"""Purity and stale-state refusal for inactive adult Group realization candidates."""
from copy import deepcopy
import json
from pathlib import Path
import random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "examples")]

from atomic_publication import RNGCursor
from encounter import Encounter
from field_observation import BeliefLedger
from group_member_realization import (
    AdultMemberRequest,
    GroupMemberCandidateRejected,
    StaleGroupMemberCandidate,
    prepare_adult_member_candidate,
    validate_adult_member_candidate,
)
from library import Library
from statistical_group import StatisticalGroup
from universe import Universe


CONFIG = json.loads((ROOT / "examples" / "nomadic_group.json").read_text())


def make_context(*, group_id="candidate-group", encounter_id="candidate-encounter"):
    config = deepcopy(CONFIG)
    config["group_id"] = group_id
    world = Universe("Group candidate test",
                     library=Library(config_dir=str(ROOT / "src" / "config")))
    group = StatisticalGroup("Candidate Group", group_id, config, config["seed"])
    counts = group.counts()  # This increment accepts already committed composition only.
    world.add_object(group)
    observer_id = world.make_being("Human", "Observer")
    observer = world.get_object_by_id(observer_id)
    encounter = Encounter(world, 15, 0, initiated=True, id=encounter_id)
    world.add_event(encounter)
    encounter.add_being(observer_id)
    encounter.add_object(group.id)
    rng = RNGCursor(random.Random(1904).getstate())
    encounter.enable_transactional_progression(quiescent=True, rng_owner=rng)
    ledger = BeliefLedger(observer_id)
    return world, encounter, group, observer, ledger, rng, counts


def state_snapshot(world, encounter, group, observer, ledger, rng):
    from interval_staging import _read_set
    return {
        "members": tuple(group._members.items()),
        "realized": tuple((key, id(value)) for key, value in group._realized_beings.items()),
        "motion": frozenset(group._motion_attached_native_ids),
        "counts": group.counts(),
        "composition": (group._composition_reality.revision,
                        group._composition_reality.view().all_facts()),
        "registry_container": id(world.object_registry.object_instances),
        "registry": tuple((key, id(value)) for key, value
                           in world.object_registry.object_instances.items()),
        "being_list_container": id(encounter.being_list),
        "being_list": tuple(encounter.being_list),
        "object_list_container": id(encounter.non_being_object_list),
        "object_list": tuple(encounter.non_being_object_list),
        "schedule": _read_set(encounter),
        "time": (encounter.time, encounter.last_processed_boundary,
                 encounter.active_boundary, encounter._coordinator_time,
                 encounter._interval_start),
        "rng": rng.state,
        "observer": (ledger.evidence, ledger.belief_history,
                     tuple(ledger._interpretations.items()),
                     tuple(ledger._known_waypoints.items()),
                     tuple(ledger._inquiry_history)),
        "module_rng": random.getstate(),
        "observer_identity": observer.id,
    }


class TestAdultMemberCandidate(unittest.TestCase):
    def test_candidate_is_detached_repeatable_and_pure(self):
        world, encounter, group, observer, ledger, rng, counts = make_context()
        request = AdultMemberRequest(group.id, 0, "adults", 0, 1)
        before = state_snapshot(world, encounter, group, observer, ledger, rng)

        candidate = prepare_adult_member_candidate(encounter, group, request)
        repeated = prepare_adult_member_candidate(encounter, group, request)

        self.assertEqual(candidate, repeated)
        self.assertEqual(candidate.member_id, f"{group.id}/0/adults/0")
        self.assertEqual(candidate.formation_counts, tuple(sorted(counts.items())))
        self.assertEqual(candidate.first_eligible_boundary, 2)
        self.assertIsNone(world.get_object_by_id(candidate.member_id))
        self.assertEqual(group._members, {})
        self.assertEqual(group._realized_beings, {})
        self.assertEqual(group._motion_attached_native_ids, set())
        self.assertNotIn(candidate.member_id, encounter.being_list)
        self.assertEqual(state_snapshot(world, encounter, group, observer, ledger, rng), before)
        self.assertIs(validate_adult_member_candidate(encounter, group, candidate), candidate)
        with self.assertRaises((AttributeError, TypeError)):
            candidate.member_id = "changed"

    def test_invalid_and_foreign_requests_refuse_without_side_effects(self):
        world, encounter, group, observer, ledger, rng, _ = make_context()
        before = state_snapshot(world, encounter, group, observer, ledger, rng)
        invalid = (
            AdultMemberRequest(group.id, 0, "dogs", 0, 1),
            AdultMemberRequest(group.id, 0, "adults", 10_000, 1),
        )
        for request in invalid:
            with self.subTest(request=request):
                with self.assertRaises(GroupMemberCandidateRejected):
                    prepare_adult_member_candidate(encounter, group, request)
                self.assertEqual(state_snapshot(world, encounter, group, observer, ledger, rng), before)

        other_world, other_encounter, other_group, other_observer, other_ledger, other_rng, _ = make_context(
            group_id="other-candidate-group", encounter_id="other-candidate-encounter")
        foreign_before = state_snapshot(other_world, other_encounter, other_group,
                                        other_observer, other_ledger, other_rng)
        with self.assertRaises(GroupMemberCandidateRejected):
            prepare_adult_member_candidate(encounter, other_group,
                AdultMemberRequest(other_group.id, 0, "adults", 0, 1))
        self.assertEqual(state_snapshot(other_world, other_encounter, other_group,
                                        other_observer, other_ledger, other_rng), foreign_before)

    def test_candidate_preserves_native_adult_formation_skill_assignment(self):
        config = deepcopy(CONFIG)
        config["group_id"] = "formation-candidate-group"
        config["formation_traits"] = {
            "adults": {"trained": {"count": 1, "initial_skills": {"run": 2}}}
        }
        world = Universe("Formation candidate test",
                         library=Library(config_dir=str(ROOT / "src" / "config")))
        group = StatisticalGroup("Formation Group", config["group_id"], config,
                                 config["seed"])
        group.counts()
        world.add_object(group)
        observer_id = world.make_being("Human", "Observer")
        encounter = Encounter(world, 15, 0, initiated=True, id="formation-encounter")
        world.add_event(encounter)
        encounter.add_being(observer_id)
        encounter.add_object(group.id)
        encounter.enable_transactional_progression(
            quiescent=True, rng_owner=RNGCursor(random.Random(1905).getstate()))
        selected = next(iter(group._adult_formation_assignments("trained")))
        _, household, _, index = selected.rsplit("/", 3)
        candidate = prepare_adult_member_candidate(encounter, group,
            AdultMemberRequest(group.id, int(household), "adults", int(index), 1))
        self.assertEqual(candidate.initial_skills, (("run", 2),))
        self.assertEqual(group._members, {})
        self.assertEqual(group._realized_beings, {})

    def test_identity_collision_and_realized_slot_refuse_without_candidate_mutation(self):
        from object import ObjectDefinition, ObjectInstance

        world, encounter, group, observer, ledger, rng, _ = make_context()
        member_id = f"{group.id}/0/adults/0"
        collision = ObjectInstance(ObjectDefinition("collision", 0, 0, 0, 0, 0, 0, 0),
                                   name="Collision", id=member_id)
        world.add_object(collision)
        before = state_snapshot(world, encounter, group, observer, ledger, rng)
        with self.assertRaisesRegex(GroupMemberCandidateRejected, "collides"):
            prepare_adult_member_candidate(encounter, group,
                AdultMemberRequest(group.id, 0, "adults", 0, 1))
        self.assertEqual(state_snapshot(world, encounter, group, observer, ledger, rng), before)

        world, encounter, group, observer, ledger, rng, _ = make_context(
            group_id="realized-group", encounter_id="realized-encounter")
        group.realize_being(world, 0, "adults", 0)
        before = state_snapshot(world, encounter, group, observer, ledger, rng)
        with self.assertRaisesRegex(GroupMemberCandidateRejected, "already realized"):
            prepare_adult_member_candidate(encounter, group,
                AdultMemberRequest(group.id, 0, "adults", 0, 1))
        self.assertEqual(state_snapshot(world, encounter, group, observer, ledger, rng), before)

    def test_stale_read_set_and_wrong_publication_boundary_refuse(self):
        world, encounter, group, observer, ledger, rng, _ = make_context()
        candidate = prepare_adult_member_candidate(encounter, group,
            AdultMemberRequest(group.id, 0, "adults", 0, 1))
        # A changed participant list invalidates the exact captured read set.
        encounter.being_list.append("external-change")
        before = state_snapshot(world, encounter, group, observer, ledger, rng)
        with self.assertRaises(StaleGroupMemberCandidate):
            validate_adult_member_candidate(encounter, group, candidate)
        self.assertEqual(state_snapshot(world, encounter, group, observer, ledger, rng), before)

        world, encounter, group, observer, ledger, rng, _ = make_context(
            group_id="boundary-group", encounter_id="boundary-encounter")
        before = state_snapshot(world, encounter, group, observer, ledger, rng)
        with self.assertRaisesRegex(GroupMemberCandidateRejected, "stale"):
            prepare_adult_member_candidate(encounter, group,
                AdultMemberRequest(group.id, 0, "adults", 0, 2))
        self.assertEqual(state_snapshot(world, encounter, group, observer, ledger, rng), before)


if __name__ == "__main__":
    unittest.main()
