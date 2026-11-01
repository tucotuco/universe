"""Resolved Encounters grappling subset: real dice, action legality and R4 states."""
from copy import deepcopy
import json
import unittest
from pathlib import Path
import yaml
from workbench import simulate, validated_config
from grapple_encounter import opposed,validate, DEFAULT_COSTS, fatigue_contest_penalty, fatigue_contest_penalty
from random import Random
from universe_physical_fatigue_r4 import State, human_profile
from universe_physical_fatigue_r4 import State, human_profile

ROOT=Path(__file__).resolve().parents[1]

class ResolvedGrappleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg=yaml.safe_load((ROOT/'config.yaml').read_text())
        cls.name='combat_d_live_grapple'

    def test_standard_scenario_and_unchanged_grapple_work(self):
        g=self.cfg['scenarios'][self.name]['grapple_encounter']
        self.assertEqual([x['seconds'] for x in g['phases']],[180,30,180])
        self.assertEqual(g['costs']['grapple']['demand'],.70)
        self.assertEqual(g['costs']['grapple']['fitness_exponent'],.35)
        self.assertEqual(g['seed'],20261026)

    def test_two_bouts_with_rest_continue_through_unaffordable_actions(self):
        r=simulate(self.cfg,self.name)
        self.assertEqual(r['combat']['elapsed_seconds'],390)
        # The default seeded contest may prevent sustained Grapple effort;
        # infeasibility is guaranteed in the separate high-demand test.
        self.assertEqual([p['seconds'] for p in r['actors']['Grappler Fitness 12']['points']],[*range(391)])
        for data in r['actors'].values():
            self.assertTrue(data['summary']['completed'])
            self.assertEqual(data['summary']['total_seconds'],390)
            self.assertEqual(data['summary']['events_by_type'].get('seconds rest'),30)
            self.assertGreater(data['summary']['events_by_type'].get('grapple resolved',0),0)

    def test_dice_are_seeded_and_reproducible(self):
        a=simulate(self.cfg,self.name);b=simulate(self.cfg,self.name)
        self.assertEqual(a['combat']['event_log'],b['combat']['event_log'])
        c=deepcopy(self.cfg)
        c['scenarios'][self.name]['grapple_encounter']['seed']+=1
        d=simulate(c,self.name)
        self.assertNotEqual(a['combat']['event_log'],d['combat']['event_log'])

    def test_real_opposed_rolls_and_tie_behavior(self):
        actors={'A':{'abilities':{'strength':13,'dexterity':12},'improved_grapple':4},
                'B':{'abilities':{'strength':13,'dexterity':12},'improved_grapple':4}}
        r=opposed(Random(7),'grapple','A','B',actors,{'A':'grapple','B':'escape'})
        self.assertEqual(len(r['dice']['A']),3)
        self.assertEqual(len(r['dice']['B']),3)
        self.assertEqual(r['scores']['A'],sum(r['dice']['A'])+r['modifiers']['A'])
        self.assertEqual(r['scores']['B'],sum(r['dice']['B'])+r['modifiers']['B'])
        self.assertIsNone(r['winner']) if r['scores']['A']==r['scores']['B'] else self.assertIn(r['winner'],actors)

    def test_escape_and_break_hold_are_distinct(self):
        r=simulate(self.cfg,self.name)
        events=[e for frame in r['combat']['event_log'] for e in frame.get('events',[])]
        escapes=[e for e in events if e.get('action')=='grapple-check' and 'escape' in e.get('declared',{}).values()]
        breaks=[e for e in events if e.get('action')=='break_hold']
        self.assertTrue(escapes)
        self.assertTrue(breaks)
        self.assertTrue(all(b['check']['kind']=='break_hold' for b in breaks))
        self.assertTrue(all(e['check']['kind']=='grapple' for e in escapes))
        self.assertTrue(any(e.get('action')=='hold maintenance' for e in events))

    def test_output_changes_with_skill_and_cost_parameters(self):
        baseline=simulate(self.cfg,self.name)
        c=deepcopy(self.cfg)
        c['scenarios'][self.name]['actors']['Grappler Fitness 12']['escape_artist']=10
        changed=simulate(c,self.name)
        self.assertNotEqual(baseline['combat']['event_log'],changed['combat']['event_log'])
        c2=deepcopy(self.cfg)
        c2['scenarios'][self.name]['grapple_encounter']['costs']['grapple']['demand']=.55
        changed2=simulate(c2,self.name)
        self.assertGreater(changed2['actors']['Grappler Fitness 12']['summary']['q'],baseline['actors']['Grappler Fitness 12']['summary']['q'])

    def test_infeasible_grapple_is_a_local_action_failure_not_bout_termination(self):
        c=deepcopy(self.cfg)
        c['scenarios'][self.name]['grapple_encounter']['costs']['grapple']['demand']=.90
        r=simulate(c,self.name)
        self.assertTrue(r['combat']['had_infeasible_actions'])
        self.assertEqual(r['combat']['elapsed_seconds'],390)
        self.assertGreater(r['actors']['Grappler Fitness 12']['summary']['events_by_type'].get('infeasible grapple',0),0)
        self.assertEqual(r['actors']['Grappler Fitness 16']['summary']['total_seconds'],390)

    def test_invalid_scenario_rejected(self):
        c=deepcopy(self.cfg)
        c['scenarios'][self.name]['grapple_encounter']['phases'][1]['seconds']=90
        with self.assertRaises(ValueError):validated_config(c)
        c=deepcopy(self.cfg);c['scenarios'][self.name]['grapple_encounter']['costs']['grapple']['demand']=-0.1
        with self.assertRaises(ValueError):validated_config(c)

    def test_contest_penalty_is_derived_from_exact_r4_output_and_zero_when_fresh(self):
        prof=human_profile(12)
        self.assertEqual(fatigue_contest_penalty(State(1,1),prof),0)
        self.assertEqual(fatigue_contest_penalty(State(0,1),prof),2)
        self.assertEqual(fatigue_contest_penalty(State(0,0),prof),4)
        self.assertEqual(fatigue_contest_penalty(State(.2,1),prof),1)

    def test_same_fatigue_modifier_applies_to_touch_grab_grapple_and_break_hold(self):
        actors={'A':{'abilities':{'strength':13,'dexterity':12},'improved_grapple':4,'attack_level':2,'defense_level':2},
                'B':{'abilities':{'strength':13,'dexterity':12},'improved_grapple':4,'attack_level':2,'defense_level':2}}
        states={'A':State(.10,.70),'B':State(1,1)}
        profiles={'A':human_profile(12),'B':human_profile(12)}
        for kind in ('touch','grab','grapple','break_hold'):
            updated=opposed(Random(42),kind,'A','B',actors,{},states,profiles,5)
            plain=opposed(Random(42),kind,'A','B',actors,{})
            self.assertEqual(updated['dice'],plain['dice'])
            self.assertEqual(updated['fatigue_penalties']['A'],fatigue_contest_penalty(states['A'],profiles['A']))
            self.assertEqual(updated['fatigue_penalties']['B'],0)
            self.assertEqual(updated['scores']['B'],plain['scores']['B'])
            self.assertEqual(updated['scores']['A'],plain['scores']['A']-updated['fatigue_penalties']['A'])

    def test_two_bouts_fatigue_penalty_changes_resolved_checks_with_same_seed(self):
        base=deepcopy(self.cfg)
        g=base['scenarios'][self.name]['grapple_encounter']
        self.assertTrue(g['fatigue_contest_penalty_enabled'])
        modified=simulate(base,self.name)
        g['fatigue_contest_penalty_enabled']=False
        unmodified=simulate(base,self.name)
        self.assertEqual(modified['combat']['elapsed_seconds'],390)
        self.assertEqual(unmodified['combat']['elapsed_seconds'],390)
        self.assertEqual(modified['combat']['seed'],unmodified['combat']['seed'])
        mchecks=[e['check'] for frame in modified['combat']['event_log'] for e in frame.get('events',[]) if 'check' in e]
        bchecks=[e['check'] for frame in unmodified['combat']['event_log'] for e in frame.get('events',[]) if 'check' in e]
        self.assertTrue(any(any(v>0 for v in x['fatigue_penalties'].values()) for x in mchecks))
        self.assertTrue(all(all(v==0 for v in x['fatigue_penalties'].values()) for x in bchecks))
        self.assertNotEqual(modified['combat']['control_history'],unmodified['combat']['control_history'])
        for a in modified['actors']:
            self.assertTrue(modified['actors'][a]['summary']['completed'])
        self.assertEqual(base['scenarios'][self.name]['grapple_encounter']['costs']['grapple']['demand'],.70)

    def test_invalid_modifier_configuration_rejected(self):
        c=deepcopy(self.cfg)
        c['scenarios'][self.name]['grapple_encounter']['physical_check_fatigue_sensitivity']=-3
        with self.assertRaises(ValueError):validated_config(c)
        c=deepcopy(self.cfg)
        c['scenarios'][self.name]['grapple_encounter']['fatigue_contest_penalty_enabled']='yes'
        with self.assertRaises(ValueError):validated_config(c)

    def test_old_scripted_grappling_is_still_available(self):
        r=simulate(self.cfg,'combat_c_grapple_repeated')
        self.assertEqual(r['combat']['elapsed_seconds'],171)
        self.assertEqual(r['combat']['scheduled_seconds'],390)
        self.assertTrue(r['combat']['contests_disabled'])
        self.assertFalse(simulate(self.cfg,self.name)['combat']['contests_disabled'])

if __name__=='__main__':unittest.main()
