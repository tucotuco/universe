"""Regression tests for the first aggregate Reality/Observation/Belief experiment."""
from pathlib import Path
import json
import math
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "examples")]

from field_observation import BeliefLedger, FieldObservation, FieldObserver
from field_observation import CountReport
from statistical_group import StatisticalGroup, _draw_cdf
from spatial.state import CartesianPosition
from nomadic_group_experiment import run_scenario
from encounter import Encounter
from library import Library
from universe import Universe

CONFIG = json.loads((ROOT / "examples" / "nomadic_group.json").read_text())


def make_group():
    return StatisticalGroup(CONFIG["group_name"], CONFIG["group_id"],
                            CONFIG, CONFIG["seed"])


class TestStatisticalComposition(unittest.TestCase):
    def test_unrealized_until_needed_and_coherent(self):
        group = make_group()
        self.assertIsNone(group._counts)
        self.assertIsNone(group._household_count)
        self.assertEqual(group.materialized_count, 0)
        counts = group.counts()
        self.assertEqual(counts["humans"], counts["adults"] + counts["children"])
        self.assertEqual(counts["households"], group.household_count)
        self.assertEqual(group.materialized_count, 0)
        for category in group.CATEGORIES:
            self.assertEqual(counts[category], sum(group.household(i)[category]
                            for i in range(group.household_count)))

    def test_resolution_order_does_not_change_identity_or_counts(self):
        first = make_group()
        second = make_group()
        # Materialize a member before requesting group counts.
        a = first.member(0, "adults", 0)
        first_counts = first.counts()
        second_counts = second.counts()
        b = second.member(0, "adults", 0)
        self.assertEqual(a, b)
        self.assertEqual(first_counts, second_counts)
        self.assertEqual(first.member(0, "adults", 0), a)
        first_counts["adults"] = -100
        self.assertNotEqual(first.counts()["adults"], -100)

    def test_selected_member_is_bounded_and_does_not_expand_count(self):
        group = make_group()
        member = group.member(0, "adults", 0)
        before = group.counts()
        point = group.member_position(member)
        self.assertLessEqual(math.dist(point.as_tuple(), group.get_position().as_tuple()),
                             group.footprint_radius + 1e-9)
        self.assertEqual(group.materialized_count, 1)
        self.assertEqual(group.counts(), before)
        with self.assertRaises(IndexError):
            group.member(0, "adults", 999)
        with self.assertRaises(ValueError):
            group.member(0, "horses", 0)

    def test_reject_invalid_cdf_and_motion(self):
        import random
        for cdf in ([], [[1, 0.4], [2, 0.3]], [[1, 0.4], [1, 1.0]],
                    [[1, 0.4], [2, 0.9]]):
            with self.subTest(cdf=cdf), self.assertRaises(ValueError):
                _draw_cdf(cdf, random.Random(3))
        config = json.loads(json.dumps(CONFIG))
        config["motion"]["max_acceleration_mps2"] = 0.0001
        with self.assertRaises(ValueError):
            StatisticalGroup("Bad", "bad", config, 42)


class TestMotionAndConstraints(unittest.TestCase):
    def test_constant_acceleration_and_conservative_future_envelope(self):
        group = make_group()
        self.assertEqual(group.velocity, (0.0, -3.0, 0.0))
        member = group.member(0, "adults", 0)
        offset = member.offset
        group.advance(100)
        self.assertAlmostEqual(group.get_position().y, -275)
        self.assertAlmostEqual(group.velocity[1], -2.5)
        self.assertEqual(group.time, 100)
        self.assertAlmostEqual(group.member_position(member).y, -275 + offset[1])
        envelope = group.reachable_at(160)
        self.assertAlmostEqual(envelope.center.y, -425)
        self.assertAlmostEqual(envelope.radius_m, 54)
        # A fully realized continuation under the established acceleration is bounded.
        group.advance(60)
        actual_distance = math.dist(group.get_position().as_tuple(), envelope.center.as_tuple())
        self.assertLessEqual(actual_distance, envelope.radius_m + 1e-9)
        with self.assertRaises(ValueError):
            group.reachable_at(100)
        with self.assertRaises(ValueError):
            group.advance(-1)


