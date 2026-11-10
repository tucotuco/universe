"""Universe snapshots and native import for npcgen's Arena-ready Being API.

Universe owns the preference and native Object mapping. The installed Generator
owns the versioned initial-equipment selection result. Its payload makes no
combat or protection claims; only native Object definitions/state do that.
"""
from __future__ import annotations

import copy
import hashlib
import json

from armor import ArmorInstance
from weapon import WeaponInstance


POLICY_ID = "universe-arena-class-xp-equipment/2"
CATALOG_ID = "universe-native-arena-equipment/1"
ANATOMY_ID = "universe-native-arena-anatomy/1"
ARMOR_POLICY_TIERS = ("Leather armor", "Studded leather armor", "Ring mail")
_EQUIPMENT_FIELDS = {"policy", "being_id", "equipment_seed", "catalog", "anatomy",
                     "policy_snapshot", "specification", "object_ids"}


class ArenaInitialEquipmentRefusal(ValueError):
    pass


def _typed_armor_preference(native, universe):
    """Preserve the established preference as API input, without constructing an item."""
    for row in (native.generated_items or {}).get("instances", ()):
        if row.get("category") == "armor":
            key = row.get("native_type_key")
            definition = universe.library.armor_dictionary.get_object_definition(key)
            if definition is not None and definition.is_magical is False and definition.weight > 0:
                return key

    allocations = native.being._arena_initial_profile["class_allocations"]
    highest = max((row["level"] for row in allocations), default=0)
    strength = native.being.current.STR()
    # This remains the documented Arena preference (not a Generator rule,
    # strength requirement, fit assertion, or claim of armor effects).
    tier = min(2, int(highest >= 2) + int(strength >= 16))
    return ARMOR_POLICY_TIERS[tier]


def _ordinary_definition(definition, expected_type, key):
    if (not isinstance(definition, expected_type) or definition.obj_type != key
            or definition.is_magical is not False or type(definition.weight) is not int
            or definition.weight <= 0):
        raise ArenaInitialEquipmentRefusal(
            f"Arena-ready catalog type {key!r} is not a supported ordinary native definition")
    return definition


def build_arena_ready_inputs(native, universe, api, equipment_seed):
    """Build explicit versioned snapshots from current native dictionaries/state."""
    from armor import ArmorDefinition
    from weapon import WeaponDefinition

    being = native.being
    if type(being.current.body_parts) is not dict:
        raise ArenaInitialEquipmentRefusal("native Being hand anatomy is malformed")
    hands = [name for name in ("right hand", "left hand")
             if name in being.current.body_parts and being.current.body_parts[name] is None]
    if not hands:
        raise ArenaInitialEquipmentRefusal("generated Being has no represented free native hand")
    _ordinary_definition(
        universe.library.weapon_dictionary.get_object_definition("Dagger"),
        WeaponDefinition, "Dagger")
    armor_key = _typed_armor_preference(native, universe)
    _ordinary_definition(
        universe.library.armor_dictionary.get_object_definition(armor_key),
        ArmorDefinition, armor_key)

    catalog = {
        "format": "npcgen-arena-equipment-catalog", "schema_version": 1,
        "catalog_id": CATALOG_ID, "catalog_version": "1",
        "items": [
            {"native_type_key": "Dagger", "category": "weapon", "label": "Dagger",
             "tier": 0, "hands_required": 1, "min_strength": 0,
             "skill_requirements": []},
            {"native_type_key": armor_key, "category": "armor", "label": armor_key,
             "tier": 0, "worn_slot": "armor_id", "min_strength": 0,
             "skill_requirements": []},
        ],
    }
    anatomy = {
        "format": "npcgen-arena-anatomy", "schema_version": 1,
        "anatomy_id": ANATOMY_ID, "anatomy_version": "1",
        "hands": hands,
        # The native Being has a single armor_id reference, not per-body-part
        # armor geometry. This names that existing slot without inventing one.
        "worn_slots": ["armor_id"] if being.current.armor_id is None else [],
        "carry_locations": [],
    }
    if not anatomy["worn_slots"]:
        raise ArenaInitialEquipmentRefusal("native Being has no free represented armor_id slot")

    class_names = api.default_rules().class_names
    kit = {"weapons": [{"native_type_key": "Dagger", "weight": 1}],
           "armor": [{"native_type_key": armor_key, "weight": 1}],
           "shields": [], "shield_chance": [0, 1]}
    policy = {
        "format": "npcgen-arena-equipment-policy", "schema_version": 1,
        "policy_id": POLICY_ID, "policy_version": "1",
        "tiers": [{"min_total_xp": 0, "max_tier": 0}],
        "class_kits": {name: copy.deepcopy(kit) for name in class_names},
        "acquired_skill_weight_multiplier": 1,
        "sidearm": "never", "require_primary_weapon": True,
        "fallback_to_default_kit": False,
    }
    if type(equipment_seed) is not int or equipment_seed < 0:
        raise ArenaInitialEquipmentRefusal("Arena-ready equipment seed must be a nonnegative integer")
    return catalog, anatomy, policy


