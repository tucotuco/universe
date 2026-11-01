"""Revision-60 deliberate Spot semantics in legacy and native evaluation paths."""
import math
import random
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from action_evaluation import AwarenessEffect, capture_snapshot, evaluate_snapshot
from activities import SpotAction
from encounter import Encounter
from library import Library
from spatial import CartesianPosition, Sphere
from universe import Universe


class TestSpotAction(unittest.TestCase):
    def setUp(self):
        self.world = Universe('Spotting', library=Library(config_dir=str(ROOT / 'src/config')))
        self.actor_id = self.world.make_being('Human', 'Observer')
        self.target_id = self.world.make_being('Human', 'Target')
        self.actor = self.world.get_object_by_id(self.actor_id)
        self.target = self.world.get_object_by_id(self.target_id)
        self.actor.set_position(CartesianPosition(0, 0, 0))
        self.target.set_position(CartesianPosition(100, 0, 0))  # no arbitrary fixed cap
        self.actor.set_geometry(Sphere(.5)); self.target.set_geometry(Sphere(.5))
        self.encounter = Encounter(self.world, difficulty_class=99, start_time=0, initiated=True)
        self.encounter.add_being(self.actor_id); self.encounter.add_being(self.target_id)
        self.encounter.mark_aware(self.actor_id, self.target_id)

    def test_six_second_duration_is_fixed_at_integer_and_fractional_start(self):
        self.assertEqual(SpotAction(self.world, self.actor_id, self.target_id, 0).end_time, 6)
        fractional = SpotAction(self.world, self.actor_id, self.target_id, .25)
        self.assertEqual(fractional.end_time, 6.25)
        self.assertEqual(math.ceil(fractional.end_time), 7)
        with self.assertRaisesRegex(ValueError, 'exactly six'):
            SpotAction(self.world, self.actor_id, self.target_id, 0, duration=1)

    def _evaluate(self, *, roll, conditions=()):
        action = SpotAction(self.world, self.actor_id, self.target_id, 0,
                            die_roll=roll, spotting_conditions=conditions)
        self.encounter.schedule_choice((action,))
        self.encounter.time = 6
        return action, evaluate_snapshot(capture_snapshot(self.encounter, 6))

    def test_target_default_dc_not_encounter_attack_dc_and_no_spot_xp(self):
        action, result = self._evaluate(roll=15)
        proposal = result.proposals[0]
        self.assertEqual(proposal.outcome, 'success')
        self.assertIn(('effective_dc', 15), proposal.metadata)
        self.assertEqual([e for e in proposal.effects if type(e) is AwarenessEffect],
                         [AwarenessEffect(action.id, self.actor_id, self.target_id, 100.0, None)])
        self.assertFalse(any(type(e).__name__ == 'PracticeEffect' for e in proposal.effects))
        self.assertNotIn('spot', self.actor.skill_experience)

    def test_explicit_target_dc_and_named_spotting_adjustments(self):
        self.target.current.discovery_dc = 18
        action, result = self._evaluate(roll=13, conditions=('high_contrast', 'light_fog'))
        proposal = result.proposals[0]
        self.assertEqual(proposal.outcome, 'failure')
        self.assertIn(('effective_dc', 14), proposal.metadata)

    def test_racial_action_aptitude_is_a_roll_bonus(self):
        elf_id = self.world.make_being('High elf', 'Elf observer')
        elf = self.world.get_object_by_id(elf_id)
        elf.set_position(CartesianPosition(0, 1, 0)); elf.set_geometry(Sphere(.5))
        self.encounter.add_being(elf_id)
        action = SpotAction(self.world, elf_id, self.target_id, 0, die_roll=13)
        self.encounter.schedule_choice((action,)); self.encounter.time = 6
        proposal = evaluate_snapshot(capture_snapshot(self.encounter, 6)).proposals[0]
        self.assertEqual(proposal.outcome, 'success')
        self.assertIn(('racial_action_bonus', 2), proposal.metadata)

    def test_discovery_uses_modified_total_without_unadopted_natural_roll_rules(self):
        self.target.current.discovery_dc = 1
        low, result = self._evaluate(roll=1)
        self.assertEqual(result.proposals[0].outcome, 'success')
        self.setUp()
        self.target.current.discovery_dc = 21
        high, result = self._evaluate(roll=20)
        self.assertEqual(result.proposals[0].outcome, 'failure')

    def test_failed_roll_and_impossible_unmodeled_path_do_not_create_awareness(self):
        action, result = self._evaluate(roll=14)
        self.assertEqual(result.proposals[0].outcome, 'failure')
        self.assertEqual(result.proposals[0].effects, ())
        self.setUp()
        self.target.set_geometry(None)
        action2 = SpotAction(self.world, self.actor_id, self.target_id, 0, die_roll=20)
        self.encounter.schedule_choice((action2,)); self.encounter.time = 6
        proposal = evaluate_snapshot(capture_snapshot(self.encounter, 6)).proposals[0]
        self.assertEqual(proposal.outcome, 'unmodeled_target')
        self.assertEqual(proposal.effects, ())

    def test_rng_evaluation_is_repeatable_and_does_not_advance_authority(self):
        action = SpotAction(self.world, self.actor_id, self.target_id, 0)
        self.encounter.schedule_choice((action,)); self.encounter.time = 6
        snapshot = capture_snapshot(self.encounter, 6)
        before = random.getstate()
        first = evaluate_snapshot(snapshot); second = evaluate_snapshot(snapshot)
        self.assertEqual(first, second)
        self.assertEqual(random.getstate(), before)

    def test_spotting_condition_contract_rejects_unknown_numeric_and_duplicate_inputs(self):
        for conditions in ((4,), ('made_up',), ('high_contrast', 'high_contrast')):
            with self.subTest(conditions=conditions), self.assertRaises(ValueError):
                SpotAction(self.world, self.actor_id, self.target_id, 0,
                           spotting_conditions=conditions)

    def test_all_applicable_named_spotting_adjustments_sum(self):
        action, result = self._evaluate(roll=15,
            conditions=('high_contrast', 'target_moving'))
        proposal = result.proposals[0]
        self.assertIn(('spotting_dc_adjustment', -10), proposal.metadata)
        self.assertEqual(proposal.outcome, 'success')


if __name__ == '__main__':
    unittest.main()
