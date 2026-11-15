"""Small noncombat Actions for the first live Encounter progression loop.

This module deliberately contains only a testable running activity. It does not
claim to model gait, exertion, fatigue, terrain, or whether a speed is realistic.
"""

from transactional_progression import guard_legacy_action

import math
import json
import random

from action import Action
from scheduling import PreparedSchedule
from experience import ActionResolution, SkillExercise
from perception import Perception
from spatial.state import CartesianPosition
from object import ObjectInstance
from weapon import WeaponInstance


def declare_stun(universe, encounter, actor_id, target_id, *, region, motion,
                 strategy=None, id=None):
    """Declare an adopted unarmed Stun using represented Arm/Leg weapon data."""
    from being import BeingInstance
    from weapon import WeaponDictionary
    actor = encounter.get_being(actor_id)
    target = encounter.get_being(target_id)
    if (actor is None or target is None or actor is target
            or not encounter.is_aware(actor_id, target_id)):
        raise ValueError('Stun requires two distinct aware participating Beings')
    if region not in ('Arm', 'Leg') or motion not in ('swing', 'thrust'):
        raise ValueError('Stun requires a represented Arm/Leg and swing/thrust motion')
    if region == 'Leg' and motion == 'thrust':
        raise ValueError('the adopted Leg profile does not support thrust')
    level = actor.current.skills.get_skill_level('stun') or 0
    if level < 1:
        raise ValueError('Stun requires acquired extraordinary Stun skill')
    strategy = strategy or __import__('strategy').Strategy()
    armor_penalty = 0
    armor_id = actor.current.armor_id
    if armor_id is not None:
        armor = universe.get_object_by_id(armor_id)
        if armor is None:
            raise ValueError('Stun armor check penalty is unsupported')
        armor_penalty = armor.current.armor_check_penalty
    strength_mod = math.floor((actor.STR()-10)/2)
    dexterity_mod = math.floor((actor.DEX()-10)/2)
    pool = max(0, 2*(actor.current.skills.get_skill_level('unarmed combat') or 0)
        + strength_mod + dexterity_mod - armor_penalty)
    values = (strategy.attack,strategy.defense,strategy.timing,strategy.extra_damage)
    if any(type(value) is not int or value < 0 for value in values) or sum(values) > pool:
        raise ValueError(f'Stun strategy must allocate no more than its current {pool}-point pool')
    if strategy.extra_damage > max(0,(actor.current.skills.get_skill_level('unarmed combat') or 0)+strength_mod):
        raise ValueError('Stun extra damage exceeds its unarmed combat and Strength limit')
    dictionary = universe.library.weapon_dictionary
    definition = dictionary.objects.get(region)
    if definition is None:
        raise ValueError('native library lacks the adopted unarmed body profile')
    timing = definition.St() if motion == 'swing' else definition.Tt()
    action = Action(universe, encounter.time, encounter.time + timing, 'stun',
                    actor_id, target_id, None, strategy=strategy, id=id)
    action.end_time = encounter.time + max(1, timing - action.strategy.timing_adjustment())
    action.motion, action.body_region = motion, region
    action.reach = __import__('melee_combat').effective_melee_reach_meters(actor.current, definition)
    return action


def declare_subdue(universe, encounter, actor_id, target_id, weapon_id, *,
                   motion, strategy=None, id=None):
    """Declare Subdue with an actually held, represented melee weapon."""
    from being import BeingInstance
    actor, target = encounter.get_being(actor_id), encounter.get_being(target_id)
    weapon = universe.get_object_by_id(weapon_id)
    if (actor is None or target is None or actor is target
            or not encounter.is_aware(actor_id, target_id)):
        raise ValueError('Subdue requires two distinct aware participating Beings')
    if type(weapon) is not WeaponInstance or weapon_id not in actor.armed_with(universe).values():
        raise ValueError('Subdue requires an actually held native weapon')
    if motion not in weapon.get_melee_types() or motion not in ('swing', 'thrust'):
        raise ValueError('Subdue requires a represented melee weapon motion')
    profile = weapon.current.attacks['S' if motion == 'swing' else 'T']
    if profile.get('p') != 'B':
        raise ValueError('Subdue requires a bludgeon penetration profile')
    if target.current.immunities.get('subdual') is True:
        raise ValueError('a represented subdual immunity prohibits this Action')
    timing = weapon.current.St() if motion == 'swing' else weapon.current.Tt()
    from melee_combat import effective_melee_reach_meters
    action = Action(universe, encounter.time, encounter.time + timing, 'subdue',
                    actor_id, target_id, weapon_id, strategy=strategy, id=id)
    action.end_time = encounter.time + max(1, timing - action.strategy.timing_adjustment())
    action.motion = motion
    action.reach = effective_melee_reach_meters(actor.current, weapon.current)
    return action


