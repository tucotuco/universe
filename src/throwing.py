"""Pure reference throwing-velocity calculations.

This module does not schedule or resolve a Throw Action. It implements the
adopted smooth velocity equation for callers that already supply the
projectile's weight and the Being's heavy-load reference.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from spatial.state import CartesianPosition
from melee_combat import reference_arm_length_inches


REFERENCE_ARM_LENGTH_INCHES = {
    'D': 3.5,
    'T': 7.0,
    'S': 14.0,
    'M': 28.0,
    'L': 56.0,
    'H': 112.0,
    'G': 224.0,
    'C': 448.0,
}
_CATEGORY_NAMES = {
    'diminutive': 'D',
    'tiny': 'T',
    'small': 'S',
    'medium': 'M',
    'large': 'L',
    'huge': 'H',
    'gargantuan': 'G',
    'colossal': 'C',
}
HEAVY_LOAD_FRACTION = 0.08081
WEIGHT_RESPONSE_EXPONENT = 0.6010
EFFECTIVE_ADJACENT_THROW_THRESHOLD_YD_S = 5.0
REFERENCE_ARM_DENOMINATOR_INCHES = 28.0


def _finite_number(value, label, *, positive=False, nonnegative=False):
    if type(value) not in (int, float):
        raise ValueError(f'{label} must be a finite numeric value')
    try:
        result = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValueError(f'{label} must be a finite numeric value') from exc
    if (not math.isfinite(result)
            or (positive and result <= 0)
            or (nonnegative and result < 0)):
        qualifier = 'positive' if positive else 'nonnegative' if nonnegative else 'finite'
        raise ValueError(f'{label} must be finite and {qualifier}')
    return result


def _throw_skill_modifier(throw_skill_level):
    if type(throw_skill_level) is not int or throw_skill_level < 0:
        raise ValueError('Throw skill level must be a nonnegative integer')
    return 1 if throw_skill_level >= 1 else 0


def maximum_throw_velocity_yd_s(strength, throw_skill_level):
    """Return the adopted maximum velocity in yards/second.

    Throw skill contributes a one-time +1 modifier at any acquired level; its
    numeric level does not repeatedly increase maximum velocity.
    """
    strength = _finite_number(strength, 'Strength', positive=True)
    modifier = _throw_skill_modifier(throw_skill_level)
    return 5.0 * (strength + modifier - 2.0) / 2.0


def reference_arm_inches(*, height_inches=None, length_inches=None,
                         size_category=None):
    """Return the measured reference arm or an explicitly known category value.

    Full category names and the existing one-letter category codes are
    accepted. No category is inferred from geometry or an unimplemented
    native category stub. Positive measured dimensions take precedence.
    """
    if isinstance(size_category, str):
        category = _CATEGORY_NAMES.get(size_category.strip().lower(),
                                       size_category.strip().upper())
    else:
        category = size_category
    return reference_arm_length_inches(
        height_inches=height_inches,
        length_inches=length_inches,
        size_category=category)


def release_velocity_yd_s(*, strength, throw_skill_level,
                          projectile_weight_lb, heavy_load_reference_lb,
                          height_inches=None, length_inches=None,
                          size_category=None):
    """Return smooth-model projectile release speed in yards/second.

    The supplied heavy-load value is only the equation's historical numeric
    normalizer. This function does not apply the separate absolute throwability
    limit, trajectory calculation, or any Throw Action semantics.
    """
    projectile_weight_lb = _finite_number(
        projectile_weight_lb, 'projectile weight', nonnegative=True)
    heavy_load_reference_lb = _finite_number(
        heavy_load_reference_lb, 'heavy-load reference', positive=True)
    arm_inches = reference_arm_inches(
        height_inches=height_inches,
        length_inches=length_inches,
        size_category=size_category)
    maximum = maximum_throw_velocity_yd_s(strength, throw_skill_level)
    ratio = projectile_weight_lb / heavy_load_reference_lb
    try:
        weight_exponent = (ratio / HEAVY_LOAD_FRACTION) ** WEIGHT_RESPONSE_EXPONENT
    except OverflowError:
        weight_exponent = math.inf
    weight_factor = math.exp(-weight_exponent)
    arm_factor = math.sqrt(arm_inches / REFERENCE_ARM_DENOMINATOR_INCHES)
    return maximum * weight_factor * arm_factor


def is_effective_adjacent_throw(release_velocity_yd_s_value):
    """Whether release velocity meets the adopted 5 yd/s adjacent-hex floor."""
    velocity = _finite_number(release_velocity_yd_s_value, 'release velocity')
    return velocity >= EFFECTIVE_ADJACENT_THROW_THRESHOLD_YD_S


@dataclass(frozen=True)
class DragFreeTrajectoryProjection:
    """Pure flight projection; it is not authoritative Encounter state."""

    release_velocity_yd_s: float
    velocity_m_s: tuple
    release_position: CartesianPosition
    landing_position: CartesianPosition
    flight_time_s: float
    horizontal_range_m: float
    horizontal_range_yd: float
    gravity_m_s2: float = field(default=10.0, init=False)

    def position_at(self, elapsed_s):
        """Return projected position from release through (not after) impact."""
        elapsed_s = _finite_number(elapsed_s, 'elapsed flight time', nonnegative=True)
        if elapsed_s > self.flight_time_s:
            raise ValueError('elapsed time is after projected landing')
        if elapsed_s == self.flight_time_s:
            return self.landing_position
        vx, vy, vz = self.velocity_m_s
        origin = self.release_position
        return CartesianPosition(
            origin.x + vx * elapsed_s,
            origin.y + vy * elapsed_s,
            origin.z + vz * elapsed_s - 0.5 * self.gravity_m_s2 * elapsed_s ** 2,
        )


def project_drag_free_trajectory(*, release_velocity_yd_s, release_position,
                                 landing_elevation_m, elevation_degrees,
                                 azimuth_degrees=0.0):
    """Project an authored point-mass launch onto a flat horizontal plane.

    Inputs are explicit scenario/calculation values. Coordinates and trajectory
    state use meters; the supplied velocity and reported horizontal range use
    yards/second and yards respectively. No collision, drag, wind, damage,
    bounce, RNG, or authoritative mutation is modeled.
    """
    release_velocity_yd_s = _finite_number(
        release_velocity_yd_s, 'release velocity', positive=True)
    if type(release_position) is not CartesianPosition:
        raise ValueError('release_position must be a native CartesianPosition in meters')
    landing_elevation_m = _finite_number(landing_elevation_m, 'landing elevation')
    elevation_degrees = _finite_number(elevation_degrees, 'elevation angle', nonnegative=True)
    azimuth_degrees = _finite_number(azimuth_degrees, 'azimuth angle')
    if elevation_degrees > 90.0:
        raise ValueError('elevation angle must be in the supported range 0..90 degrees')
    height = release_position.z - landing_elevation_m
    if height <= 0:
        raise ValueError('release point must be above the flat landing plane')

    speed_m_s = release_velocity_yd_s * 0.9144
    elevation = math.radians(elevation_degrees)
    azimuth = math.radians(azimuth_degrees)
    horizontal = speed_m_s * math.cos(elevation)
    velocity = (horizontal * math.cos(azimuth),
                horizontal * math.sin(azimuth),
                speed_m_s * math.sin(elevation))
    gravity = 10.0
    vz = velocity[2]
    flight_time = (vz + math.sqrt(vz * vz + 2.0 * gravity * height)) / gravity
    dx, dy = velocity[0] * flight_time, velocity[1] * flight_time
    landing = CartesianPosition(release_position.x + dx,
                                release_position.y + dy,
                                landing_elevation_m)
    horizontal_range_m = math.hypot(dx, dy)
    return DragFreeTrajectoryProjection(
        release_velocity_yd_s=release_velocity_yd_s,
        velocity_m_s=velocity,
        release_position=release_position,
        landing_position=landing,
        flight_time_s=flight_time,
        horizontal_range_m=horizontal_range_m,
        horizontal_range_yd=horizontal_range_m / 0.9144,
    )
