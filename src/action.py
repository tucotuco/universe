#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2024 Rauthiflor LLC"
__version__ = "action.py 2024-03-26T08:36-3:00"

# TODO: Implement drop_weapon()
# TODO: Implement other options in damage_potential()
# TODO: Implement Locations as possible targets
# TODO: Implement Spells as instruments

from transactional_progression import guard_legacy_action
import json
import math

from armor import ArmorInstance
from being import BeingInstance
from event import Event
from object import ObjectInstance
from strategy import Strategy
from utils import roll_dice, get_random_key
from weapon import WeaponInstance
from scheduling import PreparedSchedule

class Action(Event):
    """
    An Event with an ObjectInstance as the actor and an ObjectInstance or Location as an
    optional target.
    """

    def __init__(
        self,
        universe,
        start_time,
        end_time,
        event_type,
        actor_id,
        target_id,
        instrument_id,
        strategy=None,
        location=None,
        name=None,
        parent_event_id=None,
        id=None
    ):
        Event.__init__(
            self,
            universe,
            start_time,
            end_time,
            event_type,
            location,
            name,
            parent_event_id,
            id=id
        )
        self.actor_id = actor_id
        self.target_id = target_id
        self.instrument_id = instrument_id
        self.strategy = strategy or Strategy()
        self.resolution = None  # Set only after successful structured resolution.
        self.end_time = self.calculate_end_time(0, self.strategy.timing_adjustment())
        instrument = self.get_instrument()
        if instrument is not None:
            if self.event_type == 'swing':
                self.end_time = self.calculate_end_time(instrument.current.St(), self.strategy.timing_adjustment())
            elif self.event_type == 'thrust':
                self.end_time = self.calculate_end_time(instrument.current.Tt(), self.strategy.timing_adjustment())

    def to_json(self):
        """
        Serialize the Action as JSON.
        """
        guard_legacy_action(self)
        def handle_circular_refs(obj):
            if isinstance(obj, (Universe)):
                return obj.id  # Return only the ID for Universe
            return obj.__dict__

        parent_json = super().to_json()
        data = {
            **json.loads(parent_json),
            "actor_id": self.actor_id,
            "target_id": self.target_id,
            "instrument_id": self.instrument_id,
            "strategy": json.loads(self.strategy.to_json()),
            "resolution": None if self.resolution is None else self.resolution.to_dict()
        }
        return json.dumps(data, indent = 2)

    def prepare_schedule(self, encounter):
        """Derive a candidate without modifying this Action or the world.

        Encounter invokes only reviewed native implementations. The Encounter
        argument is read-only during preparation, never an extension sandbox.
        """
        if self.event_type == 'feint':
            from encounter import Encounter
            if type(encounter) is not Encounter or encounter.progression_mode != 'transactional':
                raise ValueError('Feint requires the native transactional Encounter pathway')
            actor, target = encounter.get_being(self.actor_id), encounter.get_being(self.target_id)
            weapon = self.get_instrument()
            motion = object.__getattribute__(self, '__dict__').get('feint_motion')
            reach = object.__getattribute__(self, '__dict__').get('reach')
            if (actor is None or target is None or actor is target
                    or self.actor_id not in encounter.being_list
                    or self.target_id not in encounter.being_list):
                raise ValueError('Feint requires two distinct participating Beings')
            if not encounter.is_aware(self.actor_id, self.target_id):
                raise ValueError('Feint requires current native awareness of its target')
            if (weapon is None or self.instrument_id not in actor.armed_with(encounter.universe).values()
                    or motion not in ('swing', 'thrust')
                    or motion not in weapon.get_melee_types()):
                raise ValueError('Feint requires an actually held weapon and supported attack motion')
            rank = actor.current.skills.weapon_skills.get(weapon.original.obj_type, 0)
            if rank <= 1:
                raise ValueError('armed Feint requires advanced skill with the selected weapon')
            native_timing = weapon.St() if motion == 'swing' else weapon.Tt()
            if type(native_timing) not in (int, float) or not math.isfinite(native_timing) or native_timing <= 0:
                raise ValueError('Feint requires a supported positive weapon attack timing')
            duration = max(1, math.ceil(native_timing / 2) - self.strategy.timing_adjustment())
            if (self.end_time - self.start_time != duration
                    or type(reach) not in (int, float) or not math.isfinite(reach) or reach <= 0):
                raise ValueError('Feint timing or native reach declaration is invalid')
            from melee_combat import effective_melee_reach_meters
            expected_reach = effective_melee_reach_meters(actor.current, weapon.current)
            if not math.isclose(reach, expected_reach, rel_tol=1e-12, abs_tol=1e-12):
                raise ValueError('Feint reach does not match native Being/weapon dimensions')
            return PreparedSchedule.from_action(self)
        if self.event_type == 'touch':
            from encounter import Encounter
            if type(encounter) is not Encounter or encounter.progression_mode != 'transactional':
                raise ValueError('Touch requires the native transactional Encounter pathway')
            actor, target = encounter.get_being(self.actor_id), encounter.get_being(self.target_id)
            if (actor is None or target is None or actor is target
                    or self.actor_id not in encounter.being_list
                    or self.target_id not in encounter.being_list):
                raise ValueError('Touch requires two distinct participating Beings')
            if not encounter.is_aware(self.actor_id, self.target_id):
                raise ValueError('Touch requires current native awareness of the target')
            if (self.instrument_id is not None
                    or self.end_time - self.start_time != 1):
                raise ValueError('Touch is a one-second unarmed Action')
            return PreparedSchedule.from_action(self)
        if self.instrument_id is not None and self.event_type not in ('swing', 'thrust'):
            if encounter.universe.get_object_by_id(self.instrument_id) is None:
                raise ValueError('action instrument must be an existing Object')
            from scheduling import UnsupportedScheduleExtension
            raise UnsupportedScheduleExtension(
                'Active instrument semantics require a reviewed native Action adapter')
        return PreparedSchedule.from_action(self)

    def resolve(self, difficulty_class):
        """
        Resolve the effects of this Action.
        """
        guard_legacy_action(self, effect=True)
        hit_type = self.hit_result(difficulty_class)
        if hit_type == "normal":
            self.do_normal_hit()
        elif hit_type == "critical":
            self.do_critical_hit()
        elif hit_type == "fatal":
            self.do_fatal_hit()
        elif hit_type == "hit self":
            self.do_critical_failure()
        elif hit_type == "drop weapon":
            self.do_drop_weapon()
        elif hit_type == "miss":
            self.do_miss()
        elif hit_type == "spectacular miss":
            self.do_spectacular_miss()

    # Actor Management
    def set_actor_id(self, actor_id):
        """
        Set the actor_id of the Action, making sure that it is an ObjectInstance.
        """
        self.actor_id = None
        actor = self.universe.get_object_by_id(actor_id)
        if actor is None:
            print("Ojo, eh! This shouldn't happen. set_actor_id() has no such actor.")
            return
        self.actor_id = actor_id

    def get_actor(self):
        """
        Get the instance of the actor for the Action.
        """
        return self.universe.get_object_by_id(self.actor_id)

    def get_actor_strategy(self):
        """
        Get the strategy used by the actor in the Action.
        """
        actor = self.get_actor()
        if actor is None:
            print("Ojo, eh! This shouldn't happen. get_actor_strategy() has no such actor.")
            return None
        return actor.strategy

    def get_actor_armor_id(self):
        """
        Get the id of the ArmorInstance used by the actor in the Action.
        """
        actor = self.get_actor()
        if actor is None:
            print("Ojo, eh! This shouldn't happen. get_actor_armor_id() has no such actor.")
            return None
        if isinstance(actor, BeingInstance):
            return actor.get_armor_id()
        return None

    # Target Management
    def set_target_id(self, target_id):
        """
        Set the target_id of the Action, making sure that it is an ObjectInstance.
        """
        self.target_id = None
        target = self.universe.get_object_by_id(target_id)
        if target is None:
            print("Ojo, eh! This shouldn't happen. set_target_id() has no such target.")
            return
        self.target_id = target_id

    def get_target(self):
        """
        Get the instance of the target of the Action.
        """
        return self.universe.get_object_by_id(self.target_id)

    def get_target_strategy(self):
        """
        Get the strategy used by the target of the Action.
        """
        target = self.get_target()
        if target is None:
            print("Ojo, eh! This shouldn't happen. get_target_strategy() has no such target.")
            return None
        return target.strategy

    def get_target_armor_id(self):
        """
        Get the id of the ArmorInstance used by the target in the Action.
        """
        target = self.get_target()
        if target is None:
            print("Ojo, eh! This shouldn't happen. get_target_armor_id() has no such target.")
            return None
        if isinstance(target, BeingInstance):
            return target.get_armor_id()
        return None

    # Instrument Management
    def set_instrument_id(self, instrument_id):
        """
        Set the instrument_id used by the actor, making sure that it is a valid instrument type.
        """
        self.instrument_id = None
        instrument = self.universe.get_object_by_id(instrument_id)
        if instrument is None:
            print("Ojo, eh! This shouldn't happen. set_instrument_id() has no such instrument.")
            return
        self.instrument_id = instrument_id

    def get_instrument(self):
        """
        Get the instance of the instrument used for the Action.
        """
        return self.universe.get_object_by_id(self.instrument_id)

    # Strategy Management
    def set_strategy(self, strategy):
        """
        Set the strategy used by the actor. If none is given, make a default one.
        """
        if isinstance(strategy, Strategy):
            print("Ojo, eh! This shouldn't happen. set_strategy() is not setting a Strategy, default new Strategy created.")
            self.strategy = strategy
        else:
            self.strategy = Strategy()

    # Damage Calculation and Application
    def damage_potential(self):
        """
        Get the base damage that can be done by the instrument in the Action.
        """
        instrument = self.get_instrument()
        if self.event_type == 'swing':
            if instrument.Sd() is None:
                return 0
            return instrument.Sd()
        elif self.event_type == 'thrust':
            if instrument.Td() is None:
                return 0
            return instrument.Td()
        return 0

    def _resolve_damage_to_target_shield(self, damage):
        """
        Apply damage to the target's shield and return the amount that gets through.
        """
        # See if damage hits a shield
        guard_legacy_action(self, effect=True)
        target = self.get_target()
        if not isinstance(target, BeingInstance):
            return damage
        shields = target.shielded_with(self.universe)
        target_shield_location = get_random_key(shields)
        target_shield_id = shields.get(target_shield_location)
        return self._resolve_damage_to_shield(target_shield_id, damage)

    def _resolve_damage_to_actor_shield(self, damage):
        """
        Apply damage to the actor's shield and return the amount that gets through.
        """
        # See if damage hits a shield
        guard_legacy_action(self, effect=True)
        actor = self.get_actor()
        if not isinstance(actor, BeingInstance):
            return damage
        shields = actor.shielded_with(self.universe)
        actor_shield_location = get_random_key(shields)
        actor_shield_id = shields.get(actor_shield_location)
