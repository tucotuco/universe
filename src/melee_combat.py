"""First playable, event-backed armed-melee exchange.

This integrates the draft's weapon timing, attack rolls, strategy, shield/armor
and injury rules with Encounter position/awareness/timeline checks. It does not
pretend that optical sightline is a complete collision/reach/facing model.
"""

from transactional_progression import guard_legacy_action

from dataclasses import asdict, dataclass
import json
import math

from action import Action
from scheduling import PreparedSchedule
from experience import ActionResolution, SkillExercise
from weapon import WeaponInstance


SIZE_CATEGORY_REFERENCE_ARM_INCHES = {
    'D': 3.5, 'T': 7, 'S': 14, 'M': 28, 'L': 56,
    'H': 112, 'G': 224, 'C': 448,
}
INCHES_TO_METERS = 0.0254


def reference_arm_length_inches(*, height_inches=None, length_inches=None,
                                size_category=None):
    """Return measured or explicit size-category personal arm-length estimate."""
    dimensions = []
    for value in (height_inches, length_inches):
        if value is None:
            continue
        if type(value) not in (int, float):
            raise ValueError('physical height and length must be finite nonnegative inches')
        try:
            value = float(value)
        except (OverflowError, ValueError) as exc:
            raise ValueError('physical height and length must be finite nonnegative inches') from exc
        if not math.isfinite(value) or value < 0:
            raise ValueError('physical height and length must be finite nonnegative inches')
        if value > 0:
            dimensions.append(value)
    if dimensions:
        return max(dimensions) * (15 / 37)
    if size_category not in SIZE_CATEGORY_REFERENCE_ARM_INCHES:
        raise ValueError('a known physical dimension or size category is required for Reach')
    return SIZE_CATEGORY_REFERENCE_ARM_INCHES[size_category]


def effective_melee_reach_meters(being_definition, weapon_definition, *, size_category=None):
    """Calculate physical Reach in meters for Encounter center-distance checks.

    Being/weapon physical dimensions are inches; Encounter spatial coordinates
    and impact distances are meters. Collision geometry is independent.
    """
    weapon_length = weapon_definition.length
    if (type(weapon_length) not in (int, float) or not math.isfinite(weapon_length)
            or weapon_length < 0):
        raise ValueError('weapon length must be a finite nonnegative number of inches')
    arm_inches = reference_arm_length_inches(
        height_inches=being_definition.height,
        length_inches=being_definition.length,
        size_category=size_category)
    return (arm_inches + float(weapon_length)) * INCHES_TO_METERS


@dataclass(frozen=True)
class MeleeResult:
    """Legacy live-only sequential result; never used by pure proposals.

    HP deltas remain for current replay consumers until separate activation.
    The inactive ActionProposal contract instead records causal contributions.
    """
    action_id: str
    at_time: float
    actor_id: str
    target_id: str
    instrument_id: str
    motion: str
    outcome: str
    distance: float | None
    actor_hp_before: float
    actor_hp_after: float
    target_hp_before: float
    target_hp_after: float
    target_armor_damage: float = 0
    actor_armor_damage: float = 0

    def to_dict(self):
        return asdict(self)


