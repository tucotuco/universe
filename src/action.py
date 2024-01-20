#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2023 Rauthiflor LLC"
__version__ = "action.py 2024-01-19T09:35-8:00"

# TODO: Implement drop_weapon()
# TODO: Implement damage stopped by armor in do_hit()
# TODO: Implement damage stopped by armor in do_critical_miss()

import json

from utils import roll_dice, get_random_key
from event import Event
from object import ObjectInstance
from strategy import Strategy

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

    def resolve(self, difficult_class):
        """
        Resolve the effects of this Action.
        """
        # Expected to be overriden in subclasses
        print(f"Generic action resolve()")
        return True

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
        Get the actor for the Action.
        """
        return self.universe.get_object_by_id(self.actor_id)

    def set_target_id(self, target_id):
        # TODO: Allow a Location to be a target.
        """
        Set the target_id of the Action, making sure that it is an ObjectInstance.
        """
        self.target_id = None
        target = self.universe.get_object_by_id(target_id)
        if target is None:
            print(f"Target_id {target_id} not found in Universe.")
        elif not isinstance(actor, ObjectInstance):
            print(f"Target {target_id} is not an ObjectInstance.")
        else:
            self.target_id = target_id

    def get_target(self):
        """
        Get the target for the Action.
        """
        return self.universe.get_object_by_id(self.target_id)

    def set_instrument_id(self, instrument_id):
        # TODO: Allow a Spell to be an instrument.
        """
        Set the instrument_id used by the actor, making sure that it is an ObjectInstance
        or other valid instrument (e.g., Spell).
        """
        self.instrument_id = None
        instrument = self.universe.get_object_by_id(instrument_id)
        if instrument is None:
            print(f"Instrument_id {instrument_id} not found in Universe.")
        elif not isinstance(actor, ObjectInstance):
            print(f"Instrument {instrument_id} is not an ObjectInstance.")
        else:
            self.instrument_id = instrument_id

    def get_instrument(self):
        """
        Get the insturment used for the Action.
        """
        return self.universe.get_object_by_id(self.instrument_id)

    def set_strategy(self, strategy):
        """
        Set the strategy used by the actor, making sure that it is a Strategy or None.
        """
        if isinstance(strategy, Strategy):
            self.strategy = strategy
        else:
            self.strategy = Strategy()

    def calculate_end_time(self, action_timing, timing_adjustment):
        """
        Determine when the Action will finish.
        """
        if timing_adjustment >= action_timing:
            return self.start_time + 1  
        else: 
            return self.start_time + action_timing - timing_adjustment

    def roll_hits(self, roll, difficulty_class):
        """
        Determine if the roll is sufficient to hit.
        """
        actor = self.universe.get_object_by_id(self.actor_id)

        # Get the attacker's attack level
        aal = actor.strategy.attack + actor.get_weapon_skill_level(self.instrument_id)

        # Get the defender's defense level
        target = self.universe.get_object_by_id(self.target_id)
        ddl = target.strategy.defense
        return roll + aal - ddl >= difficulty_class

    def do_hit(self, remaining_damage):
        """
        Distribute damage from a successful critical hit.
        """
        # See if the attack hit a shield
        target = self.universe.get_object_by_id(self.target_id)
        shields = target.shielded_with(self.universe)
        target_shield_location = get_random_key(shields)
        target_shield = shields.get(target_shield_location)
        if target_shield is not None:
            shield_size = target_shield.weapon_size
            # If a roll on a d10 is less than or equal to the shield size+4, the attack
            # hits the shield first and it will stop damage equal to the lesser of a) the
            # damage done in the attack and, b) the shield size. For each hit on the
            # shield,  the total damage in excess of the shield size is taken from the
            # shield’s hit points.
            shield_roll = roll_dice("1d10+0")
            if shield_roll <= shield_size + 4:
                # Damage shield
                target_shield.damage(remaining_damage)
                remaining_damage -= shield_size
                print(f"Shield for {target.name} was hit for {remaining_damage} damage leaving {target_shiled.current.hit_points} hit points")
                if remaining_damage < 0:
                    return
        # See if the remainder hits armor
        target_armor = target.get_armor()
        if target_armor is not None:
            # The amount of damage that gets through armor is the amount that got past a
            # shield (if any) minus the number in the damage column under the appropriate
            # penetration type (see the Armors Table). Critical hit damage (that part of
            # damage from extra dice due to a hit being critical) is not stopped by armor.

            # If a roll on a d10 is less than or equal to the shield size+4, the attack
            # hits the shield first and it will stop damage equal to the lesser of a) the
            # damage done in the attack and, b) the shield size. For each hit on the
            # shield,  the total damage in excess of the shield size is taken from the
            # shield’s hit points.
            pass

        # Deliver any remaining damage to the target
        target.current.hit_points -= remaining_damage
        print(f"{target.name} was hit for {remaining_damage} damage leaving {target.current.hit_points} hit points")

    def do_critical_miss(self, remaining_damage):
        """
        Critical miss - actor hits self
        """
        actor = self.universe.get_object_by_id(self.actor_id)

        # Distribute damage from an attack that hits self.
        # Critical misses to not hit shields
        # See if the remainder hits armor
        armor = actor.get_armor()
        if armor is not None:
            # The amount of damage that gets through armor is the amount that got past a
            # shield (if any) minus the number in the damage column under the appropriate
            # penetration type (see the Armors Table). Critical hit damage (that part of
            # damage from extra dice due to a hit being critical) is not stopped by armor.

            # If a roll on a d10 is less than or equal to the shield size+4, the attack
            # hits the shield first and it will stop damage equal to the lesser of a) the
            # damage done in the attack and, b) the shield size. For each hit on the
            # shield,  the total damage in excess of the shield size is taken from the
            # shield’s hit points.
            pass

        # Deliver any remaining damage to the target
        actor.current.hit_points -= remaining_damage
        print(f"{actor.name} hit self for {remaining_damage} damage leaving {actor.current.hit_points} hit points")

    def drop_weapon(self):
        """
        Drop weapon
        """
        actor = self.universe.get_object_by_id(self.actor_id)
        print(f"{actor.name} drops weapon (not implemented)")

    def do_fatal_hit(self):
        """
        Critical hit that kills the target outright
        """
        target = self.universe.get_object_by_id(self.target_id)
        target.set_hit_points(-10)
        print(f"{target.name} fatally hit leaving {target.current.hit_points} hit points")

    def do_damage(self, max_damage, difficulty_class):
        actor = self.universe.get_object_by_id(self.actor_id)
        target = self.universe.get_object_by_id(self.target_id)

        roll = roll_dice("1d20")
        print(f"Roll to hit: {roll}")
        extra_damage = self.strategy.extra_damage

        if roll == 20:
            # The hit is a threat
            threat_roll = roll_dice("1d20")
            print(f"Threat roll: {threat_roll}")
            if threat_roll == 20:
                saved = actor.makes_save(actor.current.abilities.CON, difficulty_class)
                if not saved:
                    # Fatal
                    print(f"*** Save failed, fatal hit: {threat_roll} ***")
                    self.do_fatal_hit()
                else:
                    # Revert from fatal hit to critical hit
                    # Calculate the critical hit damage
                    damage_roll = roll_dice(f"2d{max_damage}+{extra_damage}")
                    print(f"*** Save successful, critical hit (damage={damage_roll}) ***")
                    self.do_hit(damage_roll)
            elif self.roll_hits(threat_roll, difficulty_class):
                # Critical hit
                damage_roll = roll_dice(f"2d{max_damage}+{extra_damage}")
                print(f"*** Critical hit (damage={damage_roll}) ***")
                self.do_hit(damage_roll)
            else:
                # Normal hit
                die = f"1d{max_damage}+{extra_damage}"
                damage_roll = roll_dice(die)
#                print(f"{max_damage} {extra_damage} {damage_roll} {die}")
                self.do_hit(damage_roll)
        elif roll == 1:
            # The attempt was a potentially dangerous failure
            threat_roll = roll_dice("1d20")
            if threat_roll == 1:
                # Hit actor instead of target
                damage_roll = roll_dice(f"1d{max_damage}+{extra_damage}")
                print(f"*** Critical miss (damage={damage_roll}) ***")
                self.do_critical_miss(damage_roll)
            elif not self.roll_hits(roll, difficulty_class):
                # Actor must make Reflex Saving Throw
                saved = actor.makes_save(
                    actor.current.abilities.DEX, difficulty_class
                )
                if not saved:
                    # Actor drops weapon
                    self.drop_weapon()
                else:
                    # Spectacular miss
                    print(f"{actor.name} misses spectacularly")
            else:
                # Miss
                print(f"{actor.name} misses")
        elif self.roll_hits(roll, difficulty_class):
            # Normal hit
            die = f"1d{max_damage}+{extra_damage}"
            damage_roll = roll_dice(die)
            self.do_hit(damage_roll)
        else:
            # No hit
            print(f"{actor.name} misses")

class Swing(Action):
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
        Action.__init__(
            self,
            universe,
            start_time,
            end_time,
            event_type,
            actor_id,
            target_id,
            instrument_id,
            strategy,
            location,
            name,
            parent_event_id,
        )
        instrument = self.universe.get_object_by_id(self.instrument_id)
        self.end_time = self.calculate_end_time(instrument.current.St(), self.strategy.timing_adjustment())

    def resolve(self, difficulty_class):
        """
        Resolve the effects of this Swing.
        """
        instrument = self.universe.get_object_by_id(self.instrument_id)
#        print(f"Swing action resolve() instrument.Sd(): {instrument.Sd()}  {self.id}")
        self.do_damage(instrument.Sd(), difficulty_class)

class Thrust(Action):
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
        Action.__init__(
            self,
            universe,
            start_time,
            end_time,
            event_type,
            actor_id,
            target_id,
            instrument_id,
            strategy,
            location,
            name,
            parent_event_id,
        )
        instrument = self.universe.get_object_by_id(self.instrument_id)
        self.end_time = self.calculate_end_time(instrument.current.Tt(), self.strategy.timing_adjustment())

    def resolve(self, difficulty_class):
        """
        Resolve the effects of this Thrust.
        """
        instrument = self.universe.get_object_by_id(self.instrument_id)
#        print(f"Thrust action resolve() instrument.Td(): {instrument.Sd()} {self.id}")
        self.do_damage(instrument.Td(), difficulty_class)
