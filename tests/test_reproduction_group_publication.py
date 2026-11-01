"""World-owned, no-Encounter ReproductionGroup publication and rollback tests."""
from copy import deepcopy
import json
from pathlib import Path
import random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from being import BeingDefinition, BeingInstance
from encounter import Encounter
from field_observation import BeliefLedger
from library import Library
from reproduction_group import (
    InjectedReproductionGroupFailure,
    ReproductionGroupPublicationError,
    StaleReproductionGroupRevision,
    prepare_reproduction_group,
    ReproductionGroupProposal,
)
from statistical_group import StatisticalGroup
from universe import Universe

GROUP_CONFIG = json.loads((ROOT / "examples/nomadic_group.json").read_text())


def make_world(name="Reproduction tests"):
    return Universe(name, library=Library(config_dir=str(ROOT / "src/config")))


def candidate(group="RG-PQ", parents=("P", "Q"), children=("C1",), source="author:RG0"):
    return prepare_reproduction_group(
        ReproductionGroupProposal(group, parents, children, source)
    )


class ReproductionGroupPublicationTests(unittest.TestCase):
    def publish(self, world, value, key="request-1", revision=None, **kwargs):
        if revision is None:
            revision = world.reproduction_group_snapshot().revision
        return world.publish_reproduction_group(
            value, request_key=key, expected_revision=revision, **kwargs
        )

    def test_world_only_publication_commits_group_and_first_child_without_encounter(self):
        world = make_world()
        object_map = world.object_registry.object_instances
        event_map = world.event_history
        belief = BeliefLedger("observer-1")
        belief_before = (belief.evidence, belief.belief_history, belief.inquiry_history)
        rng_before = random.getstate()

        result = self.publish(world, candidate())
        snapshot = world.reproduction_group_snapshot()

        self.assertEqual(snapshot.revision, 1)
        self.assertEqual(len(snapshot.groups), 1)
        self.assertEqual(snapshot.groups[0].group_id, "RG-PQ")
        self.assertEqual(snapshot.groups[0].offspring_ids, ("C1",))
        self.assertEqual(snapshot.group_id_by_parent_set, (( ("P", "Q"), "RG-PQ"),))
        self.assertEqual(snapshot.group_id_by_offspring, (("C1", "RG-PQ"),))
        self.assertEqual(snapshot.parent_set_by_offspring, (("C1", ("P", "Q")),))
        self.assertFalse(snapshot.groups[0].offspring_enumeration_complete)
        self.assertIs(world.get_reproduction_group("RG-PQ"), snapshot.groups[0])
        self.assertEqual(result.request_key, "request-1")
        self.assertEqual(result.world_identity, id(world))
        self.assertEqual(event_map.keys(), {"0"})
        self.assertIs(world.event_history, event_map)
        self.assertIs(world.object_registry.object_instances, object_map)
        self.assertEqual(object_map, {})
        self.assertEqual(world._choice_books, [])
        self.assertEqual((belief.evidence, belief.belief_history, belief.inquiry_history), belief_before)
        self.assertEqual(random.getstate(), rng_before)

    def test_canonical_parent_set_uniqueness_and_shared_parent_across_groups(self):
        world = make_world()
        first = self.publish(world, candidate(parents=("P", "Q")), key="pq")
        before_conflict = world.reproduction_group_snapshot()
        with self.assertRaisesRegex(ReproductionGroupPublicationError, "exact parent set"):
            self.publish(world, candidate(group="RG-QP", parents=("Q", "P")), key="pq-again")
        self.assertEqual(world.reproduction_group_snapshot(), before_conflict)

        second = self.publish(
            world, candidate(group="RG-PR", parents=("P", "R"), children=("C2",)),
            key="pr", revision=1,
        )
        snapshot = world.reproduction_group_snapshot()
        self.assertEqual(first.parent_ids, ("P", "Q"))
        self.assertEqual(second.parent_ids, ("P", "R"))
        self.assertEqual(snapshot.revision, 2)
        self.assertEqual(snapshot.person_id_reservations, ("C1", "C2", "P", "Q", "R"))
        self.assertEqual(len(snapshot.groups), 2)

    def test_single_parent_group_and_child_parent_role_reuse(self):
        world = make_world()
        first = self.publish(world, candidate(group="RG-P", parents=("P",), children=("A1",)), key="asexual")
        second = self.publish(
            world,
            candidate(group="RG-A1-Q", parents=("A1", "Q"), children=("C2",)),
            key="later-parent", revision=1,
        )
        self.assertEqual(first.parent_ids, ("P",))
        self.assertIn("A1", second.parent_ids)
        self.assertEqual(world.reproduction_group_snapshot().revision, 2)

    def test_invalid_requests_and_conflicting_offspring_refuse_without_mutation(self):
        world = make_world()
        empty = world.reproduction_group_snapshot()
        for parents, children in (((), ("C",)), (("P",), ()), (("P", "P"), ("C",)), (("P",), ("C", "C"))):
            with self.subTest(parents=parents, children=children), self.assertRaises(ValueError):
                prepare_reproduction_group(ReproductionGroupProposal("RG", parents, children, "src"))
            self.assertEqual(world.reproduction_group_snapshot(), empty)

        self.publish(world, candidate(), key="original")
        committed = world.reproduction_group_snapshot()
        with self.assertRaisesRegex(ReproductionGroupPublicationError, "parent-set assignment"):
            self.publish(world, candidate(group="RG-PR", parents=("P", "R")), key="child-collision", revision=1)
        self.assertEqual(world.reproduction_group_snapshot(), committed)

    def test_group_and_person_id_collisions_refuse(self):
        world = make_world()
        self.publish(world, candidate(), key="first")
        committed = world.reproduction_group_snapshot()
        with self.assertRaisesRegex(ReproductionGroupPublicationError, "group ID is already reserved"):
            self.publish(world, candidate(group="RG-PQ", parents=("R",), children=("C2",)), key="same-id", revision=1)
        with self.assertRaisesRegex(ReproductionGroupPublicationError, "exact parent set"):
            self.publish(world, candidate(group="RG-PQ-2", parents=("Q", "P"), children=("C2",)), key="same-set", revision=1)
        with self.assertRaisesRegex(ReproductionGroupPublicationError, "Person ID collides with a reserved group ID"):
            self.publish(world, candidate(group="RG-2", parents=("RG-PQ",), children=("C2",)), key="namespace", revision=1)
        with self.assertRaisesRegex(ReproductionGroupPublicationError, "group ID collides with a reserved Person ID"):
            self.publish(world, candidate(group="P", parents=("R",), children=("C2",)), key="reserved-person", revision=1)
        self.assertEqual(world.reproduction_group_snapshot(), committed)

    def test_native_object_identity_collisions_refuse(self):
        world = make_world()
        definition = BeingDefinition("Human", 6, 170, 10, "2d6", "Neutral", 10, 1)
        being = BeingInstance(definition, "Native", id="P")
        world.add_object(being)
        object_map = world.object_registry.object_instances
        before = world.reproduction_group_snapshot()
        with self.assertRaisesRegex(ReproductionGroupPublicationError, "logical Person ID collides"):
            self.publish(world, candidate(), key="object-collision")
        self.assertEqual(world.reproduction_group_snapshot(), before)
        self.assertIs(world.get_object_by_id("P"), being)
        self.assertIs(world.object_registry.object_instances, object_map)
        with self.assertRaisesRegex(ReproductionGroupPublicationError, "group ID collides"):
            self.publish(world, candidate(group="P", parents=("R",), children=("C2",)), key="group-object-collision")
        self.assertEqual(world.reproduction_group_snapshot(), before)

    def test_idempotency_replays_without_revision_or_history_change_and_rejects_key_reuse(self):
        world = make_world()
        value = candidate()
        result = self.publish(world, value, key="stable-request")
        committed = world.reproduction_group_snapshot()
        replay = self.publish(world, value, key="stable-request", revision=0)
        self.assertIs(replay, result)
        self.assertEqual(world.reproduction_group_snapshot(), committed)
        with self.assertRaisesRegex(ReproductionGroupPublicationError, "different normalized content"):
            self.publish(world, candidate(group="RG-PR", parents=("P", "R")), key="stable-request", revision=1)
        self.assertEqual(world.reproduction_group_snapshot(), committed)

    def test_stale_registry_revision_refuses_before_writes(self):
        world = make_world()
        self.publish(world, candidate(), key="current")
        before = world.reproduction_group_snapshot()
        with self.assertRaises(StaleReproductionGroupRevision):
            self.publish(world, candidate(group="RG-PR", parents=("P", "R")), key="stale", revision=0)
        self.assertEqual(world.reproduction_group_snapshot(), before)

    def test_every_write_phase_and_post_consistency_fault_roll_back_in_place_then_retry(self):
        phases = (
            "group", "parent_set_index", "offspring_indexes", "person_reservations",
            "group_reservation", "idempotency", "revision", "consistency",
        )
        for phase in phases:
            with self.subTest(phase=phase):
                world = make_world()
                registry = world._reproduction_group_registry
                aliases = (
                    registry._groups_by_id,
                    registry._group_id_by_parent_set,
                    registry._group_id_by_offspring,
                    registry._parent_set_by_offspring,
                    registry._person_id_reservations,
                    registry._group_id_reservations,
                    registry._requests,
                )
                object_map = world.object_registry.object_instances
                event_map = world.event_history
                before = world.reproduction_group_snapshot()
                with self.assertRaises(InjectedReproductionGroupFailure):
                    self.publish(world, candidate(), key="retry", revision=0, _fail_after=phase)
                self.assertEqual(world.reproduction_group_snapshot(), before)
                self.assertEqual(world.object_registry.object_instances, {})
                self.assertIs(world.object_registry.object_instances, object_map)
                self.assertIs(world.event_history, event_map)
                self.assertEqual(world.event_history.keys(), {"0"})
                for current, original in zip((
                    registry._groups_by_id,
                    registry._group_id_by_parent_set,
                    registry._group_id_by_offspring,
                    registry._parent_set_by_offspring,
                    registry._person_id_reservations,
                    registry._group_id_reservations,
                    registry._requests,
                ), aliases):
                    self.assertIs(current, original)
                result = self.publish(world, candidate(), key="retry", revision=0)
                self.assertEqual(result.revision, 1)
                self.assertEqual(len(world.reproduction_group_snapshot().groups), 1)

    def test_worlds_have_isolated_identity_and_request_namespaces(self):
        first_world = make_world("first")
        second_world = make_world("second")
        first = self.publish(first_world, candidate(), key="same-key")
        second = self.publish(second_world, candidate(), key="same-key")
        self.assertNotEqual(first.world_identity, second.world_identity)
        self.assertEqual(first_world.get_reproduction_group("RG-PQ").group_id, "RG-PQ")
        self.assertEqual(second_world.get_reproduction_group("RG-PQ").group_id, "RG-PQ")
        self.assertEqual(first_world.reproduction_group_snapshot().request_keys, ("same-key",))
        self.assertEqual(second_world.reproduction_group_snapshot().request_keys, ("same-key",))

    def test_encounter_context_refuses_and_persistence_fails_closed(self):
        world = make_world()
        encounter = Encounter(world, difficulty_class=10, start_time=0)
        world.add_event(encounter)
        before = world.reproduction_group_snapshot()
        with self.assertRaisesRegex(ReproductionGroupPublicationError, "no Encounter"):
            self.publish(world, candidate(), key="not-authorized")
        self.assertEqual(world.reproduction_group_snapshot(), before)

        no_encounter_world = make_world()
        self.publish(no_encounter_world, candidate(), key="published")
        with self.assertRaisesRegex(ValueError, "persistence contract"):
            no_encounter_world.to_json()

    def test_statistical_group_being_rng_and_observer_state_are_unchanged(self):
        world = make_world()
        config = deepcopy(GROUP_CONFIG)
        config["group_id"] = "population"
        group = StatisticalGroup("Population", "population", config, config["seed"])
        world.add_object(group)
        counts = group.counts()
        group_cache = group._counts
        member_store = group._members
        realized_store = group._realized_beings
        motion_store = group._motion_attached_native_ids
        object_map = world.object_registry.object_instances
        native_being = BeingInstance(
            BeingDefinition("Human", 6, 170, 10, "2d6", "Neutral", 10, 1), "Present", id="native-being"
        )
        world.add_object(native_being)
        ledger = BeliefLedger("observer")
        before_ledger = (ledger.evidence, ledger.belief_history, ledger.inquiry_history)
        before_rng = random.getstate()
        before_being = native_being.to_json()
        before_group = (group.counts(), dict(group._members), dict(group._realized_beings), set(group._motion_attached_native_ids))

        self.publish(world, candidate(), key="independent")

        self.assertEqual(group.counts(), counts)
        self.assertIs(group._members, member_store)
        self.assertIs(group._realized_beings, realized_store)
        self.assertIs(group._motion_attached_native_ids, motion_store)
        self.assertIs(group._counts, group_cache)
        self.assertEqual((group.counts(), dict(group._members), dict(group._realized_beings), set(group._motion_attached_native_ids)), before_group)
        self.assertIs(world.get_object_by_id("native-being"), native_being)
        self.assertEqual(native_being.to_json(), before_being)
        self.assertIs(world.object_registry.object_instances, object_map)
        self.assertEqual((ledger.evidence, ledger.belief_history, ledger.inquiry_history), before_ledger)
        self.assertEqual(random.getstate(), before_rng)


if __name__ == "__main__":
    unittest.main()
