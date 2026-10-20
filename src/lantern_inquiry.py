"""Bounded, read-only optical *proxy* for a fixed lamp on a regional hillside.

Coordinates and terrain heights belong to GeographicalDesign. A sampled
straight ray is not a continuous-visibility proof, radiative transfer, or a
model of adaptation, obstacles, weather, or real human visual physiology.
"""
from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Lantern:
    # The lamp is anchored to the terrain, NOT independently elevated in the
    # already-known map. Ground height remains unresolved until necessary.
    location_km: tuple[float, float] = (5.8, -1.8)
    mast_height_m: float = 1.5
    intensity_cd: float = 7000.0
    lit: bool = True


class LanternInquiry:
    """Compute an interval-based sampled sightline without touching reality.

    Only an explicit look action may ask the caller to realize missing tiles.
    Each uncertain tile is reported as a dependency. Unknown elevations are
    bounded by GeographicalDesign's authoritative relief/condition intervals.
    """
    STEP_M = 25.0
    EYE_HEIGHT_M = 1.7
    DUSK_CONTRAST_THRESHOLD_LUX = 0.00015
    ATTENUATION_PER_KM = 0.16  # chosen example assumption, not a weather model
    CLEARANCE_EPS_M = 1e-7

    def __init__(self, terrain, lamp=None):
        self.terrain = terrain
        self.lamp = lamp or Lantern()

    def assess(self, observer_km):
        sx, sy = self.terrain._xy(*observer_km)
        tx, ty = self.terrain._xy(*self.lamp.location_km)
        length_m = math.hypot(tx-sx, ty-sy)*1000.0
        if length_m < 0.01:
            raise ValueError('Observer cannot stand at the lantern center')
        total = max(2, math.ceil(length_m/self.STEP_M))
        ground_start = self.terrain.elevation_bounds(sx, sy)
        ground_target = self.terrain.elevation_bounds(tx, ty)
        start_lo = ground_start['min_m'] + self.EYE_HEIGHT_M
        start_hi = ground_start['max_m'] + self.EYE_HEIGHT_M
        target_lo = ground_target['min_m'] + self.lamp.mast_height_m
        target_hi = ground_target['max_m'] + self.lamp.mast_height_m
        # The eye and lamp elevations have independent uncertainty. Interpolate
        # their respective extrema; compare against terrain height bounds.
        definite_blocker = None
        unknown = set()
        max_clearance_lower = float('inf')
        for i in range(1, total):
            f = i/total
            x, y = sx+f*(tx-sx), sy+f*(ty-sy)
            local = self.terrain.elevation_bounds(x, y)
            low_ray = (1-f)*start_lo + f*target_lo
            high_ray = (1-f)*start_hi + f*target_hi
            # Below-ground at a sampled point for *every* possible refinement.
            if local['min_m'] > high_ray + self.CLEARANCE_EPS_M:
                definite_blocker = (round(x, 6), round(y, 6))
                break
            max_clearance_lower = min(max_clearance_lower, low_ray-local['max_m'])
            if local['max_m'] >= low_ray - self.CLEARANCE_EPS_M and not local['resolved']:
                unknown.add(tuple(local['tile']))
        if definite_blocker is not None:
            status = 'blocked'
        elif max_clearance_lower > self.CLEARANCE_EPS_M:
            status = 'clear'
        else:
            status = 'unresolved'
            # Both endpoint ground heights are part of the ray. They must be
            # fixed before we can conclude a marginal/intersecting sightline.
            for endpoint in (ground_start, ground_target):
                if not endpoint['resolved']:
                    unknown.add(tuple(endpoint['tile']))
            # In a bound-tightened world, all uncertain samples might be stable
            # yet touch the ray. Conservatively report indeterminate rather
            # than asserting a continuous tangent is clear or blocked.
        if status != 'unresolved':
            unknown.clear()
        # No commitment is involved in photometry. Illuminance is for a point
        # source facing the eye, before contrast, glare and intervening objects.
        # Worst-case distance takes endpoint elevation uncertainty into account.
        distance_max = math.hypot(length_m, max(abs(target_lo-start_hi),
                                                 abs(target_hi-start_lo)))
        illuminance = (self.lamp.intensity_cd / (distance_max**2) *
                       math.exp(-self.ATTENUATION_PER_KM*distance_max/1000)) if self.lamp.lit else 0.0
        enough_light = illuminance >= self.DUSK_CONTRAST_THRESHOLD_LUX
        if not self.lamp.lit or not enough_light:
            physical = 'undetectable_light'
        elif status == 'blocked':
            physical = 'occluded'
        elif status == 'clear':
            physical = 'detectable_candidate'
        else:
            physical = 'unresolved_geometry'
        return {
            'geometry': status, 'physical_visibility': physical,
            'missing_terrain_tiles': [list(v) for v in sorted(unknown)],
            'blocking_sample_km': list(definite_blocker) if definite_blocker else None,
            'distance_m': round(length_m, 2), 'samples': total-1,
            'sample_spacing_max_m': self.STEP_M,
            'illuminance_lux_lower_bound': round(illuminance, 9),
            'dusk_threshold_lux': self.DUSK_CONTRAST_THRESHOLD_LUX,
            'lit': self.lamp.lit,
            'assumptions': ['straight sampled line of sight; unsampled terrain not certified',
                            'terrain bounds from GeographicalDesign',
                            'fixed dusk contrast threshold and exponential attenuation',
                            'no intervening objects, fog, visual adaptation or planetary curvature'],
            'source': 'LanternInquiry + GeographicalDesign',
        }