class ThrowAction(Action):
    """Native drag-free Throw with bounded target, impact, and Coup de grace rules."""

    def __init__(self, universe, actor_id, instrument_id, start_time, *,
                 heavy_load_reference_lb, elevation_degrees, azimuth_degrees=0.0,
                 landing_elevation_m=0.0, target_id=None, coup_de_grace=False,
                 id=None):
        values = (start_time, heavy_load_reference_lb, elevation_degrees,
                  azimuth_degrees, landing_elevation_m)
        if any(type(value) not in (int, float) or not math.isfinite(value) for value in values):
            raise ValueError('Throw inputs must be finite native numbers')
        if heavy_load_reference_lb <= 0 or not 0 <= elevation_degrees <= 90:
            raise ValueError('invalid Throw load reference or elevation')
        if type(actor_id) is not str or type(instrument_id) is not str:
            raise ValueError('Throw requires native actor and Object identities')
        if target_id is not None and (type(target_id) is not str or not target_id):
            raise ValueError('Throw target must be a native Being identity')
        if type(coup_de_grace) is not bool:
            raise ValueError('thrown Coup de grace mode must be an explicit Boolean')
        super().__init__(universe, start_time, start_time + 4, 'throw', actor_id,
                         target_id=target_id, instrument_id=instrument_id, id=id)
        self.end_time = start_time + 4
        self.heavy_load_reference_lb = float(heavy_load_reference_lb)
        self.elevation_degrees = float(elevation_degrees)
        self.azimuth_degrees = float(azimuth_degrees)
        self.landing_elevation_m = float(landing_elevation_m)
        self.coup_de_grace = coup_de_grace

    def prepare_schedule(self, encounter):
        if encounter.progression_mode != 'transactional':
            raise ValueError('ThrowAction requires explicitly selected native transactional progression')
        if self.end_time - self.start_time != 4:
            raise ValueError('native Throw currently supports the authored four-second bracket')
        actor = encounter.get_being(self.actor_id)
        obj = encounter.universe.get_object_by_id(self.instrument_id)
        if actor is None or type(obj) not in (ObjectInstance, WeaponInstance):
            raise ValueError('Throw requires a participating Being and registered ObjectInstance')
        if self.target_id is not None:
            from being import BeingInstance
            target = encounter.universe.get_object_by_id(self.target_id)
            if (self.target_id not in encounter.being_list or type(target) is not BeingInstance
                    or target.get_position() is None or target is actor):
                raise ValueError('Targeted Throw requires a positioned participating Being')
        if self.coup_de_grace:
            if (self.target_id is None or type(obj) is not WeaponInstance
                    or actor.is_helpless() or not target.is_helpless()
                    or not encounter.is_aware(actor.id, target.id)
                    or math.hypot(actor.get_position().x-target.get_position().x,
                                  actor.get_position().y-target.get_position().y) > 0.9144):
                raise ValueError('thrown Coup de grace requires an aware helpless target within one yard and a thrown weapon')
        if type(obj) is WeaponInstance:
            held_hands = [hand for hand, held in actor.current.body_parts.items()
                          if hand in ('left hand','right hand') and held == self.instrument_id]
            ranged_time = obj.current.attacks.get('R', {}).get('t')
            ranged_damage = obj.current.attacks.get('R', {}).get('d')
            ranged_penetration = obj.current.attacks.get('R', {}).get('p')
            if (self.instrument_id not in actor.weapons or len(held_hands) != 1
                    or (self.instrument_id not in actor.possessions
                        and actor.current.body_parts[held_hands[0]] != self.instrument_id)
                    or type(ranged_time) is not int or ranged_time != 4
                    or type(ranged_damage) is not int or ranged_damage <= 0
                    or type(ranged_penetration) is not str or not ranged_penetration):
                raise ValueError('native Throw supports held weapons with the authored four-second ranged profile')
        elif self.instrument_id not in actor.possessions:
            raise ValueError('Throw Object must be available in actor possessions')
        from being import BeingInstance
        holders = [being.id for being in encounter.universe.object_registry.object_instances.values()
                   if type(being) is BeingInstance and (self.instrument_id in being.possessions
                       or self.instrument_id in being.weapons
                       or self.instrument_id in being.current.body_parts.values())]
        if holders != [actor.id]:
            raise ValueError('Throw Object must have exactly one native Being possessor')
        weight = obj.current.weight
        if type(weight) not in (int, float) or not math.isfinite(weight) or weight <= 0:
            raise ValueError('Throw Object must have positive finite pound weight')
        # The implemented preparation contract is deliberately the reviewed
        # Strength-10, <=3.3 lb, four-second table bracket only.
        strength = actor.current.abilities.STR()
        if strength != 10 or weight > 3.3:
            raise ValueError('native Throw supports only the authored Strength 10 four-second weight bracket')
        if actor.get_position() is None:
            raise ValueError('Thrower requires an authored spatial position')
        return PreparedSchedule.from_action(self)

    def resolve(self, difficulty_class):
        guard_legacy_action(self, effect=True)
        raise RuntimeError('ThrowAction resolves only through native transactional publication')


