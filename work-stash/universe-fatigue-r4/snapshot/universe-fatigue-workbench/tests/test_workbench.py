import sys,unittest,copy
from pathlib import Path
import yaml
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from workbench import validated_config,resolve_reference,effective_profile,simulate,simulate_actor
from universe_physical_fatigue_r4 import Profile, human_profile

class TestWorkbench(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg=yaml.safe_load((Path(__file__).resolve().parents[1]/'config.yaml').read_text())
    def test_default_valid(self):
        self.assertEqual(validated_config(self.cfg)['engine_revision'],'R4')
    def test_scaling_matches_authentic_r4(self):
        p=effective_profile(self.cfg,'human',18,20,True)
        q=human_profile(18,run_level=20,running=True)
        for name in p.__dataclass_fields__: self.assertAlmostEqual(getattr(p,name),getattr(q,name))
    def test_scenario_catalog(self):
        for key in self.cfg['scenarios']:
            with self.subTest(key=key):
                result=simulate(self.cfg,key)
                self.assertGreater(len(result['actors']),0)
                for actor in result['actors'].values():
                    self.assertTrue(0<=actor['summary']['q']<=100)
                    self.assertTrue(0<=actor['summary']['b']<=100)
                    self.assertGreater(actor['summary']['total_seconds'],0)
    def test_reference_edit_propagates(self):
        c=copy.deepcopy(self.cfg)
        initial=simulate(c,'legionary')['actors']['Legionary']['summary']['b']
        c['profiles']['mammal_reference']['parameters']['slow_depletion']*=.5
        modified=simulate(c,'legionary')['actors']['Legionary']['summary']['b']
        self.assertLess(modified,initial)
    def test_relay_individuals_independent(self):
        output=simulate(self.cfg,'pony_express')['actors']
        self.assertEqual(set(output),{'Horse A','Horse B','Rider'})
        self.assertGreater(output['Rider']['summary']['b'],output['Horse A']['summary']['b'])
    def test_cycle_rejected(self):
        c=copy.deepcopy(self.cfg)
        c['profiles']['mammal_reference']['parent']='human'
        with self.assertRaisesRegex(ValueError,'cycle'):validated_config(c)
    def test_inconsistent_profile_rejected(self):
        c=copy.deepcopy(self.cfg)
        c['profiles']['mammal_reference']['parameters']['critical_floor']=1.
        c['profiles']['mammal_reference']['parameters']['peak_floor']=.1
        with self.assertRaises(ValueError):validated_config(c)
    def test_zero_demand_sleep(self):
        c=copy.deepcopy(self.cfg)
        c['scenarios']['legionary']['actors']['Legionary']['segments'][-1]['demand']=.15
        with self.assertRaisesRegex(ValueError,'sleeping'):validated_config(c)
    def test_r4_source_unmodified(self):
        import hashlib
        p=Path(__file__).resolve().parents[1]/'universe_physical_fatigue_r4.py'
        self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),'0b54662e5c0f204120792257dd7ff2c9a29394e59cc2cfd8cb51dd863e63ba3f')
if __name__=='__main__': unittest.main()

