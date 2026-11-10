import unittest

from measured_values import is_truncated_measurement, truncate_measurement
from object import ObjectDefinition
from spatial.state import CartesianPosition, SpatialState


class TestMeasuredValues(unittest.TestCase):
    def test_decimal_truncation_is_toward_zero_and_threshold_safe(self):
        self.assertEqual(truncate_measurement(70.999), 70.99)
        self.assertEqual(truncate_measurement(150.678), 150.67)
        self.assertEqual(truncate_measurement(-1.239), -1.23)
        self.assertEqual(truncate_measurement(-0.009), 0.0)
        self.assertEqual(truncate_measurement(62.720001220703125), 62.72)
        self.assertTrue(is_truncated_measurement(70.99))
        self.assertFalse(is_truncated_measurement(70.999))

    def test_definition_measures_and_every_spatial_state_assignment_truncate(self):
        definition = ObjectDefinition("Test", 70.999, 1.239, 2.349, 150.678,
                                      0, 0, 1)
        self.assertEqual((definition.length, definition.width,
                          definition.height, definition.weight),
                         (70.99, 1.23, 2.34, 150.67))
        state = SpatialState(CartesianPosition(-1.239, 70.999, 0.009))
        self.assertEqual(state.position.as_tuple(), (-1.23, 70.99, 0.0))
        state.position = CartesianPosition(1.239, -70.999, 0.018)
        self.assertEqual(state.position.as_tuple(), (1.23, -70.99, 0.01))


if __name__ == "__main__":
    unittest.main()
