"""Explicit prepublication geometry and source facts for the Arena discovery exercise.

These dimensions describe this authored fixture only; they are not generated
Being anatomy or a production geometry model.
"""

import math

from spatial.geometry import Sphere
from spatial.occlusion import VisualOcclusion


SCENARIO_ID = "arena-spot-demo"


def author_scenario(candidate):
    """Place one explicitly modeled opaque screen between the two Beings."""
    first, second = (row.native.being for row in candidate.participants)
    start, end = first.get_position(), second.get_position()
    if start is None or end is None or start == end:
        raise ValueError("authored discovery scenario requires distinct placed Beings")
    distance = math.dist(start.as_tuple(), end.as_tuple())
    wall_id = candidate.universe.make_object("Brick", "Opaque screen · discovery exercise")
    wall = candidate.universe.get_object_by_id(wall_id)
    wall.set_position(type(start)(*(a + (b - a) / 2
                                    for a, b in zip(start.as_tuple(), end.as_tuple()))))
    wall.set_geometry(Sphere(max(0.05, distance / 10)))
    wall.set_visual_occlusion(VisualOcclusion(1.0))
    candidate.encounter.add_object(wall_id)

    # The named, prepublication test scenario authors this point-target shape;
    # no dimensions are inferred from a generated Being race or stature.
    second.set_name("Obscured Target")
    second.set_geometry(Sphere(0.25))
    # A low, explicit DC makes the demonstration's successful check
    # deterministic for every sampled d20 face without changing the rule.
    second.current.discovery_dc = 1
    # These fixture-only source facts support bounded Search/Listen examples.
    # They are author statements of access and audibility, not reach or sound
    # propagation models.
    second.current.tags['arena_search_accessible'] = True
    second.current.tags['arena_audible'] = True
    return {"wall_id": wall_id, "target_id": second.id,
            "target_geometry": "authored Sphere radius 0.25 m",
            "wall_geometry": "authored opaque Sphere centered on initial sightline"}
