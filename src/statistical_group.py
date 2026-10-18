"""Experimental statistical aggregate with partially realized composition and motion.

An aggregate is a real, persistent Encounter Entity even when none of its
members has been materialized.  Sampling is keyed, rather than consuming a
shared random stream, so requesting different details in different orders does
not change the underlying realization.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
import random

from object import ObjectDefinition, ObjectInstance
from spatial.state import CartesianPosition


def _vec(value, name):
    try:
        values = tuple(float(v) for v in value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must have three numeric coordinates") from exc
    if len(values) != 3 or not all(math.isfinite(v) for v in values):
        raise ValueError(f"{name} must be a finite three-vector")
    return values


def _norm(vector):
    return math.sqrt(sum(component * component for component in vector))


def _draw_cdf(points, rng):
    """Draw an integer from an explicit cumulative distribution (value, P<=value)."""
    if not points or not isinstance(points, list):
        raise ValueError("CDF must contain a list of points")
    previous_probability = 0.0
    previous_value = -1
    for value, probability in points:
        if (isinstance(value, bool) or not isinstance(value, int)
                or value <= previous_value or value < 0):
            raise ValueError("CDF values must be distinct ascending nonnegative integers")
        if not math.isfinite(probability) or probability <= previous_probability or probability > 1:
            raise ValueError("CDF probabilities must increase within (0, 1]")
        previous_value, previous_probability = value, probability
    if not math.isclose(previous_probability, 1.0, abs_tol=1e-12):
        raise ValueError("CDF must terminate at probability 1")
    u = rng.random()
    for value, probability in points:
        if u < probability:
            return value
    return points[-1][0]


@dataclass(frozen=True)
class GroupMember:
    """Materialized *identity/placement*, not yet a complete BeingInstance."""
    id: str
    household: int
    category: str
    index: int
    offset: tuple[float, float, float]


@dataclass(frozen=True)
class ReachableRegion:
    """Conservative sphere containing all group centers under bounded acceleration."""
    center: CartesianPosition
    radius_m: float
    time: float


class StatisticalGroup(ObjectInstance):
    """An Encounter ObjectInstance whose internal population is still statistical.

    The root and household CDFs determine coherent counts. Neither counts nor
    individual positions are sampled until requested.  Derived household
    totals are stable even when members are materialized in a different order.
    The group footprint is a *modeling bound*, not a solid opaque object.
    """

    CATEGORIES = ("adults", "children", "livestock", "dogs")

    def __init__(self, name, id, config, seed, time=0.0):
        super().__init__(ObjectDefinition("statistical_group", 0, 0, 0, 0, 0, 0, 0),
                         name=name, id=id)
        self.config = config
        self.seed = int(seed)
        self.time = float(time)
        motion = config["motion"]
        self.set_position(CartesianPosition(*_vec(motion["position"], "position")))
        self.velocity = _vec(motion["velocity"], "velocity")
        self.acceleration = _vec(motion["acceleration"], "acceleration")
        self.max_acceleration = float(motion["max_acceleration_mps2"])
        self.footprint_radius = float(motion["footprint_radius_m"])
        if (not math.isfinite(self.max_acceleration) or self.max_acceleration < 0
                or not math.isfinite(self.footprint_radius) or self.footprint_radius <= 0
                or _norm(self.acceleration) > self.max_acceleration + 1e-12):
            raise ValueError("invalid motion limits or spatial footprint")
        self._household_count = None
        self._households = {}
        self._counts = None
        self._members = {}

    def _rng(self, *parts):
        token = "|".join(map(str, (self.seed, self.id, *parts)))
        value = int.from_bytes(hashlib.sha256(token.encode("utf-8")).digest()[:16], "big")
        return random.Random(value)

    @property
    def household_count(self):
        if self._household_count is None:
            self._household_count = _draw_cdf(self.config["composition"]["households_cdf"],
                                              self._rng("household_count"))
        return self._household_count

    def household(self, index):
        if not 0 <= index < self.household_count:
            raise IndexError("household index outside established composition")
        if index not in self._households:
            source = self.config["composition"]["per_household"]
            self._households[index] = {
                category: _draw_cdf(source[category + "_cdf"],
                                    self._rng("household", index, category))
                for category in self.CATEGORIES
            }
        return self._households[index].copy()

    def counts(self):
        """Commit numerical composition without creating any individual Being."""
        if self._counts is None:
            totals = {key: 0 for key in self.CATEGORIES}
            for index in range(self.household_count):
                for key, number in self.household(index).items():
                    totals[key] += number
            totals["humans"] = totals["adults"] + totals["children"]
            totals["households"] = self.household_count
            self._counts = totals
        return self._counts.copy()

    @property
    def materialized_count(self):
        return len(self._members)

    def member(self, household, category, index):
        """Instantiate one member, consistently inside the group's footprint."""
        if category not in self.CATEGORIES:
            raise ValueError("unknown population category")
        if not isinstance(index, int) or not 0 <= index < self.household(household)[category]:
            raise IndexError("member index outside established household count")
        key = (household, category, index)
        if key not in self._members:
            rng = self._rng("member", *key)
            angle = 2 * math.pi * rng.random()
            radius = self.footprint_radius * math.sqrt(rng.random())
            offset = (radius * math.cos(angle), radius * math.sin(angle), 0.0)
            self._members[key] = GroupMember(
                f"{self.id}/{household}/{category}/{index}", household,
                category, index, offset)
        return self._members[key]

    def member_position(self, member):
        if member.id not in {m.id for m in self._members.values()}:
            raise ValueError("member is not realized within this group")
        return CartesianPosition(*(c + v for c, v in zip(self.get_position().as_tuple(),
                                                          member.offset)))

    def advance(self, duration):
        """Exact constant-acceleration step in the current shared Cartesian frame."""
        duration = float(duration)
        if not math.isfinite(duration) or duration < 0:
            raise ValueError("duration must be finite and nonnegative")
        new_position = tuple(p + v * duration + .5 * a * duration**2
                             for p, v, a in zip(self.get_position().as_tuple(),
                                                self.velocity, self.acceleration))
        self.set_position(CartesianPosition(*new_position))
        self.velocity = tuple(v + a * duration for v, a in zip(self.velocity,
                                                               self.acceleration))
        self.time += duration

    def reachable_at(self, time):
        """Conservative future center envelope: unknown |acceleration| <= limit.

        No terrain, navigation, speed cap, or decision model is assumed. This is
        an *outer bound*, not a claim of uniform probability inside the sphere.
        """
        dt = float(time) - self.time
        if not math.isfinite(dt) or dt < 0:
            raise ValueError("target time must be finite and not in the past")
        center = CartesianPosition(*(p + v * dt for p, v in zip(
            self.get_position().as_tuple(), self.velocity)))
        return ReachableRegion(center, .5 * self.max_acceleration * dt * dt, float(time))