class PickUpAction(Action):
    """Revision-64 one-second acquisition of a free ground Object in Arena."""

    def __init__(self, encounter, actor_id, object_id, start_time, *,
                 map_width_cells, map_height_cells, id=None):
        if (type(actor_id) is not str or not actor_id or type(object_id) is not str or not object_id
                or actor_id == object_id):
            raise ValueError('Pick up requires distinct native Being and Object identities')
        for name, value in (('start_time', start_time),
                            ('map_width_cells', map_width_cells),
                            ('map_height_cells', map_height_cells)):
            if type(value) not in (int, float) or not math.isfinite(value):
                raise ValueError(f'{name} must be a finite native number')
        if start_time < 0 or float(start_time).is_integer() is False:
            raise ValueError('Pick up must begin at an integer Encounter second')
        if (type(map_width_cells) is not int or map_width_cells < 5
                or type(map_height_cells) is not int or map_height_cells < 5
                or map_width_cells * map_height_cells > 1_000_000):
            raise ValueError('Pick up requires the bounded generated-Arena hex dimensions')
        super().__init__(encounter.universe, start_time, start_time + 1, 'pick up',
                         actor_id, object_id, instrument_id=None, id=id)
        self.encounter = encounter
        self.end_time = start_time + 1
        self.map_width_cells = map_width_cells
        self.map_height_cells = map_height_cells

    def prepare_schedule(self, encounter):
        from being import BeingInstance
        if (encounter is not self.encounter or not encounter.arena_activation_enabled
                or encounter.progression_mode != 'transactional'):
            raise ValueError('Pick up requires the activated generated-Arena transaction path')
        actor = encounter.get_being(self.actor_id)
        target = encounter.universe.get_object_by_id(self.target_id)
        if actor is None or not isinstance(target, ObjectInstance) or isinstance(target, BeingInstance):
            raise ValueError('Pick up requires a participating Being and registered physical Object')
        if self.end_time - self.start_time != 1:
            raise ValueError('revision-64 Pick up lasts exactly one second')
        # The target is intentionally not an active-object reservation: native
        # boundary evaluation resolves simultaneous pickup contention together.
        return PreparedSchedule.from_action(self)

    def resolve(self, difficulty_class):
        guard_legacy_action(self, effect=True)
        raise RuntimeError('PickUpAction resolves only through native transactional publication')


