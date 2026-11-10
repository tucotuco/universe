"""Closed browser profiles for native Arena ground loadouts.

NPC Generator profiles remain accepted unchanged. A small Arena-owned versioned
format adds scenario-wide exact inventories and seeded sampling per actual
native weapon group, which the Generator's per-category weighted sampler does
not express.
"""
from __future__ import annotations

import copy
import hashlib
import json
import random
from pathlib import Path


PROFILE_DIR = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "arena"
ARENA_FORMAT = "universe-arena-ground-loadout-profile"
ARENA_SCHEMA = 1
MAX_UPLOAD_BYTES = 1_000_000
MAX_ITEMS = 3000
_ARENA_FIELDS = {"format", "schema_version", "profile_id", "title", "mode", "items"}
_ITEM_FIELDS = {"category", "native_type_key"}


class ArenaLoadoutProfileError(ValueError):
    pass


def bundled_profiles():
    profiles = {}
    names = ("empty.json", "starter.json", "all-swords.json",
             "one-random-per-weapon-group.json")
    for filename in names:
        path = PROFILE_DIR / filename
        try:
            profile = json.loads(path.read_text(encoding="utf-8"))
            validated = validate_profile(profile)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            raise ArenaLoadoutProfileError(f"bundled profile {path.name} is invalid: {exc}") from exc
        profile_id = validated["profile_id"]
        if profile_id in profiles:
            raise ArenaLoadoutProfileError("bundled profile IDs must be unique")
        profiles[profile_id] = validated
    return profiles


def _catalog(library):
    weapons = library.weapon_dictionary
    shields = set(weapons.get_objects_in_category("Shields"))
    native = {}
    for key, definition in weapons.objects.items():
        if (definition.is_magical is False and type(definition.weight) in (int, float)
                and definition.weight > 0):
            native[key] = "shield" if key in shields else "weapon"
    for key, definition in library.armor_dictionary.objects.items():
        if (definition.is_magical is False and type(definition.weight) in (int, float)
                and definition.weight > 0):
            native[key] = "armor"
    return native


def validate_profile(profile, library=None):
    """Return a detached supported profile; no paths or executable content are accepted."""
    if type(profile) is not dict:
        raise ArenaLoadoutProfileError("profile must be a JSON object")
    result = copy.deepcopy(profile)
    if result.get("format") == ARENA_FORMAT:
        expected_fields = _ARENA_FIELDS | ({"seed"} if result.get("mode") == "one_per_weapon_group" else set())
        if set(result) != expected_fields or type(result.get("schema_version")) is not int \
                or result["schema_version"] != ARENA_SCHEMA:
            raise ArenaLoadoutProfileError("Arena profile has an unsupported version or field set")
        if (type(result.get("profile_id")) is not str or not result["profile_id"]
                or type(result.get("title")) is not str or not result["title"].strip()
                or result.get("mode") not in ("empty", "explicit_items", "one_per_weapon_group")):
            raise ArenaLoadoutProfileError("Arena profile identity or mode is invalid")
        if type(result.get("items")) is not list or len(result["items"]) > MAX_ITEMS:
            raise ArenaLoadoutProfileError(f"Arena profile items must be a list of at most {MAX_ITEMS}")
        if result["mode"] == "one_per_weapon_group":
            if type(result.get("seed")) is not int or result["seed"] < 0 or result["items"]:
                raise ArenaLoadoutProfileError("seeded group profile needs a nonnegative seed and no explicit items")
        elif "seed" in result:
            raise ArenaLoadoutProfileError("only seeded group profiles may contain a seed")
        if result["mode"] == "empty" and result["items"]:
            raise ArenaLoadoutProfileError("empty profile cannot contain items")
        if result["mode"] == "explicit_items" and not result["items"]:
            raise ArenaLoadoutProfileError("explicit_items profile requires at least one item")
        for index, item in enumerate(result["items"]):
            if (type(item) is not dict or set(item) != _ITEM_FIELDS
                    or item.get("category") not in ("weapon", "armor", "shield")
                    or type(item.get("native_type_key")) is not str or not item["native_type_key"]):
                raise ArenaLoadoutProfileError(f"items[{index}] has invalid typed item fields")
    else:
        result = _validate_generator_profile(result)
    if library is not None:
        supported = _catalog(library)
        if result.get("format") == ARENA_FORMAT:
            items = result["items"]
            if result["mode"] == "one_per_weapon_group":
                groups = library.weapon_dictionary.object_categories
                if not groups or type(groups) is not dict:
                    raise ArenaLoadoutProfileError("native weapon group catalog is unavailable")
                for group, keys in groups.items():
                    eligible = [key for key in sorted(set(keys)) if supported.get(key) in ("weapon", "shield")]
                    if not eligible:
                        raise ArenaLoadoutProfileError(f"native weapon group {group!r} has no supported ground item")
            for index, item in enumerate(items):
                key = item["native_type_key"]
                if supported.get(key) != item["category"]:
                    raise ArenaLoadoutProfileError(
                        f"items[{index}] type {key!r} is not a supported native {item['category']}")
        else:
            for category in ("weapon", "armor", "shield"):
                for item in result["categories"][category]["items"]:
                    key = item["native_type_key"]
                    if supported.get(key) != category:
                        raise ArenaLoadoutProfileError(
                            f"catalog type {key!r} is not a supported native {category}")
    return result


