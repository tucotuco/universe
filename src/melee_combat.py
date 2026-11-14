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
    dimensions. In a mapped hex Encounter, impact eligibility requires that
    reach enter the target's authoritative occupied hex; elsewhere it retains
    the legacy center-distance check.

    An obstructed or indeterminate reference-point path is conservatively
    unavailable, even if an intervening modeled physical Entity is transparent.
    StatisticalGroup footprint envelopes are descriptive bounds, not physical
    Entities for this test. An open straight segment does not certify that a
    swing has enough room. Being body geometry remains deferred.
    """

    def __init__(self, encounter, actor_id, target_id, weapon_id,
                 motion='thrust', reach=None, strategy=None,
                 feint_source_action_id=None, charge=False, two_handed=False,
                 shield_bash=False):
        if motion not in ('swing', 'thrust'):
            raise ValueError('motion must be swing or thrust')
        if isinstance(reach, bool) or not isinstance(reach, (int, float)):
            raise TypeError('reach must be a numeric length in Encounter units')
        if not math.isfinite(reach) or reach <= 0:
            raise ValueError('reach must be finite and positive')
        if type(charge) is not bool:
            raise TypeError('charge declaration must be an explicit Boolean')
        if type(two_handed) is not bool:
            raise TypeError('two-handed declaration must be an explicit Boolean')
        if type(shield_bash) is not bool or (shield_bash and two_handed):
            raise TypeError('shield bash must be an explicit one-handed attack')
        self.encounter = encounter
        self.reach = float(reach)
        self.charge = charge
        self.two_handed = two_handed
        self.shield_bash = shield_bash
        self.shield_hand = None
        if shield_bash:
            actor = encounter.get_being(actor_id)
            self.shield_hand = (None if actor is None else next((slot for slot, value
                in actor.current.body_parts.items() if value == weapon_id), None))
        self.hit_type = None
        self.combat_result = None
        self._simultaneous_eligibility = None
        self.defended_by = None
        self.feint_source_action_id = feint_source_action_id
        super().__init__(encounter.universe, encounter.time, None, motion,
                         actor_id, target_id, weapon_id, strategy=strategy,
                         parent_event_id=encounter.id)
        from weapon import WeaponInstance, native_ready_preparation
        weapon = encounter.universe.get_object_by_id(weapon_id)
        preparation = native_ready_preparation(weapon) if type(weapon) is WeaponInstance else None
        if (preparation is not None and preparation['owner_id'] == actor_id
                and preparation['motion'] == motion
                and preparation['completed_at'] <= encounter.time):
            native_timing = weapon.St() if motion == 'swing' else weapon.Tt()
            reduced = max(1, native_timing - preparation['readying_seconds']
                          - self.strategy.timing_adjustment())
            self.end_time = self.start_time + reduced

    def _status(self, encounter):
        from action_calculations import melee_hex_path_status, melee_path_status
        from arena_hex_map import layout_from_encounter_map
        distance = encounter.distance_between_beings(self.actor_id, self.target_id)
        source = encounter.get_being(self.actor_id).get_position()
        target = encounter.get_being(self.target_id).get_position()
        layout = layout_from_encounter_map(encounter.map)
        if layout is not None:
            path = encounter.physical_path(self.actor_id, self.target_id)
            facing = encounter.get_being(self.actor_id).hex_facing
            return melee_hex_path_status(source, target, self.reach, path, layout, facing)
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
        hands = actor.current.body_parts
        weapon = self.get_instrument()
        if not isinstance(weapon, WeaponInstance):
            raise ValueError('instrument is not an instantiated Weapon')
        shield_names = set(encounter.universe.library.weapon_dictionary
                           .get_objects_in_category('Shields'))
        if self.shield_bash:
            shield_slots = actor.shielded_with(encounter.universe)
            if (weapon.current.obj_type not in shield_names
                    or self.instrument_id not in shield_slots.values()):
                raise ValueError('Shield bash requires an actually equipped native shield')
            if 'tower' in weapon.current.obj_type.casefold():
                raise ValueError('tower shields cannot be used to Shield bash')
            if not any(slot in ('left hand','right hand') and value == self.instrument_id
                       for slot,value in hands.items()):
                raise ValueError('Shield bash requires a shield mounted on a represented hand')
            tags = actor.current.tags
            dominant = (tags.get('universe.native_dominant_hand')
                        if type(tags) is dict else None)
            if dominant not in ('left hand','right hand'):
                raise ValueError('Shield bash requires explicitly authored dominant-hand evidence')
        elif self.instrument_id not in actor.armed_with(encounter.universe).values():
            raise ValueError('actor does not hold that weapon')
        occupied_hands = {slot: value for slot, value in hands.items()
                          if slot in ('left hand', 'right hand')}
        weapon_hand = next((slot for slot, value in occupied_hands.items()
                            if value == self.instrument_id), None)
        if weapon_hand is None:
            raise ValueError('weapon is not held in an explicitly represented hand')
        being_sizes = {'diminutive': 'D', 'tiny': 'T', 'small': 'S',
                       'medium': 'M', 'large': 'L', 'huge': 'H',
                       'gargantuan': 'G', 'colossal': 'C'}
        size_codes = ('D', 'T', 'S', 'M', 'L', 'H', 'G', 'C')
        being_size = being_sizes.get(getattr(actor, 'size_category', None))
        weapon_size = weapon.get_weapon_size()
        if self.shield_bash:
            size_delta = None
        elif being_size is None or weapon_size not in size_codes:
            if self.two_handed:
                raise ValueError('two-handed weapon use requires known native Being and weapon sizes')
            size_delta = None
        else:
            size_delta = size_codes.index(weapon_size) - size_codes.index(being_size)
            if size_delta > 1:
                raise ValueError('weapon is more than one size category larger than the Being')
            if size_delta == 1 and not self.two_handed:
                raise ValueError('a weapon one size larger than the Being requires two hands')
        if self.two_handed:
            other_hand = 'left hand' if weapon_hand == 'right hand' else 'right hand'
            if other_hand not in occupied_hands:
                raise ValueError('two-handed strike requires both native hands to be represented')
            if occupied_hands[other_hand] is not None:
                held = encounter.universe.get_object_by_id(occupied_hands[other_hand])
                shield_names = encounter.universe.library.weapon_dictionary.get_objects_in_category('Shields')
                if (held is None or held.current.obj_type not in shield_names
                        or 'buckler' not in held.current.obj_type.casefold()):
                    raise ValueError('two-handed strike requires the other hand free or a buckler')
        if self.feint_source_action_id is not None:
            from action_evaluation import ActionProposal
            source = encounter.universe.get_event_by_id(self.feint_source_action_id)
            if (type(source) is not Action or source.event_type != 'feint'
                    or source.id not in encounter.finished_action_list
                    or source.actor_id != self.actor_id or source.target_id != self.target_id
                    or type(source.resolution) is not ActionProposal
                    or source.resolution.outcome != 'success'):
                raise ValueError('Feint follow-up requires the immediately available successful native Feint')
            for choice in encounter._choice_book._choices.values():
                if choice.view.state not in ('accepted', 'executing', 'finished'):
                    continue
                for member in choice.members:
                    chosen = member.action
                    if (chosen.actor_id == self.actor_id and chosen.id != source.id
                            and chosen.start_time >= source.end_time):
                        raise ValueError('successful Feint benefit was already forfeited or consumed')
        if self.event_type not in weapon.get_melee_types():
            raise ValueError('weapon does not support requested attack motion')
        if self.damage_potential() is None or self.damage_potential() <= 0:
            raise ValueError('non-damaging attack not implemented')
        if self.charge:
            # Engagement is directional and reach-based. Check every present
            # Being that can reach and faces the actor, not only the declared
            # charge victim.
            if self._status(encounter)[0] == 'in_reach':
                raise ValueError('must disengage from pressing opponents before beginning a Charge')
            from arena_hex_map import layout_from_encounter_map
            from action_calculations import melee_hex_path_status, melee_path_status
            from hex_facing import FacingSector, classify_vector
            layout = layout_from_encounter_map(encounter.map)
            for opponent_id in encounter.being_list:
                if opponent_id == actor.id:
                    continue
                opponent = encounter.get_being(opponent_id)
                source, destination = opponent.get_position(), actor.get_position()
                if source is None or destination is None or opponent.get_hit_points() <= 0:
                    continue
                facing = opponent.hex_facing
                if facing is None or classify_vector(facing,
                        (destination.x-source.x,destination.y-source.y,
                         destination.z-source.z)) is not FacingSector.FRONT:
                    continue
                distances = []
                for weapon_id in opponent.armed_with(encounter.universe).values():
                    weapon = encounter.universe.get_object_by_id(weapon_id)
                    if isinstance(weapon, WeaponInstance):
                        try:
                            distances.append(effective_melee_reach_meters(
                                opponent.current,weapon.current,
                                size_category=opponent.size_category))
                        except ValueError:
                            pass
                if not distances:
                    try:
                        distances.append(reference_arm_length_inches(
                            height_inches=opponent.current.height,
                            length_inches=opponent.current.length,
                            size_category=opponent.size_category)*INCHES_TO_METERS)
                    except ValueError:
                        continue
                reach = max(distances)
                distance = math.dist(source.as_tuple(),destination.as_tuple())
                path = encounter.physical_path(opponent.id,actor.id)
                status = (melee_hex_path_status(source,destination,reach,path,layout,facing)[0]
                          if layout is not None else melee_path_status(distance,reach,path)[0])
                if status == 'in_reach':
                    raise ValueError('must disengage from pressing opponents before beginning a Charge')
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
        target_dc = difficulty_class
        from arena_hex_map import layout_from_encounter_map
        if layout_from_encounter_map(self.encounter.map) is not None:
            target = self.get_target()
            actor = self.get_actor()
            if (target is not None and actor is not None
                    and target.hex_facing is not None
                    and target.get_position() is not None
                    and actor.get_position() is not None):
                from hex_facing import vector_is_behind
                target_to_actor = (actor.get_position().x - target.get_position().x,
                                   actor.get_position().y - target.get_position().y,
                                   actor.get_position().z - target.get_position().z)
                if vector_is_behind(target.hex_facing, target_to_actor):
                    target_dc -= target.strategy.defense
        return super().roll_hits(roll, target_dc - adjustment)

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
        data['charge'] = self.charge
        return json.dumps(data, indent=2)
