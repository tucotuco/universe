"""Native twelve-way facing convention for the flat-top Arena hex lattice.

Facing indices advance counter-clockwise from world +x in 30 degree steps.
Even indices point at a hex vertex; odd indices point at a side normal.
The adopted Encounter rules define the sectors, while this zero axis and
encoding are local implementation conventions.
"""

from __future__ import annotations

from enum import Enum
import math


FACING_TIE_TOLERANCE_STEPS = 16.0 * math.ulp(1.0)


class FacingSector(str, Enum):
    FRONT = "front"
    NON_FORWARD = "non_forward"


def validate_facing(value: int) -> int:
    if type(value) is not int or not 0 <= value < 12:
        raise ValueError("hex facing must be an integer from 0 through 11")
    return value


def facing_angle(facing: int) -> float:
    return math.radians(30.0 * validate_facing(facing))


def facing_vector(facing: int) -> tuple[float, float]:
    angle = facing_angle(facing)
    return math.cos(angle), math.sin(angle)


def nearest_facing(vector: tuple[float, float, float]) -> int:
    """Return the nearest heading; midpoint ties choose the smaller index.

    The tolerance is measured in 30-degree facing steps and is limited to 16
    binary64 ULPs at 1.0. It only stabilizes a mathematically exact midpoint
    represented with floating-point trigonometry.
    """
    if type(vector) not in (tuple, list) or len(vector) != 3:
        raise ValueError("nearest facing requires a three-component Cartesian vector")
    x, y = vector[0], vector[1]
    if (isinstance(x, bool) or isinstance(y, bool)
            or not isinstance(x, (int, float)) or not isinstance(y, (int, float))
            or not math.isfinite(x) or not math.isfinite(y) or (x == 0 and y == 0)):
        raise ValueError("nearest facing requires a finite, nonzero horizontal vector")
    steps = (math.atan2(y, x) % (2.0 * math.pi)) / (math.pi / 6.0)
    lower = math.floor(steps)
    fraction = steps - lower
    upper_index = (lower + 1) % 12
    lower_index = lower % 12
    if abs(fraction - 0.5) <= FACING_TIE_TOLERANCE_STEPS:
        return min(lower_index, upper_index)
    return lower_index if fraction < 0.5 else upper_index


def classify_vector(facing: int, vector: tuple[float, float, float]) -> FacingSector:
    """Front includes both adjacent-heading boundaries; all else is non-forward."""
    fx, fy = facing_vector(facing)
    dx, dy = vector[0], vector[1]
    magnitude = math.hypot(dx, dy)
    if not math.isfinite(magnitude) or magnitude == 0:
        raise ValueError("facing classification requires a finite horizontal vector")
    # Dot-product comparison makes both inclusive ±30° boundaries stable.
    dot = (fx * dx + fy * dy) / magnitude
    boundary = math.sqrt(3.0) / 2.0
    tolerance = 16.0 * math.ulp(1.0)
    return (FacingSector.FRONT if dot + tolerance >= boundary
            else FacingSector.NON_FORWARD)