def prepare_arena_ready_specification(native, universe, api, candidate, equipment_seed):
    """Call the installed API and retain its exact specification and snapshots."""
    try:
        from npcgen.arena_ready import validate_ready_being
    except ImportError as exc:
        raise ArenaInitialEquipmentRefusal("installed npcgen lacks its Arena-ready validator") from exc
    catalog, anatomy, policy = build_arena_ready_inputs(native, universe, api, equipment_seed)
    try:
        specification = api.arena_ready_being(candidate, catalog, anatomy, policy, equipment_seed)
    except Exception as exc:
        raise ArenaInitialEquipmentRefusal(
            f"npcgen arena_ready_being refused: {type(exc).__name__}: {str(exc)[:512]}") from exc
    errors = validate_ready_being(specification, catalog, anatomy)
    if errors:
        raise ArenaInitialEquipmentRefusal("npcgen Arena-ready output failed validation: " + "; ".join(errors[:12]))
    if (type(specification) is not dict
            or specification.get("format") != "npcgen-arena-ready-being"
            or specification.get("schema_version") != 1
            or specification.get("being", {}).get("source_record")
            != json.loads(native.source_record_bytes)):
        raise ArenaInitialEquipmentRefusal(
            "npcgen Arena-ready output does not preserve the complete generated source record")
    return {
        "equipment_seed": equipment_seed, "catalog": catalog, "anatomy": anatomy,
        "policy_snapshot": policy, "specification": specification,
    }