def _validate_generator_profile(profile):
    """Local strict mirror of the installed npcgen loadout profile envelope.

    This lets the Arena restore a save in a process that only needs native
    continuation; actual generation still calls npcgen's own validator.
    """
    required = {"format", "schema_version", "profile_id", "profile_version", "catalog_id",
                "catalog_version", "catalog", "categories"}
    if set(profile) != required or profile.get("format") != "npcgen-arena-loadout-profile" \
            or type(profile.get("schema_version")) is not int or profile["schema_version"] != 1:
        raise ArenaLoadoutProfileError("NPC Generator profile has an unsupported version or field set")
    for key in ("profile_id", "profile_version", "catalog_id", "catalog_version"):
        if type(profile.get(key)) is not str or not profile[key]:
            raise ArenaLoadoutProfileError(f"{key} must be nonempty text")
    if type(profile["catalog"]) is not list or not profile["catalog"]:
        raise ArenaLoadoutProfileError("catalog must be a nonempty list")
    catalog = {}
    for row in profile["catalog"]:
        if (type(row) is not dict or set(row) - {"native_type_key", "category", "label"}
                or type(row.get("native_type_key")) is not str or not row["native_type_key"]
                or row.get("category") not in ("weapon", "armor", "shield")
                or "label" in row and (type(row["label"]) is not str or not row["label"])):
            raise ArenaLoadoutProfileError("catalog entries must have a native key/category and optional label")
        key = row["native_type_key"]
        if key in catalog:
            raise ArenaLoadoutProfileError(f"duplicate catalog key {key!r}")
        catalog[key] = row["category"]
    categories = profile["categories"]
    if type(categories) is not dict or set(categories) != {"weapon", "armor", "shield"}:
        raise ArenaLoadoutProfileError("categories must contain weapon, armor, and shield")
    for category, section in categories.items():
        if type(section) is not dict or set(section) != {"count", "items"} or type(section["items"]) is not list:
            raise ArenaLoadoutProfileError(f"categories.{category} has invalid fields")
        raw_count = section["count"]
        if type(raw_count) is int:
            counts = [raw_count]
        elif (type(raw_count) is dict and set(raw_count) == {"choices"}
              and type(raw_count["choices"]) is list and raw_count["choices"]):
            counts = []
            seen = set()
            for choice in raw_count["choices"]:
                if (type(choice) is not dict or set(choice) != {"count", "weight"}
                        or type(choice["count"]) is not int or not 0 <= choice["count"] <= 1000
                        or type(choice["weight"]) is not int or choice["weight"] < 1
                        or choice["count"] in seen):
                    raise ArenaLoadoutProfileError(f"categories.{category}.count.choices is invalid")
                counts.append(choice["count"]); seen.add(choice["count"])
        else:
            raise ArenaLoadoutProfileError(f"categories.{category}.count is invalid")
        if any(type(count) is not int or not 0 <= count <= 1000 for count in counts):
            raise ArenaLoadoutProfileError(f"categories.{category}.count must be 0..1000")
        seen_items = set()
        for item in section["items"]:
            if (type(item) is not dict or set(item) != {"native_type_key", "weight"}
                    or item.get("native_type_key") not in catalog
                    or catalog.get(item.get("native_type_key")) != category
                    or type(item.get("weight")) is not int or item["weight"] < 1
                    or item["native_type_key"] in seen_items):
                raise ArenaLoadoutProfileError(f"categories.{category}.items contains an invalid entry")
            seen_items.add(item["native_type_key"])
        if any(count > 0 for count in counts) and not section["items"]:
            raise ArenaLoadoutProfileError(f"categories.{category} needs eligible items")
    return profile


