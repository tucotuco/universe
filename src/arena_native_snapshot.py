"""Compatibility import for the generated-Arena native graph adapter.

The graph codec itself lives in :mod:`native_graph_snapshot` so independent
native persistence consumers do not import an Arena-named module. This shim
preserves the existing /12 API and its private migration helpers.
"""
import native_graph_snapshot as _implementation

globals().update({name: value for name, value in vars(_implementation).items()
                  if not name.startswith("__")})
