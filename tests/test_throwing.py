import math
import unittest

from throwing import (
    EFFECTIVE_ADJACENT_THROW_THRESHOLD_YD_S,
    REFERENCE_ARM_LENGTH_INCHES,
    is_effective_adjacent_throw,
    maximum_throw_velocity_yd_s,
    reference_arm_inches,
    release_velocity_yd_s,
)


class ThrowingReferenceMathTests(unittest.TestCase):
    def test_reference_categories_and_medium_denominator(self):
        expected = {
            'Diminutive': 3.5, 'Tiny': 7, 'Small': 14, 'Medium': 28,
            'Large': 56, 'Huge': 112, 'Gargantuan': 224, 'Colossal': 448,
        }
        for name, inches in expected.items():
            with self.subTest(category=name):
                self.assertEqual(reference_arm_inches(size_category=name), inches)
        self.assertEqual(REFERENCE_ARM_LENGTH_INCHES['M'], 28.0)

    def test_measured_dimension_precedes_category_and_matches_69_inch_case(self):
        self.assertAlmostEqual(
            reference_arm_inches(height_inches=69, size_category='Small'),
            69 * 15 / 37)
        self.assertAlmostEqual(reference_arm_inches(length_inches=69), 69 * 15 / 37)
        self.assertAlmostEqual(
            reference_arm_inches(height_inches=60, length_inches=69),
            69 * 15 / 37)

    def test_requires_valid_measured_dimension_or_explicit_category(self):
        for kwargs in ({}, {'height_inches': 0}, {'height_inches': -1},
                       {'height_inches': float('nan')}, {'size_category': 'unknown'}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                reference_arm_inches(**kwargs)
        self.assertEqual(reference_arm_inches(height_inches=0, size_category='M'), 28)

    def test_medium_reference_factor_is_one_and_size_scaling_is_sqrt_two(self):
        args = dict(strength=10, throw_skill_level=1, projectile_weight_lb=5,
                    heavy_load_reference_lb=100)
        expected = 22.5 * math.exp(-((0.05 / 0.08081) ** 0.6010))
        medium = release_velocity_yd_s(size_category='Medium', **args)
        large = release_velocity_yd_s(size_category='Large', **args)
        self.assertAlmostEqual(medium, expected)
        self.assertAlmostEqual(large / medium, math.sqrt(2))

    def test_throw_skill_is_one_time_maximum_velocity_modifier(self):
        self.assertEqual(maximum_throw_velocity_yd_s(10, 0), 20)
        self.assertEqual(maximum_throw_velocity_yd_s(10, 1), 22.5)
        self.assertEqual(maximum_throw_velocity_yd_s(10, 3), 22.5)
        level_zero = release_velocity_yd_s(
            strength=10, throw_skill_level=0, projectile_weight_lb=5,
            heavy_load_reference_lb=100, size_category='M')
        level_one = release_velocity_yd_s(
            strength=10, throw_skill_level=1, projectile_weight_lb=5,
            heavy_load_reference_lb=100, size_category='M')
        level_three = release_velocity_yd_s(
            strength=10, throw_skill_level=3, projectile_weight_lb=5,
            heavy_load_reference_lb=100, size_category='M')
        self.assertAlmostEqual(level_one / level_zero, 22.5 / 20)
        self.assertEqual(level_one, level_three)

    def test_heavier_projectile_reduces_velocity_and_5_yd_s_floor(self):
        light = release_velocity_yd_s(
            strength=10, throw_skill_level=1, projectile_weight_lb=1,
            heavy_load_reference_lb=100, size_category='M')
        heavy = release_velocity_yd_s(
            strength=10, throw_skill_level=1, projectile_weight_lb=20,
            heavy_load_reference_lb=100, size_category='M')
        self.assertGreater(light, heavy)
        self.assertEqual(EFFECTIVE_ADJACENT_THROW_THRESHOLD_YD_S, 5.0)
        self.assertTrue(is_effective_adjacent_throw(5.0))
        self.assertFalse(is_effective_adjacent_throw(4.999999))

    def test_input_validation(self):
        with self.assertRaises(ValueError):
            maximum_throw_velocity_yd_s(True, 1)
        with self.assertRaises(ValueError):
            maximum_throw_velocity_yd_s(10, -1)
        for weight, heavy_reference in ((-1, 100), (float('inf'), 100), (1, 0)):
            with self.subTest(weight=weight, heavy_reference=heavy_reference):
                with self.assertRaises(ValueError):
                    release_velocity_yd_s(
                        strength=10, throw_skill_level=1,
                        projectile_weight_lb=weight,
                        heavy_load_reference_lb=heavy_reference,
                        size_category='M')
        with self.assertRaises(ValueError):
            is_effective_adjacent_throw(float('nan'))


if __name__ == '__main__':
    unittest.main()
