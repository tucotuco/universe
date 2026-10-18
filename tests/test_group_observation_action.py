"""Integration and statistical checks for Action-mediated group observation."""
import json
from pathlib import Path
import random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'examples')]

from encounter import Encounter
from field_observation import BeliefLedger
from field_interpretation import FieldInterpreter
from group_observation import ObserveGroupAction, SampledGroupObservation
from library import Library
from spatial.state import CartesianPosition
from statistical_group import StatisticalGroup
from universe import Universe
from group_observation_encounter import run_scenario

CONFIG = json.loads((ROOT / 'examples' / 'nomadic_group.json').read_text())


def setup(spot_level=1, *, position=(0, -200, 0), difficulty=10):
    world = Universe('Action group observations', library=Library(config_dir=str(ROOT / 'src' / 'config')))
    group = StatisticalGroup('Test', 'group-1', CONFIG, CONFIG['seed'])
    world.add_object(group)
    scout_id = world.make_being('Human', 'Scout')
    scout = world.get_object_by_id(scout_id)
    scout.set_skill_level(world.get_skill_dictionary(), 'spot', spot_level)
    scout.set_position(CartesianPosition(*position))
    encounter = Encounter(world, difficulty_class=difficulty, start_time=0)
    encounter.add_being(scout_id)
    encounter.add_object(group.id)
    encounter.perceive_within(scout_id, 1000)
    assert encounter.decide_to_act(scout_id, group.id, 'investigate')
    ledger = BeliefLedger(scout_id)
    return world, group, scout, encounter, ledger


class TestGroupObservationAction(unittest.TestCase):
    def test_scouts_observe_through_actual_actions_without_instantiating_members(self):
        result = run_scenario(seed=62)
        self.assertEqual(result['initially_unrealized'], (True, 0))
        self.assertEqual(result['materialized'], 0)
        self.assertEqual(result['group'].time, result['encounter'].time)
        self.assertEqual(result['group'].counts()['dogs'], 7)
        self.assertEqual(len(result['actions']), 4)
        self.assertTrue(all(action.id in result['encounter'].finished_action_list
                            for _, action in result['actions']))
        self.assertTrue(all(action.resolution.outcome == 'success'
                            for _, action in result['actions']))
        self.assertTrue(all(action.field_observation is not None
                            for _, action in result['actions']))
        self.assertGreater(result['scouts']['father'].get_skill_level('spot'),
                           result['scouts']['son'].get_skill_level('spot'))
        self.assertEqual(len(result['ledgers']['son'].evidence), 4)
        self.assertEqual(len(result['ledgers']['father'].evidence), 4)
        self.assertEqual(result['exchanged'], (2, 2))
        self.assertTrue(result['discrepancies'])
        self.assertEqual(result['group'].materialized_count, 0)
        for role, scout in result['scouts'].items():
            self.assertEqual(len(scout.skill_use_history), 2)
            self.assertEqual(scout.get_skill_experience('spot'), 24)
            self.assertTrue(result['encounter'].is_aware(scout.id, result['group'].id))
        for role, action in result['actions']:
            use = [u for u in result['scouts'][role].skill_use_history
                   if u.action_id == action.id]
            self.assertEqual(len(use), 1)
            self.assertEqual(use[0].outcome, 'success')
            self.assertEqual(action.field_interpretation.skill_level,
                             action.skill_level_used)
            # Histories are reconstructible from Event/Action provenance.
            stored = json.loads(action.to_json())
            self.assertEqual(stored['field_observation']['id'], action.id)
            self.assertEqual(stored['resolution']['outcome'], 'success')

    def test_seed_is_reproducible_despite_new_world_and_action_identifiers(self):
        first = run_scenario(seed=62)
        second = run_scenario(seed=62)
        for (_, a), (_, b) in zip(first['actions'], second['actions']):
            self.assertEqual((a.roll, a.resolution.outcome),
                             (b.roll, b.resolution.outcome))
            self.assertEqual(a.field_observation.reports,
                             b.field_observation.reports)
            self.assertEqual(a.field_observation.reported_position,
                             b.field_observation.reported_position)
            self.assertEqual(a.field_interpretation.reports,
                             b.field_interpretation.reports)

    def test_failed_feasible_check_records_experience_but_not_observation(self):
        world, group, scout, encounter, ledger = setup(spot_level=1, difficulty=200)
        action = ObserveGroupAction(world, scout.id, group.id, 0, seed=9,
                                    random_key='failed', observation=CONFIG['observation'],
                                    ledger=ledger, experience={'success': 9, 'failure': 17})
        encounter.schedule_action(action)
        encounter.step()
        self.assertEqual(action.resolution.outcome, 'failure')
        self.assertIsNone(action.field_observation)
        self.assertFalse(ledger.evidence)
        self.assertIsNone(group._counts)
        self.assertEqual(scout.get_skill_experience('spot'), 17)
        self.assertEqual(scout.skill_use_history[-1].outcome, 'failure')

    def test_out_of_range_does_not_roll_or_commit_counts_or_award_xp(self):
        world, group, scout, encounter, ledger = setup(position=(900, 0, 0))
        action = ObserveGroupAction(world, scout.id, group.id, 0, seed=9,
                                    random_key='too-far', observation={'coarse_range_m': 500,
                                    'detailed_range_m': 200}, ledger=ledger)
        encounter.schedule_action(action)
        encounter.step()
        self.assertEqual(action.resolution.outcome, 'out_of_range')
        self.assertIsNone(action.roll)
        self.assertIsNone(group._counts)
        self.assertFalse(ledger.evidence)
        self.assertEqual(scout.get_skill_experience('spot'), 0)

    def test_skill_statistically_improves_evidence_and_interpretation(self):
        # Compare *matched* perspectives/noise seeds. Higher rank should
        # improve expected accuracy, but still sometimes be mistaken.
        group = StatisticalGroup('Group', 'test-group', CONFIG, CONFIG['seed'])
        world = Universe('Skill trials', library=Library(config_dir=str(ROOT/'src'/'config')))
        ids = [world.make_being('Human', name) for name in ('Apprentice', 'Veteran')]
        beings = [world.get_object_by_id(identifier) for identifier in ids]
        for being, level in zip(beings, (1, 6)):
            being.set_skill_level(world.get_skill_dictionary(), 'spot', level)
        sampler = SampledGroupObservation(**CONFIG['observation'])
        interpreter = FieldInterpreter(**CONFIG['interpretation'])
        errors = [0., 0.]
        veteran_wrong = 0
        actual = group.counts()['dogs']
        for trial in range(300):
            for i, level in enumerate((1, 6)):
                obs = sampler.sample(group, ids[i], 0, 400, level,
                                     f'{trial}', random.Random(trial))
                report = interpreter.interpret(obs, beings[i]).reports['dogs'].estimate
                errors[i] += abs(report - actual)
                if i == 1 and report != actual:
                    veteran_wrong += 1
        self.assertLess(errors[1], errors[0] * .85)
        self.assertGreater(veteran_wrong, 0)
        self.assertEqual(group.materialized_count, 0)

    def test_invalid_ledger_cannot_be_attached_to_another_scout(self):
        world, group, scout, encounter, _ = setup()
        with self.assertRaises(ValueError):
            ObserveGroupAction(world, scout.id, group.id, 0,
                               observation=CONFIG['observation'],
                               ledger=BeliefLedger('someone-else'))


if __name__ == '__main__':
    unittest.main()
