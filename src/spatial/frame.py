#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Rigid local Cartesian frames anchored in Universe's continuous 3D space.

An Encounter frame changes how physical positions and velocities are *expressed*;
it does not move entities or discretize physical space. Global positions remain
CartesianPosition objects. Local coordinates have a distinct type to avoid
silently confusing them with global positions.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Tuple

from spatial.state import CartesianPosition, Vec3


_TOLERANCE = 1e-9


def _vector(value, name: str) -> Vec3:
    """Validate a real, finite three-component coordinate or direction."""
    try:
        x, y, z = value
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must have three numeric components") from exc
    try:
        result = (float(x), float(y), float(z))
    except (TypeError, ValueError, OverflowError) as exc:
        raise TypeError(f"{name} components must be numeric") from exc
    if not all(math.isfinite(v) for v in result):
        raise ValueError(f"{name} components must be finite")
    return result


def _dot(a: Vec3, b: Vec3) -> float:
    return sum(x * y for x, y in zip(a, b))


def _cross(a: Vec3, b: Vec3) -> Vec3:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


@dataclass(frozen=True)
class LocalPosition:
    """Coordinates relative to a particular LocalFrame (not a global position).

    The owning frame must be supplied when transforming back to world space.
    """

    x: float
    y: float
    z: float

    def __post_init__(self) -> None:
        x, y, z = _vector((self.x, self.y, self.z), "local coordinates")
        object.__setattr__(self, "x", x)
        object.__setattr__(self, "y", y)
        object.__setattr__(self, "z", z)

    def as_tuple(self) -> Vec3:
        return (self.x, self.y, self.z)


@dataclass(frozen=True)
class LocalFrame:
    """Orthonormal, right-handed frame positioned in a shared global 3D space.

    x_axis/y_axis/z_axis are directions in global Cartesian coordinates. All
    lengths and velocities use the same physical units as the global frame.
    The origin is a global CartesianPosition; there is no implicit connection
    to a tessellation, a particular planet, or a local hex overlay.
    """

    origin: CartesianPosition
    x_axis: Vec3
    y_axis: Vec3
    z_axis: Vec3

    def __post_init__(self) -> None:
        if not isinstance(self.origin, CartesianPosition):
            raise TypeError("origin must be a CartesianPosition")
        for name in ("x_axis", "y_axis", "z_axis"):
            object.__setattr__(self, name, _vector(getattr(self, name), name))
        axes = (self.x_axis, self.y_axis, self.z_axis)
        if any(abs(_dot(axis, axis) - 1.0) > _TOLERANCE for axis in axes):
            raise ValueError("frame axes must be unit vectors")
        if any(abs(_dot(axes[i], axes[j])) > _TOLERANCE
               for i, j in ((0, 1), (0, 2), (1, 2))):
            raise ValueError("frame axes must be mutually perpendicular")
        if _dot(_cross(self.x_axis, self.y_axis), self.z_axis) < 1.0 - _TOLERANCE:
            raise ValueError("frame axes must form a right-handed system")

    @classmethod
    def aligned_at(cls, origin: CartesianPosition) -> "LocalFrame":
        """Create a translated frame with axes parallel to the global axes."""
        return cls(origin, (1, 0, 0), (0, 1, 0), (0, 0, 1))

    @classmethod
    def tangent_at(cls, position: CartesianPosition,
                   body_center: CartesianPosition = CartesianPosition(0, 0, 0)) -> "LocalFrame":
        """Create an east/north/up tangent frame for a spherical body.

        The local origin is ``position``, and up is radial from ``body_center``.
        The frame is geometric and makes *no* assumptions about ellipsoids,
        gravity, terrain, or atmospheric physics. At a geographic pole, the
        +global X meridian is used as the deterministic reference direction.
        """
        if not isinstance(position, CartesianPosition):
            raise TypeError("position must be a CartesianPosition")
        if not isinstance(body_center, CartesianPosition):
            raise TypeError("body_center must be a CartesianPosition")
        latitude, longitude = position.angular_coordinate(body_center)
        phi, lam = math.radians(latitude), math.radians(longitude)
        slat, clat = math.sin(phi), math.cos(phi)
        slon, clon = math.sin(lam), math.cos(lam)
        east = (-slon, clon, 0.0)
        north = (-slat * clon, -slat * slon, clat)
        up = (clat * clon, clat * slon, slat)
        return cls(position, east, north, up)

    def to_local(self, position: CartesianPosition) -> LocalPosition:
        """Project a global 3D position onto this local orthonormal frame."""
        if not isinstance(position, CartesianPosition):
            raise TypeError("position must be a global CartesianPosition")
        displacement = position.relative_to(self.origin)
        return LocalPosition(*(_dot(displacement, axis) for axis in
                               (self.x_axis, self.y_axis, self.z_axis)))

    def to_global(self, position: LocalPosition) -> CartesianPosition:
        """Map local coordinates to the authoritative global 3D frame."""
        if not isinstance(position, LocalPosition):
            raise TypeError("position must be a LocalPosition")
        return CartesianPosition(*(
            origin_value + position.x * x + position.y * y + position.z * z
            for origin_value, x, y, z in zip(
                self.origin.as_tuple(), self.x_axis, self.y_axis, self.z_axis
            )
        ))

    def vector_to_local(self, vector) -> Vec3:
        """Rotate a global vector into local coordinates (no translation)."""
        vector = _vector(vector, "vector")
        return tuple(_dot(vector, axis) for axis in
                     (self.x_axis, self.y_axis, self.z_axis))

    def vector_to_global(self, vector) -> Vec3:
        """Rotate a local vector into global coordinates (no translation)."""
        u, v, w = _vector(vector, "vector")
        return tuple(u * x + v * y + w * z for x, y, z in
                     zip(self.x_axis, self.y_axis, self.z_axis))

    def to_dict(self) -> dict:
        """JSON-compatible representation with an explicit frame orientation."""
        return {
            "origin": list(self.origin.as_tuple()),
            "x_axis": list(self.x_axis),
            "y_axis": list(self.y_axis),
            "z_axis": list(self.z_axis),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LocalFrame":
        """Restore a frame from its serialized axes and origin."""
        if not isinstance(data, dict):
            raise TypeError("frame data must be a mapping")
        return cls(CartesianPosition(*data["origin"]),
                   data["x_axis"], data["y_axis"], data["z_axis"])
