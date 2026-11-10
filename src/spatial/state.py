#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Continuous spatial state for entities in Universe.

Discrete grids are overlays on this continuous state.  A Cartesian position is
therefore authoritative; a grid cell is derived at whatever resolution a
caller currently needs.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Tuple, Union

from spatial.cell import CellAddress
from spatial.grid import SpatialGrid


Vec3 = Tuple[float, float, float]


@dataclass(frozen=True)
class CartesianPosition:
    """A point in a continuous three-dimensional Cartesian reference frame.

    The class deliberately does not define what the reference frame *is*.
    Planetary body-fixed, Universe-global, and local encounter frames can be
    introduced explicitly later without making grid coordinates authoritative.
    """

    x: float
    y: float
    z: float

    def __post_init__(self) -> None:
        values = (float(self.x), float(self.y), float(self.z))
        if not all(math.isfinite(value) for value in values):
            raise ValueError("Cartesian coordinates must be finite numbers")
        object.__setattr__(self, "x", values[0])
        object.__setattr__(self, "y", values[1])
        object.__setattr__(self, "z", values[2])

    @classmethod
    def from_lat_lon(
        cls,
        latitude: float,
        longitude: float,
        radial_distance: float = 1.0,
        origin: Union["CartesianPosition", Vec3, None] = None,
    ) -> "CartesianPosition":
        """Construct a Cartesian point from angular coordinates around an origin."""
        latitude = float(latitude)
        longitude = float(longitude)
        radial_distance = float(radial_distance)
        if not math.isfinite(latitude) or not -90.0 <= latitude <= 90.0:
            raise ValueError("latitude must be finite and in the range -90..90 degrees")
        if not math.isfinite(longitude):
            raise ValueError("longitude must be finite")
        if not math.isfinite(radial_distance) or radial_distance < 0.0:
            raise ValueError("radial_distance must be a finite non-negative number")

        ox, oy, oz = _coordinates(origin)
        latitude_radians = math.radians(latitude)
        longitude_radians = math.radians(longitude)
        cos_latitude = math.cos(latitude_radians)
        return cls(
            ox + radial_distance * cos_latitude * math.cos(longitude_radians),
            oy + radial_distance * cos_latitude * math.sin(longitude_radians),
            oz + radial_distance * math.sin(latitude_radians),
        )

    def as_tuple(self) -> Vec3:
        return (self.x, self.y, self.z)

    def relative_to(self, origin: Union["CartesianPosition", Vec3, None] = None) -> Vec3:
        ox, oy, oz = _coordinates(origin)
        return (self.x - ox, self.y - oy, self.z - oz)

    def radial_distance(self, origin: Union["CartesianPosition", Vec3, None] = None) -> float:
        x, y, z = self.relative_to(origin)
        return math.sqrt(x * x + y * y + z * z)

    def angular_coordinate(
        self, origin: Union["CartesianPosition", Vec3, None] = None
    ) -> Tuple[float, float]:
        """Return ``(latitude, longitude)`` of this point as seen from ``origin``.

        Radial distance is intentionally discarded here.  This is the bridge
        from continuous 3D physical position to a surface indexing overlay.
        """
        x, y, z = self.relative_to(origin)
        radius = math.sqrt(x * x + y * y + z * z)
        if radius == 0.0:
            raise ValueError("angular coordinates are undefined at the reference-frame origin")
        latitude = math.degrees(math.asin(max(-1.0, min(1.0, z / radius))))
        longitude = math.degrees(math.atan2(y, x))
        return (latitude, longitude)


def _coordinates(value: Union[CartesianPosition, Vec3, None]) -> Vec3:
    if value is None:
        return (0.0, 0.0, 0.0)
    if isinstance(value, CartesianPosition):
        return value.as_tuple()
    try:
        x, y, z = value
    except (TypeError, ValueError) as exc:
        raise TypeError("origin must be a CartesianPosition or a three-value coordinate") from exc
    coordinates = (float(x), float(y), float(z))
    if not all(math.isfinite(component) for component in coordinates):
        raise ValueError("origin coordinates must be finite numbers")
    return coordinates


@dataclass
class SpatialState:
    """The continuous spatial state currently attached to an entity.

    Only position is represented at this stage.  Velocity, orientation, and
    reference-frame transforms belong here later if concrete simulation needs
    demonstrate that they should be persistent entity state.
    """

    position: CartesianPosition

    def __setattr__(self, name, value) -> None:
        if name == "position":
            from measured_values import truncate_position
            value = truncate_position(value)
        object.__setattr__(self, name, value)

    def __post_init__(self) -> None:
        if not isinstance(self.position, CartesianPosition):
            raise TypeError("position must be a CartesianPosition")

    def set_position(self, position: CartesianPosition) -> None:
        if not isinstance(position, CartesianPosition):
            raise TypeError("position must be a CartesianPosition")
        self.position = position

    def cell(
        self,
        grid: SpatialGrid,
        level: int,
        origin: Union[CartesianPosition, Vec3, None] = None,
    ) -> CellAddress:
        """Derive the grid cell containing the current continuous position."""
        if not isinstance(grid, SpatialGrid):
            raise TypeError("grid must implement SpatialGrid")
        latitude, longitude = self.position.angular_coordinate(origin)
        return grid.cell_at(latitude, longitude, level)


def integrate_position(previous, velocity, duration):
    """Native constant-velocity displacement, shared by live and inactive paths."""
    vx, vy, vz = velocity
    return CartesianPosition(previous.x + vx * duration,
                             previous.y + vy * duration,
                             previous.z + vz * duration)
