#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2023 Rauthiflor LLC"
__version__ = "action.py 2023-12-28T12:04-53:00"

# TODO: Reduce redundancy between Swing and Thrust

import json

from utils import roll_dice, get_random_key
from event import Event
from object import ObjectInstance
from strategy import Strategy

class Action(Event):
    '''
    An Event with an ObjectInstance as the actor and an ObjectInstance or Location as a
    target.
    '''
    def __init__(self, universe, start_time, end_time, event_type, actor_id, target_id, 
                instrument_id, strategy=None, location=None, name=None, 
                parent_event_id=None):
        Event.__init__(self, universe, start_time, end_time, event_type, location, name, 
                parent_event_id)
        self.actor_id = actor_id
        self.target_id = target_id
        self.instrument_id = instrument_id
        self.strategy = strategy or Strategy()

    def resolve(self, current_time):
        '''
        Resolve the effects of this Action at the current_time.
        '''
        # Expected to be overriden in subclasses
        pass

    def set_actor_id(self, actor_id):
        '''
        Set the actor_id of the Action, making sure that it is an ObjectInstance.
        '''
        self.actor_id = actor_id

    def set_target_id(self, target_id):
        '''
        Set the target_id of the Action, making sure that it is either an ObjectInstance or 
        a Location.
        '''
        self.target_id = target_id

    def set_instrument_id(self, instrument_id):
        '''
        Set the instrument_id used by the actor, making sure that it is an ObjectInstance 
        or other valid instrument (e.g., Spell).
        '''
        self.instrument_id = instrument_id

    def set_strategy(self, strategy):
        '''
        Set the strategy used by the actor, making sure that it is a Strategy or None.
        '''
        self.strategy = strategy

    def roll_hits(self, roll):
        '''
        Determine if the roll is sufficient to hit.
        '''
        actor = self.universe.get_object_by_id(self.actor_id)
        parent_event = self.universe.get_event_by_id(self.parent_event_id)

        # Get the Difficulty Class from the parent event.
        dcl = parent_event.difficulty_class

        # Get the attacker's attack level
        aal = actor.strategy.attack + actor.get_weapon_skill_level(self.instrument_id)

        # Get the defender's defense level
        target = self.universe.get_object_by_id(self.target_id)
        ddl = target.strategy.defense
#        print(f"Roll: {roll} dcl: {dcl} aal: {aal} ddl: {ddl} {roll + aal - ddl >= dcl}")
        return roll + aal - ddl >= dcl

    def do_normal_hit(self, max_damage):
        '''
        Distribute damage from a successful hit.
        '''
        # Calculate the damage
        extra_damage = self.strategy.extra_damage
        damage_roll = roll_dice(f'1d{max_damage}+{extra_damage}')
        remaining_damage = damage_roll
        # See if the swing hit a shield
