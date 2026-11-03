"""Inactive, pure candidates for realizing an already-counted adult Group member.

Candidate preparation never constructs or registers a Being. It captures the
native deterministic slot data and Encounter read set. The publisher-only
helper can construct a detached Being after revalidation, still before writes.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

from spatial.state import CartesianPosition
from statistical_group import (
    StatisticalGroup,
    composition_rng,
    validate_composition_records,
)


class GroupMemberCandidateRejected(ValueError):
    """The request is not a supported, currently valid adult-slot candidate."""


class StaleGroupMemberCandidate(GroupMemberCandidateRejected):
    """A candidate's captured Encounter or Group dependencies have changed."""


@dataclass(frozen=True)
class AdultMemberGeometryDescriptor:
    """Optional scenario-supplied sphere geometry for one adult candidate.

    This is an explicit modeling premise, not a default body shape for Human
    Beings. Keeping only the validated radius in the candidate avoids retaining
    caller-owned geometry objects or mutable world references.
    """

    sphere_radius: float

    def __post_init__(self):
        value = self.sphere_radius
        if type(value) not in (int, float):
            raise TypeError("sphere_radius must be a finite positive number")
        value = float(value)
        if not math.isfinite(value) or value <= 0.0:
            raise ValueError("sphere_radius must be finite and positive")
        object.__setattr__(self, "sphere_radius", value)


@dataclass(frozen=True)
class AdultMemberRequest:
    """A request bound to one Group slot and prospective publication boundary."""

    group_id: str
    household: int
    category: str
    index: int
    publication_boundary: int
    name: str | None = None
    geometry: AdultMemberGeometryDescriptor | None = None
    # Explicit world-authored assertion that this already-counted population
    # slot is the same logical Person as an established reproductive offspring.
    # A key is required so the native identity binding is idempotent/auditable.
    reproductive_person_id: str | None = None
    reproduction_request_key: str | None = None


@dataclass(frozen=True)
class AdultMemberCandidate:
    """Detached immutable proposal; contains no Being or mutable world reference."""

    request: AdultMemberRequest
    request_identity: int
    encounter_id: str
    encounter_identity: int
    universe_identity: int
    group_identity: int
    member_id: str
    display_name: str
    definition_name: str
    definition_identity: int
    skill_dictionary_identity: int
    member_offset: tuple[float, float, float]
    initial_position: CartesianPosition
    initial_skills: tuple[tuple[str, int], ...]
    geometry: AdultMemberGeometryDescriptor | None
    formation_counts: tuple[tuple[str, int], ...]
    composition_revision: int
    first_eligible_boundary: int
    read_dependencies: tuple
    prospective_write_set: tuple[str, ...]
    prospective_rollback_obligations: tuple[str, ...]
    reproduction_registry_identity: int | None
    reproduction_registry_revision: int | None
    reproduction_group_id: str | None
    reproduction_binding_ids: tuple
    reproduction_request_records: tuple


PROSPECTIVE_WRITE_SET = (
    "Universe.object_registry.object_instances[member_id] = prepared Being",
    "StatisticalGroup._members[slot] = deterministic GroupMember (only if absent)",
    "StatisticalGroup._realized_beings[member_id] = same Being object",
    "StatisticalGroup._motion_attached_native_ids.add(member_id)",
    "Encounter.being_list append member_id",
    "when explicitly requested: ReproductionGroupRegistry._native_beings_by_person_id[member_id] = same Being",
    "when explicitly requested: ReproductionGroupRegistry._native_being_requests[request_key] = binding record",
)

PROSPECTIVE_ROLLBACK_OBLIGATIONS = (
    "remove the registry key only if it still names the exact inserted Being",
    "remove the Group member only if this publication inserted it; remove the realized-Being entry only if it still matches",
    "remove the motion attachment only if it was added by this publication",
    "restore Encounter.being_list contents in place, preserving list identity and order",
    "preserve Universe registry and Group mapping/set identities and all pre-existing aliases",
    "when explicitly requested: restore both ReproductionGroup native-binding dictionaries in place",
)


