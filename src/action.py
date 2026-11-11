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
        if self.event_type == 'coup de grace':
            from encounter import Encounter
            if type(encounter) is not Encounter or encounter.progression_mode != 'transactional':
                raise ValueError('Coup de grace requires the native transactional Encounter pathway')
            actor, target = encounter.get_being(self.actor_id), encounter.get_being(self.target_id)
            weapon = self.get_instrument()
            motion = object.__getattribute__(self, '__dict__').get('coup_motion')
            reach = object.__getattribute__(self, '__dict__').get('reach')
            if (actor is None or target is None or actor is target
                    or self.actor_id not in encounter.being_list
                    or self.target_id not in encounter.being_list):
                raise ValueError('Coup de grace requires two distinct participating Beings')
            if not encounter.is_aware(self.actor_id, self.target_id):
                raise ValueError('Coup de grace requires current native awareness of its target')
            if actor.is_helpless() or not target.is_helpless():
                raise ValueError('Coup de grace requires an able Actor and helpless target')
            if (weapon is None or self.instrument_id not in actor.armed_with(encounter.universe).values()
                    or motion not in ('swing', 'thrust')
                    or motion not in weapon.get_melee_types()):
                raise ValueError('Coup de grace requires an actually held weapon and supported motion')
            native_timing = weapon.St() if motion == 'swing' else weapon.Tt()
            if (type(native_timing) not in (int, float) or not math.isfinite(native_timing)
                    or native_timing <= 0
                    or self.end_time - self.start_time != max(1, native_timing - self.strategy.timing_adjustment())
                    or type(reach) not in (int, float) or not math.isfinite(reach) or reach <= 0):
                raise ValueError('Coup de grace timing or native reach declaration is invalid')
            from melee_combat import effective_melee_reach_meters
            expected_reach = effective_melee_reach_meters(actor.current, weapon.current)
            if not math.isclose(reach, expected_reach, rel_tol=1e-12, abs_tol=1e-12):
                raise ValueError('Coup de grace reach does not match native Being/weapon dimensions')
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
        if self.event_type == 'strike object':
            from encounter import Encounter
            if type(encounter) is not Encounter or encounter.progression_mode != 'transactional':
                raise ValueError('Strike an object requires the native transactional Encounter pathway')
            actor = encounter.get_being(self.actor_id)
            target = encounter.universe.get_object_by_id(self.target_id)
            weapon = self.get_instrument()
            motion = object.__getattribute__(self, '__dict__').get('object_motion')
            reach = object.__getattribute__(self, '__dict__').get('reach')
            if actor is None or self.actor_id not in encounter.being_list or target is None or target is actor:
                raise ValueError('Strike an object requires a participating Being and a native Object target')
            if not encounter.is_aware(self.actor_id, self.target_id):
                raise ValueError('Strike an object requires current native awareness of its target')
            if weapon is None or self.instrument_id not in actor.armed_with(encounter.universe).values():
                raise ValueError('Strike an object requires an actually held weapon')
            if motion not in ('swing', 'thrust') or motion not in weapon.get_melee_types():
                raise ValueError('Strike an object requires a supported weapon motion')
            native_timing = weapon.St() if motion == 'swing' else weapon.Tt()
            if (type(native_timing) not in (int, float) or not math.isfinite(native_timing)
                    or native_timing <= 0 or self.end_time - self.start_time !=
                    max(1, native_timing - self.strategy.timing_adjustment())
                    or type(reach) not in (int, float) or not math.isfinite(reach) or reach <= 0):
                raise ValueError('Strike an object timing or reach declaration is invalid')
            from melee_combat import effective_melee_reach_meters
            expected_reach = effective_melee_reach_meters(actor.current, weapon.current)
            if not math.isclose(reach, expected_reach, rel_tol=1e-12, abs_tol=1e-12):
                raise ValueError('Strike an object reach does not match native Being/weapon dimensions')
            return PreparedSchedule.from_action(self)
        if self.event_type == 'break weapon':
            from encounter import Encounter
            if type(encounter) is not Encounter or encounter.progression_mode != 'transactional':
                raise ValueError('Break weapon requires the native transactional Encounter pathway')
            actor, defender = encounter.get_being(self.actor_id), encounter.get_being(self.target_id)
            weapon, victim_weapon = self.get_instrument(), encounter.universe.get_object_by_id(
                object.__getattribute__(self,'__dict__').get('break_weapon_id'))
            motion = object.__getattribute__(self,'__dict__').get('break_motion')
            reach = object.__getattribute__(self,'__dict__').get('reach')
            if (actor is None or defender is None or actor is defender
                    or self.actor_id not in encounter.being_list or self.target_id not in encounter.being_list
                    or not encounter.is_aware(self.actor_id,self.target_id)):
                raise ValueError('Break weapon requires two aware participating Beings')
            if (weapon is None or self.instrument_id not in actor.armed_with(encounter.universe).values()
                    or victim_weapon is None or victim_weapon.id not in defender.armed_with(encounter.universe).values()):
                raise ValueError('Break weapon requires the actual held weapons of both Beings')
            if motion != 'swing' or motion not in weapon.get_melee_types():
                raise ValueError('Break weapon uses a supported swing with the attacking weapon')
            timing = weapon.St()
            if (type(timing) not in (int,float) or timing <= 0
                    or self.end_time-self.start_time != max(1,timing-self.strategy.timing_adjustment())
                    or type(reach) not in (int,float) or reach <= 0):
                raise ValueError('Break weapon timing or reach is invalid')
            from melee_combat import effective_melee_reach_meters
            expected = effective_melee_reach_meters(actor.current,weapon.current)
            if not math.isclose(reach,expected,rel_tol=1e-12,abs_tol=1e-12):
                raise ValueError('Break weapon reach differs from native Being/weapon dimensions')
            from melee_combat import MeleeStrike
            # A legal response may be chosen against an opponent's accepted
            # but not yet started Action. Choices are authoritative scheduler
            # state; checking only pending_action_list incorrectly rejected
            # that interval before its first one-second activation boundary.
            declarations=[encounter.universe.get_event_by_id(aid)
                          for aid in encounter.pending_action_list]
            book=encounter._choice_book
            for choice in book._choices.values():
                if choice.view.state not in ('accepted','executing'):
                    continue
                declarations.extend(member.action for member in choice.members
                                    if type(member.action) is MeleeStrike)
            declarations={row.id:row for row in declarations if type(row) is MeleeStrike}.values()
            attacks=[row for row in declarations if type(row) is MeleeStrike
                and row.actor_id==defender.id and row.target_id==actor.id
                and row.instrument_id==victim_weapon.id
                and math.ceil(row.end_time)==math.ceil(self.end_time)+1]
            if len(attacks)!=1:
                raise ValueError('Break weapon must resolve in the second before the targeted weapon attack')
            return PreparedSchedule.from_action(self)
        if self.event_type == 'disarm':
            from encounter import Encounter
            if type(encounter) is not Encounter or encounter.progression_mode!='transactional':
                raise ValueError('Disarm requires the native transactional Encounter pathway')
            actor,defender=encounter.get_being(self.actor_id),encounter.get_being(self.target_id)
            from weapon import WeaponInstance
            weapon=self.get_instrument()
            target_weapon=encounter.universe.get_object_by_id(object.__getattribute__(self,'__dict__').get('disarm_weapon_id'))
            motion=object.__getattribute__(self,'__dict__').get('disarm_motion')
            reach=object.__getattribute__(self,'__dict__').get('reach')
            if (actor is None or defender is None or actor is defender
                    or self.actor_id not in encounter.being_list or self.target_id not in encounter.being_list
                    or not encounter.is_aware(self.actor_id,self.target_id)):
                raise ValueError('Disarm requires two aware participating Beings')
            if (type(weapon) is not WeaponInstance or weapon.id not in actor.armed_with(encounter.universe).values()
                    or type(target_weapon) is not WeaponInstance
                    or target_weapon.id not in defender.armed_with(encounter.universe).values()):
                raise ValueError('Disarm requires an attacking held weapon and a specifically held target weapon')
            if (actor.current.skills.weapon_skills.get(weapon.original.obj_type,0)<=1
                    or motion not in ('swing','thrust') or motion not in weapon.get_melee_types()):
                raise ValueError('armed Disarm requires advanced weapon skill and a supported attack motion')
            timing=weapon.St() if motion=='swing' else weapon.Tt()
            if (type(timing) not in (int,float) or timing<=0
                    or self.end_time-self.start_time!=max(1,timing-self.strategy.timing_adjustment())
                    or type(reach) not in (int,float) or not math.isfinite(reach) or reach<=0):
                raise ValueError('Disarm timing or reach is invalid')
            from melee_combat import effective_melee_reach_meters
            if not math.isclose(reach,effective_melee_reach_meters(actor.current,weapon.current),rel_tol=1e-12,abs_tol=1e-12):
                raise ValueError('Disarm reach differs from native Being/weapon dimensions')
            return PreparedSchedule.from_action(self)
        if self.event_type in ('grab', 'hold', 'break hold', 'grapple', 'grapple escape',
                               'takedown', 'reverse', 'pin', 'trip'):
            from encounter import Encounter
            from physical_contact import active_contact_state, successful_touch
            if type(encounter) is not Encounter or encounter.progression_mode != 'transactional':
                raise ValueError('physical contact Actions require native transactional Encounter progression')
            actor, target = encounter.get_being(self.actor_id), encounter.get_being(self.target_id)
            if (actor is None or target is None or actor is target
                    or self.actor_id not in encounter.being_list or self.target_id not in encounter.being_list
                    or not encounter.is_aware(self.actor_id, self.target_id)):
                raise ValueError('physical contact requires two aware participating Beings')
            if actor.is_helpless() or target.is_helpless():
                raise ValueError('physical contact requires able participants')
            grips, controls = active_contact_state(encounter)
            data = object.__getattribute__(self, '__dict__')
            if self.event_type == 'grab':
                hand, touch_id = data.get('grab_hand'), data.get('touch_action_id')
                if not successful_touch(encounter, touch_id, actor.id, target.id):
                    raise ValueError('Grab requires a completed successful Touch by this actor against this target')
                if hand not in ('left hand', 'right hand') or actor.current.body_parts.get(hand, 'missing') is not None:
                    raise ValueError('Grab requires one explicitly represented free native hand')
                if any(row[1] == actor.id and row[3] == hand for row in grips):
                    raise ValueError('Grab requires a hand not maintaining another physical Grip')
                if self.instrument_id is not None or self.end_time - self.start_time != 1:
                    raise ValueError('Grab is a separate unarmed one-second Action')
            elif self.event_type == 'hold':
                state_id = data.get('grip_id')
                row = next((r for r in grips if r[0] == state_id and r[1] == actor.id
                            and r[2] == target.id), None)
                if row is None or self.end_time - self.start_time != 1 or self.end_time != row[5]:
                    raise ValueError('Hold maintenance must resolve at its individual six-second due boundary')
            elif self.event_type == 'break hold':
                state_id = data.get('grip_id')
                if not any(r[0] == state_id and r[1] == target.id and r[2] == actor.id
                           for r in grips):
                    raise ValueError('Break hold requires one identifiable physical grip on the actor')
                if self.instrument_id is not None or self.end_time - self.start_time != 1:
                    raise ValueError('Break hold is a one-second unarmed Action')
            elif self.event_type == 'grapple':
                state_id = data.get('grip_id')
                if not any(r[0] == state_id and r[1] == actor.id and r[2] == target.id
                           for r in grips):
                    raise ValueError('Grapple initiation requires an established physical Grab')
                if self.instrument_id is not None or self.end_time - self.start_time != 6:
                    raise ValueError('initial Grapple requires separate six-second preparation')
                grip = next(r for r in grips if r[0] == state_id)
                if grip[5] != self.end_time:
                    raise ValueError('Grapple check must coincide with the prerequisite Grip maintenance boundary')
            elif self.event_type == 'grapple escape':
                state_id = data.get('grapple_id')
                if not any(r[0] == state_id and r[1] == target.id and r[2] == actor.id
                           for r in controls):
                    raise ValueError('Grapple Escape requires an established control held over this Being')
                if self.instrument_id is not None or self.end_time - self.start_time != 6:
                    raise ValueError('Grapple Escape resolves at the next six-second control check')
                control = next(r for r in controls if r[0] == state_id)
                if self.end_time != control[5]:
                    raise ValueError('Grapple Escape must resolve at the established control check boundary')
            elif self.event_type in ('takedown','reverse','pin'):
                control_id = data.get('grapple_id')
                control = next((r for r in controls if r[0] == control_id
                    and r[1] == actor.id and r[2] == target.id), None)
                if control is None or self.end_time != control[5] or self.end_time-self.start_time != 6:
                    raise ValueError('position transition requires the established control’s next six-second check')
                source_position = control[6] if len(control)>6 else 'standing'
                if self.event_type == 'takedown':
                    if source_position != 'standing' or actor.get_posture() != 'standing' or target.get_posture() != 'standing':
                        raise ValueError('Takedown requires standing Grapple control and two standing participants')
                    sizes = (getattr(actor,'size_category',None),getattr(target,'size_category',None))
                    order = ('diminutive','tiny','small','medium','large','huge','gargantuan','colossal')
                    if any(value not in order for value in sizes):
                        raise ValueError('Takedown requires explicit native size categories for both Beings')
                    if order.index(sizes[1])-order.index(sizes[0]) > 1:
                        raise ValueError('target is more than one size category larger')
                    if data.get('grapple_position') not in ('kneeling','prone'):
                        raise ValueError('Takedown must declare kneeling or prone outcome')
                elif self.event_type == 'reverse':
                    if source_position not in ('disadvantaged_takedown_bottom','pin_bottom'):
                        raise ValueError('Reverse requires a disadvantaged takedown or pin-from-below position')
                    sizes=(getattr(actor,'size_category',None),getattr(target,'size_category',None))
                    order=('diminutive','tiny','small','medium','large','huge','gargantuan','colossal')
                    if any(value not in order for value in sizes):
                        raise ValueError('Reverse requires explicit native size categories for both Beings')
                    if order.index(sizes[1])-order.index(sizes[0]) > 1:
                        raise ValueError('Reverse target is more than one size category larger')
                elif source_position != 'advantaged_takedown_top' or data.get('grapple_position') not in ('pin_top','pin_bottom'):
                    raise ValueError('Pin requires advantaged takedown control and a declared top/bottom position')
                if self.instrument_id is not None:
                    raise ValueError('Grapple position transitions are unarmed Actions')
            else:
                touch_id=data.get('trip_source_action_id')
                from physical_contact import successful_touch
                if (not successful_touch(encounter,touch_id,actor.id,target.id)
                        or self.end_time-self.start_time != 2 or self.instrument_id is not None):
                    raise ValueError('Trip requires this actor’s successful Touch and two-second unarmed timing')
                if data.get('trip_defender_ability') not in ('STR','DEX'):
                    raise ValueError('Trip requires the defender’s Strength or Dexterity choice')
                sizes=(getattr(actor,'size_category',None),getattr(target,'size_category',None))
                order=('diminutive','tiny','small','medium','large','huge','gargantuan','colossal')
                if any(value not in order for value in sizes):
                    raise ValueError('Trip requires explicit native size categories for both Beings')
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
