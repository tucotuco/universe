#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "John Wieczorek"
__copyright__ = "Copyright 2024 Rauthiflor LLC"
__version__ = "weapon.py 2024-03-15T22:52-03:00"

# TODO: WeaponDefinitions from file will need widths and heights eventually
# TODO: Deprecate weapon_size in favor of a function based on actual size and size of wielder
# TODO: Make ''' comments on classes and methods

import json
import math
from object import ObjectInstance, ObjectDefinition, ObjectDictionary
from utils import convert_to_numeric


NATIVE_DRAW_LOCATION_TAG = "universe.native_draw_location"
DRAWABLE_WORN_SHEATH = "worn_sheath"
NATIVE_READY_PREPARATION_TAG = "universe.native_ready_preparation"
NATIVE_SHIELD_ATTACHMENT_TAG = "universe.native_shield_attachment"
NATIVE_LOCKED_GAUNTLET_WEAPON_TAG = "universe.native_locked_gauntlet_weapon_attachment"
NATIVE_PENDING_DISARM_LANDING_TAG = "universe.native_pending_disarm_landing"


def native_pending_disarm_landing(weapon):
    """Read the persisted post-roll landing request attached to one Weapon."""
    if type(weapon) is not WeaponInstance:
        raise TypeError("pending Disarm landing requires an exact native WeaponInstance")
    tags=weapon.current.tags
    if type(tags) is not dict:raise ValueError("native Weapon tags are malformed")
    record=tags.get(NATIVE_PENDING_DISARM_LANDING_TAG)
    if record is None:return None
    keys={"actor_id","margin","max_landing_hexes","origin_cell","owner_id","source_action_id"}
    if (type(record) is not dict or set(record)!=keys
            or any(type(record.get(key)) is not str or not record[key]
                   for key in ("actor_id","owner_id","source_action_id"))
            or type(record.get("margin")) is not int or record["margin"]<=0
            or type(record.get("max_landing_hexes")) is not int
            or record["max_landing_hexes"]!=record["margin"]//3
            or type(record.get("origin_cell")) is not tuple or len(record["origin_cell"])!=2
            or any(type(value) is not int for value in record["origin_cell"])):
        raise ValueError("native pending Disarm landing record is malformed")
    return record


def native_locked_gauntlet_weapon_attachment(weapon):
    """Return explicit owner-linked evidence that a held Weapon is attached.

    This is instance-authored state. No attachment is inferred from names,
    body slots, or a second gauntlet merely being carried.
    """
    if type(weapon) is not WeaponInstance:
        raise TypeError("locked-gauntlet attachment evidence requires an exact native WeaponInstance")
    tags=weapon.current.tags
    if type(tags) is not dict:
        raise ValueError("native Weapon tags are malformed")
    record=tags.get(NATIVE_LOCKED_GAUNTLET_WEAPON_TAG)
    if record is None:return None
    if (type(record) is not dict or set(record)!={"owner_id","gauntlet_id"}
            or any(type(record.get(key)) is not str or not record[key]
                   for key in ("owner_id","gauntlet_id"))):
        raise ValueError("native locked-gauntlet Weapon attachment record is malformed")
    return record


def author_locked_gauntlet_weapon_attachment(universe, weapon, owner_id, gauntlet_id):
    """Author an explicit attachment only for a held Weapon and owned Locked gauntlet."""
    from being import BeingInstance
    if type(weapon) is not WeaponInstance:
        raise TypeError("attachment target must be an exact native WeaponInstance")
    owner=universe.get_object_by_id(owner_id) if type(owner_id) is str else None
    gauntlet=universe.get_object_by_id(gauntlet_id) if type(gauntlet_id) is str else None
    if (type(owner) is not BeingInstance or type(gauntlet) is not WeaponInstance
            or gauntlet.original.obj_type!="Locked gauntlet"
            or weapon.id not in owner.weapons
            or sum(value==weapon.id for value in owner.current.body_parts.values())!=1
            or gauntlet.id not in owner.weapons and gauntlet.id not in owner.possessions
            or gauntlet.parent_container_id not in (None,owner.id)
            or weapon.parent_container_id not in (None,owner.id)):
        raise ValueError("attachment requires an owner's actually held Weapon and native owned Locked gauntlet")
    if type(weapon.current.tags) is not dict:
        raise ValueError("native Weapon tags are malformed")
    if native_locked_gauntlet_weapon_attachment(weapon) is not None:
        raise ValueError("Weapon already has locked-gauntlet attachment evidence")
    weapon.current.tags[NATIVE_LOCKED_GAUNTLET_WEAPON_TAG]={
        "owner_id":owner.id,"gauntlet_id":gauntlet.id}


