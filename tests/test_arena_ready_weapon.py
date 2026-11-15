"""Native two-second Draw from explicitly authored source and hand state."""
from pathlib import Path
import json
import math
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from activities import DelayAction, ReadyPreparationAction, ReadyWeaponAction, ShieldEquipmentAction
from activities import SpotAction
from arena_browser_session import ArenaBrowserRequestError, GeneratedArenaSession
from arena_hex_map import HexAddress
from arena_perception import ArenaPerceptionEvidence
from atomic_publication import PublicationFailure, _WritePlan
from melee_combat import MeleeStrike
from weapon import (DRAWABLE_WORN_SHEATH, NATIVE_DRAW_LOCATION_TAG, WeaponInstance,
                    author_forearm_buckler_attachment, author_worn_sheath_draw_location,
                    native_weapon_draw_location,
                    re_ready_time_after_strike, native_ready_preparation,
                    weapon_readying_time)

GENERATE = {"starting_experience": "10000", "width_cells": "10", "height_cells": "5"}
DAGGER = [{"source_item_id": "ready-test:dagger", "category": "weapon",
           "native_type_key": "Dagger", "quantity": 1, "ordinary": True,
           "magical": False, "mechanics": None, "origin": "ready-test.v1"}]


def arena(seed=20261108, *, ground_dagger=False):
    session = GeneratedArenaSession(root_seed_factory=lambda: seed,
        ground_item_descriptions=DAGGER if ground_dagger else ())
    session.generate(GENERATE)
    candidate = session.active_candidate
    player = candidate.participants[0].native.being
    if player.current.hit_points <= 0:
        raise AssertionError("deterministic fixture must contain a positive-HP player")
    return session, candidate, player


def add_authored_drawable_dagger(session, candidate, player, *, hand="right hand"):
    """Author one carried weapon, a drawable-source tag, and an explicit free hand."""
    object_id = candidate.encounter.make_weapon("Dagger", "Test Dagger")
    weapon = candidate.universe.get_object_by_id(object_id)
    if type(weapon) is not WeaponInstance:
        raise AssertionError("test fixture requires an exact native WeaponInstance")
    player.possessions.append(weapon.id)
    weapon.parent_container_id = player.id
    player.current.body_parts[hand] = None
    author_worn_sheath_draw_location(weapon, player.id)
    ledger = object.__getattribute__(player, "__dict__")["_arena_perception_ledger"]
    evidence = ArenaPerceptionEvidence(player.id, weapon.id, "object", weapon.name,
        "Dagger", None, "carried", 0, 0.0)
    ledger._current[weapon.id] = evidence
    ledger._history.append(evidence)
    return weapon


def activate(session):
    session.choose_run()
    return session.advance_one_second()


def select_draw(session, weapon):
    entity = next(row for row in session.public_view()["entities"]
                  if row["name"] == weapon.name and row["type"] == weapon.current.obj_type)
    inspected = session.inspect_entity({"handle": entity["handle"]})
    return entity["handle"], inspected


def draw_scenario():
    return json.loads((ROOT / "examples/arena_scenarios/ordinary-dagger-draw.json")
                      .read_text(encoding="utf-8"))


