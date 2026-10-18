#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Minimal, replaceable perception models for Universe encounters.

The first implementation is deliberately not a model of vision or hearing.  It
uses continuous 3D range only, providing a simple bridge from spatial state to
directed awareness while richer physical perception is developed later.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Perception:
    """A successful observation produced by a perception model.

    ``mode`` records the model that produced the observation.  ``distance`` and
    ``threshold`` make the reason for this first range-based observation explicit
    without treating proximity itself as a real sensory mechanism.
    """

    observer_id: str
    target_id: str
    mode: str
    distance: float
    threshold: float


class RangePerception:
    """Scaffolding perception model based solely on continuous 3D distance.

    This model exists to exercise the perception -> awareness transition.  It is
    intentionally replaceable by vision, hearing, or other models that account
    for geometry, environment, agent capabilities, and physical propagation.
    """

    mode = "range"

    def __init__(self, max_distance):
        try:
            max_distance = float(max_distance)
        except (TypeError, ValueError) as exc:
            raise TypeError("max_distance must be numeric") from exc
        if max_distance < 0.0:
            raise ValueError("max_distance must be non-negative")
        # Encounter performs the full finite-number validation as well.  Keeping
        # this class independent avoids importing Encounter and a circular import.
        if max_distance == float("inf") or max_distance != max_distance:
            raise ValueError("max_distance must be finite")
        self.max_distance = max_distance

    def detect(self, spatial_context, observer_id):
        """Return successful observations without mutating awareness state.

        ``spatial_context`` is intentionally duck-typed.  At present Encounter
        provides the required ``get_being``, ``entities_within``, and
        ``distance_between_entities`` methods; future spatial contexts may do so
        as well.
        """
        if spatial_context.get_being(observer_id) is None:
            return []

        results = []
        for target_id in spatial_context.entities_within(observer_id, self.max_distance):
            distance = spatial_context.distance_between_entities(observer_id, target_id)
            if distance is None:
                continue
            results.append(
                Perception(
                    observer_id=observer_id,
                    target_id=target_id,
                    mode=self.mode,
                    distance=distance,
                    threshold=self.max_distance,
                )
            )
        return results


class GeometricPathPerception(RangePerception):
    """Opt-in, deliberately incomplete line-of-sight perception scaffold.

    Reports targets *with explicit physical geometry* only when their reference
    point is within range and the sightline has no modeled obstruction,
    unknown-opacity intersection, or unmodeled candidate Entities. This is not visual detection: illumination, terrain, target
    surfaces, eye points, and unmodeled Entities are not simulated. In
    particular, incomplete geometry cannot justify claims of real visibility.
    """

    mode = "geometric_path_only"

    def detect(self, spatial_context, observer_id):
        if spatial_context.get_being(observer_id) is None:
            return []
        observations = []
        for candidate in super().detect(spatial_context, observer_id):
            target = spatial_context.get_entity(candidate.target_id)
            if target is None or target.geometry is None:
                continue
            sightline = spatial_context.line_of_sight(observer_id, candidate.target_id)
            if sightline is not None and sightline.clear:
                observations.append(Perception(
                    observer_id=observer_id,
                    target_id=candidate.target_id,
                    mode=self.mode,
                    distance=candidate.distance,
                    threshold=self.max_distance,
                ))
        return observations
