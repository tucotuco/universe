"""Realized Group members can be discovered only by a later native Spot."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from action_evaluation import AwarenessEffect
from examples.transactional_group_member_spot import _execute
from spatial import Sphere


class TestTransactionalGroupMemberSpot(unittest.TestCase):
    def test_attention_spot_and_followup_are_reproducible_from_private_rng_cursor(self):
        first = _execute()
        second = _execute()
        for state in (first, second):
            spot = state["inspection"].action(state["spot"].id)
            self.assertTrue(state["attention_result"].accepted)
            self.assertEqual(spot.facts.outcome, "success")
            self.assertEqual(dict(spot.facts.metadata)["roll"], 18)
            self.assertEqual(state["spot"].target_id, state["member"].id)
            self.assertEqual(state["thrust"].target_id, state["member"].id)
        self.assertEqual(first["spot_receipt"].rng_state,
                         second["spot_receipt"].rng_state)
        self.assertEqual(first["thrust_receipt"].rng_state,
                         second["thrust_receipt"].rng_state)
        self.assertEqual(first["member"].get_hit_points(),
                         second["member"].get_hit_points())

    def test_realization_run_then_observer_specific_six_second_spot(self):
        state = _execute()
        world = state["world"]
        encounter = state["encounter"]
        group = state["group"]
        observer_one, observer_two = state["observers"]
        member = state["member"]
        candidate = state["candidate"]

        # Boundary 1's common snapshot excludes the candidate; publication
        # installs the very same Being in the registry, Group and Encounter.
        self.assertNotIn(member.id, state["first_interval"].pre_action_snapshot.entities)
        self.assertIs(world.get_object_by_id(member.id), member)
        self.assertIs(group._realized_beings[member.id], member)
        self.assertEqual(group._members[(0, "adults", 0)].id, member.id)
        self.assertEqual(encounter.being_list.count(member.id), 1)
        self.assertEqual(member.id, f"{group.id}/0/adults/0")
        self.assertEqual(candidate.geometry.sphere_radius, 0.5)
        self.assertEqual(member.geometry, Sphere(0.5))
        self.assertEqual(group.counts(), state["counts_before"])
        self.assertEqual(state["boundary_one_awareness"], (False, False))
        self.assertNotIn(member.id, state["boundary_one_receipt"].action_ids)
        self.assertNotIn(member.id, state["boundary_one_receipt"].effect_ids)
        self.assertNotIn(member.id, world.event_history)

        # The next boundary can include the Being and its legitimate Run.
        self.assertIn(member.id, state["second_interval"].pre_action_snapshot.entities)
        self.assertEqual(state["boundary_two_awareness"], (False, False))
        self.assertNotIn(member.id, state["awareness_before_spot"][0])
        self.assertNotIn(member.id, state["awareness_before_spot"][1])
        self.assertEqual(state["inspection"].action(state["member_run"].id).facts.outcome,
                         "success")
        self.assertEqual(member.get_skill_experience("run"), 7)
        self.assertIn(state["member_run"].id,
                      state["boundary_two_receipt"].action_ids)

        # The six-second Spot is scheduled after realization and only its
        # successful resolution adds directed Awareness to observer two.
        self.assertEqual(state["spot"].end_time - state["spot"].start_time, 6)
        spot_record = state["inspection"].action(state["spot"].id)
        self.assertEqual(spot_record.resolved_boundary, 8)
        self.assertEqual(spot_record.facts.outcome, "success")
        self.assertEqual(dict(spot_record.facts.metadata)["roll"], 18)
        self.assertEqual(state["awareness_by_boundary"], (
            (3, False, False), (4, False, False), (5, False, False),
            (6, False, False), (7, False, False), (8, False, True),
        ))
        self.assertFalse(encounter.is_aware(observer_one.id, member.id))
        self.assertTrue(encounter.is_aware(observer_two.id, member.id))
        self.assertNotIn(member.id, state["awareness_after_spot"][0])
        self.assertEqual(state["awareness_after_spot"][1], (observer_one.id, member.id))
        self.assertNotIn(member.id, state["awareness_before_spot"][1])
        self.assertTrue(state["attention_result"].accepted)
        self.assertFalse(hasattr(state["attention_result"], "target_id"))
        self.assertFalse(hasattr(state["attention_result"], "action_id"))
        self.assertEqual(state["spot"].target_id, member.id)  # trusted developer view
        awareness = [row.effect for row in spot_record.effects
                     if type(row.effect) is AwarenessEffect]
        self.assertEqual(len(awareness), 1)
        self.assertEqual((awareness[0].target_id, awareness[0].observed_id),
                         (observer_two.id, member.id))
        self.assertEqual(observer_one.get_skill_experience("spot"), 0)
        self.assertEqual(observer_two.get_skill_experience("spot"), 0)
        self.assertEqual(member.get_skill_experience("spot"), 0)
        self.assertIn(state["spot"].id, state["spot_receipt"].action_ids)
        self.assertEqual(group.counts(), state["counts_before"])
        self.assertNotEqual(state["rng_before"], state["rng"].state)
        self.assertEqual(state["rng"].state, state["thrust_receipt"].rng_state)

    def test_post_spot_native_targeted_thrust_uses_publisher(self):
        from action_evaluation import DamageEffect, PracticeEffect

        state = _execute()
        encounter = state["encounter"]
        member = state["member"]
        observer_one, observer_two = state["observers"]
        strike = state["thrust"]
        record = state["inspection"].action(strike.id)

        self.assertIs(encounter.get_being(strike.target_id), member)
        self.assertEqual(strike.target_id, state["thrust_target_id"])
        self.assertIn(strike.target_id, state["awareness_after_spot"][1])
        self.assertEqual((strike.actor_id, strike.target_id),
                         (observer_two.id, member.id))
        self.assertEqual(strike.instrument_id,
                         observer_two.armed_with(state["world"])["right hand"])
        self.assertEqual((strike.start_time, strike.end_time), (8, 12))
        self.assertTrue(encounter.is_aware(observer_two.id, member.id))
        self.assertFalse(encounter.is_aware(observer_one.id, member.id))
        path = encounter.line_of_sight(observer_two.id, member.id)
        self.assertTrue(any(row.entity_id == state["group"].id
                            and row.opacity == 0 for row in path.intersections))
        physical_path = encounter.physical_path(observer_two.id, member.id)
        self.assertNotIn(state["group"].id,
                         {row.entity_id for row in physical_path.intersections})
        self.assertEqual(record.resolved_boundary, 12)
        self.assertEqual(record.declaration.target_id, member.id)
        self.assertEqual(record.facts.outcome, "normal")
        self.assertEqual(record.facts.metadata[0][0], "distance")
        self.assertLessEqual(record.facts.metadata[0][1], strike.reach)
        self.assertEqual(member.get_hit_points(), state["target_hp_before_thrust"] - 4)
        self.assertEqual(state["inspection"].target(member.id).state.projected_hp,
                         member.get_hit_points())
        damage = [row for row in record.effects
                  if type(row.effect) is DamageEffect
                  and row.effect.target_id == member.id]
        self.assertEqual(len(damage), 1)
        self.assertEqual(damage[0].effect.amount, 4)
        self.assertEqual(damage[0].identity.source_action_id, strike.id)
        practice = [row for row in record.effects
                    if type(row.effect) is PracticeEffect]
        self.assertEqual(len(practice), 1)
        self.assertEqual((practice[0].effect.target_id,
                          practice[0].effect.skill,
                          practice[0].effect.experience),
                         (observer_two.id, 'Dagger', 10))
        self.assertEqual(practice[0].identity.source_action_id, strike.id)
        self.assertEqual(observer_two.get_skill_experience('Dagger'), 10)
        self.assertEqual(record.damage_by_target[member.id]["body"], 4)
        self.assertEqual(state["inspection"].target(member.id)
                         .damage_by_action[strike.id]["body"], 4)
        self.assertTrue(record.effects)
        self.assertTrue(all(row.identity.source_action_id == strike.id
                            for row in record.effects))
        self.assertIn(strike.id, state["thrust_receipt"].action_ids)
        self.assertEqual(state["thrust_receipt"].boundary, 12)
        from atomic_publication import _COMMITTED_RECEIPTS
        receipt_row = _COMMITTED_RECEIPTS[id(state["thrust_receipt"])]
        self.assertIs(receipt_row[0](), state["thrust_receipt"])
        self.assertIs(receipt_row[1](), encounter)
        self.assertEqual(state["group"].counts(), state["counts_before"])

    def test_failed_spot_does_not_create_a_followup_target_reference(self):
        state = _execute(spot_succeeds=False)
        member = state["member"]
        encounter = state["encounter"]
        observer_one, observer_two = state["observers"]

        self.assertEqual(state["inspection"].action(state["spot"].id).facts.outcome,
                         "failure")
        self.assertEqual(state["awareness_after_spot"], ((), (observer_one.id,)))
        self.assertFalse(encounter.is_aware(observer_one.id, member.id))
        self.assertFalse(encounter.is_aware(observer_two.id, member.id))
        self.assertIsNone(state["thrust"])
        self.assertIsNone(state["thrust_receipt"])
        self.assertIsNone(state["thrust_target_id"])
        self.assertEqual(encounter.time, 8)
        self.assertEqual(member.get_skill_experience("run"), 7)
        self.assertEqual(observer_two.get_skill_experience("spot"), 0)
        self.assertNotEqual(state["rng_before"], state["rng"].state)
        self.assertEqual(state["rng"].state, state["spot_receipt"].rng_state)

    def test_targeted_thrust_publication_fault_rolls_back_then_retries(self):
        state = _execute(inject_targeted_fault=True)
        self.assertEqual(state["targeted_rollback"],
                         {"phase": "targets", "restored": True})
        record = state["inspection"].action(state["thrust"].id)
        self.assertEqual(record.facts.outcome, "normal")
        self.assertEqual(record.resolved_boundary, 12)
        self.assertIn(state["thrust"].id, state["thrust_receipt"].action_ids)
        self.assertEqual(state["member"].get_hit_points(),
                         state["target_hp_before_thrust"] - 4)
        self.assertEqual(state["group"].counts(), state["counts_before"])


if __name__ == "__main__":
    unittest.main()