class TestArenaReadyWeapon(unittest.TestCase):
    def test_shield_don_remove_native_browser_choices_and_pending_fresh_process_restore(self):
        session, candidate, player = arena(seed=20261159)
        shield_id = candidate.encounter.make_weapon("Medium shield", "Authored carried shield")
        shield = candidate.universe.get_object_by_id(shield_id)
        player.possessions.append(shield_id)
        shield.parent_container_id = player.id
        player.current.body_parts["right hand"] = None
        ledger = object.__getattribute__(player, "__dict__")["_arena_perception_ledger"]
        evidence = ArenaPerceptionEvidence(player.id, shield.id, "object", shield.name,
            "Medium shield", None, "carried", 0, 0.0)
        ledger._current[shield.id] = evidence
        ledger._history.append(evidence)
        activate(session)
        entity = next(row for row in session.public_view()["entities"]
                      if row["name"] == shield.name)
        catalog = session.inspect_entity({"handle": entity["handle"]})["action_catalog"]
        don = next(row for row in catalog["entries"] if row["name"] == "don shield")
        self.assertEqual(don["status"], "available", don["reason"])
        duration = shield.St() * 5
        accepted = session.choose_shield_equipment({"handle": entity["handle"],
            "hand": "right hand", "operation": "don"})
        action = next(member.action for choice in candidate.encounter._choice_book._choices.values()
            for member in choice.members if type(member.action) is ShieldEquipmentAction)
        self.assertEqual(action.end_time - action.start_time, duration)
        self.assertEqual(player.current.body_parts["right hand"], None)
        pending = session.save_encounter_bytes()
        script = """import sys
from arena_browser_session import GeneratedArenaSession
from activities import ShieldEquipmentAction
s=GeneratedArenaSession();s.load_encounter_bytes(sys.stdin.buffer.read())
c=s.active_candidate;p=c.participants[0].native.being
a=next(m.action for r in c.encounter._choice_book._choices.values()
 for m in r.members if type(m.action) is ShieldEquipmentAction)
assert a.id==sys.argv[1] and a.operation=='don'
assert p.current.body_parts['right hand'] is None
assert p.possessions.count(sys.argv[2])==1 and sys.argv[2] not in p.weapons
for _ in range(int(sys.argv[3])):s.advance_one_second()
c=s.active_candidate;p=c.participants[0].native.being
o=c.universe.get_object_by_id(sys.argv[2])
assert p.current.body_parts['right hand']==o.id and p.weapons.count(o.id)==1
assert p.possessions.count(o.id)==1 and o.parent_container_id==p.id and o.get_position() is None
assert c.encounter.inspect_committed(int(c.encounter.time)).action(sys.argv[1]).facts.outcome=='success'
print('restored-and-committed-same-shield')"""
        restored = subprocess.run([sys.executable, "-B", "-c", script, action.id,
            shield_id, str(duration)], input=pending, cwd=ROOT, capture_output=True,
            check=False, timeout=60)
        self.assertEqual(restored.returncode, 0, restored.stderr.decode("utf-8", "replace"))
        self.assertEqual(restored.stdout.decode().strip(), "restored-and-committed-same-shield")
        # Continue in the parent session after the pending state has completed.
        session.load_encounter_bytes(pending)
        for _ in range(duration):
            session.advance_one_second()
        candidate = session.active_candidate
        player = candidate.participants[0].native.being
        view = session.public_view()
        self.assertEqual(player.shielded_with(candidate.universe).get("right hand"), shield_id)
        block = next(row for row in view["action_catalog"]["entries"] if row["name"] == "Block")
        self.assertNotIn("No native shield is equipped", block["reason"])
        completed_don = session.save_encounter_bytes()
        completed_script = """import sys
from arena_browser_session import GeneratedArenaSession
s=GeneratedArenaSession();s.load_encounter_bytes(sys.stdin.buffer.read())
c=s.active_candidate;p=c.participants[0].native.being;o=c.universe.get_object_by_id(sys.argv[1])
assert c.encounter.time==int(sys.argv[2]) and o.id==sys.argv[1]
assert p.current.body_parts['right hand']==o.id and p.weapons.count(o.id)==1
assert p.possessions.count(o.id)==1 and o.parent_container_id==p.id and o.get_position() is None
print('fresh-completed-don-same-shield')"""
        completed = subprocess.run([sys.executable, "-B", "-c", completed_script,
            shield_id, str(session.active_candidate.encounter.time)], input=completed_don,
            cwd=ROOT, capture_output=True, check=False, timeout=60)
        self.assertEqual(completed.returncode, 0, completed.stderr.decode("utf-8", "replace"))
        self.assertEqual(completed.stdout.decode().strip(), "fresh-completed-don-same-shield")
        entity = next(row for row in view["entities"] if row["name"] == shield.name)
        catalog = session.inspect_entity({"handle": entity["handle"]})["action_catalog"]
        remove = next(row for row in catalog["entries"] if row["name"] == "remove shield")
        self.assertEqual(remove["status"], "available", remove["reason"])
        duration = shield.St() * 2
        session.choose_shield_equipment({"handle": entity["handle"],
            "hand": "right hand", "operation": "remove"})
        remove_action = next(member.action for choice in session.active_candidate.encounter._choice_book._choices.values()
            for member in choice.members if type(member.action) is ShieldEquipmentAction
            and member.action.operation == 'remove')
        pending_remove = session.save_encounter_bytes()
        remove_script = """import sys
from arena_browser_session import GeneratedArenaSession
from activities import ShieldEquipmentAction
s=GeneratedArenaSession();s.load_encounter_bytes(sys.stdin.buffer.read())
c=s.active_candidate;p=c.participants[0].native.being;o=c.universe.get_object_by_id(sys.argv[1])
a=next(m.action for r in c.encounter._choice_book._choices.values()
 for m in r.members if type(m.action) is ShieldEquipmentAction and m.action.id==sys.argv[2])
assert (a.id, a.operation, p.current.body_parts['right hand'], o.id)==(sys.argv[2], 'remove', o.id, o.id), (a.id, a.operation, p.current.body_parts['right hand'], o.id, sys.argv[2])
for _ in range(int(sys.argv[3])):s.advance_one_second()
c=s.active_candidate;p=c.participants[0].native.being;o=c.universe.get_object_by_id(sys.argv[1])
assert p.current.body_parts['right hand'] is None and sys.argv[1] not in p.weapons
assert p.possessions.count(sys.argv[1])==1 and o.parent_container_id==p.id and o.get_position() is None
assert c.encounter.inspect_committed(int(c.encounter.time)).action(sys.argv[2]).facts.outcome=='success'
print('fresh-pending-remove-same-shield-carried')"""
        restored_remove = subprocess.run([sys.executable, "-B", "-c", remove_script,
            shield_id, remove_action.id, str(duration)], input=pending_remove, cwd=ROOT,
            capture_output=True, check=False, timeout=60)
        self.assertEqual(restored_remove.returncode, 0,
            restored_remove.stderr.decode("utf-8", "replace"))
        self.assertEqual(restored_remove.stdout.decode().strip(),
            "fresh-pending-remove-same-shield-carried")
        for _ in range(duration):
            session.advance_one_second()
        player = session.active_candidate.participants[0].native.being
        self.assertIsNone(player.current.body_parts["right hand"])
        self.assertIsNone(player.shielded_with(session.active_candidate.universe).get("right hand"))
        self.assertNotIn(shield_id, player.weapons)
        self.assertEqual(player.possessions.count(shield_id), 1)
        self.assertEqual(session.active_candidate.universe.get_object_by_id(shield_id).parent_container_id,
                         player.id)
        self.assertEqual(session.active_candidate.encounter.inspect_committed(
            int(session.active_candidate.encounter.time)).action(remove_action.id).facts.outcome,
            "success")
        view = session.public_view()
        block = next(row for row in view["action_catalog"]["entries"] if row["name"] == "Block")
        self.assertIn("No native shield is equipped", block["reason"])

    def test_tower_shield_don_is_refused_by_adopted_wielding_rule(self):
        session, candidate, player = arena(seed=20261160)
        shield_id = candidate.encounter.make_weapon("Tower shield", "Authored tower shield")
        shield = candidate.universe.get_object_by_id(shield_id)
        player.possessions.append(shield_id)
        shield.parent_container_id = player.id
        player.current.body_parts["right hand"] = None
        ledger = object.__getattribute__(player, "__dict__")["_arena_perception_ledger"]
        evidence = ArenaPerceptionEvidence(player.id, shield.id, "object", shield.name,
            "Tower shield", None, "carried", 0, 0.0)
        ledger._current[shield.id] = evidence
        ledger._history.append(evidence)
        activate(session)
        entity = next(row for row in session.public_view()["entities"]
                      if row["name"] == shield.name)
        catalog = session.inspect_entity({"handle": entity["handle"]})["action_catalog"]
        don = next(row for row in catalog["entries"] if row["name"] == "don shield")
        self.assertEqual(don["status"], "unavailable")
        self.assertIn("tower", don["reason"].casefold())
        self.assertIsNone(player.current.body_parts["right hand"])
        self.assertNotIn(shield_id, player.weapons)

    def test_generated_forearm_buckler_shows_free_hand_and_restores_bash_choice(self):
        session, candidate, player = arena(seed=20261148)
        buckler_id = candidate.encounter.make_weapon("Buckler", "Authored forearm buckler")
        buckler = candidate.universe.get_object_by_id(buckler_id)
        player.possessions.append(buckler_id)
        player.weapons.append(buckler_id)
        buckler.parent_container_id = player.id
        author_forearm_buckler_attachment(buckler, player.id, "left")
        player.current.tags["universe.native_dominant_hand"] = "right hand"
        ledger = object.__getattribute__(player, "__dict__")["_arena_perception_ledger"]
        evidence = ArenaPerceptionEvidence(player.id, buckler.id, "object", buckler.name,
            "Buckler", None, "carried", candidate.encounter.time, 0.0)
        ledger._current[buckler.id] = evidence
        ledger._history.append(evidence)
        activate(session)
        view = session.public_view()
        inventory_row = next(row for row in view["character"]["inventory"]["items"]
                             if row["type"] == "Buckler")
        self.assertEqual(inventory_row["status"], "attached to left forearm")
        self.assertEqual(next(row for row in view["character"]["anatomy"]["hands"]
                              if row["name"] == "left hand")["occupancy"], "empty")
        target = candidate.participants[1].native.being
        target_view = next(row for row in view["entities"]
                           if row.get("category") == "being" and row["name"].startswith(target.name))
        catalog = session.inspect_entity({"handle": target_view["handle"]})["action_catalog"]
        bash = next(row for row in catalog["entries"] if row["name"] == "Shield bash")
        self.assertEqual(bash["status"], "available", bash["reason"])
        self.assertTrue(any(row["type"] == "Buckler" for row in bash["weapon_options"]))
        session.choose_melee_strike({"handle": target_view["handle"], "motion": "swing",
            "weapon_handle": inventory_row["handle"], "shield_bash": True})
        saved = session.save_encounter_bytes()
        script = ("import sys;sys.path.insert(0,'src');"
            "from arena_browser_session import GeneratedArenaSession;"
            "s=GeneratedArenaSession();s.load_encounter_bytes(sys.stdin.buffer.read());"
            "c=s.active_candidate;p=c.participants[0].native.being;"
            "b=c.universe.get_object_by_id(sys.argv[1]);"
            "assert p.shielded_with(c.universe)['left forearm']==b.id;"
            "assert p.current.body_parts['left hand'] is None;"
            "assert any(m.action.instrument_id==b.id and m.action.shield_bash "
            "for r in c.encounter._choice_book._choices.values() for m in r.members);"
            "print('restored-forearm-buckler-and-bash-choice')")
        restored = subprocess.run([sys.executable, "-B", "-c", script, buckler.id],
            input=saved, cwd=ROOT, capture_output=True, check=False, timeout=30)
        self.assertEqual(restored.returncode, 0, restored.stderr.decode("utf-8", "replace"))
        self.assertEqual(restored.stdout.decode().strip(),
                         "restored-forearm-buckler-and-bash-choice")

    def test_generated_long_sword_draw_ready_with_shield_blocks_two_handed_use(self):
        empty_profile = json.loads((ROOT / "tests/fixtures/arena/empty.json").read_text())
        session = GeneratedArenaSession(root_seed_factory=lambda: 20261150,
            ground_loadout_profile=empty_profile)
        session.generate({"starting_experience": "10000", "width_cells": "10",
            "height_cells": "5", "equipment_mode": "unequipped",
            "opponent_strategy": "none",
            "size_categories": {"player": "medium", "opponent": "medium"}})
        candidate = session.active_candidate
        player, target = (row.native.being for row in candidate.participants)
        self.assertEqual(player.current.body_parts, {"left hand": None, "right hand": None})
        shield_id = candidate.encounter.make_weapon("Medium shield", "Authored carried shield")
        shield = candidate.universe.get_object_by_id(shield_id)
        player.possessions.append(shield_id)
        player.weapons.append(shield_id)
        shield.parent_container_id = player.id
        player.current.body_parts["left hand"] = shield_id
        player.current.tags["universe.native_dominant_hand"] = "right hand"

        weapon_id = candidate.encounter.make_weapon("Longsword", "Authored sheathed longsword")
        weapon = candidate.universe.get_object_by_id(weapon_id)
        player.possessions.append(weapon_id)
        weapon.parent_container_id = player.id
        author_worn_sheath_draw_location(weapon, player.id)
        ledger = object.__getattribute__(player, "__dict__")["_arena_perception_ledger"]
        evidence = ArenaPerceptionEvidence(player.id, weapon.id, "object", weapon.name,
            "Longsword", None, "carried", candidate.encounter.time, 0.0)
        ledger._current[weapon.id] = evidence
        ledger._history.append(evidence)

        layout = candidate.arena_map.layout
        target_cell = layout.cell_at_position(target.get_position())
        player_cell = layout.cell_at_position(player.get_position())
        destination = min((cell for cell in layout.neighbors(target_cell)
                           if layout.contains(cell) and cell != player_cell),
            key=lambda cell: math.dist(
                layout.center_position(cell, z=player.get_position().z).as_tuple(),
                player.get_position().as_tuple()))
        from hex_facing import nearest_facing
        destination_position = layout.center_position(destination, z=player.get_position().z)
        player.set_hex_facing(nearest_facing((target.get_position().x-destination_position.x,
            target.get_position().y-destination_position.y,
            target.get_position().z-destination_position.z)))
        session.choose_destination({"column": destination.column, "row": destination.row,
                                    "rate": "sprint", "facing_policy": "maintain"})
        while session.public_view()["movement_plan"] is not None:
            session.advance_one_second()

        weapon_handle, _ = select_draw(session, weapon)
        session.choose_ready_weapon({"handle": weapon_handle, "hand": "right hand"})
        session.advance_one_second()
        session.advance_one_second()
        weapon_handle, _ = select_draw(session, weapon)
        session.choose_ready_preparation({"handle": weapon_handle, "motion": "swing"})
        session.advance_one_second()
        session.advance_one_second()

        target_view = next(row for row in session.public_view()["entities"]
                           if row.get("category") == "being" and row["name"].startswith(target.name))
        catalog = session.inspect_entity({"handle": target_view["handle"]})["action_catalog"]
        strike = next(row for row in catalog["entries"] if row["name"] == "swing at being")
        options = strike["weapon_options"]
        self.assertTrue(any(row["type"] == "Longsword" and row["grip"] == "one-handed"
                            for row in options))
        self.assertFalse(any(row["type"] == "Longsword" and row["grip"] == "two-handed"
                             for row in options))
        with self.assertRaisesRegex(ArenaBrowserRequestError,
                                    "Native swing Choice is unavailable"):
            session.choose_melee_strike({"handle": target_view["handle"],
                "motion": "swing", "weapon_handle": weapon_handle, "two_handed": True})
        session.choose_melee_strike({"handle": target_view["handle"],
            "motion": "swing", "weapon_handle": weapon_handle})
        self.assertEqual(player.current.body_parts["left hand"], shield_id)
        self.assertEqual(player.current.body_parts["right hand"], weapon_id)
        self.assertEqual(native_ready_preparation(weapon)["motion"], "swing")
        action = next(member.action for choice in candidate.encounter._choice_book._choices.values()
            for member in choice.members if type(member.action) is MeleeStrike
            and member.action.instrument_id == weapon_id)
        self.assertFalse(action.two_handed)
        saved = session.save_encounter_bytes()
        script = """import json,sys
from arena_browser_session import GeneratedArenaSession
from melee_combat import MeleeStrike
from weapon import native_ready_preparation
s=GeneratedArenaSession()
s.load_encounter_bytes(sys.stdin.buffer.read())
c=s.active_candidate
a=next(m.action for r in c.encounter._choice_book._choices.values()
    for m in r.members if type(m.action) is MeleeStrike and m.action.id==sys.argv[1])
w=c.universe.get_object_by_id(sys.argv[2])
shield=c.universe.get_object_by_id(sys.argv[3])
p=c.participants[0].native.being
assert not a.two_handed and a.instrument_id==w.id
assert p.current.body_parts['left hand']==shield.id and p.current.body_parts['right hand']==w.id
for _ in range(12):
    s.advance_one_second()
    if a.resolution is not None:
        break
assert a.resolution is not None and a.id in c.encounter.finished_action_list
assert native_ready_preparation(w) is None
print(json.dumps({'outcome':a.resolution.outcome,'time':c.encounter.time,
    'weapon_id':w.id,'shield_id':shield.id,'ready':native_ready_preparation(w)}))
"""
        restored = subprocess.run([sys.executable, "-B", "-c", script,
            action.id, weapon_id, shield_id], input=saved, cwd=ROOT,
            capture_output=True, check=False, timeout=90)
        self.assertEqual(restored.returncode, 0, restored.stderr.decode("utf-8", "replace"))
        evidence = json.loads(restored.stdout)
        self.assertIn(evidence["outcome"], ("normal", "miss"))
        self.assertEqual(evidence["weapon_id"], weapon_id)
        self.assertEqual(evidence["shield_id"], shield_id)
        self.assertIsNone(evidence["ready"])

    def test_generated_arena_exposes_native_shield_bash_and_persists_pending_choice(self):
        session, candidate, player = arena(seed=20261148)
        shield_id = candidate.universe.make_weapon("Medium shield", "Authored Arena shield")
        shield = candidate.universe.get_object_by_id(shield_id)
        player.possessions.append(shield_id)
        player.weapons.append(shield_id)
        shield.parent_container_id = player.id
        shield_hand = next(slot for slot in ("left hand", "right hand")
                           if player.current.body_parts.get(slot) is None)
        player.current.body_parts[shield_hand] = shield_id
        dominant = "right hand" if shield_hand == "left hand" else "left hand"
        player.current.tags["universe.native_dominant_hand"] = dominant
        ledger = object.__getattribute__(player, "__dict__")["_arena_perception_ledger"]
        evidence = ArenaPerceptionEvidence(player.id, shield.id, "object", shield.name,
            "Medium shield", None, "carried", candidate.encounter.time, 0.0)
        ledger._current[shield.id] = evidence
        ledger._history.append(evidence)
        activate(session)
        target = candidate.participants[1].native.being
        target_view = next(row for row in session.public_view()["entities"]
                           if row.get("category") == "being"
                           and row["name"].startswith(target.name))
        action_catalog = session.inspect_entity({"handle": target_view["handle"]})["action_catalog"]
        bash = next(row for row in action_catalog["entries"] if row["name"] == "Shield bash")
        self.assertEqual(bash["status"], "available")
        self.assertTrue(any(row["type"] == "Medium shield" for row in bash["weapon_options"]))
        shield_view = next(row for row in session.public_view()["entities"]
                           if row["name"] == shield.name)
        session.choose_melee_strike({"handle": target_view["handle"],
            "motion": "swing", "weapon_handle": shield_view["handle"],
            "shield_bash": True})
        saved = session.save_encounter_bytes()
        script = ("import sys;sys.path.insert(0,'src');"
            "from arena_browser_session import GeneratedArenaSession;"
            "s=GeneratedArenaSession();s.load_encounter_bytes(sys.stdin.buffer.read());"
            "c=s.active_candidate;b=c.universe.get_object_by_id(sys.argv[1]);"
            "assert any(m.action.instrument_id==b.id and m.action.shield_bash "
            "for r in c.encounter._choice_book._choices.values() for m in r.members);"
            "print('restored-shield-bash-choice')")
        restored = subprocess.run([sys.executable, "-B", "-c", script, shield.id],
            input=saved, cwd=ROOT, capture_output=True, check=False, timeout=30)
        self.assertEqual(restored.returncode, 0, restored.stderr.decode("utf-8", "replace"))
        self.assertEqual(restored.stdout.decode().strip(), "restored-shield-bash-choice")

    def test_generated_medium_shield_bash_resolves_after_fresh_process_restore(self):
        session, candidate, player = arena(seed=20261148)
        shield_id = candidate.universe.make_weapon("Medium shield", "Authored Arena bash shield")
        shield = candidate.universe.get_object_by_id(shield_id)
        player.possessions.append(shield_id)
        player.weapons.append(shield_id)
        shield.parent_container_id = player.id
        hand = next(slot for slot in ("left hand", "right hand")
                    if player.current.body_parts.get(slot) is None)
        player.current.body_parts[hand] = shield_id
        dominant = "right hand" if hand == "left hand" else "left hand"
        player.current.tags["universe.native_dominant_hand"] = dominant
        ledger = object.__getattribute__(player, "__dict__")["_arena_perception_ledger"]
        evidence = ArenaPerceptionEvidence(player.id, shield.id, "object", shield.name,
            "Medium shield", None, "carried", candidate.encounter.time, 0.0)
        ledger._current[shield.id] = evidence
        ledger._history.append(evidence)
        target = candidate.participants[1].native.being
        layout = candidate.arena_map.layout
        target_cell = layout.cell_at_position(target.get_position())
        player_cell = layout.cell_at_position(player.get_position())
        destination = min((cell for cell in layout.neighbors(target_cell)
                           if layout.contains(cell) and cell != player_cell),
            key=lambda cell: math.dist(layout.center_position(cell,
                z=player.get_position().z).as_tuple(), player.get_position().as_tuple()))
        # The fixture explicitly authors the Being's initial facing toward the
        # target and asks the native movement route to preserve it.
        from hex_facing import nearest_facing
        destination_position = layout.center_position(destination, z=player.get_position().z)
        player.set_hex_facing(nearest_facing((target.get_position().x-destination_position.x,
            target.get_position().y-destination_position.y,
            target.get_position().z-destination_position.z)))
        session.choose_destination({"column": destination.column, "row": destination.row,
            "rate": "sprint", "facing_policy": "maintain"})
        while session.public_view()["movement_plan"] is not None:
            session.advance_one_second()
        target_row = next(row for row in session.public_view()["entities"]
            if row.get("category") == "being" and row["name"].startswith(target.name))
        shield_row = next(row for row in session.public_view()["entities"]
            if row["name"] == shield.name)
        session.choose_melee_strike({"handle": target_row["handle"], "motion": "swing",
            "weapon_handle": shield_row["handle"], "shield_bash": True})
        choice = next(member.action for row in candidate.encounter._choice_book._choices.values()
            for member in row.members if getattr(member.action, "shield_bash", False))
        save = session.save_encounter_bytes()
        script = """import json,sys
from arena_browser_session import GeneratedArenaSession
s=GeneratedArenaSession()
s.load_encounter_bytes(sys.stdin.buffer.read())
c=s.active_candidate
a=next(m.action for r in c.encounter._choice_book._choices.values()
    for m in r.members if m.action.id==sys.argv[1])
assert a.shield_bash and a.instrument_id==sys.argv[2]
for _ in range(8):
    s.advance_one_second()
    if a.resolution is not None:
        break
assert a.resolution is not None
print(json.dumps({'outcome':a.resolution.outcome,'time':c.encounter.time,
    'shield_id':a.instrument_id,'target_id':a.target_id}))
"""
        restored = subprocess.run([sys.executable, "-B", "-c", script, choice.id, shield_id],
            input=save, cwd=ROOT, capture_output=True, check=False, timeout=60)
        self.assertEqual(restored.returncode, 0, restored.stderr.decode("utf-8", "replace"))
        result = json.loads(restored.stdout)
        self.assertIn(result["outcome"], ("normal", "miss"))
        self.assertEqual(result["shield_id"], shield_id)
        self.assertEqual(result["target_id"], target.id)

    def test_generated_arena_draws_non_dagger_weapon_with_identity_preserved_after_fresh_process_load(self):
        session, candidate, player = arena(seed=20261147)
        activate(session)
        weapon_id = candidate.encounter.make_weapon("Longsword", "Authored test longsword")
        weapon = candidate.universe.get_object_by_id(weapon_id)
        player.possessions.append(weapon_id)
        weapon.parent_container_id = player.id
        free_hand = next(slot for slot in ("left hand", "right hand")
                         if player.current.body_parts.get(slot) is None)
        author_worn_sheath_draw_location(weapon, player.id)
        ledger = object.__getattribute__(player, "__dict__")["_arena_perception_ledger"]
        evidence = ArenaPerceptionEvidence(player.id, weapon.id, "object", weapon.name,
            "Longsword", None, "carried", candidate.encounter.time, 0.0)
        ledger._current[weapon.id] = evidence
        ledger._history.append(evidence)
        handle, inspected = select_draw(session, weapon)
        draw_row = next(row for row in inspected["action_catalog"]["entries"]
                        if row["name"] == "ready weapon")
        self.assertEqual(draw_row["status"], "available")
        self.assertIn("2 seconds", draw_row["reason"])
        session.choose_ready_weapon({"handle": handle, "hand": free_hand})
        session.advance_one_second()
        session.advance_one_second()
        self.assertEqual(player.current.body_parts[free_hand], weapon.id)
        self.assertEqual(weapon.parent_container_id, player.id)
        handle, inspected = select_draw(session, weapon)
        self.assertEqual(next(row for row in inspected["action_catalog"]["entries"]
                              if row["name"] == "ready object")["status"], "available")
        session.choose_ready_preparation({"handle": handle, "motion": "swing"})
        session.advance_one_second()
        session.advance_one_second()
        player.size_category = "medium"
        other_hand = "right hand" if free_hand == "left hand" else "left hand"
        player.current.body_parts[other_hand] = None
        target = candidate.participants[1].native.being
        target_view = next(row for row in session.public_view()["entities"]
                           if row.get("category") == "being"
                           and row["name"].startswith(target.name))
        selected_weapon = next(row for row in session.public_view()["entities"]
                               if row["name"] == weapon.name)
        catalog = session.inspect_entity({"handle": target_view["handle"]})["action_catalog"]
        melee_row = next(row for row in catalog["entries"] if row["name"] == "swing at being")
        self.assertTrue(any(row["type"] == "Longsword" and row["grip"] == "two-handed"
                            for row in melee_row["weapon_options"]))
        session.choose_melee_strike({"handle": target_view["handle"],
            "motion": "swing", "weapon_handle": selected_weapon["handle"],
            "two_handed": True})
        saved = session.save_encounter_bytes()
        script = ("import sys;sys.path.insert(0,'src');"
            "from arena_browser_session import GeneratedArenaSession;"
            "s=GeneratedArenaSession();s.load_encounter_bytes(sys.stdin.buffer.read());"
            "c=s.active_candidate;b=c.universe.get_object_by_id(sys.argv[1]);"
            "p=c.participants[0].native.being;"
            "assert b.current.obj_type=='Longsword' and b.parent_container_id==p.id;"
            "assert b.id in p.possessions and b.id in p.weapons;"
            "assert b.id in p.current.body_parts.values();"
            "assert any(m.action.instrument_id==b.id for r in c.encounter._choice_book._choices.values() "
            "for m in r.members);"
            "print('restored-non-dagger-draw-and-pending-strike')")
        restored = subprocess.run([sys.executable, "-B", "-c", script, weapon.id],
            input=saved, cwd=ROOT, capture_output=True, check=False, timeout=30)
        self.assertEqual(restored.returncode, 0, restored.stderr.decode("utf-8", "replace"))
        self.assertEqual(restored.stdout.decode().strip(), "restored-non-dagger-draw-and-pending-strike")

    def test_unequipped_generated_arena_draw_ready_and_two_handed_strike_round_trip(self):
        empty_profile = json.loads((ROOT / "tests/fixtures/arena/empty.json").read_text())
        session = GeneratedArenaSession(root_seed_factory=lambda: 20261161,
            ground_loadout_profile=empty_profile)
        session.generate({"starting_experience": "10000", "width_cells": "10",
            "height_cells": "5", "equipment_mode": "unequipped",
            "opponent_strategy": "none",
            "size_categories": {"player": "medium", "opponent": "medium"}})
        candidate = session.active_candidate
        player, target = (row.native.being for row in candidate.participants)
        self.assertEqual(player.current.body_parts, {"left hand": None, "right hand": None})
        weapon_id = candidate.encounter.make_weapon("Longsword", "Authored lifecycle Longsword")
        weapon = candidate.universe.get_object_by_id(weapon_id)
        player.possessions.append(weapon_id)
        weapon.parent_container_id = player.id
        author_worn_sheath_draw_location(weapon, player.id)
        ledger = object.__getattribute__(player, "__dict__")["_arena_perception_ledger"]
        evidence = ArenaPerceptionEvidence(player.id, weapon.id, "object", weapon.name,
            "Longsword", None, "carried", candidate.encounter.time, 0.0)
        ledger._current[weapon.id] = evidence
        ledger._history.append(evidence)

        layout = candidate.arena_map.layout
        target_cell = layout.cell_at_position(target.get_position())
        player_cell = layout.cell_at_position(player.get_position())
        destination = min((cell for cell in layout.neighbors(target_cell)
                           if layout.contains(cell) and cell != player_cell),
            key=lambda cell: math.dist(layout.center_position(cell,
                z=player.get_position().z).as_tuple(), player.get_position().as_tuple()))
        from hex_facing import nearest_facing
        destination_position = layout.center_position(destination, z=player.get_position().z)
        player.set_hex_facing(nearest_facing((target.get_position().x-destination_position.x,
            target.get_position().y-destination_position.y,
            target.get_position().z-destination_position.z)))
        session.choose_destination({"column": destination.column, "row": destination.row,
            "rate": "sprint", "facing_policy": "maintain"})
        while session.public_view()["movement_plan"] is not None:
            session.advance_one_second()

        weapon_row = next(row for row in session.public_view()["entities"]
            if row.get("category") == "object" and row["name"] == weapon.name)
        hand = "right hand"
        session.choose_ready_weapon({"handle": weapon_row["handle"], "hand": hand})
        session.advance_one_second()
        session.advance_one_second()
        self.assertEqual(player.current.body_parts[hand], weapon_id)
        self.assertIsNone(player.current.body_parts["left hand"])
        weapon_row = next(row for row in session.public_view()["entities"]
            if row.get("category") == "object" and row["name"] == weapon.name)
        session.choose_ready_preparation({"handle": weapon_row["handle"], "motion": "swing"})
        for _ in range(weapon_readying_time(weapon, "swing")):
            session.advance_one_second()
        self.assertEqual(native_ready_preparation(weapon)["motion"], "swing")

        target_row = next(row for row in session.public_view()["entities"]
            if row.get("category") == "being" and row["name"].startswith(target.name))
        weapon_row = next(row for row in session.public_view()["entities"]
            if row.get("category") == "object" and row["name"] == weapon.name)
        options = session.inspect_entity({"handle": target_row["handle"]})["action_catalog"]
        strike = next(row for row in options["entries"] if row["name"] == "swing at being")
        self.assertTrue(any(row["handle"] == weapon_row["handle"]
                            and row["grip"] == "two-handed"
                            for row in strike["weapon_options"]))
        session.choose_melee_strike({"handle": target_row["handle"], "motion": "swing",
            "weapon_handle": weapon_row["handle"], "two_handed": True})
        action = next(member.action for choice in candidate.encounter._choice_book._choices.values()
            for member in choice.members if getattr(member.action, "two_handed", False))
        saved = session.save_encounter_bytes()
        script = """import json,sys
from arena_browser_session import GeneratedArenaSession
from melee_combat import MeleeStrike
from weapon import native_ready_preparation
s=GeneratedArenaSession()
s.load_encounter_bytes(sys.stdin.buffer.read())
c=s.active_candidate
a=next(m.action for r in c.encounter._choice_book._choices.values()
    for m in r.members if m.action.id==sys.argv[1])
w=c.universe.get_object_by_id(sys.argv[2])
p=c.participants[0].native.being
assert type(a) is MeleeStrike and a.two_handed and a.instrument_id==w.id
assert p.current.body_parts['left hand'] is None and p.current.body_parts['right hand']==w.id
for _ in range(12):
    s.advance_one_second()
    if a.resolution is not None:
        break
assert a.resolution is not None
assert native_ready_preparation(w) is None
assert a.id in c.encounter.finished_action_list
print(json.dumps({'outcome':a.resolution.outcome,'time':c.encounter.time,
    'weapon_id':w.id,'two_handed':a.two_handed,'ready':native_ready_preparation(w)}))
"""
        restored = subprocess.run([sys.executable, "-B", "-c", script, action.id, weapon_id],
            input=saved, cwd=ROOT, capture_output=True, check=False, timeout=90)
        self.assertEqual(restored.returncode, 0, restored.stderr.decode("utf-8", "replace"))
        result = json.loads(restored.stdout)
        self.assertIn(result["outcome"], ("normal", "miss"))
        self.assertEqual(result["weapon_id"], weapon_id)
        self.assertTrue(result["two_handed"])
        self.assertIsNone(result["ready"])

    def test_generated_arena_offers_and_persists_adopted_set_pole_control(self):
        session, candidate, player = arena(seed=20261144)
        activate(session)
        weapon_id = candidate.encounter.make_weapon_for_being(
            player.id, "Spear", "Arena set-pole spear")
        weapon = candidate.universe.get_object_by_id(weapon_id)
        hand = next(slot for slot, held in player.current.body_parts.items()
                    if slot in ("left hand", "right hand") and held is None)
        player.possessions.append(weapon_id)
        player.weapons.append(weapon_id)
        player.current.body_parts[hand] = weapon_id
        ledger = object.__getattribute__(player, "__dict__")["_arena_perception_ledger"]
        evidence = ArenaPerceptionEvidence(player.id, weapon.id, "object", weapon.name,
            "Spear", None, "carried", candidate.encounter.time, 0.0)
        ledger._current[weapon.id] = evidence
        ledger._history.append(evidence)
        handle, inspected = select_draw(session, weapon)
        ready_row = next(row for row in inspected["action_catalog"]["entries"]
                         if row["name"] == "ready object")
        self.assertIn({"motion": "set pole", "duration_seconds": 4}, ready_row["motions"])
        session.choose_ready_preparation({"handle": handle, "motion": "set pole"})
        for _ in range(4):
            session.advance_one_second()
        preparation = native_ready_preparation(weapon)
        self.assertTrue(preparation["pole_set"])
        saved = session.save_encounter_bytes()
        script = ("import sys;sys.path.insert(0,'src');"
            "from arena_browser_session import GeneratedArenaSession;"
            "from weapon import native_ready_preparation;"
            "s=GeneratedArenaSession();s.load_encounter_bytes(sys.stdin.buffer.read());"
            "c=s.active_candidate;b=next(x for x in c.universe.object_registry.object_instances.values() "
            "if getattr(x,'name',None)=='Arena set-pole spear');"
            "assert native_ready_preparation(b)['pole_set'] is True;print('restored-pole-set')")
        restored = subprocess.run([sys.executable, "-B", "-c", script], input=saved,
            cwd=ROOT, capture_output=True, check=False, timeout=30)
        self.assertEqual(restored.returncode, 0, restored.stderr.decode("utf-8", "replace"))
        self.assertEqual(restored.stdout.decode().strip(), "restored-pole-set")

    def test_eligible_action_pause_resume_preserves_remaining_duration_and_process_save(self):
        session, candidate, player = arena(seed=20261132)
        opponent=candidate.participants[1].native.being
        session.choose_run(); session.advance_one_second()
        spot=SpotAction(candidate.universe,player.id,opponent.id,candidate.encounter.time)
        candidate.encounter.schedule_action(spot)
        candidate.encounter.step(2)
        self.assertEqual(candidate.encounter.time,3)
        pause=candidate.encounter._choice_book.pause_action(spot.id)
        self.assertEqual(pause['remaining'],4)
        candidate.encounter.step(3)
        self.assertEqual(candidate.encounter.time,6)
        self.assertIsNone(spot.resolution)
        paused_bytes=session.save_encounter_bytes()
        script=("import sys;sys.path.insert(0,'src');"
            "from arena_browser_session import GeneratedArenaSession;"
            "s=GeneratedArenaSession();s.load_encounter_bytes(sys.stdin.buffer.read());"
            "c=s.active_candidate;b=c.encounter._choice_book;"
            "rows=[c.universe.get_event_by_id(a) for a in c.encounter.pending_action_list];"
            "a=next(x for x in rows if x.event_type=='spot');"
            "assert b.is_paused(a.id) and b._paused[a.id]['remaining']==4;"
            "print('restored-paused-action')")
        fresh=subprocess.run([sys.executable,'-B','-c',script],input=paused_bytes,
            cwd=ROOT,capture_output=True,check=False,timeout=30)
        self.assertEqual(fresh.returncode,0,fresh.stderr.decode('utf-8','replace'))
        self.assertEqual(fresh.stdout.decode().strip(),'restored-paused-action')
        candidate.encounter._choice_book.resume_action(spot.id)
        self.assertEqual(candidate.encounter._choice_book.effective_end(spot),10)
        candidate.encounter.step(3)
        self.assertIsNone(spot.resolution)
        candidate.encounter.step(1)
        self.assertIsNotNone(spot.resolution)
        self.assertEqual(candidate.encounter.time,10)

    def test_momentum_dependent_strike_cannot_be_paused(self):
        session,candidate,player=arena(seed=20261133)
        opponent=candidate.participants[1].native.being
        weapon_id=candidate.encounter.make_weapon('Dagger','Pause-test Dagger')
        weapon=candidate.universe.get_object_by_id(weapon_id)
        player.possessions.append(weapon_id);player.weapons.append(weapon_id)
        player.current.body_parts['right hand']=weapon_id;weapon.parent_container_id=player.id
        session.choose_run();session.advance_one_second()
        strike=MeleeStrike(candidate.encounter,player.id,opponent.id,weapon_id,
            motion='swing',reach=100)
        candidate.encounter.schedule_action(strike)
        candidate.encounter.step(1)
        with self.assertRaisesRegex(ValueError,'Momentum-dependent'):
            candidate.encounter._choice_book.pause_action(strike.id)

    def test_generated_draw_ready_delay_and_use_controls(self):
        session = GeneratedArenaSession(authored_draw_scenario=draw_scenario(),
            root_seed_factory=lambda: 20261130)
        session.generate(GENERATE)
        candidate = session.active_candidate
        player = candidate.participants[0].native.being
        weapon = candidate.universe.get_object_by_id(player.possessions[0])
        handle, _ = select_draw(session, weapon)
        session.choose_ready_weapon({"handle": handle, "hand": "right hand"})
        session.advance_one_second()
        session.advance_one_second()
        handle, inspected = select_draw(session, weapon)
        ready_row = next(row for row in inspected["action_catalog"]["entries"]
                         if row["name"] == "ready object")
        self.assertEqual(ready_row["status"], "available")
        self.assertEqual(ready_row["motions"], [
            {"motion": "swing", "duration_seconds": 1},
            {"motion": "thrust", "duration_seconds": 1}])
        session.choose_ready_preparation({"handle": handle, "motion": "swing"})
        self.assertEqual(session.advance_one_second()["ready_preparation_action"]["outcome"],
                         "success")
        ready = native_ready_preparation(weapon)
        session.choose_delay({"defense": 0})
        self.assertEqual(session.advance_one_second()["delay_action"]["outcome"], "success")
        self.assertEqual(native_ready_preparation(weapon), ready)
        wire = session.save_encounter_bytes()
        restored = GeneratedArenaSession(root_seed_factory=lambda: 20261130)
        restored.load_encounter_bytes(wire)
        loaded_weapon = restored.active_candidate.universe.get_object_by_id(weapon.id)
        self.assertEqual(native_ready_preparation(loaded_weapon), ready)
        self.assertEqual(restored.active_candidate.participants[0].native.being.strategy.defense, 0)
        script = (
            "import sys; sys.path.insert(0, 'src'); "
            "from arena_browser_session import GeneratedArenaSession; "
            "from weapon import WeaponInstance, native_ready_preparation; "
            "s=GeneratedArenaSession(); s.load_encounter_bytes(sys.stdin.buffer.read()); "
            "c=s.active_candidate; "
            "rows=[native_ready_preparation(o) for o in c.universe.object_registry.object_instances.values() "
            "if type(o) is WeaponInstance and native_ready_preparation(o) is not None]; "
            "assert len(rows)==1 and rows[0]['motion']=='swing'; "
            "assert c.participants[0].native.being.strategy.defense==0; print('restored-ready-delay')")
        fresh = subprocess.run([sys.executable, "-B", "-c", script], input=wire,
            cwd=ROOT, capture_output=True, check=False, timeout=30)
        self.assertEqual(fresh.returncode, 0, fresh.stderr.decode("utf-8", "replace"))
        self.assertEqual(fresh.stdout.decode().strip(), "restored-ready-delay")
        opponent = candidate.participants[1].native.being
        strike = MeleeStrike(candidate.encounter, player.id, opponent.id, weapon.id,
                             motion="swing", reach=100)
        self.assertEqual(strike.end_time - strike.start_time, 3)

    def test_ready_long_sword_swing_uses_two_seconds_and_persists_native_preparation(self):
        session, candidate, player = arena(seed=20261131)
        weapon_id = candidate.encounter.make_weapon("Longsword", "Test Longsword")
        weapon = candidate.universe.get_object_by_id(weapon_id)
        player.possessions.append(weapon.id)
        player.weapons.append(weapon.id)
        weapon.parent_container_id = player.id
        player.current.body_parts["right hand"] = weapon.id
        self.assertEqual(weapon_readying_time(weapon, "swing"), 2)
        session.choose_run()
        session.advance_one_second()
        action = ReadyPreparationAction(candidate.encounter, player.id, weapon.id,
                                        "swing", 1)
        candidate.encounter.schedule_action(action)
        candidate.encounter.step(2)
        preparation = native_ready_preparation(weapon)
        self.assertEqual(preparation, {
            "owner_id": player.id, "motion": "swing", "ready_action_id": action.id,
            "completed_at": 3, "readying_seconds": 2})
        delay = DelayAction(candidate.encounter, player.id, defense=0, start_time=3)
        candidate.encounter.schedule_action(delay)
        candidate.encounter.step(1)
        self.assertEqual(native_ready_preparation(weapon), preparation)
        opponent = candidate.participants[1].native.being
        strike = MeleeStrike(candidate.encounter, player.id, opponent.id, weapon.id,
                             motion="swing", reach=100)
        self.assertEqual(strike.end_time - strike.start_time, 4)
        candidate.encounter.schedule_action(strike)
        candidate.encounter.step(4)
        self.assertIsNone(native_ready_preparation(weapon))
        repeated = MeleeStrike(candidate.encounter, player.id, opponent.id, weapon.id,
                               motion="swing", reach=100)
        self.assertEqual(repeated.end_time - repeated.start_time, 6)
        consumed_wire = session.save_encounter_bytes()
        script = """import json,sys
from arena_browser_session import GeneratedArenaSession
from melee_combat import MeleeStrike
from weapon import WeaponInstance,native_ready_preparation
s=GeneratedArenaSession()
s.load_encounter_bytes(sys.stdin.buffer.read())
c=s.active_candidate
w=c.universe.get_object_by_id(sys.argv[1])
p=c.participants[0].native.being
actions=[a for a in c.universe.event_history.values()
    if type(a) is MeleeStrike and a.actor_id==p.id and a.instrument_id==w.id]
assert len(actions)==1 and actions[0].id in c.encounter.finished_action_list
assert native_ready_preparation(w) is None and w.parent_container_id==p.id
print(json.dumps({'weapon_id':w.id,'outcome':actions[0].resolution.outcome,
    'time':c.encounter.time,'ready':native_ready_preparation(w)}))
"""
        restored = subprocess.run([sys.executable, "-B", "-c", script, weapon.id],
            input=consumed_wire, cwd=ROOT, capture_output=True, check=False, timeout=60)
        self.assertEqual(restored.returncode, 0, restored.stderr.decode("utf-8", "replace"))
        evidence = json.loads(restored.stdout)
        self.assertEqual(evidence, {"weapon_id": weapon.id,
            "outcome": strike.resolution.outcome, "time": candidate.encounter.time,
            "ready": None})

    def test_opt_in_authored_scenario_draws_as_first_choice_and_regenerates_cleanly(self):
        session = GeneratedArenaSession(root_seed_factory=iter((20261120, 20261121)).__next__,
                                        authored_draw_scenario=draw_scenario())
        first_view = session.generate(GENERATE)
        candidate = session.active_candidate
        player = candidate.participants[0].native.being
        opponent = candidate.participants[1].native.being
        self.assertEqual(candidate.encounter.time, 0)
        self.assertFalse(candidate.encounter.initiated)
        self.assertIsNone(candidate.encounter.initiation)
        self.assertEqual(player.current.body_parts,
                         {"left hand": None, "right hand": None})
        self.assertEqual(len(player.possessions), 1)
        weapon = candidate.universe.get_object_by_id(player.possessions[0])
        self.assertIs(type(weapon), WeaponInstance)
        self.assertEqual(weapon.current.obj_type, "Dagger")
        self.assertEqual(weapon.name, "Drawable Dagger")
        self.assertEqual(weapon.parent_container_id, player.id)
        self.assertEqual(player.weapons, [])
        self.assertIsNone(player.current.armor_id)
        self.assertEqual(native_weapon_draw_location(weapon),
                         {"kind": "worn_sheath", "owner_id": player.id})
        own_ledger = object.__getattribute__(player, "__dict__")["_arena_perception_ledger"]
        opponent_ledger = object.__getattribute__(opponent, "__dict__")["_arena_perception_ledger"]
        self.assertIn(weapon.id, {row.entity_id for row in own_ledger.current})
        self.assertNotIn(weapon.id, {row.entity_id for row in opponent_ledger.current})
        self.assertNotIn(weapon.id, opponent.possessions)
        self.assertNotIn(weapon.id, json.dumps(first_view))
        self.assertEqual(candidate.encounter.pending_action_list, [])
        self.assertFalse(any(type(event) is ReadyWeaponAction
                             for event in candidate.universe.event_history.values()))

        entity = next(row for row in first_view["entities"]
                      if row["name"] == "Drawable Dagger")
        inspected = session.inspect_entity({"handle": entity["handle"]})
        catalog = next(row for row in inspected["action_catalog"]["entries"]
                       if row["name"] == "ready weapon")
        self.assertEqual((catalog["status"], catalog["display_name"], catalog["hands"]),
                         ("available", "Draw (2 s)", ["left hand", "right hand"]))
        weight = weapon.current.weight
        activation_awareness = dict((key, set(value)) for key, value in candidate.encounter.awareness.items())
        accepted = session.choose_ready_weapon({"handle": entity["handle"], "hand": "right hand"})
        self.assertTrue(candidate.encounter.initiated)
        self.assertIsNone(candidate.encounter.initiation)
        self.assertEqual(candidate.encounter.awareness, activation_awareness)
        self.assertIsNotNone(candidate.encounter.arena_activation)
        self.assertEqual(candidate.encounter.arena_activation.activation_kind,
                         "first_player_choice")
        self.assertNotIn("target_id", candidate.encounter.arena_activation.to_dict())
        self.assertEqual(accepted["ready_weapon_action"]["seconds_remaining"], 2)
        self.assertEqual(accepted["character"]["inventory"]["items"][0]["status"],
                         "carried; not readied")
        one = session.advance_one_second()
        self.assertEqual(one["time_seconds"], 1)
        self.assertEqual(one["ready_weapon_action"]["seconds_remaining"], 1)
        self.assertEqual(one["character"]["inventory"]["items"][0]["status"],
                         "carried; not readied")
        self.assertIsNone(player.current.body_parts["right hand"])
        self.assertIsNotNone(native_weapon_draw_location(weapon))
        two = session.advance_one_second()
        self.assertEqual(two["time_seconds"], 2)
        self.assertEqual(two["ready_weapon_action"]["outcome"], "success")
        self.assertEqual(two["character"]["inventory"]["items"][0]["status"],
                         "readied in right hand")
        self.assertEqual(two["character"]["inventory"]["items"][0]["weight_pounds"], weight)
        self.assertEqual(two["character"]["inventory"]["carried_weight_pounds"], weight)
        self.assertEqual(player.current.body_parts["right hand"], weapon.id)
        self.assertEqual(player.possessions, [weapon.id])
        self.assertEqual(weapon.parent_container_id, player.id)
        self.assertIsNone(native_weapon_draw_location(weapon))
        self.assertNotIn(opponent.id, json.dumps(two["character"]))
        old_id = weapon.id

        session.generate(GENERATE)
        replacement = session.active_candidate
        replacement_player = replacement.participants[0].native.being
        replacement_weapon = replacement.universe.get_object_by_id(replacement_player.possessions[0])
        self.assertNotEqual(replacement_weapon.id, old_id)
        self.assertEqual(replacement.encounter.time, 0)
        self.assertEqual(replacement_player.current.body_parts,
                         {"left hand": None, "right hand": None})
        self.assertEqual(replacement_player.weapons, [])
        self.assertIsNotNone(native_weapon_draw_location(replacement_weapon))

    def test_opt_in_scenario_is_strict_and_failed_replacement_preserves_active_candidate(self):
        from arena_browser_session import ArenaBrowserRequestError

        invalid = draw_scenario()
        invalid["player_hand_slots"] = {"right hand": "forged-object-id"}
        with self.assertRaisesRegex(ArenaBrowserRequestError, "exactly one free right hand"):
            GeneratedArenaSession(authored_draw_scenario=invalid)

        session = GeneratedArenaSession(root_seed_factory=iter((20261122, 20261123)).__next__,
                                        authored_draw_scenario=draw_scenario())
        session.generate(GENERATE)
        original = session.active_candidate
        original_view = session.public_view()
        with patch("arena_authored_draw_scenario.author_scenario",
                   side_effect=ValueError("fixture native preflight refusal")):
            with self.assertRaisesRegex(ArenaBrowserRequestError, "candidate could not be activated"):
                session.generate(GENERATE)
        self.assertIs(session.active_candidate, original)
        self.assertEqual(session.public_view(), original_view)

    def test_normal_generated_arena_does_not_receive_authored_hand_or_weapon(self):
        session, candidate, player = arena(seed=20261124)
        self.assertEqual(player.current.body_parts, player.original.body_parts)
        self.assertEqual(player.current.body_parts,
                         {"left hand": None, "right hand": None})
        self.assertEqual(player.possessions, [])
        self.assertEqual(player.weapons, [])
        self.assertFalse(candidate.ground_objects)
        self.assertFalse(any(type(obj) is WeaponInstance and obj.parent_container_id == player.id
                             for obj in candidate.universe.object_registry.object_instances.values()))

    def test_ordinary_generated_human_and_high_elf_use_native_hand_templates(self):
        expected = {"left hand": None, "right hand": None}
        for seed, native_type in ((20261120, "Human"), (20261121, "High elf")):
            with self.subTest(native_type=native_type):
                session = GeneratedArenaSession(root_seed_factory=lambda seed=seed: seed)
                view = session.generate(GENERATE)
                candidate = session.active_candidate
                player = candidate.participants[0].native.being
                opponent = candidate.participants[1].native.being
                self.assertEqual(player.original.obj_type, native_type)
                self.assertEqual(player.current.body_parts, expected)
                self.assertEqual(player.current.body_parts, player.original.body_parts)
                self.assertEqual(view["character"]["anatomy"], {
                    "status": "available", "hands": [
                        {"name": "left hand", "occupancy": "empty"},
                        {"name": "right hand", "occupancy": "empty"}]})
                # Arena presentation adds a session-only label to the opponent;
                # it remains the sole other Being in the observer's entity view.
                opponent_projection, = (row for row in view["entities"]
                                        if row["category"] == "being")
                self.assertNotIn("anatomy", opponent_projection)
                self.assertNotIn("body_parts", opponent_projection)
                source = json.loads(candidate.participants[0].native.source_record_bytes)
                scores = source["state"]["scores"]
                self.assertEqual(player.get_abilities(), {
                    "STR": scores[0], "INT": scores[1], "WIS": scores[2],
                    "DEX": scores[3], "CON": scores[4], "CHA": scores[5],
                    "FIT": scores[4]})
                self.assertEqual(player.get_hit_points(), source["state"]["hps"])
                self.assertEqual(player.get_experience(), 10000)
                from measured_values import truncate_measurement
                self.assertEqual(player.current.length,
                                 truncate_measurement(source["state"]["height"]))
                self.assertEqual(player.current.weight,
                                 truncate_measurement(source["state"]["weight"]))
                self.assertEqual(player.possessions, [])
                self.assertEqual(player.weapons, [])
                self.assertEqual(opponent.possessions, [])

    def test_native_hand_projection_marks_unsupported_template_unrepresented(self):
        from arena_browser_session import GeneratedArenaSession
        from being import BeingInstance
        from library import Library

        library = Library(config_dir=str(ROOT / "src" / "config"))
        skeleton = BeingInstance(library.get_being_definition("Skeleton"), "Skeleton")
        self.assertEqual(skeleton.current.body_parts, {})
        self.assertEqual(GeneratedArenaSession._native_hand_projection(
            skeleton, {"status": "available", "items": []}),
            {"status": "unrepresented", "hands": []})

    def test_revision_61_re_ready_timing_uses_weapon_and_motion_table_values(self):
        _, candidate, _ = arena()
        weapons = candidate.universe.get_weapon_dictionary()
        dagger = weapons.get_object_definition("Dagger")
        longsword = weapons.get_object_definition("Longsword")
        repeating_crossbow = weapons.get_object_definition("Repeating crossbow")
        self.assertEqual([re_ready_time_after_strike(dagger, motion)
                          for motion in ("range", "swing", "thrust")], [1, 1, 1])
        self.assertEqual(re_ready_time_after_strike(longsword, "swing"), 2)
        # This native-config row is absent from the adopted r61 appendix. The
        # helper preserves its arithmetic zero without creating any Action.
        self.assertEqual(re_ready_time_after_strike(repeating_crossbow, "range"), 0)

    def test_draw_commits_only_at_two_second_boundary_and_consumes_source_evidence(self):
        session, candidate, player = arena(seed=20261109)
        weapon = add_authored_drawable_dagger(session, candidate, player)
        other_ledger = object.__getattribute__(
            candidate.participants[1].native.being, "__dict__")["_arena_perception_ledger"]
        self.assertNotIn(weapon.id, {row.entity_id for row in other_ledger.current})
        activate(session)
        start = int(candidate.encounter.time)
        handle, view = select_draw(session, weapon)
        entry = next(row for row in view["action_catalog"]["entries"]
                     if row["name"] == "ready weapon")
        self.assertEqual(entry["status"], "available")
        self.assertEqual(entry["display_name"], "Draw (2 s)")
        self.assertEqual(entry["hands"], ["left hand", "right hand"])
        self.assertIn("worn sheath", entry["reason"])
        weight = view["character"]["inventory"]["carried_weight_pounds"]
        accepted = session.choose_ready_weapon({"handle": handle, "hand": "right hand"})
        action_id = session._ready_weapon_action_id
        self.assertEqual(accepted["ready_weapon_action"]["duration_seconds"], 2)
        self.assertEqual(accepted["ready_weapon_action"]["seconds_remaining"], 2)

        first = session.advance_one_second()
        self.assertEqual(first["time_seconds"], start + 1)
        self.assertEqual(first["ready_weapon_action"]["status"], "executing")
        self.assertEqual(first["ready_weapon_action"]["seconds_remaining"], 1)
        self.assertEqual(first["character"]["inventory"]["items"][0]["status"],
                         "carried; not readied")
        self.assertEqual(player.current.body_parts["right hand"], None)
        self.assertEqual(player.weapons, [])
        self.assertIsNotNone(native_weapon_draw_location(weapon))

        second = session.advance_one_second()
        self.assertEqual(second["time_seconds"], start + 2)
        self.assertEqual(second["ready_weapon_action"]["outcome"], "success")
        self.assertEqual(second["character"]["inventory"]["items"][0]["status"],
                         "readied in right hand")
        self.assertEqual(second["character"]["anatomy"]["hands"], [
            {"name": "left hand", "occupancy": "empty"},
            {"name": "right hand", "occupancy": "occupied",
             "object": {"handle": second["character"]["inventory"]["items"][0]["handle"],
                        "name": "Test Dagger", "type": "Dagger"}}])
        self.assertEqual(second["character"]["inventory"]["carried_weight_pounds"], weight)
        self.assertEqual(player.possessions, [weapon.id])
        self.assertEqual(weapon.parent_container_id, player.id)
        self.assertEqual(player.weapons, [weapon.id])
        expected_parts = dict(player.original.body_parts)
        expected_parts["right hand"] = weapon.id
        self.assertEqual(player.current.body_parts, expected_parts)
        self.assertIsNone(native_weapon_draw_location(weapon))
        self.assertEqual(candidate.encounter.inspect_committed(start + 2)
                         .action(action_id).facts.outcome, "success")
        self.assertNotIn(candidate.participants[1].native.being.id,
                         json.dumps(second["character"]))

    def test_pending_draw_restores_and_commits_in_a_fresh_process(self):
        session, candidate, player = arena(seed=20261162)
        weapon = add_authored_drawable_dagger(session, candidate, player)
        activate(session)
        handle, _ = select_draw(session, weapon)
        accepted = session.choose_ready_weapon({"handle": handle, "hand": "right hand"})
        action_id = session._ready_weapon_action_id
        session.advance_one_second()
        self.assertEqual(candidate.encounter.time, 2)
        self.assertIn(action_id, candidate.encounter.pending_action_list)
        self.assertEqual(player.current.body_parts["right hand"], None)

        script = """import json,sys
from arena_browser_session import GeneratedArenaSession
from weapon import native_weapon_draw_location
s=GeneratedArenaSession();s.load_encounter_bytes(sys.stdin.buffer.read())
c=s.active_candidate;e=c.encounter;a=c.universe.get_event_by_id(sys.argv[1])
w=c.universe.get_object_by_id(sys.argv[2]);p=c.participants[0].native.being
assert a.id in e.pending_action_list and e.time==2 and a.end_time==3
assert p.current.body_parts['right hand'] is None
assert native_weapon_draw_location(w)['owner_id']==p.id
s.advance_one_second()
assert a.id in e.finished_action_list and p.current.body_parts['right hand']==w.id
assert native_weapon_draw_location(w) is None
print(json.dumps({'action_id':a.id,'weapon_id':w.id,'time':e.time,
    'committed':a.id in e.finished_action_list,'hand':p.current.body_parts['right hand']}))
"""
        restored = subprocess.run([sys.executable, "-B", "-c", script, action_id, weapon.id],
            input=session.save_encounter_bytes(), cwd=ROOT,
            capture_output=True, check=False, timeout=60)
        self.assertEqual(restored.returncode, 0, restored.stderr.decode("utf-8", "replace"))
        result = json.loads(restored.stdout)
        self.assertEqual(result["action_id"], action_id)
        self.assertEqual(result["weapon_id"], weapon.id)
        self.assertEqual(result["time"], 3)
        self.assertTrue(result["committed"])
        self.assertEqual(result["hand"], weapon.id)

    def test_cancelled_pending_draw_restores_with_identity_and_uncommitted_custody(self):
        session, candidate, player = arena(seed=20261163)
        weapon = add_authored_drawable_dagger(session, candidate, player)
        activate(session)
        handle, _ = select_draw(session, weapon)
        accepted = session.choose_ready_weapon({"handle": handle, "hand": "right hand"})
        action_id = session._ready_weapon_action_id
        session.advance_one_second()
        candidate.encounter.cancel_action(action_id)
        self.assertIn(action_id, candidate.encounter.cancelled_action_list)

        script = """import json,sys
from arena_browser_session import GeneratedArenaSession
from weapon import native_weapon_draw_location
s=GeneratedArenaSession();s.load_encounter_bytes(sys.stdin.buffer.read())
c=s.active_candidate;e=c.encounter;a=c.universe.get_event_by_id(sys.argv[1])
w=c.universe.get_object_by_id(sys.argv[2]);p=c.participants[0].native.being
assert a.id in e.cancelled_action_list and a.id not in e.pending_action_list
assert e._choice_book._states[a.id]=='cancelled' and e.time==2
assert p.current.body_parts['right hand'] is None
assert w.id in p.possessions and w.id not in p.weapons
assert native_weapon_draw_location(w)['owner_id']==p.id
print(json.dumps({'action_id':a.id,'weapon_id':w.id,'time':e.time,
    'cancelled':a.id in e.cancelled_action_list,'hand':p.current.body_parts['right hand']}))
"""
        restored = subprocess.run([sys.executable, "-B", "-c", script, action_id, weapon.id],
            input=session.save_encounter_bytes(), cwd=ROOT,
            capture_output=True, check=False, timeout=60)
        self.assertEqual(restored.returncode, 0, restored.stderr.decode("utf-8", "replace"))
        result = json.loads(restored.stdout)
        self.assertEqual(result, {"action_id": action_id, "weapon_id": weapon.id,
            "time": 2, "cancelled": True, "hand": None})

    def test_ground_pickup_remains_carried_unreadied_and_does_not_create_draw_location(self):
        session, candidate, player = arena(seed=20261110, ground_dagger=True)
        placement = candidate.ground_objects[0]
        ground = candidate.universe.get_object_by_id(placement.native_object_id)
        player.current.body_parts["right hand"] = None
        address = HexAddress(placement.column, placement.row)
        destination = candidate.arena_map.layout.center_position(address, z=player.get_position().z)
        if player.get_position() != destination:
            session.choose_destination({"column": address.column, "row": address.row,
                                       "rate": "sprint", "facing_policy": "turn"})
            while session.public_view()["movement_plan"] is not None:
                session.advance_one_second()
        visible = next(row for row in session.public_view()["entities"]
                       if row["handle"] in session._view_handles.values()
                       and row["type"] == "Dagger")
        session.inspect_entity({"handle": visible["handle"]})
        session.choose_pickup({"handle": visible["handle"]})
        picked = session.advance_one_second()
        self.assertEqual(picked["pickup_action"]["outcome"], "success")
        self.assertEqual(ground.parent_container_id, player.id)
        self.assertIn(ground.id, player.possessions)
        self.assertEqual(player.current.body_parts["right hand"], None)
        self.assertEqual(
            [(row["name"], row["occupancy"]) for row in picked["character"]["anatomy"]["hands"]],
            [(name, "empty") for name in ("left hand", "right hand")
             if name in player.current.body_parts])
        self.assertEqual(player.weapons, [])
        self.assertIsNone(native_weapon_draw_location(ground))
        draw = next(row for row in picked["action_catalog"]["entries"]
                    if row["name"] == "ready weapon")
        self.assertEqual(draw["status"], "unavailable")
        self.assertIn("no authored drawable source location", draw["reason"])
        self.assertEqual(picked["character"]["inventory"]["items"][0]["status"],
                         "carried; not readied")

    def test_missing_occupied_malformed_or_wrong_owner_evidence_fails_closed(self):
        session, candidate, player = arena(seed=20261111)
        weapon = add_authored_drawable_dagger(session, candidate, player)
        activate(session)
        handle, _ = select_draw(session, weapon)
        time_before = candidate.encounter.time
        choices_before = dict(candidate.encounter._choice_book._choices)
        player.current.body_parts["right hand"] = weapon.id
        with self.assertRaisesRegex(ValueError, "already held/readied"):
            session.choose_ready_weapon({"handle": handle, "hand": "right hand"})
        player.current.body_parts["right hand"] = None
        weapon.current.tags[NATIVE_DRAW_LOCATION_TAG] = {"kind": DRAWABLE_WORN_SHEATH}
        malformed = session.public_view()
        self.assertEqual(next(row for row in malformed["action_catalog"]["entries"]
                             if row["name"] == "ready weapon")["status"], "unavailable")
        self.assertIn("malformed", next(row for row in malformed["action_catalog"]["entries"]
                                        if row["name"] == "ready weapon")["reason"])
        malformed_action = ReadyWeaponAction(candidate.encounter, player.id, weapon.id,
                                             "right hand", int(candidate.encounter.time))
        with self.assertRaisesRegex(ValueError, "draw-location record is malformed"):
            candidate.encounter.schedule_action(malformed_action)
        author_worn_sheath_draw_location(weapon, candidate.participants[1].native.being.id)
        wrong_owner = session.public_view()
        self.assertEqual(next(row for row in wrong_owner["action_catalog"]["entries"]
                             if row["name"] == "ready weapon")["status"], "unavailable")
        self.assertIn("not assigned", next(row for row in wrong_owner["action_catalog"]["entries"]
                                            if row["name"] == "ready weapon")["reason"])
        self.assertEqual(player.weapons, [])
        self.assertEqual(player.possessions, [weapon.id])
        self.assertEqual(player.current.body_parts["right hand"], None)
        self.assertEqual(candidate.encounter.time, time_before)
        self.assertEqual(candidate.encounter._choice_book._choices, choices_before)

    def test_same_second_action_cannot_use_draw_that_has_not_committed(self):
        session, candidate, player = arena(seed=20261112)
        weapon = add_authored_drawable_dagger(session, candidate, player)
        activate(session)
        handle, _ = select_draw(session, weapon)
        session.choose_ready_weapon({"handle": handle, "hand": "right hand"})
        opponent = candidate.participants[1].native.being
        with self.assertRaisesRegex(ValueError, "actor does not hold that weapon"):
            MeleeStrike(candidate.encounter, player.id, opponent.id, weapon.id,
                        motion="thrust", reach=100).prepare_schedule(candidate.encounter)
        session.advance_one_second()
        self.assertEqual(player.current.body_parts["right hand"], None)
        self.assertEqual(player.weapons, [])
        session.advance_one_second()
        self.assertEqual(player.current.body_parts["right hand"], weapon.id)

    def test_overlapping_draw_claims_by_same_actor_are_rejected(self):
        session, candidate, player = arena(seed=20261113)
        weapon = add_authored_drawable_dagger(session, candidate, player)
        activate(session)
        start = int(candidate.encounter.time)
        first = ReadyWeaponAction(candidate.encounter, player.id, weapon.id, "right hand", start)
        second = ReadyWeaponAction(candidate.encounter, player.id, weapon.id, "right hand", start)
        with self.assertRaisesRegex(ValueError, "require acquired Multi-action skill"):
            candidate.encounter.schedule_choice((first, second))
        self.assertEqual(candidate.encounter.time, start)
        self.assertEqual(player.possessions, [weapon.id])
        self.assertEqual(player.weapons, [])
        self.assertEqual(player.current.body_parts["right hand"], None)
        self.assertIsNotNone(native_weapon_draw_location(weapon))

    def test_interruption_and_publication_rollback_preserve_draw_location_and_identity(self):
        session, candidate, player = arena(seed=20261114)
        weapon = add_authored_drawable_dagger(session, candidate, player)
        activate(session)
        handle, _ = select_draw(session, weapon)
        session.choose_ready_weapon({"handle": handle, "hand": "right hand"})
        action_id = session._ready_weapon_action_id
        choice_id = next(key for key, row in candidate.encounter._choice_book._choices.items()
                         if action_id in row.view.action_ids)
        candidate.encounter._choice_book.undo(choice_id)
        self.assertNotIn(action_id, candidate.universe.event_history)
        self.assertEqual(player.current.body_parts["right hand"], None)
        self.assertIsNotNone(native_weapon_draw_location(weapon))

        session, candidate, player = arena(seed=20261115)
        weapon = add_authored_drawable_dagger(session, candidate, player)
        activate(session)
        handle, _ = select_draw(session, weapon)
        session.choose_ready_weapon({"handle": handle, "hand": "right hand"})
        before_rng = session._rng_cursor.state
        before_view = session.public_view()
        original_apply = _WritePlan.apply_phase

        def fail_after_target_write(plan, phase):
            original_apply(plan, phase)
            if phase == "targets":
                raise RuntimeError("injected Draw publication fault")

        session.advance_one_second()
        with patch.object(_WritePlan, "apply_phase", fail_after_target_write):
            with self.assertRaises(ArenaBrowserRequestError) as caught:
                session.advance_one_second()
        failure = caught.exception.__cause__
        self.assertIsInstance(failure, PublicationFailure)
        self.assertFalse(failure.rollback_errors)
        self.assertEqual(candidate.encounter.time, before_view["time_seconds"] + 1)
        self.assertEqual(session._rng_cursor.state, before_rng)
        self.assertEqual(player.current.body_parts["right hand"], None)
        self.assertEqual(player.weapons, [])
        self.assertEqual(player.possessions, [weapon.id])
        self.assertEqual(native_weapon_draw_location(weapon)["owner_id"], player.id)
        candidate.encounter.recover_transactional_progression(failure.recovery_token)
        drawn = session.advance_one_second()
        self.assertEqual(drawn["ready_weapon_action"]["outcome"], "success")
        self.assertEqual(player.current.body_parts["right hand"], weapon.id)
        self.assertIsNone(native_weapon_draw_location(weapon))

    def test_re_ready_formula_zero_config_case_is_not_a_zero_duration_action(self):
        _, candidate, _ = arena()
        weapons = candidate.universe.get_weapon_dictionary()
        self.assertEqual(re_ready_time_after_strike(
            weapons.get_object_definition("Repeating crossbow"), "range"), 0)
        self.assertEqual(ReadyWeaponAction.DRAW_DURATION_SECONDS, 2)


if __name__ == "__main__":
    unittest.main()
