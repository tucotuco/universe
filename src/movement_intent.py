"""Explicit one-boundary movement intent and adopted movement-rate arithmetic.

This module derives native rate limits and a destination-directed velocity for
one transactional Encounter boundary. It does not model path clearance,
collisions, body geometry, acceleration, or arrival.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

from being import BeingInstance
from object import ObjectInstance
from spatial.state import CartesianPosition


YARDS_TO_METERS = 0.9144
FEET_PER_YARD = 3.0

_CATEGORY_RATIO = {
    "sprint": 1.0,
    "run": 2.0 / 3.0,
    "jog": 1.0 / 2.0,
    "hustle": 1.0 / 3.0,
    "walk": 1.0 / 4.0,
}
_FATIGUE_MAX_CATEGORY = ("sprint", "run", "jog", "hustle", "walk", None)
_HEAVY_LOAD_UPPER_LB = {
    1: 10, 2: 20, 3: 30, 4: 40, 5: 50, 6: 60, 7: 70, 8: 80, 9: 90,
    10: 100, 11: 115, 12: 130, 13: 150, 14: 175, 15: 200, 16: 230,
    17: 260, 18: 300, 19: 350, 20: 400, 21: 460, 22: 520, 23: 600,
}
_RACE_DIVISOR = {
    "human": 2.0,
    "elf": 2.0,
    "half-elf": 2.0,
    "half-orc": 2.0,
    "dwarf": 3.0,
    "gnome": 3.0,
    "halfling": 3.0,
}


class MovementIntentRefusal(ValueError):
    """A movement request lacks a supported native prerequisite."""

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class MovementRateConditions:
    """Required movement facts that native Being/Encounter state lacks.

    These have no neutral defaults. A caller must establish terrain,
    hampering, posture, direction, and any concurrent demanding-action
    classification before requesting a legal rate. Encumbrance and all
    Being-derived values are read from native state.
    """

    terrain_multiplier: float | None = None
    hampered_multiplier: float | None = None
    posture: str | None = None
    direction: str | None = None
    concurrent_demanding_action: bool | None = None


@dataclass(frozen=True)
class NativeMovementInputs:
    race: str
    fitness: float
    strength: float
    run_level: int
    physical_fatigue_level: int
    fatigue_ability_adjustment: int | None
    encumbrance_lb: float


@dataclass(frozen=True)
class MovementIntent:
    """A single-boundary target decision, independent of the Action ChoiceBook."""

    actor_id: str
    destination: CartesianPosition
    rate: str
    decision_id: str
    boundary: int


@dataclass(frozen=True)
class MovementRateResult:
    rate: str
    run_level: int
    physical_fatigue_level: int
    encumbrance_lb: float
    sprint_yards_per_second: float
    requested_yards_per_second: float
    maximum_yards_per_second: float
    yards_per_second: float
    meters_per_second: float


@dataclass(frozen=True)
class PreparedMovementIntent:
    intent: MovementIntent
    start_position: CartesianPosition
    velocity_meters_per_second: tuple[float, float, float]
    rate_result: MovementRateResult


def _finite_factor(value, name):
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(value) or not 0 <= value <= 1):
        raise MovementIntentRefusal("unknown_movement_limit",
                                    f"{name} must be an explicit finite factor in [0, 1]")
    return float(value)


def _native_carried_weight_lb(being, universe, snapshot_data=None, snapshot=None):
    """Sum represented native gear weights; refuse incomplete item references."""
    from being import BeingInstance
    from universe import Universe

    if type(universe) is not Universe or universe.get_object_by_id(being.id) is not being:
        raise MovementIntentRefusal("invalid_native_owner", "Being must belong to the supplied native Universe")
    if (type(being.possessions) is not list or type(being.weapons) is not list
            or type(being.current.body_parts) is not dict):
        raise MovementIntentRefusal("unknown_encumbrance", "native inventory references are not modeled")

    references = list(being.possessions) + list(being.weapons)
    references.extend(value for value in being.current.body_parts.values() if value is not None)
    if being.current.armor_id is not None:
        references.append(being.current.armor_id)
    if snapshot_data is not None:
        snapshot_references = (
            tuple(snapshot_data.get("possessions", ())),
            tuple(snapshot_data.get("weapons", ())),
            dict(snapshot_data.get("body_parts", {})),
            snapshot_data.get("armor_id"),
        )
        native_references = (
            tuple(being.possessions), tuple(being.weapons),
            dict(being.current.body_parts), being.current.armor_id,
        )
        if native_references != snapshot_references:
            raise MovementIntentRefusal(
                "stale_native_context", "native inventory changed after the pre-action snapshot")
    if any(type(reference) is not str for reference in references):
        raise MovementIntentRefusal("unknown_encumbrance", "inventory references must be native Object IDs")

    to_visit = list(dict.fromkeys(references))
    visited = set()
    total = 0.0
    while to_visit:
        item_id = to_visit.pop()
        if item_id in visited:
            continue
        visited.add(item_id)
        if snapshot is not None:
            try:
                item_view = snapshot.entity(item_id)
            except Exception as exc:
                raise MovementIntentRefusal(
                    "unknown_encumbrance", f"inventory Object {item_id!r} is unavailable in snapshot") from exc
            if item_view.category in ("being", "statistical_group"):
                raise MovementIntentRefusal("unknown_encumbrance", f"inventory Object {item_id!r} is not gear")
            weight = item_view.data.get("weight")
            children = (view.id for view in snapshot.entities.values()
                        if view.data.get("parent_container_id") == item_id)
        else:
            item = universe.get_object_by_id(item_id)
            if not isinstance(item, ObjectInstance) or isinstance(item, BeingInstance):
                raise MovementIntentRefusal("unknown_encumbrance", f"inventory Object {item_id!r} is unavailable")
            weight = item.current.weight
            registry = universe.get_object_registry().object_instances
            children = (child_id for child_id, child in registry.items()
                        if getattr(child, "parent_container_id", None) == item_id)
        if (isinstance(weight, bool) or not isinstance(weight, (int, float))
                or not math.isfinite(weight) or weight < 0):
            raise MovementIntentRefusal("unknown_encumbrance", f"inventory Object {item_id!r} has no known pound weight")
        total += float(weight)
        if not math.isfinite(total):
            raise MovementIntentRefusal("unknown_encumbrance", "total carried weight is not finite")
        # Native parent_container_id records represented contents. Include each
        # contained object once; unsupported/cyclic inventory terminates safely.
        to_visit.extend(children)
    return total


def derive_native_movement_inputs(being, universe, *, skill_dictionary=None,
                                  pre_action_snapshot=None) -> NativeMovementInputs:
    """Read movement inputs that current native Being state actually defines."""
    from skill import SkillDictionary

    if not isinstance(being, BeingInstance):
        raise MovementIntentRefusal("invalid_actor", "native BeingInstance required")
    if skill_dictionary is None:
        if universe is None or not hasattr(universe, "get_skill_dictionary"):
            raise MovementIntentRefusal("unknown_run_skill", "native Run SkillDictionary is unavailable")
        skill_dictionary = universe.get_skill_dictionary()
    if not isinstance(skill_dictionary, SkillDictionary):
        raise MovementIntentRefusal("unknown_run_skill", "native Run SkillDictionary is unavailable")
    run_definition = skill_dictionary.get_skill_definition("run")
    if (type(run_definition) is not dict or run_definition.get("is_ordinary") is not True
            or run_definition.get("is_progressive") is not True):
        raise MovementIntentRefusal(
            "unknown_run_skill", "native dictionary lacks adopted ordinary progressive skill 'run'")
    snapshot_data = None
    if pre_action_snapshot is not None:
        from action_evaluation import EvaluationSnapshot
        if type(pre_action_snapshot) is not EvaluationSnapshot:
            raise MovementIntentRefusal("invalid_native_snapshot", "native pre-action EvaluationSnapshot required")
        view = pre_action_snapshot.entity(being.id)
        if view.category != "being":
            raise MovementIntentRefusal("invalid_actor", "movement snapshot actor is not a Being")
        snapshot_data = view.data
        race = snapshot_data.get("race")
        abilities = snapshot_data.get("abilities")
        skills = snapshot_data.get("skills")
        adjustments = snapshot_data.get("fatigue_adjustments")
        if not all(hasattr(value, "get") for value in (abilities, skills, adjustments)):
            raise MovementIntentRefusal("unknown_movement_input", "pre-action snapshot lacks native movement fields")
        fitness, strength = abilities.get("FIT"), abilities.get("STR")
        run_level = skills.get("run")
        fatigue = snapshot_data.get("fatigue_level")
        fatigue_entry = adjustments.get(fatigue)
        if not hasattr(fatigue_entry, "get"):
            raise MovementIntentRefusal("unknown_fatigue", "pre-action snapshot lacks current PFL effects")
        ability_adjustment = fatigue_entry.get("ability_adjustment")
    else:
        race = being.current.race
        fitness = being.FIT()
        strength = being.STR()
        run_level = being.get_skill_level("run")
        fatigue = being.get_fatigue_level()
        fatigue_entry = being.exertion.fatigue_levels.get(fatigue)
        ability_adjustment = (fatigue_entry.get("ability_adjustment")
                              if type(fatigue_entry) is dict else None)
    if run_level is None:
        run_level = 0
    if type(run_level) is not int or run_level < 0:
        raise MovementIntentRefusal("unknown_run_skill", "native Run skill level must be a nonnegative integer")

    if type(fatigue) is not int or not 0 <= fatigue <= 5:
        raise MovementIntentRefusal("unknown_fatigue", "native physical fatigue level is unavailable")
    if type(race) is not str or not race.strip():
        raise MovementIntentRefusal("unsupported_race", "native Being race is unavailable")
    if (isinstance(fitness, bool) or not isinstance(fitness, (int, float))
            or not math.isfinite(fitness) or fitness <= 0):
        raise MovementIntentRefusal("unknown_fitness", "positive native Fitness is required")
    if (isinstance(strength, bool) or not isinstance(strength, (int, float))
            or not math.isfinite(strength)):
        raise MovementIntentRefusal("unknown_strength", "native Strength is required for heavy-load limit")
    if type(ability_adjustment) is not int and not (fatigue == 5 and ability_adjustment is None):
        raise MovementIntentRefusal("unknown_fatigue", "native fatigue ability adjustment is unavailable")
    return NativeMovementInputs(
        race, float(fitness), float(strength), run_level, fatigue, ability_adjustment,
        _native_carried_weight_lb(being, universe, snapshot_data, pre_action_snapshot))


def evaluate_movement_rate(being, rate: str,
                           conditions: MovementRateConditions, *, universe,
                           skill_dictionary=None, pre_action_snapshot=None) -> MovementRateResult:
    """Derive a movement category's current speed from r61 and supplied limits.

    Run skill adds one foot per second per level to maximum sprint speed; the
    adopted category ratios are then applied. The result is capped by the
    r61 maximum movement rate, fatigue category, posture, direction and
    concurrent-demanding-action limits.
    """
    if type(rate) is not str or rate not in _CATEGORY_RATIO:
        raise MovementIntentRefusal("invalid_rate", "select sprint, run, jog, hustle, or walk")
    if type(conditions) is not MovementRateConditions:
        raise MovementIntentRefusal("unknown_movement_limit", "explicit MovementRateConditions required")

    missing = [name for name in (
        "terrain_multiplier", "hampered_multiplier", "posture", "direction",
        "concurrent_demanding_action")
        if getattr(conditions, name) is None]
    if missing:
        raise MovementIntentRefusal(
            "unknown_movement_limit", "movement limits are unknown: " + ", ".join(missing))

    terrain = _finite_factor(conditions.terrain_multiplier, "terrain multiplier")
    hampered = _finite_factor(conditions.hampered_multiplier, "hampered multiplier")
    if type(conditions.concurrent_demanding_action) is not bool:
        raise MovementIntentRefusal("unknown_movement_limit", "concurrent demanding-action status must be explicit")

    posture = conditions.posture
    if posture not in ("standing", "crouching", "lying"):
        raise MovementIntentRefusal("unsupported_posture", "posture must be standing, crouching, or lying")
    direction = conditions.direction
    if direction not in ("forward", "backward"):
        raise MovementIntentRefusal(
            "unsupported_direction", "non-forward/non-backward movement needs an adopted hex-distance mapping")

    native = derive_native_movement_inputs(
        being, universe, skill_dictionary=skill_dictionary,
        pre_action_snapshot=pre_action_snapshot)
    fatigue = native.physical_fatigue_level
    run_level = native.run_level
    encumbrance = native.encumbrance_lb
    max_fatigue_category = _FATIGUE_MAX_CATEGORY[fatigue]
    if max_fatigue_category is None:
        raise MovementIntentRefusal("incapacitated", "fatigue level 5 permits no physical activity")

    ability_adjustment = native.fatigue_ability_adjustment
    if type(ability_adjustment) is not int:
        raise MovementIntentRefusal("unknown_fatigue", "native fatigue ability adjustment is unsupported")

    race_key = native.race.strip().casefold()
    divisor = _RACE_DIVISOR.get(race_key)
    if divisor is None:
        raise MovementIntentRefusal("unsupported_race", f"no adopted sprint formula for race {race!r}")
    effective_fitness = native.fitness + ability_adjustment
    effective_strength = native.strength + ability_adjustment
    if effective_fitness <= 0:
        raise MovementIntentRefusal("invalid_fitness", "fatigue-adjusted Fitness must be positive")
    if effective_strength != math.floor(effective_strength):
        raise MovementIntentRefusal("unsupported_strength", "carrying-capacity table requires integer Strength")
    heavy_load_limit = _HEAVY_LOAD_UPPER_LB.get(int(effective_strength))
    if heavy_load_limit is None:
        raise MovementIntentRefusal("unsupported_strength", "carrying-capacity table supports Strength 1..23")
    if encumbrance > 2 * heavy_load_limit:
        raise MovementIntentRefusal("unsupported_encumbrance", "r61 load factor is negative above twice heavy load")

    sprint = effective_fitness / divisor + run_level / FEET_PER_YARD
    requested = sprint * _CATEGORY_RATIO[rate]
    maximum = sprint * terrain * hampered * (1 - fatigue / 5.0)
    maximum *= (2 * heavy_load_limit - encumbrance) / (2 * heavy_load_limit)
    fatigue_cap = sprint * _CATEGORY_RATIO[max_fatigue_category]
    caps = [maximum, fatigue_cap]
    if posture == "crouching":
        caps.append(1.0)  # r61: at most one yard/second while crouching.
    elif posture == "lying":
        caps.append(0.5)  # r61: at most one yard every two seconds.
    if direction == "backward":
        caps.append(1.0)  # r61: at most one yard/second backward.
    if conditions.concurrent_demanding_action:
        caps.append(1.0)  # r61: ordinary movement during another demanding Action.
    allowed = min([requested] + caps)
    if not math.isfinite(allowed) or allowed <= 0:
        raise MovementIntentRefusal("no_movement_rate", "the supplied conditions permit no positive movement rate")
    return MovementRateResult(rate, run_level, fatigue, encumbrance, sprint, requested,
                              min(caps), allowed, allowed * YARDS_TO_METERS)


def prepare_movement_intent(encounter, intent: MovementIntent,
                            conditions: MovementRateConditions, *, duration=1.0,
                            pre_action_snapshot) -> PreparedMovementIntent:
    """Read-only preflight for a fresh one-boundary destination intent.

    This derives only the direction and legal scalar speed. It makes no path,
    obstacle, collision, arrival, or geometry claim.
    """
    from encounter import Encounter
    from transactional_progression import mode_of

    if type(encounter) is not Encounter:
        raise MovementIntentRefusal("invalid_encounter", "native Encounter required")
    if type(intent) is not MovementIntent:
        raise MovementIntentRefusal("invalid_intent", "native MovementIntent required")
    if not encounter.initiated:
        raise MovementIntentRefusal("uninitiated", "movement cannot activate an Encounter")
    if mode_of(encounter) != "transactional":
        raise MovementIntentRefusal("nontransactional", "movement intent requires native transactional progression")
    if type(intent.actor_id) is not str or not intent.actor_id:
        raise MovementIntentRefusal("invalid_actor", "actor ID must be nonempty")
    if type(intent.decision_id) is not str or not intent.decision_id.strip():
        raise MovementIntentRefusal("invalid_decision", "decision reference must be nonempty")
    if type(intent.boundary) is not int or intent.boundary < 1:
        raise MovementIntentRefusal("invalid_boundary", "movement boundary must be a positive integer")
    if (isinstance(duration, bool) or not isinstance(duration, (int, float))
            or not math.isfinite(duration) or duration != 1.0):
        raise MovementIntentRefusal("unsupported_duration", "movement intents currently cover exactly one second")
    if (encounter.active_boundary is not None
            or encounter.time != encounter.last_processed_boundary
            or intent.boundary != encounter.last_processed_boundary + 1):
        raise MovementIntentRefusal("stale_boundary", "movement decision must target the next untouched boundary")
    from action_evaluation import EvaluationSnapshot
    if (type(pre_action_snapshot) is not EvaluationSnapshot
            or pre_action_snapshot.encounter_id != encounter.id
            or pre_action_snapshot.boundary != intent.boundary
            or intent.actor_id not in pre_action_snapshot.participant_ids):
        raise MovementIntentRefusal("stale_native_context", "movement requires this boundary's common pre-action snapshot")

    actor = encounter.get_being(intent.actor_id)
    if not isinstance(actor, BeingInstance):
        raise MovementIntentRefusal("invalid_actor", "movement actor must be a participating Being")
    actor_view = pre_action_snapshot.entity(intent.actor_id)
    if actor_view.category != "being":
        raise MovementIntentRefusal("invalid_actor", "movement snapshot actor must be a Being")
    if actor_view.hp <= 0:
        raise MovementIntentRefusal("ineligible_actor", "a Being at 0 HP or below cannot choose voluntary movement")
    start = actor_view.position
    if not isinstance(start, CartesianPosition):
        raise MovementIntentRefusal("unpositioned_actor", "movement actor requires native Cartesian position")
    if not isinstance(intent.destination, CartesianPosition):
        raise MovementIntentRefusal("invalid_destination", "destination must be a native CartesianPosition")

    rate = evaluate_movement_rate(
        actor, intent.rate, conditions, universe=encounter.universe,
        pre_action_snapshot=pre_action_snapshot)
    delta = tuple(end - begin for begin, end in zip(start.as_tuple(), intent.destination.as_tuple()))
    distance = math.sqrt(sum(component * component for component in delta))
    if not math.isfinite(distance):
        raise MovementIntentRefusal("invalid_destination", "destination distance is not finite")
    if distance == 0:
        raise MovementIntentRefusal("zero_distance", "destination must differ from current position")
    if distance <= rate.meters_per_second * duration:
        raise MovementIntentRefusal(
            "arrival_unsupported", "requested interval could reach the destination; arrival behavior is not adopted")
    unit = tuple(component / distance for component in delta)
    velocity = tuple(component * rate.meters_per_second for component in unit)
    return PreparedMovementIntent(intent, start, velocity, rate)