def native_forearm_buckler_attachment(shield):
    """Return explicit owner/arm evidence for a native forearm-worn buckler."""
    if type(shield) is not WeaponInstance:
        raise TypeError("shield attachment evidence requires an exact native WeaponInstance")
    tags = shield.current.tags
    if type(tags) is not dict:
        raise ValueError("native shield tags are malformed")
    record = tags.get(NATIVE_SHIELD_ATTACHMENT_TAG)
    if record is None:
        return None
    if (type(record) is not dict or set(record) != {"kind", "owner_id", "arm"}
            or record.get("kind") != "forearm_buckler"
            or type(record.get("owner_id")) is not str or not record["owner_id"]
            or record.get("arm") not in ("left", "right")
            or "buckler" not in shield.current.obj_type.casefold()):
        raise ValueError("native shield attachment record is malformed")
    return record


def author_forearm_buckler_attachment(shield, owner_id, arm):
    """Author explicit per-instance forearm attachment; the hand remains usable."""
    if type(shield) is not WeaponInstance:
        raise TypeError("buckler attachment requires an exact native WeaponInstance")
    if type(owner_id) is not str or not owner_id or arm not in ("left", "right"):
        raise ValueError("buckler attachment requires native owner and left/right arm evidence")
    if "buckler" not in shield.current.obj_type.casefold():
        raise ValueError("only an explicitly defined buckler can attach to a forearm")
    if type(shield.current.tags) is not dict:
        raise ValueError("native shield tags are malformed")
    if native_forearm_buckler_attachment(shield) is not None:
        raise ValueError("buckler already has native forearm attachment evidence")
    shield.current.tags[NATIVE_SHIELD_ATTACHMENT_TAG] = {
        "kind": "forearm_buckler", "owner_id": owner_id, "arm": arm}


def native_weapon_draw_location(weapon):
    """Read an explicitly authored, owner-linked native weapon source location.

    The location record lives in the Weapon's existing instance-specific
    current definition tags. This adds no Object identity, generic container,
    body rule, or checkpoint field.
    """
    if type(weapon) is not WeaponInstance:
        raise TypeError("draw-location evidence requires an exact native WeaponInstance")
    tags = weapon.current.tags
    if type(tags) is not dict:
        raise ValueError("native weapon tags are malformed")
    record = tags.get(NATIVE_DRAW_LOCATION_TAG)
    if record is None:
        return None
    if (type(record) is not dict or set(record) != {"kind", "owner_id"}
            or record.get("kind") != DRAWABLE_WORN_SHEATH
            or type(record.get("owner_id")) is not str or not record["owner_id"]):
        raise ValueError("native weapon draw-location record is malformed")
    return record


def author_worn_sheath_draw_location(weapon, owner_id):
    """Author explicit per-instance worn-sheath evidence for a known owner."""
    if type(weapon) is not WeaponInstance:
        raise TypeError("draw-location evidence requires an exact native WeaponInstance")
    if type(owner_id) is not str or not owner_id:
        raise ValueError("worn-sheath draw location requires a native Being identity")
    if type(weapon.current.tags) is not dict:
        raise ValueError("native weapon tags are malformed")
    weapon.current.tags[NATIVE_DRAW_LOCATION_TAG] = {
        "kind": DRAWABLE_WORN_SHEATH, "owner_id": owner_id}


def native_ready_preparation(weapon):
    """Return exact Object preparation evidence, if this Weapon has any."""
    if type(weapon) is not WeaponInstance:
        raise TypeError("ready preparation evidence requires an exact WeaponInstance")
    tags = weapon.current.tags
    if type(tags) is not dict:
        raise ValueError("native weapon tags are malformed")
    record = tags.get(NATIVE_READY_PREPARATION_TAG)
    if record is None:
        return None
    if (type(record) is not dict
            or set(record) not in ({"owner_id", "motion", "ready_action_id", "completed_at", "readying_seconds"},
                                   {"owner_id", "motion", "ready_action_id", "completed_at", "readying_seconds", "pole_set"})
            or type(record.get("owner_id")) is not str or not record["owner_id"]
            or record.get("motion") not in ("swing", "thrust")
            or type(record.get("ready_action_id")) is not str or not record["ready_action_id"]
            or type(record.get("completed_at")) is not int or record["completed_at"] < 0
            or type(record.get("readying_seconds")) is not int or record["readying_seconds"] < 1
            or ("pole_set" in record and type(record["pole_set"]) is not bool)):
        raise ValueError("native weapon ready-preparation record is malformed")
    return record


