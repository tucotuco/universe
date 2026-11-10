"""Deterministic, explicitly Arena-owned initial equipment policy.

This chooses native Objects and writes native custody/equipment references. It
does not grant skill, combat, armor, shield, or action effects beyond those
already represented by the selected native definitions and Being state.
"""
from __future__ import annotations

import json

from armor import ArmorInstance
from weapon import WeaponInstance


POLICY_ID = "universe-arena-class-xp-equipment/1"
ARMOR_POLICY_TIERS = ("Leather armor", "Studded leather armor", "Ring mail")


class ArenaInitialEquipmentRefusal(ValueError):
    pass


def _best_weapon(native, universe):
    record = json.loads(native.source_record_bytes)
    acquired = record["state"].get("skills") or {}
    ranks = acquired.get("weapon_skills") or {}
    # Dagger is the ordinary one-handed weapon with an adopted native Draw
    # path. Other weapon definitions do not currently encode a hand-count
    # contract, so do not infer one from a skill name or equipment label.
    definition = universe.library.weapon_dictionary.get_object_definition("Dagger")
    if definition is None or definition.is_magical is not False or definition.weight <= 0:
        raise ArenaInitialEquipmentRefusal("no supported ordinary native weapon is available")
    if type(ranks.get("Dagger")) is int and ranks["Dagger"] > 0:
        return "Dagger", f"explicitly acquired native Dagger skill rank {ranks['Dagger']}"
    return "Dagger", "Arena low-weight fallback; no proficiency is inferred"


def _armor_type(native, universe):
    """Prefer an exact typed NPC Generator possession; otherwise use class-level policy."""
    generated = native.generated_items or {}
    instances = generated.get("instances", ())
    for row in instances:
        if row.get("category") == "armor":
            key = row.get("native_type_key")
            definition = universe.library.armor_dictionary.get_object_definition(key)
            if definition is not None and definition.is_magical is False and definition.weight > 0:
                return key, "exact supported NPC Generator typed possession"

    levels = [row["level"] for row in native.being._arena_initial_profile["class_allocations"]]
    highest = max(levels, default=0)
    strength = native.being.current.STR()
    # This is a declared Arena loadout preference, not a strength requirement,
    # class combat feature, encumbrance rule, or claim about garment fit.
    tier = min(2, int(highest >= 2) + int(strength >= 16))
    key = ARMOR_POLICY_TIERS[tier]
    definition = universe.library.armor_dictionary.get_object_definition(key)
    if definition is None or definition.is_magical is not False or definition.weight <= 0:
        raise ArenaInitialEquipmentRefusal(f"Arena armor policy type {key!r} is not supported natively")
    return key, (f"{POLICY_ID}: highest Generator class level {highest} and native Strength "
                 f"{strength} select preference tier {tier}")


def equip_generated_being(native, universe, encounter):
    """Create, register, and equip the participant's selected native kit at time zero."""
    from being import BeingInstance

    being = native.being
    if type(being) is not BeingInstance:
        raise ArenaInitialEquipmentRefusal("starting equipment requires a native BeingInstance")
    if type(being.current.body_parts) is not dict:
        raise ArenaInitialEquipmentRefusal("native hand anatomy is malformed")
    free_hands = [name for name in ("right hand", "left hand")
                  if name in being.current.body_parts and being.current.body_parts[name] is None]
    if not free_hands:
        raise ArenaInitialEquipmentRefusal(
            "generated Being has no explicitly represented free native hand for its starting weapon")

    weapon_key, weapon_basis = _best_weapon(native, universe)
    armor_key, armor_basis = _armor_type(native, universe)
    weapon_definition = universe.library.weapon_dictionary.get_object_definition(weapon_key)
    armor_definition = universe.library.armor_dictionary.get_object_definition(armor_key)
    if not isinstance(weapon_definition, type(universe.library.weapon_dictionary.get_object_definition("Dagger"))):
        raise ArenaInitialEquipmentRefusal("selected native weapon definition has an unsupported subtype")
    if not isinstance(armor_definition, type(universe.library.armor_dictionary.get_object_definition("Leather armor"))):
        raise ArenaInitialEquipmentRefusal("selected native armor definition has an unsupported subtype")

    weapon = WeaponInstance(weapon_definition, weapon_key)
    armor = ArmorInstance(armor_definition, armor_key)
    if weapon.id == armor.id or any(universe.get_object_by_id(obj.id) is not None for obj in (weapon, armor)):
        raise ArenaInitialEquipmentRefusal("starting equipment Object identity collision")
    shield_names = set(universe.library.weapon_dictionary.get_objects_in_category("Shields"))
    shield_instances = [row for row in (native.generated_items or {}).get("instances", ())
                        if row.get("category") == "shield" and row.get("native_type_key") in shield_names]
    shield = None
    if shield_instances and len(free_hands) > 1:
        shield_key = shield_instances[0]["native_type_key"]
        shield_definition = universe.library.weapon_dictionary.get_object_definition(shield_key)
        if shield_definition is not None and shield_definition.is_magical is False and shield_definition.weight > 0:
            shield = WeaponInstance(shield_definition, shield_key)

    objects = [weapon, armor] + ([] if shield is None else [shield])
    if len({obj.id for obj in objects}) != len(objects):
        raise ArenaInitialEquipmentRefusal("starting equipment Object identities are not unique")
    # The world/Encounter is still an unpublished candidate. Direct custody is
    # native container state; no past Draw/Equip Action or receipt is implied.
    for obj in objects:
        obj.parent_container_id = being.id
        universe.add_object(obj)
        encounter.add_object(obj.id)
        being.add_possession(obj.id)
    being.weapons.append(weapon.id)
    being.set_body_part_holds_object(free_hands[0], weapon.id)
    if shield is not None:
        being.weapons.append(shield.id)
        being.set_body_part_holds_object(free_hands[1], shield.id)
    being.set_armor_id(armor.id)
    return {
        "policy": POLICY_ID,
        "being_id": being.id,
        "weapon": {"object_id": weapon.id, "type": weapon_key, "hand": free_hands[0],
                   "basis": weapon_basis, "status": "native held/readied at initial state"},
        "armor": {"object_id": armor.id, "type": armor_key, "basis": armor_basis,
                  "status": "native armor_id reference"},
        "shield": (None if shield is None else {
            "object_id": shield.id, "type": shield.current.obj_type,
            "hand": free_hands[1], "basis": "exact supported NPC Generator typed possession",
            "status": "native held shield reference"}),
    }
