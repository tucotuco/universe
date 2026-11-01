"""EXPERIMENTAL: Belief-conditioned follow-up after the Group observation demo.

Run with ``python examples/spatial_belief_inquiry.py``. Inquiry planning reads
only observer two's committed ledger. The returned proposal is detached demo
provenance; no native inquiry history is written outside the publisher.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'examples'))

from field_inquiry import InquiryPolicy
from group_observation import ObserveGroupAction
from spatial_two_observers import _schedule_second_observation
from spatial_group_observation import _build_scenario
from spatial import ISEAGrid


def _prepare_two_boundaries():
    (world, encounter, first_observer, second_observer, group,
     first_ledger, second_ledger, first_action, first_choice, rng,
     first_inspection) = _build_scenario()
    second_action, second_choice = _schedule_second_observation(
        world, encounter, second_observer, group, second_ledger)
    encounter.step(1)
    second_inspection = encounter.inspect_committed()
    return (world, encounter, first_observer, second_observer, group,
            first_ledger, second_ledger, first_action, first_choice, rng,
            first_inspection, second_action, second_choice, second_inspection)


def _decide(group_id, ledger, time):
    """Pure source-policy call. Receives no Group object or other ledger."""
    return InquiryPolicy(relative_uncertainty_threshold=0.5).propose(
        ledger, group_id, time)


def run_scenario(*, advance=True):
    (world, encounter, first_observer, second_observer, group,
     first_ledger, second_ledger, first_action, first_choice, rng,
     first_inspection, second_action, second_choice, second_inspection) = (
        _prepare_two_boundaries())
    source_evidence = second_ledger.evidence[-1]
    source_interpretation = second_ledger.interpretation_for(source_evidence.id)
    objective_records_at_decision = tuple(group._composition_reality._records.items())
    objective_revision_at_decision = group._composition_reality.revision
    history_before_decision = second_ledger.inquiry_history
    proposal = _decide(group.id, second_ledger, encounter.time)
    history_unchanged_by_decision = second_ledger.inquiry_history == history_before_decision
    if proposal is None:
        return {
            'world': world, 'encounter': encounter, 'group': group,
            'first_observer': first_observer, 'second_observer': second_observer,
            'first_ledger': first_ledger, 'second_ledger': second_ledger,
            'first_action': first_action, 'second_action': second_action,
            'first_choice': first_choice, 'second_choice': second_choice,
            'first_inspection': first_inspection,
            'second_inspection': second_inspection, 'proposal': None,
            'followup': None, 'followup_choice': None,
            'inspection': second_inspection, 'rng': rng,
            'source_evidence': source_evidence,
            'source_interpretation': source_interpretation,
            'history_unchanged_by_decision': history_unchanged_by_decision,
            'objective_records_at_decision': objective_records_at_decision,
            'objective_revision_at_decision': objective_revision_at_decision,
        }

    # Map the existing policy proposal to its existing supported Action. The
    # selected category focuses the same native sensor; no new resolver runs.
    action_settings = group.config['action_observation']
    followup = ObserveGroupAction(world, second_observer.id, group.id,
        encounter.time, seed=0, random_key='observer-two-inquiry',
        observation=action_settings['sensor'],
        interpretation=group.config['interpretation'],
        experience=action_settings['experience'], ledger=second_ledger,
        focus_category=proposal.category)
    followup_choice = encounter.schedule_choice((followup,))
    if advance:
        encounter.step(1)
        inspection = encounter.inspect_committed()
    else:
        inspection = second_inspection
    return {
        'world': world, 'encounter': encounter, 'group': group,
        'first_observer': first_observer, 'second_observer': second_observer,
        'first_ledger': first_ledger, 'second_ledger': second_ledger,
        'first_action': first_action, 'second_action': second_action,
        'first_choice': first_choice, 'second_choice': second_choice,
        'first_inspection': first_inspection,
        'second_inspection': second_inspection,
        'proposal': proposal, 'followup': followup,
        'followup_choice': followup_choice, 'inspection': inspection,
        'rng': rng, 'source_evidence': source_evidence,
        'source_interpretation': source_interpretation,
        'history_unchanged_by_decision': history_unchanged_by_decision,
        'objective_records_at_decision': objective_records_at_decision,
        'objective_revision_at_decision': objective_revision_at_decision,
    }


def demo_data():
    result = run_scenario()
    world, encounter, group = result['world'], result['encounter'], result['group']
    first_observer, second_observer = result['first_observer'], result['second_observer']
    first_ledger, second_ledger = result['first_ledger'], result['second_ledger']
    first_action, second_action = result['first_action'], result['second_action']
    proposal, followup = result['proposal'], result['followup']
    inspection = result['inspection']
    first_record = inspection.action(first_action.id)
    second_record = inspection.action(second_action.id)
    followup_record = inspection.action(followup.id)
    source = result['source_evidence']
    source_interpretation = result['source_interpretation']
    evidence = second_ledger.evidence[-1]
    interpretation = second_ledger.interpretation_for(followup.id)
    grid = ISEAGrid(radius=1.0)
    return {
        'encounter': {
            'time': encounter.time,
            'committed_boundaries': tuple(row.boundary
                for row in encounter.__dict__['_atomic_interval_history']),
        },
        'decision': {
            'policy': 'native InquiryPolicy(relative_uncertainty_threshold=0.5)',
            'observer_id': second_observer.id,
            'reason': proposal.reason,
            'category': proposal.category,
            'decision_time': proposal.time,
            'source_evidence_ids': proposal.evidence_ids,
            'source_observation_id': source.id,
            'source_action_id': second_action.id,
            'source_boundary': second_record.resolved_boundary,
            'source_estimates': {key: source.reports[key].estimate
                                 for key in ('humans', 'livestock', 'dogs')},
            'source_interpretation_observer_id': source_interpretation.observer_id,
            'inquiry_history_unchanged_by_decision': result['history_unchanged_by_decision'],
            'native_inquiry_history_entries': len(second_ledger.inquiry_history),
        },
        'followup': {
            'action_id': followup.id,
            'choice_id': result['followup_choice'].id,
            'actor_id': followup_record.declaration.actor_id,
            'target_id': followup_record.facts.target_ids[0],
            'focus_category': followup.focus_category,
            'boundary': followup_record.resolved_boundary,
            'outcome': followup_record.facts.outcome,
            'new_evidence_id': evidence.id if evidence.id != source.id else None,
            'new_evidence_time': evidence.time,
            'new_evidence_estimate': evidence.reports[proposal.category].estimate,
            'new_interpretation_estimate': interpretation.reports[proposal.category].estimate,
            'belief_revision_ids': tuple(row.trigger_observation_id
                                         for row in second_ledger.belief_history),
            'practice_times': tuple(row.time for row in
                                    inspection.target(second_observer.id).practice_history),
            'practice_exercise_action_ids': tuple(
                batch.exercises[0].action_id for batch in
                inspection.target(second_observer.id).practice_history),
        },
        'objective_group': {
            'composition': {key: group.counts()[key]
                            for key in ('humans', 'livestock', 'dogs')},
            'reality_revision': group._composition_reality.revision,
            'reality_revision_at_decision': result['objective_revision_at_decision'],
            'fact_storage_unchanged_since_decision': (
                len(result['objective_records_at_decision']) ==
                    len(group._composition_reality._records)
                and all(k1 is k2 and v1 is v2
                    for (k1, v1), (k2, v2) in
                    zip(result['objective_records_at_decision'],
                        group._composition_reality._records.items()))),
            'fact_revisions': tuple(sorted({record.revision for record in
                group._composition_reality._records.values()})),
            'materialized_beings': group.materialized_count,
        },
        'observer_isolation': {
            'first_evidence_count': len(first_ledger.evidence),
            'second_evidence_ids': tuple(second_ledger._evidence),
            'first_knows_followup_id': followup.id in first_ledger._evidence,
            'first_and_second_spatial_cells': (
                str(first_observer.spatial_cell(grid, 5)),
                str(second_observer.spatial_cell(grid, 5))),
        },
    }


if __name__ == '__main__':
    print(json.dumps(demo_data(), indent=2, sort_keys=True))