def weapon_readying_time(weapon, motion):
    """Adopted one-third weapon timing for an explicitly selected motion."""
    if type(weapon) is not WeaponInstance or motion not in ("swing", "thrust"):
        raise ValueError("weapon Ready requires a native Weapon and selected swing or thrust")
    if motion not in weapon.get_melee_types():
        raise ValueError(f"weapon does not support {motion}")
    timing = weapon.St() if motion == "swing" else weapon.Tt()
    if type(timing) not in (int, float) or not math.isfinite(timing) or timing <= 0:
        raise ValueError("weapon motion has no supported positive timing")
    seconds = math.floor(timing / 3)
    if seconds < 1:
        raise ValueError("this weapon motion's one-third Ready time is below the native one-second Action minimum")
    return seconds

class WeaponDefinition(ObjectDefinition):
    '''
    A template for characteristics of a Weapon, which is a subtype of Object.
    Native weapon length is stored in inches and weight in pounds. The
    configuration loader converts the source table's feet-valued lengths.
    R - Throw  t - timing
    S - Swing  d - damage
    T - Thrust p - penetration types
    '''
    def __init__(self, obj_type, length, weight, cost, hardness, hit_points, Rt, Rd, Rp, 
                 St, Sd, Sp, Tt, Td, Tp, weapon_size, width=0, height=0, is_magical=False, 
                 tags=None, weapon_categories=None):
        super().__init__(obj_type, length, width, height, weight, cost, hardness, 
                         hit_points, is_magical, tags, weapon_categories)
        self.attacks = {
            'R': {'t': convert_to_numeric(Rt), 'd': convert_to_numeric(Rd), 'p': Rp},
            'S': {'t': convert_to_numeric(St), 'd': convert_to_numeric(Sd), 'p': Sp},
            'T': {'t': convert_to_numeric(Tt), 'd': convert_to_numeric(Td), 'p': Tp}
        }
        self.weapon_size = weapon_size

    def copy(self):
        '''
        Get an independent copy of the WeaponDefinition.
        '''
        new_weapon_definition = WeaponDefinition(
            self.obj_type,
            self.length,
            self.weight,
            self.cost,
            self.hardness,
            self.hit_points,
            self.Rt(), # Throw timing
            self.Rd(), # Throw damage
            self.Rp(), # Throw penetration types
            self.St(), # Swing timing
            self.Sd(), # Swing damage
            self.Sp(), # Swing penetration types
            self.Tt(), # Thrust timing
            self.Td(), # Thrust damage
            self.Tp(), # Thrust penetration types
            self.weapon_size,
            self.width,
            self.height,
            self.is_magical,
            self.tags.copy(),
            self.weapon_categories.copy())
        return new_weapon_definition

    def to_json(self):
        '''
        Get a representation of a WeaponDefinition as JSON.
        '''
        parent_json = super().to_json()
        data = {
            **json.loads(parent_json),
            'attacks': self.attacks,
            'weapon_size': self.weapon_size
        }
        return json.dumps(data)

    def Rt(self):
        return self.attacks.get('R').get('t')

    def Rd(self):
        return self.attacks.get('R').get('d')

    def Rp(self):
        return self.attacks.get('R').get('p')

    def St(self):
        return self.attacks.get('S').get('t')

    def Sd(self):
        return self.attacks.get('S').get('d')

    def Sp(self):
        return self.attacks.get('S').get('p')

    def Tt(self):
        return self.attacks.get('T').get('t')

    def Td(self):
        return self.attacks.get('T').get('d')

    def Tp(self):
        return self.attacks.get('T').get('p')

