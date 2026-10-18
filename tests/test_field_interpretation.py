"""Interpretation may depend on learned spotting while never setting reality."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'examples')]

from field_interpretation import FieldInterpreter
from field_observation import BeliefLedger, CountReport, FieldObservation
from spatial.state import CartesianPosition
from library import Library
from universe import Universe
from nomadic_group_experiment import run_scenario


class TestSkillInterpretation(unittest.TestCase):
    def test_same_observation_skills_change_interpretation_not_evidence(self):
        world = Universe('Interpretation test', library=Library(config_dir=str(ROOT/'src'/'config')))
        observer_id = world.make_being('Human', 'Hunter')
        being = world.get_object_by_id(observer_id)
        evidence = FieldObservation('e1', observer_id, 'g1', 0,
            CartesianPosition(0,0,0), 10,
            {'dogs': CountReport(9,2)}, 'controlled_test', {'dogs':2})
        interpreter = FieldInterpreter(expert_level=5)
        being.set_skill_level(world.get_skill_dictionary(), 'spot', 0)
        novice = interpreter.interpret(evidence, being)
        being.set_skill_level(world.get_skill_dictionary(), 'spot', 5)
        veteran = interpreter.interpret(evidence, being)
        self.assertEqual(novice.reports['dogs'].estimate, 9)
        self.assertEqual(veteran.reports['dogs'].estimate, 7)
        self.assertEqual((novice.skill_level, veteran.skill_level), (0, 5))
        self.assertEqual(evidence.reports['dogs'].estimate, 9)
        self.assertEqual(evidence.dubious_candidates['dogs'], 2)
        self.assertEqual(novice.reports['dogs'].uncertainty,
                         veteran.reports['dogs'].uncertainty)

    def test_expertise_not_guaranteed_correct(self):
        world = Universe('False cue test', library=Library(config_dir=str(ROOT/'src'/'config')))
        observer_id = world.make_being('Human', 'Expert')
        observer = world.get_object_by_id(observer_id)
        observer.set_skill_level(world.get_skill_dictionary(), 'spot', 10)
        # Here the flagged creatures actually ARE dogs. Interpreting dubious
        # cues as false positives makes the expert wrong, without an oracle.
        evidence = FieldObservation('e2', observer_id, 'g2', 0,
             CartesianPosition(0,0,0), 10, {'dogs': CountReport(7,1)},
             'controlled_test', {'dogs':2})
        report = FieldInterpreter().interpret(evidence, observer)
        self.assertEqual(report.reports['dogs'].estimate, 5)
        self.assertEqual(evidence.reports['dogs'].estimate, 7)

    def test_source_interpretations_survive_communication_and_keep_provenance(self):
        result = run_scenario()
        son, father = result['son'], result['father']
        observations = result['observations']
        son_ledger = result['beliefs'][son.id]
        father_ledger = result['beliefs'][father.id]
        self.assertEqual(son_ledger.interpretation_for(observations[2].id).skill_level, 6)
        self.assertEqual(father_ledger.interpretation_for(observations[1].id).skill_level, 1)
        self.assertIn(('dogs','alpha-t100','beta-t100'), son_ledger.discrepancies(result['group'].id))
        self.assertNotEqual(son_ledger.count_estimate(result['group'].id,'dogs'),
                            result['counts']['dogs'])
        self.assertEqual(result['group'].materialized_count, 1)
        with self.assertRaisesRegex(ValueError, 'original observer'):
            FieldInterpreter().interpret(observations[2], son)

    def test_bad_ambiguity_counts_rejected(self):
        from field_observation import FieldObserver
        from statistical_group import StatisticalGroup
        from encounter import Encounter
        cfg = json.loads((ROOT/'examples'/'nomadic_group.json').read_text())
        world = Universe('Test', library=Library(config_dir=str(ROOT/'src'/'config')))
        group = StatisticalGroup('Test','group',cfg,cfg['seed'])
        world.add_object(group)
        scout_id = world.make_being('Human','Scout')
        world.get_object_by_id(scout_id).set_position(CartesianPosition(0, -650, 0))
        encounter = Encounter(world, difficulty_class=10, start_time=0)
        encounter.add_being(scout_id)
        encounter.add_object(group.id)
        for candidates in ({'dogs': -1}, {'unknown': 1}, {'dogs': 1000}, {'dogs': True}):
            with self.subTest(candidates=candidates), self.assertRaises(ValueError):
                FieldObserver(**cfg['observation']).observe(encounter, scout_id, group,
                    'bad', dubious_candidates=candidates)


if __name__ == '__main__':
    unittest.main()