class TestObserverAndBelief(unittest.TestCase):
    def test_complete_scenario_and_false_observations_do_not_change_reality(self):
        result = run_scenario()
        group = result["group"]
        first, second, third = result["observations"]
        self.assertEqual(result["initially_unrealized"], (True, 0))
        self.assertEqual(group.materialized_count, 1)
        self.assertEqual((first.mode, second.mode, third.mode),
                         ("coarse_range_proxy", "detailed_range_proxy", "detailed_range_proxy"))
        self.assertEqual((first.time, second.time, third.time), (0, 100, 100))
        self.assertEqual(result["encounter"].time, group.time)
        self.assertEqual(result["counts"]["dogs"], 7)
        self.assertEqual((first.reports["dogs"].estimate,
                          second.reports["dogs"].estimate,
                          third.reports["dogs"].estimate), (9, 11, 9))
        self.assertEqual(group.counts()["dogs"], 7)
        self.assertEqual((result["son"].get_skill_level("spot"),
                          result["father"].get_skill_level("spot")), (1, 6))
        self.assertEqual(result["family"],
                         {"relationship": "father_of", "parent_id": result["father"].id,
                          "child_id": result["son"].id})
        interpreted = result["interpretations"]
        self.assertEqual(tuple(i.reports["dogs"].estimate for i in interpreted),
                         (9, 10, 7))
        self.assertEqual(tuple(i.rejected_candidates["dogs"] for i in interpreted),
                         (0, 1, 2))
        self.assertEqual(result["shared"], (1, 2))
        self.assertIn(("dogs", "alpha-t100", "beta-t100"), result["conflicts"])
        self.assertEqual(result["estimated_velocity"], (-0.08, -2.68, 0.0))
        self.assertAlmostEqual(result["alpha_prediction"].y, -438.8)
        self.assertNotEqual(result["alpha_prediction"], result["reachable"].center)
        self.assertEqual(result["encounter"].initiated, True)
        for scout in result["scouts"]:
            self.assertTrue(result["encounter"].is_aware(scout.id, group.id))

    def test_repeated_observations_communication_and_deduplication(self):
        result = run_scenario()
        first, second, third = result["observations"]
        alpha, beta = result["scouts"]
        alpha_ledger = result["beliefs"][alpha.id]
        beta_ledger = result["beliefs"][beta.id]
        self.assertEqual(len(alpha_ledger.evidence), 3)
        self.assertEqual(len(beta_ledger.evidence), 3)
        self.assertFalse(alpha_ledger.learn(first))
        self.assertEqual(alpha_ledger.share_from(beta_ledger), 0)
        self.assertEqual(len(alpha_ledger.evidence), 3)
        self.assertEqual(alpha_ledger.communication_log,
                         [(third.id, beta.id)])
        self.assertEqual(alpha_ledger.interpretation_for(third.id),
                         result["interpretations"][2])
        self.assertEqual(beta_ledger.interpretation_for(second.id),
                         result["interpretations"][1])
        self.assertEqual(alpha_ledger.interpretation_for(third.id).observer_id,
                         beta.id)
        self.assertEqual(beta_ledger.estimated_velocity(result["group"].id), None)
        self.assertNotEqual(alpha_ledger.count_estimate(result["group"].id, "dogs"),
                            result["counts"]["dogs"])
        with self.assertRaises(ValueError):
            alpha_ledger.learn(FieldObservation(first.id, first.observer_id,
                first.group_id, first.time, first.reported_position,
                first.position_uncertainty_m, {"dogs": CountReport(100, 0)}, first.mode))

    def test_no_observation_when_out_of_range(self):
        world = Universe("Far away", library=Library(config_dir=str(ROOT / "src" / "config")))
        group = make_group()
        world.add_object(group)
        scout_id = world.make_being("Human", "Far scout")
        world.get_object_by_id(scout_id).set_position(CartesianPosition(2000, 0, 0))
        encounter = Encounter(world, difficulty_class=10, start_time=0)
        encounter.add_being(scout_id)
        encounter.add_object(group.id)
        observer = FieldObserver(**CONFIG["observation"])
        self.assertIsNone(observer.observe(encounter, scout_id, group, "unseen"))
        self.assertIsNone(group._counts)
        self.assertFalse(encounter.is_aware(scout_id, group.id))


if __name__ == "__main__":
    unittest.main()