class MeleeStrike(Action):
    """A scheduled swing or thrust between two present Beings.

    ``reach`` is an explicit limit in the Encounter's continuous-coordinate
    units (meters). Callers with native physical definitions should use
    ``effective_melee_reach_meters`` to combine inch-valued personal/weapon
    dimensions. This Action checks that limit against center distance at impact.

    An obstructed or indeterminate reference-point path is conservatively
    unavailable, even if an intervening modeled physical Entity is transparent.
    StatisticalGroup footprint envelopes are descriptive bounds, not physical
    Entities for this test. An open straight segment does not certify that a
    swing has enough room. Facing, body-part reach and simultaneous impacts are next.
    """

    def __init__(self, encounter, actor_id, target_id, weapon_id,
                 motion='thrust', reach=None, strategy=None):
        if motion not in ('swing', 'thrust'):
            raise ValueError('motion must be swing or thrust')
        if isinstance(reach, bool) or not isinstance(reach, (int, float)):
            raise TypeError('reach must be a numeric length in Encounter units')
        if not math.isfinite(reach) or reach <= 0:
            raise ValueError('reach must be finite and positive')
        self.encounter = encounter
        self.reach = float(reach)
        self.hit_type = None
        self.combat_result = None
        self._simultaneous_eligibility = None
        self.defended_by = None
        super().__init__(encounter.universe, encounter.time, None, motion,
                         actor_id, target_id, weapon_id, strategy=strategy,
                         parent_event_id=encounter.id)

    def _status(self, encounter):
        from action_calculations import melee_path_status
        distance = encounter.distance_between_beings(self.actor_id, self.target_id)
        path = (encounter.physical_path(self.actor_id, self.target_id)
                if distance is not None and 0 < distance <= self.reach else None)
        return melee_path_status(distance, self.reach, path)

    def prepare_schedule(self, encounter):
        if encounter is not self.encounter:
            raise ValueError('MeleeStrike belongs to a different Encounter')
        actor = encounter.get_being(self.actor_id)
        target = encounter.get_being(self.target_id)
        if actor is None or target is None or actor is target:
            raise ValueError('melee requires two distinct participating Beings')
        if actor.get_hit_points() <= 0 or target.get_hit_points() <= 0:
            raise ValueError('combatants must be able to participate')
        if not encounter.is_aware(self.actor_id, self.target_id):
            raise ValueError('actor is not aware of target')
        weapon = self.get_instrument()
        if not isinstance(weapon, WeaponInstance):
            raise ValueError('instrument is not an instantiated Weapon')
        if self.instrument_id not in actor.armed_with(encounter.universe).values():
            raise ValueError('actor does not hold that weapon')
        if self.event_type not in weapon.get_melee_types():
            raise ValueError('weapon does not support requested attack motion')
        if self.damage_potential() is None or self.damage_potential() <= 0:
            raise ValueError('non-damaging attack not implemented')
        # Reach/path are evaluated at impact only; actors may wind up while
        # approaching a target, or anticipate movement into reach.
        return PreparedSchedule.from_action(self)

    def hit_result(self, difficulty_class):
        self.hit_type = super().hit_result(difficulty_class)
        return self.hit_type

    def capture_simultaneous_eligibility(self):
        """Freeze attempt prerequisites before any same-time melee impact.

        This is an Encounter-owned batch precondition, never an independently
        committed state or a guarantee about later armor interactions.
        """
        actor = self.get_actor()
        target = self.get_target()
        status, distance = self._status(self.encounter)
        return (actor.get_hit_points() > 0, target.get_hit_points() > 0,
                self.instrument_id in actor.armed_with(self.universe).values(),
                status, distance)

    def roll_hits(self, roll, difficulty_class):
        # Use the Being's established Exertion fatigue adjustment. This affects
        # attack accuracy, not the underlying random number or skill history.
        fatigue = self.get_actor().get_fatigue_level()
        adjustment = self.get_actor().exertion.fatigue_levels[fatigue]['ability_adjustment']
        if adjustment is None:
            return False
        return super().roll_hits(roll, difficulty_class - adjustment)

    def resolve(self, difficulty_class):
        guard_legacy_action(self, effect=True)
        if self.combat_result is not None:
            raise RuntimeError('melee Action already resolved')
        actor = self.get_actor()
        target = self.get_target()
        before_actor = actor.get_hit_points()
        before_target = target.get_hit_points()
        actor_armor = self.universe.get_object_by_id(actor.get_armor_id())
        target_armor = self.universe.get_object_by_id(target.get_armor_id())
        armor_before = (target_armor.hit_points() if target_armor else None)
        actor_armor_before = (actor_armor.hit_points() if actor_armor else None)
        eligible = self._simultaneous_eligibility
        if eligible is None:
            eligible = self.capture_simultaneous_eligibility()
        actor_ready, target_ready, weapon_ready, status, distance = eligible
        actor_ready = actor_ready and actor.get_fatigue_level() < 5
        attempted = False
        if not actor_ready:
            outcome = 'unable_to_act'
        elif not target_ready:
            outcome = 'target_down'
        elif not weapon_ready:
            outcome = 'weapon_unavailable'
        elif status != 'in_reach':
            outcome = status
        elif self.defended_by is not None:
            outcome = 'parried' if self.universe.get_event_by_id(self.defended_by).kind == 'parry' else 'dodged'
            attempted = True
        else:
            super().resolve(difficulty_class)
            outcome = self.hit_type
            attempted = True
        # Canceled strikes never exercised a weapon.  Both hits and misses
        # record real attempts on the ordinary Encounter experience path.
        exercises = ()
        if attempted:
            weapon_type = self.get_instrument().original.obj_type
            exercises = (SkillExercise(weapon_type, 10),)
        self.combat_result = MeleeResult(
            self.id, self.end_time, self.actor_id, self.target_id,
            self.instrument_id, self.event_type, outcome, distance,
            before_actor, actor.get_hit_points(),
            before_target, target.get_hit_points(),
            0 if armor_before is None else max(0, armor_before - target_armor.hit_points()),
            0 if actor_armor_before is None else max(0, actor_armor_before - actor_armor.hit_points()))
        return ActionResolution(outcome, skill_exercises=exercises)

    def to_json(self):
        data = json.loads(super().to_json())
        data['combat_result'] = (None if self.combat_result is None
                                 else self.combat_result.to_dict())
        data['reach'] = self.reach
        return json.dumps(data, indent=2)