#        print(f"actor_shield: {actor_shield_id} location: {actor_shield_location} shields: {shields}")
        return self._resolve_damage_to_shield(actor_shield_id, damage)

    def _resolve_damage_to_shield(self, shield_id, damage):
        """
        Apply damage to a specified shield and return the amount that gets through.
        """
        guard_legacy_action(self, effect=True)
        shield_instance = self.universe.get_object_by_id(shield_id)
#        print(f"{shield_instance.to_json()}")
        if shield_instance is None:
#            print(f"No shield instance in _resolve_damage_to_actor_shield()")
            return damage
        if not isinstance(shield_instance, WeaponInstance):
#            print(f"Shield instance not a WeaponInstance in _resolve_damage_to_actor_shield()")
            return damage
        shield_size = shield_instance.get_weapon_size()
        # If a roll on a d10 is less than or equal to the shield size+4, the attack
        # hits the shield first and it will stop damage equal to the lesser of a) the
        # damage done in the attack and, b) the shield size. For each hit on the
        # shield,  the total damage in excess of the shield size is taken from the
        # shield’s hit points.
        shield_roll = roll_dice("1d10+0")
#        print(f"Shield size: {shield_size} shield roll: {shield_roll}")
        from action_calculations import shield_impact
        intercepted, remaining_damage = shield_impact(damage, shield_size, shield_roll)
        if intercepted:
            # Damage shield
            shield_instance.damage(damage)
