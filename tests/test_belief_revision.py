"""Evidence, interpretation and belief histories remain independent of reality."""
import json
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'examples')]

from field_observation import BeliefLedger
from field_interpretation import FieldInterpreter
from group_belief_revision import run_revision_scenario
from group_observation_encounter import run_scenario


class TestBeliefRevision(unittest.TestCase):
    def test_observation_and_communication_create_dated_assessments(self):
        result = run_scenario(seed=62)
        son = result['ledgers']['son']
        self.assertEqual(len(son.evidence), 4)
        self.assertEqual(len(son.belief_history), 12)  # 4 reports x 3 categories
        self.assertEqual({v.trigger for v in son.belief_history},
                         {'observation', 'communication'})
        self.assertEqual(sum(e.trigger == 'communication' for e in son.belief_history), 6)
        self.assertTrue(all(e.estimate >= 0 for e in son.belief_history))
        self.assertEqual(son.belief_history[-1].time, 101.0)  # time of sharing
        self.assertEqual(result['group'].materialized_count, 0)
        self.assertEqual(len(son.reassessments), 0)

    def test_later_skill_changes_belief_not_earlier_experience(self):
        scenario = run_revision_scenario()
        ledger, action = scenario['ledger'], scenario['original_action']
        before = scenario['original_interpretation']
        self.assertTrue(scenario['reconsidered'])
        self.assertEqual(ledger.interpretation_for(action.id), before)
        self.assertEqual(before.skill_level, 1)
        self.assertEqual(ledger.current_interpretation_for(action.id).skill_level, 3)
        self.assertEqual(action.field_interpretation, before)
        self.assertEqual(action.field_observation.reports['dogs'].estimate, 6)
        self.assertNotEqual(scenario['prior_estimate'], scenario['new_estimate'])
        self.assertEqual(ledger.reassessments[-1].time, 103)
        self.assertEqual(ledger.reassessments[-1].observation_id, action.id)
        self.assertEqual(ledger.belief_history[-1].trigger, 'reinterpretation')
        self.assertEqual(ledger.belief_history[-1].time, 103)
        self.assertEqual(ledger.belief_history[-1].trigger_observation_id, action.id)
        self.assertFalse(ledger.reconsider(action.id, scenario['son'],
                                           FieldInterpreter(), at_time=104))
        self.assertEqual(len(ledger.reassessments), 1)
        self.assertEqual(scenario['result']['group'].materialized_count, 0)

    def test_original_source_interpretation_unchanged_by_communication(self):
        scenario = run_revision_scenario()
        ledger = scenario['ledger']
        father = scenario['father']
        fathers_record = next(e for e in ledger.evidence if e.observer_id == father.id)
        original = ledger.interpretation_for(fathers_record.id)
        self.assertEqual(ledger.current_interpretation_for(fathers_record.id), original)
        with self.assertRaisesRegex(ValueError, 'original observer'):
            ledger.reconsider(fathers_record.id, scenario['son'],
                              FieldInterpreter(), at_time=104)
        self.assertEqual(ledger.interpretation_for(fathers_record.id), original)
        self.assertEqual(len(ledger.reassessments), 1)

    def test_export_keeps_old_and_revised_interpretation(self):
        scenario = run_revision_scenario()
        ledger, action = scenario['ledger'], scenario['original_action']
        exported = json.loads(json.dumps(ledger.to_dict()))
        self.assertEqual(exported['original_interpretations'][action.id]['skill_level'], 1)
        self.assertEqual(exported['reassessments'][0]['interpretation']['skill_level'], 3)
        self.assertEqual(exported['reassessments'][0]['observation_id'], action.id)
        self.assertEqual(len(exported['belief_history']), len(ledger.belief_history))
        self.assertEqual(len(exported['evidence']), 4)

    def test_reject_invalid_reattribution_or_retroactive_revision(self):
        scenario = run_revision_scenario()
        ledger, action = scenario['ledger'], scenario['original_action']
        with self.assertRaises(ValueError):
            ledger.reconsider(action.id, scenario['son'], FieldInterpreter(), at_time=-1)
        with self.assertRaises(ValueError):
            ledger.reconsider(action.id, scenario['father'], FieldInterpreter(), at_time=104)
        with self.assertRaises(KeyError):
            ledger.reconsider('unknown', scenario['son'], FieldInterpreter(), at_time=104)
        with self.assertRaises(ValueError):
            ledger.learn(action.field_observation, at_time=-1)


if __name__ == '__main__':
    unittest.main()
