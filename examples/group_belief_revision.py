"""Belief revision on new evidence, communication, and later skill advancement.

Run from repo root: python examples/group_belief_revision.py

The first sightings are the real ObserveGroupAction simulation. The later
skill advancement is explicit externally acquired practice: this demo does NOT
claim that merely hearing a report automatically trains a skill.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from field_interpretation import FieldInterpreter
from group_observation_encounter import run_scenario


def run_revision_scenario():
    result = run_scenario(seed=62)
    son = result['scouts']['son']
    father = result['scouts']['father']
    ledger = result['ledgers']['son']
    group_id = result['group'].id
    original_action = next(action for role, action in result['actions'] if role == 'son')
    original = ledger.interpretation_for(original_action.id)
    before = ledger.count_estimate(group_id, 'dogs')

    # Additional *actual skill practice* is supplied as a test input here;
    # parent-child tutoring/skill-teaching Actions remain future work.
    skill_use = son.record_skill_use(
        result['world'].get_skill_dictionary(), 'spot', experience=1250,
        action_id='external-practice-spot-1', time=102, outcome='guided_practice')
    assert skill_use.level_after > skill_use.level_before
    changed = ledger.reconsider(original_action.id, son, FieldInterpreter(), at_time=103)
    after = ledger.count_estimate(group_id, 'dogs')

    return {'result': result, 'son': son, 'father': father, 'ledger': ledger,
            'original_action': original_action, 'original_interpretation': original,
            'prior_estimate': before, 'new_estimate': after, 'reconsidered': changed,
            'skill_use': skill_use}


if __name__ == '__main__':
    info = run_revision_scenario()
    ledger = info['ledger']
    action = info['original_action']
    print('Original dog evidence:', action.field_observation.reports['dogs'].estimate)
    print('Original interpretation at rank', info['original_interpretation'].skill_level,
          ':', info['original_interpretation'].reports['dogs'].estimate)
    print('Father and son shared reports; no objective counts were copied into belief.')
    print('Son skill rank after explicit practice:', info['son'].get_skill_level('spot'))
    print('Reinterpreted original report:', ledger.current_interpretation_for(action.id).reports['dogs'].estimate)
    print('Dog belief estimate, before -> after:', info['prior_estimate'], '->', info['new_estimate'])
    print('Belief revision history entries:', len(ledger.belief_history))
    print('Personal reassessments:', len(ledger.reassessments))
    print('True group composition still:', info['result']['group'].counts())
