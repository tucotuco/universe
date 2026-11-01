"""EXPERIMENTAL Group sensor: discrepancy -> targeted observation -> evidence.

Run from repository root: python examples/group_inquiry_encounter.py
Seeded for reproducible tests; not a scripted correct observation.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'examples')]

from field_inquiry import InquiryPolicy
from group_observation import ObserveGroupAction
from group_observation_encounter import run_scenario


def run_inquiry_scenario(seed=62, followup_seed=7):
    result = run_scenario(seed=seed)
    encounter = result['encounter']
    group = result['group']
    son = result['scouts']['son']
    ledger = result['ledgers']['son']
    group_id = group.id

    # The decision uses *only the son's acquired/communicated evidence*.
    proposal = InquiryPolicy().propose(ledger, group_id, time=encounter.time)
    if proposal is None:
        return {'result': result, 'proposal': None, 'followup': None}
    original_evidence = len(ledger.evidence)
    action = ObserveGroupAction(
        result['world'], son.id, group_id, encounter.time,
        seed=followup_seed, random_key='son-inquiry',
        observation=result['group'].config['action_observation']['sensor'],
        interpretation=result['group'].config['interpretation'],
        experience=result['group'].config['action_observation']['experience'],
        ledger=ledger, focus_category=proposal.category)
    encounter.schedule_action(action)
    # Record only once Encounter accepted the scheduled decision/action.
    record = ledger.record_inquiry(proposal, action.id)
    group.advance(1)
    encounter.step(duration=1)
    return {
        'result': result, 'proposal': proposal, 'followup': action,
        'record': record, 'original_evidence_count': original_evidence,
        'remaining_discrepancies': ledger.discrepancies(group_id),
        'final_estimate': ledger.count_estimate(group_id, proposal.category),
    }


if __name__ == '__main__':
    info = run_inquiry_scenario()
    if info['proposal'] is None:
        print('No evidence-based question warrants follow-up under this policy.')
    else:
        proposal, action = info['proposal'], info['followup']
        ledger = info['result']['ledgers']['son']
        print('Son considers:', proposal.category, 'because', proposal.reason)
        print('Prompting evidence:', proposal.evidence_ids)
        print('Follow-up Action:', action.resolution.outcome, 'roll=', action.roll,
              'skill level=', action.skill_level_used)
        print('New evidence:', len(ledger.evidence) - info['original_evidence_count'])
        print('Updated estimate:', info['final_estimate'])
        print('Remaining discrepancies:', info['remaining_discrepancies'])
        print('Inquiry provenance saved:', json.dumps(ledger.to_dict()['inquiry_history']))
        print('Group members materialized:', info['result']['group'].materialized_count)
