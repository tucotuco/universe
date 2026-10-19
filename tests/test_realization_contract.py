"""Contract probes: objective inquiry, selective commitment, and constraints."""
from pathlib import Path
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'examples')]

from realization import Fact, FactKey, ImpossibleRealization, RealityLedger
from realization_constraints import bounded_speed, fixed_composition, within_lifetime
from realization_contract_experiment import run_experiment


class RealizationContractTests(unittest.TestCase):
    def test_inspection_and_snapshot_do_not_realize(self):
        ledger = RealityLedger()
        key = FactKey('scout', 'childhood', 12)
        self.assertIsNone(ledger.inspect(key))
        self.assertEqual(ledger.view().facts_at('scout', 12), ())
        self.assertEqual(ledger.revision, 0)
        self.assertEqual(ledger.to_jsonable(), [])

    def test_interrogation_commits_once_and_reuses_fact(self):
        ledger = RealityLedger()
        key = FactKey('herder', 'teacher', 15)
        calls = []
        def propose(view):
            calls.append(1)
            self.assertFalse(view.contains(key))
            return [Fact(key, 'Ariadne')]
        first = ledger.ask(key, propose)
        second = ledger.ask(key, lambda view: self.fail('should not call generator'))
        self.assertTrue(first.newly_realized)
        self.assertFalse(second.newly_realized)
        self.assertEqual(first.record.value, 'Ariadne')
        self.assertEqual(second.record.value, 'Ariadne')
        self.assertEqual(len(calls), 1)
        self.assertEqual(ledger.revision, 1)

    def test_atomic_rejection_does_not_commit_supporting_facts(self):
        total = FactKey('caravan', 'adults', 0)
        a = FactKey('caravan', 'households', 0, 'a')
        b = FactKey('caravan', 'households', 0, 'b')
        ledger = RealityLedger([fixed_composition('caravan', 0, 'adults', 'households', ('a', 'b'))])
        ledger.commit([Fact(total, 9)])
        initial_revision = ledger.revision
        with self.assertRaises(ImpossibleRealization):
            ledger.ask(a, lambda view: [Fact(a, 5), Fact(b, 5)])
        self.assertEqual(ledger.revision, initial_revision)
        self.assertIsNone(ledger.inspect(a))
        self.assertIsNone(ledger.inspect(b))
        self.assertEqual(ledger.inspect(total).value, 9)
        self.assertTrue(ledger.ask(a, lambda view: [Fact(a, 4), Fact(b, 5)]).newly_realized)

    def test_unresolved_partitions_can_be_incomplete_but_not_contradictory(self):
        total = FactKey('g', 'total', 0)
        a = FactKey('g', 'member_count', 0, 'a')
        b = FactKey('g', 'member_count', 0, 'b')
        ledger = RealityLedger([fixed_composition('g', 0, 'total', 'member_count', ('a', 'b'))])
        ledger.commit([Fact(total, 9), Fact(a, 4)])
        self.assertFalse(ledger.view().contains(b))
        with self.assertRaises(ImpossibleRealization):
            ledger.commit([Fact(b, 4)])
        self.assertIsNone(ledger.inspect(b))
        ledger.commit([Fact(b, 5)])
        self.assertEqual(ledger.inspect(total).value, 9)

    def test_conflicting_recommit_is_rejected_and_identical_one_is_noop(self):
        ledger = RealityLedger()
        key = FactKey('herder', 'attribute')
        ledger.commit([Fact(key, {'role': 'hunter'})])
        before = ledger.revision
        self.assertEqual(ledger.commit([Fact(key, {'role': 'hunter'})]), ())
        with self.assertRaises(ImpossibleRealization):
            ledger.commit([Fact(key, {'role': 'guide'})])
        self.assertEqual(ledger.revision, before)
        self.assertEqual(ledger.inspect(key).value, {'role': 'hunter'})

    def test_malformed_candidate_is_rejected_before_any_change(self):
        ledger = RealityLedger()
        with self.assertRaises(ValueError):
            ledger.commit([Fact(FactKey('a', 'value'), float('nan'))])
        self.assertEqual(ledger.revision, 0)
        with self.assertRaises(ValueError):
            ledger.ask(FactKey('a', 'requested'), lambda view: [Fact(FactKey('a', 'other'), 1)])
        self.assertEqual(ledger.revision, 0)

    def test_mutable_value_cannot_rewrite_committed_history(self):
        ledger = RealityLedger()
        key = FactKey('g', 'composition')
        value = {'roles': ['herder']}
        ledger.commit([Fact(key, value)])
        value['roles'].append('hunter')
        read = ledger.inspect(key)
        read.value['roles'].append('guide')
        view = ledger.view()
        view.get(key)['roles'].append('scout')
        self.assertEqual(ledger.inspect(key).value, {'roles': ['herder']})

    def test_life_history_realization_does_not_commit_testimony(self):
        event = FactKey('being', 'training', 16)
        ledger = RealityLedger([within_lifetime('being', 'training', 0, 40)])
        testimony = 'I once trained with dragons'
        self.assertIsNone(ledger.inspect(event))
        self.assertEqual(ledger.revision, 0)  # hearing testimony changes no reality
        ledger.ask(event, lambda view: [Fact(event, 'trained with a mentor')])
        self.assertNotEqual(ledger.inspect(event).value, testimony)
        with self.assertRaises(ImpossibleRealization):
            ledger.commit([Fact(FactKey('being', 'training', 42), 'late training')])
        self.assertEqual(len(ledger.view().all_facts()), 1)

    def test_past_and_future_motion_may_constrain_intermediate_detail(self):
        validator = bounded_speed('group', 2.0)
        ledger = RealityLedger([validator])
        start = FactKey('group', 'position', 0)
        mid = FactKey('group', 'position', 5)
        finish = FactKey('group', 'position', 10)
        ledger.commit([Fact(start, [0,0,0]), Fact(finish, [10,0,0])])
        with self.assertRaises(ImpossibleRealization):
            ledger.commit([Fact(mid, [50,0,0])])
        self.assertIsNone(ledger.inspect(mid))
        ledger.commit([Fact(mid, [5,2,0])])
        self.assertEqual(ledger.inspect(finish).value, [10,0,0])

    def test_same_constraint_is_optional_when_no_motion_model_available(self):
        ledger = RealityLedger()
        ledger.commit([Fact(FactKey('group', 'position', 0), [0,0,0]),
                       Fact(FactKey('group', 'position', 1), [1000,0,0])])
        self.assertEqual(len(ledger.view().all_facts()), 2)

    def test_revision_distinct_from_in_world_time_and_json_export(self):
        ledger = RealityLedger()
        later = FactKey('person', 'location', 40)
        earlier = FactKey('person', 'training', 15)
        ledger.commit([Fact(later, 'home')])
        ledger.ask(earlier, lambda view: [Fact(earlier, 'school')])
        records = ledger.to_jsonable()
        self.assertEqual([r['time'] for r in records], [40,15])
        self.assertEqual([r['revision'] for r in records], [1,2])
        self.assertEqual(ledger.view().facts_at('person', 15)[0].value, 'school')
        self.assertEqual(ledger.inspect(later).value, 'home')


    def test_round_trip_recovers_realized_history_and_rechecks_constraints(self):
        total = FactKey('caravan', 'total', 0)
        a = FactKey('caravan', 'subgroup', 0, 'a')
        b = FactKey('caravan', 'subgroup', 0, 'b')
        rules = [fixed_composition('caravan', 0, 'total', 'subgroup', ('a','b'))]
        ledger = RealityLedger(rules)
        ledger.commit([Fact(total, 9)])
        ledger.ask(a, lambda view: [Fact(a, 4), Fact(b, 5)])
        saved = json.loads(json.dumps(ledger.to_jsonable()))
        restored = RealityLedger.from_jsonable(saved, rules)
        self.assertEqual(restored.to_jsonable(), saved)
        self.assertEqual(restored.revision, 2)
        self.assertFalse(restored.ask(a, lambda view: self.fail('already known')).newly_realized)
        with self.assertRaises(ImpossibleRealization):
            restored.commit([Fact(b, 10)])
        self.assertEqual(restored.inspect(b).value, 5)
        tampered = [dict(item) for item in saved]
        tampered[2]['value'] = 6
        with self.assertRaises(ImpossibleRealization):
            RealityLedger.from_jsonable(tampered, rules)

    def test_cross_domain_example(self):
        r = run_experiment()
        self.assertTrue(r['initially_unresolved'])
        self.assertTrue(r['group_detail'].newly_realized)
        self.assertTrue(r['invalid_position_rejected'])
        self.assertFalse(r['second_inquiry'].newly_realized)
        self.assertFalse(any(f.value == r['spoken_claim']
                             for f in r['ledger'].view().all_facts()))


if __name__ == '__main__':
    unittest.main()
