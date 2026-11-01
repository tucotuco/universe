"""Revision-60 Spot supplies exact, observer-owned visible Group count evidence."""
import json
from pathlib import Path
import random
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'examples')]

from activities import SpotAction
from action_evaluation import UnsupportedEvaluation
from atomic_publication import PublicationFailure, RNGCursor
from encounter import Encounter
from field_observation import BeliefLedger
from library import Library
from spatial import CartesianPosition, Sphere
from statistical_group import StatisticalGroup
from universe import Universe


def build(*, rolls=(20, 20), visible=(True, True)):
    config = json.loads((ROOT / 'examples' / 'nomadic_group.json').read_text())
    config['group_id'] = 'exact-visible-group'
    config['motion'].update(position=[0, 0, 0], velocity=[0, 0, 0], acceleration=[0, 0, 0])
    world = Universe('Exact Group Spot', library=Library(config_dir=str(ROOT / 'src' / 'config')))
    ids = [world.make_being('Human', name) for name in ('First observer', 'Second observer')]
    observers = [world.get_object_by_id(key) for key in ids]
    observers[0].set_position(CartesianPosition(0, -20, 0))
    observers[1].set_position(CartesianPosition(20, -20, 0))
    for observer in observers:
        observer.set_geometry(Sphere(.5))
    group = StatisticalGroup('Visible group', config['group_id'], config, config['seed'])
    group.set_geometry(Sphere(5))
    world.add_object(group)
    encounter = Encounter(world, difficulty_class=15, start_time=0, initiated=True)
    world.add_event(encounter)
    for observer in observers:
        encounter.add_being(observer.id)
    encounter.add_object(group.id)
    ledgers = [BeliefLedger(observer.id) for observer in observers]
    rng = RNGCursor(random.Random(5102).getstate())
    encounter.enable_transactional_progression(quiescent=True, rng_owner=rng)
    actions = [SpotAction(world, observer.id, group.id, 0, die_roll=roll,
        ledger=ledger, group_fully_visible=full)
        for observer, ledger, roll, full in zip(observers, ledgers, rolls, visible)]
    for action in actions:
        encounter.schedule_choice((action,))
    return world, encounter, observers, group, ledgers, actions, rng


class TestSpotGroupEvidence(unittest.TestCase):
    def test_two_successful_native_spots_share_reality_but_keep_exact_evidence_private(self):
        global_rng = random.getstate()
        world, encounter, observers, group, ledgers, actions, rng = build()
        encounter.step(6)
        inspection = encounter.inspect_committed()
        self.assertEqual(random.getstate(), global_rng)
        self.assertEqual(encounter.time, 6)
        self.assertEqual(tuple(ledger.evidence for ledger in ledgers),
                         ((ledgers[0].evidence[0],), (ledgers[1].evidence[0],)))
        evidence = [ledger.evidence[0] for ledger in ledgers]
        self.assertEqual([item.observer_id for item in evidence],
                         [observer.id for observer in observers])
        self.assertNotEqual(evidence[0].id, evidence[1].id)
        self.assertEqual([item.reports['visible_count'].uncertainty for item in evidence], [0, 0])
        self.assertEqual([item.reports['visible_count'].estimate for item in evidence],
                         [evidence[0].reports['visible_count'].estimate] * 2)
        self.assertTrue(all(item.reported_position is None and
                            item.position_uncertainty_m is None for item in evidence))
        self.assertEqual([ledger.count_estimate(group.id, 'visible_count') for ledger in ledgers],
                         [evidence[0].reports['visible_count'].estimate] * 2)
        self.assertFalse(ledgers[0].interpretation_for(actions[0].id))
        self.assertFalse(ledgers[1].interpretation_for(actions[1].id))
        self.assertEqual(group.materialized_count, 0)
        self.assertEqual(len(group._composition_reality.view().all_facts()), 4)
        self.assertEqual([observer.get_skill_experience('spot') for observer in observers], [0, 0])
        self.assertTrue(all(not inspection.target(observer.id).practice_history for observer in observers))
        for action, ledger in zip(actions, ledgers):
            record = inspection.action(action.id)
            self.assertEqual((record.facts.outcome, record.facts.target_ids), ('success', (group.id,)))
            self.assertTrue(any(type(row.effect).__name__ == 'ObservationEffect'
                                and row.effect.source_action_id == action.id
                                for row in record.effects))
            self.assertTrue(any(type(row.effect).__name__ == 'BeliefAcquisitionEffect'
                                and row.effect.source_action_id == action.id
                                and row.effect.target_id == action.actor_id for row in record.effects))
            self.assertEqual(record.facts.metadata and dict(record.facts.metadata)['evidence_kind'],
                             'exact_visible_aggregate_count')
        self.assertTrue(encounter.is_aware(observers[0].id, group.id))
        self.assertTrue(encounter.is_aware(observers[1].id, group.id))
        # Awareness/evidence of the aggregate Group does not provide a Being
        # target or reveal any latent individual slot.
        self.assertEqual(encounter.aware_beings(observers[0].id), [])
        self.assertEqual(encounter.aware_beings(observers[1].id), [])

    def test_failed_spot_publishes_no_objective_or_observer_evidence(self):
        _, encounter, _, group, ledgers, _, _ = build(rolls=(1, 1))
        encounter.step(6)
        self.assertTrue(all(not ledger.evidence for ledger in ledgers))
        self.assertEqual(group._composition_reality.view().all_facts(), ())
        self.assertIsNone(group._counts)

    def test_ineligible_visibility_or_ledger_is_rejected_before_registration(self):
        world, encounter, observers, group, _, _, _ = build()
        with self.assertRaises(ValueError):
            SpotAction(world, observers[0].id, group.id, 6,
                       ledger=BeliefLedger(observers[0].id), group_fully_visible=False)
        ordinary_target = observers[1]
        wrong_target = SpotAction(world, observers[0].id, ordinary_target.id, 6,
            die_roll=20, ledger=BeliefLedger(observers[0].id), group_fully_visible=True)
        with self.assertRaises(UnsupportedEvaluation):
            encounter.prepare_action(wrong_target)
        self.assertNotIn(wrong_target.id, encounter.pending_action_list)

    def test_ordinary_spot_does_not_claim_a_shared_reality_request(self):
        from action_evaluation import UnsupportedEvaluation, future_reality_request
        world, _, observers, group, _, _, _ = build()
        ordinary = SpotAction(world, observers[0].id, group.id, 6, die_roll=20)
        with self.assertRaisesRegex(UnsupportedEvaluation, 'does not declare'):
            future_reality_request(ordinary)

    def test_publication_fault_rolls_back_reality_evidence_awareness_and_rng(self):
        _, encounter, observers, group, ledgers, actions, rng = build(rolls=(20, 1))
        before_rng = rng.state
        import atomic_publication
        publish = atomic_publication.publish_interval_candidate

        def fail_after_observers(*args, **kwargs):
            kwargs['_fail_after'] = 'observers'
            return publish(*args, **kwargs)

        with patch('atomic_publication.publish_interval_candidate', side_effect=fail_after_observers):
            with self.assertRaises(PublicationFailure):
                encounter.step(6)
        self.assertEqual(encounter.time, 0)
        self.assertEqual(encounter.last_processed_boundary, 0)
        self.assertEqual(tuple(ledger.evidence for ledger in ledgers), ((), ()))
        self.assertEqual(group._composition_reality.view().all_facts(), ())
        self.assertEqual(rng.state, before_rng)
        self.assertTrue(all(not encounter.is_aware(observer.id, group.id) for observer in observers))


if __name__ == '__main__':
    unittest.main()
