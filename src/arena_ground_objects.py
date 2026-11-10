"""Fail-closed native ground Object realization for generated Arena candidates.

The adapter accepts only typed, ordinary equipment descriptions. It does not
infer equipment from historical possession prose or assign ownership, geometry,
collision, visibility, or pickup behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import random

from armor import ArmorDefinition, ArmorInstance
from arena_hex_map import ArenaHexLayout, HexAddress
from object import ObjectInstance
from spatial.state import CartesianPosition
from weapon import WeaponDefinition, WeaponInstance


MAX_GROUND_OBJECTS = 3000
MAX_GROUND_EXPANSION_CELLS = 3000
MAX_GROUND_LAYOUT_AREA = 1_000_000
_CATEGORIES = frozenset(("weapon", "armor", "shield"))


class ArenaGroundObjectRefusal(ValueError):
    """Structured refusal before the candidate is returned or published."""

    def __init__(self, code: str, message: str, *, details=None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(f"{code}: {message}")


@dataclass(frozen=True)
class ArenaGroundObject:
    source_item_id: str
    native_object_id: str
    category: str
    native_type_key: str
    origin: str
    column: int
    row: int
    position: CartesianPosition


@dataclass(frozen=True)
class ArenaGroundObjectSet:
    placements: tuple[ArenaGroundObject, ...]
    layout: ArenaHexLayout
    source_to_native_object_id: tuple[tuple[str, str], ...]


def _refuse(code, message, **details):
    raise ArenaGroundObjectRefusal(code, message, details=details)


def _validated_specs(universe, item_descriptions):
    if type(item_descriptions) not in (list, tuple):
        _refuse("invalid_ground_items", "ground item descriptions must be a finite list")
    if len(item_descriptions) > MAX_GROUND_OBJECTS:
        _refuse("ground_item_limit", "ground item count exceeds the bounded Arena limit",
                maximum=MAX_GROUND_OBJECTS)
    library = universe.library
    if (library is None or library.weapon_dictionary is None
            or library.armor_dictionary is None):
        _refuse("native_item_dictionary_unavailable",
                "native weapon, shield, and armor dictionaries are required")

    shield_types = library.weapon_dictionary.get_objects_in_category("Shields")
    if type(shield_types) not in (list, tuple, set):
        _refuse("native_shield_category_unavailable",
                "native weapon dictionary has no verified Shields category")
    shield_types = set(shield_types)

    seen_source_ids = set()
    validated = []
    for index, item in enumerate(item_descriptions):
        required = {"source_item_id", "category", "native_type_key", "quantity",
                    "ordinary", "magical", "mechanics", "origin"}
        if type(item) is not dict or set(item) != required:
            _refuse("invalid_ground_item", "typed ground item has missing or unknown fields", index=index)
        source_id = item["source_item_id"]
        if type(source_id) is not str or not source_id.strip() or source_id in seen_source_ids:
            _refuse("duplicate_or_missing_source_id",
                    "every source-local item ID must be unique nonempty text", index=index)
        if type(item["category"]) is not str or item["category"] not in _CATEGORIES:
            _refuse("unsupported_ground_category", "ground item category must be weapon, armor, or shield",
                    index=index, category=item["category"])
        if (type(item["native_type_key"]) is not str or not item["native_type_key"]
                or type(item["quantity"]) is not int or item["quantity"] != 1
                or item["ordinary"] is not True or item["magical"] is not False
                or item["mechanics"] is not None or type(item["origin"]) is not str
                or not item["origin"]):
            _refuse("invalid_ground_item_semantics",
                    "each item must be one ordinary nonmagical physical unit with provenance", index=index)

        category, key = item["category"], item["native_type_key"]
        if category == "armor":
            definition = library.armor_dictionary.get_object_definition(key)
            if not isinstance(definition, ArmorDefinition):
                _refuse("unknown_native_armor", "exact armor key is absent from the native dictionary",
                        index=index, native_type_key=key)
        else:
            definition = library.weapon_dictionary.get_object_definition(key)
            if not isinstance(definition, WeaponDefinition):
                _refuse("unknown_native_weapon", "exact weapon key is absent from the native dictionary",
                        index=index, native_type_key=key)
            if category == "shield" and key not in shield_types:
                _refuse("native_shield_category_mismatch",
                        "shield items must be native weapons in the Shields category",
                        index=index, native_type_key=key)
            if category == "weapon" and key in shield_types:
                _refuse("native_weapon_category_mismatch",
                        "native Shields-category Objects must be typed as shields",
                        index=index, native_type_key=key)
        weight = definition.weight
        if (type(weight) not in (int, float) or not math.isfinite(weight) or weight <= 0):
            _refuse("invalid_native_item_weight",
                    "native combat Objects require a finite positive physical weight",
                    index=index, native_type_key=key)
        if definition.is_magical is not False:
            _refuse("magical_native_item_refused",
                    "the ground adapter accepts only verified nonmagical native definitions",
                    index=index, native_type_key=key)
        seen_source_ids.add(source_id)
        validated.append((source_id, category, key, item["origin"], definition))
    return tuple(validated)


def _ground_positions(layout, occupied_addresses, item_count, seed):
    if type(seed) is not int or seed < 0:
        _refuse("invalid_ground_placement_seed", "ground placement seed must be a nonnegative integer")
    if type(item_count) is not int or item_count < 0 or item_count > MAX_GROUND_OBJECTS:
        _refuse("ground_item_limit", "ground item count exceeds the bounded Arena limit",
                maximum=MAX_GROUND_OBJECTS)
    occupied = set(occupied_addresses)
    if any(type(address) is not HexAddress or not layout.contains(address) for address in occupied):
        _refuse("invalid_being_placement", "every Being must occupy a distinct in-footprint hex")
    if len(occupied) != len(occupied_addresses):
        _refuse("overlapping_being_placement", "initial Being placements must use distinct hexes")
    vacant = [address for address in layout.addresses() if address not in occupied]
    rng = random.Random(seed)
    if item_count <= len(vacant):
        return layout, tuple(rng.sample(vacant, item_count))

    if item_count - len(vacant) > MAX_GROUND_EXPANSION_CELLS:
        _refuse("ground_expansion_limit", "required edge expansion exceeds the bounded Arena limit",
                maximum=MAX_GROUND_EXPANSION_CELLS)
    chosen_initial = rng.sample(vacant, len(vacant))
    all_addresses = set(layout.addresses())
    expanded = []
    while len(expanded) < item_count - len(vacant):
        frontier = set()
        for address in all_addresses:
            for neighbor in layout.neighbors(address):
                if neighbor.column >= 0 and neighbor.row >= 0 and neighbor not in all_addresses:
                    frontier.add(neighbor)
        candidates = sorted(frontier)
        candidates = [address for address in candidates
                      if (max(layout.width_columns, address.column + 1)
                          * max(layout.height_rows, address.row + 1)) <= MAX_GROUND_LAYOUT_AREA]
        if not candidates:
            _refuse("ground_expansion_limit", "no bounded nonnegative edge-sharing cell remains")
        address = candidates[rng.randrange(len(candidates))]
        all_addresses.add(address)
        expanded.append(address)
    width = max(layout.width_columns, max(address.column for address in all_addresses) + 1)
    height = max(layout.height_rows, max(address.row for address in all_addresses) + 1)
    if width * height > MAX_GROUND_LAYOUT_AREA:
        _refuse("ground_expansion_limit", "expanded ground footprint exceeds the bounded area")
    expanded_layout = ArenaHexLayout.irregular(width, height, all_addresses)
    rng.shuffle(expanded)
    return expanded_layout, tuple(chosen_initial + expanded)


def realize_arena_ground_objects(universe, item_descriptions, initial_layout,
                                 being_addresses, placement_seed) -> ArenaGroundObjectSet:
    """Preflight, independently instantiate, and register typed ground Objects.

    Initial vacant hexes are randomly selected without replacement. If those
    cells are exhausted, additional cells are selected from a seeded frontier;
    every such cell shares an edge with the existing finite footprint. This is
    a display-reference placement only and makes no geometry or clearance claim.
    """
    specs = _validated_specs(universe, item_descriptions)
    layout, addresses = _ground_positions(initial_layout, being_addresses, len(specs), placement_seed)
    if len(addresses) != len(specs) or len(set(addresses)) != len(specs):
        _refuse("ground_placement_collision", "ground Objects must receive distinct cell addresses")

    instances = []
    provisional_ids = set()
    for (source_id, category, key, origin, definition), address in zip(specs, addresses):
        display_name = key
        try:
            instance = (ArmorInstance(definition, display_name) if category == "armor"
                        else WeaponInstance(definition, display_name))
        except Exception as exc:
            _refuse("native_item_construction_failed",
                    "native constructor refused a prevalidated ground item",
                    source_item_id=source_id, error=type(exc).__name__)
        if (not isinstance(instance, ObjectInstance) or universe.get_object_by_id(instance.id) is not None
                or instance.id in provisional_ids):
            _refuse("native_object_identity_collision", "native Object instance identity is not unique",
                    source_item_id=source_id)
        provisional_ids.add(instance.id)
        position = layout.center_position(address)
        instance.set_position(position)
        position = instance.get_position()
        if (instance.parent_container_id is not None or instance.get_position() != position
                or instance.geometry is not None):
            _refuse("invalid_native_ground_state", "constructed Object is not in supported uncontained ground state",
                    source_item_id=source_id)
        instances.append((source_id, category, key, origin, address, position, instance))

    # The Universe is still the private unpublished candidate. Register only
    # after every description, placement, and native instance has passed checks.
    for *_prefix, instance in instances:
        universe.add_object(instance)
    placements = []
    bindings = []
    for source_id, category, key, origin, address, position, instance in instances:
        if universe.get_object_by_id(instance.id) is not instance:
            _refuse("native_registration_failed", "fresh Universe did not retain a ground Object",
                    source_item_id=source_id)
        placements.append(ArenaGroundObject(source_id, instance.id, category, key, origin,
                                             address.column, address.row, position))
        bindings.append((source_id, instance.id))
    return ArenaGroundObjectSet(tuple(placements), layout, tuple(bindings))