class WeaponInstance(ObjectInstance):
    ''' 
    An ObjectInstance based on a WeaponDefinition.
    '''
    def __init__(self, weapon_definition, name=None):
        ObjectInstance.__init__(self, weapon_definition, name)
        self.original = weapon_definition
        self.current = weapon_definition.copy()

    def reset(self):
        self.current = self.original.copy()

    def get_weapon_size(self):
        return self.current.weapon_size

    def set_weapon_size(self, new_weapon_size):
        self.current.weapon_size = new_weapon_size

    def Rt(self):
        return self.current.attacks.get('R').get('t')

    def Rd(self):
        return self.current.attacks.get('R').get('d')

    def Rp(self):
        return self.current.attacks.get('R').get('p')

    def St(self):
        return self.current.attacks.get('S').get('t')

    def Sd(self):
        return self.current.attacks.get('S').get('d')

    def Sp(self):
        return self.current.attacks.get('S').get('p')

    def Tt(self):
        return self.current.attacks.get('T').get('t')

    def Td(self):
        return self.current.attacks.get('T').get('d')

    def Tp(self):
        return self.current.attacks.get('T').get('p')

    def get_penetration_types(self, attack_type):
        if attack_type == 'swing':
            return self.Sp()
        if attack_type == 'thrust':
            return self.Tp()
        return self.Rp()

    def get_melee_types(self):
        melee_types = []
        if self.St() is not None:
            melee_types.append("swing")
        if self.Tt() is not None:
            melee_types.append("thrust")
        return melee_types

    def set_attack(self, attack_type, attack_attribute, new_value):
        try:
            self.attacks[attack_type][attack_attribute] = new_value
            if self.attacks[attack_type][attack_attribute] < 1:
                self.attacks[attack_type][attack_attribute] = 1
        except Exception(e):
            return

    def set_attacks(self, new_attacks_dict):
        self.current.attacks = new_attacks_dict

    def modify_attacks(self, mod_attack_dict):
        for attack_type in mod_attack_dict:
            for attack_attribute in mod_attack_dict[attack_type]:
                if attack_attribute != 'p':
                    try:
                        new_value = mod_attack_dict[attack_type][attack_attribute]
                        self.current.attacks[attack_type][attack_attribute] += new_value
                        if self.current.attacks[attack_type][attack_attribute] < 1:
                            self.current.attacks[attack_type][attack_attribute] = 1
                    except Exception as e:
                        print(f'Version: {__version__}: {e}')

# A dictionary of all information about weapons
class WeaponDictionary(ObjectDictionary):
    def __init__(self, dictionary_file=None):
        ObjectDictionary.__init__(self)

        if dictionary_file is not None:
            self.load(dictionary_file)

    def load(self, filename):
        # The weapon reference table defines physical L values in feet. Native
        # WeaponDefinition.length is inches; convert at this input boundary.
        FEET_TO_INCHES = 12.0
        p = True
        with open(filename, 'r') as f:
            lines = f.readlines()
            headers = lines[0].strip().split('\t')
            if p==True:
                p = False
            for line in lines[1:]:
                fields = line.strip().split('\t')
                weapon_dict = {}
                for i in range(len(headers)):
                    weapon_dict[headers[i]] = fields[i]
                if "length" in weapon_dict and weapon_dict["length"] not in (None, ""):
                    weapon_dict["length"] = float(weapon_dict["length"]) * FEET_TO_INCHES
                weapon = WeaponDefinition(**weapon_dict)
                self.objects[weapon.obj_type] = weapon


def re_ready_time_after_strike(weapon, motion):
    """Return revision-61 post-strike re-ready time for a native weapon motion.

    This derives only from the weapon table's unmodified timing. It does not
    compute ordinary draw time or model whether a carried Object is drawable.
    A result of zero is retained as a timing value; it is not a zero-duration
    Action declaration.
    """
    if type(weapon) not in (WeaponDefinition, WeaponInstance):
        raise TypeError('post-strike re-ready timing requires a native Weapon definition or instance')
    motion_keys = {'range': 'R', 'swing': 'S', 'thrust': 'T'}
    if type(motion) is not str or motion not in motion_keys:
        raise ValueError('weapon motion must be range, swing, or thrust')
    timing = weapon.current.attacks[motion_keys[motion]]['t'] if type(weapon) is WeaponInstance \
        else weapon.attacks[motion_keys[motion]]['t']
    if (type(timing) not in (int, float) or not math.isfinite(timing)
            or timing <= 0 or not float(timing).is_integer()):
        raise ValueError('selected weapon motion has no supported positive whole-second timing')
    return int(timing) // 3
