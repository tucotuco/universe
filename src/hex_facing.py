"""Native twelve-way facing convention for the flat-top Arena hex lattice.

Facing indices advance counter-clockwise from world +x in 30 degree steps.
Even indices point at a hex vertex; odd indices point at a side normal.
The adopted Encounter rules define the sectors, while this zero axis and
encoding are local implementation conventions.
"""

from __future__ import annotations

from enum import Enum
import math


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
