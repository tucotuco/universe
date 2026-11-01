"""Combat scenarios: genuine Encounters preparation times, scripted outcomes disabled."""
import copy
import unittest
from pathlib import Path
import yaml
from combat_calibration import duration, effort_for_actor
from workbench import validated_config, simulate

ROOT=Path(__file__).resolve().parents[1]
NAMES=['combat_a_weapon_duel','combat_b_aggressive_defensive','combat_c_grapple_repeated']

class TestCombatCalibration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config=yaml.safe_load((ROOT/'config.yaml').read_text())
    def test_three_cases_registered(self):
        for name in NAMES:
            self.assertIn(name,self.config['scenarios'])
            self.assertIn('combat',self.config['scenarios'][name])
    def test_action_preparation_timing(self):
        self.assertEqual(duration({'kind':'strike','weapon_timing_s':6}),6)
        self.assertEqual(duration({'kind':'parry','weapon_timing_s':6}),5)
        self.assertEqual(duration({'kind':'dodge'}),2)
        self.assertEqual(duration({'kind':'grab'}),1)
        self.assertEqual(duration({'kind':'grapple'}),6)
        self.assertEqual(duration({'kind':'hold'}),6)
    def test_full_experiments(self):
        for name in NAMES[:2]:
            r=simulate(self.config,name)
            self.assertEqual(r['combat']['elapsed_seconds'],300)
            self.assertIsNone(r['combat']['first_failure'])
            self.assertTrue(r['combat']['injuries_disabled'])
            self.assertTrue(r['combat']['attack_rolls_disabled'])
            for actor in r['actors'].values():
                self.assertEqual(actor['summary']['total_seconds'],300)
                self.assertTrue(actor['summary']['completed'])
                self.assertEqual(actor['points'][-1]['seconds'],300)
    def test_grappling_has_two_180_second_bouts_and_30_second_rest(self):
        phases=self.config['scenarios'][NAMES[2]]['combat']['phases']
        self.assertEqual([x['seconds'] for x in phases],[180,30,180])
        self.assertEqual([x['kind'] for x in phases[1]['programs']['Grappler Fitness 12']], ['rest'])
    def test_original_grappling_workload_fails_before_first_bout_completes(self):
        r=simulate(self.config,NAMES[2])
        self.assertEqual(r['combat']['scheduled_seconds'],390)
        self.assertEqual(r['combat']['elapsed_seconds'],171)
        self.assertIsNotNone(r['combat']['first_failure'])
        self.assertEqual(r['combat']['first_failure'][0]['actor'],'Grappler Fitness 12')
        self.assertEqual(r['combat']['first_failure'][0]['action'],'Grapple control check')
        self.assertTrue(r['combat']['injuries_disabled'])
        for actor in r['actors'].values():
            self.assertFalse(actor['summary']['completed'])
            self.assertEqual(actor['summary']['total_seconds'],171)
    def test_same_external_demands_fitness_effect(self):
        a=simulate(self.config,NAMES[0])['actors']
        self.assertLess(a['Fitness 12 swordsman']['summary']['q'],a['Fitness 16 swordsman']['summary']['q'])
        self.assertLess(a['Fitness 12 swordsman']['summary']['b'],a['Fitness 16 swordsman']['summary']['b'])
        base={'reference_fitness':12,'fitness_exponent':1}
        act={'kind':'strike','demand':.72,'demand_basis':'reference_fitness'}
        self.assertAlmostEqual(effort_for_actor(act,{'fitness':12},base),.72)
        self.assertAlmostEqual(effort_for_actor(act,{'fitness':16},base),.54)
    def test_contests_not_fabricated(self):
        r=simulate(self.config,NAMES[2])
        events=r['combat']['event_log']
        self.assertTrue(any(e.get('events') for e in events))
        self.assertTrue(all(e.get('outcome') in ('action preparations completed (no hit/contest rolls)', 'prescribed action infeasible') for e in events))
        for actor in r['actors'].values():
            self.assertEqual(actor['summary']['events_by_type'].get('grab'),1)
            self.assertEqual(actor['summary']['events_by_type'].get('touch'),1)
            self.assertGreater(actor['summary']['events_by_type'].get('grapple',0),10)
    def test_rest_recovers_fast_reserve_between_bouts_when_effort_feasible(self):
        # Alternate workload is test-only; default demand=0.70 is not silently lowered.
        c=copy.deepcopy(self.config)
        phases=c['scenarios'][NAMES[2]]['combat']['phases']
        for phase in (phases[0], phases[2]):
            for program in phase['programs'].values():
                for action in program:
                    if action['kind']=='grapple': action['demand']=0.64
        result=simulate(c,NAMES[2])
        self.assertIsNone(result['combat']['first_failure'])
        self.assertEqual(result['combat']['elapsed_seconds'],390)
        for actor in result['actors'].values():
            self.assertEqual(actor['summary']['events_by_type'].get('grab'),2)
            self.assertEqual(actor['summary']['events_by_type'].get('touch'),2)
        points=result['actors']['Grappler Fitness 12']['points']
        self.assertGreater(points[210]['q'],points[180]['q'])
        self.assertLess(points[390]['q'],points[210]['q'])
    def test_defense_is_prepared_before_spending(self):
        r=simulate(self.config,NAMES[1])
        counter=r['actors']['Defensive fighter']['summary']['events_by_type']
        self.assertGreater(counter.get('parry',0),0)
        self.assertGreater(counter.get('defenses applied',0),0)
        for e in r['combat']['event_log']:
            for d in e.get('defenses',[]):
                self.assertIn(d['defense'],('parry','dodge'))
    def test_fixed_requirement_not_silently_relaxed(self):
        c=copy.deepcopy(self.config)
        a=c['scenarios'][NAMES[1]]['combat']['phases'][0]['programs']['Aggressive fighter'][0]
        a['demand']=1
        r=simulate(c,NAMES[1])
        self.assertIsNotNone(r['combat']['first_failure'])
        self.assertFalse(r['actors']['Aggressive fighter']['summary']['completed'])
        self.assertLess(r['combat']['elapsed_seconds'],300)
        self.assertTrue(all(x['summary']['total_seconds']==r['combat']['elapsed_seconds'] for x in r['actors'].values()))
    def test_invalid_workloads_rejected(self):
        c=copy.deepcopy(self.config)
        c['scenarios'][NAMES[0]]['combat']['phases'][0]['programs']['Fitness 12 swordsman'][0]['demand']=1.5
        with self.assertRaises(ValueError):validated_config(c)
    def test_inherited_parameter_edit_affects_combat(self):
        c=copy.deepcopy(self.config)
        before=simulate(c,NAMES[0])['actors']['Fitness 12 swordsman']['summary']['q']
        c['profiles']['mammal_reference']['parameters']['fast_budget']*=.7
        after=simulate(c,NAMES[0])['actors']['Fitness 12 swordsman']['summary']['q']
        self.assertLess(after,before)

if __name__=='__main__':unittest.main()
