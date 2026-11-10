#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Simple physical extents in Universe's continuous Cartesian space.

These primitives are independent of planetary cells and Encounter overlays.
Their reference point is the owning Entity's authoritative global position.
AxisAlignedBox axes currently follow the global frame; rotating bodies and
composite shapes are deliberately deferred.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
import math
from typing import Optional, Tuple

from spatial.state import CartesianPosition


SegmentInterval = Tuple[float, float]  # entry/exit fractions along a finite segment


def _positive_finite(value, name):
    try:
        value = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise TypeError(f"{name} must be numeric") from exc
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError(f"{name} must be finite and positive")
    from measured_values import truncate_measurement
    value = truncate_measurement(value)
    if value <= 0.0:
        raise ValueError(f"{name} is too small for authoritative hundredth-unit precision")
    return value


def _point(value, name):
    if not isinstance(value, CartesianPosition):
        raise TypeError(f"{name} must be a CartesianPosition")
    return value


@dataclass(frozen=True)
class Bounds3D:
    """World-axis-aligned bounding bounds, useful for candidate indexing."""

    minimum: CartesianPosition
    maximum: CartesianPosition

    def __post_init__(self):
        _point(self.minimum, "minimum")
        _point(self.maximum, "maximum")
        if any(low > high for low, high in zip(self.minimum.as_tuple(), self.maximum.as_tuple())):
            raise ValueError("minimum must not exceed maximum")

    def contains(self, point: CartesianPosition) -> bool:
        _point(point, "point")
        return all(low <= x <= high for low, x, high in zip(
            self.minimum.as_tuple(), point.as_tuple(), self.maximum.as_tuple()
        ))


class Geometry3D(ABC):
    """Immutable local shape measured relative to an Entity's global position."""

    @abstractmethod
    def bounds(self, center: CartesianPosition) -> Bounds3D:
        """Return world-aligned bounds for this shape at ``center``."""

    @abstractmethod
    def contains(self, point: CartesianPosition, center: CartesianPosition) -> bool:
        """Whether this shape occupies the given global point (boundary included)."""

    @abstractmethod
    def segment_interval(self, start: CartesianPosition, end: CartesianPosition,
                         center: CartesianPosition) -> Optional[SegmentInterval]:
        """Return entry/exit fractions along the *finite* global segment.

        Fractions are clamped to [0, 1]. A tangent returns a zero-length
        interval. None means there is no intersection. Geometry only: opacity
        and perception are evaluated separately.
        """

    @abstractmethod
    def to_dict(self) -> dict:
        """A JSON-compatible, explicitly typed shape description."""


@dataclass(frozen=True)
class Sphere(Geometry3D):
    """Sphere centered on its Entity's position, with radius in world units."""

    radius: float
    _MEASURED_ATTRIBUTES = frozenset(("radius",))

    def __post_init__(self):
        object.__setattr__(self, "radius", _positive_finite(self.radius, "radius"))

    def bounds(self, center):
        _point(center, "center")
        r = self.radius
        return Bounds3D(CartesianPosition(center.x-r, center.y-r, center.z-r),
                        CartesianPosition(center.x+r, center.y+r, center.z+r))

    def contains(self, point, center):
        _point(point, "point")
        _point(center, "center")
        return sum(c*c for c in point.relative_to(center)) <= self.radius**2

    def segment_interval(self, start, end, center):
        _point(start, "start")
        _point(end, "end")
        _point(center, "center")
        fx, fy, fz = start.relative_to(center)
        dx, dy, dz = end.relative_to(start)
        a = dx*dx + dy*dy + dz*dz
        c = fx*fx + fy*fy + fz*fz - self.radius*self.radius
        if a == 0.0:
            return (0.0, 0.0) if c <= 0.0 else None
        b = 2.0*(fx*dx + fy*dy + fz*dz)
        discriminant = b*b - 4.0*a*c
        if discriminant < 0.0:
            return None
        root = math.sqrt(discriminant)
        t0 = (-b-root)/(2.0*a)
        t1 = (-b+root)/(2.0*a)
        enter, exit = max(0.0, t0), min(1.0, t1)
        return (enter, exit) if enter <= exit else None

    def to_dict(self):
        return {"type": "sphere", "radius": self.radius}


@dataclass(frozen=True)
class AxisAlignedBox(Geometry3D):
    """Box with full x/y/z side lengths, aligned to global Cartesian axes.

    This initial primitive intentionally has no orientation model. The future
    oriented-box implementation must not alter the meaning of this class.
    """

    size_x: float
    size_y: float
    size_z: float
    _MEASURED_ATTRIBUTES = frozenset(("size_x", "size_y", "size_z"))

    def __post_init__(self):
        for name in ("size_x", "size_y", "size_z"):
            object.__setattr__(self, name, _positive_finite(getattr(self, name), name))

    def _halves(self):
        return (self.size_x/2.0, self.size_y/2.0, self.size_z/2.0)

    def bounds(self, center):
        _point(center, "center")
        cx, cy, cz = center.as_tuple()
        hx, hy, hz = self._halves()
        return Bounds3D(CartesianPosition(cx-hx, cy-hy, cz-hz),
                        CartesianPosition(cx+hx, cy+hy, cz+hz))

    def contains(self, point, center):
        _point(point, "point")
        _point(center, "center")
        return all(abs(coord) <= half for coord, half in
                   zip(point.relative_to(center), self._halves()))

    def segment_interval(self, start, end, center):
        _point(start, "start")
        _point(end, "end")
        _point(center, "center")
        offset = start.relative_to(center)
        direction = end.relative_to(start)
        low, high = 0.0, 1.0
        for p, d, half in zip(offset, direction, self._halves()):
            if d == 0.0:
                if abs(p) > half:
                    return None
                continue
            t0, t1 = (-half-p)/d, (half-p)/d
            if t0 > t1:
                t0, t1 = t1, t0
            low, high = max(low, t0), min(high, t1)
            if low > high:
                return None
        return (low, high)

    def to_dict(self):
        return {"type": "axis_aligned_box", "size_x": self.size_x,
                "size_y": self.size_y, "size_z": self.size_z}


def geometry_from_dict(data: dict) -> Geometry3D:
    """Restore one of the supported initial shapes without guessing geometry."""
    if not isinstance(data, dict):
        raise TypeError("geometry data must be a mapping")
    if data.get("type") == "sphere":
        return Sphere(data["radius"])
    if data.get("type") == "axis_aligned_box":
        return AxisAlignedBox(data["size_x"], data["size_y"], data["size_z"])
    raise ValueError("unknown geometry type")
