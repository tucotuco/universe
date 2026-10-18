"""Spatial indexing and continuous spatial-state primitives for Universe.

The spatial package deliberately separates discrete spatial indexing from the
continuous physical space that the grid indexes.  The first grid implementation
is an equal-area hierarchical triangular grid on a sphere.
"""

from spatial.cell import CellAddress
from spatial.isea import ISEAGrid
from spatial.frame import LocalFrame, LocalPosition
from spatial.geometry import AxisAlignedBox, Bounds3D, Geometry3D, Sphere, geometry_from_dict
from spatial.occlusion import VisualOcclusion
from spatial.relation import SpatialRelation
from spatial.state import CartesianPosition, SpatialState
from spatial.visibility import SightlineIntersection, SightlineResult, trace_sightline

__all__ = [
    "AxisAlignedBox",
    "Bounds3D",
    "CartesianPosition",
    "Geometry3D",
    "CellAddress",
    "ISEAGrid",
    "LocalFrame",
    "LocalPosition",
    "SpatialRelation",
    "SpatialState",
    "SightlineIntersection",
    "SightlineResult",
    "trace_sightline",
    "Sphere",
    "VisualOcclusion",
    "geometry_from_dict",
]
