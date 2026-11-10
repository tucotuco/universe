"""Strict local-only authored facts for the ordinary Dagger Draw demonstration."""

from __future__ import annotations

import copy


SCENARIO_FORMAT = "universe-arena-authored-draw-scenario"
SCENARIO_ID = "ordinary-dagger-draw"


class ArenaDrawScenarioRefusal(ValueError):
    """Invalid or inapplicable authored Draw scenario; candidate stays private."""


def validate_scenario(value):
    """Accept only the single bounded, reviewed local scenario schema."""
    if (type(value) is not dict
            or set(value) != {"format", "schema_version", "scenario_id",
                              "player_hand_slots", "carried_weapon"}
            or value.get("format") != SCENARIO_FORMAT
            or type(value.get("schema_version")) is not int
            or value["schema_version"] != 1
            or value.get("scenario_id") != SCENARIO_ID):
        raise ArenaDrawScenarioRefusal("unsupported authored Draw scenario schema")
    if value["player_hand_slots"] != {"right hand": None}:
        raise ArenaDrawScenarioRefusal("authored Draw scenario requires exactly one free right hand")
    weapon = value["carried_weapon"]
    if (type(weapon) is not dict
            or set(weapon) != {"native_type_key", "display_name", "draw_location"}
            or weapon.get("native_type_key") != "Dagger"
            or weapon.get("display_name") != "Drawable Dagger"
            or weapon.get("draw_location") != "worn_sheath"):
        raise ArenaDrawScenarioRefusal("authored Draw scenario supports only its declared ordinary Dagger")
    return copy.deepcopy(value)


def author_scenario(candidate, value):
    """Add one native carried Dagger and its player-owned evidence to a private candidate."""
    scenario = validate_scenario(value)
    from being import BeingInstance
    from weapon import (WeaponInstance, author_worn_sheath_draw_location)
    from arena_perception import ArenaPerceptionEvidence, ArenaPerceptionLedger

    players = [participant.native.being for participant in candidate.participants
               if participant.role == "player_controlled"]
    if len(players) != 1 or type(players[0]) is not BeingInstance:
        raise ArenaDrawScenarioRefusal("authored Draw scenario requires one native player Being")
    player = players[0]
    if (player.current.hit_points <= 0 or player.is_helpless()
            or player.possessions or player.weapons or player.current.armor_id
            or type(player.current.body_parts) is not dict
            or any(type(slot) is not str or not slot.strip()
                   or occupant is not None and type(occupant) is not str
                   for slot, occupant in player.current.body_parts.items())):
        raise ArenaDrawScenarioRefusal("generated player state cannot accept the authored Draw fixture")
    requested_slots = scenario["player_hand_slots"]
    if any(slot not in player.current.body_parts
           or player.current.body_parts[slot] is not None
           for slot in requested_slots):
        raise ArenaDrawScenarioRefusal(
            "authored Draw hand must be explicitly declared free by the native Being template")
    ledger = object.__getattribute__(player, "__dict__").get("_arena_perception_ledger")
    if type(ledger) is not ArenaPerceptionLedger or ledger.observer_id != player.id:
        raise ArenaDrawScenarioRefusal("player-owned Arena perception ledger is unavailable")

    object_id = candidate.encounter.make_weapon(
        scenario["carried_weapon"]["native_type_key"],
        scenario["carried_weapon"]["display_name"])
    weapon = candidate.universe.get_object_by_id(object_id)
    if type(weapon) is not WeaponInstance or weapon.current.obj_type != "Dagger":
        raise ArenaDrawScenarioRefusal("native Dagger construction did not return the verified Weapon type")
    if (weapon.parent_container_id is not None or weapon.get_position() is not None
            or object_id in player.possessions or object_id in player.weapons):
        raise ArenaDrawScenarioRefusal("new native Dagger already has conflicting custody")

    player.possessions.append(object_id)
    weapon.parent_container_id = player.id
    author_worn_sheath_draw_location(weapon, player.id)
    evidence = ArenaPerceptionEvidence(player.id, object_id, "object", weapon.name,
        "Dagger", None, "carried", 0, float(candidate.encounter.time),
        owner_id=player.id, equipment_status="carried")
    ledger._current[object_id] = evidence
    ledger._history.append(evidence)
    candidate.encounter.awareness[player.id].add(object_id)

    if (candidate.universe.get_object_by_id(object_id) is not weapon
            or player.possessions.count(object_id) != 1
            or weapon.parent_container_id != player.id
            or candidate.encounter.get_entity(object_id) is not weapon
            or object_id not in ledger._current
            or any(row.entity_id == object_id for row in
                   object.__getattribute__(candidate.participants[1].native.being,
                                           "__dict__")["_arena_perception_ledger"].current)):
        raise ArenaDrawScenarioRefusal("authored native Dagger identity or observer custody failed validation")
    return weapon