def _construct_detached_adult(candidate, encounter, group):
    """Construct native Being/GroupMember values, with no authoritative writes.

    Called by the publisher while it owns the complete authority closure and
    before building/applying any writes. The optional Being ID avoids the
    ordinary UUID-generation path; all other initialization uses native APIs.
    """
    validate_adult_member_candidate(encounter, group, candidate)
    world = encounter.universe
    definition = world.get_being_definition(candidate.definition_name)
    skills = world.get_skill_dictionary()
    if (id(definition) != candidate.definition_identity
            or id(skills) != candidate.skill_dictionary_identity):
        raise StaleGroupMemberCandidate("native Being or skill definition changed")
    from being import BeingInstance
    from statistical_group import GroupMember

    being = BeingInstance(definition, name=candidate.display_name, id=candidate.member_id)
    being.set_position(candidate.initial_position)
    if candidate.geometry is not None:
        from spatial.geometry import Sphere
        being.set_geometry(Sphere(candidate.geometry.sphere_radius))
    for skill_name, level in candidate.initial_skills:
        being.set_skill_level(skills, skill_name, level)
    if (being.id != candidate.member_id
            or being.get_position() != candidate.initial_position
            or (candidate.geometry is None and being.geometry is not None)
            or (candidate.geometry is not None
                and being.geometry.to_dict() != {
                    "type": "sphere",
                    "radius": candidate.geometry.sphere_radius,
                })
            or any(being.current.skills.skills.get(skill_name) != level
                   for skill_name, level in candidate.initial_skills)):
        raise GroupMemberCandidateRejected("detached Being differs from candidate initialization")
    member = GroupMember(candidate.member_id, candidate.request.household, "adults",
                         candidate.request.index, candidate.member_offset)
    return being, member


def _reject(condition, message):
    if not condition:
        raise GroupMemberCandidateRejected(message)


def _composition(group):
    """Read a complete, already-committed composition without asking Reality."""
    records = group._composition_reality.view().all_facts()
    validate_composition_records(group.id, group.formation_time, records)
    from realization import FactKey

    values = {record.key: record.value for record in records}
    root_key = FactKey(group.id, "household_count", group.formation_time)
    _reject(root_key in values, "Group composition must already be committed")
    household_count = values[root_key]
    _reject(type(household_count) is int and household_count > 0,
            "Group must have a committed household count")
    household_values = []
    totals = {category: 0 for category in group.CATEGORIES}
    for household in range(household_count):
        key = FactKey(group.id, "household", group.formation_time, str(household))
        _reject(key in values, "Group composition is incomplete")
        composition = values[key]
        household_values.append(tuple((category, composition[category])
                                      for category in group.CATEGORIES))
        for category in group.CATEGORIES:
            totals[category] += composition[category]
    totals["humans"] = totals["adults"] + totals["children"]
    totals["households"] = household_count
    committed = group.__dict__.get("_counts")
    _reject(type(committed) is dict and committed == totals,
            "Group count cache is not the committed composition")
    return household_count, tuple(household_values), tuple(sorted(totals.items()))


def _adult_initial_skills(group, member_id, skill_dictionary, household_values):
    """Reproduce the native exact-quota rule from committed facts, without writes."""
    traits = group._formation_traits
    _reject(type(traits) is dict and not (set(traits) - {"adults"}),
            "only native adult formation traits are supported")
    adult_traits = traits.get("adults", {})
    _reject(type(adult_traits) is dict, "adult formation traits must be a mapping")
    adult_ids = tuple(
        f"{group.id}/{household}/adults/{index}"
        for household, composition in enumerate(household_values)
        for index in range(dict(composition)["adults"])
    )
    skills = {}
    for trait_name, specification in sorted(adult_traits.items()):
        _reject(type(trait_name) is str and trait_name,
                "formation trait names must be nonempty strings")
        _reject(type(specification) is dict,
                "formation trait specification must be a mapping")
        quota = specification.get("count")
        _reject(type(quota) is int and quota >= 0,
                "formation trait count must be a nonnegative integer")
        initial = specification.get("initial_skills", {})
        _reject(type(initial) is dict and all(
            type(name) is str and name and type(level) is int and level >= 0
            for name, level in initial.items()),
            "formation initial skills must be nonnegative integer levels")
        _reject(quota <= len(adult_ids),
                "formation trait quota exceeds committed adult cohort")
        ranked = sorted(adult_ids, key=lambda identifier: (
            composition_rng(group.seed, group.id, "formation_trait",
                            trait_name, identifier).random(), identifier
        ))
        if member_id in frozenset(ranked[:quota]):
            for skill_name, level in initial.items():
                _reject(skill_dictionary.get_skill_definition(skill_name) is not None,
                        f"unknown formation skill: {skill_name}")
                _reject(skill_name not in skills or skills[skill_name] == level,
                        "conflicting initial skill levels across traits")
                skills[skill_name] = level
        else:
            # Preserve the native realization rule's eager definition check for
            # every configured initial skill, including unselected traits.
            for skill_name in initial:
                _reject(skill_dictionary.get_skill_definition(skill_name) is not None,
                        f"unknown formation skill: {skill_name}")
    return tuple(sorted(skills.items()))