class ReadyPreparationAction(Action):
    """Prepare a held Weapon for an attack motion or the adopted pole set."""

    def __init__(self, encounter, actor_id, weapon_id, motion, start_time=None, *, strategy=None, id=None):
        from weapon import WeaponInstance, weapon_readying_time
        if type(motion) is not str or motion not in ('swing', 'thrust', 'set pole'):
            raise ValueError('weapon Ready requires swing, thrust, or the adopted set-pole preparation')
        weapon = encounter.universe.get_object_by_id(weapon_id)
        if type(weapon) is not WeaponInstance:
            raise ValueError('weapon Ready requires an exact native WeaponInstance')
        pole_set = motion == 'set pole'
        if pole_set:
            dictionary = encounter.universe.library.weapon_dictionary
            groups = dictionary.object_categories
            pole_names = set(groups.get('Spears', ())) | set(groups.get('Lances', ()))
            if weapon.current.obj_type not in pole_names or 'thrust' not in weapon.get_melee_types():
                raise ValueError('set pole requires an adopted spear- or lance-group weapon with a thrust')
            from strategy import Strategy
            selected_strategy = strategy or Strategy()
            seconds = max(1, 4 - selected_strategy.timing_adjustment())
            ready_motion = 'set pole'
        else:
            seconds = weapon_readying_time(weapon, motion)
            ready_motion = motion
        start = encounter.time if start_time is None else start_time
        if (type(start) not in (int, float) or not math.isfinite(start)
                or start < 0 or not float(start).is_integer()):
            raise ValueError('Ready must begin at an integer Encounter second')
        super().__init__(encounter.universe, start, start + seconds, 'ready object',
                         actor_id, weapon_id, instrument_id=None,
                         strategy=strategy, parent_event_id=encounter.id, id=id)
        self.encounter = encounter
        self.ready_motion = ready_motion
        self.readying_seconds = seconds
        self.pole_set = pole_set
        self.end_time = start + seconds

    def prepare_schedule(self, encounter):
        from being import BeingInstance
        from weapon import WeaponInstance, native_ready_preparation
        from atomic_publication import publication_owned
        activation = (encounter.arena_activation_enabled and publication_owned(encounter)
                      and (not encounter.initiated or encounter.arena_activation is not None))
        if (encounter is not self.encounter
                or (encounter.progression_mode != 'transactional' and not activation)):
            raise ValueError('weapon Ready requires its native transactional Encounter')
        actor = encounter.get_being(self.actor_id)
        weapon = encounter.universe.get_object_by_id(self.target_id)
        if (type(actor) is not BeingInstance or type(weapon) is not WeaponInstance
                or self.target_id not in actor.weapons
                or self.target_id not in actor.armed_with(encounter.universe).values()):
            raise ValueError('Ready requires a currently held weapon')
        if native_ready_preparation(weapon) is not None:
            raise ValueError('weapon already has completed Ready preparation')
        if self.start_time < encounter.time:
            raise ValueError('Ready cannot begin before current Encounter time')
        if self.pole_set:
            expected = max(1, 4 - self.strategy.timing_adjustment())
            if (self.ready_motion != 'set pole' or self.readying_seconds != expected
                    or self.end_time - self.start_time != expected):
                raise ValueError('set pole requires its adopted four-second base preparation with normal timing adjustment')
        return PreparedSchedule.from_action(self)

    def resolve(self, difficulty_class):
        guard_legacy_action(self, effect=True)
        raise RuntimeError('ReadyPreparationAction resolves only through native transactional publication')


class DelayAction(Action):
    """One committed second of waiting with an explicitly selected defense allocation."""
    DURATION_SECONDS = 1

    def __init__(self, encounter, actor_id, defense=0, start_time=None, *, id=None):
        if type(defense) not in (int, float) or not math.isfinite(defense) or defense < 0:
            raise ValueError('Delay defense allocation must be finite and nonnegative')
        start = encounter.time if start_time is None else start_time
        if (type(start) not in (int, float) or not math.isfinite(start)
                or start < 0 or not float(start).is_integer()):
            raise ValueError('Delay must begin at an integer Encounter second')
        from strategy import Strategy
        super().__init__(encounter.universe, start, start + self.DURATION_SECONDS,
                         'delay', actor_id, None, instrument_id=None,
                         strategy=Strategy(defense=defense),
                         parent_event_id=encounter.id, id=id)
        self.encounter = encounter
        self.end_time = start + self.DURATION_SECONDS

    def prepare_schedule(self, encounter):
        from being import BeingInstance
        from atomic_publication import publication_owned
        activation = (encounter.arena_activation_enabled and publication_owned(encounter)
                      and (not encounter.initiated or encounter.arena_activation is not None))
        if (encounter is not self.encounter
                or (encounter.progression_mode != 'transactional' and not activation)):
            raise ValueError('Delay requires its native transactional Encounter')
        actor = encounter.get_being(self.actor_id)
        if type(actor) is not BeingInstance or actor.current.hit_points <= 0 or actor.is_helpless():
            raise ValueError('Delay requires a Being able to take a voluntary Action')
        if self.start_time < encounter.time:
            raise ValueError('Delay cannot begin before the current committed boundary')
        return PreparedSchedule.from_action(self)

    def resolve(self, difficulty_class):
        guard_legacy_action(self, effect=True)
        raise RuntimeError('DelayAction resolves only through native transactional publication')


