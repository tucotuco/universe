"""Spatial indexing primitives for Universe.

The spatial package deliberately separates discrete spatial indexing from the
continuous physical space that the grid indexes.  The first implementation is
an equal-area hierarchical triangular grid on a sphere.
"""

from spatial.cell import CellAddress
from spatial.isea import ISEAGrid

__all__ = ["CellAddress", "ISEAGrid"]