def _build(encounter, group, request):
    from encounter import Encounter
    from universe import Universe
    from being import BeingDefinition

    _reject(type(encounter) is Encounter, "only native Encounter instances are supported")
    _reject(type(group) is StatisticalGroup,
            "only native StatisticalGroup instances are supported")
    _reject(type(request) is AdultMemberRequest, "invalid adult-member request")
    from interval_staging import _read_set
    initial_read_dependencies = _read_set(encounter)
    _reject(type(request.group_id) is str and request.group_id == group.id,
            "request refers to a different Group")
    _reject(type(request.household) is int and request.household >= 0,
            "household must be a nonnegative integer")
    _reject(type(request.index) is int and request.index >= 0,
            "member index must be a nonnegative integer")
    _reject(request.category == "adults", "only adult Human slots are supported")
    _reject(request.name is None or type(request.name) is str,
            "Being name must be a string or None")
    _reject(request.geometry is None
            or type(request.geometry) is AdultMemberGeometryDescriptor,
            "geometry must be an AdultMemberGeometryDescriptor or None")
    _reject(request.reproductive_person_id is None
            or (type(request.reproductive_person_id) is str
                and request.reproductive_person_id.strip()),
            "reproductive_person_id must be nonempty text or None")
    _reject(request.reproduction_request_key is None
            or (type(request.reproduction_request_key) is str
                and request.reproduction_request_key.strip()),
            "reproduction_request_key must be nonempty text or None")
    _reject((request.reproductive_person_id is None)
            == (request.reproduction_request_key is None),
            "reproductive identity and request key must be supplied together")
    _reject(type(request.publication_boundary) is int and request.publication_boundary > 0,
            "publication boundary must be a positive integer")

    world = encounter.universe
    _reject(type(world) is Universe, "only native Universe instances are supported")
    _reject(group.id in world.object_registry.object_instances
            and world.get_object_by_id(group.id) is group,
            "Group is not registered in the Encounter's Universe")
    _reject(group.id in encounter.non_being_object_list,
            "Group is not a participant in this Encounter")
    _reject(encounter.progression_mode == "transactional",
            "candidate requires an explicitly transactional Encounter")
    _reject(encounter.initiated and encounter.boundary_fault is None
            and not encounter._advancing and not encounter._dispatching
            and not encounter._running,
            "Encounter is uninitiated, faulted, or reentrant")
    publication_boundary = (encounter.active_boundary if encounter.active_boundary is not None
                            else encounter.last_processed_boundary + 1)
    _reject(request.publication_boundary == publication_boundary,
            "request publication boundary is stale or does not match Encounter")

    household_count, household_values, formation_counts = _composition(group)
    _reject(request.household < household_count,
            "household index outside committed composition")
    household = dict(household_values[request.household])
    _reject(request.index < household["adults"],
            "adult member index outside committed household count")
    member_id = f"{group.id}/{request.household}/adults/{request.index}"
    slot = (request.household, "adults", request.index)
    _reject(member_id not in group._realized_beings,
            "adult slot is already realized")
    _reject(member_id not in group._motion_attached_native_ids
            and member_id not in group._departed_member_ids
            and member_id not in group._incoming_beings,
            "adult identity already has conflicting Group state")
    cached_member = group._members.get(slot)
    _reject(member_id not in world.object_registry.object_instances,
            "stable member identity collides with a Universe Object")
    _reject(member_id not in encounter.being_list,
            "stable member identity already participates in Encounter")
    _reject(member_id not in encounter.non_being_object_list,
            "stable member identity conflicts with an Encounter Object")
    _reject(member_id not in encounter.awareness,
            "stable member identity already has Encounter awareness state")

    reproduction_registry_identity = None
    reproduction_registry_revision = None
    reproduction_group_id = None
    reproduction_binding_ids = ()
    reproduction_request_records = ()
    reproduction = world._reproduction_group_registry
    if request.reproductive_person_id is None:
        _reject(member_id not in reproduction._person_id_reservations,
                "reserved reproductive identity requires an explicit matching offspring association")
    if request.reproductive_person_id is not None:
        _reject(request.reproductive_person_id == member_id,
                "authored reproductive identity must equal the selected stable Group-member identity")
        _reject(reproduction._world is world,
                "ReproductionGroup registry is not owned by this Universe")
        try:
            reproduction._assert_consistent()
        except (RuntimeError, ValueError, TypeError) as exc:
            raise GroupMemberCandidateRejected(
                f"ReproductionGroup identity state is inconsistent: {exc}") from exc
        _reject(member_id in reproduction._group_id_by_offspring,
                "explicit reproductive identity is not an established offspring")
        reproduction_group_id = reproduction._canonical_group_id_unlocked(
            reproduction._group_id_by_offspring[member_id])
        _reject(reproduction_group_id in reproduction._groups_by_id,
                "established offspring has no canonical ReproductionGroup")
        _reject(member_id not in reproduction._native_beings_by_person_id,
                "logical offspring already has a native Being binding")
        key = request.reproduction_request_key
        _reject(key not in reproduction._native_being_requests,
                "native Being binding request key is already used")
        _reject(key not in (set(reproduction._requests)
                            | set(reproduction._generation_requests)
                            | set(reproduction._progressive_requests)),
                "request key is already used by a ReproductionGroup publication")
        _reject(member_id in reproduction._person_id_reservations,
                "established offspring identity is not reserved by reproduction state")
        reproduction_registry_identity = id(reproduction)
        reproduction_registry_revision = reproduction._revision
        reproduction_binding_ids = tuple(sorted(
            (identity, id(being))
            for identity, being in reproduction._native_beings_by_person_id.items()))
        reproduction_request_records = tuple(sorted(
            (key, record.person_id, record.normalized_request, id(record.being))
            for key, record in reproduction._native_being_requests.items()))

    definition = world.get_being_definition("Human")
    _reject(isinstance(definition, BeingDefinition),
            "the Universe has no native Human BeingDefinition")
    skills_dict = world.get_skill_dictionary()
    _reject(skills_dict is not None, "the Universe has no native SkillDictionary")

    # This is the exact keyed placement rule in StatisticalGroup.member(),
    # evaluated locally. It does not populate the Group member cache or touch
    # the Encounter/authoritative RNG.
    rng = composition_rng(group.seed, group.id, "member", *slot)
    angle = 2 * math.pi * rng.random()
    radius = group.footprint_radius * math.sqrt(rng.random())
    offset = (radius * math.cos(angle), radius * math.sin(angle), 0.0)
    if cached_member is not None:
        _reject(cached_member.id == member_id
                and cached_member.household == request.household
                and cached_member.category == "adults"
                and cached_member.index == request.index
                and cached_member.offset == offset,
                "cached GroupMember conflicts with deterministic adult slot")
    group_position = group.get_position().as_tuple()
    position = CartesianPosition(*(value + delta
                                   for value, delta in zip(group_position, offset)))
    initial_skills = _adult_initial_skills(
        group, member_id, skills_dict, household_values)

    read_dependencies = _read_set(encounter)
    if read_dependencies != initial_read_dependencies:
        raise StaleGroupMemberCandidate("Encounter or Group changed during candidate preparation")
    return AdultMemberCandidate(
        request=request,
        request_identity=id(request),
        encounter_id=encounter.id,
        encounter_identity=id(encounter),
        universe_identity=id(world),
        group_identity=id(group),
        member_id=member_id,
        display_name=request.name or f"Member {request.household}:{request.index}",
        definition_name="Human",
        definition_identity=id(definition),
        skill_dictionary_identity=id(skills_dict),
        member_offset=offset,
        initial_position=position,
        initial_skills=initial_skills,
        geometry=request.geometry,
        formation_counts=formation_counts,
        composition_revision=group._composition_reality.revision,
        first_eligible_boundary=request.publication_boundary + 1,
        read_dependencies=initial_read_dependencies,
        prospective_write_set=PROSPECTIVE_WRITE_SET,
        prospective_rollback_obligations=PROSPECTIVE_ROLLBACK_OBLIGATIONS,
        reproduction_registry_identity=reproduction_registry_identity,
        reproduction_registry_revision=reproduction_registry_revision,
        reproduction_group_id=reproduction_group_id,
        reproduction_binding_ids=reproduction_binding_ids,
        reproduction_request_records=reproduction_request_records,
    )


def prepare_adult_member_candidate(encounter, group, request):
    """Prepare an immutable, non-publishing candidate for one existing adult slot."""
    candidate = _build(encounter, group, request)
    # Detect concurrent or callback-driven drift during the read-only capture.
    from interval_staging import _read_set
    if _read_set(encounter) != candidate.read_dependencies:
        raise StaleGroupMemberCandidate("Encounter or Group changed during candidate preparation")
    return candidate


def validate_adult_member_candidate(encounter, group, candidate):
    """Revalidate captured identities, slot facts, and the full native read set."""
    if type(candidate) is not AdultMemberCandidate:
        raise GroupMemberCandidateRejected("unsupported adult-member candidate")
    if id(candidate.request) != candidate.request_identity:
        raise StaleGroupMemberCandidate("adult-member request identity changed")
    from interval_staging import _read_set
    if _read_set(encounter) != candidate.read_dependencies:
        raise StaleGroupMemberCandidate("adult-member candidate read dependencies are stale")
    rebuilt = _build(encounter, group, candidate.request)
    if rebuilt != candidate:
        raise StaleGroupMemberCandidate("adult-member candidate no longer matches native state")
    return candidate