def _equipment_objects(native, universe, ready):
    from armor import ArmorDefinition
    from weapon import WeaponDefinition

    being = native.being
    spec = ready["specification"]
    units = spec["equipment"]["units"]
    if not units:
        raise ArenaInitialEquipmentRefusal("npcgen Arena-ready output has no required initial equipment")
    if (spec["being"]["arena"].get("starting_experience")
            != being._arena_initial_profile["initial_total_experience"]):
        raise ArenaInitialEquipmentRefusal("Arena-ready specification XP differs from the accepted Being")
    catalog = {row["native_type_key"]: row for row in ready["catalog"]["items"]}
    objects, object_ids = [], {}
    for unit in units:
        key, category = unit["native_type_key"], unit["category"]
        entry = catalog.get(key)
        if (entry is None or entry["category"] != category or unit["quantity"] != 1
                or unit["mechanics"] is not None or unit["ordinary"] is not True
                or unit["magical"] is not False or unit["owner"] != {
                    "being_id": spec["being"]["being_id"]}
                or unit["possession"] != "owned"):
            raise ArenaInitialEquipmentRefusal("Arena-ready unit has unsupported ownership or item semantics")
        if category == "weapon":
            definition = _ordinary_definition(
                universe.library.weapon_dictionary.get_object_definition(key), WeaponDefinition, key)
            obj = WeaponInstance(definition, key)
        elif category == "shield":
            definition = _ordinary_definition(
                universe.library.weapon_dictionary.get_object_definition(key), WeaponDefinition, key)
            if key not in universe.library.weapon_dictionary.get_objects_in_category("Shields"):
                raise ArenaInitialEquipmentRefusal(f"Arena-ready shield {key!r} is not a native shield")
            obj = WeaponInstance(definition, key)
        elif category == "armor":
            definition = _ordinary_definition(
                universe.library.armor_dictionary.get_object_definition(key), ArmorDefinition, key)
            obj = ArmorInstance(definition, key)
        else:
            raise ArenaInitialEquipmentRefusal(f"npcgen returned unsupported equipment category {category!r}")
        placement = unit["placement"]
        if placement["kind"] == "held":
            hands = placement["hands"]
            if (unit["readied"] is not True or type(hands) is not list or not hands
                    or any(hand not in being.current.body_parts
                           or being.current.body_parts[hand] is not None for hand in hands)):
                raise ArenaInitialEquipmentRefusal("Arena-ready held item does not map to free represented native hands")
            if len(hands) != entry.get("hands_required"):
                raise ArenaInitialEquipmentRefusal("Arena-ready hand count differs from the caller catalog")
        elif placement["kind"] == "worn":
            if (category != "armor" or unit["readied"] is not False
                    or placement.get("slot") != "armor_id" or being.current.armor_id is not None):
                raise ArenaInitialEquipmentRefusal("Arena-ready worn armor does not map to the native armor_id slot")
        else:
            # No native carry-location record is currently adopted. Do not
            # reinterpret a carried NPC Generator item as held, sheathed, etc.
            raise ArenaInitialEquipmentRefusal(
                f"npcgen placement {placement['kind']!r} has no supported native Arena mapping")
        objects.append((unit, obj))
        object_ids[unit["equipment_id"]] = obj.id
    ids = [obj.id for _, obj in objects]
    if len(ids) != len(set(ids)) or any(universe.get_object_by_id(obj_id) is not None for obj_id in ids):
        raise ArenaInitialEquipmentRefusal("native equipment Object identities collided")
    return objects, object_ids


def equip_generated_being(native, universe, encounter):
    """Materialize only the validated Generator units into native time-zero state."""
    from being import BeingInstance

    being = native.being
    if type(being) is not BeingInstance:
        raise ArenaInitialEquipmentRefusal("starting equipment requires a native BeingInstance")
    ready = native.arena_ready_equipment
    if type(ready) is not dict or set(ready) != {
            "equipment_seed", "catalog", "anatomy", "policy_snapshot", "specification"}:
        raise ArenaInitialEquipmentRefusal("generated Being has no valid npcgen Arena-ready specification")
    objects, object_ids = _equipment_objects(native, universe, ready)
    # The candidate is still unpublished. Only after validating every unit and
    # identity do we apply direct initial-state custody and slot references.
    for unit, obj in objects:
        obj.parent_container_id = being.id
        universe.add_object(obj)
        encounter.add_object(obj.id)
        being.add_possession(obj.id)
        placement = unit["placement"]
        if placement["kind"] == "held":
            being.weapons.append(obj.id)
            for hand in placement["hands"]:
                being.set_body_part_holds_object(hand, obj.id)
        elif placement["kind"] == "worn":
            being.set_armor_id(obj.id)
    return {
        "policy": POLICY_ID, "being_id": being.id,
        "equipment_seed": ready["equipment_seed"],
        "catalog": copy.deepcopy(ready["catalog"]),
        "anatomy": copy.deepcopy(ready["anatomy"]),
        "policy_snapshot": copy.deepcopy(ready["policy_snapshot"]),
        "specification": copy.deepcopy(ready["specification"]),
        "object_ids": object_ids,
    }


