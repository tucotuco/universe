"""U-THROW-003: assert the safe native admission blocker and pure projection."""
import math
import unittest

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'examples'))

from native_throw_arena import build_blocked_scene, build_projection
from spatial.state import CartesianPosition
from throwing import project_drag_free_trajectory


class NativeThrowBlockerTests(unittest.TestCase):
    def test_native_choice_refuses_throw_without_registering_or_reserving(self):
        world, encounter, actor, projectile, rng, action, validation = build_blocked_scene()
        expected_rng = __import__('random').Random(141).getstate()
        self.assertFalse(validation.valid)
        self.assertEqual(len(validation.diagnostics), 1)
        self.assertIn('unsupported transactional base Action activity',
                      validation.diagnostics[0].reason)
        self.assertIsNone(world.get_event_by_id(action.id))
        self.assertEqual(encounter.pending_action_list, [])
        self.assertEqual(encounter.finished_action_list, [])
        self.assertEqual(encounter.active_reservations, ())
        self.assertEqual(encounter.__dict__.get('_atomic_interval_history', []), [])
        self.assertEqual(projectile.get_position(), CartesianPosition(0, 0, 0.9))
        self.assertIn(projectile.id, actor.possessions)
        self.assertEqual(encounter.last_processed_boundary, 0)
        self.assertEqual(encounter.time, 0)
        self.assertEqual(rng.state, expected_rng)

    def test_projection_uses_si_ballistics_and_exact_positive_landing_root(self):
        arm, release_height, speed_yd_s, trajectory = build_projection()
        speed_m_s = speed_yd_s * 0.9144
        self.assertAlmostEqual(arm, 69 * 15 / 37)
        self.assertAlmostEqual(release_height, 69 * 0.0254)
        self.assertAlmostEqual(math.sqrt(sum(v*v for v in trajectory.velocity_m_s)), speed_m_s)
        self.assertGreater(trajectory.flight_time_s, 0)
        self.assertEqual(trajectory.gravity_m_s2, 10.0)
        self.assertAlmostEqual(trajectory.landing_position.z, 0)
        self.assertAlmostEqual(trajectory.landing_position.x,
                               trajectory.velocity_m_s[0] * trajectory.flight_time_s)
        self.assertAlmostEqual(trajectory.horizontal_range_yd,
                               trajectory.horizontal_range_m / 0.9144)
        apex = trajectory.position_at(1.0)
        self.assertGreater(apex.z, release_height)
        self.assertEqual(trajectory.position_at(trajectory.flight_time_s),
                         trajectory.landing_position)
        self.assertEqual(build_projection()[3], trajectory)
        with self.assertRaisesRegex(ValueError, 'after projected landing'):
            trajectory.position_at(trajectory.flight_time_s + 0.01)

    def test_projection_validation_fails_closed_for_missing_or_unsupported_inputs(self):
        common = dict(release_position=CartesianPosition(0, 0, 1.75),
                      landing_elevation_m=0, elevation_degrees=45)
        for changes in (
            {'release_velocity_yd_s': 0},
            {'release_velocity_yd_s': -1},
            {'release_velocity_yd_s': float('inf')},
            {'release_velocity_yd_s': 10, 'release_position': None},
            {'release_velocity_yd_s': 10, 'landing_elevation_m': float('nan')},
            {'release_velocity_yd_s': 10, 'elevation_degrees': float('nan')},
            {'release_velocity_yd_s': 10, 'elevation_degrees': 91},
            {'release_velocity_yd_s': 10, 'elevation_degrees': -1},
            {'release_velocity_yd_s': 10, 'azimuth_degrees': float('inf')},
            {'release_velocity_yd_s': 10,
             'release_position': CartesianPosition(0, 0, 0)},
        ):
            args = dict(common)
            args.update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                project_drag_free_trajectory(**args)


if __name__ == '__main__':
    unittest.main()
