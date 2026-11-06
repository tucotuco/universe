"""Private adapter for the bounded npcgen-npc v2 native-skill fixture."""

from dataclasses import dataclass
import math

from abilities import Abilities
from being import BeingDefinition, BeingInstance
from skill import Skills
from universe import Universe


_ABILITY_ORDER = ("Str", "Int", "Wis", "Dex", "Con", "Cha")
_ABILITY_KEYWORDS = {
    "Str": "strength",
    "Int": "intelligence",
    "Wis": "wisdom",
    "Dex": "dexterity",
    "Con": "constitution",
    "Cha": "charisma",
}
_ORDINARY_RANKS = {"armed combat"}
_WEAPON_RANKS = {"Dagger"}


@dataclass(frozen=True)
class _NpcgenV2Fields:
    name: str
    stature_inches: float
    body_weight_pounds: float
    abilities: tuple
    ordinary_ranks: tuple
    weapon_ranks: tuple
    initial_hit_points: int


def _positive_rank_dict(value, expected_keys, field_name):
    if type(value) is not dict or set(value) != expected_keys:
        raise ValueError(f"{field_name} must contain exactly {sorted(expected_keys)!r}")
    result = []
    for key in sorted(expected_keys):
        level = value[key]
        if type(level) is not int or level <= 0:
            raise ValueError(f"{field_name}.{key} must be a positive integer")
        result.append((key, level))
    return tuple(result)


def _positive_finite_measurement(value, field_name):
    if type(value) not in (int, float):
        raise ValueError(f"{field_name} must be a finite positive number")
    try:
        numeric = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a finite positive number") from exc
    if not math.isfinite(numeric) or numeric <= 0:
        raise ValueError(f"{field_name} must be a finite positive number")
    return numeric


def _validate_npcgen_v2_record(record, library):
    """Validate only the exact source contract used by this integration fixture.

    This is not a general NPC importer. Unknown acquired skills are refused so
    they cannot disappear during conversion.
    """
    if type(record) is not dict or record.get("format") != "npcgen-npc":
        raise ValueError("expected an npcgen-npc record")
    if type(record.get("schema_version")) is not int or record["schema_version"] != 2:
        raise ValueError("only npcgen-npc schema_version 2 is supported")
    state = record.get("state")
    sheet = record.get("sheet")
    if type(state) is not dict or type(sheet) is not dict:
        raise ValueError("npcgen v2 state and sheet objects are required")

    # The supported v2 contract's canonical units are inches/pounds. Explicit
    # incompatible unit annotations are rejected instead of silently ignored.
    for key, accepted in (("height_unit", {"in", "inch", "inches"}),
                          ("height_units", {"in", "inch", "inches"}),
                          ("weight_unit", {"lb", "lbs", "pound", "pounds"}),
                          ("weight_units", {"lb", "lbs", "pound", "pounds"})):
        if key in state and (type(state[key]) is not str or state[key] not in accepted):
            raise ValueError(f"unsupported physical measurement unit: state.{key}")

    # npcgen v2 defines state.height in inches and state.weight in pounds.
    # The sheet is a two-decimal projection of the same generated measurements.
    stature_inches = _positive_finite_measurement(state.get("height"), "state.height")
    body_weight_pounds = _positive_finite_measurement(state.get("weight"), "state.weight")
    age = sheet.get("age")
    if type(age) is not dict:
        raise ValueError("sheet.age must contain the physical measurement projections")
    sheet_height = _positive_finite_measurement(age.get("height_inches"),
                                                "sheet.age.height_inches")
    sheet_weight = _positive_finite_measurement(age.get("weight_pounds"),
                                                "sheet.age.weight_pounds")
    if round(stature_inches, 2) != sheet_height or round(body_weight_pounds, 2) != sheet_weight:
        raise ValueError("state height/weight must agree with the rounded sheet projections")

    # npcgen's canonical state.hps is its generated hit-point total. The v2
    # sheet is derived from that same state and must agree; this fixture has no
    # separate current/damage history.
    initial_hit_points = state.get("hps")
    sheet_hit_points = sheet.get("hit_points")
    if type(initial_hit_points) is not int or initial_hit_points < 0:
        raise ValueError("state.hps must be a nonnegative integer initial HP value")
    if type(sheet_hit_points) is not int or sheet_hit_points != initial_hit_points:
        raise ValueError("sheet.hit_points must be the same integer value as state.hps")

    name = state.get("name")
    sheet_identity = sheet.get("identity")
    if (type(name) is not str or not name.strip() or type(sheet_identity) is not dict
            or sheet_identity.get("name") != name):
        raise ValueError("state.name and sheet.identity.name must be the same nonempty name")

    scores = state.get("scores")
    sheet_abilities = sheet.get("abilities")
    named_scores = sheet_abilities.get("scores") if type(sheet_abilities) is dict else None
    if (type(scores) is not list or len(scores) != len(_ABILITY_ORDER)
            or type(named_scores) is not dict or set(named_scores) != set(_ABILITY_ORDER)):
        raise ValueError("the six named npcgen ability scores are required")
    abilities = []
    for key, score in zip(_ABILITY_ORDER, scores):
        named_score = named_scores[key]
        if (type(score) is not int or score <= 0 or type(named_score) is not int
                or named_score != score):
            raise ValueError("state.scores must agree with the six named sheet scores")
        abilities.append((key, score))

    source_skills = state.get("skills")
    if source_skills is None:
        raise ValueError("state.skills is unknown (null), not an empty learned profile")
    if type(source_skills) is not dict or set(source_skills) != {"skills", "weapon_skills"}:
        raise ValueError("state.skills must contain ordinary and weapon rank dictionaries")
    if sheet.get("skills") != source_skills:
        raise ValueError("state.skills and sheet.skills must agree for this fixture contract")
    ordinary = _positive_rank_dict(source_skills["skills"], _ORDINARY_RANKS,
                                   "state.skills.skills")
    weapons = _positive_rank_dict(source_skills["weapon_skills"], _WEAPON_RANKS,
                                  "state.skills.weapon_skills")

    if library is None or library.skill_dictionary is None or library.weapon_dictionary is None:
        raise ValueError("native skill and weapon dictionaries must be configured")
    for skill_name, _level in ordinary:
        if library.skill_dictionary.get_skill_definition(skill_name) is None:
            raise ValueError(f"ordinary skill is not configured natively: {skill_name}")
    for weapon_name, _level in weapons:
        if library.weapon_dictionary.get_object_definition(weapon_name) is None:
            raise ValueError(f"weapon skill is not configured natively: {weapon_name}")

    return _NpcgenV2Fields(name, stature_inches, body_weight_pounds, tuple(abilities),
                           ordinary, weapons, initial_hit_points)


