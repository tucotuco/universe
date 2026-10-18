#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""3D sightline geometry against explicitly modeled physical Entities.

An ISEA cell or Encounter grid is never used as a visibility test.  This is
one segment between two supplied global points (not a whole-target visibility
or optical propagation calculation).  "clear" means clear of *modeled*
opaque/uncertain geometry only; omitted Entities and terrain may still obstruct.
"""

from dataclasses import dataclass

from spatial.state import CartesianPosition


@dataclass(frozen=True)
class SightlineIntersection:
    """A modeled Entity intersecting a finite sightline, in entry order."""

    entity_id: str
    entry: float
    exit: float
    opacity: float | None  # None: geometric hit, but optical character unknown


@dataclass(frozen=True)
class SightlineResult:
    """Outcome for a single 3D sightline, limited to supplied modeled geometry.

    Status: ``blocked`` (an opaque hit), ``unknown`` (unknown opacity or
    unmodeled candidate geometry), ``partial`` (partially opaque hits), or
    ``clear`` (no intersecting nontransparent geometry and no missing
    candidate models).  Status is NOT a determination
    of vision: light, eye anatomy, terrain, and missing geometry are unmodeled.
    ``unmodeled_entity_ids`` records Entities that could not be tested at all.
    """

    start: CartesianPosition
    end: CartesianPosition
    status: str
    intersections: tuple[SightlineIntersection, ...]
    unmodeled_entity_ids: tuple[str, ...]

    @property
    def clear(self):
        """No modeled obstruction or missing Entity model; NOT physical vision."""
        return self.status == "clear"



def trace_sightline(start, end, entities, *, exclude_ids=()):
    """Trace a world-space segment past ``(entity_id, entity)`` candidates.

    ``entities`` can contain physical Beings and ordinary Objects.  Each
    candidate may provide geometry, placement, and visual_occlusion.  The
    excluded ids normally identify the observer and target: their own volumes
    must not block the sightline to the target reference point.

    Only overlaps with an interior part of the finite segment are considered;
    isolated endpoint touches are ignored. Tangencies within the segment
    conservatively count as geometric intersections.  No mutation occurs.
    """
    if not isinstance(start, CartesianPosition) or not isinstance(end, CartesianPosition):
        raise TypeError("sightline endpoints must be CartesianPosition values")
    # Positions are usually distinct; coincident reference points form a
    # zero-length test which cannot establish an optical path.
    if start == end:
        raise ValueError("sightline endpoints must be distinct")

    excluded = set(exclude_ids)
    intersections = []
    unmodeled = []
    for entity_id, entity in entities:
        if entity_id in excluded:
            continue
        # An absent shape/placement is not automatically transparent.
        if getattr(entity, "geometry", None) is None or entity.get_position() is None:
            unmodeled.append(entity_id)
            continue
        interval = entity.segment_intersection(start, end)
        if interval is None:
            continue
        entry, exit = interval
        if exit <= 0.0 or entry >= 1.0:
            continue
        optics = getattr(entity, "visual_occlusion", None)
        intersections.append(SightlineIntersection(
            entity_id=entity_id,
            entry=entry,
            exit=exit,
            opacity=None if optics is None else optics.opacity,
        ))

    # Missing geometry/placement is conservatively unknown, not transparent.
    # Return the actual geometric sequence, irrespective of Encounter insertion
    # order. Stable tie-breaking keeps diagnostics/replays reproducible.
    intersections.sort(key=lambda item: (item.entry, str(item.entity_id)))
    if any(hit.opacity == 1.0 for hit in intersections):
        status = "blocked"
    elif unmodeled or any(hit.opacity is None for hit in intersections):
        status = "unknown"
    elif any(hit.opacity > 0.0 for hit in intersections):
        status = "partial"
    else:
        status = "clear"
    return SightlineResult(start, end, status, tuple(intersections), tuple(unmodeled))
