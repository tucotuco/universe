"""Independent observations of one established Group across native boundaries."""
import sys
import unittest
from unittest.mock import patch

ROOT = __import__('pathlib').Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'examples')]

from atomic_publication import PublicationFailure
from observer_proposals import (ObservationEffect, InterpretationEffect,
                                BeliefAcquisitionEffect)
from spatial import ISEAGrid
from spatial_group_observation import _build_scenario
from spatial_two_observers import _schedule_second_observation, demo_data


def _second(world, encounter, observer, group, ledger):
    return _schedule_second_observation(world, encounter, observer, group, ledger)


class TestSpatialTwoObservers(unittest.TestCase):
    def test_second_boundary_reuses_objective_facts_and_keeps_beliefs_independent(self):
        (world, encounter, first_observer, second_observer, group,
         first_ledger, second_ledger, first_action, _, rng,
         first_inspection) = _build_scenario()
        ledger = group._composition_reality
        revision_after_first = ledger.revision
        fact_storage = ledger._records
        first_records = tuple(fact_storage.items())
        established_composition = group.counts()
        materialized_after_first = group.materialized_count
        evidence_a = first_ledger.evidence[0]
        beliefs_a = first_ledger.belief_history
        first_practice = first_observer.skill_use_history[0]

        second_action, second_choice = _second(
            world, encounter, second_observer, group, second_ledger)
        encounter.step(1)
        inspection = encounter.inspect_committed()

        self.assertEqual(tuple(row.boundary for row in encounter.__dict__['_atomic_interval_history']), (1, 2))
        self.assertEqual((first_inspection.boundary, inspection.boundary), (1, 2))
        self.assertEqual(inspection.action(first_action.id).resolved_boundary, 1)
        result_b = inspection.action(second_action.id)
        self.assertEqual(result_b.resolved_boundary, 2)
        self.assertEqual(result_b.facts.outcome, 'success')
        self.assertEqual(result_b.declaration.actor_id, second_observer.id)
        self.assertEqual(result_b.facts.target_ids, (group.id,))
        self.assertEqual(result_b.lifecycle.choice_id, second_choice.id)

        # Formation facts and native record identities are unchanged; every
        # boundary-2 objective fact was already established at revision 1.
        objective = inspection.objective[group.id]
        second_records = tuple(fact_storage.items())
        self.assertIs(ledger._records, fact_storage)
        self.assertEqual(ledger.revision, revision_after_first)
        self.assertEqual(len(first_records), len(second_records))
        self.assertTrue(all(k1 is k2 and v1 is v2
                            for (k1, v1), (k2, v2)
                            in zip(first_records, second_records)))
        self.assertEqual(dict(objective.counts), established_composition)
        self.assertTrue(all(fact.established_before and fact.revision == revision_after_first
                            for fact in objective.facts.values()))
        household_root = next(fact for key, fact in objective.facts.items()
                              if key.attribute == 'household_count')
        self.assertIn(first_action.id, household_root.requesting_action_ids)
        self.assertIn(second_action.id, household_root.requesting_action_ids)
        self.assertEqual(group.materialized_count, materialized_after_first)

        evidence_a_after = first_ledger.evidence[0]
        evidence_b = second_ledger.evidence[0]
        self.assertIs(evidence_a_after, evidence_a)
        self.assertEqual(first_ledger.evidence, (evidence_a,))
        self.assertEqual(tuple(second_ledger._evidence), (second_action.id,))
        self.assertIsNot(evidence_a, evidence_b)
        self.assertEqual((evidence_a.id, evidence_a.observer_id,
                          evidence_a.group_id, evidence_a.time),
                         (first_action.id, first_observer.id, group.id, 1))
        self.assertEqual((evidence_b.id, evidence_b.observer_id,
                          evidence_b.group_id, evidence_b.time),
                         (second_action.id, second_observer.id, group.id, 2))
        self.assertTrue(all(row.trigger_observation_id == first_action.id
                            for row in first_ledger.belief_history))
        self.assertTrue(all(row.trigger_observation_id == second_action.id
                            for row in second_ledger.belief_history))
        self.assertTrue(any(evidence_a.reports[k].estimate != evidence_b.reports[k].estimate
                            for k in ('humans', 'livestock', 'dogs')))
        self.assertTrue(any(evidence_b.reports[k].estimate != established_composition[k]
                            for k in ('humans', 'livestock', 'dogs')))

        for record, action_id in ((inspection.action(first_action.id), first_action.id),
                                  (result_b, second_action.id)):
            effects = [row.effect for row in record.effects]
            self.assertTrue(any(type(effect) is ObservationEffect
                                and effect.source_action_id == action_id
                                and effect.observation_id == action_id for effect in effects))
            self.assertTrue(any(type(effect) is InterpretationEffect
                                and effect.source_action_id == action_id for effect in effects))
            self.assertTrue(any(type(effect) is BeliefAcquisitionEffect
                                and effect.source_action_id == action_id
                                and effect.acquired for effect in effects))

        practice_a = inspection.target(first_observer.id).practice_history
        practice_b = inspection.target(second_observer.id).practice_history
        self.assertEqual((len(practice_a), len(practice_b)), (1, 1))
        self.assertEqual(practice_a[0], first_practice)
        self.assertIs(first_observer.skill_use_history[0], first_practice)
        self.assertEqual((practice_a[0].time, practice_a[0].experience,
                          practice_a[0].exercises[0].action_id),
                         (1, 12, first_action.id))
        self.assertEqual((practice_b[0].time, practice_b[0].experience,
                          practice_b[0].exercises[0].action_id),
                         (2, 12, second_action.id))
        self.assertTrue(encounter.is_aware(first_observer.id, group.id))
        self.assertTrue(encounter.is_aware(second_observer.id, group.id))
        self.assertFalse(encounter.is_aware(first_observer.id, second_observer.id))
        self.assertFalse(encounter.is_aware(second_observer.id, first_observer.id))
        self.assertEqual(first_observer.get_position().as_tuple(), (0., -200., 1000.))
        self.assertEqual(second_observer.get_position().as_tuple(), (0., -300., 1000.))
        grid = ISEAGrid(radius=1.0)
        for being in (first_observer, second_observer, group):
            self.assertEqual(being.spatial_cell(grid, 5),
                grid.cell_at(*being.get_position().angular_coordinate(), 5))
        self.assertEqual(rng.state[0], 3)

    def test_example_is_reproducible_with_distinct_logical_observers(self):
        first, second = demo_data(), demo_data()
        for result in (first, second):
            self.assertEqual(result['encounter']['committed_boundaries'], (1, 2))
            self.assertTrue(result['objective_group']['second_request_reuses_established_facts'])
            self.assertTrue(result['objective_group']['fact_storage_unchanged_after_second'])
            self.assertEqual(result['objective_group']['ledger_revision_after_first'], 1)
            self.assertEqual(result['objective_group']['ledger_revision_after_second'], 1)
            self.assertEqual(result['observers']['first']['boundary'], 1)
            self.assertEqual(result['observers']['second']['boundary'], 2)
            self.assertEqual(result['observers']['first']['outcome'], 'success')
            self.assertEqual(result['observers']['second']['outcome'], 'success')
            self.assertNotEqual(result['observers']['first']['estimates'],
                                result['observers']['second']['estimates'])
            self.assertTrue(result['observer_independence']['first_evidence_preserved'])
            self.assertTrue(result['observer_independence']['first_beliefs_preserved'])
            self.assertTrue(result['observer_independence']['second_has_only_its_observation'])
        self.assertEqual(first['objective_group']['composition'],
                         second['objective_group']['composition'])
        for key in ('estimates', 'interpretation_estimates'):
            self.assertEqual(first['observers']['first'][key], second['observers']['first'][key])
            self.assertEqual(first['observers']['second'][key], second['observers']['second'][key])
        self.assertEqual(first['derived_isea_cells'], second['derived_isea_cells'])

    def test_out_of_range_second_observer_does_not_change_first_commit(self):
        (world, encounter, first_observer, second_observer, group,
         first_ledger, second_ledger, first_action, _, rng,
         first_inspection) = _build_scenario(other_position=(0, -5000, 1000))
        ledger = group._composition_reality
        before_records = tuple(ledger._records.items())
        before_revision = ledger.revision
        before_evidence = first_ledger.evidence[0]
        before_practice = first_observer.get_skill_experience('spot')

        second_action, _ = _second(world, encounter, second_observer, group, second_ledger)
        encounter.step(1)
        inspection = encounter.inspect_committed()
        self.assertEqual(inspection.action(second_action.id).facts.outcome, 'out_of_range')
        self.assertEqual(encounter.time, 2)
        self.assertEqual(ledger.revision, before_revision)
        self.assertTrue(all(k1 is k2 and v1 is v2
                            for (k1, v1), (k2, v2)
                            in zip(before_records, ledger._records.items())))
        self.assertEqual(first_ledger.evidence, (before_evidence,))
        self.assertFalse(second_ledger.evidence)
        self.assertEqual(first_observer.get_skill_experience('spot'), before_practice)
        self.assertEqual(second_observer.get_skill_experience('spot'), 0)
        self.assertEqual(inspection.action(first_action.id).resolved_boundary, 1)
        self.assertEqual(first_inspection.boundary, 1)

    def test_second_boundary_publisher_failure_restores_only_boundary_two(self):
        (world, encounter, first_observer, second_observer, group,
         first_ledger, second_ledger, first_action, _, rng,
         first_inspection) = _build_scenario()
        ledger = group._composition_reality
        fact_storage = ledger._records
        first_records = tuple(fact_storage.items())
        first_revision = ledger.revision
        first_counts = group._counts
        first_receipt = encounter.__dict__['_atomic_interval_history'][0]
        first_evidence = first_ledger.evidence[0]
        first_beliefs = first_ledger.belief_history
        first_practice = tuple(first_observer.skill_use_history)
        first_experience = first_observer.get_skill_experience('spot')
        rng_at_boundary_one = rng.state

        second_action, _ = _second(world, encounter, second_observer, group, second_ledger)
        import atomic_publication
        native_publish = atomic_publication.publish_interval_candidate

        def fail_after_observers(*args, **kwargs):
            kwargs['_fail_after'] = 'observers'
            return native_publish(*args, **kwargs)

        with patch('atomic_publication.publish_interval_candidate', fail_after_observers):
            with self.assertRaises(PublicationFailure) as caught:
                encounter.step(1)
        self.assertEqual(caught.exception.phase, 'observers')
        self.assertEqual((encounter.time, encounter.last_processed_boundary), (1, 1))
        self.assertEqual(encounter.__dict__['_atomic_interval_history'], [first_receipt])
        self.assertEqual(encounter.__dict__['_atomic_interval_history'][0].boundary, 1)
        self.assertIs(ledger._records, fact_storage)
        self.assertEqual(ledger.revision, first_revision)
        self.assertIs(group._counts, first_counts)
        self.assertTrue(all(k1 is k2 and v1 is v2
                            for (k1, v1), (k2, v2)
                            in zip(first_records, fact_storage.items())))
        self.assertEqual(first_ledger.evidence, (first_evidence,))
        self.assertTrue(all(old is new for old, new
                            in zip(first_beliefs, first_ledger.belief_history)))
        self.assertEqual(tuple(first_observer.skill_use_history), first_practice)
        self.assertEqual(first_observer.get_skill_experience('spot'), first_experience)
        self.assertFalse(second_ledger.evidence)
        self.assertFalse(second_ledger.belief_history)
        self.assertEqual(second_observer.get_skill_experience('spot'), 0)
        self.assertNotIn(second_action.id, encounter.finished_action_list)
        self.assertEqual(rng.state, rng_at_boundary_one)

        # Existing controlled recovery returns exactly to boundary 1; the
        # staged second observation then succeeds deterministically.
        encounter.recover_transactional_progression(caught.exception.recovery_token)
        self.assertEqual((encounter.time, encounter.last_processed_boundary), (1, 1))
        encounter.step(1)
        recovered = encounter.inspect_committed()
        self.assertEqual(recovered.action(second_action.id).facts.outcome, 'success')
        self.assertEqual(recovered.action(first_action.id).resolved_boundary, 1)
        self.assertEqual(second_ledger.evidence[0].time, 2)
        self.assertEqual(ledger.revision, first_revision)
        self.assertEqual(group.materialized_count, 0)


if __name__ == '__main__':
    unittest.main()