#            print(f"Shield {shield_instance.name} was hit for {damage} damage leaving {shield_instance.current.hit_points} hit points")
#            print(f"{remaining_damage} gets through shield")
            return remaining_damage
        else:
#            print(f"All {damage} damage passes shield")
            pass
        return damage

    def _resolve_damage_to_target_armor(self, damage):
        """
        Apply damage to the target's armor and return the amount that gets through.
        """
        guard_legacy_action(self, effect=True)
        target_armor = self.universe.get_object_by_id(self.get_target_armor_id())
        if target_armor is None:
            return damage
        weapon = self.universe.get_object_by_id(self.instrument_id)
        if weapon is None:
            return damage
        attack_type = self.event_type
        penetration_types = weapon.get_penetration_types(attack_type)
        damage_to_armor = target_armor.damage_to_armor(damage, penetration_types)
        damage_through = target_armor.damage_through(damage, weapon, attack_type)
        target_armor.damage(damage_to_armor)
#        print(f"_resolve_damage_to_target_armor(): {target_armor.name} hit for {damage_to_armor} from {attack_type} leaving {target_armor.hit_points()}, penetration types: {penetration_types}, {damage_through} gets through")
        return damage_through

    def _resolve_damage_to_actor_armor(self, damage):
        """
        Apply damage to the actor's armor and return the amount that gets through.
        """
        guard_legacy_action(self, effect=True)
        actor_armor = self.universe.get_object_by_id(self.get_actor_armor_id())
        if actor_armor is None:
            return damage
        weapon = self.universe.get_object_by_id(self.instrument_id)
        if weapon is None:
            return damage
        attack_type = self.event_type
        penetration_types = weapon.get_penetration_types(attack_type)
        damage_to_armor = actor_armor.damage_to_armor(damage, penetration_types)
        damage_through = actor_armor.damage_through(damage, weapon, attack_type)
        actor_armor.damage(damage_to_armor)
