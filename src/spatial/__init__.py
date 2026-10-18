"""Spatial indexing and continuous spatial-state primitives for Universe.

The spatial package deliberately separates discrete spatial indexing from the
continuous physical space that the grid indexes.  The first grid implementation
is an equal-area hierarchical triangular grid on a sphere.
"""

from spatial.cell import CellAddress
from spatial.isea import ISEAGrid
from spatial.frame import LocalFrame, LocalPosition
from spatial.relation import SpatialRelation
from spatial.state import CartesianPosition, SpatialState

__all__ = [
    "CartesianPosition",
    "CellAddress",
    "ISEAGrid",
    "LocalFrame",
    "LocalPosition",
    "SpatialRelation",
    "SpatialState",
]
