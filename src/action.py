#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2024 Rauthiflor LLC"
__version__ = "action.py 2024-02-27T15:38-3:00"

# TODO: Implement drop_weapon()
# TODO: Update documentation to reflect that Shields also do not stop the extra critical hit damage (see do_critical_hit())
# TODO: Implement other options in damage_potential()
# TODO: Implement Locations as possible targets
# TODO: Implement Spells as instruments

import json

from armor import ArmorInstance
from event import Event
from object import ObjectInstance
from strategy import Strategy
from utils import roll_dice, get_random_key
from weapon import WeaponInstance

class Action(Event):
    """
    An Event with an ObjectInstance as the actor and an ObjectInstance or Location as a
    target.
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
        )
        self.actor_id = actor_id
        self.target_id = target_id
        self.instrument_id = instrument_id
        self.strategy = strategy or Strategy()
        self.end_time = self.calculate_end_time(0, self.strategy.timing_adjustment())
        instrument = self.get_instrument()
        if instrument is not None:
            if self.event_type == 'swing':
                self.end_time = self.calculate_end_time(instrument.current.St(), self.strategy.timing_adjustment())
            elif self.event_type == 'thrust':
                self.end_time = self.calculate_end_time(instrument.current.Tt(), self.strategy.timing_adjustment())

    # JSON Serialization
    def to_json(self):

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
            "strategy": json.loads(self.strategy.to_json())
        }
        return json.dumps(data, indent = 2)

    # Action Resolution
    def resolve(self, difficulty_class):
        """
        Resolve the effects of this Action.
        """
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
            print(f"Actor_id {actor_id} not found in Universe.")
        elif not isinstance(actor, ObjectInstance):
            print(f"Actor {actor_id} is not an ObjectInstance.")
        else:
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
            return None
        return actor.strategy

    def get_actor_armor_id(self):
        """
        Get the id of the ArmorInstance used by the actor in the Action.
        """
        actor = self.get_actor()
        if actor is None:
            return None
        return actor.get_armor_id()

    # Target Management
    def set_target_id(self, target_id):
        """
        Set the target_id of the Action, making sure that it is an ObjectInstance.
        """
        self.target_id = None
        target = self.universe.get_object_by_id(target_id)
        if target is None:
            print(f"Target_id {target_id} not found in Universe.")
        elif not isinstance(target, ObjectInstance):
            print(f"Target {target_id} is not an ObjectInstance.")
        else:
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
            return None
        return target.strategy

    def get_target_armor_id(self):
        target = self.get_target()
        if target is None:
            return None
        return target.get_armor_id()

    # Instrument Management
    def set_instrument_id(self, instrument_id):
        """
        Set the instrument_id used by the actor, making sure that it is an ObjectInstance
        or other valid instrument (e.g., Spell).
        """
        self.instrument_id = None
        instrument = self.universe.get_object_by_id(instrument_id)
        if instrument is None:
            print(f"Instrument_id {instrument_id} not found in Universe.")
        elif not isinstance(instrument, ObjectInstance):
            print(f"Instrument {instrument_id} is not an ObjectInstance.")
        else:
            self.instrument_id = instrument_id

    def get_instrument(self):
        """
        Get the instance of the instrument used for the Action.
        """
        return self.universe.get_object_by_id(self.instrument_id)

    # Strategy Management
    def set_strategy(self, strategy):
        """
        Set the strategy used by the actor, making sure that it is a Strategy or None.
        """
        if isinstance(strategy, Strategy):
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
        target = self.get_target()
        shields = target.shielded_with(self.universe)
        target_shield_location = get_random_key(shields)
        target_shield_id = shields.get(target_shield_location)
        return self._resolve_damage_to_shield(target_shield_id, damage)

    def _resolve_damage_to_actor_shield(self, damage):
        """
        Apply damage to the actor's shield and return the amount that gets through.
        """
        # See if damage hits a shield
        actor = self.get_actor()
        shields = actor.shielded_with(self.universe)
        actor_shield_location = get_random_key(shields)
        actor_shield_id = shields.get(actor_shield_location)
#        print(f"actor_shield: {actor_shield_id} location: {actor_shield_location} shields: {shields}")
        return self._resolve_damage_to_shield(actor_shield_id, damage)

    def _resolve_damage_to_shield(self, shield_id, damage):
        """
        Apply damage to a specified shield and return the amount that gets through.
        """
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
        if shield_roll <= int(shield_size) + 4:
            # Damage shield
            shield_instance.damage(damage)
#            print(f"Shield {shield_instance.name} was hit for {damage} damage leaving {shield_instance.current.hit_points} hit points")
            remaining_damage = damage - int(shield_size)
            if remaining_damage < 0:
                remaining_damage = 0
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
            return False

        # Get the attacker's attack level
        actor_strategy = self.get_actor_strategy()
        aal = 0
        aal += actor.get_weapon_skill_level(self.instrument_id)
        if actor_strategy is not None:
            aal += actor_strategy.attack 

        # Get the defender's defense level
        target_strategy = self.get_target_strategy()
        ddl = 0
        if target_strategy is not None:
            ddl = target_strategy.defense
        return roll + aal - ddl >= difficulty_class

    def hit_result(self, difficulty_class):
        roll = roll_dice("1d20")
        actor = self.get_actor()
        if actor is None:
            return "ACTOR_ERROR"
        if roll == 20:
            # The hit is a threat
            threat_roll = roll_dice("1d20")
            if threat_roll == 20:
                saved = actor.makes_save(actor.current.abilities.CON, difficulty_class)
                if not saved:
                    # Fatal hit
                    return "fatal"
                else:
                    # Revert from fatal hit to critical hit
                    return "critical"
            elif self.roll_hits(threat_roll, difficulty_class):
                # Critical hit
                return "critical"
            else:
                # Normal hit
                return "normal"
        elif roll == 1:
            # The attempt was a potentially dangerous failure
            threat_roll = roll_dice("1d20")
            if threat_roll == 1:
                # Hit actor instead of target
                return "hit self"
            elif not self.roll_hits(roll, difficulty_class):
                # Actor must make Reflex Saving Throw
                saved = False
                if actor is not None:
                    saved = actor.makes_save(actor.current.abilities.DEX, difficulty_class)
                if saved == False:
                    return "drop weapon"
                else:
                    # Spectacular miss
                    return "spectacular miss"
            else:
                # Miss
                return "miss"
        elif self.roll_hits(roll, difficulty_class):
            # Normal hit
            return "normal"
        else:
            # Miss
            return "miss"

    def do_normal_hit(self):
        """
        Distribute damage from a successful normal hit.
        """
        normal_damage = self.damage_potential()
        extra_damage = self.strategy.extra_damage
        damage_roll = 0
        try:
            damage_roll = roll_dice(f"1d{normal_damage}")
        except Exception as e:
            instrument = self.get_instrument()
            print(f"event type: {self.event_type} normal_damage: {normal_damage} SD: {instrument.Sd()} TD: {instrument.Td()}")
        remaining_damage = self._resolve_damage_to_target_shield(damage_roll + extra_damage)
        remaining_damage = self._resolve_damage_to_target_armor(remaining_damage)
        self.get_target().damage(remaining_damage)

    def do_critical_hit(self):
        """
        Distribute damage from a successful critical hit.
        """
        # Critical hit damage (that part of damage from extra dice due to a hit being 
        # critical) is not stopped by shields or armor.
        normal_damage = self.damage_potential()
        extra_damage = self.strategy.extra_damage
        damage_roll = 0
        critical_damage_roll = 0
        try:
            damage_roll = roll_dice(f"1d{normal_damage}")
            critical_damage_roll = roll_dice(f"1d{normal_damage}")
        except Exception as e:
            instrument = self.get_instrument()
            print(f"event type: {self.event_type} normal_damage: {normal_damage} SD: {instrument.Sd()} TD: {instrument.Td()}")
        remaining_damage = self._resolve_damage_to_target_shield(damage_roll + extra_damage)
        remaining_damage = self._resolve_damage_to_target_armor(remaining_damage)
        self.get_target().damage(remaining_damage + critical_damage_roll)

    def do_critical_failure(self):
        """
        Distribute damage to the actor from a critical failure.
        """
        normal_damage = self.damage_potential()
        extra_damage = self.strategy.extra_damage
        damage_roll = roll_dice(f"1d{normal_damage}")
        remaining_damage = self._resolve_damage_to_actor_shield(damage_roll + extra_damage)
        remaining_damage = self._resolve_damage_to_actor_armor(remaining_damage)
        self.get_actor().damage(remaining_damage)

    def do_miss(self):
        actor = self.get_actor()
#        print(f"{actor.name} missed")

    def do_spectacular_miss(self):
        actor = self.get_actor()
#        print(f"{actor.name} missed spectacularly")

    def do_drop_weapon(self):
        """
        Drop weapon
        """
        # TODO: do_drop_weapon() Not implemented
        actor = self.get_actor()
        if actor is None:
            return
#        print(f"{actor.name} drops weapon (not implemented)")

    def do_fatal_hit(self):
        """
        Critical hit that kills the target outright
        """
        target = self.get_target()
        if target is None:
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
