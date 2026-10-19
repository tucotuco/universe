"""Small, opt-in constraint examples for Universe realization experiments.

These are *domain-specific* validators, not claims that the entire Universe can
be validated with counts and speed bounds. The speed check is a necessary
kinematic feasibility condition, not a full collision/dynamics simulation.
"""
from __future__ import annotations

import math

from realization import FactKey, ImpossibleRealization, RealityView


def fixed_composition(entity_id: str, time: float, total_attribute: str,
                      detail_attribute: str, categories: tuple[str, ...]):
    """Require committed subgroup counts to partition one known total.

    Accept incomplete partitions; all parts must total exactly when every part
    is committed. No subgroup is generated just to run this validation.
    """
    if not categories or len(set(categories)) != len(categories):
        raise ValueError("categories must be distinct and nonempty")
    total_key = FactKey(entity_id, total_attribute, time)
    part_keys = tuple(FactKey(entity_id, detail_attribute, time, c)
                      for c in categories)

    def validate(view: RealityView):
        if not view.contains(total_key):
            return
        total = view.get(total_key)
        if type(total) is not int or total < 0:
            raise ImpossibleRealization("total must be a nonnegative integer")
        known = [view.get(k) for k in part_keys if view.contains(k)]
        if any(type(value) is not int or value < 0 for value in known):
            raise ImpossibleRealization("subgroup counts must be nonnegative integers")
        if sum(known) > total:
            raise ImpossibleRealization("subgroup counts exceed committed total")
        if len(known) == len(part_keys) and sum(known) != total:
            raise ImpossibleRealization("complete subgroup counts must sum to total")
    return validate


def within_lifetime(entity_id: str, attribute: str, start: float, end: float):
    """Require a historical detail to fall inside an established lifespan."""
    if start > end:
        raise ValueError("start must not exceed end")

    def validate(view: RealityView):
        for fact in view.all_facts():
            if fact.key.entity_id == entity_id and fact.key.attribute == attribute:
                if fact.key.time is None or not start <= fact.key.time <= end:
                    raise ImpossibleRealization("historical detail outside established lifetime")
    return validate


def bounded_speed(entity_id: str, max_speed: float, *, attribute="position"):
    """Necessary Euclidean reachability test for committed dated positions.

    Every pair of established positions must be within max_speed * elapsed
    time. It intentionally does not model terrain, acceleration or obstacles.
    """
    if not math.isfinite(max_speed) or max_speed < 0:
        raise ValueError("max_speed must be finite and nonnegative")

    def validate(view: RealityView):
        points = []
        for fact in view.all_facts():
            if fact.key.entity_id != entity_id or fact.key.attribute != attribute:
                continue
            if fact.key.time is None:
                raise ImpossibleRealization("kinematic positions require a time")
            values = fact.value
            if (not isinstance(values, list) or len(values) != 3 or
                    any(type(n) not in (int, float) or not math.isfinite(n)
                        for n in values)):
                raise ImpossibleRealization("position must be a finite 3-vector")
            points.append((fact.key.time, values))
        for index, (time, point) in enumerate(points):
            for other_time, other in points[index + 1:]:
                if math.dist(point, other) > max_speed * abs(other_time-time) + 1e-9:
                    raise ImpossibleRealization("position exceeds available travel bound")
    return validate
