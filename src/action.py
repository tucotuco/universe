#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2023 Rauthiflor LLC"
__version__ = "action.py 2023-12-27T01:03-03:00"

# TODO: 

import json

from event import Event
from object import ObjectInstance
from strategy import Strategy

class Action(Event):
    '''
    An Event with an ObjectInstance as the actor and an ObjectInstance or Location as a
    target.
    '''
    def __init__(self, universe, start_time, end_time, action_type, actor, target, 
                instrument, strategy=None, location=None, name=None, parent=None):
        Event.__init__(self, universe, start_time, end_time, action_type, location, name, parent)
        self.actor = actor
        self.target = target
        self.instrument = instrument
        self.strategy = strategy or Strategy()

    def set_actor(self, actor):
        '''
        Set the actor of the Action, making sure that it is an ObjectInstance.
        '''
        self.actor = actor
        return actor

    def set_target(self, target):
        '''
        Set the target of the Action, making sure that it is either an ObjectInstance or 
        a Location.
        '''
        self.target = target

    def set_instrument(self, instrument):
        '''
        Set the instrument used by the actor, making sure that it is an ObjectInstance or 
        other valid instrument (e.g., Spell).
        '''
        self.instrument = instrument

    def set_strategy(self, strategy):
        '''
        Set the strategy used by the actor, making sure that it is a Strategy or None.
        '''
        self.strategy = strategy
        return strategy

class Swing(Action):
    def __init__(self, universe, start_time, end_time, action_type, actor, target, 
                instrument, strategy=None, location=None, name=None, parent=None):
        Action.__init__(self, universe, start_time, end_time, action_type, actor, target, 
                instrument, strategy, location, name, parent)
#        print(f"action.py Swing.__init__() instrument: {instrument.to_json()}")
        self.end_time = self.calculate_end_time()
#        print(f"action.py Swing.__init__() instrument: {instrument}")

    def calculate_end_time(self):
        print(f"action.py Swing.calculate_end_time() start_time: {self.start_time}")
        print(f"action.py Swing.calculate_end_time() Tt: {self.instrument.current.Tt()}")
        print(f"action.py Swing.calculate_end_time() timing: {self.strategy.timing_adjustment()}")
        print(f"action.py Swing.calculate_end_time() Action: {self.to_json()}")
        
        return self.start_time + self.instrument.current.St() - self.strategy.timing_adjustment()

    def resolve(self, current_time):
        '''
        Resolve the effects of this Action at the current_time.
        '''
        if self.start_time == current_time:
            roll = roll_dice('1d20')
            if roll == 20:
                # The hit is a threat
                thxreat_roll = roll_dice('1d20')
                if roll == 20:
                    # Fatal
                    target.set_hit_points(-10)
                elif self.roll_hits(threat_roll):
                    # Critical hit
                    do_critical_hit()
                else:
                    # Normal hit
                    self.do_normal_hit()
            elif roll == 1:
                # The attempt was a potentially dangerous failure
                thxreat_roll = roll_dice('1d20')
                if roll == 1:
                    # Hit actor instead of target
                    self.do_critical_miss()
                elif not self.roll_hits(roll):
                    # Actor must make Reflex Saving Throw
                    if actor.makes_reflex_save(self.parent.difficulty_class):
                        # Super spectacular miss
                        pass
                    else:
                        # Actor drops weapon
                        # TODO: Implement dropping weapon
                        pass
                else:
                    # Spectacular miss
                    # TODO: Consider if there should be any other effect of spectacular miss
                    pass
            elif self.roll_hits(roll):
                # Normal hit
                self.do_normal_hit()
            else:
                # No hit
                pass

class Thrust(Action):
    def __init__(self, universe, start_time, end_time, action_type, actor, target, 
                instrument, strategy=None, location=None, name=None, parent=None):
        Action.__init__(self, universe, start_time, end_time, action_type, actor, target, 
                instrument, strategy, location, name, parent)
#        print(f"action.py Thrust.__init__() instrument: {instrument.to_json()}")
        self.end_time = self.calculate_end_time()

    def calculate_end_time(self):
        print(f"action.py Thrust.calculate_end_time() start_time: {self.start_time}")
        print(f"action.py Thrust.calculate_end_time() St: {self.instrument.current.Tt()}")
        print(f"action.py Thrust.calculate_end_time() timing: {self.strategy.timing_adjustment()}")
        print(f"action.py Swing.calculate_end_time() Action: {self.to_json()}")
        return self.start_time + self.instrument.current.Tt() - self.strategy.timing_adjustment()

    def resolve(self, current_time):
        '''
        Resolve the effects of this Action at the current_time.
        '''
        if self.start_time == current_time:
            roll = roll_dice('1d20')
            if roll == 20:
                # The hit is a threat
                thxreat_roll = roll_dice('1d20')
                if roll == 20:
                    # Fatal
                    target.set_hit_points(-10)
                elif self.roll_hits(threat_roll):
                    # Critical hit
                    do_critical_hit()
                else:
                    # Normal hit
                    self.do_normal_hit()
            elif roll == 1:
                # The attempt was a potentially dangerous failure
                thxreat_roll = roll_dice('1d20')
                if roll == 1:
                    # Hit actor instead of target
                    self.do_critical_miss()
                elif not self.roll_hits(roll):
                    # Actor must make Reflex Saving Throw
                    if actor.makes_reflex_save(self.parent.difficulty_class):
                        # Super spectacular miss
                        pass
                    else:
                        # Actor drops weapon
                        # TODO: Implement dropping weapon
                        pass
                else:
                    # Spectacular miss
                    # TODO: Consider if there should be any other effect of spectacular miss
                    pass
            elif self.roll_hits(roll):
                # Normal hit
                self.do_normal_hit()
            else:
                # No hit
                pass

    def roll_hits(self, roll):
        '''
        Determine if the roll is sufficient to hit.
        '''
        # Get the DC from the parent.
        dcl = self.parent.difficulty_class
        # Get the attacker's attack level
        aal = actor.strategy.attack + get_weapon_skill_level(actor.instrument)
        # Get the defender's defense level
        ddl = target.strategy.defense
        return roll + aal - ddl >= dcl

    def do_normal_hit(self, weapon_dict):
        '''
        Distribute damage from a successful hit.
        '''
        # Calculate the damage
        max_damage = self.instrument.SD()
        extra_damage = self.strategy.extra_damage
        damage_roll = roll_dice(f'1d{max_damage}+{extra_damage}')
        remaining_damage = damage_roll
        # See if the swing hit a shield
        shields = self.target.shielded_with(weapon_dict)
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
        target_armor = self.target.get_armor()
        # TODO: damage by most favorable penetration type
        # Deliver the remainder to the target
        print("implement remainder of damage to target")

    def do_critical_hit(self):
        '''
        Distribute damage from a successful hit.
        '''
        # See if the swing hit a shield
        # See if the remainder hits armor
        # deliver the remainder to the target

    def do_critical_miss(self):
        '''
        Distribute damage from a successful hit.
        '''
        # See if the swing hit a shield
        # See if the remainder hits armor
        # deliver the remainder to the target