def validate_saved_equipment_row(row, being, source_record_bytes, universe):
    """Validate persisted Generator commitment against source and current native state."""
    if type(row) is not dict or set(row) != _EQUIPMENT_FIELDS:
        raise ValueError("initial Arena-ready equipment record has an unsupported field set")
    if row["policy"] != POLICY_ID or row["being_id"] != being.id:
        raise ValueError("initial Arena-ready equipment identity/policy mismatch")
    if type(row["equipment_seed"]) is not int or row["equipment_seed"] < 0:
        raise ValueError("initial Arena-ready equipment seed is malformed")
    try:
        from npcgen.arena_ready import validate_ready_being
        from npcgen_arena_adapter import validate_npcgen_source_record
        validate_npcgen_source_record(source_record_bytes)
        errors = validate_ready_being(row["specification"], row["catalog"], row["anatomy"])
    except Exception as exc:
        raise ValueError(f"saved npcgen Arena-ready specification is incompatible: {exc}") from exc
    if errors:
        raise ValueError("saved npcgen Arena-ready specification is invalid: " + "; ".join(errors[:12]))
    record = json.loads(source_record_bytes)
    spec = row["specification"]
    if (spec["being"]["source_record"] != record
            or spec["being"]["arena"]["starting_experience"] != record["generation"]["starting_experience"]
            or spec["equipment"]["equipment_seed"] != row["equipment_seed"]):
        raise ValueError("saved Arena-ready source/profile disagrees with its authoritative Generator record")
    def digest(value):
        canonical = json.dumps(value, sort_keys=True, separators=(",", ":"),
                               ensure_ascii=False).encode("utf-8")
        return "sha256:" + hashlib.sha256(canonical).hexdigest()
    equipment = spec["equipment"]
    if (row["policy_snapshot"].get("policy_id") != row["policy"]
            or equipment["policy"] != {
                "policy_id": row["policy_snapshot"]["policy_id"],
                "policy_version": row["policy_snapshot"]["policy_version"],
                "sha256": digest(row["policy_snapshot"])}
            or equipment["catalog"] != {
                "catalog_id": row["catalog"]["catalog_id"],
                "catalog_version": row["catalog"]["catalog_version"],
                "sha256": digest(row["catalog"])}
            or {key: equipment["anatomy"].get(key)
                for key in ("format", "schema_version", "anatomy_id",
                            "anatomy_version", "hands", "worn_slots", "carry_locations")}
                != row["anatomy"]
            or equipment["anatomy"].get("sha256") != digest(row["anatomy"])):
        raise ValueError("saved Arena-ready API input snapshots do not match their recorded digests")
    units = spec["equipment"]["units"]
    mappings = row["object_ids"]
    if (type(mappings) is not dict or set(mappings) != {unit["equipment_id"] for unit in units}
            or len(set(mappings.values())) != len(mappings)):
        raise ValueError("saved Arena-ready native Object identity map is incomplete or duplicated")
    for unit in units:
        obj = universe.get_object_by_id(mappings[unit["equipment_id"]])
        if (obj is None or obj.parent_container_id != being.id or obj.get_position() is not None
                or obj.id not in being.possessions or obj.current.obj_type != unit["native_type_key"]):
            raise ValueError("saved Arena-ready unit disagrees with native Object identity/custody")
        from armor import ArmorInstance
        from weapon import WeaponInstance
        expected_type = ArmorInstance if unit["category"] == "armor" else WeaponInstance
        if type(obj) is not expected_type:
            raise ValueError("saved Arena-ready category disagrees with the native Object type")
        placement = unit["placement"]
        if placement["kind"] == "held":
            if (obj.id not in being.weapons or unit["readied"] is not True
                    or any(being.current.body_parts.get(hand) != obj.id for hand in placement["hands"])):
                raise ValueError("saved Arena-ready held unit disagrees with native hand state")
        elif placement["kind"] == "worn":
            if being.current.armor_id != obj.id or unit["readied"] is not False:
                raise ValueError("saved Arena-ready armor disagrees with native armor state")
        else:
            raise ValueError("saved Arena-ready carried placement has no native mapping")
    return True
