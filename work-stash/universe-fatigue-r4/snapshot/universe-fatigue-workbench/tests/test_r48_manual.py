import copy,sys, unittest,yaml
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from workbench import validated_config, simulate
from manual_cards import make_card
from universe_physical_fatigue_r4 import State
from workbench import effective_profile
from grapple_encounter import fatigue_contest_penalty

class TestR48Manual(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg=yaml.safe_load((ROOT/'config.yaml').read_text())
        cls.scenario='combat_d_live_grapple'
        cls.actor='Grappler Fitness 12'
    def test_fixed_sensitivity_is_not_configurable(self):
        g=self.cfg['scenarios'][self.scenario]['grapple_encounter']
        self.assertNotIn('physical_check_fatigue_sensitivity',g)
        self.assertNotIn('contest_penalty_scale',g)
        self.assertTrue(validated_config(copy.deepcopy(self.cfg)))
        old=copy.deepcopy(self.cfg)
        old['scenarios'][self.scenario]['grapple_encounter']['contest_penalty_scale']=5
        self.assertTrue(validated_config(old))
        self.assertNotIn('contest_penalty_scale',old['scenarios'][self.scenario]['grapple_encounter'])
        for key in ('contest_penalty_scale','physical_check_fatigue_sensitivity'):
            old=copy.deepcopy(self.cfg)
            old['scenarios'][self.scenario]['grapple_encounter'][key]=10
            with self.assertRaisesRegex(ValueError,'no longer configurable'):
                validated_config(old)

    def test_universal_penalty_independent_of_fitness_and_physiology(self):
        from standard_fatigue_check import physical_check_penalty, penalty_table
        state=State(.1,.6)
        for name,fitness in [('human',6),('human',12),('human',20),('equine_illustrative',15)]:
            prof=effective_profile(self.cfg,name,fitness)
            self.assertEqual(fatigue_contest_penalty(state,prof),physical_check_penalty(.1,.6))
        self.assertEqual(len(penalty_table()),11)
        self.assertEqual([len(row) for row in penalty_table()],[11]*11)

    def test_manual_card_uses_single_table_but_actor_specific_activity_cards(self):
        from standard_fatigue_check import markdown_table
        md=make_card(self.cfg,self.scenario,self.actor)
        self.assertIn('Physical Check Fatigue Sensitivity (rules constant): **5**',md)
        self.assertIn('It is **not repeated here**',md)
        self.assertNotIn(markdown_table(),md)
        self.assertIn('### Starting B ≈ 100%',md)
        self.assertIn('Grapple, 6 s',md)
        self.assertIn('Between-bout rest, 30 s',md)
        self.assertIn('**X**',md)
        alternate=copy.deepcopy(self.cfg)
        alternate['scenarios'][self.scenario]['actors'][self.actor]['profile']='equine_illustrative'
        equine=make_card(alternate,self.scenario,self.actor)
        self.assertNotIn(markdown_table(),equine)
        # But the effects of action/recovery remain individual.
        self.assertNotEqual(md.split('## Action and recovery reference cards')[1],
                            equine.split('## Action and recovery reference cards')[1])

    def test_combat_results_report_action_history_not_only_final_q(self):
        for F in (10,10.5):
            c=copy.deepcopy(self.cfg)
            c['scenarios'][self.scenario]['actors'][self.actor]['fitness']=F
            r=simulate(c,self.scenario)
            s=r['actors'][self.actor]['summary']
            self.assertEqual(s['total_seconds'],390)
            self.assertIn('seconds grapple',s['events_by_type'])
            self.assertIn('seconds recover',s['events_by_type'])
            self.assertGreaterEqual(s['q'],0)
            self.assertLessEqual(s['q'],100)

    def test_markup_order(self):
        html=(ROOT/'static/index.html').read_text()
        self.assertLess(html.index('SCENARIO ACTIVITY EDITOR'),html.index('REFERENCE PARAMETERS'))
        self.assertIn('manual-card-button',html)
        self.assertIn('being-contest-feedback',html)

if __name__=='__main__':unittest.main()
