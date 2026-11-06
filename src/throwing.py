"""Pure reference throwing-velocity calculations.

This module does not schedule or resolve a Throw Action. It implements the
adopted smooth velocity equation for callers that already supply the
projectile's weight and the Being's heavy-load reference.
"""
from __future__ import annotations

import math

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