def create_npcgen_v2_native_being(universe, source_bytes):
    """Create one genuine native Being from the supported, validated v2 record.

    The original bytes remain with the caller for provenance and complete-record
    inspection. Source ``state.hps`` initializes current HP only; it is not a
    maximum-HP or Hit Dice mapping. This function imports no source race, age,
    class/level/XP, possessions, family, notes, Action history, or practice
    history.
    """
    import json

    if not isinstance(universe, Universe):
        raise TypeError("universe must be a native Universe")
    if type(source_bytes) is not bytes:
        raise TypeError("source_bytes must be the original fixture bytes")
    try:
        record = json.loads(source_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("source must be valid UTF-8 JSON") from exc
    fields = _validate_npcgen_v2_record(record, universe.library)

    abilities = Abilities(**{
        _ABILITY_KEYWORDS[key]: score for key, score in fields.abilities
    })
    skills = Skills()
    for skill_name, level in fields.ordinary_ranks:
        skills.set_skill_level(universe.library.skill_dictionary, skill_name, level)
    for weapon_name, level in fields.weapon_ranks:
        # Native Skills applies configured weapon-category propagation. Only the
        # source Dagger rank is an acquired source rank; propagated ranks are derived.
        skills.set_weapon_skill_level(universe.library.weapon_dictionary, weapon_name, level)

    # Explicit native-only test baseline. These required mechanics have no
    # verified mapping from this source record and are not imported NPC facts.
    definition = BeingDefinition(
        "npcgen fixture baseline", length=fields.stature_inches,
        weight=fields.body_weight_pounds,
        hit_points=fields.initial_hit_points,
        hit_dice="1d8", alignment="Neutral", armor_class=11,
        challenge_rating=1, abilities=abilities, skills=skills,
    )
    being = BeingInstance(definition, name=fields.name)
    universe.add_object(being)
    if universe.get_object_by_id(being.id) is not being:
        raise RuntimeError("native Universe did not register the constructed Being")
    return being
