"""Demand-driven planetary refinement and an honest preview/commit boundary."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'examples'))
from planetary_requirements import PlanetaryDesign
from planetary_designer import DesignerApp, make_handler
from http.server import ThreadingHTTPServer
from threading import Thread
from urllib.request import Request, urlopen
from urllib.error import HTTPError


class PlanetaryRequirementsTests(unittest.TestCase):
    def setUp(self):
        self.cfg = json.loads((ROOT / 'examples' / 'planetary_design_conditions.json').read_text())
        self.design = PlanetaryDesign(**self.cfg)

    def test_inspection_does_not_resolve_or_mutate(self):
        before = self.design.export()
        answer = self.design.inspect('time_to_sunset_hours')
        self.assertIsNone(answer['answer'])
        self.assertEqual(set(answer['missing']), {'solar_day_hours', 'axial_tilt_deg'})
        self.assertEqual(before, self.design.export())

    def test_candidate_is_consistent_with_declared_world_conditions(self):
        candidate = self.design.preview()
        self.assertEqual(candidate.newly_realized, ('solar_day_hours', 'axial_tilt_deg'))
        self.assertAlmostEqual(candidate.answer['solar_day_hours'], 30, delta=.2)
        self.assertAlmostEqual(candidate.answer['daylight_hours'], 11.45, delta=.45)
        self.assertEqual(len(self.design.known), 2)  # still just the initially known facts

    def test_preview_reproducible_but_not_authoritative(self):
        first = self.design.preview(candidate_index=11)
        second = self.design.preview(candidate_index=11)
        alternate = self.design.preview(candidate_index=12)
        self.assertEqual(first, second)
        self.assertNotEqual(first.parameters, alternate.parameters)
        self.assertEqual(self.design.revision, 2)

    def test_commit_realizes_only_missing_required_parameters(self):
        p = self.design.preview()
        result = self.design.commit(p)
        self.assertEqual(set(result), {'solar_day_hours', 'axial_tilt_deg'})
        self.assertNotIn('orbital_year_days', self.design.known)
        self.assertNotIn('sidereal_rotation_hours', self.design.known)
        self.assertEqual(self.design.inspect('time_to_sunset_hours')['missing'], [])
        self.assertEqual(self.design.inspect('time_to_sunset_hours')['answer'], p.answer)

    def test_stale_candidate_rejected_without_mutation(self):
        p = self.design.preview()
        self.design.add_condition({'metric': 'solar_day_hours', 'target':30, 'tolerance':.3})
        before = self.design.export()
        with self.assertRaisesRegex(ValueError, 'Stale proposal'):
            self.design.commit(p)
        self.assertEqual(self.design.export(), before)

    def test_incompatible_trials_do_not_change_reality(self):
        before = self.design.export()
        with self.assertRaisesRegex(ValueError, 'No admissible candidate'):
            self.design.preview(trial={'axial_tilt_deg':0, 'solar_day_hours':30}, max_attempts=1)
        self.assertEqual(self.design.export(), before)

    def test_adding_impossible_condition_rejected_atomically(self):
        self.design.commit(self.design.preview())
        before = self.design.export()
        with self.assertRaisesRegex(ValueError, 'Contradicts'):
            self.design.add_condition({'metric':'solar_day_hours','target':80,'tolerance':0})
        self.assertEqual(before, self.design.export())

    def test_trial_values_respected_and_committed_only_if_needed(self):
        p = self.design.preview(trial={'solar_day_hours':30, 'axial_tilt_deg':23})
        self.assertEqual(dict(p.parameters)['axial_tilt_deg'], 23)
        self.design.commit(p)
        self.assertAlmostEqual(self.design.known['axial_tilt_deg'], 23)
        self.assertEqual(len(self.design.commits), 1)

    def test_later_epoch_demand_requires_year_without_advancing_every_day(self):
        self.design.commit(self.design.preview())
        query = self.design.inspect('daylight_hours', time_s=10_000_000)
        self.assertEqual(query['missing'], ['orbital_year_days'])
        p = self.design.preview('daylight_hours', time_s=10_000_000)
        self.assertEqual(p.newly_realized, ('orbital_year_days',))
        self.design.commit(p)
        self.assertEqual(self.design.inspect('daylight_hours', time_s=10_000_000)['missing'], [])
        self.assertEqual(len(self.design.commits), 2)

    def test_different_latitude_uses_same_committed_world(self):
        self.design.commit(self.design.preview())
        revision = self.design.revision
        south = self.design.inspect('daylight_hours', -40)['answer']['daylight_hours']
        north = self.design.inspect('daylight_hours', 40)['answer']['daylight_hours']
        self.assertGreater(south, north)
        self.assertAlmostEqual(south + north, self.design.known['solar_day_hours'], places=8)
        self.assertEqual(revision, self.design.revision)

    def test_prograde_synodic_day_can_be_derived_from_rotation_and_year(self):
        d = PlanetaryDesign(known={'sidereal_rotation_hours':23.9344696,
                                   'orbital_year_days':365.256,
                                   'axial_tilt_deg':23.44,
                                   'season_phase_deg':0,
                                   'hour_angle_deg':0})
        a = d.inspect('time_to_sunset_hours', 40)['answer']
        self.assertAlmostEqual(a['solar_day_hours'], 24, delta=.02)
        self.assertNotIn('solar_day_hours', d.known)  # no unnecessary commitment

    def test_retrograde_or_inconsistent_rates_rejected(self):
        with self.assertRaisesRegex(ValueError, 'prograde'):
            PlanetaryDesign(known={'sidereal_rotation_hours':100, 'orbital_year_days':2})
        with self.assertRaisesRegex(ValueError, 'contradicts'):
            PlanetaryDesign(known={'sidereal_rotation_hours':23.9344696,
                                   'orbital_year_days':365.256, 'solar_day_hours':30})

    def test_polar_day_has_no_fictional_sunset(self):
        d = PlanetaryDesign(known={'solar_day_hours':24,'axial_tilt_deg':25,
                                  'season_phase_deg':180,'hour_angle_deg':0})
        p = d.inspect('time_to_sunset_hours',latitude_deg=80)['answer']
        self.assertIsNone(p['time_to_sunset_hours'])
        self.assertTrue(p['sunset_status'].startswith('polar_day'))

    def test_export_restore_keeps_committed_state_and_conditions(self):
        self.design.commit(self.design.preview())
        data = json.loads(json.dumps(self.design.export()))
        d = PlanetaryDesign.restore(data)
        self.assertEqual(d.export(), data)
        self.assertEqual(d.inspect('time_to_sunset_hours'), self.design.inspect('time_to_sunset_hours'))

    def test_world_rejects_invalid_inputs(self):
        with self.assertRaises(ValueError):
            self.design.inspect('orbital_chaos')
        with self.assertRaises(ValueError):
            self.design.inspect('daylight_hours', 91)
        with self.assertRaises(ValueError):
            self.design.preview(trial={'axial_tilt_deg':float('nan')})
        with self.assertRaises(ValueError):
            self.design.add_condition({'metric':'daylight_hours','target':10,'tolerance':-1})

    def test_inspection_excludes_local_hour_angle_for_daylength(self):
        d = PlanetaryDesign(known={'solar_day_hours':30,'axial_tilt_deg':20,'season_phase_deg':0})
        self.assertEqual(d.inspect('daylight_hours')['missing'], [])
        self.assertEqual(d.inspect('time_to_sunset_hours')['missing'], ['hour_angle_deg'])


class DesignerHttpTests(unittest.TestCase):
    def setUp(self):
        d = PlanetaryDesign(known={'season_phase_deg':0, 'hour_angle_deg':40})
        self.httpd = ThreadingHTTPServer(('127.0.0.1', 0), make_handler(DesignerApp(d)))
        self.thread = Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.root = f'http://127.0.0.1:{self.httpd.server_address[1]}'

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(3)

    def post(self, path, obj, origin=None):
        headers = {'Content-Type':'application/json'}
        if origin: headers['Origin'] = origin
        req = Request(self.root+path, data=json.dumps(obj).encode(), headers=headers)
        return json.load(urlopen(req, timeout=2))

    def test_http_inspect_preview_commit_and_export(self):
        initial = json.load(urlopen(self.root+'/api/state'))
        self.assertNotIn('solar_day_hours', initial['known'])
        html = urlopen(self.root).read().decode()
        self.assertIn('World conditions laboratory', html)
        self.assertIn('Daylight through a modeled year', html)
        preview = self.post('/api/preview', {'candidate_index':1})
        self.assertIn('solar_day_hours', preview['newly_realized'])
        self.assertNotIn('solar_day_hours', json.load(urlopen(self.root+'/api/state'))['known'])
        saved = self.post('/api/commit', {})
        self.assertIn('solar_day_hours', saved['world']['known'])

    def test_cross_origin_request_blocked_before_mutation(self):
        with self.assertRaises(HTTPError) as err:
            self.post('/api/condition', {'metric':'solar_day_hours','target':30,'tolerance':.2},
                      origin='https://untrusted.example')
        self.assertEqual(err.exception.code, 403)
        self.assertEqual(json.load(urlopen(self.root+'/api/state'))['conditions'], [])


if __name__ == '__main__':
    unittest.main()