#        print(f"Normal hit max_damage={max_damage} extra_damage={extra_damage} damage_roll={damage_roll} remaining_damage={remaining_damage}")
        
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
            shield_roll = roll_dice('1d10+0')
            if shield_roll <= shield_size + 4:
                # Damage shield
                target_shield.damage(remaining_damage)
                remaining_damage -= shield_size
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

    def do_critical_hit(self, max_damage):
        '''
        Distribute damage from a successful hit.
        '''
        target = self.universe.get_object_by_id(self.target_id)
        print(f"{target.name} critically hit (not implemented)")

    def do_critical_miss(self):
        '''
        Critical miss
        '''
        actor = self.universe.get_object_by_id(self.actor_id)
        print(f"{actor.name} critically misses (not implemented)")

    def do_super_spectacular_miss(self):
        '''
        Super spectacular miss
        '''
        actor = self.universe.get_object_by_id(self.actor_id)
        print(f"{actor.name} super spectacularly misses (not implemented)")

    def do_spectacular_miss(self):
        '''
        Spectacular miss
        '''
        actor = self.universe.get_object_by_id(self.actor_id)
        print(f"{actor.name} spectacularly misses (not implemented)")

    def do_miss(self):
        '''
        Miss
        '''
        actor = self.universe.get_object_by_id(self.actor_id)
        print(f"{actor.name} misses (not implemented)")

    def drop_weapon(self):
        '''
        Drop weapon
        '''
        actor = self.universe.get_object_by_id(self.actor_id)
        print(f"{self.actor.name} drops weapon (not implemented)")

    def do_fatal_hit(self):
        '''
        Critical hit that kills the target outright
        '''
        target = self.universe.get_object_by_id(self.target_id)
        target.set_hit_points(-10)
        print(f"{target.name} fatally hit leaving {target.current.hit_points} hit points")

    def do_damage(self, current_time, max_damage):
        if self.end_time != current_time:
            return

        actor = self.universe.get_object_by_id(self.actor_id)
        target = self.universe.get_object_by_id(self.target_id)
        parent_event = self.universe.get_event_by_id(self.parent_event_id)

        roll = roll_dice('1d20')
        print(f"Roll to hit: {roll}")

        if roll == 20:
            # The hit is a threat
            threat_roll = roll_dice('1d20')
            if threat_roll == 20:
                # Fatal
                self.do_fatal_hit()
            elif self.roll_hits(threat_roll):
                # Critical hit
                self.do_critical_hit(max_damage)
            else:
                # Normal hit
                self.do_normal_hit(max_damage)
        elif roll == 1:
            # The attempt was a potentially dangerous failure
            threat_roll = roll_dice('1d20')
            if threat_roll == 1:
                # Hit actor instead of target
                self.do_critical_miss()
            elif not self.roll_hits(roll):
                # Actor must make Reflex Saving Throw
                saved = actor.makes_save(actor.current.abilities.DEX, parent_event.difficulty_class)
                if saved == FALSE:
                    # Super spectacular miss
                    self.do_super_spectacular_miss()
                else:
                    # Actor drops weapon
                    self.drop_weapon()
            else:
                # Spectacular miss
                self.do_spectacular_miss()
        elif self.roll_hits(roll):
            # Normal hit
            self.do_normal_hit(max_damage)
        else:
            # No hit
            self.do_miss()

class Swing(Action):
    def __init__(self, universe, start_time, end_time, event_type, actor_id, target_id, 
                instrument_id, strategy=None, location=None, name=None, 
                parent_event_id=None):
        Action.__init__(self, universe, start_time, end_time, event_type, actor_id, 
                target_id, instrument_id, strategy, location, name, parent_event_id)
        self.end_time = self.calculate_end_time()

    def calculate_end_time(self):
        '''
        Determine when the Action will finish.
        '''
        instrument = self.universe.get_object_by_id(self.instrument_id)
        return self.start_time + instrument.current.St() - self.strategy.timing_adjustment()

    def resolve(self, current_time):
        '''
        Resolve the effects of this Swing at the current_time.
        '''
        instrument = self.universe.get_object_by_id(self.instrument_id)
        self.do_damage(current_time, instrument.Sd())

class Thrust(Action):
    def __init__(self, universe, start_time, end_time, event_type, actor_id, target_id, 
                instrument_id, strategy=None, location=None, name=None, 
                parent_event_id=None):
        Action.__init__(self, universe, start_time, end_time, event_type, actor_id, 
                target_id, instrument_id, strategy, location, name, parent_event_id)
        self.end_time = self.calculate_end_time()

    def calculate_end_time(self):
        '''
        Determine when the Action will finish.
        '''
        instrument = self.universe.get_object_by_id(self.instrument_id)
        return self.start_time + instrument.current.Tt() - self.strategy.timing_adjustment()

    def resolve(self, current_time):
        '''
        Resolve the effects of this Thrust at the current_time.
        '''
        instrument = self.universe.get_object_by_id(self.instrument_id)
        self.do_damage(current_time, instrument.Td())
