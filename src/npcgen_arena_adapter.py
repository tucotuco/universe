"""Direct npcgen Arena candidate generation and bounded native Being import.

Only fields with an explicit source-to-native mapping are overlaid on an exact
native race-template match. Generator class/level facts and the full source
record remain provenance; no class mechanics or skill practice are inferred.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math

from abilities import Abilities
from being import BeingDefinition, BeingInstance
from skill import Skills
from universe import Universe


_ABILITY_ORDER = ("Str", "Int", "Wis", "Dex", "Con", "Cha")
_ABILITY_KEYWORDS = {
    "Str": "strength", "Int": "intelligence", "Wis": "wisdom",
    "Dex": "dexterity", "Con": "constitution", "Cha": "charisma",
}


class ArenaNPCRefusal(ValueError):
    """Structured, fail-closed refusal before a candidate is registered."""

    def __init__(self, code: str, message: str, *, details: dict | None = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(f"{code}: {message}")

    def to_dict(self) -> dict:
        return {"code": self.code, "message": self.message, "details": dict(self.details)}


@dataclass(frozen=True)
class ArenaNativeBeing:
    """A registered native Being plus the complete immutable Generator record."""

    being: BeingInstance
    source_record_bytes: bytes
    source_sha256: str
    engine_identity: dict
    skills_status: dict


def _refuse(code: str, message: str, **details):
    raise ArenaNPCRefusal(code, message, details=details)


def _positive_measure(value, field: str) -> float:
    if type(value) not in (int, float):
        _refuse("invalid_generator_record", f"{field} must be a finite positive number", field=field)
    result = float(value)
    if not math.isfinite(result) or result <= 0:
        _refuse("invalid_generator_record", f"{field} must be a finite positive number", field=field)
    return result


def _rank_entries(value, field: str) -> tuple[tuple[str, int], ...]:
    if type(value) is not dict:
        _refuse("invalid_generator_record", f"{field} must be a rank object", field=field)
    if any(type(name) is not str for name in value):
        _refuse("invalid_generator_record", f"{field} keys must be text", field=field)
    rows = []
    for name, rank in sorted(value.items()):
        if type(name) is not str or not name.strip() or type(rank) is not int or rank <= 0:
            _refuse("invalid_generator_record", f"{field} must contain named positive integer ranks",
                    field=field, skill=name)
        rows.append((name, rank))
    return tuple(rows)


def _validate_record(universe: Universe, candidate, requested_xp: int, seed: int,
                     cost_modifiers: str, api):
    """Validate generation semantics and every mapped field before construction."""
    record = candidate.record
    if type(record) is not dict or record.get("format") != "npcgen-npc" or record.get("schema_version") != 2:
        _refuse("unsupported_record", "expected the current npcgen-npc schema v2 record")
    identity = record.get("engine")
    installed_identity = api.engine_identity()
    if type(identity) is not dict or identity != installed_identity:
        _refuse("engine_identity_mismatch", "candidate engine identity differs from the installed npcgen package")

    generation = record.get("generation")
    state = record.get("state")
    sheet = record.get("sheet")
    if type(generation) is not dict or type(state) is not dict or type(sheet) is not dict:
        _refuse("invalid_generator_record", "generation, state, and sheet objects are required")
    if (type(generation.get("seed")) is not int or generation.get("seed") != seed
            or type(state.get("seed")) is not int or state.get("seed") != seed):
        _refuse("generation_mismatch", "candidate seed does not match the requested seed")
    if (type(generation.get("starting_experience")) is not int
            or generation.get("starting_experience") != requested_xp
            or generation.get("starting_experience_meaning") != "arena-starting-total"):
        _refuse("experience_mismatch", "Generator record does not preserve the exact requested Arena starting total")
    xp_slots = state.get("xps")
    if type(xp_slots) is not list or any(type(value) is not int or value < 0 for value in xp_slots):
        _refuse("invalid_class_experience", "class XP slots must be nonnegative integers")
    if sum(xp_slots) != requested_xp:
        _refuse("experience_mismatch", "integer class XP slots do not sum to the requested total",
                requested=requested_xp, actual=sum(xp_slots))
    classes, levels = state.get("classes"), state.get("levels")
    if (type(classes) is not list or type(levels) is not list
            or len(classes) != len(xp_slots) or len(levels) != len(xp_slots)):
        _refuse("invalid_class_state", "class, XP, and level arrays must be parallel")
    rules = api.default_rules()
    for slot, (class_id, level) in enumerate(zip(classes, levels)):
        if type(class_id) is not int or not 0 <= class_id < len(rules.classes):
            _refuse("invalid_class_state", "class slot is outside installed Generator rules", slot=slot)
        if type(level) is not int or level < 0:
            _refuse("invalid_class_state", "class levels must be nonnegative integers", slot=slot)

    source_status = generation.get("skill_resolution")
    if (type(source_status) is not dict or source_status.get("policy") != "resolve_skills_by_age"
            or source_status.get("cost_modifiers") != cost_modifiers
            or source_status != candidate.skills_status):
        _refuse("skill_status_mismatch", "candidate skill-resolution status does not match its generation request")
    if source_status.get("status") != "resolved":
        reason = source_status.get("reason")
        reason_text = reason if isinstance(reason, str) else ""
        age_unavailable = (
            "has no starting-skill age class" in reason_text
            and reason_text.startswith("NPC age category ")
        )
        _refuse("skill_profile_unresolved", "Generator did not resolve an age-derived skill profile",
                reason=reason, cost_modifiers=cost_modifiers,
                age=sheet.get("age") if type(sheet.get("age")) is dict else None,
                age_unavailable=age_unavailable)
    source_skills = state.get("skills")
    if type(source_skills) is not dict or set(source_skills) != {"skills", "weapon_skills"}:
        _refuse("skill_profile_unresolved", "resolved candidate must contain ordinary and weapon skill maps")
    if sheet.get("skills") != source_skills:
        _refuse("invalid_generator_record", "sheet.skills disagrees with authoritative state.skills")
    ordinary = _rank_entries(source_skills["skills"], "state.skills.skills")
    weapons = _rank_entries(source_skills["weapon_skills"], "state.skills.weapon_skills")
    library = universe.library
    if (library is None or library.skill_dictionary is None or library.weapon_dictionary is None
            or library.being_dictionary is None):
        _refuse("native_dictionary_unavailable", "Universe Being, skill, and weapon dictionaries must be configured")
    for name, _rank in ordinary:
        if library.skill_dictionary.get_skill_definition(name) is None:
            _refuse("unsupported_skill", "Generator skill has no native definition", skill=name)
    for name, _rank in weapons:
        if (library.weapon_dictionary.get_object_definition(name) is None
                or library.skill_dictionary.get_skill_definition(name) is None):
            _refuse("unsupported_weapon_skill", "Generator weapon rank has no native weapon/skill definition",
                    skill=name)

    scores = state.get("scores")
    sheet_scores = sheet.get("abilities", {}).get("scores") if type(sheet.get("abilities")) is dict else None
    if (type(scores) is not list or len(scores) != len(_ABILITY_ORDER)
            or type(sheet_scores) is not dict or set(sheet_scores) != set(_ABILITY_ORDER)):
        _refuse("invalid_abilities", "six named Generator ability scores are required")
    ability_values = {}
    for key, score in zip(_ABILITY_ORDER, scores):
        if type(score) is not int or score <= 0 or sheet_scores.get(key) != score:
            _refuse("invalid_abilities", "state and sheet ability scores must agree as positive integers",
                    ability=key)
        ability_values[_ABILITY_KEYWORDS[key]] = score

    initial_hp = state.get("hps")
    if type(initial_hp) is not int or initial_hp < 0 or sheet.get("hit_points") != initial_hp:
        _refuse("invalid_hit_points", "state.hps and sheet.hit_points must agree as a nonnegative integer")
    height = _positive_measure(state.get("height"), "state.height")
    weight = _positive_measure(state.get("weight"), "state.weight")
    age = sheet.get("age")
    if (type(age) is not dict or age.get("height_inches") != round(height, 2)
            or age.get("weight_pounds") != round(weight, 2)):
        _refuse("invalid_measurements", "source measurements disagree with their rounded sheet projections")

    race_index = state.get("race")
    race_name = sheet.get("identity", {}).get("race") if type(sheet.get("identity")) is dict else None
    if (type(race_index) is not int or not 0 <= race_index < len(rules.races)
            or rules.races[race_index] != race_name):
        _refuse("invalid_race", "source race index and name do not agree with installed Generator rules")
    if type(state.get("name")) is not str or not state["name"].strip():
        _refuse("invalid_name", "state.name must be nonempty text")

    being_dictionary = library.being_dictionary
    native_names = [name for name in being_dictionary.objects if name.casefold() == race_name.casefold()]
    if len(native_names) != 1:
        _refuse("unsupported_native_race", "source race has no unique case-insensitive native Being definition",
                source_race=race_name, matches=native_names)
    template = being_dictionary.get_object_definition(native_names[0])
    if not isinstance(template, BeingDefinition):
        _refuse("unsupported_native_race", "matched native definition is not a BeingDefinition",
                source_race=race_name, native_type=native_names[0])
    if template.armor_id is not None or template.body_parts:
        _refuse("unsupported_native_template", "native race template has equipment that cannot be mapped")

    return {
        "record": record,
        "record_bytes": api.export_json(candidate.npc).encode("utf-8"),
        "identity": identity,
        "status": dict(source_status),
        "template": template,
        "name": state["name"],
        "height": height,
        "weight": weight,
        "hit_points": initial_hp,
        "experience": requested_xp,
        "abilities": ability_values,
        "ordinary_ranks": ordinary,
        "weapon_ranks": weapons,
    }


def prepare_npcgen_arena_being(universe: Universe, *, seed: int, starting_experience: int,
                               cost_modifiers: str, class_index: int | None = None) -> ArenaNativeBeing:
    """Generate and validate one supported native Being without registry mutation.

    The cost policy is mandatory and passed through unchanged. The supplied
    Universe provides native dictionaries only; the returned Being stays detached.
    """
    if not isinstance(universe, Universe):
        raise TypeError("universe must be a native Universe")
    if type(seed) is not int:
        _refuse("invalid_request", "seed must be an integer")
    if type(starting_experience) is not int or starting_experience < 0:
        _refuse("invalid_request", "starting_experience must be a nonnegative integer")
    if cost_modifiers not in ("neutral", "character"):
        _refuse("invalid_request", "cost_modifiers must explicitly be 'neutral' or 'character'")
    try:
        from npcgen import api
    except ImportError as exc:
        _refuse("npcgen_unavailable", "install the npcgen package before Arena candidate generation",
                error=str(exc))
    try:
        candidate = api.generate_arena_candidate(
            seed, starting_experience, class_index=class_index, cost_modifiers=cost_modifiers)
    except (TypeError, ValueError, IndexError) as exc:
        _refuse("generator_refusal", "npcgen rejected the Arena generation request", error=str(exc))

    fields = _validate_record(universe, candidate, starting_experience, seed, cost_modifiers, api)
    record_bytes = fields["record_bytes"]
    if json.loads(record_bytes) != fields["record"]:
        _refuse("record_mismatch", "npcgen API record and canonical JSON export disagree")

    definition = fields["template"].copy()
    definition.length = fields["height"]
    definition.weight = fields["weight"]
    definition.hit_points = fields["hit_points"]
    definition.experience = fields["experience"]
    definition.abilities = Abilities(**fields["abilities"])
    skills = Skills()
    for skill_name, level in fields["ordinary_ranks"]:
        skills.set_skill_level(universe.library.skill_dictionary, skill_name, level)
    for weapon_name, level in fields["weapon_ranks"]:
        skills.set_weapon_skill_level(universe.library.weapon_dictionary, weapon_name, level)
    definition.skills = skills

    being = BeingInstance(definition, name=fields["name"])
    return ArenaNativeBeing(
        being=being,
        source_record_bytes=record_bytes,
        source_sha256=hashlib.sha256(record_bytes).hexdigest(),
        engine_identity=dict(fields["identity"]),
        skills_status=fields["status"],
    )


def generate_npcgen_arena_being(universe: Universe, *, seed: int, starting_experience: int,
                                cost_modifiers: str, class_index: int | None = None) -> ArenaNativeBeing:
    """Generate through installed ``npcgen.api`` and register one supported native Being."""
    result = prepare_npcgen_arena_being(
        universe, seed=seed, starting_experience=starting_experience,
        cost_modifiers=cost_modifiers, class_index=class_index)
    if universe.get_object_by_id(result.being.id) is not None:
        _refuse("native_identity_collision", "generated native Being identity already exists")
    universe.add_object(result.being)
    if universe.get_object_by_id(result.being.id) is not result.being:
        _refuse("native_registration_failed", "Universe did not register the constructed Being")
    return result
