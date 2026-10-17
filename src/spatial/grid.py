#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Interface for discrete spatial overlays."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Tuple, Union

from spatial.cell import CellAddress


Coordinate = Tuple[float, float]  # (latitude_degrees, longitude_degrees)


class SpatialGrid(ABC):
    """A discrete overlay on an underlying continuous spatial frame.

    A grid is an indexing and resolution mechanism.  It is explicitly *not*
    the physical space itself; physics may use continuous 3D coordinates while
    this interface supplies stable cells for indexing, aggregation and spatial
    refinement.
    """

    @abstractmethod
    def cell_at(self, latitude: float, longitude: float, level: int) -> CellAddress:
        """Return the cell containing the supplied angular coordinate."""

    @abstractmethod
    def vertices(self, cell: Union[str, CellAddress]) -> Tuple[Coordinate, Coordinate, Coordinate]:
        """Return the three spherical vertices of a triangular cell."""

    @abstractmethod
    def centroid(self, cell: Union[str, CellAddress]) -> Coordinate:
        """Return a stable representative point inside a cell."""

    @abstractmethod
    def area(self, cell: Union[str, CellAddress]) -> float:
        """Return cell area in squared units of the grid radius."""

    @abstractmethod
    def contains(self, cell: Union[str, CellAddress], latitude: float, longitude: float) -> bool:
        """Return whether the coordinate lies in the cell."""
