"""Cross-scale invariants of the first planetary ephemeris experiment."""

import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'examples'))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from planetary_first_light import from_config
from planetary_system import G, KeplerOrbit, Moon, Planet, PlanetarySystem, Star

CONFIG = Path(__file__).resolve().parents[1] / 'examples' / 'planetary_analogue.json'


class OrbitTests(unittest.TestCase):
    def test_circular_orbit_repeats(self):
        orbit = KeplerOrbit(2e8, 1000)
        self.assertAlmostEqual(orbit.position_at(0)[0], 2e8, delta=1e-5)
        self.assertAlmostEqual(orbit.position_at(250)[1], 2e8, delta=1e-5)
        for a, b in zip(orbit.position_at(13), orbit.position_at(1013)):
            self.assertAlmostEqual(a, b, delta=1e-4)

    def test_elliptic_apsides(self):
        orbit = KeplerOrbit(1e8, 1000, 0.3)
        self.assertAlmostEqual(orbit.position_at(0)[0], 7e7)
        self.assertAlmostEqual(orbit.position_at(500)[0], -1.3e8)

    def test_inclination_rotates_orbit_into_three_dimensions(self):
        orbit = KeplerOrbit(1e8, 1000, inclination_rad=math.pi / 2)
        self.assertAlmostEqual(orbit.position_at(250)[1], 0, delta=1e-7)
        self.assertAlmostEqual(orbit.position_at(250)[2], 1e8, delta=1e-7)

    def test_rejects_invalid_orbits_and_times(self):
        for value in (-0.1, 1.0, math.inf):
            with self.assertRaises(ValueError):
                KeplerOrbit(1e8, 1000, eccentricity=value)
        with self.assertRaises(ValueError):
            KeplerOrbit(1e8, 1000).position_at(float('nan'))


class SurfaceSkyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.system = from_config(CONFIG)
        cls.year = cls.system.planet.orbit.period_s

    def test_config_matches_approximate_terrestrial_solar_day(self):
        hours = self.system.planet.approximate_solar_day_s() / 3600
        self.assertAlmostEqual(hours, 24, delta=0.05)

    def test_northern_winter_and_summer_daylength(self):
        winter = self.system.state_at(0, 40, 0)
        summer = self.system.state_at(self.year / 2, 40, 0)
        self.assertLess(winter.approximate_daylight_hours, 10)
        self.assertGreater(summer.approximate_daylight_hours, 14)
        self.assertLess(winter.sun_declination_deg, -20)
        self.assertGreater(summer.sun_declination_deg, 20)

    def test_hemispheres_have_opposite_seasons(self):
        n = self.system.state_at(0, 40, 0)
        s = self.system.state_at(0, -40, 0)
        self.assertLess(n.approximate_daylight_hours, s.approximate_daylight_hours)

    def test_polar_day_and_night(self):
        self.assertAlmostEqual(self.system.state_at(0, 85, 0).approximate_daylight_hours, 0)
        self.assertGreater(self.system.state_at(self.year / 2, 85, 0).approximate_daylight_hours, 23)

    def test_local_rotation_changes_daylight(self):
        noon = self.system.state_at(0, 0, 0)
        night = self.system.state_at(self.system.planet.rotation_period_s / 2, 0, 0)
        self.assertGreater(noon.sun_altitude_deg, 0)
        self.assertLess(night.sun_altitude_deg, 0)
        self.assertGreater(noon.surface_insolation_w_m2, 0)
        self.assertEqual(night.surface_insolation_w_m2, 0)

    def test_new_and_full_moon_geometry(self):
        new = self.system.state_at(0, 0, 0).moons[0]
        full = self.system.state_at(self.system.moons[0].orbit.period_s / 2, 0, 0).moons[0]
        self.assertLess(new.illuminated_fraction, 0.02)
        self.assertGreater(full.illuminated_fraction, 0.96)

    def test_tide_forcing_has_inverse_cube_distance_dependence(self):
        system = self.system
        moon = system.moons[0]
        changed = Moon(moon.name, moon.mass_kg, moon.radius_m,
                       KeplerOrbit(moon.orbit.semi_major_axis_m * 2,
                                   moon.orbit.period_s * math.sqrt(8), 0,
                                   mean_anomaly_at_epoch_rad=math.pi))
        base_orbit = KeplerOrbit(moon.orbit.semi_major_axis_m, moon.orbit.period_s,
                                0, mean_anomaly_at_epoch_rad=math.pi)
        base = PlanetarySystem(system.star, system.planet,
                              (Moon(moon.name, moon.mass_kg, moon.radius_m, base_orbit),))
        distant = PlanetarySystem(system.star, system.planet, (changed,))
        here = base.state_at(0, 0, 0).moons[0].tidal_potential_m2_s2
        there = distant.state_at(0, 0, 0).moons[0].tidal_potential_m2_s2
        self.assertAlmostEqual(here / there, 8.0, delta=1e-5)

    def test_queries_are_reproducible_regardless_of_order(self):
        expected = self.system.state_at(1e6, 43.5, -71.25)
        self.system.state_at(20, -80, 178)
        self.system.state_at(3e7, 75, 12)
        self.assertEqual(self.system.state_at(1e6, 43.5, -71.25), expected)

    def test_rejects_physically_incompatible_orbital_period(self):
        with self.assertRaisesRegex(ValueError, "incompatible"):
            PlanetarySystem(Star('Star', 1e30, 1e26),
                            Planet('Planet', 5e24, 6e6,
                                   KeplerOrbit(1e11, 1e6), 85000, 0.0))

    def test_rejects_invalid_surface_coordinate(self):
        for latitude in (-91, 91, float('nan')):
            with self.assertRaises(ValueError):
                self.system.state_at(0, latitude, 0)

    def test_no_moon_system_and_equatorial_zero_tilt(self):
        system = PlanetarySystem(Star('Star', 1e30, 1e26),
                                 Planet('Planet', 5e24, 6e6, KeplerOrbit(1e11, 24320691.6),
                                        85000, 0.0))
        sky = system.state_at(0, 0, 0)
        self.assertEqual(sky.moons, ())
        self.assertAlmostEqual(sky.approximate_daylight_hours / sky.approximate_solar_day_hours, 0.5)
        self.assertEqual(sky.total_tidal_potential_m2_s2, sky.stellar_tidal_potential_m2_s2)


if __name__ == '__main__':
    unittest.main()