def preview(profile, library):
    profile = validate_profile(profile, library)
    if profile.get("format") == ARENA_FORMAT:
        if profile["mode"] == "empty":
            types, count = [], 0
        elif profile["mode"] == "explicit_items":
            types = [row["native_type_key"] for row in profile["items"]]
            count = len(types)
        else:
            groups = library.weapon_dictionary.object_categories
            types = []
            for _group, keys in groups.items():
                types.append(_sample_group(profile["seed"], _group, keys, _catalog(library)))
            count = len(types)
        return {"profile_id": profile["profile_id"], "title": profile["title"],
                "count_per_encounter": count, "type_counts": _counts(types),
                "groups": (list(library.weapon_dictionary.object_categories)
                           if profile["mode"] == "one_per_weapon_group" else [])}
    counts = {}
    type_counts = {}
    for category in ("weapon", "armor", "shield"):
        section = profile["categories"][category]
        raw_count = section["count"]
        possible = ([raw_count] if type(raw_count) is int else
                    [row["count"] for row in raw_count["choices"]])
        counts[category] = [min(possible), max(possible)]
        type_counts[category] = [item["native_type_key"] for item in section["items"]]
    maximum = sum(bounds[1] for bounds in counts.values()) * 2
    return {"profile_id": profile["profile_id"], "title": profile["profile_id"],
            "count_per_encounter": maximum, "type_counts": type_counts,
            "per_being_count_bounds": counts}


def _counts(types):
    result = {}
    for key in types:
        result[key] = result.get(key, 0) + 1
    return result


def _sample_group(seed, group, keys, supported):
    eligible = sorted({key for key in keys if supported.get(key) in ("weapon", "shield")})
    if not eligible:
        raise ArenaLoadoutProfileError(f"weapon group {group!r} has no supported native item")
    material = f"universe-arena-weapon-group/1\0{seed}\0{group}".encode()
    stream = int.from_bytes(hashlib.sha256(material).digest(), "big")
    return eligible[random.Random(stream).randrange(len(eligible))]


def realize(profile, library, *, root_seed, api=None):
    """Return native typed descriptions plus reproducible scenario provenance."""
    profile = validate_profile(profile, library)
    if profile.get("format") != ARENA_FORMAT:
        api = api or __import__("npcgen", fromlist=["api"]).api
        descriptions = []
        sources = []
        for role_index, role in enumerate(("player_controlled", "arena_controlled")):
            seed = int.from_bytes(hashlib.sha256(
                f"arena-loadout-v1:{root_seed}:{role_index}".encode()).digest(), "big")
            # candidate is passed by caller; returned here as a marker.
            sources.append({"kind": "npcgen_profile", "role": role, "sampling_seed": seed})
        return None, tuple(sources)
    supported = _catalog(library)
    if profile["mode"] == "empty":
        selected = []
    elif profile["mode"] == "explicit_items":
        selected = list(profile["items"])
    else:
        selected = []
        for group, keys in library.weapon_dictionary.object_categories.items():
            key = _sample_group(profile["seed"], group, keys, supported)
            selected.append({"category": supported[key], "native_type_key": key,
                             "weapon_group": group})
    descriptions = [{"source_item_id": f"profile:{profile['profile_id']}:{index}",
        "category": item["category"], "native_type_key": item["native_type_key"],
        "quantity": 1, "ordinary": True, "magical": False, "mechanics": None,
        "origin": f"arena-profile:{profile['profile_id']}"} for index, item in enumerate(selected)]
    provenance = ({"kind": "arena_profile", "profile_id": profile["profile_id"],
        "profile_sha256": hashlib.sha256(json.dumps(profile, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False).encode()).hexdigest(), "mode": profile["mode"],
        "seed": profile.get("seed"), "selected_items": copy.deepcopy(selected)},)
    return descriptions, provenance


def parse_upload(raw, library):
    if type(raw) is not bytes or not raw or len(raw) > MAX_UPLOAD_BYTES:
        raise ArenaLoadoutProfileError(f"profile upload must be 1..{MAX_UPLOAD_BYTES} bytes")
    try:
        profile = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_pairs,
                             parse_constant=lambda value: (_ for _ in ()).throw(
                                 ArenaLoadoutProfileError(f"non-finite JSON value {value}")))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ArenaLoadoutProfileError(f"uploaded profile is not valid UTF-8 JSON: {exc}") from None
    return validate_profile(profile, library)


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ArenaLoadoutProfileError(f"duplicate JSON field {key!r}")
        result[key] = value
    return result