def end_run_action(encounter, actor_id, target_id, exit_position, *,
                   terrain_multiplier, hampered_multiplier, direction,
                   occupant_willing=False, rate='run', start_time=None,
                   strategy=None, id=None):
    """Create the adopted three-second End Run declaration.

    The exit and ordinary movement premises are explicit declaration data.
    ``occupant_willing`` is a target-authored scenario decision, never inferred
    from NPC posture, strategy, or hidden attributes.
    """
    from spatial.state import CartesianPosition
    from encounter import Encounter
    from strategy import Strategy
    if type(encounter) is not Encounter:
        raise ValueError('End Run requires a native Encounter')
    if type(exit_position) is not CartesianPosition:
        raise ValueError('End Run requires a native Cartesian exit position')
    if type(occupant_willing) is not bool:
        raise ValueError('End Run occupant willingness must be an explicit target decision')
    if type(rate) is not str or rate not in ('sprint','run','jog','hustle','walk'):
        raise ValueError('End Run requires an adopted ordinary movement rate')
    if (type(terrain_multiplier) not in (int, float)
            or type(hampered_multiplier) not in (int, float)
            or not math.isfinite(terrain_multiplier)
            or not math.isfinite(hampered_multiplier)
            or not 0 <= terrain_multiplier <= 1
            or not 0 <= hampered_multiplier <= 1
            or direction not in ('forward', 'backward', 'sideways', 'non_forward')):
        raise ValueError('End Run requires explicit supported movement-rate premises')
    start = encounter.time if start_time is None else start_time
    if type(start) not in (int, float) or not math.isfinite(start) or start < 0 or not float(start).is_integer():
        raise ValueError('End Run must begin at a committed integer boundary')
    allocation = strategy if strategy is not None else Strategy()
    if type(allocation) is not Strategy:
        raise ValueError('End Run requires a native Strategy')
    duration = max(1, 3 - allocation.timing_adjustment())
    action = Action(encounter.universe, start, start + duration, 'end-run',
                    actor_id, target_id, instrument_id=None,
                    strategy=allocation, parent_event_id=encounter.id, id=id)
    action.end_run_exit_position = exit_position
    action.end_run_movement_conditions = (
        float(terrain_multiplier), float(hampered_multiplier), direction, False)
    action.end_run_occupant_willing = occupant_willing
    action.end_run_rate = rate
    return action


class ReadyWeaponAction(Action):
    """Candidate ordinary weapon draw; resolution follows the native boundary."""

    HANDS = frozenset(('left hand', 'right hand'))
    DRAW_DURATION_SECONDS = 2

    def __init__(self, encounter, actor_id, weapon_id, hand, start_time, *, id=None):
        if (type(actor_id) is not str or not actor_id or type(weapon_id) is not str
                or not weapon_id or actor_id == weapon_id):
            raise ValueError('Ready weapon requires distinct native Being and Weapon identities')
        if type(hand) is not str or hand not in self.HANDS:
            raise ValueError('Ready weapon requires an explicitly selected native hand')
        actor = encounter.get_being(actor_id)
        weapon = encounter.universe.get_object_by_id(weapon_id)
        if (actor is not None and weapon is not None
                and actor.get_skill_level('quick-draw')
                and (actor.get_weapon_skill_level(weapon.current.obj_type) or 0) > 1):
            raise ValueError(
                'Quick-draw with advanced weapon skill is essentially no-time and is not '
                'represented by the integer-second draw Action')
        if (type(start_time) not in (int, float) or not math.isfinite(start_time)
                or start_time < 0 or not float(start_time).is_integer()):
            raise ValueError('Ready weapon must begin at an integer Encounter second')
        super().__init__(encounter.universe, start_time,
                         start_time + self.DRAW_DURATION_SECONDS, 'ready weapon',
                         actor_id, weapon_id, instrument_id=None, id=id)
        self.encounter = encounter
        self.end_time = start_time + self.DRAW_DURATION_SECONDS
        self.hand = hand

    def prepare_schedule(self, encounter):
        from being import BeingInstance
        from weapon import WeaponInstance, native_weapon_draw_location
        from atomic_publication import publication_owned
        first_choice_preparation = (publication_owned(encounter)
            and encounter.arena_activation_enabled
            and encounter.progression_mode == 'legacy'
            and (not encounter.initiated
                 or (encounter.arena_activation is not None
                     and encounter.arena_activation.actor_id == self.actor_id)))
        if (encounter is not self.encounter or not encounter.arena_activation_enabled
                or (encounter.progression_mode != 'transactional'
                    and not first_choice_preparation)):
            raise ValueError('Ready weapon requires the activated generated-Arena transaction path')
        actor = encounter.get_being(self.actor_id)
        target = encounter.universe.get_object_by_id(self.target_id)
        if actor is None or type(target) is not WeaponInstance:
            raise ValueError('Ready weapon requires a participating Being and registered WeaponInstance')
        if self.end_time - self.start_time != self.DRAW_DURATION_SECONDS:
            raise ValueError('ordinary weapon drawing uses the adopted two-second duration')
        location = native_weapon_draw_location(target)
        if location is None or location.get('owner_id') != actor.id:
            raise ValueError('Draw requires explicitly authored drawable-source evidence for this Being')
        if (self.target_id not in actor.possessions
                or target.parent_container_id != actor.id or target.spatial_state is not None):
            raise ValueError('Draw requires exact native carried custody')
        if (self.hand not in actor.current.body_parts
                or actor.current.body_parts[self.hand] is not None):
            raise ValueError('Draw requires an explicitly represented free native hand')
        return PreparedSchedule.from_action(self)

    def resolve(self, difficulty_class):
        guard_legacy_action(self, effect=True)
        raise RuntimeError('ReadyWeaponAction resolves only through native transactional publication')


