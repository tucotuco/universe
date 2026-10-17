#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Derived spatial relationships between positions in a common Cartesian frame."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Optional, Tuple, Union

from spatial.cell import CellAddress
from spatial.grid import SpatialGrid
from spatial.state import CartesianPosition, Vec3


@dataclass(frozen=True)
class SpatialRelation:
    """The current geometric relation from one position to another.

    The relation is derived, not persistent world state.  ``source`` and
    ``target`` are assumed to be expressed in the same Cartesian reference
    frame.  Explicit frame identities and transforms can be added later when
    local encounter frames are introduced.

    Discrete grid cells are optional views of this continuous relation; they
    never determine the physical distance or direction.
    """

    source: CartesianPosition
    target: CartesianPosition

    def __post_init__(self) -> None:
        if not isinstance(self.source, CartesianPosition):
            raise TypeError("source must be a CartesianPosition")
        if not isinstance(self.target, CartesianPosition):
            raise TypeError("target must be a CartesianPosition")

    @property
    def displacement(self) -> Vec3:
        """Return the Cartesian vector from source to target."""
        return (
            self.target.x - self.source.x,
            self.target.y - self.source.y,
            self.target.z - self.source.z,
        )

    @property
    def distance(self) -> float:
        """Return straight-line Euclidean distance in the shared frame."""
        dx, dy, dz = self.displacement
        return math.sqrt(dx * dx + dy * dy + dz * dz)

    @property
    def unit_direction(self) -> Optional[Vec3]:
        """Return the unit displacement vector, or ``None`` if coincident."""
        distance = self.distance
        if distance == 0.0:
            return None
        dx, dy, dz = self.displacement
        return (dx / distance, dy / distance, dz / distance)

    @property
    def coincident(self) -> bool:
        return self.distance == 0.0

    def cells_at(
        self,
        grid: SpatialGrid,
        level: int,
        origin: Union[CartesianPosition, Vec3, None] = None,
    ) -> Tuple[CellAddress, CellAddress]:
        """Return the overlay cells containing source and target at ``level``."""
        if not isinstance(grid, SpatialGrid):
            raise TypeError("grid must implement SpatialGrid")
        source_latitude, source_longitude = self.source.angular_coordinate(origin)
        target_latitude, target_longitude = self.target.angular_coordinate(origin)
        return (
            grid.cell_at(source_latitude, source_longitude, level),
            grid.cell_at(target_latitude, target_longitude, level),
        )

    def shares_cell(
        self,
        grid: SpatialGrid,
        level: int,
        origin: Union[CartesianPosition, Vec3, None] = None,
    ) -> bool:
        """Return whether both positions fall in the same cell at ``level``."""
        source_cell, target_cell = self.cells_at(grid, level, origin)
        return source_cell == target_cell

    def deepest_shared_cell(
        self,
        grid: SpatialGrid,
        level: int,
        origin: Union[CartesianPosition, Vec3, None] = None,
    ) -> Optional[CellAddress]:
        """Return the deepest common ancestor of both level-specific cells.

        ``None`` means the positions lie in different root icosahedral faces.
        This is an indexing relationship only, not a substitute for physical
        distance.
        """
        source_cell, target_cell = self.cells_at(grid, level, origin)
        return source_cell.common_ancestor(target_cell)
