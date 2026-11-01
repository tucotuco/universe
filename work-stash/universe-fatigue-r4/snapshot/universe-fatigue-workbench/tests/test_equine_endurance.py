"""Objective-based equine endurance regression/acceptance tests."""
import copy
from pathlib import Path
import unittest
import yaml
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from workbench import simulate,validated_config,physical_demand

class TestEquine160km(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg=yaml.safe_load((Path(__file__).resolve().parents[1]/'config.yaml').read_text())

    @staticmethod
    def speed(cfg,kph):
        for actor in cfg['scenarios']['equine_160km']['actors'].values():
            for segment in actor['segments']:
                if 'distance_km' in segment:segment['speed_kmh']=kph

    def test_reference_course_and_feasible_pace(self):
        r=simulate(self.cfg,'equine_160km')
        o=r['objective']
        self.assertEqual(o['distance_km'],160)
        self.assertEqual(o['distance_reached_km'],160)
        self.assertTrue(o['mount_and_rider_feasible'])
        self.assertAlmostEqual(o['elapsed_hours'],12.912,places=2)
        self.assertIn('not modeled',o['vet_clearance'])
        self.assertEqual(len(r['actors']['Endurance horse']['summary']['checkpoints']),6)
        self.assertLess(r['actors']['Endurance horse']['summary']['b'],70)

    def test_speed_past_capacity_fails_without_slack(self):
        c=copy.deepcopy(self.cfg);self.speed(c,18)
        r=simulate(c,'equine_160km');o=r['objective']
        self.assertFalse(o['mount_and_rider_feasible'])
        self.assertLess(o['distance_reached_km'],160)
        self.assertIn('infeasible',o['reason'])
        self.assertEqual(r['actors']['Endurance horse']['summary']['schedule_delay_seconds'],0)

    def test_lower_fitness_fails_same_external_ride(self):
        c=copy.deepcopy(self.cfg)
        c['scenarios']['equine_160km']['actors']['Endurance horse']['fitness']=14
        r=simulate(c,'equine_160km')
        self.assertFalse(r['objective']['mount_and_rider_feasible'])
        self.assertLess(r['objective']['distance_reached_km'],160)

    def test_lower_speed_does_not_ignore_deadline(self):
        c=copy.deepcopy(self.cfg);self.speed(c,12)
        o=simulate(c,'equine_160km')['objective']
        self.assertEqual(o['distance_reached_km'],160)
        self.assertFalse(o['mount_and_rider_feasible'])
        self.assertEqual(o['reason'],'deadline exceeded')

    def test_rest_held_then_propagates_to_both_actors(self):
        c=copy.deepcopy(self.cfg)
        for actor in c['scenarios']['equine_160km']['actors'].values():
            actor['segments'][1]['seconds']=3000
        a=simulate(c,'equine_160km')
        self.assertTrue(a['objective']['mount_and_rider_feasible'])
        self.assertAlmostEqual(a['objective']['elapsed_hours'],12.912+10/60,places=2)
        one,two=a['actors'].values()
        self.assertAlmostEqual(one['summary']['total_seconds'],two['summary']['total_seconds'],places=2)

    def test_reject_joint_schedule_disagreement(self):
        c=copy.deepcopy(self.cfg)
        c['scenarios']['equine_160km']['actors']['Rider']['segments'][0]['speed_kmh']=15
        with self.assertRaisesRegex(ValueError,'share journey schedule'):validated_config(c)

    def test_reject_missing_required_hold(self):
        c=copy.deepcopy(self.cfg)
        for actor in c['scenarios']['equine_160km']['actors'].values():
            actor['segments'][9]['seconds']=25*60
        with self.assertRaisesRegex(ValueError,'hold'):validated_config(c)

    def test_reject_fixed_work_escape(self):
        c=copy.deepcopy(self.cfg)
        c['scenarios']['equine_160km']['actors']['Endurance horse']['segments'][0]['execution']='fixed_work'
        with self.assertRaisesRegex(ValueError,'fixed pace'):validated_config(c)

    def test_faster_riding_requires_more_relative_effort(self):
        c=self.cfg;horse=c['scenarios']['equine_160km']['actors']['Endurance horse']
        original=physical_demand(c,horse,horse['segments'][0])
        faster={**horse['segments'][0],'speed_kmh':18}
        self.assertGreater(physical_demand(c,horse,faster),original)

if __name__=='__main__':unittest.main()

class TestSharedStop(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg=yaml.safe_load((Path(__file__).resolve().parents[1]/'config.yaml').read_text())

    def test_ride_and_rider_end_same_time_when_horse_fails(self):
        c=copy.deepcopy(self.cfg)
        for actor in c['scenarios']['equine_160km']['actors'].values():
            for segment in actor['segments']:
                if 'distance_km' in segment:segment['speed_kmh']=19
        r=simulate(c,'equine_160km')
        horse=r['actors']['Endurance horse']['summary']
        rider=r['actors']['Rider']['summary']
        self.assertFalse(r['objective']['mount_and_rider_feasible'])
        self.assertAlmostEqual(horse['total_seconds'],rider['total_seconds'],delta=.01)
        self.assertAlmostEqual(horse['distance_km'],rider['distance_km'],delta=.01)
        self.assertTrue(rider['interrupted_by_joint_failure'])