class RunAction(Action):
    """Attempt to cover a configured straight-line distance while running.

    The Encounter moves the Being using its ordinary step() velocities. This
    Action *observes* the resulting displacement; it never moves the Being.

    The initial position is captured when activity starts, not construction, so an
    Action cannot credit movement that happened before it was scheduled.
    Successful or partial movement exercises 'run'; no motion earns no XP.
    ``experience`` is an explicit scenario award, not a progression policy.

    Straight-line displacement is a deliberately provisional measure: a route
    that returns to its origin will count as no movement until we introduce
    path-aware movement histories.
    """

    def __init__(self, universe, actor_id, start_time, duration,
                 minimum_distance, experience=0, id=None):
        for name, value in (("start_time", start_time),
                            ("duration", duration),
                            ("minimum_distance", minimum_distance)):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"{name} must be a finite number")
        if duration <= 0 or minimum_distance <= 0:
            raise ValueError("duration and minimum_distance must be positive")
        if isinstance(experience, bool) or not isinstance(experience, int) or experience < 0:
            raise ValueError("experience must be a nonnegative integer")
        super().__init__(universe, start_time, None, 'run', actor_id,
                         target_id=None, instrument_id=None, id=id)
        self.end_time = start_time + duration
        if not math.isfinite(self.end_time):
            raise ValueError("end_time must be finite")
        self.minimum_distance = float(minimum_distance)
        self.practice_experience = experience
        self.start_position = None
        self.displacement = None


    def to_json(self):
        """Preserve the declared task and measured evidence with the Action."""
        data = json.loads(super().to_json())
        data.update({
            'minimum_distance': self.minimum_distance,
            'practice_experience': self.practice_experience,
            'start_position': (None if self.start_position is None
                               else dict(zip(('x', 'y', 'z'), self.start_position.as_tuple()))),
            'displacement': self.displacement,
        })
        return json.dumps(data, indent=2)

    def prepare_schedule(self, encounter):
        """Stage a sample; the choice coordinator captures the actual start."""
        if self.start_position is not None:
            raise ValueError("running activity has already been started")
        if self.start_time < encounter.time:
            raise ValueError("running activity cannot begin before scheduling time")
        actor = encounter.get_being(self.actor_id)
        if actor is None or actor.get_position() is None:
            raise ValueError("running activity requires a positioned participating Being")
        return PreparedSchedule.from_action(self, initialization=(
            ('start_position', actor.get_position()),))

    def resolve(self, difficulty_class):
        """Report practice from measured displacement, not declared intention."""
        guard_legacy_action(self, effect=True)
        if self.start_position is None:
            if getattr(self, '_activity_started', False):
                return ActionResolution('unplaced')
            raise RuntimeError("running activity has not been scheduled")
        actor = self.get_actor()
        position = actor.get_position() if actor is not None else None
        if position is None:
            return ActionResolution('unplaced')
        if not isinstance(position, CartesianPosition):
            raise ValueError("running activity requires the Being's current position")
        displacement = math.dist(self.start_position.as_tuple(), position.as_tuple())
        if displacement == 0:
            result = ActionResolution('no_movement')
        else:
            from action_calculations import run_outcome
            outcome = run_outcome(displacement, self.minimum_distance)
            result = ActionResolution(outcome, (SkillExercise('run', self.practice_experience),))
        self.displacement = displacement
        return result