class TestWorkloadAndAbilities(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg=yaml.safe_load((Path(__file__).resolve().parents[1]/'config.yaml').read_text())

    def test_identical_march_changes_workload_with_fitness(self):
        from workbench import physical_demand
        actor=self.cfg['scenarios']['legionary']['actors']['Legionary']
        seg=actor['segments'][0]
        self.assertEqual(seg['demand_basis'],'reference_fitness')
        low={**actor,'fitness':10.5}
        high={**actor,'fitness':15}
        self.assertGreater(physical_demand(self.cfg,low,seg),physical_demand(self.cfg,high,seg))
        self.assertAlmostEqual(physical_demand(self.cfg,low,seg),.44*12/10.5)

    def test_individual_effort_not_rescaled(self):
        from workbench import physical_demand
        actor={'profile':'human','fitness':10.5}
        self.assertEqual(physical_demand(self.cfg,actor,{'demand':.37}),.37)
        self.assertEqual(physical_demand(self.cfg,actor,{'demand':.37,'demand_basis':'individual'}),.37)

    def test_hard_duty_preserves_same_task_no_slack(self):
        statuses=[]
        for fitness in (10.5,11,11.5,12,13,14,15):
            case=copy.deepcopy(self.cfg)
            actor=case['scenarios']['legionary']['actors']['Legionary']
            actor['fitness']=fitness
            result=simulate(case,'legionary')['actors']['Legionary']['summary']
            statuses.append((fitness,result['completed'],result['total_seconds']))
            self.assertEqual(result['schedule_delay_seconds'],0)
            self.assertIsNone(result['work_pace_percent'])
        for f,completed,elapsed in statuses:
            if f<=13:self.assertFalse(completed, f)
            if f>=14:self.assertTrue(completed, f)
        self.assertEqual(statuses[-1][2],4*86400)
        self.assertLess(statuses[0][2],statuses[-1][2])

    def test_hard_duty_disallows_pacing_mode_and_schedule_extension(self):
        case=copy.deepcopy(self.cfg)
        case['scenarios']['legionary']['actors']['Legionary']['segments'][0]['execution']='fixed_work'
        with self.assertRaisesRegex(ValueError,'hard schedule forbids'):validated_config(case)
        case=copy.deepcopy(self.cfg)
        case['scenarios']['legionary']['actors']['Legionary']['segments'][0]['seconds']+=600
        with self.assertRaisesRegex(ValueError,'schedule blocks must total'):validated_config(case)

    def test_scenario_assessment_scope_is_not_external_completion(self):
        for key in ('ultramarathon','triathlon','pony_express','combat','sprint_recovery'):
            result=simulate(self.cfg,key)
            self.assertNotEqual(result['assessment_kind'],'fixed_duty')
            self.assertIn('assessment_note',result)
            self.assertGreater(len(result['assessment_note']),30)
        for key in ('legionary','legionary_moderate'):
            self.assertEqual(simulate(self.cfg,key)['assessment_kind'],'fixed_duty')

    def test_fixed_pace_mode_retains_strict_failure(self):
        case=copy.deepcopy(self.cfg)
        actor=case['scenarios']['legionary']['actors']['Legionary']
        actor['fitness']=11.5
        actor['segments'][0]['execution']='fixed_pace'
        actor['segments'][1]['execution']='fixed_pace'
        actor['segments'][0]['demand']=.37
        actor['segments'][1]['demand']=.42
        result=simulate(case,'legionary')['actors']['Legionary']['summary']
        self.assertFalse(result['completed'])
        self.assertEqual(result['failed_segment'],'Camp construction')
        self.assertGreater(result['total_seconds']/3600,29)
        self.assertLess(result['total_seconds']/3600,31)

    def test_bad_execution_mode_rejected(self):
        case=copy.deepcopy(self.cfg)
        actor=case['scenarios']['legionary']['actors']['Legionary']
        actor['segments'][0]['execution']='magical'
        with self.assertRaisesRegex(ValueError,'execution'):
            validated_config(case)

    def test_nonwork_fixed_mode_rejected(self):
        case=copy.deepcopy(self.cfg)
        actor=case['scenarios']['legionary']['actors']['Legionary']
        actor['segments'][3]['execution']='fixed_work' # sleep
        with self.assertRaisesRegex(ValueError,'fixed_work'):
            validated_config(case)

    def test_constitution_bounds_fitness_if_supplied(self):
        c=copy.deepcopy(self.cfg)
        c['scenarios']['legionary']['actors']['Legionary']['fitness']=17
        with self.assertRaisesRegex(ValueError,'Fitness cannot exceed Constitution'):
            validated_config(c)

    def test_workload_schema_configurable_and_exportable(self):
        from workbench import workload_scaling
        self.assertEqual(workload_scaling(self.cfg,'human')['reference_fitness'],12)
        new=copy.deepcopy(self.cfg)
        new['profiles']['human']['workload_scaling']['fitness_exponent']=.7
        self.assertEqual(workload_scaling(new,'human')['fitness_exponent'],.7)
        self.assertEqual(validated_config(yaml.safe_load(yaml.safe_dump(new)))['schema_version'],1)
