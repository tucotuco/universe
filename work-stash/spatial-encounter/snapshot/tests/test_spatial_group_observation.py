"""Transactional spatial Group observation, objective Reality and private Belief."""
import random
import sys
import unittest
from unittest.mock import patch

ROOT = __import__('pathlib').Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'examples')]

from atomic_publication import PublicationFailure
from group_observation import ObserveGroupAction
from observer_proposals import (ObservationEffect, InterpretationEffect,
                                BeliefAcquisitionEffect)
from spatial import ISEAGrid
from spatial_group_observation import _build_scenario, demo_data


class TestSpatialGroupObservation(unittest.TestCase):
    def test_transaction_commits_objective_group_and_observer_owned_estimates(self):
        module_rng_before = random.getstate()
        (world, encounter, observer, other, group, ledger, other_ledger,
         action, choice, rng, inspection) = _build_scenario()
        self.assertEqual(random.getstate(), module_rng_before)
        self.assertEqual((encounter.time, inspection.boundary), (1, 1))
        self.assertEqual(tuple(encounter.being_list), (observer.id, other.id))
        self.assertEqual(encounter.get_entity(group.id), group)
        self.assertEqual(group.materialized_count, 0)

        grid = ISEAGrid(radius=1.0)
        for entity in (observer, other, group):
            self.assertEqual(entity.spatial_cell(grid, 5),
                grid.cell_at(*entity.get_position().angular_coordinate(), 5))
        self.assertEqual(observer.get_position().as_tuple(), (0., -200., 1000.))
        self.assertEqual(group.get_position().as_tuple(), (0., 0., 1000.))

        record = inspection.action(action.id)
        self.assertEqual(record.declaration.actor_id, observer.id)
        self.assertEqual(record.facts.target_ids, (group.id,))
        self.assertEqual(record.facts.outcome, 'success')
        self.assertEqual((action.id, choice.id),
                         (record.declaration.id, record.lifecycle.choice_id))
        effects = [row.effect for row in record.effects]
        self.assertTrue(any(type(effect) is ObservationEffect
                            and effect.source_action_id == action.id
                            and effect.target_id == observer.id for effect in effects))
        self.assertTrue(any(type(effect) is InterpretationEffect
                            and effect.source_action_id == action.id for effect in effects))
        self.assertTrue(any(type(effect) is BeliefAcquisitionEffect
                            and effect.source_action_id == action.id
                            and effect.acquired for effect in effects))
        self.assertEqual(inspection.objective[group.id].counts,
                         group.counts())
        committed_belief = next(iter(inspection.recipients.values()))
        self.assertEqual(committed_belief.observer_id, observer.id)
        self.assertIn(action.id, committed_belief.evidence)
        self.assertEqual(len(committed_belief.belief_history), 3)

        # Objective facts belong to the Group. The noisy estimate differs from
        # at least one actual aggregate count and never overwrites those facts.
        facts = group._composition_reality.view().all_facts()
        self.assertEqual(len(facts), 5)
        truth = group.counts()
        evidence = ledger.evidence[0]
        self.assertEqual((evidence.id, evidence.observer_id, evidence.group_id,
                          evidence.time),
                         (action.id, observer.id, group.id, 1))
        self.assertTrue(any(evidence.reports[key].estimate != truth[key]
                            for key in ('humans', 'livestock', 'dogs')))
        self.assertTrue(all(evidence.reports[key].uncertainty > 0
                            for key in ('humans', 'livestock', 'dogs')))
        self.assertEqual(ledger.interpretation_for(action.id).skill_level, 1)
        self.assertEqual(len(ledger.belief_history), 3)
        self.assertTrue(all(row.trigger == 'observation'
                            and row.trigger_observation_id == action.id
                            for row in ledger.belief_history))
        self.assertFalse(other_ledger.evidence)
        self.assertFalse(other_ledger.belief_history)
        self.assertEqual(group.materialized_count, 0)

        practice = inspection.target(observer.id).practice_history
        self.assertEqual(len(practice), 1)
        self.assertEqual((practice[0].being_id, practice[0].skill_name,
                          practice[0].experience, practice[0].time),
                         (observer.id, 'spot', 12, 1))
        self.assertEqual(practice[0].exercises[0].action_id, action.id)
        self.assertEqual(practice[0].exercises[0].effect_identity.source_action_id,
                         action.id)
        self.assertEqual(observer.get_skill_experience('spot'), 12)
        self.assertEqual(rng.state[0], 3)
        self.assertIsNone(encounter.location)

    def test_seeded_example_is_reproducible_and_keeps_reality_separate(self):
        first, second = demo_data(), demo_data()
        for result in (first, second):
            self.assertEqual(result['encounter']['committed_boundary'], 1)
            self.assertEqual(result['observation']['outcome'], 'success')
            self.assertTrue(result['observation']['estimates_differ_from_objective'])
            self.assertTrue(result['observation']['observer_has_belief'])
            self.assertEqual(result['observation']['belief_revision_count'], 3)
            self.assertTrue(result['observation']['other_being_has_no_belief'])
            self.assertEqual(result['group']['realized_being_count'], 0)
            self.assertEqual(result['practice']['experience'], 12)
            self.assertEqual(result['practice']['exercise_action_id'],
                             result['observation']['action_id'])
        self.assertEqual(first['group']['objective_composition'],
                         second['group']['objective_composition'])
        self.assertEqual(first['observation']['evidence_estimates'],
                         second['observation']['evidence_estimates'])
        self.assertEqual(first['observation']['interpretation_estimates'],
                         second['observation']['interpretation_estimates'])
        self.assertEqual(first['derived_isea_cells'], second['derived_isea_cells'])

    def test_out_of_range_action_commits_without_group_realization_or_belief(self):
        from spatial_group_observation import _build_scenario
        (world, encounter, observer, other, group, ledger, _, action, _, _, inspection) = (
            _build_scenario(observer_position=(0., -5000., 1000.)))
        self.assertEqual(inspection.action(action.id).facts.outcome, 'out_of_range')
        self.assertEqual(group._composition_reality.view().all_facts(), ())
        self.assertIsNone(group._counts)
        self.assertFalse(ledger.evidence)
        self.assertEqual(observer.get_skill_experience('spot'), 0)
        self.assertEqual(encounter.time, 1)

    def test_non_group_target_is_rejected_before_native_registration(self):
        (world, encounter, observer, other, group, ledger, _, _, _, _, _) = (
            _build_scenario(advance=False))
        bad = ObserveGroupAction(world, observer.id, other.id, 0,
            seed=0, random_key='invalid-target',
            observation={'coarse_range_m': 1000, 'detailed_range_m': 450},
            ledger=ledger)
        events_before = dict(world.event_history)
        with self.assertRaises(ValueError):
            encounter.prepare_action(bad)
        self.assertEqual(world.event_history, events_before)
        self.assertNotIn(bad.id, encounter.pending_action_list)
        self.assertIsNone(bad._encounter)

    def test_failure_after_reality_and_belief_phases_rolls_back_the_whole_boundary(self):
        (world, encounter, observer, other, group, ledger, other_ledger,
         action, _, rng, _) = _build_scenario(advance=False)
        before_rng = rng.state
        import atomic_publication
        native_publish = atomic_publication.publish_interval_candidate

        def fail_after_observers(*args, **kwargs):
            kwargs['_fail_after'] = 'observers'
            return native_publish(*args, **kwargs)

        with patch('atomic_publication.publish_interval_candidate', fail_after_observers):
            with self.assertRaises(PublicationFailure):
                encounter.step(1)
        self.assertEqual(encounter.time, 0)
        self.assertEqual(encounter.last_processed_boundary, 0)
        self.assertIsNone(group._counts)
        self.assertEqual(group._composition_reality.view().all_facts(), ())
        self.assertFalse(ledger.evidence)
        self.assertFalse(ledger.belief_history)
        self.assertFalse(other_ledger.evidence)
        self.assertEqual(observer.get_skill_experience('spot'), 0)
        self.assertEqual(other.get_skill_experience('spot'), 0)
        self.assertEqual(rng.state, before_rng)
        self.assertNotIn(action.id, encounter.finished_action_list)


if __name__ == '__main__':
    unittest.main()