class SpotAction(Action):
    """Six-second deliberate Search, Spot, or Listen discovery Action.

    The geometry gate remains a limited scaffold and does not model complete
    visibility, lighting, acuity, or terrain.
    """

    def __init__(self, universe, actor_id, target_id, start_time,
                 duration=6, die_roll=None, id=None, spotting_conditions=(), *,
                 ledger=None, group_fully_visible=False,
                 location_ledger=None, object_ledger=None, sense='spot'):
        for name, value in (("start_time", start_time), ("duration", duration)):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"{name} must be a finite number")
        if duration != 6:
            raise ValueError("deliberate Spot takes exactly six seconds")
        if die_roll is not None and (type(die_roll) is not int or not 1 <= die_roll <= 20):
            raise ValueError("die_roll must be an integer between 1 and 20")
        if sense not in ('search', 'spot', 'listen'):
            raise ValueError('discovery sense must be Search, Spot, or Listen')
        if actor_id == target_id:
            raise ValueError("a Being cannot discover itself")
        if type(group_fully_visible) is not bool:
            raise TypeError("group_fully_visible must be a Boolean scenario premise")
        if ledger is not None:
            from field_observation import BeliefLedger
            if type(ledger) is not BeliefLedger or ledger.observer_id != actor_id:
                raise ValueError("Spot evidence ledger must belong to the observing Being")
        if group_fully_visible and ledger is None:
            raise ValueError("fully visible Group observation requires the observer's BeliefLedger")
        if ledger is not None and not group_fully_visible:
            raise ValueError("Spot ledger is supported only with an explicit fully visible Group premise")
        if location_ledger is not None:
            from location_observation import LocationEvidenceLedger
            if (type(location_ledger) is not LocationEvidenceLedger
                    or location_ledger.observer_id != actor_id):
                raise ValueError("location evidence ledger must belong to the Spotter")
        if object_ledger is not None:
            from object_observation import ObjectObservationLedger
            if (type(object_ledger) is not ObjectObservationLedger
                    or object_ledger.observer_id != actor_id):
                raise ValueError("Object evidence ledger must belong to the Spotter")
            if ledger is not None or location_ledger is not None or group_fully_visible:
                raise ValueError("Object Spot evidence cannot be combined with Group/Being evidence")
        from discovery import HearingConditions, SpottingConditions
        if sense == 'search':
            if tuple(spotting_conditions):
                raise ValueError('Search has no additional named circumstance modifier table')
            conditions = ()
        else:
            conditions = (HearingConditions(tuple(spotting_conditions)) if sense == 'listen'
                          else SpottingConditions(tuple(spotting_conditions)))
        if sense != 'spot' and (ledger is not None or group_fully_visible
                                or location_ledger is not None or object_ledger is not None):
            raise ValueError('Search and Listen use observer-owned Arena evidence only')
        super().__init__(universe, start_time, None, sense, actor_id,
                         target_id, instrument_id=None, id=id)
        self.end_time = start_time + 6
        if not math.isfinite(self.end_time):
            raise ValueError("end_time must be finite")
        self.spotting_conditions = (() if sense == 'search' else conditions.values)
        self.declared_roll = die_roll
        self.roll = None
        self.path_status = None
        self._encounter = None
        self.ledger = ledger
        self.group_fully_visible = group_fully_visible
        if location_ledger is not None:
            self.location_ledger = location_ledger
        if object_ledger is not None:
            self.object_ledger = object_ledger

    def prepare_schedule(self, encounter):
        """Bind to a validated Encounter but do not manufacture awareness."""
        if self._encounter is not None:
            raise ValueError("spotting activity has already been scheduled")
        if self.start_time < encounter.time:
            raise ValueError("spotting activity cannot begin before scheduling time")
        if self.event_type in ('search', 'listen'):
            target = encounter.get_being(self.target_id)
            if target is None:
                raise ValueError(f'{self.event_type.title()} requires a participating Being target')
            tags = target.current.tags
            premise = 'arena_search_accessible' if self.event_type == 'search' else 'arena_audible'
            if tags.get(premise) is not True:
                raise ValueError(f'{self.event_type.title()} lacks its explicitly represented prerequisite')
        if self.group_fully_visible:
            from statistical_group import StatisticalGroup
            if type(encounter.get_entity(self.target_id)) is not StatisticalGroup:
                raise ValueError("fully visible Group premise requires a StatisticalGroup target")
        location_ledger = self.__dict__.get('location_ledger')
        if location_ledger is not None:
            target = encounter.get_being(self.target_id)
            if target is None:
                raise ValueError("location evidence requires a participating Being target")
            if location_ledger.observer_id != self.actor_id:
                raise ValueError("location evidence ledger owner changed")
        object_ledger = self.__dict__.get('object_ledger')
        if object_ledger is not None:
            from object import ObjectInstance
            target = encounter.get_entity(self.target_id)
            if type(target) is not ObjectInstance:
                raise ValueError("Object evidence requires a participating native ObjectInstance target")
            if object_ledger.observer_id != self.actor_id:
                raise ValueError("Object evidence ledger owner changed")
        return PreparedSchedule.from_action(self, initialization=(('_encounter', encounter),))

    def resolve(self, difficulty_class):
        """Report the check and any awareness; Encounter applies consequences."""
        guard_legacy_action(self, effect=True)
        if self.group_fully_visible:
            raise RuntimeError("exact Group evidence requires native transactional Spot publication")
        if self._encounter is None:
            raise RuntimeError("spotting activity has not been scheduled")
        actor = self._encounter.get_being(self.actor_id)
        target = self._encounter.get_entity(self.target_id)
        if actor is None or target is None:
            raise ValueError("spotting requires participating actor and target")
        distance = self._encounter.distance_between_entities(self.actor_id, self.target_id)
        self.path_status = None
        self.roll = None
        observation = ()
        if distance is None:
            outcome = 'unplaced'
        elif self.event_type == 'spot' and target.geometry is None:
            outcome = 'unmodeled_target'
        elif self.event_type == 'spot':
            path = self._encounter.line_of_sight(self.actor_id, self.target_id)
            self.path_status = None if path is None else path.status
            if path is None or not path.clear:
                outcome = 'no_clear_path'
            else:
                self.roll = self.declared_roll if self.declared_roll is not None else random.randint(1, 20)
                from discovery import SpottingConditions, discovery_dc, racial_discovery_bonus
                target_dc = discovery_dc(target.current.discovery_dc)
                target_dc += SpottingConditions(self.spotting_conditions).dc_adjustment
                race = getattr(actor.current, 'race', None)
                passed = self.roll + racial_discovery_bonus(race, 'spot') >= target_dc
                outcome = 'success' if passed else 'failure'
                if passed:
                    observation = (Perception(self.actor_id, self.target_id,
                                              'spot_check_geometric_path',
                                              distance, None),)
        else:
            from discovery import HearingConditions, SpottingConditions, discovery_dc, racial_discovery_bonus
            tags = target.current.tags
            premise = 'arena_search_accessible' if self.event_type == 'search' else 'arena_audible'
            conditions = (HearingConditions(self.spotting_conditions)
                          if self.event_type == 'listen' else None)
            if tags.get(premise) is not True:
                outcome = 'no_search_access' if self.event_type == 'search' else 'no_audible_evidence'
            elif self.event_type == 'listen' and conditions.impossible:
                outcome = 'impossible'
            else:
                self.roll = self.declared_roll if self.declared_roll is not None else random.randint(1, 20)
                action = self.event_type
                target_dc = discovery_dc(target.current.discovery_dc) + (
                    0 if conditions is None else conditions.dc_adjustment)
                race = getattr(actor.current, 'race', None)
                passed = self.roll + racial_discovery_bonus(race, action) >= target_dc
                outcome = 'success' if passed else 'failure'
                if passed:
                    observation = (Perception(self.actor_id, self.target_id,
                                              f'{action}_authored_prerequisite',
                                              distance, None),)
        return ActionResolution(outcome, (), observation)

    def to_json(self):
        data = json.loads(super().to_json())
        data.update({
            'spotting_conditions': self.spotting_conditions,
            'declared_roll': self.declared_roll,
            'roll': self.roll,
            'path_status': self.path_status,
        })
        return json.dumps(data, indent=2)