#        print(f"PTs: {penetration_types} damage to armor: {damage_to_armor} damage through: {damage_through}")
        return damage_through

    # Hit Results and Types
    def roll_hits(self, roll, difficulty_class):
        """
        Determine if the roll is sufficient to hit.
        """
        actor = self.get_actor()
        if actor is None:
            print("Ojo, eh! This shouldn't happen. roll_hits() has no actor.")
            return False

        # Get the attacker's attack level
        actor_strategy = self.get_actor_strategy()
        aal = 0
        # Weapon skills are indexed by weapon *type*, not instance identifier.
        instrument = self.get_instrument()
        if isinstance(instrument, WeaponInstance):
            aal += actor.get_weapon_skill_level(instrument.current.obj_type)
        if actor_strategy is not None:
            aal += actor_strategy.attack 

        # Get the defender's defense level
        target_strategy = self.get_target_strategy()
        ddl = 0
        if target_strategy is not None:
            ddl = target_strategy.defense
        from action_calculations import attack_hits
        return attack_hits(roll, aal, ddl, difficulty_class)

    def hit_result(self, difficulty_class):
        """
        Determine the type of result from an attempt to hit.
        """
        guard_legacy_action(self, effect=True)
        from action_calculations import hit_outcome
        actor, target = self.get_actor(), self.get_target()
        if actor is None:
            roll_dice('1d20')  # Preserve the direct legacy helper's draw.
            print("Ojo, eh! This shouldn't happen. hit_result() has no actor.")
            return None
        return hit_outcome(difficulty_class, roll_dice, self.roll_hits,
            lambda dc: target.makes_save(target.current.abilities.CON, dc),
            lambda dc: actor.makes_save(actor.current.abilities.DEX, dc))

    def _distribute_hit_damage(self, outcome):
        guard_legacy_action(self, effect=True)
        from action_calculations import damage_path
        self_hit = outcome == 'hit self'
        potential = self.damage_potential()
        failed = False

        def legacy_damage_roll(dice):
            # Direct legacy helpers retain their old malformed-die fallback.
            # Pure evaluation never uses this mutating/error-suppressing adapter.
            nonlocal failed
            if failed:
                return 0
            try:
                return roll_dice(dice)
            except Exception:
                failed = True
                instrument = self.get_instrument()
                method = 'do_critical_hit' if outcome == 'critical' else 'do_normal_hit'
                print(f"Ojo, eh! This shouldn't happen. {method}() trying to roll 1d{{normal_damage}}.")
                print(f'event type: {self.event_type} normal_damage: {potential} SD: {instrument.Sd()} TD: {instrument.Td()}')
                return 0

        damage_path(outcome, potential, self.strategy.extra_damage,
            roll_dice if self_hit else legacy_damage_roll,
            self._resolve_damage_to_actor_shield if self_hit else self._resolve_damage_to_target_shield,
            self._resolve_damage_to_actor_armor if self_hit else self._resolve_damage_to_target_armor,
            lambda ordinary, critical: (self.get_actor() if self_hit else self.get_target()).damage(ordinary + critical))

    def do_normal_hit(self):
        guard_legacy_action(self, effect=True)
        self._distribute_hit_damage('normal')

    def do_critical_hit(self):
        guard_legacy_action(self, effect=True)
        self._distribute_hit_damage('critical')

    def do_critical_failure(self):
        guard_legacy_action(self, effect=True)
        self._distribute_hit_damage('hit self')

    def do_miss(self):
        """
        Resolve the effect of a miss.
        """
        guard_legacy_action(self, effect=True)
        actor = self.get_actor()
