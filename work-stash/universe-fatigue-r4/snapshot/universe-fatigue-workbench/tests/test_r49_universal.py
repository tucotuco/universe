"""R4.9: universal, nonparametric check-table contract and appendix provenance."""
import unittest, yaml, csv, copy
from pathlib import Path
from math import floor
from standard_fatigue_check import physical_check_penalty, penalty_table, markdown_table, CHECK_SENSITIVITY
from workbench import effective_profile, simulate, validated_config
from universe_physical_fatigue_r4 import peak
from grapple_encounter import fatigue_contest_penalty
from universe_physical_fatigue_r4 import State

ROOT=Path(__file__).resolve().parents[1]

class UniversalFatigueTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg=yaml.safe_load((ROOT/'config.yaml').read_text())

    def test_exact_one_standard_table_all_profiles(self):
        self.assertEqual(CHECK_SENSITIVITY,5)
        for name,fitness in [('human',6),('human',12),('human',20),('equine_illustrative',15)]:
            prof=effective_profile(self.cfg,name,fitness)
            for qi,q in enumerate(range(100,-1,-10)):
                for bi,b in enumerate(range(100,-1,-10)):
                    v=fatigue_contest_penalty(State(q/100,b/100),prof)
                    self.assertEqual(v,penalty_table()[qi][bi])
        self.assertEqual(physical_check_penalty(1,1),0)
        self.assertEqual(physical_check_penalty(0,0),4)

    def test_appendix_reproduces_before_after_sensitivity_audit(self):
        bands=list(range(100,-1,-10))
        expected=[('human',6,1),('human',12,0),('human',20,4),('equine_illustrative',15,9)]
        for name,fitness,n in expected:
            p=effective_profile(self.cfg,name,fitness)
            delta=[floor(5*(1-peak(q/100,b/100,p))+.5+1e-12)-physical_check_penalty(q/100,b/100)
                   for q in bands for b in bands]
            self.assertEqual(sum(d!=0 for d in delta),n)
            self.assertTrue(all(abs(d)<=1 for d in delta))

    def test_csv_and_markdown_are_same_table(self):
        self.assertIn(markdown_table(),(ROOT/'FATIGUE-CONTEST-TABLE.md').read_text())
        with (ROOT/'fatigue-contest-table-universal.csv').open() as f:
            rows=list(csv.reader(f))
        self.assertEqual(len(rows),12)
        self.assertEqual(rows[0],['Q%/B%']+[str(x) for x in range(100,-1,-10)])
        for row,expected in zip(rows[1:],penalty_table()):
            self.assertEqual([int(x) for x in row[1:]],[-x for x in expected])

    def test_old_yaml_accepted_only_when_fixed_five_and_removed(self):
        for key in ('contest_penalty_scale','physical_check_fatigue_sensitivity'):
            cfg=copy.deepcopy(self.cfg)
            cfg['scenarios']['combat_d_live_grapple']['grapple_encounter'][key]=5
            validated_config(cfg)
            self.assertNotIn(key,cfg['scenarios']['combat_d_live_grapple']['grapple_encounter'])
            cfg=copy.deepcopy(self.cfg)
            cfg['scenarios']['combat_d_live_grapple']['grapple_encounter'][key]=5.5
            with self.assertRaisesRegex(ValueError,'no longer configurable'):
                validated_config(cfg)

    def test_each_side_contest_uses_universal_check_and_r4_engine_not_modified(self):
        r=simulate(copy.deepcopy(self.cfg),'combat_d_live_grapple')
        for name,out in r['actors'].items():
            s=out['summary']
            self.assertEqual(s['check_penalty'],physical_check_penalty(s['q']/100,s['b']/100))
        self.assertEqual(r['combat']['physical_check_fatigue_sensitivity'],5)
        self.assertTrue(r['combat']['fatigue_contest_penalty_enabled'])
        self.assertEqual(r['combat']['elapsed_seconds'],390)
        self.assertEqual(len(r['combat']['control_history']),15)
        self.assertEqual(self.cfg['scenarios']['combat_d_live_grapple']['grapple_encounter']['costs']['grapple']['demand'],.7)

    def test_one_universal_appendix_is_present_and_activity_card_does_not_reprint(self):
        appendix=(ROOT/'APPENDIX-UNIVERSAL-FATIGUE-TABLE.md').read_text()
        for marker in ['1 | 1 check point','4 | 1 check point','9 | 1 check point','**not observed human/horse equivalence data**','manual']:
            self.assertIn(marker,appendix)
        card=(ROOT/'MANUAL-CARD-COMBAT-D-F12.md').read_text()
        self.assertNotIn(markdown_table(),card)
        self.assertIn('FATIGUE-CONTEST-TABLE.md',card)
        html=(ROOT/'static/index.html').read_text()
        self.assertLess(html.index('SCENARIO ACTIVITY EDITOR'),html.index('REFERENCE PARAMETERS'))
        self.assertNotIn('grapple-fatigue-scale',(ROOT/'static/app.js').read_text())

if __name__=='__main__':unittest.main()
