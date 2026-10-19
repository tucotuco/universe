"""Experimental statistical aggregate with partially realized composition and motion.

An aggregate is a real, persistent Encounter Entity even when none of its
members has been materialized.  Sampling is keyed, rather than consuming a
shared random stream, so requesting different details in different orders does
not change the underlying realization.
"""
from __future__ import annotations

from dataclasses import dataclass
from copy import deepcopy
import hashlib
import math
import random

from object import ObjectDefinition, ObjectInstance
from spatial.state import CartesianPosition
from conditional_attributes import ConditionalAttributes


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


@dataclass(frozen=True)
class MembershipTransfer:
    """One historical transfer, referenced by both Group-owned journals.

    Time is expressed in the shared Universe simulation time convention.
    Membership and spatial presence are deliberately independent.
    """
    time: float
    being_id: str
    category: str
    source_group_id: str
    destination_group_id: str

    def to_dict(self):
        return dict(time=self.time, being_id=self.being_id,
                    category=self.category, source_group_id=self.source_group_id,
                    destination_group_id=self.destination_group_id)


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
        # A GroupMember records stable identity; only selected members become Beings.
        self._realized_beings = {}
        # Original cohort is immutable; current membership is a separate layer.
        # Departures from the original cohort never delete historical provenance.
        self._departed_member_ids = set()
        # Arrivals are already realized Beings, indexed by stable global identity.
        self._incoming_beings = {}  # member_id -> (BeingInstance, category)
        self.membership_history = []
        # Group motion is not implied by affiliation. Pre-existing native members
        # accompany the group until they depart; arrivals do not automatically do so.
        self._motion_attached_native_ids = set()
        # A formation-time quota is a commitment about the original cohort,
        # not the member's current learned capability. Freeze configuration
        # so later caller edits cannot retrospectively rewrite that cohort.
        self._formation_traits = deepcopy(config.get("formation_traits", {}))
        attribute_specs = deepcopy(config.get("formation_attributes", {}))
        if not isinstance(attribute_specs, dict) or set(attribute_specs) - {"adults"}:
            raise ValueError("formation attributes currently support adults only")
        adult_specs = attribute_specs.get("adults", {})
        traits = self._formation_traits.get("adults", {})
        self._conditional_attributes = ConditionalAttributes(
            adult_specs,
            lambda member_id, attribute: self._rng("formation_attribute", member_id, attribute),
            external_names=traits.keys(),
        )

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

    def _adult_formation_assignments(self, trait_name):
        """Return latent, stable member IDs satisfying one exact cohort quota.

        Uses keyed pseudo-random priorities rather than realization order.
        Enumerating candidate keys does NOT instantiate GroupMembers/Beings.
        The whole-cohort sort is intentionally limited to this small experiment;
        a scalable exact-quota selector will be needed for enormous groups.
        """
        specifications = self._formation_traits
        if not isinstance(specifications, dict) or set(specifications) - {"adults"}:
            raise ValueError("formation traits currently support adults only")
        traits = specifications.get("adults", {})
        if not isinstance(traits, dict) or trait_name not in traits:
            raise ValueError("unknown adult formation trait")
        spec = traits[trait_name]
        if not isinstance(spec, dict):
            raise ValueError("formation trait specification must be a mapping")
        quota = spec.get("count")
        if isinstance(quota, bool) or not isinstance(quota, int) or quota < 0:
            raise ValueError("formation trait count must be a nonnegative integer")
        initial_skills = spec.get("initial_skills", {})
        if not isinstance(initial_skills, dict) or any(
            not isinstance(name, str) or not name
            or isinstance(level, bool) or not isinstance(level, int) or level < 0
            for name, level in initial_skills.items()
        ):
            raise ValueError("initial_skills must be nonnegative integer skill levels")
        candidates = [
            f"{self.id}/{household}/adults/{index}"
            for household in range(self.household_count)
            for index in range(self.household(household)["adults"])
        ]
        if quota > len(candidates):
            raise ValueError("formation trait quota exceeds committed adult cohort")
        ranked = sorted(candidates, key=lambda identifier: (
            self._rng("formation_trait", trait_name, identifier).random(), identifier
        ))
        return frozenset(ranked[:quota])

    def formation_trait_state(self, trait_name):
        """Original adult trait quota conditioned on realized identities.

        No unresolved member is instantiated. The unresolved qualified count is
        an exact constraint, not an estimate of current skill or health.
        """
        qualified = self._adult_formation_assignments(trait_name)
        realized = set(self._realized_beings)
        if not realized.issubset({
            f"{self.id}/{household}/adults/{index}"
            for household in range(self.household_count)
            for index in range(self.household(household)["adults"])
        }):
            raise RuntimeError("realized member is outside original adult cohort")
        committed_adults = self.counts()["adults"]
        realized_qualified = len(realized & qualified)
        unresolved_qualified = len(qualified) - realized_qualified
        return {
            "trait": trait_name,
            "committed_qualified": len(qualified),
            "realized_qualified": realized_qualified,
            "realized_other": len(realized) - realized_qualified,
            "unresolved_qualified": unresolved_qualified,
            "unresolved_other": committed_adults - len(realized) - unresolved_qualified,
        }

    def formation_attribute(self, household, category, index, attribute):
        """Commit a correlated formation fact without realizing a Being/member.

        Fixed formation quotas, when configured, are already committed facts
        that may serve as conditions for sampling other characteristics.
        These original attributes never change when a Being later develops.
        """
        if category != "adults":
            raise NotImplementedError("conditional attributes currently support adults")
        if (isinstance(household, bool) or not isinstance(household, int)
                or not 0 <= household < self.household_count
                or isinstance(index, bool) or not isinstance(index, int)
                or not 0 <= index < self.household(household)["adults"]):
            raise IndexError("adult identity outside committed cohort")
        identity = f"{self.id}/{household}/adults/{index}"
        traits = self._formation_traits.get("adults", {})
        external = {name: identity in self._adult_formation_assignments(name)
                    for name in traits}
        return self._conditional_attributes.resolve(identity, attribute, external)

    def committed_formation_attributes(self, household, category, index):
        """Return previously realized attributes without generating details."""
        if category != "adults":
            raise NotImplementedError("conditional attributes currently support adults")
        # Validate the identity without triggering sampling or Being creation.
        if (isinstance(household, bool) or not isinstance(household, int)
                or not 0 <= household < self.household_count
                or isinstance(index, bool) or not isinstance(index, int)
                or not 0 <= index < self.household(household)["adults"]):
            raise IndexError("adult identity outside committed cohort")
        return self._conditional_attributes.committed(
            f"{self.id}/{household}/adults/{index}")

    def _initial_skills_for_adult(self, member_id, skill_dictionary):
        """Select formation-time attributes before a Being is registered."""
        skills = {}
        traits = self._formation_traits.get("adults", {})
        if not isinstance(traits, dict):
            raise ValueError("adult formation traits must be a mapping")
        for trait_name, spec in sorted(traits.items()):
            # Check every configured quota, even if this member is not selected.
            # This prevents malformed formation specifications staying hidden.
            assigned = self._adult_formation_assignments(trait_name)
            for name in spec.get("initial_skills", {}):
                if skill_dictionary.get_skill_definition(name) is None:
                    raise ValueError(f"unknown formation skill: {name}")
            if member_id in assigned:
                for name, level in spec.get("initial_skills", {}).items():
                    if name in skills and skills[name] != level:
                        raise ValueError("conflicting initial skill levels across traits")
                    skills[name] = level
        return skills

    @property
    def realized_being_count(self):
        """Number of members promoted to full BeingInstances, not identities."""
        return len(self._realized_beings)

    def realize_being(self, universe, household, category, index, name=None):
        """Promote one *adult human* to the existing Universe Being model.

        Identity and initial placement come from the group's committed member
        key, not from a fresh random draw. Subsequent calls return the same
        mutable BeingInstance so its actions, skills, and history survive.
        The other members remain statistical. Other categories require their
        own appropriate biological/age definitions and are not silently mapped
        to an adult Human.
        """
        from being import BeingInstance
        from universe import Universe

        if not isinstance(universe, Universe) or universe.get_object_by_id(self.id) is not self:
            raise ValueError("the statistical group must be registered in this Universe")
        if category not in self.CATEGORIES:
            raise ValueError("unknown population category")
        if category != "adults":
            raise NotImplementedError("Being definitions for children and animals are not yet configured")
        # Validate first, without creating a member or changing population counts.
        if not isinstance(household, int) or isinstance(household, bool):
            raise TypeError("household must be an integer index")
        if not isinstance(index, int) or isinstance(index, bool):
            raise TypeError("member index must be an integer")
        if not 0 <= index < self.household(household)[category]:
            raise IndexError("member index outside established household count")
        identifier = f"{self.id}/{household}/{category}/{index}"
        existing_being = self._realized_beings.get(identifier)
        if existing_being is not None:
            if universe.get_object_by_id(identifier) is not existing_being:
                raise ValueError("realized Being is missing or replaced in Universe registry")
            if name is not None and name != existing_being.name:
                raise ValueError("a realized Being cannot be renamed by materialization")
            return existing_being
        if universe.get_object_by_id(identifier) is not None:
            raise ValueError("member identity conflicts with an existing Universe Entity")
        definition = universe.get_being_definition("Human")
        if definition is None:
            raise ValueError("the Universe has no Human BeingDefinition")
        # Validate the entire formation rule before creating or registering an
        # individual. Traits constrain initial capabilities, not lifetime state.
        initial_skills = self._initial_skills_for_adult(
            identifier, universe.get_skill_dictionary())

        member = self.member(household, category, index)
        being = BeingInstance(definition, name=name or f"Member {household}:{index}")
        being.id = member.id  # stable identity predates the Being's full realization
        being.set_position(self.member_position(member))
        for skill_name, level in initial_skills.items():
            being.set_skill_level(universe.get_skill_dictionary(), skill_name, level)
        universe.add_object(being)
        if universe.get_object_by_id(member.id) is not being:
            raise RuntimeError("could not register realized Being")
        self._realized_beings[member.id] = being
        self._motion_attached_native_ids.add(member.id)
        return being

    def _current_realized_members(self):
        """Current realized members, keyed by identity, with their categories.

        This is not a full listing of members: unresolved original-cohort people
        remain represented by aggregate counts rather than individual objects.
        """
        native = {member.id: member.category for member in self._members.values()}
        current = {
            identity: (being, native[identity])
            for identity, being in self._realized_beings.items()
            if identity not in self._departed_member_ids
        }
        for identity, entry in self._incoming_beings.items():
            if identity in current:
                raise RuntimeError("duplicate current Group membership")
            current[identity] = entry
        return current

    def has_realized_member(self, being_or_id):
        """Test current membership of an *already realized* Being only."""
        identity = getattr(being_or_id, "id", being_or_id)
        return identity in self._current_realized_members()

    def current_counts(self):
        """Current membership counts, separate from formation-time counts().

        Membership transitions affect adults only in this experiment. An adult
        arrival/departure does not itself establish or dissolve a household.
        """
        counts = self.counts()
        counts['adults'] += (len(self._incoming_beings)
                             - len(self._departed_member_ids))
        counts['humans'] = counts['adults'] + counts['children']
        return counts

    def transfer_being_to(self, universe, being, destination, time=None):
        """Transfer a realized adult between Group-owned memberships.

        One validated operation changes both groups, and the *same immutable*
        transfer record appears in both journals. The Being's registry entry,
        identity, history, skills, and 3D position are not modified. This first
        experiment does not implement eligibility or overlapping membership.
        """
        from being import BeingInstance
        from universe import Universe
        if (not isinstance(universe, Universe)
                or not isinstance(destination, StatisticalGroup)
                or destination is self
                or universe.get_object_by_id(self.id) is not self
                or universe.get_object_by_id(destination.id) is not destination):
            raise ValueError("source and destination must be distinct registered Groups in the same Universe")
        if (not isinstance(being, BeingInstance)
                or universe.get_object_by_id(being.id) is not being):
            raise ValueError("Being must exist in the shared Universe registry")
        source_members = self._current_realized_members()
        entry = source_members.get(being.id)
        if entry is None or entry[0] is not being:
            raise ValueError("Being is not a current realized member of source Group")
        if destination.has_realized_member(being):
            raise ValueError("Being is already a current member of destination Group")
        category = entry[1]
        if category != "adults":
            raise NotImplementedError("membership transfer currently supports adult Beings only")
        if self.time != destination.time:
            raise ValueError("Groups must have the same current simulation time for transfer")
        now = self.time if time is None else float(time)
        if not math.isfinite(now) or now != self.time:
            raise ValueError("transfer must occur at the Groups' current simulation time")
        # Preflight: receiving the Being must correspond to either a returning
        # native member or a new incoming member, never an identity collision.
        returning = being.id in destination._realized_beings
        if returning and being.id not in destination._departed_member_ids:
            raise ValueError("destination's native identity is not departed")
        if returning and destination._realized_beings[being.id] is not being:
            raise ValueError("returning Being identity conflicts with destination history")
        record = MembershipTransfer(now, being.id, category, self.id, destination.id)
        # Commit both membership changes only after the complete preflight.
        if being.id in self._realized_beings:
            self._departed_member_ids.add(being.id)
        else:
            del self._incoming_beings[being.id]
        self._motion_attached_native_ids.discard(being.id)
        if returning:
            destination._departed_member_ids.remove(being.id)
        else:
            destination._incoming_beings[being.id] = (being, category)
        self.membership_history.append(record)
        destination.membership_history.append(record)
        return record

    def aggregate_state(self):
        """Live, *derived* group view of known individual state.

        ``counts()`` is the committed original composition; ``current_counts()``
        reflects membership transfers. Neither assumes that dead members have
        departed. Unresolved members have no fabricated health/activity state.
        Health categories overlap:
        incapacitated and injured are subsets of known_living, not additional
        members. Calling this does not cache or copy a Being's mutable state.
        """
        composition = self.counts()
        current = self.current_counts()
        categories = {}
        for category in self.CATEGORIES:
            categories[category] = dict(
                committed=composition[category],
                current=current[category],
                realized=0,
                unresolved=current[category],
                known_living=0,
                known_dead=0,
                known_incapacitated=0,
                known_injured=0,
            )
        for member_id, (being, category) in self._current_realized_members().items():
            summary = categories[category]
            summary['realized'] += 1
            summary['unresolved'] -= 1
            hp = being.get_hit_points()
            if being.is_dead():
                summary['known_dead'] += 1
            else:
                summary['known_living'] += 1
                if hp <= 0:
                    summary['known_incapacitated'] += 1
                if hp < being.original.hit_points:
                    summary['known_injured'] += 1
        return {'composition': composition, 'current_composition': current,
                'categories': categories}

    def known_skill_state(self, skill_name):
        """Realized members' current capability, not a whole-group estimate.

        Unresolved member skills are genuinely unknown; do not interpret the
        known levels or earned experience as a representative group average.
        Only current Group members are included, not historical departures.
        """
        if not isinstance(skill_name, str) or not skill_name:
            raise ValueError("skill_name must be a nonempty string")
        known = {}
        for member_id, (being, category) in sorted(self._current_realized_members().items()):
            level = being.get_skill_level(skill_name)
            if level is None:
                level = being.get_weapon_skill_level(skill_name)
            known[member_id] = {
                'level': level or 0,
                'practice_experience': being.get_skill_experience(skill_name),
            }
        return {
            'skill': skill_name,
            'known': known,
            'unresolved_adults': self.current_counts()['adults'] - len(known),
        }

    def member_position(self, member):
        if member.id not in {m.id for m in self._members.values()}:
            raise ValueError("member is not realized within this group")
        # Once a Being is realized its continuous position is authoritative:
        # Encounter actions may change it relative to the group's original offset.
        if member.id in self._realized_beings:
            return self._realized_beings[member.id].get_position()
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
        old_position = self.get_position().as_tuple()
        delta = tuple(new - old for new, old in zip(new_position, old_position))
        self.set_position(CartesianPosition(*new_position))
        # Only members explicitly attached to the group's ongoing movement
        # accompany it. Transfer never teleports a Being or assumes presence.
        for identity in self._motion_attached_native_ids:
            being = self._realized_beings[identity]
            previous = being.get_position().as_tuple()
            being.set_position(CartesianPosition(*(p + d for p, d in zip(previous, delta))))
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