#        print(f"{actor.name} missed")

    def do_spectacular_miss(self):
        """
        Resolve the effect of a spectacular miss.
        """
        guard_legacy_action(self, effect=True)
        actor = self.get_actor()
#        print(f"{actor.name} missed spectacularly")

    def do_drop_weapon(self):
        """
        Resolve the effect of dropping a weapon used in the action.
        """
        guard_legacy_action(self, effect=True)
        actor = self.get_actor()
        if actor is None:
            print("Ojo, eh! This shouldn't happen. do_drop_weapon() has no actor.")
            return
        actor.drop_weapon(self.instrument_id)
#        print(f"{actor.name} dropped weapon")

    def do_fatal_hit(self):
        """
        Resolve the effect of a critical hit that kills the target outright.
        """
        guard_legacy_action(self, effect=True)
        target = self.get_target()
        if target is None:
            print("Ojo, eh! This shouldn't happen. do_fatal_hit() has no target.")
            return
        if target.hit_points() > -10:
            target.set_hit_points(-10)
#        print(f"{target.name} fatally hit leaving {target.current.hit_points} hit points")

    # Utility Methods
    def calculate_end_time(self, action_timing, timing_adjustment):
        """
        Determine when the Action will finish.
        """
        if action_timing is None:
            return self.start_time + 1
        if timing_adjustment >= action_timing:
            return self.start_time + 1
        else: 
            return self.start_time + action_timing - timing_adjustment
