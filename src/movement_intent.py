"""Explicit one-boundary movement intent and adopted movement-rate arithmetic.

This module derives native rate limits and a destination-directed velocity for
one transactional Encounter boundary. It does not model path clearance,
collisions, body geometry, acceleration, or arrival.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

from being import BeingInstance
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
    """Required, explicitly supplied current movement limits.

    These have no neutral defaults. A caller must establish terrain,
    hampering, encumbrance, posture, direction, and any concurrent demanding
    action before requesting a legal rate.
    """

    terrain_multiplier: float | None = None
    hampered_multiplier: float | None = None
    encumbrance_lb: float | None = None
    posture: str | None = None
    direction: str | None = None
    concurrent_demanding_action: bool | None = None


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


def evaluate_movement_rate(being, rate: str,
                           conditions: MovementRateConditions) -> MovementRateResult:
    """Derive a movement category's current speed from r61 and supplied limits.

    Run skill adds one foot per second per level to maximum sprint speed; the
    adopted category ratios are then applied. The result is capped by the
    r61 maximum movement rate, fatigue category, posture, direction and
    concurrent-demanding-action limits.
    """
    if not isinstance(being, BeingInstance):
        raise MovementIntentRefusal("invalid_actor", "native BeingInstance required")
    if type(rate) is not str or rate not in _CATEGORY_RATIO:
        raise MovementIntentRefusal("invalid_rate", "select sprint, run, jog, hustle, or walk")
    if type(conditions) is not MovementRateConditions:
        raise MovementIntentRefusal("unknown_movement_limit", "explicit MovementRateConditions required")

    missing = [name for name in (
        "terrain_multiplier", "hampered_multiplier", "encumbrance_lb",
        "posture", "direction", "concurrent_demanding_action")
        if getattr(conditions, name) is None]
    if missing:
        raise MovementIntentRefusal(
            "unknown_movement_limit", "movement limits are unknown: " + ", ".join(missing))

    terrain = _finite_factor(conditions.terrain_multiplier, "terrain multiplier")
    hampered = _finite_factor(conditions.hampered_multiplier, "hampered multiplier")
    encumbrance = conditions.encumbrance_lb
    if (isinstance(encumbrance, bool) or not isinstance(encumbrance, (int, float))
            or not math.isfinite(encumbrance) or encumbrance < 0):
        raise MovementIntentRefusal("unknown_encumbrance", "encumbrance must be explicitly known and nonnegative")
    if type(conditions.concurrent_demanding_action) is not bool:
        raise MovementIntentRefusal("unknown_movement_limit", "concurrent demanding-action status must be explicit")

    posture = conditions.posture
    if posture not in ("standing", "crouching", "lying"):
        raise MovementIntentRefusal("unsupported_posture", "posture must be standing, crouching, or lying")
    direction = conditions.direction
    if direction not in ("forward", "backward"):
        raise MovementIntentRefusal(
            "unsupported_direction", "non-forward/non-backward movement needs an adopted hex-distance mapping")

    fatigue = being.get_fatigue_level()
    if type(fatigue) is not int or not 0 <= fatigue <= 5:
        raise MovementIntentRefusal("unknown_fatigue", "native physical fatigue level is unavailable")
    max_fatigue_category = _FATIGUE_MAX_CATEGORY[fatigue]
    if max_fatigue_category is None:
        raise MovementIntentRefusal("incapacitated", "fatigue level 5 permits no physical activity")

    fatigue_entry = being.exertion.fatigue_levels.get(fatigue)
    if type(fatigue_entry) is not dict or "ability_adjustment" not in fatigue_entry:
        raise MovementIntentRefusal("unknown_fatigue", "native fatigue ability adjustment is unavailable")
    ability_adjustment = fatigue_entry["ability_adjustment"]
    if type(ability_adjustment) is not int:
        raise MovementIntentRefusal("unknown_fatigue", "fatigue ability adjustment is unsupported")

    race = being.current.race
    race_key = race.strip().casefold() if type(race) is str else ""
    divisor = _RACE_DIVISOR.get(race_key)
    if divisor is None:
        raise MovementIntentRefusal("unsupported_race", f"no adopted sprint formula for race {race!r}")
    fitness = being.FIT()
    strength = being.STR()
    if (isinstance(fitness, bool) or not isinstance(fitness, (int, float))
            or not math.isfinite(fitness) or fitness <= 0):
        raise MovementIntentRefusal("unknown_fitness", "positive native Fitness is required")
    if isinstance(strength, bool) or not isinstance(strength, (int, float)) or not math.isfinite(strength):
        raise MovementIntentRefusal("unknown_strength", "native Strength is required for heavy-load limit")
    effective_fitness = fitness + ability_adjustment
    effective_strength = strength + ability_adjustment
    if effective_fitness <= 0:
        raise MovementIntentRefusal("invalid_fitness", "fatigue-adjusted Fitness must be positive")
    if effective_strength != math.floor(effective_strength):
        raise MovementIntentRefusal("unsupported_strength", "carrying-capacity table requires integer Strength")
    heavy_load_limit = _HEAVY_LOAD_UPPER_LB.get(int(effective_strength))
    if heavy_load_limit is None:
        raise MovementIntentRefusal("unsupported_strength", "carrying-capacity table supports Strength 1..23")
    if encumbrance > 2 * heavy_load_limit:
        raise MovementIntentRefusal("unsupported_encumbrance", "r61 load factor is negative above twice heavy load")

    run_level = being.get_skill_level("Run")
    if run_level is None:
        run_level = 0
    if type(run_level) is not int or run_level < 0:
        raise MovementIntentRefusal("unknown_run_skill", "native Run skill level must be a nonnegative integer")
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
    return MovementRateResult(rate, run_level, fatigue, sprint, requested,
                              min(caps), allowed, allowed * YARDS_TO_METERS)


def prepare_movement_intent(encounter, intent: MovementIntent,
                            conditions: MovementRateConditions, *, duration=1.0) -> PreparedMovementIntent:
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

    actor = encounter.get_being(intent.actor_id)
    if not isinstance(actor, BeingInstance):
        raise MovementIntentRefusal("invalid_actor", "movement actor must be a participating Being")
    if actor.get_hit_points() <= 0:
        raise MovementIntentRefusal("ineligible_actor", "a Being at 0 HP or below cannot choose voluntary movement")
    start = actor.get_position()
    if not isinstance(start, CartesianPosition):
        raise MovementIntentRefusal("unpositioned_actor", "movement actor requires native Cartesian position")
    if not isinstance(intent.destination, CartesianPosition):
        raise MovementIntentRefusal("invalid_destination", "destination must be a native CartesianPosition")

    rate = evaluate_movement_rate(actor, intent.rate, conditions)
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
